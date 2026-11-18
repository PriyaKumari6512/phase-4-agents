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
  * an agent's deterministic checks fail      -> stop and show the open gaps (no endless retry)
  * a rate limit or transient provider error  -> wait and retry (bounded); beyond the bound stop with the reason

Every run is fresh and depends only on its inputs. What each agent last read is kept in
phase4/orchestrator-state.json: a stage is skipped only when its recorded inputs are byte-for-byte unchanged and its
last run succeeded (a pure cache). Saved recovery state (interrupted repairs, reviews, parallel merges) is used only
when `--resume` / PHASE4_RESUME=true asks for it. Outputs without a recorded run are regenerated, not adopted.
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

from agent_engine import config, perf, recovery
from agent_engine.gates import APPROVED_SUFFIX, Gate, load_gates, record_decision
from agent_engine.history import file_digest
from agent_engine.runtime import atomic_json, project_lock

STATE_FILE = "phase4/orchestrator-state.json"
PROJECT_FILE = "phase4/project.json"
MAX_STEPS = 12
RATE_LIMIT_MARKERS = ("SUBSCRIPTION_RATE_LIMITED", "rate_limit_error")
# Provider hiccups that a later attempt usually survives (after the SDK's own retries were exhausted).
TRANSIENT_MARKERS = ("overloaded_error", "Overloaded", "Error code: 529", "Error code: 503", "Error code: 502",
                     "Error code: 500", "APIConnectionError", "Connection error", "APITimeoutError")
_RESET_RE = __import__("re").compile(r"resets in (\d+)s")
# `--resume` / PHASE4_RESUME: reuse saved recovery state. Off by default: runs start fresh.
_RESUME = False
_sleep = time.sleep   # injectable for tests


def _retry_limits() -> tuple[int, float, float]:
    """(attempts, longest single wait in seconds, backoff for transient errors) from the environment."""
    attempts = int(os.environ.get("AGENT_ENGINE_PROVIDER_RETRIES", "3"))
    max_wait = float(os.environ.get("AGENT_ENGINE_RATE_LIMIT_MAX_WAIT_SECONDS", "1800"))
    backoff = float(os.environ.get("AGENT_ENGINE_TRANSIENT_BACKOFF_SECONDS", "60"))
    if attempts < 0 or max_wait < 0 or backoff < 0:
        raise ValueError("provider retry settings must be non-negative")
    return attempts, max_wait, backoff

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
    upstream: tuple[str, ...] = ()              # earlier-phase gates (no Phase 4 owner) that must be approved first
    request: str = ""


STAGES: tuple[Stage, ...] = (
    Stage(
        "task-breakdown", "P4-G1",
        ("phase4/stories.json", "prd.md", "architecture.md", f"gates/G3A{APPROVED_SUFFIX}", f"gates/G3B{APPROVED_SUFFIX}"),
        ("phase4/history.json", "designs/designs.md", "api/openapi.yaml", "api/openapi.yml", "api/openapi.json"),
        ("project_name", "code_repos", "infra_repo", "definition_of_done", "story_point_scale",
         "hours_per_story_point", "max_story_points_per_story", "deadlines"),
        upstream=("G3A", "G3B"),
        request="Break the approved stories down into tasks.",
    ),
    Stage(
        "infra-pipeline", "P4-G4", ("architecture.md",), (),
        ("project_name", "tracker", "code_repos", "infra_repo"),
        request="Set up dev, qa, stg and prod.",
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
    if stage.agent == "task-breakdown" and "phase4/history.json" in digests:
        # Only resolved tickets matter to Task Breakdown; closed sprints are Sprint Planning's velocity.
        from agent_engine.phase4.task_breakdown import history_tickets_digest
        digests["phase4/history.json"] = history_tickets_digest((root / "phase4/history.json").read_text(encoding="utf-8"))
    project = root / PROJECT_FILE
    if project.is_file():
        data = json.loads(project.read_text(encoding="utf-8"))
        from agent_engine.phase4.settings import project_overrides
        data = project_overrides(data)
        if stage.project_keys is not None:
            data = {k: data.get(k) for k in stage.project_keys}
        digests[PROJECT_FILE] = _digest_json(data)
    if stage.agent == "work-allocation":
        digests["param:sprint"] = str(sprint)
        manifest = root / "infra/manifest.json"
        if (root / f"gates/P4-G4{APPROVED_SUFFIX}").is_file() and manifest.is_file():  # CI-ready repos let AI take tasks
            digests["infra/manifest.json"] = file_digest(manifest)
    if stage.agent == "infra-pipeline" and project.is_file():
        digests[PROJECT_FILE] = _digest_json(project_overrides(json.loads(project.read_text(encoding="utf-8"))))
        from agent_engine.phase4.infra import catalog_dir
        catalog = catalog_dir()
        for p in sorted(catalog.rglob("*")):
            if p.is_file():
                digests["catalog:" + p.relative_to(catalog).as_posix()] = file_digest(p)
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
        for event_index, line in enumerate(history.read_text(encoding="utf-8").splitlines()):
            if line.strip():
                record = json.loads(line)
                if record.get("gate") == gate.name:
                    last = {**record, "_event_index": event_index}
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


def record_parallel_results(root: Path, results: dict, sprint: int = 1, state: dict | None = None) -> None:
    state = load_state(root) if state is None else state
    for agent, result in results.items():
        if agent not in STAGE_BY_AGENT:
            raise ValueError("unknown recovered stage")
        state[agent] = {"inputs": input_digests(STAGE_BY_AGENT[agent], root, sprint),
                        "status": result["status"], "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    save_state(root, state)


@dataclass
class Step:
    stage: Stage
    action: str      # run | gate_pending | done | blocked_input | waiting_gate | escalate
    why: str
    request: str = ""
    gate_status: str = ""
    resume_action: str = ""


def assess(project: str, sprint: int = 1, gates: dict[str, Gate] | None = None,
           verified_test_approval: bool = False, resume: bool | None = None) -> list[Step]:
    """The decision table: one Step per agent, from the current files and gate decisions (no side effects).

    Without `resume` a stage is reused only as a pure cache: its last recorded run succeeded and every input it read
    is byte-for-byte unchanged. Saved recovery state never decides what runs."""
    resume = _RESUME if resume is None else resume
    root, gates = _root(project), gates if gates is not None else load_gates()
    state = load_state(root)
    steps = []
    for stage in STAGES:
        gate = gates[stage.gate]
        # PDLC: Phase 4 starts only when the design (G3A) and architecture (G3B) gates are approved by a human.
        upstream = []
        for name in stage.upstream:
            if name not in gates:
                upstream.append(f"gates.toml has no [{name}] gate")
                continue
            up_status, _ = gate_state(root, gates[name])
            if up_status != "approved":
                upstream.append(f"{name} is {up_status} ({gates[name].description}); a human approves it with "
                                f"`agent-engine gate {name} --project-name {project} --decision approved ...`")
        if upstream:
            steps.append(Step(stage, "blocked_input", "earlier-phase gate not approved: " + "; ".join(upstream)))
            continue
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
        if verified_test_approval and status == "approved":
            from agent_engine.phase4.approval_policy import automated, test_publication_allowed
            if automated(record) and not test_publication_allowed(project, stage.gate, record):
                status = "pending"  # renew old test approvals only after current automated review
        request = stage.request.format(sprint=sprint)
        if resume and status not in ("changes_requested", "rejected", "approved"):
            from agent_engine.agent import load_pack
            pack = load_pack(stage.agent)
            action, retained = recovery.next_action(root, pack)
            # Allocation's selected sprint is part of its request contract.
            same_parameter = stage.agent != "work-allocation" or not retained or retained["request"] == request
            if retained and same_parameter:
                if action == "complete":
                    steps.append(Step(stage, "gate_pending", "retained review is complete; awaiting gate",
                                      retained["request"], status, "complete"))
                    continue
                if action in ("verify", "repair", "restore_repair"):
                    steps.append(Step(stage, "run", f"resume retained {action}; generation is saved",
                                      retained["request"], status))
                    continue
                if action in ("wait", "conflict"):
                    steps.append(Step(stage, "escalate", "retained output needs a decision: " +
                                      "; ".join(retained.get("gaps", [])), gate_status=status))
                    continue
        outputs_exist = all((root / f).is_file() for f in _outputs(stage))
        if not outputs_exist:
            steps.append(Step(stage, "run", "no output yet", request, status))
            continue
        entry = state.get(stage.agent)
        recorded = (entry or {}).get("inputs")
        now = input_digests(stage, root, sprint)
        changed = sorted(k for k in now if recorded is not None and recorded.get(k) != now[k])
        changed += sorted(k for k in (recorded or {}) if k not in now)
        feedback = status == "changes_requested"
        if not resume and not feedback and status != "rejected":
            # Fresh by default: outputs are reused only as a cache of a successful run on identical inputs.
            if entry is None:
                steps.append(Step(stage, "run", "no recorded run for the current inputs; running fresh", request, status))
                continue
            if entry.get("status") not in SUCCESS + ("adopted",) and not changed and status != "approved":
                steps.append(Step(stage, "run", f"last run ended {entry.get('status')!r}; running fresh",
                                  request, status))
                continue
        if feedback or changed:
            parts, why = [], []
            if feedback:
                comment = record.get("comment") or "(no comment given)"
                parts.append(f"Gate {gate.name} was reviewed by {record.get('approver', {}).get('name', 'a reviewer')} "
                             f"(decision event {record.get('_event_index', -1)}, {record.get('decided_at', '')}) "
                             f"and changes were requested: {comment}")
                why.append(f"{gate.name} asked for changes")
            if changed:
                parts.append("These inputs changed since your last run: " + ", ".join(changed)
                             + ". Update your output to match them and change only what needs changing.")
                why.append("inputs changed: " + ", ".join(changed))
            if feedback and resume:
                from agent_engine.agent import load_pack
                action, retained = recovery.next_action(root, load_pack(stage.agent))
                if retained and retained.get("request", "").startswith(parts[0]):
                    if action == "complete":
                        steps.append(Step(stage, "gate_pending", "reviewed response retained; renew the gate decision",
                                          retained["request"], status, "complete"))
                        continue
                    if action in ("verify", "repair", "restore_repair"):
                        steps.append(Step(stage, "run", f"resume retained {action}; generation is saved",
                                          retained["request"], status))
                        continue
                    if action in ("wait", "conflict"):
                        steps.append(Step(stage, "escalate", "retained response needs attention: " +
                                          "; ".join(retained.get("gaps", [])), gate_status=status))
                        continue
            steps.append(Step(stage, "run", "; ".join(why), "\n\n".join(parts), status))
        elif status == "rejected":
            back = (" Per the PDLC a rejected task breakdown goes back to design: revise and re-approve "
                    + "/".join(stage.upstream) + ", then Task Breakdown runs again.") if stage.upstream else ""
            steps.append(Step(stage, "escalate", f"{gate.name} was rejected; a human has to decide.{back}",
                              gate_status=status))
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


def run_agent(agent: str, request: str, project: str, *, outputs_dir: Path | None = None,
              logs_dir: Path | None = None) -> dict:
    """`agent-engine run` as a child process, output shown live.
    Returns {status, exit_code, rate_limited, gaps, invocation_id, report_problem}."""
    invocation_id = perf.new_id(24)
    cmd = [sys.executable, "-m", "agent_engine.cli", "run", request, "--agent", agent, "--project-name", project]
    if _RESUME:   # saved recovery state is used only when explicitly requested
        cmd.append("--resume")
    with perf.span("child", agent, agent=agent, invocation_id=invocation_id) as sp:
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", perf.ENV_INVOCATION: invocation_id, **perf.child_env(sp.id)}
        if outputs_dir is not None:
            env["AGENT_ENGINE_OUTPUTS_DIR"] = str(outputs_dir.resolve())
        if logs_dir is not None:
            env["AGENT_ENGINE_LOGS_DIR"] = str(logs_dir.resolve())
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
            child_root = outputs_dir / project if outputs_dir is not None else _root(project)
            status, gaps, problem = read_child_report(child_root / "report.json", agent, invocation_id, code)
        text = "".join(tail)
        rate_limited = any(m in text for m in RATE_LIMIT_MARKERS)
        reset = _RESET_RE.search(text)
        transient = status not in SUCCESS and not rate_limited and any(m in text for m in TRANSIENT_MARKERS)
        sp.set(exit_code=code, report_status=status, report_problem=problem, first_output_s=first_output,
               rate_limited=rate_limited, transient=transient)
        if status not in SUCCESS:
            sp.set_status("failed", problem or f"stage ended {status}", "stage_outcome")
    return {
        "status": status, "exit_code": code, "gaps": gaps, "rate_limited": rate_limited,
        "retry_after": int(reset.group(1)) if reset else None, "transient": transient,
        "invocation_id": invocation_id, "report_problem": problem,
    }


def _provider_retry(result: dict, agent: str, attempts: dict[str, int], out: Callable[[str], None]) -> bool | None:
    """None: not a provider problem. True: waited, run the stage again. False: retries exhausted (reason printed)."""
    if not (result.get("rate_limited") or result.get("transient")):
        return None
    limit, max_wait, backoff = _retry_limits()
    attempts[agent] = attempts.get(agent, 0) + 1
    kind = "rate limit" if result.get("rate_limited") else "transient provider error"
    wait = result.get("retry_after") if result.get("rate_limited") else backoff * 2 ** (attempts[agent] - 1)
    if wait is None:
        wait = backoff
    if attempts[agent] > limit or wait > max_wait:
        why = (f"{attempts[agent] - 1} retries used" if attempts[agent] > limit
               else f"reset in {int(wait)}s exceeds AGENT_ENGINE_RATE_LIMIT_MAX_WAIT_SECONDS={int(max_wait)}")
        out(f"\nSTOP: {agent} hit a {kind} ({why}). Nothing was merged from the failed attempt; run the same command "
            "again later (it starts fresh), or raise the limits.")
        return False
    out(f"\n>>> {agent} hit a {kind}; waiting {int(wait)}s, then running it again (attempt {attempts[agent] + 1})")
    perf.event("provider_retry", agent, problem=kind, wait_s=wait, attempt=attempts[agent])
    _sleep(wait)
    return True


def _approve(root: Path, step: Step, gates: dict[str, Gate], status: str, verified_test_approval: bool = False) -> None:
    from agent_engine.phase4.approval_policy import TEST_ORIGIN
    source = "PHASE4_AUTO_APPROVE_FOR_TESTING" if verified_test_approval else "--test-approve"
    record_decision(
        root, gates[step.stage.gate], "approved",
        {"name": "Orchestrator (automated test approval)", "role": "NOT a human sign-off",
         **({"automation": TEST_ORIGIN} if verified_test_approval else {})},
        {"name": f"{step.stage.agent} agent"},
        f"Automated test approval by the orchestrator ({source}), not a human review. Validator: {status}.",
    )


def _show_gate_notes(project: str, step: Step, out: Callable[[str], None]) -> None:
    """Advisory reviewer findings and open questions travel with the gate; they never block."""
    from agent_engine.cli import review_notes
    from agent_engine.phase4 import attention
    notes = review_notes(project, step.stage.agent) or {}
    items = attention.open_items(project, step.stage.agent)
    if not notes.get("findings") and not items:
        return
    out(f"\n--- {step.stage.gate} notes for the approver ({step.stage.agent}); these do not block ---")
    for f in (notes.get("findings") or [])[:20]:
        out(f"  review: {f}")
    for line in items[:30]:
        out(f"  {line}")


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
    runner: Runner = run_agent, out: Callable[[str], None] = print, parallel_independent: bool = False,
    verified_test_approval: bool = False, resume: bool = False,
) -> int:
    global _RESUME
    _RESUME = resume
    try:
        return _orchestrate_once(project, sprint, test_approve, publish, plan_only, runner, out, parallel_independent,
                                 verified_test_approval)
    finally:
        _RESUME = False   # never leaks into a later assessment or run


def _orchestrate_once(project: str, sprint: int, test_approve: bool, publish: bool, plan_only: bool, runner: Runner,
                      out: Callable[[str], None], parallel_independent: bool, verified_test_approval: bool) -> int:
    if _RESUME:
        out(">>> --resume: saved recovery state (interrupted repairs, reviews, parallel merges) will be reused")
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
            code = _orchestrate(project, sprint, test_approve, publish, plan_only, runner, out, parallel_independent,
                                verified_test_approval)
        sp.set(exit_code=code, outcome={DONE: "done", FAILED: "failed", WAITING: "waiting"}.get(code, str(code)))
        if code == FAILED:
            sp.set_status("failed", category="pipeline_outcome")
        return code


def _orchestrate(project: str, sprint: int, test_approve: bool, publish: bool, plan_only: bool, runner: Runner,
                 out: Callable[[str], None], parallel_independent: bool = False,
                 verified_test_approval: bool = False) -> int:
    with perf.span("orchestrator", "preflight"):
        root, gates = _root(project), load_gates()
        if not (root / PROJECT_FILE).is_file():
            out(f"ERROR: {root / PROJECT_FILE} is missing. Add the project inputs first (phase4 init, or copy your own).")
            return FAILED
        state = load_state(root)
        _observe_approvals(root, gates)
        if not plan_only and os.environ.get("PHASE4_IMPORT_STORIES", "true").strip().lower() != "false":
            # Approved stories live in the tracker; refresh the snapshot (read-only, rewritten only when changed).
            from agent_engine.phase4.settings import project_overrides
            try:
                raw = json.loads((root / PROJECT_FILE).read_text(encoding="utf-8"))
                if (project_overrides(raw).get("tracker") or {}).get("kind") == "jira":
                    from agent_engine.phase4.story_import import import_history, import_stories
                    summary = import_stories(project)
                    out(f">>> approved stories: {summary['stories']} from Jira"
                        f"{' (updated)' if summary['changed'] else ' (unchanged)'}"
                        + (f"; excluded {len(summary['excluded'])}" if summary["excluded"] else ""))
                    velocity = import_history(project)
                    if velocity.get("history") == "updated":
                        out(f">>> velocity history: {velocity['closed_sprints']} closed sprints from Jira")
            except Exception as exc:  # noqa: BLE001  (network, auth, schema: stop before any generation)
                out(f"ERROR: importing approved stories failed: {exc}")
                return FAILED
        # Every input is checked before any model call; all problems are reported at once.
        from agent_engine.phase4.preflight import check_inputs
        problems, cautions = check_inputs(project)
        for c in cautions:
            out(f"WARNING (input): {c}")
        if problems:
            out(f"\nSTOP: {len(problems)} input problem(s) must be fixed before any agent runs (no model was called):")
            for p in problems:
                out(f"  - {p}")
            if not plan_only:
                return FAILED
        if not plan_only:
            from agent_engine.phase4.parallel_stages import replay_pending, acknowledge, pending
            if _RESUME:
                try:
                    restored = replay_pending(root, runner=runner)
                except Exception as exc:
                    out(f"STOP: retained parallel merge needs recovery: {exc}; child outputs remain saved.")
                    return FAILED
                if restored:
                    record_parallel_results(root, restored, sprint, state)
                    acknowledge(root)
                    out(">>> recovered retained parallel results without rerunning stage writers")
            elif pending(root):
                # A fresh run never replays an unfinished merge; its evidence stays under logs/parallel.
                acknowledge(root)
                out(">>> an unfinished parallel session was left by an earlier run; it is not replayed (fresh run). "
                    "Use --resume to recover it instead.")
    ran: list[str] = []
    failed_attempts: set[str] = set()
    provider_attempts: dict[str, int] = {}
    parallel_ok = parallel_independent
    for _ in range(MAX_STEPS):
        with perf.span("orchestrator", "assess") as asp:
            steps = assess(project, sprint, gates, verified_test_approval=verified_test_approval)
            asp.set(actions={s.stage.agent: s.action for s in steps})
        # --resume only: existing outputs of a project run by hand are taken as up to date.
        for s in steps:
            if s.resume_action == "complete":
                state[s.stage.agent] = {"inputs": input_digests(s.stage, root, sprint), "status": "success",
                                       "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            elif _RESUME and s.action in ("done", "gate_pending") and s.stage.agent not in state:
                state[s.stage.agent] = {"inputs": input_digests(s.stage, root, sprint), "status": "adopted",
                                        "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        if not plan_only:
            save_state(root, state)
        out(format_table(steps))
        blocked = [s for s in steps if s.action in ("blocked_input", "escalate")]
        runnable = [s for s in steps if s.action == "run" and s.stage.agent not in failed_attempts]
        if plan_only:
            return DONE if all(s.action == "done" for s in steps) else WAITING
        if blocked and not runnable:
            for s in blocked:
                out(f"\nSTOP {s.stage.agent}: {s.why}")
            return FAILED if failed_attempts else WAITING
        if runnable:
            pair = [s for s in runnable if s.stage.agent in ("task-breakdown", "infra-pipeline")]
            # Only these two stages have verified independent inputs. Injected
            # runners keep the existing sequential contract unless tested directly.
            if parallel_ok and len(pair) == 2 and runner is run_agent:
                from agent_engine.phase4.parallel_stages import run_pair, acknowledge
                out("\n>>> running Task Breakdown and Infrastructure in isolated workspaces")
                try:
                    results = run_pair(root, pair, runner)
                except Exception as exc:
                    # All or nothing: a refused or rolled-back merge changed nothing in the project. Parallelism is
                    # only an optimisation, so the same two stages run again one after the other, fresh.
                    acknowledge(root)
                    parallel_ok = False
                    out(f">>> parallel merge did not complete ({exc}); nothing was merged. Running Task Breakdown "
                        "and Infrastructure one after the other instead (isolated evidence kept under logs/parallel).")
                    continue
                retry = [r for r in results.values() if r.get("rate_limited") or r.get("transient")]
                if retry:
                    agent = next(a for a, r in results.items() if r in retry)
                    if not _provider_retry(retry[0], agent, provider_attempts, out):
                        return FAILED
                    from agent_engine.phase4.parallel_stages import acknowledge as _ack
                    _ack(root)
                    continue
                for item in pair:
                    result = results[item.stage.agent]
                    state[item.stage.agent] = {"inputs": input_digests(item.stage, root, sprint),
                                               "status": result["status"],
                                               "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
                    ran.append(item.stage.agent)
                save_state(root, state)
                from agent_engine.phase4.parallel_stages import acknowledge
                acknowledge(root)
                failed = {name: r for name, r in results.items() if r["status"] not in SUCCESS}
                if failed:
                    out("STOP: parallel stages need review: " + json.dumps(failed))
                    failed_attempts.update(failed)
                continue
            step = runnable[0]
            out(f"\n>>> running {step.stage.agent}: {step.why}\n")
            digests = input_digests(step.stage, root, sprint)
            result = runner(step.stage.agent, step.request, project)
            ran.append(step.stage.agent)
            retried = _provider_retry(result, step.stage.agent, provider_attempts, out)
            if retried is True:
                continue        # the next assessment runs the stage again, fresh
            if retried is False:
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
                failed_attempts.add(step.stage.agent)
                continue
            state[step.stage.agent] = {"inputs": digests, "status": "success",
                                       "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            save_state(root, state)
            continue
        pending = [s for s in steps if s.action == "gate_pending"]
        if pending:
            approvable = [s for s in pending if state.get(s.stage.agent, {}).get("status") in ("success", "adopted")]
            if test_approve and verified_test_approval:
                from agent_engine.agent import load_pack
                from agent_engine.phase4.approval_policy import current_review
                verified = []
                prepared = False
                for s in approvable:
                    if current_review(project, s.stage.gate):
                        verified.append(s)
                    elif not recovery.path(root, s.stage.agent).exists():
                        # Legacy files are reviewed in place, never approved merely because they exist.
                        with project_lock(root):
                            recovery.save(root, load_pack(s.stage.agent), s.request or s.stage.request.format(sprint=sprint),
                                          perf.new_id(), "review_pending")
                        prepared = True
                approvable = verified
                if prepared and not verified:
                    continue
            for s in pending:
                _show_gate_notes(project, s, out)
            if test_approve and approvable:
                for s in approvable:
                    _approve(root, s, gates, state[s.stage.agent]["status"], verified_test_approval)
                    perf.event("gate_decision", s.stage.gate, decision="approved", automated=True,
                               decided_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
                    out(f">>> TEST-approved {s.stage.gate} (not a human sign-off)")
                continue
            if failed_attempts:
                return FAILED
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
            return FAILED if failed_attempts else WAITING
        if failed_attempts:
            return FAILED
        break  # every stage is done
    else:
        out(f"STOP: no end after {MAX_STEPS} steps; check the project folder.")
        return FAILED

    final_status, final_record = gate_state(root, gates["G4"])
    if final_status != "approved":
        if test_approve:
            record_decision(root, gates["G4"], "approved",
                            {"name": "Orchestrator test", "role": "NOT a human sign-off", "automation": "phase4-env-test-mode"},
                            {"name": "Phase 4 agents"})
            out(">>> TEST-approved final G4 (not a human sign-off)")
        else:
            if final_status == "rejected":
                out("Final G4 rejected: return to design gates G3A/G3B before replanning.")
            elif final_status == "changes_requested":
                out("Final G4 changes requested: request changes at P4-G1 for plan issues or P4-G4 for environment issues, then rerun.")
            out('WAITING for final G4. Record agent-engine gate G4 --decision approved with the human approver and submitted-by, then rerun.')
            return WAITING
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
