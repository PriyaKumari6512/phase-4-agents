"""Paths and settings, with env-var overrides.

Engine-only settings use `AGENT_ENGINE_<NAME>`. Model, auth and tuning
settings keep the `SDLC_AGENT_<NAME>` names of the agent-harness repo this
engine was split from, so one .env works for both.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

# src/agent_engine/config.py -> repo root is 2 parents up.
ENGINE_ROOT = Path(__file__).resolve().parents[2]
OUTPUTS_DIR = Path(os.environ.get("AGENT_ENGINE_OUTPUTS_DIR") or ENGINE_ROOT / "outputs")
LOGS_DIR = Path(os.environ.get("AGENT_ENGINE_LOGS_DIR") or ENGINE_ROOT / "logs")
# One folder per agent: agent.toml + system_prompt.md (agent.py).
AGENTS_DIR = Path(os.environ.get("AGENT_ENGINE_AGENTS_DIR") or ENGINE_ROOT / "agents")
# Human approval gates: which project files each gate approves (gates.py).
GATES_FILE = Path(os.environ.get("AGENT_ENGINE_GATES_FILE") or ENGINE_ROOT / "gates.toml")

# Used when ANTHROPIC_API_KEY is set.
ANTHROPIC_STRONG_MODEL = "anthropic:claude-sonnet-5-5"
ANTHROPIC_FAST_MODEL = "anthropic:claude-haiku-4-5-20251001"

# OpenAI fallback IDs — drift faster than Anthropic's; override via env if superseded.
OPENAI_STRONG_MODEL = "openai:gpt-5.6-terra"
OPENAI_FAST_MODEL = "openai:gpt-5.6-luna"

# Used when OPENROUTER_API_KEY is set (checked after the two above).
OPENROUTER_STRONG_MODEL = "openrouter:nvidia/nemotron-3.5-lightning:free"
OPENROUTER_FAST_MODEL = "openrouter:nvidia/nemotron-3.5-lightning:free"


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    return int(value) if value else default


def _env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    return float(value) if value else default


def _env_str(name: str, default: str) -> str:
    return os.environ.get(name) or default


@dataclass(frozen=True)
class ModelTiers:
    """`strong` for the real work, `fast` for cheap subtasks (summarization)."""

    strong: str
    fast: str


# --- Anthropic auth mode -------------------------------------------------------
# "api_key" (default): ANTHROPIC_API_KEY. "subscription": a Claude.ai
# subscription OAuth credential instead (subscription_models.py).
ANTHROPIC_AUTH_MODE_API_KEY = "api_key"
ANTHROPIC_AUTH_MODE_SUBSCRIPTION = "subscription"
ANTHROPIC_AUTH_MODE = _env_str("SDLC_AGENT_ANTHROPIC_AUTH_MODE", ANTHROPIC_AUTH_MODE_API_KEY)


def anthropic_subscription_enabled() -> bool:
    return ANTHROPIC_AUTH_MODE.strip().lower() == ANTHROPIC_AUTH_MODE_SUBSCRIPTION


# --- OpenAI/Codex auth mode -----------------------------------------------------
OPENAI_AUTH_MODE_API_KEY = "api_key"
OPENAI_AUTH_MODE_SUBSCRIPTION = "subscription"
OPENAI_AUTH_MODE = _env_str("SDLC_AGENT_OPENAI_AUTH_MODE", OPENAI_AUTH_MODE_API_KEY)


def codex_subscription_enabled() -> bool:
    return OPENAI_AUTH_MODE.strip().lower() == OPENAI_AUTH_MODE_SUBSCRIPTION


def resolve_model_tiers() -> ModelTiers:
    strong_override = os.environ.get("SDLC_AGENT_STRONG_MODEL")
    fast_override = os.environ.get("SDLC_AGENT_FAST_MODEL")
    if strong_override and fast_override:
        return ModelTiers(strong=strong_override, fast=fast_override)

    if os.environ.get("ANTHROPIC_API_KEY"):
        strong, fast = ANTHROPIC_STRONG_MODEL, ANTHROPIC_FAST_MODEL
    elif os.environ.get("OPENAI_API_KEY"):
        strong, fast = OPENAI_STRONG_MODEL, OPENAI_FAST_MODEL
    elif os.environ.get("OPENROUTER_API_KEY"):
        strong, fast = OPENROUTER_STRONG_MODEL, OPENROUTER_FAST_MODEL
    else:
        raise RuntimeError(
            "No model provider credentials found. Set ANTHROPIC_API_KEY, "
            "OPENAI_API_KEY, or OPENROUTER_API_KEY (or set SDLC_AGENT_STRONG_MODEL / "
            "SDLC_AGENT_FAST_MODEL explicitly for a different provider)."
        )

    return ModelTiers(strong=strong_override or strong, fast=fast_override or fast)


# --- Virtual paths ---------------------------------------------------------------
# The agent only ever sees these prefixes, never a real host path (backends.py).
OUTPUTS_VIRTUAL_PREFIX = "/outputs/"
KNOWLEDGE_VIRTUAL_ROOT = "/knowledge/"
# A pack's `skills` folder (Agent Skills: one SKILL.md per sub-folder), read-only.
SKILLS_VIRTUAL_ROOT = "/skills/"
# Every request made for a project, oldest first: the agent and its verifier
# both read it, so a feedback run never loses the original requirement.
REQUESTS_FILENAME = "requests.md"
# A pack with `request_history = "agent"` keeps its own history instead, in
# requests/<agent>.md, so other agents' requests on the project don't reach it.
REQUESTS_DIRNAME = "requests"
# runs/<job-id>/: one folder per run, holding its report.json and a copy of
# every project file the run created or changed (history.py).
RUNS_DIRNAME = "runs"
REPORT_FILENAME = "report.json"

# --- Logging ------------------------------------------------------------------
APP_LOGGER_NAME = "agent_engine"
TRANSCRIPT_LOGGER_NAME = "deepagent.transcript"
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
APP_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s job=%(job_id)s: %(message)s"
DEFAULT_LOG_LEVEL = _env_int("AGENT_ENGINE_LOG_LEVEL", logging.INFO)
APP_LOG_FILENAME = "app.log"
DEEPAGENT_LOG_FILENAME = "deepagent.log"
JOB_LOGS_SUBDIR_NAME = "jobs"
PROJECT_LOGS_SUBDIR_NAME = "logs"
JOB_ID_TIME_FORMAT = "%Y%m%d-%H%M%S"
JOB_ID_RANDOM_SUFFIX_LENGTH = 6

# --- Model retries / context-compaction budget --------------------------------
# Raises the retry ceiling above LangChain's default (2), a thin buffer
# against a transient model-provider connection error crashing the job.
MODEL_MAX_RETRIES = _env_int("SDLC_AGENT_MODEL_MAX_RETRIES", 6)
# Longest server-requested `retry-after` (seconds) a subscription-auth model
# call will sleep through; beyond this the call fails fast instead of hanging.
SUBSCRIPTION_MAX_RETRY_AFTER_SECONDS = _env_float("SDLC_AGENT_SUBSCRIPTION_MAX_RETRY_AFTER_SECONDS", 60.0)

# Truncation fires before compaction, as a lighter first intervention.
COMPACTION_TRIGGER_FRACTION = _env_float("SDLC_AGENT_COMPACTION_TRIGGER_FRACTION", 0.30)
TRUNCATE_ARGS_TRIGGER_FRACTION = _env_float("SDLC_AGENT_TRUNCATE_ARGS_TRIGGER_FRACTION", 0.20)
# Fallback absolute token budgets, used only if a model's profile lookup fails.
COMPACTION_FALLBACK_TOKENS = _env_int("SDLC_AGENT_COMPACTION_FALLBACK_TOKENS", 100_000)
TRUNCATE_ARGS_FALLBACK_TOKENS = _env_int("SDLC_AGENT_TRUNCATE_ARGS_FALLBACK_TOKENS", 60_000)
SUMMARIZATION_KEEP_MESSAGES = _env_int("SDLC_AGENT_SUMMARIZATION_KEEP_MESSAGES", 20)
TRUNCATE_ARGS_KEEP_MESSAGES = _env_int("SDLC_AGENT_TRUNCATE_ARGS_KEEP_MESSAGES", 10)
TRUNCATE_ARGS_MAX_LENGTH = _env_int("SDLC_AGENT_TRUNCATE_ARGS_MAX_LENGTH", 500)

# --- Filesystem guard / locking -----------------------------------------------
# Every filesystem tool a pack may list. No `execute`: the backend has no shell.
FILESYSTEM_TOOLS = frozenset({"ls", "read_file", "write_file", "edit_file", "glob", "grep"})
# The only tools that can mutate disk — shared by guardrails.py and locking.py.
MUTATING_FILESYSTEM_TOOLS = frozenset({"write_file", "edit_file", "delete"})
# Folders inside a project that agents may read but never write: uploaded
# client files (inputs/), human gate decisions (gates/), per-agent request
# histories (requests/) and run history (runs/), all written by the engine.
INPUTS_DIRNAME = "inputs"
GATES_DIRNAME = "gates"
READ_ONLY_PROJECT_DIRS = frozenset({INPUTS_DIRNAME, GATES_DIRNAME, REQUESTS_DIRNAME, RUNS_DIRNAME})
# inputs/round-1/, inputs/round-2/, ...: one folder per batch of client files.
INPUT_ROUND_PREFIX = "round-"
# Rows per sheet kept when an Excel file is converted to Markdown.
XLSX_MAX_ROWS_PER_SHEET = _env_int("AGENT_ENGINE_XLSX_MAX_ROWS_PER_SHEET", 2000)
FILE_LOCK_ACQUIRE_TIMEOUT_SECONDS = _env_int("AGENT_ENGINE_FILE_LOCK_TIMEOUT_SECONDS", 120)

# --- Observability ----------------------------------------------------------------
LANGFUSE_HOST_DEFAULT = "http://localhost:3000"
