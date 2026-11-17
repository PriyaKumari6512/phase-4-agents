"""Hash-checked completion records for feature generation, never review approvals.

Checkpoints live outside model-writable files. They retain completed feature work
across a failed parent run, but any changed source or output requires rechecking.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from agent_engine import config
from agent_engine.history import file_digest
from agent_engine.runtime import atomic_json
from agent_engine.phase4 import files
from agent_engine.phase4.contracts import FeatureList, ProjectSettings

VERSION = 1
SETTINGS_KEYS = ("project_name", "code_repos", "infra_repo", "definition_of_done", "story_point_scale",
                 "hours_per_story_point", "max_story_points_per_story", "deadlines")


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def feature(project: str, directory: str):
    from agent_engine.phase4.speckit import FEATURE_DIR_RE
    if not FEATURE_DIR_RE.fullmatch(directory):
        raise files.ProjectError("feature_directory must be specs/NNN-name")
    root = files.project_dir(project)
    if (root / "specs").is_symlink() or (root / directory).is_symlink():
        raise files.ProjectError("feature directories must not be symlinks")
    registered = files.read_json(project, files.FEATURES, FeatureList)
    match = next((f for f in registered.features if f.feature_dir == directory), None)
    if match is None:
        raise files.ProjectError("feature_directory is not in backlog/features.json")
    return match


def _requests(root: Path) -> str:
    path = root / "requests/task-breakdown.md"
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise files.ProjectError("request history must stay inside its project")
    if not path.is_file():
        return _digest([])
    import re
    # Audit timestamps do not alter business meaning. Adjacent identical retries
    # do not supersede other requests; keep all nonidentical requests in order.
    sections = re.split(r"(?m)^## Request \d+ \([^\n]*\)\s*\n", path.read_text(encoding="utf-8"))
    effective = []
    for section in sections:
        content = section.strip()
        if content and (not effective or effective[-1] != content):
            effective.append(content)
    return _digest(effective)


def inputs(project: str, directory: str) -> dict[str, str]:
    root = files.project_dir(project)
    selected = feature(project, directory)
    settings = files.read_json(project, files.PROJECT_SETTINGS, ProjectSettings).model_dump(mode="json")
    result = {"feature": _digest(selected.model_dump(mode="json")),
              files.PROJECT_SETTINGS: _digest({k: settings[k] for k in SETTINGS_KEYS}),
              "requests:effective": _requests(root)}
    for rel in (files.PRD, files.ARCHITECTURE, files.HISTORY, ".specify/memory/constitution.md", ".specify/engine-policy.json",
                "backlog/implementation-contract.md"):
        p = files.path(project, rel)
        if rel == files.PRD:
            from agent_engine.phase4.evidence import packet
            result[rel] = _digest(packet(project, selected.requirement_ids).get(rel, []))
        else:
            result[rel] = file_digest(p) if p.is_file() else "missing"
    for p in sorted((root / ".specify/templates").rglob("*")):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            result[rel] = file_digest(files.path(project, rel))
    # Exact PRD sections and all unclassified/global constraints participate in identity.
    # Architecture remains global until applicability is explicit.
    paths = [Path(config.AGENTS_DIR) / "task-breakdown"]
    for base in paths:
        for p in sorted(base.rglob("*")):
            if p.is_file() and "validator" not in p.relative_to(base).parts:
                result["pack:" + p.relative_to(base).as_posix()] = file_digest(p)
    for name in ("feature_jobs.py", "feature_documents.py", "speckit.py", "speckit_parse.py", "contracts.py", "breakdown_workflow.py", "evidence.py", "planning_records.py", "paged_operation.py", "breakdown_state.py", "review_batches.py"):
        p = Path(__file__).parent / name
        result["implementation:" + name] = file_digest(p) if p.is_file() else "missing"
    for p in sorted((Path(__file__).parent / "speckit_assets").rglob("*")):
        if p.is_file():
            result["template:" + p.relative_to(Path(__file__).parent).as_posix()] = file_digest(p)
    return result


def outputs(project: str, directory: str) -> dict[str, str]:
    base = files.path(project, directory)
    result = {}
    for p in sorted(base.rglob("*")):
        if p.is_symlink():
            raise files.ProjectError("feature outputs must not contain symlinks")
        if p.is_file() and not p.name.startswith(".engine-"):
            result[p.relative_to(base).as_posix()] = file_digest(p)
    return result


def _path(project: str, directory: str) -> Path:
    # directory has already been validated by feature().
    return files.project_dir(project) / ".engine-feature-jobs" / (directory.split("/")[-1] + ".json")


def status(project: str, directory: str) -> dict:
    current = inputs(project, directory)
    path = _path(project, directory)
    record = {}
    if path.is_file():
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    previous = record.get("inputs", {})
    changes = [k for k in sorted(set(current) | set(previous)) if current.get(k) != previous.get(k)]
    actual = outputs(project, directory)
    required = {"spec.md", "plan.md", "tasks.md"}
    reusable = (record.get("version") == VERSION and not changes and required <= actual.keys()
                and record.get("outputs") == actual)
    return {"feature_directory": directory, "reusable": reusable, "changed_inputs": changes,
            "outputs_changed": bool(record and record.get("outputs") != actual),
            "input_sha256": _digest(current), "files": len(actual),
            "note": "Completion checkpoint only; independent backlog validation and semantic review remain required."}


def checkpoint(project: str, directory: str, expected_input_sha256: str) -> dict:
    before = inputs(project, directory)
    if not expected_input_sha256 or expected_input_sha256 != _digest(before):
        raise files.ProjectError("feature inputs changed or input digest missing; read status and recheck the feature")
    from agent_engine.phase4.speckit_parse import parse_spec_md, parse_tasks_md
    parse_spec_md(files.read_text(project, directory + "/spec.md"))
    parse_tasks_md(files.read_text(project, directory + "/tasks.md"))
    actual = outputs(project, directory)
    if not {"spec.md", "plan.md", "tasks.md"} <= actual.keys():
        raise files.ProjectError("feature checkpoint needs spec.md, plan.md and tasks.md")
    if inputs(project, directory) != before:
        raise files.ProjectError("feature inputs changed during checkpoint; retry")
    from agent_engine.stage_controls import active_stage_budget
    if (budget := active_stage_budget.get()) is not None:
        budget.check()
    atomic_json(_path(project, directory), {"version": VERSION, "inputs": before, "outputs": actual})
    return {"feature_directory": directory, "checkpointed": True, "files": len(actual), "approved": False}
