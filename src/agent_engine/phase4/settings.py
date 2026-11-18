"""Phase 4 settings, read from the environment (the engine loads .env at import).

Phase 4 infrastructure settings use a `PHASE4_` prefix; tracker and GitHub
credentials keep their usual names. Read at call time so tests can monkeypatch.
"""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path

from agent_engine import config


def _bool(name: str, default: bool) -> bool:
    value = _env(name, str(default)).lower()
    if value not in {"true", "false", "1", "0", "yes", "no", "on", "off"}:
        raise ValueError(f"{name} must be true or false")
    return value in {"true", "1", "yes", "on"}


def _json_object(name: str) -> dict:
    try:
        value = json.loads(_env(name, "{}"))
    except ValueError as exc:
        raise ValueError(f"{name} must contain a JSON object") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{name} must contain a JSON object")
    return value


@dataclass(frozen=True)
class PipelineSettings:
    project: str
    sprint: int
    publish: bool
    parallel: bool
    auto_approve_for_testing: bool
    diagnostics: bool
    scanner_concurrency: int
    resume: bool = False      # PHASE4_RESUME: reuse saved recovery state; default runs fresh


def get_pipeline_settings() -> PipelineSettings:
    project = _env("PHASE4_PROJECT_NAME")
    if project and not re.fullmatch(r"[a-z0-9][a-z0-9-]*", project):
        raise ValueError("PHASE4_PROJECT_NAME must be an existing project folder name (a-z, 0-9, -)")
    sprint = int(_env("PHASE4_SPRINT_INDEX", "1"))
    scans = int(_env("PHASE4_IAC_CHECK_CONCURRENCY", "2"))
    if sprint < 1 or not 1 <= scans <= 4:
        raise ValueError("PHASE4_SPRINT_INDEX must be >=1 and PHASE4_IAC_CHECK_CONCURRENCY must be 1..4")
    return PipelineSettings(project, sprint, _bool("PHASE4_PUBLISH", True),
                            _bool("PHASE4_PARALLEL_STAGES", True),
                            _bool("PHASE4_AUTO_APPROVE_FOR_TESTING", False),
                            _bool("AGENT_ENGINE_PERF", True), scans, _bool("PHASE4_RESUME", False))


@dataclass(frozen=True)
class JiraOptions:
    concurrency: int
    min_write_interval: float
    timeout: float
    max_retries: int
    issue_type_ids: dict
    create_fields: dict
    story_points_field: str


def get_jira_options() -> JiraOptions:
    workers = int(_env("JIRA_PUBLISH_CONCURRENCY", "4"))
    interval = float(_env("JIRA_MIN_WRITE_INTERVAL_SECONDS", "0.25"))
    timeout = float(_env("JIRA_TIMEOUT_SECONDS", "30"))
    retries = int(_env("JIRA_MAX_RETRIES", "5"))
    if not 1 <= workers <= 16 or not 0 <= interval <= 120 or not 0 < timeout <= 300 or not 0 <= retries <= 10:
        raise ValueError("Jira limits: concurrency 1..16, write interval 0..120, timeout (0,300], retries 0..10")
    if not math.isfinite(interval) or not math.isfinite(timeout):
        raise ValueError("Jira interval and timeout must be finite")
    types, fields = _json_object("JIRA_ISSUE_TYPE_IDS"), _json_object("JIRA_CREATE_FIELDS")
    if set(types) - {"epic", "story", "task"} or any(not isinstance(v, str) or not v.isdigit() for v in types.values()):
        raise ValueError("JIRA_ISSUE_TYPE_IDS maps epic/story/task to string issue type IDs")
    reserved = {"project", "issuetype", "parent", "labels", "summary", "description", "timetracking"}
    if set(fields) - {"epic", "story", "task"} or any(not isinstance(v, dict) or set(v) & reserved for v in fields.values()):
        raise ValueError("JIRA_CREATE_FIELDS maps epic/story/task to extra fields; core issue fields cannot be overridden")
    points = _env("JIRA_STORY_POINTS_FIELD_ID")
    if points and not re.fullmatch(r"customfield_[0-9]+", points):
        raise ValueError("JIRA_STORY_POINTS_FIELD_ID must be customfield_<number>")
    return JiraOptions(workers, interval, timeout, retries, types, fields, points)


def project_overrides(data: dict) -> dict:
    """Apply integration ENV values without rewriting authoritative project input bytes."""
    tracker = dict(data.get("tracker") or {})
    kind = _env("PHASE4_TRACKER")
    if kind:
        if kind not in {"jira", "local", "linear", "github"}:
            raise ValueError("PHASE4_TRACKER must be jira/local/linear/github")
        tracker["kind"] = kind
    for env, key in (("JIRA_BASE_URL", "jira_base_url"), ("JIRA_PROJECT_KEY", "jira_project_key"), ("JIRA_BOARD_ID", "jira_board_id")):
        value = _env(env)
        if env == "JIRA_BASE_URL":
            value = value or _env("JIRA_URL")
        if value:
            tracker[key] = int(value) if key == "jira_board_id" else value
    if tracker.get("kind") == "jira":
        from urllib.parse import urlsplit
        url = urlsplit(tracker.get("jira_base_url") or "")
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("JIRA_BASE_URL must be an HTTPS Jira URL without embedded credentials/query")
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", tracker.get("jira_project_key") or ""):
            raise ValueError("JIRA_PROJECT_KEY must be the Jira project key")
        if int(tracker.get("jira_board_id") or 0) < 1:
            raise ValueError("JIRA_BOARD_ID must be a positive Scrum board ID")
    result = {**data, "tracker": tracker} if tracker else dict(data)
    accounts = _json_object("JIRA_ACCOUNT_MAP")
    if accounts:
        known = {m.get("member_id") for m in data.get("team", [])}
        if set(accounts) - known or any(not isinstance(v, str) or not v.strip() for v in accounts.values()):
            raise ValueError("JIRA_ACCOUNT_MAP must map existing member IDs to nonempty Jira account IDs")
        result["team"] = [{**m, "tracker_account_id": accounts.get(m.get("member_id"), m.get("tracker_account_id"))}
                          for m in data.get("team", [])]
    return result


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass(frozen=True)
class Settings:
    # Work Allocation
    phase4_allocation_solver_url: str
    phase4_allocation_solver_mode: str      # auto | timefold | local
    phase4_allocation_time_limit: str       # ISO-8601 duration for Timefold
    phase4_ai_review_ratio: float
    # Infra & Pipeline
    phase4_infra_catalog_dir: str
    phase4_iac_sandbox_image: str
    phase4_iac_sandbox_mode: str            # auto | off
    phase4_iac_cache_dir: str               # OpenTofu plugin cache shared by every sandbox run
    phase4_terraform_registry_url: str
    # Publishing (after a gate)
    phase4_pr_mode: str                     # local | github
    phase4_output_root: str                 # kept for ported modules; the project folder is used instead
    # Trackers / GitHub / calendars
    jira_email: str
    jira_api_token: str
    linear_api_key: str
    github_token: str
    github_copilot_user_token: str
    google_sa_json: str
    ms_graph_tenant_id: str
    ms_graph_client_id: str
    ms_graph_client_secret: str

    def __post_init__(self):
        if self.phase4_allocation_solver_mode not in ("auto", "timefold", "local"):
            raise ValueError("PHASE4_ALLOCATION_SOLVER_MODE must be auto, timefold or local")
        if self.phase4_iac_sandbox_mode not in ("auto", "off"):
            raise ValueError("PHASE4_IAC_SANDBOX_MODE must be auto or off")
        if self.phase4_pr_mode not in ("local", "github"):
            raise ValueError("PHASE4_PR_MODE must be local or github")
        if not 0 < self.phase4_ai_review_ratio <= 1:
            raise ValueError("PHASE4_AI_REVIEW_RATIO must be > 0 and <= 1")
        if not re.fullmatch(r"PT(?=.+)(?:\d+(?:\.\d+)?H)?(?:\d+(?:\.\d+)?M)?(?:\d+(?:\.\d+)?S)?", self.phase4_allocation_time_limit):
            raise ValueError("PHASE4_ALLOCATION_TIME_LIMIT must be an ISO-8601 time duration, e.g. PT30S")
        if sum(float(n) for n in re.findall(r"\d+(?:\.\d+)?", self.phase4_allocation_time_limit)) <= 0:
            raise ValueError("PHASE4_ALLOCATION_TIME_LIMIT must be positive")


def get_settings() -> Settings:
    return Settings(
        phase4_allocation_solver_url=_env("PHASE4_ALLOCATION_SOLVER_URL", "http://localhost:8080"),
        phase4_allocation_solver_mode=_env("PHASE4_ALLOCATION_SOLVER_MODE", "auto"),
        phase4_allocation_time_limit=_env("PHASE4_ALLOCATION_TIME_LIMIT", "PT30S"),
        phase4_ai_review_ratio=float(_env("PHASE4_AI_REVIEW_RATIO", "0.25")),
        phase4_infra_catalog_dir=_env("PHASE4_INFRA_CATALOG_DIR")
        or str(config.AGENTS_DIR / "infra-pipeline" / "knowledge" / "catalog"),
        phase4_iac_sandbox_image=_env("PHASE4_IAC_SANDBOX_IMAGE", "phase4/iac-sandbox:dev"),
        phase4_iac_sandbox_mode=_env("PHASE4_IAC_SANDBOX_MODE", "auto"),
        phase4_iac_cache_dir=_env("PHASE4_IAC_CACHE_DIR") or str(config.ENGINE_ROOT / ".cache" / "iac"),
        phase4_terraform_registry_url=_env("PHASE4_TERRAFORM_REGISTRY_URL", "https://registry.terraform.io"),
        phase4_pr_mode=_env("PHASE4_PR_MODE", "local"),
        phase4_output_root=str(Path(config.OUTPUTS_DIR)),
        jira_email=_env("JIRA_EMAIL"),
        jira_api_token=_env("JIRA_API_TOKEN"),
        linear_api_key=_env("LINEAR_API_KEY"),
        github_token=_env("GITHUB_TOKEN"),
        github_copilot_user_token=_env("GITHUB_COPILOT_USER_TOKEN"),
        google_sa_json=_env("GOOGLE_SA_JSON"),
        ms_graph_tenant_id=_env("MS_GRAPH_TENANT_ID"),
        ms_graph_client_id=_env("MS_GRAPH_CLIENT_ID"),
        ms_graph_client_secret=_env("MS_GRAPH_CLIENT_SECRET"),
    )
