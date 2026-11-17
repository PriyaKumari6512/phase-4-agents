"""Sprint Planning (PDLC Phase 4, step 4.2): the approved backlog -> sprints, goals and a release plan.

Code does the planning (sprint.py): capacity and velocity, the approved priority (release -> MoSCoW -> Rank),
CP-SAT packing with dependencies and release deadlines, the release plan and deferral reasons. A small model writes
what needs language, in one structured call: a goal per sprint, plain deferral explanations, a short summary and,
when nothing fits, which verified option to recommend. When a reviewer's request names pins or an option, one more
small call turns it into exact decisions, which code checks against real story ids and the plan's own options.
"""
from __future__ import annotations

import contextvars
import hashlib
import json
import re
from contextlib import contextmanager
from pathlib import Path

from langchain_core.messages import AIMessage
from typing import Literal

from pydantic import BaseModel, ConfigDict

from agent_engine.phase4 import files, sprint
from agent_engine.phase4.contracts import Backlog, ProjectSettings, SprintPlan
from agent_engine.phase4.structured import invoke as _invoke

STATE_DIR = ".engine-sprint-planning"
DEFAULT_REQUESTS = {"", "Plan the sprints."}


class _Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SprintGoal(_Record):
    sprint_index: int
    goal: str                       # ONE outcome users can see at the end of the sprint


class DeferralNote(_Record):
    story_id: str
    explanation: str                # plain words for a non-engineer, true to the reason code


class Annotation(_Record):
    goals: list[SprintGoal]
    deferral_explanations: list[DeferralNote]
    summary_md: str                 # 3-6 lines for the approver
    recommended_option: str | None  # an option_id when the plan is infeasible, else null


class Pin(_Record):
    story_id: str
    sprint_index: int               # 0 = keep out of the planning horizon


class Decisions(_Record):
    pins: list[Pin]
    clear_pins: list[str]           # story ids whose earlier pin the request removes
    option_id: str | None           # the infeasibility option the approver chose, if any
    note: str                       # what the request asks that is not a pin or an option (answered in the summary)


class ReviewFinding(_Record):
    item: str                       # "sprint 2" or a deferred story id
    severity: Literal["blocking", "warning"]
    message: str


class LightReview(_Record):
    findings: list[ReviewFinding]


# ---------------------------------------------------------------------------------------------- model selection
_tier = contextvars.ContextVar("sprint_planning_tier", default="fast")


@contextmanager
def operation_model(pack, level: int):
    token = _tier.set(pack.models[level])
    try:
        yield
    finally:
        _tier.reset(token)


def _spec() -> str:
    from agent_engine.agent import model_spec
    return model_spec(_tier.get())


def _rules() -> str:
    from agent_engine.agent import load_pack
    return load_pack("sprint-planning").system_prompt


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def _state(project: str, *parts: str) -> Path:
    root = files.project_dir(project).resolve()
    path = root / STATE_DIR / Path(*parts)
    if not path.resolve().is_relative_to(root / STATE_DIR):
        raise files.ProjectError("invalid sprint-planning state path")
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


def _previous(project: str) -> SprintPlan | None:
    if not files.exists(project, files.SPRINT_PLAN):
        return None
    try:
        return files.read_json(project, files.SPRINT_PLAN, SprintPlan)
    except files.ProjectError:
        return None


def _statement(item) -> str:
    return (item.description_md or "").split("\n\n", 1)[0][:400]


# ---------------------------------------------------------------------------------------------- reviewer decisions
def check_decisions(decisions: Decisions, backlog: Backlog, horizon: int, previous: SprintPlan | None) -> list[str]:
    stories = {s.item_id for s in backlog.stories()}
    errors = []
    for p in decisions.pins:
        if p.story_id not in stories:
            errors.append(f"pin names unknown story {p.story_id}")
        if not 0 <= p.sprint_index <= horizon:
            errors.append(f"pin {p.story_id} -> sprint {p.sprint_index} is outside 0..{horizon}")
    if unknown := [s for s in decisions.clear_pins if s not in stories]:
        errors.append(f"clear_pins names unknown stories {unknown}")
    options = {o.option_id for o in (previous.options_if_infeasible if previous else [])}
    if decisions.option_id and decisions.option_id not in options:
        errors.append(f"option {decisions.option_id} is not one of the plan's options {sorted(options) or '(none)'}")
    return errors


async def decide(project: str, request: str, backlog: Backlog, settings: ProjectSettings,
                 previous: SprintPlan | None, callbacks) -> Decisions:
    """Turn a reviewer's free-text request into exact pins / an option choice (checked; one retry)."""
    payload = {"reviewer_request": request, "horizon_sprints": settings.calendar.planning_horizon_sprints,
               "stories": [{"id": s.item_id, "title": s.title, "release": s.release} for s in backlog.stories()],
               "current_pins": previous.pins if previous else {},
               "options": [o.model_dump() for o in (previous.options_if_infeasible if previous else [])]}
    human = ("Decisions request (see 'Reviewer decisions' in your instructions):\n"
             + json.dumps(payload, ensure_ascii=False, indent=1))
    spec = _spec()
    result = await _invoke(Decisions, _rules(), human, callbacks, spec)
    errors = check_decisions(result, backlog, settings.calendar.planning_horizon_sprints, previous)
    if errors:
        result = await _invoke(Decisions, _rules(), human + "\n\nYour previous answer failed these checks:\n- "
                               + "\n- ".join(errors) + "\nPrevious answer:\n" + result.model_dump_json(),
                               callbacks, spec)
        errors = check_decisions(result, backlog, settings.calendar.planning_horizon_sprints, previous)
        if errors:
            raise files.ProjectError("could not turn the request into valid decisions: " + "; ".join(errors))
    return result


# ---------------------------------------------------------------------------------------------- the language part
def annotation_payload(plan: SprintPlan, backlog: Backlog, request: str = "", findings=()) -> dict:
    by = backlog.by_id()

    def story(sid):
        item = by.get(sid)
        return {"id": sid, "title": item.title if item else sid, "statement": _statement(item) if item else "",
                "release": item.release if item else None,
                "points": item.estimate.story_points if item and item.estimate else None}
    payload = {
        "solver": plan.solver.status, "conflicting": plan.solver.conflicting_constraints,
        "sprints": [{"sprint_index": s.sprint_index, "name": s.name, "start": str(s.start), "end": str(s.end),
                     "committed_points": s.committed_points, "capacity_p50": s.capacity_p50,
                     "capacity_p85": s.capacity_p85, "stories": [story(i) for i in s.story_ids]} for s in plan.sprints],
        "deferred": [{**story(d.story_id), "reason_code": d.reason_code, "reason": d.explanation} for d in plan.deferred],
        "releases": [r.model_dump(mode="json", exclude={"story_ids"}) for r in plan.releases],
        "forecast": plan.forecast.model_dump(mode="json") if plan.forecast else None,
        "assumptions": plan.assumptions,
        "options": [o.model_dump() for o in plan.options_if_infeasible]}
    if request.strip() not in DEFAULT_REQUESTS:
        payload["reviewer_request"] = request
    if findings:
        payload["findings_to_fix"] = list(findings)
    return payload


def check_annotation(result: Annotation, plan: SprintPlan) -> list[str]:
    errors = []
    with_stories = {s.sprint_index for s in plan.sprints if s.story_ids}
    goals = {g.sprint_index: g.goal.strip() for g in result.goals}
    if missing := sorted(i for i in with_stories if not goals.get(i)):
        errors.append(f"sprints {missing} have stories but no goal")
    if extra := sorted(set(goals) - {s.sprint_index for s in plan.sprints}):
        errors.append(f"goals for sprints that do not exist: {extra}")
    deferred = {d.story_id for d in plan.deferred}
    if unknown := sorted({n.story_id for n in result.deferral_explanations} - deferred):
        errors.append(f"explanations for stories that are not deferred: {unknown}")
    if not result.summary_md.strip():
        errors.append("summary_md is empty")
    options = {o.option_id for o in plan.options_if_infeasible}
    if plan.solver.status == "INFEASIBLE" and options and result.recommended_option not in options:
        errors.append(f"the plan is infeasible: recommend one of {sorted(options)}")
    return errors


async def annotate(project: str, callbacks, request: str = "", findings=()) -> Annotation:
    plan = files.read_json(project, files.SPRINT_PLAN, SprintPlan)
    backlog = files.read_json(project, files.BACKLOG, Backlog)
    payload = annotation_payload(plan, backlog, request, findings)
    rules, spec = _rules(), _spec()
    identity = _digest({"payload": payload, "rules": rules, "model": spec, "schema": Annotation.model_json_schema()})
    saved = _load(project, "annotations", identity + ".json")
    if saved is not None:
        result = Annotation.model_validate(saved)
    else:
        human = "Annotate this sprint plan:\n" + json.dumps(payload, ensure_ascii=False, indent=1)
        result = await _invoke(Annotation, rules, human, callbacks, spec)
        errors = check_annotation(result, plan)
        if errors:
            result = await _invoke(Annotation, rules, human + "\n\nYour previous answer failed these checks:\n- "
                                   + "\n- ".join(errors) + "\nPrevious answer:\n" + result.model_dump_json(),
                                   callbacks, spec)
            errors = check_annotation(result, plan)
            if errors:
                raise files.ProjectError("sprint plan annotation still fails checks: " + "; ".join(errors))
        _save(project, result.model_dump(mode="json"), "annotations", identity + ".json")
    summary = result.summary_md.strip()
    option = next((o for o in plan.options_if_infeasible if o.option_id == result.recommended_option), None)
    if option:
        summary += f"\n\n**Recommended option {option.option_id}:** {option.summary} ({option.impact})."
    sprint.annotate(project, {str(g.sprint_index): g.goal for g in result.goals if g.goal.strip()},
                    {n.story_id: n.explanation for n in result.deferral_explanations if n.explanation.strip()}, summary)
    return result


# ---------------------------------------------------------------------------------------------- stage operations
async def generate(project: str, request: str, callbacks, findings=()):
    settings = files.read_json(project, files.PROJECT_SETTINGS, ProjectSettings)
    backlog = files.read_json(project, files.BACKLOG, Backlog)
    previous = _previous(project)
    pins = dict(previous.pins) if previous else {}
    relax = list(previous.relaxations) if previous else []
    note = ""
    if request.strip() not in DEFAULT_REQUESTS:
        decisions = await decide(project, request, backlog, settings, previous, callbacks)
        for p in decisions.pins:
            pins[p.story_id] = p.sprint_index
        for sid in decisions.clear_pins:
            pins.pop(sid, None)
        if decisions.option_id:
            option = next(o for o in previous.options_if_infeasible if o.option_id == decisions.option_id)
            relax = list(dict.fromkeys([*relax, *option.changes]))
        note = decisions.note
    stories = {s.item_id for s in backlog.stories()}
    pins = {k: v for k, v in pins.items() if k in stories}          # stories that left the backlog drop their pins
    sprint.capacity_report(project)
    solved = json.loads(sprint.solve(project, pins, relax))
    await annotate(project, callbacks, request if not note else f"{request}\n(Answer in the summary: {note})", findings)
    planned = sum(len(s["stories"]) for s in solved["sprints"])
    text = (f"Sprint plan: sprint/sprint-plan.json and sprint/sprint-plan.md. Solver {solved['solver']}; "
            f"{planned} stories planned in {sum(1 for s in solved['sprints'] if s['stories'])} sprints, "
            f"{len(solved['deferred'])} deferred.")
    return {"messages": [AIMessage(content=text)]}


KEY_RE = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")
REASON_WORDS = {
    "capacity": ("capacity", "room", "fit", "full", "space"),
    "dependency": ("depend", "after", "wait", "block", "needs", "first"),
    "deadline_infeasible": ("deadline", "date", "infeasible", "fit"),
    "human_override": ("approver", "kept", "pinned", "decision", "decided", "chose", "out of"),
    "too_large": ("large", "big", "split", "size"),
    "unestimated": ("estimate", "points", "size"),
    "wont": ("won't", "wont", "not planned", "scope"),
}


def flagged_text(plan: SprintPlan, backlog: Backlog) -> dict[str, dict]:
    """{item: {"text", "reasons", ...}} for goals and deferral explanations deterministic rules find weak."""
    by = backlog.by_id()
    flags: dict[str, dict] = {}
    for s in plan.sprints:
        if not s.story_ids or not s.goal:
            continue
        reasons = []
        if KEY_RE.search(s.goal):
            reasons.append("names story keys instead of an outcome")
        titles = [by[i].title.lower() for i in s.story_ids if i in by and len(by[i].title) > 8]
        if sum(t in s.goal.lower() for t in titles) >= 2:
            reasons.append("repeats several story titles")
        if s.goal.count(";") or s.goal.count(",") >= 3 or s.goal.lower().count(" and ") >= 3 or len(s.goal) > 220:
            reasons.append("may list several outcomes")
        if reasons:
            flags[f"sprint {s.sprint_index}"] = {"text": s.goal, "reasons": reasons,
                                                 "stories": [by[i].title for i in s.story_ids if i in by]}
    texts = [d.explanation.strip().lower() for d in plan.deferred]
    for d in plan.deferred:
        reasons = []
        text = d.explanation.strip()
        if len(text) < 15:
            reasons.append("empty or too short")
        elif not any(w in text.lower() for w in REASON_WORDS.get(d.reason_code, ())):
            reasons.append(f"may not match its reason code '{d.reason_code}'")
        if texts.count(text.lower()) > 1 and len({x.reason_code for x in plan.deferred
                                                    if x.explanation.strip().lower() == text.lower()}) > 1:
            reasons.append("the same text explains different reasons")
        if reasons:
            flags[d.story_id] = {"text": text, "reasons": reasons, "reason_code": d.reason_code}
    return flags


async def review(project: str, callbacks=None):
    """Deterministic checks first; a model looks only at goals/explanations the rules flag. Nothing flagged: no call."""
    from agent_engine.agent import Verdict, load_pack
    check = json.loads(sprint.check(project))
    problems, warnings = check["problems"], check["warnings"]
    if problems or check["solver"] == "INFEASIBLE":
        verdict = Verdict(
            satisfied=False, status_so_far="partial",
            gaps=problems + (["The plan is infeasible; the approver chooses one of the verified options."]
                             if check["solver"] == "INFEASIBLE" else []),
            summary=(f"Deterministic checks: {len(problems)} problems, {len(warnings)} warnings. "
                     + " ".join(warnings[:6])).strip())
        return {"structured_response": verdict, "messages": [AIMessage(content=verdict.summary)]}
    plan = files.read_json(project, files.SPRINT_PLAN, SprintPlan)
    backlog = files.read_json(project, files.BACKLOG, Backlog)
    flags = flagged_text(plan, backlog)
    findings: list[ReviewFinding] = []
    if flags:
        rules, spec = load_pack("sprint-planning/validator").system_prompt, _spec()
        identity = _digest({"flags": flags, "rules": rules, "model": spec, "schema": LightReview.model_json_schema()})
        saved = _load(project, "reviews", identity + ".json")
        if saved is not None:
            result = LightReview.model_validate(saved)
        else:
            human = "Review these flagged items:\n" + json.dumps(flags, ensure_ascii=False, indent=1)
            result = await _invoke(LightReview, rules, human, callbacks, spec)
            _save(project, result.model_dump(mode="json"), "reviews", identity + ".json")
        findings = [f for f in result.findings if f.item in flags]
    hard = [f for f in findings if f.severity == "blocking"]
    soft = [f"{f.item}: {f.message}" for f in findings if f.severity == "warning"]
    verdict = Verdict(
        satisfied=not hard, status_so_far="partial" if hard else "success",
        gaps=[f"{f.item}: {f.message}" for f in hard],
        summary=(f"Deterministic checks passed ({len(warnings)} warnings). Reviewed {len(flags)} flagged texts: "
                 f"{len(hard)} blocking, {len(soft)} warnings. " + " ".join([*warnings, *soft][:8])).strip())
    return {"structured_response": verdict, "messages": [AIMessage(content=verdict.summary)]}


async def repair(project: str, gaps: list[str], callbacks):
    """Re-plan (deterministic, cheap) and rewrite the plan's text with the findings; stop if nothing changes."""
    previous = _previous(project)
    volatile = {"plan_id": True, "version": True, "generated_at": True, "solver": {"wall_time_s"}}
    content = previous.model_dump(mode="json", exclude=volatile) if previous else None
    attempt = _digest({"gaps": sorted(gaps), "plan": content})     # content, not the version/timestamp
    if _load(project, "repairs", attempt + ".json"):
        raise files.ProjectError("the same findings remain after a repair; the plan is kept for the Scrum Master")
    result = await generate(project, "", callbacks, findings=gaps)
    _save(project, {"gaps": gaps}, "repairs", attempt + ".json")
    return result
