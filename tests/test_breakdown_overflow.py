import asyncio
import copy
import json
from types import SimpleNamespace
import pytest
from pydantic import BaseModel
from agent_engine.phase4.paged_operation import Workspace, encode
from agent_engine.phase4 import breakdown_workflow as workflow, files, backlog, speckit
from agent_engine.phase4.review_batches import batches, size
from agent_engine.phase4.feature_documents import FeatureDocument, write
from agent_engine.phase4.contracts import Backlog
from test_phase4_pipeline import proj, P, _features, _enrich
from test_task_breakdown_documents import document


class LargeOutput(BaseModel):
    text: str
    records: list[dict]


def test_overflow_keeps_every_input_and_output_byte_and_resumes():
    payload = {'source': '界abc' * 20000, 'constraints': ['must retain this']}
    saved = []
    w = Workspace(LargeOutput, payload, page_chars=311, persist=lambda s: saved.append(copy.deepcopy(s)))
    assert ''.join(w.read(i) for i in range(len(w.pages))) == encode(payload)
    w.edit([], {'text': '', 'records': []}, 'set')
    for i in range(100):
        w.edit(['text'], 'content' * 100, 'append_text')
        w.edit(['records'], {'id': i}, 'append')
    resumed = Workspace(LargeOutput, payload, page_chars=311, saved=saved[-1])
    result = resumed.finish()
    assert result.text == 'content' * 10000
    assert result.records == [{'id': i} for i in range(100)]


def test_overflow_cannot_complete_unread_pages_or_invalid_schema():
    w = Workspace(LargeOutput, {'text': 'x' * 4000}, page_chars=100)
    w.edit([], {'text': 'done', 'records': []}, 'set')
    w.read(0)
    with pytest.raises(ValueError, match='unread'):
        w.finish()
    for i in range(len(w.pages)):
        w.read(i)
    w.edit(['records'], 'invalid', 'set')
    with pytest.raises(ValueError):
        w.finish()


def test_paged_tool_execution_assembles_schema(monkeypatch):
    import langchain.agents
    from agent_engine.phase4 import paged_operation
    def create_agent(**kwargs):
        tools = {t.name: t for t in kwargs['tools']}
        async def ainvoke(state, config):
            manifest = json.loads(state['messages'][0][1])
            for i in range(manifest['input_pages']):
                tools['read_input'].invoke({'page': i})
            tools['write_output'].invoke({'path': [], 'value_json': '{"text":"","records":[]}'})
            for _ in range(8):
                tools['write_output'].invoke({'path': ['text'], 'value_json': json.dumps('x'*5000), 'mode': 'append_text'})
            assert tools['complete_output'].invoke({}) == 'COMPLETE'
            return {'messages': []}
        return SimpleNamespace(ainvoke=ainvoke)
    monkeypatch.setattr(langchain.agents, 'create_agent', create_agent)
    # Middleware construction needs a chat model but the graph is controlled.
    from langchain_core.language_models.fake_chat_models import FakeListChatModel
    model = FakeListChatModel(responses=['unused'])
    result = asyncio.run(paged_operation.run(LargeOutput, 'generate', {'input': 'y'*100000}, [], model, 'test:model', 'rules'))
    assert len(result.text) == 40000


def test_review_batch_reduces_duplicate_evidence_without_losing_obligations():
    evidence = {'architecture.md': [{'start': 0, 'end': 10000, 'text': 'x'*10000, 'sha256': 'shared'}]}
    jobs = [('requirement', [f'FR-{i}'], {'sources': evidence, 'requirement': f'FR-{i}'}) for i in range(8)]
    grouped = list(batches(jobs, 64000))
    assert len(grouped) == 1
    assert set(grouped[0][1]) == {f'FR-{i}' for i in range(8)}
    assert sum(size(j[2]) for j in grouped) < sum(size(j[2]) for j in jobs) / 3
    assert grouped[0][2]['sources'] == evidence
    assert len(grouped[0][2]['parts']) == 8


def test_retained_partial_item_gets_missing_field_without_overwrite(proj):
    backlog.set_features(P, _features()); backlog.build(P); _enrich(P)
    retained = backlog._load_enrichments(P)
    raw = files.read_json(P, files.BACKLOG)
    task = next(i for i in raw['items'] if i['level'] == 'task')
    task['acceptance_criteria'] = []
    files.write_json(P, files.BACKLOG, raw)
    patch = {'item_id': task['item_id'], 'acceptance_criteria': ['WHEN saved THE SYSTEM SHALL retain it'],
             'ai_eligible': True, 'ai_eligibility_reason': 'overwrite'}
    selected = workflow.missing_fields(P, [patch], retained)
    assert selected == [{'item_id': task['item_id'], 'acceptance_criteria': patch['acceptance_criteria']}]


def setup_two_stories():
    d = document()
    second = copy.deepcopy(d['stories'][0]); second.update(number=2, title='Other work', source_ids=['FR-002'])
    d['stories'].append(second)
    d['phases'].append({'kind':'user_story', 'story_number':2, 'tasks':[
        {'task_id':'T003','description':'Other task','file_paths':['src/other.py']}]})
    return d


def test_structural_repair_retains_unaffected_story_and_enrichment(proj, monkeypatch):
    speckit.init(P); backlog.set_features(P, _features())
    d = setup_two_stories()
    write(P, _features()[0]['feature_dir'], d)
    backlog.build(P); _enrich(P); backlog.validate(P)
    before = files.read_json(P, files.BACKLOG, Backlog).by_id()['S-001-US2'].model_dump()
    async def fake(schema, purpose, payload, callbacks):
        changed = copy.deepcopy(d)
        changed['stories'][0]['title'] = 'Corrected story'
        changed['stories'][1]['title'] = 'Unrequested change'
        return workflow.Generated(document=FeatureDocument.model_validate(changed), patches=[])
    monkeypatch.setattr(workflow, '_call', fake)
    asyncio.run(workflow.repair(P, [json.dumps({'rule':'story_size','item_ids':['S-001-US1'],'message':'split'})], []))
    after = files.read_json(P, files.BACKLOG, Backlog).by_id()['S-001-US2'].model_dump()
    assert after == before


def test_structural_failure_rolls_back_existing_outputs(proj, monkeypatch):
    from agent_engine.history import fingerprint
    speckit.init(P); backlog.set_features(P, _features())
    d = setup_two_stories(); write(P, _features()[0]['feature_dir'], d)
    backlog.build(P); _enrich(P); backlog.validate(P)
    before = fingerprint(proj)
    async def fake(*args):
        changed = copy.deepcopy(d); changed['stories'][0]['title'] = 'Corrected'
        return workflow.Generated(document=FeatureDocument.model_validate(changed), patches=[workflow.Patch(item_id='999-T001', type='docs')])
    monkeypatch.setattr(workflow, '_call', fake)
    with pytest.raises(files.ProjectError, match='outside assigned'):
        asyncio.run(workflow.repair(P, [json.dumps({'rule':'story_size','item_ids':['S-001-US1'],'message':'split'})], []))
    assert fingerprint(proj) == before


def test_operation_uses_pack_selected_model(monkeypatch):
    monkeypatch.setattr(workflow, 'model_spec', lambda tier: 'test:' + tier)
    with workflow.operation_model(SimpleNamespace(name='task-breakdown/validator', models=['fast','strong']), 0):
        assert workflow.operation_identity(True)['model'] == 'test:fast'
    with workflow.operation_model(SimpleNamespace(name='task-breakdown/validator', models=['fast','strong']), 1):
        assert workflow.operation_identity(True)['model'] == 'test:strong'


def test_source_snapshot_rejects_change_during_review(proj, monkeypatch):
    backlog.set_features(P, _features()); backlog.build(P)
    monkeypatch.setattr(workflow, 'model_spec', lambda tier: 'test:model')
    async def fake(schema, purpose, payload, callbacks):
        path = files.path(P, files.PRD)
        path.write_text(path.read_text() + '\nChanged while reviewing')
        return workflow.Review(reviewed_ids=payload['required_review_ids'], complete=True, findings=[])
    monkeypatch.setattr(workflow, '_call', fake)
    with pytest.raises(files.ProjectError, match='source inputs changed'):
        asyncio.run(workflow.review(P, []))


@pytest.mark.parametrize('oversized', [True, False])
def test_large_input_or_output_automatically_uses_paged_execution(monkeypatch, oversized):
    from langchain_core.exceptions import OutputParserException
    from agent_engine.phase4 import paged_operation
    monkeypatch.setattr(workflow, 'operation_identity', lambda *a: {'model':'test:model', 'prompt':'Review faithfully'})
    monkeypatch.setenv('AGENT_ENGINE_BREAKDOWN_JOB_MAX_CHARS', '1000')
    class Model:
        max_tokens = 16000
        def with_structured_output(self, schema, **kwargs):
            async def ainvoke(*args, **kwargs):
                raise OutputParserException('response exceeded complete schema representation')
            return SimpleNamespace(ainvoke=ainvoke)
    monkeypatch.setattr(workflow, 'resolve_model_with_retries', lambda spec: Model())
    calls = []
    async def paged(schema, purpose, payload, callbacks, model, spec, rules):
        calls.append(payload)
        return LargeOutput(text='complete', records=[])
    monkeypatch.setattr(paged_operation, 'run', paged)
    payload = {'source': 'x' * (10000 if oversized else 10)}
    result = asyncio.run(workflow._call(LargeOutput, 'generate', payload, []))
    assert result.text == 'complete' and calls == [payload]
