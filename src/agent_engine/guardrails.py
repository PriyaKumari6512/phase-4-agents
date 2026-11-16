"""Hard enforcement that mutating filesystem tools stay under /outputs/, and
out of a project's read-only folders (READ_ONLY_PROJECT_DIRS).

The backend also routes /knowledge/ (a pack's reference docs) to real disk,
and everything else to in-memory scratch state — so write/edit/delete would
only be kept inside /outputs/ by instruction unless this middleware closes
the gap.
"""

from __future__ import annotations

import logging
import posixpath
from typing import Any, Awaitable, Callable

from langchain.agents.middleware import AgentMiddleware, ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.types import Command

from agent_engine.config import MUTATING_FILESYSTEM_TOOLS, OUTPUTS_VIRTUAL_PREFIX, READ_ONLY_PROJECT_DIRS
from agent_engine.logging_setup import notify_job_log_path
from agent_engine.runtime import active_project, active_inputs, managed_outputs

logger = logging.getLogger(__name__)


def _normalize(file_path: str) -> str:
    normalized = file_path.strip().replace("\\", "/")
    return posixpath.normpath("/" + normalized.lstrip("/"))


def _is_under_outputs(file_path: str) -> bool:
    normalized = _normalize(file_path)
    return normalized == OUTPUTS_VIRTUAL_PREFIX.rstrip("/") or normalized.startswith(OUTPUTS_VIRTUAL_PREFIX)


def _is_read_only(file_path: str) -> bool:
    """True for /outputs/<project>/<dir>/... with <dir> in READ_ONLY_PROJECT_DIRS
    (inputs/, gates/, ...), including the folders themselves.
    """
    parts = [p for p in _normalize(file_path).removeprefix(OUTPUTS_VIRTUAL_PREFIX).split("/") if p]
    return len(parts) >= 2 and (parts[1] in READ_ONLY_PROJECT_DIRS or parts[1] == "report.json"
                               or parts[1].startswith(".engine-") or "/".join(parts[1:]) in active_inputs.get() | managed_outputs.get())


def _has_traversal(file_path: str) -> bool:
    """True if `file_path` contains `..` or a leading `~` — the same check
    deepagents' own backend applies, but raised there as an uncaught
    `ValueError` with no `handle_tool_errors` configured on the graph, which
    crashes the whole run instead of giving the model a correctable error.
    Catching it here first, in the same reject-with-a-ToolMessage style as
    the outside-/outputs/ check below, keeps a single malformed path (e.g. a
    subagent abbreviating a long project name with a literal '...') from
    taking down an otherwise-healthy multi-hour job.
    """
    return ".." in file_path or file_path.strip().startswith("~")


class OutputsOnlyGuardMiddleware(AgentMiddleware):
    """Refuses write_file/edit_file/delete calls whose file_path isn't under
    /outputs/, or is inside a project's inputs/ or gates/. Placed before
    FileLockMiddleware so a rejected path never bothers acquiring a lock.
    """

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        tool_name = request.tool.name if request.tool else request.tool_call["name"]
        if tool_name not in MUTATING_FILESYSTEM_TOOLS:
            return await handler(request)

        file_path = request.tool_call["args"].get("file_path")
        if not file_path:
            return await handler(request)
        from agent_engine.stage_controls import helper_write_allowed
        path_parts = _normalize(file_path).removeprefix(OUTPUTS_VIRTUAL_PREFIX).split("/")
        if not helper_write_allowed(path_parts[0], "/".join(path_parts[1:])):
            return ToolMessage(content="ERROR: helper may write only its assigned feature directory; enrichment uses scoped backlog tools.",
                               tool_call_id=request.tool_call["id"])

        if _has_traversal(file_path):
            logger.warning("%s rejected: %r contains '..' or a leading '~'", tool_name, file_path)
            return ToolMessage(
                content=(
                    f"ERROR: refused — {file_path!r} contains '..' or starts with '~'. "
                    "This looks like a malformed or abbreviated path (e.g. an ellipsis "
                    "standing in for the project name) rather than the real "
                    "/outputs/<project-name>/... path. Re-issue this call with the "
                    "exact, full path spelled out — never an abbreviation."
                ),
                tool_call_id=request.tool_call["id"],
            )

        project = active_project.get()
        if project and _is_under_outputs(file_path) and not _normalize(file_path).startswith(f"/outputs/{project}/"):
            return ToolMessage(content=f"ERROR: this run may write only /outputs/{project}/", tool_call_id=request.tool_call["id"])
        if _is_under_outputs(file_path) and _is_read_only(file_path):
            logger.warning("%s rejected: %r is in a read-only project folder", tool_name, file_path)
            return ToolMessage(
                content=(
                    f"ERROR: refused — {file_path!r} is read-only. A project's "
                    f"{', '.join(d + '/' for d in sorted(READ_ONLY_PROJECT_DIRS))} folders are written by "
                    "the engine (uploaded files, human approvals, request history); agents may read them "
                    "but never change them. Write your output to its own file under /outputs/<project-name>/."
                ),
                tool_call_id=request.tool_call["id"],
            )

        if _is_under_outputs(file_path):
            # Earliest point a project directory becomes known.
            notify_job_log_path(file_path)
            return await handler(request)

        logger.warning("%s rejected: %r is outside /outputs/", tool_name, file_path)
        return ToolMessage(
            content=(
                f"ERROR: refused — {file_path!r} is outside /outputs/. Every generated "
                "output file must live under /outputs/"
                "<project-name>/. /knowledge/ is read-only reference material."
            ),
            tool_call_id=request.tool_call["id"],
        )
