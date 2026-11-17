"""Shared Phase 4 test setup: the inputs Task Breakdown now needs before it may run."""
from __future__ import annotations

import json
from pathlib import Path

from agent_engine import gates

MIN_STORIES = {
    "project": "", "source": "file",
    "stories": [{"key": "DEMO-1", "issue_id": "1", "summary": "Create a task",
                 "statement": "As a member, I want to create a task so that work is tracked.",
                 "acceptance_criteria": [{"ac_id": "US-1.AC1", "text": "Given a board, When I add a task, Then it is listed."}],
                 "requirement_ids": ["US-1", "FR-1"], "moscow": "must", "story_points": 3}],
}


def write_stories(root: Path) -> None:
    path = root / "phase4" / "stories.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({**MIN_STORIES, "project": root.name}), encoding="utf-8")


def approve_design_gates(root: Path) -> None:
    """Human approvals of G3A (designs) and G3B (architecture), as the PDLC requires before Phase 4."""
    design = root / "designs" / "designs.md"
    design.parent.mkdir(parents=True, exist_ok=True)
    if not design.exists():
        design.write_text("# Approved designs\n", encoding="utf-8")
    if not (root / "architecture.md").exists():
        (root / "architecture.md").write_text("arch", encoding="utf-8")
    defined = gates.load_gates()
    for name in ("G3A", "G3B"):
        gates.record_decision(root, defined[name], "approved", {"name": "Design Lead"}, {"name": "Architect"})


def make_design_ready(root: Path) -> None:
    write_stories(root)
    approve_design_gates(root)


# ---------------------------------------------------------------------------------------------- a story-based backlog
def _task(local, discipline, title, hours, skills, files_, covers, depends=(), repo="acme/taskflow-api"):
    from agent_engine.phase4 import task_breakdown as tb
    return tb.TaskDraft(local_id=local, discipline=discipline, title=title, description=f"{title}.",
                        acceptance_criteria=[f"WHEN {title.lower()} is done THE SYSTEM SHALL pass its tests"],
                        covers=list(covers), file_paths=list(files_), repo=repo, hours=hours, depends_on=list(depends),
                        skills=list(skills), definition_of_done=[], confidence="medium", open_questions=[])


BOOKMARK_STORIES = [   # key, US, requirement, MoSCoW, points from the tracker (None = derived), noun
    ("BM-2", "US-1", "FR-001", "must", 3, "save"),
    ("BM-3", "US-2", "FR-002", "should", 2, "list by tag"),
    ("BM-4", "US-3", "FR-003", "could", None, "delete"),
]


def build_story_backlog(root: Path) -> None:
    """What Task Breakdown produces for the bookmarks fixture, without a model: approved stories in
    phase4/stories.json and a validated story-based backlog (DB, BE, FE and QA tasks per story)."""
    from agent_engine.phase4 import backlog, files, task_breakdown as tb
    from agent_engine.phase4.contracts import ProjectSettings, StorySnapshot
    stories = []
    for n, (key, us, fr, moscow, points, noun) in enumerate(BOOKMARK_STORIES):
        stories.append({"key": key, "issue_id": str(10002 + n), "summary": f"Bookmarks: {noun}",
                        "statement": f"As a user, I want to {noun} bookmarks so that I find saved pages again.",
                        "acceptance_criteria": [{"ac_id": f"{us}.AC1", "text": f"Given a bookmark, When I {noun} it, Then it works."},
                                                {"ac_id": f"{us}.AC2", "text": f"Given no access, When I {noun}, Then it is refused."}],
                        "requirement_ids": [us, fr], "moscow": moscow, "story_points": points,
                        "components": ["ARCH-001", "ARCH-002"], "epic_key": "BM-1",
                        "blocks": ["BM-3"] if key == "BM-2" else []})
    snapshot = {"project": root.name, "source": "file", "project_key": "BM", "stories": stories,
                "epics": [{"key": "BM-1", "issue_id": "10001", "summary": "Bookmark management",
                           "requirement_ids": ["FR-001", "FR-002", "FR-003"]}]}
    (root / "phase4").mkdir(parents=True, exist_ok=True)
    (root / "phase4/stories.json").write_text(json.dumps(snapshot), encoding="utf-8")
    project = root.name
    snap = files.read_json(project, files.STORIES, StorySnapshot)
    settings = files.read_json(project, files.PROJECT_SETTINGS, ProjectSettings)
    results = {}
    for key, us, _, _, _, noun in BOOKMARK_STORIES:
        both = [f"{us}.AC1", f"{us}.AC2"]
        slug = noun.replace(" ", "_")
        results[key] = tb.StoryBreakdown(story_key=key, estimate_rationale="DB, API, screen and tests.",
                                         reference_ticket_ids=[], open_questions=[], deferred_criteria=[], tasks=[
            _task("T1", "DB", f"Bookmark table for {noun}", 2, ["postgres"], [f"migrations/{slug}.sql"], []),
            _task("T2", "BE", f"API to {noun} bookmarks", 4, ["backend-python", "api-design"], [f"app/bookmarks/{slug}.py"],
                  both, ["T1"]),
            _task("T3", "FE", f"Screen to {noun} bookmarks", 3, ["frontend-react"], [f"web/src/{slug}.tsx"], [f"{us}.AC1"],
                  ["T2"], repo="acme/taskflow-web"),
            _task("T4", "QA", f"End-to-end tests to {noun} bookmarks", 3, ["qa-automation"], [f"tests/test_{slug}.py"], both,
                  ["T2", "T3"])])
    files.write_json(project, files.BACKLOG, tb.build_backlog(project, snap, settings, results))
    report = json.loads(backlog.validate_report(project))
    assert report["ready_for_review"], report["blocking"]
