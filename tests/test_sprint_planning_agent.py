"""Sprint Planning driven by code: planning is deterministic, the model writes goals/explanations/summary in one
structured call, and turns a reviewer's request into checked pins or an option choice. Fake model; no network."""
from __future__ import annotations

import asyncio
import json

import pytest

from agent_engine.phase4 import files, sprint_planning as spa
from agent_engine.phase4.contracts import SprintPlan

from phase4_helpers import build_story_backlog
from test_phase4_pipeline import P, proj  # noqa: F401  (fixture)

REAL_SPEC = spa._spec


class FakeModel:
    def __init__(self, decisions=None, broken_first=False, recommend=None):
        self.calls, self.decisions, self.broken_first, self.recommend = [], decisions, broken_first, recommend

    async def __call__(self, schema, system, human, callbacks, spec):
        self.calls.append({"schema": schema.__name__, "human": human, "spec": spec})
        if schema is spa.Decisions:
            return self.decisions or spa.Decisions(pins=[], clear_pins=[], option_id=None, note="")
        payload = json.loads(human.split("\n", 1)[1].split("\n\nYour previous answer")[0])
        goals = [spa.SprintGoal(sprint_index=s["sprint_index"], goal="Users can save and find bookmarks.")
                 for s in payload["sprints"] if s["stories"]]
        if self.broken_first and len([c for c in self.calls if c["schema"] == "Annotation"]) == 1:
            goals = []
        return spa.Annotation(goals=goals, summary_md="Sprint 1 delivers saving bookmarks. No release is at risk.",
                              deferral_explanations=[spa.DeferralNote(story_id=d["id"], explanation="Kept out by the approver.")
                                                     for d in payload["deferred"]],
                              recommended_option=self.recommend)


@pytest.fixture
def planned(proj, monkeypatch):
    build_story_backlog(proj)
    monkeypatch.setattr(spa, "_spec", lambda: "test:fast")
    return proj


def run(coro):
    return asyncio.run(coro)


def annotations(fake):
    return [c for c in fake.calls if c["schema"] == "Annotation"]


def test_code_plans_and_one_small_call_writes_the_text(planned, monkeypatch):
    fake = FakeModel()
    monkeypatch.setattr(spa, "_invoke", fake)
    reply = run(spa.generate(P, "Plan the sprints.", []))
    assert "Solver OPTIMAL" in reply["messages"][0].content or "Solver FEASIBLE" in reply["messages"][0].content
    assert [c["schema"] for c in fake.calls] == ["Annotation"] and fake.calls[0]["spec"] == "test:fast"
    plan = files.read_json(P, files.SPRINT_PLAN, SprintPlan)
    assert plan.annotated and all(s.goal for s in plan.sprints if s.story_ids)
    assert plan.summary_md.startswith("Sprint 1 delivers")
    assert files.exists(P, files.CAPACITY)
    assert "Goal: Users can save and find bookmarks." in (planned / files.SPRINT_PLAN_MD).read_text()
    run(spa.generate(P, "Plan the sprints.", []))
    assert len(fake.calls) == 1                                          # unchanged plan: the text is reused


def test_a_failed_text_check_is_retried_once(planned, monkeypatch):
    fake = FakeModel(broken_first=True)
    monkeypatch.setattr(spa, "_invoke", fake)
    run(spa.generate(P, "", []))
    assert len(annotations(fake)) == 2 and "have stories but no goal" in annotations(fake)[1]["human"]


def test_reviewer_pins_are_checked_applied_and_kept(planned, monkeypatch):
    decisions = spa.Decisions(pins=[spa.Pin(story_id="BM-4", sprint_index=0)], clear_pins=[], option_id=None,
                              note="explain the delete story later")
    fake = FakeModel(decisions=decisions)
    monkeypatch.setattr(spa, "_invoke", fake)
    run(spa.generate(P, "Gate P4-G2: keep BM-4 out of this horizon.", []))
    assert [c["schema"] for c in fake.calls] == ["Decisions", "Annotation"]
    plan = files.read_json(P, files.SPRINT_PLAN, SprintPlan)
    assert plan.pins == {"BM-4": 0} and [d.story_id for d in plan.deferred] == ["BM-4"]
    assert plan.deferred[0].reason_code == "human_override" and plan.deferred[0].explanation == "Kept out by the approver."
    assert "explain the delete story later" in annotations(fake)[0]["human"]
    run(spa.generate(P, "Plan the sprints.", []))                        # no new decisions: the pin stays
    assert files.read_json(P, files.SPRINT_PLAN, SprintPlan).pins == {"BM-4": 0}


def test_invalid_decisions_are_retried_then_refused(planned, monkeypatch):
    bad = spa.Decisions(pins=[spa.Pin(story_id="BM-99", sprint_index=9)], clear_pins=[], option_id="OPT-7", note="")
    monkeypatch.setattr(spa, "_invoke", FakeModel(decisions=bad))
    with pytest.raises(files.ProjectError, match="unknown story BM-99"):
        run(spa.generate(P, "pin BM-99 to sprint 9", []))


def test_infeasible_plans_need_a_recommended_option_and_the_choice_is_applied(planned, monkeypatch):
    doc = json.loads((planned / files.BACKLOG).read_text())
    doc["releases"] = [{"name": "MVP", "order": 1, "release_date": "2026-11-15"}]
    for item in doc["items"]:
        if item["item_id"] == "BM-2":
            item["release"] = "MVP"
    (planned / files.BACKLOG).write_text(json.dumps(doc))
    settings = json.loads((planned / files.PROJECT_SETTINGS).read_text())
    settings["release_deadlines"] = [{"release": "MVP", "due_date": "2026-11-15", "hard": True}]
    (planned / files.PROJECT_SETTINGS).write_text(json.dumps(settings))
    from agent_engine.phase4 import capacity
    monkeypatch.setattr(capacity, "utc_today", lambda: __import__("datetime").date(2026, 11, 5))
    monkeypatch.setattr(spa, "_invoke", FakeModel(recommend=None))
    with pytest.raises(files.ProjectError, match="recommend one of"):
        run(spa.generate(P, "", []))
    monkeypatch.setattr(spa, "_invoke", FakeModel(recommend="OPT-1"))
    run(spa.generate(P, "", []))
    plan = files.read_json(P, files.SPRINT_PLAN, SprintPlan)
    assert plan.solver.status == "INFEASIBLE" and "**Recommended option OPT-1:**" in plan.summary_md
    verdict = run(spa.review(P))["structured_response"]
    assert not verdict.satisfied and any("infeasible" in g for g in verdict.gaps)
    choice = spa.Decisions(pins=[], clear_pins=[], option_id="OPT-1", note="")
    monkeypatch.setattr(spa, "_invoke", FakeModel(decisions=choice))
    run(spa.generate(P, "We choose OPT-1.", []))
    plan = files.read_json(P, files.SPRINT_PLAN, SprintPlan)
    assert plan.solver.status in ("OPTIMAL", "FEASIBLE") and plan.relaxations


def test_review_is_deterministic_and_repair_reruns_once(planned, monkeypatch):
    fake = FakeModel()
    monkeypatch.setattr(spa, "_invoke", fake)
    run(spa.generate(P, "", []))
    verdict = run(spa.review(P))["structured_response"]
    assert verdict.satisfied and len(fake.calls) == 1
    run(spa.repair(P, ["Sprint 1 goal lists titles"], []))
    assert "findings_to_fix" in annotations(fake)[-1]["human"]
    with pytest.raises(files.ProjectError, match="same findings remain"):
        run(spa.repair(P, ["Sprint 1 goal lists titles"], []))


def test_cli_runs_sprint_planning_on_the_small_model_without_an_agent_loop(planned, monkeypatch, tmp_path):
    from agent_engine import agent, cli, gates, logging_setup
    gates.record_decision(planned, gates.load_gates()["P4-G1"], "approved", {"name": "Tech Lead"}, {"name": "Agent"})
    for module in (agent, cli):
        monkeypatch.setattr(module, "model_spec", lambda tier: f"test:{tier}")
    monkeypatch.setattr(spa, "_spec", REAL_SPEC)
    monkeypatch.setattr(cli, "OUTPUTS_DIR", planned.parent)
    monkeypatch.setattr(logging_setup, "OUTPUTS_DIR", planned.parent)
    monkeypatch.setattr(logging_setup, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(cli, "build_langfuse_handler", lambda: None)
    monkeypatch.setattr(cli, "build_agent", lambda *a, **k: pytest.fail("no deep agent is built for Sprint Planning"))
    fake = FakeModel()
    monkeypatch.setattr(spa, "_invoke", fake)
    assert asyncio.run(cli._run("Plan the sprints.", "sprint-planning", P)) == 0
    report = json.loads((planned / "report.json").read_text())
    assert report["status"] == "success" and [(p["kind"], p["model_tier"]) for p in report["passes"]] == [
        ("write", "fast"), ("verify", "fast")]
    assert [c["spec"] for c in fake.calls] == ["test:fast"]


# ---------------------------------------------------------------------------------------------- validation step
class TextModel(FakeModel):
    """Writes a key-listing goal until the findings ask for a fix; reviews flagged text with a scripted answer."""

    def __init__(self, review=None):
        super().__init__()
        self.reviews = review or []

    async def __call__(self, schema, system, human, callbacks, spec):
        if schema is spa.LightReview:
            self.calls.append({"schema": "LightReview", "human": human, "spec": spec, "system": system})
            n = len([c for c in self.calls if c["schema"] == "LightReview"])
            return self.reviews[min(n, len(self.reviews)) - 1] if self.reviews else spa.LightReview(findings=[])
        result = await super().__call__(schema, system, human, callbacks, spec)
        if schema is spa.Annotation and "findings_to_fix" not in human:
            for g in result.goals:
                g.goal = "Deliver BM-2 and BM-3."
        return result


def finding(item, severity="blocking"):
    return spa.ReviewFinding(item=item, severity=severity, message="state one user outcome instead of story keys")


def test_weak_goals_and_explanations_are_flagged(planned, monkeypatch):
    monkeypatch.setattr(spa, "_invoke", FakeModel())
    run(spa.generate(P, "", []))
    plan = files.read_json(P, files.SPRINT_PLAN, SprintPlan)
    from agent_engine.phase4.contracts import Backlog
    backlog = files.read_json(P, files.BACKLOG, Backlog)
    assert spa.flagged_text(plan, backlog) == {}
    plan.sprints[0].goal = "Deliver BM-2; then polish, docs, tests, and release notes"
    from agent_engine.phase4.contracts import Deferral
    plan.deferred = [Deferral(story_id="BM-4", reason_code="dependency",
                              explanation="The team will look at this next quarter.")]
    flags = spa.flagged_text(plan, backlog)
    assert "names story keys instead of an outcome" in flags["sprint 1"]["reasons"]
    assert "may list several outcomes" in flags["sprint 1"]["reasons"]
    assert flags["BM-4"]["reasons"] == ["may not match its reason code 'dependency'"]


def test_clean_text_needs_no_review_call_and_flagged_text_gets_one(planned, monkeypatch):
    fake = FakeModel()
    monkeypatch.setattr(spa, "_invoke", fake)
    run(spa.generate(P, "", []))
    verdict = run(spa.review(P))["structured_response"]
    assert verdict.satisfied and "Reviewed 0 flagged texts" in verdict.summary and len(fake.calls) == 1
    text = TextModel(review=[spa.LightReview(findings=[finding("sprint 1"), finding("sprint 9"),
                                                       finding("sprint 1", "warning")])])
    monkeypatch.setattr(spa, "_invoke", text)
    import shutil
    shutil.rmtree(planned / ".engine-sprint-planning")                                # force fresh text
    run(spa.generate(P, "", []))
    verdict = run(spa.review(P))["structured_response"]
    reviews = [c for c in text.calls if c["schema"] == "LightReview"]
    assert len(reviews) == 1 and reviews[0]["system"].startswith("You are the Sprint Plan Reviewer")
    assert '"sprint 1"' in reviews[0]["human"] and "BM-2" in reviews[0]["human"]
    assert not verdict.satisfied and verdict.gaps == ["sprint 1: state one user outcome instead of story keys"]
    assert "sprint 1: state one user outcome" in verdict.summary                      # the warning is reported
    run(spa.review(P))
    assert len([c for c in text.calls if c["schema"] == "LightReview"]) == 1          # unchanged: reused


def test_a_later_release_planned_over_an_earlier_must_have_is_a_warning(planned, monkeypatch):
    doc = json.loads((planned / files.BACKLOG).read_text())
    doc["releases"] = [{"name": "MVP", "order": 1}, {"name": "R2", "order": 2}]
    for item in doc["items"]:
        if item["item_id"] in ("BM-2", "BM-3", "BM-4"):
            item["release"] = {"BM-2": "MVP", "BM-3": "R2", "BM-4": "R2"}[item["item_id"]]
    (planned / files.BACKLOG).write_text(json.dumps(doc))
    monkeypatch.setattr(spa, "_invoke", FakeModel())
    run(spa.generate(P, "", []))
    plan_doc = json.loads((planned / files.SPRINT_PLAN).read_text())    # simulate: BM-2 deferred for capacity
    for s in plan_doc["sprints"]:
        s["story_ids"] = [i for i in s["story_ids"] if i != "BM-2"]
    plan_doc["deferred"].append({"story_id": "BM-2", "reason_code": "capacity", "explanation": "No room left."})
    (planned / files.SPRINT_PLAN).write_text(json.dumps(plan_doc))
    from agent_engine.phase4 import sprint
    warnings = json.loads(sprint.check(P))["warnings"]
    assert any("BM-2 (must-have, release MVP) is deferred for capacity while later-release stories" in w for w in warnings)


def test_cli_text_review_findings_are_recorded_for_the_gate_not_fixed(planned, monkeypatch, tmp_path):
    """Only deterministic checks block: the model reviewer's finding becomes an advisory note for P4-G2."""
    from agent_engine import agent, cli, gates, logging_setup
    gates.record_decision(planned, gates.load_gates()["P4-G1"], "approved", {"name": "Tech Lead"}, {"name": "Agent"})
    for module in (agent, cli):
        monkeypatch.setattr(module, "model_spec", lambda tier: f"test:{tier}")
    monkeypatch.setattr(spa, "_spec", REAL_SPEC)
    monkeypatch.setattr(cli, "OUTPUTS_DIR", planned.parent)
    monkeypatch.setattr(logging_setup, "OUTPUTS_DIR", planned.parent)
    monkeypatch.setattr(logging_setup, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(cli, "build_langfuse_handler", lambda: None)
    fake = TextModel(review=[spa.LightReview(findings=[finding("sprint 1")])])
    monkeypatch.setattr(spa, "_invoke", fake)
    assert asyncio.run(cli._run("Plan the sprints.", "sprint-planning", P)) == 0
    report = json.loads((planned / "report.json").read_text())
    assert [(p["kind"], p["model_tier"]) for p in report["passes"]] == [("write", "fast"), ("verify", "fast")]
    assert report["status"] == "success" and report["review_findings"]
    assert not [c for c in fake.calls if c["schema"] == "Annotation" and "findings_to_fix" in c["human"]]
    assert cli.review_notes(P, "sprint-planning")["findings"] == report["review_findings"]
