"""Task Breakdown from approved stories: one structured call per story, exact assembly in code, retained results,
deterministic review and targeted repair. The model is a fake; no network."""
from __future__ import annotations

import asyncio
import json

import pytest

from agent_engine import config
from agent_engine.phase4 import backlog, files, task_breakdown as tb
from agent_engine.phase4.contracts import Backlog

P = "tb"
REAL_SPEC, REAL_IDENTITY_SPEC = tb._spec, tb._identity_spec


def snapshot(points=(3, None), summary="Staff sign in"):
    def story(key, us, pts, blocks=()):
        return {"key": key, "issue_id": key[-1], "summary": f"{summary} {key}",
                "statement": "As front-desk staff, I want to sign in so that I see my screens.",
                "acceptance_criteria": [{"ac_id": f"{us}.AC1", "text": "Given an account, When the password is right, Then I am in."},
                                        {"ac_id": f"{us}.AC2", "text": "Given an account, When it is wrong, Then sign-in fails."}],
                "notes": "See NFR-010.", "requirement_ids": [us, "FR-002"], "moscow": "must",
                "components": ["MOD-01 Accounts"], "epic_key": "GR-1", "story_points": pts, "blocks": list(blocks)}
    return {"project": P, "source": "jira", "project_key": "GR",
            "epics": [{"key": "GR-1", "issue_id": "1", "summary": "Access", "requirement_ids": ["FR-001", "FR-002"]}],
            "stories": [story("GR-9", "US-001", points[0], blocks=["GR-10"]), story("GR-10", "US-002", points[1])]}


@pytest.fixture
def proj(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUTS_DIR", tmp_path / "outputs")
    root = tmp_path / "outputs" / P
    (root / "phase4").mkdir(parents=True)
    settings = json.loads((config.ASSETS_ROOT / "examples/phase4/taskflow/phase4/project.json").read_text())
    (root / "phase4/project.json").write_text(json.dumps({**settings, "project_name": P}))
    (root / "phase4/stories.json").write_text(json.dumps(snapshot()))
    (root / "architecture.md").write_text("# Architecture\n\n## Auth\nPOST /api/sessions, table users.\n")
    (root / "prd.md").write_text("# PRD\n\n- **FR-002**: staff sign in.\n- NFR-010: lockout after 5 tries.\n")
    monkeypatch.setattr(tb, "_spec", lambda: "test:strong")
    monkeypatch.setattr(tb, "_identity_spec", lambda: "test:strong")
    return root


def good(story_key, us):
    return tb.StoryBreakdown(story_key=story_key, estimate_rationale="Two layers and a test.", reference_ticket_ids=[], deferred_criteria=[],
                             open_questions=[], tasks=[
        tb.TaskDraft(local_id="T1", discipline="DB", title="Add users.password_hash column", description="Migration.",
                     acceptance_criteria=["Given the migration, When applied, Then the column exists."], covers=[],
                     file_paths=[], repo="acme/taskflow-api", hours=2, depends_on=[], skills=["postgres"],
                     definition_of_done=["Migration is reversible"], confidence="high", open_questions=[]),
        tb.TaskDraft(local_id="T2", discipline="BE", title="Add POST /api/sessions", description="Endpoint.",
                     acceptance_criteria=["WHEN the password is right THE SYSTEM SHALL return 200."],
                     covers=[f"{us}.AC1", f"{us}.AC2"], file_paths=[], repo="acme/taskflow-api", hours=5.2,
                     depends_on=["T1"], skills=["backend-python", "api-design"], definition_of_done=[],
                     confidence="medium", open_questions=["Lockout window? (NFR-010 gives 5 tries only)"]),
        tb.TaskDraft(local_id="T3", discipline="QA", title="E2E sign-in tests", description="Playwright.",
                     acceptance_criteria=["Given both scenarios, When run in CI, Then they pass."],
                     covers=[f"{us}.AC1", f"{us}.AC2"], file_paths=[], repo=None, hours=3, depends_on=["T2"],
                     skills=["qa-automation"], definition_of_done=[], confidence="medium", open_questions=[])])


class FakeModel:
    def __init__(self, broken=(), cross=None, review=None):
        self.calls, self.broken, self.active, self.max_active = [], set(broken), 0, 0
        self.cross_calls, self.cross = [], cross or tb.CrossStoryReview(dependencies=[], shared_work=[])
        reviews = review if isinstance(review, list) else [review or tb.LightReview(findings=[])]
        self.review_calls, self.reviews = [], reviews

    async def __call__(self, schema, system, human, callbacks, spec):
        if schema is tb.LightReview:
            self.review_calls.append({"system": system, "spec": spec, "human": human,
                                      "payload": json.loads(human.split("Review these flagged items:\n", 1)[1])})
            return self.reviews[min(len(self.review_calls), len(self.reviews)) - 1]
        if schema is tb.CrossStoryReview:
            self.cross_calls.append({"system": system, "index": json.loads(human.split("\n", 1)[1])})
            return self.cross
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0.01)
        self.active -= 1
        payload = json.loads(human.split("\n", 1)[1].split("\n\nYour previous answer")[0])
        key = payload["story"]["key"]
        self.calls.append({"key": key, "system": system, "payload": payload, "retry": "previous answer" in human,
                           "spec": spec})
        us = payload["story"]["acceptance_criteria"][0]["ac_id"].split(".")[0]
        result = good(key, us)
        if "findings_to_fix" in payload:
            result.tasks[0].hours = 3                # a repair changes something
        if key in self.broken:
            self.broken.discard(key)
            result.tasks[1].covers = []          # first answer misses criteria; the retry fixes it
            result.tasks[2].covers = []
        return result


def run(coro):
    return asyncio.run(coro)


def test_stories_become_tasks_without_rewriting_the_story(proj, monkeypatch):
    fake = FakeModel()
    monkeypatch.setattr(tb, "_invoke", fake)
    reply = run(tb.generate(P, "Break the approved stories down into tasks.", []))
    assert "2 stories, 6 tasks" in reply["messages"][0].content and "0 blocking" in reply["messages"][0].content
    b = files.read_json(P, files.BACKLOG, Backlog)
    by = b.by_id()
    story = by["GR-9"]
    assert story.parent_id == "GR-1" and story.priority == "P1" and story.moscow == "must"
    assert [a.ac_id for a in story.acceptance_criteria] == ["US-001.AC1", "US-001.AC2"]
    assert story.user_story.as_a == "front-desk staff"
    assert (story.estimate.story_points, story.estimate.method) == (3, "human")          # kept from Jira
    derived = by["GR-10"].estimate
    assert derived.method == "rollup" and derived.story_points == 2                      # 10 h / 6 h per SP -> 2
    t = by["GR-9-T02"]
    assert (t.discipline, t.type, t.estimate.hours, t.repo) == ("BE", "feature", 5.0, "acme/taskflow-api")
    assert [d.on_id for d in t.dependencies] == ["GR-9-T01"] and not t.ai_eligible
    assert by["GR-9-T01"].definition_of_done[-1] == "Migration is reversible"
    assert {r.req_id for r in t.source_refs} == {"US-001.AC1", "US-001.AC2"}
    assert [d.on_id for d in by["GR-10"].dependencies] == ["GR-9"]                       # Jira: GR-9 blocks GR-10
    assert b.coverage["FR-002"] == ["GR-9", "GR-10"] and files.STORIES in b.sources
    md = (proj / files.BACKLOG_MD).read_text()
    assert "| GR-9-T02 | BE | Add POST /api/sessions | 5.0 |" in md
    effort = [i for i in b.issues if i.rule == "effort_total"]
    assert effort and effort[0].severity == "warning"                                    # 3 SP = 18 h vs 10 h of tasks
    system = {c["system"] for c in fake.calls}
    assert len(system) == 1 and "POST /api/sessions" in system.pop()                     # one shared, cacheable prefix


def test_unchanged_stories_are_never_sent_again(proj, monkeypatch):
    fake = FakeModel()
    monkeypatch.setattr(tb, "_invoke", fake)
    run(tb.generate(P, "", []))
    assert len(fake.calls) == 2
    run(tb.generate(P, "", []))
    assert len(fake.calls) == 2
    changed = snapshot()
    changed["stories"][1]["acceptance_criteria"][1]["text"] = "Given an account, When it is wrong 5 times, Then it locks."
    (proj / "phase4/stories.json").write_text(json.dumps(changed))
    run(tb.generate(P, "", []))
    assert [c["key"] for c in fake.calls[2:]] == ["GR-10"]
    assert json.loads(backlog.validate_report(P, write=False))["ready_for_review"]


def test_first_call_runs_alone_then_the_rest_in_parallel(proj, monkeypatch):
    stories = snapshot()
    for n in range(11, 15):
        extra = json.loads(json.dumps(stories["stories"][1]))
        extra["key"], extra["blocks"] = f"GR-{n}", []
        stories["stories"].append(extra)
    (proj / "phase4/stories.json").write_text(json.dumps(stories))
    fake = FakeModel()
    order = []
    async def tracked(*args):
        order.append(("start", fake.active))
        return await fake(*args)
    monkeypatch.setattr(tb, "_invoke", tracked)
    run(tb.generate(P, "", []))
    assert order[0] == ("start", 0) and fake.max_active > 1 and len(fake.calls) == 6


def test_a_failed_check_is_retried_once_then_reported(proj, monkeypatch):
    fake = FakeModel(broken={"GR-9"})
    monkeypatch.setattr(tb, "_invoke", fake)
    run(tb.generate(P, "", []))
    assert [c["retry"] for c in fake.calls if c["key"] == "GR-9"] == [False, True]

    async def always_broken(schema, system, human, callbacks, spec):
        result = good("GR-9", "US-001")
        result.tasks[0].hours = 40
        return result
    monkeypatch.setattr(tb, "_invoke", always_broken)
    with pytest.raises(files.ProjectError, match="hours must be > 0 and <= 16"):
        run(tb.breakdown_story(P, tb.snapshot(P).stories[0], tb._settings(P), "prefix", []))


def test_reviewer_request_naming_a_story_regenerates_only_that_story(proj, monkeypatch):
    fake = FakeModel()
    monkeypatch.setattr(tb, "_invoke", fake)
    run(tb.generate(P, "", []))
    run(tb.generate(P, "Gate P4-G1: changes requested: GR-10 needs a lockout task.", []))
    assert [c["key"] for c in fake.calls[2:]] == ["GR-10"]
    assert "lockout" in fake.calls[2]["payload"]["reviewer_request"]


def test_review_is_deterministic_and_repair_targets_only_the_named_story(proj, monkeypatch):
    fake = FakeModel()
    monkeypatch.setattr(tb, "_invoke", fake)
    run(tb.generate(P, "", []))
    verdict = run(tb.review(P))["structured_response"]
    assert verdict.satisfied and verdict.status_so_far == "success" and len(fake.calls) == 2
    finding = json.dumps({"rule": "acceptance_criteria", "item_ids": ["GR-10-T02"], "message": "vague criterion"})
    run(tb.repair(P, [finding], []))
    assert [c["key"] for c in fake.calls[2:]] == ["GR-10"]
    assert fake.calls[2]["payload"]["findings_to_fix"] == ["vague criterion"]
    run(tb.generate(P, "", []))
    assert len(fake.calls) == 3                       # the repaired story is kept, not regenerated
    run(tb.repair(P, [finding], []))                  # the backlog changed since: a second attempt is allowed
    with pytest.raises(files.ProjectError, match="same findings remain"):
        run(tb.repair(P, [finding], []))              # that attempt changed nothing: stop for the Tech Lead


def test_missing_coverage_and_disciplines_block_review(proj, monkeypatch):
    monkeypatch.setattr(tb, "_invoke", FakeModel())
    run(tb.generate(P, "", []))
    doc = json.loads((proj / files.BACKLOG).read_text())
    for item in doc["items"]:
        if item["item_id"].startswith("GR-9-T"):
            item["source_refs"] = []
        if item["item_id"] == "GR-10-T01":
            item["discipline"] = None
    (proj / files.BACKLOG).write_text(json.dumps(doc))
    report = json.loads(backlog.validate_report(P, write=False))
    rules = {b["rule"] for b in report["blocking"]}
    assert {"acceptance_coverage", "discipline"} <= rules
    verdict = run(tb.review(P))["structured_response"]
    assert not verdict.satisfied and any("acceptance_coverage" in g for g in verdict.gaps)


def test_changed_architecture_makes_the_backlog_stale(proj, monkeypatch):
    monkeypatch.setattr(tb, "_invoke", FakeModel())
    run(tb.generate(P, "", []))
    (proj / "architecture.md").write_text("# Architecture v2\n")
    report = json.loads(backlog.validate_report(P, write=False))
    assert any(b["rule"] == "stale_sources" for b in report["blocking"])


def test_anthropic_calls_send_the_shared_prefix_as_a_cached_block(monkeypatch):
    seen = {}

    class Structured:
        async def ainvoke(self, messages, config=None):
            seen["messages"] = messages
            return good("GR-9", "US-001")

    class Model:
        max_tokens = 64000

        def with_structured_output(self, schema, **kw):
            seen["kw"] = kw
            return Structured()

    from agent_engine import model_setup
    monkeypatch.setattr(model_setup, "resolve_model_with_retries", lambda spec: Model())
    run(tb._invoke(tb.StoryBreakdown, "SHARED PREFIX", "story", [], "anthropic:claude-sonnet-5-5"))
    system = seen["messages"][0].content
    assert system == [{"type": "text", "text": "SHARED PREFIX", "cache_control": {"type": "ephemeral"}}]
    assert seen["kw"] == {"method": "json_schema"}
    run(tb._invoke(tb.StoryBreakdown, "SHARED PREFIX", "story", [], "openai:gpt"))
    assert seen["messages"][0].content == "SHARED PREFIX"


def test_cli_run_writes_checks_and_verifies_without_a_review_model(proj, monkeypatch, tmp_path):
    from agent_engine import cli, logging_setup
    from phase4_helpers import approve_design_gates
    approve_design_gates(proj)
    monkeypatch.setattr(cli, "OUTPUTS_DIR", proj.parent)
    monkeypatch.setattr(logging_setup, "OUTPUTS_DIR", proj.parent)
    monkeypatch.setattr(logging_setup, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(cli, "build_langfuse_handler", lambda: None)
    monkeypatch.setattr(cli, "build_agent", lambda *a, **k: pytest.fail("no deep agent is built for Task Breakdown"))
    fake = FakeModel()
    monkeypatch.setattr(tb, "_invoke", fake)
    assert asyncio.run(cli._run("Break the approved stories down into tasks.", "task-breakdown", P)) == 0
    report = json.loads((proj / "report.json").read_text())
    assert report["status"] == "success" and report["verified"] and report["verdict"]["satisfied"]
    assert [p["kind"] for p in report["passes"]] == ["write", "verify"] and len(fake.calls) == 2


# ---------------------------------------------------------------------------------------------- cross-story pass
def edge(item, on, confidence=0.9, reason="needs it"):
    return tb.CrossDependency(item_id=item, on_id=on, reason=reason, confidence=confidence)


def shared(keep, dups, confidence=0.9):
    return tb.SharedWork(keep_id=keep, duplicate_ids=dups, reason="same users column", confidence=confidence)


def test_cross_story_pass_runs_once_on_the_shared_prefix_and_is_retained(proj, monkeypatch):
    fake = FakeModel()
    monkeypatch.setattr(tb, "_invoke", fake)
    run(tb.generate(P, "", []))
    assert len(fake.cross_calls) == 1
    call = fake.cross_calls[0]
    assert call["system"] == fake.calls[0]["system"]                       # reads the cache the story calls wrote
    assert [r["story"] for r in call["index"]] == ["GR-9", "GR-10"]
    assert call["index"][0]["tasks"][1] == {"id": "GR-9-T02", "discipline": "BE", "title": "Add POST /api/sessions",
                                            "description": "Endpoint.", "depends_on": ["GR-9-T01"]}
    run(tb.generate(P, "", []))
    assert len(fake.cross_calls) == 1                                      # nothing changed: no new call
    changed = snapshot(summary="Owner signs in")
    (proj / "phase4/stories.json").write_text(json.dumps(changed))
    run(tb.generate(P, "", []))
    assert len(fake.cross_calls) == 2


def test_confident_cross_story_edges_are_added_and_the_rest_become_questions(proj, monkeypatch):
    review = tb.CrossStoryReview(shared_work=[], dependencies=[
        edge("GR-10-T02", "GR-9-T01", 0.85),            # added
        edge("GR-10-T03", "GR-9-T02", 0.4),             # question
        edge("GR-9-T02", "GR-9-T01"),                   # same story: ignored
        edge("GR-10", "GR-9"),                          # Jira already says GR-9 blocks GR-10: ignored
        edge("GR-10-T02", "GR-9"),                      # mixed levels: ignored
        edge("GR-77-T01", "GR-9-T01")])                 # unknown id: ignored
    monkeypatch.setattr(tb, "_invoke", FakeModel(cross=review))
    run(tb.generate(P, "", []))
    by = files.read_json(P, files.BACKLOG, Backlog).by_id()
    added = [d for d in by["GR-10-T02"].dependencies if d.on_id == "GR-9-T01"]
    assert len(added) == 1 and added[0].origin == "llm" and added[0].confidence == 0.85
    assert not any(d.on_id == "GR-9-T02" for d in by["GR-10-T03"].dependencies)
    assert by["GR-10-T03"].open_questions == ["Possible dependency on GR-9-T02 (0.4): needs it"]
    assert [d.on_id for d in by["GR-10"].dependencies] == ["GR-9"]
    assert json.loads(backlog.validate_report(P, write=False))["ready_for_review"]


def test_shared_work_is_merged_into_one_task_that_serves_both_stories(proj, monkeypatch):
    review = tb.CrossStoryReview(dependencies=[], shared_work=[shared("GR-9-T01", ["GR-10-T01"])])
    monkeypatch.setattr(tb, "_invoke", FakeModel(cross=review))
    run(tb.generate(P, "", []))
    b = files.read_json(P, files.BACKLOG, Backlog)
    by = b.by_id()
    assert "GR-10-T01" not in by
    assert [d.on_id for d in by["GR-10-T02"].dependencies] == ["GR-9-T01"]      # rewired to the kept task
    assert "Shared work: also serves GR-10 in place of GR-10-T01" in by["GR-9-T01"].open_questions[0]
    assert by["GR-10"].estimate.story_points == 1                              # 8 h left at 6 h/SP (was 10 h -> 2)
    assert by["GR-9"].estimate.story_points == 3                               # Jira points are never recomputed
    assert json.loads(backlog.validate_report(P, write=False))["ready_for_review"]


def test_unsafe_or_unsure_merges_are_only_questions(proj, monkeypatch):
    review = tb.CrossStoryReview(dependencies=[], shared_work=[
        shared("GR-9-T03", ["GR-10-T03"]),                 # QA work is never shared
        shared("GR-9-T01", ["GR-10-T02"]),                 # different disciplines
        shared("GR-9-T02", ["GR-10-T02"], 0.7)])           # not sure enough
    monkeypatch.setattr(tb, "_invoke", FakeModel(cross=review))
    run(tb.generate(P, "", []))
    by = files.read_json(P, files.BACKLOG, Backlog).by_id()
    assert {"GR-10-T01", "GR-10-T02", "GR-10-T03"} <= set(by)
    assert any(q.startswith("Possibly the same work as GR-10-T03") for q in by["GR-9-T03"].open_questions)
    assert any(q.startswith("Possibly the same work as GR-10-T02 (0.7)") for q in by["GR-9-T02"].open_questions)


def test_a_single_story_needs_no_cross_story_call(proj, monkeypatch):
    one = snapshot()
    one["stories"] = one["stories"][:1]
    one["stories"][0]["blocks"] = []
    (proj / "phase4/stories.json").write_text(json.dumps(one))
    fake = FakeModel()
    monkeypatch.setattr(tb, "_invoke", fake)
    run(tb.generate(P, "", []))
    assert fake.cross_calls == [] and len(fake.calls) == 1


# ---------------------------------------------------------------------------------------------- validation step
def finding(item, severity="blocking", message="criterion cannot be tested"):
    return tb.ReviewFinding(item_id=item, severity=severity, message=message)


def points(proj, gr9=3, gr10=None):
    stories = snapshot(points=(gr9, gr10))
    (proj / "phase4/stories.json").write_text(json.dumps(stories))


def test_effort_mismatch_only_when_the_hours_point_to_another_size(proj, monkeypatch):
    monkeypatch.setattr(tb, "_invoke", FakeModel())
    points(proj, gr9=2)                                  # 10 h at 6 h/SP is about 2 SP: agrees
    run(tb.generate(P, "", []))
    assert not [i for i in files.read_json(P, files.BACKLOG, Backlog).issues if i.rule == "effort_total"]
    points(proj, gr9=5)                                  # 10 h is not 5 SP
    run(tb.generate(P, "", []))
    issue = next(i for i in files.read_json(P, files.BACKLOG, Backlog).issues if i.rule == "effort_total")
    assert issue.item_ids == ["GR-9"] and "about 2 SP" in issue.message and issue.severity == "warning"


def test_vague_task_criteria_are_flagged_unless_measured(proj, monkeypatch):
    monkeypatch.setattr(tb, "_invoke", FakeModel())
    run(tb.generate(P, "", []))
    doc = json.loads((proj / files.BACKLOG).read_text())
    for item in doc["items"]:
        if item["item_id"] == "GR-9-T02":
            item["acceptance_criteria"][0]["text"] = "WHEN signing in THE SYSTEM SHALL respond fast"
        if item["item_id"] == "GR-10-T02":
            item["acceptance_criteria"][0]["text"] = "WHEN signing in THE SYSTEM SHALL respond fast, within 2 seconds"
    (proj / files.BACKLOG).write_text(json.dumps(doc))
    _, issues = backlog.validate(P, write=False)
    vague = next(i for i in issues if i.rule == "vague_criteria")
    assert vague.item_ids == ["GR-9-T02"] and vague.severity == "warning"


def test_nothing_flagged_means_no_review_call(proj, monkeypatch):
    points(proj, gr9=2)
    fake = FakeModel()
    monkeypatch.setattr(tb, "_invoke", fake)
    run(tb.generate(P, "", []))
    verdict = run(tb.review(P))["structured_response"]
    assert verdict.satisfied and fake.review_calls == [] and "Reviewed 0 flagged items" in verdict.summary


def test_review_looks_only_at_flagged_items_and_blocking_findings_become_gaps(proj, monkeypatch):
    points(proj, gr9=5)                                  # GR-9 effort mismatch; GR-10 is clean
    review = tb.LightReview(findings=[
        finding("GR-9-T02"), finding("GR-9", "warning", "points depend on lockout decision"),
        finding("GR-10-T01", "blocking", "not flagged, so ignored")])
    fake = FakeModel(review=review)
    monkeypatch.setattr(tb, "_invoke", fake)
    run(tb.generate(P, "", []))
    verdict = run(tb.review(P))["structured_response"]
    assert len(fake.review_calls) == 1
    call = fake.review_calls[0]
    assert [i["flagged"] for i in call["payload"]["items"]] == [{"GR-9": ["effort_mismatch"]}]
    assert call["system"] == fake.calls[0]["system"]                       # same cached prefix as the story calls
    assert call["human"].startswith("You are the Backlog Reviewer")
    assert not verdict.satisfied and verdict.status_so_far == "partial"
    assert [json.loads(g)["item_ids"] for g in verdict.gaps] == [["GR-9-T02"]]
    assert "GR-9: points depend on lockout decision" in verdict.summary
    run(tb.review(P))
    assert len(fake.review_calls) == 1                                     # unchanged: the review is reused


def test_low_confidence_tasks_are_reviewed(proj, monkeypatch):
    points(proj, gr9=2)
    fake = FakeModel()
    monkeypatch.setattr(tb, "_invoke", fake)
    run(tb.generate(P, "", []))
    doc = json.loads((proj / files.BACKLOG).read_text())
    for item in doc["items"]:
        if item["item_id"] == "GR-10-T03":
            item["estimate"]["confidence"] = "low"
    (proj / files.BACKLOG).write_text(json.dumps(doc))
    run(tb.review(P))
    assert [i["flagged"] for i in fake.review_calls[0]["payload"]["items"]] == [{"GR-10-T03": ["low_confidence"]}]


def test_escalated_fix_uses_the_bigger_model_only_for_affected_stories(proj, monkeypatch):
    from agent_engine import agent
    monkeypatch.setattr(tb, "_spec", REAL_SPEC)
    monkeypatch.setattr(tb, "_identity_spec", REAL_IDENTITY_SPEC)
    monkeypatch.setattr(agent, "model_spec", lambda tier: f"test:{tier}")
    pack = agent.load_pack("task-breakdown")
    assert pack.models == ["strong", "frontier"]
    fake = FakeModel()
    monkeypatch.setattr(tb, "_invoke", fake)
    with tb.operation_model(pack, 0):
        run(tb.generate(P, "", []))
    gap = json.dumps({"rule": "review", "item_ids": ["GR-10-T02"], "message": "fix the criterion"})
    with tb.operation_model(pack, 1):
        run(tb.repair(P, [gap], []))
    assert [(c["key"], c["spec"]) for c in fake.calls] == [
        ("GR-9", "test:strong"), ("GR-10", "test:strong"), ("GR-10", "test:frontier")]
    with tb.operation_model(pack, 0):
        run(tb.generate(P, "", []))
    assert len(fake.calls) == 3                          # the repair is kept; nothing is regenerated


def test_frontier_tier_resolution(monkeypatch):
    from agent_engine import agent, config
    monkeypatch.setenv("SDLC_AGENT_STRONG_MODEL", "anthropic:claude-sonnet-5-5")
    monkeypatch.setenv("SDLC_AGENT_FAST_MODEL", "anthropic:claude-haiku-4-5-20251001")
    monkeypatch.delenv("SDLC_AGENT_FRONTIER_MODEL", raising=False)
    assert agent.model_spec("frontier") == "anthropic:claude-opus-5-5"
    monkeypatch.setenv("SDLC_AGENT_FRONTIER_MODEL", "anthropic:custom-frontier")
    assert agent.model_spec("frontier") == "anthropic:custom-frontier"
    monkeypatch.delenv("SDLC_AGENT_FRONTIER_MODEL")
    monkeypatch.setenv("SDLC_AGENT_STRONG_MODEL", "openai:gpt-x")
    monkeypatch.setenv("SDLC_AGENT_FAST_MODEL", "openai:gpt-x-mini")
    assert agent.model_spec("frontier") == "openai:gpt-x"            # no bigger model known: stays on strong


def test_cli_failed_review_escalates_one_fix_then_succeeds(proj, monkeypatch, tmp_path):
    from agent_engine import agent, cli, logging_setup
    from phase4_helpers import approve_design_gates
    approve_design_gates(proj)
    points(proj, gr9=5)
    for module in (agent, cli):
        monkeypatch.setattr(module, "model_spec", lambda tier: f"test:{tier}")
    monkeypatch.setattr(tb, "_spec", REAL_SPEC)
    monkeypatch.setattr(tb, "_identity_spec", REAL_IDENTITY_SPEC)
    monkeypatch.setattr(cli, "OUTPUTS_DIR", proj.parent)
    monkeypatch.setattr(logging_setup, "OUTPUTS_DIR", proj.parent)
    monkeypatch.setattr(logging_setup, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(cli, "build_langfuse_handler", lambda: None)
    fake = FakeModel(review=[tb.LightReview(findings=[finding("GR-9-T02")]), tb.LightReview(findings=[])])
    monkeypatch.setattr(tb, "_invoke", fake)
    assert asyncio.run(cli._run("Break the approved stories down into tasks.", "task-breakdown", P)) == 0
    report = json.loads((proj / "report.json").read_text())
    assert [(p["kind"], p["model_tier"]) for p in report["passes"]] == [
        ("write", "strong"), ("verify", "strong"), ("fix", "frontier"), ("verify", "strong")]
    assert report["status"] == "success" and len(fake.review_calls) == 2
    assert [(c["key"], c["spec"]) for c in fake.calls] == [
        ("GR-9", "test:strong"), ("GR-10", "test:strong"), ("GR-9", "test:frontier")]


def test_backlog_carries_the_roadmap_without_regenerating_on_reorder(proj, monkeypatch):
    stories = snapshot()
    stories["releases"] = [{"name": "MVP", "order": 1, "release_date": "2027-01-29"}, {"name": "R2", "order": 2}]
    stories["stories"][0].update(fix_versions=["MVP"], rank="0|i000hb:")
    stories["stories"][1].update(fix_versions=["R2", "MVP"], rank="0|i000h2:")
    (proj / "phase4/stories.json").write_text(json.dumps(stories))
    fake = FakeModel()
    monkeypatch.setattr(tb, "_invoke", fake)
    run(tb.generate(P, "", []))
    b = files.read_json(P, files.BACKLOG, Backlog)
    by = b.by_id()
    assert (by["GR-9"].release, by["GR-9"].rank) == ("MVP", "0|i000hb:")
    assert by["GR-10"].release == "MVP"                   # earliest fix version on the roadmap
    assert [r.name for r in b.releases] == ["MVP", "R2"]
    assert "release MVP" in (proj / files.BACKLOG_MD).read_text() and "Roadmap: MVP (2027-01-29) → R2" in (proj / files.BACKLOG_MD).read_text()
    calls = len(fake.calls)
    stories["stories"][0]["rank"] = "0|i000zz:"            # reordered in Jira
    (proj / "phase4/stories.json").write_text(json.dumps(stories))
    run(tb.generate(P, "", []))
    assert len(fake.calls) == calls and files.read_json(P, files.BACKLOG, Backlog).by_id()["GR-9"].rank == "0|i000zz:"


def test_a_proposed_link_against_the_tracker_order_becomes_a_question(proj, monkeypatch):
    # Jira: GR-9 blocks GR-10. The model proposes the opposite (a GR-9 task waiting on a GR-10 task).
    review = tb.CrossStoryReview(shared_work=[], dependencies=[edge("GR-9-T02", "GR-10-T01", 0.8, "needs the table")])
    monkeypatch.setattr(tb, "_invoke", FakeModel(cross=review))
    run(tb.generate(P, "", []))
    by = files.read_json(P, files.BACKLOG, Backlog).by_id()
    assert not any(d.on_id == "GR-10-T01" for d in by["GR-9-T02"].dependencies)
    assert any("contradicts the existing story order (GR-10 already waits for GR-9)" in q
               for q in by["GR-9-T02"].open_questions)
    assert json.loads(backlog.validate_report(P, write=False))["ready_for_review"]


def test_validation_breaks_a_loop_made_by_a_model_link(proj, monkeypatch):
    monkeypatch.setattr(tb, "_invoke", FakeModel())
    run(tb.generate(P, "", []))
    doc = json.loads((proj / files.BACKLOG).read_text())
    for item in doc["items"]:                    # bypass screening: a model link against Jira's GR-9 -> GR-10
        if item["item_id"] == "GR-9-T02":
            item["dependencies"].append({"on_id": "GR-10-T01", "reason": "x", "confidence": 0.7, "origin": "llm"})
    (proj / files.BACKLOG).write_text(json.dumps(doc))
    _, issues = backlog.validate(P)
    loop = [i for i in issues if i.rule == "dependency_cycle"]
    assert loop and loop[0].severity == "warning" and loop[0].item_ids == ["GR-9-T02"]
    assert not any(i.severity == "blocking" for i in issues)


def test_findings_without_story_ids_rebuild_from_retained_results(proj, monkeypatch):
    fake = FakeModel()
    monkeypatch.setattr(tb, "_invoke", fake)
    run(tb.generate(P, "", []))
    calls = len(fake.calls)
    old = json.dumps({"rule": "dependency_cycle", "item_ids": [], "message": "story graph has a cycle"})
    run(tb.repair(P, [old], []))
    assert len(fake.calls) == calls                       # rebuilt from retained results, no new story calls
    assert json.loads(backlog.validate_report(P, write=False))["ready_for_review"]


def test_only_a_reviewer_decision_may_leave_a_criterion_unplanned(proj):
    """A gate decision ("do not build US-001.AC2") is expressed as a deferred criterion, never as a missing one."""
    from agent_engine.phase4 import files as phase4_files
    from agent_engine.phase4.contracts import ProjectSettings
    snap = tb.StorySnapshot.model_validate(snapshot())
    story = next(s for s in snap.stories if s.key == "GR-9")
    settings = phase4_files.read_json(P, phase4_files.PROJECT_SETTINGS, ProjectSettings)
    result = good("GR-9", "US-001")
    for t in result.tasks:
        t.covers = [c for c in t.covers if c != "US-001.AC2"]
    assert any("no task covers acceptance criteria ['US-001.AC2']" in e for e in tb.check_breakdown(story, result, settings))
    result.deferred_criteria = [tb.DeferredCriterion(ac_id="US-001.AC2", reason="Out of scope per PRD section 3 (P4-G1 decision)")]
    assert any("only for criteria a reviewer_request" in e for e in tb.check_breakdown(story, result, settings))
    assert tb.check_breakdown(story, result, settings, deferrable=True) == []
    items = tb.story_items(story, "GR-1", result, settings)
    assert any("US-001.AC2 is not planned (reviewer decision)" in q for q in items[-1].open_questions + items[0].open_questions)
    story_item = next(i for i in items if i.level == "story")
    assert story_item.deferred_criteria == ["US-001.AC2"]     # backlog validation counts it as decided, not missing
    result.tasks[1].covers.append("US-001.AC2")
    assert any("both deferred and covered" in e for e in tb.check_breakdown(story, result, settings, deferrable=True))


def test_a_repair_keeps_the_reviewer_request_the_story_was_generated_with(proj, monkeypatch):
    import asyncio
    seen = []
    async def fake(project, story, settings, prefix, callbacks, *, request="", findings=(), spec=None):
        seen.append((story.key, request, tuple(findings)))
        us = "US-001" if story.key == "GR-9" else "US-002"
        return good(story.key, us)
    monkeypatch.setattr(tb, "breakdown_story", fake)
    monkeypatch.setattr(tb, "_invoke", FakeModel())
    asyncio.run(tb.generate(P, "Gate P4-G1 decision: do not build US-001.AC2 in GR-9.", []))
    assert ("GR-9", "Gate P4-G1 decision: do not build US-001.AC2 in GR-9.", ()) in seen
    assert ("GR-10", "", ()) in seen
    seen.clear()
    finding = json.dumps({"rule": "review", "severity": "blocking", "item_ids": ["GR-9-T02"], "message": "Fix T2"})
    asyncio.run(tb.repair(P, [finding], []))
    assert [(k, r) for k, r, f in seen] == [("GR-9", "Gate P4-G1 decision: do not build US-001.AC2 in GR-9.")]



def test_the_light_review_sees_reviewer_decisions(proj, monkeypatch):
    """Without the decision the reviewer re-flags a settled conflict and the repair undoes the deferral."""
    import asyncio
    async def fake(project, story, settings, prefix, callbacks, *, request="", findings=(), spec=None):
        result = good(story.key, "US-001" if story.key == "GR-9" else "US-002")
        if story.key == "GR-9":
            for t in result.tasks:
                t.covers = [c for c in t.covers if c != "US-001.AC2"]
                t.acceptance_criteria = ["Given it, When run, Then the result is fast."]        # flags a review
            result.deferred_criteria = [tb.DeferredCriterion(ac_id="US-001.AC2", reason="Out of scope (P4-G1)")]
        return result
    monkeypatch.setattr(tb, "breakdown_story", fake)
    model = FakeModel()
    monkeypatch.setattr(tb, "_invoke", model)
    asyncio.run(tb.generate(P, "P4-G1 decision for GR-9: defer US-001.AC2.", []))
    asyncio.run(tb.review(P))
    payloads = [c for c in model.review_calls]
    assert payloads and any('"decided_by_reviewer"' in str(c) and "US-001.AC2" in str(c) for c in payloads)


def test_stories_outside_a_repair_keep_their_decided_result(proj, monkeypatch):
    """Repairing GR-10 must not swap GR-9 back to a result generated before the reviewer's decision."""
    import asyncio
    calls = []
    async def fake(project, story, settings, prefix, callbacks, *, request="", findings=(), spec=None):
        calls.append((story.key, request, bool(findings)))
        result = good(story.key, "US-001" if story.key == "GR-9" else "US-002")
        result.open_questions = [f"made with request: {request!r}"]
        return result
    monkeypatch.setattr(tb, "breakdown_story", fake)
    monkeypatch.setattr(tb, "_invoke", FakeModel())
    asyncio.run(tb.generate(P, "", []))                                   # before any decision
    asyncio.run(tb.generate(P, "P4-G1 decision for GR-9: follow the PRD.", []))
    calls.clear()
    finding = json.dumps({"rule": "review", "severity": "blocking", "item_ids": ["GR-10-T02"], "message": "Fix T2"})
    asyncio.run(tb.repair(P, [finding], []))
    assert calls == [("GR-10", "", True)]
    from agent_engine.phase4 import files as phase4_files
    from agent_engine.phase4.contracts import Backlog
    gr9 = phase4_files.read_json(P, phase4_files.BACKLOG, Backlog).by_id()["GR-9"]
    assert any("P4-G1 decision for GR-9" in q for q in gr9.open_questions)
