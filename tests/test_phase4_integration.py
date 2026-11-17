"""Final-gate and local end-to-end tests. Every model, scanner and tracker is offline."""
import asyncio
import json
import time
import pytest
from agent_engine import config, gates
from agent_engine.phase4 import files, publish, infra, task_breakdown as tb, sprint_planning as sp, work_allocation as wa, infra_pipeline as ip
from agent_engine.phase4.contracts import InfraIntent
from test_phase4_pipeline import proj as _base_proj, P, _intent, mock_passed_checks
from test_task_breakdown_stories import FakeModel as BreakdownModel
from test_sprint_planning_agent import FakeModel as SprintModel

@pytest.fixture
def proj(_base_proj):
    return _base_proj


def approve(root, name):
    gates.record_decision(root, gates.load_gates()[name], 'approved',
                          {'name': 'Synthetic reviewer ' + name}, {'name': 'Synthetic agent'})


def test_offline_eight_story_cli_pipeline_and_final_gate(proj, monkeypatch, tmp_path):
    from agent_engine import cli, logging_setup
    from phase4_helpers import approve_design_gates
    stories = []
    for i in range(1, 9):
        us = f'US-{i:03}'
        stories.append({'key':f'DEMO-{i}', 'issue_id':str(i), 'summary':f'Account sign-in scenario {i}',
                        'statement':'As staff, I want to sign in so that I can access my screens.',
                        'epic_key': 'DEMO-100' if i <= 4 else 'DEMO-200', 'story_points':3,
                        'moscow':'must' if i <= 4 else 'should', 'rank':str(i),
                        'fix_versions':['MVP' if i<=4 else 'R2'], 'requirement_ids':[us,'FR-002'],
                        'acceptance_criteria':[{'ac_id':us+'.AC1','text':'Given an account, When the password is correct, Then sign in succeeds.'},
                                               {'ac_id':us+'.AC2','text':'Given an account, When the password is wrong, Then sign in fails.'}]})
    files.write_json(P, files.STORIES, {'project':P,'source':'file','project_key':'DEMO','stories':stories,
        'epics':[{'key':k,'issue_id':k,'summary':k} for k in ('DEMO-100','DEMO-200')],
        'releases':[{'name':'MVP','order':1}, {'name':'R2','order':2}]})
    files.write_text(P, files.ARCHITECTURE, '# Architecture\nAWS Kubernetes. POST /api/sessions; users.password_hash. Python API, React screens; QA uses Playwright.\n')
    files.write_text(P, files.PRD, '# PRD\nFR-002: staff sign in. NFR-010: lockout after five attempts.\n')
    approve_design_gates(proj)
    settings = files.read_json(P, files.PROJECT_SETTINGS)
    settings['calendar']['first_sprint_start'] = '2026-11-17'
    settings['release_deadlines'] = [{'release':'MVP','due_date':'2026-12-15'}, {'release':'R2','due_date':'2027-01-15'}]
    files.write_json(P, files.PROJECT_SETTINGS, settings)
    monkeypatch.setattr(cli, 'OUTPUTS_DIR', proj.parent)
    monkeypatch.setattr(logging_setup, 'OUTPUTS_DIR', proj.parent)
    monkeypatch.setattr(logging_setup, 'LOGS_DIR', tmp_path/'logs')
    monkeypatch.setattr(cli, 'build_langfuse_handler', lambda: None)
    monkeypatch.setattr(cli, 'build_agent', lambda *a, **k: pytest.fail('All four stages must be code-driven'))
    breakdown, sprint = BreakdownModel(), SprintModel()
    monkeypatch.setattr(tb, '_invoke', breakdown)
    monkeypatch.setattr(sp, '_invoke', sprint)
    async def intent(*args):
        data = _intent()
        data['environments'] = ['dev','qa','stg','prod']
        return InfraIntent.model_validate(data)
    monkeypatch.setattr(ip, '_invoke', intent)
    mock_passed_checks(monkeypatch)
    original_stories = files.read_text(P, files.STORIES)
    timings = {}
    for name, request, gate in (
        ('task-breakdown','Break the approved stories down into tasks.','P4-G1'),
        ('sprint-planning','Plan the sprints.','P4-G2'),
        ('work-allocation','Assign sprint 1.','P4-G3'),
        ('infra-pipeline','Set up dev, qa, stg and prod.','P4-G4')):
        start = time.monotonic()
        assert asyncio.run(cli._run(request, name, P)) == 0
        timings[name] = round(time.monotonic()-start, 3)
        approve(proj, gate)
    assert files.read_text(P, files.STORIES) == original_stories
    assert not (proj/'tracker').exists()
    with pytest.raises(publish.PublishError, match='Final G4'):
        publish.publish_backlog(P)
    approve(proj, 'G4')
    for name in ('infra','backlog','sprint','assignments'):
        publish.PUBLISHERS[name](P)
    assert not (proj/'publish/dispatch').exists()
    assert files.read_json(P, files.SPRINT_PLAN)['releases']
    with pytest.raises(publish.PublishError, match='readiness'):
        publish.dispatch_assignments(P)
    assignments = files.read_text(P, files.ASSIGNMENTS)
    files.write_text(P, files.ASSIGNMENTS, assignments+'\n')
    with pytest.raises(publish.PublishError, match='approved again|stale'):
        publish.publish_backlog(P)
    print('LOCAL_E2E ' + json.dumps({'stories':8,'epics':2,'releases':2,'tasks':24,'timings_seconds':timings,
          'breakdown_calls':len(breakdown.calls),'cross_calls':len(breakdown.cross_calls),
          'review_calls':len(breakdown.review_calls),'sprint_calls':len(sprint.calls),
          'network':'blocked','scanners':'fake','approvals':'synthetic test identities','tokens':'not measured by fakes'}))


def test_ui_and_api_documents_are_tracked(proj):
    from agent_engine.phase4.contracts import ProjectSettings
    files.write_text(P, 'api/openapi.yaml', 'openapi: 3.1.0\n')
    settings = files.read_json(P, files.PROJECT_SETTINGS, ProjectSettings)
    assert 'api/openapi.yaml' in tb.source_manifest(P)
    assert 'openapi: 3.1.0' in tb.prompt_prefix(P, settings)


def test_final_gate_rejection_routes_back_to_design(proj, monkeypatch):
    from agent_engine import cli
    monkeypatch.setattr(cli, 'OUTPUTS_DIR', proj.parent)
    assert cli._gate('G4', P, 'rejected', {'name':'Synthetic reviewer'}, {'name':'Synthetic agent'}, 'Revisit the design') == 0
    assert not files.exists(P, 'gates/G3A.approved.json')
    assert not files.exists(P, 'gates/G3B.approved.json')


def test_final_gate_cannot_be_approved_before_parts(proj, monkeypatch):
    from agent_engine import cli
    monkeypatch.setattr(cli, 'OUTPUTS_DIR', proj.parent)
    assert cli._gate('G4', P, 'approved', {'name':'Synthetic reviewer'}, {'name':'Synthetic agent'}, '') == 1
    assert not files.exists(P, 'gates/G4.approved.json')


def test_stage_budgets_are_configurable_and_bounded(monkeypatch):
    from agent_engine.stage_controls import StageBudget, StageBudgetExceeded
    monkeypatch.setenv('AGENT_ENGINE_WORK_ALLOCATION_MAX_CALLS', '1')
    budget = StageBudget.from_env('work-allocation')
    budget.begin_call()
    with pytest.raises(StageBudgetExceeded):
        budget.begin_call()
