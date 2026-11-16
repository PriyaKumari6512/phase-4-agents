"""Validated feature decisions rendered into legacy spec-kit artifacts.

The model supplies decisions once. Formatting, numbering and repeated document
sections are deterministic; legacy Markdown-only features remain supported.
"""
from __future__ import annotations

import json
import re
import hashlib
import os
import tempfile
from typing import Literal

import networkx as nx
from pydantic import BaseModel, ConfigDict, Field, model_validator

from agent_engine.phase4 import files
from agent_engine.phase4.speckit import FEATURE_DIR_RE
from agent_engine.phase4.speckit_parse import REQ_ID_RE, parse_spec_md, parse_tasks_md
from agent_engine.runtime import project_lock


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Scenario(Record):
    given: str = Field(min_length=1)
    when: str = Field(min_length=1)
    then: str = Field(min_length=1)


class Story(Record):
    number: int = Field(ge=1, le=9999)
    title: str = Field(min_length=1)
    priority: Literal["P1", "P2", "P3"]
    as_a: str = Field(min_length=1)
    i_want: str = Field(min_length=1)
    so_that: str = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1)
    acceptance: list[Scenario] = Field(min_length=1)


class Requirement(Record):
    number: int = Field(ge=1, le=9999)
    text: str = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1)


class Task(Record):
    task_id: str = Field(pattern=r"^T\d{3,4}$")
    description: str = Field(min_length=1)
    file_paths: list[str] = Field(default_factory=list)
    parallel: bool = False
    depends_on: list[str] = Field(default_factory=list)


class Phase(Record):
    kind: Literal["setup", "foundational", "user_story", "polish"]
    story_number: int | None = Field(default=None, ge=1, le=9999)
    tasks: list[Task] = Field(default_factory=list)

    @model_validator(mode="after")
    def story_binding(self):
        if (self.kind == "user_story") != (self.story_number is not None):
            raise ValueError("only user_story phases require story_number")
        return self


class Decision(Record):
    topic: str = Field(min_length=1)
    status: Literal["source", "proposal", "unresolved"]
    decision: str = Field(min_length=1)
    rationale: str = ""
    source_refs: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def evidence(self):
        if self.status == "source" and not self.source_refs:
            raise ValueError("a source-backed decision requires source_refs")
        return self


class Entity(Record):
    name: str = Field(min_length=1)
    fields: dict[str, str] = Field(default_factory=dict)
    relationships: list[str] = Field(default_factory=list)


class Interface(Record):
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    description: str = Field(min_length=1)
    source_refs: list[str] = Field(default_factory=list)
    status: Literal["source", "proposal", "unresolved"]

    @model_validator(mode="after")
    def evidence(self):
        if self.status == "source" and not self.source_refs:
            raise ValueError("a source-backed interface requires source_refs")
        return self


class FeatureDocument(Record):
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    stories: list[Story] = Field(min_length=1)
    requirements: list[Requirement] = Field(min_length=1)
    phases: list[Phase] = Field(min_length=1)
    technical_context: dict[str, str] = Field(default_factory=dict)
    decisions: list[Decision] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    interfaces: list[Interface] = Field(default_factory=list)
    validation_steps: list[str] = Field(min_length=1)
    success_criteria: list[str] = Field(min_length=1)
    edge_cases: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    shared_prerequisites: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def consistency(self):
        stories = {s.number for s in self.stories}
        if len(stories) != len(self.stories):
            raise ValueError("story numbers must be unique")
        if len({r.number for r in self.requirements}) != len(self.requirements):
            raise ValueError("local requirement numbers must be unique")
        tasks = [t for p in self.phases for t in p.tasks]
        ids = {t.task_id for t in tasks}
        if not tasks or len(ids) != len(tasks):
            raise ValueError("tasks are required and task IDs must be unique across phases")
        assigned = {p.story_number for p in self.phases if p.kind == "user_story" and p.tasks}
        if assigned != stories:
            raise ValueError("every story requires tasks in its own user_story phase; unknown stories are forbidden")
        if len({i.name for i in self.interfaces}) != len(self.interfaces):
            raise ValueError("interface names must be unique")
        graph = nx.DiGraph()
        graph.add_nodes_from(ids)
        for task in tasks:
            for dep in task.depends_on:
                if dep not in ids:
                    raise ValueError(f"{task.task_id}: unknown dependency {dep}")
                graph.add_edge(dep, task.task_id)
        if not nx.is_directed_acyclic_graph(graph):
            raise ValueError("task dependencies contain a cycle")
        # Markdown controls are generated by the renderer, never by free text.
        strings = [self.title] + [s.title for s in self.stories] + [s.as_a for s in self.stories] + [s.i_want for s in self.stories] + [s.so_that for s in self.stories]
        strings += [t.description for t in tasks] + [r.text for r in self.requirements]
        strings += [v for s in self.stories for a in s.acceptance for v in (a.given, a.when, a.then)]
        if any("\n" in value or "\r" in value or "(source:" in value.lower() for value in strings):
            raise ValueError("story, task, requirement and scenario fields must be single-line strings")
        for task in tasks:
            if re.search(r"\((?:depends on|after|requires)\s", task.description, re.I):
                raise ValueError("put dependencies in depends_on, not task description")
            for path in task.file_paths:
                if ("\n" in path or "\r" in path or "`" in path or path.startswith(("/", "\\", "~"))
                        or ".." in path.replace("\\", "/").split("/")):
                    raise ValueError("file_paths must be safe repository-relative paths")
        return self


def _bullets(values: list[str]) -> list[str]:
    return [f"- {v}" for v in values] or ["- None recorded."]


def _restore_bytes(path, value: bytes) -> None:
    """Engine-only rollback of validated paths; a stopped work budget must not block restoration."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".engine-feature-restore-", dir=path.parent)
    try:
        os.chmod(temporary, path.stat().st_mode & 0o777 if path.exists() else 0o644)
        with os.fdopen(fd, "wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        from pathlib import Path
        Path(temporary).unlink(missing_ok=True)


def _decision_lines(document: FeatureDocument) -> list[str]:
    result = []
    for d in document.decisions:
        result += [f"### {d.topic} [{d.status}]", d.decision,
                   f"Rationale: {d.rationale or 'Not supplied.'}",
                   f"Sources: {', '.join(d.source_refs) or 'No source-backed decision.'}"]
        if d.alternatives:
            result += ["Alternatives considered:", *_bullets(d.alternatives)]
    return result or ["No additional technology decisions; follow architecture.md and the shared contract."]


def render(document: FeatureDocument) -> dict[str, str]:
    spec = [f"# Feature Specification: {document.title}", "", document.summary, "", "## User Scenarios & Testing"]
    for s in document.stories:
        spec += ["", f"### User Story {s.number} - {s.title} (Priority: {s.priority})", "",
                 f"As a {s.as_a}, I want {s.i_want}, so that {s.so_that} (source: {', '.join(s.source_ids)})", "",
                 "**Acceptance Scenarios**:", ""]
        spec += [f"{n}. **Given** {a.given}, **When** {a.when}, **Then** {a.then}" for n, a in enumerate(s.acceptance, 1)]
    spec += ["", "## Requirements", "", "### Functional Requirements", ""]
    spec += [f"- **FR-{r.number:03d}**: {r.text} (source: {', '.join(r.source_ids)})" for r in document.requirements]
    spec += ["", "## Success Criteria", *_bullets(document.success_criteria)]
    spec += ["", "## Edge Cases", *_bullets(document.edge_cases), "", "## Assumptions and Open Questions"]
    spec += _bullets(document.open_questions)
    spec += [f"- [{d.status}] {d.topic}: {d.decision}" for d in document.decisions if d.status != "source"]
    tasks = [f"# Tasks: {document.title}", "", "Shared prerequisites (reuse their owner; do not duplicate):", *_bullets(document.shared_prerequisites)]
    for n, phase in enumerate(document.phases, 1):
        title = {"setup": "Setup", "foundational": "Foundational", "polish": "Polish"}.get(phase.kind)
        if phase.kind == "user_story":
            story = next(s for s in document.stories if s.number == phase.story_number)
            title = f"User Story {story.number} - {story.title}"
        tasks += ["", f"## Phase {n}: {title}", ""]
        if not phase.tasks:
            tasks += ["No newly owned work in this phase; reuse the shared prerequisites."]
        for task in phase.tasks:
            labels = ("[P] " if task.parallel else "") + (f"[US{phase.story_number}] " if phase.kind == "user_story" else "")
            paths = " " + " ".join(f"`{path}`" for path in task.file_paths) if task.file_paths else ""
            deps = f" (depends on {', '.join(task.depends_on)})" if task.depends_on else ""
            tasks += [f"- [ ] {task.task_id} {labels}{task.description}{paths}{deps}"]
    tasks += ["", "## Validation", *_bullets(document.validation_steps)]
    plan = [f"# Implementation Plan: {document.title}", "", document.summary, "", "## Technical Context"]
    plan += [f"- {key}: {value}" for key, value in document.technical_context.items()]
    plan += ["", "## Constitution Check", "Follow the approved .specify/memory/constitution.md. Engine policy and unresolved deviations remain visible; this renderer does not certify semantic compliance.",
             "", "## Shared Prerequisites", *_bullets(document.shared_prerequisites), "", "## Decisions", *_decision_lines(document),
             "", "## Validation", *_bullets(document.validation_steps)]
    plan += ["", "## Project Structure", *_bullets(sorted({path for phase in document.phases for task in phase.tasks for path in task.file_paths}))]
    research = [f"# Research and Decisions: {document.title}", "", "These are source-backed decisions or explicit proposals, not a claim of external research.", "", *_decision_lines(document)]
    quickstart = [f"# Quickstart Validation: {document.title}", "", "Use the approved architecture and existing project tooling; commands below are proposals unless sourced.", "", *_bullets(document.validation_steps)]
    entities = [f"# Data Model: {document.title}"]
    for entity in document.entities:
        entities += ["", f"## {entity.name}", *[f"- {k}: {v}" for k, v in entity.fields.items()], *_bullets(entity.relationships)]
    output = {"spec.md": "\n".join(spec) + "\n", "tasks.md": "\n".join(tasks) + "\n",
              "plan.md": "\n".join(plan) + "\n", "research.md": "\n".join(research) + "\n",
              "quickstart.md": "\n".join(quickstart) + "\n"}
    if document.entities:
        output["data-model.md"] = "\n".join(entities) + "\n"
    for interface in document.interfaces:
        output[f"contracts/{interface.name}.md"] = (f"# {interface.name} [{interface.status}]\n\n{interface.description}\n\n"
                                                        f"Sources: {', '.join(interface.source_refs) or 'Unresolved/proposed; no source-backed contract.'}\n")
    output["clarifications.md"] = "# Open Questions and Proposals\n\n" + "\n".join(_bullets(document.open_questions) + [f"- [{d.status}] {d.topic}: {d.decision}" for d in document.decisions if d.status != "source"]) + "\n"
    output["checklists/requirements.md"] = "# Specification Quality Checklist\n\n- [x] Structured schema, IDs, references and task DAG validated by code.\n- [ ] Semantic requirement coverage, source fidelity, independent testability and cross-feature consistency reviewed.\n"
    return output


def write(project: str, feature_directory: str, document: dict, expected_sha256: str = "") -> str:
    """Validate a complete feature record before writing any generated files."""
    if not FEATURE_DIR_RE.fullmatch(feature_directory):
        raise files.ProjectError("invalid feature directory")
    from agent_engine.phase4.speckit import ASSETS, TEMPLATE_NAMES
    for name in TEMPLATE_NAMES:
        rel = f".specify/templates/{name}.md"
        if files.exists(project, rel) and files.read_text(project, rel) != (ASSETS / "templates" / f"{name}.md").read_text(encoding="utf-8"):
            raise files.ProjectError("custom project template detected; use the legacy feature workflow to preserve its requirements")
    try:
        record = FeatureDocument.model_validate(document)
    except ValueError as exc:
        raise files.ProjectError(f"invalid feature document: {exc}") from exc
    source_ids = set(REQ_ID_RE.findall(files.read_text(project, files.PRD)))
    for story in record.stories:
        if set(story.source_ids) - source_ids:
            raise files.ProjectError(f"story {story.number} cites unknown PRD IDs")
    for requirement in record.requirements:
        if set(requirement.source_ids) - source_ids:
            raise files.ProjectError(f"requirement {requirement.number} cites unknown PRD IDs")
    output = render(record)
    spec = parse_spec_md(output["spec.md"])
    tasks = parse_tasks_md(output["tasks.md"])
    if (len(spec.stories) != len(record.stories) or len(tasks) != sum(len(p.tasks) for p in record.phases)
            or any(not s.scenarios or not s.source_ids for s in spec.stories)):
        raise files.ProjectError("rendered feature did not preserve all structured stories/tasks")
    effective_graph = nx.DiGraph()
    effective_graph.add_nodes_from(t.task_id for t in tasks)
    previous = {}
    for task in tasks:
        deps = task.depends_on or ([previous[task.phase_num]] if not task.parallel and task.phase_num in previous else [])
        effective_graph.add_edges_from((dep, task.task_id) for dep in deps)
        if not task.parallel:
            previous[task.phase_num] = task.task_id
    if not nx.is_directed_acyclic_graph(effective_graph):
        raise files.ProjectError("task dependencies including implicit sequential order contain a cycle")
    output["feature.json"] = record.model_dump_json(indent=2) + "\n"
    with project_lock(files.project_dir(project), "feature-" + feature_directory.split("/")[1]):
        canonical = f"{feature_directory}/feature.json"
        actual = files.file_sha(project, canonical) if files.exists(project, canonical) else ""
        if expected_sha256 and actual != expected_sha256:
            raise files.ProjectError("feature changed since it was read; reload before updating")
        manifest_path = f"{feature_directory}/feature-render-manifest.json"
        owned = files.read_json(project, manifest_path) if files.exists(project, manifest_path) else {}
        old_hashes = owned.get("files", {}) if owned.get("version") == 1 else {}
        if not isinstance(old_hashes, dict):
            raise files.ProjectError("invalid feature render manifest; review generated file ownership")
        allowed = lambda rel: rel in {"spec.md", "tasks.md", "plan.md", "research.md", "quickstart.md", "data-model.md", "feature.json", "clarifications.md", "checklists/requirements.md"} or bool(re.fullmatch(r"contracts/[a-z0-9][a-z0-9-]*\.md", rel))
        if any(not allowed(rel) for rel in old_hashes):
            raise files.ProjectError("invalid owned artifact path in feature render manifest")
        stale = [rel for rel in old_hashes if rel not in output]
        for rel in old_hashes:
            if rel not in stale and files.exists(project, f"{feature_directory}/{rel}") and files.file_sha(project, f"{feature_directory}/{rel}") != old_hashes[rel]:
                raise files.ProjectError(f"generated artifact {rel} was edited outside its canonical record; reconcile it before regeneration")
        for rel in stale:
            if files.exists(project, f"{feature_directory}/{rel}") and files.file_sha(project, f"{feature_directory}/{rel}") != old_hashes[rel]:
                raise files.ProjectError(f"obsolete generated artifact {rel} was edited; preserve/reconcile it before regeneration")
        output["feature-render-manifest.json"] = json.dumps({"version": 1, "files": {rel: hashlib.sha256(text.encode()).hexdigest() for rel, text in output.items()}}, indent=2) + "\n"
        # Validate all mutation targets while work is authorized, and retain exact
        # bytes (including BOM/CRLF) so interruption cannot damage legacy artifacts.
        targets = {rel: files.path(project, f"{feature_directory}/{rel}", write=True) for rel in [*output, *stale]}
        before = {rel: target.read_bytes() if target.is_file() else None for rel, target in targets.items()}
        written = []
        try:
            for rel, text in output.items():
                written.append(rel)
                files.write_text(project, f"{feature_directory}/{rel}", text)
            for rel in stale:
                written.append(rel)
                files.path(project, f"{feature_directory}/{rel}", write=True).unlink(missing_ok=True)
        except BaseException:
            for rel in reversed(written):
                # Revalidate containment and active project scope, but bypass the
                # budget's mutation check ONLY for undoing this transaction.
                target = files.path(project, f"{feature_directory}/{rel}")
                if before[rel] is None:
                    target.unlink(missing_ok=True)
                else:
                    _restore_bytes(target, before[rel])
            raise
    return json.dumps({"feature_directory": feature_directory, "feature_sha256": files.file_sha(project, canonical),
                       "stories": len(spec.stories), "tasks": len(tasks), "written": [f"{feature_directory}/{rel}" for rel in output],
                       "removed_obsolete_generated": [f"{feature_directory}/{rel}" for rel in stale],
                       "open_questions": len(record.open_questions), "unresolved_decisions": sum(d.status != "source" for d in record.decisions),
                       "semantic_review_required": True}, separators=(",", ":"))
