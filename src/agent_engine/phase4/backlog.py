"""Task Breakdown's deterministic checks: backlog/backlog.json -> issues, safe fixes and backlog/backlog.md.

The backlog is built from the approved stories by task_breakdown.py. The rules here are exact and need no model:
hierarchy, dependency targets and cycles (low-confidence model edges are dropped to break a cycle), every approved
story present with tasks that cover all its acceptance criteria, disciplines, estimates on the scale, task size,
skills from the taxonomy, effort against the points set upstream, vague task criteria, duplicates, stale inputs.
It also computes requirement coverage, story waves and the critical path that Sprint Planning reads.
"""

from __future__ import annotations

import json
import re
import threading

import networkx as nx

from agent_engine import perf
from agent_engine.phase4 import files, skills_taxonomy, textsim
from agent_engine.phase4.contracts import Backlog, ProjectSettings, ValidationIssue, WorkItem

REQ_ID_RE = re.compile(r"\b((?:FR|NFR|US|DS|ARCH)-\d{1,4})\b")
DUPLICATE_THRESHOLD = 0.92
COVERAGE_PREFIXES = ("FR-", "NFR-", "US-", "DS-")
MIN_HISTORY = 10
MIN_SIMILARITY = 0.2
SPLIT_HOURS = 16.0
VAGUE_RE = re.compile(r"\b(fast|quick(ly)?|easy|easily|user[- ]friendly|intuitive|appropriate(ly)?|properly|"
                      r"efficient(ly)?|robust|seamless(ly)?|smooth(ly)?|as needed|reasonabl[ey]|etc\.?|and so on)\b", re.I)
_BREAKDOWN_SETTINGS = frozenset({"project_name", "code_repos", "infra_repo", "definition_of_done",
                                 "story_point_scale", "hours_per_story_point", "max_story_points_per_story", "deadlines"})
_lock = threading.RLock()


def source_settings(settings: ProjectSettings) -> dict:
    """The project settings Task Breakdown depends on (other settings changing does not make the backlog stale)."""
    return settings.model_dump(mode="json", include=_BREAKDOWN_SETTINGS)


def _prd_ids(project: str) -> list[str]:
    if not files.exists(project, files.PRD):
        return []
    return list(dict.fromkeys(REQ_ID_RE.findall(files.read_text(project, files.PRD))))


def _snap(points: float, scale: list[int]) -> int:
    return min(scale, key=lambda s: (abs(s - points), s))


# ============================================================================ graphs
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


# ============================================================================ rules
def _validate(backlog: Backlog, settings: ProjectSettings, stories: list) -> list[ValidationIssue]:
    """All rules over the backlog and the approved stories; applies safe fixes in place."""
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
    for level in ("story", "task"):
        for _ in range(50):
            g = _graph(items, level)
            try:
                cycle = nx.find_cycle(g)
            except nx.NetworkXNoCycle:
                break
            llm_edges = [(u, v) for u, v in cycle if g.edges[u, v]["origin"] == "llm"]
            if not llm_edges:
                issue("dependency_cycle", f"cycle among tracker/human dependencies: {cycle}", [u for u, _ in cycle])
                break
            u, v = min(llm_edges, key=lambda e: g.edges[e]["confidence"])
            items[v].dependencies = [d for d in items[v].dependencies if d.on_id != u]
            issue("dependency_cycle", f"removed low-confidence edge {v} -> {u} to break a cycle", [v], "warning")
        if not nx.is_directed_acyclic_graph(_graph(items, level)):
            issue("dependency_cycle", f"{level} dependencies still contain a cycle after bounded repair", [])
    g = _graph(items, "story")
    if nx.is_directed_acyclic_graph(g):
        red = nx.transitive_reduction(g)
        for s in [i for i in items.values() if i.level == "story"]:
            s.dependencies = [d for d in s.dependencies if red.has_edge(d.on_id, s.item_id)]
    sec.end()

    sec = perf.start_span("compute", "backlog.validate.rules")
    coverage: dict[str, list[str]] = {}
    for s in items.values():
        if s.level == "story":
            for ref in s.source_refs:
                if s.item_id not in coverage.setdefault(ref.req_id, []):
                    coverage[ref.req_id].append(s.item_id)
    missing = [s.key for s in stories if s.key not in items or items[s.key].level != "story"]
    if missing:
        issue("missing_story", f"approved stories missing from the backlog: {', '.join(missing)}", missing)
    without = [s.item_id for s in items.values() if s.level == "story" and not backlog.tasks_of(s.item_id)]
    if without:
        issue("story_tasks", f"stories without tasks: {', '.join(without)}", without)
    no_disc = [t.item_id for t in items.values() if t.level == "task" and not t.discipline]
    if no_disc:
        issue("discipline", f"{len(no_disc)} tasks have no discipline (FE/BE/DB/DevOps/QA)", no_disc)
    for s in stories:
        if s.key not in items:
            continue
        covered = {r.req_id for t in items.values() if t.level == "task"
                   for r in t.source_refs if t.parent_id == s.key or r.anchor == s.key}   # shared work counts
        gaps = [c.ac_id for c in s.acceptance_criteria if c.ac_id not in covered]
        if gaps:
            issue("acceptance_coverage", f"{s.key}: no task covers {', '.join(gaps)}", [s.key])
        if not s.acceptance_criteria:
            issue("acceptance_criteria", f"{s.key}: the approved story has no acceptance criteria; ask the product owner",
                  [s.key], "warning")
    no_ac_t = [i.item_id for i in items.values() if i.level == "task" and not i.acceptance_criteria]
    if no_ac_t:
        issue("acceptance_criteria", f"{len(no_ac_t)} tasks without acceptance criteria", no_ac_t)
    vague = [t.item_id for t in items.values() if t.level == "task"
             and any(VAGUE_RE.search(a.text) and not re.search(r"\d", a.text) for a in t.acceptance_criteria)]
    if vague:
        issue("vague_criteria", f"{len(vague)} tasks have acceptance criteria without a measure "
              f"(e.g. 'fast', 'user-friendly'): {', '.join(vague[:20])}", vague, "warning")
    for t in items.values():
        if t.level == "task":
            absent = [d for d in settings.definition_of_done if d not in t.definition_of_done]
            if absent:
                t.definition_of_done = absent + t.definition_of_done
    bad_hours = [t.item_id for t in items.values() if t.level == "task" and not (t.estimate and (t.estimate.hours or 0) > 0)]
    bad_points = [s.item_id for s in items.values() if s.level == "story" and not (
        s.estimate and s.estimate.story_points in settings.story_point_scale)]
    if bad_hours or bad_points:
        issue("estimates", f"unestimated items: {', '.join((bad_points + bad_hours)[:20])}", bad_points + bad_hours)
    for story in (i for i in items.values() if i.level == "story" and i.estimate and i.estimate.story_points):
        tasks = backlog.tasks_of(story.item_id)
        if not tasks or any(not t.estimate or t.estimate.hours is None for t in tasks):
            continue
        if story.estimate.method in ("rollup", "analogy"):
            continue  # points were derived from these hours; snapping to the scale is not a disagreement
        actual = sum(t.estimate.hours for t in tasks)
        implied = _snap(actual / settings.hours_per_story_point, settings.story_point_scale)
        if implied != story.estimate.story_points:
            issue("effort_total", f"{story.item_id}: tasks total {actual:g} h (about {implied} SP) but the story has "
                  f"{story.estimate.story_points} SP from upstream; the Tech Lead decides whether the points or the "
                  "tasks change", [story.item_id], "warning")
    too_big = [s.item_id for s in items.values() if s.level == "story" and s.estimate and s.estimate.story_points
               and s.estimate.story_points > settings.max_story_points_per_story and s.moscow != "wont"]
    if too_big:
        issue("story_size", f"approved stories above the {settings.max_story_points_per_story} SP limit; raise a split "
              f"with the product owner: {', '.join(too_big)}", too_big, "warning")
    big_tasks = [t.item_id for t in items.values() if t.level == "task" and t.estimate and (t.estimate.hours or 0) > SPLIT_HOURS]
    if big_tasks:
        issue("task_size", f"tasks above {SPLIT_HOURS:.0f} h; split them: {', '.join(big_tasks[:20])}", big_tasks)
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
        issue("skills", f"{len(no_skill)} tasks without a skill tag", no_skill)
    sec.end()

    tasks = [t for t in items.values() if t.level == "task"]
    sec = perf.start_span("compute", "backlog.validate.duplicates", attrs={"tasks": len(tasks)})
    if 1 < len(tasks) <= 1500:
        m = textsim.tfidf_matrix([f"{t.title}\n{t.description_md}" for t in tasks])
        sim = m @ m.T
        for a in range(len(tasks)):
            for b in range(a + 1, len(tasks)):
                if tasks[a].parent_id != tasks[b].parent_id and sim[a, b] >= DUPLICATE_THRESHOLD:
                    issue("duplicates", f"possible duplicates {tasks[a].item_id} / {tasks[b].item_id}",
                          [tasks[a].item_id, tasks[b].item_id], "warning")
    elif len(tasks) > 1500:
        issue("duplicate_scan_incomplete", "Duplicate similarity scanning was not run above 1500 tasks; review "
              "duplicate coverage separately.", [], "warning")
    sec.end()

    sec = perf.start_span("compute", "backlog.validate.waves_and_critical_path")
    for _ in range(50):     # loops through task links across stories: drop the weakest model-proposed link
        try:
            cycle = nx.find_cycle(story_graph(items))
        except nx.NetworkXNoCycle:
            break
        pairs = set(cycle)
        links = [(d.confidence, t.item_id, d.on_id) for t in items.values() if t.level == "task" for d in t.dependencies
                 if d.origin == "llm" and d.on_id in items and items[d.on_id].level == "task"
                 and (items[d.on_id].parent_id, t.parent_id) in pairs]
        if not links:
            break
        _, task_id, on_id = min(links)
        items[task_id].dependencies = [d for d in items[task_id].dependencies if d.on_id != on_id]
        issue("dependency_cycle", f"removed low-confidence link {task_id} -> {on_id}: it made stories wait for each "
              f"other ({' -> '.join(u for u, _ in cycle)})", [task_id], "warning")
    questions = [i.item_id for i in items.values() if i.open_questions]
    if questions:
        issue("open_questions", f"{len(questions)} items have open questions for the reviewer", questions, "warning")
    sg = story_graph(items)
    backlog.coverage = coverage
    backlog.story_waves, backlog.critical_path = [], []
    if nx.is_directed_acyclic_graph(sg):
        backlog.story_waves = [sorted(gen) for gen in nx.topological_generations(sg)]
        weight = {n: (items[n].estimate.story_points if items[n].estimate and items[n].estimate.story_points else 1)
                  for n in sg.nodes}
        lengths, paths = {}, {}
        for n in nx.topological_sort(sg):     # longest path by story points, counting the first story's effort
            pred = max(sg.predecessors(n), key=lambda p: lengths[p], default=None)
            lengths[n] = weight[n] + (lengths[pred] if pred is not None else 0)
            paths[n] = (paths[pred] if pred is not None else []) + [n]
        backlog.critical_path = paths[max(lengths, key=lengths.get)] if lengths else []
    else:
        stuck = [u for u, _ in nx.find_cycle(sg)]
        issue("dependency_cycle", "stories wait for each other through tracker or human links: " + " -> ".join(stuck)
              + "; a human must fix the order", stuck)
    sec.end(critical_path=len(backlog.critical_path), waves=len(backlog.story_waves))
    return issues


def validate(project: str, *, write: bool = True) -> tuple[Backlog, list[ValidationIssue]]:
    with _lock:
        settings = files.read_json(project, files.PROJECT_SETTINGS, ProjectSettings)
        backlog = files.read_json(project, files.BACKLOG, Backlog)
        original = {i.item_id: i.model_dump() for i in backlog.items} if not write else None
        if files.STORIES not in backlog.sources:
            issues = [ValidationIssue(rule="legacy_backlog", severity="blocking", item_ids=[],
                                      message="this backlog was built by the retired spec-kit workflow; run Task "
                                      "Breakdown again from the approved stories (phase4/stories.json)")]
            backlog.issues = issues
            return backlog, issues
        from agent_engine.phase4.contracts import StorySnapshot
        from agent_engine.phase4.task_breakdown import source_manifest
        stories = files.read_json(project, files.STORIES, StorySnapshot).stories
        issues = _validate(backlog, settings, stories)
        traced = set(backlog.coverage)
        untraced = [r for r in _prd_ids(project) if r.startswith(COVERAGE_PREFIXES) and r not in traced]
        if untraced:
            issues.append(ValidationIssue(rule="prd_trace", severity="warning", item_ids=untraced,
                                          message="prd.md ids no imported story traces (done, not yet approved, or "
                                          "missing in the tracker): " + ", ".join(untraced[:30])))
        current_sources = source_manifest(project, settings)
        stale = sorted(rel for rel in set(current_sources) | set(backlog.sources)
                       if current_sources.get(rel) != backlog.sources.get(rel))
        if stale:
            issues.append(ValidationIssue(rule="stale_sources", severity="blocking", item_ids=[],
                                          message="backlog inputs changed; run Task Breakdown again: " + ", ".join(stale)))
        if original is not None:
            changed = [i.item_id for i in backlog.items if original[i.item_id] != i.model_dump()]
            if changed:
                issues.append(ValidationIssue(rule="repair_required", severity="blocking", item_ids=changed,
                                              message="the saved backlog was not validated; run Task Breakdown again"))
        backlog.issues = issues
        perf.event("backlog_counts", "validate", blocking=sum(i.severity == "blocking" for i in issues),
                   warnings=sum(i.severity == "warning" for i in issues), stories=len(backlog.stories()),
                   tasks=sum(i.level == "task" for i in backlog.items), write=write)
        if write:
            with perf.span("fs", "backlog.write_validated") as sp:
                files.write_json(project, files.BACKLOG, backlog)
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
    lines += ["## Requirements traced by the approved stories", ""]
    lines += [f"- {r}: {', '.join(ids)}" for r, ids in b.coverage.items()] or ["- (no requirement ids on the stories)"]
    lines += ["", f"Critical path: {' → '.join(b.critical_path) or '-'}", ""]
    if b.releases:
        lines += ["Roadmap: " + " → ".join(f"{r.name}" + (f" ({r.release_date})" if r.release_date else "")
                                         for r in sorted(b.releases, key=lambda r: r.order)), ""]
    for e in [i for i in b.items if i.level == "epic"]:
        lines += [f"## {e.item_id} {e.title}", "", e.description_md, ""]
        for s in [i for i in b.items if i.level == "story" and i.parent_id == e.item_id]:
            est = f"{s.estimate.story_points} SP ({s.estimate.confidence}, {s.estimate.method})" if s.estimate else "unestimated"
            deps = ", ".join(d.on_id for d in s.dependencies) or "-"
            release = f" · release {s.release}" if s.release else ""
            lines += [f"### {s.item_id} {s.title} — {s.priority}/{s.moscow}{release} · {est}", ""]
            if s.description_md:
                lines += [s.description_md, ""]
            lines += [f"Depends on: {deps} · Sources: {', '.join(r.req_id for r in s.source_refs) or '-'}", ""]
            lines += [f"- [{a.ac_id}] {a.text}" for a in s.acceptance_criteria] + [""]
            lines += ["| Task | Discipline | Title | Hours | Skills | Covers | Depends on |", "|---|---|---|---|---|---|---|"]
            for t in b.tasks_of(s.item_id):
                h = t.estimate.hours if t.estimate and t.estimate.hours else "-"
                lines.append(f"| {t.item_id} | {t.discipline or '-'} | {t.title[:80].replace('|', '/')} | {h} | "
                             f"{', '.join(t.skills_required)} | {', '.join(r.req_id for r in t.source_refs) or '-'} | "
                             f"{', '.join(d.on_id for d in t.dependencies) or '-'} |")
            lines.append("")
    questions = [(i.item_id, q) for i in by.values() for q in i.open_questions]
    if questions:
        lines += ["## Open questions", ""] + [f"- {iid}: {q}" for iid, q in questions] + [""]
    return "\n".join(lines)
