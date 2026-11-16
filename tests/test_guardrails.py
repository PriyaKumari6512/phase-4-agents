"""The write guard (guardrails.py): writes stay under /outputs/, and out of a
project's read-only inputs/ and gates/ folders. Reads are never blocked.
"""

import asyncio
from types import SimpleNamespace

import pytest

from agent_engine.guardrails import OutputsOnlyGuardMiddleware


def _call(tool: str, file_path: str):
    """Runs one tool call through the guard; returns the guard's refusal, or "passed"."""
    request = SimpleNamespace(tool=None, tool_call={"name": tool, "args": {"file_path": file_path}, "id": "c1"})

    async def handler(_request):
        return "passed"

    result = asyncio.run(OutputsOnlyGuardMiddleware().awrap_tool_call(request, handler))
    return result if result == "passed" else result.content


@pytest.mark.parametrize(
    "path",
    [
        "/outputs/gym-app/prd.md",
        "/outputs/gym-app/requirements/register.md",
        "/outputs/gym-app/sources/SRC-001.md",
        "/outputs/gym-app/inputs-notes.md",  # only the inputs/ folder itself is protected
    ],
)
def test_writes_under_outputs_pass(path):
    assert _call("write_file", path) == "passed"


@pytest.mark.parametrize(
    "path",
    [
        "/outputs/gym-app/inputs/round-1/rfp.pdf",
        "/outputs/gym-app/inputs",
        "/outputs/gym-app/gates/G1.approved.json",
        "outputs\\gym-app\\gates\\history.jsonl",
        "/outputs/gym-app/requests/prd.md",
        "/outputs/gym-app/runs/20261103-101500-abc123/files/prd.md",
    ],
)
@pytest.mark.parametrize("tool", ["write_file", "edit_file", "delete"])
def test_read_only_project_folders_are_refused(tool, path):
    assert "is read-only" in _call(tool, path)


@pytest.mark.parametrize("path", ["/knowledge/contract.md", "/tmp/x.md"])
def test_writes_outside_outputs_are_refused(path):
    assert "is outside /outputs/" in _call("write_file", path)


def test_reads_of_read_only_folders_pass():
    assert _call("read_file", "/outputs/gym-app/inputs/round-1/rfp.pdf") == "passed"
