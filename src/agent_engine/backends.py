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
from deepagents.backends.protocol import BackendProtocol, WriteResult, EditResult, FileUploadResponse

from agent_engine.config import KNOWLEDGE_VIRTUAL_ROOT, OUTPUTS_DIR, OUTPUTS_VIRTUAL_PREFIX, SKILLS_VIRTUAL_ROOT
from agent_engine.runtime import active_project, active_inputs, managed_outputs
from agent_engine.config import READ_ONLY_PROJECT_DIRS


class ProjectBackend(FilesystemBackend):
    """Enforce reserved paths at the disk boundary as well as in middleware."""

    def __init__(self, root_dir, bound=False):
        super().__init__(root_dir=root_dir, virtual_mode=True)
        self.bound = bound
        self.inputs = active_inputs.get() | managed_outputs.get()

    def _denied(self, path):
        resolved = self._resolve_path(path)
        parts = resolved.relative_to(self.cwd).parts
        rel = parts if self.bound else parts[1:]
        from agent_engine.stage_controls import helper_write_allowed
        project = active_project.get() if self.bound else (parts[0] if parts else "")
        if not helper_write_allowed(project or "", "/".join(rel)):
            return True
        return bool(rel and (rel[0] in READ_ONLY_PROJECT_DIRS or rel[0] == "report.json"
                             or rel[0].startswith(".engine-") or "/".join(rel) in self.inputs))

    def write(self, file_path, content):
        if self._denied(file_path):
            return WriteResult(error="Read-only engine/input path")
        return super().write(file_path, content)

    def edit(self, file_path, old_string, new_string, replace_all=False):
        if self._denied(file_path):
            return EditResult(error="Read-only engine/input path")
        return super().edit(file_path, old_string, new_string, replace_all)

    def upload_files(self, files):
        return [FileUploadResponse(path=p, error="permission_denied") if self._denied(p)
                else super(ProjectBackend, self).upload_files([(p, data)])[0] for p, data in files]


def build_backend(knowledge_dir: Path | None = None, skills_dir: Path | None = None) -> BackendProtocol:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    project = active_project.get()
    routes = ({f"{OUTPUTS_VIRTUAL_PREFIX}{project}/": ProjectBackend(OUTPUTS_DIR / project, bound=True)}
              if project else {OUTPUTS_VIRTUAL_PREFIX: ProjectBackend(OUTPUTS_DIR)})
    if knowledge_dir is not None:
        routes[KNOWLEDGE_VIRTUAL_ROOT] = FilesystemBackend(root_dir=knowledge_dir, virtual_mode=True)
    if skills_dir is not None:
        routes[SKILLS_VIRTUAL_ROOT] = FilesystemBackend(root_dir=skills_dir, virtual_mode=True)
    return CompositeBackend(default=StateBackend(), routes=routes)
