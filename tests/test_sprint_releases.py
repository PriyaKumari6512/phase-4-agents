"""Roadmap releases as deadlines (tracker date first, project.json fallback) and the release plan."""
from __future__ import annotations

import json

from agent_engine.phase4 import files, sprint
from agent_engine.phase4.contracts import SprintPlan

from phase4_helpers import build_story_backlog
from test_phase4_pipeline import AS_OF, P, proj  # noqa: F401  (fixture)

# Example calendar: sprint 1 = 2026-11-09..22, sprint 2 = 11-23..12-06, sprint 3 = 12-07..20, capacity ~20 SP each.


def setup(proj, releases, story_release, release_deadlines=()):
    build_story_backlog(proj)
    doc = json.loads((proj / files.BACKLOG).read_text())
    doc["releases"] = releases
    for item in doc["items"]:
        if item["item_id"] in story_release:
            item["release"] = story_release[item["item_id"]]
    (proj / files.BACKLOG).write_text(json.dumps(doc))
    settings = json.loads((proj / files.PROJECT_SETTINGS).read_text())
    settings["release_deadlines"] = list(release_deadlines)
    (proj / files.PROJECT_SETTINGS).write_text(json.dumps(settings))


ROADMAP = [{"name": "MVP", "order": 1, "release_date": "2026-12-06"}, {"name": "R2", "order": 2}, {"name": "R3", "order": 3}]
STORIES = {"BM-2": "MVP", "BM-3": "R2", "BM-4": "R3"}


def test_dates_come_from_the_tracker_then_project_json(proj):
    setup(proj, ROADMAP, STORIES, [{"release": "MVP", "due_date": "2026-11-30"},
                                   {"release": "R2", "due_date": "2026-12-20", "hard": True},
                                   {"release": "Ghost", "due_date": "2027-01-01"}])
    assert json.loads(sprint.solve(P, as_of=AS_OF))["solver"] in ("OPTIMAL", "FEASIBLE")
    plan = files.read_json(P, files.SPRINT_PLAN, SprintPlan)
    got = {r.release: (str(r.due_date) if r.due_date else None, r.date_source, r.hard, r.status) for r in plan.releases}
    assert got == {"MVP": ("2026-12-06", "tracker", False, "on_track"), "R2": ("2026-12-20", "project", True, "on_track"),
                   "R3": (None, "none", False, "no_deadline")}
    assert [r.release for r in plan.releases] == ["MVP", "R2", "R3"]
    mvp = plan.releases[0]
    assert mvp.story_ids == ["BM-2"] and mvp.points == 3 and mvp.last_sprint_index == 1
    assert str(mvp.planned_finish) == "2026-11-22" and mvp.p50_date and mvp.p85_date
    assert any("tracker date 2026-12-06 is used, not 2026-11-30" in a for a in plan.assumptions)
    assert any("not on the roadmap are ignored: Ghost" in a for a in plan.assumptions)
    md = (proj / files.SPRINT_PLAN_MD).read_text()
    assert "## Release plan" in md and "| R2 | 2026-12-20 (hard, project) | 1 |" in md


def test_a_soft_date_before_the_first_sprint_ends_is_reported_late(proj):
    setup(proj, [{"name": "MVP", "order": 1, "release_date": "2026-11-15"}], {"BM-2": "MVP"})
    sprint.solve(P, as_of=AS_OF)
    plan = files.read_json(P, files.SPRINT_PLAN, SprintPlan)
    assert plan.releases[0].status == "late"
    sprint.annotate(P, {str(s.sprint_index): "Users can save bookmarks" for s in plan.sprints if s.story_ids})
    check = json.loads(sprint.check(P))
    assert check["ok"] and any("release MVP finishes 2026-11-22, after its deadline 2026-11-15" in w for w in check["warnings"])


def test_an_impossible_hard_release_date_offers_verified_options(proj):
    setup(proj, [{"name": "MVP", "order": 1, "release_date": "2026-11-15"}], {"BM-2": "MVP"},
          [{"release": "MVP", "due_date": "2026-11-15", "hard": True}])
    out = json.loads(sprint.solve(P, as_of=AS_OF))
    assert out["solver"] == "INFEASIBLE" and "deadline:release/MVP" in out["conflicting"]
    changes = [c for o in out["options_if_infeasible"] for c in o["changes"]]
    assert "relax:deadline:release/MVP:+1" in changes
    chosen = json.loads(sprint.solve(P, relax=["relax:deadline:release/MVP:+1"], as_of=AS_OF))
    assert chosen["solver"] in ("OPTIMAL", "FEASIBLE")


def test_a_release_with_a_deferred_story_is_incomplete(proj):
    setup(proj, ROADMAP, STORIES)
    sprint.solve(P, pins={"BM-4": 0}, as_of=AS_OF)                      # the approver keeps BM-4 out of the horizon
    plan = files.read_json(P, files.SPRINT_PLAN, SprintPlan)
    r3 = next(r for r in plan.releases if r.release == "R3")
    assert r3.status == "incomplete" and r3.deferred_story_ids == ["BM-4"] and r3.planned_finish is None
