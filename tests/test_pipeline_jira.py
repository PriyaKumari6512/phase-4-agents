"""ENV entry point and Jira publishing boundaries; no live Jira/model calls."""
import argparse
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import httpx
import pytest

from agent_engine import agent, cli, config, gates, perf, recovery
from agent_engine.phase4 import files, pipeline, publish, approval_policy as policy
from agent_engine.phase4 import orchestrator as orch
from agent_engine.phase4.contracts import Backlog, ProjectSettings, TrackerConfig, SprintPlan
from agent_engine.phase4.settings import get_pipeline_settings, get_jira_options
from agent_engine.phase4.trackers.base import ExtObj, HttpClient, TrackerError
from agent_engine.phase4.trackers.jira import JiraTracker
from test_phase4_pipeline import proj, P, approve, AS_OF
from phase4_helpers import build_story_backlog
from test_phase4_orchestrator import root, FakeAgents, OUTPUTS


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    import os
    for key in list(os.environ):
        if key.startswith("JIRA_") or key in {
            "PHASE4_TRACKER", "PHASE4_PROJECT_NAME", "PHASE4_AUTO_APPROVE_FOR_TESTING",
            "PHASE4_PUBLISH", "PHASE4_PARALLEL_STAGES", "PHASE4_SPRINT_INDEX",
            "PHASE4_IAC_CHECK_CONCURRENCY", "AGENT_ENGINE_PERF", "AGENT_ENGINE_PERF_MODE"}:
            monkeypatch.delenv(key)


def jira_env(monkeypatch):
    for key, value in {"PHASE4_TRACKER": "jira", "JIRA_BASE_URL": "https://demo.atlassian.net",
                       "JIRA_PROJECT_KEY": "DEMO", "JIRA_BOARD_ID": "12",
                       "JIRA_EMAIL": "user@example.test", "JIRA_API_TOKEN": "test-secret"}.items():
        monkeypatch.setenv(key, value)


def built_backlog():
    from agent_engine.phase4 import backlog
    build_story_backlog(files.project_dir(P))


def test_env_overrides_are_effective_without_changing_input_bytes(proj, monkeypatch):
    original = (proj / files.PROJECT_SETTINGS).read_bytes()
    jira_env(monkeypatch)
    monkeypatch.setenv("JIRA_ACCOUNT_MAP", '{"m-alice":"jira-account-123"}')
    settings = files.read_json(P, files.PROJECT_SETTINGS, ProjectSettings)
    assert settings.tracker.kind.value == "jira" and settings.tracker.jira_board_id == 12
    assert settings.team[0].tracker_account_id == "jira-account-123"
    assert (proj / files.PROJECT_SETTINGS).read_bytes() == original


@pytest.mark.parametrize("key,value", [
    ("JIRA_BASE_URL", "http://insecure.test"), ("JIRA_BOARD_ID", "0"),
    ("JIRA_PROJECT_KEY", 'bad"key'), ("JIRA_ACCOUNT_MAP", '{"unknown":"account"}')])
def test_bad_jira_destination_is_rejected(proj, monkeypatch, key, value):
    jira_env(monkeypatch)
    monkeypatch.setenv(key, value)
    with pytest.raises(files.ProjectError):
        files.read_json(P, files.PROJECT_SETTINGS, ProjectSettings)


@pytest.mark.parametrize("key,value", [
    ("JIRA_PUBLISH_CONCURRENCY", "0"), ("JIRA_TIMEOUT_SECONDS", "nan"),
    ("JIRA_MIN_WRITE_INTERVAL_SECONDS", "inf"), ("JIRA_MAX_RETRIES", "-1"),
    ("JIRA_ISSUE_TYPE_IDS", '[]'), ("JIRA_ISSUE_TYPE_IDS", '{"task":5}'),
    ("JIRA_CREATE_FIELDS", '{"story":{"parent":{}}}'), ("JIRA_STORY_POINTS_FIELD_ID", "summary")])
def test_bad_jira_options_are_rejected(monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    with pytest.raises(ValueError):
        get_jira_options()


def test_pipeline_defaults_enable_full_flow_and_keep_test_approval_explicit(monkeypatch):
    settings = get_pipeline_settings()
    assert settings.publish and settings.parallel and settings.diagnostics
    assert not settings.auto_approve_for_testing
    pipeline.configure_environment()
    import os
    assert os.environ["AGENT_ENGINE_PERF_MODE"] == "publication"
    assert os.environ["PHASE4_IAC_CHECK_CONCURRENCY"] == "2"
    monkeypatch.setenv("AGENT_ENGINE_PERF_MODE", "generation")
    pipeline.configure_environment()
    assert os.environ["AGENT_ENGINE_PERF_MODE"] == "generation"


def test_entry_dispatch_requires_no_cli_parameters(monkeypatch):
    monkeypatch.setattr(pipeline, "run", lambda: 23)
    assert cli._dispatch(argparse.Namespace(command="pipeline")) == 23


def test_entry_wires_env_and_closes_readonly_preflight_client(proj, monkeypatch):
    jira_env(monkeypatch)
    monkeypatch.setenv("PHASE4_PROJECT_NAME", P)
    monkeypatch.setenv("PHASE4_AUTO_APPROVE_FOR_TESTING", "true")
    monkeypatch.setattr(config, "resolve_model_tiers", lambda: None)
    monkeypatch.setattr(perf, "publication_blocked", lambda: None)
    events = []
    class Preflight:
        def __init__(self, cfg):
            assert cfg.jira_project_key == "DEMO"
        def preflight(self, accounts):
            assert accounts["m-alice"] == "alice"
            events.append("preflight")
            return {"checks": "passed"}
        def close(self):
            events.append("close")
    monkeypatch.setattr("agent_engine.phase4.trackers.jira.JiraTracker", Preflight)
    def orchestrate(project, **kw):
        assert project == P and kw["test_approve"] and kw["verified_test_approval"]
        assert kw["publish"] and kw["parallel_independent"]
        events.append("orchestrate")
        return 0
    monkeypatch.setattr(orch, "orchestrate", orchestrate)
    assert pipeline.run(out=lambda _: None) == 0
    assert events == ["preflight", "close", "orchestrate"]


def test_entry_refuses_generation_diagnostics_before_any_external_work(proj, monkeypatch):
    monkeypatch.setenv("PHASE4_PROJECT_NAME", P)
    monkeypatch.setattr(perf, "publication_blocked", lambda: "generation mode blocks publication")
    monkeypatch.setattr(orch, "orchestrate", lambda *a, **kw: pytest.fail("must fail before generation"))
    messages = []
    assert pipeline.run(out=messages.append) == 1
    assert "AGENT_ENGINE_PERF_MODE=publication" in " ".join(messages)


def test_jira_credentials_do_not_silently_publish_locally(proj, monkeypatch):
    monkeypatch.setenv("PHASE4_PROJECT_NAME", P)
    monkeypatch.setenv("JIRA_EMAIL", "user@example.test")
    monkeypatch.setenv("JIRA_API_TOKEN", "test")
    monkeypatch.setattr(perf, "publication_blocked", lambda: None)
    messages = []
    assert pipeline.run(out=messages.append) == 1
    assert "PHASE4_TRACKER=jira" in " ".join(messages)


def jira_http(handler, **kw):
    return HttpClient("https://demo.atlassian.net", {}, min_write_interval_s=0,
                      transport=httpx.MockTransport(handler), **kw)


def metadata_handler(request):
    path = request.url.path
    if path.endswith("/board/12"):
        data = {"type": "scrum"}
    elif path.endswith("/mypermissions"):
        data = {"permissions": {key: {"havePermission": True} for key in request.url.params["permissions"].split(",")}}
    elif path.endswith("/issuetypes"):
        data = {"total": 3, "issueTypes": [{"id": "1", "name": "Epic"}, {"id": "2", "name": "Story"},
                                          {"id": "3", "name": "Sub-task", "subtask": True}]}
    elif path.endswith("/configuration"):
        data = {"estimation": {"field": {"fieldId": "customfield_10016"}}}
    elif "/issuetypes/" in path:
        data = {"fields": [{"fieldId": "summary", "required": True}]}
    else:
        data = {}
    return httpx.Response(200, json=data)


def test_jira_preflight_is_readonly_and_metadata_is_warmed_once(monkeypatch):
    jira_env(monkeypatch)
    calls = []
    def handle(request):
        calls.append((request.method, request.url.path))
        return metadata_handler(request)
    tracker = JiraTracker(TrackerConfig(kind="jira", jira_base_url="https://demo.atlassian.net",
                                       jira_project_key="DEMO", jira_board_id=12), http=jira_http(handle))
    try:
        assert tracker.preflight()["checks"] == "passed"
        tracker.prepare()
        assert all(method == "GET" for method, path in calls)
        assert sum(path.endswith("/issuetypes") for _, path in calls) == 1
        assert sum(path.endswith("/configuration") for _, path in calls) == 1
    finally:
        tracker.close()


def test_localized_issue_types_and_metadata_pagination(monkeypatch):
    monkeypatch.setenv("JIRA_ISSUE_TYPE_IDS", '{"epic":"1","story":"2","task":"3"}')
    calls = []
    def handle(request):
        start = int(request.url.params.get("startAt", 0))
        calls.append(start)
        rows = [{"id": "1", "name": "Épopée"}, {"id": "2", "name": "Histoire"},
                {"id": "3", "name": "Sous-tâche", "subtask": True}]
        return httpx.Response(200, json={"isLast": start == 2, "values": rows[start:start + 1]})
    tracker = JiraTracker(TrackerConfig(), http=jira_http(handle))
    try:
        assert tracker.issue_types == {"epic": "1", "story": "2", "task": "3"}
        assert calls == [0, 1, 2]
    finally:
        tracker.close()


@pytest.mark.parametrize("failure", ["kanban", "permission", "required_field"])
def test_preflight_rejects_incompatible_jira_setup(failure):
    def handle(request):
        if failure == "kanban" and request.url.path.endswith("/board/12"):
            return httpx.Response(200, json={"type": "kanban"})
        if failure == "permission" and request.url.path.endswith("/mypermissions"):
            return httpx.Response(200, json={"permissions": {}})
        if failure == "required_field" and request.url.path.endswith("/issuetypes/2"):
            return httpx.Response(200, json={"fields": [{"fieldId": "customfield_999", "required": True}]})
        return metadata_handler(request)
    tracker = JiraTracker(TrackerConfig(jira_project_key="DEMO", jira_board_id=12), http=jira_http(handle))
    try:
        with pytest.raises(TrackerError):
            tracker.preflight()
    finally:
        tracker.close()


@pytest.mark.parametrize("status,expected_calls", [(429, 2), (503, 1)])
def test_only_explicitly_rejected_jira_posts_are_replayed(status, expected_calls):
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(status if len(calls) == 1 else 201, headers={"Retry-After": "0"}, json={"id": "created"})
    client = jira_http(handle, retry_rejected_posts=True, max_retries=1)
    try:
        if status == 503:
            with pytest.raises(TrackerError):
                client.post("/create")
        else:
            assert client.post("/create").status_code == 201
        assert len(calls) == expected_calls
    finally:
        client.close()


def test_concurrent_requests_share_write_throttle():
    starts = []
    lock = threading.Lock()
    def handle(request):
        with lock:
            starts.append(time.monotonic())
        return httpx.Response(204)
    client = HttpClient("https://jira.test", {}, min_write_interval_s=0.02, transport=httpx.MockTransport(handle))
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda i: client.put(f"/issue/{i}"), range(4)))
        assert all(b - a >= 0.015 for a, b in zip(starts, starts[1:]))
    finally:
        client.close()


class ConcurrentTracker(publish.LocalTracker):
    """In-memory fake Jira, because LocalTracker JSON collections are deliberately serial."""
    system = "jira"
    def __init__(self, project):
        super().__init__(project)
        self.lock = threading.Lock()
        self.remote = {}
        self.running = self.peak = 0
        self.closed = False
        self.fail_id = None
    def create(self, payload):
        with self.lock:
            parent = payload.get("parent_id")
            assert not parent or parent in self.remote
            self.running += 1
            self.peak = max(self.peak, self.running)
        try:
            time.sleep(0.003)
            if self.fail_id and self.fail_id in payload["body_md"]:
                raise TrackerError("rejected", status_code=429)
            with self.lock:
                key = f"J-{len(self.remote) + 1}"
                self.remote[key] = dict(payload)
                return ExtObj(key, key)
        finally:
            with self.lock:
                self.running -= 1
    def find_by_marker(self, marker, level=None):
        with self.lock:
            return next((ExtObj(key, key) for key, value in self.remote.items() if value["_marker"] == marker), None)
    def blocks_of(self, issue_id):
        return []
    def add_blocks(self, *args):
        pass
    def close(self):
        assert self.running == 0
        self.closed = True


def test_backlog_parallel_waves_are_ordered_durable_and_repeatable(proj, monkeypatch):
    built_backlog()
    approve(proj, "P4-G1")
    tracker = ConcurrentTracker(P)
    monkeypatch.setattr(publish, "_tracker_for", lambda *args: tracker)
    report = publish.publish_backlog(P)
    count = len(files.read_json(P, files.BACKLOG, Backlog).items)
    assert report["created"] == count and 1 < tracker.peak <= 4 and tracker.closed
    ids = publish.ExternalIds(P)
    assert len(ids.data[ids.namespace("jira")]) == count
    assert publish.publish_backlog(P)["created"] == 0
    assert len(tracker.remote) == count


def test_partial_publish_retains_completed_ids_and_rejected_create_can_resume(proj, monkeypatch):
    built_backlog()
    approve(proj, "P4-G1")
    tracker = ConcurrentTracker(P)
    tracker.fail_id = "BM-2-T"
    monkeypatch.setattr(publish, "_tracker_for", lambda *args: tracker)
    with pytest.raises(TrackerError, match="rejected"):
        publish.publish_backlog(P)
    assert tracker.closed and tracker.remote
    before = len(tracker.remote)
    tracker.fail_id = None
    publish.publish_backlog(P)
    assert len(tracker.remote) == len(files.read_json(P, files.BACKLOG, Backlog).items) > before


def test_concurrent_same_issue_create_has_only_one_remote_side_effect(proj):
    tracker = ConcurrentTracker(P)
    ids = publish.ExternalIds(P)
    payload = {"level": "epic", "title": "one", "body_md": "one"}
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: publish.ensure(tracker, ids, P, "E-1", payload), range(8)))
    assert len(tracker.remote) == 1 and sum(row["created"] for row in results) == 1


@pytest.mark.parametrize("status,cleared", [(429, True), (400, True), (503, False)])
def test_only_definite_rejections_clear_pending_outbox(proj, status, cleared):
    ids = publish.ExternalIds(P)
    def fail():
        raise TrackerError("failure", status_code=status)
    with pytest.raises(TrackerError):
        publish._once(ids, "jira_comment", "once", fail)
    assert (ids.get("jira_comment", "once") is None) == cleared


def test_test_publication_needs_flag_marker_and_current_review(proj, monkeypatch):
    built_backlog()
    pack = agent.load_pack("task-breakdown")
    # The test supplies a verified boundary; real engine records it only after deterministic + semantic checks.
    for rel in pack.output_files:
        if not (proj / rel).exists():
            files.write_text(P, rel, "reviewed")
    recovery.save(proj, pack, "request", "job", "verified")
    gate = gates.load_gates()["P4-G1"]
    approver = {"name": "Test automation", "role": "NOT a human sign-off", "automation": policy.TEST_ORIGIN}
    gates.record_decision(proj, gate, "approved", approver, {"name": "writer"})
    with pytest.raises(publish.PublishError, match="automated test approvals"):
        publish.require_gate(P, "backlog")
    monkeypatch.setenv("PHASE4_AUTO_APPROVE_FOR_TESTING", "true")
    assert publish.require_gate(P, "backlog")["approver"]["automation"] == policy.TEST_ORIGIN
    recovery.save(proj, pack, "request", "job", "awaiting_decision", human=True, gaps=["human choice"])
    with pytest.raises(publish.PublishError, match="automated test approvals"):
        publish.require_gate(P, "backlog")


def test_env_auto_approves_only_completed_review_boundaries(root, monkeypatch):
    monkeypatch.setenv("PHASE4_AUTO_APPROVE_FOR_TESTING", "true")
    fake = FakeAgents(root)
    def run(agent_name, request, project):
        result = fake(agent_name, request, project)
        recovery.save(root, agent.load_pack(agent_name), request, "fake-reviewed", "verified")
        return result
    assert orch.orchestrate("demo", test_approve=True, verified_test_approval=True, runner=run,
                            out=lambda _: None) == orch.DONE
    for stage in orch.STAGES:
        record = json.loads((root / f"gates/{stage.gate}.approved.json").read_text())
        assert record["approver"]["automation"] == policy.TEST_ORIGIN


def test_legacy_existing_files_are_reviewed_before_env_auto_approval(root, monkeypatch):
    monkeypatch.setenv("PHASE4_AUTO_APPROVE_FOR_TESTING", "true")
    fake = FakeAgents(root)
    for name in OUTPUTS:
        fake(name, "", "demo")
    calls = []
    def review(agent_name, request, project):
        action, record = recovery.next_action(root, agent.load_pack(agent_name))
        assert action == "verify"  # retained outputs, not writer regeneration
        calls.append(agent_name)
        recovery.save(root, agent.load_pack(agent_name), request, "reviewed", "verified")
        return {"status": "success"}
    assert orch.orchestrate("demo", test_approve=True, verified_test_approval=True, runner=review,
                            out=lambda _: None) == orch.DONE
    assert set(calls) == set(OUTPUTS)


def test_env_destination_changes_only_affected_stage_input_identities(proj, monkeypatch):
    before = {stage.agent: orch.input_digests(stage, proj, 1) for stage in orch.STAGES}
    packs = {stage.agent: agent.load_pack(stage.agent) for stage in orch.STAGES}
    snapshots = {name: recovery.snapshot(proj, pack) for name, pack in packs.items()}
    assert all("integration_settings" not in value for value in snapshots.values())
    jira_env(monkeypatch)
    after = {stage.agent: orch.input_digests(stage, proj, 1) for stage in orch.STAGES}
    assert before["task-breakdown"] == after["task-breakdown"]
    assert snapshots["task-breakdown"] == recovery.snapshot(proj, packs["task-breakdown"])
    for name in ("infra-pipeline", "sprint-planning", "work-allocation"):
        assert before[name] != after[name]
        assert snapshots[name] != recovery.snapshot(proj, packs[name])


def test_preflight_rejects_unassignable_team_accounts():
    def handle(request):
        if request.url.path.endswith("/user/assignable/search"):
            assert request.url.params["accountId"] == "not-a-jira-account"
            return httpx.Response(200, json=[])
        return metadata_handler(request)
    tracker = JiraTracker(TrackerConfig(jira_project_key="DEMO", jira_board_id=12), http=jira_http(handle))
    try:
        with pytest.raises(TrackerError, match="JIRA_ACCOUNT_MAP"):
            tracker.preflight({"m-alice": "not-a-jira-account"})
    finally:
        tracker.close()


def test_jira_sprints_publish_concurrently_and_keep_their_own_issue_sets(proj, monkeypatch):
    from agent_engine.phase4 import sprint
    built_backlog()
    approve(proj, "P4-G1")
    backlog = files.read_json(P, files.BACKLOG, Backlog)
    sprint.solve(P, {s.item_id: 5 for s in backlog.stories()}, as_of=AS_OF)
    plan = files.read_json(P, files.SPRINT_PLAN)
    stories = [sid for slot in plan["sprints"] for sid in slot["story_ids"]]
    assert len(stories) >= 2 and len(plan["sprints"]) >= 2
    for slot in plan["sprints"]:
        slot["story_ids"] = []
    plan["sprints"][0]["story_ids"] = stories[::2]
    plan["sprints"][1]["story_ids"] = stories[1::2]
    files.write_json(P, files.SPRINT_PLAN, plan)
    approve(proj, "P4-G2")
    class SprintTracker(ConcurrentTracker):
        def __init__(self):
            super().__init__(P)
            self.moves = {}
        def create_sprint(self, name, start, end, goal):
            with self.lock:
                self.running += 1
                self.peak = max(self.peak, self.running)
            try:
                time.sleep(0.02)
                return ExtObj(start.isoformat())
            finally:
                with self.lock:
                    self.running -= 1
        def move_to_sprint(self, sprint_id, issue_ids):
            with self.lock:
                self.moves[sprint_id] = issue_ids
        def move_to_backlog(self, issue_ids):
            pass
    tracker = SprintTracker()
    monkeypatch.setattr(publish, "_tracker_for", lambda *a: tracker)
    ids = publish.ExternalIds(P)
    for sid in stories:
        ids.put("jira", sid, "remote-" + sid, None, {})
    result = publish.publish_sprint(P)
    assert tracker.peak == 2 and tracker.closed and result["moved"] == len(stories)
    for slot in plan["sprints"][:2]:
        assert tracker.moves[slot["start"]] == ["remote-" + sid for sid in slot["story_ids"]]


def test_jira_human_assignments_are_parallel_and_follow_account_map_changes(proj, monkeypatch):
    from agent_engine.phase4 import allocation
    built_backlog()
    approve(proj, "P4-G1")
    # Isolate publishing with a consistent two-task assignment contract; allocation
    # correctness is already covered by its own affected integration tests.
    tasks = [t for t in files.read_json(P, files.BACKLOG, Backlog).items if t.level == "task"][:2]
    assignments = [SimpleNamespace(task_id=t.item_id, worker_id="m-alice", worker_kind="human", explanation="tested") for t in tasks]
    ap = SimpleNamespace(assignments=assignments, unassigned=[], sprint_index=1)
    slot = SimpleNamespace(sprint_index=1)
    original_read = files.read_json
    def read(project, rel, model=None):
        if rel == files.ASSIGNMENTS:
            return ap
        if rel == files.SPRINT_PLAN:
            return SimpleNamespace(sprints=[slot])
        return original_read(project, rel, model)
    monkeypatch.setattr(files, "read_json", read)
    monkeypatch.setattr(publish, "require_gate", lambda *a: {})
    monkeypatch.setattr(allocation, "check", lambda *a: '{"problems":[]}')
    monkeypatch.setattr(allocation, "ci_ready_repos", lambda *a: set())
    class AssignmentTracker(ConcurrentTracker):
        def __init__(self):
            super().__init__(P)
            self.assigned = []
        def assign(self, issue, account):
            with self.lock:
                self.running += 1
                self.peak = max(self.peak, self.running)
            try:
                time.sleep(0.02)
                with self.lock:
                    self.assigned.append((issue, account))
            finally:
                with self.lock:
                    self.running -= 1
        def add_comment(self, *args):
            pass
    tracker = AssignmentTracker()
    monkeypatch.setattr(publish, "_tracker_for", lambda *a: tracker)
    ids = publish.ExternalIds(P)
    for task in tasks:
        ids.put("jira", task.item_id, "remote-" + task.item_id, None, {})
    assert publish.publish_assignments(P)["assigned"] == 2
    assert tracker.peak == 2 and tracker.closed
    assert publish.publish_assignments(P)["assigned"] == 0
    monkeypatch.setenv("JIRA_ACCOUNT_MAP", '{"m-alice":"updated-account"}')
    assert publish.publish_assignments(P)["assigned"] == 2
    assert all(account == "updated-account" for issue, account in tracker.assigned[-2:])
