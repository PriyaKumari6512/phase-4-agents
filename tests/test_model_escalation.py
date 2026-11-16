"""`model = ["fast", "strong"]`: a failed verdict or a model error moves the
next pass one step along the list. Fake agents, no model calls.
"""

import asyncio
import json

import pytest

from agent_engine import agent, cli, logging_setup


def _pack(tmp_path, name: str, toml: str):
    d = tmp_path / name
    d.mkdir()
    (d / "agent.toml").write_text(toml, encoding="utf-8")
    (d / "system_prompt.md").write_text("demo", encoding="utf-8")


@pytest.fixture
def engine(tmp_path, monkeypatch):
    packs, outputs = tmp_path / "agents", tmp_path / "outputs"
    packs.mkdir()
    for module, name, value in [
        (agent, "AGENTS_DIR", packs), (cli, "OUTPUTS_DIR", outputs),
        (logging_setup, "OUTPUTS_DIR", outputs), (logging_setup, "LOGS_DIR", tmp_path / "logs"),
    ]:
        monkeypatch.setattr(module, name, value)
    monkeypatch.setattr(cli, "build_langfuse_handler", lambda: None)
    monkeypatch.setattr(cli, "model_spec", lambda tier: f"test:{tier}")
    _pack(packs, "writer", 'model = ["fast", "strong"]\nverifier = "judge"\nmax_fix_loops = 2')
    _pack(packs, "judge", 'returns = "verdict"')
    # build_agent returns what was built; _stream plays the scripted outcome for it.
    monkeypatch.setattr(cli, "build_agent", lambda pack, level=0: (pack.name, pack.models[level]))
    return outputs


def _script(monkeypatch, verdicts: list[bool], fail_on: set = frozenset()):
    verdicts = iter(verdicts)

    async def fake_stream(built, message, callbacks, run_name):
        name, tier = built
        if (name, tier) in fail_on:
            raise RuntimeError(f"{tier} is down")
        if name == "judge":
            ok = next(verdicts)
            return {"structured_response": agent.Verdict(
                satisfied=ok, status_so_far="success" if ok else "partial",
                gaps=[] if ok else ["US-4 has no acceptance criteria"], summary="checked")}
        return {"messages": []}

    monkeypatch.setattr(cli, "_stream", fake_stream)


def _passes(outputs):
    report = json.loads((outputs / "demo" / "report.json").read_text(encoding="utf-8"))
    return report, [(p["kind"], p["model_tier"], p["ok"]) for p in report["passes"]]


def test_failed_verdict_escalates_fix_pass(engine, monkeypatch):
    _script(monkeypatch, verdicts=[False, True])
    assert asyncio.run(cli._run("Build a gym app", "writer", "demo")) == 0
    report, passes = _passes(engine)
    assert passes == [("write", "fast", True), ("verify", "strong", True), ("fix", "strong", True), ("verify", "strong", True)]
    assert report["status"] == "success"


def test_model_error_retries_on_next_model(engine, monkeypatch):
    _script(monkeypatch, verdicts=[True], fail_on={("writer", "fast")})
    assert asyncio.run(cli._run("Build a gym app", "writer", "demo")) == 0
    _, passes = _passes(engine)
    assert passes[:2] == [("write", "fast", False), ("write", "strong", True)]


def test_last_model_error_fails_the_run(engine, monkeypatch):
    _script(monkeypatch, verdicts=[], fail_on={("writer", "fast"), ("writer", "strong")})
    assert asyncio.run(cli._run("Build a gym app", "writer", "demo")) == 1
    report, _ = _passes(engine)
    assert report["status"] == "fail" and "strong is down" in report["error"]


@pytest.mark.parametrize("model", ['[]', '["fast", "medium"]', '"huge"'])
def test_bad_model_list_is_rejected(tmp_path, monkeypatch, model):
    monkeypatch.setattr(agent, "AGENTS_DIR", tmp_path)
    _pack(tmp_path, "demo", f"model = {model}")
    with pytest.raises(ValueError, match="model must be"):
        agent.load_pack("demo")


def test_missing_input_stops_before_any_model_call(engine, monkeypatch, capsys):
    packs = agent.AGENTS_DIR
    _pack(packs, "prd", '[output]\nfiles = ["prd.md"]')
    _pack(packs, "ux", '[input]\nfiles = ["prd.md"]\n[output]\nfiles = ["ux.md"]')
    built = []
    monkeypatch.setattr(cli, "build_agent", lambda pack, level=0: built.append(pack.name))
    assert asyncio.run(cli._run("Make flows", "ux", "demo")) == 1
    assert built == []
    assert "Run --agent prd on this project first" in capsys.readouterr().out


def test_missing_output_fails_without_paying_the_verifier(engine, monkeypatch):
    _pack(agent.AGENTS_DIR, "lazy", 'verifier = "judge"\n[output]\nfiles = ["out.md"]')
    _script(monkeypatch, verdicts=[True])
    assert asyncio.run(cli._run("Do it", "lazy", "demo")) == 1
    report, passes = _passes(engine)
    assert report["status"] == "fail" and "out.md" in report["error"]
    assert [p[0] for p in passes] == ["write"]
