"""Adversarial regression cases from the audit and the recorded clinic run.

No paid model calls, cloud applies, live tracker mutations or real approvals.
"""
import asyncio
import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from agent_engine import backends, config, gates, perf
from agent_engine.runtime import active_inputs, project_scope, project_lock
from agent_engine.phase4 import allocation, backlog, files, infra, publish, sandbox, sprint, tools
from agent_engine.phase4 import alloc_solver as alloc
from agent_engine.phase4.contracts import Backlog, ProjectSettings, SprintPlan, CheckResult
from agent_engine.phase4.sprint_model import StoryIn, SprintIn, DeadlineIn, Relaxation, solve as packing
from test_phase4_pipeline import proj, P, AS_OF, _intent, approve, mock_passed_checks, seed_ci_evidence
from phase4_helpers import build_story_backlog


def prepared():
    build_story_backlog(files.project_dir(P))
    b = files.read_json(P, files.BACKLOG, Backlog)
    return b, {s.item_id: 5 for s in b.stories()}


def test_gate_dot_path_and_other_project_are_denied_at_disk_boundary(tmp_path, monkeypatch):
    monkeypatch.setattr(backends, "OUTPUTS_DIR", tmp_path)
    with project_scope("p"):
        backend = backends.build_backend()
        assert backend.write("/outputs/p/out.md", "ok").error is None
        assert backend.write("/outputs/p/./gates/P4-G1.approved.json", "{}").error
        with pytest.raises(RuntimeError, match="graph"):
            backend.write("/outputs/other/out.md", "scratch")
        assert not (tmp_path / "other/out.md").exists()
        with pytest.raises(files.ProjectError, match="bound"):
            files.project_dir("other")
    assert not (tmp_path / "p/gates/P4-G1.approved.json").exists()


def test_empty_approval_map_never_holds(proj):
    b, _ = prepared()
    approve(proj, "P4-G1")
    path = proj / "gates/P4-G1.approved.json"
    record = json.loads(path.read_text())
    record["artifacts"] = {}
    path.write_text(json.dumps(record))
    assert gates.stale_approvals(proj, ["gates/P4-G1.approved.json"])


@pytest.mark.parametrize("patch", [
    {"hours_per_story_point": 0}, {"story_point_scale": []},
    {"calendar": {"first_sprint_start": "2026-11-01", "sprint_length_days": 0}},
])
def test_bad_settings_are_rejected_before_solver(proj, patch):
    value = files.read_json(P, files.PROJECT_SETTINGS)
    value.update(patch)
    with pytest.raises(ValidationError):
        ProjectSettings.model_validate(value)


def test_scoped_backlog_view_is_paginated_and_read_only(proj):
    prepared()
    before = files.path(P, files.BACKLOG).read_bytes()
    page = json.loads(tools.backlog_view.invoke({"project": P, "epic_id": "BM-1", "limit": 2}))
    assert page["next_offset"] == 2 and len(page["items"]) == 2
    assert page["total"] > 2 and files.path(P, files.BACKLOG).read_bytes() == before


def test_soft_deadline_candidate_matches_actual_transformation():
    stories = [StoryIn("s", 1, 0)]
    windows = [SprintIn(1, 10, 10)]
    hard = [DeadlineIn("d", ["s"], 0, True)]
    candidate = packing(stories, windows, hard, Relaxation(soft_deadlines={"d"}), workers=1)
    applied = copy.deepcopy(hard)
    sprint._apply_relax(["soften:deadline:d"], stories, windows, applied, [])
    actual = packing(stories, windows, applied, workers=1)
    assert candidate.placement == actual.placement == {"s": 1}
    assert candidate.objective == actual.objective


def test_recorded_clinic_capacity_option_passes_its_own_checker(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1] / "docs/pipeline-run-results/clinic-fresh-run1/pipeline-artifacts/clinic-test-2"
    for rel in (files.PROJECT_SETTINGS, files.BACKLOG, files.SPRINT_PLAN):
        target = tmp_path / "clinic-test-2" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / rel, target)
    # The recording predates the story-based backlog: drop the retired spec-kit fields Sprint Planning never reads.
    recorded = json.loads((tmp_path / "clinic-test-2" / files.BACKLOG).read_text(encoding="utf-8"))
    for item in recorded["items"]:
        item.pop("speckit_phase", None)
        item.pop("speckit_ref", None)
        for d in item["dependencies"]:
            d["origin"] = "llm" if d["origin"] == "llm" else "human"
        for r in item["source_refs"]:
            r["source"] = "story" if r["source"] == "speckit" else r["source"]
    (tmp_path / "clinic-test-2" / files.BACKLOG).write_text(json.dumps(recorded), encoding="utf-8")
    plan_file = tmp_path / "clinic-test-2" / files.SPRINT_PLAN       # model-scored values are retired too
    recorded_plan = json.loads(plan_file.read_text(encoding="utf-8"))
    recorded_plan.pop("business_values", None)
    recorded_plan.pop("wsjf", None)
    plan_file.write_text(json.dumps(recorded_plan), encoding="utf-8")
    monkeypatch.setattr(config, "OUTPUTS_DIR", tmp_path)
    old = files.read_json("clinic-test-2", files.SPRINT_PLAN, SprintPlan)
    result = json.loads(sprint.solve("clinic-test-2", relax=["capacity:x1.3"], as_of="2026-11-16", time_limit_s=8))
    assert result["solver"] in ("FEASIBLE", "OPTIMAL")
    sprint.annotate("clinic-test-2", {str(s["sprint_index"]): "Test goal" for s in result["sprints"] if s["stories"]}, {}, "Test plan")
    checked = json.loads(sprint.check("clinic-test-2"))
    assert checked["ok"], checked["problems"]


def test_local_solver_checks_end_time_and_actual_cross_worker_precedence():
    w = [alloc.Worker("a", "A", "human", ["x"], 60, {"area": "MEDIUM"})]
    t = [alloc.TaskIn("late", 30, ["x"], "area", "MINOR", min_start=100)]
    assert alloc.solve_local(w, t).unassigned == ["late"]
    workers = [alloc.Worker("a", "A", "human", ["a"], 240, {"area": "MEDIUM"}),
               alloc.Worker("b", "B", "human", ["b"], 240, {"area": "MEDIUM"})]
    tasks = [alloc.TaskIn("before", 30, ["a"], "area", "MINOR"),
             alloc.TaskIn("after", 30, ["b"], "area", "MINOR", predecessors=["before"])]
    out = alloc.solve_local(workers, tasks)
    alloc.validate_schedule(out, workers, tasks)
    assert out.assigned["b"][0][1] >= out.assigned["a"][0][1] + 60


def test_blocked_ai_pin_cannot_override_hard_rules(proj):
    b, values = prepared()
    sprint.solve(P, as_of=AS_OF)
    plan = files.read_json(P, files.SPRINT_PLAN, SprintPlan)
    slot = next(s for s in plan.sprints if s.story_ids)
    task = b.tasks_of(slot.story_ids[0])[0]
    with pytest.raises(files.ProjectError, match="pin.*violates"):
        allocation.solve(P, slot.sprint_index, pins={task.item_id: "claude-code"}, block_ai=[task.item_id])
    assert not files.exists(P, files.ASSIGNMENTS)


@pytest.mark.parametrize("tool,code,text", [("checkov", 1, "{}"), ("checkov", 0, "{}"), ("trivy", 1, "{}"), ("tflint", 0, "{}")])
def test_wrong_schema_or_failed_scanner_is_never_a_pass(tmp_path, monkeypatch, tool, code, text):
    monkeypatch.setattr(sandbox, "_available", lambda *a: True)
    monkeypatch.setattr(sandbox, "_exec", lambda *a, **kw: sandbox.CmdResult(code, text, ""))
    result = sandbox._other_checks(tmp_path, False, lambda name: name == tool, lambda name: None)[0]
    assert not result.passed


def test_skipped_kubernetes_resources_are_incomplete():
    result = sandbox._schema_result("kubeconform", sandbox.CmdResult(0,
        "Summary: 10 resources found - Valid: 0, Invalid: 0, Errors: 0, Skipped: 10", ""))
    assert not result.passed and result.skipped and sandbox.incomplete([result])


def test_human_override_survives_repeated_publication(proj):
    b, _ = prepared()
    ids = publish.ExternalIds(P)
    tracker = publish.LocalTracker(P)
    payload = {"level": "story", "title": "Generated 1", "body_md": "body"}
    row = publish.ensure(tracker, ids, P, "test-story", payload)
    tracker.update(row["id"], {"title": "Human choice"})
    for title in ("Generated 2", "Generated 3", "Generated 4"):
        changed = publish.ensure(tracker, ids, P, "test-story", payload | {"title": title})
        assert "title" in changed["kept_human_edits"]
        assert tracker.get_fields(row["id"])["title"] == "Human choice"


def test_publication_checks_actual_approved_bytes(proj, monkeypatch):
    infra.set_intent(P, _intent())
    infra.render(P)
    mock_passed_checks(monkeypatch)
    infra.validate(P)
    approve(proj, "P4-G4")
    target = proj / "infra/repo/envs/dev/core/main.tf"
    target.write_text(target.read_text() + "\n# changed after approval\n")
    with pytest.raises(publish.PublishError):
        publish.publish_infra(P)
    assert not files.exists(P, "publish/infra.json")


def test_project_job_lease_is_cross_process_and_reentrant(tmp_path):
    script = "from pathlib import Path; from agent_engine.runtime import project_lock; import sys\ntry:\n with project_lock(Path(sys.argv[1]), timeout=.1): pass\nexcept TimeoutError:\n sys.exit(7)\n"
    with project_lock(tmp_path):
        with project_lock(tmp_path):
            result = subprocess.run([sys.executable, "-c", script, str(tmp_path)], env=os.environ.copy(), capture_output=True)
            assert result.returncode == 7, result.stderr


def test_diagnostics_bad_sample_setting_does_not_crash(tmp_path, monkeypatch):
    perf.reset_for_tests()
    monkeypatch.setenv(perf.ENV_SAMPLE_SECONDS, "invalid")
    try:
        assert perf.init("probe", force=True, perf_dir=tmp_path)
    finally:
        perf.reset_for_tests()


def test_helper_fanout_has_a_real_concurrency_bound():
    from agent_engine.locking import HelperLimitMiddleware
    async def exercise():
        middleware = HelperLimitMiddleware(2)
        running = peak = 0
        async def handler(request):
            nonlocal running, peak
            running += 1
            peak = max(peak, running)
            await asyncio.sleep(.01)
            running -= 1
        request = SimpleNamespace(tool=None, tool_call={"name": "task"})
        await asyncio.gather(*(middleware.awrap_tool_call(request, handler) for _ in range(9)))
        assert peak == 2
    asyncio.run(exercise())


def test_model_clients_close_once_and_cleanup_failure_does_not_hide_outcome():
    from agent_engine.agent import close_agent
    calls = []
    class SyncClient:
        def close(self):
            calls.append("sync")
            raise RuntimeError("cleanup failure")
    class AsyncClient:
        async def close(self):
            calls.append("async")
    first, second = SyncClient(), AsyncClient()
    graph = SimpleNamespace(_agent_engine_models=[SimpleNamespace(_client=first, root_client=first,
                                                                root_async_client=second)])
    asyncio.run(close_agent(graph))
    assert calls == ["sync", "async"]


def test_closing_writer_models_keeps_shared_transport_open_for_verifier():
    # Regression: closing the writer's clients closed langchain_anthropic's cached httpx client, so every
    # verifier pass failed with "Connection error" (client has been closed). No network call is made here.
    from agent_engine.agent import close_agent
    from agent_engine.subscription_models import build_anthropic_subscription_llm

    async def exercise():
        writer = build_anthropic_subscription_llm("claude-sonnet-5-5", "token")
        verifier = build_anthropic_subscription_llm("claude-sonnet-5-5", "token")
        shared = verifier._async_client._client
        assert writer._async_client._client is shared
        await close_agent(SimpleNamespace(_agent_engine_models=[writer]))
        assert not shared.is_closed
        assert not verifier._client._client.is_closed
    asyncio.run(exercise())


def test_provider_cache_changes_when_non_tf_file_changes_or_disappears(tmp_path, monkeypatch):
    monkeypatch.setenv("PHASE4_IAC_CACHE_DIR", str(tmp_path / "cache"))
    root = tmp_path / "source"
    root.mkdir()
    (root / "main.tf").write_text("# tf")
    values = root / "terraform.tfvars"
    values.write_text("x=1")
    seen = []
    monkeypatch.setattr(sandbox, "_validate_cached_envs", lambda path, *a: seen.append(path))
    sandbox._validate_envs(root, [], False)
    values.write_text("x=2")
    sandbox._validate_envs(root, [], False)
    values.unlink()
    sandbox._validate_envs(root, [], False)
    assert len(set(seen)) == 3
    assert not (seen[-1] / values.name).exists()


def test_auto_solver_recovers_after_healthy_probe_but_failed_job(monkeypatch):
    monkeypatch.setenv("PHASE4_ALLOCATION_SOLVER_MODE", "auto")
    monkeypatch.setattr(alloc, "timefold_available", lambda: True)
    def broken(*args):
        raise RuntimeError("remote job failed")
    monkeypatch.setattr(alloc, "solve_timefold", broken)
    workers = [alloc.Worker("a", "A", "human", ["x"], 120)]
    tasks = [alloc.TaskIn("t", 10, ["x"], "app", "MINOR")]
    result = alloc.solve(workers, tasks, "probe")
    assert result.engine == "local_cpsat" and not result.unassigned


def test_ambiguous_post_is_not_retried():
    import httpx
    from agent_engine.phase4.trackers.base import HttpClient, TrackerError
    calls = []
    def respond(request):
        calls.append(request)
        return httpx.Response(503, json={"error": "ambiguous"})
    client = HttpClient("https://tracker.test", {}, transport=httpx.MockTransport(respond), min_write_interval_s=0)
    try:
        with pytest.raises(TrackerError):
            client.post("/create", json={"title": "one"})
        assert len(calls) == 1
    finally:
        client.close()


def test_ci_probe_failure_replaces_old_readiness_evidence(proj, monkeypatch):
    from agent_engine.phase4 import readiness
    infra.set_intent(P, _intent())
    infra.render(P)
    seed_ci_evidence(P)
    class FailingHttp:
        def get(self, *args, **kw):
            raise RuntimeError("repository unavailable")
        def close(self):
            pass
    monkeypatch.setattr(readiness, "github_http", FailingHttp)
    result = readiness.check_ci(P)
    assert result and all(not record["success"] and record["errors"] for record in result.values())
    assert files.read_json(P, "phase4/ci-readiness.json") == result


def test_jira_link_direction_is_checked_by_readback():
    from agent_engine.phase4.trackers.jira import JiraTracker
    from agent_engine.phase4.trackers.base import TrackerError
    from agent_engine.phase4.contracts import TrackerConfig
    class LinkHttp:
        linked = False
        def post(self, url, json):
            assert json["inwardIssue"]["id"] == "before"
            assert json["outwardIssue"]["id"] == "after"
            self.linked = True
        def get(self, *args, **kwargs):
            links = [{"type": {"name":"Blocks"}, "outwardIssue":{"id":"after"}}] if self.linked else []
            return SimpleNamespace(json=lambda: {"fields":{"issuelinks":links}})
    tracker = JiraTracker(TrackerConfig(), http=LinkHttp())
    tracker.add_blocks("before", "after")
    assert tracker.blocks_of("before") == ["after"]
    tracker.blocks_of = lambda issue: []
    with pytest.raises(TrackerError, match="read-back"):
        tracker.add_blocks("before", "after")


@pytest.fixture(autouse=True)
def _isolate_component_publication(monkeypatch):
    # These tests exercise one publisher/checkpoint; final G4 has dedicated integration tests.
    from agent_engine.phase4 import publish
    monkeypatch.setattr(publish, "require_final_gate", lambda project: {})
