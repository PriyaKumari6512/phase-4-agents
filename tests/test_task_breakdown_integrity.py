"""Task Breakdown integrity and reuse regressions, using synthetic/fixture inputs."""
import json
from datetime import datetime, timezone

import networkx as nx
import pytest

from agent_engine.phase4 import backlog, files
from agent_engine.phase4.contracts import (
    AcceptanceCriterion, Backlog, Dependency, Estimate, Feature, ProjectSettings, WorkItem,
)
from agent_engine.phase4.speckit_parse import SpeckitFormatError, parse_spec_md
from test_phase4_pipeline import proj, P, _features, _enrich


def prepared():
    backlog.set_features(P, _features())
    backlog.build(P)
    _enrich(P)
    assert json.loads(backlog.validate_report(P))["ready_for_review"]
    return files.read_json(P, files.BACKLOG, Backlog)


def estimate(points=None, hours=None, method="rollup"):
    return Estimate(story_points=points, hours=hours, complexity=2, confidence="low", method=method)


def graph_backlog(tasks, story_points=1):
    return Backlog(backlog_id="proof", project="proof", sources={}, features=[],
                   items=[WorkItem(item_id="E1", level="epic", title="Epic"),
                          WorkItem(item_id="S1", level="story", parent_id="E1", title="Story",
                                   estimate=estimate(points=story_points, method="llm"),
                                   acceptance_criteria=[AcceptanceCriterion(ac_id="AC1", format="gherkin",
                                                                           text="Given A When B Then C")]),
                          *tasks], generated_at=datetime.now(timezone.utc))


def test_duplicate_story_numbers_are_rejected_before_losing_content():
    source = ("# Feature\n### User Story 1 - First (Priority: P1)\nFirst requirements\n"
              "### User Story 1 - Second (Priority: P2)\nSecond requirements\n")
    with pytest.raises(SpeckitFormatError, match="duplicate user story numbers"):
        parse_spec_md(source)


def test_missing_story_citations_do_not_inherit_all_feature_requirements(proj):
    directory = "specs/002-uncited"
    root = proj / directory
    root.mkdir()
    (root / "spec.md").write_text("# Feature\n### User Story 1 - Save (Priority: P1)\n"
                                  "1. **Given** a page, **When** saved, **Then** it exists\n")
    (root / "tasks.md").write_text("## Phase 1: User Story 1\n- [ ] T001 [US1] Save src/save.py\n")
    feature = Feature(feature_key="F2", feature_dir=directory, title="Save", summary="Save",
                      requirement_ids=["FR-001", "FR-002"])
    settings = files.read_json(P, files.PROJECT_SETTINGS, ProjectSettings)
    items = backlog._feature_items(P, feature, settings)
    story = next(i for i in items if i.level == "story")
    assert story.source_refs == []
    b = graph_backlog([])
    b.items = items
    issues = backlog._validate(b, settings, ["FR-001", "FR-002"])
    assert any(i.rule == "coverage" and i.severity == "blocking" for i in issues)
    assert b.coverage == {"FR-001": [], "FR-002": []}


@pytest.mark.parametrize("relative", ["prd.md", "architecture.md", "specs/001-bookmark-management/spec.md",
                                     "specs/001-bookmark-management/tasks.md", "specs/001-bookmark-management/plan.md",
                                     "backlog/implementation-contract.md"])
def test_changed_or_added_sources_block_review_until_rebuilt(proj, relative):
    prepared()
    path = proj / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text((path.read_text() if path.exists() else "") + "\nChanged source decision.\n")
    report = json.loads(backlog.validate_report(P, write=False))
    assert not report["ready_for_review"]
    assert any(i["rule"] == "stale_sources" and relative in i["message"] for i in report["blocking"])


def test_calendar_changes_require_cheap_rebuild_and_preserve_enrichments(proj):
    prepared()
    settings = files.read_json(P, files.PROJECT_SETTINGS)
    settings["calendar"]["planning_horizon_sprints"] = 5
    settings["team"][0]["allocation_pct"] = 50
    files.write_json(P, files.PROJECT_SETTINGS, settings)
    assert not json.loads(backlog.validate_report(P, write=False))["ready_for_review"]
    assert json.loads(backlog.build(P))["enrichments_dropped_changed_items"] == []
    assert json.loads(backlog.validate_report(P))["ready_for_review"]


@pytest.mark.parametrize("relative", ["specs/001-bookmark-management/plan.md", "backlog/implementation-contract.md"])
def test_changed_decisions_invalidate_enrichment(proj, relative):
    prepared()
    path = proj / relative
    path.write_text("Changed decision")
    result = json.loads(backlog.build(P))
    assert result["enrichments_dropped_changed_items"]


def test_duplicate_request_retry_preserves_enrichment_but_changed_request_invalidates(proj):
    path = proj / "requests/task-breakdown.md"
    path.parent.mkdir()
    path.write_text("# Request history\n\n## Request 1 (2026-01-01)\n\nBuild the backlog.\n")
    prepared()
    with path.open("a") as stream:
        stream.write("\n## Request 2 (2026-01-02)\n\nBuild the backlog.\n")
    assert json.loads(backlog.build(P))["enrichments_dropped_changed_items"] == []
    with path.open("a") as stream:
        stream.write("\n## Request 3 (2026-01-03)\n\nChange notification behavior.\n")
    assert json.loads(backlog.build(P))["enrichments_dropped_changed_items"]


def test_unrelated_feature_definition_does_not_invalidate_existing_feature(proj):
    b = prepared()
    item = next(i for i in b.items if i.level == "task")
    previous = backlog._item_source(P, item)
    features = files.read_json(P, files.FEATURES)
    features["features"].append(dict(feature_key="F2", feature_dir="specs/002-other", title="Other",
                                     summary="Unrelated", requirement_ids=[]))
    files.write_json(P, files.FEATURES, features)
    assert backlog._item_source(P, item) == previous


def test_update_hashes_shared_source_files_once_per_operation(proj, monkeypatch):
    b = prepared()
    calls = {}
    original = files.file_sha
    def counted(project, relative):
        calls[relative] = calls.get(relative, 0) + 1
        return original(project, relative)
    monkeypatch.setattr(files, "file_sha", counted)
    result = json.loads(backlog.update(P, [{"item_id": i.item_id, "type": i.type} for i in b.items]))
    assert not result["errors"]
    assert calls and max(calls.values()) == 1


def test_final_task_dag_check_detects_cycle_after_repair_limit(proj):
    settings = files.read_json(P, files.PROJECT_SETTINGS, ProjectSettings)
    tasks = []
    for number in range(51):
        for side in (0, 1):
            tasks.append(WorkItem(item_id=f"T{number}-{side}", level="task", parent_id="S1", title="Task",
                                  estimate=estimate(hours=1), dependencies=[Dependency(
                                      on_id=f"T{number}-{1-side}", reason="synthetic cycle", confidence=.5, origin="llm")]))
    b = graph_backlog(tasks)
    issues = backlog._validate(b, settings, [])
    assert not nx.is_directed_acyclic_graph(backlog._graph(b.by_id(), "task"))
    assert any(i.rule == "dependency_cycle" and i.severity == "blocking" for i in issues)


def test_automatic_rollup_conserves_rounding_and_rejects_impossible_granularity(proj):
    settings = files.read_json(P, files.PROJECT_SETTINGS, ProjectSettings)
    tasks = [WorkItem(item_id=f"T{i}", level="task", parent_id="S1", title="Task") for i in range(7)]
    b = graph_backlog(tasks)
    backlog._rollup(b, b.by_id()["S1"], {"T0": .01, "T1": 9}, settings)
    assert sum(t.estimate.hours for t in b.tasks_of("S1")) == pytest.approx(6)
    assert all(t.estimate.hours >= .5 for t in b.tasks_of("S1"))
    b = graph_backlog([WorkItem(item_id=f"T{i}", level="task", parent_id="S1", title="Task") for i in range(20)])
    with pytest.raises(ValueError, match="cannot cover 20 tasks"):
        backlog._rollup(b, b.by_id()["S1"], {}, settings)


def test_mixed_explicit_estimates_keep_override_and_conserve_feasible_remainder(proj):
    settings = files.read_json(P, files.PROJECT_SETTINGS, ProjectSettings)
    b = graph_backlog([WorkItem(item_id="T1", level="task", parent_id="S1", title="Explicit",
                               estimate=estimate(hours=4, method="human")),
                       WorkItem(item_id="T2", level="task", parent_id="S1", title="Auto")])
    backlog._rollup(b, b.by_id()["S1"], {}, settings)
    assert b.by_id()["T1"].estimate.hours == 4 and b.by_id()["T2"].estimate.hours == 2
    b.by_id()["T1"].estimate.hours = 9
    backlog._rollup(b, b.by_id()["S1"], {}, settings)
    assert b.by_id()["T1"].estimate.hours == 9 and b.by_id()["T2"].estimate.hours == .5
    issues = backlog._validate(b, settings, [])
    assert any(i.rule == "effort_total" and i.severity == "warning" for i in issues)
    assert not any(i.rule == "effort_total" and i.severity == "blocking" for i in issues)


def test_invalid_automatic_rollup_is_a_blocker(proj):
    settings = files.read_json(P, files.PROJECT_SETTINGS, ProjectSettings)
    b = graph_backlog([WorkItem(item_id="T1", level="task", parent_id="S1", title="Task", estimate=estimate(hours=10))])
    assert any(i.rule == "effort_total" and i.severity == "blocking" for i in backlog._validate(b, settings, []))


def test_impossible_story_update_is_atomic_and_large_weights_stay_finite(proj):
    settings = files.read_json(P, files.PROJECT_SETTINGS, ProjectSettings)
    b = graph_backlog([WorkItem(item_id=f"T{i}", level="task", parent_id="S1", title="Task") for i in range(20)], 3)
    backlog._rollup(b, b.by_id()["S1"], {"T0": 1e308, "T1": 1e308}, settings)
    assert sum(t.estimate.hours for t in b.tasks_of("S1")) == pytest.approx(18)
    before = b.model_dump()
    errors = []
    assert not backlog._transaction(b, "S1", {"estimate": estimate(points=1, method="llm").model_dump()}, settings, errors)
    assert errors and b.model_dump() == before


@pytest.mark.parametrize("existing", [(True, True), (False, False), (True, False), (False, True)])
def test_failed_second_save_restores_both_files_byte_exactly(proj, monkeypatch, existing):
    b = prepared()
    paths = [proj / backlog.ENRICHMENTS, proj / files.BACKLOG]
    for path, keep in zip(paths, existing):
        if keep:
            path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes().replace(b"\n", b"\r\n"))
        else:
            path.unlink()
    previous = [path.read_bytes() if path.exists() else None for path in paths]
    original = files.write_json
    from agent_engine.stage_controls import StageBudgetExceeded
    failure = StageBudgetExceeded("synthetic budget exhaustion before second save")
    def stop_second(project, relative, value):
        if relative == files.BACKLOG:
            raise failure
        return original(project, relative, value)
    monkeypatch.setattr(files, "write_json", stop_second)
    with pytest.raises(StageBudgetExceeded) as caught:
        backlog._save(P, b, {"changed": "new ledger"})
    assert caught.value is failure
    assert [path.read_bytes() if path.exists() else None for path in paths] == previous
    assert not list((proj / "backlog").glob(".engine-backlog-rollback-*"))
