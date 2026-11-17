"""Lossless overflow path: exact input pages and incrementally assembled output.

The ordinary typed call remains the fast path. Large inputs/outputs use bounded
read/write tools and context compaction; no source bytes or output fields are
truncated. Completion requires all input pages and the full original schema.
"""
from __future__ import annotations
import copy
import json
from pydantic import ValidationError
from agent_engine.phase4 import files


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), default=str)


class Workspace:
    def __init__(self, schema, payload, page_chars=12000, saved=None, persist=lambda value: None):
        self.schema = schema
        text = encode(payload)
        self.pages = [text[i:i+page_chars] for i in range(0, len(text), page_chars)] or ['{}']
        self.output = copy.deepcopy((saved or {}).get('output', {}))
        self.seen = set((saved or {}).get('seen', []))
        self.persist = persist
        self.page_chars = page_chars
        self.complete = False

    def save(self):
        self.persist({'output': self.output, 'seen': sorted(self.seen)})

    def read(self, page):
        if not 0 <= page < len(self.pages):
            raise ValueError('unknown input page')
        self.seen.add(page)
        self.save()
        return self.pages[page]

    def get(self, path):
        node = self.output
        for key in path:
            node = node[int(key)] if isinstance(node, list) else node[key]
        return node

    def edit(self, path, value, mode):
        if self.complete:
            raise ValueError('operation already completed')
        before = copy.deepcopy(self.output)
        try:
            if not path:
                if mode != 'set' or not isinstance(value, dict):
                    raise ValueError('root must be an object')
                self.output = value
            else:
                node = self.get(path[:-1])
                key = int(path[-1]) if isinstance(node, list) else path[-1]
                if mode == 'set':
                    if isinstance(node, list) and key == len(node):
                        node.append(value)
                    else:
                        node[key] = value
                elif mode == 'append':
                    node[key].append(value)
                elif mode == 'append_text':
                    if not isinstance(node[key], str) or not isinstance(value, str):
                        raise ValueError('append_text requires strings')
                    node[key] += value
                else:
                    raise ValueError('unknown edit mode')
            self.save()
        except BaseException:
            self.output = before
            raise

    def finish(self):
        missing = sorted(set(range(len(self.pages))) - self.seen)
        if missing:
            raise ValueError('unread input pages: ' + str(missing[:30]))
        result = self.schema.model_validate(self.output)
        self.complete = True
        return result


async def run(schema, purpose, payload, callbacks, model, spec, rules):
    from langchain.agents import create_agent
    from langchain_core.tools import tool
    from langchain.agents.middleware import SummarizationMiddleware
    from agent_engine.stage_controls import StageBudgetMiddleware
    from agent_engine.runtime import active_project
    from agent_engine.phase4 import breakdown_workflow as workflow
    from agent_engine.phase4.evidence import digest
    project = active_project.get()
    key = digest({'schema': schema.model_json_schema(), 'payload': payload, 'purpose': purpose,
                  'spec': spec, 'rules': rules, 'version': 1})
    saved = workflow._load(project, 'operations', key) if project else None
    persist = (lambda value: workflow._save(project, 'operations', key, value)) if project else (lambda value: None)
    workspace = Workspace(schema, payload, saved=saved, persist=persist)
    schema_text = encode(schema.model_json_schema())
    schema_pages = [schema_text[i:i+12000] for i in range(0, len(schema_text), 12000)]

    @tool
    def read_input(page: int) -> str:
        """Read an exact numbered page of the immutable input JSON. Read every page."""
        try:
            return workspace.read(page)
        except ValueError as exc:
            return str(exc)

    @tool
    def read_schema(page: int = 0) -> str:
        """Read the complete output schema in numbered pages."""
        return schema_pages[page] if 0 <= page < len(schema_pages) else 'unknown schema page'

    @tool
    def read_output(path: list[str], offset: int = 0) -> str:
        """Read a bounded slice of existing output JSON at a key/index path. Follow next_offset."""
        try:
            if offset < 0:
                raise ValueError('offset must be nonnegative')
            text = encode(workspace.get(path))
            end = min(len(text), offset + 12000)
            return encode({'text': text[offset:end], 'next_offset': end if end < len(text) else None})
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            return 'ERROR: ' + str(exc)

    @tool
    def write_output(path: list[str], value_json: str, mode: str = 'set') -> str:
        """Build output in small pieces. Path is object keys/list indexes; mode set,
        append (one list entry), or append_text (string continuation). Root path [] sets an object.
        Parents must exist. Never rewrite unrelated completed entries."""
        try:
            workspace.edit(path, json.loads(value_json), mode)
            return 'Saved. Output bodies are retained; use read_output only when needed.'
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            return 'ERROR: ' + str(exc)

    @tool
    def complete_output() -> str:
        """Finish only after every source page was read and output is complete. Validates full schema."""
        try:
            workspace.finish()
            return 'COMPLETE'
        except ValidationError as exc:
            return encode({'errors': [{'path': list(e['loc']), 'message': e['msg']} for e in exc.errors()][:30]})
        except ValueError as exc:
            return str(exc)

    # Compaction affects transcript only. Exact input and accumulated output remain
    # available through tools after compaction, and page completion is tracked by code.
    class AllocationMiddleware(StageBudgetMiddleware):
        async def awrap_model_call(self, request, handler):
            workflow.check_allocation(purpose)
            return await super().awrap_model_call(request, handler)

    graph = create_agent(model=model, tools=[read_input, read_schema, read_output, write_output, complete_output],
        system_prompt=rules + '\nOperation: ' + purpose + '\n'
        'This operation is split into exact input pages and incremental output records. '
        'Read all input pages and schema pages. Input pages concatenate to the original JSON; '
        'do not treat a page boundary as a semantic boundary. Review cross-page relationships. '
        'Write output in small entries and string fragments, preserving all needed details. '
        'Use stored output as working memory after compaction. Complete only via complete_output; '
        'never echo the final document in your reply.',
        middleware=[SummarizationMiddleware(model=model, trigger=('tokens', 24000), keep=('messages', 6)),
                    AllocationMiddleware()])
    for attempt in range(2):
        await graph.ainvoke({'messages': [('user', encode({'input_pages': len(workspace.pages),
            'schema_pages': len(schema_pages), 'already_read': sorted(workspace.seen),
            'instruction': 'Continue retained output and complete the operation.'}))]},
            config={'callbacks': callbacks, 'recursion_limit': max(200, 30 * len(workspace.pages))})
        if workspace.complete:
            return workspace.finish()
    raise files.ProjectError('Paged operation did not complete; exact pages and output retained for resume')
