"""Publishing a story-based backlog to Jira: tasks become sub-tasks of the existing approved stories; upstream
epics and stories are never created, edited, linked or closed. The tracker is a fake; no network."""
from __future__ import annotations

import asyncio
import json
import threading

import pytest

from agent_engine import gates
from agent_engine.phase4 import files, publish, task_breakdown as tb
from agent_engine.phase4.trackers.base import ExtObj

from test_task_breakdown_stories import FakeModel, P, proj, snapshot  # noqa: F401  (fixture)


class FakeJira(publish.LocalTracker):
    system = "jira"

    def __init__(self, project, existing):
        super().__init__(project)
        self.lock = threading.Lock()
        self.existing = dict(existing)            # upstream issue id -> fields
        self.created, self.updated, self.links, self.closed, self.field_writes = {}, [], [], [], []

    def create(self, payload):
        with self.lock:
            assert payload["level"] == "task", "only tasks may be created"
            assert payload["parent_id"] in self.existing, "a sub-task needs an existing story as parent"
            key = f"GR-{100 + len(self.created)}"
            self.created[key] = dict(payload)
            return ExtObj(key, key)

    def update(self, external_id, fields):
        assert external_id in self.created, "upstream issues are never edited"
        self.updated.append((external_id, fields))

    def get_fields(self, external_id):
        c = self.created[external_id]
        return {k: c.get(k) for k in ("title", "body_md", "labels", "parent_id")}

    def find_by_marker(self, marker, level=None):
        return next((ExtObj(k, k) for k, v in self.created.items() if v["_marker"] == marker), None)

    def blocks_of(self, issue_id):
        return [b for a, b in self.links if a == issue_id]

    def add_blocks(self, blocker, blocked):
        for issue in (blocker, blocked):
            assert issue in self.created, "links are only made between tasks"
        self.links.append((blocker, blocked))

    def remove_blocks(self, blocker, blocked):
        self.links.remove((blocker, blocked))

    def close_item(self, issue_id, reason):
        assert issue_id in self.created, "upstream issues are never closed"
        self.closed.append(issue_id)

    def set_field_if_empty(self, issue_id, field, value):
        current = self.existing[issue_id].get(field)
        if current is not None:
            return False
        self.existing[issue_id][field] = value
        self.field_writes.append((issue_id, field, value))
        return True


@pytest.fixture
def jira(proj, monkeypatch):
    for key, value in {"PHASE4_TRACKER": "jira", "JIRA_BASE_URL": "https://demo.atlassian.net",
                       "JIRA_PROJECT_KEY": "GR", "JIRA_BOARD_ID": "4"}.items():
        monkeypatch.setenv(key, value)
    stories = snapshot()
    stories["story_points_field"] = "customfield_10016"
    for s in stories["stories"]:
        s["issue_id"] = {"GR-9": "10086", "GR-10": "10087"}[s["key"]]
    stories["epics"][0]["issue_id"] = "10078"
    (proj / "phase4/stories.json").write_text(json.dumps(stories))
    monkeypatch.setattr(tb, "_invoke", FakeModel())
    asyncio.run(tb.generate(P, "", []))
    approve(proj)
    tracker = FakeJira(P, {"10078": {}, "10086": {"customfield_10016": 3}, "10087": {"customfield_10016": None}})
    monkeypatch.setattr(publish, "_tracker_for", lambda *a: tracker)
    return tracker


def approve(proj):
    gates.record_decision(proj, gates.load_gates()["P4-G1"], "approved", {"name": "Tech Lead"}, {"name": "Agent"})


def test_only_tasks_are_published_as_sub_tasks_of_the_existing_stories(proj, jira):
    report = publish.publish_backlog(P)
    assert report["created"] == 6 and report["referenced"] == 3 and report["story_points_written"] == []
    first = next(v for v in jira.created.values() if "· GR-9-T02_" in v["body_md"])
    assert first["parent_id"] == "10086" and "hours" not in first
    assert first["body_md"].startswith("**Estimate:** 5 h (medium confidence)")
    assert first["labels"] == ["phase4", "discipline-be"]
    assert len(jira.links) == 4                       # T1 -> T2 -> T3 in each story; story links stay upstream
    ids = publish.ExternalIds(P)
    rows = ids.data[ids.namespace("jira")]
    assert rows["GR-9"]["id"] == "10086" and rows["GR-9"]["last_payload"] == publish.REFERENCED
    assert rows["GR-1"]["id"] == "10078"
    again = publish.publish_backlog(P)
    assert again["created"] == 0 and len(jira.created) == 6 and jira.updated == []


def test_publishing_to_a_different_project_than_the_import_is_refused(proj, jira, monkeypatch):
    monkeypatch.setenv("JIRA_PROJECT_KEY", "GT")
    with pytest.raises(publish.PublishError, match="imported from jira project 'GR'"):
        publish.publish_backlog(P)


def test_a_story_leaving_the_import_closes_its_tasks_but_never_the_story(proj, jira, monkeypatch):
    publish.publish_backlog(P)
    stories = json.loads((proj / "phase4/stories.json").read_text())
    stories["stories"] = [s for s in stories["stories"] if s["key"] == "GR-9"]
    stories["stories"][0]["blocks"] = []
    (proj / "phase4/stories.json").write_text(json.dumps(stories))
    asyncio.run(tb.generate(P, "", []))
    approve(proj)
    report = publish.publish_backlog(P)
    assert report["closed"] == 3 and len(jira.closed) == 3          # GR-10's three sub-tasks only


def test_story_points_are_written_only_when_asked_and_only_where_empty(proj, jira, monkeypatch):
    monkeypatch.setenv("PHASE4_WRITE_STORY_POINTS", "if_empty")
    report = publish.publish_backlog(P)
    assert report["story_points_written"] == ["GR-10"]
    assert jira.field_writes == [("10087", "customfield_10016", 2)]        # GR-9 keeps its 3 SP from Jira
    monkeypatch.setenv("PHASE4_WRITE_STORY_POINTS", "always")
    with pytest.raises(publish.PublishError, match="never or if_empty"):
        publish.publish_backlog(P)
