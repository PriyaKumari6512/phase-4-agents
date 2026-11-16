"""Cross-agent file locking: one GLOBAL asyncio.Lock across every
write_file/edit_file/delete call, not one lock per file path.

Per-path locking was tried first and didn't hold: two different files landing
in the same brand-new directory at the same time can race on Windows'
directory-creation/path-resolution, crashing the run even though the two
calls have different lock keys. A single global lock removes that race
outright, at negligible cost — writes are small next to model/network
latency.
"""

from __future__ import annotations

import asyncio
import os
import logging
import time
from typing import Any, Awaitable, Callable

from langchain.agents.middleware import AgentMiddleware, ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.types import Command

from agent_engine import perf
from agent_engine.config import FILE_LOCK_ACQUIRE_TIMEOUT_SECONDS, MUTATING_FILESYSTEM_TOOLS

logger = logging.getLogger(__name__)


class HelperLimitMiddleware(AgentMiddleware):
    """Bound task fan-out without serializing ordinary reads."""
    def __init__(self, limit: int | None = None):
        limit = limit if limit is not None else int(os.environ.get("AGENT_ENGINE_HELPER_CONCURRENCY", "9"))
        if not 1 <= limit <= 32:
            raise ValueError("AGENT_ENGINE_HELPER_CONCURRENCY must be between 1 and 32")
        self.limit = limit
        self.active = 0
        self.peak = 0
        self.slots = asyncio.Semaphore(limit)

    async def awrap_tool_call(self, request, handler):
        name = request.tool.name if request.tool else request.tool_call["name"]
        if name == "task":
            started = time.perf_counter()
            async with self.slots:
                acquired = time.perf_counter()
                self.active += 1
                self.peak = max(self.peak, self.active)
                try:
                    return await handler(request)
                finally:
                    self.active -= 1
                    perf.event("concurrency", "helper_slot", limit=self.limit, peak=self.peak,
                               active=self.active, wait_s=round(acquired - started, 6),
                               hold_s=round(time.perf_counter() - acquired, 6))
        return await handler(request)

# Module-level, not per-instance, so every subagent's own FileLockMiddleware
# shares this one lock with the main agent.
_global_lock = asyncio.Lock()


class FileLockMiddleware(AgentMiddleware):
    """Serializes write_file/edit_file/delete across the whole run onto one
    global lock — see module docstring. Read-only tools and execute pass
    through untouched.
    """

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        tool_name = request.tool.name if request.tool else request.tool_call["name"]
        if tool_name not in MUTATING_FILESYSTEM_TOOLS:
            return await handler(request)

        file_path = request.tool_call["args"].get("file_path", "<unknown>")

        t_wait = time.perf_counter()
        try:
            await asyncio.wait_for(_global_lock.acquire(), timeout=FILE_LOCK_ACQUIRE_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            logger.warning("%s on %s timed out waiting for the file lock", tool_name, file_path)
            perf.event("lock", "file_lock", tool=tool_name, wait_s=round(time.perf_counter() - t_wait, 4),
                       acquired=False)
            return ToolMessage(
                content=(
                    f"ERROR: the filesystem lock stayed held by another agent for "
                    f"{FILE_LOCK_ACQUIRE_TIMEOUT_SECONDS}s while waiting to {tool_name} {file_path}. "
                    "Retry this call."
                ),
                tool_call_id=request.tool_call["id"],
            )

        t_hold = time.perf_counter()
        try:
            logger.info("%s acquired global file lock for %s", tool_name, file_path)
            return await handler(request)
        finally:
            _global_lock.release()
            logger.info("%s released global file lock for %s", tool_name, file_path)
            perf.event("lock", "file_lock", tool=tool_name, wait_s=round(t_hold - t_wait, 4),
                       hold_s=round(time.perf_counter() - t_hold, 4), acquired=True)
