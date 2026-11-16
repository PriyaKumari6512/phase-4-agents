"""SDLC_AGENT_TEMPERATURE / SDLC_AGENT_EFFORT reach the strong model only,
in each provider's own kwarg shape."""
import pytest

from agent_engine import config
from agent_engine.model_setup import _tuning_kwargs


@pytest.mark.parametrize("spec,expected", [
    ("anthropic:claude-sonnet-5-5", {"effort": "high"}),
    ("openai:gpt-5.6-terra", {"reasoning_effort": "high"}),
    ("openrouter:anthropic/claude-sonnet-5.5", {"reasoning": {"effort": "high"}}),
])
def test_effort_maps_per_provider_and_wins_over_temperature(monkeypatch, spec, expected):
    monkeypatch.setenv("SDLC_AGENT_STRONG_MODEL", spec)
    monkeypatch.setenv("SDLC_AGENT_EFFORT", "high")
    monkeypatch.setenv("SDLC_AGENT_TEMPERATURE", "0.3")
    assert _tuning_kwargs(spec) == expected


def test_temperature_when_no_effort(monkeypatch):
    monkeypatch.setenv("SDLC_AGENT_STRONG_MODEL", "openai:gpt-4.1")
    monkeypatch.delenv("SDLC_AGENT_EFFORT", raising=False)
    monkeypatch.setenv("SDLC_AGENT_TEMPERATURE", "0.3")
    assert _tuning_kwargs("openai:gpt-4.1") == {"temperature": 0.3}


def test_fast_model_and_unset_env_get_nothing(monkeypatch):
    monkeypatch.setenv("SDLC_AGENT_STRONG_MODEL", "openai:gpt-5.6-terra")
    monkeypatch.setenv("SDLC_AGENT_EFFORT", "high")
    assert _tuning_kwargs("openai:gpt-5.6-luna") == {}
    monkeypatch.delenv("SDLC_AGENT_EFFORT")
    monkeypatch.delenv("SDLC_AGENT_TEMPERATURE", raising=False)
    assert _tuning_kwargs("openai:gpt-5.6-terra") == {}


def test_describe_model_config_shows_tuning_without_secrets(monkeypatch):
    from agent_engine.model_setup import describe_model_config

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-secret-value")
    monkeypatch.setenv("SDLC_AGENT_STRONG_MODEL", "anthropic:claude-sonnet-4-6")
    monkeypatch.setenv("SDLC_AGENT_FAST_MODEL", "anthropic:claude-haiku-4-5-20251001")
    monkeypatch.setenv("SDLC_AGENT_EFFORT", "medium")
    monkeypatch.delenv("SDLC_AGENT_TEMPERATURE", raising=False)
    line = describe_model_config()
    assert "strong=anthropic:claude-sonnet-4-6" in line and "fast=anthropic:claude-haiku-4-5-20251001" in line
    assert "effort=medium" in line and "temperature=default" in line
    assert "applied_to_strong={'effort': 'medium'}" in line
    assert "secret" not in line


def test_anthropic_structured_output_is_native_not_forced_tool(monkeypatch):
    """Sonnet 5.5 isn't in langchain's model profiles, so without an explicit
    ProviderStrategy it would fall back to forcing a tool (tool_choice any),
    which that model rejects with a 400."""
    from langchain.agents.structured_output import ProviderStrategy
    from pydantic import BaseModel

    from agent_engine.model_setup import structured_response_format

    class Out(BaseModel):
        a: str

    assert isinstance(structured_response_format("anthropic:claude-sonnet-5-5", Out), ProviderStrategy)
    assert structured_response_format("openai:gpt-5.6-terra", Out) is Out


def test_unknown_anthropic_model_gets_a_real_max_tokens(monkeypatch):
    from agent_engine.model_setup import resolve_model_with_retries

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
    assert resolve_model_with_retries("anthropic:claude-sonnet-5-5").max_tokens == 64000  # not in profiles: was 4096
    assert resolve_model_with_retries("anthropic:claude-sonnet-5").max_tokens == 128000   # profile wins


@pytest.mark.parametrize("spec", [config.ANTHROPIC_STRONG_MODEL, config.ANTHROPIC_FAST_MODEL])
def test_default_anthropic_model_ids_are_api_ids(spec):
    # The API names versions with hyphens: "claude-sonnet-5.5" is a 404.
    assert spec.startswith("anthropic:claude-") and "." not in spec
