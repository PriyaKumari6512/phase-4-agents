"""Agent 2 (Sprint Planning): the deterministic parts around the agent's judgement.

  capacity   sprint windows, availability (holidays, PTO, calendars), Monte Carlo P50/P85 -> sprint/capacity.json
  solve      the agent's business values (1..10 per story) -> WSJF -> CP-SAT packing with dependencies, deadlines,
             must-haves, pins, churn penalty; verified options when infeasible -> sprint/sprint-plan.json
  annotate   the agent's sprint goals and deferral explanations -> sprint/sprint-plan.json + sprint-plan.md
  check      read-only consistency check for the validator
"""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta

import networkx as nx

from agent_engine import perf
from agent_engine.phase4 import capacity as cap
from agent_engine.phase4 import files
from agent_engine.phase4.backlog import story_graph
from agent_engine.phase4.contracts import (
    Backlog,
    Deferral,
    Forecast,
    History,
    PlanOption,
    ProjectSettings,
    SolverReport,
    SprintPlan,
    SprintSlot,
)
from agent_engine.phase4.sprint_model import DeadlineIn, SprintIn, StoryIn, solve as cpsat_solve, verified_options

RELAX_KINDS = ("relax", "soften", "downgrade", "unpin", "capacity")
log = logging.getLogger(__name__)


def _load(project: str):
    with perf.span("phase", "sprint.load_inputs") as sp:
        settings = files.read_json(project, files.PROJECT_SETTINGS, ProjectSettings)
        backlog = files.read_json(project, files.BACKLOG, Backlog)
        history = files.read_json(project, files.HISTORY, History) if files.exists(project, files.HISTORY) else History()
        prev = files.read_json(project, files.SPRINT_PLAN, SprintPlan) if files.exists(project, files.SPRINT_PLAN) else None
        sp.set(stories=len(backlog.stories()), items=len(backlog.items), history_sprints=len(history.sprints),
               previous_plan=prev is not None)
    return settings, backlog, history, prev


def _as_of(as_of: str | None) -> date:
    return date.fromisoformat(as_of) if as_of else cap.utc_today()


def _windows(settings: ProjectSettings, history: History, as_of: date):
    with perf.span("phase", "sprint.windows_and_capacity", horizon=settings.calendar.planning_horizon_sprints) as sp:
        windows = cap.sprint_windows(settings, as_of)
        cap.fill_availability(settings, windows)
        hist = [h.model_dump() for h in history.sprints]
        assumptions = cap.fill_capacity(settings, windows, hist)
        sp.set(sprints=len(windows), capacity_p50=[w.cap_p50 for w in windows])
    return windows, hist, assumptions


def _prechecks(backlog: Backlog, settings: ProjectSettings, windows) -> tuple[list[str], list[str]]:
    max_cap = max((w.cap_p50 for w in windows), default=0)
    unest = [s.item_id for s in backlog.stories() if not (s.estimate and s.estimate.story_points) and s.moscow != "wont"]
    too_big = [s.item_id for s in backlog.stories() if s.estimate and s.estimate.story_points and s.moscow != "wont"
               and (s.estimate.story_points > settings.max_story_points_per_story or s.estimate.story_points > max_cap)]
    return unest, too_big


def capacity_report(project: str, as_of: str | None = None) -> str:
    settings, backlog, history, _ = _load(project)
    windows, _, assumptions = _windows(settings, history, _as_of(as_of))
    unest, too_big = _prechecks(backlog, settings, windows)
    data = {"as_of": str(_as_of(as_of)), "assumptions": assumptions,
            "sprints": [{"sprint_index": w.index, "number": w.number, "start": str(w.start), "end": str(w.end),
                         "active": w.active, "person_days": w.person_days, "person_hours": w.person_hours,
                         "capacity_p50": w.cap_p50, "capacity_p85": w.cap_p85, "maintenance_reserved": w.reserved,
                         "hours_by_member": w.hours_by_member} for w in windows],
            "backlog_points": sum((s.estimate.story_points or 0) for s in backlog.stories() if s.estimate),
            "unestimated_stories": unest, "too_large_stories": too_big}
    files.write_json(project, files.CAPACITY, data)
    return json.dumps({**{k: v for k, v in data.items() if k != "sprints"},
                       "sprints": [{k: s[k] for k in ("sprint_index", "number", "start", "end", "person_days",
                                                      "capacity_p50", "capacity_p85")} for s in data["sprints"]],
                       "written": files.virtual(project, files.CAPACITY)})


def wsjf(backlog: Backlog, business: dict[str, int], deadline_limit: dict[str, int], graph: nx.DiGraph) -> dict[str, float]:
    """WSJF = cost of delay (business value + time criticality + enablement) / size, normalized to 0..100."""
    crit = set(backlog.critical_path)
    raw = {}
    for s in backlog.stories():
        pts = (s.estimate.story_points if s.estimate and s.estimate.story_points else 1)
        lim = deadline_limit.get(s.item_id)
        time_crit = 10 - min(9, lim) if lim is not None else 1
        enable = min(10, len(nx.descendants(graph, s.item_id)) if s.item_id in graph else 0) + (3 if s.item_id in crit else 0)
        raw[s.item_id] = (business.get(s.item_id, 5) + time_crit + enable) / max(1, pts)
    top = max(raw.values(), default=1) or 1
    return {k: round(100 * v / top, 2) for k, v in raw.items()}


def _apply_relax(changes: list[str], stories: list[StoryIn], sprints: list[SprintIn], deadlines: list[DeadlineIn],
                 assumptions: list[str]) -> None:
    for change in changes:
        kind, _, rest = change.partition(":")
        if kind not in RELAX_KINDS:
            raise files.ProjectError(f"unknown relaxation {change!r}; use an option's 'changes' strings")
        if kind == "relax" and rest.startswith("deadline:"):
            _, ref_id, shift = rest.split(":")
            for d in deadlines:
                if d.ref_id == ref_id:
                    d.last_sprint += int(shift.lstrip("+"))
        elif kind == "soften" and rest.startswith("deadline:"):
            for d in deadlines:
                if d.ref_id == rest.split(":")[1]:
                    d.hard = False
        elif kind == "downgrade":
            for s in stories:
                if s.story_id == rest.split(":", 1)[1]:
                    s.must = False
        elif kind == "unpin":
            for s in stories:
                if s.story_id == rest.split("->")[0]:
                    s.pinned_sprint = None
        elif kind == "capacity":
            f = float(rest.lstrip("x"))
            for sp in sprints:
                sp.cap_p50 *= f
                sp.cap_p85 *= f
            assumptions.append(f"Capacity scaled x{f} by the approver's choice.")


def solve(project: str, business_values: dict[str, int], pins: dict[str, int] | None = None,
          relax: list[str] | None = None, as_of: str | None = None, time_limit_s: float = 10.0) -> str:
    settings, backlog, history, prev = _load(project)
    as_of_d = _as_of(as_of)
    windows, hist, assumptions = _windows(settings, history, as_of_d)
    unest, too_big = _prechecks(backlog, settings, windows)
    pins = {k: int(v) for k, v in (pins or {}).items()}
    relax = list(relax or [])
    by = backlog.by_id()
    unknown = [s for s in [*business_values, *pins] if s not in by or by[s].level != "story"]
    if unknown:
        raise files.ProjectError(f"unknown story ids: {', '.join(sorted(set(unknown)))}")
    bad = {k: v for k, v in business_values.items() if not (isinstance(v, int) and 1 <= v <= 10)}
    if bad:
        raise files.ProjectError(f"business values must be integers 1..10: {bad}")
    business = {**(prev.business_values if prev else {}), **business_values}
    defaulted = [s.item_id for s in backlog.stories() if s.item_id not in business]
    for sid in defaulted:
        business[sid] = 5

    # previous plan: churn penalty and the frozen active sprint (by absolute sprint number)
    first = windows[0].number
    prev_place: dict[str, int] = {}
    if prev:
        for sp in prev.sprints:
            for sid in sp.story_ids:
                prev_place[sid] = sp.number - first + 1
    graph = story_graph(by)
    deadline_limit: dict[str, int] = {}
    deadlines = []
    for d in settings.deadlines:
        last = 0
        for w in windows:
            if w.end <= d.due_date:
                last = w.index
        sids = sorted({sid for rid in d.requirement_ids for sid in backlog.coverage.get(rid, [])})
        deadlines.append(DeadlineIn(ref_id=d.ref_id, story_ids=sids, last_sprint=last, hard=d.hard))
        for sid in sids:
            deadline_limit[sid] = min(deadline_limit.get(sid, 99), last)
    values = wsjf(backlog, business, deadline_limit, graph)
    excluded = set(unest) | set(too_big)
    stories = []
    for s in backlog.stories():
        skill_hours: dict[str, float] = {}
        for t in backlog.tasks_of(s.item_id):
            for sk in t.skills_required[:1]:
                skill_hours[sk] = skill_hours.get(sk, 0) + (t.estimate.hours if t.estimate and t.estimate.hours else 0)
        frozen = 1 if windows[0].active and prev_place.get(s.item_id) == 1 else None
        stories.append(StoryIn(
            story_id=s.item_id, points=float(s.estimate.story_points or 0) if s.estimate else 0.0,
            value=values.get(s.item_id, 1), depends_on=[d.on_id for d in s.dependencies if d.on_id in by],
            must=s.moscow == "must" and s.item_id not in excluded, wont=s.moscow == "wont" or s.item_id in excluded,
            frozen_sprint=None if s.item_id in excluded else frozen, pinned_sprint=pins.get(s.item_id),
            previous_sprint=prev_place.get(s.item_id), skill_hours=skill_hours))
    for u, v in graph.edges:                     # task-level dependencies across stories
        st = next((x for x in stories if x.story_id == v), None)
        if st and u not in st.depends_on:
            st.depends_on.append(u)
    sprints = [SprintIn(index=w.index, cap_p50=w.cap_p50, cap_p85=w.cap_p85) for w in windows]
    _apply_relax(relax, stories, sprints, deadlines, assumptions)
    if defaulted:
        assumptions.append(f"Business value 5 (neutral) assumed for {len(defaulted)} stories without a score.")
    perf.event("solver_input", "sprint", stories=len(stories), sprints=len(sprints), deadlines=len(deadlines),
               pins=len(pins), relaxations=len(relax), excluded=len(excluded))
    res = cpsat_solve(stories, sprints, deadlines, time_limit_s=time_limit_s)
    if res.status not in ("OPTIMAL", "FEASIBLE", "INFEASIBLE"):
        # UNKNOWN (time limit without a solution) or MODEL_INVALID: neither a plan nor a proof that none exists.
        # Writing it would replace the last valid plan with one that defers every story for no stated reason.
        log.warning("sprint solve for %s ended %s after %ss (limit %ss); sprint-plan.json left unchanged",
                    project, res.status, res.wall_time_s, time_limit_s)
        perf.event("solver_unsuccessful", "sprint", status=res.status, wall_time_s=res.wall_time_s,
                   time_limit_s=time_limit_s, previous_plan_kept=prev is not None)
        kept = f"the previous plan (v{prev.version}) is kept" if prev else "no plan was written"
        raise files.ProjectError(
            f"the CP-SAT solver ended {res.status} after {res.wall_time_s}s (time limit {time_limit_s}s) without a plan "
            f"or a proof of infeasibility; sprint/sprint-plan.json was not changed and {kept}. Nothing was relaxed. "
            "Tell the approver; do not present an empty plan.")
    options = verified_options(stories, sprints, deadlines, res.conflicting) if res.status == "INFEASIBLE" else []
    placement = res.placement or {s.story_id: 0 for s in stories}
    deferred = []
    for s in stories:
        if placement.get(s.story_id, 0) != 0:
            continue
        if s.story_id in unest:
            code, why = "unestimated", "No story points; Agent 1 must estimate it."
        elif s.story_id in too_big:
            code, why = "too_large", (f"Larger than {settings.max_story_points_per_story} SP or one sprint's P50 capacity; "
                                      "Agent 1 must split it.")
        elif by[s.story_id].moscow == "wont":
            code, why = "wont", "Marked won't-have."
        elif res.status == "INFEASIBLE":
            code, why = "deadline_infeasible", f"No feasible plan; conflicting: {', '.join(res.conflicting) or 'capacity'}."
        elif any(placement.get(d, 0) == 0 for d in s.depends_on):
            code, why = "dependency", "Depends on deferred stories: " + ", ".join(d for d in s.depends_on if placement.get(d, 0) == 0)
        elif s.pinned_sprint == 0:
            code, why = "human_override", "Pinned out of the horizon by the approver."
        else:
            code, why = "capacity", "Capacity in the horizon is used by higher-value, deadline or must-have stories."
        deferred.append(Deferral(story_id=s.story_id, reason_code=code, explanation=why))
    with perf.span("phase", "sprint.forecast"):
        censored = []
        p50_k, p85_k = cap.forecast(sum(s.points for s in stories if not s.wont), windows, hist, censored_out=censored)
        if censored and censored[0]:
            assumptions.append(f"Forecast censored: {censored[0]}/2000 samples did not finish within 60 sprints; boundary dates are not completion guarantees.")
    L = settings.calendar.sprint_length_days
    end_of = lambda k: windows[0].start + timedelta(days=k * L - 1)  # noqa: E731
    pts = {s.story_id: s.points for s in stories}
    slots = []
    for w in windows:
        ids = sorted([sid for sid, k in placement.items() if k == w.index], key=lambda i: -values.get(i, 0))
        effective = next(s for s in sprints if s.index == w.index)
        slots.append(SprintSlot(sprint_index=w.index, number=w.number, name=f"{settings.project_name} Sprint {w.number}",
                                start=w.start, end=w.end, story_ids=ids,
                                committed_points=int(round(sum(pts[i] for i in ids))), capacity_p50=effective.cap_p50,
                                capacity_p85=effective.cap_p85, maintenance_reserved_points=w.reserved,
                                available_person_days=w.person_days))
    plan = SprintPlan(
        plan_id=prev.plan_id if prev else files.new_id(), version=(prev.version + 1) if prev else 1, project=project,
        backlog_sha256=files.file_sha(project, files.BACKLOG), settings_sha256=files.file_sha(project, files.PROJECT_SETTINGS),
        as_of=as_of_d, sprints=slots, deferred=deferred,
        forecast=Forecast(p50_last_sprint=first + p50_k - 1, p85_last_sprint=first + p85_k - 1,
                          p50_date=end_of(p50_k), p85_date=end_of(p85_k)),
        solver=SolverReport(status=res.status, objective=res.objective, best_bound=res.best_bound,
                            wall_time_s=res.wall_time_s, conflicting_constraints=res.conflicting),
        assumptions=assumptions, options_if_infeasible=[PlanOption(**o) for o in options],
        business_values=business, wsjf=values, pins=pins, relaxations=relax, generated_at=files.utcnow())
    with perf.span("fs", "sprint.write_plan") as sp:
        files.write_json(project, files.SPRINT_PLAN, plan)
        files.write_text(project, files.SPRINT_PLAN_MD, render_md(plan, backlog))
        sp.set(planned=sum(len(s.story_ids) for s in slots), deferred=len(deferred), options=len(options),
               solver_status=res.status)
    return json.dumps({
        "written": files.virtual(project, files.SPRINT_PLAN), "solver": res.status, "conflicting": res.conflicting,
        "sprints": [{"sprint_index": s.sprint_index, "name": s.name, "start": str(s.start), "end": str(s.end),
                     "committed_points": s.committed_points, "capacity_p85": s.capacity_p85, "capacity_p50": s.capacity_p50,
                     "stories": [{"id": i, "title": by[i].title} for i in s.story_ids]} for s in slots],
        "deferred": [d.model_dump() for d in deferred], "options_if_infeasible": [o for o in options],
        "forecast": plan.forecast.model_dump(mode="json"), "assumptions": assumptions,
        "next": "call sprint_annotate with a goal for every sprint that has stories and an explanation per deferral"})


def annotate(project: str, goals: dict[str, str], deferral_explanations: dict[str, str] | None = None,
             summary_md: str = "") -> str:
    plan = files.read_json(project, files.SPRINT_PLAN, SprintPlan)
    backlog = files.read_json(project, files.BACKLOG, Backlog)
    goals = {int(k): str(v).strip() for k, v in goals.items()}
    missing = [s.sprint_index for s in plan.sprints if s.story_ids and not goals.get(s.sprint_index, s.goal)]
    if missing:
        raise files.ProjectError(f"sprints {missing} have stories but no goal")
    for s in plan.sprints:
        if s.sprint_index in goals:
            s.goal = goals[s.sprint_index]
    expl = deferral_explanations or {}
    unknown = [k for k in expl if k not in {d.story_id for d in plan.deferred}]
    if unknown:
        raise files.ProjectError(f"not deferred in this plan: {', '.join(unknown)}")
    for d in plan.deferred:
        if d.story_id in expl:
            d.explanation = str(expl[d.story_id]).strip()
    plan.summary_md = summary_md.strip()
    plan.annotated = True
    files.write_json(project, files.SPRINT_PLAN, plan)
    files.write_text(project, files.SPRINT_PLAN_MD, render_md(plan, backlog))
    return json.dumps({"written": [files.virtual(project, files.SPRINT_PLAN), files.virtual(project, files.SPRINT_PLAN_MD)],
                       "annotated": True})


def check(project: str) -> str:
    """Read-only: does sprint-plan.json respect capacity, dependencies and the current backlog?"""
    plan = files.read_json(project, files.SPRINT_PLAN, SprintPlan)
    backlog = files.read_json(project, files.BACKLOG, Backlog)
    by = backlog.by_id()
    problems, warnings = [], []
    if plan.settings_sha256 != files.file_sha(project, files.PROJECT_SETTINGS):
        problems.append("sprint plan settings provenance is missing or stale; re-run sprint_solve")
    if plan.backlog_sha256 != files.file_sha(project, files.BACKLOG):
        problems.append("sprint-plan.json was built from an older backlog.json; re-run sprint_solve")
    placed = {sid: s.sprint_index for s in plan.sprints for sid in s.story_ids}
    story_ids = {s.item_id for s in backlog.stories()}
    all_placed = [sid for s in plan.sprints for sid in s.story_ids]
    deferred_ids = [d.story_id for d in plan.deferred]
    if len(all_placed) != len(set(all_placed)) or len(deferred_ids) != len(set(deferred_ids)):
        problems.append("a story is placed or deferred more than once")
    if set(all_placed) & set(deferred_ids) or (set(all_placed) | set(deferred_ids)) - story_ids:
        problems.append("planned/deferred stories overlap or contain unknown story IDs")
    accounted = set(placed) | {d.story_id for d in plan.deferred}
    missing = [s.item_id for s in backlog.stories() if s.item_id not in accounted]
    if missing:
        problems.append(f"stories neither planned nor deferred: {', '.join(missing)}")
    for s in plan.sprints:
        load = sum((by[i].estimate.story_points or 0) for i in s.story_ids if i in by and by[i].estimate)
        if load > s.capacity_p50 + 1e-6:
            problems.append(f"{s.name}: {load} SP exceeds P50 capacity {s.capacity_p50}")
        elif load > s.capacity_p85:
            warnings.append(f"{s.name}: {load} SP is above the 85%-confidence capacity {s.capacity_p85}")
        if s.story_ids and not s.goal:
            problems.append(f"{s.name} has no sprint goal")
    for sid, k in placed.items():
        for d in by[sid].dependencies if sid in by else []:
            if d.on_id in by and by[d.on_id].level == "story" and placed.get(d.on_id, 99) > k:
                problems.append(f"{sid} (sprint {k}) depends on {d.on_id} planned later or not at all")
    if not plan.annotated:
        problems.append("goals and deferral explanations not written (sprint_annotate not called)")
    if plan.solver.status in ("UNKNOWN", "MODEL_INVALID"):
        problems.append(f"the solver ended {plan.solver.status}: this plan is not a solution; re-run sprint_solve")
    if plan.solver.status == "INFEASIBLE" and not plan.options_if_infeasible:
        warnings.append("infeasible with no verified options; the approver must change inputs")
    must_deferred = [d.story_id for d in plan.deferred if d.story_id in by and by[d.story_id].moscow == "must"]
    if must_deferred:
        warnings.append(f"must-have stories deferred: {', '.join(must_deferred)}")
    return json.dumps({"ok": not problems, "problems": problems, "warnings": warnings, "solver": plan.solver.status})


def render_md(plan: SprintPlan, backlog: Backlog) -> str:
    by = backlog.by_id()
    lines = [f"# Sprint plan v{plan.version} — {plan.project}", "",
             f"Solver **{plan.solver.status}** ({plan.solver.wall_time_s}s) · as of {plan.as_of}", ""]
    if plan.summary_md:
        lines += [plan.summary_md, ""]
    if plan.forecast:
        f = plan.forecast
        lines += [f"Forecast for the whole backlog: sprint {f.p50_last_sprint} ({f.p50_date}) at P50, "
                  f"sprint {f.p85_last_sprint} ({f.p85_date}) at P85.", ""]
    for s in plan.sprints:
        lines += [f"## {s.name} ({s.start} → {s.end})", "",
                  f"Goal: {s.goal or '_not written_'}", "",
                  f"{s.committed_points} SP committed · capacity P85 {s.capacity_p85} / P50 {s.capacity_p50} · "
                  f"{s.maintenance_reserved_points} SP reserved for maintenance · {s.available_person_days} person-days", ""]
        for sid in s.story_ids:
            st = by.get(sid)
            pts = st.estimate.story_points if st and st.estimate else "?"
            lines.append(f"- {sid} {st.title if st else ''} — {pts} SP · WSJF {plan.wsjf.get(sid, 0)}")
        lines.append("")
    if plan.deferred:
        lines += ["## Deferred", ""] + [f"- {d.story_id} `{d.reason_code}`: {d.explanation}" for d in plan.deferred] + [""]
    if plan.options_if_infeasible:
        lines += ["## Options (each verified feasible by the solver)", ""]
        lines += [f"- **{o.option_id}** {o.summary} — {o.impact} (`{', '.join(o.changes)}`)" for o in plan.options_if_infeasible]
        lines.append("")
    lines += ["## Assumptions", ""] + [f"- {a}" for a in plan.assumptions]
    return "\n".join(lines) + "\n"
