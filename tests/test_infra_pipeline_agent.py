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


def test_unsupported_cloud_is_a_gap_report_not_a_failure(proj):
    from agent_engine.phase4 import attention
    intent = _intent()
    intent['cloud'] = 'azure'
    result = json.loads(infra.set_intent(P, intent))
    assert any('only implements AWS' in w for w in result.get('warnings', []))
    infra.render(P)
    assert any('only has AWS entries' in g for g in files.read_json(P, files.INFRA_MANIFEST)['gaps'])
    assert any('only has AWS entries' in line for line in attention.open_items(P, 'infra-pipeline'))


def test_hosting_target_outside_the_catalog_is_reported_as_gaps(proj):
    intent = _intent()
    intent['deploy_target'] = 'serverless'
    for c in intent['components']:
        c['needs'] = [n for n in c['needs'] if n not in ('k8s_workload', 'ecs_service')]
    result = json.loads(infra.set_intent(P, intent))
    assert any("no workload template" in w for w in result.get('warnings', []))
    infra.render(P)
    gaps = files.read_json(P, files.INFRA_MANIFEST)['gaps']
    services = [c['name'] for c in intent['components'] if c['kind'] in ('service', 'worker')]
    assert services and all(any(s in g and "'serverless' is not in the catalog" in g for g in gaps) for s in services)


def test_checkov_policy_blocks_only_high_findings_in_generated_code():
    from agent_engine.phase4 import sandbox
    out = {"results": {"failed_checks": [
        {"check_id": "CKV_TF_1", "check_name": "commit hash", "file_path": "/envs/dev/core/main.tf"},
        {"check_id": "CKV_AWS_58", "check_name": "EKS secrets", "file_path": "/.external_modules/github.com/x/main.tf"},
    ]}, "summary": {"parsing_errors": 0}}
    ok = sandbox._checkov_result(sandbox.CmdResult(0, json.dumps(out), ""))
    assert ok.passed and ok.outcome == "findings" and len(ok.findings) == 2   # medium + third-party: warnings only
    out["results"]["failed_checks"].append(
        {"check_id": "CKV_AWS_17", "check_name": "RDS public", "file_path": "/envs/dev/core/main.tf"})
    bad = sandbox._checkov_result(sandbox.CmdResult(0, json.dumps(out), ""))
    assert not bad.passed and "1 blocking" in bad.summary


def test_infra_repair_applies_only_small_targeted_edits():
    from agent_engine.phase4.infra_pipeline import Edit, apply_edits, MAX_EDIT_LINES
    content = {"envs/dev/main.tf": 'resource "aws_s3_bucket" "logs" {\n  acl = "public-read"\n}\n'}
    new, errors = apply_edits(content, [Edit(path="envs/dev/main.tf", find='acl = "public-read"', replace='acl = "private"')])
    assert not errors and 'acl = "private"' in new["envs/dev/main.tf"] and 'resource "aws_s3_bucket"' in new["envs/dev/main.tf"]
    _, errors = apply_edits(content, [Edit(path="envs/dev/main.tf", find="missing", replace="x")])
    assert errors and "exactly once" in errors[0]
    _, errors = apply_edits(content, [Edit(path="envs/dev/main.tf", find='acl = "public-read"',
                                           replace="\n" * MAX_EDIT_LINES)])
    assert errors and "at most" in errors[0]                    # whole-file rewrites are refused


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


def _ecs_intent():
    """The gym architecture's shape: static web on CloudFront, API on ECS Fargate behind a public ALB, RDS."""
    intent = _intent()
    intent['deploy_target'] = 'ecs_fargate'
    intent['environments'] = ['dev', 'qa', 'stg', 'prod']
    api, web, worker = intent['components'][:3]
    api['needs'] = ['ecs_service', 'container_registry', 'public_endpoint']
    api['public_endpoint'] = True
    web.update(needs=['object_storage', 'cdn'], repo=None)
    worker['needs'] = ['ecs_service']
    return intent


def test_ecs_fargate_renders_services_load_balancer_and_static_site(proj, monkeypatch):
    infra.set_intent(P, _ecs_intent())
    infra.render(P)
    core = files.read_text(P, 'infra/repo/envs/prod/core/main.tf')
    for expected in ('module "ecs_cluster"', 'module "svc_taskflow_api"', 'module "svc_notify_worker"',
                     'module "alb"', 'aws_wafv2_web_acl_association', 'aws_cloudfront_distribution" "taskflow_web"',
                     'web_acl_id', 'module "db_taskflow_db"', '"/api/*"'):
        assert expected in core, expected
    assert 'module "eks"' not in core
    # Secrets are references by name; the worker shares the API image and needs its command set.
    assert f'name = "/{P}/prod/notify-worker/EMAIL_PROVIDER_API_KEY"' in core and 'TODO-start-command' in core
    paths = {f['path'] for f in files.read_json(P, files.INFRA_MANIFEST)['files']}
    assert not any(p.startswith('repo/gitops/') for p in paths)
    assert {'repo/envs/dev/core/images.auto.tfvars.json', 'repo/promotion.json'} <= paths
    gaps = ' '.join(files.read_json(P, files.INFRA_MANIFEST)['gaps'])
    assert 'certificate_arn' in gaps and 'Argo CD' not in gaps
    runbook = files.read_text(P, 'infra/repo/docs/RUNBOOK.md')
    assert 'ECS Fargate' in runbook and 'Argo CD' not in runbook
    seen = {}
    from agent_engine.phase4 import sandbox
    def fake(wd, envs, **kw):
        seen.setdefault('only', kw.get('only'))
        return [infra.CheckResult(tool=t, passed=True, outcome='passed', summary='mock')
                for t in sandbox.ALL_TOOLS if kw.get('only') is None or t in kw['only']]
    monkeypatch.setattr(sandbox, 'run_checks', fake)
    result = json.loads(infra.validate(P))
    assert result['checks_passed'] and result['validation_complete']
    assert not seen['only'] & {'helm_lint', 'kubeconform'}             # nothing Kubernetes to lint on ECS


def test_ecs_promotion_moves_the_digest_through_the_tfvars_files(proj):
    import importlib.util
    infra.set_intent(P, _ecs_intent())
    infra.render(P)
    root = files.path(P, 'infra/repo')
    spec = importlib.util.spec_from_file_location('generated_promote_ecs', root / 'scripts/promote.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    digest = 'sha256:' + 'c' * 64
    module.promote(root, 'taskflow-api', 'dev', digest)
    module.promote(root, 'taskflow-api', 'qa')
    for env in ('dev', 'qa'):
        tfvars = json.loads((root / f'envs/{env}/core/images.auto.tfvars.json').read_text())
        assert tfvars == {'image_digests': {'taskflow-api': digest}}
    with pytest.raises(ValueError, match='exactly'):
        module.promote(root, 'taskflow-api', 'stg', 'sha256:' + 'd' * 64)
    tfvars = root / 'envs/prod/core/images.auto.tfvars.json'
    tfvars.write_text(json.dumps({'image_digests': {'taskflow-api': 'latest'}}))
    manifest = files.read_json(P, files.INFRA_MANIFEST, infra.InfraManifest)
    assert any('must pin a sha256 digest' in p for p in infra.deployment_problems(P, manifest))


@pytest.mark.parametrize('change, message', [
    (lambda i: i['components'][0].update(needs=['k8s_workload', 'container_registry']), 'needs k8s_workload but deploy_target is ecs_fargate'),
    (lambda i: i['components'][1].update(needs=['cdn']), 'also needs object_storage'),
    (lambda i: i.update(deploy_target='serverless'), 'needs ecs_service but deploy_target is serverless'),
])
def test_ecs_intent_mismatches_are_rejected(proj, change, message):
    intent = _ecs_intent()
    change(intent)
    with pytest.raises(files.ProjectError, match=message):
        infra.set_intent(P, intent)


def test_kubernetes_intent_cannot_use_ecs_services(proj):
    intent = _intent()
    intent['components'][0]['needs'] = ['ecs_service', 'container_registry']
    with pytest.raises(files.ProjectError, match='needs ecs_service but deploy_target is kubernetes'):
        infra.set_intent(P, intent)


def test_repair_that_deletes_infrastructure_is_refused():
    """A repair once returned a 4-line dev main.tf: valid Terraform, fewer checkov findings, no environment."""
    from agent_engine.phase4.infra_pipeline import removed_blocks
    before = ('terraform {\n}\nprovider "aws" {\n}\nmodule "network" {\n}\nresource "aws_s3_bucket" "logs" {\n}\n'
              'data "aws_caller_identity" "current" {}\n')
    assert removed_blocks(before, 'terraform {\n}\n') == [
        'data aws_caller_identity current', 'module network', 'provider aws', 'resource aws_s3_bucket logs']
    hardened = before.replace('resource "aws_s3_bucket" "logs" {\n}', 'resource "aws_s3_bucket" "logs" {\n  force_destroy = false\n}')
    assert removed_blocks(before, hardened + 'resource "aws_s3_bucket_versioning" "logs" {\n}\n') == []


def test_accepted_checkov_risks_come_only_from_the_catalog(proj, monkeypatch, tmp_path):
    import shutil
    infra.set_intent(P, _intent())
    infra.render(P)
    assert not files.exists(P, 'infra/repo/.checkov.yaml')               # default catalog accepts nothing
    catalog = tmp_path / 'catalog'
    shutil.copytree(infra.catalog_dir(), catalog)
    (catalog / 'templates/repo/checkov.yaml').write_text('# justification per check\nskip-check:\n  - CKV_TF_1\n')
    monkeypatch.setattr(infra, 'catalog_dir', lambda: catalog)
    infra.render(P)
    assert 'CKV_TF_1' in files.read_text(P, 'infra/repo/.checkov.yaml')
    assert any('CKV_TF_1' in g for g in files.read_json(P, files.INFRA_MANIFEST)['gaps'])
    mock_passed_checks(monkeypatch)
    infra.validate(P)
    assert '`CKV_TF_1`' in files.read_text(P, files.INFRA_PR)


def test_repair_guard_ignores_attributes_named_like_blocks():
    from agent_engine.phase4.infra_pipeline import removed_blocks
    before = 'module "x" {\n  data = 1\n  output = "y"\n}\nlocals {\n}\n'
    assert removed_blocks(before, 'module "x" {\n}\nlocals {\n}\n') == []
    assert removed_blocks(before, 'module "x" {\n}\n') == ['locals']
