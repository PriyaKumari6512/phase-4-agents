"""Agent 2 (Sprint Planning): the deterministic parts around the agent's judgement.

  capacity   sprint windows, availability (holidays, PTO, calendars), Monte Carlo P50/P85 -> sprint/capacity.json
  solve      the approved priority (roadmap release -> MoSCoW -> tracker Rank) -> CP-SAT packing with dependencies,
             deadlines, must-haves, pins, churn penalty; verified options when infeasible -> sprint/sprint-plan.json
  annotate   the agent's sprint goals and deferral explanations -> sprint/sprint-plan.json + sprint-plan.md
  check      read-only consistency check for the validator
"""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta


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
    ReleasePlan,
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
        prev = None
        if files.exists(project, files.SPRINT_PLAN):
            try:
                prev = files.read_json(project, files.SPRINT_PLAN, SprintPlan)
            except files.ProjectError as exc:   # an older plan format: plan afresh rather than fail
                log.warning("previous sprint plan ignored (%s)", str(exc)[:200])
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
    # Stories marked "needs attention" by Task Breakdown have no tasks yet: left out like unestimated stories.
    unest = [s.item_id for s in backlog.stories() if (s.needs_attention or not (s.estimate and s.estimate.story_points))
             and s.moscow != "wont"]
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


MOSCOW_ORDER = {"must": 0, "should": 1, "could": 2, "wont": 3}


def _key_number(item_id: str) -> tuple[str, int]:
    prefix, _, number = item_id.rpartition("-")
    return prefix, int(number) if number.isdigit() else 0


def priority_order(backlog: Backlog) -> list[str]:
    """The approved order of the stories: roadmap release, then MoSCoW, then the tracker's Rank (Phase 2 decisions).

    Stories of a release not on the roadmap come after the known releases, stories without a release last; stories
    without a Rank come after ranked ones in their group. Nothing here is re-scored by a model."""
    release = {r.name: r.order for r in backlog.releases}
    unknown = len(release) + 1

    def key(s):
        r = release.get(s.release, unknown) if s.release else unknown + 1
        return (r, MOSCOW_ORDER.get(s.moscow, 1), s.rank is None, s.rank or "", _key_number(s.item_id))
    return [s.item_id for s in sorted(backlog.stories(), key=key)]


def release_ref(name: str) -> str:
    return "release/" + name.replace(":", "-")


def release_deadlines(backlog: Backlog, settings: ProjectSettings, assumptions: list[str]) -> list[tuple]:
    """(release, due date, source, hard) per roadmap release: the tracker's version date, else project.json."""
    fallback = {r.release: r for r in settings.release_deadlines}
    out = []
    for r in sorted(backlog.releases, key=lambda r: r.order):
        entry = fallback.get(r.name)
        if r.release_date:
            due, source = r.release_date, "tracker"
            if entry and entry.due_date != r.release_date:
                assumptions.append(f"Release {r.name}: the tracker date {r.release_date} is used, not "
                                   f"{entry.due_date} from project.json.")
        elif entry:
            due, source = entry.due_date, "project"
        else:
            due, source = None, "none"
        out.append((r, due, source, bool(entry and entry.hard)))
    ignored = sorted(set(fallback) - {r.name for r in backlog.releases})
    if ignored:
        assumptions.append("release_deadlines for releases not on the roadmap are ignored: " + ", ".join(ignored))
    return out


def priority_weights(order: list[str]) -> dict[str, float]:
    """Weight per story point, 100 for the first story down to 1 for the last. The solver's value of a story is
    points x weight, so a higher-priority point is always worth more than a lower-priority one."""
    n = len(order)
    return {sid: round(1 + 99 * (n - 1 - i) / (n - 1), 2) if n > 1 else 100.0 for i, sid in enumerate(order)}


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


def solve(project: str, pins: dict[str, int] | None = None, relax: list[str] | None = None,
          as_of: str | None = None, time_limit_s: float = 10.0) -> str:
    settings, backlog, history, prev = _load(project)
    as_of_d = _as_of(as_of)
    windows, hist, assumptions = _windows(settings, history, as_of_d)
    unest, too_big = _prechecks(backlog, settings, windows)
    pins = {k: int(v) for k, v in (pins or {}).items()}
    relax = list(relax or [])
    by = backlog.by_id()
    unknown = [s for s in pins if s not in by or by[s].level != "story"]
    if unknown:
        raise files.ProjectError(f"unknown story ids: {', '.join(sorted(set(unknown)))}")
    order = priority_order(backlog)
    weights = priority_weights(order)

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
    excluded = set(unest) | set(too_big)
    releases = release_deadlines(backlog, settings, assumptions)
    for r, due, _, hard in releases:            # each dated roadmap release is a deadline for its stories
        if due is None:
            continue
        sids = sorted(s.item_id for s in backlog.stories()
                      if s.release == r.name and s.moscow != "wont" and s.item_id not in excluded)
        last = max([w.index for w in windows if w.end <= due], default=0)
        deadlines.append(DeadlineIn(ref_id=release_ref(r.name), story_ids=sids, last_sprint=last, hard=hard))
        for sid in sids:
            deadline_limit[sid] = min(deadline_limit.get(sid, 99), last)
    stories = []
    for s in backlog.stories():
        frozen = 1 if windows[0].active and prev_place.get(s.item_id) == 1 else None
        points = float(s.estimate.story_points or 0) if s.estimate else 0.0
        stories.append(StoryIn(
            story_id=s.item_id, points=points, value=max(points, 1.0) * weights[s.item_id], depends_on=[d.on_id for d in s.dependencies if d.on_id in by],
            must=s.moscow == "must" and s.item_id not in excluded, wont=s.moscow == "wont" or s.item_id in excluded,
            frozen_sprint=None if s.item_id in excluded else frozen, pinned_sprint=pins.get(s.item_id),
            previous_sprint=prev_place.get(s.item_id)))
    for u, v in graph.edges:                     # task-level dependencies across stories
        st = next((x for x in stories if x.story_id == v), None)
        if st and u not in st.depends_on:
            st.depends_on.append(u)
    sprints = [SprintIn(index=w.index, cap_p50=w.cap_p50, cap_p85=w.cap_p85) for w in windows]
    _apply_relax(relax, stories, sprints, deadlines, assumptions)
    if backlog.releases:
        assumptions.append("Priority follows the approved roadmap: release (" +
                           " → ".join(r.name for r in sorted(backlog.releases, key=lambda r: r.order)) +
                           "), then MoSCoW, then the tracker's Rank.")
    else:
        assumptions.append("Priority follows MoSCoW, then the tracker's Rank (no roadmap releases in the backlog).")
    perf.event("solver_input", "sprint", stories=len(stories), sprints=len(sprints), deadlines=len(deadlines),
               pins=len(pins), relaxations=len(relax), excluded=len(excluded))
    res = cpsat_solve(stories, sprints, deadlines, time_limit_s=time_limit_s)
    from agent_engine.phase4.sprint_model import diagnostics
    diagnostic = diagnostics(stories, sprints, deadlines, res)
    diagnostic.update(backlog_sha256=files.file_sha(project, files.BACKLOG),
                      settings_sha256=files.file_sha(project, files.PROJECT_SETTINGS),
                      generated_at=files.utcnow(), as_of=as_of_d.isoformat(), candidates=[])
    files.write_json(project, "sprint/solver-diagnostics.json", diagnostic)
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
    options = (verified_options(stories, sprints, deadlines, res.conflicting, audit=diagnostic["candidates"])
               if res.status == "INFEASIBLE" else [])
    files.write_json(project, "sprint/solver-diagnostics.json", diagnostic)
    placement = res.placement or {s.story_id: 0 for s in stories}
    deferred = []
    for s in stories:
        if placement.get(s.story_id, 0) != 0:
            continue
        if s.story_id in unest and by[s.story_id].needs_attention:
            code, why = "unestimated", ("Needs attention: Task Breakdown produced no tasks for it "
                                        f"({by[s.story_id].needs_attention[:200]}). Plan it once it is broken down.")
        elif s.story_id in unest:
            code, why = "unestimated", "No story points; Task Breakdown must estimate it."
        elif s.story_id in too_big:
            code, why = "too_large", (f"Larger than {settings.max_story_points_per_story} SP or one sprint's P50 capacity; "
                                      "raise a split with the product owner.")
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
    release_plan = []
    with perf.span("phase", "sprint.release_plan", releases=len(releases)):
        cumulative = 0.0
        for r, due, source, hard in releases:
            members = [s for s in backlog.stories() if s.release == r.name and s.moscow != "wont"]
            ids = [s.item_id for s in members]
            cumulative += sum(pts.get(i, 0) for i in ids)
            deferred_ids = [i for i in ids if placement.get(i, 0) == 0]
            placed = [placement[i] for i in ids if placement.get(i, 0)]
            last = max(placed) if placed else None
            finish = windows[last - 1].end if last and not deferred_ids else None
            p50_r, p85_r = cap.forecast(cumulative, windows, hist) if cumulative else (0, 0)
            status = ("incomplete" if deferred_ids else "no_deadline" if due is None
                      else "late" if finish and finish > due else "on_track")
            release_plan.append(ReleasePlan(
                release=r.name, order=r.order, due_date=due, date_source=source, hard=hard, story_ids=ids,
                points=sum(pts.get(i, 0) for i in ids), deferred_story_ids=deferred_ids, last_sprint_index=last,
                planned_finish=finish, p50_date=end_of(p50_r) if p50_r else None,
                p85_date=end_of(p85_r) if p85_r else None, status=status))
    slots = []
    for w in windows:
        position = {sid: n for n, sid in enumerate(order)}
        ids = sorted([sid for sid, k in placement.items() if k == w.index], key=lambda i: position.get(i, 0))
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
        releases=release_plan,
        solver=SolverReport(status=res.status, objective=res.objective, best_bound=res.best_bound,
                            wall_time_s=res.wall_time_s, conflicting_constraints=res.conflicting),
        assumptions=assumptions, options_if_infeasible=[PlanOption(**o) for o in options],
        priority_order=order, priority=weights, pins=pins, relaxations=relax, generated_at=files.utcnow())
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
    })


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
        problems.append("sprint plan settings provenance is missing or stale; run Sprint Planning again")
    if plan.backlog_sha256 != files.file_sha(project, files.BACKLOG):
        problems.append("sprint-plan.json was built from an older backlog.json; run Sprint Planning again")
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
        problems.append("sprint goals and deferral explanations are not written yet")
    if plan.solver.status in ("UNKNOWN", "MODEL_INVALID"):
        problems.append(f"the solver ended {plan.solver.status}: this plan is not a solution; run Sprint Planning again")
    if plan.solver.status == "INFEASIBLE" and not plan.options_if_infeasible:
        warnings.append("infeasible with no verified options; the approver must change inputs")
    for r in plan.releases:
        if r.status == "late":
            (problems if r.hard else warnings).append(
                f"release {r.release} finishes {r.planned_finish}, after its {'hard ' if r.hard else ''}deadline {r.due_date}")
        elif r.status == "incomplete":
            warnings.append(f"release {r.release} is not complete in the horizon: {', '.join(r.deferred_story_ids)} deferred")
        if r.due_date and r.p85_date and r.p85_date > r.due_date and r.status == "on_track":
            warnings.append(f"release {r.release}: the 85%-confidence forecast {r.p85_date} is after its deadline {r.due_date}")
    order = {r.release: r.order for r in plan.releases}
    capacity_deferred = [d.story_id for d in plan.deferred if d.reason_code == "capacity" and d.story_id in by
                         and by[d.story_id].moscow == "must" and by[d.story_id].release in order]
    for sid in capacity_deferred:
        rank = order[by[sid].release]
        later = sorted(p for p in placed if p in by and by[p].release in order and order[by[p].release] > rank)
        if later:
            warnings.append(f"{sid} (must-have, release {by[sid].release}) is deferred for capacity while later-release "
                            f"stories are planned: {', '.join(later[:6])}; check that it does not fit or split it")
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
            release = f" · {st.release}" if st and st.release else ""
            rank = plan.priority_order.index(sid) + 1 if sid in plan.priority_order else "-"
            lines.append(f"- {sid} {st.title if st else ''} — {pts} SP{release} · priority #{rank}")
        lines.append("")
    if plan.releases:
        lines += ["## Release plan", "", "| Release | Deadline | Stories | Points | Planned finish | P50 / P85 forecast | Status |",
                  "|---|---|---|---|---|---|---|"]
        for r in plan.releases:
            deadline = (f"{r.due_date} ({'hard, ' if r.hard else ''}{r.date_source})" if r.due_date else "-")
            finish = f"{r.planned_finish} (sprint {r.last_sprint_index})" if r.planned_finish else "-"
            lines.append(f"| {r.release} | {deadline} | {len(r.story_ids)} | {r.points:g} | {finish} | "
                         f"{r.p50_date or '-'} / {r.p85_date or '-'} | {r.status.replace('_', ' ')} |")
        lines.append("")
    if plan.deferred:
        lines += ["## Deferred", ""] + [f"- {d.story_id} `{d.reason_code}`: {d.explanation}" for d in plan.deferred] + [""]
    if plan.options_if_infeasible:
        lines += ["## Options (each verified feasible by the solver)", ""]
        lines += [f"- **{o.option_id}** {o.summary} — {o.impact} (`{', '.join(o.changes)}`)" for o in plan.options_if_infeasible]
        lines.append("")
    lines += ["## Assumptions", ""] + [f"- {a}" for a in plan.assumptions]
    return "\n".join(lines) + "\n"
