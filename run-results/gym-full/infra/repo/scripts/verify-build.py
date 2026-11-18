"""Verify the source run and its recorded digest before a dev promotion."""
import io
import json
import os
import subprocess
import zipfile
from pathlib import Path

inventory = json.loads(Path('promotion.json').read_text())
component, repo, run_id = (os.environ[n] for n in ('COMPONENT', 'SOURCE_REPO', 'SOURCE_RUN'))
if inventory['repositories'].get(component) != repo or not run_id.isdigit():
    raise ValueError('Unknown build source')

def api(path):
    return subprocess.check_output(['gh', 'api', path])

run = json.loads(api(f'repos/{repo}/actions/runs/{run_id}'))
if run['head_branch'] != 'main' or run['event'] != 'push' or run['conclusion'] != 'success' or run['path'] != f'.github/workflows/ci-{component}.yml':
    raise ValueError('Source must be a successful main CI push run')
artifacts = json.loads(api(f'repos/{repo}/actions/runs/{run_id}/artifacts'))['artifacts']
artifact = next(a for a in artifacts if a['name'] == f'image-{component}' and not a['expired'])
with zipfile.ZipFile(io.BytesIO(api(f"repos/{repo}/actions/artifacts/{artifact['id']}/zip"))) as z:
    metadata = json.loads(z.read('image.json'))
if metadata['digest'] != os.environ['DIGEST'] or metadata['sha'] != run['head_sha']:
    raise ValueError('Digest does not match the source build artifact')
