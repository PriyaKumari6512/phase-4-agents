"""Publishing an approved file to the outside world: `agent-engine phase4 publish <what> --project-name P`.

  backlog      (P4-G1)  epics/stories/tasks + "blocks" links -> tracker (local files, Jira, Linear, GitHub Issues)
  sprint       (P4-G2)  sprints/cycles/iterations, stories moved in, deferred ones back to the backlog
  assignments  (P4-G3)  assignees + explanation comments; AI tasks dispatched to Copilot / Claude Code Action
  infra        (P4-G4)  one infra PR (infra/repo) + one CI PR per code repository (infra/ci/<repo>)

Every command refuses unless the gate is approved and the approved files are unchanged since. Writes are
recorded durably: publish/external-ids.json maps every local id to its tracker id (adopting items found by marker
label after a crash), and the last payload sent is kept so fields a human edited in the tracker are never
overwritten (three-way merge). Nothing is ever deleted: items that left the backlog are closed as won't-do.
Each run writes a report to publish/<what>.json.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar, copy_context
from copy import deepcopy
from datetime import date, datetime, timezone, timedelta
from functools import wraps
from typing import Any

from agent_engine import perf
from agent_engine.gates import load_gates, stale_approvals
from agent_engine.phase4 import files
from agent_engine.phase4.contracts import (
    AssignmentPlan,
    Backlog,
    InfraManifest,
    ProjectSettings,
    SprintPlan,
    TrackerKind,
    WorkItem,
)
from agent_engine.phase4.trackers.base import ExtObj, TrackerAdapter, TrackerError
from agent_engine.phase4.settings import get_settings, get_jira_options
from agent_engine.runtime import project_lock

log = logging.getLogger(__name__)
EXTERNAL_IDS = "publish/external-ids.json"
OWNED_FIELDS = ("title", "body_md", "story_points", "hours", "labels", "parent_id")
ORDER = {"epic": 0, "story": 1, "task": 2}
GATE_FOR = {"backlog": "P4-G1", "sprint": "P4-G2", "assignments": "P4-G3", "infra": "P4-G4"}
_resources: ContextVar[ExitStack | None] = ContextVar("publisher_resources", default=None)


class PublishError(RuntimeError):
    pass


# ============================================================================ gate
def require_gate(project: str, what: str) -> dict:
    for parent in {"sprint": ("backlog",), "assignments": ("backlog", "sprint")}.get(what, ()):
        require_gate(project, parent)
    gate = GATE_FOR[what]
    gates = load_gates()
    if gate not in gates:
        raise PublishError(f"gate {gate} is not defined in gates.toml")
    approval = gates[gate].approval_file
    if not files.exists(project, approval):
        raise PublishError(f"gate {gate} is not approved for {project}; record it with `agent-engine gate {gate} ...`")
    stale = stale_approvals(files.project_dir(project), [approval])
    if stale:
        raise PublishError("; ".join(stale) + f". Get {gate} approved again.")
    record = files.read_json(project, approval)
    from agent_engine.phase4.approval_policy import automated, test_publication_allowed
    if automated(record) and not test_publication_allowed(project, gate, record):
        raise PublishError("automated test approvals cannot authorize publication without PHASE4_AUTO_APPROVE_FOR_TESTING=true and a current verified review")
    if what == "backlog":
        backlog = files.read_json(project, files.BACKLOG, Backlog)
        if files.STORIES in backlog.sources:      # story-based: same manifest the validator checks
            from agent_engine.phase4.task_breakdown import source_manifest
            current = source_manifest(project)
            for rel in sorted(set(current) | set(backlog.sources)):
                if current.get(rel) != backlog.sources.get(rel):
                    raise PublishError(f"backlog source {rel} changed; rebuild and approve again")
        else:
            for rel, digest in backlog.sources.items():
                if not files.exists(project, rel) or files.file_sha(project, rel) != digest:
                    raise PublishError(f"backlog source {rel} changed; rebuild and approve again")
    if what in ("sprint", "assignments"):
        plan = files.read_json(project, files.SPRINT_PLAN, SprintPlan)
        if plan.solver.status not in ("OPTIMAL", "FEASIBLE") or plan.backlog_sha256 != files.file_sha(project, files.BACKLOG):
            raise PublishError("cannot publish a non-feasible or stale sprint plan")
    return record


def serialized(fn):
    @wraps(fn)
    def call(project, *args, **kwargs):
        if blocked := perf.publication_blocked():
            raise PublishError(blocked)
        with project_lock(files.project_dir(project)), ExitStack() as resources:
            token = _resources.set(resources)
            try:
                return fn(project, *args, **kwargs)
            finally:
                _resources.reset(token)
    return call


# ============================================================================ exactly-once mapping
class ExternalIds:
    """publish/external-ids.json: {system: {local_id: {id, key, payload_sha256, last_payload}}}."""

    def __init__(self, project: str) -> None:
        self.project = project
        self.data: dict = files.read_json(project, EXTERNAL_IDS) if files.exists(project, EXTERNAL_IDS) else {}
        settings = files.read_json(project, files.PROJECT_SETTINGS, ProjectSettings)
        self.destination = _sha(settings.tracker.model_dump())[:16]
        self.kind = settings.tracker.kind.value
        self._lock = threading.RLock()
        self._operations: dict[tuple[str, str], threading.RLock] = {}

    @contextmanager
    def operation(self, system: str, key: str):
        with self._lock:
            lock = self._operations.setdefault((self.namespace(system), key), threading.RLock())
        with lock:
            yield

    def namespace(self, system):
        # A dispatch belongs to the project/task, with its actual repo/provider
        # stored in the payload. Editing a tracker destination must not redispatch it.
        return system if system.startswith(("local", "dispatch")) else f"{system}:{self.destination}"

    def get(self, system: str, local_id: str) -> dict | None:
        with self._lock:
            return deepcopy(self.data.get(self.namespace(system), {}).get(local_id))

    def put(self, system: str, local_id: str, ext_id: str, key: str | None, payload: dict) -> None:
        with self._lock:
            self.data.setdefault(self.namespace(system), {})[local_id] = {"id": ext_id, "key": key, "payload_sha256": _sha(payload),
                                                           "last_payload": deepcopy(payload)}
            self.save()           # persist each acknowledged mapping before reporting success

    def remove(self, system: str, local_id: str) -> None:
        with self._lock:
            self.data.get(self.namespace(system), {}).pop(local_id, None)
            self.save()

    def save(self) -> None:
        with self._lock:
            files.write_json(self.project, EXTERNAL_IDS, self.data)


def _sha(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def marker(project: str, local_id: str) -> str:
    return "p4-" + hashlib.sha256(f"{project}:{local_id}".encode()).hexdigest()[:8]


def _norm(v: Any) -> Any:
    if isinstance(v, list):
        return sorted(v)
    if isinstance(v, str):
        return " ".join(v.split())
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def three_way(current: dict, last: dict, new: dict, comparable=None) -> tuple[dict, list[str]]:
    """Fields to write, and the fields a human changed in the tracker (kept, never overwritten)."""
    cmp = comparable or (lambda f, v: v)
    to_write, kept = {}, []
    for f in OWNED_FIELDS:
        if f not in new:
            continue
        cur, prev, nxt = _norm(current.get(f)), _norm(cmp(f, last.get(f))), _norm(cmp(f, new.get(f)))
        if f not in last or cur != prev:
            if cur != nxt:
                kept.append(f)
            continue
        if cur != nxt:
            to_write[f] = new[f]
    return to_write, kept


def ensure(adapter: TrackerAdapter, ids: ExternalIds, project: str, local_id: str, payload: dict) -> dict:
    with ids.operation(adapter.system, local_id):
        return _ensure(adapter, ids, project, local_id, payload)


def _ensure(adapter: TrackerAdapter, ids: ExternalIds, project: str, local_id: str, payload: dict) -> dict:
    system = adapter.system
    row = ids.get(system, local_id)
    if row is None:
        found = adapter.find_by_marker(marker(project, local_id), payload.get("level"))
        if found is not None:   # created earlier but the mapping was lost: adopt it
            ids.put(system, local_id, found.id, found.key, {})
            row = ids.get(system, local_id)
    if row is not None:
        kept: list[str] = []
        if row["payload_sha256"] != _sha(payload):
            current = adapter.get_fields(row["id"])
            to_write, kept = three_way(current, row.get("last_payload") or {}, payload, getattr(adapter, "comparable", None))
            if to_write:
                adapter.update(row["id"], to_write | {"level": payload.get("level")})
            # The baseline is the engine's desired payload, never a human override.
            ids.put(system, local_id, row["id"], row["key"], payload)
        return {"id": row["id"], "key": row["key"], "created": False, "kept_human_edits": kept}
    pending = f"{system}_pending"
    if ids.get(pending, local_id):
        raise PublishError(f"ambiguous previous create for {local_id}; reconcile the destination marker before retrying")
    ids.put(pending, local_id, "pending", None, {"marker": marker(project, local_id)})
    try:
        created = adapter.create(payload | {"_marker": marker(project, local_id)})
    except TrackerError as exc:
        if exc.rejected:
            ids.remove(pending, local_id)
        raise
    ids.put(system, local_id, created.id, created.key, payload)
    return {"id": created.id, "key": created.key, "created": True, "kept_human_edits": []}


def _once(ids, system, key, action):
    """Durable outbox: an ambiguous response is never silently replayed."""
    with ids.operation(system, key):
        return _once_locked(ids, system, key, action)


def _once_locked(ids, system, key, action):
    row = ids.get(system, key)
    if row:
        if row["id"] == "pending":
            raise PublishError(f"ambiguous {system} operation {key}; reconcile with the remote before retrying")
        return row
    ids.put(system, key, "pending", None, {})
    try:
        result = action()
    except TrackerError as exc:
        if exc.rejected:
            ids.remove(system, key)
        raise
    ext_id = result.id if isinstance(result, ExtObj) else str(result or "done")
    ids.put(system, key, ext_id, result.key if isinstance(result, ExtObj) else None, {})
    return ids.get(system, key)


def _comment(tracker, ids, issue, text):
    return _once(ids, tracker.system + "_comment", _sha([issue, text]), lambda: tracker.add_comment(issue, text))


# ============================================================================ local tracker (files)
class LocalTracker(TrackerAdapter):
    """A tracker kept as JSON files in outputs/<project>/tracker/ (items.json, links.json, sprints.json)."""

    kind = system = "local"

    def __init__(self, project: str) -> None:
        self.project = project

    def _load(self, name: str) -> list:
        rel = f"{files.TRACKER_DIR}/{name}.json"
        return files.read_json(self.project, rel) if files.exists(self.project, rel) else []

    def _save(self, name: str, rows: list) -> None:
        files.write_json(self.project, f"{files.TRACKER_DIR}/{name}.json", rows)

    def _items(self) -> list[dict]:
        return self._load("items")

    def _with_item(self, key: str, fn) -> None:
        items = self._items()
        for i in items:
            if i["key"] == key:
                fn(i)
                self._save("items", items)
                return
        raise TrackerError(f"local item {key} not found")

    def create(self, payload: dict) -> ExtObj:
        items = self._items()
        key = f"LOC-{len(items) + 1}"
        items.append({"key": key, "level": payload["level"], "title": payload["title"], "body_md": payload.get("body_md", ""),
                      "labels": list(payload.get("labels", [])) + ([payload["_marker"]] if payload.get("_marker") else []),
                      "parent_key": payload.get("parent_id"), "story_points": payload.get("story_points"),
                      "hours": payload.get("hours"), "status": "open", "assignee": None, "sprint_key": None,
                      "comments": []})
        self._save("items", items)
        return ExtObj(id=key, key=key)

    def update(self, external_id: str, fields: dict) -> None:
        def apply(i):
            updates = {k: v for k, v in fields.items() if k in OWNED_FIELDS and k != "parent_id"}
            if "labels" in updates:
                updates["labels"] = updates["labels"] + [x for x in i.get("labels", []) if re.fullmatch(r"p4-[0-9a-f]{8}", x)]
            i.update(updates)
            if "parent_id" in fields:
                i["parent_key"] = fields["parent_id"]
        self._with_item(external_id, apply)

    def get_fields(self, external_id: str) -> dict:
        i = next((x for x in self._items() if x["key"] == external_id), None)
        if i is None:
            raise TrackerError(f"local item {external_id} not found")
        result = {f: i.get(f) for f in OWNED_FIELDS}
        result["parent_id"] = i.get("parent_key")
        result["labels"] = [x for x in i.get("labels", []) if not re.fullmatch(r"p4-[0-9a-f]{8}", x)]
        return result

    def find_by_marker(self, marker_label: str, level: str | None = None) -> ExtObj | None:
        for i in self._items():
            if marker_label in i.get("labels", []) and (level is None or i["level"] == level):
                return ExtObj(id=i["key"], key=i["key"])
        return None

    def add_blocks(self, blocker_id: str, blocked_id: str) -> None:
        links = self._load("links")
        if [blocker_id, blocked_id] not in links:
            links.append([blocker_id, blocked_id])
            self._save("links", links)

    def blocks_of(self, issue_id: str) -> list[str]:
        return [b for a, b in self._load("links") if a == issue_id]

    def remove_blocks(self, blocker_id: str, blocked_id: str) -> None:
        self._save("links", [edge for edge in self._load("links") if edge != [blocker_id, blocked_id]])

    def reopen_item(self, issue_id: str) -> None:
        self._with_item(issue_id, lambda i: i.update(status="open"))

    def add_comment(self, issue_id: str, text: str) -> None:
        self._with_item(issue_id, lambda i: i["comments"].append(text))

    def item_done(self, issue_id: str) -> bool:
        return next((i["status"] == "done" for i in self._items() if i["key"] == issue_id), False)

    def close_item(self, issue_id: str, reason: str) -> None:
        self._with_item(issue_id, lambda i: i.update(status="wont_do", close_reason=reason))

    def create_sprint(self, name: str, start: date, end: date, goal: str) -> ExtObj:
        sprints = self._load("sprints")
        key = f"SPR-{len(sprints) + 1}"
        sprints.append({"key": key, "name": name, "start": str(start), "end": str(end), "goal": goal, "state": "future"})
        self._save("sprints", sprints)
        return ExtObj(id=key, key=key)

    def move_to_sprint(self, sprint_id: str, issue_ids: list[str]) -> None:
        items = self._items()
        moved = set(issue_ids)
        for i in items:
            if i["key"] in moved or (i["level"] == "task" and i.get("parent_key") in moved):
                i["sprint_key"] = sprint_id
        self._save("items", items)

    def move_to_backlog(self, issue_ids: list[str]) -> None:
        self.move_to_sprint(None, issue_ids)  # type: ignore[arg-type]

    def assign(self, issue_id: str, account_id: str | None) -> None:
        self._with_item(issue_id, lambda i: i.update(assignee=account_id))


def tracker_for(project: str, settings: ProjectSettings) -> TrackerAdapter:
    tracker = _tracker_for(project, settings)
    if resources := _resources.get():
        resources.callback(tracker.close)
    return tracker


def _tracker_for(project: str, settings: ProjectSettings) -> TrackerAdapter:
    kind = settings.tracker.kind
    if kind == TrackerKind.LOCAL:
        return LocalTracker(project)
    if kind == TrackerKind.JIRA:
        from agent_engine.phase4.trackers.jira import JiraTracker
        return JiraTracker(settings.tracker)
    if kind == TrackerKind.LINEAR:
        from agent_engine.phase4.trackers.linear import LinearTracker
        return LinearTracker(settings.tracker)
    if kind == TrackerKind.GITHUB:
        from agent_engine.phase4.trackers.github import GitHubTracker
        return GitHubTracker(settings.tracker)
    raise PublishError(f"unsupported tracker {kind}")


def _parallel_jira(tracker, rows, action):
    """Bounded, ordered results; local/other adapters retain serial behavior.

    Each submitted task carries the caller's project/diagnostic context. A
    failure cancels queued work and joins in-flight requests before closing HTTP.
    """
    rows = list(rows)
    workers = get_jira_options().concurrency if tracker.system == "jira" else 1
    if workers == 1 or len(rows) < 2:
        return [action(row) for row in rows]
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="jira-publish") as pool:
        futures = [pool.submit(copy_context().run, action, row) for row in rows]
        try:
            return [future.result() for future in futures]
        except BaseException:
            for future in futures:
                future.cancel()
            raise


# ============================================================================ backlog
def body_md(item: WorkItem) -> str:
    parts = []
    if item.user_story:
        u = item.user_story
        parts.append(f"**As a** {u.as_a}, **I want** {u.i_want}, **so that** {u.so_that}.")
    if item.description_md and (not item.user_story or item.level != "story"):
        parts.append(item.description_md)
    if item.acceptance_criteria:
        parts.append("## Acceptance criteria\n" + "\n".join(f"- {a.text}" for a in item.acceptance_criteria))
    if item.definition_of_done:
        parts.append("## Definition of Done\n" + "\n".join(f"- [ ] {d}" for d in item.definition_of_done))
    if item.file_paths:
        parts.append("## Files\n" + "\n".join(f"- `{p}`" for p in item.file_paths))
    if item.source_refs:
        parts.append("## Sources\n" + ", ".join(sorted({s.req_id for s in item.source_refs})))
    if item.estimate and item.estimate.rationale:
        parts.append(f"_Estimate ({item.estimate.method}, {item.estimate.confidence} confidence): {item.estimate.rationale}_")
    parts.append(f"_Generated by PDLC Phase 4 · {item.item_id}_")
    return "\n\n".join(parts)


def payload_for(item: WorkItem, parent_external: str | None, hours_in_body: bool = False) -> dict:
    """`hours_in_body`: Jira sub-task screens often have no time-tracking field, so the estimate goes in the text."""
    num = re.search(r"\d{3}", item.item_id) if not item.discipline else None
    labels = ["phase4"] + ([f"feature-{num.group(0)}"] if num else [])
    if item.discipline:
        labels.append(f"discipline-{item.discipline.lower()}")
    if item.level == "task" and item.ai_eligible:
        labels.append("ai-eligible")
    body = body_md(item)
    if hours_in_body and item.level == "task" and item.estimate and item.estimate.hours is not None:
        body = f"**Estimate:** {item.estimate.hours:g} h ({item.estimate.confidence} confidence)\n\n" + body
    p = {"level": item.level, "title": item.title[:240], "body_md": body, "labels": labels,
         "parent_id": parent_external}
    if item.level == "story" and item.estimate and item.estimate.story_points is not None:
        p["story_points"] = item.estimate.story_points
    if item.level == "task" and item.estimate and item.estimate.hours is not None and not hours_in_body:
        p["hours"] = item.estimate.hours
    return p


def _stories_source(project: str) -> str:
    from agent_engine.phase4.contracts import StorySnapshot
    return files.read_json(project, files.STORIES, StorySnapshot).source if files.exists(project, files.STORIES) else ""


REFERENCED = {"referenced": True}     # ledger payload of an upstream tracker item this engine must never edit or close


def _story_points_mode() -> str:
    import os
    mode = os.environ.get("PHASE4_WRITE_STORY_POINTS", "never").strip().lower() or "never"
    if mode not in ("never", "if_empty"):
        raise PublishError("PHASE4_WRITE_STORY_POINTS must be never or if_empty")
    return mode


def _reference_upstream(project: str, settings: ProjectSettings, backlog: Backlog, tracker, ids, ext: dict) -> dict:
    """Story-based backlog on Jira: epics and stories already exist (approved upstream). Record their ids so tasks
    become their sub-tasks and sprint publishing can move them; never create, edit or close them."""
    from agent_engine.phase4.contracts import StorySnapshot
    snap = files.read_json(project, files.STORIES, StorySnapshot)
    if snap.project_key != settings.tracker.jira_project_key:
        raise PublishError(f"the approved stories were imported from {snap.source} project {snap.project_key!r}, not the "
                           f"publish destination {settings.tracker.jira_project_key!r}; import the stories again")
    upstream = {s.key: (s.issue_id, s.key) for s in snap.stories} | {e.key: (e.issue_id, e.key) for e in snap.epics}
    referenced = 0
    for item in backlog.items:
        if item.level == "task" or item.item_id not in upstream:
            continue
        issue_id, key = upstream[item.item_id]
        ext[item.item_id] = issue_id
        row = ids.get(tracker.system, item.item_id)
        if row is None or row["id"] != issue_id or row.get("last_payload") != REFERENCED:
            ids.put(tracker.system, item.item_id, issue_id, key, REFERENCED)
        referenced += 1
    written = []
    if _story_points_mode() == "if_empty" and snap.story_points_field:
        stories = {s.key: s for s in snap.stories}
        for item in backlog.stories():
            source = stories.get(item.item_id)
            if source and source.story_points is None and item.estimate and item.estimate.story_points:
                if tracker.set_field_if_empty(source.issue_id, snap.story_points_field, item.estimate.story_points):
                    written.append(item.item_id)
    return {"referenced": referenced, "story_points_written": written}


@serialized
def publish_backlog(project: str) -> dict:
    require_gate(project, "backlog")
    settings = files.read_json(project, files.PROJECT_SETTINGS, ProjectSettings)
    backlog = files.read_json(project, files.BACKLOG, Backlog)
    tracker = tracker_for(project, settings)
    tracker.prepare()
    ids = ExternalIds(project)
    items = backlog.by_id()
    ext: dict[str, str] = {}
    report = {"tracker": tracker.system, "created": 0, "updated_or_unchanged": 0, "kept_human_edits": {},
              "links": 0, "closed": 0}
    # Approved stories imported from Jira: only their tasks are published, as sub-tasks of the existing stories.
    reference = tracker.system == "jira" and files.STORIES in backlog.sources and _stories_source(project) == "jira"
    if reference:
        report |= _reference_upstream(project, settings, backlog, tracker, ids, ext)

    def publish_item(item):
        closed_key = ids.get(f"{tracker.system}_closed", item.item_id)
        if closed_key is not None:
            tracker.reopen_item(closed_key["id"])
            ids.remove(f"{tracker.system}_closed", item.item_id)
        res = ensure(tracker, ids, project, item.item_id,
                     payload_for(item, ext.get(item.parent_id) if item.parent_id else None, hours_in_body=reference))
        return item.item_id, res

    for level in (["task"] if reference else ORDER):
        wave = sorted((i for i in backlog.items if i.level == level), key=lambda i: i.item_id)
        for item_id, res in _parallel_jira(tracker, wave, publish_item):
            ext[item_id] = res["id"]
            report["created" if res["created"] else "updated_or_unchanged"] += 1
            if res["kept_human_edits"]:
                report["kept_human_edits"][item_id] = res["kept_human_edits"]
    link_sys = f"{tracker.system}_link"
    def linkable(item, d):    # upstream story links belong to the product team, not to this engine
        return d.on_id in ext and items[d.on_id].level == item.level and (not reference or item.level == "task")
    wanted_links = {f"{d.on_id}->{item.item_id}" for item in backlog.items for d in item.dependencies if linkable(item, d)}
    for key, row in list(ids.data.get(ids.namespace(link_sys), {}).items()):
        if key not in wanted_links:
            source, target = row["id"].split("->", 1)
            tracker.remove_blocks(source, target)
            ids.data[ids.namespace(link_sys)].pop(key)
            ids.save()
    def publish_links(item):
        count = 0
        for d in item.dependencies:
            key = f"{d.on_id}->{item.item_id}"
            if linkable(item, d):
                with ids.operation(link_sys, key):
                    if ids.get(link_sys, key) is None:
                        source, target = ext[d.on_id], ext[item.item_id]
                        # Read-back adopts an accepted link after an interrupted response.
                        if target not in tracker.blocks_of(source):
                            tracker.add_blocks(source, target)
                        ids.put(link_sys, key, f"{source}->{target}", None, {})
                        count += 1
        return count
    report["links"] = sum(_parallel_jira(tracker, (i for i in backlog.items if i.level != "epic"), publish_links))
    closed_sys = f"{tracker.system}_closed"
    for local_id, row in list(ids.data.get(ids.namespace(tracker.system), {}).items()):
        if row.get("last_payload") == REFERENCED:
            continue                     # an upstream story or epic: never closed by this engine
        if local_id not in items and ids.get(closed_sys, local_id) is None:
            tracker.close_item(row["id"], "removed from the backlog by a requirement change (won't do)")
            ids.put(closed_sys, local_id, row["id"], row.get("key"), {})
            report["closed"] += 1
    files.write_json(project, f"{files.PUBLISH_DIR}/backlog.json", report | {"at": files.utcnow().isoformat()})
    return report


# ============================================================================ sprint
def match_sprints(planned: list, existing: list[dict]) -> dict[int, dict]:
    """Planned sprint index -> an existing tracker sprint to reuse instead of creating a duplicate.

    In order: same start date; an active sprint whose dates cover the planned start; same name; then undated future
    sprints (e.g. the one Jira creates with a new board), oldest first, for the remaining planned sprints in order."""
    free = list(existing)
    out = {}

    def take(sp, sprint):
        out[sp.sprint_index] = sprint
        free.remove(sprint)
    for sp in planned:
        match = (next((s for s in free if s["start"] == sp.start), None)
                 or next((s for s in free if s["state"] == "active" and s["start"] and s["end"]
                          and s["start"] <= sp.start <= s["end"]), None)
                 or next((s for s in free if s["name"] == sp.name), None))
        if match:
            take(sp, match)
    undated = sorted((s for s in free if s["state"] == "future" and not s["start"]), key=lambda s: int(s["id"])
                     if str(s["id"]).isdigit() else 0)
    for sp in [p for p in planned if p.sprint_index not in out]:
        if not undated:
            break
        take(sp, undated.pop(0))
    return out


@serialized
def publish_sprint(project: str) -> dict:
    require_gate(project, "sprint")
    settings = files.read_json(project, files.PROJECT_SETTINGS, ProjectSettings)
    plan = files.read_json(project, files.SPRINT_PLAN, SprintPlan)
    tracker = tracker_for(project, settings)
    ids = ExternalIds(project)
    report = {"tracker": tracker.system, "sprints": 0, "moved": 0, "to_backlog": 0, "missing_in_tracker": []}

    external = {}
    for story_id in dict.fromkeys([sid for sp in plan.sprints for sid in sp.story_ids] + [d.story_id for d in plan.deferred]):
        row = ids.get(tracker.system, story_id)
        if row is None:
            report["missing_in_tracker"].append(story_id)
        else:
            external[story_id] = row["id"]

    sprint_sys = f"{tracker.system}_sprint"
    nonempty = [sp for sp in plan.sprints if sp.story_ids]
    report["adopted"] = []
    unmapped = [sp for sp in nonempty if ids.get(sprint_sys, f"sprint:{sp.start.isoformat()}") is None]
    known = {row["id"] for row in ids.data.get(ids.namespace(sprint_sys), {}).values()}
    by_index = {sp.sprint_index: sp for sp in unmapped}
    for index, existing in match_sprints(unmapped, [s for s in tracker.board_sprints() if s["id"] not in known]).items():
        sp = by_index[index]
        fill = {k: v for k, v in (("start", sp.start if not existing["start"] else None),
                                  ("end", sp.end if not existing["end"] else None),
                                  ("goal", sp.goal if not existing["goal"] else None)) if v}
        if fill:
            tracker.update_sprint(existing["id"], fill)
        ids.put(sprint_sys, f"sprint:{sp.start.isoformat()}", existing["id"], existing["name"], {"adopted": True})
        report["adopted"].append({"sprint_index": sp.sprint_index, "tracker_sprint": existing["name"],
                                  "filled": sorted(fill)})

    def publish_slot(sp):
        row = ids.get(sprint_sys, f"sprint:{sp.start.isoformat()}")
        if row is None or row.get("id") == "pending":
            row = _once(ids, sprint_sys, f"sprint:{sp.start.isoformat()}", lambda: tracker.create_sprint(sp.name, sp.start, sp.end, sp.goal))
            sid = row["id"]
        else:
            sid = row["id"]
        moved = [external[s] for s in sp.story_ids if s in external]
        if moved:
            tracker.move_to_sprint(sid, moved)
        return len(moved)
    # Defend the concurrency boundary even for manually edited plan artifacts.
    selected = [sid for sp in nonempty for sid in sp.story_ids] + [d.story_id for d in plan.deferred]
    if len(selected) != len(set(selected)):
        raise PublishError("a story appears in multiple sprint/deferred destinations")
    counts = _parallel_jira(tracker, nonempty, publish_slot)
    report["sprints"], report["moved"] = len(counts), sum(counts)
    deferred = [external[d.story_id] for d in plan.deferred if d.story_id in external]
    if deferred:
        try:
            tracker.move_to_backlog(deferred)
            report["to_backlog"] = len(deferred)
        except Exception as exc:   # best effort: the plan itself is already published
            log.warning("moving deferred stories to the backlog failed: %s", exc)
    if report["missing_in_tracker"]:
        report["hint"] = "publish the backlog first: agent-engine phase4 publish backlog"
    files.write_json(project, f"{files.PUBLISH_DIR}/sprint.json", report | {"at": files.utcnow().isoformat()})
    return report


# ============================================================================ assignment publication (Phase 4)
@serialized
def publish_assignments(project: str) -> dict:
    require_gate(project, "assignments")
    from agent_engine.phase4.allocation import check
    problems = json.loads(check(project))["problems"]
    if problems:
        raise PublishError("assignment checks failed: " + "; ".join(problems))
    settings = files.read_json(project, files.PROJECT_SETTINGS, ProjectSettings)
    ap = files.read_json(project, files.ASSIGNMENTS, AssignmentPlan)
    tracker, ids = tracker_for(project, settings), ExternalIds(project)
    accounts = {m.member_id: m.tracker_account_id for m in settings.team}
    report = {"tracker": tracker.system, "assigned": 0, "ai_owners_recorded": 0, "missing_in_tracker": []}
    def publish_one(a):
        row = ids.get(tracker.system, a.task_id)
        if row is None:
            return a.task_id, 0, 0
        system = tracker.system + "_assign"
        with ids.operation(system, a.task_id):
            payload = {"account_id": accounts.get(a.worker_id), "worker_kind": a.worker_kind, "explanation": a.explanation}
            prev = ids.get(system, a.task_id)
            if prev and prev["id"] == a.worker_id and prev.get("last_payload") == payload:
                return None, 0, 0
            if a.worker_kind == "human":
                if tracker.system == "jira" and not payload["account_id"]:
                    raise PublishError(f"No Jira account ID for {a.worker_id}; set JIRA_ACCOUNT_MAP")
                tracker.assign(row["id"], payload["account_id"])
            _comment(tracker, ids, row["id"], f"Owner recommended by PDLC Phase 4 (P4-G3): {a.worker_id} ({a.worker_kind}). {a.explanation}")
            ids.put(system, a.task_id, a.worker_id, None, payload)
            return None, int(a.worker_kind == "human"), int(a.worker_kind == "ai_agent")
    for missing, human, ai in _parallel_jira(tracker, ap.assignments, publish_one):
        if missing:
            report["missing_in_tracker"].append(missing)
        report["assigned"] += human
        report["ai_owners_recorded"] += ai
    files.write_json(project, f"{files.PUBLISH_DIR}/assignments.json", report | {"at": files.utcnow().isoformat()})
    return report


# ============================================================================ assignments + AI dispatch
@serialized
def dispatch_assignments(project: str) -> dict:
    for part in ("backlog", "sprint", "assignments", "infra"):
        require_gate(project, part)
    from agent_engine.phase4 import dispatch

    require_gate(project, "assignments")
    settings = files.read_json(project, files.PROJECT_SETTINGS, ProjectSettings)
    ap = files.read_json(project, files.ASSIGNMENTS, AssignmentPlan)
    backlog = files.read_json(project, files.BACKLOG, Backlog)
    by = backlog.by_id()
    tracker = tracker_for(project, settings)
    ids = ExternalIds(project)
    accounts = {m.member_id: m.tracker_account_id for m in settings.team}
    agents = {a.agent_id: a for a in settings.ai_agents}
    report = {"tracker": tracker.system, "assigned": 0, "dispatched": [], "missing_in_tracker": []}
    from agent_engine.phase4.allocation import ci_ready_repos, _task_graph, check
    if any(a.worker_kind == "ai_agent" for a in ap.assignments) and get_settings().phase4_pr_mode == "github":
        from agent_engine.phase4.readiness import check_ci, reconcile
        check_ci(project)  # Re-read the actual repository head immediately before dispatch.
        reconcile(project)
        ids = ExternalIds(project)  # reconciliation updates durable dispatch state
    problems = json.loads(check(project))["problems"]
    if problems:
        raise PublishError("assignment checks failed: " + "; ".join(problems))
    plan = files.read_json(project, files.SPRINT_PLAN, SprintPlan)
    slot = next(s for s in plan.sprints if s.sprint_index == ap.sprint_index)
    graph = _task_graph([by[a.task_id] for a in ap.assignments] + [by[u.task_id] for u in ap.unassigned], by)
    ready = ci_ready_repos(project)
    active = {}
    for task_id, row in ids.data.get(ids.namespace("dispatch"), {}).items():
        payload = row.get("last_payload") or {}
        if payload.get("status", "queued") not in ("failed", "cancelled", "timed_out") and not payload.get("merged"):
            worker = payload.get("worker_id")
            active[worker] = active.get(worker, 0) + 1
    report["deferred_dispatches"] = []
    def assign_human(a):
        row = ids.get(tracker.system, a.task_id)
        if row is None:
            return a.task_id, 0
        with ids.operation(f"{tracker.system}_assign", a.task_id):
            account = accounts.get(a.worker_id)
            if tracker.system == "jira" and not account:
                raise PublishError(f"No Jira account ID for {a.worker_id}; set JIRA_ACCOUNT_MAP")
            prev = ids.get(f"{tracker.system}_assign", a.task_id)
            if prev is not None and prev["id"] == a.worker_id and prev.get("last_payload", {}).get("account_id") == account:
                return None, 0
            tracker.assign(row["id"], account)
            if a.explanation:
                _comment(tracker, ids, row["id"], f"Assigned by PDLC Phase 4 (approved at P4-G3): {a.explanation}")
            ids.put(f"{tracker.system}_assign", a.task_id, a.worker_id, None, {"account_id": account})
            return None, 1
    for missing, count in _parallel_jira(tracker, (a for a in ap.assignments if a.worker_kind == "human"), assign_human):
        if missing:
            report["missing_in_tracker"].append(missing)
        report["assigned"] += count
    # AI dispatch remains ordered: predecessor completion and worker limits are shared constraints.
    for a in ap.assignments:
        if a.worker_kind == "human":
            continue
        row = ids.get(tracker.system, a.task_id)
        if row is None:
            report["missing_in_tracker"].append(a.task_id)
            continue
        if ids.get("dispatch", a.task_id) is not None:
            continue                                      # each AI task is dispatched once
        agent = agents.get(a.worker_id)
        task = by[a.task_id]
        repo = task.repo or (settings.code_repos[0] if len(settings.code_repos) == 1 else None)
        if agent is None or repo is None:
            report["dispatched"].append({"task_id": a.task_id, "error": "unknown AI agent or repository"})
            continue
        reasons = []
        if repo not in ready:
            reasons.append("no current operational CI evidence; run phase4 check-ci after workflows are merged")
        not_before = datetime.combine(slot.start, datetime.min.time(), tzinfo=timezone.utc) + timedelta(minutes=a.planned_start_minute)
        if datetime.now(timezone.utc) < not_before:
            reasons.append(f"planned start is {not_before.isoformat()}")
        if active.get(a.worker_id, 0) >= agent.max_concurrent_tasks:
            reasons.append("worker concurrency limit reached; run phase4 reconcile")
        for predecessor in graph.predecessors(a.task_id):
            pred_row = ids.get(tracker.system, predecessor)
            if not pred_row or not tracker.item_done(pred_row["id"]):
                reasons.append(f"predecessor {predecessor} is not complete")
        if reasons:
            report["deferred_dispatches"].append({"task_id": a.task_id, "reasons": reasons})
            continue
        brief = dispatch.brief_for(task, by.get(task.parent_id), row.get("key"))
        adapter = dispatch.adapter_for(agent.provider, files.path(project, f"{files.PUBLISH_DIR}/dispatch", write=True))
        if ids.get("dispatch_pending", a.task_id):
            raise PublishError(f"ambiguous previous dispatch for {a.task_id}; reconcile provider state before retrying")
        ids.put("dispatch_pending", a.task_id, "pending", None, {"repo": repo, "provider": agent.provider})
        with perf.span("dispatch", agent.provider, adapter=type(adapter).__name__, operation="dispatch"):
            handle = adapter.start(repo=repo, base_ref="main", task_id=a.task_id, brief=brief)
        ids.put("dispatch", a.task_id, handle, None, {"provider": agent.provider, "repo": repo, "worker_id": a.worker_id, "status": "queued"})
        active[a.worker_id] = active.get(a.worker_id, 0) + 1
        _comment(tracker, ids, row["id"], f"Dispatched to {agent.agent_id} ({agent.provider}): {handle}. {a.explanation}")
        report["dispatched"].append({"task_id": a.task_id, "agent": agent.agent_id, "handle": handle})
    if report["missing_in_tracker"]:
        report["hint"] = "publish the backlog first: agent-engine phase4 publish backlog"
    files.write_json(project, f"{files.PUBLISH_DIR}/assignments.json", report | {"at": files.utcnow().isoformat()})
    return report


# ============================================================================ infra + CI pull requests
@serialized
def publish_infra(project: str) -> dict:
    from agent_engine.phase4.github_api import open_pr

    approval = require_gate(project, "infra")
    settings = files.read_json(project, files.PROJECT_SETTINGS, ProjectSettings)
    manifest = files.read_json(project, files.INFRA_MANIFEST, InfraManifest)
    from agent_engine.phase4.infra import check
    checked = json.loads(check(project))
    if not checked["ok"] or manifest.validation_complete is not True:
        raise PublishError("infrastructure is not fully validated: " + "; ".join(checked.get("problems", [])))
    snapshot = {}
    for f in manifest.files:
        data = files.path(project, f"infra/{f.path}").read_bytes()
        if hashlib.sha256(data).hexdigest() != f.sha256:
            raise PublishError(f"{f.path} changed after validation; publish refused")
        snapshot[f.path] = data.decode("utf-8")
    if not settings.infra_repo:
        raise PublishError("set infra_repo in phase4/project.json")
    short = manifest.intent_sha256[:8]
    local_root = files.path(project, f"{files.PUBLISH_DIR}/prs", write=True)
    pr_body = files.read_text(project, files.INFRA_PR) + (
        f"\n\nApproved at P4-G4 by {approval.get('approver', {}).get('name', '?')} on {approval.get('decided_at', '?')}.\n")
    repo_files = {f.path.removeprefix("repo/"): snapshot[f.path]
                  for f in manifest.files if f.path.startswith("repo/")}
    prs = [open_pr(settings.infra_repo, f"phase4/infra-{short}", repo_files,
                   f"Phase 4 infrastructure ({', '.join(manifest.environments)})", pr_body, local_root).__dict__]
    for repo in manifest.ci_repos:
        prefix = f"ci/{repo.replace('/', '__')}/"
        ci_files = {f.path.removeprefix(prefix): snapshot[f.path]
                    for f in manifest.files if f.path.startswith(prefix)}
        prs.append(open_pr(repo, f"phase4/ci-{short}", ci_files, "Phase 4 CI pipeline",
                           "CI workflows generated by PDLC Phase 4 from the approved infrastructure change set "
                           f"({settings.infra_repo} branch phase4/infra-{short}).", local_root).__dict__)
    report = {"pull_requests": prs}
    files.write_json(project, f"{files.PUBLISH_DIR}/infra.json", report | {"at": files.utcnow().isoformat()})
    return report


PUBLISHERS = {"backlog": publish_backlog, "sprint": publish_sprint, "assignments": publish_assignments,
              "infra": publish_infra}
