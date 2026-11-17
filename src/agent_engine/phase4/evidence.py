"""Exact source sections with conservative inclusion of unclassified constraints."""
import hashlib
import re
from contextvars import ContextVar

frozen_text = ContextVar("breakdown_frozen_sources", default=None)


def source_text(project, source):
    frozen = frozen_text.get()
    if frozen is not None and frozen[0] == project and source in frozen[1]:
        return frozen[1][source]
    return files.read_text(project, source) if files.exists(project, source) else None
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
        text = source_text(project, source)
        if text is None:
            continue
        # Architecture and requests can encode implicit/global dependencies: retain
        # them in full until explicit applicability is available. PRD headings with
        # unrelated numbered functional requirements can be excluded conservatively.
        pieces = re.split(r'(?m)(?=^#{1,6} )', text)
        sections = []
        offset = 0
        for piece in pieces:
            ids = set(REQ_ID_RE.findall(piece))
            # Merely mentioning an ID does not make a section local: a global
            # policy can cite an unrelated requirement as an example.
            heading = piece.split('\n', 1)[0]
            explicit_heading = re.match(r'^#{1,6}\s+(?:\*\*)?(?:FR|US)-\d{1,4}\b', heading)
            explicit_local = bool(explicit_heading) and ids and all(i.startswith(('FR-', 'US-')) for i in ids)
            if source != files.PRD or not selected or not explicit_local or ids & selected:
                sections.append({'start': offset, 'end': offset + len(piece), 'text': piece,
                                 'sha256': hashlib.sha256(piece.encode()).hexdigest()})
            offset += len(piece)
        output[source] = sections
    return output
