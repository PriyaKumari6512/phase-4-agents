"""Refuse unprotected promotions; environment names alone do not create approvals."""
import json
import os
import subprocess


def verify(target, expected, repo, sha, api):
    if target == 'dev':
        return
    if target not in ('qa', 'stg', 'prod') or not expected.isdigit():
        raise ValueError('Configure the required QA/client/DevOps reviewer ID before promotion')
    environment = api(f'repos/{repo}/environments/{target}')
    reviewers = [r for rule in environment.get('protection_rules', []) if rule.get('type') == 'required_reviewers'
                 and rule.get('prevent_self_review') is True for r in rule.get('reviewers', [])]
    if {int(expected)} != {r['reviewer']['id'] for r in reviewers} or environment.get('can_admins_bypass', True):
        raise ValueError('Required environment reviewer protection is missing or permits bypass')
    if target == 'prod':
        statuses = api(f'repos/{repo}/commits/{sha}/status').get('statuses', [])
        latest = next((s for s in statuses if s.get('context') == 'production/go-no-go'), None)
        if not latest or latest.get('state') != 'success':
            raise ValueError('Production requires a separate successful go/no-go check on this infra revision')


if __name__ == '__main__':
    def api(path):
        return json.loads(subprocess.check_output(['gh', 'api', path]))
    verify(os.environ['TARGET'], os.environ.get('EXPECTED_REVIEWER', ''),
           os.environ['GITHUB_REPOSITORY'], os.environ['GITHUB_SHA'], api)
