"""Planning/review compatibility and failure boundaries without model services."""
import asyncio
import json
import pytest
from agent_engine.phase4 import backlog, files, tools, speckit
from agent_engine.phase4 import breakdown_workflow as workflow
from agent_engine.phase4.contracts import Backlog, ProjectSettings
from agent_engine.phase4.feature_documents import write, FeatureDocument
from agent_engine.phase4.planning_records import read_feature
from agent_engine.phase4.evidence import packet
from test_phase4_pipeline import proj, P, _features, _enrich
from test_task_breakdown_documents import document


def test_direct_record_matches_legacy_public_items(proj, monkeypatch):
    speckit.init(P)
    f = _features()[0]
    write(P, f['feature_dir'], document())
    from agent_engine.phase4.contracts import Feature
    feature = Feature.model_validate(f)
    settings = files.read_json(P, files.PROJECT_SETTINGS, ProjectSettings)
    direct = backlog._feature_items(P, feature, settings)
    import agent_engine.phase4.planning_records as records
    monkeypatch.setattr(records, 'read_feature', lambda *args: None)
    legacy = backlog._feature_items(P, feature, settings)
    assert [i.model_dump() for i in direct] == [i.model_dump() for i in legacy]


def test_external_edit_uses_legacy_import(proj):
    speckit.init(P)
    directory = _features()[0]['feature_dir']
    write(P, directory, document())
    assert read_feature(P, directory)
    path = files.path(P, directory + '/spec.md')
    path.write_text(path.read_text() + '\nAccepted manual addition\n')
    assert read_feature(P, directory) is None
    assert not workflow.generation_supported(P) if files.exists(P, files.FEATURES) else True


def test_scoped_pagination_ignores_other_epic_changes(proj):
    backlog.set_features(P, _features())
    backlog.build(P)
    first = json.loads(tools.backlog_view.invoke({'project': P, 'epic_id': 'E-001', 'limit': 1}))
    raw = files.read_json(P, files.BACKLOG)
    raw['version'] += 1  # unrelated metadata is outside the selected records
    files.write_json(P, files.BACKLOG, raw)
    page = tools.backlog_view.invoke({'project': P, 'epic_id': 'E-001', 'offset': 1,
                                     'expected_sha256': first['backlog_sha256']})
    assert 'ERROR:' not in page
    raw['items'][1]['title'] += ' changed'
    files.write_json(P, files.BACKLOG, raw)
    assert 'changed' in tools.backlog_view.invoke({'project': P, 'epic_id': 'E-001',
                                                  'expected_sha256': first['backlog_sha256']})


def test_evidence_keeps_global_and_exact_relevant_sections(proj):
    files.path(P, files.PRD).write_text('# Global\nRoles apply everywhere\n## FR-001\nSave a bookmark\n## FR-002\nDelete a bookmark\n## NFR-001\nEncrypt data\n')
    text = '\n'.join(s['text'] for s in packet(P, ['FR-001'])[files.PRD])
    assert 'Save a bookmark' in text and 'Roles apply' in text and 'Encrypt data' in text
    assert 'Delete a bookmark' not in text


def test_review_is_complete_cached_and_internal(proj, monkeypatch):
    backlog.set_features(P, _features()); backlog.build(P); _enrich(P); backlog.validate(P)
    monkeypatch.setattr(workflow, 'model_spec', lambda tier: 'test:model')
    calls = []
    async def fake(schema, purpose, payload, callbacks):
        calls.append(payload['required_review_ids'])
        return workflow.Review(reviewed_ids=payload['required_review_ids'], complete=True, findings=[])
    monkeypatch.setattr(workflow, '_call', fake)
    before = files.path(P, files.BACKLOG).read_bytes()
    result = asyncio.run(workflow.review(P, []))
    assert result['structured_response'].satisfied
    assert len(calls) > len(files.read_json(P, files.BACKLOG, Backlog).stories())
    count = len(calls)
    assert asyncio.run(workflow.review(P, []))['structured_response'].satisfied
    assert len(calls) == count
    assert files.path(P, files.BACKLOG).read_bytes() == before
    from agent_engine.history import fingerprint
    assert not any('.engine-breakdown' in p for p in fingerprint(proj))


def test_incomplete_partition_cannot_approve(proj, monkeypatch):
    backlog.set_features(P, _features()); backlog.build(P)
    async def fake(schema, purpose, payload, callbacks):
        return workflow.Review(reviewed_ids=[], complete=True, findings=[])
    monkeypatch.setattr(workflow, '_call', fake)
    with pytest.raises(files.ProjectError, match='incomplete'):
        asyncio.run(workflow.review(P, []))


def test_generation_and_enrichment_without_agent_tools(proj, monkeypatch):
    # A fresh project contains only unchanged public input formats.
    import shutil
    shutil.rmtree(proj / 'specs')
    monkeypatch.setattr(workflow, 'model_spec', lambda tier: 'test:model')
    doc = document()
    doc['stories'][0]['source_ids'] = _features()[0]['requirement_ids']
    calls = []
    async def fake(schema, purpose, payload, callbacks):
        calls.append(schema)
        if schema is workflow.Plan:
            return workflow.Plan(features={'features': _features()}, implementation_contract='Use approved architecture; choices remain open.')
        if schema is workflow.Generated:
            return workflow.Generated(document=FeatureDocument.model_validate(doc), patches=[
                workflow.Patch(item_id='S-001-US1', estimate={'story_points': 3, 'complexity': 3, 'method': 'llm', 'confidence': 'low'}),
                *[workflow.Patch(item_id='001-T00'+str(n), acceptance_criteria=['WHEN saving THE SYSTEM SHALL persist the bookmark'],
                                 skills_required=['backend-python'], ai_eligible=False, ai_eligibility_reason='Human review required') for n in (1,2)]])
        return workflow.Dependencies(edges=[])
    monkeypatch.setattr(workflow, '_call', fake)
    asyncio.run(workflow.generate(P, 'Build backlog', []))
    b = files.read_json(P, files.BACKLOG, Backlog)
    assert b.stories()[0].estimate.story_points == 3
    assert all(t.acceptance_criteria for t in b.tasks_of('S-001-US1'))
    assert files.exists(P, files.BACKLOG_MD)
    count = calls.count(workflow.Generated)
    asyncio.run(workflow.generate(P, 'Build backlog', []))
    assert calls.count(workflow.Generated) == count
    plans_before = calls.count(workflow.Plan)
    files.write_text(P, 'backlog/implementation-contract.md', 'Reviewed source-backed contract amendment')
    asyncio.run(workflow.generate(P, 'Build backlog', []))
    assert calls.count(workflow.Plan) == plans_before + 1


def test_unrelated_requirement_edit_reuses_feature_checkpoint(proj):
    from agent_engine.phase4 import feature_jobs
    files.path(P, files.PRD).write_text('# Global\nRules\n## FR-001\nSave\n## FR-002\nDelete\n')
    f = _features()[0]
    f['requirement_ids'] = ['FR-001']
    backlog.set_features(P, [f]); speckit.init(P)
    files.write_text(P, f['feature_dir'] + '/plan.md', '# Existing approved plan\n')
    first = feature_jobs.status(P, f['feature_dir'])
    feature_jobs.checkpoint(P, f['feature_dir'], first['input_sha256'])
    files.path(P, files.PRD).write_text('# Global\nRules\n## FR-001\nSave\n## FR-002\nDelete differently\n')
    assert feature_jobs.status(P, f['feature_dir'])['reusable']
    files.path(P, files.PRD).write_text('# Global\nChanged policy\n## FR-001\nSave\n## FR-002\nDelete differently\n')
    assert not feature_jobs.status(P, f['feature_dir'])['reusable']


def test_targeted_repair_rejects_unrelated_patch(proj, monkeypatch):
    backlog.set_features(P, _features()); backlog.build(P); _enrich(P); backlog.validate(P)
    before = files.path(P, files.BACKLOG).read_bytes()
    async def fake(*args):
        return workflow.Repairs(patches=[workflow.Patch(item_id='S-001-US2', open_questions=['unrelated'])])
    monkeypatch.setattr(workflow, '_call', fake)
    finding = json.dumps({'rule': 'testability', 'item_ids': ['S-001-US1'], 'message': 'Fix criterion'})
    with pytest.raises(files.ProjectError, match='outside affected'):
        asyncio.run(workflow.repair(P, [finding], []))
    assert files.path(P, files.BACKLOG).read_bytes() == before


def test_typed_findings_keep_all_affected_ids(proj):
    backlog.set_features(P, _features()); backlog.build(P)
    from agent_engine.cli import _deterministic_gaps
    findings, human = _deterministic_gaps('task-breakdown', P)
    parsed = [json.loads(f) for f in findings]
    unestimated = next(f for f in parsed if f['rule'] == 'estimates')
    b = files.read_json(P, files.BACKLOG, Backlog)
    assert len(unestimated['item_ids']) == sum(i.level in ('story', 'task') for i in b.items)
    assert not human


def test_history_change_invalidates_completed_feature(proj):
    from agent_engine.phase4 import feature_jobs
    f = _features()[0]
    backlog.set_features(P, [f]); speckit.init(P)
    files.write_text(P, f['feature_dir'] + '/plan.md', '# Existing plan\n')
    status = feature_jobs.status(P, f['feature_dir'])
    feature_jobs.checkpoint(P, f['feature_dir'], status['input_sha256'])
    assert feature_jobs.status(P, f['feature_dir'])['reusable']
    path = files.path(P, files.HISTORY)
    path.write_text(path.read_text() + '\n')
    assert not feature_jobs.status(P, f['feature_dir'])['reusable']


def test_global_section_citing_other_requirement_is_retained(proj):
    files.path(P, files.PRD).write_text('# Security policy\nAll endpoints require authentication, including FR-002.\n## FR-001\nSave\n## FR-002\nDelete\n')
    evidence = packet(P, ['FR-001'])[files.PRD]
    text = ''.join(s['text'] for s in evidence)
    assert 'All endpoints require authentication' in text
    assert 'Delete' not in text
