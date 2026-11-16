"""Task Breakdown capability/budget invariants without model service calls."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage
from langchain.agents.middleware.types import ModelResponse

from agent_engine import config, model_setup, backends
from agent_engine.runtime import project_scope
from agent_engine.stage_controls import (
    StageBudget, StageBudgetExceeded, StageBudgetMiddleware, StageBudgetCallback,
    active_stage_budget, helper_scope, HelperScope, BreakdownHandoffMiddleware,
)
from test_model_escalation import engine, _script
from test_phase4_pipeline import proj


def budget(**overrides):
    values = dict(max_calls=10, max_input_tokens=1000, max_output_tokens=1000,
                  seconds=10, max_helpers=10, max_same_handoff=2)
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


def test_breakdown_build_assigns_role_tools_and_fast_helper_summarizers(tmp_path, monkeypatch):
    from agent_engine import agent
    captured = {}
    monkeypatch.setattr(backends, "OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(agent, "model_spec", lambda tier: "test:" + tier)
    monkeypatch.setattr(agent, "resolve_model_with_retries", lambda spec: SimpleNamespace(spec=spec))
    monkeypatch.setattr(agent, "summarization_middleware", lambda spec, model, backend: SimpleNamespace(model=model))
    monkeypatch.setattr(agent.perf, "enabled", lambda: False)
    def compile(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace()
    monkeypatch.setattr(agent, "create_deep_agent", compile)
    agent.build_agent(agent.load_pack("task-breakdown"))
    helpers = {s["name"]: s for s in captured["subagents"]}
    writer = helpers["speckit-feature"]
    enricher = helpers["backlog-enricher"]
    assert "speckit_script" in {t.name for t in writer["tools"]}
    assert "backlog_build" not in {t.name for t in writer["tools"]}
    assert {t.name for t in enricher["tools"]} <= {"source_context", "backlog_view", "backlog_find_similar", "backlog_update"}
    for helper in (writer, enricher):
        assert any(getattr(getattr(m, "model", None), "spec", None) == "test:fast" for m in helper["middleware"])


def test_enricher_cannot_write_raw_files(tmp_path, monkeypatch):
    monkeypatch.setattr(backends, "OUTPUTS_DIR", tmp_path)
    with project_scope("p"):
        token = helper_scope.set(HelperScope("backlog-enricher", "p", epic_id="E-001"))
        try:
            assert backends.build_backend().write("/outputs/p/specs/001-a/spec.md", "bad").error
            assert backends.build_backend().write("/outputs/p/backlog/backlog.md", "bad").error
        finally:
            helper_scope.reset(token)


def test_helper_scope_isolated_and_cross_feature_writes_denied(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUTS_DIR", tmp_path)
    monkeypatch.setattr(backends, "OUTPUTS_DIR", tmp_path)
    project = tmp_path / "p"
    (project / "backlog").mkdir(parents=True)
    (project / "backlog/features.json").write_text(json.dumps({"features": [
        {"feature_dir": "specs/001-a"}, {"feature_dir": "specs/002-b"}]}))
    async def exercise():
        middleware = BreakdownHandoffMiddleware()
        async def run(directory):
            request = SimpleNamespace(tool=None, tool_call={"name": "task", "id": directory,
                "args": {"subagent_type": "speckit-feature", "description": json.dumps({"project": "p", "feature_directory": directory})}})
            async def handler(request):
                backend = backends.build_backend()
                await asyncio.sleep(.01)
                assert helper_scope.get().feature_directory == directory
                assert backend.write(f"/outputs/p/{directory}/spec.md", "own").error is None
                other = "specs/002-b" if directory.endswith("a") else "specs/001-a"
                assert backend.write(f"/outputs/p/{other}/bad.md", "bad").error
                assert backend.write("/outputs/p/backlog/implementation-contract.md", "bad").error
                return "ok"
            return await middleware.awrap_tool_call(request, handler)
        with project_scope("p"):
            assert await asyncio.gather(run("specs/001-a"), run("specs/002-b")) == ["ok", "ok"]
            assert helper_scope.get() is None
    asyncio.run(exercise())


def test_helper_barrier_released_on_failure_and_parent_writes_wait(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUTS_DIR", tmp_path)
    monkeypatch.setattr(backends, "OUTPUTS_DIR", tmp_path)
    (tmp_path / "p/backlog").mkdir(parents=True)
    (tmp_path / "p/backlog/features.json").write_text('{"features":[{"feature_dir":"specs/001-a"}]}')
    async def exercise():
        shared = budget()
        token = active_stage_budget.set(shared)
        request = SimpleNamespace(tool=None, tool_call={"name": "task", "id": "t", "args": {
            "subagent_type": "speckit-feature", "description": '{"project":"p","feature_directory":"specs/001-a"}'}})
        async def helper(request):
            assert shared.active_helpers == 1
            with pytest.raises(ValueError, match="active"):
                shared.check_parent_mutation()
            scope_token = helper_scope.set(None)  # parent sees the same budget, no helper ownership
            try:
                assert backends.build_backend().write("/outputs/p/backlog/implementation-contract.md", "bad").error
            finally:
                helper_scope.reset(scope_token)
            raise RuntimeError("helper failed")
        try:
            with project_scope("p"):
                with pytest.raises(RuntimeError, match="helper failed"):
                    await BreakdownHandoffMiddleware().awrap_tool_call(request, helper)
                assert shared.active_helpers == 0 and helper_scope.get() is None
                shared.check_parent_mutation()
        finally:
            active_stage_budget.reset(token)
    asyncio.run(exercise())


def test_closed_budget_blocks_backend_write_with_copied_context(tmp_path, monkeypatch):
    monkeypatch.setattr(backends, "OUTPUTS_DIR", tmp_path)
    shared = budget()
    token = active_stage_budget.set(shared)
    try:
        with project_scope("p"):
            backend = backends.build_backend()
            shared.stop("execution closed")
            with pytest.raises(StageBudgetExceeded, match="closed"):
                backend.write("/outputs/p/late.md", "late")
            assert not (tmp_path / "p/late.md").exists()
    finally:
        active_stage_budget.reset(token)


@pytest.mark.parametrize("role,description", [
    ("general-purpose", {}), ("speckit-feature", {"project": "other", "feature_directory": "specs/001-a"}),
    ("speckit-feature", {"project": "p", "feature_directory": "specs/999-unknown"}),
    ("speckit-feature", {"project": "p", "feature_directory": "specs/../outside"}),
])
def test_unscoped_and_unregistered_handoffs_refused(tmp_path, monkeypatch, role, description):
    monkeypatch.setattr(config, "OUTPUTS_DIR", tmp_path)
    (tmp_path / "p/backlog").mkdir(parents=True)
    (tmp_path / "p/backlog/features.json").write_text('{"features":[]}')
    async def exercise():
        request = SimpleNamespace(tool=None, tool_call={"name": "task", "id": "t",
            "args": {"subagent_type": role, "description": json.dumps(description)}})
        async def forbidden(request):
            pytest.fail("invalid task was launched")
        with project_scope("p"):
            result = await BreakdownHandoffMiddleware().awrap_tool_call(request, forbidden)
            assert "ERROR:" in result.content
            assert helper_scope.get() is None
    asyncio.run(exercise())


def test_repeated_handoffs_and_total_helpers_are_bounded():
    shared = budget(max_same_handoff=1)
    shared.begin_helper('{"feature":"a"}')
    with pytest.raises(StageBudgetExceeded, match="repeated"):
        shared.begin_helper('{"feature":"a"}')
    shared = budget(max_helpers=1)
    shared.begin_helper("a")
    with pytest.raises(StageBudgetExceeded):
        shared.begin_helper("b")


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
    assert asyncio.run(cli._run("Build backlog", "task-breakdown", proj.name)) == 1
    report = json.loads((proj / "report.json").read_text())
    assert report["status"] == "partial"
    assert report["stage_budget"]["model_calls"] == 1
    assert (proj / "retained-partial.md").read_text() == "completed work"
    assert active_stage_budget.get() is None
