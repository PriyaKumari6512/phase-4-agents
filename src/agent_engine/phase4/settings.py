"""Phase 4 settings, read from the environment (the engine loads .env at import).

Phase 4 infrastructure settings use a `PHASE4_` prefix; tracker and GitHub
credentials keep their usual names. Read at call time so tests can monkeypatch.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from agent_engine import config


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
