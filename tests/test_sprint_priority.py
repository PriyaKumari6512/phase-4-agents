"""Sprint Planning priority comes from the approved roadmap (release -> MoSCoW -> tracker Rank), not from a model."""
from __future__ import annotations

import json

from agent_engine.phase4 import files, sprint
from agent_engine.phase4.contracts import Backlog, SprintPlan
from agent_engine.phase4.sprint_model import SprintIn, StoryIn, solve as packing

from phase4_helpers import build_story_backlog
from test_phase4_pipeline import AS_OF, P, proj  # noqa: F401  (fixture)


def roadmap(proj, releases, stories):
    """Edit the built backlog: roadmap releases and each story's (release, moscow, rank)."""
    doc = json.loads((proj / files.BACKLOG).read_text())
    doc["releases"] = [{"name": n, "order": i} for i, n in enumerate(releases, 1)]
    for item in doc["items"]:
        if item["item_id"] in stories:
            item["release"], item["moscow"], item["rank"] = stories[item["item_id"]]
    (proj / files.BACKLOG).write_text(json.dumps(doc))
    return files.read_json(P, files.BACKLOG, Backlog)


def test_order_is_release_then_moscow_then_rank(proj):
    build_story_backlog(proj)
    b = roadmap(proj, ["MVP", "R2"], {"BM-2": ("R2", "must", "0|a"), "BM-3": ("MVP", "should", "0|b"),
                                      "BM-4": ("MVP", "must", "0|c")})
    assert sprint.priority_order(b) == ["BM-4", "BM-3", "BM-2"]          # MVP before R2; must before should
    b = roadmap(proj, ["MVP", "R2"], {"BM-2": ("MVP", "must", "0|c"), "BM-3": ("MVP", "must", "0|a"),
                                      "BM-4": ("MVP", "must", None)})
    assert sprint.priority_order(b) == ["BM-3", "BM-2", "BM-4"]          # Rank, unranked last
    b = roadmap(proj, ["MVP"], {"BM-2": (None, "must", "0|a"), "BM-3": ("Later", "must", "0|a"),
                                "BM-4": ("MVP", "could", "0|z")})
    assert sprint.priority_order(b) == ["BM-4", "BM-3", "BM-2"]          # known release, unknown, none


def test_weights_fall_from_100_to_1():
    assert sprint.priority_weights(["a", "b", "c"]) == {"a": 100.0, "b": 50.5, "c": 1.0}
    assert sprint.priority_weights(["only"]) == {"only": 100.0}


def test_a_big_high_priority_story_is_not_displaced_by_small_lower_ones():
    weights = sprint.priority_weights(["mvp", "r2a", "r2b"])
    stories = [StoryIn("mvp", 5, 5 * weights["mvp"]), StoryIn("r2a", 2, 2 * weights["r2a"]),
               StoryIn("r2b", 3, 3 * weights["r2b"])]
    res = packing(stories, [SprintIn(index=1, cap_p50=5, cap_p85=5)], [], time_limit_s=5)
    assert res.placement == {"mvp": 1, "r2a": 0, "r2b": 0}


def test_plan_records_the_order_and_no_model_scores(proj):
    build_story_backlog(proj)
    roadmap(proj, ["MVP", "R2"], {"BM-2": ("MVP", "must", "0|a"), "BM-3": ("MVP", "should", "0|b"),
                                  "BM-4": ("R2", "could", "0|c")})
    out = json.loads(sprint.solve(P, as_of=AS_OF))
    assert out["solver"] in ("OPTIMAL", "FEASIBLE")
    plan = files.read_json(P, files.SPRINT_PLAN, SprintPlan)
    assert plan.priority_order == ["BM-2", "BM-3", "BM-4"] and plan.priority["BM-2"] == 100.0
    assert any("release (MVP → R2)" in a for a in plan.assumptions)
    md = (proj / files.SPRINT_PLAN_MD).read_text()
    assert "· MVP · priority #1" in md


def test_an_older_plan_format_is_replanned_not_fatal(proj):
    build_story_backlog(proj)
    (proj / "sprint").mkdir(exist_ok=True)
    (proj / files.SPRINT_PLAN).write_text(json.dumps({"business_values": {"BM-2": 8}, "wsjf": {}}))
    assert json.loads(sprint.solve(P, as_of=AS_OF))["solver"] in ("OPTIMAL", "FEASIBLE")
