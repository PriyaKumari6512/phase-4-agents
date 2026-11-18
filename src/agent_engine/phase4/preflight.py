"""Check every Phase 4 input before any model call, and report all problems at once.

Problems that would otherwise surface mid-run (a missing approval, a team member without skills, a roadmap release
without a date, an unreadable stories file) stop the run up front with the complete list. Things a human may
reasonably leave open (a story without acceptance criteria, missing story points) are warnings: the run continues and
they are reported at the gate.
"""
from __future__ import annotations

from pydantic import ValidationError

from agent_engine.phase4 import files
from agent_engine.phase4.contracts import ProjectSettings, StorySnapshot


def _gate_approved(project: str, name: str) -> bool:
    from agent_engine.gates import load_gates
    from agent_engine.phase4.orchestrator import gate_state
    gates = load_gates()
    return name in gates and gate_state(files.project_dir(project), gates[name])[0] == "approved"


def check_inputs(project: str) -> tuple[list[str], list[str]]:
    """(errors, warnings) for the whole pipeline's inputs. Reads files only; no model, no network."""
    errors: list[str] = []
    warnings: list[str] = []
    settings = None
    if not files.exists(project, files.PROJECT_SETTINGS):
        errors.append(f"{files.PROJECT_SETTINGS} is missing")
    else:
        try:
            settings = files.read_json(project, files.PROJECT_SETTINGS, ProjectSettings)
        except (ValidationError, ValueError, files.ProjectError) as exc:
            errors.append(f"{files.PROJECT_SETTINGS} is invalid: {' '.join(str(exc).split())[:600]}")
    for rel in (files.PRD, files.ARCHITECTURE):
        if not files.exists(project, rel):
            errors.append(f"{rel} is missing")
        elif not files.read_text(project, rel).strip():
            errors.append(f"{rel} is empty")
    for gate in ("G3A", "G3B"):
        if not _gate_approved(project, gate):
            errors.append(f"gate {gate} (approved {'designs' if gate == 'G3A' else 'architecture'}) has no human "
                          f"approval; record it with `agent-engine gate {gate} --project-name {project} "
                          "--decision approved ...`")
    snap = None
    if not files.exists(project, files.STORIES):
        errors.append(f"{files.STORIES} is missing: import the approved stories (Jira) or add the file")
    else:
        try:
            snap = files.read_json(project, files.STORIES, StorySnapshot)
        except (ValidationError, ValueError, files.ProjectError) as exc:
            errors.append(f"{files.STORIES} is invalid: {' '.join(str(exc).split())[:600]}")
        if snap is not None and not snap.stories:
            errors.append(f"{files.STORIES} has no approved stories")
    if settings is not None:
        if not settings.code_repos:
            errors.append("project.json code_repos is empty: tasks cannot name a repository")
        no_skills = [m.member_id for m in settings.team if not m.declared_skills]
        if no_skills:
            errors.append("team members without declared_skills (Work Allocation cannot match them to tasks): "
                          + ", ".join(no_skills))
        if all(m.allocation_pct == 0 for m in settings.team):
            errors.append("every team member has allocation_pct 0: there is no capacity to plan")
    if snap is not None:
        dated = {r.release for r in settings.release_deadlines} if settings is not None else set()
        used = {v for s in snap.stories for v in (getattr(s, "fix_versions", None) or [])}
        undated = [r.name for r in snap.releases if r.name in used and not r.release_date and r.name not in dated
                   and not r.released]
        if undated:
            errors.append("roadmap releases without a date (set it on the tracker version or in project.json "
                          "release_deadlines): " + ", ".join(undated))
        no_ac = [s.key for s in snap.stories if not s.acceptance_criteria]
        if no_ac:
            warnings.append("stories without acceptance criteria (the product owner should add them): "
                            + ", ".join(no_ac[:30]))
    return errors, warnings
