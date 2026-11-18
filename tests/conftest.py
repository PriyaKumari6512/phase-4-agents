"""Shared test isolation.

`import agent_engine` loads the repository `.env` into the process environment. Without this fixture a developer's
real tracker settings (PHASE4_TRACKER=jira, JIRA_*, ...) leak into every test, and a test that publishes would talk
to the live tracker. Tests that need these values set them explicitly with monkeypatch.
"""
from __future__ import annotations

import os

import pytest

_LIVE_INTEGRATION_PREFIXES = ("JIRA_", "LINEAR_", "PHASE4_TRACKER", "PHASE4_PROJECT_NAME", "PHASE4_PUBLISH",
                              "PHASE4_AUTO_APPROVE_FOR_TESTING", "PHASE4_PR_MODE", "GITHUB_TOKEN",
                              "GITHUB_COPILOT_USER_TOKEN")


@pytest.fixture(autouse=True)
def _no_live_integrations(monkeypatch):
    for name in list(os.environ):
        if name.startswith(_LIVE_INTEGRATION_PREFIXES):
            monkeypatch.delenv(name, raising=False)
    # Model-name resolution must also work on a clean machine without credentials.
    # Calls remain fake; these are names, never authentication material.
    from agent_engine import config
    for name, default in (("SDLC_AGENT_STRONG_MODEL", config.ANTHROPIC_STRONG_MODEL),
                          ("SDLC_AGENT_FAST_MODEL", config.ANTHROPIC_FAST_MODEL)):
        if not os.environ.get(name):
            monkeypatch.setenv(name, default)
    # Real HTTP never leaves a test: trackers are exercised with fake clients / httpx.MockTransport.
    import httpx

    def _blocked(self, request):
        raise httpx.ConnectError(f"network disabled in tests: {request.method} {request.url.host}", request=request)

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", _blocked)


def pytest_configure(config):
    config.addinivalue_line("markers", "real_preflight: run the orchestrator's input preflight (phase4/preflight.py)")


@pytest.fixture(autouse=True)
def _preflight_only_where_tested(request, monkeypatch):
    """Orchestrator tests use deliberately minimal project folders to test decision logic; the input preflight is
    tested on its own (and end to end) with @pytest.mark.real_preflight."""
    if request.node.get_closest_marker("real_preflight") is None:
        from agent_engine.phase4 import preflight
        monkeypatch.setattr(preflight, "check_inputs", lambda project: ([], []))
