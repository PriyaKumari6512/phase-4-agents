"""Checked intent extraction and bounded repairs around the golden-path renderer."""
from __future__ import annotations
import hashlib
import json
import re
from contextlib import contextmanager
from contextvars import ContextVar
from langchain_core.messages import AIMessage
from pydantic import BaseModel, ConfigDict
from agent_engine.phase4 import files, infra
from agent_engine.phase4.contracts import InfraIntent, InfraManifest
from agent_engine.phase4.structured import invoke as _invoke

_tier = ContextVar('infra_tier', default='strong')
_TF_BLOCK = re.compile(r'(?m)^\s*(?:(resource|module|data|variable|output|provider)((?:\s+"[^"]+")+)|(locals|terraform)())\s*\{')


def removed_blocks(before: str, after: str) -> list[str]:
    """Terraform blocks present before a repair and missing after it. A repair fixes findings in place; it never
    deletes infrastructure (an empty file is valid Terraform and would silently 'pass' every scanner)."""
    def blocks(text):
        return {f"{kind or bare}{names or empty}".replace('"', '').strip()
                for kind, names, bare, empty in _TF_BLOCK.findall(text)}
    return sorted(blocks(before) - blocks(after))

class Edit(BaseModel):
    """One targeted fix: replace the exact text `find` (it must occur once in the file) with `replace`."""
    model_config = ConfigDict(extra='forbid')
    path: str
    find: str
    replace: str


MAX_EDIT_LINES, MAX_EDITS = 40, 12


def apply_edits(content: dict[str, str], edits: list[Edit]) -> tuple[dict[str, str], list[str]]:
    """Apply targeted edits to copies of `content`. Returns (new contents, errors); nothing is written here."""
    out, errors = dict(content), []
    if not edits:
        return out, ['Return at least one targeted edit']
    if len(edits) > MAX_EDITS:
        errors.append(f'At most {MAX_EDITS} edits per repair; report the rest instead of rewriting files')
    for e in edits:
        if e.path not in out:
            errors.append(f'{e.path}: edit only the supplied failing files')
            continue
        if not e.find.strip():
            errors.append(f'{e.path}: `find` must quote the exact text to change')
            continue
        if max(e.find.count('\n'), e.replace.count('\n')) + 1 > MAX_EDIT_LINES:
            errors.append(f'{e.path}: each edit may change at most {MAX_EDIT_LINES} lines; make a smaller, targeted fix')
            continue
        found = out[e.path].count(e.find)
        if found != 1:
            errors.append(f'{e.path}: `find` must occur exactly once (found {found} times); quote more context')
            continue
        out[e.path] = out[e.path].replace(e.find, e.replace, 1)
    return out, errors

class Repairs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    edits: list[Edit]

class SemanticFinding(BaseModel):
    model_config = ConfigDict(extra='forbid')
    component_id: str
    blocking: bool
    message: str

class SemanticReview(BaseModel):
    model_config = ConfigDict(extra='forbid')
    findings: list[SemanticFinding]

@contextmanager
def operation_model(pack, level):
    token = _tier.set(pack.models[level])
    try:
        yield
    finally:
        _tier.reset(token)

async def _call(project, schema, rules, payload, callbacks, check):
    from agent_engine.agent import model_spec
    from agent_engine.runtime import atomic_json
    spec = model_spec(_tier.get())
    key = hashlib.sha256(json.dumps([schema.model_json_schema(), rules, payload, spec], sort_keys=True).encode()).hexdigest()
    target = files.path(project, f'.engine-infra-pipeline/{key}.json')
    if target.exists():
        result = schema.model_validate_json(target.read_text())
        if not check(result):
            return result
    errors = []
    for _ in range(2):
        result = await _invoke(schema, rules, json.dumps({'input': payload, 'errors': errors}), callbacks, spec)
        errors = check(result)
        if not errors:
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_json(target, result.model_dump(mode='json'))
            return result
    raise files.ProjectError('; '.join(errors))

async def generate(project, request, callbacks=None):
    from agent_engine.agent import load_pack
    architecture = files.read_text(project, files.ARCHITECTURE)
    if any(p.search(architecture) for p in infra.SECRET_PATTERNS):
        raise files.ProjectError('Architecture contains secret-like literals; remove them before model extraction')
    def check(intent):
        try:
            infra.set_intent(project, intent.model_dump(mode='json'))
            if intent.environments != ['dev', 'qa', 'stg', 'prod']:
                return ['Provide dev, qa, stg and prod in promotion order']
            return []
        except files.ProjectError as exc:
            return [str(exc)]
    settings = files.read_json(project, files.PROJECT_SETTINGS)
    payload = {'architecture': architecture, 'request': request,
               'code_repos': settings.get('code_repos', []), 'catalog': infra.load_catalog()}
    rules = load_pack('infra-pipeline').system_prompt + '\nApproved architecture:\n' + architecture + '\nCatalog:\n' + json.dumps(infra.load_catalog(), sort_keys=True)
    payload.pop('architecture')
    payload.pop('catalog')
    await _call(project, InfraIntent, rules, payload, callbacks, check)
    infra.render(project)
    result = json.loads(infra.validate(project))
    return {'messages': [AIMessage(content=json.dumps(result))]}

async def review(project, callbacks=None):
    from agent_engine.agent import Verdict, load_pack
    checked = json.loads(infra.check(project))
    intent = files.read_json(project, files.INFRA_INTENT, InfraIntent)
    flags = {c.component_id: c.model_dump(mode='json') for c in intent.components
             if (c.public_endpoint and 'public_endpoint' not in c.needs) or (c.kind == 'worker' and c.exposes_http)}
    if checked['ok'] and flags:
        def valid(result):
            return ['Review names an unflagged component'] if any(f.component_id not in flags for f in result.findings) else []
        result = await _call(project, SemanticReview, load_pack('infra-pipeline/validator').system_prompt,
                             {'flagged_components': flags, 'architecture': files.read_text(project, files.ARCHITECTURE)}, callbacks, valid)
        checked['problems'].extend(f'{f.component_id}: {f.message}' for f in result.findings if f.blocking)
        checked['ok'] = not checked['problems']
    # Scanner and policy results already identify concrete failures. Operational gaps go to the human lead.
    verdict = Verdict(satisfied=checked['ok'], status_so_far='success' if checked['ok'] else 'partial',
                      gaps=checked['problems'], summary='; '.join(checked['problems'] or ['Static checks passed; DevOps Lead and Solution Architect review operational gaps and readiness evidence.']))
    return {'structured_response': verdict, 'messages': [AIMessage(content=verdict.summary)]}

async def repair(project, gaps, callbacks=None):
    checked = json.loads(infra.check(project))
    if checked['ok']:
        return await review(project, callbacks)
    manifest = files.read_json(project, files.INFRA_MANIFEST, InfraManifest)
    if manifest.validation_complete is not True:
        raise files.ProjectError('Required scanners are unavailable/incomplete; repair paused for DevOps Lead')
    checks = files.read_json(project, files.INFRA_CHECKS)
    named = {f.get('file') for c in checks if not c.get('passed') for f in c.get('findings', []) if f.get('file')}
    candidates = [f for f in manifest.files if any(f.path.endswith(n) for n in named)]
    if not candidates:
        raise files.ProjectError('No specific failing generated files identified; DevOps Lead must resolve the findings')
    content = {f.path: files.read_text(project, 'infra/' + f.path) for f in candidates}
    if any(p.search(text) for text in content.values() for p in infra.SECRET_PATTERNS):
        raise files.ProjectError('Secret-like generated content requires human removal before repair')
    def check(result):
        new, errors = apply_edits(content, result.edits)
        if errors:
            return errors
        if new == content:
            return ['Repair must change the failing content']
        if any(p.search(e.replace) for e in result.edits for p in infra.SECRET_PATTERNS):
            return ['Secrets must remain references only']
        removed = {path: removed_blocks(content[path], new[path]) for path in new if path.endswith('.tf')}
        removed = {path: gone for path, gone in removed.items() if gone}
        if removed:
            return [f'Fix findings in place; never delete infrastructure. {path} drops: '
                    + ', '.join(gone[:10]) for path, gone in removed.items()]
        return []
    result = await _call(project, Repairs,
                         'Make small, targeted edits to the supplied generated files to resolve the scanner findings. '
                         'Each edit replaces the exact text `find` (quoted from the file, occurring once) with `replace`; '
                         f'at most {MAX_EDITS} edits of at most {MAX_EDIT_LINES} lines. Never return whole files. '
                         'Preserve the catalog topology, digest promotion, approvals and secret references. Findings '
                         'that need a design decision are left for the DevOps Lead, not rewritten.',
                         {'files': content, 'gaps': gaps, 'checks': [c for c in checks if not c.get('passed')]}, callbacks, check)
    new, _ = apply_edits(content, result.edits)
    for path, text in new.items():
        if text != content[path]:
            files.write_text(project, 'infra/' + path, text)
    return {'messages': [AIMessage(content=infra.validate(project))]}
