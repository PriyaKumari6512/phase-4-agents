"""Benchmark provenance: what ran, on what inputs, with which settings — one JSON file per diagnostic
execution in <session>/manifests/.

Configuration comes from an explicit allowlist (``SAFE_SETTINGS``). Credentials are recorded only as
set/unset; URLs only as scheme://host[:port]. The process environment is never dumped and .env is never read
or copied. Inputs are recorded as digests and sizes, not contents.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from importlib import metadata
from pathlib import Path

from agent_engine import config, perf

# Non-secret settings that change what a run does or how long it takes.
SAFE_SETTINGS = (
    "SDLC_AGENT_STRONG_MODEL", "SDLC_AGENT_FAST_MODEL", "SDLC_AGENT_ANTHROPIC_AUTH_MODE", "SDLC_AGENT_OPENAI_AUTH_MODE",
    "SDLC_AGENT_EFFORT", "SDLC_AGENT_TEMPERATURE", "SDLC_AGENT_MODEL_MAX_RETRIES",
    "SDLC_AGENT_SUBSCRIPTION_MAX_RETRY_AFTER_SECONDS", "SDLC_AGENT_COMPACTION_TRIGGER_FRACTION",
    "SDLC_AGENT_TRUNCATE_ARGS_TRIGGER_FRACTION", "SDLC_AGENT_COMPACTION_FALLBACK_TOKENS",
    "SDLC_AGENT_TRUNCATE_ARGS_FALLBACK_TOKENS", "SDLC_AGENT_SUMMARIZATION_KEEP_MESSAGES",
    "SDLC_AGENT_TRUNCATE_ARGS_KEEP_MESSAGES", "SDLC_AGENT_TRUNCATE_ARGS_MAX_LENGTH",
    "PHASE4_ALLOCATION_SOLVER_MODE", "PHASE4_ALLOCATION_TIME_LIMIT", "PHASE4_AI_REVIEW_RATIO",
    "PHASE4_IAC_SANDBOX_IMAGE", "PHASE4_IAC_SANDBOX_MODE", "PHASE4_PR_MODE",
    "AGENT_ENGINE_LOG_LEVEL", "AGENT_ENGINE_FILE_LOCK_TIMEOUT_SECONDS",
    perf.ENV_SESSION, perf.ENV_SAMPLE_SECONDS, perf.ENV_RAW, perf.ENV_MODE,
)
# Only scheme://host:port of these is kept (no user info, path or query).
SAFE_URL_SETTINGS = ("PHASE4_ALLOCATION_SOLVER_URL", "PHASE4_TERRAFORM_REGISTRY_URL", "LANGFUSE_HOST")
# Recorded as "set" / "unset" only.
PRESENCE_ONLY = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY", "SDLC_AGENT_ANTHROPIC_OAUTH_TOKEN",
                 "SDLC_AGENT_OPENAI_OAUTH_TOKEN", "LANGFUSE_PUBLIC_KEY", "JIRA_API_TOKEN", "LINEAR_API_KEY",
                 "GITHUB_TOKEN", "GITHUB_COPILOT_USER_TOKEN", "GOOGLE_SA_JSON", "MS_GRAPH_CLIENT_ID")
PACKAGES = ("deepagents", "langchain", "langchain-core", "langchain-anthropic", "langchain-openai", "langgraph",
            "anthropic", "openai", "httpx", "ortools", "numpy", "networkx", "pydantic", "jinja2", "langfuse")
PROJECT_INPUTS = ("prd.md", "architecture.md", "phase4/project.json", "phase4/history.json",
                  "phase4/skill-profiles.json", "phase4/agent-outcomes.json")


def _sha_file(path: Path) -> str | None:
    try:
        return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def tree_digest(root: Path) -> dict:
    """One digest over every file (relative path + content) under root, with file count and bytes."""
    if not root.is_dir():
        return {"exists": False}
    h, count, size = hashlib.sha256(), 0, 0
    for p in sorted((x for x in root.rglob("*") if x.is_file() and "__pycache__" not in x.parts),
                    key=lambda p: p.relative_to(root).as_posix()):
        data = p.read_bytes()
        h.update(p.relative_to(root).as_posix().encode() + b"\0" + hashlib.sha256(data).digest())
        count, size = count + 1, size + len(data)
    return {"sha256": h.hexdigest(), "files": count, "bytes": size}


def _git(*args: str) -> str | None:
    if not shutil.which("git"):
        return None
    try:
        r = subprocess.run(["git", *args], cwd=config.ENGINE_ROOT, capture_output=True, text=True, timeout=20,
                           encoding="utf-8", errors="replace")
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:  # noqa: BLE001
        return None


def source_identity() -> dict:
    """The revision that ran, and the identity of any uncommitted change on top of it."""
    head = _git("rev-parse", "HEAD")
    diff = _git("diff", "HEAD", "--binary")
    untracked = _git("ls-files", "--others", "--exclude-standard")
    return {
        "head": head, "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "merge_base_main": _git("merge-base", "HEAD", "main"),
        "dirty": bool(diff) or bool(untracked),
        "diff_sha256": hashlib.sha256(diff.encode()).hexdigest() if diff else None,
        "untracked_files": len(untracked.splitlines()) if untracked else 0,
        "untracked_list_sha256": hashlib.sha256(untracked.encode()).hexdigest() if untracked else None,
    }


def safe_settings() -> dict:
    out: dict = {k: os.environ.get(k) for k in SAFE_SETTINGS if os.environ.get(k) not in (None, "")}
    for k in SAFE_URL_SETTINGS:
        raw = os.environ.get(k)
        if raw:
            try:
                import httpx

                u = httpx.URL(raw)
                out[k] = f"{u.scheme}://{u.host}" + (f":{u.port}" if u.port else "")
            except Exception:  # noqa: BLE001
                out[k] = "set (unparseable)"
    out["presence"] = {k: ("set" if os.environ.get(k) else "unset") for k in PRESENCE_ONLY}
    return out


def model_metadata() -> dict:
    from agent_engine.model_setup import describe_model_config

    try:
        tiers = config.resolve_model_tiers()
        strong, fast = tiers.strong, tiers.fast
    except Exception as exc:  # noqa: BLE001
        strong = fast = f"<unresolved: {type(exc).__name__}>"
    return {"strong": strong, "fast": fast, "anthropic_auth_mode": config.ANTHROPIC_AUTH_MODE,
            "openai_auth_mode": config.OPENAI_AUTH_MODE, "model_max_retries": config.MODEL_MAX_RETRIES,
            "describe": perf.redact(describe_model_config())}


def _default(fn, name: str):
    try:
        return inspect.signature(fn).parameters[name].default
    except Exception:  # noqa: BLE001
        return None


def solver_settings() -> dict:
    from agent_engine.phase4 import alloc_solver, capacity, sprint, sprint_model
    from agent_engine.phase4.settings import get_settings

    s = get_settings()
    return {
        "sprint_main": {"time_limit_s": _default(sprint.solve, "time_limit_s"),
                        "workers": _default(sprint_model.solve, "workers")},
        "sprint_core_extraction": {"time_limit_s": "same as main", "workers": 1},
        "sprint_candidates": {"time_limit_s": _default(sprint_model.verified_options, "time_limit_s"),
                              "workers": _default(sprint_model.solve, "workers"), "max_options": 4},
        "capacity_monte_carlo": {"samples": capacity.SAMPLES, "seed": _default(capacity.fill_capacity, "seed")},
        "forecast": {"seed": _default(capacity.forecast, "seed"), "runs": 2000},
        "allocation": {"mode": s.phase4_allocation_solver_mode, "timefold_spent_limit": s.phase4_allocation_time_limit,
                       "timefold_poll_interval_s": 2, "timefold_deadline_s": "configured spent limit + 30s, checked per request",
                       "local_time_limit_s": _default(alloc_solver.solve_local, "time_limit_s"), "local_workers": 8},
    }


def project_inputs(project: str | None) -> dict:
    if not project:
        return {}
    root = Path(config.OUTPUTS_DIR) / project
    if not root.is_dir():
        return {"exists": False}
    out: dict = {"files": {}, "approvals": {}, "areas": {}}
    for rel in PROJECT_INPUTS:
        p = root / rel
        if p.is_file():
            out["files"][rel] = {"sha256": _sha_file(p), "bytes": p.stat().st_size}
    gates = root / "gates"
    if gates.is_dir():
        for p in sorted(gates.glob("*.approved.json")):
            out["approvals"][p.name] = _sha_file(p)
    for child in sorted(root.iterdir()):
        if child.is_dir():
            files = [p for p in child.rglob("*") if p.is_file()]
            out["areas"][child.name] = {"files": len(files), "bytes": sum(p.stat().st_size for p in files)}
    return out


def cache_observations() -> dict:
    from agent_engine.phase4.settings import get_settings

    s = get_settings()
    local = Path(s.phase4_iac_cache_dir) / "tofu-plugins"
    obs: dict = {"local_tofu_plugin_cache": tree_digest(local) if local.is_dir() else {"exists": False},
                 "docker_cli": bool(shutil.which("docker"))}
    if obs["docker_cli"]:
        try:
            r = subprocess.run(["docker", "volume", "inspect", "phase4-tofu-plugin-cache", "--format", "{{.CreatedAt}}"],
                               capture_output=True, text=True, timeout=15)
            obs["docker_plugin_cache_volume"] = "exists" if r.returncode == 0 else "absent or docker unavailable"
        except Exception as exc:  # noqa: BLE001
            obs["docker_plugin_cache_volume"] = f"not inspected ({type(exc).__name__})"
    obs["note"] = ("A cache that exists is not proof that every provider/module a run needs is in it; downloads during "
                   "a run show up as tofu init time in the command spans.")
    return obs


def build(kind: str, ident: str, *, project: str | None = None, packs: list[str] | None = None,
          execution_mode: str = "generation_only", extra: dict | None = None, light: bool = False) -> dict:
    """`light`: a stage child under an orchestrator skips what its pipeline manifest already holds and what
    costs subprocesses (git, docker): about 0.3 s per stage on the development machine."""
    agents_dir = Path(config.AGENTS_DIR)
    from agent_engine.phase4.settings import get_settings

    catalog = Path(get_settings().phase4_infra_catalog_dir)
    manifest = {
        "kind": kind, "id": ident, **perf.ids(), "created_at": perf.utc_iso(),
        "execution_mode": execution_mode, "light": light,
        "packs": {name: tree_digest(agents_dir / name) for name in (packs or [])},
        "models": model_metadata(),
        "settings": safe_settings(),
        "planning": {"utc_date": time.strftime("%Y-%m-%d", time.gmtime()), "local_timezone": time.tzname,
                     "note": "sprint tools default as_of to the UTC date unless the agent passes one"},
        "project_inputs": project_inputs(project),
        "diagnostics": {"dir": str(perf.resolve_dir()), "raw_output": perf._S.raw_output,
                        "sample_seconds": os.environ.get(perf.ENV_SAMPLE_SECONDS) or perf.DEFAULT_SAMPLE_SECONDS},
    }
    if not light:
        manifest.update({
            "source": source_identity(),
            "lockfile_sha256": _sha_file(config.ENGINE_ROOT / "uv.lock"),
            "python": sys.version.split()[0], "platform": platform.platform(),
            "packages": {p: _version(p) for p in PACKAGES},
            "gates_toml": _sha_file(Path(config.GATES_FILE)),
            "catalog": tree_digest(catalog), "policies": tree_digest(catalog / "policies"),
            "solvers": solver_settings(),
            "caches": cache_observations(),
        })
    manifest.update(extra or {})
    return manifest


def _version(dist: str) -> str | None:
    try:
        return metadata.version(dist)
    except metadata.PackageNotFoundError:
        return None


def write(kind: str, ident: str, **kwargs) -> str | None:
    """Builds and writes the manifest; returns its path relative to the session folder. Never raises."""
    d = perf.session_dir()
    if d is None:
        return None
    with perf.span("diagnostics", "manifest", manifest_kind=kind) as sp:
        try:
            data = build(kind, ident, **kwargs)
            rel = f"manifests/{kind}-{ident}.json"
            (d / "manifests").mkdir(parents=True, exist_ok=True)
            (d / rel).write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
            sp.set(path=rel)
            return rel
        except Exception as exc:  # noqa: BLE001
            perf._mark_incomplete(f"manifest {kind}-{ident} not written: {perf.error_summary(exc)}")
            sp.set_status("error", perf.error_summary(exc), perf.classify_error(exc))
            return None
