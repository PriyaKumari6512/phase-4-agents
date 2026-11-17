"""CP-SAT sprint packing model + verified infeasibility options.

Decision: every story goes into exactly one of sprint 1..K or "not planned" (0).
Hard: capacity <= P50 (after maintenance reserve), dependency order, frozen active sprint, won't-haves out.
Named switches (assumption literals): hard deadlines, must-haves, human pins -> infeasibility core.
Soft: load above P85, lateness of soft deadlines, churn vs the previous plan.
Objective: maximize sum(value * (K + 1 - sprint)) - penalties.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from agent_engine import perf

SCALE = 10                # points are scaled to integers (0.1 SP resolution)
LATE_WEIGHT = 40
OVER_WEIGHT = 30
CHURN_WEIGHT = 25
UNPLANNED_DEADLINE_WEIGHT = 400


@dataclass
class StoryIn:
    story_id: str
    points: float
    value: float                       # WSJF 0..100
    depends_on: list[str] = field(default_factory=list)
    must: bool = False
    wont: bool = False
    frozen_sprint: int | None = None   # active sprint content (hard, no switch)
    pinned_sprint: int | None = None   # human pin (switch)
    previous_sprint: int | None = None


@dataclass
class DeadlineIn:
    ref_id: str
    story_ids: list[str]
    last_sprint: int                   # latest sprint index allowed (0 = before the horizon)
    hard: bool


@dataclass
class SprintIn:
    index: int
    cap_p50: float
    cap_p85: float


@dataclass
class Relaxation:
    drop_switches: set[str] = field(default_factory=set)
    deadline_shift: dict[str, int] = field(default_factory=dict)
    capacity_factor: float = 1.0
    soft_deadlines: set[str] = field(default_factory=set)


@dataclass
class SolveResult:
    status: str
    placement: dict[str, int]          # story -> sprint (0 = not planned)
    objective: float | None
    best_bound: float | None
    wall_time_s: float
    conflicting: list[str]
    sprint_load: dict[int, float]
    proof: str | None = None


def required_ids(stories, sprints, deadlines, relax: Relaxation) -> set[str]:
    """Mandatory placement and dependency closure, matching the model switches."""
    by = {s.story_id: s for s in stories}
    K = len(sprints)
    required = {s.story_id for s in stories
                if (s.must and not s.wont and f"must:{s.story_id}" not in relax.drop_switches)
                or (s.frozen_sprint is not None and 1 <= s.frozen_sprint <= K)
                or (not (s.frozen_sprint is not None and 1 <= s.frozen_sprint <= K)
                    and s.pinned_sprint is not None and 1 <= s.pinned_sprint <= K
                    and f"pin:{s.story_id}->{s.pinned_sprint}" not in relax.drop_switches)}
    for d in deadlines:
        if d.hard and d.ref_id not in relax.soft_deadlines and f"deadline:{d.ref_id}" not in relax.drop_switches:
            required.update(s for s in d.story_ids if s in by)
    todo = list(required)
    while todo:
        for dep in by[todo.pop()].depends_on:
            if dep in by and dep not in required:
                required.add(dep)
                todo.append(dep)
    return required


def diagnostics(stories, sprints, deadlines, result: SolveResult) -> dict:
    required = required_ids(stories, sprints, deadlines, Relaxation())
    demand = sum(round(s.points * SCALE) for s in stories if s.story_id in required)
    capacity = sum(int(s.cap_p50 * SCALE) for s in sprints)
    return {"status": result.status, "wall_time_s": result.wall_time_s,
            "objective": result.objective, "best_bound": result.best_bound,
            "required_story_ids": sorted(required), "required_points_scaled": demand,
            "capacity_points_scaled": capacity, "scale": SCALE,
            "aggregate_deficit_points": max(0, demand - capacity) / SCALE,
            "aggregate_bound_proves_infeasible": demand > capacity,
            "conflicting_assumptions": result.conflicting,
            "conflict_note": "Solver assumption core is sufficient, not necessarily minimal or the only cause.",
            "dependency_edges": [[d, s.story_id] for s in stories for d in s.depends_on],
            "limitations": "Bounds are necessary, not sufficient. Dependencies allow the same sprint; no task-duration critical path is inferred. UNKNOWN is not infeasibility."}


def _status(code: int) -> str:
    return {cp_model.OPTIMAL: "OPTIMAL", cp_model.FEASIBLE: "FEASIBLE", cp_model.INFEASIBLE: "INFEASIBLE",
            cp_model.MODEL_INVALID: "MODEL_INVALID"}.get(code, "UNKNOWN")


def _model_size(m: cp_model.CpModel) -> dict:
    proto = m.Proto()
    return {"variables": len(proto.variables), "constraints": len(proto.constraints)}


def solve(stories: list[StoryIn], sprints: list[SprintIn], deadlines: list[DeadlineIn],
          relax: Relaxation | None = None, time_limit_s: float = 10.0, workers: int = 8,
          want_core: bool = True, purpose: str = "main") -> SolveResult:
    relax = relax or Relaxation()
    K = len(sprints)
    ids = [s.story_id for s in stories]
    by_id = {s.story_id: s for s in stories}
    if not want_core:
        required = required_ids(stories, sprints, deadlines, relax)
        # A necessary bound only: it can prove infeasibility, never declare feasibility.
        if sum(round(by_id[s].points * SCALE) for s in required) > sum(int(s.cap_p50 * relax.capacity_factor * SCALE) for s in sprints):
            perf.event("solver_pruned", "sprint.candidate", reason="required points exceed total capacity")
            return SolveResult("INFEASIBLE", {}, None, None, 0.0, [], {}, "required points exceed total scaled capacity")
    m = cp_model.CpModel()
    x = {(s.story_id, k): m.new_bool_var(f"x[{s.story_id},{k}]") for s in stories for k in range(K + 1)}
    sp, planned = {}, {}
    for s in stories:
        m.add_exactly_one(x[s.story_id, k] for k in range(K + 1))
        sp[s.story_id] = m.new_int_var(0, K, f"sp[{s.story_id}]")
        m.add(sp[s.story_id] == sum(k * x[s.story_id, k] for k in range(K + 1)))
        planned[s.story_id] = x[s.story_id, 0].Not()

    switches: dict[str, cp_model.IntVar] = {}

    def switch(name: str) -> cp_model.IntVar | None:
        if name in relax.drop_switches:
            return None
        if name not in switches:
            switches[name] = m.new_bool_var(name)
        return switches[name]

    # fixed placements
    for s in stories:
        if s.wont:
            m.add(x[s.story_id, 0] == 1)
        if s.frozen_sprint is not None and 1 <= s.frozen_sprint <= K:
            m.add(x[s.story_id, s.frozen_sprint] == 1)
        elif s.pinned_sprint is not None and 0 <= s.pinned_sprint <= K:
            lit = switch(f"pin:{s.story_id}->{s.pinned_sprint}")
            if lit is not None:
                m.add(x[s.story_id, s.pinned_sprint] == 1).only_enforce_if(lit)
        if s.must and not s.wont:
            lit = switch(f"must:{s.story_id}")
            if lit is not None:
                m.add(x[s.story_id, 0] == 0).only_enforce_if(lit)

    # capacity (hard at P50) and overload above P85 (soft)
    over = {}
    for spr in sprints:
        load = sum(int(round(by_id[i].points * SCALE)) * x[i, spr.index] for i in ids)
        m.add(load <= int(spr.cap_p50 * relax.capacity_factor * SCALE))
        over[spr.index] = m.new_int_var(0, 10_000_000, f"over[{spr.index}]")
        m.add(over[spr.index] >= load - int(spr.cap_p85 * relax.capacity_factor * SCALE))

    # dependencies: B planned => A planned and sprint(A) <= sprint(B)
    for s in stories:
        for a in s.depends_on:
            if a not in by_id:
                continue
            m.add_implication(planned[s.story_id], planned[a])
            m.add(sp[a] <= sp[s.story_id]).only_enforce_if(planned[s.story_id])

    # deadlines
    late_terms = []
    for d in deadlines:
        limit = max(0, min(K, d.last_sprint + relax.deadline_shift.get(d.ref_id, 0)))
        hard = d.hard and d.ref_id not in relax.soft_deadlines
        lit = switch(f"deadline:{d.ref_id}") if hard else None
        for sid in d.story_ids:
            if sid not in by_id:
                continue
            if hard and lit is not None:
                m.add(x[sid, 0] == 0).only_enforce_if(lit)
                m.add(sp[sid] <= limit).only_enforce_if(lit)
            elif not hard:
                late = m.new_int_var(0, K, f"late[{d.ref_id},{sid}]")
                m.add(late >= sp[sid] - limit)
                late_terms.append(LATE_WEIGHT * late)
                late_terms.append(UNPLANNED_DEADLINE_WEIGHT * x[sid, 0])

    # objective
    value_terms = [int(round(s.value * 10)) * (K + 1 - k) * x[s.story_id, k]
                   for s in stories for k in range(1, K + 1)]
    churn_terms = []
    for s in stories:
        if s.previous_sprint is not None and 1 <= s.previous_sprint <= K and s.frozen_sprint is None:
            churn_terms.append(CHURN_WEIGHT * 10 * x[s.story_id, s.previous_sprint].Not())
            m.add_hint(x[s.story_id, s.previous_sprint], 1)
    m.maximize(sum(value_terms) - sum(late_terms) * 10 - OVER_WEIGHT * sum(over.values()) - sum(churn_terms))

    lits = list(switches.values())
    if lits:
        m.add_assumptions(lits)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_workers = workers
    sizes = _model_size(m) if perf.enabled() else {}
    t0 = time.perf_counter()
    with perf.span("solver", "sprint.cpsat", purpose=purpose, stories=len(stories), sprints=K, switches=len(lits),
                   time_limit_s=time_limit_s, workers=workers, **sizes) as sp:
        code = solver.solve(m)
        status = _status(code)
        sp.set(status=status, objective=solver.objective_value if status in ("OPTIMAL", "FEASIBLE") else None,
               best_bound=solver.best_objective_bound if status in ("OPTIMAL", "FEASIBLE") else None,
               solver_wall_s=round(solver.wall_time, 4))
    conflicting: list[str] = []
    if status == "INFEASIBLE" and want_core and lits:
        # A second solve with its own time budget: total time can exceed time_limit_s.
        with perf.span("solver", "sprint.core_extraction", time_limit_s=time_limit_s, workers=1,
                       switches=len(lits)) as sp:
            core_solver = cp_model.CpSolver()           # assumption cores are reliable with one worker
            core_solver.parameters.max_time_in_seconds = time_limit_s
            core_solver.parameters.num_workers = 1
            core_code = core_solver.solve(m)
            idx = set(core_solver.sufficient_assumptions_for_infeasibility())
            conflicting = sorted(lit.name for lit in lits if lit.index in idx)
            sp.set(status=_status(core_code), core_size=len(conflicting), solver_wall_s=round(core_solver.wall_time, 4))
    wall = time.perf_counter() - t0
    placement, load = {}, {}
    if status in ("OPTIMAL", "FEASIBLE"):
        for s in stories:
            placement[s.story_id] = next(k for k in range(K + 1) if solver.boolean_value(x[s.story_id, k]))
        for spr in sprints:
            load[spr.index] = sum(by_id[i].points for i, k in placement.items() if k == spr.index)
    return SolveResult(status=status, placement=placement,
                       objective=solver.objective_value if status in ("OPTIMAL", "FEASIBLE") else None,
                       best_bound=solver.best_objective_bound if status in ("OPTIMAL", "FEASIBLE") else None,
                       wall_time_s=round(wall, 3), conflicting=conflicting, sprint_load=load)


def verified_options(stories, sprints, deadlines, conflicting: list[str], time_limit_s: float = 5.0,
                     audit: list[dict] | None = None) -> list[dict]:
    """Candidate fixes for each conflicting switch; only those that make the model feasible are returned."""
    candidates: list[tuple[str, Relaxation, list[str], str]] = []
    for name in conflicting:
        kind, _, rest = name.partition(":")
        if kind == "deadline":
            for shift in (1, 2):
                candidates.append((f"Move {rest} by {shift} sprint(s)", Relaxation(deadline_shift={rest: shift}),
                                   [f"relax:deadline:{rest}:+{shift}"], f"deadline {rest} slips {shift} sprint(s)"))
            candidates.append((f"Treat {rest} as a soft target", Relaxation(soft_deadlines={rest}),
                               [f"soften:deadline:{rest}"], "stories may finish after the date (lateness penalized)"))
        elif kind == "must":
            candidates.append((f"Downgrade {rest} from must to should", Relaxation(drop_switches={name}),
                               [f"downgrade:must:{rest}"], f"{rest} may be deferred"))
        elif kind == "pin":
            candidates.append((f"Unpin {rest}", Relaxation(drop_switches={name}), [f"unpin:{rest}"],
                               "solver may move the pinned story"))
    for factor in (1.15, 1.3):
        candidates.append((f"Add {round((factor - 1) * 100)}% capacity", Relaxation(capacity_factor=factor),
                           [f"capacity:x{factor}"], f"needs about {round((factor - 1) * 100)}% more person-days per sprint"))
    out, seen = [], set()
    with perf.span("solver", "sprint.verified_options", candidates=len(candidates), conflicting=len(conflicting),
                   time_limit_s_each=time_limit_s) as group:
        attempts = 0
        for n, (summary, relax, changes, impact) in enumerate(candidates, 1):
            attempts += 1
            with perf.span("solver", "sprint.candidate", candidate=n, transformation=",".join(changes)) as sp:
                res = solve(stories, sprints, deadlines, relax, time_limit_s=time_limit_s, want_core=False,
                            purpose="candidate")
                sp.set(status=res.status, feasible=res.status in ("OPTIMAL", "FEASIBLE"))
            if audit is not None:
                audit.append({"changes": changes, "status": res.status, "wall_time_s": res.wall_time_s,
                              "proof": res.proof, "time_limit_s": time_limit_s})
            if res.status in ("OPTIMAL", "FEASIBLE") and summary not in seen:
                seen.add(summary)
                deferred = [s for s, k in res.placement.items() if k == 0]
                out.append({"option_id": f"OPT-{len(out) + 1}", "summary": summary, "changes": changes,
                            "impact": f"{impact}; {len(deferred)} stories left unplanned"})
            if len(out) >= 4:
                if audit is not None:
                    audit.extend({"changes": c[2], "status": "NOT_TESTED", "reason": "four feasible options found"}
                                 for c in candidates[n:])
                break
        group.set(attempts=attempts, verified=len(out))
    return out
