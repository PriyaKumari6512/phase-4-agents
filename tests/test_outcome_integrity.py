"""The minimum corrections that keep a run's reported outcome trustworthy, one test group each:

  6.1  a stage result must come from this invocation's own report, consistent with its exit code
  6.2  a self-contradicting verdict never counts as success; outputs are re-checked after fix passes
  6.3  an UNKNOWN / MODEL_INVALID solve never replaces the last valid sprint plan
  6.4  a scanner that failed, timed out or printed unreadable output is never "passed, zero findings"

plus: the deterministic Phase 4 flow writes the same artifacts with diagnostics on and off.
"""

import asyncio
import json
import re
import shutil
from pathlib import Path

import pytest

from agent_engine import agent, cli, perf
from agent_engine.phase4 import allocation, backlog, files, infra, orchestrator, sandbox, sprint
from agent_engine.phase4 import tools as phase4_tools
from agent_engine.phase4.contracts import Backlog, CheckResult, SprintPlan
from agent_engine.phase4.sandbox import CmdResult
from agent_engine.phase4.sprint_model import SolveResult
from test_model_escalation import _pack, engine  # noqa: F401  (fixture)
from test_phase4_pipeline import AS_OF, P, _enrich, _features, _intent, approve, proj  # noqa: F401  (fixture)


# ============================================================================ 6.1 stale child reports
def _report(tmp_path: Path, **data) -> Path:
    p = tmp_path / "report.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


@pytest.mark.parametrize("data, code, expected, problem", [
    ({"agent": "a", "status": "success"}, 1, "fail", "not from this invocation"),                 # older report left over
    ({"agent": "a", "status": "success", "invocation_id": "other"}, 0, "fail", "not from this invocation"),
    ({"agent": "b", "status": "success", "invocation_id": "inv"}, 0, "fail", "for agent 'b'"),
    ({"agent": "a", "status": "success", "invocation_id": "inv"}, 1, "fail", "contradicts"),       # crashed after writing
    ({"agent": "a", "status": "partial", "invocation_id": "inv", "verdict": {"gaps": ["g"]}}, 1, "partial", None),
    ({"agent": "a", "status": "success", "invocation_id": "inv"}, 0, "success", None),
])
def test_only_this_invocations_consistent_report_counts(tmp_path, data, code, expected, problem):
    status, _, why = orchestrator.read_child_report(_report(tmp_path, **data), "a", "inv", code)
    assert status == expected
    assert (why is None) if problem is None else (problem in why)


def test_missing_report_is_a_failure(tmp_path):
    status, gaps, why = orchestrator.read_child_report(tmp_path / "report.json", "a", "inv", 0)
    assert (status, gaps) == ("fail", []) and "no report.json" in why


def test_child_stamps_its_invocation_id_into_the_report(engine, monkeypatch):  # noqa: F811
    _pack(agent.AGENTS_DIR, "solo", "")
    monkeypatch.setattr(cli, "build_agent", lambda pack, level=0: object())

    async def ok(*a, **k):
        return {"messages": []}

    monkeypatch.setattr(cli, "_stream", ok)
    monkeypatch.setenv(perf.ENV_INVOCATION, "inv-123")
    assert asyncio.run(cli._run("Do it", "solo", "demo")) == 0
    report = json.loads((engine / "demo" / "report.json").read_text(encoding="utf-8"))
    assert report["invocation_id"] == "inv-123"
    status, _, why = orchestrator.read_child_report(engine / "demo" / "report.json", "solo", "inv-123", 0)
    assert (status, why) == ("done", None)


def test_orchestrator_stops_on_a_stale_report_and_says_why(tmp_path, monkeypatch):
    lines = []
    monkeypatch.setattr(orchestrator.config, "OUTPUTS_DIR", tmp_path)
    root = tmp_path / "p"
    (root / "phase4").mkdir(parents=True)
    for f in ("prd.md", "architecture.md"):
        (root / f).write_text("x", encoding="utf-8")
    (root / "phase4/project.json").write_text("{}", encoding="utf-8")

    def runner(agent_name, request, project):
        return {"status": "fail", "exit_code": 1, "gaps": [], "rate_limited": False,
                "report_problem": "report.json is not from this invocation (an older or different run's report)"}

    assert orchestrator.orchestrate("p", runner=runner, out=lines.append) == orchestrator.FAILED
    assert any("not from this invocation" in ln for ln in lines)


# ============================================================================ 6.2 contradictory verdicts
def _verdicts(monkeypatch, verdicts, write_output=None):
    it = iter(verdicts)

    async def fake_stream(built, message, callbacks, run_name):
        name, _ = built
        if name == "judge":
            return {"structured_response": next(it)}
        if write_output:
            write_output(name, run_name)
        return {"messages": []}

    monkeypatch.setattr(cli, "_stream", fake_stream)


def test_unsatisfied_verdict_claiming_success_is_not_success(engine, monkeypatch):  # noqa: F811
    _pack(agent.AGENTS_DIR, "w", 'verifier = "judge"\nmax_fix_loops = 1')
    contradictory = agent.Verdict(satisfied=False, status_so_far="success", gaps=["US-2 is missing"], summary="s")
    _verdicts(monkeypatch, [contradictory, contradictory])
    assert asyncio.run(cli._run("Build", "w", "demo")) == 1
    report = json.loads((engine / "demo" / "report.json").read_text(encoding="utf-8"))
    assert report["status"] == "partial" and "satisfied=false" in report["verdict_inconsistent"]
    assert [p["kind"] for p in report["passes"]] == ["write", "verify", "fix", "verify"]


def test_unchanged_output_that_satisfies_the_request_still_succeeds(engine, monkeypatch):  # noqa: F811
    _pack(agent.AGENTS_DIR, "w", 'verifier = "judge"\nmax_fix_loops = 1\n[output]\nfiles = ["out.md"]')
    (engine / "demo").mkdir(parents=True)
    (engine / "demo" / "out.md").write_text("already right", encoding="utf-8")
    _verdicts(monkeypatch, [agent.Verdict(satisfied=True, status_so_far="success", gaps=[], summary="fine")])
    assert asyncio.run(cli._run("Check it", "w", "demo")) == 0
    assert json.loads((engine / "demo" / "report.json").read_text(encoding="utf-8"))["status"] == "success"


def test_output_deleted_by_a_fix_pass_fails_the_run(engine, monkeypatch):  # noqa: F811
    _pack(agent.AGENTS_DIR, "w", 'verifier = "judge"\nmax_fix_loops = 1\n[output]\nfiles = ["out.md"]')
    out = engine / "demo" / "out.md"

    def writer(name, run_name):
        if run_name.endswith("-write"):
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text("v1", encoding="utf-8")
        elif run_name.endswith("-fix"):
            out.unlink()

    _verdicts(monkeypatch, [agent.Verdict(satisfied=False, status_so_far="partial", gaps=["g"], summary="s"),
                            agent.Verdict(satisfied=True, status_so_far="success", gaps=[], summary="ok")], writer)
    assert asyncio.run(cli._run("Build", "w", "demo")) == 1
    report = json.loads((engine / "demo" / "report.json").read_text(encoding="utf-8"))
    assert report["status"] == "fail" and "missing after its fix passes" in report["error"]


# ============================================================================ 6.3 unsuccessful solver results
def _planned(proj_root: Path) -> dict:  # noqa: F811
    backlog.set_features(P, _features())
    backlog.build(P)
    _enrich(P)
    b = files.read_json(P, files.BACKLOG, Backlog)
    return {s.item_id: 5 for s in b.stories()}


@pytest.mark.parametrize("status", ["UNKNOWN", "MODEL_INVALID"])
def test_unsuccessful_solve_keeps_the_previous_valid_plan(proj, monkeypatch, status):  # noqa: F811
    values = _planned(proj)
    assert json.loads(sprint.solve(P, values, as_of=AS_OF))["solver"] in ("OPTIMAL", "FEASIBLE")
    before = (proj / files.SPRINT_PLAN).read_bytes()
    before_md = (proj / files.SPRINT_PLAN_MD).read_bytes()
    monkeypatch.setattr(sprint, "cpsat_solve", lambda *a, **k: SolveResult(
        status=status, placement={}, objective=None, best_bound=None, wall_time_s=10.0, conflicting=[], sprint_load={}))
    out = phase4_tools._run("sprint_solve", lambda: sprint.solve(P, values, as_of=AS_OF))
    assert out.startswith("ERROR:") and status in out and "previous plan (v1) is kept" in out
    assert (proj / files.SPRINT_PLAN).read_bytes() == before and (proj / files.SPRINT_PLAN_MD).read_bytes() == before_md


def test_unsuccessful_first_solve_writes_no_plan(proj, monkeypatch):  # noqa: F811
    values = _planned(proj)
    monkeypatch.setattr(sprint, "cpsat_solve", lambda *a, **k: SolveResult(
        status="UNKNOWN", placement={}, objective=None, best_bound=None, wall_time_s=10.0, conflicting=[], sprint_load={}))
    with pytest.raises(files.ProjectError, match="no plan was written"):
        sprint.solve(P, values, as_of=AS_OF)
    assert not (proj / files.SPRINT_PLAN).exists()


def test_check_rejects_a_plan_written_from_an_unknown_solve(proj):  # noqa: F811
    values = _planned(proj)
    sprint.solve(P, values, as_of=AS_OF)
    plan = files.read_json(P, files.SPRINT_PLAN, SprintPlan)
    plan.solver.status = "UNKNOWN"                       # what the old code could leave behind
    files.write_json(P, files.SPRINT_PLAN, plan)
    assert any("UNKNOWN" in p for p in json.loads(sprint.check(P))["problems"])


# ============================================================================ 6.4 scanner outcomes
@pytest.fixture
def scan(tmp_path, monkeypatch):
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    results: dict[str, CmdResult] = {}
    available = {"tflint", "trivy", "checkov", "actionlint", "gitleaks", "conftest", "helm", "tofu"}
    monkeypatch.setattr(sandbox, "_available", lambda tool, use_docker: tool in available)
    monkeypatch.setattr(sandbox, "_exec", lambda cmd, wd, docker, timeout=300, **kw: results[kw["tool"]])
    monkeypatch.setattr(sandbox, "get_settings", lambda: type("S", (), {
        "phase4_infra_catalog_dir": str(tmp_path / "catalog"), "phase4_iac_sandbox_mode": "auto"})())
    (tmp_path / "catalog" / "policies").mkdir(parents=True)

    def run(tools: set[str]) -> dict[str, CheckResult]:
        out = sandbox._run_checks(tmp_path, [], [t for t in sandbox.ALL_TOOLS if t in tools], False, True)
        return {r.tool: r for r in out}

    return results, available, run


def _trivy_json(n: int) -> str:
    return json.dumps({"Results": [{"Target": f"envs/dev/core/m{i}.tf", "Misconfigurations": [
        {"ID": f"AVD-AWS-{i:04d}", "Severity": "HIGH", "Title": "S3 bucket without encryption " + "x" * 80}]}
        for i in range(n)]})


def test_scanner_outcomes_are_classified_honestly(scan):
    results, available, run = scan
    big = _trivy_json(400)
    assert len(big) > 20000                     # larger than the old 20,000-character tail that was parsed
    results.update({
        "trivy": CmdResult(0, big, "2026-11-16T10:00:00Z WARN some trailing log line\n"),   # large valid JSON + stderr
        "checkov": CmdResult(0, "Traceback: not json at all", ""),                         # invalid output, exit 0
        "tflint": CmdResult(1, json.dumps({"issues": [], "errors": [{"message": "plugin failed"}]}), ""),
        "actionlint": CmdResult(0, "", ""),                                                 # clean
        "gitleaks": CmdResult(127, "", "sh: gitleaks: not found"),                         # cannot run
        "conftest": CmdResult(124, "", "timeout after 300s", timed_out=True),
    })
    r = run({"trivy", "checkov", "tflint", "actionlint", "gitleaks", "conftest"})
    assert (r["trivy"].outcome, len(r["trivy"].findings), r["trivy"].passed) == ("findings", 400, False)
    assert (r["checkov"].outcome, r["checkov"].passed, r["checkov"].skipped) == ("parse_error", False, True)
    assert (r["tflint"].outcome, r["tflint"].passed) == ("execution_error", False)
    assert (r["actionlint"].outcome, r["actionlint"].passed) == ("passed", True)
    assert (r["gitleaks"].outcome, r["gitleaks"].passed) == ("execution_error", False)
    assert "could not run" in r["gitleaks"].summary and "secrets found" not in r["gitleaks"].summary
    assert (r["conftest"].outcome, r["conftest"].skipped, r["conftest"].passed) == ("timeout", True, False)
    assert not any(c.passed and c.outcome != "passed" for c in r.values())
    assert sorted(sandbox.incomplete(list(r.values()))) == ["checkov: parse_error", "conftest: timeout",
                                                             "gitleaks: execution_error", "tflint: execution_error"]


def test_findings_unavailable_tools_and_clean_runs(scan):
    results, available, run = scan
    available.discard("conftest")
    results.update({"gitleaks": CmdResult(1, "leak at file.tf", ""),
                    "trivy": CmdResult(0, json.dumps({"Results": []}), ""),
                    "checkov": CmdResult(0, json.dumps({"results": {"failed_checks": [
                        {"check_id": "CKV_AWS_1", "severity": "LOW", "file_path": "/a.tf", "check_name": "n"}]}}), "")})
    r = run({"gitleaks", "trivy", "checkov", "conftest"})
    assert (r["gitleaks"].outcome, r["gitleaks"].passed) == ("findings", False)
    assert (r["trivy"].outcome, r["trivy"].passed, r["trivy"].findings) == ("passed", True, [])
    assert (r["checkov"].outcome, r["checkov"].passed) == ("findings", True)    # low severity does not block, as before
    assert (r["conftest"].outcome, r["conftest"].skipped) == ("tool_unavailable", True)


def test_parse_json_reads_past_banners_and_trailing_text():
    assert sandbox.parse_json('banner {not json} then {"a": [1, {"b": 2}]} trailing {') == {"a": [1, {"b": 2}]}
    assert sandbox.parse_json("no json here") is None
    assert sandbox.parse_json("", fallback='x [1, 2]') == [1, 2]


def test_skipped_validation_is_reported_as_incomplete(proj):  # noqa: F811
    infra.set_intent(P, _intent())
    infra.render(P)
    v = json.loads(infra.validate(P))                    # PHASE4_IAC_SANDBOX_MODE=off in this fixture
    assert v["checks_passed"] is False                   # skipped checks cannot authorize publication
    assert v["validation_complete"] is False                                  # ... but it is never "complete"
    assert len([x for x in v["incomplete"] if not x.startswith("ci/")]) == 10  # every infra repo check
    assert sorted(x for x in v["incomplete"] if x.startswith("ci/")) == [       # and each CI repo's actionlint
        "ci/acme__taskflow-api actionlint: skipped", "ci/acme__taskflow-web actionlint: skipped"]
    assert any("validation incomplete" in w for w in json.loads(infra.check(P))["warnings"])
    # checks.json written before `outcome` existed still loads
    assert CheckResult.model_validate({"tool": "trivy", "passed": True, "summary": "0 HIGH/CRITICAL"}).outcome is None


# ============================================================================ diagnostics on/off: same artifacts
# Differ between any two runs, diagnostics or not: timestamps, random ids, hashes of files that hold them, and
# the solver's measured wall time (sprint-plan.json solver.wall_time_s and the line of sprint-plan.md showing it).
VOLATILE = {"generated_at", "plan_id", "backlog_id", "backlog_sha256", "sprint_plan_sha256", "decided_at", "at",
            "wall_time_s"}
_SOLVER_TIME = re.compile(r"(Solver \*\*[A-Z_]+\*\* )\([0-9.]+s\)")


def _normalize(value):
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items() if k not in VOLATILE}
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    return value


def _flow(root: Path) -> dict[str, object]:
    backlog.set_features(P, _features())
    backlog.build(P)
    _enrich(P)
    backlog.validate_report(P)
    approve(root, "P4-G1")
    sprint.capacity_report(P, AS_OF)
    b = files.read_json(P, files.BACKLOG, Backlog)
    plan = json.loads(sprint.solve(P, {s.item_id: (8 if s.moscow == "must" else 5) for s in b.stories()}, as_of=AS_OF))
    sprint.annotate(P, {str(s["sprint_index"]): "goal" for s in plan["sprints"] if s["stories"]}, {}, "summary")
    approve(root, "P4-G2")
    first = next(s["sprint_index"] for s in plan["sprints"] if s["stories"])
    allocation.prepare(P, first)
    out = json.loads(allocation.solve(P, first))
    allocation.annotate(P, {a["task_id"]: "fits" for a in out["assignments"]})
    infra.set_intent(P, _intent())
    infra.render(P)
    infra.validate(P)
    artifacts = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if not p.is_file() or rel.split("/")[0] in ("gates", "runs", "logs"):
            continue
        text = p.read_text(encoding="utf-8")
        if rel == files.ASSIGNMENTS_MD:
            continue                     # renders the per-task choice compared through its invariants below
        if rel == files.ASSIGNMENTS:
            artifacts[rel] = _allocation_invariants(json.loads(text))
            continue
        artifacts[rel] = _normalize(json.loads(text)) if rel.endswith(".json") else _SOLVER_TIME.sub(r"\1(…s)", text)
    return artifacts


def _allocation_invariants(ap: dict) -> dict:
    """The local CP-SAT allocation (8 workers) breaks ties between equally scored assignments differently from run
    to run, diagnostics or not. What is stable: engine, status, optimal objective, which tasks are assigned or not,
    total planned hours, eligibility."""
    return {"engine": ap["solver_engine"], "status": ap["solver_status"], "score": ap["solver_score"],
            "assigned": sorted(a["task_id"] for a in ap["assignments"]),
            "unassigned": sorted(u["task_id"] for u in ap["unassigned"]),
            "planned_hours": round(sum(w["planned_hours"] for w in ap["workers"]), 1),
            "eligibility": ap["eligibility"], "annotated": ap["annotated"]}


def test_artifacts_are_identical_with_diagnostics_on_and_off(proj, tmp_path, monkeypatch):  # noqa: F811
    off = _flow(proj)
    shutil.rmtree(proj)
    shutil.copytree(Path(__file__).parent / "fixtures" / "phase4" / "bookmarks", proj)
    (proj / "phase4").mkdir()
    example = Path(__file__).resolve().parents[1] / "examples" / "phase4" / "taskflow" / "phase4"
    for name in ("project.json", "history.json"):
        shutil.copy(example / name, proj / "phase4" / name)
    perf.reset_for_tests()
    monkeypatch.setenv(perf.ENV_SESSION, "equivalence")
    monkeypatch.setenv(perf.ENV_SAMPLE_SECONDS, "0")
    try:
        assert perf.init("test", force=True, perf_dir=tmp_path / "perf")
        on = _flow(proj)
        perf.shutdown()
        assert any((tmp_path / "perf" / "equivalence" / "events").glob("*.jsonl"))
    finally:
        perf.reset_for_tests()
    assert off.keys() == on.keys()
    different = [k for k in off if off[k] != on[k]]
    assert different == [], different
