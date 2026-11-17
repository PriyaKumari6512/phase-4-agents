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
    # Real HTTP never leaves a test: trackers are exercised with fake clients / httpx.MockTransport.
    import httpx

    def _blocked(self, request):
        raise httpx.ConnectError(f"network disabled in tests: {request.method} {request.url.host}", request=request)

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", _blocked)
