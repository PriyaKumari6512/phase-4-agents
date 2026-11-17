"""Exact source sections with conservative inclusion of unclassified constraints."""
import hashlib
import re
from agent_engine.phase4 import files
from agent_engine.phase4.speckit_parse import REQ_ID_RE

SOURCES = (files.PRD, files.ARCHITECTURE, 'requests/task-breakdown.md',
           'backlog/implementation-contract.md', '.specify/memory/constitution.md', '.specify/engine-policy.json')


def digest(value):
    import json
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def packet(project, requirement_ids=()):
    selected = set(requirement_ids)
    output = {}
    for source in SOURCES:
        if not files.exists(project, source):
            continue
        text = files.read_text(project, source)
        # Architecture and requests can encode implicit/global dependencies: retain
        # them in full until explicit applicability is available. PRD headings with
        # unrelated numbered functional requirements can be excluded conservatively.
        pieces = re.split(r'(?m)(?=^#{1,6} )', text)
        sections = []
        offset = 0
        for piece in pieces:
            ids = set(REQ_ID_RE.findall(piece))
            explicit_local = ids and all(i.startswith(('FR-', 'US-')) for i in ids)
            if source != files.PRD or not selected or not explicit_local or ids & selected:
                sections.append({'start': offset, 'end': offset + len(piece), 'text': piece,
                                 'sha256': hashlib.sha256(piece.encode()).hexdigest()})
            offset += len(piece)
        output[source] = sections
    return output
