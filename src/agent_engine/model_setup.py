"""Model resolution and summarization-middleware construction shared by
every agent pack this engine builds — each needs the same retry-raising
model wrapper and the same compaction policy, sized against its own primary
model's real context window.
"""

from __future__ import annotations

import logging
import os

from deepagents.backends.protocol import BackendProtocol
from deepagents.middleware.summarization import SummarizationMiddleware
from deepagents.profiles.provider.provider_profiles import apply_provider_profile
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from agent_engine import subscription_models
from agent_engine.config import (
    COMPACTION_FALLBACK_TOKENS,
    COMPACTION_TRIGGER_FRACTION,
    MODEL_MAX_RETRIES,
    SUMMARIZATION_KEEP_MESSAGES,
    TRUNCATE_ARGS_FALLBACK_TOKENS,
    TRUNCATE_ARGS_KEEP_MESSAGES,
    TRUNCATE_ARGS_MAX_LENGTH,
    TRUNCATE_ARGS_TRIGGER_FRACTION,
    anthropic_subscription_enabled,
    codex_subscription_enabled,
    resolve_model_tiers,
)

logger = logging.getLogger(__name__)


def _is_anthropic_spec(spec: str) -> bool:
    return spec.split(":", 1)[0].strip().lower() == "anthropic"


def _is_openai_spec(spec: str) -> bool:
    return spec.split(":", 1)[0].strip().lower() == "openai"


def _bare_model_id(spec: str) -> str:
    return spec.split(":", 1)[1] if ":" in spec else spec


def _tuning_kwargs(spec: str) -> dict:
    """User tuning from SDLC_AGENT_TEMPERATURE / SDLC_AGENT_EFFORT (set by
    fast_api_generator_backend from Settings > Model Configuration), applied
    to the strong model only — the fast tier keeps provider defaults, since
    not every small model accepts an effort setting. Effort wins over
    temperature: reasoning/thinking modes reject a custom temperature."""
    if spec != os.environ.get("SDLC_AGENT_STRONG_MODEL"):
        return {}
    effort = os.environ.get("SDLC_AGENT_EFFORT", "").strip().lower()
    if effort:
        provider = spec.split(":", 1)[0].strip().lower()
        if provider == "anthropic":
            return {"effort": effort}
        if provider == "openrouter":
            return {"reasoning": {"effort": effort}}
        return {"reasoning_effort": effort}
    temperature = os.environ.get("SDLC_AGENT_TEMPERATURE", "").strip()
    return {"temperature": float(temperature)} if temperature else {}


def describe_model_config() -> str:
    """One-line, secret-free summary of the models and tuning this run uses —
    logged once at run start. `applied` is what the strong model is actually
    built with (effort wins over temperature, see _tuning_kwargs). Never
    raises: a missing credential should fail in the run itself, not here."""
    try:
        tiers = resolve_model_tiers()
        strong, fast, applied = tiers.strong, tiers.fast, _tuning_kwargs(tiers.strong)
    except Exception as exc:
        strong = fast = f"<unresolved: {exc}>"
        applied = {}
    subscription = (_is_anthropic_spec(strong) and anthropic_subscription_enabled()) or (
        _is_openai_spec(strong) and codex_subscription_enabled()
    )
    auth = "subscription" if subscription else "api_key"
    return (
        f"model config: strong={strong} fast={fast} auth={auth} "
        f"effort={os.environ.get('SDLC_AGENT_EFFORT') or 'default'} "
        f"temperature={os.environ.get('SDLC_AGENT_TEMPERATURE') or 'default'} "
        f"applied_to_strong={applied or 'provider defaults'}"
    )


def structured_response_format(spec: str, schema):
    """`response_format` for create_deep_agent. Anthropic always gets native
    structured outputs (ProviderStrategy -> output_config.format) instead of
    langchain's fallback of forcing a tool (`tool_choice: any`), which Claude
    Opus 5.5 / Sonnet 5.5 / Fable 5.1 / Mythos 5.1 reject with a 400. Langchain
    only auto-picks the native path for models whose profile it knows, and the
    5.5 family isn't in it yet. Other providers keep langchain's own choice."""
    from langchain.agents.structured_output import ProviderStrategy

    return ProviderStrategy(schema) if _is_anthropic_spec(spec) else schema


# langchain-anthropic falls back to max_tokens=4096 for a model its installed
# profiles don't know yet (Sonnet/Opus 5.5). Thinking/effort tokens count against
# it and one generated file easily exceeds 4096, so use Haiku 4.5's ceiling.
_UNKNOWN_PROFILE_MAX_TOKENS = 64000


def resolve_model_with_retries(spec: str) -> BaseChatModel:
    model = _build_model(spec)
    if (
        _is_anthropic_spec(spec)
        and hasattr(model, "max_tokens")
        and not (getattr(model, "profile", None) or {}).get("max_output_tokens")
    ):
        model.max_tokens = _UNKNOWN_PROFILE_MAX_TOKENS
    return model


def _build_model(spec: str) -> BaseChatModel:
    """Builds the model object so `max_retries` (config.py) can be raised
    above the client default, via deepagents' `apply_provider_profile` so
    provider-specific defaults (e.g. OpenAI's Responses API) still apply.

    When `SDLC_AGENT_ANTHROPIC_AUTH_MODE=subscription` (Anthropic specs) or
    `SDLC_AGENT_OPENAI_AUTH_MODE=subscription` (OpenAI specs), bypasses
    `init_chat_model`/`apply_provider_profile` entirely and constructs a
    subscription-credential model directly via `subscription_models` — see
    that module for why (billing-marker injection, Codex payload shape).
    """
    if _is_anthropic_spec(spec) and anthropic_subscription_enabled():
        token = os.environ.get("SDLC_AGENT_ANTHROPIC_OAUTH_TOKEN", "").strip()
        if not token:
            raise RuntimeError(
                "SDLC_AGENT_ANTHROPIC_AUTH_MODE=subscription but "
                "SDLC_AGENT_ANTHROPIC_OAUTH_TOKEN is unset/empty."
            )
        return subscription_models.build_anthropic_subscription_llm(
            _bare_model_id(spec), token, max_retries=MODEL_MAX_RETRIES, **_tuning_kwargs(spec),
        )

    if _is_openai_spec(spec) and codex_subscription_enabled():
        token = os.environ.get("SDLC_AGENT_OPENAI_OAUTH_TOKEN", "").strip()
        if not token:
            raise RuntimeError(
                "SDLC_AGENT_OPENAI_AUTH_MODE=subscription but "
                "SDLC_AGENT_OPENAI_OAUTH_TOKEN is unset/empty."
            )
        account_id = os.environ.get("SDLC_AGENT_OPENAI_ACCOUNT_ID", "").strip()
        return subscription_models.build_codex_subscription_llm(
            _bare_model_id(spec), token, account_id, max_retries=MODEL_MAX_RETRIES,  # fixed Codex payload: no tuning
        )

    kwargs = {"max_retries": MODEL_MAX_RETRIES, **_tuning_kwargs(spec)}
    return init_chat_model(spec, **apply_provider_profile(spec, kwargs))


def _token_trigger(primary_model: str, fraction: float) -> tuple[str, int] | None:
    """Absolute token count = `fraction` of `primary_model`'s real context
    window. Deliberately not a `("fraction", ...)` trigger passed straight to
    `SummarizationMiddleware`: that fraction is evaluated against the
    summarizer model, not the primary one — sizing it here against the
    right model's profile and passing an absolute `("tokens", N)` keeps the
    two independent. Returns None if the profile lookup fails.
    """
    try:
        profile = init_chat_model(primary_model).profile
        max_input_tokens = profile.get("max_input_tokens") if profile else None
    except Exception:
        logger.exception("could not resolve model profile for %r", primary_model)
        return None
    if not isinstance(max_input_tokens, int):
        logger.warning(
            "model %r has no max_input_tokens in its profile; falling back to a fixed token trigger",
            primary_model,
        )
        return None
    return ("tokens", int(max_input_tokens * fraction))


def summarization_middleware(
    primary_model: str, summarizer_model: BaseChatModel, backend: BackendProtocol
) -> SummarizationMiddleware:
    """Shared compaction policy for every agent/subagent. `primary_model` is
    a bare spec string (only used to read its profile); `summarizer_model`
    is always the fast model, even when `primary_model` is the strong one —
    otherwise `create_deep_agent` would default to each subagent's own model
    compacting its own transcript.
    """
    trigger = _token_trigger(primary_model, COMPACTION_TRIGGER_FRACTION) or ("tokens", COMPACTION_FALLBACK_TOKENS)
    truncate_trigger = _token_trigger(primary_model, TRUNCATE_ARGS_TRIGGER_FRACTION) or (
        "tokens",
        TRUNCATE_ARGS_FALLBACK_TOKENS,
    )
    return SummarizationMiddleware(
        model=summarizer_model,
        backend=backend,
        trigger=trigger,
        keep=("messages", SUMMARIZATION_KEEP_MESSAGES),
        truncate_args_settings={
            "trigger": truncate_trigger,
            "keep": ("messages", TRUNCATE_ARGS_KEEP_MESSAGES),
            "max_length": TRUNCATE_ARGS_MAX_LENGTH,
        },
    )


__all__ = [
    "describe_model_config", "resolve_model_with_retries", "structured_response_format", "summarization_middleware",
]
