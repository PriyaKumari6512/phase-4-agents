"""Run history (history.py): each run keeps runs/<job-id>/ with its report and
a copy of every output it created or changed. No model calls: the agent pass
is replaced by a fake that edits files.
"""

import asyncio
import json

import pytest
from langchain_core.messages import AIMessage

from agent_engine import agent, cli, history, logging_setup


@pytest.fixture
def project(tmp_path, monkeypatch):
    outputs = tmp_path / "outputs"
    for module in (cli, logging_setup):
        monkeypatch.setattr(module, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(logging_setup, "LOGS_DIR", tmp_path / "logs")
    return outputs / "p"


def test_fingerprint_skips_engine_bookkeeping(project):
    for f in ("prd.md", "product/stories.md", "inputs/round-1/a.pdf", "gates/G1.approved.json",
              "runs/j1/report.json", "logs/j1.log", "requests/prd.md", "requests.md", "report.json"):
        (project / f).parent.mkdir(parents=True, exist_ok=True)
        (project / f).write_text(f, encoding="utf-8")
    assert sorted(history.fingerprint(project)) == ["prd.md", "product/stories.md"]


def test_save_run_copies_only_what_the_run_created_or_changed(project):
    project.mkdir(parents=True)
    (project / "same.md").write_text("same", encoding="utf-8")
    (project / "edited.md").write_text("v1", encoding="utf-8")
    (project / "removed.md").write_text("x", encoding="utf-8")
    before = history.fingerprint(project)
    (project / "edited.md").write_text("v2", encoding="utf-8")
    (project / "removed.md").unlink()
    (project / "sources").mkdir()
    (project / "sources/SRC-001.md").write_text("new", encoding="utf-8")

    report = {"job_id": "j1"}
    changes = history.save_run(project, "j1", before, report)

    assert changes == {"created": ["sources/SRC-001.md"], "changed": ["edited.md"], "deleted": ["removed.md"]}
    run = project / "runs/j1"
    assert sorted(p.relative_to(run / "files").as_posix() for p in (run / "files").rglob("*") if p.is_file()) == [
        "edited.md", "sources/SRC-001.md",
    ]
    assert (run / "files/edited.md").read_text(encoding="utf-8") == "v2"
    assert json.loads((run / "report.json").read_text(encoding="utf-8"))["files"] == changes


def test_every_run_keeps_its_own_version(project, tmp_path, monkeypatch):
    """Two real cli runs (fake model) on one project: each run folder holds the
    PRD as that run left it, and the project report.json is the latest run.
    """
    monkeypatch.setattr(agent, "AGENTS_DIR", tmp_path / "agents")
    pack_dir = tmp_path / "agents" / "demo"
    pack_dir.mkdir(parents=True)
    (pack_dir / "agent.toml").write_text('[output]\nfiles = ["prd.md"]', encoding="utf-8")
    (pack_dir / "system_prompt.md").write_text("Write prd.md.", encoding="utf-8")
    monkeypatch.setattr(cli, "build_agent", lambda pack, level=0: None)
    monkeypatch.setattr(cli, "model_spec", lambda tier: "fake:model")
    monkeypatch.setattr(cli, "build_langfuse_handler", lambda: None)

    async def fake_stream(agent_graph, message, callbacks, run_name):
        (project / "prd.md").write_text(message.split("\n")[0], encoding="utf-8")
        return {"messages": [AIMessage("done")]}

    monkeypatch.setattr(cli, "_stream", fake_stream)
    job_ids = []
    for request in ("PRD for a gym app", "Add a 7-day free trial"):
        assert asyncio.run(cli._run(request, "demo", "p")) == 0
        job_ids.append(json.loads((project / "report.json").read_text(encoding="utf-8"))["job_id"])

    first, second = (project / "runs" / j for j in job_ids)
    assert (first / "files/prd.md").read_text(encoding="utf-8") == "PRD for a gym app"
    assert (second / "files/prd.md").read_text(encoding="utf-8") == "Add a 7-day free trial"
    second_report = json.loads((second / "report.json").read_text(encoding="utf-8"))
    assert second_report["request_text"] == "Add a 7-day free trial"
    assert second_report["files"]["changed"] == ["prd.md"]
    assert json.loads((project / "report.json").read_text(encoding="utf-8")) == second_report
