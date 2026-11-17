"""Approved stories come from Jira (read-only) into phase4/stories.json, and Task Breakdown may only run after the
design (G3A) and architecture (G3B) gates are approved. No network: Jira is a fake client."""
from __future__ import annotations

import json

import pytest

from agent_engine import config, gates
from agent_engine.phase4 import files, orchestrator as orch, story_import
from agent_engine.phase4.contracts import StorySnapshot

from phase4_helpers import approve_design_gates, write_stories
from test_phase4_orchestrator import FakeAgents, P, PROJECT, go


# ---------------------------------------------------------------------------------------------- fake Jira
def text(t):
    return {"type": "text", "text": t}


def para(t):
    return {"type": "paragraph", "content": [text(t)]}


def heading(t):
    return {"type": "heading", "attrs": {"level": 3}, "content": [text(t)]}


def bullets(*items):
    return {"type": "bulletList", "content": [{"type": "listItem", "content": [para(i)]} for i in items]}


def story_description(us, approved=True):
    return {"type": "doc", "version": 1, "content": [
        para("As front-desk staff, I want to sign in so that I see my screens."),
        heading("Acceptance criteria"),
        bullets(f"{us}.AC1: Given an account, When the password is right, Then the user is signed in.",
                f"{us}.AC2: Given an account, When the password is wrong, Then sign-in fails."),
        heading("Notes"), para("Applies to managers too. See NFR-010."),
        heading("Traceability"), para(f"Story {us} · Epic EPIC-01 · Traces FR-002 · MoSCoW Must"),
        *([para("Approved at gate G2 on 2026-11-13T13:42:55+00:00.")] if approved else []),
    ]}


def issue(key, us, *, approved=True, kind="Story", points=3.0, blocks=(), parent="DEMO-1"):
    return {"id": key.split("-")[1], "key": key, "fields": {
        "summary": f"Story {key}", "description": story_description(us, approved),
        "labels": [us, "FR-002", "P-02", "moscow-must"], "priority": {"name": "Medium"},
        "fixVersions": [{"name": "MVP"}], "components": [{"name": "MOD-01 Accounts"}],
        "parent": {"key": parent, "fields": {"issuetype": {"name": "Epic"}}},
        "issuelinks": [{"type": {"name": "Blocks", "outward": "blocks"}, "outwardIssue": {"key": b}} for b in blocks],
        "status": {"name": "To Do"}, "issuetype": {"name": kind}, "project": {"key": "DEMO"},
        "customfield_10016": points, "customfield_10036": None}}


EPIC = {"id": "1", "key": "DEMO-1", "fields": {
    "summary": "Access", "issuetype": {"name": "Epic"}, "labels": ["EPIC-01"],
    "description": {"type": "doc", "content": [para("Epic EPIC-01. Functional requirements: FR-001, FR-002.")]}}}
NAMES = {"customfield_10016": "Story point estimate", "customfield_10036": "Story Points"}


class Response:
    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data


class FakeJira:
    """Serves /search/jql in pages; records every call. It has no post/put/delete: only reads are possible."""

    def __init__(self, stories, page=2):
        self.stories, self.page, self.calls = stories, page, []

    def get(self, url, params=None):
        self.calls.append(("GET", url, dict(params or {})))
        assert url == "/rest/api/3/search/jql"
        if params["jql"].startswith("key in"):
            return Response({"issues": [EPIC], "isLast": True})
        start = int(params.get("nextPageToken") or 0)
        chunk = self.stories[start:start + self.page]
        more = start + self.page < len(self.stories)
        return Response({"issues": chunk, "names": NAMES, "isLast": not more,
                         **({"nextPageToken": str(start + self.page)} if more else {})})


@pytest.fixture
def jira_project(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUTS_DIR", tmp_path / "outputs")
    root = tmp_path / "outputs" / P
    (root / "phase4").mkdir(parents=True)
    project = json.loads((config.ASSETS_ROOT / "examples/phase4/taskflow/phase4/project.json").read_text())
    (root / "phase4/project.json").write_text(json.dumps({**project, "project_name": P}))
    for key, value in {"PHASE4_TRACKER": "jira", "JIRA_BASE_URL": "https://demo.atlassian.net",
                       "JIRA_PROJECT_KEY": "DEMO", "JIRA_BOARD_ID": "3",
                       "JIRA_EMAIL": "user@example.test", "JIRA_API_TOKEN": "test-secret"}.items():
        monkeypatch.setenv(key, value)
    return root


STORIES = [issue("DEMO-9", "US-001", blocks=["DEMO-10"]), issue("DEMO-10", "US-002", points=None),
           issue("DEMO-11", "US-003", approved=False), issue("DEMO-12", "US-004", kind="Bug")]


# ---------------------------------------------------------------------------------------------- parsing
def test_story_is_kept_exactly_with_its_own_criteria_ids_and_traceability():
    s = story_import.parse_story(STORIES[0], "customfield_10016")
    assert s.statement.startswith("As front-desk staff, I want")
    assert [(c.ac_id, c.text[:26]) for c in s.acceptance_criteria] == [
        ("US-001.AC1", "Given an account, When the"), ("US-001.AC2", "Given an account, When the")]
    assert s.notes.startswith("Applies to managers") and "MoSCoW Must" in s.traceability
    assert s.requirement_ids == ["US-001", "FR-002"] and s.persona_ids == ["P-02"] and s.moscow == "must"
    assert (s.epic_key, s.story_points, s.blocks, s.fix_versions) == ("DEMO-1", 3.0, ["DEMO-10"], ["MVP"])
    assert s.approval.startswith("Approved at gate G2")


def test_plain_markdown_descriptions_and_unnumbered_criteria_are_parsed():
    raw = issue("DEMO-20", "US-020")
    raw["fields"]["description"] = ("As a member, I want to pay online so that I renew quickly.\n\n"
                                    "Acceptance criteria:\n- Given a plan, When I pay, Then it renews.\n"
                                    "- Given a failed payment, When I retry, Then I see why.\n")
    s = story_import.parse_story(raw, approval_marker="")
    assert s.statement.startswith("As a member")
    assert [c.ac_id for c in s.acceptance_criteria] == ["DEMO-20.AC1", "DEMO-20.AC2"]


def test_points_field_is_the_populated_one_not_the_board_field(monkeypatch):
    assert story_import._points_field(STORIES, NAMES) == "customfield_10016"
    monkeypatch.setenv("JIRA_STORY_POINTS_FIELD_ID", "customfield_10036")
    assert story_import._points_field(STORIES, NAMES) == "customfield_10036"


# ---------------------------------------------------------------------------------------------- import
def test_import_reads_only_and_writes_a_content_only_snapshot(jira_project):
    fake = FakeJira(STORIES)
    result = story_import.import_stories(P, http=fake)
    assert all(method == "GET" for method, *_ in fake.calls)
    first = fake.calls[0][2]
    assert first["jql"] == 'project = "DEMO" AND issuetype = Story AND statusCategory = "To Do" ORDER BY key ASC'
    assert len([c for c in fake.calls if not c[2]["jql"].startswith("key in")]) == 2   # followed the page token
    snap = files.read_json(P, files.STORIES, StorySnapshot)
    assert [s.key for s in snap.stories] == ["DEMO-9", "DEMO-10"]
    assert {e.key: e.reason[:20] for e in snap.excluded} == {"DEMO-11": "description has no a",
                                                             "DEMO-12": "issue type Bug is no"}
    assert [e.key for e in snap.epics] == ["DEMO-1"] and snap.epics[0].requirement_ids == ["FR-001", "FR-002"]
    assert snap.story_points_field == "customfield_10016"
    assert result["changed"] and result["without_story_points"] == ["DEMO-10"]
    before = (jira_project / files.STORIES).read_bytes()
    again = story_import.import_stories(P, http=FakeJira(STORIES))
    assert not again["changed"] and (jira_project / files.STORIES).read_bytes() == before


def test_custom_jql_and_no_approval_check(jira_project, monkeypatch):
    monkeypatch.setenv("JIRA_STORY_JQL", 'project = "DEMO" AND labels = ready')
    monkeypatch.setenv("PHASE4_STORY_APPROVAL_MARKER", "")
    fake = FakeJira(STORIES)
    story_import.import_stories(P, http=fake)
    assert fake.calls[0][2]["jql"] == 'project = "DEMO" AND labels = ready'
    snap = files.read_json(P, files.STORIES, StorySnapshot)
    assert [s.key for s in snap.stories] == ["DEMO-9", "DEMO-10", "DEMO-11"]


def test_no_approved_story_is_an_error_and_keeps_the_previous_snapshot(jira_project):
    story_import.import_stories(P, http=FakeJira(STORIES))
    before = (jira_project / files.STORIES).read_bytes()
    with pytest.raises(files.ProjectError, match="no approved stories"):
        story_import.import_stories(P, http=FakeJira([STORIES[2]]))
    assert (jira_project / files.STORIES).read_bytes() == before


def test_local_tracker_uses_a_provided_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUTS_DIR", tmp_path / "outputs")
    root = tmp_path / "outputs" / P
    (root / "phase4").mkdir(parents=True)
    project = json.loads((config.ASSETS_ROOT / "examples/phase4/taskflow/phase4/project.json").read_text())
    (root / "phase4/project.json").write_text(json.dumps({**project, "project_name": P}))
    with pytest.raises(files.ProjectError, match="stories.json is missing"):
        story_import.import_stories(P)
    write_stories(root)
    assert story_import.import_stories(P)["stories"] == 1


# ---------------------------------------------------------------------------------------------- gates
@pytest.fixture
def bare(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUTS_DIR", tmp_path / "outputs")
    root = tmp_path / "outputs" / P
    (root / "phase4").mkdir(parents=True)
    (root / "phase4/project.json").write_text(json.dumps(PROJECT))
    (root / "prd.md").write_text("prd")
    (root / "architecture.md").write_text("arch")
    write_stories(root)
    return root


def test_task_breakdown_waits_for_design_and_architecture_approval(bare):
    lines = []
    fake = FakeAgents(bare)
    assert orch.orchestrate(P, runner=fake, out=lines.append) == orch.WAITING
    assert fake.calls == ["infra-pipeline"]                       # infra does not depend on the design gates
    joined = "\n".join(lines)
    assert "G3A is pending" in joined and "G3B is pending" in joined
    approve_design_gates(bare)
    assert go(fake) == orch.WAITING and fake.calls == ["infra-pipeline", "task-breakdown"]


def test_an_architecture_change_after_g3b_blocks_task_breakdown_again(bare):
    approve_design_gates(bare)
    fake = FakeAgents(bare)
    go(fake)
    (bare / "architecture.md").write_text("changed after approval")
    steps = {s.stage.agent: s for s in orch.assess(P)}
    assert steps["task-breakdown"].action == "blocked_input" and "G3B is stale" in steps["task-breakdown"].why


def test_rejected_task_breakdown_points_back_to_design(bare):
    approve_design_gates(bare)
    fake = FakeAgents(bare)
    go(fake)
    gates.record_decision(bare, gates.load_gates()["P4-G1"], "rejected", {"name": "Tech Lead"}, {"name": "Agent"})
    step = next(s for s in orch.assess(P) if s.stage.agent == "task-breakdown")
    assert step.action == "escalate" and "G3A/G3B" in step.why


def test_orchestrator_refreshes_stories_from_jira_before_running(bare, monkeypatch):
    approve_design_gates(bare)
    monkeypatch.setenv("PHASE4_TRACKER", "jira")
    for key, value in {"JIRA_BASE_URL": "https://demo.atlassian.net", "JIRA_PROJECT_KEY": "DEMO",
                       "JIRA_BOARD_ID": "3"}.items():
        monkeypatch.setenv(key, value)
    calls = []
    monkeypatch.setattr(story_import, "import_stories",
                        lambda project: calls.append(project) or {"stories": 1, "changed": False, "excluded": []})
    fake = FakeAgents(bare)
    lines = []
    orch.orchestrate(P, runner=fake, out=lines.append)
    assert calls == [P] and "approved stories: 1 from Jira (unchanged)" in lines[0]
    assert orch.orchestrate(P, runner=fake, out=lines.append, plan_only=True) == orch.WAITING and calls == [P]

    def broken(project):
        raise files.ProjectError("401 from Jira")
    monkeypatch.setattr(story_import, "import_stories", broken)
    lines.clear()
    assert orch.orchestrate(P, runner=fake, out=lines.append) == orch.FAILED
    assert "importing approved stories failed: 401 from Jira" in lines[-1]
