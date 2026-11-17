"""Behavior and failure-path regressions; no paid APIs or live publication."""
import asyncio
import json
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from agent_engine import cli, config, perf, verification_resume
from agent_engine.locking import HelperLimitMiddleware
from agent_engine.phase4 import backlog, files, sandbox, tools
from agent_engine.phase4.cache_retention import prune_validation_cache
from agent_engine.phase4.parallel_stages import run_pair
from agent_engine.phase4.orchestrator import STAGES, Step
from agent_engine.phase4.sprint_model import (
    StoryIn, SprintIn, DeadlineIn, Relaxation, solve, diagnostics, required_ids, verified_options,
)
from test_model_escalation import engine, _script, _passes
from test_phase4_pipeline import proj, P
from phase4_helpers import build_story_backlog
from test_phase4_orchestrator import root, FakeAgents


def test_backlog_pages_are_lossless_and_reject_changed_snapshot(proj):
    build_story_backlog(files.project_dir(P))
    raw = files.read_text(P, files.BACKLOG)
    expected = json.loads(raw)["items"]
    rows, offset, digest = [], 0, ""
    while True:
        page = json.loads(tools.backlog_view.invoke({"project": P, "offset": offset,
                          "max_chars": 1000, "expected_sha256": digest}))
        digest = page["backlog_sha256"]
        assert page["items"]
        rows.extend(page["items"])
        offset = page["next_offset"]
        if offset is None:
            break
    assert rows == expected
    assert files.read_text(P, files.BACKLOG) == raw
    files.path(P, files.BACKLOG).write_text(raw + "\n")
    assert "changed" in tools.backlog_view.invoke({"project": P, "expected_sha256": digest})


def test_json_compaction_preserves_all_values_and_errors():
    data = {"description": "line one\n line two", "unicode": "é", "a": [None, False, 12]}
    pretty = json.dumps(data, indent=2)
    result = tools._run("test", lambda: pretty)
    assert json.loads(result) == data and len(result) < len(pretty)
    assert tools._run("test", lambda: "ERROR: keep this exact message") == "ERROR: keep this exact message"


def test_failed_verification_retry_skips_writer(engine, monkeypatch):
    _script(monkeypatch, verdicts=[], fail_on={("judge", "strong")})
    assert asyncio.run(cli._run("same request", "writer", "demo")) == 1
    assert verification_resume.checkpoint_path(engine / "demo", "writer").exists()
    _script(monkeypatch, verdicts=[True])
    assert asyncio.run(cli._run("same request", "writer", "demo", resume_verification=True)) == 0
    report, passes = _passes(engine)
    assert [p[0] for p in passes] == ["verify"]
    assert report["verification_resumed_from"]
    assert not verification_resume.checkpoint_path(engine / "demo", "writer").exists()


@pytest.mark.parametrize("change", ["request", "input", "new-input", "output", "gate", "pack"])
def test_retry_invalidates_changed_context_before_any_model(engine, monkeypatch, change):
    root = engine / "demo"
    root.mkdir(parents=True)
    (root / "prd.md").write_text("original")
    (root / "out.md").write_text("original")
    _script(monkeypatch, verdicts=[], fail_on={("judge", "strong")})
    assert asyncio.run(cli._run("same", "writer", "demo")) == 1
    request = "different" if change == "request" else "same"
    paths = {"input": root / "prd.md", "new-input": root / "phase4/history.json",
             "output": root / "out.md", "gate": root / "gates/g.approved.json"}
    if change in paths:
        paths[change].parent.mkdir(parents=True, exist_ok=True)
        paths[change].write_text("changed")
    if change == "pack":
        # Snapshot follows the configured pack root, including helper instructions.
        monkeypatch.setattr(config, "AGENTS_DIR", root / "different-packs")
    monkeypatch.setattr(cli, "build_agent", lambda *a: pytest.fail("stale retry paid for a model"))
    assert asyncio.run(cli._run(request, "writer", "demo", resume_verification=True)) == 1


def test_helpers_are_bounded_and_release_slots_on_failure(monkeypatch):
    events = []
    monkeypatch.setattr(perf, "event", lambda *a, **kw: events.append(kw))
    async def exercise():
        limiter = HelperLimitMiddleware(2)
        active, peak = 0, 0
        async def handler(request):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            try:
                await asyncio.sleep(0.01)
                if request.fail:
                    raise RuntimeError("helper failed")
                return "ok"
            finally:
                active -= 1
        def request(fail=False):
            return SimpleNamespace(tool=None, tool_call={"name": "task"}, fail=fail)
        results = await asyncio.gather(*(limiter.awrap_tool_call(request(i == 0), handler)
                                        for i in range(6)), return_exceptions=True)
        assert peak == 2 and limiter.active == 0
        assert isinstance(results[0], RuntimeError) and results[1:] == ["ok"] * 5
    asyncio.run(exercise())
    assert len(events) == 6 and any(e["wait_s"] > .005 for e in events)


def test_parallel_scanners_overlap_with_private_files_and_shared_deadline(tmp_path, monkeypatch):
    root = tmp_path / "infra"
    root.mkdir()
    (root / "main.tf").write_text("unchanged")
    barrier = threading.Barrier(2)
    def check(workdir, envs, names, include_init, docker):
        assert sandbox._budget_deadline.get() == 12345
        assert (workdir / "main.tf").read_text() == "unchanged"
        (workdir / "scratch").write_text(names[0])
        barrier.wait(timeout=5)
        assert (workdir / "scratch").read_text() == names[0]
        return [sandbox._check(names[0], "passed", passed=True, summary="ok")]
    monkeypatch.setattr(sandbox, "_run_checks", check)
    token = sandbox._budget_deadline.set(12345)
    try:
        result = sandbox._parallel_checks(root, [], ["trivy", "conftest"], True, False, 2)
    finally:
        sandbox._budget_deadline.reset(token)
    assert [r.tool for r in result] == ["trivy", "conftest"]
    assert list(root.iterdir()) == [root / "main.tf"]


def test_scanner_source_change_discards_success(tmp_path, monkeypatch):
    (tmp_path / "main.tf").write_text("before")
    def check(*args):
        (tmp_path / "main.tf").write_text("after")
        return [sandbox._check("trivy", "passed", passed=True, summary="ok")]
    monkeypatch.setattr(sandbox, "_run_checks", check)
    result = sandbox._parallel_checks(tmp_path, [], ["trivy"], True, False, 2)
    assert result[0].outcome == "execution_error" and not result[0].passed


def test_cache_retention_only_removes_owned_inactive_entries(tmp_path, monkeypatch):
    monkeypatch.setenv("PHASE4_IAC_CACHE_MAX_BYTES", "1")
    folders = [tmp_path / "validation" / (c * 64) for c in "abcd"]
    for d in folders:
        d.mkdir(parents=True)
        (d / "download").write_text("payload")
    for d in folders[:2]:
        (d / ".engine-cache-owned").write_text("phase4-validation-v1\n")
    removed = prune_validation_cache(tmp_path, keep=folders[1])
    assert removed == ["a" * 64]
    assert all(d.exists() for d in folders[1:])


def test_candidate_pruning_matches_scaled_solver_and_dependency_closure():
    windows = [SprintIn(1, 1, 1)]
    # Model rounds 1.04 to 1.0. A raw-float capacity bound falsely rejected it.
    stories = [StoryIn("s", 1.04, 1, must=True)]
    assert solve(stories, windows, [], want_core=False, workers=1).status == "OPTIMAL"
    stories = [StoryIn("a", 1, 1), StoryIn("b", 1, 1, depends_on=["a"], must=True)]
    res = solve(stories, windows, [], want_core=False, workers=1)
    assert res.status == "INFEASIBLE" and res.proof
    report = diagnostics(stories, windows, [], res)
    assert report["required_story_ids"] == ["a", "b"] and report["aggregate_deficit_points"] == 1
    assert required_ids([StoryIn("s", 9, 1, frozen_sprint=0)], windows, [], Relaxation()) == set()


def test_option_audit_does_not_call_unknown_infeasible(monkeypatch):
    from agent_engine.phase4 import sprint_model as model
    monkeypatch.setattr(model, "solve", lambda *a, **kw: model.SolveResult("UNKNOWN", {}, None, None, 5, [], {}))
    audit = []
    assert verified_options([], [], [], [], audit=audit) == []
    assert len(audit) == 2 and all(r["status"] == "UNKNOWN" for r in audit)


@pytest.mark.parametrize("bad_write", [False, True])
def test_parallel_stages_isolate_and_reject_unowned_changes(tmp_path, monkeypatch, bad_write):
    root = tmp_path / "outputs" / "demo"
    root.mkdir(parents=True)
    (root / "architecture.md").write_text("source")
    monkeypatch.setattr(config, "LOGS_DIR", tmp_path / "logs")
    barrier = threading.Barrier(2)
    def runner(agent, request, project, *, outputs_dir, logs_dir):
        child = outputs_dir / project
        assert child != root
        folder = "backlog" if agent == "task-breakdown" else "infra"
        (child / folder).mkdir()
        (child / folder / "partial.json").write_text(agent)
        barrier.wait(timeout=5)
        assert not (root / folder).exists()
        if bad_write and agent == "task-breakdown":
            (child / "architecture.md").write_text("not allowed")
        (child / "report.json").write_text(json.dumps({"agent": agent, "status": "partial"}))
        return {"status": "partial"}
    steps = [Step(s, "run", "test", s.request) for s in STAGES[:2]]
    if bad_write:
        with pytest.raises(ValueError, match="unexpected"):
            run_pair(root, steps, runner)
        assert not (root / "backlog").exists() and not (root / "infra").exists()
    else:
        results = run_pair(root, steps, runner)
        assert set(results) == {"task-breakdown", "infra-pipeline"}
        assert (root / "backlog/partial.json").read_text() == "task-breakdown"
        assert (root / "infra/partial.json").read_text() == "infra-pipeline"
    assert (root / "architecture.md").read_text() == "source"


def test_parallel_orchestrator_preserves_human_gates(root, monkeypatch):
    from agent_engine.phase4 import orchestrator as orch, parallel_stages
    calls = []
    def pair(project_root, steps, runner):
        fake = FakeAgents(project_root)
        results = {s.stage.agent: fake(s.stage.agent, s.request, project_root.name) for s in steps}
        calls.extend(fake.calls)
        return results
    monkeypatch.setattr(parallel_stages, "run_pair", pair)
    assert orch.orchestrate("demo", parallel_independent=True, out=lambda _: None) == orch.WAITING
    assert calls == ["task-breakdown", "infra-pipeline"]
    assert not list((root / "gates").glob("P4-*.approved.json"))
    assert not (root / "sprint").exists()


def test_parallel_merge_rolls_back_io_failure(tmp_path, monkeypatch):
    from agent_engine.phase4 import parallel_stages
    project = tmp_path / "demo"
    project.mkdir()
    (project / "architecture.md").write_text("original")
    monkeypatch.setattr(config, "LOGS_DIR", tmp_path / "logs")
    def runner(agent, request, name, *, outputs_dir, logs_dir):
        child = outputs_dir / name
        folder = "backlog" if agent == "task-breakdown" else "infra"
        (child / folder).mkdir()
        (child / folder / "file").write_text("generated")
        return {"status": "partial"}
    original = parallel_stages._replace
    calls = 0
    def replace(source, dest):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("disk failure")
        original(source, dest)
    monkeypatch.setattr(parallel_stages, "_replace", replace)
    with pytest.raises(OSError, match="disk failure"):
        run_pair(project, [Step(s, "run", "test", s.request) for s in STAGES[:2]], runner)
    assert parallel_stages.inventory(project) == {"architecture.md": parallel_stages.file_digest(project / "architecture.md")}
