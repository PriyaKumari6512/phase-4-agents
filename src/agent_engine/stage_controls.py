"""Task Breakdown's shared execution budget: model calls, reported tokens and a deadline for one CLI invocation.

Every call of the stage (story breakdowns, the cross-story pass, the review, repairs) charges the same budget.
A stopped budget leaves reviewable partial artifacts and never counts as an approval.
"""
from __future__ import annotations

import asyncio
import contextvars
import math
import os
import threading
import time
from dataclasses import dataclass, field

from langchain.agents.middleware import AgentMiddleware
from langchain_core.callbacks import BaseCallbackHandler

from agent_engine import perf


class StageBudgetExceeded(RuntimeError):
    """Generation stopped with reviewable partial artifacts, never approval."""


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
    started: float = field(default_factory=time.monotonic)
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    stopped: str | None = None
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    callback_accounting: bool = False

    @classmethod
    def from_env(cls, stage="task-breakdown"):
        if stage != "task-breakdown":
            prefix = "AGENT_ENGINE_" + stage.upper().replace("-", "_")
            return cls(_number(prefix + "_MAX_CALLS", 16, integer=True),
                       _number(prefix + "_MAX_INPUT_TOKENS", 1000000, integer=True),
                       _number(prefix + "_MAX_OUTPUT_TOKENS", 64000, integer=True),
                       _number(prefix + "_TIMEOUT_SECONDS", 1800))
        return cls(_number("AGENT_ENGINE_BREAKDOWN_MAX_CALLS", 1000, integer=True),
                   _number("AGENT_ENGINE_BREAKDOWN_MAX_INPUT_TOKENS", 30000000, integer=True),
                   _number("AGENT_ENGINE_BREAKDOWN_MAX_OUTPUT_TOKENS", 2000000, integer=True),
                   _number("AGENT_ENGINE_BREAKDOWN_TIMEOUT_SECONDS", 7200))

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

    def summary(self):
        return {"model_calls": self.calls, "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "elapsed_seconds": round(time.monotonic() - self.started, 3),
                "stopped": self.stopped, "max_calls": self.max_calls,
                "max_input_tokens": self.max_input_tokens, "max_output_tokens": self.max_output_tokens,
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
