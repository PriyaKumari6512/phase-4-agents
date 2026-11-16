"""The one backend every agent runs on. Deliberately has NO shell: the default
route is deepagents' in-memory StateBackend, which can't execute commands, so
no agent (or the general-purpose helper subagent deepagents adds to it) gets
an `execute` tool, and nothing can read this process's environment (API keys)
through one. Real disk is reachable only through two routes:

- /outputs/   -> OUTPUTS_DIR, where every agent's output lands.
- /knowledge/ -> a pack's own `knowledge` folder, its reference docs.
- /skills/    -> a pack's own `skills` folder (Agent Skills, SKILL.md files).

Writes outside /outputs/ are refused by guardrails.OutputsOnlyGuardMiddleware.
"""

from __future__ import annotations

from pathlib import Path

from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend
from deepagents.backends.protocol import BackendProtocol

from agent_engine.config import KNOWLEDGE_VIRTUAL_ROOT, OUTPUTS_DIR, OUTPUTS_VIRTUAL_PREFIX, SKILLS_VIRTUAL_ROOT


def build_backend(knowledge_dir: Path | None = None, skills_dir: Path | None = None) -> BackendProtocol:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    routes = {OUTPUTS_VIRTUAL_PREFIX: FilesystemBackend(root_dir=OUTPUTS_DIR, virtual_mode=True)}
    if knowledge_dir is not None:
        routes[KNOWLEDGE_VIRTUAL_ROOT] = FilesystemBackend(root_dir=knowledge_dir, virtual_mode=True)
    if skills_dir is not None:
        routes[SKILLS_VIRTUAL_ROOT] = FilesystemBackend(root_dir=skills_dir, virtual_mode=True)
    return CompositeBackend(default=StateBackend(), routes=routes)
