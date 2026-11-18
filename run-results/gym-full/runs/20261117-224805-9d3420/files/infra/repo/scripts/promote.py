"""Update GitOps values with an immutable digest, preserving the promotion chain."""
import argparse
import json
from pathlib import Path
import re
import yaml


def promote(root, component, target, digest=None):
    inventory = json.loads((root / 'promotion.json').read_text())
    if component not in inventory['images'] or target not in inventory['environments']:
        raise ValueError('Unknown component or environment')
    envs = inventory['environments']
    index = envs.index(target)
    members = inventory['images'][component]
    if index:
        before = envs[index - 1]
        digests = {yaml.safe_load((root / f'gitops/apps/{name}/{before}/values.yaml').read_text())['image']['digest'] for name in members}
        if len(digests) != 1:
            raise ValueError('Shared image workloads have different predecessor digests')
        previous = digests.pop()
        if digest and digest != previous:
            raise ValueError('Promotion must use exactly the predecessor digest')
        digest = previous
    if not digest or not re.fullmatch(r'sha256:[0-9a-f]{64}', digest) or digest == 'sha256:' + '0' * 64:
        raise ValueError('A real immutable build digest is required')
    for name in members:
        path = root / f'gitops/apps/{name}/{target}/values.yaml'
        text = path.read_text()
        text, count = re.subn(r'(?m)^  digest:.*$', f'  digest: "{digest}"', text)
        if count != 1:
            raise ValueError('Expected exactly one image digest field')
        path.write_text(text)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('component')
    p.add_argument('target')
    p.add_argument('--digest')
    args = p.parse_args()
    promote(Path('.'), args.component, args.target, args.digest)
