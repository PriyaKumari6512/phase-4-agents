"""The Phase 4 orchestrator decides with plain code, so it is tested without a model: a fake runner plays the four
agents (it writes their declared outputs) and the test checks which agents get run, and when it stops for a human."""

import itertools
import json
from pathlib import Path

import pytest

from agent_engine import config, gates
from agent_engine.phase4 import orchestrator as orch

P = "demo"
PROJECT = {
    "project_name": "demo", "code_repos": ["acme/api"], "infra_repo": "acme/infra", "definition_of_done": ["tested"],
    "story_point_scale": [1, 2, 3], "hours_per_story_point": 6, "max_story_points_per_story": 3, "deadlines": [],
    "team": [{"id": "a", "name": "Asha"}], "calendar": {"sprint_length_days": 14},
}
OUTPUTS = {  # what each fake agent writes
    "task-breakdown": ["backlog/backlog.json"], "infra-pipeline": ["infra/intent.json", "infra/manifest.json"],
    "sprint-planning": ["sprint/sprint-plan.json"], "work-allocation": ["allocation/assignments.json"],
}


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


def test_a_team_change_reruns_only_planning_and_allocation(root):
    go(FakeAgents(root), test_approve=True)
    project = json.loads((root / "phase4" / "project.json").read_text(encoding="utf-8"))
    project["team"].append({"id": "b", "name": "Bo"})
    (root / "phase4" / "project.json").write_text(json.dumps(project), encoding="utf-8")
    fake = FakeAgents(root)
    assert go(fake, test_approve=True) == orch.DONE
    assert fake.calls == ["sprint-planning", "work-allocation"]  # not the backlog, not the infra


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
    assert fake.calls == ["task-breakdown"]
    assert not (root / "gates" / "P4-G1.approved.json").exists()
    assert go(FakeAgents(root, status="partial"), test_approve=True, plan_only=True) == orch.WAITING


def test_a_rate_limit_stops_the_run_so_it_can_resume(root):
    calls = []

    def limited(agent, request, project):
        calls.append(agent)
        return {"status": "fail", "exit_code": 1, "gaps": [], "rate_limited": True}

    assert go(limited, test_approve=True) == orch.FAILED and calls == ["task-breakdown"]


def test_a_project_run_by_hand_is_adopted_not_rerun(root):
    fake = FakeAgents(root)
    for agent in OUTPUTS:
        fake(agent, "", P)
    fake.calls.clear()
    for name in ("P4-G1", "P4-G2", "P4-G3", "P4-G4"):
        approve(root, name)
    assert go(fake) == orch.DONE and fake.calls == []
