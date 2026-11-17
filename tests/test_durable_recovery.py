"""Failure-injection tests for recovery only; no model APIs or publications."""
import asyncio
import json
import shutil
from pathlib import Path

import pytest

from agent_engine import agent, cli, config, logging_setup, recovery, verification_resume
from agent_engine.history import file_digest
from agent_engine.phase4 import orchestrator as orch, parallel_stages as parallel
from test_model_escalation import _pack
from test_phase4_pipeline import proj, P
from test_phase4_orchestrator import root, OUTPUTS


class Crash(BaseException):
    pass


@pytest.fixture
def stage(proj, tmp_path, monkeypatch):
    packs = tmp_path / "agents"
    packs.mkdir()
    _pack(packs, "task-breakdown", 'model="strong"\nverifier="task-breakdown/validator"\nmax_fix_loops=1\nrequest_history="agent"\n[input]\nfiles=["prd.md","architecture.md","phase4/project.json"]\n[output]\nfiles=["backlog/backlog.json","backlog/backlog.md"]')
    _pack(packs, "task-breakdown/validator", 'returns="verdict"')
    _pack(packs, "infra-pipeline", 'model="strong"\n[input]\nfiles=["architecture.md"]\n[output]\nfiles=["infra/manifest.json"]')
    monkeypatch.setattr(agent, "AGENTS_DIR", packs)
    monkeypatch.setattr(cli, "OUTPUTS_DIR", proj.parent)
    monkeypatch.setattr(logging_setup, "OUTPUTS_DIR", proj.parent)
    monkeypatch.setattr(logging_setup, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(cli, "build_langfuse_handler", lambda: None)
    monkeypatch.setattr(cli, "model_spec", lambda tier: "test:" + tier)
    monkeypatch.setattr(cli, "build_agent", lambda pack, level=0: (pack.name, pack.models[level]))
    monkeypatch.setattr(cli, "_deterministic_gaps", lambda *args: ([], False))
    # Mock the operation boundary; these tests exercise recovery with deliberately
    # synthetic artifacts, not planning or semantic review implementations.
    from agent_engine.phase4 import task_breakdown as workflow
    async def generate(project, request, callbacks):
        return await cli._stream(None, request, callbacks, "task-breakdown-write")
    async def review(project, callbacks):
        return await cli._stream(None, "review", callbacks, "task-breakdown/validator-verify")
    async def repair(project, gaps, callbacks):
        assert gaps, "resumed repairs must receive retained findings"
        return await cli._stream(None, str(gaps), callbacks, "task-breakdown-fix")
    monkeypatch.setattr(workflow, "generate", generate)
    monkeypatch.setattr(workflow, "review", review)
    monkeypatch.setattr(workflow, "repair", repair)
    return proj


def artifacts(root, content="generated"):
    (root / "backlog").mkdir(exist_ok=True)
    (root / "backlog/backlog.json").write_text(json.dumps({"text": content}))
    (root / "backlog/backlog.md").write_text(content)


def verdict(ok=True):
    return {"structured_response": agent.Verdict(satisfied=ok, status_so_far="success" if ok else "partial",
                                                 gaps=[] if ok else ["S-1: missing requirement"], summary="reviewed")}


def report(root):
    return json.loads((root / "report.json").read_text())


def test_malformed_review_retries_only_review_then_resumes_after_model_change(stage, monkeypatch):
    calls = []
    async def stream(built, message, callbacks, run_name):
        calls.append(run_name)
        if run_name.endswith("-write"):
            artifacts(stage)
            return {"messages": []}
        raise json.JSONDecodeError("empty", "", 0)
    monkeypatch.setattr(cli, "_stream", stream)
    assert asyncio.run(cli._run("request", "task-breakdown", P)) == 1
    assert calls == ["task-breakdown-write", "task-breakdown/validator-verify"]
    history = (stage / "requests/task-breakdown.md").read_bytes()
    before = (stage / "backlog/backlog.json").read_bytes()
    monkeypatch.setenv("SDLC_AGENT_STRONG_MODEL", "different:reviewer")
    async def review_only(built, message, callbacks, run_name):
        assert run_name.endswith("-verify")
        return verdict()
    monkeypatch.setattr(cli, "_stream", review_only)
    assert asyncio.run(cli._run("request", "task-breakdown", P, resume=True)) == 0
    assert (stage / "requests/task-breakdown.md").read_bytes() == history
    assert (stage / "backlog/backlog.json").read_bytes() == before
    assert report(stage)["recovery_action"] == "verify"
    assert not list((stage / "gates").glob("P4-*.approved.json"))


def test_empty_state_is_bounded_format_failure(stage, monkeypatch):
    calls = []
    async def stream(built, message, callbacks, run_name):
        calls.append(run_name)
        if run_name.endswith("-write"):
            artifacts(stage)
        return {"messages": []}
    monkeypatch.setattr(cli, "_stream", stream)
    assert asyncio.run(cli._run("request", "task-breakdown", P)) == 1
    assert len(calls) == 2
    assert report(stage)["passes"][-1]["invalid_verdict"]["response_chars"] == 0
    assert recovery.next_action(stage, agent.load_pack("task-breakdown"), "request")[0] == "verify"


def test_restart_during_review_retains_generation(stage, monkeypatch):
    async def crash(built, message, callbacks, run_name):
        if run_name.endswith("-write"):
            artifacts(stage)
            return {"messages": []}
        raise Crash("process interrupted")
    monkeypatch.setattr(cli, "_stream", crash)
    with pytest.raises(Crash):
        asyncio.run(cli._run("request", "task-breakdown", P))
    assert recovery.next_action(stage, agent.load_pack("task-breakdown"))[0] == "verify"
    async def review(built, message, callbacks, run_name):
        assert run_name.endswith("-verify")
        return verdict()
    monkeypatch.setattr(cli, "_stream", review)
    assert asyncio.run(cli._run("request", "task-breakdown", P, resume=True)) == 0


def test_interrupted_repair_retains_edits_and_resumes_from_saved_artifacts(stage, monkeypatch):
    async def crash(built, message, callbacks, run_name):
        if run_name.endswith("-write"):
            artifacts(stage, "original")
            return {"messages": []}
        if run_name.endswith("-fix"):
            artifacts(stage, "unfinished repair")
            raise Crash("repair interrupted")
        return verdict(False)
    monkeypatch.setattr(cli, "_stream", crash)
    with pytest.raises(Crash):
        asyncio.run(cli._run("request", "task-breakdown", P))
    assert recovery.next_action(stage, agent.load_pack("task-breakdown"))[0] == "restore_repair"
    calls = []
    async def finish(built, message, callbacks, run_name):
        calls.append(run_name)
        if run_name.endswith("-fix"):
            assert (stage / "backlog/backlog.md").read_text() == "original"
            artifacts(stage, "finished repair")
            return {"messages": []}
        return verdict()
    monkeypatch.setattr(cli, "_stream", finish)
    assert asyncio.run(cli._run("request", "task-breakdown", P, resume=True)) == 0
    assert calls == ["task-breakdown-fix", "task-breakdown/validator-verify"]
    assert any(p.read_text() == "unfinished repair" for p in (stage / ".engine-recovery/interrupted").rglob("backlog.md"))


def test_unchanged_verified_result_needs_no_model_call(stage, monkeypatch):
    async def stream(built, message, callbacks, run_name):
        if run_name.endswith("-write"):
            artifacts(stage)
            return {"messages": []}
        return verdict()
    monkeypatch.setattr(cli, "_stream", stream)
    assert asyncio.run(cli._run("request", "task-breakdown", P)) == 0
    monkeypatch.setattr(cli, "build_agent", lambda *args: pytest.fail("unchanged completed work called a model"))
    assert asyncio.run(cli._run("request", "task-breakdown", P, resume=True)) == 0
    assert report(stage)["review_reused"]


def test_changed_sources_invalidate_reuse_and_semantic_gaps_do_not_loop(stage, monkeypatch):
    async def stream(built, message, callbacks, run_name):
        if run_name.endswith(("-write", "-fix")):
            artifacts(stage)
            return {"messages": []}
        return verdict(False)
    monkeypatch.setattr(cli, "_stream", stream)
    assert asyncio.run(cli._run("request", "task-breakdown", P)) == 1
    assert recovery.next_action(stage, agent.load_pack("task-breakdown"))[0] == "wait"
    monkeypatch.setattr(cli, "build_agent", lambda *args: pytest.fail("decision wait called a model"))
    assert asyncio.run(cli._run("request", "task-breakdown", P, resume=True)) == 1
    (stage / "prd.md").write_text("Changed actual requirement")
    assert recovery.next_action(stage, agent.load_pack("task-breakdown"))[0] == "generate"


def steps():
    return [orch.Step(s, "run", "test", s.request) for s in orch.STAGES[:2]]


def fake_runner(calls, *, feature_checkpoint=False):
    def run(agent_name, request, project, *, outputs_dir, logs_dir):
        calls.append(agent_name)
        child = outputs_dir / project
        for rel in OUTPUTS[agent_name]:
            path = child / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"agent": agent_name}))
        if agent_name == "task-breakdown" and feature_checkpoint:
            state = child / ".engine-task-breakdown"
            (state / "stories").mkdir(parents=True)
            (state / "stories" / ("a" * 64 + ".json")).write_text(json.dumps({"base": "a" * 64, "result": {}}))
            (state / "current.json").write_text(json.dumps({"BM-2": "a" * 64}))
        return {"status": "partial", "gaps": ["needs review"], "rate_limited": False}
    return run


@pytest.fixture
def parallel_root(root, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LOGS_DIR", tmp_path / "logs")
    return root


def test_retained_story_results_merge_only_for_task_breakdown(parallel_root):
    calls = []
    result = parallel.run_pair(parallel_root, steps(), fake_runner(calls, feature_checkpoint=True))
    assert len(calls) == 2 and result["task-breakdown"]["status"] == "partial"
    assert (parallel_root / ".engine-task-breakdown/current.json").is_file()
    assert (parallel_root / ".engine-task-breakdown/stories" / ("a" * 64 + ".json")).is_file()
    assert not list((parallel_root / "gates").glob("P4-*.approved.json"))


def test_merge_error_replay_does_not_call_writers(parallel_root, monkeypatch):
    calls = []
    real = parallel._replace
    count = 0
    def fail(source, dest):
        nonlocal count
        count += 1
        if count == 2:
            raise OSError("disk failure")
        real(source, dest)
    monkeypatch.setattr(parallel, "_replace", fail)
    before = parallel.inventory(parallel_root)
    with pytest.raises(OSError):
        parallel.run_pair(parallel_root, steps(), fake_runner(calls))
    assert parallel.inventory(parallel_root) == before and len(calls) == 2
    monkeypatch.setattr(parallel, "_replace", real)
    result = parallel.run_pair(parallel_root, steps(), lambda *a, **kw: pytest.fail("replayed merge reran a writer"))
    assert result["infra-pipeline"]["status"] == "partial"
    assert len(calls) == 2


def test_process_crash_mid_merge_replays_idempotently(parallel_root, monkeypatch):
    real = parallel._replace
    count = 0
    def crash(source, dest):
        nonlocal count
        count += 1
        if count == 2:
            raise Crash("machine interrupted")
        real(source, dest)
    monkeypatch.setattr(parallel, "_replace", crash)
    with pytest.raises(Crash):
        parallel.run_pair(parallel_root, steps(), fake_runner([]))
    monkeypatch.setattr(parallel, "_replace", real)
    result = parallel.replay_pending(parallel_root)
    assert set(result) == {"task-breakdown", "infra-pipeline"}
    assert (parallel_root / "infra/manifest.json").is_file()


def test_completed_child_is_not_rerun_after_other_child_failure(parallel_root):
    calls = []
    base = fake_runner(calls)
    fail = True
    def run(agent_name, *args, **kwargs):
        nonlocal fail
        if agent_name == "task-breakdown" and fail:
            fail = False
            raise RuntimeError("child crashed")
        return base(agent_name, *args, **kwargs)
    with pytest.raises(RuntimeError):
        parallel.run_pair(parallel_root, steps(), run)
    assert calls == ["infra-pipeline"]
    parallel.run_pair(parallel_root, steps(), run)
    assert calls.count("infra-pipeline") == 1 and calls.count("task-breakdown") == 1


def test_stale_original_blocks_replay_without_losing_child_work(parallel_root, monkeypatch):
    original = parallel._replace
    monkeypatch.setattr(parallel, "_replace", lambda *a: (_ for _ in ()).throw(OSError("full disk")))
    with pytest.raises(OSError):
        parallel.run_pair(parallel_root, steps(), fake_runner([]))
    (parallel_root / "prd.md").write_text("New source requirements")
    monkeypatch.setattr(parallel, "_replace", original)
    with pytest.raises(ValueError, match="changed"):
        parallel.replay_pending(parallel_root)
    assert list((config.LOGS_DIR / "parallel").glob("*/task-breakdown/outputs/demo/backlog/backlog.json"))


@pytest.mark.parametrize("bad", ["unknown-engine", "wrong-owner", "bad-path"])
def test_merge_rejects_unknown_engine_metadata_and_invalid_retained_state(parallel_root, bad):
    base = fake_runner([], feature_checkpoint=True)
    def run(agent_name, *args, **kwargs):
        result = base(agent_name, *args, **kwargs)
        child = kwargs["outputs_dir"] / "demo"
        if bad == "unknown-engine" and agent_name == "task-breakdown":
            (child / ".engine-unknown").mkdir()
            (child / ".engine-unknown/data.json").write_text("{}")
        if bad == "wrong-owner" and agent_name == "infra-pipeline":
            (child / ".engine-task-breakdown").mkdir()
            (child / ".engine-task-breakdown/current.json").write_text("{}")
        if bad == "bad-path" and agent_name == "task-breakdown":
            (child / ".engine-task-breakdown/stories/not-a-digest.json").write_text("{}")
        return result
    with pytest.raises(ValueError):
        parallel.run_pair(parallel_root, steps(), run)
    assert not (parallel_root / "backlog").exists()


def test_orchestrator_selects_saved_review_and_preserves_gates(stage):
    artifacts(stage)
    pack = agent.load_pack("task-breakdown")
    recovery.save(stage, pack, "original request", "job", "review_pending")
    chosen = orch.assess(P)[0]
    assert chosen.action == "run" and chosen.request == "original request" and "resume retained verify" in chosen.why
    assert not list((stage / "gates").glob("P4-*.approved.json"))


def test_changed_reviewer_instructions_reuse_generation(stage, monkeypatch):
    artifacts(stage)
    pack = agent.load_pack("task-breakdown")
    recovery.save(stage, pack, "request", "job", "verified")
    (agent.AGENTS_DIR / "task-breakdown/validator/system_prompt.md").write_text("New review checks")
    assert recovery.next_action(stage, pack)[0] == "verify"
    async def review(built, message, callbacks, run_name):
        assert run_name.endswith("-verify")
        return verdict()
    monkeypatch.setattr(cli, "_stream", review)
    assert asyncio.run(cli._run("request", "task-breakdown", P, resume=True)) == 0


def test_artifact_changes_during_review_cannot_be_approved(stage, monkeypatch):
    async def stream(built, message, callbacks, run_name):
        artifacts(stage, "initial" if run_name.endswith("-write") else "changed during review")
        return {"messages": []} if run_name.endswith("-write") else verdict()
    monkeypatch.setattr(cli, "_stream", stream)
    assert asyncio.run(cli._run("request", "task-breakdown", P)) == 1
    assert not report(stage)["verified"]
    assert recovery.next_action(stage, agent.load_pack("task-breakdown"))[0] == "verify"


def test_model_fix_does_not_allow_changed_source_checkpoint(stage):
    artifacts(stage)
    pack = agent.load_pack("task-breakdown")
    recovery.save(stage, pack, "request", "job", "review_pending")
    (stage / "prd.md").write_text("Changed source")
    assert recovery.next_action(stage, pack)[0] == "generate"


def test_orchestrator_automatically_resumes_review_once_then_waits_at_gate(stage, monkeypatch):
    artifacts(stage)
    recovery.save(stage, agent.load_pack("task-breakdown"), "request", "job", "review_pending")
    monkeypatch.setattr(orch, "STAGES", (orch.STAGES[0],))
    calls = []
    async def review(built, message, callbacks, run_name):
        calls.append(run_name)
        assert run_name.endswith("-verify")
        return verdict()
    monkeypatch.setattr(cli, "_stream", review)
    def runner(agent_name, request, project):
        code = asyncio.run(cli._run(request, agent_name, project, resume=True))
        return {"status": report(stage)["status"], "exit_code": code}
    assert orch.orchestrate(P, runner=runner, out=lambda _: None) == orch.WAITING
    assert calls == ["task-breakdown/validator-verify"]
    assert orch.orchestrate(P, runner=lambda *a: pytest.fail("completed stage restarted"), out=lambda _: None) == orch.WAITING
    assert not list((stage / "gates").glob("P4-*.approved.json"))


def test_orchestrator_recovers_committed_merge_before_state_save(parallel_root):
    base = fake_runner([])
    def run(*args, **kwargs):
        result = base(*args, **kwargs)
        result["status"] = "success"
        return result
    parallel.run_pair(parallel_root, steps(), run)
    assert parallel.pending(parallel_root)
    assert orch.orchestrate("demo", runner=lambda *a, **kw: pytest.fail("merge replay reran a writer"),
                            out=lambda _: None) == orch.WAITING
    assert not parallel.pending(parallel_root)
    assert orch.load_state(parallel_root)["task-breakdown"]["status"] == "success"


@pytest.mark.parametrize("changed", [False, True])
@pytest.mark.parametrize("already_merged", [False, True])
def test_legacy_parallel_session_can_be_recovered_without_model_calls(parallel_root, changed, already_merged):
    session = config.LOGS_DIR / "parallel/legacy"
    base = fake_runner([])
    for step in steps():
        source = session / step.stage.agent / "outputs/demo"
        shutil.copytree(parallel_root, source)
        base(step.stage.agent, step.request, "demo", outputs_dir=source.parent, logs_dir=session / "logs")
        (source / "report.json").write_text(json.dumps({
            "agent": step.stage.agent, "project": "demo", "request_text": step.request, "job_id": "old-job",
            "finished_at": "2026-11-17T01:00:00Z", "status": "partial", "verified": False,
            "passes": [{"agent": step.stage.agent, "kind": "write", "ok": True}],
            "verdict": {"gaps": ["review incomplete"]}}))
    if already_merged:
        for agent_name in parallel.OWNED:
            source = session / agent_name / "outputs/demo"
            for directory in parallel.OWNED[agent_name]:
                if (source / directory).is_dir():
                    shutil.copytree(source / directory, parallel_root / directory, dirs_exist_ok=True)
    if changed:
        (parallel_root / "architecture.md").write_text("New input")
        with pytest.raises(ValueError, match="changed"):
            parallel.recover_session(parallel_root, session)
        if not already_merged:
            assert not (parallel_root / "backlog").exists()
    else:
        result = parallel.recover_session(parallel_root, session)
        assert result["task-breakdown"]["status"] == "partial"
        assert recovery.next_action(parallel_root, agent.load_pack("task-breakdown"))[0] == "verify"


def test_unfinished_parallel_session_resumes_without_requiring_parallel_flag(parallel_root):
    base = fake_runner([])
    failed = False
    def run(agent_name, *args, **kwargs):
        nonlocal failed
        if agent_name == "task-breakdown" and not failed:
            failed = True
            raise RuntimeError("interrupted")
        return base(agent_name, *args, **kwargs)
    with pytest.raises(RuntimeError):
        parallel.run_pair(parallel_root, steps(), run)
    assert parallel.replay_pending(parallel_root, runner=run)["task-breakdown"]["status"] == "partial"


def test_engine_backups_are_excluded_from_artifact_history(parallel_root):
    from agent_engine.history import fingerprint
    data = parallel_root / ".engine-recovery/artifacts/id/infra/file.json"
    data.parent.mkdir(parents=True)
    data.write_text("retained data")
    assert not any(".engine-" in rel for rel in fingerprint(parallel_root))


@pytest.mark.parametrize("corrupt_record", [False, True])
def test_changed_artifacts_require_explicit_review_without_regeneration(stage, monkeypatch, corrupt_record):
    artifacts(stage)
    pack = agent.load_pack("task-breakdown")
    recovery.save(stage, pack, "request", "job", "review_pending")
    if corrupt_record:
        recovery.path(stage, pack.name).write_text("not json")
    else:
        artifacts(stage, "manual correction")
    assert recovery.next_action(stage, pack)[0] == "conflict"
    def no_model(*args):
        pytest.fail("conflict triggered a model call")
    original = cli.build_agent
    monkeypatch.setattr(cli, "build_agent", no_model)
    assert asyncio.run(cli._run("request", pack.name, P, resume=True)) == 1
    assert asyncio.run(cli._run("request", pack.name, P, resume_verification=True)) == 1
    monkeypatch.setattr(cli, "build_agent", original)
    async def review(built, message, callbacks, run_name):
        assert run_name.endswith("-verify")
        return verdict()
    monkeypatch.setattr(cli, "_stream", review)
    assert asyncio.run(cli._run("request", pack.name, P, review_existing=True)) == 0


def test_real_decision_is_not_cleared_by_model_change(stage, monkeypatch):
    artifacts(stage)
    pack = agent.load_pack("task-breakdown")
    recovery.save(stage, pack, "request", "job", "awaiting_decision", human=True, gaps=["Budget decision needed"])
    monkeypatch.setenv("SDLC_AGENT_STRONG_MODEL", "new:reviewer")
    assert recovery.next_action(stage, pack)[0] == "wait"


def test_tampered_repair_backup_does_not_overwrite_current_work(stage):
    artifacts(stage, "original")
    pack = agent.load_pack("task-breakdown")
    record = recovery.save(stage, pack, "request", "job", "repair_running", gaps=["fix"])
    artifacts(stage, "unfinished edit")
    (stage / record["backup"] / "backlog/backlog.md").write_text("tampered")
    with pytest.raises(ValueError, match="backup"):
        recovery.restore_repair(stage, pack, record)
    assert (stage / "backlog/backlog.md").read_text() == "unfinished edit"


def test_completed_feedback_response_waits_for_gate_but_new_decision_is_respected(stage, monkeypatch):
    from agent_engine import gates
    artifacts(stage)
    monkeypatch.setattr(orch, "STAGES", (orch.STAGES[0],))
    gate = gates.load_gates()["P4-G1"]
    def feedback():
        gates.record_decision(stage, gate, "changes_requested", {"name": "Reviewer"}, {"name": "Author"}, "Explain the scope")
    feedback()
    first = orch.assess(P)[0]
    assert first.action == "run"
    recovery.save(stage, agent.load_pack("task-breakdown"), first.request, "job", "verified")
    assert orch.orchestrate(P, runner=lambda *a: pytest.fail("completed feedback response restarted"), out=lambda _: None) == orch.WAITING
    feedback()
    second = orch.assess(P)[0]
    assert second.action == "run" and second.request != first.request


def test_changed_approved_input_prevents_interrupted_repair_restoration(stage):
    artifacts(stage)
    policy = stage / "architecture.md"
    policy.write_text("Original approved policy")
    pack = agent.load_pack("task-breakdown")
    record = recovery.save(stage, pack, "request", "job", "repair_running")
    artifacts(stage, "unfinished edit")
    policy.write_text("New approved policy")
    assert recovery.next_action(stage, pack)[0] == "generate"     # changed input: regenerate, never restore
    with pytest.raises(ValueError, match="inputs changed"):
        recovery.restore_repair(stage, pack, record)
    assert policy.read_text() == "New approved policy"


def test_restart_after_state_save_before_merge_acknowledgment(parallel_root, monkeypatch):
    base = fake_runner([])
    def run(*args, **kwargs):
        result = base(*args, **kwargs)
        result["status"] = "success"
        return result
    parallel.run_pair(parallel_root, steps(), run)
    actual = parallel.acknowledge
    monkeypatch.setattr(parallel, "acknowledge", lambda *a: (_ for _ in ()).throw(Crash("after state save")))
    with pytest.raises(Crash):
        orch.orchestrate("demo", runner=lambda *a: pytest.fail("retained run restarted"), out=lambda _: None)
    assert orch.load_state(parallel_root)["task-breakdown"]["status"] == "success"
    monkeypatch.setattr(parallel, "acknowledge", actual)
    assert orch.orchestrate("demo", runner=lambda *a: pytest.fail("retained run restarted"), out=lambda _: None) == orch.WAITING
    assert not parallel.pending(parallel_root)


def test_child_cannot_modify_orchestrator_bookkeeping(parallel_root):
    base = fake_runner([])
    def run(agent_name, *args, **kwargs):
        result = base(agent_name, *args, **kwargs)
        if agent_name == "task-breakdown":
            (kwargs["outputs_dir"] / "demo/phase4/orchestrator-state.json").write_text("{}")
        return result
    with pytest.raises(ValueError, match="bookkeeping"):
        parallel.run_pair(parallel_root, steps(), run)
    assert not (parallel_root / "backlog").exists()
