"""Human approval gates (gates.py): decisions are logged, an approval pins
the files it approved, maker-checker holds, and a gated agent can't run
before approval or after an approved file changes.
"""

import asyncio
import json

import pytest

from agent_engine import agent, cli, gates

ALICE = {"name": "Alice", "role": "Delivery Manager"}
BOB = {"name": "Bob", "role": "Business Analyst"}
G1 = gates.Gate("G1", "Scope", ["scope/scope.md", "requirements/register.md"])


@pytest.fixture
def project(tmp_path):
    project = tmp_path / "outputs" / "p"
    for f in G1.files:
        (project / f).parent.mkdir(parents=True, exist_ok=True)
        (project / f).write_text(f"v1 of {f}", encoding="utf-8")
    return project


def test_gates_file_is_loaded_and_checked(tmp_path):
    path = tmp_path / "gates.toml"
    path.write_text('[G1]\ndescription = "Scope"\nfiles = ["scope/scope.md"]\n', encoding="utf-8")
    assert gates.load_gates(path)["G1"].approval_file == "gates/G1.approved.json"
    assert gates.load_gates(tmp_path / "missing.toml") == {}


@pytest.mark.parametrize(
    "toml, error",
    [
        ('[G1]\nfile = ["scope.md"]', "unknown key 'file'"),
        ("[G1]\nfiles = []", "needs files"),
        ('[G1]\nfiles = ["../secrets.md"]', "must be a path inside the project folder"),
        ('["bad gate"]\nfiles = ["a.md"]', "must be a gate table"),
    ],
)
def test_bad_gates_file_is_rejected(tmp_path, toml, error):
    (tmp_path / "gates.toml").write_text(toml, encoding="utf-8")
    with pytest.raises(ValueError, match=error):
        gates.load_gates(tmp_path / "gates.toml")


def test_the_shipped_gates_file_loads():
    gates.load_gates()


def test_approval_pins_the_approved_files(project):
    record = gates.record_decision(project, G1, "approved", ALICE, BOB, "Looks complete")
    approval = json.loads((project / "gates/G1.approved.json").read_text(encoding="utf-8"))
    assert approval == record
    assert set(record["artifacts"]) == set(G1.files)
    assert all(d.startswith("sha256:") for d in record["artifacts"].values())
    history = (project / "gates/history.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["decision"] for line in history] == ["approved"]


@pytest.mark.parametrize("approver", [BOB, {"name": " bob "}, {"name": "Robert", "id": "u-1"}])
def test_submitter_cant_approve_their_own_work(project, approver):
    submitter = {"name": "Bob", "id": "u-1"} if "id" in approver else BOB
    with pytest.raises(ValueError, match="maker-checker"):
        gates.record_decision(project, G1, "approved", approver, submitter)


def test_cant_approve_files_that_dont_exist(project):
    (project / "scope/scope.md").unlink()
    with pytest.raises(ValueError, match="scope/scope.md doesn't exist"):
        gates.record_decision(project, G1, "approved", ALICE, BOB)


@pytest.mark.parametrize("decision", ["changes_requested", "rejected"])
def test_later_decision_withdraws_the_approval(project, decision):
    gates.record_decision(project, G1, "approved", ALICE, BOB)
    gates.record_decision(project, G1, decision, ALICE, BOB, "Estimate is too vague")
    assert not (project / "gates/G1.approved.json").exists()
    history = (project / "gates/history.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["decision"] for line in history] == ["approved", decision]


def test_approval_goes_stale_when_an_approved_file_changes(project):
    gates.record_decision(project, G1, "approved", ALICE, BOB)
    inputs = ["scope/scope.md", "gates/G1.approved.json"]
    assert gates.stale_approvals(project, inputs) == []
    (project / "scope/scope.md").write_text("v2", encoding="utf-8")
    [problem] = gates.stale_approvals(project, inputs)
    assert "scope/scope.md changed after G1 was approved" in problem


def test_gated_agent_runs_only_while_the_approval_holds(project, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(agent, "AGENTS_DIR", tmp_path / "agents")
    monkeypatch.setattr(cli, "OUTPUTS_DIR", tmp_path / "outputs")
    pack_dir = tmp_path / "agents" / "prd-next"
    pack_dir.mkdir(parents=True)
    (pack_dir / "agent.toml").write_text('[input]\nfiles = ["scope/scope.md", "gates/G1.approved.json"]', encoding="utf-8")
    (pack_dir / "system_prompt.md").write_text("x", encoding="utf-8")

    def no_model(*args, **kwargs):
        raise AssertionError("the agent must not be built")

    monkeypatch.setattr(cli, "build_agent", no_model)
    monkeypatch.setattr(cli, "load_gates", lambda: {"G1": G1})

    assert asyncio.run(cli._run("Write the PRD", "prd-next", "p")) == 1
    assert "can't run until gate G1 is approved" in capsys.readouterr().out

    gates.record_decision(project, G1, "approved", ALICE, BOB)
    (project / "scope/scope.md").write_text("changed after approval", encoding="utf-8")
    assert asyncio.run(cli._run("Write the PRD", "prd-next", "p")) == 1
    assert "changed after G1 was approved" in capsys.readouterr().out


def test_cli_gate_command(project, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(cli, "load_gates", lambda: {"G1": G1})
    assert cli._gate("G1", "p", "approved", ALICE, BOB, "") == 0
    assert "G1 approved by Alice" in capsys.readouterr().out
    assert cli._gate("G9", "p", "approved", ALICE, BOB, "") == 1
    assert "no gate 'G9'" in capsys.readouterr().out
    assert cli._gate("G1", "p", "approved", BOB, BOB, "") == 1
    assert "maker-checker" in capsys.readouterr().out
