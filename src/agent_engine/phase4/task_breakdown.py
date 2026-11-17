"""Task Breakdown (PDLC Phase 4, step 4.1): approved stories -> FE / BE / DB / DevOps / QA tasks.

Input is phase4/stories.json (the stories approved at Gate 2, imported from Jira by story_import.py), plus
architecture.md, prd.md (for the A-/PD-/NFR- references stories make) and phase4/project.json. Stories, their
acceptance criteria and priorities are never rewritten; this stage only adds tasks, estimates and dependencies.

  * One structured model call per story. The shared part of every call (rules, settings, skill list, the full
    architecture and PRD) is one cached prompt prefix; the first call runs alone so the others read the cache.
  * Results are kept under .engine-task-breakdown/ by an exact digest of what produced them, so an unchanged story
    is never sent again; a repaired story keeps its repair until its inputs change.
  * Code does everything exact: ids, dependency graph checks, Jira "blocks" links as story dependencies, hour
    rounding, story points (kept from Jira, or derived from task hours), and the backlog file itself.

Review is deterministic here (backlog.validate); a failed check sends only the affected stories back once.
"""
from __future__ import annotations

import asyncio
import contextvars
import hashlib
import json
import os
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from langchain_core.messages import AIMessage
from pydantic import BaseModel, ConfigDict

from agent_engine.phase4 import backlog, files, skills_taxonomy
from agent_engine.phase4.contracts import (
    AcceptanceCriterion,
    Backlog,
    Dependency,
    Estimate,
    Feature,
    History,
    ImportedStory,
    ProjectSettings,
    SourceRef,
    StorySnapshot,
    UserStory,
    WorkItem,
)

STATE_DIR = ".engine-task-breakdown"
MAX_TASK_HOURS = 16.0
DISCIPLINES = ("FE", "BE", "DB", "DevOps", "QA")
DISCIPLINE_TYPE = {"FE": "ui", "BE": "feature", "DB": "feature", "DevOps": "infra", "QA": "test"}
MOSCOW_PRIORITY = {"must": "P1", "should": "P2", "could": "P3", "wont": "P3"}
DEFAULT_REQUESTS = {"", "Break the approved stories down into tasks.", "Break prd.md down into a backlog."}
NO_EPIC = "NO-EPIC"
_STATEMENT = re.compile(r"^\s*as\s+(?:an?\s+)?(.+?),\s*I\s+want(?:\s+to)?\s+(.+?)(?:,?\s+so\s+that\s+(.+?))?\.?\s*$",
                        re.I | re.S)


# ---------------------------------------------------------------------------------------------- model output
class _Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TaskDraft(_Record):
    local_id: str                                     # T1, T2, ... unique within the story
    discipline: Literal["FE", "BE", "DB", "DevOps", "QA"]
    title: str
    description: str
    acceptance_criteria: list[str]                    # 1-3 testable statements for this task
    covers: list[str]                                 # story acceptance-criterion ids this task implements/verifies
    file_paths: list[str]                             # only paths the architecture/PRD defines; else empty
    repo: str | None                                  # one of the project's code_repos, or null
    hours: float
    depends_on: list[str]                             # local ids of tasks in this story that must finish first
    skills: list[str]                                 # 1-2 tags from the skill taxonomy, most important first
    definition_of_done: list[str]                     # task-specific additions only; the project DoD is added by code
    confidence: Literal["low", "medium", "high"]
    open_questions: list[str]


class DeferredCriterion(_Record):
    ac_id: str                                        # a story acceptance criterion no task implements yet
    reason: str                                       # the reviewer decision it follows


class StoryBreakdown(_Record):
    story_key: str
    tasks: list[TaskDraft]
    estimate_rationale: str
    reference_ticket_ids: list[str]                   # history tickets actually used as analogies; else empty
    open_questions: list[str]
    deferred_criteria: list[DeferredCriterion]        # only when reviewer_request says not to build them; else empty


class CrossDependency(_Record):
    item_id: str                                      # the task (or story) that has to wait
    on_id: str                                        # the task (or story) in ANOTHER story it waits for
    reason: str
    confidence: float                                 # 0-1; below 0.6 it becomes an open question, not an edge


class SharedWork(_Record):
    keep_id: str                                      # the task that stays and serves every story listed
    duplicate_ids: list[str]                          # same work planned in other stories; they are removed
    reason: str
    confidence: float                                 # 0-1; merged only at 0.8 or above, else an open question


class CrossStoryReview(_Record):
    dependencies: list[CrossDependency]
    shared_work: list[SharedWork]


# ---------------------------------------------------------------------------------------------- model selection
_tier = contextvars.ContextVar("task_breakdown_tier", default="strong")
_base_tier = contextvars.ContextVar("task_breakdown_base_tier", default="strong")


@contextmanager
def operation_model(pack, level: int):
    """The model of this pass (escalated after a failed check) and the pack's default model."""
    token, base = _tier.set(pack.models[level]), _base_tier.set(pack.models[0])
    try:
        yield
    finally:
        _tier.reset(token)
        _base_tier.reset(base)


def _spec() -> str:
    """The model that answers calls in this pass."""
    from agent_engine.agent import model_spec
    return model_spec(_tier.get())


def _identity_spec() -> str:
    """The configured default model: part of what makes a retained result reusable. An escalated fix pass must not
    invalidate every unaffected story."""
    from agent_engine.agent import model_spec
    return model_spec(_base_tier.get())


# ---------------------------------------------------------------------------------------------- inputs
def snapshot(project: str) -> StorySnapshot:
    if not files.exists(project, files.STORIES):
        raise files.ProjectError(f"{files.STORIES} is missing: import the approved stories first "
                                 "(agent-engine phase4 import-stories)")
    return files.read_json(project, files.STORIES, StorySnapshot)


def _settings(project: str) -> ProjectSettings:
    return files.read_json(project, files.PROJECT_SETTINGS, ProjectSettings)


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def history_tickets_digest(text: str) -> str:
    """Task Breakdown reads only the resolved tickets of history.json (estimation examples). Closed sprints are Sprint
    Planning's velocity; a new closed sprint must not make an approved backlog stale."""
    tickets = json.loads(text).get("tickets", [])
    return "tickets:" + _digest(tickets)


def source_manifest(project: str, settings: ProjectSettings | None = None) -> dict[str, str]:
    """What a story-based backlog was built from; validation reports it stale when any of these change."""
    settings = settings or _settings(project)
    out = {rel: files.file_sha(project, rel) for rel in (files.STORIES, files.ARCHITECTURE, files.PRD)
           if files.exists(project, rel)}
    for rel in context_documents(project):
        out[rel] = files.file_sha(project, rel)
    if files.exists(project, files.HISTORY):
        out[files.HISTORY] = history_tickets_digest(files.read_text(project, files.HISTORY))
    out[files.PROJECT_SETTINGS] = "settings:" + _digest(backlog.source_settings(settings))
    return out


def _settings_view(settings: ProjectSettings) -> dict:
    return {"definition_of_done": settings.definition_of_done, "code_repos": settings.code_repos,
            "infra_repo": settings.infra_repo, "story_point_scale": settings.story_point_scale,
            "hours_per_story_point": settings.hours_per_story_point, "max_task_hours": MAX_TASK_HOURS}


def _rules() -> str:
    from agent_engine.agent import load_pack
    return load_pack("task-breakdown").system_prompt


def context_documents(project: str) -> list[str]:
    root = files.project_dir(project)
    return [rel for rel in ("designs/designs.md", "api/openapi.yaml", "api/openapi.yml", "api/openapi.json")
            if (root / rel).is_file()]


def prompt_prefix(project: str, settings: ProjectSettings) -> str:
    """The part shared by every story call; sent once as a cached prefix."""
    parts = [_rules(),
             "## Project settings\n" + json.dumps(_settings_view(settings), ensure_ascii=False, indent=1),
             "## Skill taxonomy (use only these tags)\n" + ", ".join(skills_taxonomy.tags())]
    for rel, title in ((files.ARCHITECTURE, "Approved architecture (architecture.md)"),
                       (files.PRD, "Approved PRD (prd.md): defines the A-, PD-, NFR- and FR- ids stories refer to")):
        if files.exists(project, rel):
            parts.append(f"## {title}\n\n" + files.read_text(project, rel))
    for rel in context_documents(project):
        parts.append(f"## Approved context ({rel})\n\n" + files.read_text(project, rel))
    return "\n\n".join(parts)


def _analogies(project: str, story: ImportedStory) -> dict:
    if not files.exists(project, files.HISTORY):
        return {"analogy_valid": False, "references": []}
    from agent_engine.phase4.textsim import similarities
    tickets = [t for t in files.read_json(project, files.HISTORY, History).tickets if t.story_points or t.hours]
    if not tickets:
        return {"analogy_valid": False, "references": []}
    query = "\n".join([story.summary, story.statement, *(c.text for c in story.acceptance_criteria)])
    scores = similarities([query], [f"{t.title}\n{t.body}" for t in tickets])[0]
    order = [i for i in sorted(range(len(tickets)), key=lambda i: -scores[i]) if scores[i] > 0][:5]
    valid = len(tickets) >= backlog.MIN_HISTORY and bool(order) and float(scores[order[0]]) >= backlog.MIN_SIMILARITY
    return {"analogy_valid": valid,
            "references": [{**tickets[i].model_dump(mode="json", include={"key", "title", "story_points", "hours"}),
                            "similarity": round(float(scores[i]), 3)} for i in order] if valid else []}


def _story_view(story: ImportedStory) -> dict:
    """What a story's tasks depend on. Backlog order (rank) and release do not change the tasks, so reordering the
    roadmap in the tracker rebuilds the backlog from retained results without new model calls."""
    return story.model_dump(mode="json", exclude={"description_md", "issue_id", "labels", "approval", "status",
                                                  "rank", "fix_versions"})


def story_release(story: ImportedStory, releases) -> str | None:
    """The story's roadmap release: its earliest fix version in roadmap order (else its first fix version)."""
    order = {r.name: r.order for r in releases}
    known = sorted((v for v in story.fix_versions if v in order), key=order.get)
    return known[0] if known else (story.fix_versions[0] if story.fix_versions else None)


def _targets(request: str, keys: set[str]) -> set[str] | None:
    """Story keys a reviewer request names; None = it applies to every story."""
    if request.strip() in DEFAULT_REQUESTS:
        return set()
    named = {k for k in re.findall(r"\b[A-Z][A-Z0-9]+-\d+\b", request) if k in keys}
    return named or None


# ---------------------------------------------------------------------------------------------- checks on one result
def check_breakdown(story: ImportedStory, result: StoryBreakdown, settings: ProjectSettings,
                    deferrable: bool = False) -> list[str]:
    """`deferrable`: a gate reviewer's request names this story, so it may leave criteria unplanned on purpose."""
    errors = []
    if result.story_key != story.key:
        errors.append(f"story_key must be {story.key}, got {result.story_key}")
    if not result.tasks:
        return errors + ["at least one task is required"]
    ids = [t.local_id for t in result.tasks]
    if len(ids) != len(set(ids)):
        errors.append("local_id values must be unique")
    known = set(ids)
    ac_ids = {c.ac_id for c in story.acceptance_criteria}
    taxonomy = set(skills_taxonomy.tags())
    for t in result.tasks:
        where = f"task {t.local_id}"
        if not t.title.strip() or not t.description.strip():
            errors.append(f"{where}: title and description are required")
        if not 1 <= len([a for a in t.acceptance_criteria if a.strip()]) <= 3:
            errors.append(f"{where}: give 1 to 3 acceptance criteria")
        if not 0 < t.hours <= MAX_TASK_HOURS:
            errors.append(f"{where}: hours must be > 0 and <= {MAX_TASK_HOURS:g}; split bigger work into more tasks")
        if unknown := [d for d in t.depends_on if d not in known or d == t.local_id]:
            errors.append(f"{where}: depends_on has unknown or self ids {unknown}")
        if bad := [c for c in t.covers if c not in ac_ids]:
            errors.append(f"{where}: covers names acceptance criteria not in the story {bad}")
        if t.repo and t.repo not in settings.code_repos:
            errors.append(f"{where}: repo {t.repo!r} is not one of {settings.code_repos}")
        if not [s for s in t.skills if s in taxonomy or skills_taxonomy.normalize(s)]:
            errors.append(f"{where}: needs 1-2 skills from the taxonomy")
    deferred = {d.ac_id for d in result.deferred_criteria}
    if result.deferred_criteria and not deferrable:
        errors.append("deferred_criteria is only for criteria a reviewer_request says not to build; cover every criterion")
    if bad := sorted(deferred - ac_ids):
        errors.append(f"deferred_criteria names acceptance criteria not in the story {bad}")
    if not all(d.reason.strip() for d in result.deferred_criteria):
        errors.append("each deferred criterion needs the reviewer decision as its reason")
    covered = {c for t in result.tasks for c in t.covers}
    if both := sorted(deferred & covered):
        errors.append(f"acceptance criteria {both} are both deferred and covered by a task")
    if uncovered := sorted(ac_ids - covered - deferred):
        errors.append(f"no task covers acceptance criteria {uncovered}")
    graph = {t.local_id: set(t.depends_on) for t in result.tasks}
    seen, stack = set(), set()

    def cyclic(node):
        if node in stack:
            return True
        if node in seen:
            return False
        seen.add(node)
        stack.add(node)
        found = any(cyclic(n) for n in graph.get(node, ()) if n in graph)
        stack.discard(node)
        return found
    if any(cyclic(n) for n in graph):
        errors.append("depends_on contains a cycle")
    return errors


# ---------------------------------------------------------------------------------------------- model call
from agent_engine.phase4.structured import invoke as _invoke   # noqa: E402  (one structured call, cached prefix)


# ---------------------------------------------------------------------------------------------- retained results
def _state(project: str, *parts: str) -> Path:
    root = files.project_dir(project).resolve()
    path = root / STATE_DIR / Path(*parts)
    if not path.resolve().is_relative_to(root / STATE_DIR):
        raise files.ProjectError("invalid task-breakdown state path")
    return path


def _load(project: str, *parts: str):
    try:
        return json.loads(_state(project, *parts).read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return None


def _save(project: str, value, *parts: str) -> None:
    from agent_engine.runtime import atomic_json
    path = _state(project, *parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_json(path, value)


def _base_identity(project, story, settings, prefix, request_for_story, spec) -> str:
    return _digest({"story": _story_view(story), "settings": _settings_view(settings), "prefix": _digest(prefix),
                    "request": request_for_story, "analogies": _analogies(project, story), "model": spec,
                    "schema": StoryBreakdown.model_json_schema()})


async def breakdown_story(project, story, settings, prefix, callbacks, *, request="", findings=(), spec=None):
    """One story -> a checked StoryBreakdown. A failed check is repaired once, then the error is raised."""
    spec = spec or _spec()
    analogies = _analogies(project, story)
    payload = {"story": _story_view(story), "history": analogies}
    if request:
        payload["reviewer_request"] = request
    if findings:
        payload["findings_to_fix"] = list(findings)
    human = "Break this approved story into tasks.\n" + json.dumps(payload, ensure_ascii=False, indent=1)
    result = await _invoke(StoryBreakdown, prefix, human, callbacks, spec)
    errors = check_breakdown(story, result, settings, deferrable=bool(request))
    if errors:
        retry = human + "\n\nYour previous answer failed these checks; return a corrected complete answer:\n- " + \
            "\n- ".join(errors) + "\n\nPrevious answer:\n" + result.model_dump_json()
        result = await _invoke(StoryBreakdown, prefix, retry, callbacks, spec)
        errors = check_breakdown(story, result, settings, deferrable=bool(request))
        if errors:
            raise files.ProjectError(f"{story.key}: task breakdown still fails checks: " + "; ".join(errors))
    valid_refs = {r["key"] for r in analogies["references"]}
    result.reference_ticket_ids = [r for r in result.reference_ticket_ids if r in valid_refs]
    return result


# ---------------------------------------------------------------------------------------------- backlog assembly
def _user_story(statement: str) -> UserStory | None:
    m = _STATEMENT.match(statement or "")
    if not m:
        return None
    return UserStory(as_a=m.group(1).strip(), i_want=m.group(2).strip(" ,."),
                     so_that=(m.group(3) or "").strip(" .") or "the acceptance criteria are met")


def _complexity_from_points(points: int, scale: list[int]) -> int:
    index = scale.index(points) if points in scale else len(scale) - 1
    return min(10, max(1, round(10 * (index + 1) / len(scale))))


def _story_estimate(story: ImportedStory, tasks: list[WorkItem], result: StoryBreakdown,
                    settings: ProjectSettings) -> Estimate:
    scale = settings.story_point_scale
    hours = sum(t.estimate.hours for t in tasks)
    if story.story_points is not None and int(story.story_points) == story.story_points and int(story.story_points) in scale:
        points = int(story.story_points)
        return Estimate(story_points=points, complexity=_complexity_from_points(points, scale), confidence="high",
                        method="human", rationale=f"Set upstream in the tracker; tasks total {hours:g} h.")
    points = backlog._snap(hours / settings.hours_per_story_point, scale)
    order = {"low": 0, "medium": 1, "high": 2}
    confidence = min((t.estimate.confidence for t in tasks), key=order.get, default="low")
    return Estimate(story_points=points, complexity=_complexity_from_points(points, scale), confidence=confidence,
                    method="analogy" if result.reference_ticket_ids else "rollup",
                    reference_ticket_ids=result.reference_ticket_ids,
                    rationale=f"Derived from {len(tasks)} tasks totalling {hours:g} h at {settings.hours_per_story_point:g} "
                              f"h/SP. {result.estimate_rationale}".strip())


def _round_hours(hours: float) -> float:
    return max(0.5, round(hours * 2) / 2)


def story_items(story: ImportedStory, epic_id: str, result: StoryBreakdown, settings: ProjectSettings,
                releases=()) -> list[WorkItem]:
    moscow = story.moscow or "should"
    task_ids = {t.local_id: f"{story.key}-T{n:02d}" for n, t in enumerate(result.tasks, 1)}
    method = "analogy" if result.reference_ticket_ids else "llm"
    tasks = []
    for t in result.tasks:
        tid = task_ids[t.local_id]
        skills = list(dict.fromkeys(s if s in skills_taxonomy.tags() else skills_taxonomy.normalize(s) or "" for s in t.skills))
        hours = _round_hours(t.hours)
        tasks.append(WorkItem(
            item_id=tid, level="task", parent_id=story.key, title=" ".join(t.title.split())[:200],
            description_md=t.description.strip(), type=DISCIPLINE_TYPE[t.discipline], discipline=t.discipline,
            priority=MOSCOW_PRIORITY[moscow], moscow=moscow,
            acceptance_criteria=[AcceptanceCriterion(ac_id=f"AC-{tid}-{i}",
                                                     format="gherkin" if a.strip().lower().startswith("given") else "ears",
                                                     text=a.strip())
                                 for i, a in enumerate([a for a in t.acceptance_criteria if a.strip()], 1)],
            definition_of_done=list(dict.fromkeys([*settings.definition_of_done, *t.definition_of_done])),
            file_paths=list(t.file_paths), components=list(story.components), repo=t.repo,
            dependencies=[Dependency(on_id=task_ids[d], reason="must finish first within the story", confidence=0.9,
                                     origin="llm") for d in t.depends_on],
            estimate=Estimate(hours=hours, complexity=min(10, max(1, round(hours / MAX_TASK_HOURS * 10))),
                              confidence=t.confidence, method=method, reference_ticket_ids=result.reference_ticket_ids,
                              rationale=f"{t.discipline} task of {story.key}"),
            skills_required=[s for s in skills if s][:2], ai_eligible=False,
            ai_eligibility_reason="Decided by the Work Allocation agent.",
            source_refs=[SourceRef(req_id=c, source="story", anchor=story.key) for c in t.covers],
            open_questions=list(t.open_questions)))
    story_item = WorkItem(
        item_id=story.key, level="story", parent_id=epic_id, title=story.summary,
        description_md="\n\n".join(p for p in (story.statement, story.notes) if p), type="feature",
        priority=MOSCOW_PRIORITY[moscow], moscow=moscow, user_story=_user_story(story.statement),
        release=story_release(story, releases), rank=story.rank,
        acceptance_criteria=[AcceptanceCriterion(ac_id=c.ac_id, text=c.text,
                                                 format="gherkin" if c.text.lower().startswith("given") else "ears")
                             for c in story.acceptance_criteria],
        definition_of_done=list(settings.definition_of_done), components=list(story.components),
        source_refs=[SourceRef(req_id=r, source="story", anchor=story.key) for r in story.requirement_ids],
        open_questions=[*result.open_questions,
                        *(f"{d.ac_id} is not planned (reviewer decision): {d.reason}" for d in result.deferred_criteria)],
        deferred_criteria=[d.ac_id for d in result.deferred_criteria])
    story_item.estimate = _story_estimate(story, tasks, result, settings)
    return [story_item, *tasks]


def build_backlog(project: str, snap: StorySnapshot, settings: ProjectSettings,
                  results: dict[str, StoryBreakdown], cross: "CrossStoryReview | None" = None) -> Backlog:
    epics = {e.key: e for e in snap.epics}
    by_epic: dict[str, list[ImportedStory]] = {}
    for s in snap.stories:
        by_epic.setdefault(s.epic_key if s.epic_key in epics else NO_EPIC, []).append(s)
    items: list[WorkItem] = []
    features: list[Feature] = []
    rank = {"must": 0, "should": 1, "could": 2, "wont": 3}
    keys = {s.key for s in snap.stories}
    for epic_id, stories in by_epic.items():
        epic = epics.get(epic_id)
        title = epic.summary if epic else "Stories without an epic"
        moscow = min((s.moscow or "should" for s in stories), key=rank.get)
        requirement_ids = epic.requirement_ids if epic else []
        components = sorted({c for s in stories for c in s.components})
        features.append(Feature(feature_key=epic_id, feature_dir="", title=title,
                                summary=(epic.description_md if epic else "")[:1000],
                                requirement_ids=requirement_ids, component_ids=components))
        items.append(WorkItem(item_id=epic_id, level="epic", title=title,
                              description_md=epic.description_md if epic else "", priority=MOSCOW_PRIORITY[moscow],
                              moscow=moscow, components=components,
                              source_refs=[SourceRef(req_id=r, source="prd", anchor=epic_id) for r in requirement_ids]))
        for s in stories:
            items += story_items(s, epic_id, results[s.key], settings, snap.releases)
    by = {i.item_id: i for i in items}
    for s in snap.stories:                       # Jira "A blocks B": B cannot start before A
        for blocked in s.blocks:
            if blocked in keys and blocked != s.key:
                by[blocked].dependencies.append(Dependency(on_id=s.key, reason=f"tracker link: {s.key} blocks {blocked}",
                                                           confidence=1.0, origin="human"))
    if cross is not None:
        items = apply_cross(items, snap, settings, results, cross)
    previous = files.read_json(project, files.BACKLOG) if files.exists(project, files.BACKLOG) else {}
    return Backlog(backlog_id=previous.get("backlog_id") or files.new_id(), version=int(previous.get("version", 0)) + 1,
                   project=project, sources=source_manifest(project, settings), features=features,
                   releases=list(snap.releases), items=items,
                   generated_at=files.utcnow())


# ---------------------------------------------------------------------------------------------- cross-story pass
MIN_EDGE_CONFIDENCE = 0.6
MIN_MERGE_CONFIDENCE = 0.8


def task_ids(story_key: str, result: StoryBreakdown) -> dict[str, str]:
    return {t.local_id: f"{story_key}-T{n:02d}" for n, t in enumerate(result.tasks, 1)}


def cross_story_index(snap: StorySnapshot, results: dict[str, StoryBreakdown]) -> list[dict]:
    """A compact view of every story and its tasks: enough to see shared work and ordering, nothing more."""
    rows = []
    for s in snap.stories:
        ids = task_ids(s.key, results[s.key])
        rows.append({"story": s.key, "summary": s.summary, "epic": s.epic_key, "components": s.components,
                     "requirement_ids": s.requirement_ids, "blocks": s.blocks,
                     "tasks": [{"id": ids[t.local_id], "discipline": t.discipline, "title": t.title,
                                "description": t.description[:300],
                                "depends_on": [ids[d] for d in t.depends_on]} for t in results[s.key].tasks]})
    return rows


def _owner(item_id: str, stories: set[str], task_owner: dict[str, str]) -> str | None:
    return item_id if item_id in stories else task_owner.get(item_id)


def screen_cross(review: CrossStoryReview, snap: StorySnapshot, results: dict[str, StoryBreakdown]):
    """Keep only valid, confident proposals. Returns (edges, merges, questions{item_id: [text]})."""
    stories = {s.key for s in snap.stories}
    task_owner, discipline = {}, {}
    for s in snap.stories:
        ids = task_ids(s.key, results[s.key])
        for t in results[s.key].tasks:
            task_owner[ids[t.local_id]] = s.key
            discipline[ids[t.local_id]] = t.discipline
    jira = {(b, s.key) for s in snap.stories for b in s.blocks} | {(s.key, b) for s in snap.stories for b in s.blocks}
    import networkx as nx
    order = nx.DiGraph()                       # story order so far: tracker links, then accepted proposals
    order.add_edges_from((s.key, b) for s in snap.stories for b in s.blocks if b in stories)
    edges, merges, questions, seen = [], [], {}, set()
    for d in sorted(review.dependencies, key=lambda d: -d.confidence):
        a, b = _owner(d.item_id, stories, task_owner), _owner(d.on_id, stories, task_owner)
        same_level = (d.item_id in stories) == (d.on_id in stories)
        if not a or not b or a == b or not same_level or (d.item_id, d.on_id) in seen:
            continue
        if d.item_id in stories and (d.item_id, d.on_id) in jira:
            continue                                   # the tracker already says so
        seen.add((d.item_id, d.on_id))
        if a in order and b in order and nx.has_path(order, a, b):
            questions.setdefault(d.item_id, []).append(
                f"Proposed dependency on {d.on_id} contradicts the existing story order ({b} already waits for {a}); "
                f"not added: {d.reason}")
            continue
        if d.confidence >= MIN_EDGE_CONFIDENCE:
            order.add_edge(b, a)
            edges.append(d)
        else:
            questions.setdefault(d.item_id, []).append(
                f"Possible dependency on {d.on_id} ({d.confidence:.1f}): {d.reason}")
    used = set()
    for m in review.shared_work:
        dups = [x for x in dict.fromkeys(m.duplicate_ids) if x != m.keep_id]
        group = [m.keep_id, *dups]
        valid = (dups and all(x in task_owner for x in group)
                 and len({task_owner[x] for x in group}) == len(group)          # one task per story
                 and len({discipline[x] for x in group}) == 1 and discipline[m.keep_id] != "QA"
                 and not used & set(group))
        if valid and m.confidence >= MIN_MERGE_CONFIDENCE:
            merges.append(SharedWork(keep_id=m.keep_id, duplicate_ids=dups, reason=m.reason, confidence=m.confidence))
            used |= set(group)
        elif dups and m.keep_id in task_owner:
            questions.setdefault(m.keep_id, []).append(
                f"Possibly the same work as {', '.join(dups)} ({m.confidence:.1f}): {m.reason}")
    return edges, merges, questions


async def cross_story(project: str, snap: StorySnapshot, settings: ProjectSettings,
                      results: dict[str, StoryBreakdown], callbacks) -> CrossStoryReview:
    """One call over all stories: dependencies between stories' tasks and the same work planned twice."""
    empty = CrossStoryReview(dependencies=[], shared_work=[])
    if len(snap.stories) < 2:
        return empty
    spec = _spec()
    prefix = prompt_prefix(project, settings)
    index = cross_story_index(snap, results)
    identity = _digest({"index": index, "prefix": _digest(prefix), "model": _identity_spec(),
                        "schema": CrossStoryReview.model_json_schema()})
    saved = _load(project, "cross", identity + ".json")
    if saved is not None:
        return CrossStoryReview.model_validate(saved)
    human = ("Cross-story review (see 'Cross-story review' in your instructions). Stories and their tasks:\n"
             + json.dumps(index, ensure_ascii=False, indent=1))
    review = await _invoke(CrossStoryReview, prefix, human, callbacks, spec)
    _save(project, review.model_dump(mode="json"), "cross", identity + ".json")
    return review


def apply_cross(items: list[WorkItem], snap: StorySnapshot, settings: ProjectSettings,
                results: dict[str, StoryBreakdown], review: CrossStoryReview) -> list[WorkItem]:
    edges, merges, questions = screen_cross(review, snap, results)
    by = {i.item_id: i for i in items}
    for e in edges:
        item = by[e.item_id]
        if not any(d.on_id == e.on_id for d in item.dependencies):
            item.dependencies = [*item.dependencies, Dependency(on_id=e.on_id, reason=e.reason,
                                                                confidence=e.confidence, origin="llm")]
    removed: dict[str, str] = {}
    for m in merges:
        keep = by[m.keep_id]
        for dup_id in m.duplicate_ids:
            dup = by[dup_id]
            keep.source_refs = [*keep.source_refs, *[r for r in dup.source_refs if r not in keep.source_refs]]
            keep.open_questions = [*keep.open_questions,
                                   f"Shared work: also serves {dup.parent_id} in place of {dup_id} ({m.reason})"]
            keep.dependencies = [*keep.dependencies, *[d for d in dup.dependencies if d.on_id != keep.item_id
                                                       and not any(x.on_id == d.on_id for x in keep.dependencies)]]
            removed[dup_id] = keep.item_id
    items = [i for i in items if i.item_id not in removed]
    for i in items:
        deps, targets = [], set()
        for d in i.dependencies:
            on = removed.get(d.on_id, d.on_id)
            if on != i.item_id and on not in targets:
                targets.add(on)
                deps.append(d if on == d.on_id else Dependency(on_id=on, reason=d.reason, confidence=d.confidence,
                                                               origin=d.origin))
        i.dependencies = deps
    for item_id, texts in questions.items():
        target = by.get(removed.get(item_id, item_id))
        if target is not None:
            target.open_questions = [*target.open_questions, *texts]
    if removed:                                  # derived story points follow the tasks that remain
        stories = {s.key: s for s in snap.stories}
        by = {i.item_id: i for i in items}
        for key in {by[k].parent_id for k in removed.values()} | {dup.rsplit("-T", 1)[0] for dup in removed}:
            story = by.get(key)
            if story and story.estimate and story.estimate.method in ("rollup", "analogy"):
                tasks = [i for i in items if i.parent_id == key and i.level == "task"]
                if tasks:
                    story.estimate = _story_estimate(stories[key], tasks, results[key], settings)
    return items


# ---------------------------------------------------------------------------------------------- stage operations
def _generation_request(project: str, keys: set[str], key: str) -> str:
    """The stage request a story was last generated under (results saved before requests were recorded)."""
    from agent_engine import recovery
    try:
        request = json.loads(recovery.path(files.project_dir(project), "task-breakdown").read_text(encoding="utf-8"))["request"]
    except (OSError, ValueError, KeyError, TypeError):
        return ""
    targets = _targets(request, keys)
    return request if targets is None or key in targets else ""


def _current(project: str) -> dict:
    return _load(project, "current.json") or {}


async def _results(project: str, snap: StorySnapshot, settings: ProjectSettings, callbacks, request: str,
                   repairs: dict[str, list[str]] | None = None) -> dict[str, StoryBreakdown]:
    """Every story's breakdown: retained when its inputs are unchanged, generated otherwise."""
    spec, identity_spec = _spec(), _identity_spec()
    prefix = prompt_prefix(project, settings)
    keys = {s.key for s in snap.stories}
    targets = _targets(request, keys)
    current = _current(project)
    results: dict[str, StoryBreakdown] = {}
    todo = []
    for story in snap.stories:
        story_request = request if targets is None or story.key in targets else ""
        fix = (repairs or {}).get(story.key)
        record = _load(project, "stories", current.get(story.key, "") + ".json") if current.get(story.key) else None
        if not story_request:
            # A reviewer request stays with its story (e.g. a decision to defer criteria) until a newer request names
            # the story: repairs and rebuilds must not fall back to a result generated before the decision.
            if record and "request" in record:
                story_request = record["request"]
            elif fix:
                story_request = _generation_request(project, keys, story.key)
        base = _base_identity(project, story, settings, prefix, story_request, identity_spec)
        if not fix and record and record.get("base") == base:
            results[story.key] = StoryBreakdown.model_validate(record["result"])
            continue
        cached = None if fix else _load(project, "stories", base + ".json")
        if cached:
            results[story.key] = StoryBreakdown.model_validate(cached["result"])
            current[story.key] = base
            continue
        todo.append((story, story_request, base, fix))

    concurrency = int(os.environ.get("AGENT_ENGINE_HELPER_CONCURRENCY", "9"))
    if not 1 <= concurrency <= 32:
        raise ValueError("AGENT_ENGINE_HELPER_CONCURRENCY must be between 1 and 32")
    semaphore = asyncio.Semaphore(concurrency)

    async def run(story, story_request, base, fix):
        async with semaphore:
            result = await breakdown_story(project, story, settings, prefix, callbacks, request=story_request,
                                           findings=fix or (), spec=spec)
            record_id = base if not fix else _digest({"base": base, "findings": fix})
            _save(project, {"base": base, "request": story_request, "findings": fix or [], "model": spec,
                            "result": result.model_dump(mode="json")},
                  "stories", record_id + ".json")
            return story.key, record_id, result

    async def gather(batch):
        jobs = [asyncio.create_task(run(*job)) for job in batch]
        try:
            return await asyncio.gather(*jobs)
        except BaseException:
            for job in jobs:
                job.cancel()
            await asyncio.gather(*jobs, return_exceptions=True)
            raise
    done = []
    if todo:
        done += await gather(todo[:1])          # first call alone: it writes the prompt cache the others read
        done += await gather(todo[1:])
    for key, record_id, result in done:
        results[key] = result
        current[key] = record_id
    _save(project, {k: v for k, v in current.items() if k in keys}, "current.json")
    return results


async def _write(project: str, snap: StorySnapshot, settings: ProjectSettings, results, callbacks) -> dict:
    cross = await cross_story(project, snap, settings, results, callbacks)
    files.write_json(project, files.BACKLOG, build_backlog(project, snap, settings, results, cross))
    return json.loads(backlog.validate_report(project))


def _summary(check: dict, generated: int, total: int) -> str:
    return (f"Backlog: backlog/backlog.json and backlog/backlog.md. {check['stories']} stories, {check['tasks']} tasks, "
            f"{check['story_points']} story points ({generated} of {total} stories generated, the rest unchanged). "
            f"{len(check['blocking'])} blocking issues, {len(check['warnings'])} warnings.")


async def generate(project: str, request: str, callbacks):
    snap, settings = snapshot(project), _settings(project)
    before = dict(_current(project))
    results = await _results(project, snap, settings, callbacks, request)
    generated = sum(1 for k, v in _current(project).items() if before.get(k) != v)
    check = await _write(project, snap, settings, results, callbacks)
    return {"messages": [AIMessage(content=_summary(check, generated, len(snap.stories)))]}


class ReviewFinding(_Record):
    item_id: str
    severity: Literal["blocking", "warning"]
    message: str


class LightReview(_Record):
    findings: list[ReviewFinding]


REVIEW_STORIES_PER_CALL = 8


def flagged_items(doc: Backlog, issues) -> dict[str, dict[str, list[str]]]:
    """{story key: {item id: [reasons]}} for the items deterministic checks cannot judge alone."""
    by = doc.by_id()
    out: dict[str, dict[str, list[str]]] = {}

    def flag(item_id: str, reason: str) -> None:
        item = by.get(item_id)
        story = item_id if item and item.level == "story" else item.parent_id if item and item.level == "task" else None
        if story:
            reasons = out.setdefault(story, {}).setdefault(item_id, [])
            if reason not in reasons:
                reasons.append(reason)
    for i in doc.items:
        if i.level == "task" and i.estimate and i.estimate.confidence == "low":
            flag(i.item_id, "low_confidence")
    for issue in issues:
        reason = {"vague_criteria": "vague_criteria", "effort_total": "effort_mismatch"}.get(issue.rule)
        for item_id in issue.item_ids if reason else ():
            flag(item_id, reason)
    return out


async def review(project: str, callbacks=None):
    """Deterministic checks always; a model looks only at what they flag (low confidence, vague criteria, effort)."""
    from agent_engine.agent import Verdict, load_pack
    doc, issues = backlog.validate(project, write=False)
    blocking = [i for i in issues if i.severity == "blocking"]
    warnings = [i for i in issues if i.severity == "warning"]
    if blocking:
        verdict = Verdict(satisfied=False, status_so_far="partial",
                          gaps=[json.dumps(b.model_dump(), ensure_ascii=False) for b in blocking],
                          summary=f"Deterministic checks found {len(blocking)} blocking issues.")
        return {"structured_response": verdict, "messages": [AIMessage(content=verdict.summary)]}
    flags = flagged_items(doc, issues)
    findings: list[ReviewFinding] = []
    if flags:
        snap, settings = snapshot(project), _settings(project)
        stories = {s.key: s for s in snap.stories}
        prefix = prompt_prefix(project, settings)
        rules = load_pack("task-breakdown/validator").system_prompt
        spec = _spec()
        by = doc.by_id()
        keys = sorted(flags, key=lambda k: list(stories).index(k) if k in stories else 0)
        batches = [keys[n:n + REVIEW_STORIES_PER_CALL] for n in range(0, len(keys), REVIEW_STORIES_PER_CALL)]
        semaphore = asyncio.Semaphore(int(os.environ.get("AGENT_ENGINE_BREAKDOWN_REVIEW_CONCURRENCY", "4")))

        async def one(batch):
            payload = {"items": [{"story": _story_view(stories[k]) if k in stories else by[k].model_dump(mode="json"),
                                  "tasks": [t.model_dump(mode="json", exclude={"definition_of_done"})
                                            for t in doc.tasks_of(k)],
                                  "flagged": flags[k],
                                  **({"decided_by_reviewer": {
                                      "deferred_criteria": by[k].deferred_criteria,
                                      "decisions": [q for q in by[k].open_questions if "(reviewer decision)" in q]}}
                                     if k in by and by[k].deferred_criteria else {})} for k in batch]}
            identity = _digest({"payload": payload, "rules": rules, "prefix": _digest(prefix), "model": spec,
                                "schema": LightReview.model_json_schema()})
            saved = _load(project, "reviews", identity + ".json")
            if saved is not None:
                return LightReview.model_validate(saved)
            async with semaphore:
                human = rules + "\n\nReview these flagged items:\n" + json.dumps(payload, ensure_ascii=False, indent=1)
                result = await _invoke(LightReview, prefix, human, callbacks, spec)
            _save(project, result.model_dump(mode="json"), "reviews", identity + ".json")
            return result
        allowed = {i for k in flags for i in [k, *(t.item_id for t in doc.tasks_of(k))]}
        for result in await asyncio.gather(*(one(b) for b in batches)):
            findings += [f for f in result.findings if f.item_id in allowed]
    hard = [f for f in findings if f.severity == "blocking"]
    soft = [f for f in findings if f.severity == "warning"]
    notes = "; ".join(f"{f.item_id}: {f.message}" for f in soft[:10])
    verdict = Verdict(
        satisfied=not hard, status_so_far="partial" if hard else "success",
        gaps=[json.dumps({"rule": "review", "severity": "blocking", "item_ids": [f.item_id], "message": f.message},
                         ensure_ascii=False) for f in hard],
        summary=(f"Deterministic checks passed ({len(warnings)} warnings) over {len(doc.stories())} stories. "
                 f"Reviewed {sum(len(v) for v in flags.values())} flagged items in {len(flags)} stories: "
                 f"{len(hard)} blocking, {len(soft)} warnings for the Tech Lead." + (f" {notes}" if notes else "")))
    return {"structured_response": verdict, "messages": [AIMessage(content=verdict.summary)]}


def _affected_stories(backlog_doc: Backlog, findings: list[dict], keys: set[str]) -> dict[str, list[str]]:
    by = backlog_doc.by_id()
    out: dict[str, list[str]] = {}
    for f in findings:
        for iid in f.get("item_ids") or []:
            item = by.get(iid)
            key = iid if iid in keys else (item.parent_id if item and item.level == "task" else None)
            if item and item.level == "epic":
                continue
            if key in keys:
                out.setdefault(key, []).append(f.get("message") or json.dumps(f))
    return out


async def repair(project: str, gaps: list[str], callbacks):
    """Send only the stories named by blocking findings back once, with the findings; rebuild the backlog."""
    snap, settings = snapshot(project), _settings(project)
    findings = []
    for gap in gaps:
        try:
            findings.append(json.loads(gap))
        except ValueError:
            findings.append({"message": gap, "item_ids": []})
    keys = {s.key for s in snap.stories}
    if any(f.get("rule") in ("stale_sources", "missing_story") for f in findings):
        return await generate(project, "", callbacks)        # unchanged stories are reused, changed ones regenerated
    current = files.read_json(project, files.BACKLOG, Backlog)
    affected = _affected_stories(current, findings, keys)
    if not affected:
        # Findings that name no story (e.g. a dependency loop reported by an older check): rebuild from retained
        # results — no new story calls — and let validation repair what it can deterministically.
        return await generate(project, "", callbacks)
    attempt = _digest({"affected": affected, "backlog": [i.model_dump(mode="json") for i in current.items]})
    if _load(project, "repairs", attempt + ".json"):
        raise files.ProjectError("the same findings remain after a repair; partial backlog retained for the Tech Lead")
    results = await _results(project, snap, settings, callbacks, "", repairs=affected)
    _save(project, {"affected": affected}, "repairs", attempt + ".json")
    check = await _write(project, snap, settings, results, callbacks)
    return {"messages": [AIMessage(content=f"Repaired {len(affected)} stories. " + _summary(check, len(affected), len(keys)))]}
