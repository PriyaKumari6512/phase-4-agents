"""Contract-level structured generation tests with no model or API calls."""
import json

import pytest

from agent_engine.phase4 import files, speckit
from agent_engine.phase4.feature_documents import write
from agent_engine.phase4.speckit_parse import parse_spec_md, parse_tasks_md
from test_phase4_pipeline import proj, P


def document():
    return {"title": "Bookmark management", "summary": "Save, list and delete bookmarks.",
            "stories": [{"number": 1, "title": "Save a bookmark", "priority": "P1", "as_a": "member",
                         "i_want": "save a bookmark", "so_that": "I can retrieve it later", "source_ids": ["FR-001"],
                         "acceptance": [{"given": "a signed-in member", "when": "a bookmark is saved",
                                         "then": "the bookmark appears in their list"}]}],
            "requirements": [{"number": 1, "text": "Save bookmarks for members", "source_ids": ["FR-001"]}],
            "phases": [{"kind": "setup", "tasks": []}, {"kind": "user_story", "story_number": 1, "tasks": [
                {"task_id": "T001", "description": "Implement bookmark storage", "file_paths": ["src/bookmarks.py"]},
                {"task_id": "T002", "description": "Test saving bookmarks", "file_paths": ["tests/test_bookmarks.py"],
                 "depends_on": ["T001"]}]}],
            "technical_context": {"Language": "Follow architecture.md"},
            "decisions": [{"topic": "Retention", "status": "unresolved", "decision": "Retention period is not specified"}],
            "entities": [{"name": "Bookmark", "fields": {"url": "User-supplied URL"}}],
            "interfaces": [{"name": "bookmark-api", "description": "Persist the supplied URL; return saved bookmark or validation error.",
                            "status": "proposal"}],
            "validation_steps": ["Save a bookmark and verify it appears for its owner"],
            "success_criteria": ["A saved bookmark can be retrieved by its owner"],
            "open_questions": ["Which retention policy applies?"], "shared_prerequisites": ["Reuse existing identity service"]}


def test_canonical_generation_preserves_parser_contract_and_required_artifacts(proj):
    speckit.init(P)
    receipt = json.loads(write(P, "specs/002-bookmarks", document()))
    root = proj / "specs/002-bookmarks"
    assert receipt["semantic_review_required"] and receipt["stories"] == 1 and receipt["tasks"] == 2
    required = {"spec.md", "tasks.md", "plan.md", "research.md", "data-model.md", "contracts/bookmark-api.md",
                "quickstart.md", "clarifications.md", "checklists/requirements.md", "feature.json", "feature-render-manifest.json"}
    assert set(receipt["written"]) == {"specs/002-bookmarks/" + p for p in required}
    spec = parse_spec_md((root / "spec.md").read_text())
    tasks = parse_tasks_md((root / "tasks.md").read_text())
    assert spec.stories[0].source_ids == ["FR-001"] and len(spec.stories[0].scenarios) == 1
    assert [t.task_id for t in tasks] == ["T001", "T002"] and tasks[1].depends_on == ["T001"]
    assert tasks[0].paths == ["src/bookmarks.py"]
    assert "[unresolved]" in (root / "spec.md").read_text()
    assert "not a claim of external research" in (root / "research.md").read_text()
    before = {p: (root / p).read_bytes() for p in required}
    write(P, "specs/002-bookmarks", document(), receipt["feature_sha256"])
    assert before == {p: (root / p).read_bytes() for p in required}


@pytest.mark.parametrize("change", ["unknown-source", "duplicate-task", "unknown-dependency", "cycle", "missing-story-tasks", "injected-heading", "undocumented-source"])
def test_invalid_documents_never_publish_partial_artifacts(proj, change):
    value = document()
    tasks = value["phases"][1]["tasks"]
    if change == "unknown-source":
        value["stories"][0]["source_ids"] = ["FR-9999"]
    elif change == "duplicate-task":
        tasks[1]["task_id"] = tasks[0]["task_id"]
    elif change == "unknown-dependency":
        tasks[1]["depends_on"] = ["T999"]
    elif change == "cycle":
        tasks[0]["depends_on"] = ["T002"]
    elif change == "missing-story-tasks":
        value["phases"][1]["tasks"] = []
    elif change == "injected-heading":
        tasks[0]["description"] = "Useful work\n## Phase 99: Polish"
    elif change == "undocumented-source":
        value["decisions"][0]["status"] = "source"
    with pytest.raises(files.ProjectError):
        write(P, "specs/002-invalid", value)
    assert not (proj / "specs/002-invalid").exists()


def test_failed_multi_artifact_write_restores_previous_bytes(proj, monkeypatch):
    write(P, "specs/002-bookmarks", document())
    root = proj / "specs/002-bookmarks"
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    actual = files.write_text
    calls = 0
    def fail_once(project, rel, text):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError("disk is full")
        return actual(project, rel, text)
    monkeypatch.setattr(files, "write_text", fail_once)
    value = document()
    value["summary"] = "Changed summary"
    with pytest.raises(OSError, match="disk is full"):
        write(P, "specs/002-bookmarks", value)
    assert before == {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_init_preserves_approved_overrides_and_structured_writer_uses_legacy_fallback(proj):
    speckit.init(P)
    custom = proj / ".specify/templates/spec-template.md"
    constitution = proj / ".specify/memory/constitution.md"
    custom.write_text("# Approved custom sections\n")
    constitution.write_text("# Approved project constitution\n")
    speckit.init(P)
    assert custom.read_text() == "# Approved custom sections\n"
    assert constitution.read_text() == "# Approved project constitution\n"
    assert "engine policy defaults" in (proj / ".specify/engine-policy.json").read_text()
    with pytest.raises(files.ProjectError, match="custom project template"):
        write(P, "specs/002-bookmarks", document())


def test_changed_canonical_hash_rejects_stale_update(proj):
    receipt = json.loads(write(P, "specs/002-bookmarks", document()))
    value = document()
    value["summary"] = "Reviewed change"
    write(P, "specs/002-bookmarks", value, receipt["feature_sha256"])
    with pytest.raises(files.ProjectError, match="feature changed"):
        write(P, "specs/002-bookmarks", document(), receipt["feature_sha256"])


def test_regeneration_removes_only_unchanged_obsolete_owned_artifacts(proj):
    write(P, "specs/002-bookmarks", document())
    root = proj / "specs/002-bookmarks"
    (root / "contracts/legacy.md").write_text("Keep unowned legacy contract")
    value = document()
    value["interfaces"] = []
    value["entities"] = []
    receipt = json.loads(write(P, "specs/002-bookmarks", value))
    assert not (root / "contracts/bookmark-api.md").exists()
    assert not (root / "data-model.md").exists()
    assert (root / "contracts/legacy.md").read_text() == "Keep unowned legacy contract"
    assert len(receipt["removed_obsolete_generated"]) == 2


def test_regeneration_does_not_delete_edited_obsolete_contract(proj):
    write(P, "specs/002-bookmarks", document())
    root = proj / "specs/002-bookmarks"
    (root / "contracts/bookmark-api.md").write_text("Reviewed custom contract")
    value = document()
    value["interfaces"] = []
    with pytest.raises(files.ProjectError, match="was edited"):
        write(P, "specs/002-bookmarks", value)
    assert (root / "contracts/bookmark-api.md").read_text() == "Reviewed custom contract"


def test_regeneration_detects_edited_current_generated_artifact(proj):
    write(P, "specs/002-bookmarks", document())
    root = proj / "specs/002-bookmarks"
    (root / "spec.md").write_text("Reviewed custom specification")
    with pytest.raises(files.ProjectError, match="edited outside"):
        write(P, "specs/002-bookmarks", document())
    assert (root / "spec.md").read_text() == "Reviewed custom specification"


def test_effective_implicit_sequential_dependencies_are_checked_before_publish(proj):
    value = document()
    tasks = value["phases"][1]["tasks"]
    tasks[0]["depends_on"] = ["T002"]
    tasks[1]["depends_on"] = []
    with pytest.raises(files.ProjectError, match="implicit sequential"):
        write(P, "specs/002-invalid", value)
    assert not (proj / "specs/002-invalid").exists()


def test_budget_stop_mid_publish_rolls_back_exact_legacy_bytes(proj, monkeypatch):
    from agent_engine.stage_controls import StageBudget, StageBudgetExceeded, active_stage_budget
    root = proj / "specs/002-bookmarks"
    root.mkdir()
    (root / "spec.md").write_bytes(b"\xef\xbb\xbf# Legacy specification\r\n")
    (root / "plan.md").write_bytes(b"# Legacy plan\r\n")
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    budget = StageBudget(100, 100000, 100000, 60, 20, 3)
    original_write = files.write_text
    calls = 0
    def stop_during_publish(project, rel, text):
        nonlocal calls
        calls += 1
        if calls == 3:
            budget.stop("test budget exhausted after partial publish")
        return original_write(project, rel, text)
    monkeypatch.setattr(files, "write_text", stop_during_publish)
    token = active_stage_budget.set(budget)
    try:
        with pytest.raises(StageBudgetExceeded):
            write(P, "specs/002-bookmarks", document())
        assert budget.stopped
    finally:
        active_stage_budget.reset(token)
    assert before == {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
