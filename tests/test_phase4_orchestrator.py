"""The Phase 4 orchestrator decides with plain code, so it is tested without a model: a fake runner plays the four
agents (it writes their declared outputs) and the test checks which agents get run, and when it stops for a human."""

import itertools
import json
from pathlib import Path

import pytest

from agent_engine import config, gates
from agent_engine.phase4 import orchestrator as orch
from phase4_helpers import make_design_ready

P = "demo"
PROJECT = {
    "project_name": "demo", "code_repos": ["acme/api"], "infra_repo": "acme/infra", "definition_of_done": ["tested"],
    "story_point_scale": [1, 2, 3], "hours_per_story_point": 6, "max_story_points_per_story": 3, "deadlines": [],
    "team": [{"id": "a", "name": "Asha"}], "calendar": {"sprint_length_days": 14},
}
from agent_engine.agent import load_pack
OUTPUTS = {s.agent: load_pack(s.agent).output_files for s in orch.STAGES}


_RUNS = itertools.count(1)  # one counter for every fake agent, so a re-run always writes new content


class FakeAgents:
    def __init__(self, root: Path, status: str = "success"):
        self.root, self.status, self.calls, self.requests = root, status, [], []

    def __call__(self, agent: str, request: str, project: str) -> dict:
        self.calls.append(agent)
        self.requests.append(request)
        for f in OUTPUTS[agent]:  # new content on every run, as a real agent's output would change
            path = self.root / f
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"agent": agent, "run": next(_RUNS)}), encoding="utf-8")
        return {"status": self.status, "exit_code": 0, "gaps": ["open gap"] if self.status != "success" else [],
                "rate_limited": False}


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUTS_DIR", tmp_path / "outputs")
    root = tmp_path / "outputs" / P
    (root / "phase4").mkdir(parents=True)
    (root / "phase4" / "project.json").write_text(json.dumps(PROJECT), encoding="utf-8")
    (root / "prd.md").write_text("prd", encoding="utf-8")
    (root / "architecture.md").write_text("arch", encoding="utf-8")
    make_design_ready(root)
    return root


def go(fake, **kw):
    return orch.orchestrate(P, runner=fake, out=lambda _: None, **kw)


def approve(root, name):
    gates.record_decision(root, gates.load_gates()[name], "approved", {"name": "Dana"}, {"name": "Rahul"})


def test_missing_input_blocks_only_the_agent_that_needs_it(root):
    (root / "prd.md").unlink()
    fake = FakeAgents(root)
    assert go(fake) == orch.WAITING
    assert fake.calls == ["infra-pipeline"]  # infra reads architecture.md only; nothing after Task Breakdown can run


@pytest.mark.real_preflight
def test_every_input_problem_is_reported_up_front_before_any_agent_runs(root):
    """Missing PRD, an unapproved design gate, a member without skills, an undated release: one stop, full list."""
    (root / "prd.md").unlink()
    (root / "gates" / "G3B.approved.json").unlink()
    project = json.loads((root / "phase4" / "project.json").read_text())
    (root / "phase4" / "project.json").write_text(json.dumps({**project, "team": [{"member_id": "a"}]}))
    lines, fake = [], FakeAgents(root)
    assert orch.orchestrate(P, runner=fake, out=lines.append) == orch.FAILED
    assert fake.calls == []                                   # no model was called
    text = "\n".join(lines)
    assert "input problem(s)" in text and "prd.md is missing" in text and "G3B" in text
    assert "project.json is invalid" in text


@pytest.mark.real_preflight
def test_preflight_lists_team_skills_and_undated_releases(tmp_path, monkeypatch):
    from agent_engine.phase4 import files, preflight
    from phase4_helpers import approve_design_gates
    from test_phase4_pipeline import EXAMPLE
    monkeypatch.setattr(config, "OUTPUTS_DIR", tmp_path / "outputs")
    root = tmp_path / "outputs" / "pf"
    (root / "phase4").mkdir(parents=True)
    settings = json.loads((EXAMPLE / "phase4" / "project.json").read_text())
    settings["team"][0]["declared_skills"] = []
    (root / "phase4" / "project.json").write_text(json.dumps(settings))
    (root / "prd.md").write_text("prd")
    (root / "architecture.md").write_text("arch")
    approve_design_gates(root)
    (root / "phase4" / "stories.json").write_text(json.dumps({
        "project": "pf", "source": "file", "releases": [{"name": "MVP", "order": 1}],
        "stories": [{"key": "PF-1", "issue_id": "1", "summary": "s", "fix_versions": ["MVP"]}]}))
    errors, warnings = preflight.check_inputs("pf")
    # A plan can still be made from these, so they are warnings: the run continues and the gaps show at the gates.
    assert not errors
    assert any("without declared_skills" in w and settings["team"][0]["member_id"] in w for w in warnings)
    assert any("releases without a date" in w and "MVP" in w for w in warnings)
    assert any("without acceptance criteria" in w and "PF-1" in w for w in warnings)
    assert files.exists("pf", files.STORIES)


def test_stops_at_the_first_gate_and_never_approves_by_itself(root):
    fake = FakeAgents(root)
    assert go(fake) == orch.WAITING
    assert fake.calls == ["task-breakdown", "infra-pipeline"]  # sprint planning waits for P4-G1
    assert not (root / "gates" / "P4-G1.approved.json").exists()


def test_resumes_after_a_human_approves(root):
    fake = FakeAgents(root)
    go(fake)
    approve(root, "P4-G1")
    assert go(fake) == orch.WAITING
    assert fake.calls == ["task-breakdown", "infra-pipeline", "sprint-planning"]  # then waits at P4-G2


def test_test_approve_runs_the_whole_chain_in_order(root):
    fake = FakeAgents(root)
    assert go(fake, test_approve=True) == orch.DONE
    assert fake.calls == ["task-breakdown", "infra-pipeline", "sprint-planning", "work-allocation"]
    record = json.loads((root / "gates" / "P4-G1.approved.json").read_text(encoding="utf-8"))
    assert "NOT a human sign-off" in record["approver"]["role"]  # recorded as a test, never as a person
    assert go(fake, test_approve=True) == orch.DONE and len(fake.calls) == 4  # nothing to do the second time


def test_a_team_change_also_invalidates_infra_codeowners(root):
    go(FakeAgents(root), test_approve=True)
    project = json.loads((root / "phase4" / "project.json").read_text(encoding="utf-8"))
    project["team"].append({"id": "b", "name": "Bo"})
    (root / "phase4" / "project.json").write_text(json.dumps(project), encoding="utf-8")
    fake = FakeAgents(root)
    assert go(fake, test_approve=True) == orch.DONE
    assert fake.calls == ["infra-pipeline", "sprint-planning", "work-allocation"]


def test_a_prd_change_reruns_everything_that_depends_on_it(root):
    go(FakeAgents(root), test_approve=True)
    (root / "prd.md").write_text("a new requirement", encoding="utf-8")
    fake = FakeAgents(root)
    assert go(fake, test_approve=True) == orch.DONE
    assert fake.calls == ["task-breakdown", "sprint-planning", "work-allocation"]  # infra reads only architecture.md


def test_requested_changes_go_back_to_the_owning_agent_with_the_comment(root):
    go(FakeAgents(root), test_approve=True)
    gates.record_decision(root, gates.load_gates()["P4-G2"], "changes_requested", {"name": "Dana"}, {"name": "Rahul"},
                          "Move the polish story before the deadline.")
    fake = FakeAgents(root)
    assert go(fake, test_approve=True) == orch.DONE
    assert fake.calls[0] == "sprint-planning" and "Move the polish story" in fake.requests[0]


def test_a_partial_result_stops_the_run_and_is_not_test_approved(root):
    fake = FakeAgents(root, status="partial")
    assert go(fake, test_approve=True) == orch.FAILED
    assert fake.calls == ["task-breakdown", "infra-pipeline"]  # independent work is retained too
    assert not (root / "gates" / "P4-G1.approved.json").exists()
    assert go(FakeAgents(root, status="partial"), test_approve=True, plan_only=True) == orch.WAITING


def test_a_rate_limit_beyond_the_wait_limit_stops_with_the_reason(root, monkeypatch):
    calls, waits = [], []
    monkeypatch.setattr(orch, "_sleep", waits.append)
    monkeypatch.setenv("AGENT_ENGINE_RATE_LIMIT_MAX_WAIT_SECONDS", "60")

    def limited(agent, request, project):
        calls.append(agent)
        return {"status": "fail", "exit_code": 1, "gaps": [], "rate_limited": True, "retry_after": 7000}

    assert go(limited, test_approve=True) == orch.FAILED and calls == ["task-breakdown"] and waits == []


def test_a_rate_limit_is_waited_out_and_the_stage_runs_again(root, monkeypatch):
    fake, waits, limited = FakeAgents(root), [], {"left": 1}
    monkeypatch.setattr(orch, "_sleep", waits.append)

    def runner(agent, request, project):
        if agent == "task-breakdown" and limited["left"]:
            limited["left"] -= 1
            return {"status": "fail", "exit_code": 1, "gaps": [], "rate_limited": True, "retry_after": 30}
        return fake(agent, request, project)

    assert go(runner, test_approve=True) == orch.DONE
    assert waits == [30] and fake.calls.count("task-breakdown") == 1


def test_transient_provider_errors_back_off_then_give_up_cleanly(root, monkeypatch):
    waits = []
    monkeypatch.setattr(orch, "_sleep", waits.append)
    monkeypatch.setenv("AGENT_ENGINE_PROVIDER_RETRIES", "2")
    monkeypatch.setenv("AGENT_ENGINE_TRANSIENT_BACKOFF_SECONDS", "5")

    def overloaded(agent, request, project):
        return {"status": "fail", "exit_code": 1, "gaps": [], "rate_limited": False, "transient": True}

    assert go(overloaded, test_approve=True) == orch.FAILED and waits == [5, 10]


def test_a_project_run_by_hand_is_rerun_fresh_unless_resume_is_asked(root):
    fake = FakeAgents(root)
    for agent in OUTPUTS:
        fake(agent, "", P)
    fake.calls.clear()
    for name in ("P4-G1", "P4-G2", "P4-G3", "P4-G4", "G4"):
        approve(root, name)
    steps = orch.assess(P)
    assert steps[0].action == "run" and "no recorded run" in steps[0].why     # fresh by default: nothing adopted
    assert go(fake, resume=True) == orch.DONE and fake.calls == []             # explicit resume adopts it
