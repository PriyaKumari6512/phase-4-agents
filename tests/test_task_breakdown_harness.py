"""Task Breakdown's shared stage budget and recovery invariants, without model service calls."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage
from langchain.agents.middleware.types import ModelResponse

from agent_engine import config, model_setup
from agent_engine.stage_controls import (
    StageBudget, StageBudgetExceeded, StageBudgetMiddleware, StageBudgetCallback, active_stage_budget,
)
from test_model_escalation import engine, _script
from test_phase4_pipeline import proj


def budget(**overrides):
    values = dict(max_calls=10, max_input_tokens=1000, max_output_tokens=1000, seconds=10)
    return StageBudget(**(values | overrides))


def usage_message(input_tokens=10, output_tokens=2):
    return AIMessage(content="ok", usage_metadata={"input_tokens": input_tokens,
                     "output_tokens": output_tokens, "total_tokens": input_tokens + output_tokens})


def test_tuning_applies_to_resolved_default_strong_model(monkeypatch):
    monkeypatch.delenv("SDLC_AGENT_STRONG_MODEL", raising=False)
    monkeypatch.setenv("SDLC_AGENT_EFFORT", "low")
    monkeypatch.setattr(model_setup, "resolve_model_tiers", lambda: config.ModelTiers("anthropic:resolved", "anthropic:small"))
    assert model_setup._tuning_kwargs("anthropic:resolved") == {"effort": "low"}
    assert model_setup._tuning_kwargs("anthropic:small") == {}


def test_shared_budget_admission_and_usage_across_middleware_instances():
    async def exercise():
        shared = budget(max_calls=2)
        token = active_stage_budget.set(shared)
        async def handler(request):
            return ModelResponse(result=[usage_message()])
        try:
            await StageBudgetMiddleware().awrap_model_call(None, handler)
            await StageBudgetMiddleware().awrap_model_call(None, handler)
            with pytest.raises(StageBudgetExceeded):
                await StageBudgetMiddleware().awrap_model_call(None, handler)
        finally:
            active_stage_budget.reset(token)
        assert shared.calls == 2 and shared.input_tokens == 20 and shared.output_tokens == 4
    asyncio.run(exercise())


def test_parallel_call_admission_never_exceeds_call_limit():
    async def exercise():
        shared = budget(max_calls=2)
        token = active_stage_budget.set(shared)
        entered = 0
        async def handler(request):
            nonlocal entered
            entered += 1
            await asyncio.sleep(.01)
            return ModelResponse(result=[usage_message()])
        try:
            out = await asyncio.gather(*(StageBudgetMiddleware().awrap_model_call(None, handler) for _ in range(6)),
                                       return_exceptions=True)
        finally:
            active_stage_budget.reset(token)
        assert entered == 2 and sum(isinstance(x, StageBudgetExceeded) for x in out) == 4
    asyncio.run(exercise())


def test_reported_tokens_stop_next_admission_and_callback_counts_internal_calls():
    shared = budget(max_input_tokens=5)
    callback = StageBudgetCallback(shared)
    callback.on_chat_model_start({}, [])
    callback.on_llm_end(SimpleNamespace(generations=[[SimpleNamespace(message=usage_message())]]))
    with pytest.raises(StageBudgetExceeded):
        callback.on_chat_model_start({}, [])
    assert shared.calls == 1 and shared.input_tokens == 10


def test_stage_deadline_cancels_model_work():
    async def exercise():
        shared = budget(seconds=.01)
        token = active_stage_budget.set(shared)
        cleaned = False
        async def handler(request):
            nonlocal cleaned
            try:
                await asyncio.sleep(10)
            finally:
                cleaned = True
        try:
            with pytest.raises(StageBudgetExceeded, match="deadline"):
                await StageBudgetMiddleware().awrap_model_call(None, handler)
        finally:
            active_stage_budget.reset(token)
        assert cleaned
    asyncio.run(exercise())


def test_budget_does_not_affect_other_stages():
    async def exercise():
        async def handler(request):
            return "unchanged"
        assert await StageBudgetMiddleware().awrap_model_call(None, handler) == "unchanged"
    asyncio.run(exercise())


def test_verification_retry_preserves_business_request_history(engine, monkeypatch):
    from agent_engine import cli
    _script(monkeypatch, verdicts=[], fail_on={("judge", "strong")})
    assert asyncio.run(cli._run("original request", "writer", "demo")) == 1
    history = engine / "demo/requests.md"
    before = history.read_bytes()
    _script(monkeypatch, verdicts=[True])
    assert asyncio.run(cli._run("original request", "writer", "demo", resume_verification=True)) == 0
    assert history.read_bytes() == before


def test_cli_budget_exhaustion_is_partial_and_keeps_artifacts(proj, monkeypatch, tmp_path):
    from agent_engine import cli, logging_setup
    monkeypatch.setattr(cli, "OUTPUTS_DIR", proj.parent)
    monkeypatch.setattr(logging_setup, "OUTPUTS_DIR", proj.parent)
    monkeypatch.setattr(logging_setup, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(cli, "build_langfuse_handler", lambda: None)
    monkeypatch.setattr(cli, "model_spec", lambda tier: "test:" + tier)
    monkeypatch.setattr(cli, "build_agent", lambda *a: SimpleNamespace())
    monkeypatch.setenv("AGENT_ENGINE_BREAKDOWN_MAX_CALLS", "1")
    async def stream(graph, message, callbacks, run_name):
        callback = next(c for c in callbacks if isinstance(c, StageBudgetCallback))
        callback.on_chat_model_start({}, [])
        (proj / "retained-partial.md").write_text("completed work")
        callback.on_chat_model_start({}, [])
    monkeypatch.setattr(cli, "_stream", stream)
    from agent_engine.phase4 import task_breakdown as workflow
    async def generate(project, request, callbacks):
        return await stream(None, request, callbacks, "task-breakdown-write")
    monkeypatch.setattr(workflow, "generate", generate)
    assert asyncio.run(cli._run("Build backlog", "task-breakdown", proj.name)) == 1
    report = json.loads((proj / "report.json").read_text())
    assert report["status"] == "partial"
    assert report["stage_budget"]["model_calls"] == 1
    assert (proj / "retained-partial.md").read_text() == "completed work"
    assert active_stage_budget.get() is None
