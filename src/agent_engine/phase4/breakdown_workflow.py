"""Application-controlled Task Breakdown; public artifacts and Verdict stay unchanged.

Each model operation is bounded and typed. Internal receipts are engine-owned,
never approval evidence. Review receipts survive repairs and serialization errors.
"""
from __future__ import annotations
import asyncio
import json
import os
import contextvars
from contextlib import contextmanager
from typing import Literal
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from langchain_core.messages import AIMessage
from agent_engine import config
from agent_engine.agent import Verdict, model_spec
from agent_engine.model_setup import resolve_model_with_retries
from agent_engine.runtime import atomic_json
from agent_engine.stage_controls import active_stage_budget, StageBudgetExceeded
from agent_engine.phase4 import files, backlog, speckit, feature_jobs
from agent_engine.phase4.contracts import FeatureList, Backlog, ProjectSettings, Estimate, UserStory
from agent_engine.phase4.feature_documents import FeatureDocument, write as write_feature
from agent_engine.phase4.evidence import packet, digest, source_text
from agent_engine.phase4.breakdown_state import frozen_operation, artifact_transaction, freeze_contract


class Record(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Finding(Record):
    rule: str
    item_ids: list[str]
    field: str
    message: str
    source_refs: list[str] = Field(default_factory=list)
    severity: Literal['blocking', 'warning'] = 'blocking'


class DependencyPatch(Record):
    on_id: str
    reason: str
    confidence: float = Field(ge=0, le=1)


class SplitPart(Record):
    title: str
    description: str
    acceptance_criteria: list[str]
    hours: float = Field(gt=0)


class Patch(Record):
    item_id: str
    description_md: str | None = None
    priority: Literal['P1', 'P2', 'P3'] | None = None
    moscow: Literal['must', 'should', 'could', 'wont'] | None = None
    file_paths: list[str] | None = None
    components: list[str] | None = None
    repo: str | None = None
    definition_of_done: list[str] | None = None
    add_dependencies: list[DependencyPatch] | None = None
    remove_dependencies: list[str] | None = None
    split_into: list[SplitPart] | None = None
    acceptance_criteria: list[str] | None = None
    user_story: UserStory | None = None
    estimate: Estimate | None = None
    skills_required: list[str] | None = None
    type: Literal['feature', 'test', 'infra', 'ui', 'chore', 'spike', 'docs'] | None = None
    ai_eligible: bool | None = None
    ai_eligibility_reason: str | None = None
    open_questions: list[str] | None = None
    task_shares: dict[str, float] | None = None
    source_ids: list[str] | None = None


class Generated(Record):
    document: FeatureDocument
    patches: list[Patch]


class Plan(Record):
    features: FeatureList
    implementation_contract: str


class Review(Record):
    reviewed_ids: list[str]
    complete: bool
    findings: list[Finding]


class Repairs(Record):
    patches: list[Patch]


class Edge(Record):
    item_id: str
    on_id: str
    reason: str
    confidence: float = Field(ge=0, le=1)


class Dependencies(Record):
    edges: list[Edge]


RULES = '''Check source fidelity and actual requirement implementation, omitted behavior,
contradictions, testable acceptance criteria, source-backed priorities, plausible relative estimates,
concrete task scope, architecture compatibility, unsafe AI eligibility, unanswered decisions,
shared foundation ownership and duplicate work. Proposals are not approved requirements.
Never invent product facts, numbers, paths, roles or deadlines. Include applicable edge/error cases.
Independent semantic review is mandatory; format validity is not semantic correctness.'''


def _positive(name, default):
    value = int(os.environ.get(name, default))
    if value <= 0:
        raise ValueError(f'{name} must be positive')
    return value


def _path(project, kind, key):
    root = files.project_dir(project)
    path = root / '.engine-breakdown' / kind / (key + '.json')
    if any(p.is_symlink() for p in (path, *path.parents) if p != root.parent) or not path.resolve().is_relative_to(root.resolve()):
        raise files.ProjectError('invalid workflow receipt path')
    return path


def _load(project, kind, key):
    path = _path(project, kind, key)
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, ValueError):
        return None


def _save(project, kind, key, value):
    budget = active_stage_budget.get()
    if budget:
        budget.check()
    atomic_json(_path(project, kind, key), value)


_active_model = contextvars.ContextVar('breakdown_operation_model', default=None)
_active_request = contextvars.ContextVar('breakdown_original_request', default='')


@contextmanager
def operation_model(pack, level, request=""):
    request_token = _active_request.set(request)
    token = _active_model.set((pack.name, pack.models[level]))
    try:
        yield
    finally:
        _active_model.reset(token)
        _active_request.reset(request_token)


def operation_identity(review=False):
    from agent_engine.agent import load_pack
    name, tier = _active_model.get() or ('task-breakdown/validator' if review else 'task-breakdown', 'strong')
    pack = load_pack(name)
    return {'model': model_spec(tier), 'prompt': pack.system_prompt}


def check_allocation(purpose):
    budget = active_stage_budget.get()
    if budget:
        budget.check()
        reserve = float(os.environ.get('AGENT_ENGINE_BREAKDOWN_REVIEW_RESERVE', '.2'))
        if not 0 < reserve < 1:
            raise ValueError('review reserve must be between zero and one')
        if not purpose.startswith('Independently review') and (
            budget.calls >= budget.max_calls * (1-reserve) or
            budget.output_tokens >= budget.max_output_tokens * (1-reserve) or
            budget.input_tokens >= budget.max_input_tokens * (1-reserve)):
            raise StageBudgetExceeded('generation/repair allocation exhausted; review reserve retained')


async def _call(schema, purpose, payload, callbacks):
    text = json.dumps(payload, ensure_ascii=False, separators=(',', ':'), default=str)
    identity = operation_identity(purpose.startswith('Independently review'))
    spec = identity['model']
    check_allocation(purpose)
    budget = active_stage_budget.get()
    model = resolve_model_with_retries(spec)
    if hasattr(model, 'max_tokens'):
        model.max_tokens = min(getattr(model, 'max_tokens', None) or 16000, 16000)
    try:
        rules = RULES + '\nRole instructions (file/tool orchestration is supplied by the application):\n' + identity['prompt']
        if len(text) > _positive('AGENT_ENGINE_BREAKDOWN_JOB_MAX_CHARS', 160000):
            from agent_engine.phase4.paged_operation import run
            return await run(schema, purpose, payload, callbacks, model, spec, rules)
        # The provider receives the complete schema. No tool discovery or file
        # navigation loop is used. Callbacks include shared token/call accounting.
        operation = model.with_structured_output(schema, **({'method': 'json_schema'} if spec.startswith('anthropic:') else {}))
        try:
            result = await asyncio.wait_for(operation.ainvoke([
                ('system', rules + '\nOperation: ' + purpose), ('human', text)],
                config={'callbacks': callbacks}), timeout=min(budget.remaining() if budget else 1800, 1800))
            return schema.model_validate(result)
        except Exception as exc:
            # A response/schema limit must split output as well as large inputs.
            # Provider/network errors retain normal escalation/retry semantics.
            from langchain_core.exceptions import OutputParserException
            from pydantic import ValidationError
            if not isinstance(exc, (OutputParserException, ValidationError)) and 'length' not in type(exc).__name__.lower():
                raise
            from agent_engine.phase4.paged_operation import run
            return await run(schema, purpose, payload, callbacks, model, spec, rules)
    finally:
        from agent_engine.agent import close_agent
        from types import SimpleNamespace
        await close_agent(SimpleNamespace(_agent_engine_models=[model]))


def settings(project):
    return backlog.source_settings(ProjectSettings.model_validate_json(source_text(project, files.PROJECT_SETTINGS)))


def generation_supported(project):
    """Preserve legacy/custom project semantics via the existing writer."""
    root = files.project_dir(project)
    from agent_engine.phase4.speckit import ASSETS, TEMPLATE_NAMES
    if any((root / '.specify/templates' / f'{n}.md').exists() and
           (root / '.specify/templates' / f'{n}.md').read_bytes() != (ASSETS / 'templates' / f'{n}.md').read_bytes()
           for n in TEMPLATE_NAMES):
        return False
    if files.exists(project, files.FEATURES):
        from agent_engine.phase4.planning_records import read_feature
        for f in files.read_json(project, files.FEATURES, FeatureList).features:
            if (root / f.feature_dir / 'spec.md').exists() and read_feature(project, f.feature_dir) is None:
                return False
    return True


@frozen_operation
async def generate(project, request, callbacks):
    sources = packet(project)
    existing = files.read_json(project, files.FEATURES) if files.exists(project, files.FEATURES) else None
    plan_sources = {k: v for k, v in sources.items() if k != 'backlog/implementation-contract.md'}
    if 'requests/task-breakdown.md' in plan_sources:
        plan_sources['requests/task-breakdown.md'] = feature_jobs._requests(files.project_dir(project))
    contract_identity = files.file_sha(project, 'backlog/implementation-contract.md') if files.exists(project, 'backlog/implementation-contract.md') else None
    planner_identity = {'schema': Plan.model_json_schema(), 'implementation': Path(__file__).read_text(),
                        'model': operation_identity()}
    def plan_identity(features):
        return digest({'sources': plan_sources, 'settings': settings(project), 'request': request,
                       'existing': features, 'planner': planner_identity, 'contract': contract_identity})
    plan_key = plan_identity(existing)
    saved = _load(project, 'plans', plan_key)
    plan = Plan.model_validate(saved) if saved else await _call(Plan,
        'Group every requirement into valuable features; retain existing IDs/directories. '
        'Return a shared implementation contract citing source-backed roots/interfaces and foundation owners. '
        'Unspecified choices remain proposals/open questions.',
        {'sources': sources, 'settings': settings(project), 'existing': existing, 'request': request}, callbacks)
    _save(project, 'plans', plan_key, plan.model_dump(mode='json'))
    if existing:
        old = {f['feature_key']: f['feature_dir'] for f in existing['features']}
        if any(old.get(f.feature_key, f.feature_dir) != f.feature_dir for f in plan.features.features) or not set(old) <= {f.feature_key for f in plan.features.features}:
            raise files.ProjectError('feature plan changed existing identity; manual reconciliation required')
    response = json.loads(backlog.set_features(project, [f.model_dump() for f in plan.features.features]))
    if response['not_yet_covered']:
        raise files.ProjectError('feature partition omitted requirements: ' + ', '.join(response['not_yet_covered']))
    # set_features checks valid IDs and reports uncovered IDs; build validation is
    # authoritative before independent review.
    contract = 'backlog/implementation-contract.md'
    if not files.exists(project, contract) or files.read_text(project, contract) != plan.implementation_contract:
        files.write_text(project, contract, plan.implementation_contract)
    # Store the post-registration identity too: registering features and writing
    # the derived contract must not invalidate an otherwise unchanged plan.
    contract_identity = files.file_sha(project, contract)
    freeze_contract(project)
    _save(project, 'plans', plan_identity(plan.features.model_dump(mode='json')), plan.model_dump(mode='json'))
    concurrency = _positive('AGENT_ENGINE_HELPER_CONCURRENCY', 9)
    if concurrency > 32:
        raise ValueError('AGENT_ENGINE_HELPER_CONCURRENCY must be between 1 and 32')
    semaphore = asyncio.Semaphore(concurrency)
    async def feature(f):
        async with semaphore:
            status = feature_jobs.status(project, f.feature_dir)
            evidence = packet(project, f.requirement_ids)
            identity = digest({'feature': f.model_dump(), 'inputs': status['input_sha256'], 'settings': settings(project),
                               'schema': Generated.model_json_schema(), 'model': operation_identity(),
                               'history': history_evidence(project, f)})
            saved = _load(project, 'generation', identity)
            if status['reusable'] and saved and saved.get('outputs') == feature_jobs.outputs(project, f.feature_dir):
                return saved['patches']
            from agent_engine.stage_controls import helper_scope, HelperScope
            budget = active_stage_budget.get()
            if budget:
                budget.begin_helper(identity)
            scope_token = helper_scope.set(HelperScope('speckit-feature', project, feature_directory=f.feature_dir))
            try:
                n = f.feature_dir.split('/')[1][:3]
                generated = await _call(Generated,
                    'Generate ONE complete feature and enrichment patches. Story IDs are S-' + n + '-US<number>; '
                    'task IDs are ' + n + '-Tnnn. Setup/foundational/polish IDs are S-SETUP/FOUND/POLISH-' + n + '. '
                    'Include patches for every story estimate and every task acceptance criteria, skill tags and AI reason. '
                    'Story estimates use the project scale; task hours derive from story task_shares. '
                    'Use method llm/low confidence when no valid historical analogy exists. '
                    'Preserve existing feature IDs, scenarios, contracts and unresolved decisions. '
                    'Only newly owned work belongs here; shared prerequisites reuse their owner.',
                    {'feature': f.model_dump(), 'sources': evidence, 'settings': settings(project),
                     'existing_document': files.read_json(project, f.feature_dir + '/feature.json') if files.exists(project, f.feature_dir + '/feature.json') else None,
                     'history': history_evidence(project, f),
                     'skill_taxonomy': _taxonomy()}, callbacks)
                write_feature(project, f.feature_dir, generated.document.model_dump(mode='json'))
                feature_jobs.checkpoint(project, f.feature_dir, status['input_sha256'])
                value = {'patches': [p.model_dump(mode='json', exclude_none=True) for p in generated.patches],
                         'outputs': feature_jobs.outputs(project, f.feature_dir)}
                _save(project, 'generation', identity, value)
                return value['patches']
            finally:
                helper_scope.reset(scope_token)
                if budget:
                    budget.end_helper()
    tasks = [asyncio.create_task(feature(f)) for f in plan.features.features]
    try:
        patches = await asyncio.gather(*tasks)
    except BaseException:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
    backlog.build(project)
    retained = backlog._load_enrichments(project)
    for f, updates in zip(plan.features.features, patches):
        n = f.feature_dir.split('/')[1][:3]
        b = files.read_json(project, files.BACKLOG, Backlog)
        children = {i.item_id for i in b.items if i.parent_id == 'E-' + n}
        allowed = children | {i.item_id for i in b.items if i.parent_id in children}
        if any(p['item_id'] not in allowed for p in updates):
            raise files.ProjectError('generation patch outside assigned feature')
        _apply(project, missing_fields(project, updates, retained))
    b = files.read_json(project, files.BACKLOG, Backlog)
    index = [i.model_dump(mode='json') for i in b.stories()]
    dependency_payload = {'stories': index, 'sources': packet(project)}
    dependency_key = digest({'payload': dependency_payload, 'model': operation_identity(),
                             'schema': Dependencies.model_json_schema(), 'version': 1})
    cached_edges = _load(project, 'dependencies', dependency_key)
    if cached_edges is not None:
        edges = Dependencies.model_validate(cached_edges)
    else:
        edges = await _call(Dependencies, 'Identify only real cross-feature story prerequisites. '
                        'Uncertain edges below 0.6 are not added.',
                        dependency_payload, callbacks)
        _save(project, 'dependencies', dependency_key, edges.model_dump(mode='json'))
    story_ids = {s.item_id for s in b.stories()}
    if any(e.item_id not in story_ids or e.on_id not in story_ids or e.item_id == e.on_id for e in edges.edges):
        raise files.ProjectError('dependency operation returned invalid story IDs')
    _apply(project, [{'item_id': e.item_id, 'add_dependencies': [{'on_id': e.on_id, 'reason': e.reason, 'confidence': e.confidence}]}
                     for e in edges.edges if e.confidence >= .6])
    check = json.loads(backlog.validate_report(project))
    dependency_payload['stories'] = [i.model_dump(mode='json') for i in files.read_json(project, files.BACKLOG, Backlog).stories()]
    _save(project, 'dependencies', digest({'payload': dependency_payload, 'model': operation_identity(),
          'schema': Dependencies.model_json_schema(), 'version': 1}), edges.model_dump(mode='json'))
    b = files.read_json(project, files.BACKLOG, Backlog)
    summary = (f'Backlog: /outputs/{project}/backlog/backlog.json and backlog/backlog.md. '
               f'{len(b.features)} epics, {check["stories"]} stories, {check["tasks"]} tasks, '
               f'{check["story_points"]} story points. '
               f'{sum(bool(i.open_questions) for i in b.items)} items with open questions; '
               f'{len(check["blocking"])} blocking findings and {len(check["warnings"])} warnings. '
               'Independent review follows.')
    return {'messages': [AIMessage(content=summary)]}


def history_evidence(project, feature):
    """Retrieve exact candidate tickets; feature similarity is not a story estimate."""
    from agent_engine.phase4.contracts import History
    from agent_engine.phase4.textsim import similarities
    raw_history = source_text(project, files.HISTORY)
    history = History.model_validate_json(raw_history) if raw_history is not None else History()
    tickets = [t for t in history.tickets if t.story_points]
    if not tickets:
        return {'analogy_valid': False, 'references': []}
    scores = similarities([feature.title + '\n' + feature.summary], [t.title + '\n' + t.body for t in tickets])[0]
    order = sorted(range(len(tickets)), key=lambda i: -scores[i])[:20]
    selected, values = [], set()
    for i in order:
        if scores[i] > 0 and tickets[i].story_points not in values:
            selected.append(i)
            values.add(tickets[i].story_points)
    selected = (selected + [i for i in order if i not in selected and scores[i] > 0])[:8]
    return {'analogy_valid': len(tickets) >= backlog.MIN_HISTORY and float(max(scores)) >= backlog.MIN_SIMILARITY,
            'references': [tickets[i].model_dump(mode='json') for i in selected],
            'note': 'Candidate feature-level analogies. Compare actual story scope before claiming a reference; otherwise use llm/low confidence.'}


def _taxonomy():
    from agent_engine.phase4 import skills_taxonomy
    return skills_taxonomy.tags()


def missing_fields(project, patches, retained):
    """Preserve valid retained fields while filling missing/invalid required ones."""
    b = files.read_json(project, files.BACKLOG, Backlog)
    by = b.by_id()
    scale = settings(project)['story_point_scale']
    from agent_engine.phase4.skills_taxonomy import tags
    output = []
    for patch in patches:
        iid = patch['item_id']
        item = by[iid]
        old = retained.get(iid, {})
        value = {'item_id': iid}
        for key, supplied in patch.items():
            if key == 'item_id':
                continue
            invalid = (key == 'acceptance_criteria' and not item.acceptance_criteria or
                       key == 'skills_required' and not any(t in tags() for t in item.skills_required) or
                       key == 'estimate' and (not item.estimate or
                           (item.level == 'story' and item.estimate.story_points not in scale) or
                           (item.level == 'task' and not (item.estimate.hours or 0) > 0)))
            if key == 'task_shares' and 'estimate' in old and item.estimate and item.estimate.story_points in scale:
                continue  # preserve established allocations alongside a valid retained estimate
            if key not in old or invalid:
                value[key] = supplied
        if len(value) > 1:
            output.append(value)
    return output


def _apply(project, patches):
    # Stories before tasks: explicit task decisions survive deterministic rollups.
    b = files.read_json(project, files.BACKLOG, Backlog)
    by = b.by_id()
    patches = sorted(patches, key=lambda p: by.get(p['item_id']).level == 'task' if p['item_id'] in by else False)
    if patches:
        result = json.loads(backlog.update(project, patches))
        if result.get('errors'):
            raise files.ProjectError(json.dumps(result['errors']))


@frozen_operation
async def review(project, callbacks):
    from agent_engine.recovery import evaluation
    from agent_engine.agent import load_pack
    evaluator = {**evaluation(load_pack('task-breakdown')), 'resolved_model': operation_identity(True)}
    b = files.read_json(project, files.BACKLOG, Backlog)
    before = digest(b.model_dump(mode='json'))
    jobs = []
    for story in b.stories():
        records = [story, *b.tasks_of(story.item_id)]
        # Partition task payloads, repeating the complete parent story as context.
        for start in range(1, max(2, len(records)), 12):
            rows = [story, *records[start:start+12]]
            jobs.append(('story', [r.item_id for r in rows], {'records': [r.model_dump(mode='json') for r in rows],
                         'sources': packet(project, [r.req_id for r in story.source_refs])}))
    sources = packet(project)
    from agent_engine.phase4.speckit_parse import REQ_ID_RE
    ids = sorted(set(REQ_ID_RE.findall(files.read_text(project, files.PRD))))
    by = b.by_id()
    for rid in ids:
        rows = [s.model_dump(mode='json') for s in b.stories() if any(r.req_id == rid for r in s.source_refs)]
        jobs.append(('requirement', [rid], {'requirement': rid, 'stories': rows, 'sources': packet(project, [rid])}))
    # Cross-feature review has all decisions, interfaces and dependency index.
    contracts = {}
    for f in b.features:
        base = files.path(project, f.feature_dir)
        contracts[f.feature_dir] = {p.relative_to(base).as_posix(): p.read_text() for p in base.rglob('*')
                                   if p.is_file() and (p.name == 'plan.md' or 'contracts' in p.relative_to(base).parts)}
    # Canonical feature decisions need review, but rendering the same stories
    # and tasks into several files does not create additional semantic work.
    from agent_engine.phase4.planning_records import read_feature
    for feature in b.features:
        base = files.path(project, feature.feature_dir)
        if read_feature(project, feature.feature_dir) is not None:
            record = files.read_json(project, feature.feature_dir + '/feature.json')
            decisions = {k: v for k, v in record.items() if k not in {'stories', 'phases'}}
            jobs.append(('feature-decisions', [feature.feature_key], {
                'decisions': decisions, 'sources': packet(project, feature.requirement_ids)}))
            continue
        # Legacy supporting documents can contain decisions absent from backlog.
        for path in sorted(base.rglob('*.md')):
            text = path.read_text()
            relative = path.relative_to(base).as_posix()
            for offset in range(0, len(text), 24000):
                name = f'{feature.feature_dir}/{relative}#{offset}'
                jobs.append(('artifact', [name], {'artifact': name, 'text': text[offset:offset+24000],
                    'sources': packet(project, feature.requirement_ids)}))
    jobs.append(('global', ['cross-feature'], {'sources': sources, 'contracts': contracts,
                 'tasks': [{k: t.model_dump(mode='json')[k] for k in ('item_id','parent_id','title','description_md','file_paths','dependencies','source_refs','acceptance_criteria')} for t in b.items if t.level == 'task'],
                 'stories': [{k: s.model_dump(mode='json')[k] for k in ('item_id','title','source_refs','dependencies','file_paths','open_questions')}
                             for s in b.stories()]}))
    from agent_engine.phase4.review_batches import batches
    jobs = list(batches(jobs, min(_positive('AGENT_ENGINE_BREAKDOWN_JOB_MAX_CHARS', 160000),
                                 _positive('AGENT_ENGINE_BREAKDOWN_REVIEW_BATCH_CHARS', 64000))))
    semaphore = asyncio.Semaphore(_positive('AGENT_ENGINE_BREAKDOWN_REVIEW_CONCURRENCY', 4))
    async def job(kind, ids, payload):
        async with semaphore:
            payload = {**payload, 'settings': settings(project), 'required_review_ids': ids, 'original_request': _active_request.get()}
            key = digest({'payload': payload, 'evaluator': evaluator, 'schema': Review.model_json_schema(), 'kind': kind})
            cached = _load(project, 'reviews', key)
            result = Review.model_validate(cached) if cached else await _call(Review,
                'Independently review ' + kind + '. Return every required_review_id in reviewed_ids only after reviewing it. '
                'For a partition, independently complete EVERY part using its source_refs into the shared exact sources. '
                'Return complete=false if evidence is insufficient. Report actionable findings naming exact affected IDs/fields.', payload, callbacks)
            if not result.complete or set(result.reviewed_ids) != set(ids):
                raise files.ProjectError('semantic review incomplete: ' + ', '.join(ids))
            _save(project, 'reviews', key, result.model_dump(mode='json'))
            return result.findings
    tasks = [asyncio.create_task(job(*j)) for j in jobs]
    try:
        findings = [f for group in await asyncio.gather(*tasks) for f in group]
    except BaseException:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
    if before != digest(files.read_json(project, files.BACKLOG, Backlog).model_dump(mode='json')):
        raise files.ProjectError('backlog changed during semantic review')
    blocking = [f for f in findings if f.severity == 'blocking']
    _save(project, 'findings', 'latest', [f.model_dump(mode='json') for f in findings])
    verdict = Verdict(satisfied=not blocking, status_so_far='partial' if blocking else 'success',
        gaps=[json.dumps(f.model_dump(mode='json'), ensure_ascii=False) for f in blocking],
        summary=f'Completed {len(jobs)} semantic review partitions. {len(blocking)} blocking findings; {len(findings)-len(blocking)} warnings. Findings retained for targeted repair.')
    return {'structured_response': verdict, 'messages': [AIMessage(content=verdict.summary)]}


def protect_unaffected(feature, current, generated, affected, findings=()):
    """Restore unrelated canonical stories/tasks before publishing a structural fix."""
    value = generated.document.model_dump(mode='json')
    prefix = feature.feature_dir.split('/')[1][:3]
    old_stories = {s['number']: s for s in current['stories']}
    changed = {n for n, story in old_stories.items() if 'S-' + prefix + '-US' + str(n) in affected
               or set(story['source_ids']) & affected}
    for phase in current['phases']:
        if any(prefix + '-' + task['task_id'] in affected for task in phase['tasks']):
            changed.add(phase.get('story_number'))
    by_number = {s['number']: s for s in value['stories']}
    for n, story in old_stories.items():
        if n not in changed:
            by_number[n] = story
        elif n not in by_number:
            raise files.ProjectError(f'structural repair removed existing story identity US{n}')
    value['stories'] = sorted(by_number.values(), key=lambda s: s['number'])
    old_phases = {(p['kind'], p.get('story_number')): p for p in current['phases']}
    phases = {(p['kind'], p.get('story_number')): p for p in value['phases']}
    for key, phase in old_phases.items():
        sid = ('S-' + prefix + '-US' + str(key[1])) if key[0] == 'user_story' else 'S-' + {'setup':'SETUP', 'foundational':'FOUND', 'polish':'POLISH'}[key[0]] + '-' + prefix
        if key[1] not in changed and sid not in affected:
            phases[key] = phase
    value['phases'] = list(phases.values())
    # Requirements and decisions outside the identified fix are never removed.
    targeted_fields = {f.get('field', '').split('.')[0].split('/')[0] for f in findings}
    for field in ('requirements', 'decisions', 'entities', 'interfaces', 'edge_cases',
                  'open_questions', 'shared_prerequisites', 'validation_steps', 'success_criteria'):
        if field in targeted_fields:
            continue
        for old in current.get(field, []):
            if old not in value[field]:
                if isinstance(old, dict) and field == 'requirements' and set(old.get('source_ids', [])) & affected:
                    continue
                if isinstance(old, dict):
                    identity = 'number' if field == 'requirements' else 'topic' if field == 'decisions' else 'name'
                    value[field] = [entry for entry in value[field] if entry.get(identity) != old.get(identity)]
                value[field].append(old)
    generated.document = FeatureDocument.model_validate(value)
    allowed = {'S-' + prefix + '-US' + str(n) for n in changed if n is not None} | affected
    allowed |= {prefix + '-' + t['task_id'] for p in value['phases'] if p.get('story_number') in changed for t in p['tasks']}
    # Ignore attempts to alter valid unrelated enrichment; missing fields can be
    # filled later through deterministic findings without changing valid records.
    generated.patches = [p for p in generated.patches if p.item_id in allowed or p.item_id not in {
        'S-' + prefix + '-US' + str(n) for n in old_stories} | {
        prefix + '-' + t['task_id'] for phase in current['phases'] for t in phase['tasks']}]
    return generated


@frozen_operation
async def repair(project, gaps, callbacks):
    b = files.read_json(project, files.BACKLOG, Backlog)
    normalized = sorted(gaps)
    identity = digest({'gaps': normalized, 'items': [i.model_dump(mode='json') for i in b.items], 'sources': b.sources})
    if _load(project, 'repairs', identity):
        raise files.ProjectError('unchanged repair findings and artifacts; partial work retained')
    findings = []
    for gap in gaps:
        try:
            findings.append(json.loads(gap))
        except ValueError:
            findings.append({'message': gap, 'item_ids': []})
    ids = {i for f in findings for i in f.get('item_ids', [])}
    # Requirement findings route to their implementing records, retaining the
    # original requirement IDs in the finding. Structural feature repairs remain
    # separate from field patches.
    for story in b.stories():
        if any(r.req_id in ids for r in story.source_refs):
            ids.add(story.item_id)
    rows = [i for i in b.items if i.item_id in ids or i.parent_id in ids]
    structural = not rows or any(f.get('rule') in {'coverage', 'story_size', 'stale_sources'} for f in findings)
    if structural:
        features = [f for f in b.features if set(f.requirement_ids) & ids or any(
            i.item_id in ids and (i.speckit_ref or '').startswith(f.feature_dir + '/') for i in b.items)]
        if not features:
            raise files.ProjectError('cannot safely identify structural repair owner; partial artifacts retained: ' + json.dumps(findings))
        from agent_engine.phase4.planning_records import read_feature
        with artifact_transaction(project, ['backlog', *[f.feature_dir for f in features]]):
            generated_patches = []
            previous_enrichment = backlog._load_enrichments(project)
            project_settings = files.read_json(project, files.PROJECT_SETTINGS, ProjectSettings)
            old_base = {i.item_id: i.model_dump(mode='json') for f in features
                        for i in backlog._feature_items(project, f, project_settings)}
            for feature in features:
                if read_feature(project, feature.feature_dir) is None:
                    raise files.ProjectError('legacy/custom feature needs its original writer for structural repair')
                status = feature_jobs.status(project, feature.feature_dir)
                current = files.read_json(project, feature.feature_dir + '/feature.json')
                n = feature.feature_dir.split('/')[1][:3]
                generated = await _call(Generated, 'Repair the named feature structural findings. '
                    'Preserve all unaffected stories, requirements, task IDs, contracts and unresolved decisions. '
                    'Story IDs use S-' + n + '-US<number> and task IDs ' + n + '-Tnnn. '
                    'Supply complete enrichment patches for changed records.',
                    {'feature': feature.model_dump(), 'existing_document': current, 'findings': findings,
                     'sources': packet(project, feature.requirement_ids), 'settings': settings(project)}, callbacks)
                generated = protect_unaffected(feature, current, generated, ids, findings)
                write_feature(project, feature.feature_dir, generated.document.model_dump(mode='json'))
                feature_jobs.checkpoint(project, feature.feature_dir, status['input_sha256'])
                allowed_prefixes = ('S-' + n + '-US', n + '-T')
                allowed_special = {'S-' + phase + '-' + n for phase in ('SETUP', 'FOUND', 'POLISH')}
                if any(not p.item_id.startswith(allowed_prefixes) and p.item_id not in allowed_special for p in generated.patches):
                    raise files.ProjectError('structural repair patch outside assigned feature')
                generated_patches.extend(p.model_dump(mode='json', exclude_none=True) for p in generated.patches)
            new_base = {i.item_id: i.model_dump(mode='json') for f in features
                        for i in backlog._feature_items(project, f, project_settings)}
            preserved = {}
            for iid, entry in previous_enrichment.items():
                if iid not in old_base or old_base[iid] != new_base.get(iid):
                    continue
                parent = old_base[iid].get('parent_id')
                if parent in old_base and old_base[parent] != new_base.get(parent):
                    continue
                preserved[iid] = {k: v for k, v in entry.items() if not k.startswith('_')}
            backlog.build(project)
            _apply(project, [{'item_id': iid, **entry} for iid, entry in preserved.items()])
            _apply(project, missing_fields(project, generated_patches, preserved))
            backlog.validate_report(project)
            _save(project, 'repairs', identity, {'attempted': True})
            return {'messages': [AIMessage(content='Affected feature structure repaired; independent review follows.')]}

    result = await _call(Repairs, 'Repair only the structured findings, preserving unaffected values and IDs. '
                         'Return patches only for affected items. Never resolve unanswered product decisions by inventing facts.',
                         {'findings': findings, 'records': [i.model_dump(mode='json') for i in rows],
                          'sources': packet(project, [r.req_id for i in rows for r in i.source_refs]),
                          'settings': settings(project)}, callbacks)
    allowed = {i.item_id for i in rows}
    if any(p.item_id not in allowed for p in result.patches):
        raise files.ProjectError('repair patch outside affected partition')
    with artifact_transaction(project, ['backlog']):
        _apply(project, [p.model_dump(mode='json', exclude_none=True) for p in result.patches])
        backlog.validate_report(project)
    _save(project, 'repairs', identity, {'attempted': True})
    after = files.read_json(project, files.BACKLOG, Backlog)
    if digest([i.model_dump(mode='json') for i in b.items]) == digest([i.model_dump(mode='json') for i in after.items]):
        raise files.ProjectError('repair made no progress; partial work retained')
    return {'messages': [AIMessage(content='Targeted backlog repairs completed; independent review follows.')]}
