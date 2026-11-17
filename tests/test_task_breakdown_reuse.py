"""Task Breakdown reuse and capability boundaries, using local synthetic inputs."""
import json
import shutil

import pytest

from agent_engine import config, verification_resume
from agent_engine.phase4 import backlog, files, feature_jobs, tools
from agent_engine.stage_controls import HelperScope, helper_scope, StageBudget, active_stage_budget, StageBudgetExceeded
from test_phase4_pipeline import proj, P, _features


def setup_feature():
    backlog.set_features(P, _features())
    return _features()[0]["feature_dir"]


def complete_feature(proj):
    directory = setup_feature()
    (proj / directory / "plan.md").write_text("# Plan\nSource-backed architecture.\n")
    digest = feature_jobs.status(P, directory)["input_sha256"]
    feature_jobs.checkpoint(P, directory, digest)
    return directory


def test_feature_completion_is_reusable_but_not_an_approval(proj):
    directory = complete_feature(proj)
    state = feature_jobs.status(P, directory)
    assert state["reusable"] and not state["changed_inputs"]
    assert not list((proj / "gates").glob("*.approved.json"))
    (proj / directory / "tasks.md").write_text("changed")
    assert not feature_jobs.status(P, directory)["reusable"]


def test_feature_reuse_rejects_changed_source_text_with_same_ids(proj):
    directory = complete_feature(proj)
    (proj / "prd.md").write_text((proj / "prd.md").read_text() + "\nChanged product constraint.\n")
    state = feature_jobs.status(P, directory)
    assert not state["reusable"] and "prd.md" in state["changed_inputs"]


def test_feature_reuse_ignores_unrelated_schedule_but_keeps_semantic_constraints(proj):
    directory = complete_feature(proj)
    settings = json.loads((proj / "phase4/project.json").read_text())
    settings["maintenance_capacity_pct"] = 21
    (proj / "phase4/project.json").write_text(json.dumps(settings))
    assert feature_jobs.status(P, directory)["reusable"]
    settings["definition_of_done"].append("Explicit new policy")
    (proj / "phase4/project.json").write_text(json.dumps(settings))
    assert not feature_jobs.status(P, directory)["reusable"]


def test_feature_reuse_rejects_changed_project_template(proj):
    from agent_engine.phase4 import speckit
    speckit.init(P)
    directory = complete_feature(proj)
    assert feature_jobs.status(P, directory)["reusable"]
    (proj / ".specify/templates/spec-template.md").write_text("# Approved new template")
    assert not feature_jobs.status(P, directory)["reusable"]


def test_adjacent_retry_request_does_not_discard_completed_feature(proj):
    requests = proj / "requests/task-breakdown.md"
    requests.parent.mkdir()
    requests.write_text("## Request 1 (2026-01-01)\n\nBuild the backlog.\n")
    directory = complete_feature(proj)
    requests.write_text(requests.read_text() + "\n## Request 2 (2026-01-02)\n\nBuild the backlog.\n")
    assert feature_jobs.status(P, directory)["reusable"]
    requests.write_text(requests.read_text() + "\n## Request 3 (2026-01-03)\n\nAdd password reset.\n")
    assert not feature_jobs.status(P, directory)["reusable"]


def test_checkpoint_requires_unchanged_inputs_and_complete_artifacts(proj):
    directory = setup_feature()
    digest = feature_jobs.status(P, directory)["input_sha256"]
    with pytest.raises(files.ProjectError, match="plan.md"):
        feature_jobs.checkpoint(P, directory, digest)
    (proj / directory / "plan.md").write_text("Plan")
    (proj / "architecture.md").write_text("Changed architecture")
    with pytest.raises(files.ProjectError, match="changed"):
        feature_jobs.checkpoint(P, directory, digest)


def test_context_pages_preserve_exact_source_and_detect_changes(proj):
    directory = setup_feature()
    raw = files.read_text(P, files.PRD)
    offset, pieces, digest = 0, [], ""
    while True:
        page = json.loads(tools.source_context.invoke({"project": P, "feature_directory": directory,
                         "source": "prd", "offset": offset, "limit": 1000, "expected_sha256": digest}))
        pieces.append(page["text"])
        digest = page["sha256"]
        offset = page["next_offset"]
        if offset is None:
            break
    assert "".join(pieces) == raw
    files.path(P, files.PRD).write_text(raw + "changed")
    assert "changed" in tools.source_context.invoke({"project": P, "source": "prd", "expected_sha256": digest})


def test_enricher_can_only_read_and_update_assigned_epic(proj):
    first = _features()[0]
    second = {**first, "feature_key": "F02", "feature_dir": "specs/002-other"}
    shutil.copytree(proj / first["feature_dir"], proj / second["feature_dir"])
    backlog.set_features(P, [first, second])
    backlog.build(P)
    token = helper_scope.set(HelperScope("backlog-enricher", P, epic_id="E-001"))
    try:
        page = json.loads(tools.backlog_view.invoke({"project": P}))
        assert all(i["item_id"] == "E-001" or i["parent_id"] == "E-001" or i["level"] == "task"
                   for i in page["items"])
        before = files.path(P, files.BACKLOG).read_bytes()
        assert "outside" in tools.backlog_update.invoke({"project": P, "updates": [{"item_id": "E-002", "title": "bad"}]})
        assert "assigned" in tools.backlog_view.invoke({"project": P, "epic_id": "E-002"})
        assert "outside" in tools.backlog_find_similar.invoke({"project": P, "story_ids": ["S-002-US1"]})
        assert "global tool" in tools.backlog_build.invoke({"project": P})
        assert files.path(P, files.BACKLOG).read_bytes() == before
        index = json.loads(tools.source_context.invoke({"project": P}))
        assert index["feature"]["feature_dir"] == first["feature_dir"]
        assert "team" not in index["settings"]
    finally:
        helper_scope.reset(token)


def test_feature_tool_scope_rejects_other_feature_before_mutating(proj):
    directory = setup_feature()
    token = helper_scope.set(HelperScope("speckit-feature", P, feature_directory=directory))
    try:
        result = tools.speckit_write_feature.invoke({"project": P, "feature_directory": "specs/999-other", "document": {}})
        assert "assigned feature" in result
        assert "global tool" in tools.backlog_validate.invoke({"project": P})
        assert not (proj / "specs/999-other").exists()
    finally:
        helper_scope.reset(token)


def test_stopped_budget_blocks_domain_mutations(proj):
    setup_feature()
    budget = StageBudget(1, 100, 100, 60, 1, 1)
    budget.stopped = "stopped for test"
    token = active_stage_budget.set(budget)
    before = files.path(P, files.FEATURES).read_bytes()
    try:
        with pytest.raises(StageBudgetExceeded):
            tools.backlog_set_features.invoke({"project": P, "features": []})
    finally:
        active_stage_budget.reset(token)
    assert files.path(P, files.FEATURES).read_bytes() == before


def test_verification_reuse_keeps_generation_when_reviewer_settings_change(proj, monkeypatch):
    setup_feature()
    verification_resume.save(proj, "task-breakdown", "request", "job")
    (proj / "infra").mkdir()
    (proj / "infra/new-output.json").write_text("{}")
    monkeypatch.setenv("PHASE4_IAC_CHECK_CONCURRENCY", "3")
    assert verification_resume.validate(proj, "task-breakdown", "request") == "job"
    monkeypatch.setenv("SDLC_AGENT_EFFORT", "low")
    assert verification_resume.validate(proj, "task-breakdown", "request") == "job"


def test_verification_reuse_rejects_changed_backlog_sources(proj):
    setup_feature()
    verification_resume.save(proj, "task-breakdown", "request", "job")
    (proj / "architecture.md").write_text("new architecture")
    with pytest.raises(ValueError, match="stale"):
        verification_resume.validate(proj, "task-breakdown", "request")


def test_structured_feature_to_reviewable_backlog_with_scoped_tools(proj):
    from agent_engine.phase4 import speckit
    from test_task_breakdown_documents import document
    from test_phase4_pipeline import _enrich
    directory = setup_feature()
    speckit.init(P)
    value = document()
    prototype = value["stories"][0]
    value["stories"] = [{**prototype, "number": n, "title": title,
                         "source_ids": [f"FR-00{n}", f"US-{n}"]}
                        for n, title in ((1, "Save bookmarks"), (2, "Filter bookmarks by tag"), (3, "Delete bookmarks"))]
    value["requirements"] = [{"number": n, "text": title, "source_ids": [f"FR-00{n}"]}
                             for n, title in ((1, "Save a bookmark"), (2, "List by tag"), (3, "Delete a bookmark"))]
    value["phases"] = [{"kind": "user_story", "story_number": n, "tasks": [
        {"task_id": f"T00{n}", "description": title, "file_paths": ["src/bookmarks.py"],
         "depends_on": [], "parallel": False}]} for n, title in ((1, "Implement saving"), (2, "Implement listing"), (3, "Implement deletion"))]
    digest = feature_jobs.status(P, directory)["input_sha256"]
    token = helper_scope.set(HelperScope("speckit-feature", P, feature_directory=directory))
    try:
        receipt = json.loads(tools.speckit_write_feature.invoke({"project": P, "feature_directory": directory, "document": value}))
        assert receipt["stories"] == 3
        checked = json.loads(tools.speckit_check_feature.invoke({"project": P, "feature_directory": directory}))
        assert checked["format_valid"]
        assert json.loads(tools.speckit_checkpoint_feature.invoke({"project": P, "feature_directory": directory,
                          "expected_input_sha256": digest}))["checkpointed"]
    finally:
        helper_scope.reset(token)
    assert json.loads(tools.backlog_build.invoke({"project": P}))["stories"] == 3
    token = helper_scope.set(HelperScope("backlog-enricher", P, epic_id="E-001"))
    try:
        _enrich(P)
    finally:
        helper_scope.reset(token)
    assert json.loads(tools.backlog_validate.invoke({"project": P}))["ready_for_review"]
    assert json.loads(tools.backlog_check.invoke({"project": P}))["ready_for_review"]
    assert feature_jobs.status(P, directory)["reusable"]
    assert not list((proj / "gates").glob("*.approved.json"))
