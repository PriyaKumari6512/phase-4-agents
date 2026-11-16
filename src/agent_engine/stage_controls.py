"""Task Breakdown ownership and shared execution budgets.

The state belongs to one CLI invocation, not a model graph. Context variables
keep sibling helper scopes isolated while all calls charge the same budget.
"""
from __future__ import annotations

import asyncio
import contextvars
import json
import math
import os
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage
from langchain_core.callbacks import BaseCallbackHandler

from agent_engine import config, perf


class StageBudgetExceeded(RuntimeError):
    """Generation stopped with reviewable partial artifacts, never approval."""


@dataclass(frozen=True)
class HelperScope:
    role: str
    project: str
    feature_directory: str = ""
    epic_id: str = ""


helper_scope: contextvars.ContextVar[HelperScope | None] = contextvars.ContextVar("breakdown_helper_scope", default=None)
active_stage_budget: contextvars.ContextVar["StageBudget | None"] = contextvars.ContextVar("breakdown_budget", default=None)


def _number(name: str, default: float, *, integer=False):
    value = os.environ.get(name, str(default))
    parsed = int(value) if integer else float(value)
    if parsed <= 0 or not math.isfinite(parsed):
        raise ValueError(f"{name} must be positive and finite")
    return parsed


@dataclass
class StageBudget:
    max_calls: int
    max_input_tokens: int
    max_output_tokens: int
    seconds: float
    max_helpers: int
    max_same_handoff: int
    started: float = field(default_factory=time.monotonic)
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    helpers: int = 0
    active_helpers: int = 0
    stopped: str | None = None
    handoffs: dict[str, int] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    callback_accounting: bool = False

    @classmethod
    def from_env(cls):
        return cls(_number("AGENT_ENGINE_BREAKDOWN_MAX_CALLS", 1000, integer=True),
                   _number("AGENT_ENGINE_BREAKDOWN_MAX_INPUT_TOKENS", 30000000, integer=True),
                   _number("AGENT_ENGINE_BREAKDOWN_MAX_OUTPUT_TOKENS", 2000000, integer=True),
                   _number("AGENT_ENGINE_BREAKDOWN_TIMEOUT_SECONDS", 7200),
                   _number("AGENT_ENGINE_BREAKDOWN_MAX_HELPERS", 128, integer=True),
                   _number("AGENT_ENGINE_BREAKDOWN_MAX_SAME_HANDOFF", 3, integer=True))

    def remaining(self):
        return max(0, self.seconds - (time.monotonic() - self.started))

    def _check(self):
        if self.stopped:
            raise StageBudgetExceeded(self.stopped)
        if self.remaining() <= 0:
            self.stopped = "Task Breakdown stage deadline exhausted"
            raise StageBudgetExceeded(self.stopped)

    def check(self):
        with self.lock:
            self._check()

    def stop(self, reason: str):
        with self.lock:
            if self.stopped is None:
                self.stopped = reason

    def check_parent_mutation(self):
        with self.lock:
            self._check()
            if self.active_helpers:
                raise ValueError("wait for active Task Breakdown helpers before changing shared inputs or rebuilding the backlog")

    def begin_call(self):
        with self.lock:
            self._check()
            if (self.calls >= self.max_calls or self.input_tokens >= self.max_input_tokens
                    or self.output_tokens >= self.max_output_tokens):
                self.stopped = "Task Breakdown model-call or reported-token budget exhausted"
                raise StageBudgetExceeded(self.stopped)
            self.calls += 1

    def record(self, response):
        # Provider totals are cumulative across calls, not unique input text.
        result = getattr(response, "model_response", response)
        messages = getattr(result, "result", None)
        if messages is None:
            messages = [result]
        with self.lock:
            for message in messages:
                usage = getattr(message, "usage_metadata", None) or {}
                self.input_tokens += usage.get("input_tokens", 0) or 0
                self.output_tokens += usage.get("output_tokens", 0) or 0

    def begin_helper(self, description: str):
        with self.lock:
            self._check()
            count = self.handoffs.get(description, 0)
            if self.helpers >= self.max_helpers or count >= self.max_same_handoff:
                self.stopped = "Task Breakdown helper budget or repeated identical handoff limit exhausted"
                raise StageBudgetExceeded(self.stopped)
            self.helpers += 1
            self.active_helpers += 1
            self.handoffs[description] = count + 1

    def end_helper(self):
        with self.lock:
            self.active_helpers -= 1

    def summary(self):
        return {"model_calls": self.calls, "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens, "helpers": self.helpers, "active_helpers": self.active_helpers,
                "elapsed_seconds": round(time.monotonic() - self.started, 3),
                "stopped": self.stopped, "max_calls": self.max_calls,
                "max_input_tokens": self.max_input_tokens, "max_output_tokens": self.max_output_tokens,
                "max_helpers": self.max_helpers, "max_same_handoff": self.max_same_handoff,
                "timeout_seconds": self.seconds,
                "token_limit_scope": "Provider-reported tokens; concurrent in-flight calls may overshoot. Missing usage cannot be charged."}


class StageBudgetMiddleware(AgentMiddleware):
    async def awrap_model_call(self, request, handler):
        budget = active_stage_budget.get()
        if budget is None:
            return await handler(request)
        if not budget.callback_accounting:
            budget.begin_call()
        try:
            response = await asyncio.wait_for(handler(request), timeout=budget.remaining())
        except asyncio.TimeoutError as exc:
            budget.stopped = "Task Breakdown stage deadline exhausted during model call"
            raise StageBudgetExceeded(budget.stopped) from exc
        if not budget.callback_accounting:
            budget.record(response)
        perf.event("budget", "task_breakdown", **budget.summary())
        return response


class StageBudgetCallback(BaseCallbackHandler):
    """Includes internal summarizer calls that bypass agent model middleware."""
    run_inline = True
    raise_error = True

    def __init__(self, budget: StageBudget):
        self.budget = budget

    def on_chat_model_start(self, serialized, messages, **kwargs):
        self.budget.begin_call()

    def on_llm_end(self, response, **kwargs):
        for group in getattr(response, "generations", []) or []:
            for generation in group:
                message = getattr(generation, "message", None)
                if message is not None:
                    self.budget.record(message)


def helper_write_allowed(project: str, relative_path: str) -> bool:
    budget = active_stage_budget.get()
    if budget is not None:
        budget.check()
    scope = helper_scope.get()
    if scope is None:
        if budget is not None and budget.active_helpers:
            return False
        return True
    if scope.project != project or scope.role != "speckit-feature":
        return False
    path = PurePosixPath(relative_path)
    return not (".." in path.parts) and path.is_relative_to(PurePosixPath(scope.feature_directory))


def _handoff(role: str, description: str) -> tuple[HelperScope, str]:
    from agent_engine.runtime import active_project
    data = json.loads(description)
    if not isinstance(data, dict) or data.get("project") != active_project.get():
        raise ValueError("handoff project must equal the active project")
    project = data["project"]
    root = config.OUTPUTS_DIR / project
    features = json.loads((root / "backlog/features.json").read_text(encoding="utf-8"))["features"]
    if role == "speckit-feature":
        directory = data.get("feature_directory", "")
        if not isinstance(directory, str) or not re.fullmatch(r"specs/[0-9]{3}-[a-z0-9][a-z0-9-]*", directory):
            raise ValueError("handoff requires a registered specs/NNN-name feature_directory")
        if directory not in {f["feature_dir"] for f in features}:
            raise ValueError("feature_directory is not registered in backlog/features.json")
        scope = HelperScope(role, project, feature_directory=directory)
    elif role == "backlog-enricher":
        epic_id = data.get("epic_id", "")
        backlog = json.loads((root / "backlog/backlog.json").read_text(encoding="utf-8"))
        epic = next((i for i in backlog["items"] if i["item_id"] == epic_id and i["level"] == "epic"), None)
        if epic is None:
            raise ValueError("handoff requires an existing epic_id")
        directory = (epic.get("speckit_ref") or "").rsplit("/", 1)[0]
        if directory not in {f["feature_dir"] for f in features}:
            raise ValueError("epic is not linked to a registered feature")
        scope = HelperScope(role, project, epic_id=epic_id)
    else:
        raise ValueError("Task Breakdown permits only speckit-feature and backlog-enricher helpers")
    return scope, json.dumps(data, sort_keys=True, ensure_ascii=False)


class BreakdownHandoffMiddleware(AgentMiddleware):
    async def awrap_tool_call(self, request, handler):
        name = request.tool.name if request.tool else request.tool_call["name"]
        if name != "task":
            return await handler(request)
        args = request.tool_call.get("args", {})
        try:
            scope, identity = _handoff(args.get("subagent_type", ""), args.get("description", ""))
        except (ValueError, TypeError, KeyError, OSError) as exc:
            return ToolMessage(content=f"ERROR: invalid Task Breakdown handoff: {exc}. Pass description as a JSON object with project and feature_directory or epic_id.",
                               tool_call_id=request.tool_call["id"])
        budget = active_stage_budget.get()
        if budget:
            budget.begin_helper(identity)
        token = helper_scope.set(scope)
        try:
            return await handler(request)
        finally:
            helper_scope.reset(token)
            if budget:
                budget.end_helper()
