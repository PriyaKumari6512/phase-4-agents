"""Code-driven Work Allocation: checked AI judgement; deterministic assignment and explanations."""
from __future__ import annotations

import hashlib
import json
import re
from contextlib import contextmanager
from contextvars import ContextVar

from langchain_core.messages import AIMessage
from pydantic import BaseModel, ConfigDict
from agent_engine.phase4 import allocation, files
from agent_engine.phase4.contracts import AssignmentPlan
from agent_engine.phase4.structured import invoke as _invoke

_tier = ContextVar('allocation_tier', default='fast')

class Record(BaseModel):
    model_config = ConfigDict(extra='forbid')

class CandidateVerdict(Record):
    task_id: str
    eligible: bool
    reason: str

class Judgement(Record):
    verdicts: list[CandidateVerdict]

class Decisions(Record):
    pins: dict[str, str]
    vetoes: dict[str, list[str]]
    block_ai: list[str]
    clear_pins: list[str]
    clear_vetoes: list[str]
    unblock_ai: list[str]

class Finding(Record):
    task_id: str
    blocking: bool
    message: str

class LightReview(Record):
    findings: list[Finding]

@contextmanager
def operation_model(pack, level):
    token = _tier.set(pack.models[level])
    try:
        yield
    finally:
        _tier.reset(token)

async def _call(project, schema, rules, payload, callbacks, check):
    from agent_engine.agent import model_spec
    spec = model_spec(_tier.get())
    identity = hashlib.sha256(json.dumps([schema.model_json_schema(), rules, payload, spec], sort_keys=True).encode()).hexdigest()
    rel = f'.engine-work-allocation/{identity}.json'
    if files.exists(project, rel):
        result = schema.model_validate(files.read_json(project, rel))
        if not check(result):
            return result
    errors = []
    for _ in range(2):
        result = await _invoke(schema, rules, json.dumps({'input': payload, 'errors': errors}), callbacks, spec)
        errors = check(result)
        if not errors:
            from agent_engine.runtime import atomic_json
            target = files.path(project, rel)
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_json(target, result.model_dump(mode="json"))
            return result
    raise files.ProjectError('; '.join(errors))

def _previous(project):
    return files.read_json(project, files.ASSIGNMENTS, AssignmentPlan) if files.exists(project, files.ASSIGNMENTS) else None

async def generate(project, request, callbacks=None, findings=None):
    from agent_engine.agent import load_pack
    previous = _previous(project)
    match = re.fullmatch(r'Assign sprint (\d+)\.', request.strip())
    index = int(match[1]) if match else (previous.sprint_index if previous else 1)
    settings, plan, backlog, slot, tasks = allocation._ctx(project, index)
    task_ids = {t.item_id for t in tasks}
    worker_ids = {m.member_id for m in settings.team} | {a.agent_id for a in settings.ai_agents if a.enabled}
    pins = dict(previous.pins) if previous and previous.sprint_index == index else {}
    vetoes = dict(previous.vetoes) if previous and previous.sprint_index == index else {}
    blocked = set(previous.block_ai) if previous and previous.sprint_index == index else set()
    if request.strip() and not match:
        def checked(d):
            errors = []
            if (set(d.pins) | set(d.vetoes) | set(d.block_ai) | set(d.clear_pins) | set(d.clear_vetoes) | set(d.unblock_ai)) - task_ids:
                errors.append('Decisions must name tasks in the chosen sprint')
            if (set(d.pins.values()) | {w for ws in d.vetoes.values() for w in ws}) - worker_ids:
                errors.append('Decisions must name real enabled workers')
            return errors
        d = await _call(project, Decisions, 'Translate reviewer feedback into pins, vetoes and AI blocks. Return only explicit requested changes. Use empty collections otherwise.',
                        {'request': request, 'tasks': sorted(task_ids), 'workers': sorted(worker_ids)}, callbacks, checked)
        for key in d.clear_pins:
            pins.pop(key, None)
        for key in d.clear_vetoes:
            vetoes.pop(key, None)
        pins.update(d.pins)
        vetoes.update(d.vetoes)
        blocked.difference_update(d.unblock_ai)
        blocked.update(d.block_ai)
    prepared = json.loads(allocation.prepare(project, index))
    candidates = [c for c in prepared['ai_candidates'] if c['task_id'] not in blocked]
    verdicts = {}
    if candidates:
        ids = {c['task_id'] for c in candidates}
        def checked(result):
            got = [v.task_id for v in result.verdicts]
            errors = []
            if set(got) != ids or len(got) != len(ids):
                errors.append('Return exactly one verdict per candidate; no other task IDs')
            if any(len(v.reason.strip()) < 15 or v.reason.strip().lower() in ('looks simple', 'simple task') for v in result.verdicts):
                errors.append('Give a specific reason referencing task scope or acceptance criteria')
            return errors
        result = await _call(project, Judgement, load_pack('work-allocation').system_prompt,
                             {'candidates': candidates, 'findings': findings or []}, callbacks, checked)
        verdicts = {v.task_id: {'eligible': v.eligible, 'reason': v.reason} for v in result.verdicts}
    allocation.solve(project, index, verdicts, pins, vetoes, sorted(blocked))
    ap = _previous(project)
    names = {w['worker_id']: w['name'] for w in ap.workers}
    explanations = {}
    for a in ap.assignments:
        score = a.score_breakdown
        text = f"{names[a.worker_id]} meets the required skills (fit {score['skill_fit']:.0%}); ownership evidence {score['ownership']:.0%}, planned load {score['load_after']:.0%}."
        if a.pinned:
            text = 'Pinned by the approver. ' + text
        if a.runner_up_worker_id:
            text += f" Alternative with remaining capacity: {names[a.runner_up_worker_id]}."
        explanations[a.task_id] = text
    allocation.annotate(project, explanations)
    return {'messages': [AIMessage(content='Assignment plan ready for Engineering Manager review.')]}

async def review(project, callbacks=None):
    from agent_engine.agent import Verdict, load_pack
    checked = json.loads(allocation.check(project))
    problems = checked['problems']
    ap = _previous(project)
    flags = {tid: v.model_dump() for tid, v in ap.eligibility.items()
             if (v.eligible or v.shadow) and (len(v.reason.strip()) < 15 or 'looks simple' in v.reason.lower())}
    if not problems and flags:
        def valid(r):
            return ['Review names an unflagged task'] if any(f.task_id not in flags for f in r.findings) else []
        result = await _call(project, LightReview, load_pack('work-allocation/validator').system_prompt, flags, callbacks, valid)
        problems.extend(f'{f.task_id}: {f.message}' for f in result.findings if f.blocking)
    verdict = Verdict(satisfied=not problems, status_so_far='partial' if problems else 'success',
                      gaps=problems, summary='; '.join(problems or ['Deterministic assignment checks passed', *checked['warnings']]))
    return {'structured_response': verdict, 'messages': [AIMessage(content=verdict.summary)]}

async def repair(project, gaps, callbacks=None):
    before = _previous(project)
    def content(ap):
        return ap.model_dump(exclude={'version', 'generated_at', 'solver_score'})
    result = await generate(project, '', callbacks, gaps)
    if content(before) == content(_previous(project)):
        raise files.ProjectError('Repair changed no assignment content; Engineering Manager decision required')
    return result
