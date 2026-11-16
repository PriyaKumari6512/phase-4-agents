"""Run history: every run keeps outputs/<project>/runs/<job-id>/ with its
report.json and a copy of each project file it created or changed, so an
earlier version of any output (a PRD, a register) can be shown, compared or
audited. The project's own report.json still holds the latest run.

Engine bookkeeping (inputs/, gates/, runs/, logs/, request histories,
report.json) isn't part of an agent's output, so it isn't compared or copied.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from agent_engine import perf
from agent_engine.runtime import atomic_json
from agent_engine.config import (
    GATES_DIRNAME,
    INPUTS_DIRNAME,
    PROJECT_LOGS_SUBDIR_NAME,
    REPORT_FILENAME,
    REQUESTS_DIRNAME,
    REQUESTS_FILENAME,
    RUNS_DIRNAME,
)

_NOT_OUTPUT = frozenset(
    {INPUTS_DIRNAME, GATES_DIRNAME, RUNS_DIRNAME, PROJECT_LOGS_SUBDIR_NAME, REQUESTS_DIRNAME, REQUESTS_FILENAME, REPORT_FILENAME}
)


def file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(project_dir: Path) -> dict[str, str]:
    """{path relative to the project folder: digest} for every agent output."""
    if not project_dir.is_dir():
        return {}
    with perf.span("fs", "fingerprint") as sp:
        digests = {
            p.relative_to(project_dir).as_posix(): file_digest(p)
            for p in sorted(project_dir.rglob("*"))
            if p.is_file() and p.relative_to(project_dir).parts[0] not in _NOT_OUTPUT
            and not p.name.startswith(".engine-") and not p.name.endswith(".tmp")
        }
        if perf.enabled():
            sp.set(files=len(digests), bytes=sum((project_dir / f).stat().st_size for f in digests))
    return digests


def save_run(project_dir: Path, job_id: str, before: dict[str, str], report: dict) -> dict[str, list[str]]:
    """Copies the files this run created or changed into runs/<job-id>/files/,
    adds the lists to `report` and writes it as runs/<job-id>/report.json.
    """
    run_dir = project_dir / RUNS_DIRNAME / job_id
    after = fingerprint(project_dir)
    changes = {
        "created": [f for f in after if f not in before],
        "changed": [f for f in after if f in before and after[f] != before[f]],
        "deleted": [f for f in before if f not in after],
    }
    with perf.span("fs", "copy_run_history") as sp:
        copied_bytes = 0
        for f in changes["created"] + changes["changed"]:
            copy = run_dir / "files" / f
            copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(project_dir / f, copy)
            copied_bytes += copy.stat().st_size if perf.enabled() else 0
        report["files"] = changes
        run_dir.mkdir(parents=True, exist_ok=True)
        atomic_json(run_dir / REPORT_FILENAME, report)
        sp.set(files_copied=len(changes["created"]) + len(changes["changed"]), bytes_copied=copied_bytes,
               deleted=len(changes["deleted"]))
    return changes
