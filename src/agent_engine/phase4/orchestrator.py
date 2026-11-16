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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from agent_engine import config
from agent_engine.gates import APPROVED_SUFFIX, Gate, load_gates, record_decision
from agent_engine.history import file_digest

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
        held = all((root / f).is_file() and file_digest(root / f) == d for f, d in record.get("artifacts", {}).items())
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
    path = root / STATE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


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
        outputs_exist = all((root / f).is_file() for f in gate.files)
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
    return tuple(gate.files) if gate else ()


# --- running ----------------------------------------------------------------------------------------------------

Runner = Callable[[str, str, str], dict]


def run_agent(agent: str, request: str, project: str) -> dict:
    """`agent-engine run` as a child process, output shown live. Returns {status, exit_code, rate_limited, gaps}."""
    cmd = [sys.executable, "-m", "agent_engine.cli", "run", request, "--agent", agent, "--project-name", project]
    proc = subprocess.Popen(
        cmd, cwd=config.ENGINE_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    tail: list[str] = []
    for line in proc.stdout:  # type: ignore[union-attr]
        print(line, end="")
        tail = (tail + [line])[-80:]
    code = proc.wait()
    report, status, gaps = _root(project) / "report.json", "fail", []
    if report.is_file():
        data = json.loads(report.read_text(encoding="utf-8"))
        if data.get("agent") == agent:
            status = data.get("status", "fail")
            gaps = data.get("verdict", {}).get("gaps", [])
    text = "".join(tail)
    return {
        "status": status, "exit_code": code, "gaps": gaps,
        "rate_limited": any(m in text for m in RATE_LIMIT_MARKERS),
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


def orchestrate(
    project: str, sprint: int = 1, test_approve: bool = False, publish: bool = False, plan_only: bool = False,
    runner: Runner = run_agent, out: Callable[[str], None] = print,
) -> int:
    root, gates = _root(project), load_gates()
    if not (root / PROJECT_FILE).is_file():
        out(f"ERROR: {root / PROJECT_FILE} is missing. Add the project inputs first (phase4 init, or copy your own).")
        return FAILED
    state = load_state(root)
    ran: list[str] = []
    for _ in range(MAX_STEPS):
        steps = assess(project, sprint, gates)
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
                    out(f">>> TEST-approved {s.stage.gate} (not a human sign-off)")
                continue
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

        for what in ("backlog", "sprint", "assignments", "infra"):
            out(f"\n>>> publish {what}")
            out(json.dumps(PUBLISHERS[what](project), indent=2, default=str))
    else:
        out("Next: add --publish (or `agent-engine phase4 publish backlog|sprint|assignments|infra`) to push to the tracker / GitHub.")
    return DONE
