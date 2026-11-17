"""Sprint publishing reuses sprints that already exist on the Jira board instead of creating duplicates."""
from __future__ import annotations

import json
import pytest
from datetime import date

from agent_engine import gates
from agent_engine.phase4 import files, publish, sprint
from agent_engine.phase4.contracts import SprintSlot
from agent_engine.phase4.trackers.base import ExtObj

from phase4_helpers import build_story_backlog
from test_phase4_pipeline import AS_OF, P, proj  # noqa: F401  (fixture)


def slot(index, start, end, name=""):
    return SprintSlot(sprint_index=index, number=index, name=name or f"bm Sprint {index}", start=start, end=end,
                      story_ids=["BM-2"], committed_points=3, capacity_p50=10, capacity_p85=8,
                      maintenance_reserved_points=0, available_person_days=10)


def existing(sid, name, state="future", start=None, end=None, goal=""):
    return {"id": sid, "name": name, "state": state, "start": start, "end": end, "goal": goal}


S1, S2, S3 = (slot(1, date(2026, 11, 9), date(2026, 11, 22)), slot(2, date(2026, 11, 23), date(2026, 12, 6)),
              slot(3, date(2026, 12, 7), date(2026, 12, 20), name="Hardening"))


def test_matching_rules():
    dated = existing("7", "Team sprint", start=date(2026, 11, 23), end=date(2026, 12, 6))
    active = existing("5", "Running", state="active", start=date(2026, 11, 2), end=date(2026, 11, 15))
    named = existing("9", "Hardening")
    placeholder = existing("2", "GR Sprint 1")
    got = publish.match_sprints([S1, S2, S3], [placeholder, named, dated, active])
    assert {k: v["id"] for k, v in got.items()} == {1: "5", 2: "7", 3: "9"}      # active cover, date, name
    got = publish.match_sprints([S1, S2], [existing("4", "Later placeholder"), placeholder])
    assert {k: v["id"] for k, v in got.items()} == {1: "2", 2: "4"}                # undated, oldest first
    assert publish.match_sprints([S1], [existing("3", "Other", start=date(2027, 1, 1))]) == {}


class FakeBoard(publish.LocalTracker):
    system = "jira"

    def __init__(self, project, sprints):
        super().__init__(project)
        self.sprints, self.created, self.updates, self.moves = list(sprints), [], [], []

    def board_sprints(self):
        return [dict(s) for s in self.sprints]

    def update_sprint(self, sprint_id, fields):
        self.updates.append((sprint_id, fields))

    def create_sprint(self, name, start, end, goal):
        self.created.append(name)
        return ExtObj(id=f"new-{len(self.created)}", key=name)

    def move_to_sprint(self, sprint_id, issue_ids):
        self.moves.append((sprint_id, list(issue_ids)))

    def move_to_backlog(self, issue_ids):
        pass


def test_publishing_adopts_the_board_placeholder_and_fills_only_empty_fields(proj, monkeypatch):
    build_story_backlog(proj)
    settings = json.loads((proj / files.PROJECT_SETTINGS).read_text())
    settings["calendar"]["planning_horizon_sprints"] = 2
    (proj / files.PROJECT_SETTINGS).write_text(json.dumps(settings))
    build_story_backlog(proj)                                         # rebuild: settings are a backlog source
    sprint.solve(P, pins={"BM-4": 2}, as_of=AS_OF)                    # stories in both sprints
    plan = json.loads((proj / files.SPRINT_PLAN).read_text())
    sprint.annotate(P, {str(s["sprint_index"]): f"Outcome {s['sprint_index']}" for s in plan["sprints"] if s["story_ids"]})
    for gate in ("P4-G1", "P4-G2"):
        gates.record_decision(proj, gates.load_gates()[gate], "approved", {"name": "Lead"}, {"name": "Agent"})
    board = FakeBoard(P, [existing("2", "GR Sprint 1"),
                          existing("8", "Team sprint", start=date(2026, 11, 23), end=date(2026, 12, 6), goal="Keep")])
    monkeypatch.setattr(publish, "_tracker_for", lambda *a: board)
    report = publish.publish_sprint(P)
    assert board.created == [] and report["sprints"] == 2
    assert {a["tracker_sprint"]: a["filled"] for a in report["adopted"]} == {"GR Sprint 1": ["end", "goal", "start"],
                                                                            "Team sprint": []}
    assert board.updates == [("2", {"start": date(2026, 11, 9), "end": date(2026, 11, 22), "goal": "Outcome 1"})]
    again = publish.publish_sprint(P)
    assert again["adopted"] == [] and board.created == [] and len(board.updates) == 1   # recorded, not re-adopted


def test_without_a_match_a_new_sprint_is_created(proj, monkeypatch):
    build_story_backlog(proj)
    sprint.solve(P, as_of=AS_OF)
    plan = json.loads((proj / files.SPRINT_PLAN).read_text())
    sprint.annotate(P, {str(s["sprint_index"]): "Outcome" for s in plan["sprints"] if s["story_ids"]})
    for gate in ("P4-G1", "P4-G2"):
        gates.record_decision(proj, gates.load_gates()[gate], "approved", {"name": "Lead"}, {"name": "Agent"})
    board = FakeBoard(P, [existing("3", "Old", start=date(2026, 1, 5), end=date(2026, 1, 18))])
    monkeypatch.setattr(publish, "_tracker_for", lambda *a: board)
    report = publish.publish_sprint(P)
    assert report["adopted"] == [] and len(board.created) == report["sprints"] >= 1


@pytest.fixture(autouse=True)
def _isolate_component_publication(monkeypatch):
    # These tests exercise one publisher/checkpoint; final G4 has dedicated integration tests.
    from agent_engine.phase4 import publish
    monkeypatch.setattr(publish, "require_final_gate", lambda project: {})
