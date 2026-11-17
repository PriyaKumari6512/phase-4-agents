"""Durable isolated execution and replayable, conflict-checked parallel merges."""
from __future__ import annotations

import contextvars
import json
import os
import re
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath

from agent_engine import config, perf, recovery
from agent_engine.history import file_digest
from agent_engine.runtime import atomic_json, project_lock

OWNED = {"task-breakdown": {"backlog", "specs", ".specify"}, "infra-pipeline": {"infra"}}
POINTER = ".engine-pending-merge.json"
PLAN = "merge-plan.json"


def inventory(root: Path) -> dict[str, str]:
    result = {}
    for p in root.rglob("*"):
        rel = p.relative_to(root)
        if p.is_symlink():
            raise ValueError(f"stage isolation requires no symlinks: {rel}")
        # These journals are imported through validated recovery APIs, not raw
        # copies. Feature completion metadata has a separate narrow allowlist.
        if rel.parts[0] == ".engine-recovery":
            continue
        if rel.as_posix() == "phase4/orchestrator-state.json":
            continue  # acknowledged separately; state may be saved before pointer removal
        if p.is_file() and not p.name.startswith(".engine-"):
            result[rel.as_posix()] = file_digest(p)
    return result


def _replace(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=target.parent, prefix=".engine-merge-")
    os.close(fd)
    try:
        shutil.copyfile(source, name)
        os.replace(name, target)
    finally:
        Path(name).unlink(missing_ok=True)


def _read(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"invalid recovery record: {path}")
    return data


def _session(root: Path, evidence: Path) -> Path:
    evidence = evidence.resolve()
    base = Path(config.LOGS_DIR).resolve() / "parallel"
    if evidence.parent != base or evidence.is_relative_to(root.resolve()) or evidence.is_symlink():
        raise ValueError("parallel session must be a direct directory under the configured logs/parallel")
    return evidence


def _feature_checkpoint(source: Path, rel: str) -> None:
    parts = Path(rel).parts
    if len(parts) != 2 or not re.fullmatch(r"[0-9]{3}-[a-z0-9][a-z0-9-]*\.json", parts[1]):
        raise ValueError(f"unexpected feature checkpoint path: {rel}")
    directory = "specs/" + parts[1][:-5]
    features = _read(source / "backlog/features.json").get("features", [])
    if directory not in {f.get("feature_dir") for f in features}:
        raise ValueError(f"unregistered feature checkpoint: {rel}")
    data = _read(source / rel)
    outputs = data.get("outputs", {})
    if (data.get("version") != 1 or not isinstance(data.get("inputs"), dict) or not isinstance(outputs, dict)
            or not {"spec.md", "tasks.md", "plan.md"} <= outputs.keys()):
        raise ValueError(f"invalid feature checkpoint: {rel}")
    base = source / directory
    actual = {}
    for p in base.rglob("*"):
        if p.is_symlink():
            raise ValueError("feature checkpoint contains symlinks")
        if p.is_file() and not p.name.startswith(".engine-"):
            actual[p.relative_to(base).as_posix()] = file_digest(p)
    if actual != outputs:
        raise ValueError(f"feature checkpoint output hashes do not match: {rel}")


def _sources(evidence: Path, root: Path):
    result = {agent: evidence / agent / "outputs" / root.name for agent in OWNED}
    for source in result.values():
        if not source.resolve().is_relative_to(evidence.resolve()):
            raise ValueError("retained child root escapes its session")
        if any(p.is_symlink() for p in (source, source.parent, source.parent.parent)):
            raise ValueError("retained child roots must not be symlinks")
    return result


def _validate_plan(root: Path, plan: dict):
    if (plan.get("version") != 1 or plan.get("project") != root.name
            or plan.get("state") not in {"running", "ready", "applying", "committed"}
            or set(plan.get("requests", {})) != set(OWNED) or not isinstance(plan.get("before"), dict)):
        raise ValueError("invalid parallel recovery manifest")
    for rel in plan["before"]:
        p = PurePosixPath(rel)
        if p.is_absolute() or ".." in p.parts or "\\" in rel or not p.parts:
            raise ValueError("invalid path in parallel recovery manifest")


def _collect(root: Path, evidence: Path, plan: dict):
    before = plan["before"]
    changes, results = {}, {}
    for agent, source in _sources(evidence, root).items():
        if not plan.get("legacy") and "control" in plan and _control(source) != plan["control"]:
            raise ValueError(f"unexpected {agent} write to orchestrator bookkeeping")
        saved = _read(evidence / f"{agent}-result.json")
        after = inventory(source)
        if saved.get("inventory") != after:
            raise ValueError(f"retained {agent} output changed; refusing stale merge")
        result = saved["result"]
        results[agent] = result
        if result["status"] in ("success", "done"):
            from agent_engine.phase4.orchestrator import _outputs, STAGE_BY_AGENT
            if any(not (source / rel).is_file() for rel in _outputs(STAGE_BY_AGENT[agent])):
                raise ValueError(f"{agent} reported success with missing outputs")
        for rel in sorted(set(before) | set(after)):
            if before.get(rel) == after.get(rel):
                continue
            parts = Path(rel).parts
            if plan.get("legacy"):
                sibling = set().union(*OWNED.values()) - OWNED[agent]
                if parts[0] in sibling or (agent == "infra-pipeline" and parts[0] == ".engine-feature-jobs"):
                    continue  # never copy a sibling's artifacts from an older snapshot
                if parts[0] in {"runs", "logs"} and rel in before:
                    continue  # legacy sessions cannot prove ownership of prior history
                if parts[0] == "requests" and rel != f"requests/{agent}.md":
                    continue
            allowed = (parts[0] in OWNED[agent] or rel == f"requests/{agent}.md"
                       or (parts[0] == "runs" and rel not in before) or parts[0] == "logs")
            if parts[0] == ".engine-feature-jobs" and agent == "task-breakdown":
                if len(parts) != 2 or not re.fullmatch(r"[0-9]{3}-[a-z0-9][a-z0-9-]*\.json", parts[1]):
                    raise ValueError(f"unexpected feature checkpoint path: {rel}")
                if rel in after:
                    _feature_checkpoint(source, rel)
                allowed = True
            if rel == "report.json":
                changes[rel] = (source / rel) if rel in after else None
                continue
            if not allowed or rel in changes:
                raise ValueError(f"unexpected/colliding {agent} write: {rel}; evidence: {evidence}")
            changes[rel] = (source / rel) if rel in after else None
    return changes, results


def _expected(plan: dict, changes: dict) -> dict:
    result = dict(plan["before"])
    for rel, source in changes.items():
        if source is None:
            result.pop(rel, None)
        else:
            result[rel] = file_digest(source)
    return result


def _check_original(root: Path, plan: dict, expected: dict) -> None:
    actual = inventory(root)
    if plan["state"] == "committed":
        if actual != expected:
            raise ValueError("project changed after the retained merge committed")
    elif plan["state"] == "applying":
        # A crash may leave a prefix of writes installed. Each path must still
        # equal its old or intended bytes; unrelated edits are never overwritten.
        for rel in set(actual) | set(plan["before"]) | set(expected):
            if actual.get(rel) not in {plan["before"].get(rel), expected.get(rel)}:
                raise ValueError(f"original project changed at {rel}; retained results were not overwritten")
    elif actual != plan["before"]:
        raise ValueError("original project changed; retained results require conflict resolution")


def _import_journals(root: Path, evidence: Path, plan: dict):
    from agent_engine.agent import load_pack
    from agent_engine import verification_resume
    for agent, source in _sources(evidence, root).items():
        pack = load_pack(agent)
        request = plan["requests"][agent]
        record = recovery.inspect(source, pack, request)
        if record is None and recovery.path(source, agent).is_file():
            raise ValueError(f"retained {agent} generation inputs or artifacts changed; refusing stale recovery")
        if record:
            phase = record["phase"]
            if phase == "verified" and record.get("evaluation") != recovery.evaluation(pack):
                phase = "review_pending"
            recovery.save(root, pack, request, record["job_id"], phase,
                          gaps=record.get("gaps"), human=record.get("human_needed", False))
        elif verification_resume.checkpoint_path(source, agent).is_file():
            try:
                job = verification_resume.validate(source, agent, request)
            except (OSError, ValueError):
                continue
            recovery.save(root, pack, request, job, "review_pending")
            verification_resume.save(root, agent, request, job)
        elif (source / "report.json").is_file():
            report = _read(source / "report.json")
            writer_completed = any(p.get("agent") == agent and p.get("kind") == "write" and p.get("ok")
                                   for p in report.get("passes", []))
            if (writer_completed and report.get("agent") == agent and report.get("project") == root.name
                    and report.get("request_text") == request and report.get("job_id")
                    and all((root / rel).is_file() for rel in pack.output_files)):
                negative = report.get("verified") and not (report.get("verdict") or {}).get("satisfied")
                recovery.save(root, pack, request, report["job_id"],
                              "awaiting_decision" if negative else "review_pending",
                              gaps=(report.get("verdict") or {}).get("gaps", []))


def _merge(root: Path, evidence: Path, plan: dict) -> dict:
    _validate_plan(root, plan)
    changes, results = _collect(root, evidence, plan)
    expected = _expected(plan, changes)
    _check_original(root, plan, expected)
    backup = evidence / "before-merge"
    if plan["state"] != "committed":
        if plan["state"] != "applying":
            if backup.exists():
                shutil.rmtree(backup)
            shutil.copytree(root, backup, ignore=shutil.ignore_patterns(".engine-*.lock"))
        plan.update(state="applying", expected=expected, changes=list(changes))
        atomic_json(evidence / PLAN, plan)  # durable intent precedes the first mutation
        applied = []
        try:
            for rel, source in changes.items():
                applied.append(rel)
                if source is None:
                    (root / rel).unlink(missing_ok=True)
                else:
                    _replace(source, root / rel)
        except Exception as exc:
            # Process/power loss leaves state=applying for idempotent replay.
            for rel in reversed(applied):
                try:
                    if rel in plan["before"]:
                        _replace(backup / rel, root / rel)
                    else:
                        (root / rel).unlink(missing_ok=True)
                except Exception as rollback:
                    exc.add_note(f"rollback failed for {rel}: {rollback}")
            if inventory(root) == plan["before"]:
                plan["state"] = "ready"
                atomic_json(evidence / PLAN, plan)
            raise
    # Journals are re-derived after all owned artifacts are installed; they are
    # not blindly copied between roots. This step is replayable after a crash.
    _import_journals(root, evidence, plan)
    plan.update(state="committed", expected=expected)
    atomic_json(evidence / PLAN, plan)
    atomic_json(evidence / "results.json", {"results": results, "merged_files": sorted(changes)})
    perf.event("parallel_stages", "merge", agents=list(results), files=len(changes), evidence=str(evidence))
    return results


def pending(root: Path) -> bool:
    return (root / POINTER).is_file()


def _control(root: Path) -> dict:
    state = root / "phase4/orchestrator-state.json"
    return {"orchestrator_state": file_digest(state) if state.is_file() else None}


def acknowledge(root: Path) -> None:
    """Only after orchestration has durably saved stage outcomes."""
    (root / POINTER).unlink(missing_ok=True)


def replay_pending(root: Path, runner=None) -> dict | None:
    if not pending(root):
        return None
    evidence = _session(root, Path(_read(root / POINTER)["session"]))
    plan = _read(evidence / PLAN)
    if plan.get("version") != 1 or plan.get("project") != root.name:
        raise ValueError("parallel recovery manifest belongs to another project/version")
    if plan["state"] == "running":
        if runner is None:
            return None
        from agent_engine.phase4.orchestrator import Step, STAGE_BY_AGENT
        steps = [Step(STAGE_BY_AGENT[agent], "run", "resume interrupted parallel run", request)
                 for agent, request in plan["requests"].items()]
        return run_pair(root, steps, runner)
    with project_lock(root):
        return _merge(root, evidence, plan)


def recover_session(root: Path, session: Path) -> dict:
    """Explicitly recover retained sessions, including pre-journal merge failures.

    Older sessions have no trustworthy old-output manifest. Import is permitted
    only into absent/identical owned files and unchanged shared inputs; otherwise
    require conflict resolution rather than overwriting possibly newer work.
    """
    evidence = _session(root, session)
    with project_lock(root):
        if not (evidence / PLAN).is_file():
            before = inventory(root)
            requests = {}
            for agent, source in _sources(evidence, root).items():
                after = inventory(source)
                report = _read(source / "report.json")
                if (report.get("agent") != agent or report.get("project") != root.name
                        or not report.get("job_id") or not report.get("finished_at")
                        or report.get("status") not in {"success", "done", "partial", "fail"}):
                    raise ValueError(f"retained {agent} report is incomplete or belongs to another project")
                requests[agent] = report["request_text"]
                for rel in set(before) | set(after):
                    parts = Path(rel).parts
                    generated = parts[0] in OWNED[agent] or (agent == "task-breakdown" and parts[0] == ".engine-feature-jobs")
                    bookkeeping = parts[0] in {"runs", "logs"} or rel == "report.json"
                    if generated:
                        if rel in before and before.get(rel) != after.get(rel):
                            raise ValueError(f"existing project output conflicts at {rel}; retained work remains saved")
                    elif rel == f"requests/{agent}.md":
                        old = (root / rel).read_text(encoding="utf-8") if rel in before else ""
                        new = (source / rel).read_text(encoding="utf-8") if rel in after else ""
                        if not new.startswith(old):
                            raise ValueError("request history changed since the retained run")
                    elif (parts[0] in set().union(*OWNED.values()) or parts[0] == ".engine-feature-jobs"
                          or (parts[0] == "requests" and rel != f"requests/{agent}.md")):
                        continue  # sibling outputs are not inputs to this independent stage
                    elif not bookkeeping and before.get(rel) != after.get(rel):
                        raise ValueError(f"shared inputs changed at {rel}; refusing stale import")
                atomic_json(evidence / f"{agent}-result.json", {"inventory": after, "result": {
                    "status": report["status"], "exit_code": 0 if report["status"] in ("success", "done") else 1,
                    "gaps": (report.get("verdict") or {}).get("gaps", []), "rate_limited": False}})
            plan = {"version": 1, "project": root.name, "state": "ready", "before": before,
                    "requests": requests, "legacy": True}
            atomic_json(evidence / PLAN, plan)
        else:
            plan = _read(evidence / PLAN)
            if plan.get("project") != root.name or plan.get("version") != 1:
                raise ValueError("session belongs to another project/version")
        if pending(root) and _session(root, Path(_read(root / POINTER)["session"])) != evidence:
            raise ValueError("a different parallel session is already pending")
        atomic_json(root / POINTER, {"session": str(evidence)})
        if plan["state"] == "running":
            raise ValueError("session has unfinished children; rerun orchestrate --parallel-independent")
        return _merge(root, evidence, plan)


def run_pair(root: Path, steps: list, runner) -> dict:
    if {s.stage.agent for s in steps} != set(OWNED) or len(steps) != 2:
        raise ValueError("only Task Breakdown and Infra may overlap")
    with project_lock(root):
        if pending(root):
            evidence = _session(root, Path(_read(root / POINTER)["session"]))
            plan = _read(evidence / PLAN)
            if plan["project"] != root.name or plan["requests"] != {s.stage.agent: s.request for s in steps}:
                raise ValueError("pending parallel run has different requests; recover it before starting another")
            if plan["state"] != "running":
                return _merge(root, evidence, plan)
            if inventory(root) != plan["before"]:
                raise ValueError("original project changed since parallel execution began")
        else:
            evidence = _session(root, Path(config.LOGS_DIR).resolve() / "parallel" / perf.new_id(24))
            before = inventory(root)
            for source in _sources(evidence, root).values():
                shutil.copytree(root, source, ignore=shutil.ignore_patterns(".engine-*.lock"))
                if inventory(source) != before:
                    raise ValueError("project changed during snapshot; retry")
            plan = {"version": 1, "project": root.name, "state": "running", "before": before, "control": _control(root),
                    "requests": {s.stage.agent: s.request for s in steps}}
            atomic_json(evidence / PLAN, plan)
            atomic_json(root / POINTER, {"session": str(evidence)})
        sources = _sources(evidence, root)
        _validate_plan(root, plan)
        # Reject corrupt/stale retained metadata before starting any unfinished
        # child, so a merge bookkeeping problem cannot spend new model work.
        for agent, source in sources.items():
            if "control" in plan and _control(source) != plan["control"]:
                raise ValueError(f"unexpected {agent} write to orchestrator bookkeeping")
            saved_path = evidence / f"{agent}-result.json"
            if saved_path.is_file():
                saved = _read(saved_path)
                if (saved.get("inventory") != inventory(source) or not isinstance(saved.get("result"), dict)
                        or saved["result"].get("status") not in {"success", "done", "partial", "fail"}):
                    raise ValueError(f"retained {agent} result cannot be verified")
        def run(step):
            agent = step.stage.agent
            saved_path = evidence / f"{agent}-result.json"
            if saved_path.is_file():
                saved = _read(saved_path)
                if saved.get("inventory") != inventory(sources[agent]):
                    raise ValueError(f"retained {agent} output changed")
                return saved["result"]
            result = runner(agent, step.request, root.name, outputs_dir=sources[agent].parent,
                            logs_dir=evidence / agent / "logs")
            atomic_json(saved_path, {"result": result, "inventory": inventory(sources[agent])})
            return result
        # Each completion is persisted independently. Waiting for one failed child
        # does not discard the already finished child's result.
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="phase4-stage") as pool:
            futures = [pool.submit(contextvars.copy_context().run, run, step) for step in steps]
            for future in futures:
                future.result()
        plan["state"] = "ready"
        atomic_json(evidence / PLAN, plan)
        return _merge(root, evidence, plan)
