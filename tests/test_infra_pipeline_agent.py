import json
import pytest
from agent_engine.phase4 import infra, files
from test_phase4_pipeline import proj as _base_proj, P, _intent, mock_passed_checks

@pytest.fixture
def proj(_base_proj):
    return _base_proj


def test_qa_environment_rendered(proj, monkeypatch):
    intent = _intent()
    intent['environments'] = ['dev', 'qa', 'stg', 'prod']
    infra.set_intent(P, intent)
    infra.render(P)
    assert files.exists(P, 'infra/repo/envs/qa/core/main.tf')
    assert files.exists(P, 'infra/repo/gitops/apps/taskflow-api/qa/values.yaml')
    mock_passed_checks(monkeypatch)
    assert json.loads(infra.validate(P))['checks_passed']


def test_unsupported_cloud_is_rejected(proj):
    intent = _intent()
    intent['cloud'] = 'azure'
    with pytest.raises(files.ProjectError, match='only implements AWS'):
        infra.set_intent(P, intent)


def test_promotion_copies_predecessor_digest_for_shared_images(proj):
    import importlib.util
    import yaml
    intent = _intent()
    intent['environments'] = ['dev', 'qa', 'stg', 'prod']
    infra.set_intent(P, intent)
    infra.render(P)
    root = files.path(P, 'infra/repo')
    spec = importlib.util.spec_from_file_location('generated_promote', root / 'scripts/promote.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    digest = 'sha256:' + 'a' * 64
    module.promote(root, 'taskflow-api', 'dev', digest)
    module.promote(root, 'taskflow-api', 'qa')
    for name in ('taskflow-api', 'notify-worker'):
        assert yaml.safe_load((root / f'gitops/apps/{name}/qa/values.yaml').read_text())['image']['digest'] == digest
    with pytest.raises(ValueError, match='exactly'):
        module.promote(root, 'taskflow-api', 'stg', 'sha256:' + 'b'*64)
    assert 'image promotion is not generated' not in ' '.join(files.read_json(P, files.INFRA_MANIFEST)['gaps'])


def test_runbook_and_branching_are_in_manifest(proj, monkeypatch):
    infra.set_intent(P, _intent())
    infra.render(P)
    paths = {f['path'] for f in files.read_json(P, files.INFRA_MANIFEST)['files']}
    assert {'repo/docs/RUNBOOK.md', 'repo/docs/BRANCHING.md'} <= paths
    mock_passed_checks(monkeypatch)
    infra.validate(P)
    assert 'docs/RUNBOOK.md' in files.read_text(P, files.INFRA_PR)


def test_digest_policy_and_namespace_access(proj):
    infra.set_intent(P, _intent())
    infra.render(P)
    manifest = files.read_json(P, files.INFRA_MANIFEST, __import__('agent_engine.phase4.contracts', fromlist=['InfraManifest']).InfraManifest)
    assert not infra.deployment_problems(P, manifest)
    rel = 'infra/repo/gitops/apps/taskflow-api/dev/values.yaml'
    files.write_text(P, rel, files.read_text(P, rel).replace('  digest:', '  tag:'))
    assert infra.deployment_problems(P, manifest)
    access = files.read_text(P, 'infra/repo/gitops/platform/dev/access.yaml')
    assert 'restricted' in access and 'get, list, watch' in access


def test_structured_intent_is_cached_and_scanners_run(proj, monkeypatch):
    import asyncio
    from agent_engine.phase4 import infra_pipeline as ip
    from agent_engine.phase4.contracts import InfraIntent
    calls = []
    async def fake(schema, system, human, callbacks, spec):
        calls.append(spec)
        intent = _intent()
        intent['environments'] = ['dev', 'qa', 'stg', 'prod']
        return InfraIntent.model_validate(intent)
    monkeypatch.setattr(ip, '_invoke', fake)
    mock_passed_checks(monkeypatch)
    for _ in range(2):
        asyncio.run(ip.generate(P, 'Set up environments.'))
        assert asyncio.run(ip.review(P))['structured_response'].satisfied
    assert len(calls) == 1


def test_missing_readiness_sources_fail_closed_without_network(proj, monkeypatch):
    from agent_engine.phase4 import environment_check as ec
    infra.set_intent(P, _intent())
    infra.render(P)
    monkeypatch.setattr(ec, 'github_http', lambda: pytest.fail('No source configured; no API calls'))
    evidence = ec.check_environments(P)
    assert not evidence['ready'] and evidence['errors']
    assert files.exists(P, ec.EVIDENCE)


def test_readiness_checks_merged_files_apply_ci_and_argo(proj, monkeypatch):
    import hashlib
    from agent_engine.phase4 import environment_check as ec
    infra.set_intent(P, _intent())
    infra.render(P)
    manifest = files.read_json(P, files.INFRA_MANIFEST)
    tree = []
    for entry in manifest['files']:
        if not entry['path'].startswith('repo/'): continue
        data = files.path(P, 'infra/' + entry['path']).read_bytes()
        sha = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        tree.append({'path': entry['path'][5:], 'sha': sha, 'type': 'blob'})
    files.write_json(P, ec.SOURCES, {'environments': {e: {'pull_request': 1, 'apply_context': 'atlantis/apply:' + e} for e in ('dev', 'prod')}})
    monkeypatch.setenv('ARGOCD_SERVER', 'https://argo.example.invalid')
    monkeypatch.setattr(ec.readiness, 'check_ci', lambda p: {r: {'success': True} for r in manifest['ci_repos']})
    class Response:
        def __init__(self, data): self.data = data
        def json(self): return self.data
        def raise_for_status(self): pass
    class Github:
        def get(self, path, **kw):
            if '/pulls/' in path: return Response({'merged_at':'yes', 'merge_commit_sha':'merge', 'head':{'sha':'pr-head'}})
            if '/git/trees/' in path: return Response({'tree':tree})
            if '/compare/' in path: return Response({'status':'ahead'})
            if path.endswith('/status'): return Response({'statuses':[{'context':'atlantis/apply:'+e,'state':'success'} for e in ('dev','prod')]})
            if '/commits/' in path: return Response({'sha':'head'})
            return Response({'default_branch':'main'})
        def close(self): pass
    class Argo:
        healthy = True
        def __init__(self, **kw): pass
        def get(self, path): return Response({'status':{'health':{'status':'Healthy' if self.healthy else 'Degraded'},'sync':{'status':'Synced','revision':'head'}}})
        def close(self): pass
    monkeypatch.setattr(ec, 'github_http', Github)
    monkeypatch.setattr(ec.httpx, 'Client', Argo)
    assert ec.check_environments(P)['ready']
    Argo.healthy = False
    assert not ec.check_environments(P)['ready']


def test_repair_pauses_without_complete_scanners(proj, monkeypatch):
    import asyncio
    from agent_engine.phase4 import infra_pipeline as ip
    infra.set_intent(P, _intent())
    infra.render(P)
    infra.validate(P)
    monkeypatch.setattr(ip, '_invoke', lambda *a: pytest.fail('Missing scanners cannot be repaired by a model'))
    with pytest.raises(files.ProjectError, match='scanners'):
        asyncio.run(ip.repair(P, ['missing tools']))


def test_generated_promotion_refuses_unprotected_environment(proj):
    import importlib.util
    infra.set_intent(P, _intent())
    infra.render(P)
    path = files.path(P, 'infra/repo/scripts/verify-protection.py')
    spec = importlib.util.spec_from_file_location('verify_protection', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with pytest.raises(ValueError, match='protection'):
        module.verify('qa', '123', 'example/infra', 'head', lambda path: {})
    environment = {'can_admins_bypass':False, 'protection_rules':[{'type':'required_reviewers','prevent_self_review':True,'reviewers':[{'reviewer':{'id':123}}]}]}
    module.verify('qa', '123', 'example/infra', 'head', lambda path: environment)
    import copy
    permissive = copy.deepcopy(environment)
    permissive['protection_rules'][0]['reviewers'].append({'reviewer':{'id':456}})
    with pytest.raises(ValueError, match='protection'):
        module.verify('qa', '123', 'example/infra', 'head', lambda path: permissive)
    with pytest.raises(ValueError, match='go/no-go'):
        module.verify('prod', '123', 'example/infra', 'head', lambda path: environment if '/environments/' in path else {'statuses':[]})
