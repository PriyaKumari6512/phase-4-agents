"""Agent 1 (Task Breakdown): spec-kit files -> backlog/backlog.json, plus the deterministic parts around the
agent's own judgement.

  set_features   the agent's split of prd.md into features          -> backlog/features.json
  build          every specs/NNN-*/spec.md + tasks.md -> epics/stories/tasks (+ re-applies earlier enrichments)
  find_similar   resolved tickets similar to each story (estimation by analogy, phase4/history.json)
  update         the agent's enrichments: estimates, acceptance criteria, skills, AI flags, dependencies, splits
  validate       hierarchy, dependency DAG, coverage of prd.md, estimates, skills, sizes -> issues + backlog.md

Enrichments are also kept in backlog/enrichments.json keyed by item id, so a re-run (client feedback, a changed
spec) re-applies them to every item whose title did not change, and only new or changed items need new work.
"""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path

import networkx as nx
import numpy as np

from agent_engine import perf
from agent_engine.phase4 import files, skills_taxonomy, textsim
from agent_engine.phase4.contracts import (
    AcceptanceCriterion,
    Backlog,
    Dependency,
    Estimate,
    Feature,
    FeatureList,
    History,
    ProjectSettings,
    SourceRef,
    UserStory,
    ValidationIssue,
    WorkItem,
)
from agent_engine.phase4.speckit import FEATURE_DIR_RE
from agent_engine.phase4.speckit_parse import REQ_ID_RE, SpeckitFormatError, parse_spec_md, parse_tasks_md, strip_markup

ENRICHMENTS = "backlog/enrichments.json"
DUPLICATE_THRESHOLD = 0.92
COVERAGE_PREFIXES = ("FR-", "NFR-", "US-", "DS-")
MIN_HISTORY = 10
MIN_SIMILARITY = 0.2
SPLIT_HOURS = 16.0
UPDATABLE = {"description_md", "type", "priority", "moscow", "acceptance_criteria", "definition_of_done", "estimate",
             "task_shares", "skills_required", "ai_eligible", "ai_eligibility_reason", "open_questions",
             "add_dependencies", "remove_dependencies", "file_paths", "components", "repo", "split_into", "source_ids",
             "user_story"}
PLACEHOLDER_BENEFIT = "the story's acceptance scenarios are met"   # set when spec.md has no "As a ..." line
_AS_A = re.compile(r"as an?\s+(.+?),\s*i want(?: to)?\s+(.+?)(?:,?\s*so that\s+(.+?))?(?:\(source|$)", re.I | re.S)
_lock = threading.RLock()   # subagents enrich features in parallel; read-modify-write must not interleave


# ============================================================================ features
def set_features(project: str, features: list[dict]) -> str:
    try:
        fl = FeatureList(features=features)
    except Exception as e:
        raise files.ProjectError(f"features do not match the schema: {e}") from e
    keys = [f.feature_key for f in fl.features]
    dirs = [f.feature_dir for f in fl.features]
    problems = []
    if len(set(keys)) != len(keys) or len(set(dirs)) != len(dirs):
        problems.append("feature_key and feature_dir must be unique")
    for f in fl.features:
        if not FEATURE_DIR_RE.fullmatch(f.feature_dir):
            problems.append(f"{f.feature_key}: feature_dir must look like 'specs/001-short-name', got {f.feature_dir!r}")
    nums = [d.split("/")[1][:3] for d in dirs]
    if len(set(nums)) != len(nums):
        problems.append("each feature_dir needs its own 3-digit number")
    prd_ids = _prd_ids(project)
    unknown = sorted({r for f in fl.features for r in f.requirement_ids} - set(prd_ids)) if prd_ids else []
    if unknown:
        problems.append(f"requirement ids not found in prd.md: {', '.join(unknown)}")
    if problems:
        raise files.ProjectError("; ".join(problems))
    files.write_json(project, files.FEATURES, fl)
    covered = {r for f in fl.features for r in f.requirement_ids}
    missing = [r for r in prd_ids if r not in covered and r.startswith(COVERAGE_PREFIXES)]
    return json.dumps({"written": files.virtual(project, files.FEATURES), "features": len(fl.features),
                       "prd_requirement_ids": prd_ids, "not_yet_covered": missing})


def _prd_ids(project: str) -> list[str]:
    if not files.exists(project, files.PRD):
        return []
    return list(dict.fromkeys(REQ_ID_RE.findall(files.read_text(project, files.PRD))))


# ============================================================================ build
def _user_story(body: str, title: str) -> UserStory:
    if m := _AS_A.search(" ".join(body.split())):
        return UserStory(as_a=m.group(1).strip(), i_want=m.group(2).strip(" ,."),
                         so_that=(m.group(3) or "the goal of this story is met").strip(" ."))
    want = title[:1].lower() + title[1:] if title[1:2].islower() else title
    return UserStory(as_a="user", i_want=f"to {want}" if not want.lower().startswith("to ") else want,
                     so_that=PLACEHOLDER_BENEFIT)


def _feature_items(project: str, f: Feature, settings: ProjectSettings) -> list[WorkItem]:
    root = files.path(project, f.feature_dir)
    try:
        spec = parse_spec_md((root / "spec.md").read_text(encoding="utf-8"))
        tasks = parse_tasks_md((root / "tasks.md").read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise files.ProjectError(f"{f.feature_dir}: {Path(e.filename).name} is missing; finish spec-kit for this feature") from e
    except SpeckitFormatError as e:
        raise files.ProjectError(f"{f.feature_dir}: {e}") from e
    n = f.feature_dir.split("/", 1)[1][:3]
    epic_id = f"E-{n}"
    feature_ids = set(f.requirement_ids)
    items: list[WorkItem] = [WorkItem(
        item_id=epic_id, level="epic", title=spec.title or f.title, description_md=f.summary, priority="P1",
        moscow="must", components=list(f.component_ids), repo=f.repo,
        source_refs=[SourceRef(req_id=r, source="prd", anchor=f.feature_key) for r in f.requirement_ids],
        speckit_ref=f"{f.feature_dir}/spec.md")]
    stories: dict[str, WorkItem] = {}
    for st in spec.stories:
        sid = f"S-{n}-US{st.num}"
        acs = [AcceptanceCriterion(ac_id=f"AC-{sid}-{i}", format="gherkin", text=f"Given {g}, When {w}, Then {t}")
               for i, (g, w, t) in enumerate(st.scenarios, 1)]
        srcs = [SourceRef(req_id=s, source="speckit", anchor=f"{f.feature_dir}/spec.md#US{st.num}")
                for s in st.source_ids if s in feature_ids or not feature_ids]
        if not srcs and f.requirement_ids:     # spec-kit did not cite ids: the story inherits its feature's
            srcs = [SourceRef(req_id=r, source="prd", anchor=f"{f.feature_dir}/spec.md#US{st.num}") for r in f.requirement_ids]
        stories[f"US{st.num}"] = WorkItem(
            item_id=sid, level="story", parent_id=epic_id, title=st.title, description_md=strip_markup(st.body)[:4000],
            type="feature", speckit_phase="user_story", priority=st.priority if st.priority in ("P1", "P2", "P3") else "P3",
            moscow="must" if st.priority == "P1" else "should", user_story=_user_story(st.body, st.title),
            acceptance_criteria=acs, source_refs=srcs, components=list(f.component_ids), repo=f.repo,
            speckit_ref=f"{f.feature_dir}/spec.md#US{st.num}")
    synthetic = {"setup": (f"S-SETUP-{n}", "Setup", "P1", "must"),
                 "foundational": (f"S-FOUND-{n}", "Foundational prerequisites", "P1", "must"),
                 "polish": (f"S-POLISH-{n}", "Polish & cross-cutting concerns", "P3", "could")}
    phases_present = {t.phase_kind for t in tasks}
    for kind, (sid, title, prio, moscow) in synthetic.items():
        if kind in phases_present:
            stories[kind] = WorkItem(
                item_id=sid, level="story", parent_id=epic_id, title=f"{spec.title}: {title}", type="chore",
                speckit_phase=kind, priority=prio, moscow=moscow, components=list(f.component_ids), repo=f.repo,
                description_md=f"spec-kit {title.lower()} phase of {spec.title}.",
                acceptance_criteria=[AcceptanceCriterion(
                    ac_id=f"AC-{sid}-1", format="gherkin",
                    text=f"Given the {title.lower()} tasks, When they are done, Then all of them meet the Definition of Done")],
                source_refs=[SourceRef(req_id=epic_id, source="speckit", anchor=f"{f.feature_dir}/tasks.md")],
                speckit_ref=f"{f.feature_dir}/tasks.md")
    us_ids = [s.item_id for k, s in stories.items() if k.startswith("US")]
    if "foundational" in stories and "setup" in stories:
        stories["foundational"].dependencies.append(Dependency(
            on_id=stories["setup"].item_id, reason="spec-kit phase order", confidence=1.0, origin="speckit_phase"))
    base = stories.get("foundational") or stories.get("setup")
    for k, s in stories.items():
        if k.startswith("US") and base:
            s.dependencies.append(Dependency(on_id=base.item_id, reason="user stories start after foundational work",
                                             confidence=1.0, origin="speckit_phase"))
    if "polish" in stories:
        for uid in us_ids:
            stories["polish"].dependencies.append(Dependency(on_id=uid, reason="polish follows all user stories",
                                                             confidence=1.0, origin="speckit_phase"))
    task_items: list[WorkItem] = []
    last_seq_in_phase: dict[int, str] = {}
    for t in tasks:
        story = stories.get(f"US{t.story_num}") if t.phase_kind == "user_story" else stories.get(t.phase_kind)
        if story is None:
            raise files.ProjectError(f"{f.feature_dir}/tasks.md: task {t.task_id} references a story not in spec.md")
        tid = f"{n}-{t.task_id}"
        deps = [Dependency(on_id=f"{n}-{d}", reason="spec-kit inline dependency", confidence=1.0,
                           origin="speckit_inline") for d in t.depends_on]
        if not deps and not t.parallel and t.phase_num in last_seq_in_phase:
            deps.append(Dependency(on_id=last_seq_in_phase[t.phase_num], reason="spec-kit sequential order",
                                   confidence=1.0, origin="speckit_inline"))
        if not t.parallel:
            last_seq_in_phase[t.phase_num] = tid
        text = strip_markup(t.text)
        task_items.append(WorkItem(
            item_id=tid, level="task", parent_id=story.item_id, title=text[:200], description_md=text,
            speckit_phase=t.phase_kind if t.phase_kind != "unknown" else None, priority=story.priority,
            moscow=story.moscow, file_paths=t.paths, parallel=t.parallel, dependencies=deps,
            components=list(f.component_ids), repo=f.repo, definition_of_done=list(settings.definition_of_done),
            skills_required=skills_taxonomy.from_text(" ".join([text, *t.paths]), limit=2),
            speckit_ref=f"{f.feature_dir}/tasks.md#{t.task_id}"))
    return items + list(stories.values()) + task_items


def build(project: str) -> str:
    with _lock:
        settings = files.read_json(project, files.PROJECT_SETTINGS, ProjectSettings)
        features = files.read_json(project, files.FEATURES, FeatureList).features
        items: list[WorkItem] = []
        for f in features:
            with perf.span("compute", "backlog.parse_feature", feature=f.feature_key) as sp:
                feature_items = _feature_items(project, f, settings)
                sp.set(items=len(feature_items))
            items += feature_items
        by = {i.item_id: i for i in items}
        enrich = _load_enrichments(project)
        # Retain split-child edits until the parent's topology has been recreated.
        def reusable(iid, e):
            item = by.get(iid)
            if item is None and iid[-1:].isalpha():
                parent = enrich.get(iid[:-1], {})
                item = by.get(iid[:-1]) if "split_into" in parent else None
                if item is None or not reusable(iid[:-1], parent):
                    return False
                return e.get("_source_sha") == _item_source(project, item)
            return item is not None and item.title == e.get("_title") and e.get("_source_sha") == _item_source(project, item)
        stale = [iid for iid, e in enrich.items() if not reusable(iid, e)]
        for item_id in stale:
            enrich.pop(item_id)
        reapplied = len(enrich)
        backlog = Backlog(backlog_id=_backlog_id(project), version=_next_version(project), project=project,
                          sources={rel: files.file_sha(project, rel) for rel in
                                   [files.PRD, files.ARCHITECTURE, files.PROJECT_SETTINGS, files.FEATURES,
                                    *(f"{f.feature_dir}/{n}" for f in features for n in ("spec.md", "tasks.md"))]
                                   if files.exists(project, rel)},
                          features=features, items=items, generated_at=files.utcnow())
        with perf.span("compute", "backlog.enrichment_replay", reapplied=reapplied, dropped=len(stale)) as sp:
            replay_errors = _apply_all(backlog, enrich, settings)
            sp.set(errors=len(replay_errors))
            if replay_errors:
                raise files.ProjectError("enrichment replay failed; previous backlog preserved: " + "; ".join(replay_errors))
        _save(project, backlog, enrich)
        perf.event("backlog_counts", "build", features=len(features), epics=sum(i.level == "epic" for i in items),
                   stories=len(backlog.stories()), tasks=sum(i.level == "task" for i in backlog.items))
    stories = backlog.stories()
    return json.dumps({
        "written": files.virtual(project, files.BACKLOG), "version": backlog.version,
        "epics": sum(i.level == "epic" for i in items), "stories": len(stories),
        "tasks": sum(i.level == "task" for i in backlog.items), "enrichments_reapplied": reapplied,
        "enrichments_dropped_changed_items": stale,
        "stories_without_estimate": [s.item_id for s in stories if not (s.estimate and s.estimate.story_points)]})


def _backlog_id(project: str) -> str:
    if files.exists(project, files.BACKLOG):
        try:
            return json.loads(files.read_text(project, files.BACKLOG))["backlog_id"]
        except (KeyError, ValueError):
            pass
    return files.new_id()


def _next_version(project: str) -> int:
    if files.exists(project, files.BACKLOG):
        try:
            return int(json.loads(files.read_text(project, files.BACKLOG)).get("version", 0)) + 1
        except ValueError:
            pass
    return 1


def _load_enrichments(project: str) -> dict:
    return files.read_json(project, ENRICHMENTS) if files.exists(project, ENRICHMENTS) else {}


def _item_source(project: str, item: WorkItem) -> str:
    feature_dir = (item.speckit_ref or "").split("#")[0].rsplit("/", 1)[0]
    paths = [files.PRD, files.ARCHITECTURE, files.PROJECT_SETTINGS, files.FEATURES]
    if feature_dir:
        paths += [f"{feature_dir}/spec.md", f"{feature_dir}/tasks.md"]
    return files.sha256_text(json.dumps({p: files.file_sha(project, p) for p in paths if files.exists(project, p)}, sort_keys=True))


def _transaction(backlog: Backlog, item_id: str, patch: dict, settings: ProjectSettings, errors: list[str]) -> bool:
    """Copy only records a patch may mutate; failed item updates leave no partial changes."""
    impacted = {item_id} | {t.item_id for t in backlog.tasks_of(item_id)}
    if "split_into" in patch:
        impacted |= {i.item_id for i in backlog.items if any(d.on_id == item_id for d in i.dependencies)}
    candidate = backlog.model_copy(update={"items": [i.model_copy(deep=True) if i.item_id in impacted else i for i in backlog.items]})
    before = len(errors)
    _apply(candidate, item_id, patch, settings, errors)
    if len(errors) != before:
        return False
    try:
        known = set(backlog.by_id())
        candidate.items = [WorkItem.model_validate(i.model_dump()) if i.item_id in impacted or i.item_id not in known
                           else i for i in candidate.items]
        backlog.items = candidate.items
    except ValueError as exc:
        errors.append(f"{item_id}: {exc}")
        return False
    return True


def _save(project: str, backlog: Backlog, enrich: dict) -> None:
    with perf.span("fs", "backlog.save") as sp:
        p1 = files.write_json(project, ENRICHMENTS, enrich)
        p2 = files.write_json(project, files.BACKLOG, backlog)
        if perf.enabled():
            sp.set(bytes=p1.stat().st_size + p2.stat().st_size, items=len(backlog.items))


# ============================================================================ update (the agent's enrichments)
def _acs(item_id: str, texts: list[str], level: str) -> list[AcceptanceCriterion]:
    out = []
    for i, t in enumerate([t for t in texts if str(t).strip()], 1):
        t = str(t).strip()
        fmt = "gherkin" if t.lower().startswith("given") else "ears"
        out.append(AcceptanceCriterion(ac_id=f"AC-{item_id}-{i}", format=fmt, text=t))
    return out


def _apply(backlog: Backlog, item_id: str, e: dict, settings: ProjectSettings, errors: list[str]) -> None:
    by = backlog.by_id()
    item = by.get(item_id)
    if item is None:
        errors.append(f"{item_id}: no such item")
        return
    unknown = set(e) - UPDATABLE - {"_title"}
    if unknown:
        errors.append(f"{item_id}: cannot update {sorted(unknown)} (allowed: {sorted(UPDATABLE)})")
        return
    try:
        for key in ("description_md", "type", "priority", "moscow", "ai_eligible", "ai_eligibility_reason", "repo"):
            if key in e:
                setattr(item, key, e[key])
        if "acceptance_criteria" in e:
            item.acceptance_criteria = _acs(item_id, e["acceptance_criteria"], item.level)
        if "user_story" in e:
            if item.level != "story":
                errors.append(f"{item_id}: user_story is for stories only")
                return
            item.user_story = UserStory(**e["user_story"])
        if "definition_of_done" in e:
            item.definition_of_done = list(dict.fromkeys([*settings.definition_of_done, *e["definition_of_done"]]))
        if "skills_required" in e:
            item.skills_required = list(e["skills_required"])
        if "open_questions" in e:
            item.open_questions = list(e["open_questions"])
        if "file_paths" in e:
            item.file_paths = list(e["file_paths"])
        if "components" in e:
            item.components = list(e["components"])
        for rid in e.get("source_ids", []):
            if not any(r.req_id == rid for r in item.source_refs):
                item.source_refs.append(SourceRef(req_id=str(rid), source="prd", anchor="agent"))
        if "remove_dependencies" in e:
            item.dependencies = [d for d in item.dependencies if d.on_id not in set(e["remove_dependencies"])]
        for d in e.get("add_dependencies", []):
            if d["on_id"] not in by:
                errors.append(f"{item_id}: dependency target {d['on_id']} does not exist")
                continue
            if not any(x.on_id == d["on_id"] for x in item.dependencies):
                item.dependencies.append(Dependency(on_id=d["on_id"], reason=d.get("reason", ""),
                                                    confidence=float(d.get("confidence", 0.8)),
                                                    origin=d.get("origin", "llm")))
        if "estimate" in e:
            est = dict(e["estimate"])
            if item.level == "story":
                pts = est.get("story_points")
                if pts not in settings.story_point_scale:
                    errors.append(f"{item_id}: story_points must be one of {settings.story_point_scale}, got {pts!r}")
                    return
                est.pop("hours", None)
            elif item.level == "task":
                if not est.get("hours") or float(est["hours"]) <= 0:
                    errors.append(f"{item_id}: a task estimate needs hours > 0")
                    return
                est.pop("story_points", None)
            item.estimate = Estimate(**est)
            if item.level == "story":
                _rollup(backlog, item, e.get("task_shares") or {}, settings)
        elif "task_shares" in e and item.level == "story" and item.estimate:
            _rollup(backlog, item, e["task_shares"], settings)
        if "split_into" in e and item.level == "task":
            _split(backlog, item, e["split_into"])
    except Exception as ex:  # a bad value for one item must not lose the others
        errors.append(f"{item_id}: {ex}")


def _rollup(backlog: Backlog, story: WorkItem, shares: dict, settings: ProjectSettings) -> None:
    """Story points -> task hours (points x hours_per_story_point, split by the agent's shares)."""
    tasks = [t for t in backlog.tasks_of(story.item_id)]
    if not tasks:
        return
    w = {t.item_id: max(0.0, float(shares.get(t.item_id, 0) or 0)) for t in tasks}
    total = sum(w.values())
    if total <= 0:
        w = {t.item_id: 2.0 if t.type in ("feature", "ui") else 1.0 for t in tasks}
        total = sum(w.values())
    hours_total = story.estimate.story_points * settings.hours_per_story_point
    for t in tasks:
        if t.estimate and t.estimate.method in ("llm", "human", "analogy"):
            continue                                   # the agent sized this task itself
        t.estimate = Estimate(hours=max(0.5, round(hours_total * w[t.item_id] / total, 1)),
                              complexity=story.estimate.complexity, confidence=story.estimate.confidence,
                              method="rollup",
                              rationale=f"share of {story.item_id} ({story.estimate.story_points} SP x "
                                        f"{settings.hours_per_story_point} h/SP)")


def _split(backlog: Backlog, task: WorkItem, parts: list[dict]) -> None:
    if len(parts) < 2 or len(parts) > 5:
        raise ValueError("split_into needs 2 to 5 parts")
    if task.item_id[-1].isalpha():
        raise ValueError("a split part cannot be split again")
    total = sum(float(p.get("hours", 0) or 0) for p in parts) or 1.0
    hours = task.estimate.hours if task.estimate and task.estimate.hours else total
    prev = None
    new_items = []
    for k, p in enumerate(parts):
        pid = f"{task.item_id}{chr(ord('a') + k)}"
        deps = list(task.dependencies) if prev is None else [Dependency(on_id=prev, reason="split sequence",
                                                                          confidence=1.0, origin="llm")]
        new_items.append(task.model_copy(deep=True, update={
            "item_id": pid, "title": str(p["title"])[:200], "description_md": p.get("description", task.description_md),
            "dependencies": deps, "acceptance_criteria": _acs(pid, p.get("acceptance_criteria", []), "task"),
            "estimate": Estimate(hours=round(hours * float(p.get("hours", 0) or 0) / total, 1) or 0.5,
                                 complexity=max(1, (task.estimate.complexity if task.estimate else 5) - 2),
                                 confidence=task.estimate.confidence if task.estimate else "low", method="rollup",
                                 rationale=f"split of {task.item_id}")}))
        prev = pid
    for other in backlog.items:            # whoever waited for the big task now waits for its last part
        for dep in other.dependencies:
            if dep.on_id == task.item_id:
                dep.on_id = prev
    idx = backlog.items.index(task)
    backlog.items[idx:idx + 1] = new_items


def _apply_all(backlog: Backlog, enrich: dict, settings: ProjectSettings) -> list[str]:
    errors: list[str] = []
    # Stories, ordinary parent tasks, split topology, then child enrichments.
    level = {i.item_id: i.level for i in backlog.items}
    rank = {"epic": 0, "story": 1, "task": 2}
    order = sorted(enrich.items(), key=lambda kv: (3 if kv[0] not in level else
                   2 if "split_into" in kv[1] else rank.get(level.get(kv[0], "task"), 2)))
    for item_id, e in order:
        _transaction(backlog, item_id, {k: v for k, v in e.items() if not k.startswith("_")}, settings, errors)
    return errors


def update(project: str, updates: list[dict]) -> str:
    """updates: [{"item_id": ..., <field>: <value>, ...}]. Fields: see UPDATABLE."""
    with _lock:
        settings = files.read_json(project, files.PROJECT_SETTINGS, ProjectSettings)
        backlog = files.read_json(project, files.BACKLOG, Backlog)
        enrich = _load_enrichments(project)
        errors: list[str] = []
        applied = []
        stories_first = sorted(updates, key=lambda u: 0 if str(u.get("item_id", "")).startswith("S-") else 1)
        for u in stories_first:
            u = dict(u)
            item_id = str(u.pop("item_id", ""))
            before = len(errors)
            item = backlog.by_id().get(item_id)
            source_sha = _item_source(project, item) if item else None
            _transaction(backlog, item_id, u, settings, errors)
            if len(errors) == before and item is not None:
                merged = {**enrich.get(item_id, {}), **u, "_title": item.title, "_source_sha": source_sha}
                enrich[item_id] = merged
                applied.append(item_id)
        _save(project, backlog, enrich)
    perf.event("backlog_counts", "update", updates=len(updates), applied=len(applied), errors=len(errors))
    return json.dumps({"applied": len(applied), "errors": errors})


# ============================================================================ estimation by analogy
def find_similar(project: str, story_ids: list[str], top: int = 8) -> str:
    backlog = files.read_json(project, files.BACKLOG, Backlog)
    settings = files.read_json(project, files.PROJECT_SETTINGS, ProjectSettings)
    history = files.read_json(project, files.HISTORY, History) if files.exists(project, files.HISTORY) else History()
    tickets = [t for t in history.tickets if t.story_points]
    by = backlog.by_id()
    stories = [by[s] for s in story_ids if s in by and by[s].level == "story"]
    if not stories:
        raise files.ProjectError("no known story ids given")
    median = (int(np.median([t.story_points for t in tickets])) if tickets
              else settings.story_point_scale[len(settings.story_point_scale) // 2])
    out = {"history_tickets": len(tickets), "team_median_points": _snap(median, settings.story_point_scale),
           "scale": settings.story_point_scale, "stories": {}}
    if not tickets:
        for s in stories:
            out["stories"][s.item_id] = {"analogy_valid": False, "references": []}
        out["note"] = "no phase4/history.json tickets: estimate with method 'llm' and confidence 'low'"
        return json.dumps(out)
    queries = [f"{s.title}\n" + "\n".join(a.text for a in s.acceptance_criteria) + "\n" +
               "\n".join(t.title for t in backlog.tasks_of(s.item_id)) for s in stories]
    with perf.span("compute", "backlog.similarity", stories=len(stories), tickets=len(tickets)):
        sims = textsim.similarities(queries, [f"{t.title}\n{t.body}" for t in tickets])
    for row, s in zip(sims, stories):
        order = list(np.argsort(-row))
        top_idx = [i for i in order[:20] if row[i] > 0]
        chosen: list[int] = []
        for value in sorted({_snap(tickets[i].story_points, settings.story_point_scale) for i in top_idx}):
            cand = next((i for i in top_idx if _snap(tickets[i].story_points, settings.story_point_scale) == value), None)
            if cand is not None:
                chosen.append(cand)            # one reference per point value: anchors across the scale
        for i in top_idx:
            if len(chosen) >= top:
                break
            if i not in chosen:
                chosen.append(i)
        best = float(row[order[0]]) if order else 0.0
        out["stories"][s.item_id] = {
            "analogy_valid": len(tickets) >= MIN_HISTORY and best >= MIN_SIMILARITY,
            "best_similarity": round(best, 3),
            "references": [{"key": tickets[i].key, "title": tickets[i].title, "story_points": tickets[i].story_points,
                            "similarity": round(float(row[i]), 3), "body": tickets[i].body[:200]} for i in chosen[:top]]}
    return json.dumps(out)


def _snap(points: float, scale: list[int]) -> int:
    return min(scale, key=lambda s: (abs(s - points), s))


# ============================================================================ validation
def _graph(items: dict[str, WorkItem], level: str) -> nx.DiGraph:
    g = nx.DiGraph()
    for i in items.values():
        if i.level == level:
            g.add_node(i.item_id)
    for i in items.values():
        if i.level == level:
            for d in i.dependencies:
                if d.on_id in g:
                    g.add_edge(d.on_id, i.item_id, confidence=d.confidence, origin=d.origin)
    return g


def story_graph(items: dict[str, WorkItem]) -> nx.DiGraph:
    """Story DAG including edges implied by task dependencies across stories."""
    g = _graph(items, "story")
    for t in items.values():
        if t.level != "task":
            continue
        for d in t.dependencies:
            other = items.get(d.on_id)
            if other and other.level == "task" and other.parent_id != t.parent_id and other.parent_id and t.parent_id:
                if not g.has_edge(other.parent_id, t.parent_id):
                    g.add_edge(other.parent_id, t.parent_id, confidence=d.confidence, origin="derived")
    return g


def _validate(backlog: Backlog, settings: ProjectSettings, prd_ids: list[str]) -> list[ValidationIssue]:
    """All rules; applies safe fixes in place (drops bad edges, breaks LLM cycles, reduces, normalizes skills)."""
    items = backlog.by_id()
    issues: list[ValidationIssue] = []

    def issue(rule: str, msg: str, ids: list[str], severity: str = "blocking") -> None:
        issues.append(ValidationIssue(rule=rule, severity=severity, item_ids=ids, message=msg))

    sec = perf.start_span("compute", "backlog.validate.hierarchy_and_targets", attrs={"items": len(items)})
    for i in items.values():
        expected = {"epic": None, "story": "epic", "task": "story"}[i.level]
        parent = items.get(i.parent_id) if i.parent_id else None
        if expected is None and i.parent_id:
            issue("hierarchy", f"epic {i.item_id} must not have a parent", [i.item_id])
        if expected and (parent is None or parent.level != expected):
            issue("hierarchy", f"{i.item_id} needs a {expected} parent", [i.item_id])
    for i in items.values():
        keep = []
        for d in i.dependencies:
            tgt = items.get(d.on_id)
            if tgt is None or tgt.level != i.level or d.on_id == i.item_id:
                issue("dependency_target", f"dropped dependency {i.item_id} -> {d.on_id} (missing or wrong level)",
                      [i.item_id], "warning")
                continue
            keep.append(d)
        i.dependencies = keep
    sec.end()
    sec = perf.start_span("compute", "backlog.validate.cycles")
    cycle_iterations = 0
    for level in ("story", "task"):
        for _ in range(50):
            cycle_iterations += 1
            g = _graph(items, level)
            try:
                cycle = nx.find_cycle(g)
            except nx.NetworkXNoCycle:
                break
            llm_edges = [(u, v) for u, v in cycle if g.edges[u, v]["origin"] == "llm"]
            if not llm_edges:
                issue("dependency_cycle", f"cycle among spec-kit/human dependencies: {cycle}", [u for u, _ in cycle])
                break
            u, v = min(llm_edges, key=lambda e: g.edges[e]["confidence"])
            items[v].dependencies = [d for d in items[v].dependencies if d.on_id != u]
            issue("dependency_cycle", f"removed low-confidence edge {v} -> {u} to break a cycle", [v], "warning")
    sec.end(iterations=cycle_iterations)
    sec = perf.start_span("compute", "backlog.validate.transitive_reduction")
    g = _graph(items, "story")
    if nx.is_directed_acyclic_graph(g):
        red = nx.transitive_reduction(g)
        for s in [i for i in items.values() if i.level == "story"]:
            s.dependencies = [d for d in s.dependencies if red.has_edge(d.on_id, s.item_id)]
    sec.end(story_edges=g.number_of_edges())
    sec = perf.start_span("compute", "backlog.validate.rules", attrs={"prd_ids": len(prd_ids)})
    coverage: dict[str, list[str]] = {r: [] for r in prd_ids}
    for s in items.values():
        if s.level != "story":
            continue
        for ref in s.source_refs:
            if ref.req_id in coverage and s.item_id not in coverage[ref.req_id]:
                coverage[ref.req_id].append(s.item_id)
    uncovered = [r for r, ids in coverage.items() if not ids and r.startswith(COVERAGE_PREFIXES)]
    if uncovered:
        issue("coverage", f"prd.md requirements without a story: {', '.join(uncovered)}", uncovered)
    for s in items.values():
        if s.level == "story" and s.speckit_phase == "user_story" and not s.source_refs:
            issue("coverage", f"story {s.item_id} has no source requirement", [s.item_id])
    no_ac_s = [i.item_id for i in items.values() if i.level == "story" and not i.acceptance_criteria]
    if no_ac_s:
        issue("acceptance_criteria", f"{len(no_ac_s)} stories without acceptance criteria", no_ac_s)
    generic = [s.item_id for s in items.values() if s.level == "story" and s.user_story
               and s.user_story.as_a == "user" and s.user_story.so_that == PLACEHOLDER_BENEFIT]
    if generic:
        issue("user_story", f"{len(generic)} stories have a placeholder statement; set user_story with the real role "
              f"and benefit: {', '.join(generic[:20])}", generic)
    no_ac_t = [i.item_id for i in items.values() if i.level == "task" and not i.acceptance_criteria]
    if no_ac_t:
        issue("acceptance_criteria", f"{len(no_ac_t)} tasks without acceptance criteria (they cannot go to an AI "
              "agent and are harder to review)", no_ac_t, "warning")
    for t in items.values():
        if t.level == "task":
            missing = [d for d in settings.definition_of_done if d not in t.definition_of_done]
            if missing:
                t.definition_of_done = missing + t.definition_of_done
    bad_hours = [t.item_id for t in items.values() if t.level == "task" and not (t.estimate and (t.estimate.hours or 0) > 0)]
    bad_points = [s.item_id for s in items.values() if s.level == "story" and not (
        s.estimate and s.estimate.story_points in settings.story_point_scale)]
    if bad_hours or bad_points:
        issue("estimates", f"unestimated items: {', '.join((bad_points + bad_hours)[:20])}", bad_points + bad_hours)
    too_big = [s.item_id for s in items.values() if s.level == "story" and s.estimate and s.estimate.story_points
               and s.estimate.story_points > settings.max_story_points_per_story and s.moscow != "wont"]
    if too_big:
        issue("story_size", f"stories above the {settings.max_story_points_per_story} SP limit; split them along their "
              f"acceptance scenarios: {', '.join(too_big)}", too_big)
    big_tasks = [t.item_id for t in items.values() if t.level == "task" and t.estimate and (t.estimate.hours or 0) > SPLIT_HOURS]
    if big_tasks:
        issue("task_size", f"tasks above {SPLIT_HOURS:.0f} h; split them (split_into): {', '.join(big_tasks[:20])}",
              big_tasks, "warning")
    tax = set(skills_taxonomy.tags())
    for t in items.values():
        if t.level == "task":
            fixed = []
            for s in t.skills_required:
                n = s if s in tax else skills_taxonomy.normalize(s)
                if n:
                    fixed.append(n)
                else:
                    issue("skills", f"dropped unknown skill '{s}' on {t.item_id}", [t.item_id], "warning")
            t.skills_required = list(dict.fromkeys(fixed))
    no_skill = [t.item_id for t in items.values() if t.level == "task" and not t.skills_required]
    if no_skill:
        issue("skills", f"{len(no_skill)} tasks without a skill tag", no_skill, "warning")
    sec.end()
    tasks = [t for t in items.values() if t.level == "task"]
    sec = perf.start_span("compute", "backlog.validate.duplicates",
                          attrs={"tasks": len(tasks), "skipped_input_size_limit": len(tasks) > 1500,
                                 "skipped_too_few": len(tasks) <= 1, "pairs": len(tasks) * (len(tasks) - 1) // 2})
    if 1 < len(tasks) <= 1500:
        m = textsim.tfidf_matrix([f"{t.title}\n{t.description_md}" for t in tasks])
        sim = m @ m.T
        for a in range(len(tasks)):
            for b in range(a + 1, len(tasks)):
                if tasks[a].parent_id != tasks[b].parent_id and sim[a, b] >= DUPLICATE_THRESHOLD:
                    issue("duplicates", f"possible duplicates {tasks[a].item_id} / {tasks[b].item_id}",
                          [tasks[a].item_id, tasks[b].item_id], "warning")
    elif len(tasks) > 1500:
        issue("duplicate_scan_incomplete", "Duplicate similarity scanning was not run above 1500 tasks; review duplicate coverage separately.", [], "warning")
    sec.end()
    sec = perf.start_span("compute", "backlog.validate.waves_and_critical_path")
    questions = [i.item_id for i in items.values() if i.open_questions]
    if questions:
        issue("open_questions", f"{len(questions)} items have open questions for the reviewer", questions, "warning")
    sg = story_graph(items)
    backlog.coverage = coverage
    backlog.story_waves, backlog.critical_path = [], []
    if nx.is_directed_acyclic_graph(sg):
        backlog.story_waves = [sorted(gen) for gen in nx.topological_generations(sg)]
        for n in sg.nodes:
            sg.nodes[n]["w"] = (items[n].estimate.story_points if items[n].estimate and items[n].estimate.story_points else 1)
        for u, v in sg.edges:
            sg.edges[u, v]["w"] = sg.nodes[v]["w"]
        # Dynamic programming over node weights includes the first story's effort.
        lengths, paths = {}, {}
        for n in nx.topological_sort(sg):
            pred = max(sg.predecessors(n), key=lambda p: lengths[p], default=None)
            lengths[n] = sg.nodes[n]["w"] + (lengths[pred] if pred is not None else 0)
            paths[n] = (paths[pred] if pred is not None else []) + [n]
        backlog.critical_path = paths[max(lengths, key=lengths.get)] if lengths else []
    else:
        issue("dependency_cycle", "story graph (with task-derived edges) has a cycle", [])
    sec.end(critical_path=len(backlog.critical_path), waves=len(backlog.story_waves))
    return issues


def validate(project: str, *, write: bool = True) -> tuple[Backlog, list[ValidationIssue]]:
    with _lock:
        settings = files.read_json(project, files.PROJECT_SETTINGS, ProjectSettings)
        backlog = files.read_json(project, files.BACKLOG, Backlog)
        original = {i.item_id: i.model_dump() for i in backlog.items} if not write else None
        issues = _validate(backlog, settings, _prd_ids(project))
        if original is not None:
            changed = [i.item_id for i in backlog.items if original[i.item_id] != i.model_dump()]
            if changed:
                issues.append(ValidationIssue(rule="repair_required", severity="blocking", item_ids=changed,
                                              message="saved backlog needs repair; run backlog_validate before review"))
        backlog.issues = issues
        perf.event("backlog_counts", "validate", blocking=sum(i.severity == "blocking" for i in issues),
                   warnings=sum(i.severity == "warning" for i in issues), stories=len(backlog.stories()),
                   tasks=sum(i.level == "task" for i in backlog.items), write=write)
        if write:
            with perf.span("fs", "backlog.write_validated") as sp:
                files.write_json(project, files.BACKLOG, backlog)
                with perf.span("compute", "backlog.render_md"):
                    md = render_md(backlog)
                files.write_text(project, files.BACKLOG_MD, md)
                sp.set(md_chars=len(md))
    return backlog, issues


def validate_report(project: str, *, write: bool = True) -> str:
    backlog, issues = validate(project, write=write)
    blocking = [i for i in issues if i.severity == "blocking"]
    return json.dumps({
        "ready_for_review": not blocking, "blocking": [i.model_dump() for i in blocking],
        "warnings": [i.model_dump() for i in issues if i.severity == "warning"][:40],
        "stories": len(backlog.stories()), "tasks": sum(i.level == "task" for i in backlog.items),
        "story_points": sum((s.estimate.story_points or 0) for s in backlog.stories() if s.estimate),
        "written": [files.virtual(project, files.BACKLOG), files.virtual(project, files.BACKLOG_MD)] if write else []})


# ============================================================================ backlog.md
def render_md(b: Backlog) -> str:
    by = b.by_id()
    blocking = [i for i in b.issues if i.severity == "blocking"]
    pts = sum((s.estimate.story_points or 0) for s in b.stories() if s.estimate)
    lines = [f"# Backlog v{b.version} — {b.project}", "",
             f"{sum(i.level == 'epic' for i in b.items)} epics · {len(b.stories())} stories · "
             f"{sum(i.level == 'task' for i in b.items)} tasks · {pts} story points · "
             f"{len(blocking)} blocking issues", ""]
    if b.issues:
        lines += ["## Issues", ""] + [f"- **{i.severity}** `{i.rule}`: {i.message}" for i in b.issues[:60]] + [""]
    lines += ["## Coverage of prd.md", ""]
    lines += [f"- {r}: {', '.join(ids) or '**not covered**'}" for r, ids in b.coverage.items()] or ["- (no ids in prd.md)"]
    lines += ["", f"Critical path: {' → '.join(b.critical_path) or '-'}", ""]
    for e in [i for i in b.items if i.level == "epic"]:
        lines += [f"## {e.item_id} {e.title}", "", e.description_md, ""]
        for s in [i for i in b.items if i.level == "story" and i.parent_id == e.item_id]:
            est = f"{s.estimate.story_points} SP ({s.estimate.confidence}, {s.estimate.method})" if s.estimate else "unestimated"
            deps = ", ".join(d.on_id for d in s.dependencies) or "-"
            lines += [f"### {s.item_id} {s.title} — {s.priority}/{s.moscow} · {est}", ""]
            if s.user_story:
                lines.append(f"As a {s.user_story.as_a}, I want {s.user_story.i_want} so that {s.user_story.so_that}.")
            lines += [f"Depends on: {deps} · Sources: {', '.join(r.req_id for r in s.source_refs) or '-'}", ""]
            lines += [f"- [{a.ac_id}] {a.text}" for a in s.acceptance_criteria] + [""]
            lines += ["| Task | Title | Hours | Skills | AI | Depends on |", "|---|---|---|---|---|---|"]
            for t in b.tasks_of(s.item_id):
                h = t.estimate.hours if t.estimate and t.estimate.hours else "-"
                lines.append(f"| {t.item_id} | {t.title[:80].replace('|', '/')} | {h} | {', '.join(t.skills_required)} | "
                             f"{'yes' if t.ai_eligible else 'no'} | {', '.join(d.on_id for d in t.dependencies) or '-'} |")
            lines.append("")
    questions = [(i.item_id, q) for i in by.values() for q in i.open_questions]
    if questions:
        lines += ["## Open questions", ""] + [f"- {iid}: {q}" for iid, q in questions] + [""]
    return "\n".join(lines)
