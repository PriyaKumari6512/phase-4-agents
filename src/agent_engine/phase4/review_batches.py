"""Batch review obligations without dropping evidence or coverage identities."""
import copy
import json


def size(value):
    return len(json.dumps(value, ensure_ascii=False, separators=(',', ':'), default=str))


def batches(jobs, target=64000):
    pending, ids, sources = [], [], {}

    def add(kind, required, payload, parts, all_ids, evidence):
        payload = copy.deepcopy(payload)
        scoped = payload.pop('sources', {})
        refs = {}
        for path, sections in scoped.items():
            refs[path] = []
            for section in sections:
                key = (path, section['sha256'], section['start'], section['end'])
                evidence[key] = section
                refs[path].append({'sha256': section['sha256'], 'start': section['start'], 'end': section['end']})
        parts.append({'kind': kind, 'required_review_ids': required, 'source_refs': refs, **payload})
        all_ids.extend(i for i in required if i not in all_ids)

    def result(parts, all_ids, evidence):
        grouped = {}
        for (path, _, _, _), section in evidence.items():
            grouped.setdefault(path, []).append(section)
        return ('partition', all_ids, {'parts': parts, 'sources': grouped})

    for kind, required, payload in jobs:
        if kind == 'global':
            if pending:
                yield result(pending, ids, sources)
                pending, ids, sources = [], [], {}
            yield kind, required, payload
            continue
        parts, next_ids, evidence = copy.deepcopy(pending), list(ids), dict(sources)
        add(kind, required, payload, parts, next_ids, evidence)
        if pending and size(result(parts, next_ids, evidence)[2]) > target:
            yield result(pending, ids, sources)
            pending, ids, sources = [], [], {}
        add(kind, required, payload, pending, ids, sources)
    if pending:
        yield result(pending, ids, sources)
