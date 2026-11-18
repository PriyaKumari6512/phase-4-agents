"""End to end: all four agents, driven by the real orchestrator, on realistic inputs with a fake model.

Failures are injected on purpose (one story that never passes its checks, scanner findings, a provider rate limit).
The pipeline must still finish, with every issue reported for the gate approvers instead of stopping. This test runs
with the normal suite, i.e. on every change. Network is blocked by tests/conftest.py.
"""
import asyncio
import json

import pytest

from agent_engine import cli, logging_setup
from agent_engine.phase4 import attention, files, orchestrator as orch, sandbox
from agent_engine.phase4 import task_breakdown as tb, sprint_planning as sp, infra_pipeline as ip
from agent_engine.phase4.contracts import Backlog, CheckResult, InfraIntent, SprintPlan
from test_phase4_pipeline import proj as _base_proj, P, _intent
from test_task_breakdown_stories import FakeModel as BreakdownModel
from test_sprint_planning_agent import FakeModel as SprintModel

BAD_STORY = "DEMO-5"


@pytest.fixture
def proj(_base_proj):
    return _base_proj


def _inputs(proj):
    from phase4_helpers import approve_design_gates
    stories = []
    for i in range(1, 9):
        us = f"US-{i:03}"
        stories.append({"key": f"DEMO-{i}", "issue_id": str(i), "summary": f"Account sign-in scenario {i}",
                        "statement": "As staff, I want to sign in so that I can access my screens.",
                        "epic_key": "DEMO-100" if i <= 4 else "DEMO-200", "story_points": 3,
                        "moscow": "must" if i <= 4 else "should", "rank": str(i),
                        "fix_versions": ["MVP" if i <= 4 else "R2"], "requirement_ids": [us, "FR-002"],
                        "acceptance_criteria": [
                            {"ac_id": us + ".AC1", "text": "Given an account, When the password is correct, Then sign in succeeds."},
                            {"ac_id": us + ".AC2", "text": "Given an account, When the password is wrong, Then sign in fails."}]})
    files.write_json(P, files.STORIES, {"project": P, "source": "file", "project_key": "DEMO", "stories": stories,
                                         "epics": [{"key": k, "issue_id": k, "summary": k} for k in ("DEMO-100", "DEMO-200")],
                                         "releases": [{"name": "MVP", "order": 1}, {"name": "R2", "order": 2}]})
    files.write_text(P, files.ARCHITECTURE, "# Architecture\nAWS Kubernetes. POST /api/sessions; users.password_hash. "
                                            "Python API, React screens; QA uses Playwright.\n")
    files.write_text(P, files.PRD, "# PRD\nFR-002: staff sign in. NFR-010: lockout after five attempts.\n")
    approve_design_gates(proj)
    settings = files.read_json(P, files.PROJECT_SETTINGS)
    settings["calendar"]["first_sprint_start"] = "2026-11-17"
    settings["release_deadlines"] = [{"release": "MVP", "due_date": "2026-12-15"}, {"release": "R2", "due_date": "2027-01-15"}]
    files.write_json(P, files.PROJECT_SETTINGS, settings)


def _scanners_with_findings(monkeypatch):
    """Every scanner passes, except checkov which reports findings the policy accepts as warnings."""
    checkov = sandbox._checkov_result(sandbox.CmdResult(0, json.dumps({"results": {"failed_checks": [
        {"check_id": "CKV_TF_1", "check_name": "Module source should use a commit hash", "file_path": "/envs/dev/core/main.tf"},
        {"check_id": "CKV_AWS_58", "check_name": "EKS secrets encryption",
         "file_path": "/.external_modules/github.com/terraform-aws-modules/eks/main.tf"}]},
        "summary": {"parsing_errors": 0}}), ""))
    monkeypatch.setattr(sandbox, "run_checks", lambda wd, envs, **kw: [
        checkov if t == "checkov" else CheckResult(tool=t, passed=True, outcome="passed", summary="fake scanner")
        for t in sandbox.ALL_TOOLS if kw.get("only") is None or t in kw["only"]])


def _in_process_runner(proj, monkeypatch):
    """orchestrator's runner contract, without a subprocess: run the stage, then read its report like run_agent."""
    def run(agent, request, project, **_):
        code = asyncio.run(cli._run(request, agent, project))
        report = json.loads((proj / "report.json").read_text(encoding="utf-8"))
        error = report.get("error") or ""
        reset = orch._RESET_RE.search(error)
        return {"status": report["status"], "exit_code": code, "gaps": (report.get("verdict") or {}).get("gaps", []),
                "rate_limited": any(m in error for m in orch.RATE_LIMIT_MARKERS),
                "retry_after": int(reset.group(1)) if reset else None, "transient": False}
    return run


@pytest.mark.real_preflight
def test_whole_pipeline_finishes_and_reports_injected_failures(proj, monkeypatch, tmp_path):
    _inputs(proj)
    monkeypatch.setattr(cli, "OUTPUTS_DIR", proj.parent)
    monkeypatch.setattr(logging_setup, "OUTPUTS_DIR", proj.parent)
    monkeypatch.setattr(logging_setup, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(cli, "build_langfuse_handler", lambda: None)
    monkeypatch.setattr(cli, "build_agent", lambda *a, **k: pytest.fail("all four stages must be code-driven"))

    # Injected failure 1: the provider rate-limits every call of the first Task Breakdown run (the in-stage model
    # escalation cannot help), so the orchestrator must wait and run the stage again.
    # Injected failure 2: one story never passes its checks (both attempts leave its criteria uncovered).
    breakdown, runs = BreakdownModel(), {"task-breakdown": 0}

    async def flaky_breakdown(schema, system, human, callbacks, spec):
        if runs["task-breakdown"] == 1:
            raise RuntimeError("SUBSCRIPTION_RATE_LIMITED: Anthropic subscription rate-limited (429), resets in 42s")
        result = await breakdown(schema, system, human, callbacks, spec)
        if schema is tb.StoryBreakdown and result.story_key == BAD_STORY:
            for t in result.tasks:
                t.covers = []
        return result
    monkeypatch.setattr(tb, "_invoke", flaky_breakdown)
    # Injected failure 4: the model reviewer of the sprint plan calls something "blocking" (an opinion).
    sprint_model, reviews = SprintModel(), []

    async def sprint_and_review(schema, system, human, callbacks, spec):
        if schema is sp.LightReview:
            reviews.append(human)
            return sp.LightReview(findings=[sp.ReviewFinding(item=BAD_STORY, severity="blocking",
                                                             message="explain the deferral in user terms")])
        return await sprint_model(schema, system, human, callbacks, spec)
    monkeypatch.setattr(sp, "_invoke", sprint_and_review)

    async def intent(*_):
        data = _intent()
        data["environments"] = ["dev", "qa", "stg", "prod"]
        return InfraIntent.model_validate(data)
    monkeypatch.setattr(ip, "_invoke", intent)
    # Injected failure 3: the IaC scanner reports findings.
    _scanners_with_findings(monkeypatch)
    waits, lines = [], []
    monkeypatch.setattr(orch, "_sleep", waits.append)

    inner = _in_process_runner(proj, monkeypatch)

    def runner(agent, request, project, **kw):
        runs[agent] = runs.get(agent, 0) + 1
        return inner(agent, request, project, **kw)
    code = orch.orchestrate(P, test_approve=True, runner=runner, out=lines.append)
    text = "\n".join(lines)
    assert code == orch.DONE, text
    assert runs["task-breakdown"] == 2 and runs["infra-pipeline"] == runs["sprint-planning"] == runs["work-allocation"] == 1

    # The rate limit was waited out once and the stage ran again, fresh.
    assert waits == [42] and "hit a rate limit; waiting 42s" in text
    # The bad story is reported, the other seven were broken down, and the backlog is usable.
    backlog = files.read_json(P, files.BACKLOG, Backlog)
    by = backlog.by_id()
    assert by[BAD_STORY].needs_attention and not backlog.tasks_of(BAD_STORY)
    assert all(backlog.tasks_of(f"DEMO-{i}") for i in range(1, 9) if f"DEMO-{i}" != BAD_STORY)
    assert any(f"needs attention: {BAD_STORY}" in line for line in attention.open_items(P, "task-breakdown"))
    assert f"needs attention: {BAD_STORY}" in text                       # shown to the P4-G1 approver
    # Sprint Planning left the unbroken story out, with the reason, and planned the rest.
    plan = files.read_json(P, files.SPRINT_PLAN, SprintPlan)
    deferred = {d.story_id: d for d in plan.deferred}
    assert BAD_STORY in deferred and deferred[BAD_STORY].reason_code == "unestimated"
    assert all(BAD_STORY not in s.story_ids for s in plan.sprints) and any(s.story_ids for s in plan.sprints)
    assert any(line.startswith(f"left out of the plan: {BAD_STORY}") for line in attention.open_items(P, "sprint-planning"))
    # The model reviewer's "blocking" opinion became a note for the P4-G2 approver; it did not stop the pipeline.
    assert reviews and cli.review_notes(P, "sprint-planning")["findings"]
    assert "review:" in text and "explain the deferral in user terms" in text
    # Work Allocation produced assignments for sprint 1.
    assert files.exists(P, files.ASSIGNMENTS)
    # Scanner findings were reported as warnings, not a stop.
    checks = files.read_json(P, files.INFRA_CHECKS)
    checkov = next(c for c in checks if c["tool"] == "checkov")
    assert checkov["passed"] and len(checkov["findings"]) == 2
    assert any("scanner warning (checkov CKV_TF_1" in line for line in attention.open_items(P, "infra-pipeline"))
    # Every gate was approved (test approvals) and the final gate too.
    for gate in ("P4-G1", "P4-G2", "P4-G3", "P4-G4", "G4"):
        assert (proj / "gates" / f"{gate}.approved.json").is_file(), gate
