"""Agent 3 (Work Allocation): the deterministic parts around the agent's judgement.

  prepare    one sprint's tasks, hard AI-eligibility rules, worker capacity, skill gaps -> allocation/problem.json
  solve      the agent's AI-eligibility verdicts + approver pins/vetoes -> Timefold (forked task-assigning service)
             or the local CP-SAT fallback -> score breakdown, runner-up, post-checks -> allocation/assignments.json
  annotate   the agent's one-line explanation per assignment -> assignments.json + assignments.md
  check      read-only consistency check for the validator

Skill levels: declared skills (phase4/project.json) blended with mined evidence (phase4/skill-profiles.json, from
`agent-engine phase4 mine-profiles`). AI agents only get tasks that pass every hard rule, that the agent judged
self-contained, and whose repository CI the Infra agent set up and a human approved (gate P4-G4).
"""

from __future__ import annotations

import json
from collections import defaultdict

import networkx as nx

from agent_engine import perf
from agent_engine.gates import stale_approvals
from agent_engine.phase4 import capacity as cap
from agent_engine.phase4 import files
from agent_engine.phase4.alloc_solver import AFFINITY_MULT, TaskIn, Worker, solve as run_solver
from agent_engine.phase4.contracts import (
    Assignment,
    AssignmentPlan,
    Backlog,
    EligibilityVerdict,
    InfraManifest,
    ProjectSettings,
    SprintPlan,
    Unassigned,
    WorkItem,
)
from agent_engine.phase4.settings import get_settings
from agent_engine.phase4.skills_taxonomy import normalize

HUMAN_TAG = "human"
HAS_SKILL_LEVEL = 0.4
DECLARED_LEVEL = 0.7
MIN_SUCCESS = 0.6
REVIEW_SHARE = 0.10
MAX_AI_FILES = 4
INFRA_GATE_FILE = "gates/P4-G4.approved.json"
RISKY = ("auth", "login", "password", "permission", "role", "payment", "billing", "migration", "migrate",
         "terraform", "infrastructure", "deploy", "secret", "encrypt", "helm", "kubernetes", ".tf", "workflow")


# ============================================================================ context
def _ctx(project: str, sprint_index: int):
    with perf.span("phase", "allocation.load_inputs", sprint_index=sprint_index) as sp:
        settings = files.read_json(project, files.PROJECT_SETTINGS, ProjectSettings)
        plan = files.read_json(project, files.SPRINT_PLAN, SprintPlan)
        backlog = files.read_json(project, files.BACKLOG, Backlog)
        slot = next((s for s in plan.sprints if s.sprint_index == sprint_index), None)
        if slot is None:
            raise files.ProjectError(f"sprint_index {sprint_index} is not in sprint-plan.json "
                                     f"(have {[s.sprint_index for s in plan.sprints]})")
        tasks = [t for sid in slot.story_ids for t in backlog.tasks_of(sid)]
        sp.set(tasks=len(tasks), stories=len(slot.story_ids), team=len(settings.team),
               ai_agents=len([a for a in settings.ai_agents if a.enabled]))
    return settings, plan, backlog, slot, tasks


def _profiles(project: str, settings: ProjectSettings) -> tuple[dict[str, dict[str, float]], list[dict]]:
    """worker -> skill -> level (declared blended with mined evidence), and ownership rows."""
    with perf.span("phase", "allocation.profiles") as sp:
        levels, rows = _profiles_impl(project, settings)
        sp.set(workers=len(levels), ownership_rows=len(rows))
    return levels, rows


def _profiles_impl(project: str, settings: ProjectSettings) -> tuple[dict[str, dict[str, float]], list[dict]]:
    mined = files.read_json(project, files.SKILL_PROFILES) if files.exists(project, files.SKILL_PROFILES) else {}
    observed: dict[str, dict[str, float]] = mined.get("skills", {})
    levels: dict[str, dict[str, float]] = {}
    for m in settings.team:
        stated = {t: DECLARED_LEVEL for s in m.declared_skills if (t := normalize(s))}
        obs = observed.get(m.member_id, {})
        out = {}
        for skill in set(stated) | set(obs):
            st, ob = stated.get(skill, 0), obs.get(skill, 0)
            out[skill] = round(max(ob, 0.6 * st + 0.4 * ob) if st else ob, 3)
        levels[m.member_id] = out
    return levels, mined.get("ownership", [])


def _ownership(rows: list[dict], worker_id: str, area: str) -> tuple[str, float]:
    """HIGH >=30% or codeowner, MEDIUM >=10%, LOW >0, NONE; UNKNOWN when nobody has data for the area."""
    area_rows = [r for r in rows if r.get("path_prefix") == area]
    if not area_rows:
        return "UNKNOWN", 0.0
    mine = [r for r in area_rows if r.get("worker_id") == worker_id]
    if not mine:
        return "NONE", 0.0
    share = max(max(r.get("commit_share", 0), r.get("line_share", 0)) for r in mine)
    if any(r.get("is_codeowner") for r in mine) or share >= 0.3:
        return "HIGH", share
    if share >= 0.1:
        return "MEDIUM", share
    return ("LOW", share) if share > 0 else ("NONE", 0.0)


def _agent_success(project: str, provider: str, task_type: str) -> tuple[float | None, int]:
    rows = files.read_json(project, files.AGENT_OUTCOMES) if files.exists(project, files.AGENT_OUTCOMES) else []
    rows = [r for r in rows if r.get("provider") == provider and r.get("task_type", task_type) == task_type]
    if not rows:
        return None, 0
    return sum(1 for r in rows if r.get("outcome") == "merged") / len(rows), len(rows)


def ci_ready_repos(project: str) -> set[str]:
    """Repos whose CI the Infra agent generated, once a human approved P4-G4 and nothing changed since."""
    if not files.exists(project, files.INFRA_MANIFEST) or not files.exists(project, INFRA_GATE_FILE):
        return set()
    if stale_approvals(files.project_dir(project), [INFRA_GATE_FILE]):
        return set()
    return set(files.read_json(project, files.INFRA_MANIFEST, InfraManifest).ci_repos)


def path_prefix(path: str, depth: int = 2) -> str:
    """Code area of a file, the same key `mine-profiles` writes ownership rows under."""
    parts = path.replace("\\", "/").split("/")
    return "/".join(parts[:depth]) + "/" if len(parts) > 1 else parts[0]


def hard_checks(task: WorkItem, max_hours: float, repo: str | None, ready: set[str]) -> str | None:
    text = f"{task.title} {task.description_md} {' '.join(task.file_paths)}".lower()
    if not task.acceptance_criteria:
        return "no acceptance criteria"
    if not task.file_paths or len(task.file_paths) > MAX_AI_FILES:
        return f"file scope missing or more than {MAX_AI_FILES} files"
    if task.estimate is None or (task.estimate.hours or 0) > max_hours:
        return f"estimate above the agent limit of {max_hours} h"
    if any(r in text for r in RISKY):
        return "touches a sensitive area (auth, payments, migrations, infrastructure or secrets)"
    if task.open_questions:
        return "has open questions"
    if not repo:
        return "task has no code repository (Agent 1 sets `repo` per feature or task)"
    if repo not in ready:
        return f"CI for {repo} is not set up by the Infra agent and approved (gate P4-G4)"
    return None


def _window(settings: ProjectSettings, slot) -> cap.SprintWindow:
    with perf.span("phase", "allocation.availability"):
        w = cap.SprintWindow(index=slot.sprint_index, number=slot.number, start=slot.start, end=slot.end)
        cap.fill_availability(settings, [w])
    return w


# ============================================================================ prepare
def prepare(project: str, sprint_index: int) -> str:
    settings, plan, backlog, slot, tasks = _ctx(project, sprint_index)
    agents = [a for a in settings.ai_agents if a.enabled]
    max_hours = max((a.max_task_hours for a in agents), default=0)
    ready = ci_ready_repos(project)
    rows = []
    for t in tasks:
        repo = t.repo or (settings.code_repos[0] if len(settings.code_repos) == 1 else None)
        reason = "no AI agents enabled" if not agents else hard_checks(t, max_hours, repo, ready)
        rows.append({"task_id": t.item_id, "story_id": t.parent_id, "title": t.title, "type": t.type,
                     "hours": t.estimate.hours if t.estimate else None, "skills": t.skills_required,
                     "files": t.file_paths, "acceptance_criteria": [a.text for a in t.acceptance_criteria],
                     "agent1_ai_proposal": {"eligible": t.ai_eligible, "reason": t.ai_eligibility_reason},
                     "ai_candidate": reason is None, "hard_rule_failed": reason})
    w = _window(settings, slot)
    levels, _ = _profiles(project, settings)
    team = [{"worker_id": m.member_id, "name": m.display_name, "role": m.role,
             "available_hours": round(w.hours_by_member.get(m.member_id, 0.0), 1),
             "skills": sorted(s for s, lv in levels.get(m.member_id, {}).items() if lv >= HAS_SKILL_LEVEL)}
            for m in settings.team]
    have = set().union(*[set(x["skills"]) for x in team], *[set(a.skills) for a in agents]) if team else set()
    need: dict[str, float] = defaultdict(float)
    for t in tasks:
        for s in t.skills_required[:1]:
            need[s] += t.estimate.hours if t.estimate and t.estimate.hours else 0
    gaps = sorted({s for t in tasks for s in t.skills_required if s not in have})
    supply: dict[str, float] = defaultdict(float)
    for x in team:
        for s in x["skills"]:
            supply[s] += x["available_hours"]
    short = {s: {"need_h": round(h, 1), "have_h": round(supply[s], 1)} for s, h in need.items()
             if s not in gaps and h > supply[s]}
    data = {"sprint_index": sprint_index, "sprint": slot.name, "window": [str(slot.start), str(slot.end)],
            "tasks": rows, "team": team, "ai_agents": [a.model_dump() for a in agents], "ci_ready_repos": sorted(ready),
            "skill_gaps": gaps, "capacity_shortfall": short}
    files.write_json(project, files.ALLOCATION_PROBLEM, data)
    return json.dumps({"written": files.virtual(project, files.ALLOCATION_PROBLEM), "sprint": slot.name,
                       "tasks": len(rows), "ai_candidates": [r for r in rows if r["ai_candidate"]],
                       "not_ai_candidates": {r["task_id"]: r["hard_rule_failed"] for r in rows if not r["ai_candidate"]},
                       "team": team, "skill_gaps": gaps, "capacity_shortfall": short})


# ============================================================================ solve
def solve(project: str, sprint_index: int, ai_verdicts: dict[str, dict] | None = None,
          pins: dict[str, str] | None = None, vetoes: dict[str, list[str]] | None = None,
          block_ai: list[str] | None = None) -> str:
    settings, plan, backlog, slot, tasks = _ctx(project, sprint_index)
    by = backlog.by_id()
    task_ids = {t.item_id for t in tasks}
    pins, vetoes, blocked = dict(pins or {}), dict(vetoes or {}), set(block_ai or [])
    unknown = [t for t in [*pins, *vetoes, *blocked, *(ai_verdicts or {})] if t not in task_ids]
    if unknown:
        raise files.ProjectError(f"not tasks of sprint {sprint_index}: {', '.join(sorted(set(unknown)))}")
    agents = [a for a in settings.ai_agents if a.enabled]
    max_hours = max((a.max_task_hours for a in agents), default=0)
    ready = ci_ready_repos(project)
    eligibility: dict[str, EligibilityVerdict] = {}
    with perf.span("phase", "allocation.eligibility", tasks=len(tasks), pins=len(pins), vetoes=len(vetoes),
                   ai_blocks=len(blocked), verdicts=len(ai_verdicts or {})) as elig_span:
        outcome_reads = 0
        for t in tasks:
            repo = t.repo or (settings.code_repos[0] if len(settings.code_repos) == 1 else None)
            if not agents:
                eligibility[t.item_id] = EligibilityVerdict(eligible=False, reason="no AI agents enabled")
                continue
            if t.item_id in blocked:
                eligibility[t.item_id] = EligibilityVerdict(eligible=False, reason="AI blocked by the approver")
                continue
            reason = hard_checks(t, max_hours, repo, ready)
            if reason:
                eligibility[t.item_id] = EligibilityVerdict(eligible=False, reason=reason)
                continue
            v = (ai_verdicts or {}).get(t.item_id)
            if v is None:
                eligibility[t.item_id] = EligibilityVerdict(eligible=False, reason="no AI-eligibility verdict given")
                continue
            outcome_reads += len(agents)       # each call re-reads phase4/agent-outcomes.json
            rates = [_agent_success(project, a.provider, t.type) for a in agents]
            n = max((r[1] for r in rates), default=0)
            best = max((r[0] or 0 for r in rates), default=0)
            shadow = bool(v.get("eligible")) and n < settings.ai_min_recorded_outcomes
            ok = bool(v.get("eligible")) and not shadow and (n == 0 or best >= MIN_SUCCESS)
            why = str(v.get("reason", "")).strip() or "no reason given"
            if shadow:
                why = f"{why} (shadow mode: {n} recorded agent outcomes, {settings.ai_min_recorded_outcomes} needed)"
            elif v.get("eligible") and not ok:
                why = f"{why} (recorded success rate {best:.0%} below {MIN_SUCCESS:.0%})"
            eligibility[t.item_id] = EligibilityVerdict(eligible=ok, reason=why, shadow=shadow)
        elig_span.set(eligible=sum(v.eligible for v in eligibility.values()),
                      ineligible=sum(not v.eligible for v in eligibility.values()),
                      shadow=sum(v.shadow for v in eligibility.values()), outcome_history_reads=outcome_reads)

    w0 = _window(settings, slot)
    levels, own_rows = _profiles(project, settings)
    pinned_minutes: dict[str, int] = defaultdict(int)
    for tid, wid in pins.items():
        pinned_minutes[wid] += int(((by[tid].estimate.hours if by[tid].estimate else 0) or 0) * 60)
    workers: list[Worker] = []
    review_budget_h = 0.0
    for m in settings.team:
        hours = w0.hours_by_member.get(m.member_id, 0.0)
        if agents and m.can_review:
            review_budget_h += hours * REVIEW_SHARE
            hours *= 1 - REVIEW_SHARE
        skills = sorted({s for s, lv in levels.get(m.member_id, {}).items() if lv >= HAS_SKILL_LEVEL}) + [HUMAN_TAG]
        workers.append(Worker(worker_id=m.member_id, name=m.display_name, kind="human", skills=skills,
                              capacity_minutes=max(0, int(hours * 60) - pinned_minutes[m.member_id])))
    if agents:
        ai_hours_total = review_budget_h / max(0.01, get_settings().phase4_ai_review_ratio)
        for a in agents:
            limit = a.max_concurrent_tasks * a.max_task_hours * 3
            workers.append(Worker(worker_id=a.agent_id, name=a.agent_id, kind="ai_agent", skills=sorted(set(a.skills)),
                                  capacity_minutes=max(0, int(min(limit, ai_hours_total / len(agents)) * 60)
                                                       - pinned_minutes[a.agent_id])))
    wk = {w.worker_id: w for w in workers}
    bad_pins = {t: w for t, w in pins.items() if w not in wk}
    if bad_pins:
        raise files.ProjectError(f"pins name unknown workers: {bad_pins} (workers: {sorted(wk)})")
    for tid, banned in vetoes.items():              # a veto is a task-specific tag every other worker has
        tag = f"not-vetoed-{tid}"
        for w in workers:
            if w.worker_id not in banned:
                w.skills.append(tag)

    # task inputs: priority from critical path / deadlines / must, earliest start from the task DAG
    deadline_stories = {sid for d in settings.deadlines for rid in d.requirement_ids for sid in backlog.coverage.get(rid, [])}
    crit = set(backlog.critical_path) | deadline_stories
    g = nx.DiGraph()
    for t in tasks:
        g.add_node(t.item_id)
        for d in t.dependencies:
            if d.on_id in task_ids:
                g.add_edge(d.on_id, t.item_id)
    est = {t.item_id: int(((t.estimate.hours if t.estimate else 0) or 1) * 60) for t in tasks}
    es: dict[str, int] = {}
    if nx.is_directed_acyclic_graph(g):
        for n in nx.topological_sort(g):
            es[n] = max([es[p] + est[p] for p in g.predecessors(n)], default=0)
    tin: list[TaskIn] = []
    for t in tasks:
        if t.item_id in pins:
            continue
        story = by[t.parent_id]
        prio = "CRITICAL" if story.item_id in crit else ("MAJOR" if story.priority == "P1" or story.moscow == "must" else "MINOR")
        req = list(dict.fromkeys(t.skills_required[:3]))
        if not eligibility[t.item_id].eligible:
            req.append(HUMAN_TAG)
        if t.item_id in vetoes:
            req.append(f"not-vetoed-{t.item_id}")
        area = path_prefix(t.file_paths[0]) if t.file_paths else (t.components[0] if t.components else "general")
        tin.append(TaskIn(task_id=t.item_id, base_minutes=max(1, est[t.item_id] // 2), required_skills=req,
                          customer=area, priority=prio, min_start=es.get(t.item_id, 0)))
    for area in {t.customer for t in tin}:
        any_owner = any(_ownership(own_rows, w.worker_id, area)[0] != "UNKNOWN" for w in workers)
        for w in workers:
            aff = _ownership(own_rows, w.worker_id, area)[0] if (w.kind == "human" and any_owner) else "MEDIUM"
            w.affinities[area] = aff if aff != "UNKNOWN" else "MEDIUM"

    perf.event("solver_input", "allocation", tasks=len(tin), workers=len(workers), pinned=len(pins),
               vetoed=len(vetoes), areas=len({t.customer for t in tin}))
    res = run_solver(workers, tin, f"{project}-sprint{slot.number}")
    tin_by = {t.task_id: t for t in tin}
    loads: dict[str, int] = defaultdict(int)
    for wid, seq in res.assigned.items():
        for tid, _ in seq:
            loads[wid] += tin_by[tid].base_minutes * AFFINITY_MULT[wk[wid].affinities.get(tin_by[tid].customer, "MEDIUM")]
    assignments: list[Assignment] = []
    for wid, seq in res.assigned.items():
        w = wk[wid]
        for tid, start in seq:
            tt = tin_by[tid]
            lv = levels.get(wid, {}) if w.kind == "human" else {s: 0.8 for s in w.skills}
            req = [s for s in tt.required_skills if s != HUMAN_TAG and not s.startswith("not-vetoed")]
            fit = sum(lv.get(s, 0.5 if s in w.skills else 0) for s in req) / max(1, len(req))
            own = _ownership(own_rows, wid, tt.customer)[1] if w.kind == "human" else 0.0
            hours = tt.base_minutes * AFFINITY_MULT[w.affinities.get(tt.customer, "MEDIUM")] / 60
            assignments.append(Assignment(
                task_id=tid, story_id=by[tid].parent_id, sprint_index=sprint_index, worker_id=wid, worker_kind=w.kind,
                planned_start_minute=start, planned_hours=round(hours, 1),
                score_breakdown={"skill_fit": round(fit, 2), "ownership": round(own, 2),
                                 "load_after": round(loads[wid] / max(1, w.capacity_minutes), 2),
                                 "cost": 0.2 if w.kind == "ai_agent" else 1.0},
                runner_up_worker_id=_runner_up(tt, wid, workers, loads)))
    for tid, wid in pins.items():
        t = by[tid]
        assignments.append(Assignment(task_id=tid, story_id=t.parent_id, sprint_index=sprint_index, worker_id=wid,
                                      worker_kind=wk[wid].kind, planned_start_minute=0,
                                      planned_hours=(t.estimate.hours if t.estimate else 0) or 0,
                                      score_breakdown={"pinned": 1.0}, explanation="Pinned by the approver.", pinned=True))
    unassigned = []
    for tid in res.unassigned:
        t = tin_by[tid]
        if not any(set(t.required_skills) <= set(w.skills) for w in workers):
            needed = [s for s in t.required_skills if not s.startswith("not-vetoed")]
            missing = [s for s in needed if not any(s in w.skills for w in workers)]
            why = (f"Nobody has {', '.join(missing)}." if missing else
                   f"Nobody has all of {', '.join(needed)} together; pair two people or split the task.")
            code = "no_skill_match"
        elif HUMAN_TAG in t.required_skills and not eligibility[tid].eligible:
            code, why = "capacity", f"Human capacity is used up and the task is not AI-eligible ({eligibility[tid].reason})."
        else:
            code, why = "capacity", "No worker with the skills has capacity left this sprint."
        unassigned.append(Unassigned(task_id=tid, reason_code=code, explanation=why))
    # post-checks: never hand a non-eligible task to an AI agent, never exceed capacity
    for a in assignments:
        if a.worker_kind == "ai_agent" and not a.pinned and not eligibility[a.task_id].eligible:
            raise files.ProjectError(f"post-check failed: non-eligible task {a.task_id} assigned to {a.worker_id}")
    for wid, minutes in loads.items():
        if minutes > wk[wid].capacity_minutes:
            raise files.ProjectError(f"post-check failed: {wid} over capacity ({minutes} > {wk[wid].capacity_minutes} min)")
    prev = files.read_json(project, files.ASSIGNMENTS, AssignmentPlan) if files.exists(project, files.ASSIGNMENTS) else None
    planned = defaultdict(float)
    for a in assignments:
        planned[a.worker_id] += a.planned_hours
    ap = AssignmentPlan(
        plan_id=prev.plan_id if prev else files.new_id(), version=(prev.version + 1) if prev else 1, project=project,
        sprint_plan_sha256=files.file_sha(project, files.SPRINT_PLAN), sprint_index=sprint_index,
        assignments=sorted(assignments, key=lambda a: (a.worker_id, a.planned_start_minute)), unassigned=unassigned,
        eligibility=eligibility, solver_engine="timefold" if res.engine == "timefold" else "local_cpsat",
        solver_status=res.status, solver_score=res.score, pins=pins, vetoes=vetoes,
        workers=[{"worker_id": w.worker_id, "name": w.name, "kind": w.kind,
                  "capacity_hours": round(w.capacity_minutes / 60, 1), "planned_hours": round(planned[w.worker_id], 1)}
                 for w in workers],
        generated_at=files.utcnow())
    with perf.span("fs", "allocation.write_assignments") as sp:
        files.write_json(project, files.ASSIGNMENTS, ap)
        files.write_text(project, files.ASSIGNMENTS_MD, render_md(ap, backlog, slot.name))
        sp.set(assigned=len(assignments), unassigned=len(unassigned), engine=ap.solver_engine, status=res.status)
    return json.dumps({
        "written": files.virtual(project, files.ASSIGNMENTS), "engine": ap.solver_engine, "status": res.status,
        "assignments": [{"task_id": a.task_id, "task": by[a.task_id].title, "worker": wk[a.worker_id].name,
                         "worker_kind": a.worker_kind, "hours": a.planned_hours, "score_breakdown": a.score_breakdown,
                         "runner_up": wk[a.runner_up_worker_id].name if a.runner_up_worker_id else None}
                        for a in ap.assignments],
        "unassigned": [u.model_dump() for u in unassigned], "workers": ap.workers,
        "next": "call allocation_annotate with a one-sentence explanation per assigned task"})


def _runner_up(t: TaskIn, chosen: str, workers: list[Worker], loads: dict[str, int]) -> str | None:
    best, best_score = None, -1.0
    for w in workers:
        if w.worker_id == chosen or not set(t.required_skills) <= set(w.skills):
            continue
        dur = t.base_minutes * AFFINITY_MULT[w.affinities.get(t.customer, "MEDIUM")]
        if loads[w.worker_id] + dur > w.capacity_minutes:
            continue
        score = 1 - (loads[w.worker_id] + dur) / max(1, w.capacity_minutes)
        if score > best_score:
            best, best_score = w.worker_id, score
    return best


# ============================================================================ annotate / check / render
def annotate(project: str, explanations: dict[str, str]) -> str:
    ap = files.read_json(project, files.ASSIGNMENTS, AssignmentPlan)
    backlog = files.read_json(project, files.BACKLOG, Backlog)
    plan = files.read_json(project, files.SPRINT_PLAN, SprintPlan)
    known = {a.task_id for a in ap.assignments}
    unknown = [k for k in explanations if k not in known]
    if unknown:
        raise files.ProjectError(f"not assigned in this plan: {', '.join(unknown)}")
    for a in ap.assignments:
        if a.task_id in explanations:
            a.explanation = str(explanations[a.task_id]).strip()
    missing = [a.task_id for a in ap.assignments if not a.explanation]
    ap.annotated = not missing
    files.write_json(project, files.ASSIGNMENTS, ap)
    slot = next(s for s in plan.sprints if s.sprint_index == ap.sprint_index)
    files.write_text(project, files.ASSIGNMENTS_MD, render_md(ap, backlog, slot.name))
    return json.dumps({"annotated": ap.annotated, "missing_explanations": missing,
                       "written": [files.virtual(project, files.ASSIGNMENTS), files.virtual(project, files.ASSIGNMENTS_MD)]})


def check(project: str) -> str:
    ap = files.read_json(project, files.ASSIGNMENTS, AssignmentPlan)
    plan = files.read_json(project, files.SPRINT_PLAN, SprintPlan)
    backlog = files.read_json(project, files.BACKLOG, Backlog)
    problems, warnings = [], []
    if ap.sprint_plan_sha256 != files.file_sha(project, files.SPRINT_PLAN):
        problems.append("assignments.json was built from an older sprint-plan.json; re-run allocation_solve")
    slot = next((s for s in plan.sprints if s.sprint_index == ap.sprint_index), None)
    tasks = {t.item_id for sid in (slot.story_ids if slot else []) for t in backlog.tasks_of(sid)}
    covered = {a.task_id for a in ap.assignments} | {u.task_id for u in ap.unassigned}
    if tasks - covered:
        problems.append(f"tasks neither assigned nor unassigned: {', '.join(sorted(tasks - covered))}")
    if len({a.task_id for a in ap.assignments}) != len(ap.assignments):
        problems.append("a task is assigned twice")
    for a in ap.assignments:
        if a.worker_kind == "ai_agent" and not a.pinned and not (ap.eligibility.get(a.task_id) and ap.eligibility[a.task_id].eligible):
            problems.append(f"{a.task_id} assigned to AI agent {a.worker_id} without eligibility")
        if not a.explanation:
            problems.append(f"{a.task_id} has no explanation")
    for w in ap.workers:
        if w["planned_hours"] > w["capacity_hours"] + 0.05 and w["kind"] == "human":
            warnings.append(f"{w['name']} planned {w['planned_hours']} h > capacity {w['capacity_hours']} h (pins?)")
    if ap.unassigned:
        warnings.append(f"{len(ap.unassigned)} tasks unassigned: " + ", ".join(u.task_id for u in ap.unassigned[:15]))
    return json.dumps({"ok": not problems, "problems": problems, "warnings": warnings, "engine": ap.solver_engine})


def render_md(ap: AssignmentPlan, backlog: Backlog, sprint_name: str) -> str:
    by = backlog.by_id()
    names = {w["worker_id"]: w["name"] for w in ap.workers}
    lines = [f"# Assignments — {sprint_name} (v{ap.version})", "",
             f"Solver: {ap.solver_engine} · {ap.solver_status} · {ap.solver_score}", "",
             "| Worker | Kind | Planned h | Capacity h |", "|---|---|---|---|"]
    lines += [f"| {w['name']} | {w['kind']} | {w['planned_hours']} | {w['capacity_hours']} |" for w in ap.workers]
    lines += ["", "| Task | Title | Assignee | Hours | Why | Runner-up |", "|---|---|---|---|---|---|"]
    for a in ap.assignments:
        t = by.get(a.task_id)
        lines.append(f"| {a.task_id} | {(t.title if t else '')[:70].replace('|', '/')} | {names.get(a.worker_id, a.worker_id)} "
                     f"| {a.planned_hours} | {a.explanation.replace('|', '/') or '-'} | "
                     f"{names.get(a.runner_up_worker_id, '-') if a.runner_up_worker_id else '-'} |")
    if ap.unassigned:
        lines += ["", "## Unassigned", ""] + [f"- {u.task_id} `{u.reason_code}`: {u.explanation}" for u in ap.unassigned]
    ai = {k: v for k, v in ap.eligibility.items() if v.eligible or v.shadow}
    if ai:
        lines += ["", "## AI eligibility", ""] + [f"- {k}: {'eligible' if v.eligible else 'shadow'} — {v.reason}"
                                                  for k, v in ai.items()]
    return "\n".join(lines) + "\n"
