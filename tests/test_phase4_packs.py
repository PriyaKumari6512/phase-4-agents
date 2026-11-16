"""Phase 4 agent packs: skills and named subagents are wired into deepagents with the same safety as the
helper, the spec-kit skills load, and the infra secret scan has no false positive on Helm values."""

import pytest

from agent_engine import agent
from agent_engine.phase4 import infra

PHASE4_PACKS = ["task-breakdown", "sprint-planning", "work-allocation", "infra-pipeline"]


@pytest.mark.parametrize("name", PHASE4_PACKS)
def test_phase4_pack_has_a_verdict_validator_and_agent_history(name):
    pack = agent.load_pack(name)
    assert pack.verifier == f"{name}/validator" and pack.request_history == "agent"
    assert agent.load_pack(pack.verifier).returns == "verdict"


def test_task_breakdown_gets_speckit_skills_and_safe_subagents(monkeypatch):
    from deepagents.middleware.skills import SkillsMiddleware, _list_skills
    from deepagents.middleware.subagents import SubAgentMiddleware

    from agent_engine.backends import build_backend
    from agent_engine.guardrails import OutputsOnlyGuardMiddleware
    from agent_engine.locking import FileLockMiddleware

    pack = agent.load_pack("task-breakdown")
    names = {s["name"] for s in _list_skills(build_backend(pack.knowledge, pack.skills), "/skills/")}
    assert {"speckit-specify", "speckit-plan", "speckit-tasks", "speckit-analyze"} <= names

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-fake")
    seen = []
    original_init = SubAgentMiddleware.__init__

    def spy(self, *args, **kwargs):
        seen.append(kwargs["subagents"])
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(SubAgentMiddleware, "__init__", spy)
    graph = agent.build_agent(pack)
    specs = {s["name"]: s for s in seen[0]}
    assert {"general-purpose", "speckit-feature", "backlog-enricher"} <= set(specs)
    for name in ("general-purpose", "speckit-feature", "backlog-enricher"):
        kinds = {type(m) for m in specs[name]["middleware"]}
        assert {OutputsOnlyGuardMiddleware, FileLockMiddleware, SkillsMiddleware} <= kinds, name
        tool_names = {t.name for t in specs[name]["tools"]}
        assert {"speckit_script", "backlog_update"} <= tool_names and "execute" not in tool_names, name
    assert "execute" not in set(graph.get_graph().nodes["tools"].data.tools_by_name)


def test_validators_only_get_read_only_tools(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-fake")
    writers = {"backlog_update", "backlog_build", "backlog_set_features", "backlog_validate", "sprint_solve",
               "sprint_annotate", "allocation_solve", "allocation_annotate", "infra_set_intent", "infra_render",
               "infra_validate", "write_file", "edit_file", "speckit_init", "speckit_script"}
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


def test_speckit_script_through_the_tool_interface(tmp_path, monkeypatch):
    import json
    import shutil
    from pathlib import Path

    from agent_engine import config
    from agent_engine.phase4 import tools

    monkeypatch.setattr(config, "OUTPUTS_DIR", tmp_path)
    (tmp_path / "p" / "phase4").mkdir(parents=True)
    shutil.copy(Path(__file__).resolve().parents[1] / "examples/phase4/taskflow/phase4/project.json",
                tmp_path / "p" / "phase4" / "project.json")
    assert "REPO_ROOT" in tools.speckit_init.invoke({"project": "p"})
    out = json.loads(tools.speckit_script.invoke({"project": "p", "script": "resolve-template",
                                                  "script_args": "plan-template --json"}))
    assert out["TEMPLATE_NAME"] == "plan-template"
    assert tools.speckit_script.invoke({"project": "p", "script": "setup-plan", "script_args": "--json",
                                        "feature_directory": "specs/001-x"}).startswith("ERROR:")
    # a wrong argument type comes back as text for the model, it does not raise
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
