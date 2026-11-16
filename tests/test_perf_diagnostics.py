"""Performance diagnostics (agent_engine.perf*): correlation, concurrency, failure handling, privacy and the
offline summary. Fake models, temporary folders and simulated processes only — no model or network calls.
"""

import asyncio
import json
import os
import sys
import threading
import time
import types
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult, LLMResult
from langchain_core.tools import tool

from agent_engine import agent, backends, cli, history, logging_setup, perf, perf_callbacks, perf_manifest, perf_summary
from agent_engine.phase4 import tools as phase4_tools

ROOT = Path(__file__).resolve().parents[1]


# ============================================================================ helpers
@pytest.fixture
def perf_on(tmp_path, monkeypatch):
    """Diagnostics on for this test, writing to tmp_path/perf/test-session; environment restored afterwards."""
    perf.reset_for_tests()
    monkeypatch.setenv(perf.ENV_SESSION, "test-session")
    monkeypatch.setenv(perf.ENV_SAMPLE_SECONDS, "0")
    for name in (perf.ENV_PIPELINE, perf.ENV_PARENT_SPAN, perf.ENV_INVOCATION, perf.ENV_MODE):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(perf.config, "OUTPUTS_DIR", tmp_path / "outputs")
    assert perf.init("test", force=True, perf_dir=tmp_path / "perf")
    yield tmp_path / "perf" / "test-session"
    perf.reset_for_tests()


def events(session_dir: Path) -> list[dict]:
    perf.shutdown()
    out = []
    for p in sorted((session_dir / "events").glob("*.jsonl")):
        out += [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    return out


def ends(evs: list[dict], kind: str | None = None) -> list[dict]:
    return [e for e in evs if e["ev"] == "span_end" and (kind is None or e["kind"] == kind)]


def _pack(root: Path, name: str, toml: str) -> None:
    d = root / name
    d.mkdir(parents=True)
    (d / "agent.toml").write_text(toml, encoding="utf-8")
    (d / "system_prompt.md").write_text("demo", encoding="utf-8")


@pytest.fixture
def engine(tmp_path, monkeypatch):
    packs, outputs = tmp_path / "agents", tmp_path / "outputs"
    packs.mkdir()
    for module, name, value in [
        (agent, "AGENTS_DIR", packs), (cli, "OUTPUTS_DIR", outputs), (backends, "OUTPUTS_DIR", outputs),
        (logging_setup, "OUTPUTS_DIR", outputs), (logging_setup, "LOGS_DIR", tmp_path / "logs"),
    ]:
        monkeypatch.setattr(module, name, value)
    monkeypatch.setattr(perf.config, "AGENTS_DIR", packs)
    monkeypatch.setattr(cli, "build_langfuse_handler", lambda: None)
    monkeypatch.setattr(cli, "model_spec", lambda tier: f"fake:{tier}")
    monkeypatch.setattr(agent, "model_spec", lambda tier: f"fake:{tier}")
    return packs, outputs


# ============================================================================ a real deepagents graph, fake model
class _Script:
    def __init__(self, items: list[AIMessage]) -> None:
        self.items, self.lock, self.calls = list(items), threading.Lock(), 0


class ScriptedModel(BaseChatModel):
    """Returns scripted AIMessages in order (thread-safe); helper replies sleep so parallel helpers overlap."""

    script: Any

    @property
    def _llm_type(self) -> str:
        return "scripted-fake"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        with self.script.lock:
            msg = self.script.items.pop(0)
            self.script.calls += 1
        time.sleep(0.4 if msg.content == "helper done" else 0.01)
        return ChatResult(generations=[ChatGeneration(message=msg)])


def _ai(content: str, calls: list[dict] | None = None, usage: dict | None = None) -> AIMessage:
    return AIMessage(content=content, tool_calls=calls or [], usage_metadata=usage,
                     response_metadata={"model_name": "fake-strong", "stop_reason": "end_turn"})


def _call(name: str, args: dict) -> dict:
    return {"name": name, "args": args, "id": f"call_{uuid4().hex[:8]}", "type": "tool_call"}


THREADS: dict[str, str] = {}


@tool
def probe_tool(x: int) -> str:
    """Probe: a synchronous tool that opens nested deterministic spans."""
    THREADS["probe"] = threading.current_thread().name

    def work() -> str:
        with perf.span("solver", "probe.inner"):
            return json.dumps({"ok": x})

    return phase4_tools._run("probe_tool", work)


@tool
def err_tool(x: int) -> str:
    """Returns an error as text without raising, like the Phase 4 tools."""
    return "ERROR: bad input for err_tool"


def _graph_engine(engine, monkeypatch, script: list[AIMessage]):
    from deepagents.middleware.summarization import SummarizationMiddleware

    packs, outputs = engine
    model = ScriptedModel(script=_Script(script))
    monkeypatch.setattr(agent, "resolve_model_with_retries", lambda spec: model)
    monkeypatch.setattr(agent, "summarization_middleware",
                        lambda spec, fast, backend: SummarizationMiddleware(model=fast, backend=backend,
                                                                            trigger=("tokens", 10**9)))
    monkeypatch.setitem(agent.TOOLS, "probe-tools", lambda: [probe_tool, err_tool])
    _pack(packs, "probe", 'tools = ["probe-tools"]')
    return model


USAGE = {"input_tokens": 100, "output_tokens": 10, "total_tokens": 110, "input_token_details": {"cache_read": 40}}


def _script() -> list[AIMessage]:
    return [
        _ai("", [_call("probe_tool", {"x": 1}), _call("err_tool", {"x": 2})], USAGE),
        _ai("", [_call("task", {"description": "part A", "subagent_type": "general-purpose"}),
                 _call("task", {"description": "part B", "subagent_type": "general-purpose"})], USAGE),
        _ai("helper done", usage=USAGE),
        _ai("helper done", usage=None),                     # a provider that reports no usage for this call
        _ai("finished", usage=USAGE),
    ]


def test_real_graph_spans_parallel_helpers_worker_thread_tools_and_usage(engine, monkeypatch, perf_on):
    model = _graph_engine(engine, monkeypatch, _script())
    assert asyncio.run(cli._run("SECRET-REQUEST-TEXT build it", "probe", "demo")) == 0
    evs = events(perf_on)
    by_id = {e["span"]: e for e in ends(evs)}
    stage = ends(evs, "stage")[0]
    passes = ends(evs, "pass")
    assert [p["attrs"]["pass_kind"] for p in passes] == ["write"] and passes[0]["parent"] == stage["span"]
    calls = ends(evs, "model_call")
    assert len(calls) == model.script.calls == 5               # one span per logical call, none double-counted
    helpers = ends(evs, "helper")
    assert len(helpers) == 2 and len({h["span"] for h in helpers}) == 2
    assert all(h["parent"] == passes[0]["span"] and h["attrs"]["subagent_type"] == "general-purpose" for h in helpers)
    helper_calls = [c for c in calls if c["attrs"]["helper_span"]]
    assert sorted(c["parent"] for c in helper_calls) == sorted(h["span"] for h in helpers)
    # the two helpers really overlapped
    starts = {e["span"]: e["wall"] for e in evs if e["ev"] == "span_start"}
    (a, b) = [(starts[h["span"]], starts[h["span"]] + h["dur"]) for h in helpers]
    assert max(a[0], b[0]) < min(a[1], b[1])
    # a synchronous tool ran in a worker thread and its deterministic spans nest under its tool span
    probe = next(e for e in ends(evs, "tool") if e["name"] == "probe_tool")
    tool_exec = next(e for e in ends(evs, "tool_exec") if e["name"] == "probe_tool")
    inner = next(e for e in ends(evs, "solver") if e["name"] == "probe.inner")
    assert tool_exec["parent"] == probe["span"] and inner["parent"] == tool_exec["span"]
    assert THREADS["probe"] != "MainThread"
    # an error returned as text is a failed domain call, not a success
    err = next(e for e in ends(evs, "tool") if e["name"] == "err_tool")
    assert err["status"] == "domain_error" and err["error_category"] == "tool_error_text"
    # missing usage is unknown, not zero
    unreported = [c for c in calls if not c["attrs"]["usage_reported"]]
    assert len(unreported) == 1 and unreported[0]["attrs"]["input_tokens"] is None
    assert sum(c["attrs"]["input_tokens"] or 0 for c in calls) == 400
    # the request text never reaches the diagnostics
    raw = "".join(p.read_text(encoding="utf-8") for p in (perf_on / "events").glob("*.jsonl"))
    assert "SECRET-REQUEST-TEXT" not in raw
    # the summary: overlap, reconciliation with the usage aggregate, domain errors
    row = perf_summary.analyze(perf_on)["stages"][0]
    assert row["helpers"] == 2 and row["helper_max_concurrency"] == 2 and row["model_calls"] == 5
    assert row["usage_reconciliation"]["status"] == "match"
    assert row["tokens"]["input_tokens"] == {"sum": 400, "calls_reporting": 4, "calls_not_reporting": 1}
    assert row["tool_domain_errors"] >= 1 and row["outcome"] == "done"
    assert by_id[stage["span"]]["attrs"]["exit_code"] == 0


def test_multiple_review_and_fix_passes_are_attributed(engine, monkeypatch, perf_on):
    packs, outputs = engine
    _pack(packs, "writer", 'model = ["fast", "strong"]\nverifier = "judge"\nmax_fix_loops = 2')
    _pack(packs, "judge", 'returns = "verdict"')
    monkeypatch.setattr(cli, "build_agent", lambda pack, level=0: (pack.name, pack.models[level]))
    verdicts = iter([False, False, True])

    async def fake_stream(built, message, callbacks, run_name):
        name, _ = built
        if name == "judge":
            ok = next(verdicts)
            return {"structured_response": agent.Verdict(satisfied=ok, status_so_far="success" if ok else "partial",
                                                         gaps=[] if ok else ["gap"], summary="s")}
        return {"messages": []}

    monkeypatch.setattr(cli, "_stream", fake_stream)
    assert asyncio.run(cli._run("Build", "writer", "demo")) == 0
    evs = events(perf_on)
    passes = [(p["attrs"]["pass_kind"], p["attrs"]["attempt"]) for p in sorted(ends(evs, "pass"), key=lambda e: e["seq"])]
    assert passes == [("write", 1), ("verify", 1), ("fix", 1), ("verify", 2), ("fix", 2), ("verify", 3)]
    stage = ends(evs, "stage")[0]
    assert all(p["parent"] == stage["span"] for p in ends(evs, "pass"))
    assert (stage["attrs"]["writes"], stage["attrs"]["verifies"], stage["attrs"]["fixes"]) == (1, 3, 2)
    row = perf_summary.analyze(perf_on)["stages"][0]
    assert row["passes"]["verify"]["count"] == 3 and row["passes"]["fix"]["count"] == 2
    assert [v["effective_status"] for v in row["verdicts"]] == ["partial", "partial", "success"]


# ============================================================================ callbacks in isolation
def _handler():
    root = perf.start_span("pass", "unit")
    return perf_callbacks.PerfCallbackHandler(root.id, {"fake:m": "strong"}), root


def _llm_result(usage: dict | None) -> LLMResult:
    msg = AIMessage(content="x", usage_metadata=usage, response_metadata={"finish_reason": "stop"})
    return LLMResult(generations=[[ChatGeneration(message=msg)]])


def test_model_error_cancellation_and_partial_usage_fields(perf_on):
    h, root = _handler()
    meta = {"ls_provider": "fake", "ls_model_name": "m"}
    r1, r2, r3, r4 = uuid4(), uuid4(), uuid4(), uuid4()
    h.on_chat_model_start({}, [[1, 2]], run_id=r1, parent_run_id=None, metadata=meta)
    h.on_llm_error(RuntimeError("boom 500"), run_id=r1)
    h.on_chat_model_start({}, [[1]], run_id=r2, parent_run_id=None, metadata=meta)
    h.on_llm_error(asyncio.CancelledError(), run_id=r2)
    h.on_chat_model_start({}, [[1]], run_id=r3, parent_run_id=None, metadata=meta)
    h.on_chat_model_start({}, [[1]], run_id=r3, parent_run_id=None, metadata=meta)  # duplicate report: ignored
    h.on_llm_new_token("a", run_id=r3)
    h.on_llm_end(_llm_result({"input_tokens": 5, "output_tokens": 2, "total_tokens": 7}), run_id=r3)
    h.on_chat_model_start({}, [[1]], run_id=r4, parent_run_id=None, metadata=meta)
    h.on_llm_end(_llm_result(None), run_id=r4)
    root.end()
    calls = ends(events(perf_on), "model_call")
    assert [c["status"] for c in calls] == ["error", "cancelled", "ok", "ok"]
    assert calls[0]["error_category"] == "other" and calls[1]["error_category"] == "cancelled"
    ok = calls[2]["attrs"]
    assert ok["tier"] == "strong" and ok["input_tokens"] == 5 and ok["cache_read_tokens"] is None
    assert ok["time_to_first_chunk_s"] is not None and ok["finish_reason"] == "stop"
    none = calls[3]["attrs"]
    assert none["usage_reported"] is False and none["output_tokens"] is None
    assert "not exposed" in none["ttft_visibility"]


def test_sdk_retries_are_visible_through_transport_hooks(perf_on):
    import anthropic
    import httpx2  # the installed anthropic SDK's HTTP library

    seen = []

    def handler(request):
        seen.append(request.headers.get("x-stainless-retry-count"))
        if len(seen) == 1:
            return httpx2.Response(529, json={"type": "error", "error": {"type": "overloaded_error", "message": "busy"}},
                                   headers={"retry-after-ms": "10"})
        return httpx2.Response(200, json={"id": "msg_1", "type": "message", "role": "assistant", "model": "m",
                                          "content": [{"type": "text", "text": "hi"}], "stop_reason": "end_turn",
                                          "usage": {"input_tokens": 3, "output_tokens": 1}})

    client = anthropic.Anthropic(api_key="test-key-not-real", max_retries=2,
                                 http_client=httpx2.Client(transport=httpx2.MockTransport(handler)))
    model = types.SimpleNamespace(_client=client)
    assert perf_callbacks.install_transport_hooks(model) == "installed"
    token = perf.current_model_call.set("call-1")
    client.messages.create(model="m", max_tokens=5, messages=[{"role": "user", "content": "x"}])
    perf.current_model_call.reset(token)
    assert seen == ["0", "1"]
    responses = [e for e in events(perf_on) if e["ev"] == "event" and e["name"] == "model.response"]
    assert [(r["attrs"]["status_code"], r["attrs"]["sdk_retry_count"]) for r in responses] == [(529, 0), (200, 1)]
    assert all(r["attrs"]["model_call"] == "call-1" for r in responses)
    mt = perf_summary.analyze(perf_on)["http"]["model_transport"]
    assert mt["attempts"] == 2 and mt["calls_with_multiple_attempts"] == 1 and mt["sdk_retry_attempts"] == 1


def test_transport_hooks_attach_to_the_real_model_classes(perf_on):
    from langchain_anthropic import ChatAnthropic
    from langchain_openai import ChatOpenAI

    from agent_engine import subscription_models

    assert perf_callbacks.install_transport_hooks(ChatAnthropic(model="claude-x", api_key="test-not-real")) == "installed"
    assert perf_callbacks.install_transport_hooks(ChatOpenAI(model="gpt-x", api_key="test-not-real")) == "installed"
    sub = subscription_models.build_anthropic_subscription_llm("claude-x", "sk-ant-oat01-test-not-real")
    assert perf_callbacks.install_transport_hooks(sub) == "installed"
    assert perf_callbacks.install_transport_hooks(object()).startswith("unavailable")


# ============================================================================ processes, interruption, failure
def test_child_process_joins_the_session_under_the_parent_span(tmp_path, monkeypatch, perf_on):
    from agent_engine.phase4 import orchestrator

    outputs = tmp_path / "outputs"
    (outputs / "proj").mkdir(parents=True)
    # An older successful report of the same agent is still on disk; the new child fails before writing one.
    (outputs / "proj" / "report.json").write_text(json.dumps({"agent": "sprint-planning", "status": "success"}),
                                                   encoding="utf-8")
    monkeypatch.setattr(orchestrator.config, "OUTPUTS_DIR", outputs)
    monkeypatch.setenv("AGENT_ENGINE_OUTPUTS_DIR", str(outputs))
    monkeypatch.setenv("AGENT_ENGINE_LOGS_DIR", str(tmp_path / "logs"))
    perf.set_pipeline("pipe-1")
    with perf.span("pipeline", "proj") as pipe:
        result = orchestrator.run_agent("sprint-planning", "Plan the sprints.", "proj")
    assert result["exit_code"] == 1 and result["status"] == "fail"
    assert "not from this invocation" in result["report_problem"]
    evs = events(perf_on)
    child = next(e for e in ends(evs, "child"))
    assert child["parent"] == pipe.id and child["attrs"]["invocation_id"] == result["invocation_id"]
    procs = [e for e in ends(evs, "process") if e["pid"] != os.getpid()]
    assert len(procs) == 1 and procs[0]["parent"] == child["span"]
    assert procs[0]["session"] == "test-session" and procs[0]["pipeline"] == "pipe-1"
    assert procs[0]["invocation"] == result["invocation_id"]
    pre = next(e for e in ends(evs, "phase") if e["name"] == "preflight" and e["pid"] != os.getpid())
    assert pre["status"] == "blocked" and pre["error_category"] == "missing_input"


def test_interrupted_run_leaves_visible_incomplete_spans(perf_on):
    with perf.span("pipeline", "p"):
        perf.start_span("stage", "never-ends")          # e.g. a killed child process
    perf.shutdown()
    events_file = next((perf_on / "events").glob("*.jsonl"))
    with events_file.open("a", encoding="utf-8") as f:
        f.write('{"truncated": ')                         # the half-written last line of a killed process
    r = perf_summary.analyze(perf_on)
    assert [s["name"] for s in r["incomplete_spans"]] == ["never-ends"]
    assert r["evidence"]["corrupt_lines"] == 1 and r["overview"]["diagnostics_complete"] is False
    assert "spans never ended" in " ".join(r["visibility"])


def test_diagnostics_write_failure_never_masks_the_application_failure(tmp_path, monkeypatch, capsys, engine):
    perf.reset_for_tests()
    monkeypatch.setenv(perf.ENV_SESSION, "broken")
    monkeypatch.setenv(perf.ENV_SAMPLE_SECONDS, "0")
    blocker = tmp_path / "perf"
    blocker.write_text("a file where the diagnostics folder should be", encoding="utf-8")
    try:
        assert perf.init("test", force=True, perf_dir=blocker)
        packs, outputs = engine
        _pack(packs, "writer", "")
        monkeypatch.setattr(cli, "build_agent", lambda pack, level=0: object())

        async def boom(*a, **k):
            raise ValueError("the original model failure")

        monkeypatch.setattr(cli, "_stream", boom)
        assert asyncio.run(cli._run("Build", "writer", "demo")) == 1
        report = json.loads((outputs / "demo" / "report.json").read_text(encoding="utf-8"))
        assert report["status"] == "fail" and "the original model failure" in report["error"]
        with pytest.raises(ValueError, match="original"):
            with perf.span("phase", "x"):
                raise ValueError("original")
        perf.shutdown()
        err = capsys.readouterr().err
        assert "INCOMPLETE" in err or "incomplete" in err
    finally:
        perf.reset_for_tests()


# ============================================================================ privacy and configuration
def test_redaction_and_manifest_allowlist(tmp_path, monkeypatch, perf_on):
    secrets = {"ANTHROPIC_API_KEY": "sk-ant-api03-REALSECRET1234567890", "GITHUB_TOKEN": "ghp_" + "A" * 36,
               "JIRA_API_TOKEN": "jira-token-value-123456", "SDLC_AGENT_ANTHROPIC_OAUTH_TOKEN": "sk-ant-oat01-OAUTHSECRET99"}
    for k, v in secrets.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("PHASE4_ALLOCATION_SOLVER_URL", "http://user:pw@solver.internal:8080/path?token=abc")
    monkeypatch.setenv("PHASE4_ALLOCATION_SOLVER_MODE", "local")
    perf._secret_values = None
    text = " ".join(secrets.values()) + " Authorization: Bearer abcdefghijklmnop1234 password=hunter2hunter2"
    clean = perf.redact(text)
    assert not any(v in clean for v in secrets.values()) and "hunter2hunter2" not in clean and "abcdefghijklmnop1234" not in clean
    settings = perf_manifest.safe_settings()
    dumped = json.dumps(settings)
    assert not any(v in dumped for v in secrets.values())
    assert settings["PHASE4_ALLOCATION_SOLVER_URL"] == "http://solver.internal:8080"
    assert settings["presence"]["ANTHROPIC_API_KEY"] == "set" and settings["PHASE4_ALLOCATION_SOLVER_MODE"] == "local"
    rel = perf_manifest.write("pipeline", "m1", project=None, packs=["task-breakdown"])
    manifest = (perf_on / rel).read_text(encoding="utf-8")
    assert not any(v in manifest for v in secrets.values()) and "pw@" not in manifest
    assert json.loads(manifest)["packs"]["task-breakdown"]["files"] > 0
    raw = perf.write_raw("span1", "trivy", f"token leaked: {secrets['GITHUB_TOKEN']}")
    assert secrets["GITHUB_TOKEN"] not in (perf_on / raw).read_text(encoding="utf-8")


def test_diagnostics_folder_must_stay_out_of_agent_readable_and_published_folders(tmp_path, monkeypatch, capsys):
    perf.reset_for_tests()
    outputs = tmp_path / "outputs"
    monkeypatch.setattr(perf.config, "OUTPUTS_DIR", outputs)
    monkeypatch.setenv(perf.ENV_SAMPLE_SECONDS, "0")
    monkeypatch.setenv(perf.ENV_SESSION, "s")
    assert perf.separation_problems(outputs / "proj" / "perf")
    assert not perf.init("test", force=True, perf_dir=outputs / "perf")
    assert "NOT enabled" in capsys.readouterr().err and not perf.enabled()
    assert perf.separation_problems(tmp_path / "logs" / "perf") == []
    perf.reset_for_tests()


def test_diagnostic_files_are_not_fingerprinted_or_published(tmp_path, monkeypatch, engine, perf_on):
    packs, outputs = engine
    _pack(packs, "writer", '[output]\nfiles = ["out.md"]')
    monkeypatch.setattr(cli, "build_agent", lambda pack, level=0: object())

    async def write_output(*a, **k):
        (outputs / "demo" / "out.md").write_text("result", encoding="utf-8")
        return {"messages": []}

    monkeypatch.setattr(cli, "_stream", write_output)
    assert asyncio.run(cli._run("Build", "writer", "demo")) == 0
    perf.shutdown()
    project_files = [p.relative_to(outputs / "demo").as_posix() for p in (outputs / "demo").rglob("*") if p.is_file()]
    assert not any(".jsonl" in f or "perf" in f or "manifest-" in f for f in project_files)
    assert set(history.fingerprint(outputs / "demo")) == {"out.md"}
    assert list((perf_on / "events").glob("*.jsonl")) and not perf._inside(perf_on, outputs)
    assert (perf_on / "manifests").is_dir()


def test_publication_is_refused_in_generation_only_diagnostic_runs(perf_on, monkeypatch, capsys):
    from agent_engine.phase4 import orchestrator

    assert perf.publication_blocked()
    assert orchestrator.orchestrate("nope", publish=True, out=print) == orchestrator.FAILED
    assert "generation-only" in capsys.readouterr().out
    monkeypatch.setenv(perf.ENV_MODE, "publication")
    assert perf.publication_blocked() is None


# ============================================================================ disabled
def test_disabled_is_a_no_op(tmp_path, monkeypatch, engine):
    perf.reset_for_tests()
    monkeypatch.delenv(perf.ENV_ENABLED, raising=False)
    assert perf.init("test") is False and not perf.enabled()
    assert perf.span("x", "y") is perf.NOOP and perf.start_span("x", "y") is perf.NOOP
    assert perf.child_env("abc") == {} and perf.write_raw("s", "l", "t") is None
    packs, outputs = engine
    _pack(packs, "writer", "")
    monkeypatch.setattr(cli, "build_agent", lambda pack, level=0: object())

    async def ok(*a, **k):
        return {"messages": []}

    monkeypatch.setattr(cli, "_stream", ok)
    assert asyncio.run(cli._run("Build", "writer", "demo")) == 0
    assert not (tmp_path / "logs" / "perf").exists()
    report = json.loads((outputs / "demo" / "report.json").read_text(encoding="utf-8"))
    assert "invocation_id" not in report and report["status"] == "done"


# ============================================================================ summary accounting
def _write_events(session: Path, records: list[dict]) -> None:
    (session / "events").mkdir(parents=True)
    with (session / "events" / "x.jsonl").open("w", encoding="utf-8") as f:
        for i, r in enumerate(records):
            f.write(json.dumps({"v": 1, "pid": 1, "seq": i, "session": session.name, **r}) + "\n")


def _span(span_id, parent, kind, name, start, dur, **attrs):
    return [{"ev": "span_start", "span": span_id, "parent": parent, "kind": kind, "name": name, "wall": start, "attrs": {}},
            {"ev": "span_end", "span": span_id, "parent": parent, "kind": kind, "name": name, "wall": start + dur,
             "dur": dur, "status": "ok", "attrs": attrs}]


def test_summary_accounting_with_nested_and_overlapping_spans(tmp_path):
    t = 1_000_000.0
    recs = []
    recs += _span("st", None, "stage", "writer", t, 10, status="done")
    recs += _span("ps", "st", "pass", "writer:write", t, 10, pass_kind="write")
    recs += _span("h1", "ps", "helper", "general-purpose", t + 1, 5, subagent_type="general-purpose")
    recs += _span("h2", "ps", "helper", "general-purpose", t + 2, 5, subagent_type="general-purpose")
    recs += _span("m1", "h1", "model_call", "m", t + 1, 3, input_tokens=10)      # 1..4
    recs += _span("m2", "h2", "model_call", "m", t + 3, 3, input_tokens=20)      # 3..6 (overlaps m1)
    recs += _span("te", "ps", "tool_exec", "sprint_solve", t + 5, 3)             # 5..8 (overlaps m2 at 5..6)
    recs += _span("sv", "te", "solver", "sprint.cpsat", t + 6, 1)                # 6..7 inside the tool
    _write_events(tmp_path / "sess", recs)
    r = perf_summary.analyze(tmp_path / "sess")
    b = r["stages"][0]["breakdown"]
    assert b["elapsed_s"] == 10
    assert b["exclusive_wall_s"]["model_call"] == 5            # union of 1..4 and 3..6, counted once
    assert b["exclusive_wall_s"]["solver"] == 1
    assert b["exclusive_wall_s"]["tool_exec"] == 1             # 6..8 minus the solver's 6..7
    assert b["unattributed_s"] == 3
    assert b["summed_work_s"]["model_call"] == 6               # summed work exceeds its wall share
    assert r["helpers"]["max_concurrency"] == 2 and r["helpers"]["summed_s"] == 10
    assert r["helpers"]["elapsed_union_s"] == 6
    md = perf_summary.to_markdown(r)
    assert "Exclusive wall time" in md or "exclusive wall time" in md


def test_human_wait_is_measured_only_from_evidence(tmp_path):
    t = 2_000_000.0
    recs = _span("proc1", None, "process", "phase4 orchestrate", t, 100)       # first orchestrate invocation
    recs += _span("proc2", None, "process", "phase4 orchestrate", t + 500, 50)  # resumed after the approval
    recs += _span("p1", "proc1", "pipeline", "proj", t, 100, outcome="waiting", pipeline_id="a")
    recs.append({"ev": "event", "kind": "approval_wait_start", "name": "P4-G1", "wall": t + 100,
                 "attrs": {"gates": ["P4-G1", "P4-G4"]}})
    recs.append({"ev": "event", "kind": "gate_decision", "name": "P4-G1", "wall": t + 400,
                 "attrs": {"automated": False, "decided_at": "x"}})
    recs += _span("p2", "proc2", "pipeline", "proj", t + 500, 50, outcome="done", pipeline_id="b")
    _write_events(tmp_path / "sess", recs)
    o = perf_summary.analyze(tmp_path / "sess")["overview"]
    waits = {w["gate"]: w for w in o["human_waits"]}
    assert waits["P4-G1"]["wait_s"] == 300 and waits["P4-G1"]["basis"] == "gate command event"
    assert waits["P4-G4"]["wait_s"] is None and "not measured" in waits["P4-G4"]["basis"]
    assert o["active_execution_s"] == 150 and o["session_elapsed_s"] == 550
    assert o["unexplained_s"] == 100                           # 550 - 150 active - 300 measured wait


def test_cli_summarize_writes_summary_files(tmp_path, perf_on):
    with perf.span("pipeline", "p", outcome="done"):
        perf.event("approval_wait_start", "P4-G1", gates=["P4-G1"])
    perf.shutdown()
    args = types.SimpleNamespace(perf_command="summarize", session="test-session", dir=str(tmp_path / "perf"), json=False)
    assert perf_summary.cli(args) == 0
    assert (perf_on / "summary.md").read_text(encoding="utf-8").startswith("# Performance summary")
    assert json.loads((perf_on / "summary.json").read_text(encoding="utf-8"))["session"] == "test-session"


def test_resource_sampler_records_this_process(tmp_path, monkeypatch):
    perf.reset_for_tests()
    monkeypatch.setenv(perf.ENV_SESSION, "res")
    monkeypatch.setenv(perf.ENV_SAMPLE_SECONDS, "0.05")
    monkeypatch.setattr(perf.config, "OUTPUTS_DIR", tmp_path / "outputs")
    try:
        assert perf.init("test", force=True, perf_dir=tmp_path / "perf")
        time.sleep(0.3)
        evs = events(tmp_path / "perf" / "res")
        samples = [e for e in evs if e["ev"] == "sample"]
        assert samples and "cpu_user_s" in samples[0]["attrs"]
        proc = ends(evs, "process")[0]["attrs"]
        assert proc["cpu_count"] and "cpu_user_s" in proc
        if sys.platform == "win32":
            assert proc.get("peak_rss_bytes", 0) > 0
    finally:
        perf.reset_for_tests()
