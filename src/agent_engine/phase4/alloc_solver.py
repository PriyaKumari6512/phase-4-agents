"""Assignment optimization.

Primary engine: the forked Timefold task-assigning service (/v1/schedules). Fallback (PHASE4_ALLOCATION_SOLVER_MODE=local
or service unreachable in auto mode): an OR-Tools CP-SAT model with the same semantics - skills hard (incl. the
"human" tag), capacity hard, affinity stretches duration, priorities, balanced load.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import httpx
from ortools.sat.python import cp_model

from agent_engine import perf
from agent_engine.phase4.settings import get_settings

log = logging.getLogger(__name__)
AFFINITY_MULT = {"HIGH": 1, "MEDIUM": 2, "LOW": 3, "NONE": 4}
PRIORITY_WEIGHT = {"CRITICAL": 4, "MAJOR": 2, "MINOR": 1}
TERMINAL = {"SOLVING_COMPLETED", "SOLVING_INCOMPLETE", "SOLVING_FAILED", "DATASET_INVALID"}


@dataclass
class Worker:
    worker_id: str
    name: str
    kind: str                       # human | ai_agent
    skills: list[str]
    capacity_minutes: int
    affinities: dict[str, str] = field(default_factory=dict)   # customer -> HIGH/MEDIUM/LOW/NONE
    initial_task_ids: list[str] = field(default_factory=list)


@dataclass
class TaskIn:
    task_id: str
    base_minutes: int               # estimate hours * 60 / 2 (MEDIUM affinity x2 == estimate)
    required_skills: list[str]
    customer: str
    priority: str                   # CRITICAL | MAJOR | MINOR
    min_start: int = 0


@dataclass
class SolveOut:
    engine: str
    status: str
    score: str
    assigned: dict[str, list[tuple[str, int]]]   # worker -> [(task, start_minute)]
    unassigned: list[str]
    analysis: dict | None = None


# ------------------------------------------------------------------------------------------------ Timefold
def timefold_input(workers: list[Worker], tasks: list[TaskIn]) -> dict:
    customers = sorted({t.customer for t in tasks})
    return {
        "customers": [{"id": c, "name": c} for c in customers],
        "taskTypes": [{"code": t.task_id, "title": t.task_id, "baseDurationInMinutes": t.base_minutes,
                       "requiredSkills": t.required_skills} for t in tasks],
        "employees": [{"id": w.worker_id, "fullName": w.name, "skills": w.skills,
                       "customerAffinities": {c: a for c, a in w.affinities.items() if c in customers},
                       "taskIds": [i for i in w.initial_task_ids if any(t.task_id == i for t in tasks)],
                       "capacityInMinutes": w.capacity_minutes} for w in workers],
        "tasks": [{"id": t.task_id, "taskTypeCode": t.task_id, "indexInTaskType": 0, "customerId": t.customer,
                   "minStartTimeInMinutes": t.min_start, "priority": t.priority} for t in tasks],
    }


def solve_timefold(workers: list[Worker], tasks: list[TaskIn], run_name: str) -> SolveOut:
    s = get_settings()
    base = s.phase4_allocation_solver_url.rstrip("/")
    body = {"config": {"run": {"name": run_name, "termination": {"spentLimit": s.phase4_allocation_time_limit}}},
            "modelInput": timefold_input(workers, tasks)}
    with httpx.Client(timeout=60) as http:
        with perf.http_span("timefold", "submit", "POST", f"{base}/v1/schedules", include_path=True,
                            tasks=len(tasks), workers=len(workers), spent_limit=s.phase4_allocation_time_limit) as sp:
            r = http.post(f"{base}/v1/schedules", json=body)
            perf.http_result(sp, r)
            r.raise_for_status()
            data = r.json()
            job = data.get("id") or (data.get("metadata") or {}).get("id")
            sp.set(remote_job_id=str(job) if job else None)
        if not job:
            raise RuntimeError(f"Timefold returned no job id: {str(data)[:300]}")
        deadline = time.monotonic() + 600
        # Service-side queue and solve time are not reported by the service; this span is the client's view
        # (submit -> terminal status), measured to the 2 s poll interval.
        with perf.span("service_wait", "timefold.poll", poll_interval_s=2, deadline_s=600,
                       service_time_visibility="inferred from polling") as poll:
            polls, statuses, sleep_s = 0, {}, 0.0
            while True:
                polls += 1
                res = http.get(f"{base}/v1/schedules/{job}").json()
                status = (res.get("metadata") or {}).get("solverStatus")
                statuses[str(status)] = statuses.get(str(status), 0) + 1
                if status in TERMINAL:
                    break
                if time.monotonic() > deadline:
                    http.delete(f"{base}/v1/schedules/{job}")
                    poll.set(polls=polls, statuses=statuses, sleep_s=round(sleep_s, 3))
                    raise RuntimeError("Timefold solve did not finish in 600 s")
                time.sleep(2)
                sleep_s += 2
            poll.set(polls=polls, statuses=statuses, sleep_s=round(sleep_s, 3), terminal_status=status)
        if status in ("SOLVING_FAILED", "DATASET_INVALID"):
            raise RuntimeError(f"Timefold {status}: {str(res.get('metadata', {}).get('validationResult'))[:500]}")
        analysis = None
        with perf.http_span("timefold", "score_analysis", "GET", f"{base}/v1/schedules", include_path=True) as sp:
            try:
                ra = http.get(f"{base}/v1/schedules/{job}/score-analysis")
                perf.http_result(sp, ra)
                analysis = ra.json()
            except Exception as exc:   # best effort, as before: the analysis is optional
                sp.set_status("error", perf.error_summary(exc), perf.classify_error(exc))
    assigned = {e["id"]: [(a["taskId"], int(a.get("startTimeInMinutes", 0))) for a in e.get("assignedTasks", [])]
                for e in (res.get("modelOutput") or {}).get("employees", [])}
    done = {t for lst in assigned.values() for t, _ in lst}
    return SolveOut(engine="timefold", status=status, score=str(res["metadata"].get("score", "")),
                    assigned=assigned, unassigned=[t.task_id for t in tasks if t.task_id not in done], analysis=analysis)


def timefold_available() -> bool:
    url = get_settings().phase4_allocation_solver_url.rstrip("/") + "/v1/demo-data"
    with perf.http_span("timefold", "availability_probe", "GET", url, include_path=True, timeout_s=3) as sp:
        try:
            r = httpx.get(url, timeout=3)
            perf.http_result(sp, r)
            sp.set(available=r.status_code < 500)
            return r.status_code < 500
        except httpx.HTTPError as exc:
            sp.set(available=False, error_category=perf.classify_error(exc))
            return False


# ------------------------------------------------------------------------------------------------ local CP-SAT
def solve_local(workers: list[Worker], tasks: list[TaskIn], time_limit_s: float = 20.0) -> SolveOut:
    m = cp_model.CpModel()
    dur = {}
    x = {}
    for t in tasks:
        for w in workers:
            if set(t.required_skills) <= set(w.skills):
                d = t.base_minutes * AFFINITY_MULT.get(w.affinities.get(t.customer, "NONE"), 4)
                dur[t.task_id, w.worker_id] = d
                x[t.task_id, w.worker_id] = m.new_bool_var(f"x[{t.task_id},{w.worker_id}]")
    assigned_lit = {}
    for t in tasks:
        opts = [x[k] for k in x if k[0] == t.task_id]
        assigned_lit[t.task_id] = m.new_bool_var(f"a[{t.task_id}]")
        m.add(sum(opts) == assigned_lit[t.task_id]) if opts else m.add(assigned_lit[t.task_id] == 0)
    max_ratio = m.new_int_var(0, 1000, "max_ratio")
    for w in workers:
        load = sum(dur[k] * x[k] for k in x if k[1] == w.worker_id)
        m.add(load <= w.capacity_minutes)
        if w.capacity_minutes > 0:
            m.add(load * 1000 <= max_ratio * w.capacity_minutes)
    weight = {t.task_id: PRIORITY_WEIGHT[t.priority] for t in tasks}
    m.maximize(1_000_000 * sum(assigned_lit.values())
               + 10_000 * sum(weight[t] * assigned_lit[t] for t in assigned_lit)
               - 500 * max_ratio
               - sum(dur[k] * x[k] for k in x))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_workers = 8
    proto = m.Proto() if perf.enabled() else None
    with perf.span("solver", "allocation.cpsat", tasks=len(tasks), workers_in_model=len(workers),
                   time_limit_s=time_limit_s, solver_workers=8,
                   variables=len(proto.variables) if proto is not None else None,
                   constraints=len(proto.constraints) if proto is not None else None) as sp:
        code = solver.solve(m)
        sp.set(status={cp_model.OPTIMAL: "OPTIMAL", cp_model.FEASIBLE: "FEASIBLE", cp_model.INFEASIBLE: "INFEASIBLE",
                       cp_model.MODEL_INVALID: "MODEL_INVALID"}.get(code, "UNKNOWN"),
               solver_wall_s=round(solver.wall_time, 4))
    if code not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return SolveOut("local_cpsat", "SOLVING_FAILED", "", {}, [t.task_id for t in tasks])
    by_task = {t.task_id: t for t in tasks}
    assigned: dict[str, list[tuple[str, int]]] = {w.worker_id: [] for w in workers}
    for (tid, wid), var in x.items():
        if solver.boolean_value(var):
            assigned[wid].append((tid, 0))
    for wid, lst in assigned.items():          # sequence: earliest-start, then priority
        lst.sort(key=lambda p: (by_task[p[0]].min_start, -weight[p[0]]))
        clock, seq = 0, []
        for tid, _ in lst:
            start = max(clock, by_task[tid].min_start)
            seq.append((tid, start))
            clock = start + dur[tid, wid]
        assigned[wid] = seq
    done = {t for lst in assigned.values() for t, _ in lst}
    status = "SOLVING_COMPLETED" if code == cp_model.OPTIMAL else "SOLVING_INCOMPLETE"
    return SolveOut("local_cpsat", status, f"objective={solver.objective_value:.0f}", assigned,
                    [t.task_id for t in tasks if t.task_id not in done])


def solve(workers: list[Worker], tasks: list[TaskIn], run_name: str) -> SolveOut:
    mode = get_settings().phase4_allocation_solver_mode
    # Timefold and the local CP-SAT model are different solvers with different objectives and search; results
    # and timings from one are not comparable to the other.
    with perf.span("solver_backend", "allocation", requested_mode=mode) as sp:
        if mode == "timefold" or (mode == "auto" and timefold_available()):
            sp.set(selected="timefold", reason="requested" if mode == "timefold" else "auto: service reachable")
            out = solve_timefold(workers, tasks, run_name)
        else:
            if mode == "auto":
                log.warning("Timefold allocation service unreachable at %s; using the local CP-SAT solver",
                            get_settings().phase4_allocation_solver_url)
            sp.set(selected="local_cpsat", reason="auto: service unreachable" if mode == "auto" else f"mode={mode}")
            out = solve_local(workers, tasks)
        sp.set(status=out.status, score=out.score[:120], assigned=sum(len(v) for v in out.assigned.values()),
               unassigned=len(out.unassigned))
        return out
