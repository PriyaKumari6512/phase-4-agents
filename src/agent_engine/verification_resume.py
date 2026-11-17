"""Exact-snapshot retry of a failed semantic review; never a cached approval."""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os

from agent_engine import config
from agent_engine.history import file_digest
from agent_engine.runtime import atomic_json


def checkpoint_path(root: Path, agent: str) -> Path:
    return root / (".engine-review-" + agent.replace("/", "-") + ".json")


def snapshot(root: Path, agent: str | None = None) -> dict[str, str]:
    if agent == "task-breakdown":
        return _breakdown_snapshot(root)
    result = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if (rel.parts[0] in {"runs", "logs"} or any(part.startswith(".engine-") for part in rel.parts)
                or rel.as_posix() in {"report.json", "phase4/orchestrator-state.json"}):
            continue
        if p.is_symlink():
            raise ValueError(f"cannot checkpoint symlink: {rel}")
        if p.is_file():
            result[rel.as_posix()] = file_digest(p)
    # Retry must use the same implementation and pack instructions, including helpers.
    for label, directory in (("code", Path(__file__).parent), ("packs", config.AGENTS_DIR)):
        for p in sorted(directory.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
                result[f"{label}:{p.relative_to(directory).as_posix()}"] = file_digest(p)
    if Path(config.GATES_FILE).is_file():
        result["gates:contract"] = file_digest(Path(config.GATES_FILE))
    for name in ("pyproject.toml", "uv.lock"):
        path = config.ENGINE_ROOT / name
        if path.is_file():
            result["dependencies:" + name] = file_digest(path)
    from agent_engine.phase4.settings import get_settings
    catalog = Path(get_settings().phase4_infra_catalog_dir)
    for p in sorted(catalog.rglob("*")):
        if p.is_file():
            result["catalog:" + p.relative_to(catalog).as_posix()] = file_digest(p)
    # Store only a hash, never credentials or environment values.
    settings = {k: v for k, v in os.environ.items() if k.startswith("PHASE4_")}
    result["settings:phase4"] = hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()
    return result


def _breakdown_snapshot(root: Path) -> dict[str, str]:
    """Task Breakdown's read/write dependencies, excluding unrelated stage output.

    Keep project.json byte-exact: verification must judge the current full input,
    even though feature-generation reuse can ignore unrelated scheduling fields.
    """
    result = {}
    names = {"prd.md", "architecture.md", "phase4/project.json", "phase4/history.json",
             "requests/task-breakdown.md", "gates/P4-G1.approved.json"}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if rel.as_posix() not in names and rel.parts[0] not in {"specs", "backlog", ".specify"}:
            continue
        if p.is_symlink():
            raise ValueError(f"cannot checkpoint symlink: {rel}")
        if p.is_file() and not p.name.startswith(".engine-"):
            result[rel.as_posix()] = file_digest(p)
    base = Path(__file__).parent
    common = ("agent.py", "cli.py", "config.py", "runtime.py", "backends.py", "guardrails.py", "locking.py",
              "stage_controls.py", "model_setup.py", "subscription_models.py", "verification_resume.py")
    domain = ("backlog.py", "contracts.py", "files.py", "tools.py", "speckit.py", "speckit_parse.py",
              "feature_documents.py", "feature_jobs.py", "textsim.py", "skills_taxonomy.py")
    for rel in (*common, *("phase4/" + n for n in domain)):
        p = base / rel
        result["code:" + rel] = file_digest(p) if p.is_file() else "missing"
    for label, directory in (("pack", Path(config.AGENTS_DIR) / "task-breakdown"),
                             ("assets", base / "phase4/speckit_assets"),
                             ("taxonomy", base / "phase4/data")):
        for p in sorted(directory.rglob("*")):
            if p.is_file():
                result[label + ":" + p.relative_to(directory).as_posix()] = file_digest(p)
    for label, path in (("gates", Path(config.GATES_FILE)), ("dependencies", config.ENGINE_ROOT / "uv.lock"),
                        ("package", config.ENGINE_ROOT / "pyproject.toml")):
        result[label] = file_digest(path) if path.is_file() else "missing"
    controls = {k: v for k, v in os.environ.items() if
                (k.startswith("SDLC_AGENT_") and not any(s in k for s in ("TOKEN", "KEY", "SECRET", "AUTH", "ACCOUNT")))
                or k.startswith("AGENT_ENGINE_BREAKDOWN_") or k == "AGENT_ENGINE_HELPER_CONCURRENCY"}
    result["settings:effective"] = hashlib.sha256(json.dumps(controls, sort_keys=True).encode()).hexdigest()
    return result


def save(root: Path, agent: str, request: str, job_id: str) -> None:
    atomic_json(checkpoint_path(root, agent), {"version": 2 if agent == "task-breakdown" else 1,
                                             "agent": agent, "request": request,
                                             "job_id": job_id, "snapshot": snapshot(root, agent)})


def validate(root: Path, agent: str, request: str) -> str:
    path = checkpoint_path(root, agent)
    if not path.is_file():
        raise ValueError("no failed-verifier checkpoint; run generation normally")
    data = json.loads(path.read_text(encoding="utf-8"))
    from agent_engine import recovery
    if agent in recovery.DIRECTORIES and data.get("version") == (2 if agent == "task-breakdown" else 1):
        # Migration of retained review checkpoints: code/model changes require a
        # fresh review, not regeneration of byte-identical source/artifacts.
        from agent_engine.agent import load_pack
        pack = load_pack(agent)
        names = set(pack.input_files) | set(pack.output_files) | set(recovery.OPTIONAL.get(agent, ()))
        names.update({pack.requests_file, "phase4/project.json"})
        def generation_identity(values):
            result = {}
            for key, value in values.items():
                if key in names or Path(key).parts[0] in recovery.DIRECTORIES[agent]:
                    result[key] = value
                elif agent == "task-breakdown" and key.startswith("pack:") and not key.startswith("pack:validator/"):
                    result[key] = value
                elif key.startswith("packs:" + agent + "/") and "/validator/" not in key:
                    result[key] = value
            return result
        if (data.get("agent") == agent and data.get("request") == request
                and generation_identity(data.get("snapshot", {})) == generation_identity(snapshot(root, agent))):
            return data["job_id"]
    if (data.get("version") != (2 if agent == "task-breakdown" else 1)
            or data.get("agent") != agent or data.get("request") != request
            or data.get("snapshot") != snapshot(root, agent)):
        raise ValueError("verification checkpoint is stale; inputs, outputs, request or implementation changed")
    return data["job_id"]
