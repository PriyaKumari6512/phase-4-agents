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


def snapshot(root: Path) -> dict[str, str]:
    result = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if (rel.parts[0] in {"runs", "logs"} or p.name.startswith(".engine-")
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


def save(root: Path, agent: str, request: str, job_id: str) -> None:
    atomic_json(checkpoint_path(root, agent), {"version": 1, "agent": agent, "request": request,
                                             "job_id": job_id, "snapshot": snapshot(root)})


def validate(root: Path, agent: str, request: str) -> str:
    path = checkpoint_path(root, agent)
    if not path.is_file():
        raise ValueError("no failed-verifier checkpoint; run generation normally")
    data = json.loads(path.read_text(encoding="utf-8"))
    if (data.get("version") != 1 or data.get("agent") != agent or data.get("request") != request
            or data.get("snapshot") != snapshot(root)):
        raise ValueError("verification checkpoint is stale; inputs, outputs, request or implementation changed")
    return data["job_id"]
