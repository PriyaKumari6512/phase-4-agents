"""Subscription-credential (Claude.ai / ChatGPT-Codex OAuth) model construction.

Ports fast_api_generator_backend's app/core/llm.py::build_anthropic_llm /
build_codex_llm faithfully — every header/payload/Omit() choice below mirrors
that file's own comments and evidence (the billing-marker A/B test, the
Omit()-must-happen-post-construction reasoning, the Codex payload shape).
This is a REIMPLEMENTATION: this package is a separate deployable unit and
cannot import that repo. Do not "simplify" any choice below without
understanding why it's there first — re-read this module's own docstrings.
"""
from __future__ import annotations

import logging

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from . import config

logger = logging.getLogger(__name__)

# ─── Anthropic (Claude.ai subscription) ───────────────────────────────────
# Literal system-prompt TEXT, not a real HTTP header despite reading like one
# — confirmed load-bearing by a live, controlled A/B test in the reference
# repo (present: works; absent: 429s, regardless of token validity).
_ANTHROPIC_BILLING_ATTRIBUTION_TEXT = (
    "x-anthropic-billing-header: cc_version=2.1.263.8bc; cc_entrypoint=cli;"
)


class SubscriptionRateLimited(RuntimeError):
    """Subscription quota exhausted with a reset further away than
    config.SUBSCRIPTION_MAX_RETRY_AFTER_SECONDS. Message starts with a stable
    `SUBSCRIPTION_RATE_LIMITED` token so a watchdog/log scraper can tell it
    apart from a hang."""


def _cap_retry_after(sdk_client) -> None:
    """The anthropic SDK sleeps for whatever `retry-after` the API sends,
    uncapped; a subscription 429 sends the quota reset (up to hours). Wrap the
    client's own backoff calculation to raise instead of sleeping past the cap."""
    original = sdk_client._calculate_retry_timeout
    cap = config.SUBSCRIPTION_MAX_RETRY_AFTER_SECONDS

    def capped(remaining_retries, options, response_headers=None):
        retry_after = sdk_client._parse_retry_after_header(response_headers)
        if retry_after is not None and retry_after > cap:
            raise SubscriptionRateLimited(
                f"SUBSCRIPTION_RATE_LIMITED: Anthropic subscription rate-limited (429), "
                f"resets in {int(retry_after)}s (~{retry_after / 3600:.1f}h); "
                f"not waiting (cap {int(cap)}s)."
            )
        return original(remaining_retries, options, response_headers)

    sdk_client._calculate_retry_timeout = capped


class _SubscriptionChatAnthropic(ChatAnthropic):
    """ChatAnthropic with the billing marker injected as the first block of
    every request's `system` field. `_get_request_payload` is the one place
    langchain-anthropic assembles the outgoing payload — every invoke/
    ainvoke/stream/astream call funnels through it, so this is the single
    seam that covers every agent using this model instance."""

    def _get_request_payload(self, input_, *, stop=None, **kwargs):
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        marker = {"type": "text", "text": _ANTHROPIC_BILLING_ATTRIBUTION_TEXT}
        system = payload.get("system")
        if not system:
            payload["system"] = [marker]
        elif isinstance(system, str):
            payload["system"] = [marker, {"type": "text", "text": system}]
        else:  # already a list of content blocks
            payload["system"] = [marker, *system]
        return payload

    @property
    def _llm_type(self) -> str:
        return "anthropic-subscription-chat"


def build_anthropic_subscription_llm(model_id: str, oauth_token: str, **kwargs) -> ChatAnthropic:
    """`oauth_token` is the raw `sk-ant-oat01-...` setup-token, already
    resolved/validated by the caller (fast_api_generator_backend) — no
    prefix-checking or refresh needed on this side."""
    llm = _SubscriptionChatAnthropic(
        model=model_id,
        # NOT "" — a falsy api_key makes ChatAnthropic fall back to reading
        # ANTHROPIC_API_KEY from the environment, which in this deployment
        # is set to a harmless placeholder (see config.py) rather than a
        # real key — but the placeholder must never actually reach the
        # wire. The SDK never sends this value once X-Api-Key is
        # suppressed below.
        api_key="unused-oauth-bearer",
        default_headers={"Authorization": f"Bearer {oauth_token}"},
        **kwargs,
    )

    from anthropic import Omit

    # default_headers= is pydantic-validated Mapping[str, str] and rejects
    # the Omit() sentinel at construction time — it has to be poked into
    # the already-built client's _custom_headers dict instead. Without
    # this, BOTH X-Api-Key (the placeholder) and the real Authorization
    # header go out on the wire, and it's undefined which one the server
    # honors.
    llm._client._custom_headers["X-Api-Key"] = Omit()
    # ChatAnthropic builds _client/_async_client as two INDEPENDENT cached
    # clients from the same api_key — suppress both. (The reference repo
    # only suppresses the sync one, because every one of its own call
    # sites happens to only ever call .invoke(); this package's agents run
    # through deepagents/LangGraph, which is far more likely to use the
    # async path, so both must be covered here.)
    llm._async_client._custom_headers["X-Api-Key"] = Omit()
    _cap_retry_after(llm._client)
    _cap_retry_after(llm._async_client)

    logger.info("build_anthropic_subscription_llm: model=%r auth=oauth-bearer", model_id)
    return llm


# ─── OpenAI (ChatGPT/Codex subscription) ──────────────────────────────────
CODEX_BASE_URL = "https://chatgpt.com/backend-api/codex"
CODEX_STATIC_MODELS = ("gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.5")
_CODEX_ORIGINATOR = "codex_exec"
_CODEX_USER_AGENT = (
    "codex_exec/0.154.0 (Windows 10.0.26200; x86_64) unknown (codex_exec; 0.154.0)"
)


class _SubscriptionChatOpenAICodex(ChatOpenAI):
    """`ChatOpenAI` targeting the Codex subscription backend. Rewrites what
    Codex requires that has no ChatOpenAI constructor field — everything
    else (base_url, use_responses_api, reasoning/include/verbosity/store)
    is set at construction time in build_codex_subscription_llm below."""

    def _get_request_payload(self, input_, *, stop=None, **kwargs):
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)

        for item in payload.get("input") or []:
            if isinstance(item, dict) and item.get("role") == "system":
                item["role"] = "developer"  # Codex rejects role:"system" outright

        # Not a persistent field on ChatOpenAI (bind_tools()/call-time
        # only) — force it on every payload regardless of how any caller
        # ends up binding tools.
        payload["parallel_tool_calls"] = False

        # Codex 400s on any of these three unconditionally.
        for key in ("max_tokens", "max_completion_tokens", "max_output_tokens"):
            payload.pop(key, None)

        return payload

    @property
    def _llm_type(self) -> str:
        return "openai-codex-chat"


def build_codex_subscription_llm(
    model_id: str, access_token: str, account_id: str = "", **kwargs
) -> ChatOpenAI:
    """`access_token` is already a CURRENT, valid Codex access token — the
    caller (fast_api_generator_backend) refreshes it before this sandbox is
    ever created. `account_id`, when non-empty, becomes the
    `chatgpt-account-id` header (from the credential's own claims)."""
    headers: dict[str, str] = {}
    if account_id:
        headers["chatgpt-account-id"] = account_id
    headers["originator"] = _CODEX_ORIGINATOR
    headers["User-Agent"] = _CODEX_USER_AGENT

    llm = _SubscriptionChatOpenAICodex(
        model=model_id or CODEX_STATIC_MODELS[0],
        api_key=access_token,
        base_url=CODEX_BASE_URL,
        use_responses_api=True,
        streaming=True,  # Codex REQUIRES stream:true server-side
        store=False,     # Codex rejects store:true
        reasoning={"effort": "medium", "context": "all_turns"},
        include=["reasoning.encrypted_content"],
        verbosity="low",
        default_headers=headers,
        **kwargs,
    )

    from openai import Omit

    # x-stainless-* fingerprint headers are absent from real Codex traffic
    # — suppress them, derived from the client's OWN assembled headers
    # (not a hardcoded name list), on both the sync and async clients.
    stainless_keys = [k for k in llm.root_client.default_headers if k.lower().startswith("x-stainless")]
    for key in stainless_keys:
        llm.root_client._custom_headers[key] = Omit()
    if llm.root_async_client is not None:
        for key in stainless_keys:
            llm.root_async_client._custom_headers[key] = Omit()

    logger.info(
        "build_codex_subscription_llm: model=%r account_id_set=%s", model_id, bool(account_id),
    )
    return llm
