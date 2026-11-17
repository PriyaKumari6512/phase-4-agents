"""The project folder (outputs/<project>/) as the Phase 4 tools see it.

Tools are trusted code, so they write to disk directly instead of through the
agent's file tools. They still keep the engine's rules: only inside the
project folder, never in its read-only folders (inputs/, gates/, requests/,
runs/), never through `..`.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from pathlib import PurePosixPath
from typing import TypeVar

from pydantic import BaseModel

from agent_engine import config
from agent_engine.runtime import active_project, active_inputs, atomic_text

PROJECT_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
M = TypeVar("M", bound=BaseModel)

# Fixed locations inside outputs/<project>/ (the agents' [input] / [output] files).
PROJECT_SETTINGS = "phase4/project.json"
HISTORY = "phase4/history.json"
STORIES = "phase4/stories.json"      # approved stories imported from the tracker (story_import.py)
SKILL_PROFILES = "phase4/skill-profiles.json"
AGENT_OUTCOMES = "phase4/agent-outcomes.json"
PRD = "prd.md"
ARCHITECTURE = "architecture.md"
BACKLOG = "backlog/backlog.json"
BACKLOG_MD = "backlog/backlog.md"
CAPACITY = "sprint/capacity.json"
SPRINT_PLAN = "sprint/sprint-plan.json"
SPRINT_PLAN_MD = "sprint/sprint-plan.md"
ALLOCATION_PROBLEM = "allocation/problem.json"
ASSIGNMENTS = "allocation/assignments.json"
ASSIGNMENTS_MD = "allocation/assignments.md"
INFRA_INTENT = "infra/intent.json"
INFRA_MANIFEST = "infra/manifest.json"
INFRA_CHECKS = "infra/checks.json"
INFRA_PR = "infra/PR.md"
INFRA_REPO_DIR = "infra/repo"
INFRA_CI_DIR = "infra/ci"
PUBLISH_DIR = "publish"
TRACKER_DIR = "tracker"


class ProjectError(ValueError):
    """A tool-facing error; its message is returned to the model as-is."""


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def new_id() -> str:
    return str(uuid.uuid4())


def project_dir(project: str) -> Path:
    if active_project.get() not in (None, project):
        raise ProjectError(f"this run is bound to project {active_project.get()!r}, not {project!r}")
    if not PROJECT_RE.fullmatch(project or ""):
        raise ProjectError(f"invalid project name {project!r}: use the <project-name> from /outputs/<project-name>/")
    path = Path(config.OUTPUTS_DIR) / project
    if path.is_symlink() or path.resolve().parent != Path(config.OUTPUTS_DIR).resolve():
        raise ProjectError("project directory must be inside the configured outputs directory")
    if not path.is_dir():
        raise ProjectError(f"project folder /outputs/{project}/ does not exist")
    return path


def _rel(rel: str, *, write: bool) -> str:
    rel = rel.replace("\\", "/").strip("/")
    if ".." in rel.split("/"):
        raise ProjectError(f"invalid project path {rel!r}")
    rel = str(PurePosixPath(rel))
    parts = rel.split("/")
    if not rel or ".." in parts or rel.startswith("~"):
        raise ProjectError(f"invalid project path {rel!r}")
    if write and (parts[0] in config.READ_ONLY_PROJECT_DIRS or parts[0].startswith(".engine-")
                  or rel in active_inputs.get() or rel == "report.json"):
        raise ProjectError(f"{rel!r} is in a read-only project folder")
    return rel


def path(project: str, rel: str, *, write: bool = False) -> Path:
    if write:
        from agent_engine.stage_controls import active_stage_budget
        if (budget := active_stage_budget.get()) is not None:
            budget.check()
    root = project_dir(project).resolve()
    target = root / _rel(rel, write=write)
    if not target.resolve().is_relative_to(root):
        raise ProjectError(f"path escapes project: {rel!r}")
    return target


def virtual(project: str, rel: str) -> str:
    return f"{config.OUTPUTS_VIRTUAL_PREFIX}{project}/{_rel(rel, write=False)}"


def virtual_root(project: str) -> str:
    """The project folder as the agent sees it, e.g. /outputs/gym-app/."""
    project_dir(project)
    return f"{config.OUTPUTS_VIRTUAL_PREFIX}{project}/"


def exists(project: str, rel: str) -> bool:
    return path(project, rel).is_file()


def read_text(project: str, rel: str) -> str:
    p = path(project, rel)
    if not p.is_file():
        raise ProjectError(f"/outputs/{project}/{rel} does not exist")
    return p.read_text(encoding="utf-8-sig")


def read_json(project: str, rel: str, model: type[M] | None = None):
    text = read_text(project, rel)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ProjectError(f"/outputs/{project}/{rel} is not valid JSON: {e}") from e
    if model is None:
        return data
    try:
        from agent_engine.phase4.contracts import ProjectSettings
        if model is ProjectSettings:
            from agent_engine.phase4.settings import project_overrides
            data = project_overrides(data)
        parsed = model.model_validate(data)
        if hasattr(parsed, "project") and parsed.project != project:
            raise ProjectError(f"artifact belongs to project {parsed.project!r}, not {project!r}")
        return parsed
    except Exception as e:  # pydantic.ValidationError, reported to the model verbatim
        raise ProjectError(f"/outputs/{project}/{rel} does not match its schema: {e}") from e


def write_text(project: str, rel: str, text: str) -> Path:
    p = path(project, rel, write=True)
    p.parent.mkdir(parents=True, exist_ok=True)
    from agent_engine.stage_controls import active_stage_budget
    if (budget := active_stage_budget.get()) is not None:
        budget.check()
    # LF on every OS: generated repository files must not change (or change their hash) on Windows
    atomic_text(p, text)
    return p


def write_json(project: str, rel: str, data) -> Path:
    if isinstance(data, BaseModel):
        text = data.model_dump_json(indent=2)
    else:
        text = json.dumps(data, indent=2, default=str)
    return write_text(project, rel, text + "\n")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def file_sha(project: str, rel: str) -> str:
    return sha256_file(path(project, rel))
