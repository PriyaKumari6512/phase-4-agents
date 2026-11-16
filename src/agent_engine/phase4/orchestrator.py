"""Phase 4 orchestrator: runs the four agents when, and only when, they are needed.

`agent-engine phase4 orchestrate --project-name P` reads the project folder (inputs, outputs, gate decisions),
decides the next step with plain code (no model call), runs that agent with `agent-engine run`, and repeats until
every output exists and every gate is approved, or it needs a human:

  * an input is missing                       -> stop, say which file to add
  * a gate is waiting (or went stale)         -> stop, say which gate to approve (the orchestrator never approves
                                                 unless `--test-approve` is given, and that is recorded as a test)
  * a gate asked for changes                  -> run the owning agent again with the gate comment as the request
  * an input an agent read has changed        -> run only that agent (and, through the changed outputs, the agents
                                                 after it); a team or calendar change never re-runs Task Breakdown
  * an agent's validator ends partial / fails -> stop and show the open gaps (no endless retry)
  * the subscription rate limit               -> stop; run the same command later and it resumes where it was

What each agent last read is kept in phase4/orchestrator-state.json. A project that was run by hand before has no
state: its existing outputs are taken as up to date.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from agent_engine import config, perf
from agent_engine.gates import APPROVED_SUFFIX, Gate, load_gates, record_decision
from agent_engine.history import file_digest
from agent_engine.runtime import atomic_json, project_lock

STATE_FILE = "phase4/orchestrator-state.json"
PROJECT_FILE = "phase4/project.json"
MAX_STEPS = 12
RATE_LIMIT_MARKERS = ("SUBSCRIPTION_RATE_LIMITED", "rate_limit_error")

# Exit codes of `phase4 orchestrate`.
DONE, FAILED, WAITING = 0, 1, 2


@dataclass(frozen=True)
class Stage:
    agent: str
    gate: str                                   # the gate whose files are this agent's outputs
    files: tuple[str, ...]                      # inputs that must exist; a change re-runs the agent
    optional: tuple[str, ...] = ()              # inputs read when present
    project_keys: tuple[str, ...] | None = None  # parts of phase4/project.json it depends on (None = all)
    needs: tuple[str, ...] = ()                 # gates that must be approved before it runs
    request: str = ""


STAGES: tuple[Stage, ...] = (
    Stage(
        "task-breakdown", "P4-G1", ("prd.md", "architecture.md"), ("phase4/history.json",),
        ("project_name", "code_repos", "infra_repo", "definition_of_done", "story_point_scale",
         "hours_per_story_point", "max_story_points_per_story", "deadlines"),
        request="Break prd.md down into a backlog.",
    ),
    Stage(
        "infra-pipeline", "P4-G4", ("architecture.md",), (),
        ("project_name", "tracker", "code_repos", "infra_repo"),
        request="Set up dev, stg and prod.",
    ),
    Stage(
        "sprint-planning", "P4-G2", ("backlog/backlog.json",), ("phase4/history.json",),
        needs=("P4-G1",), request="Plan the sprints.",
    ),
    Stage(
        "work-allocation", "P4-G3", ("sprint/sprint-plan.json", "backlog/backlog.json"),
        ("phase4/skill-profiles.json", "phase4/agent-outcomes.json"),
        needs=("P4-G2",), request="Assign sprint {sprint}.",
    ),
)
STAGE_BY_AGENT = {s.agent: s for s in STAGES}


# --- state of the project folder -------------------------------------------------------------------------------

def _root(project: str) -> Path:
    return Path(config.OUTPUTS_DIR) / project


def _digest_json(value: object) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def input_digests(stage: Stage, root: Path, sprint: int) -> dict[str, str]:
    """What the agent reads, as digests: whole files, the parts of project.json it uses, and its parameters."""
    with perf.span("fs", "input_digests", stage=stage.agent) as sp:
        digests = _input_digests(stage, root, sprint)
        sp.set(inputs=len(digests))
    return digests


def _input_digests(stage: Stage, root: Path, sprint: int) -> dict[str, str]:
    digests = {f: file_digest(root / f) for f in (*stage.files, *stage.optional) if (root / f).is_file()}
    project = root / PROJECT_FILE
    if project.is_file():
        data = json.loads(project.read_text(encoding="utf-8"))
        if stage.project_keys is not None:
            data = {k: data.get(k) for k in stage.project_keys}
        digests[PROJECT_FILE] = _digest_json(data)
    if stage.agent == "work-allocation":
        digests["param:sprint"] = str(sprint)
        manifest = root / "infra/manifest.json"
        if (root / f"gates/P4-G4{APPROVED_SUFFIX}").is_file() and manifest.is_file():  # CI-ready repos let AI take tasks
            digests["infra/manifest.json"] = file_digest(manifest)
    if stage.agent == "infra-pipeline" and project.is_file():
        digests[PROJECT_FILE] = _digest_json(json.loads(project.read_text(encoding="utf-8")))
        from agent_engine.phase4.infra import catalog_dir
        catalog = catalog_dir()
        for p in sorted(catalog.rglob("*")):
            if p.is_file():
                digests["catalog:" + p.relative_to(catalog).as_posix()] = file_digest(p)
    if stage.agent == "task-breakdown":
        for p in sorted((root / "specs").rglob("*.md")):
            digests[p.relative_to(root).as_posix()] = file_digest(p)
    if stage.agent in ("sprint-planning", "work-allocation"):
        digests["param:planning_date"] = datetime.now(timezone.utc).date().isoformat()
        for rel in ("phase4/ci-readiness.json", "phase4/committed-work.json"):
            if (root / rel).is_file():
                digests[rel] = file_digest(root / rel)
    for p in sorted((config.AGENTS_DIR / stage.agent).rglob("*")):
        if p.is_file():
            digests["pack:" + p.relative_to(config.AGENTS_DIR).as_posix()] = file_digest(p)
    if Path(config.GATES_FILE).is_file():
        digests["gates:contract"] = file_digest(Path(config.GATES_FILE))
    return digests


def gate_state(root: Path, gate: Gate) -> tuple[str, dict]:
    """(approved | stale | changes_requested | rejected | pending, the latest decision record)."""
    history, last = root / "gates" / "history.jsonl", {}
    if history.is_file():
        for line in history.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                if record.get("gate") == gate.name:
                    last = record
    approval = root / gate.approval_file
    if approval.is_file():
        record = json.loads(approval.read_text(encoding="utf-8"))
        held = (record.get("decision") == "approved" and record.get("gate") == gate.name
                and record.get("project") == root.name and set(record.get("artifacts", {})) == set(gate.files)
                and all((root / f).is_file() and file_digest(root / f) == d for f, d in record.get("artifacts", {}).items()))
        return ("approved" if held else "stale"), record
    if last.get("decision") == "rejected":
        return "rejected", last
    if last.get("decision") == "changes_requested":
        # The agent has not answered the request while the gate files still equal what was reviewed.
        unchanged = all((root / f).is_file() and file_digest(root / f) == d for f, d in last.get("artifacts", {}).items())
        return ("changes_requested" if unchanged else "pending"), last
    return "pending", last


def load_state(root: Path) -> dict:
    path = root / STATE_FILE
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def save_state(root: Path, state: dict) -> None:
    with perf.span("fs", "save_orchestrator_state"):
        path = root / STATE_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_json(path, state)


@dataclass
class Step:
    stage: Stage
    action: str      # run | gate_pending | done | blocked_input | waiting_gate | escalate
    why: str
    request: str = ""
    gate_status: str = ""


def assess(project: str, sprint: int = 1, gates: dict[str, Gate] | None = None) -> list[Step]:
    """The decision table: one Step per agent, from the current files and gate decisions (no side effects)."""
    root, gates = _root(project), gates if gates is not None else load_gates()
    state = load_state(root)
    steps = []
    for stage in STAGES:
        gate = gates[stage.gate]
        missing = [f for f in stage.files if not (root / f).is_file() and not _produced_by_earlier_stage(f, stage)]
        if missing:
            steps.append(Step(stage, "blocked_input", "missing input: " + ", ".join(missing)))
            continue
        waiting = []
        for needed in stage.needs:
            # Waits until the agent that owns the needed gate is done: gate approved AND its output up to date
            # (an old approval of a backlog that is about to change must not let a later agent start).
            owner = next(s for s in steps if s.stage.gate == needed)
            if owner.action != "done":
                waiting.append(f"{owner.stage.agent} is not done ({owner.why})")
        if waiting:
            steps.append(Step(stage, "waiting_gate", "; ".join(waiting)))
            continue
        status, record = gate_state(root, gate)
        request = stage.request.format(sprint=sprint)
        outputs_exist = all((root / f).is_file() for f in _outputs(stage))
        if not outputs_exist:
            steps.append(Step(stage, "run", "no output yet", request, status))
            continue
        recorded = state.get(stage.agent, {}).get("inputs")
        now = input_digests(stage, root, sprint)
        changed = sorted(k for k in now if recorded is not None and recorded.get(k) != now[k])
        changed += sorted(k for k in (recorded or {}) if k not in now)
        feedback = status == "changes_requested"
        if feedback or changed:
            parts, why = [], []
            if feedback:
                comment = record.get("comment") or "(no comment given)"
                parts.append(f"Gate {gate.name} was reviewed by {record.get('approver', {}).get('name', 'a reviewer')} "
                             f"and changes were requested: {comment}")
                why.append(f"{gate.name} asked for changes")
            if changed:
                parts.append("These inputs changed since your last run: " + ", ".join(changed)
                             + ". Update your output to match them and change only what needs changing.")
                why.append("inputs changed: " + ", ".join(changed))
            steps.append(Step(stage, "run", "; ".join(why), "\n\n".join(parts), status))
        elif status == "rejected":
            steps.append(Step(stage, "escalate", f"{gate.name} was rejected; a human has to decide", gate_status=status))
        elif status == "approved":
            steps.append(Step(stage, "done", f"{gate.name} approved, output up to date", gate_status=status))
        else:
            note = state.get(stage.agent, {}).get("status", "")
            tail = f" (validator: {note})" if note and note not in ("success", "adopted") else ""
            steps.append(Step(stage, "gate_pending", f"{gate.name} {status}{tail}", gate_status=status))
    return steps


def _produced_by_earlier_stage(file: str, stage: Stage) -> bool:
    """A file another agent will write before this one runs does not make this stage 'blocked'."""
    return any(file in _outputs(s) for s in STAGES[: STAGES.index(stage)])


def _outputs(stage: Stage) -> tuple[str, ...]:
    gate = load_gates().get(stage.gate)
    from agent_engine.agent import load_pack
    try:
        declared = load_pack(stage.agent).output_files
    except ValueError:
        declared = []
    return tuple(dict.fromkeys([*(gate.files if gate else []), *declared]))


# --- running ----------------------------------------------------------------------------------------------------

Runner = Callable[[str, str, str], dict]
SUCCESS = ("success", "done")


def read_child_report(report: Path, agent: str, invocation_id: str, exit_code: int) -> tuple[str, list[str], str | None]:
    """(status, gaps, problem) for the child run `invocation_id`.

    report.json is shared by every run of the project, so a child that fails before writing its own report
    leaves an older one in place. Only a report stamped with this invocation's id counts, and its status must
    agree with the process exit code (0 exactly for success/done); anything else is a failure with a reason.
    """
    if not report.is_file():
        return "fail", [], "the child wrote no report.json"
    try:
        data = json.loads(report.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return "fail", [], f"report.json could not be read: {e}"
    if data.get("invocation_id") != invocation_id:
        return "fail", [], "report.json is not from this invocation (an older or different run's report)"
    if data.get("agent") != agent:
        return "fail", [], f"report.json is for agent {data.get('agent')!r}, not {agent!r}"
    status = data.get("status", "fail")
    gaps = (data.get("verdict") or {}).get("gaps", [])
    if exit_code != 0 and status in SUCCESS:
        return "fail", gaps, f"exit code {exit_code} contradicts report status {status!r}"
    if exit_code == 0 and status not in SUCCESS:
        return status, gaps, f"exit code 0 with report status {status!r}"
    return status, gaps, None


def run_agent(agent: str, request: str, project: str) -> dict:
    """`agent-engine run` as a child process, output shown live.
    Returns {status, exit_code, rate_limited, gaps, invocation_id, report_problem}."""
    invocation_id = perf.new_id(24)
    cmd = [sys.executable, "-m", "agent_engine.cli", "run", request, "--agent", agent, "--project-name", project]
    with perf.span("child", agent, agent=agent, invocation_id=invocation_id) as sp:
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", perf.ENV_INVOCATION: invocation_id, **perf.child_env(sp.id)}
        t0 = time.perf_counter()
        proc = subprocess.Popen(
            cmd, cwd=config.ENGINE_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", env=env,
        )
        sp.set(spawn_s=round(time.perf_counter() - t0, 4))
        tail: list[str] = []
        first_output = None
        for line in proc.stdout:  # type: ignore[union-attr]
            if first_output is None:
                first_output = round(time.perf_counter() - t0, 4)
            print(line, end="")
            tail = (tail + [line])[-80:]
        code = proc.wait()
        with perf.span("fs", "read_child_report"):
            status, gaps, problem = read_child_report(_root(project) / "report.json", agent, invocation_id, code)
        text = "".join(tail)
        rate_limited = any(m in text for m in RATE_LIMIT_MARKERS)
        sp.set(exit_code=code, report_status=status, report_problem=problem, first_output_s=first_output,
               rate_limited=rate_limited)
        if status not in SUCCESS:
            sp.set_status("failed", problem or f"stage ended {status}", "stage_outcome")
    return {
        "status": status, "exit_code": code, "gaps": gaps, "rate_limited": rate_limited,
        "invocation_id": invocation_id, "report_problem": problem,
    }


def _approve(root: Path, step: Step, gates: dict[str, Gate], status: str) -> None:
    record_decision(
        root, gates[step.stage.gate], "approved",
        {"name": "Orchestrator (automated test approval)", "role": "NOT a human sign-off"},
        {"name": f"{step.stage.agent} agent"},
        f"Automated test approval by the orchestrator (--test-approve), not a human review. Validator: {status}.",
    )


def format_table(steps: list[Step]) -> str:
    labels = {"run": "RUN", "gate_pending": "WAIT: approve gate", "done": "done", "blocked_input": "BLOCKED: add input",
              "waiting_gate": "waiting for gate", "escalate": "NEEDS A HUMAN"}
    rows = [f"{'agent':17} {'gate':6} {'state':20} why"]
    rows += [f"{s.stage.agent:17} {s.stage.gate:6} {labels[s.action]:20} {s.why}" for s in steps]
    return "\n".join(rows)


def _observe_approvals(root: Path, gates: dict[str, Gate]) -> None:
    """Diagnostics only: when each currently approved gate was decided, and whether it was a test approval."""
    if not perf.enabled():
        return
    for stage in STAGES:
        gate = gates.get(stage.gate)
        approval = root / gate.approval_file if gate else None
        if approval is None or not approval.is_file():
            continue
        try:
            record = json.loads(approval.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        automated = "NOT a human sign-off" in str((record.get("approver") or {}).get("role", ""))
        perf.event("approval_observed", gate.name, decided_at=record.get("decided_at"), automated=automated)


def orchestrate(
    project: str, sprint: int = 1, test_approve: bool = False, publish: bool = False, plan_only: bool = False,
    runner: Runner = run_agent, out: Callable[[str], None] = print,
) -> int:
    pipeline_id = perf.new_id()
    perf.set_pipeline(pipeline_id)
    with perf.span("pipeline", project, project=project, sprint=sprint, test_approve=test_approve, publish=publish,
                   plan_only=plan_only, pipeline_id=pipeline_id) as sp:
        if publish and (blocked := perf.publication_blocked()):
            out(f"ERROR: {blocked}")
            sp.set_status("blocked", blocked, "publication_blocked")
            return FAILED
        if perf.enabled() and not plan_only:
            from agent_engine import perf_manifest

            packs = sorted({p for s in STAGES for p in (s.agent, f"{s.agent}/validator")})
            perf_manifest.write("pipeline", pipeline_id, project=project, packs=packs,
                                execution_mode="publication_authorized" if publish else "generation_only",
                                extra={"test_approve": test_approve, "sprint": sprint})
        with project_lock(_root(project), "orchestrator"):
            code = _orchestrate(project, sprint, test_approve, publish, plan_only, runner, out)
        sp.set(exit_code=code, outcome={DONE: "done", FAILED: "failed", WAITING: "waiting"}.get(code, str(code)))
        if code == FAILED:
            sp.set_status("failed", category="pipeline_outcome")
        return code


def _orchestrate(project: str, sprint: int, test_approve: bool, publish: bool, plan_only: bool, runner: Runner,
                 out: Callable[[str], None]) -> int:
    with perf.span("orchestrator", "preflight"):
        root, gates = _root(project), load_gates()
        if not (root / PROJECT_FILE).is_file():
            out(f"ERROR: {root / PROJECT_FILE} is missing. Add the project inputs first (phase4 init, or copy your own).")
            return FAILED
        state = load_state(root)
        _observe_approvals(root, gates)
    ran: list[str] = []
    for _ in range(MAX_STEPS):
        with perf.span("orchestrator", "assess") as asp:
            steps = assess(project, sprint, gates)
            asp.set(actions={s.stage.agent: s.action for s in steps})
        # Existing outputs of a project run by hand: take them as up to date.
        for s in steps:
            if s.action in ("done", "gate_pending") and s.stage.agent not in state:
                state[s.stage.agent] = {"inputs": input_digests(s.stage, root, sprint), "status": "adopted",
                                        "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        if not plan_only:
            save_state(root, state)
        out(format_table(steps))
        blocked = [s for s in steps if s.action in ("blocked_input", "escalate")]
        runnable = [s for s in steps if s.action == "run"]
        if plan_only:
            return DONE if all(s.action == "done" for s in steps) else WAITING
        if blocked and not runnable:
            for s in blocked:
                out(f"\nSTOP {s.stage.agent}: {s.why}")
            return WAITING
        if runnable:
            step = runnable[0]
            out(f"\n>>> running {step.stage.agent}: {step.why}\n")
            digests = input_digests(step.stage, root, sprint)
            result = runner(step.stage.agent, step.request, project)
            if step.stage.agent == "task-breakdown":
                digests = {k: v for k, v in digests.items() if not k.startswith("specs/")}
                digests.update({k: v for k, v in input_digests(step.stage, root, sprint).items() if k.startswith("specs/")})
            ran.append(step.stage.agent)
            if result.get("rate_limited"):
                out(f"\nSTOP: the subscription rate limit stopped {step.stage.agent}. Run the same command after the "
                    "limit resets; it resumes from here (an ANTHROPIC_API_KEY in .env avoids the wait).")
                return FAILED
            if result["status"] not in ("success", "done"):
                if all((root / f).is_file() for f in gates[step.stage.gate].files):
                    state[step.stage.agent] = {"inputs": digests, "status": result["status"],
                                               "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
                    save_state(root, state)
                out(f"\nSTOP: {step.stage.agent} ended {result['status']!r}; a human has to look at it.")
                if result.get("report_problem"):
                    out(f"  report: {result['report_problem']}")
                for gap in result.get("gaps", []):
                    out(f"  - {gap}")
                return FAILED
            state[step.stage.agent] = {"inputs": digests, "status": "success",
                                       "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            save_state(root, state)
            continue
        pending = [s for s in steps if s.action == "gate_pending"]
        if pending:
            approvable = [s for s in pending if state.get(s.stage.agent, {}).get("status") in ("success", "adopted")]
            if test_approve and approvable:
                for s in approvable:
                    _approve(root, s, gates, state[s.stage.agent]["status"])
                    perf.event("gate_decision", s.stage.gate, decision="approved", automated=True,
                               decided_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
                    out(f">>> TEST-approved {s.stage.gate} (not a human sign-off)")
                continue
            # Diagnostics: human waiting starts now; it ends at the gate decision (gate command or approval record).
            perf.event("approval_wait_start", ",".join(s.stage.gate for s in pending),
                       gates=[s.stage.gate for s in pending], project=project)
            out("\nWAITING for a human. Approve (or request changes) with:")
            for s in pending:
                out(f'  uv run agent-engine gate {s.stage.gate} --project-name {project} --decision approved '
                    f'--approver "<name>" --submitted-by "<name>"      # {gates[s.stage.gate].description}')
            out("then run the same orchestrate command again.")
            return WAITING
        waiting = [s for s in steps if s.action == "waiting_gate"]
        if waiting:  # nothing runnable, no gate to approve here: an upstream stage is blocked
            return WAITING
        break  # every stage is done
    else:
        out(f"STOP: no end after {MAX_STEPS} steps; check the project folder.")
        return FAILED

    out(f"\nALL DONE for {project}: every output exists and every gate is approved. Agents run this time: "
        f"{', '.join(ran) or 'none'}.")
    if publish:
        from agent_engine.phase4.publish import PUBLISHERS

        for what in ("infra", "backlog", "sprint", "assignments"):
            out(f"\n>>> publish {what}")
            with perf.span("publish", what, project=project):
                out(json.dumps(PUBLISHERS[what](project), indent=2, default=str))
    else:
        out("Next: add --publish (or `agent-engine phase4 publish backlog|sprint|assignments|infra`) to push to the tracker / GitHub.")
    return DONE
