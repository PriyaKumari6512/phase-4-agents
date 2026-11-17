"""Builds a deepagents agent from an agent pack: one folder under AGENTS_DIR
holding `agent.toml` (model tier, tools, verifier, ...) and
`system_prompt.md`. Adding an agent means adding a folder, not Python — code
only changes when a pack needs a tool that isn't in TOOLS yet.
"""

from __future__ import annotations

import logging
import asyncio
import inspect
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from deepagents import FilesystemMiddleware, create_deep_agent
from deepagents.middleware.subagents import GENERAL_PURPOSE_SUBAGENT
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field

from agent_engine import perf
from agent_engine.backends import build_backend
from agent_engine.config import (
    AGENTS_DIR,
    FILESYSTEM_TOOLS,
    REQUESTS_DIRNAME,
    REQUESTS_FILENAME,
    SKILLS_VIRTUAL_ROOT,
    resolve_model_tiers,
)
from agent_engine.guardrails import OutputsOnlyGuardMiddleware
from agent_engine.locking import FileLockMiddleware, HelperLimitMiddleware
from agent_engine.model_setup import resolve_model_with_retries, structured_response_format, summarization_middleware
from agent_engine.phase4.tools import TOOL_FACTORIES as PHASE4_TOOLS

logger = logging.getLogger(__name__)

# Tool name a pack's `tools` list can use -> factory returning a list of
# LangChain tools. Adding a tool is adding one entry here.
TOOLS: dict = {**PHASE4_TOOLS}


class Verdict(BaseModel):
    """A judge pack's (`returns = "verdict"`) structured reply, read from
    `final_state["structured_response"]` — never parsed out of free text.
    """

    satisfied: bool = Field(description="True only if the output fully satisfies every request.")
    status_so_far: Literal["success", "fail", "partial"] = Field(
        description="success if satisfied, partial if the output exists but has gaps, fail if it is missing or mostly empty."
    )
    gaps: list[str] = Field(
        default_factory=list, description="Concrete, actionable fixes for the agent; empty when satisfied."
    )
    summary: str = Field(description="Two or three sentences on what was checked and found.")


_RETURN_SCHEMAS = {"verdict": Verdict}
# Folder path under AGENTS_DIR; no "..", no absolute paths, so a name can't escape it.
_PACK_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*(/[a-z0-9][a-z0-9_-]*)*$")
# A file inside the project's output folder, e.g. "prd.md" or "design/flows.md".
_FILE_RE = re.compile(r"^[A-Za-z0-9_-][A-Za-z0-9_.-]*(/[A-Za-z0-9_-][A-Za-z0-9_.-]*)*$")
_PACK_KEYS = {
    "description", "model", "tools", "filesystem", "knowledge", "input", "output", "returns", "verifier", "max_fix_loops",
    "request_history", "skills", "subagents",
}
_IO_KEYS = {"description", "files"}
_SUBAGENT_KEYS = {"description", "prompt", "model"}
_SUBAGENT_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
# "project": one requests.md shared by every agent on the project (default).
# "agent": this agent's own requests/<agent>.md, see config.REQUESTS_DIRNAME.
REQUEST_HISTORIES = ("project", "agent")


MODEL_TIERS = ("strong", "fast", "frontier")


def model_spec(tier: str) -> str:
    """The provider:model string a tier resolves to right now (.env)."""
    tiers = resolve_model_tiers()
    if tier == "frontier":
        return tiers.frontier or tiers.strong
    return tiers.strong if tier == "strong" else tiers.fast


@dataclass(frozen=True)
class AgentPack:
    name: str
    dir: Path
    description: str
    # Escalation order: the first pass runs on models[0]; a failed verdict or a
    # model error moves the next pass one step along (cli.py). One entry = no switching.
    models: list[str]
    tools: list[str]
    # None = deepagents' default filesystem tools (all of FILESYSTEM_TOOLS here).
    filesystem: list[str] | None
    knowledge: Path | None
    # [input] / [output]: what the agent takes and produces. Files are relative to
    # the project's output folder; cli.py checks inputs before a run and outputs after.
    input_description: str
    input_files: list[str]
    output_description: str
    output_files: list[str]
    # Structured-reply schema name ("verdict"), or None for a plain text reply.
    returns: str | None
    verifier: str | None
    max_fix_loops: int
    request_history: str = "project"
    # A folder inside the pack holding Agent Skills (one SKILL.md per sub-folder),
    # readable at /skills/ and offered to the agent and its subagents.
    skills: Path | None = None
    # Named subagents the agent can hand work to with the `task` tool: name ->
    # {"description", "prompt" (text), "model" (tier or None)}. They get the
    # agent's tools, file tools, skills, write guard and lock.
    subagents: tuple[tuple[str, dict], ...] = ()

    @property
    def system_prompt(self) -> str:
        return (self.dir / "system_prompt.md").read_text(encoding="utf-8")

    @property
    def requests_file(self) -> str:
        """This pack's request history, relative to the project's output folder."""
        return f"{REQUESTS_DIRNAME}/{self.name}.md" if self.request_history == "agent" else REQUESTS_FILENAME


def available_packs() -> list[str]:
    """Pack names are folder paths under AGENTS_DIR, so a pack can nest its
    own validator: `prd` and `prd/validator`.
    """
    return sorted(p.parent.relative_to(AGENTS_DIR).as_posix() for p in AGENTS_DIR.glob("**/agent.toml"))


def load_pack(name: str) -> AgentPack:
    """Reads and validates one pack. Fails loudly on a typo'd key, tool or
    filesystem-tool name instead of building an agent that silently lacks it.
    """
    if not _PACK_NAME_RE.fullmatch(name):
        raise ValueError(f"invalid agent name {name!r}: use folder names under agents/, like 'prd' or 'prd/validator'")
    pack_dir = AGENTS_DIR / name
    toml_path = pack_dir / "agent.toml"
    if not toml_path.is_file():
        raise ValueError(f"no agent pack {name!r} at {pack_dir} (available: {', '.join(available_packs()) or 'none'})")
    if not (pack_dir / "system_prompt.md").is_file():
        raise ValueError(f"agent pack {name!r} has no system_prompt.md")

    data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    problems = [f"unknown key {k!r}" for k in data if k not in _PACK_KEYS]
    model = data.get("model", "strong")
    models = [model] if isinstance(model, str) else model
    if not isinstance(models, list) or not models or any(m not in MODEL_TIERS for m in models):
        problems.append(f"model must be 'strong', 'fast', 'frontier', or an escalation list like [\"strong\", \"frontier\"], got {model!r}")
    tools = data.get("tools", [])
    problems += [f"unknown tool {t!r} (registered: {', '.join(TOOLS) or 'none'})" for t in tools if t not in TOOLS]
    filesystem = data.get("filesystem")
    if filesystem is not None:
        problems += [
            f"unknown filesystem tool {t!r} (allowed: {', '.join(sorted(FILESYSTEM_TOOLS))})"
            for t in filesystem if t not in FILESYSTEM_TOOLS
        ]
    returns = data.get("returns")
    if returns is not None and returns not in _RETURN_SCHEMAS:
        problems.append(f"returns must be one of {sorted(_RETURN_SCHEMAS)} or omitted, got {returns!r}")
    request_history = data.get("request_history", "project")
    if request_history not in REQUEST_HISTORIES:
        problems.append(f"request_history must be one of {list(REQUEST_HISTORIES)}, got {request_history!r}")
    io = {}
    for section in ("input", "output"):
        table = data.get(section, {})
        if not isinstance(table, dict):
            problems.append(f"[{section}] must be a table with 'description' and/or 'files', got {table!r}")
            table = {}
        problems += [f"unknown key {k!r} in [{section}]" for k in table if k not in _IO_KEYS]
        files = table.get("files", [])
        problems += [
            f"[{section}] file {f!r} must be a path inside the project folder, like 'prd.md'"
            for f in files if not isinstance(f, str) or not _FILE_RE.fullmatch(f) or ".." in f.split("/")
        ]
        io[section] = (table.get("description", ""), files)
    knowledge = data.get("knowledge")
    knowledge_dir = (pack_dir / knowledge).resolve() if knowledge else None
    if knowledge_dir is not None and not knowledge_dir.is_dir():
        problems.append(f"knowledge folder {knowledge_dir} does not exist")
    skills = data.get("skills")
    skills_dir = (pack_dir / skills).resolve() if skills else None
    if skills_dir is not None and not skills_dir.is_dir():
        problems.append(f"skills folder {skills_dir} does not exist")
    subagents = []
    sub_table = data.get("subagents", {})
    if not isinstance(sub_table, dict):
        problems.append("[subagents] must be tables like [subagents.<name>] with 'description' and 'prompt'")
        sub_table = {}
    for sub_name, spec in sub_table.items():
        if not _SUBAGENT_NAME_RE.fullmatch(sub_name) or sub_name == GENERAL_PURPOSE_SUBAGENT["name"] or not isinstance(spec, dict):
            problems.append(f"invalid subagent {sub_name!r}: use a table named like [subagents.feature-writer]")
            continue
        problems += [f"unknown key {k!r} in [subagents.{sub_name}]" for k in spec if k not in _SUBAGENT_KEYS]
        prompt_path = (pack_dir / spec.get("prompt", "")).resolve()
        if not spec.get("description") or not spec.get("prompt") or not prompt_path.is_file():
            problems.append(f"[subagents.{sub_name}] needs a 'description' and a 'prompt' file inside the pack")
            continue
        sub_model = spec.get("model")
        if sub_model is not None and sub_model not in MODEL_TIERS:
            problems.append(f"[subagents.{sub_name}] model must be 'strong' or 'fast', got {sub_model!r}")
        subagents.append((sub_name, {"description": spec["description"],
                                     "prompt": prompt_path.read_text(encoding="utf-8"), "model": sub_model}))
    if problems:
        raise ValueError(f"invalid agent pack {name!r} ({toml_path}): " + "; ".join(problems))

    return AgentPack(
        name=name,
        dir=pack_dir,
        description=data.get("description", ""),
        models=models,
        tools=tools,
        filesystem=filesystem,
        knowledge=knowledge_dir,
        input_description=io["input"][0],
        input_files=io["input"][1],
        output_description=io["output"][0],
        output_files=io["output"][1],
        returns=returns,
        verifier=data.get("verifier"),
        max_fix_loops=int(data.get("max_fix_loops", 0)),
        request_history=request_history,
        skills=skills_dir,
        subagents=tuple(subagents),
    )


def build_agent(pack: AgentPack, level: int = 0) -> CompiledStateGraph:
    """`level` indexes pack.models: which step of its escalation order to run on."""
    with perf.span("agent_build", pack.name, model_tier=pack.models[level]) as sp:
        graph = _build_agent(pack, level, sp)
    return graph


def _observed_build_config(pack: AgentPack, spec: str, model, fast_spec: str, named: list) -> dict:
    """What this build actually configured, for diagnostics: models per helper, who compacts whose transcript,
    and provider settings that limit parallel tool calls. Read from the objects, not assumed."""
    from agent_engine.perf_callbacks import install_transport_hooks

    helpers = [{"name": GENERAL_PURPOSE_SUBAGENT["name"], "model": f"{spec} (inherits the main model)",
                "summarizer": "deepagents default: the helper's own model"}]
    for entry, (sub_name, sub) in zip(named, pack.subagents):
        helpers.append({"name": sub_name,
                        "model": model_spec(sub["model"]) if sub["model"] else f"{spec} (inherits the main model)",
                        "summarizer": fast_spec if pack.name == "task-breakdown" else "deepagents default: the helper's own model"})
    forced_serial = getattr(model, "_llm_type", "") == "openai-codex-chat"
    return {"model": spec, "summarizer_main": fast_spec, "helpers": helpers,
            "parallel_tool_calls": "forced off by the Codex subscription adapter" if forced_serial else "provider default",
            "retry_visibility": install_transport_hooks(model),
            "max_retries": getattr(model, "max_retries", None)}


def _build_agent(pack: AgentPack, level: int, sp) -> CompiledStateGraph:
    spec = model_spec(pack.models[level])
    with perf.span("model_setup", "resolve_model", tier=pack.models[level]):
        model = resolve_model_with_retries(spec)
    if pack.returns == "verdict" and hasattr(model, "max_tokens"):
        # A verdict is a short typed decision, not an artifact-generation response.
        model.max_tokens = min(getattr(model, "max_tokens", None) or 4096, 4096)
    fast_spec = model_spec("fast")
    with perf.span("model_setup", "resolve_model", tier="fast"):
        fast_model = resolve_model_with_retries(fast_spec)
    backend = build_backend(pack.knowledge, pack.skills)
    skill_sources = [SKILLS_VIRTUAL_ROOT] if pack.skills is not None else None
    tools = [tool for name in pack.tools for tool in TOOLS[name]()]
    logger.info("building agent %r: model=%s (%s) tools=%d", pack.name, spec, pack.models[level], len(tools))

    # Factories, not lists: the main agent and its helper each get their own instances.
    def file_tools() -> list:
        return [FilesystemMiddleware(backend=backend, tools=pack.filesystem)] if pack.filesystem is not None else []

    def safety() -> list:
        # Always on: a pack can't opt out of the /outputs/-only write guard or the global write lock.
        return [OutputsOnlyGuardMiddleware(), FileLockMiddleware()]

    with perf.span("model_setup", "summarization_middleware"):   # includes the model-profile lookups
        summarizer = summarization_middleware(spec, fast_model, backend)
    middleware = [*file_tools(), summarizer, *safety(), HelperLimitMiddleware()]
    if pack.name in ("task-breakdown", "task-breakdown/validator"):
        from agent_engine.stage_controls import StageBudgetMiddleware
        middleware.append(StageBudgetMiddleware())
    # deepagents' general-purpose helper (the `task` tool) only inherits middleware
    # that replaces one of its default slots, so it would get write tools without
    # the guard or the lock. Declaring it here hands it the same file tools and safety.
    helper = {**GENERAL_PURPOSE_SUBAGENT, "middleware": [*file_tools(), *safety()]}
    if skill_sources:
        helper["skills"] = skill_sources
    # The pack's own named subagents: same tools, file tools, skills and safety as the helper.
    named = []
    for sub_name, sub in pack.subagents:
        entry = {"name": sub_name, "description": sub["description"], "system_prompt": sub["prompt"],
                 "middleware": [*file_tools(), *safety()]}
        if sub["model"]:
            with perf.span("model_setup", "resolve_model", tier=sub["model"], subagent=sub_name):
                entry["model"] = resolve_model_with_retries(model_spec(sub["model"]))
        if skill_sources:
            entry["skills"] = skill_sources
        named.append(entry)

    if perf.enabled():
        sp.set(tools=len(tools), subagents=len(named) + 1, **_observed_build_config(pack, spec, model, fast_spec, named))
        from agent_engine.perf_callbacks import install_transport_hooks
        for role, item in [("summarizer", fast_model), *((entry["name"], entry["model"]) for entry in named if "model" in entry)]:
            perf.event("retry_hook", role, visibility=install_transport_hooks(item))
    schema = _RETURN_SCHEMAS.get(pack.returns)
    with perf.span("model_setup", "create_deep_agent"):
        graph = create_deep_agent(
            model=model,
            backend=backend,
            tools=tools,
            system_prompt=pack.system_prompt,
            middleware=middleware,
            subagents=[helper, *named],
            skills=skill_sources,
            response_format=structured_response_format(spec, schema) if schema else None,
        )
        graph.__dict__["_agent_engine_models"] = [model, fast_model, *(e["model"] for e in named if "model" in e)]
        return graph


def _uses_shared_transport(client) -> bool:
    """True when an SDK client sends through a process-wide cached httpx client.

    langchain_anthropic and langchain_openai hand every model instance the same lru_cache'd httpx client.
    Closing it after one pass closes it for every later pass too (the verifier then fails with
    "Cannot send a request, as the client has been closed", reported as "Connection error")."""
    transport = getattr(client, "_client", None)
    return transport is not None and type(transport).__module__.startswith(("langchain_anthropic", "langchain_openai"))


async def close_agent(graph) -> None:
    """Release the SDK clients a build owns after the pass, including failures.

    Clients backed by a shared, cached transport are left open: the next build reuses that transport."""
    seen = set()
    with perf.span("diagnostics", "model_clients_close"):
        for model in getattr(graph, "_agent_engine_models", []):
            for name in ("_client", "_async_client", "root_client", "root_async_client"):
                client = getattr(model, name, None)
                close = getattr(client, "close", None)
                if client is None or id(client) in seen or not callable(close) or _uses_shared_transport(client):
                    continue
                seen.add(id(client))
                try:
                    result = close()
                    if inspect.isawaitable(result):
                        await asyncio.wait_for(result, timeout=5)
                except Exception as exc:
                    logger.warning("model client cleanup failed: %s", perf.error_summary(exc))
