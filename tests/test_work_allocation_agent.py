import json
import pytest
from agent_engine.phase4 import allocation, files
from agent_engine.phase4.contracts import Backlog, ProjectSettings, Dependency
from test_phase4_pipeline import proj, P, built

@pytest.mark.parametrize('signal', ['DB', 'DevOps', 'auth-security', 'payments', 'shared', 'component', 'dependant'])
def test_structured_risk_signals(proj, signal):
    built(proj)
    b = files.read_json(P, files.BACKLOG, Backlog)
    settings = files.read_json(P, files.PROJECT_SETTINGS, ProjectSettings)
    task = b.tasks_of('BM-4')[1]
    task.title, task.description_md, task.file_paths = 'Small change', 'Local change', ['src/item.py']
    task.open_questions, task.skills_required = [], ['backend-python']
    if signal in ('DB', 'DevOps'):
        task.discipline = signal
    elif signal in ('auth-security', 'payments'):
        task.skills_required = [signal]
    elif signal == 'shared':
        task.open_questions = ['Shared work: also serves BM-2']
    elif signal == 'component':
        settings.human_only_components = task.components
    else:
        b.tasks_of('BM-2')[0].dependencies = [Dependency(on_id=task.item_id, reason='foundation', confidence=1, origin='human')]
    assert allocation.risk_reasons(task, b, settings)


def test_problem_has_no_retired_ai_proposal(proj):
    from agent_engine.phase4 import sprint
    built(proj)
    sprint.solve(P, as_of="2026-11-05")
    allocation.prepare(P, 1)
    assert "agent1_ai_proposal" not in files.path(P, files.ALLOCATION_PROBLEM).read_text()


def test_code_driven_stage_without_ai_candidates(proj, monkeypatch):
    import asyncio
    from agent_engine.phase4 import sprint, work_allocation as wa
    built(proj)
    sprint.solve(P, as_of="2026-11-05")
    async def unexpected(*args):
        pytest.fail("No model needed without AI candidates")
    monkeypatch.setattr(wa, '_invoke', unexpected)
    asyncio.run(wa.generate(P, 'Assign sprint 1.'))
    result = asyncio.run(wa.review(P))
    assert result['structured_response'].satisfied
    assert all(a['explanation'] for a in files.read_json(P, files.ASSIGNMENTS)['assignments'])


def test_validator_recomputes_capacity(proj):
    import asyncio
    from agent_engine.phase4 import sprint, work_allocation as wa
    built(proj)
    sprint.solve(P, as_of="2026-11-05")
    asyncio.run(wa.generate(P, 'Assign sprint 1.'))
    ap = files.read_json(P, files.ASSIGNMENTS)
    ap['workers'][0]['capacity_hours'] = 10000
    files.write_json(P, files.ASSIGNMENTS, ap)
    assert not json.loads(allocation.check(P))['ok']


def test_checked_judgement_retries_and_caches(proj, monkeypatch):
    import asyncio
    from agent_engine.phase4 import work_allocation as wa
    monkeypatch.setenv('SDLC_AGENT_STRONG_MODEL', 'anthropic:test')
    monkeypatch.setenv('SDLC_AGENT_FAST_MODEL', 'anthropic:test')
    calls = []
    async def fake(schema, system, human, callbacks, spec):
        calls.append(human)
        return wa.Judgement(verdicts=[wa.CandidateVerdict(task_id='bad' if len(calls)==1 else 'real', eligible=False, reason='Needs a product decision first')])
    monkeypatch.setattr(wa, '_invoke', fake)
    def check(result):
        return [] if result.verdicts[0].task_id == 'real' else ['Unknown task']
    for _ in range(2):
        asyncio.run(wa._call(P, wa.Judgement, 'judge', {'candidate': 'real'}, None, check))
    assert len(calls) == 2


def test_phase4_publishing_never_constructs_dispatch_adapter(proj, monkeypatch):
    import asyncio
    from agent_engine.phase4 import sprint, work_allocation as wa, publish, dispatch
    from test_phase4_pipeline import approve
    built(proj)
    approve(proj, 'P4-G1')
    sprint.solve(P, as_of="2026-11-05")
    approve(proj, 'P4-G2')
    asyncio.run(wa.generate(P, 'Assign sprint 1.'))
    approve(proj, 'P4-G3')
    publish.publish_backlog(P)
    monkeypatch.setattr(dispatch, 'adapter_for', lambda *a: pytest.fail('Phase 4 cannot dispatch'))
    publish.publish_assignments(P)
    with pytest.raises(publish.PublishError, match='readiness'):
        publish.dispatch_assignments(P)


def test_cli_work_allocation_uses_structured_stage(proj, monkeypatch, tmp_path):
    import asyncio
    from agent_engine import cli, logging_setup
    from agent_engine.phase4 import sprint
    from test_phase4_pipeline import approve
    built(proj)
    approve(proj, 'P4-G1')
    sprint.solve(P, as_of="2026-11-05")
    approve(proj, 'P4-G2')
    monkeypatch.setattr(cli, 'OUTPUTS_DIR', proj.parent)
    monkeypatch.setattr(logging_setup, 'OUTPUTS_DIR', proj.parent)
    monkeypatch.setattr(logging_setup, 'LOGS_DIR', tmp_path / 'logs')
    monkeypatch.setattr(cli, 'build_langfuse_handler', lambda: None)
    monkeypatch.setattr(cli, 'build_agent', lambda *a, **k: pytest.fail('Structured stage must not build a deep agent'))
    assert asyncio.run(cli._run('Assign sprint 1.', 'work-allocation', P)) == 0


@pytest.fixture(autouse=True)
def _isolate_component_publication(monkeypatch):
    # These tests exercise one publisher/checkpoint; final G4 has dedicated integration tests.
    from agent_engine.phase4 import publish
    monkeypatch.setattr(publish, "require_final_gate", lambda project: {})


def test_a_depended_on_story_keeps_only_its_backend_away_from_ai(proj):
    """BM-3 depends on BM-2 (a tracker "blocks" link): BM-2's API is a foundation, its screen and tests are not."""
    built(proj)
    b = files.read_json(P, files.BACKLOG, Backlog)
    settings = files.read_json(P, files.PROJECT_SETTINGS, ProjectSettings)
    assert any(d.on_id == 'BM-2' for d in b.by_id()['BM-3'].dependencies)
    by_discipline = {t.discipline: t for t in b.tasks_of('BM-2')}
    assert "backend of a story other stories depend on" in allocation.risk_reasons(by_discipline['BE'], b, settings)
    for discipline in ('FE', 'QA'):
        reasons = allocation.risk_reasons(by_discipline[discipline], b, settings)
        assert not any('depend' in r for r in reasons), (discipline, reasons)
    # A story nobody depends on keeps its backend eligible on this signal.
    be_of_leaf = next(t for t in b.tasks_of('BM-4') if t.discipline == 'BE')
    assert not any('depend' in r for r in allocation.risk_reasons(be_of_leaf, b, settings))
