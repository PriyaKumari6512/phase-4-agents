"""Read-only operational evidence; missing sources always remain not ready."""
from __future__ import annotations
import hashlib
import os
from urllib.parse import urlsplit
import httpx
from agent_engine.phase4 import files, infra, readiness
from agent_engine.phase4.contracts import InfraManifest, InfraIntent
from agent_engine.phase4.trackers.github import github_http

SOURCES = 'phase4/environment-sources.json'
EVIDENCE = 'phase4/environment-readiness.json'


def check_environments(project):
    manifest = files.read_json(project, files.INFRA_MANIFEST, InfraManifest)
    intent = files.read_json(project, files.INFRA_INTENT, InfraIntent)
    sources = files.read_json(project, SOURCES) if files.exists(project, SOURCES) else {}
    evidence = {'observed_at': files.utcnow().isoformat(), 'manifest_sha256': files.file_sha(project, files.INFRA_MANIFEST),
                'sources_sha256': files.file_sha(project, SOURCES) if files.exists(project, SOURCES) else None,
                'ready': False, 'environments': {}, 'errors': []}
    server = os.environ.get('ARGOCD_SERVER', '').rstrip('/')
    parsed = urlsplit(server)
    if not sources.get('environments') or parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        evidence['errors'].append('Configure environment-sources.json and ARGOCD_SERVER (HTTPS); no readiness is assumed')
    else:
        github = argo = None
        try:
            github = github_http()
            argo = httpx.Client(base_url=server, headers={'Authorization': 'Bearer ' + os.environ.get('ARGOCD_TOKEN', '')}, timeout=20)
            repo = manifest.infra_repo
            info = github.get(f'/repos/{repo}').json()
            head = github.get(f"/repos/{repo}/commits/{info['default_branch']}").json()['sha']
            ci = readiness.check_ci(project)
            evidence['ci_ready'] = bool(manifest.ci_repos) and all(ci.get(r, {}).get('success') is True for r in manifest.ci_repos)
            for env in manifest.environments:
                errors = []
                row = {'ready': False, 'errors': errors, 'head_sha': head}
                evidence['environments'][env] = row
                try:
                    config = sources['environments'][env]
                    number = int(config['pull_request'])
                    if number <= 0:
                        raise ValueError('Invalid pull request')
                    pr = github.get(f'/repos/{repo}/pulls/{number}').json()
                    if not pr.get('merged_at') or not pr.get('merge_commit_sha'):
                        errors.append('Infrastructure PR is not merged')
                    else:
                        tree = github.get(f"/repos/{repo}/git/trees/{pr['merge_commit_sha']}", params={'recursive': '1'}).json()
                        blobs = {r['path']: r.get('sha') for r in tree.get('tree', []) if r['type'] == 'blob'}
                        if tree.get('truncated'):
                            errors.append('Cannot prove rendered files match a truncated repository tree')
                        for entry in manifest.files:
                            if not entry.path.startswith('repo/'):
                                continue
                            data = files.path(project, 'infra/' + entry.path).read_bytes()
                            blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
                            if blobs.get(entry.path.removeprefix('repo/')) != blob:
                                errors.append('Merged PR differs from generated file ' + entry.path)
                        comparison = github.get(f"/repos/{repo}/compare/{pr['merge_commit_sha']}...{head}").json()
                        if comparison.get('status') not in ('ahead', 'identical'):
                            errors.append('Current infra head does not descend from the merged change')
                    statuses = github.get(f"/repos/{repo}/commits/{pr['head']['sha']}/status").json().get('statuses', [])
                    context = config['apply_context']
                    latest = next((r for r in statuses if r['context'] == context), None)
                    if not context or not latest or latest.get('state') != 'success':
                        errors.append('No successful Atlantis apply evidence for this environment')
                    apps = [infra.ident(c.name).replace('_', '-') + '-' + env for c in intent.components if 'k8s_workload' in c.needs]
                    if not apps:
                        errors.append('No workload applications to verify')
                    for app in apps:
                        response = argo.get('/api/v1/applications/' + app)
                        response.raise_for_status()
                        status = response.json().get('status', {})
                        revisions = status.get('sync', {}).get('revisions') or [status.get('sync', {}).get('revision')]
                        if status.get('health', {}).get('status') != 'Healthy' or status.get('sync', {}).get('status') != 'Synced' or head not in revisions:
                            errors.append(app + ': not healthy and synced to the current infra head')
                    row.update(ready=not errors, pull_request=number, applications=apps)
                except Exception as exc:
                    errors.append('Read-only evidence check failed: ' + type(exc).__name__)
            evidence['ready'] = evidence['ci_ready'] and bool(evidence['environments']) and all(r['ready'] for r in evidence['environments'].values())
        except Exception as exc:
            evidence['errors'].append('Read-only evidence check failed: ' + type(exc).__name__)
        finally:
            if github is not None:
                github.close()
            if argo is not None:
                argo.close()
    files.write_json(project, EVIDENCE, evidence)
    if files.exists(project, files.INFRA_CHECKS):
        from agent_engine.phase4.contracts import CheckResult
        checks = [CheckResult.model_validate(c) for c in files.read_json(project, files.INFRA_CHECKS)]
        files.write_text(project, files.INFRA_PR, infra.render_pr(project, manifest, checks, intent))
    return evidence
