"""Agent-pack loading (agent.py's load_pack) and the no-shell backend: every
shipped pack must load, a typo must fail loudly, and no agent may ever get
an `execute` tool.
"""

import pytest

from agent_engine import agent, cli


def test_every_shipped_pack_loads():
    for name in agent.available_packs():
        pack = agent.load_pack(name)
        if pack.verifier:
            assert agent.load_pack(pack.verifier).returns == "verdict"


def _write_pack(tmp_path, toml: str):
    pack_dir = tmp_path / "demo"
    pack_dir.mkdir()
    (pack_dir / "agent.toml").write_text(toml, encoding="utf-8")
    (pack_dir / "system_prompt.md").write_text("You are a demo agent.", encoding="utf-8")


@pytest.mark.parametrize(
    "toml, error",
    [
        ('tools = ["jira"]', "unknown tool 'jira'"),
        ('modle = "fast"', "unknown key 'modle'"),
        ('filesystem = ["read_file", "writefile"]', "unknown filesystem tool 'writefile'"),
        ('filesystem = ["execute"]', "unknown filesystem tool 'execute'"),
        ('returns = "json"', "returns must be"),
        ('[input]\nfiles = ["../secrets.md"]', "must be a path inside the project folder"),
        ('[output]\nfiles = ["/etc/passwd"]', "must be a path inside the project folder"),
        ('[input]\nfile = ["prd.md"]', r"unknown key 'file' in \[input\]"),
        ('request_history = "mine"', "request_history must be one of"),
    ],
)
def test_bad_pack_is_rejected(tmp_path, monkeypatch, toml, error):
    monkeypatch.setattr(agent, "AGENTS_DIR", tmp_path)
    _write_pack(tmp_path, toml)
    with pytest.raises(ValueError, match=error):
        agent.load_pack("demo")


def test_nested_validator_is_its_own_pack():
    assert {"prd", "prd/validator"} <= set(agent.available_packs())
    assert agent.load_pack("prd").verifier == "prd/validator"


@pytest.mark.parametrize("name", ["../secrets", "prd/../../x", "/etc", "PRD", "prd/"])
def test_pack_name_cannot_escape_agents_dir(name):
    with pytest.raises(ValueError, match="invalid agent name"):
        agent.load_pack(name)


def test_no_agent_gets_a_shell(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-fake")
    for name in agent.available_packs():
        graph = agent.build_agent(agent.load_pack(name))
        tool_names = set(graph.get_graph().nodes["tools"].data.tools_by_name)
        assert "execute" not in tool_names, name


def test_helper_subagent_gets_the_write_guard_and_lock(monkeypatch):
    """deepagents' general-purpose helper (`task` tool) must run with the same
    file tools, write guard and lock as its agent, for every shipped pack.
    """
    from deepagents.middleware.subagents import SubAgentMiddleware

    from agent_engine.guardrails import OutputsOnlyGuardMiddleware
    from agent_engine.locking import FileLockMiddleware

    seen = []
    original_init = SubAgentMiddleware.__init__

    def spy(self, *args, **kwargs):
        seen.append(kwargs["subagents"])
        original_init(self, *args, **kwargs)

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-fake")
    monkeypatch.setattr(SubAgentMiddleware, "__init__", spy)
    for name in agent.available_packs():
        seen.clear()
        pack = agent.load_pack(name)
        agent.build_agent(pack)
        helpers = [s for s in seen[0] if s["name"] == "general-purpose"]
        assert len(helpers) == 1, name
        stack = helpers[0]["middleware"]
        kinds = {type(m) for m in stack}
        assert {OutputsOnlyGuardMiddleware, FileLockMiddleware} <= kinds, name
        file_tools = [sorted(t.name for t in m.tools) for m in stack if type(m).__name__ == "FilesystemMiddleware"]
        if pack.filesystem is not None:
            assert file_tools == [sorted(pack.filesystem)], name


def test_requests_are_numbered_and_kept(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "OUTPUTS_DIR", tmp_path)
    assert cli._record_request("demo", "Build a gym app") == 1
    assert cli._record_request("demo", "Reminders on WhatsApp only") == 2
    text = (tmp_path / "demo" / "requests.md").read_text(encoding="utf-8")
    assert "## Request 1" in text and "Build a gym app" in text
    assert "## Request 2" in text and "WhatsApp only" in text


def test_agent_request_history_is_kept_apart(tmp_path, monkeypatch):
    """request_history = "agent": the pack's requests go to requests/<agent>.md,
    numbered on their own, and every message points the agent there.
    """
    monkeypatch.setattr(agent, "AGENTS_DIR", tmp_path)
    monkeypatch.setattr(cli, "OUTPUTS_DIR", tmp_path / "outputs")
    _write_pack(tmp_path, 'request_history = "agent"\nverifier = "demo"')
    pack = agent.load_pack("demo")
    assert pack.requests_file == "requests/demo.md"
    assert cli._record_request("p", "Another agent's request") == 1
    assert cli._record_request("p", "Build a gym app", pack.requests_file) == 1
    assert cli._record_request("p", "WhatsApp only", pack.requests_file) == 2
    assert "Another agent" not in (tmp_path / "outputs/p/requests/demo.md").read_text(encoding="utf-8")
    for message in (
        cli._agent_message(pack, "WhatsApp only", "p", 2),
        cli._verifier_message(pack, "p"),
        cli._fix_message(pack, "p", ["US-4 has no acceptance criteria"]),
    ):
        assert "/outputs/p/requests/demo.md" in message and "/outputs/p/requests.md" not in message


def test_default_request_history_is_the_shared_requests_md(tmp_path, monkeypatch):
    monkeypatch.setattr(agent, "AGENTS_DIR", tmp_path)
    _write_pack(tmp_path, "")
    pack = agent.load_pack("demo")
    assert pack.requests_file == "requests.md"
    assert "/outputs/p/requests.md" in cli._verifier_message(pack, "p")
