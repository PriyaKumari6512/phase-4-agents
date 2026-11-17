"""One structured model call: the shared, cacheable system prefix plus the per-item request, parsed into a schema.

Used by the stages the engine drives in code (Task Breakdown, Sprint Planning) instead of a tool-using agent loop.
The active stage budget, when there is one, is checked before every call.
"""
from __future__ import annotations

import asyncio

from langchain_core.messages import HumanMessage, SystemMessage


async def invoke(schema, system: str, human: str, callbacks, spec: str):
    """One structured call. The system text is sent as a cached block for Anthropic models (prompt caching)."""
    from agent_engine.agent import close_agent
    from agent_engine.model_setup import resolve_model_with_retries
    from agent_engine.stage_controls import active_stage_budget
    from types import SimpleNamespace
    budget = active_stage_budget.get()
    if budget:
        budget.check()
    model = resolve_model_with_retries(spec)
    if hasattr(model, "max_tokens"):
        model.max_tokens = min(getattr(model, "max_tokens", None) or 16000, 16000)
    anthropic = spec.startswith("anthropic:")
    system_message = SystemMessage(content=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
                                   if anthropic else system)
    try:
        operation = model.with_structured_output(schema, **({"method": "json_schema"} if anthropic else {}))
        timeout = min(budget.remaining(), 900) if budget else 900
        result = await asyncio.wait_for(operation.ainvoke([system_message, HumanMessage(content=human)],
                                                          config={"callbacks": callbacks}), timeout=timeout)
        return schema.model_validate(result)
    finally:
        await close_agent(SimpleNamespace(_agent_engine_models=[model]))
