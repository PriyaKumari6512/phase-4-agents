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
    skill_hours: dict[str, float] = field(default_factory=dict)


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
    skill_caps: dict[str, float] = field(default_factory=dict)


@dataclass
class Relaxation:
    drop_switches: set[str] = field(default_factory=set)
    deadline_shift: dict[str, int] = field(default_factory=dict)
    capacity_factor: float = 1.0


@dataclass
class SolveResult:
    status: str
    placement: dict[str, int]          # story -> sprint (0 = not planned)
    objective: float | None
    best_bound: float | None
    wall_time_s: float
    conflicting: list[str]
    sprint_load: dict[int, float]


def _status(code: int) -> str:
    return {cp_model.OPTIMAL: "OPTIMAL", cp_model.FEASIBLE: "FEASIBLE", cp_model.INFEASIBLE: "INFEASIBLE",
            cp_model.MODEL_INVALID: "MODEL_INVALID"}.get(code, "UNKNOWN")


def solve(stories: list[StoryIn], sprints: list[SprintIn], deadlines: list[DeadlineIn],
          relax: Relaxation | None = None, time_limit_s: float = 10.0, workers: int = 8,
          want_core: bool = True) -> SolveResult:
    relax = relax or Relaxation()
    K = len(sprints)
    ids = [s.story_id for s in stories]
    by_id = {s.story_id: s for s in stories}
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
        for skill, cap in spr.skill_caps.items():
            m.add(sum(int(round(by_id[i].skill_hours.get(skill, 0) * SCALE)) * x[i, spr.index] for i in ids)
                  <= int(cap * relax.capacity_factor * SCALE))

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
        lit = switch(f"deadline:{d.ref_id}") if d.hard else None
        for sid in d.story_ids:
            if sid not in by_id:
                continue
            if d.hard and lit is not None:
                m.add(x[sid, 0] == 0).only_enforce_if(lit)
                m.add(sp[sid] <= limit).only_enforce_if(lit)
            elif not d.hard:
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
    t0 = time.perf_counter()
    code = solver.solve(m)
    status = _status(code)
    conflicting: list[str] = []
    if status == "INFEASIBLE" and want_core and lits:
        core_solver = cp_model.CpSolver()           # assumption cores are reliable with one worker
        core_solver.parameters.max_time_in_seconds = time_limit_s
        core_solver.parameters.num_workers = 1
        core_solver.solve(m)
        idx = set(core_solver.sufficient_assumptions_for_infeasibility())
        conflicting = sorted(lit.name for lit in lits if lit.index in idx)
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


def verified_options(stories, sprints, deadlines, conflicting: list[str], time_limit_s: float = 5.0) -> list[dict]:
    """Candidate fixes for each conflicting switch; only those that make the model feasible are returned."""
    candidates: list[tuple[str, Relaxation, list[str], str]] = []
    for name in conflicting:
        kind, _, rest = name.partition(":")
        if kind == "deadline":
            for shift in (1, 2):
                candidates.append((f"Move {rest} by {shift} sprint(s)", Relaxation(deadline_shift={rest: shift}),
                                   [f"relax:deadline:{rest}:+{shift}"], f"deadline {rest} slips {shift} sprint(s)"))
            candidates.append((f"Treat {rest} as a soft target", Relaxation(drop_switches={name}),
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
    for summary, relax, changes, impact in candidates:
        res = solve(stories, sprints, deadlines, relax, time_limit_s=time_limit_s, want_core=False)
        if res.status in ("OPTIMAL", "FEASIBLE") and summary not in seen:
            seen.add(summary)
            deferred = [s for s, k in res.placement.items() if k == 0]
            out.append({"option_id": f"OPT-{len(out) + 1}", "summary": summary, "changes": changes,
                        "impact": f"{impact}; {len(deferred)} stories left unplanned"})
        if len(out) >= 4:
            break
    return out
