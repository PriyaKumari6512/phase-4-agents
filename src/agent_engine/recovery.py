"""Durable generation/review boundaries; completion is never gate approval.

Artifact/source identity is independent of reviewer code or model identity. Every
resumed review runs the current deterministic checks and the current reviewer.
"""
from __future__ import annotations

import json
import shutil
import uuid
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from agent_engine.history import file_digest
from agent_engine.runtime import atomic_json

DIRECTORIES = {"task-breakdown": ("backlog",), "infra-pipeline": ("infra",),
               "sprint-planning": ("sprint",), "work-allocation": ("allocation",)}
OPTIONAL = {"task-breakdown": ("phase4/history.json",), "infra-pipeline": (),
            "sprint-planning": ("phase4/history.json", "phase4/ci-readiness.json", "phase4/committed-work.json"),
            "work-allocation": ("phase4/skill-profiles.json", "phase4/agent-outcomes.json",
                                "phase4/ci-readiness.json", "phase4/committed-work.json", "infra/manifest.json")}
PHASES = {"generated", "checked", "review_pending", "repair_pending", "repair_running", "awaiting_decision", "verified"}


def path(root: Path, agent: str) -> Path:
    if not agent or any(p in ("", ".", "..") for p in agent.split("/")):
        raise ValueError("invalid recovery agent")
    return root / ".engine-recovery" / (agent.replace("/", "-") + ".json")


def snapshot(root: Path, pack) -> dict[str, str]:
    if pack.name not in DIRECTORIES:
        from agent_engine import verification_resume
        return verification_resume.snapshot(root)
    selected = set(pack.input_files) | set(pack.output_files) | {pack.requests_file}
    selected.update(OPTIONAL.get(pack.name, ()))
    if pack.name in DIRECTORIES:
        selected.add("phase4/project.json")
        for directory in DIRECTORIES[pack.name]:
            for p in (root / directory).rglob("*"):
                if p.is_file() or p.is_symlink():
                    selected.add(p.relative_to(root).as_posix())
    result = {}
    for rel in sorted(selected):
        p = root / rel
        if p.is_symlink() or not p.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"recovery dependency must stay inside project: {rel}")
        if not any(part.startswith(".engine-") for part in Path(rel).parts):
            result[rel] = file_digest(p) if p.is_file() else "missing"
    # Changes to generation instructions invalidate reuse. Reviewer instructions,
    # model settings and runtime fixes do not invalidate saved generation.
    for p in sorted(pack.dir.rglob("*")):
        rel = p.relative_to(pack.dir)
        if p.is_file() and "validator" not in rel.parts and "__pycache__" not in rel.parts:
            result["generator:" + rel.as_posix()] = file_digest(p)
    if pack.name in ("sprint-planning", "work-allocation"):
        result["planning_date"] = datetime.now(timezone.utc).date().isoformat()
    if pack.name in ("infra-pipeline", "sprint-planning", "work-allocation") and (root / "phase4/project.json").is_file():
        from agent_engine.phase4.settings import project_overrides
        import hashlib
        raw = json.loads((root / "phase4/project.json").read_text(encoding="utf-8-sig"))
        effective = project_overrides(raw)
        integration = {"tracker": effective.get("tracker"),
                       "accounts": [(m.get("member_id"), m.get("tracker_account_id")) for m in effective.get("team", [])]}
        original = {"tracker": raw.get("tracker"),
                    "accounts": [(m.get("member_id"), m.get("tracker_account_id")) for m in raw.get("team", [])]}
        if integration != original:
            result["integration_settings"] = hashlib.sha256(json.dumps(integration, sort_keys=True).encode()).hexdigest()
    return result


def evaluation(pack) -> dict[str, str]:
    # Audit/review invalidation only: never forces generation to repeat.
    result = {}
    if pack.verifier:
        from agent_engine.agent import load_pack
        verifier = load_pack(pack.verifier)
        for p in sorted(verifier.dir.rglob("*")):
            if p.is_file():
                result["verifier:" + p.relative_to(verifier.dir).as_posix()] = file_digest(p)
    base = Path(__file__).parent
    common = ("agent.py", "cli.py", "config.py", "runtime.py", "backends.py", "guardrails.py", "locking.py",
              "stage_controls.py", "model_setup.py", "subscription_models.py", "recovery.py")
    domains = {
        "task-breakdown": ("task_breakdown", "structured", "story_import", "backlog", "contracts", "files", "textsim",
                           "skills_taxonomy"),
        "infra-pipeline": ("infra_pipeline", "structured", "infra", "sandbox", "settings", "contracts", "files", "tools"),
        "sprint-planning": ("sprint_planning", "structured", "sprint", "sprint_model", "capacity", "calendars", "settings",
                            "contracts", "files"),
        "work-allocation": ("work_allocation", "structured", "allocation", "alloc_solver", "capacity", "calendars", "readiness", "settings", "contracts", "files", "tools"),
    }
    selected = [base / rel for rel in common] + [base / "phase4" / (name + ".py") for name in domains.get(pack.name, ())]
    for p in selected:
        if p.is_file():
            result["code:" + p.relative_to(base).as_posix()] = file_digest(p)
    import os
    import hashlib
    values = {k: v for k, v in os.environ.items() if k.startswith("SDLC_AGENT_")
              and not any(x in k for x in ("AUTH", "TOKEN", "SECRET", "KEY", "ACCOUNT"))}
    result["model_settings"] = hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()
    return result


def save(root: Path, pack, request: str, job_id: str, phase: str, *, gaps=None, human=False) -> dict:
    if phase not in PHASES:
        raise ValueError("invalid recovery phase")
    if any(not (root / rel).is_file() for rel in pack.output_files):
        raise ValueError("cannot checkpoint incomplete declared outputs")
    current = snapshot(root, pack)
    previous = inspect(root, pack, request)
    backup = previous.get("backup") if previous and previous.get("snapshot") == current else None
    if not backup:
        target = root / ".engine-recovery" / "artifacts" / uuid.uuid4().hex
        for rel, digest in current.items():
            if (digest != "missing" and not rel.startswith("generator:") and rel != "planning_date"
                    and (rel in pack.output_files or Path(rel).parts[0] in DIRECTORIES.get(pack.name, ()))):
                dest = target / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(root / rel, dest)
                if file_digest(dest) != digest:
                    raise ValueError("artifacts changed while saving recovery checkpoint")
        if snapshot(root, pack) != current:
            raise ValueError("inputs changed while saving recovery checkpoint")
        backup = target.relative_to(root).as_posix()
    record = {"version": 1, "agent": pack.name, "request": request, "job_id": job_id,
              "phase": phase, "snapshot": current, "backup": backup, "gaps": list(gaps or []),
              "human_needed": human, "at": datetime.now(timezone.utc).isoformat(),
              "evaluation": evaluation(pack) if phase in ("verified", "awaiting_decision") else None}
    atomic_json(path(root, pack.name), record)
    return record


def inspect(root: Path, pack, request: str | None = None) -> dict | None:
    try:
        record = json.loads(path(root, pack.name).read_text(encoding="utf-8"))
        if (record.get("version") != 1 or record.get("agent") != pack.name or record.get("phase") not in PHASES
                or (request is not None and record.get("request") != request)
                or any(not (root / rel).is_file() for rel in pack.output_files)
                or record.get("snapshot") != snapshot(root, pack)):
            return None
        return record
    except (OSError, ValueError, TypeError):
        return None


def next_action(root: Path, pack, request: str | None = None) -> tuple[str, dict | None]:
    record = inspect(root, pack, request)
    if record is None:
        try:
            interrupted = json.loads(path(root, pack.name).read_text(encoding="utf-8"))
            if (not isinstance(interrupted, dict) or interrupted.get("version") != 1
                    or interrupted.get("agent") != pack.name or interrupted.get("phase") not in PHASES
                    or not isinstance(interrupted.get("snapshot"), dict)
                    or not isinstance(interrupted.get("request"), str) or not interrupted.get("job_id")):
                return "conflict", {"request": request or "", "job_id": "invalid-record",
                                    "gaps": ["Recovery metadata is invalid; artifacts are retained. Use --review-existing to recheck current outputs."]}
            current = snapshot(root, pack)
            if (interrupted.get("phase") == "repair_running" and interrupted.get("agent") == pack.name
                    and (request is None or request == interrupted.get("request"))
                    and _repair_inputs(interrupted["snapshot"], pack) == _repair_inputs(current, pack)):
                return "restore_repair", interrupted
            if (_inputs(interrupted["snapshot"], pack) == _inputs(current, pack)
                    and (request is None or request == interrupted["request"])):
                return "conflict", {**interrupted, "gaps": ["Saved artifacts changed; current edits are retained. Use --review-existing to recheck them without generation."]}
        except (OSError, ValueError, KeyError, TypeError):
            if path(root, pack.name).is_file():
                return "conflict", {"request": request or "", "job_id": "unreadable-record",
                                    "gaps": ["Recovery metadata cannot be verified; artifacts are retained. Use --review-existing after inspecting the current outputs."]}
        # Existing runs already saved review-only checkpoints. Upgrade on use,
        # without asking the writer to regenerate retained, unchanged artifacts.
        from agent_engine import verification_resume
        try:
            old = json.loads(verification_resume.checkpoint_path(root, pack.name).read_text(encoding="utf-8"))
            original = old["request"]
            if request is None or request == original:
                job = verification_resume.validate(root, pack.name, original)
                return "verify", {"job_id": job, "request": original, "phase": "review_pending", "legacy": True}
        except (OSError, ValueError, KeyError, TypeError):
            pass
        return "generate", None
    if record["phase"] == "awaiting_decision":
        if not record.get("human_needed") and record.get("evaluation") != evaluation(pack):
            return "verify", record
        return "wait", record
    if record["phase"] in ("repair_pending", "repair_running"):
        return "repair", record
    if record["phase"] == "verified" and record.get("evaluation") == evaluation(pack):
        return "complete", record
    return "verify", record


def _owned(rel: str, pack) -> bool:
    return rel in pack.output_files or Path(rel).parts[0] in DIRECTORIES.get(pack.name, ())


def _inputs(values: dict, pack) -> dict:
    return {key: value for key, value in values.items() if not _owned(key, pack)}


def input_identity(root: Path, pack) -> dict:
    return _inputs(snapshot(root, pack), pack)


def _repair_inputs(values: dict, pack) -> dict:
    return _inputs(values, pack)


def _copy(source: Path, target: Path):
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".engine-recovery-", dir=target.parent)
    os.close(fd)
    try:
        shutil.copyfile(source, temporary)
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)


def restore_repair(root: Path, pack, record: dict) -> None:
    """Keep interrupted edits, restore a verified-byte snapshot, then retry repair.

    Never restores after changed source inputs, and never drops the interrupted
    edits: they remain in an engine recovery directory for inspection.
    """
    current = snapshot(root, pack)
    if _repair_inputs(current, pack) != _repair_inputs(record["snapshot"], pack):
        raise ValueError("repair inputs changed; cannot restore the prior checkpoint")
    backup = root / record["backup"]
    base = (root / ".engine-recovery/artifacts").resolve()
    if backup.is_symlink() or backup.resolve().parent != base:
        raise ValueError("invalid repair backup location")
    prior = {rel: digest for rel, digest in record["snapshot"].items() if _owned(rel, pack) and digest != "missing"}
    for rel, digest in prior.items():
        if (backup / rel).is_symlink() or not (backup / rel).resolve().is_relative_to(backup.resolve()) or file_digest(backup / rel) != digest:
            raise ValueError("repair backup is missing or changed; generation was not rerun")
    retained = root / ".engine-recovery/interrupted" / uuid.uuid4().hex
    for rel, digest in current.items():
        if _owned(rel, pack) and digest != "missing":
            dest = retained / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / rel, dest)
    # Snapshot is validated before any replacement. The still-running journal
    # makes interruption of restoration itself safe to replay.
    for rel in set(prior) | {rel for rel in current if _owned(rel, pack)}:
        if rel in prior:
            _copy(backup / rel, root / rel)
        else:
            (root / rel).unlink(missing_ok=True)
    record.update(phase="repair_pending", interrupted_edits=retained.relative_to(root).as_posix())
    atomic_json(path(root, pack.name), record)
