"""Phase 4 agent packs: validators and request history are wired, validators get read-only tools, tool schemas
keep their argument names, and the infra secret scan has no false positive on Helm values."""

import pytest

from agent_engine import agent
from agent_engine.phase4 import infra

PHASE4_PACKS = ["task-breakdown", "sprint-planning", "work-allocation", "infra-pipeline"]


@pytest.mark.parametrize("name", PHASE4_PACKS)
def test_phase4_pack_has_a_verdict_validator_and_agent_history(name):
    pack = agent.load_pack(name)
    assert pack.verifier == f"{name}/validator" and pack.request_history == "agent"
    assert agent.load_pack(pack.verifier).returns == "verdict"


def test_task_breakdown_has_no_tools_helpers_or_write_access():
    """Task Breakdown runs as structured calls; its packs carry instructions and models, not tools or helpers."""
    for name in ("task-breakdown", "task-breakdown/validator"):
        pack = agent.load_pack(name)
        assert pack.tools == [] and pack.subagents == () and set(pack.filesystem) <= {"ls", "read_file"}
    assert agent.load_pack("task-breakdown").models == ["strong", "frontier"]


def test_validators_only_get_read_only_tools(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-fake")
    writers = {"backlog_update", "backlog_build", "backlog_set_features", "backlog_validate", "sprint_solve",
               "sprint_annotate", "allocation_solve", "allocation_annotate", "infra_set_intent", "infra_render",
               "infra_validate", "write_file", "edit_file"}
    for name in PHASE4_PACKS:
        graph = agent.build_agent(agent.load_pack(f"{name}/validator"))
        tools = set(graph.get_graph().nodes["tools"].data.tools_by_name)
        assert not tools & writers, (name, tools & writers)


def test_every_tool_schema_keeps_its_argument_names():
    """LangChain renames some argument names (e.g. `args` -> `v__args`), which breaks the call at run time."""
    import inspect

    from agent_engine.phase4 import tools

    for factory in tools.TOOL_FACTORIES.values():
        for t in factory():
            assert set(t.args) == set(inspect.signature(t.func).parameters), t.name


def test_wrong_argument_types_come_back_as_text(tmp_path, monkeypatch):
    from agent_engine import config
    from agent_engine.phase4 import tools

    monkeypatch.setattr(config, "OUTPUTS_DIR", tmp_path)
    bad = tools.sprint_solve.invoke({"project": "p", "business_values": "not a dict"})
    assert isinstance(bad, str) and "business_values" in bad


@pytest.mark.parametrize("text, hit", [
    ('envFromSecret: "taskflow-api-env"', False),
    ('password: "${var.db_password}"', False),
    ('password: "hunter2hunter2"', True),
    ('api_key = "abcdef123456"', True),
    ("aws_access_key_id = AKIAABCDEFGHIJKLMNOP", True),
])
def test_secret_scan(text, hit):
    assert any(p.search(text) for p in infra.SECRET_PATTERNS) is hit
