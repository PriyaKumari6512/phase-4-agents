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
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.callbacks import UsageMetadataCallbackHandler

from agent_engine.agent import AgentPack, Verdict, available_packs, build_agent, load_pack, model_spec
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
from agent_engine.phase4 import cli as phase4_cli

logger = logging.getLogger(__name__)
transcript_logger = logging.getLogger(TRANSCRIPT_LOGGER_NAME)

_PROJECT_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


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
            transcript_logger.info("[%s] %s%s", getattr(msg, "type", "?"), f"tool_calls=[{calls}] " if calls else "", _text(msg.content))
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


async def _run(request: str, agent_name: str, project_name: str) -> int:
    try:  # fail on a bad pack (or its verifier) before any model call
        pack = load_pack(agent_name)
        verifier = load_pack(pack.verifier) if pack.verifier else None
        if verifier is not None and verifier.returns != "verdict":
            raise ValueError(f"verifier {pack.verifier!r} must declare returns = \"verdict\"")
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1

    # Declared inputs must exist before any model call (and before this request is recorded).
    missing = _missing(project_name, pack.input_files)
    if missing:
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
    stale = stale_approvals(OUTPUTS_DIR / project_name, pack.input_files)
    if stale:
        for problem in stale:
            print(f"ERROR: {pack.name} can't run: {problem}. Get the gate approved again first.")
        return 1

    job_id = new_job_id()
    attach_job_log_handler(job_id)
    notify_job_log_path(f"{OUTPUTS_VIRTUAL_PREFIX}{project_name}/")
    request_number = _record_request(project_name, request, pack.requests_file)
    outputs_before = fingerprint(OUTPUTS_DIR / project_name)
    logger.info("run start job_id=%s agent=%s project=%s request=%d", job_id, pack.name, project_name, request_number)

    # One usage handler across every pass (agent, verifier, fixes) so tokens are counted for all of them.
    usage = UsageMetadataCallbackHandler()
    langfuse = build_langfuse_handler()
    callbacks = [usage, *([langfuse] if langfuse else [])]
    started = time.perf_counter()
    report: dict = {
        "job_id": job_id, "agent": pack.name, "project": project_name, "request": request_number, "request_text": request,
    }
    exit_code = 0

    passes: list[dict] = []
    report["passes"] = passes
    # Where each pack is in its `model` escalation order (agent.AgentPack.models).
    level = {pack.name: 0, **({verifier.name: 0} if verifier else {})}

    async def run_pass(p: AgentPack, kind: str, message: str) -> dict | None:
        """One pass of pack `p` on its current model; a model error moves it
        one step along its escalation order and retries, until the list runs out.
        """
        while True:
            tier = p.models[level[p.name]]
            entry = {"kind": kind, "agent": p.name, "model_tier": tier, "model": model_spec(tier)}
            passes.append(entry)
            try:
                state = await _stream(build_agent(p, level[p.name]), message, callbacks, f"{p.name}-{kind}")
                entry["ok"] = True
                return state
            except Exception as e:
                entry.update(ok=False, error=str(e))
                if level[p.name] + 1 >= len(p.models):
                    raise
                level[p.name] += 1
                logger.warning("%s %s pass failed on %s, retrying on %s: %s", p.name, kind, tier, p.models[level[p.name]], e)
                print(f"\n[{p.name}: {tier} model failed ({e}); retrying on {p.models[level[p.name]]}]")

    try:
        state = await run_pass(pack, "write", _agent_message(pack, request, project_name, request_number))
        report["agent_reply"] = _text(state["messages"][-1].content) if state and state.get("messages") else None
        print(report["agent_reply"] or "(agent produced no reply)")
        # A declared output that wasn't written is a failed run, not something to pay a verifier for.
        missing = _missing(project_name, pack.output_files)
        if missing:
            raise RuntimeError(f"{pack.name} did not create its declared output: {', '.join(missing)}")

        if verifier is None:
            report.update(status="done", verified=False)
        else:
            for attempt in range(1, pack.max_fix_loops + 2):
                report["loops"] = attempt
                try:
                    state = await run_pass(verifier, "verify", _verifier_message(pack, project_name))
                    verdict = state.get("structured_response") if state else None
                    if not isinstance(verdict, Verdict):
                        raise RuntimeError("no structured verdict returned")
                    passes[-1]["satisfied"] = verdict.satisfied
                except Exception as e:
                    logger.exception("verifier %s failed on attempt %d", verifier.name, attempt)
                    verdict = Verdict(
                        satisfied=False, status_so_far="partial", gaps=[f"verifier failed: {e}"],
                        summary="The verifier could not complete this attempt; the output was not judged.",
                    )
                    report.update(status="partial", verified=False, verdict=verdict.model_dump())
                    print(f"\n=== {verifier.name} failed (attempt {attempt}): {e} ===")
                    break
                report.update(status=verdict.status_so_far, verified=True, verdict=verdict.model_dump())
                print(f"\n=== {verifier.name} verdict (attempt {attempt}): {verdict.status_so_far} ===\n{verdict.summary}")
                for gap in verdict.gaps:
                    print(f"  - {gap}")
                if verdict.satisfied or attempt > pack.max_fix_loops:
                    break
                # A failed verdict moves the fix pass one step up the escalation order.
                if level[pack.name] + 1 < len(pack.models):
                    level[pack.name] += 1
                    print(f"\n[{pack.name}: escalating fix pass to the {pack.models[level[pack.name]]} model]")
                await run_pass(pack, "fix", _fix_message(pack, project_name, verdict.gaps))
        exit_code = 0 if report["status"] in ("done", "success") else 1
    except Exception as e:
        logger.exception("run failed job_id=%s", job_id)
        report.update(status="fail", error=str(e))
        print(f"\nERROR: run failed: {e}")
        exit_code = 1
    finally:
        report["elapsed_seconds"] = round(time.perf_counter() - started, 1)
        report["tokens"] = usage.usage_metadata
        report["finished_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        save_run(OUTPUTS_DIR / project_name, job_id, outputs_before, report)
        report_path = OUTPUTS_DIR / project_name / REPORT_FILENAME
        report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        trace_host = flush_langfuse(langfuse)
        job_log = current_job_log_path()
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
    phase4_cli.add_parser(sub)
    args = parser.parse_args()

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
    raise SystemExit(asyncio.run(_run(args.request, args.agent, args.project_name)))


if __name__ == "__main__":
    main()
