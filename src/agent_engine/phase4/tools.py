"""Phase 4 tools, registered in agent.TOOLS under the names a pack lists in `tools = [...]`.

Every tool takes `project` (the <project-name> in /outputs/<project-name>/), reads and writes only that project's
files, returns JSON text, and returns "ERROR: ..." instead of raising so the model can correct itself.
Validators get the read-only `*-check` sets.
"""

from __future__ import annotations

import logging
import json
import hashlib
from typing import Callable

from langchain_core.tools import tool

from agent_engine import perf
from agent_engine.phase4 import files

logger = logging.getLogger(__name__)


def _run(name: str, fn: Callable[[], str]) -> str:
    from agent_engine.stage_controls import active_stage_budget
    if (budget := active_stage_budget.get()) is not None:
        budget.check()
    with perf.span("tool_exec", name, tool=name) as sp:
        try:
            result = fn()
        except files.ProjectError as e:
            result = f"ERROR: {e}"
            sp.set_status("domain_error", result, "project_error")
        except Exception as e:  # a tool bug must reach the model as text, not crash the run
            logger.exception("phase4 tool failed")
            result = f"ERROR: {type(e).__name__}: {e}"
            sp.set_status("domain_error", result, "tool_exception:" + perf.classify_error(e))
        original_chars = len(result)
        # Whitespace is not domain data. Keep every field and error, but avoid paying
        # for pretty-printing these JSON responses on every subsequent model turn.
        try:
            result = json.dumps(json.loads(result), ensure_ascii=False, separators=(",", ":"))
        except (ValueError, TypeError):
            pass
        sp.set(output_chars=len(result), original_output_chars=original_chars)
        return result


# ============================================================================ backlog (read-only)
@tool
def backlog_view(project: str, epic_id: str = "", level: str = "", item_ids: list[str] | None = None,
                 offset: int = 0, limit: int = 100, details: bool = True,
                 max_chars: int = 24000, expected_sha256: str = "") -> str:
    """Read exact backlog records scoped to one epic, level or item IDs. Paginated; never silently truncates.
    Use details=false for a compact planning index; details=true includes every field of selected items.
    Follow next_offset until null. max_chars bounds item payload (one oversized item is returned whole).
    expected_sha256 optionally rejects pages from a changed snapshot; restart pagination if it changes.
    This avoids repeatedly reading the complete backlog JSON for one feature's work."""
    def view():
        from agent_engine.phase4.contracts import Backlog
        selected_epic = epic_id
        # Hash exactly the bytes parsed, not a second read that may race enrichment.
        raw = files.path(project, files.BACKLOG).read_bytes()
        b = Backlog.model_validate_json(raw)
        if not 1000 <= max_chars <= 200000:
            raise files.ProjectError("max_chars must be between 1000 and 200000")
        if offset < 0 or not 1 <= limit <= 200 or level not in ("", "epic", "story", "task"):
            raise files.ProjectError("offset must be >=0, limit 1..200, level epic/story/task or empty")
        children = {i.item_id for i in b.items if i.parent_id == selected_epic}
        rows = [i for i in b.items if (not selected_epic or i.item_id == selected_epic or i.parent_id == selected_epic or i.parent_id in children)
                and (not level or i.level == level) and (not item_ids or i.item_id in item_ids)]
        digest = (hashlib.sha256(raw).hexdigest() if not (selected_epic or level or item_ids) else
                  hashlib.sha256(json.dumps([i.model_dump(mode="json") for i in rows],
                                             sort_keys=True).encode()).hexdigest())
        if expected_sha256 and expected_sha256 != digest:
            raise files.ProjectError("selected backlog records changed since the previous page; restart pagination")
        page = rows[offset:offset + limit]
        compact = ("item_id", "level", "parent_id", "title", "priority", "moscow", "estimate", "dependencies", "source_refs", "open_questions")
        selected, size = [], 2
        for item in page:
            value = item.model_dump(mode="json") if details else item.model_dump(mode="json", include=set(compact))
            length = len(json.dumps(value, ensure_ascii=False, separators=(",", ":"))) + 1
            if selected and size + length > max_chars:
                break
            selected.append(value)
            size += length
        end = offset + len(selected)
        return json.dumps({"backlog_sha256": digest, "total": len(rows),
                           "next_offset": end if end < len(rows) else None,
                           "oversized_item": size > max_chars, "items": selected})
    return _run("backlog_view", view)


_ALL = [backlog_view]

def _invalid_arguments(error: Exception) -> str:
    return f"ERROR: invalid arguments: {error}"

for _t in _ALL:
    _t.handle_validation_error = _invalid_arguments
    _t.handle_tool_error = True

TOOL_FACTORIES: dict[str, Callable[[], list]] = {}
