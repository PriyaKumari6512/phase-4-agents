"""Explicit test-mode gate policy. Passing checks is distinct from human sign-off."""
from agent_engine import recovery
from agent_engine.agent import load_pack
from agent_engine.phase4 import files
from agent_engine.phase4.settings import _bool

TEST_ORIGIN = "phase4-env-test-mode"
AGENTS = {"P4-G1": "task-breakdown", "P4-G2": "sprint-planning",
          "P4-G3": "work-allocation", "P4-G4": "infra-pipeline"}


def testing_enabled() -> bool:
    return _bool("PHASE4_AUTO_APPROVE_FOR_TESTING", False)


def automated(record: dict) -> bool:
    approver = record.get("approver") or {}
    return bool(approver.get("automation")) or "NOT a human sign-off" in str(approver.get("role", ""))


def current_review(project: str, gate: str) -> bool:
    action, record = recovery.next_action(files.project_dir(project), load_pack(AGENTS[gate]))
    return action == "complete" and not record.get("human_needed")


def test_publication_allowed(project: str, gate: str, record: dict) -> bool:
    return (testing_enabled() and record.get("approver", {}).get("automation") == TEST_ORIGIN
            and current_review(project, gate))
