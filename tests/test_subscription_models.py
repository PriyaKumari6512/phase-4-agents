"""Regression guard for the subscription-credential (Claude.ai / ChatGPT-Codex
OAuth) model construction in `subscription_models.py` and its seam in
`model_setup.resolve_model_with_retries`.

Scoped narrowly per this repo's own testing convention (no test suite
otherwise) — only the fragile, evidence-backed logic gets a regression guard
here: the billing-marker injection, the Codex payload rewrite, and the
auth-mode branch dispatch. Everything is pure/no-network.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from agent_engine import config, model_setup, subscription_models


# --- 1. Anthropic billing-marker injection -----------------------------------


def _make_anthropic_subscription_llm() -> subscription_models._SubscriptionChatAnthropic:
    return subscription_models._SubscriptionChatAnthropic(model="claude-sonnet-5", api_key="fake-key")


def test_anthropic_billing_marker_prepended_when_system_absent():
    llm = _make_anthropic_subscription_llm()
    with patch.object(ChatAnthropic, "_get_request_payload", return_value={"model": "claude-sonnet-5"}):
        payload = llm._get_request_payload([{"role": "user", "content": "hi"}])
    assert payload["system"] == [
        {"type": "text", "text": subscription_models._ANTHROPIC_BILLING_ATTRIBUTION_TEXT}
    ]


def test_anthropic_billing_marker_prepended_when_system_is_string():
    llm = _make_anthropic_subscription_llm()
    with patch.object(
        ChatAnthropic, "_get_request_payload", return_value={"model": "claude-sonnet-5", "system": "be helpful"}
    ):
        payload = llm._get_request_payload([{"role": "user", "content": "hi"}])
    assert payload["system"] == [
        {"type": "text", "text": subscription_models._ANTHROPIC_BILLING_ATTRIBUTION_TEXT},
        {"type": "text", "text": "be helpful"},
    ]


def test_anthropic_billing_marker_prepended_when_system_is_block_list():
    original_blocks = [{"type": "text", "text": "block one"}, {"type": "text", "text": "block two"}]
    llm = _make_anthropic_subscription_llm()
    with patch.object(
        ChatAnthropic,
        "_get_request_payload",
        return_value={"model": "claude-sonnet-5", "system": list(original_blocks)},
    ):
        payload = llm._get_request_payload([{"role": "user", "content": "hi"}])
    assert payload["system"] == [
        {"type": "text", "text": subscription_models._ANTHROPIC_BILLING_ATTRIBUTION_TEXT},
        *original_blocks,
    ]


# --- 2. Codex payload rewrite -------------------------------------------------


def _make_codex_llm() -> subscription_models._SubscriptionChatOpenAICodex:
    return subscription_models._SubscriptionChatOpenAICodex(model="gpt-5.6-terra", api_key="fake-token")


def test_codex_payload_rewrites_system_role_and_strips_token_limit_fields():
    synthetic_payload = {
        "model": "gpt-5.6-terra",
        "input": [
            {"role": "system", "content": "be helpful", "type": "message"},
            {"role": "user", "content": "hi", "type": "message"},
        ],
        "max_tokens": 100,
        "max_completion_tokens": 100,
        "max_output_tokens": 100,
        "parallel_tool_calls": True,
    }
    llm = _make_codex_llm()
    with patch.object(ChatOpenAI, "_get_request_payload", return_value=synthetic_payload):
        payload = llm._get_request_payload([{"role": "user", "content": "hi"}])

    assert payload["input"][0]["role"] == "developer"
    assert payload["input"][1]["role"] == "user"
    assert payload["parallel_tool_calls"] is False
    assert "max_tokens" not in payload
    assert "max_completion_tokens" not in payload
    assert "max_output_tokens" not in payload


# --- 3. resolve_model_with_retries auth-mode dispatch -------------------------


def test_resolve_model_with_retries_returns_anthropic_subscription_instance(monkeypatch):
    # ANTHROPIC_AUTH_MODE/OPENAI_AUTH_MODE are read from the env once at
    # config.py's own import time (matching the pre-existing
    # ANTHROPIC_AUTH_MODE scaffold's design) — monkeypatch.setenv after
    # import has no effect on them, so the module-level constant itself is
    # patched instead. SDLC_AGENT_*_OAUTH_TOKEN, in contrast, is read via
    # os.environ.get() at call time inside resolve_model_with_retries, so
    # monkeypatch.setenv works for those.
    monkeypatch.setattr(config, "ANTHROPIC_AUTH_MODE", config.ANTHROPIC_AUTH_MODE_SUBSCRIPTION)
    monkeypatch.setenv("SDLC_AGENT_ANTHROPIC_OAUTH_TOKEN", "sk-ant-oat01-faketoken")
    llm = model_setup.resolve_model_with_retries("anthropic:claude-sonnet-5")
    assert isinstance(llm, subscription_models._SubscriptionChatAnthropic)


def test_resolve_model_with_retries_returns_codex_subscription_instance(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_AUTH_MODE", config.OPENAI_AUTH_MODE_SUBSCRIPTION)
    monkeypatch.setenv("SDLC_AGENT_OPENAI_OAUTH_TOKEN", "fake-access-token")
    llm = model_setup.resolve_model_with_retries("openai:gpt-5.6-terra")
    assert isinstance(llm, subscription_models._SubscriptionChatOpenAICodex)


def test_resolve_model_with_retries_raises_when_anthropic_token_missing(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_AUTH_MODE", config.ANTHROPIC_AUTH_MODE_SUBSCRIPTION)
    monkeypatch.delenv("SDLC_AGENT_ANTHROPIC_OAUTH_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="SDLC_AGENT_ANTHROPIC_OAUTH_TOKEN"):
        model_setup.resolve_model_with_retries("anthropic:claude-sonnet-5")


def test_resolve_model_with_retries_raises_when_openai_token_missing(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_AUTH_MODE", config.OPENAI_AUTH_MODE_SUBSCRIPTION)
    monkeypatch.delenv("SDLC_AGENT_OPENAI_OAUTH_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="SDLC_AGENT_OPENAI_OAUTH_TOKEN"):
        model_setup.resolve_model_with_retries("openai:gpt-5.6-terra")


# --- 4. Regression guard: plain api_key path is untouched ---------------------


def test_resolve_model_with_retries_uses_init_chat_model_when_no_subscription_mode(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_AUTH_MODE", config.ANTHROPIC_AUTH_MODE_API_KEY)
    monkeypatch.setattr(config, "OPENAI_AUTH_MODE", config.OPENAI_AUTH_MODE_API_KEY)
    sentinel = object()
    with patch.object(model_setup, "init_chat_model", return_value=sentinel) as mock_init:
        result = model_setup.resolve_model_with_retries("anthropic:claude-sonnet-5")
    assert result is sentinel
    mock_init.assert_called_once()
    assert mock_init.call_args[0][0] == "anthropic:claude-sonnet-5"
    assert mock_init.call_args[1]["max_retries"] == model_setup.MODEL_MAX_RETRIES
