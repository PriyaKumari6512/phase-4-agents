"""Isolated execution and conflict-checked merge of the two independent stages."""
from __future__ import annotations

import contextvars
import os
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from agent_engine import config, perf
from agent_engine.history import file_digest
from agent_engine.runtime import atomic_json, project_lock

OWNED = {"task-breakdown": {"backlog", "specs", ".specify"}, "infra-pipeline": {"infra"}}


def inventory(root: Path) -> dict[str, str]:
    result = {}
    for p in root.rglob("*"):
        if p.is_symlink():
            raise ValueError(f"stage isolation requires no symlinks: {p.relative_to(root)}")
        if p.is_file() and not p.name.startswith(".engine-"):
            result[p.relative_to(root).as_posix()] = file_digest(p)
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


def run_pair(root: Path, steps: list, runner) -> dict:
    if {s.stage.agent for s in steps} != set(OWNED) or len(steps) != 2:
        raise ValueError("only Task Breakdown and Infra may overlap")
    evidence = Path(config.LOGS_DIR).resolve() / "parallel" / perf.new_id(24)
    if evidence.is_relative_to(root.resolve()):
        raise ValueError("parallel evidence/logs directory must be outside the project")
    # Holding the ORIGINAL job lease blocks ordinary CLI writers, not the children,
    # which each own a different project root. All children finish before merge.
    with project_lock(root):
        from agent_engine import verification_resume
        before = inventory(root)
        context_before = verification_resume.snapshot(root)
        sources = {}
        for step in steps:
            agent = step.stage.agent
            target = evidence / agent / "outputs" / root.name
            shutil.copytree(root, target, ignore=shutil.ignore_patterns(".engine-*.lock"))
            if inventory(target) != before:
                raise ValueError("project changed during snapshot; retry")
            sources[agent] = target
        def run(step):
            agent = step.stage.agent
            return runner(agent, step.request, root.name, outputs_dir=sources[agent].parent,
                          logs_dir=evidence / agent / "logs")
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="phase4-stage") as pool:
            pending = [pool.submit(contextvars.copy_context().run, run, step) for step in steps]
            results = {step.stage.agent: future.result() for step, future in zip(steps, pending)}
        if inventory(root) != before or verification_resume.snapshot(root) != context_before:
            raise ValueError(f"original project changed; results retained at {evidence}")
        changes = {}
        resumable = {}
        for step in steps:
            agent, source = step.stage.agent, sources[step.stage.agent]
            after = inventory(source)
            if verification_resume.checkpoint_path(source, agent).is_file():
                try:
                    resumable[agent] = verification_resume.validate(source, agent, step.request)
                except (ValueError, OSError):
                    pass  # Never promote an invalid child checkpoint to the merged project.
            if results[agent]["status"] in ("success", "done"):
                from agent_engine.phase4.orchestrator import _outputs
                if any(not (source / rel).is_file() for rel in _outputs(step.stage)):
                    raise ValueError(f"{agent} reported success with missing outputs")
            for rel in sorted(set(before) | set(after)):
                if before.get(rel) == after.get(rel):
                    continue
                parts = Path(rel).parts
                allowed = (parts[0] in OWNED[agent] or rel == f"requests/{agent}.md"
                           or (parts[0] == "runs" and rel not in before) or parts[0] == "logs")
                if rel == "report.json":
                    # Preserve BOTH reports; the shared latest report is deterministic.
                    atomic_json(evidence / f"{agent}-result.json", results[agent])
                    changes[rel] = (source / rel) if rel in after else None
                    continue
                if not allowed or rel in changes:
                    raise ValueError(f"unexpected/colliding {agent} write: {rel}; evidence: {evidence}")
                changes[rel] = (source / rel) if rel in after else None
        # Validate all writes before applying any. Roll back ordinary I/O failures.
        applied = []
        backup = evidence / "before-merge"
        shutil.copytree(root, backup, ignore=shutil.ignore_patterns(".engine-*.lock"))
        try:
            for rel, source in changes.items():
                applied.append(rel)
                if source is None:
                    (root / rel).unlink(missing_ok=True)
                else:
                    _replace(source, root / rel)
        except BaseException:
            for rel in reversed(applied):
                if rel in before:
                    _replace(backup / rel, root / rel)
                else:
                    (root / rel).unlink(missing_ok=True)
            raise
        atomic_json(evidence / "results.json", {"results": results, "merged_files": sorted(changes)})
        for step in steps:
            if step.stage.agent in resumable:
                verification_resume.save(root, step.stage.agent, step.request, resumable[step.stage.agent])
            else:
                verification_resume.checkpoint_path(root, step.stage.agent).unlink(missing_ok=True)
        perf.event("parallel_stages", "merge", agents=list(results), files=len(changes), evidence=str(evidence))
        return results
