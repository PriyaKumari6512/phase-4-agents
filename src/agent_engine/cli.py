"""CLI entrypoint:
  uv run agent-engine run "<request>" --agent PACK --project-name NAME
  uv run agent-engine add-inputs FILE... --project-name NAME [--round N]
  uv run agent-engine gate GATE --project-name NAME --decision D --approver NAME --submitted-by NAME
  uv run agent-engine list
  uv run agent-engine phase4 {init,publish,mine-profiles,schemas} ...   (phase4/cli.py, no model calls)

`add-inputs` copies client files into outputs/<project>/inputs/round-N/ and
converts the ones agents can't read (inputs.py). `gate` records a human
approval decision (gates.py) until the UI's API does it.

`run` appends the request to outputs/<project>/requests.md, runs the pack,
and — when the pack names a `verifier` — hands its output to that judge pack
and the judge's gaps back to the pack, up to `max_fix_loops` fix passes.
A pack's `model` may be a list (["fast", "strong"]): each pass runs on the
current entry, and a failed verdict or a model error moves to the next one.
Plain control flow: the judge never calls the agent itself. Every run ends
with outputs/<project>/report.json.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.callbacks import UsageMetadataCallbackHandler

from agent_engine import perf
from agent_engine.agent import AgentPack, Verdict, available_packs, build_agent, close_agent, load_pack, model_spec
from agent_engine.config import (
    APP_LOG_FILENAME,
    DEEPAGENT_LOG_FILENAME,
    LOGS_DIR,
    OUTPUTS_DIR,
    OUTPUTS_VIRTUAL_PREFIX,
    REPORT_FILENAME,
    REQUESTS_FILENAME,
    RUNS_DIRNAME,
    TRANSCRIPT_LOGGER_NAME,
)
from agent_engine.gates import DECISIONS, load_gates, record_decision, stale_approvals
from agent_engine.history import fingerprint, save_run
from agent_engine.inputs import add_inputs
from agent_engine.logging_setup import (
    attach_job_log_handler,
    configure_logging,
    current_job_log_path,
    detach_job_log_handler,
    new_job_id,
    notify_job_log_path,
)
from agent_engine.observability import build_langfuse_handler, flush_langfuse
from agent_engine.runtime import atomic_json, project_lock, project_scope, active_inputs, managed_outputs
from agent_engine.phase4 import cli as phase4_cli

logger = logging.getLogger(__name__)
transcript_logger = logging.getLogger(TRANSCRIPT_LOGGER_NAME)

_PROJECT_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class InvalidVerdictError(RuntimeError):
    pass


def _invalid_verdict_error(error: BaseException) -> bool:
    """Only retry response-format failures, not arbitrary execution failures."""
    seen = set()
    for _ in range(8):
        if error is None or id(error) in seen:
            break
        seen.add(id(error))
        if isinstance(error, (InvalidVerdictError, json.JSONDecodeError)) or type(error).__name__ in {
            "StructuredOutputValidationError", "MultipleStructuredOutputsError"}:
            return True
        error = error.__cause__ or error.__context__
    return False


def _text(content: object) -> str:
    """Some providers return message content as typed blocks; keep the text."""
    if isinstance(content, list):
        return "\n".join(
            b if isinstance(b, str) else b.get("text", "")
            for b in content
            if isinstance(b, str) or b.get("type") in ("text", "output_text")
        )
    return str(content)


async def _stream(agent, message: str, callbacks: list, run_name: str) -> dict | None:
    """One agent pass, logging every new message to the transcript."""
    final_state, seen = None, 0
    async for state in agent.astream(
        {"messages": [{"role": "user", "content": message}]},
        stream_mode="values",
        config={"callbacks": callbacks, "run_name": run_name},
    ):
        final_state = state
        messages = state.get("messages", [])
        for msg in messages[seen:]:
            calls = "; ".join(f"{c['name']}({c['args']})" for c in getattr(msg, "tool_calls", None) or [])
            content = perf.redact(_text(msg.content))
            limit = max(1000, int(os.environ.get("AGENT_ENGINE_TRANSCRIPT_MAX_CHARS", "20000")))
            if len(content) > limit:
                content = content[:limit] + f"\n[transcript truncated; {len(content)} characters, full generated artifacts remain on disk]"
            transcript_logger.info("[%s] %s%s", getattr(msg, "type", "?"), perf.redact(f"tool_calls=[{calls[:limit]}] ") if calls else "", content)
        seen = len(messages)
    return final_state


def _record_request(project_name: str, request: str, requests_file: str = REQUESTS_FILENAME) -> int:
    """Appends this request to the project's request history (requests.md, or
    the pack's own `AgentPack.requests_file`); returns its number.
    """
    path = OUTPUTS_DIR / project_name / requests_file
    path.parent.mkdir(parents=True, exist_ok=True)
    previous = path.read_text(encoding="utf-8") if path.exists() else ""
    number = sum(line.startswith("## Request ") for line in previous.splitlines()) + 1
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with path.open("a", encoding="utf-8") as f:
        f.write(f"{chr(10) if previous else ''}## Request {number} ({stamp})\n\n{request.strip()}\n")
    return number


def _missing(project_name: str, files: list[str]) -> list[str]:
    return [f for f in files if not (OUTPUTS_DIR / project_name / f).is_file()]


def _producers(file: str) -> list[str]:
    """Packs whose [output] declares `file`, to tell the user what to run first."""
    names = []
    for name in available_packs():
        try:
            if file in load_pack(name).output_files:
                names.append(name)
        except ValueError:
            pass
    return names


def _io_lines(pack: AgentPack, project: str) -> str:
    lines = []
    if pack.input_files:
        lines.append("Read these inputs first: " + ", ".join(f"{project}{f}" for f in pack.input_files) + ".")
    if pack.output_files:
        lines.append("You must produce: " + ", ".join(f"{project}{f}" for f in pack.output_files) + ".")
    return ("\n\n" + "\n".join(lines)) if lines else ""


def _agent_message(pack: AgentPack, request: str, project_name: str, request_number: int) -> str:
    project = f"{OUTPUTS_VIRTUAL_PREFIX}{project_name}/"
    message = f"{request}\n\nWrite your output under {project}." + _io_lines(pack, project)
    if request_number > 1:
        message += (
            f"\n\nThis is request {request_number} for this project. Every request so far, oldest first, is in "
            f"{project}{pack.requests_file}: the earlier ones still apply unless this one changes them. Your "
            f"previous output is already under {project}; read it and change only what this request needs."
        )
    return message


def _verifier_message(pack: AgentPack, project_name: str) -> str:
    project = f"{OUTPUTS_VIRTUAL_PREFIX}{project_name}/"
    return (
        f"The {pack.name} agent's output is under {project}. Every request it was given for this project, "
        f"oldest first, is in {project}{pack.requests_file}; later requests override earlier ones where they "
        "conflict. Judge whether the output satisfies all of them."
        + (f" Its declared outputs: {', '.join(project + f for f in pack.output_files)}." if pack.output_files else "")
    )


def _fix_message(pack: AgentPack, project_name: str, gaps: list[str]) -> str:
    project = f"{OUTPUTS_VIRTUAL_PREFIX}{project_name}/"
    bullets = "\n".join(f"- {gap}" for gap in gaps) or "- (no specific gaps recorded)"
    return (
        f"Your output under {project} was reviewed by {pack.verifier}. Every request for this project is in "
        f"{project}{pack.requests_file}. Read your output, then fix these gaps without redoing work that is "
        f"already right:\n{bullets}"
    )


def verdict_status(verdict: Verdict) -> tuple[str, str | None]:
    """The run status a verdict supports, and why it differs from `status_so_far` when it does.

    A structured verdict can contradict itself (`satisfied=false` with `status_so_far="success"`). The
    validator's explicit `satisfied` flag is the judgement; a contradictory reply must never count as success.
    """
    if verdict.status_so_far == "success" and not verdict.satisfied:
        return "partial", "verdict said status_so_far=success but satisfied=false; treated as partial"
    return verdict.status_so_far, None


async def _run(request: str, agent_name: str, project_name: str, resume_verification: bool = False,
               resume: bool = False, review_existing: bool = False) -> int:
    if not _PROJECT_NAME_RE.fullmatch(project_name):
        raise ValueError("invalid project name")
    with project_scope(project_name), project_lock(OUTPUTS_DIR / project_name):
        if review_existing:
            return await _owned_run(request, agent_name, project_name, review_existing=True)
        if resume:
            return await _owned_run(request, agent_name, project_name, resume=True)
        if resume_verification:
            return await _owned_run(request, agent_name, project_name, resume_verification=True)
        return await _owned_run(request, agent_name, project_name)


async def _owned_run(request: str, agent_name: str, project_name: str, resume_verification: bool = False,
                     resume: bool = False, review_existing: bool = False) -> int:
    from agent_engine.stage_controls import StageBudget, active_stage_budget
    budget_token = None
    if agent_name in ("task-breakdown", "task-breakdown/validator"):
        budget_token = active_stage_budget.set(StageBudget.from_env())
    with perf.span("stage", agent_name, agent=agent_name, project=project_name,
                   invocation_id=os.environ.get(perf.ENV_INVOCATION)) as stage:
        try:
            options = {"resume": True} if resume else {}
            if review_existing:
                options["review_existing"] = True
            code = await _run_stage(request, agent_name, project_name, stage,
                                    resume_verification=resume_verification, **options)
        finally:
            if budget_token is not None:
                active_stage_budget.get().stop("Task Breakdown execution scope closed")
                active_stage_budget.reset(budget_token)
        stage.set(exit_code=code)
        if code:
            stage.set_status("failed", category="exit_code")
        return code


def _model_tiers() -> dict[str, str]:
    try:
        return {spec: tier for tier in ("fast", "strong") if (spec := model_spec(tier))}
    except Exception:  # noqa: BLE001  (no credentials: the run itself reports it)
        return {}


async def _run_stage(request: str, agent_name: str, project_name: str, stage, resume_verification: bool = False,
                     resume: bool = False, review_existing: bool = False) -> int:
    from agent_engine import verification_resume, recovery
    resumed_from = None
    recovery_action, recovery_record = "generate", None
    if review_existing:
        recovery_action, resumed_from = "verify", "explicit-current-artifact-review"
    if resume or resume_verification:
        pack = load_pack(agent_name)
        recovery_action, recovery_record = recovery.next_action(OUTPUTS_DIR / project_name, pack, request)
        if resume_verification and recovery_action == "conflict":
            print("ERROR: saved artifacts or recovery metadata changed; inspect them and use --review-existing for a fresh review")
            return 1
        if recovery_record is not None:
            resumed_from = recovery_record["job_id"]
            if recovery_action == "restore_repair":
                try:
                    recovery.restore_repair(OUTPUTS_DIR / project_name, pack, recovery_record)
                except (OSError, ValueError) as exc:
                    print(f"ERROR: retained repair could not be restored: {exc}")
                    return 1
                recovery_action = "repair"
    if resume_verification:
        try:
            if resumed_from is None:
                resumed_from = verification_resume.validate(OUTPUTS_DIR / project_name, agent_name, request)
            recovery_action = "verify"
        except (ValueError, OSError) as exc:
            print(f"ERROR: {exc}")
            return 1
    if recovery_action in ("wait", "conflict"):
        print("WAITING: saved work needs a decision or changed inputs; generation was retained.")
        for gap in recovery_record.get("gaps", []):
            print(f"  - {gap}")
        return 1
    with perf.span("phase", "preflight") as pre:
        try:  # fail on a bad pack (or its verifier) before any model call
            pack = load_pack(agent_name)
            verifier = load_pack(pack.verifier) if pack.verifier else None
            if review_existing and verifier is None:
                raise ValueError("--review-existing requires a pack with an independent verifier")
            if verifier is not None and verifier.returns != "verdict":
                raise ValueError(f"verifier {pack.verifier!r} must declare returns = \"verdict\"")
        except ValueError as e:
            print(f"ERROR: {e}")
            pre.set_status("blocked", str(e), "invalid_pack")
            return 1

        # Declared inputs must exist before any model call (and before this request is recorded).
        missing = _missing(project_name, pack.input_files)
        if missing:
            pre.set_status("blocked", "missing inputs: " + ", ".join(missing), "missing_input")
            try:
                approval_files = {g.approval_file: g.name for g in load_gates().values()}
            except ValueError as e:
                print(f"ERROR: {e}")
                return 1
            for f in missing:
                if f in approval_files:
                    print(f"ERROR: {pack.name} can't run until gate {approval_files[f]} is approved (agent-engine gate {approval_files[f]} ...).")
                    continue
                producers = _producers(f)
                hint = f" Run --agent {' or --agent '.join(producers)} on this project first." if producers else ""
                print(f"ERROR: {pack.name} needs {OUTPUTS_DIR / project_name / f}, which doesn't exist yet.{hint}")
            return 1
        # A gate approval listed as an input only counts while the files it approved are unchanged.
        stale = stale_approvals(OUTPUTS_DIR / project_name, pack.input_files, load_gates())
        if stale:
            pre.set_status("blocked", "; ".join(stale), "stale_approval")
            for problem in stale:
                print(f"ERROR: {pack.name} can't run: {problem}. Get the gate approved again first.")
            return 1
        if pack.name in ("task-breakdown", "infra-pipeline", "sprint-planning", "work-allocation"):
            from agent_engine.phase4 import files as project_files
            from agent_engine.phase4.contracts import ProjectSettings
            try:
                project_files.read_json(project_name, project_files.PROJECT_SETTINGS, ProjectSettings)
                if pack.name == "work-allocation":
                    from agent_engine.phase4.allocation import _ctx
                    _ctx(project_name, 1)  # validate upstream feasibility before paying for a writer
            except ValueError as exc:
                print(f"ERROR: invalid Phase 4 inputs: {exc}")
                return 1

    job_id = new_job_id()
    stage.set(job_id=job_id)
    if perf.enabled():
        from agent_engine import perf_manifest

        names = [pack.name] + ([verifier.name] if verifier else [])
        under_pipeline = bool(os.environ.get(perf.ENV_PIPELINE))
        perf_manifest.write("invocation", os.environ.get(perf.ENV_INVOCATION) or job_id, project=project_name,
                            packs=names, light=under_pipeline,
                            extra={"job_id": job_id, "agent": pack.name, "under_orchestrator": under_pipeline})
    attach_job_log_handler(job_id)
    notify_job_log_path(f"{OUTPUTS_VIRTUAL_PREFIX}{project_name}/")
    with perf.span("fs", "record_request"):
        if resumed_from:
            history = OUTPUTS_DIR / project_name / pack.requests_file
            text = history.read_text(encoding="utf-8") if history.is_file() else ""
            request_number = sum(line.startswith("## Request ") for line in text.splitlines())
        else:
            request_number = _record_request(project_name, request, pack.requests_file)
    outputs_before = fingerprint(OUTPUTS_DIR / project_name)
    logger.info("run start job_id=%s agent=%s project=%s request=%d", job_id, pack.name, project_name, request_number)

    # One usage handler across every pass (agent, verifier, fixes) so tokens are counted for all of them.
    usage = UsageMetadataCallbackHandler()
    langfuse = build_langfuse_handler()
    callbacks = [usage, *([langfuse] if langfuse else [])]
    from agent_engine.stage_controls import active_stage_budget, StageBudgetCallback
    if (budget := active_stage_budget.get()) is not None:
        budget.callback_accounting = True
        callbacks.append(StageBudgetCallback(budget))
    tiers = _model_tiers() if perf.enabled() else {}
    started = time.perf_counter()
    report: dict = {
        "job_id": job_id, "agent": pack.name, "project": project_name, "request": request_number, "request_text": request,
    }
    if resumed_from:
        report["verification_resumed_from"] = resumed_from
        report["recovery_action"] = recovery_action
    # Stamped so the orchestrator can tell this run's report from an older one (orchestrator.run_agent).
    if os.environ.get(perf.ENV_INVOCATION):
        report["invocation_id"] = os.environ[perf.ENV_INVOCATION]
    exit_code = 0

    passes: list[dict] = []
    report["passes"] = passes
    # Where each pack is in its `model` escalation order (agent.AgentPack.models).
    level = {pack.name: 0, **({verifier.name: 0} if verifier else {})}
    pass_counts: dict[str, int] = {}
    generation_inputs = recovery.input_identity(OUTPUTS_DIR / project_name, pack) if pack.name in recovery.DIRECTORIES else None

    def checkpoint(phase: str, **kwargs):
        missing = _missing(project_name, pack.output_files)
        if missing and pass_counts.get("fix", 0):
            raise RuntimeError(f"{pack.name}'s declared output is missing after its fix passes: {', '.join(missing)}")
        if generation_inputs is not None and recovery.input_identity(OUTPUTS_DIR / project_name, pack) != generation_inputs:
            raise ValueError("source inputs changed during execution; artifacts retained but completion cannot be certified")
        return recovery.save(OUTPUTS_DIR / project_name, pack, request, job_id, phase, **kwargs)

    async def run_pass(p: AgentPack, kind: str, message: str) -> dict | None:
        """One pass of pack `p` on its current model; a model error moves it
        one step along its escalation order and retries, until the list runs out.
        """
        schema_retries = 0
        while True:
            tier = p.models[level[p.name]]
            entry = {"kind": kind, "agent": p.name, "model_tier": tier, "model": model_spec(tier)}
            passes.append(entry)
            pass_counts[kind] = pass_counts.get(kind, 0) + 1
            with perf.span("pass", f"{p.name}:{kind}", pass_kind=kind, agent=p.name, model_tier=tier,
                           model=entry["model"], attempt=pass_counts[kind], pass_index=len(passes)) as ps:
                pass_callbacks = callbacks
                handler = None
                if perf.enabled():
                    from agent_engine.perf_callbacks import PerfCallbackHandler

                    handler = PerfCallbackHandler(ps.id, tiers)
                    pass_callbacks = [*callbacks, handler]
                built = None
                try:
                    protected = set(pack.input_files)
                    if pack.name in ("task-breakdown", "sprint-planning", "work-allocation", "infra-pipeline"):
                        protected.update(("phase4/history.json", "phase4/skill-profiles.json", "phase4/agent-outcomes.json", "phase4/ci-readiness.json", "phase4/committed-work.json"))
                        managed_outputs.set(frozenset(("backlog/backlog.json", "backlog/features.json", "backlog/enrichments.json",
                            "sprint/sprint-plan.json", "sprint/solver-diagnostics.json", "allocation/assignments.json", "infra/intent.json", "infra/manifest.json", "infra/checks.json")))
                    active_inputs.set(frozenset(protected))
                    built = build_agent(p, level[p.name])
                    with perf.span("graph", f"{p.name}-{kind}") as gs:
                        deadline_s = float(os.environ.get("AGENT_ENGINE_PASS_TIMEOUT_SECONDS", "1800"))
                        budget = active_stage_budget.get()
                        if budget is not None:
                            deadline_s = min(deadline_s, budget.remaining())
                        try:
                            state = await asyncio.wait_for(_stream(built, message, pass_callbacks, f"{p.name}-{kind}"), timeout=deadline_s)
                        except asyncio.TimeoutError as exc:
                            if budget is not None:
                                from agent_engine.stage_controls import StageBudgetExceeded
                                budget.stop("Task Breakdown stage or pass deadline exhausted")
                                raise StageBudgetExceeded(budget.stopped) from exc
                            raise
                        gs.set(messages=len(state.get("messages", [])) if isinstance(state, dict) else None)
                    if kind == "verify" and not isinstance((state or {}).get("structured_response"), Verdict):
                        last = state.get("messages", [])[-1] if state and state.get("messages") else None
                        metadata = getattr(last, "response_metadata", {}) or {}
                        entry["invalid_verdict"] = {"response_chars": len(_text(last.content)) if last is not None else 0,
                                                     "finish_reason": metadata.get("stop_reason") or metadata.get("finish_reason")}
                        raise InvalidVerdictError("verifier returned no valid structured Verdict")
                    entry["ok"] = True
                    return state
                except Exception as e:
                    entry.update(ok=False, error=str(e))
                    from agent_engine.stage_controls import StageBudgetExceeded
                    if isinstance(e, StageBudgetExceeded):
                        raise
                    if handler is not None:
                        ps.set(open_model_or_tool_runs=handler.open_runs())
                    if kind == "verify" and _invalid_verdict_error(e) and schema_retries < 1:
                        schema_retries += 1
                        ps.set_status("error", str(e), "structured_output")
                        message += "\nThe previous review response was empty, malformed or schema-invalid. Recheck the retained artifacts; return exactly one valid, concise Verdict. Do not rewrite artifacts or echo file bodies. Report partial if review is incomplete."
                        continue
                    if level[p.name] + 1 >= len(p.models):
                        budget = active_stage_budget.get()
                        if budget is not None:
                            budget.stop("Task Breakdown pass failed; further background mutations refused")
                        raise
                    ps.set_status("error", str(e), perf.classify_error(e))
                    level[p.name] += 1
                    logger.warning("%s %s pass failed on %s, retrying on %s: %s", p.name, kind, tier, p.models[level[p.name]], e)
                    print(f"\n[{p.name}: {tier} model failed ({e}); retrying on {p.models[level[p.name]]}]")

                finally:
                    if built is not None:
                        await close_agent(built)

    try:
        verification_resume.checkpoint_path(OUTPUTS_DIR / project_name, agent_name).unlink(missing_ok=True)
        state = None if resumed_from else await run_pass(pack, "write", _agent_message(pack, request, project_name, request_number))
        report["agent_reply"] = _text(state["messages"][-1].content) if state and state.get("messages") else None
        print(report["agent_reply"] or "(agent produced no reply)")
        # A declared output that wasn't written is a failed run, not something to pay a verifier for.
        missing = _missing(project_name, pack.output_files)
        if missing:
            raise RuntimeError(f"{pack.name} did not create its declared output: {', '.join(missing)}")

        if recovery_record is None:
            checkpoint("generated")
        if recovery_action == "repair":
            checkpoint("repair_running", gaps=recovery_record.get("gaps"))
            await run_pass(pack, "fix", _fix_message(pack, project_name, recovery_record.get("gaps", [])))
            checkpoint("generated")

        if verifier is None:
            report.update(status="done", verified=False)
        else:
            for attempt in range(1, pack.max_fix_loops + 2):
                report["loops"] = attempt
                try:
                    deterministic, human_needed = _deterministic_gaps(pack.name, project_name)
                    if deterministic:
                        verdict = Verdict(satisfied=False, status_so_far="partial", gaps=deterministic,
                                          summary="Deterministic checks found blocking issues before semantic review.")
                    elif recovery_action == "complete" and attempt == 1:
                        verdict = Verdict(satisfied=True, status_so_far="success", gaps=[],
                                          summary="Reused completed review: source, artifacts and evaluation identity are unchanged.")
                        report["review_reused"] = True
                    else:
                        reviewed_snapshot = checkpoint("checked")["snapshot"]
                        message = (_verifier_message(pack, project_name) +
                                   f"\nOriginal request for this work: {request}\nIf an imported run has no history file, use this original request and the authoritative inputs.")
                        state = await run_pass(verifier, "verify", message)
                        if recovery.snapshot(OUTPUTS_DIR / project_name, pack) != reviewed_snapshot:
                            raise ValueError("source or artifact changed during semantic review; verdict was not accepted")
                        verdict = state.get("structured_response") if state else None
                    if not isinstance(verdict, Verdict):
                        raise InvalidVerdictError("no valid structured verdict returned; response was empty or unparsable")
                    if not deterministic and not report.get("review_reused"):
                        passes[-1]["satisfied"] = verdict.satisfied
                except Exception as e:
                    logger.exception("verifier %s failed on attempt %d", verifier.name, attempt)
                    verdict = Verdict(
                        satisfied=False, status_so_far="partial", gaps=[f"verifier failed: {e}"],
                        summary="The verifier could not complete this attempt; the output was not judged.",
                    )
                    report.update(status="partial", verified=False, verdict=verdict.model_dump())
                    if not _missing(project_name, pack.output_files):
                        checkpoint("review_pending",
                                      gaps=verdict.gaps)
                        verification_resume.save(OUTPUTS_DIR / project_name, agent_name, request, job_id)
                    perf.event("verdict", verifier.name, attempt=attempt, verifier_failed=True,
                               error=perf.error_summary(e))
                    print(f"\n=== {verifier.name} failed (attempt {attempt}): {e} ===")
                    break
                status, inconsistency = verdict_status(verdict)
                report.update(status=status, verified=True, verdict=verdict.model_dump())
                if inconsistency:
                    report["verdict_inconsistent"] = inconsistency
                    logger.warning("verifier %s attempt %d: %s", verifier.name, attempt, inconsistency)
                    print(f"\n[{verifier.name}: {inconsistency}]")
                perf.event("verdict", verifier.name, attempt=attempt, satisfied=verdict.satisfied,
                           status_so_far=verdict.status_so_far, effective_status=status, gaps=len(verdict.gaps),
                           inconsistent=bool(inconsistency))
                print(f"\n=== {verifier.name} verdict (attempt {attempt}): {verdict.status_so_far} ===\n{verdict.summary}")
                for gap in verdict.gaps:
                    print(f"  - {gap}")
                if verdict.satisfied or attempt > pack.max_fix_loops or human_needed:
                    checkpoint(
                                  "verified" if verdict.satisfied and status in ("success", "done") else "awaiting_decision",
                                  gaps=verdict.gaps, human=human_needed)
                    break
                # A failed verdict moves the fix pass one step up the escalation order.
                if level[pack.name] + 1 < len(pack.models):
                    level[pack.name] += 1
                    print(f"\n[{pack.name}: escalating fix pass to the {pack.models[level[pack.name]]} model]")
                checkpoint("repair_pending", gaps=verdict.gaps)
                checkpoint("repair_running", gaps=verdict.gaps)
                await run_pass(pack, "fix", _fix_message(pack, project_name, verdict.gaps))
                checkpoint("generated")
            # Fix passes can delete or move files: success also needs every declared output to still exist.
            missing = _missing(project_name, pack.output_files)
            if missing and report.get("status") in ("done", "success"):
                raise RuntimeError(f"{pack.name}'s declared output is missing after its fix passes: {', '.join(missing)}")
        exit_code = 0 if report["status"] in ("done", "success") else 1
        if verifier is None:
            checkpoint("verified")
    except Exception as e:
        logger.exception("run failed job_id=%s", job_id)
        from agent_engine.stage_controls import StageBudgetExceeded
        report.update(status="partial" if isinstance(e, StageBudgetExceeded) else "fail", error=str(e))
        print(f"\nERROR: run failed: {e}")
        exit_code = 1
    finally:
        from agent_engine.stage_controls import active_stage_budget
        if (budget := active_stage_budget.get()) is not None:
            report["stage_budget"] = budget.summary()
        report["elapsed_seconds"] = round(time.perf_counter() - started, 1)
        report["tokens"] = usage.usage_metadata
        report["finished_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        stage.set(status=report.get("status"), passes=len(passes),
                  writes=pass_counts.get("write", 0), verifies=pass_counts.get("verify", 0),
                  fixes=pass_counts.get("fix", 0))
        perf.event("usage_aggregate", pack.name, tokens=usage.usage_metadata,
                   note="UsageMetadataCallbackHandler totals for every pass of this stage (report.json 'tokens')")
        trace_host, job_log = None, current_job_log_path()
        report_path = OUTPUTS_DIR / project_name / REPORT_FILENAME
        try:
            save_run(OUTPUTS_DIR / project_name, job_id, outputs_before, report)
            with perf.span("fs", "write_report"):
                atomic_json(report_path, report)
        finally:
            try:
                with perf.span("diagnostics", "langfuse_flush"):
                    trace_host = flush_langfuse(langfuse)
            finally:
                detach_job_log_handler()

    print(f"\nStatus: {report['status']}  |  time: {report['elapsed_seconds']}s")
    for p in passes:
        print(f"Pass {p['kind']:6} {p['agent']:16} {p['model_tier']:6} {p['model']}{'' if p.get('ok') else '  FAILED'}")
    for model_name, u in report["tokens"].items():
        print(f"Tokens {model_name}: input={u.get('input_tokens', 0)} output={u.get('output_tokens', 0)} total={u.get('total_tokens', 0)}")
    print(f"Report: {report_path}")
    print(f"Run history: {OUTPUTS_DIR / project_name / RUNS_DIRNAME / job_id}")
    print(f"Job log: {job_log}  |  transcript: {LOGS_DIR / DEEPAGENT_LOG_FILENAME}  |  app log: {LOGS_DIR / APP_LOG_FILENAME}")
    if trace_host:
        print(f"Langfuse: {trace_host}")
    return exit_code


def _deterministic_gaps(agent: str, project: str) -> tuple[list[str], bool]:
    """A semantic reviewer is still required when the cheap checks pass."""
    from agent_engine.phase4 import backlog, sprint, allocation, infra, files
    checks = {"task-breakdown": lambda: backlog.validate_report(project, write=False),
              "sprint-planning": lambda: sprint.check(project), "work-allocation": lambda: allocation.check(project),
              "infra-pipeline": lambda: infra.check(project)}
    if agent not in checks:
        return [], False
    result = json.loads(checks[agent]())
    gaps = [x["message"] for x in result.get("blocking", [])] + result.get("problems", [])
    human = False
    if agent == "sprint-planning" and result.get("solver") == "INFEASIBLE":
        gaps.append("The sprint plan is infeasible. An approver must choose an option or change the inputs before execution.")
        human = True
    if agent == "infra-pipeline":
        manifest = files.read_json(project, files.INFRA_MANIFEST)
        human = manifest.get("validation_complete") is False
    return gaps, human


def _add_inputs(files: list[str], project_name: str, round_number: int | None) -> int:
    try:
        number, added = add_inputs(project_name, [Path(f) for f in files], round_number)
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1
    print(f"Round {number}: {added[0].path.parent if added else '(no files)'}")
    for a in added:
        status = "NOT READABLE: " + a.note if a.read_as is None else (a.note or "read directly")
        print(f"  {a.path.name:40} {status}")
    return 0


def _gate(name: str, project_name: str, decision: str, approver: dict, submitted_by: dict, comment: str) -> int:
    try:
        gates = load_gates()
        if name not in gates:
            raise ValueError(f"no gate {name!r} in gates.toml (defined: {', '.join(gates) or 'none'})")
        gate = gates[name]
        record = record_decision(OUTPUTS_DIR / project_name, gate, decision, approver, submitted_by, comment)
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1
    # Evidence for human-wait accounting: when the decision was recorded (no names or comments).
    perf.event("gate_decision", gate.name, project=project_name, decision=decision, decided_at=record["decided_at"],
               automated=False)
    print(f"{gate.name} {decision} by {approver['name']} at {record['decided_at']}")
    for f, digest in record["artifacts"].items():
        print(f"  {f:40} {digest[:19]}")
    if decision == "changes_requested":
        owners = sorted({p for f in gate.files for p in _producers(f)})
        for owner in owners:
            print(f'Next: uv run agent-engine run "<the requested changes>" --agent {owner} --project-name {project_name}')
    return 0


def main() -> None:
    # Windows consoles default to a codepage that can't print what models emit (arrows, em-dashes, ...).
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    configure_logging()

    parser = argparse.ArgumentParser(description="Run PDLC agents defined as agent packs (agents/<name>/).")
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run", help="Run one agent pack on a request, with its verifier if it has one.")
    run_parser.add_argument("request", help="The request: a requirement, or feedback on an earlier output.")
    run_parser.add_argument("--agent", required=True, help="Agent pack name (see `list`).")
    run_parser.add_argument("--project-name", required=True, help="Output folder under outputs/ (a-z, 0-9, -).")
    recovery_flags = run_parser.add_mutually_exclusive_group()
    recovery_flags.add_argument("--resume-verification", action="store_true",
                            help="Retry a failed verifier without regeneration; requires unchanged checkpoint and request.")
    recovery_flags.add_argument("--resume", action="store_true",
                            help="Resume retained generation/review/repair using its source and artifact hashes.")
    recovery_flags.add_argument("--review-existing", action="store_true",
                            help="Explicitly recheck current declared outputs, including manual edits, without initial generation.")
    inputs_parser = sub.add_parser("add-inputs", help="Add client files to a project's inputs/round-N/.")
    inputs_parser.add_argument("files", nargs="+", help="Files to add (PDF, images, Word, Excel, PowerPoint, email, text).")
    inputs_parser.add_argument("--project-name", required=True, help="Output folder under outputs/ (a-z, 0-9, -).")
    inputs_parser.add_argument("--round", type=int, help="Add to this round instead of starting a new one.")
    gate_parser = sub.add_parser("gate", help="Record a human gate decision (approve, request changes, reject).")
    gate_parser.add_argument("gate", help="Gate name from gates.toml, e.g. G1.")
    gate_parser.add_argument("--project-name", required=True, help="Output folder under outputs/ (a-z, 0-9, -).")
    gate_parser.add_argument("--decision", required=True, choices=DECISIONS)
    gate_parser.add_argument("--approver", required=True, help="Name of the person deciding.")
    gate_parser.add_argument("--approver-role", default="", help="Their role, e.g. 'Delivery Manager'.")
    gate_parser.add_argument("--submitted-by", required=True, help="Name of the person who submitted the work.")
    gate_parser.add_argument("--comment", default="", help="Reason, or the changes requested.")
    sub.add_parser("list", help="List the available agent packs.")
    sub.add_parser("pipeline", help="Run the complete pipeline using .env/config only; see docs/PIPELINE_JIRA.md.")
    phase4_cli.add_parser(sub)
    perf_parser = sub.add_parser("perf", help="Offline performance diagnostics (no model or network calls).")
    perf_sub = perf_parser.add_subparsers(dest="perf_command", required=True)
    summarize = perf_sub.add_parser("summarize", help="Summarize a diagnostic session's events (complete or partial).")
    summarize.add_argument("--session", required=True, help="The AGENT_ENGINE_PERF_SESSION value of the run.")
    summarize.add_argument("--dir", help="Diagnostics folder (default: AGENT_ENGINE_PERF_DIR or logs/perf).")
    summarize.add_argument("--json", action="store_true", help="Print summary.json instead of the Markdown summary.")
    perf_list = perf_sub.add_parser("list", help="List diagnostic sessions.")
    perf_list.add_argument("--dir", help="Diagnostics folder (default: AGENT_ENGINE_PERF_DIR or logs/perf).")
    args = parser.parse_args()

    if args.command == "perf":
        from agent_engine import perf_summary

        raise SystemExit(perf_summary.cli(args))
    command = args.command if args.command != "phase4" else f"phase4 {args.phase4_command}"
    if args.command == "pipeline":
        from agent_engine.phase4.pipeline import configure_environment
        configure_environment()
    perf.init(command)
    code: int | None = None
    try:
        code = _dispatch(args)
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        raise
    except BaseException:
        code = 1
        raise
    finally:
        perf.shutdown(code)
    raise SystemExit(code)


def _dispatch(args: argparse.Namespace) -> int | None:
    if args.command == "pipeline":
        from agent_engine.phase4.pipeline import run
        return run()
    if args.command == "phase4":
        raise SystemExit(phase4_cli.run(args))
    if args.command == "list":
        for name in available_packs():
            try:
                p = load_pack(name)
                print(f"{name:24} {p.description}")
                if p.input_files or p.output_files:
                    print(f"{'':24} in: {', '.join(p.input_files) or '(request only)'}  ->  out: {', '.join(p.output_files) or '-'}")
            except ValueError as e:
                print(f"{name:24} INVALID: {e}")
        return

    if not _PROJECT_NAME_RE.fullmatch(args.project_name):
        raise SystemExit(f"ERROR: invalid --project-name {args.project_name!r} (use a-z, 0-9 and -)")
    if args.command == "add-inputs":
        raise SystemExit(_add_inputs(args.files, args.project_name, args.round))
    if args.command == "gate":
        approver = {"name": args.approver, **({"role": args.approver_role} if args.approver_role else {})}
        raise SystemExit(_gate(args.gate, args.project_name, args.decision, approver, {"name": args.submitted_by}, args.comment))
    if args.review_existing:
        raise SystemExit(asyncio.run(_run(args.request, args.agent, args.project_name, review_existing=True)))
    if args.resume:
        raise SystemExit(asyncio.run(_run(args.request, args.agent, args.project_name, resume=True)))
    if args.resume_verification:
        raise SystemExit(asyncio.run(_run(args.request, args.agent, args.project_name, resume_verification=True)))
    raise SystemExit(asyncio.run(_run(args.request, args.agent, args.project_name)))


if __name__ == "__main__":
    main()
