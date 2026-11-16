"""Publishing an approved file to the outside world: `agent-engine phase4 publish <what> --project-name P`.

  backlog      (P4-G1)  epics/stories/tasks + "blocks" links -> tracker (local files, Jira, Linear, GitHub Issues)
  sprint       (P4-G2)  sprints/cycles/iterations, stories moved in, deferred ones back to the backlog
  assignments  (P4-G3)  assignees + explanation comments; AI tasks dispatched to Copilot / Claude Code Action
  infra        (P4-G4)  one infra PR (infra/repo) + one CI PR per code repository (infra/ci/<repo>)

Every command refuses unless the gate is approved and the approved files are unchanged since. Writes are
exactly-once: publish/external-ids.json maps every local id to its tracker id (adopting items found by marker
label after a crash), and the last payload sent is kept so fields a human edited in the tracker are never
overwritten (three-way merge). Nothing is ever deleted: items that left the backlog are closed as won't-do.
Each run writes a report to publish/<what>.json.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import date
from typing import Any

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

log = logging.getLogger(__name__)
EXTERNAL_IDS = "publish/external-ids.json"
OWNED_FIELDS = ("title", "body_md", "story_points", "hours")
ORDER = {"epic": 0, "story": 1, "task": 2}
GATE_FOR = {"backlog": "P4-G1", "sprint": "P4-G2", "assignments": "P4-G3", "infra": "P4-G4"}


class PublishError(RuntimeError):
    pass


# ============================================================================ gate
def require_gate(project: str, what: str) -> dict:
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
    return files.read_json(project, approval)


# ============================================================================ exactly-once mapping
class ExternalIds:
    """publish/external-ids.json: {system: {local_id: {id, key, payload_sha256, last_payload}}}."""

    def __init__(self, project: str) -> None:
        self.project = project
        self.data: dict = files.read_json(project, EXTERNAL_IDS) if files.exists(project, EXTERNAL_IDS) else {}

    def get(self, system: str, local_id: str) -> dict | None:
        return self.data.get(system, {}).get(local_id)

    def put(self, system: str, local_id: str, ext_id: str, key: str | None, payload: dict) -> None:
        self.data.setdefault(system, {})[local_id] = {"id": ext_id, "key": key, "payload_sha256": _sha(payload),
                                                       "last_payload": payload}
        self.save()               # saved after every write, so a crash never loses a mapping already created

    def save(self) -> None:
        files.write_json(self.project, EXTERNAL_IDS, self.data)


def _sha(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def marker(project: str, local_id: str) -> str:
    return "p4-" + hashlib.sha256(f"{project}:{local_id}".encode()).hexdigest()[:8]


def _norm(v: Any) -> Any:
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
        if f in last and cur != prev:
            if cur != nxt:
                kept.append(f)
            continue
        if cur != nxt:
            to_write[f] = new[f]
    return to_write, kept


def ensure(adapter: TrackerAdapter, ids: ExternalIds, project: str, local_id: str, payload: dict) -> dict:
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
            merged = dict(payload)
            for f in kept:
                merged[f] = current.get(f)
            ids.put(system, local_id, row["id"], row["key"], merged)
        return {"id": row["id"], "key": row["key"], "created": False, "kept_human_edits": kept}
    created = adapter.create(payload | {"_marker": marker(project, local_id)})
    ids.put(system, local_id, created.id, created.key, payload)
    return {"id": created.id, "key": created.key, "created": True, "kept_human_edits": []}


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
        self._with_item(external_id, lambda i: i.update({k: v for k, v in fields.items() if k in OWNED_FIELDS}))

    def get_fields(self, external_id: str) -> dict:
        i = next((x for x in self._items() if x["key"] == external_id), None)
        if i is None:
            raise TrackerError(f"local item {external_id} not found")
        return {f: i.get(f) for f in OWNED_FIELDS}

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
    parts.append(f"_Generated by PDLC Phase 4 · {item.item_id}{' · ' + item.speckit_ref if item.speckit_ref else ''}_")
    return "\n\n".join(parts)


def payload_for(item: WorkItem, parent_external: str | None) -> dict:
    num = re.search(r"\d{3}", item.item_id)
    labels = ["phase4"] + ([f"feature-{num.group(0)}"] if num else [])
    if item.level == "task" and item.ai_eligible:
        labels.append("ai-eligible")
    p = {"level": item.level, "title": item.title[:240], "body_md": body_md(item), "labels": labels,
         "parent_id": parent_external}
    if item.level == "story" and item.estimate and item.estimate.story_points is not None:
        p["story_points"] = item.estimate.story_points
    if item.level == "task" and item.estimate and item.estimate.hours is not None:
        p["hours"] = item.estimate.hours
    return p


def publish_backlog(project: str) -> dict:
    require_gate(project, "backlog")
    settings = files.read_json(project, files.PROJECT_SETTINGS, ProjectSettings)
    backlog = files.read_json(project, files.BACKLOG, Backlog)
    tracker = tracker_for(project, settings)
    ids = ExternalIds(project)
    items = backlog.by_id()
    ext: dict[str, str] = {}
    report = {"tracker": tracker.system, "created": 0, "updated_or_unchanged": 0, "kept_human_edits": {},
              "links": 0, "closed": 0}
    for item in sorted(backlog.items, key=lambda i: (ORDER[i.level], i.item_id)):
        res = ensure(tracker, ids, project, item.item_id, payload_for(item, ext.get(item.parent_id) if item.parent_id else None))
        ext[item.item_id] = res["id"]
        report["created" if res["created"] else "updated_or_unchanged"] += 1
        if res["kept_human_edits"]:
            report["kept_human_edits"][item.item_id] = res["kept_human_edits"]
    link_sys = f"{tracker.system}_link"
    for item in backlog.items:
        if item.level == "epic":
            continue
        for d in item.dependencies:
            if d.on_id in ext and items[d.on_id].level == item.level and ids.get(link_sys, f"{d.on_id}->{item.item_id}") is None:
                tracker.add_blocks(ext[d.on_id], ext[item.item_id])
                ids.put(link_sys, f"{d.on_id}->{item.item_id}", f"{ext[d.on_id]}->{ext[item.item_id]}", None, {})
                report["links"] += 1
    closed_sys = f"{tracker.system}_closed"
    for local_id, row in list(ids.data.get(tracker.system, {}).items()):
        if local_id not in items and ids.get(closed_sys, local_id) is None:
            tracker.close_item(row["id"], "removed from the backlog by a requirement change (won't do)")
            ids.put(closed_sys, local_id, row["id"], row.get("key"), {})
            report["closed"] += 1
    files.write_json(project, f"{files.PUBLISH_DIR}/backlog.json", report | {"at": files.utcnow().isoformat()})
    return report


# ============================================================================ sprint
def publish_sprint(project: str) -> dict:
    require_gate(project, "sprint")
    settings = files.read_json(project, files.PROJECT_SETTINGS, ProjectSettings)
    plan = files.read_json(project, files.SPRINT_PLAN, SprintPlan)
    tracker = tracker_for(project, settings)
    ids = ExternalIds(project)
    report = {"tracker": tracker.system, "sprints": 0, "moved": 0, "to_backlog": 0, "missing_in_tracker": []}

    def ext(story_id: str) -> str | None:
        row = ids.get(tracker.system, story_id)
        if row is None:
            report["missing_in_tracker"].append(story_id)
            return None
        return row["id"]

    sprint_sys = f"{tracker.system}_sprint"
    for sp in plan.sprints:
        if not sp.story_ids:
            continue
        row = ids.get(sprint_sys, f"sprint:{sp.start.isoformat()}")
        if row is None:
            obj = tracker.create_sprint(sp.name, sp.start, sp.end, sp.goal)
            ids.put(sprint_sys, f"sprint:{sp.start.isoformat()}", obj.id, obj.key, {"name": sp.name})
            sid = obj.id
        else:
            sid = row["id"]
        report["sprints"] += 1
        moved = [e for e in (ext(s) for s in sp.story_ids) if e]
        if moved:
            tracker.move_to_sprint(sid, moved)
            report["moved"] += len(moved)
    deferred = [e for e in (ext(d.story_id) for d in plan.deferred) if e]
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


# ============================================================================ assignments + AI dispatch
def publish_assignments(project: str) -> dict:
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
    features = {f.feature_dir.split("/")[1][:3]: f for f in backlog.features}
    report = {"tracker": tracker.system, "assigned": 0, "dispatched": [], "missing_in_tracker": []}
    for a in ap.assignments:
        row = ids.get(tracker.system, a.task_id)
        if row is None:
            report["missing_in_tracker"].append(a.task_id)
            continue
        if a.worker_kind == "human":
            prev = ids.get(f"{tracker.system}_assign", a.task_id)
            if prev is not None and prev["id"] == a.worker_id:
                continue                                  # already assigned to the same person
            tracker.assign(row["id"], accounts.get(a.worker_id))
            if a.explanation:
                tracker.add_comment(row["id"], f"Assigned by PDLC Phase 4 (approved at P4-G3): {a.explanation}")
            ids.put(f"{tracker.system}_assign", a.task_id, a.worker_id, None, {})
            report["assigned"] += 1
            continue
        if ids.get("dispatch", a.task_id) is not None:
            continue                                      # each AI task is dispatched once
        agent = agents.get(a.worker_id)
        task = by[a.task_id]
        repo = task.repo or (settings.code_repos[0] if len(settings.code_repos) == 1 else None)
        if agent is None or repo is None:
            report["dispatched"].append({"task_id": a.task_id, "error": "unknown AI agent or repository"})
            continue
        feature = features.get(a.task_id[:3])
        brief = dispatch.brief_for(task, by.get(task.parent_id), feature.feature_dir if feature else None, row.get("key"))
        adapter = dispatch.adapter_for(agent.provider, files.path(project, f"{files.PUBLISH_DIR}/dispatch", write=True))
        handle = adapter.start(repo=repo, base_ref="main", task_id=a.task_id, brief=brief)
        ids.put("dispatch", a.task_id, handle, None, {"provider": agent.provider, "repo": repo})
        tracker.add_comment(row["id"], f"Dispatched to {agent.agent_id} ({agent.provider}): {handle}. "
                                       f"{a.explanation}")
        report["dispatched"].append({"task_id": a.task_id, "agent": agent.agent_id, "handle": handle})
    if report["missing_in_tracker"]:
        report["hint"] = "publish the backlog first: agent-engine phase4 publish backlog"
    files.write_json(project, f"{files.PUBLISH_DIR}/assignments.json", report | {"at": files.utcnow().isoformat()})
    return report


# ============================================================================ infra + CI pull requests
def publish_infra(project: str) -> dict:
    from agent_engine.phase4.github_api import open_pr

    approval = require_gate(project, "infra")
    settings = files.read_json(project, files.PROJECT_SETTINGS, ProjectSettings)
    manifest = files.read_json(project, files.INFRA_MANIFEST, InfraManifest)
    if not settings.infra_repo:
        raise PublishError("set infra_repo in phase4/project.json")
    short = manifest.intent_sha256[:8]
    local_root = files.path(project, f"{files.PUBLISH_DIR}/prs", write=True)
    pr_body = files.read_text(project, files.INFRA_PR) + (
        f"\n\nApproved at P4-G4 by {approval.get('approver', {}).get('name', '?')} on {approval.get('decided_at', '?')}.\n")
    repo_files = {f.path.removeprefix("repo/"): files.read_text(project, f"infra/{f.path}")
                  for f in manifest.files if f.path.startswith("repo/")}
    prs = [open_pr(settings.infra_repo, f"phase4/infra-{short}", repo_files,
                   f"Phase 4 infrastructure ({', '.join(manifest.environments)})", pr_body, local_root).__dict__]
    for repo in manifest.ci_repos:
        prefix = f"ci/{repo.replace('/', '__')}/"
        ci_files = {f.path.removeprefix(prefix): files.read_text(project, f"infra/{f.path}")
                    for f in manifest.files if f.path.startswith(prefix)}
        prs.append(open_pr(repo, f"phase4/ci-{short}", ci_files, "Phase 4 CI pipeline",
                           "CI workflows generated by PDLC Phase 4 from the approved infrastructure change set "
                           f"({settings.infra_repo} branch phase4/infra-{short}).", local_root).__dict__)
    report = {"pull_requests": prs}
    files.write_json(project, f"{files.PUBLISH_DIR}/infra.json", report | {"at": files.utcnow().isoformat()})
    return report


PUBLISHERS = {"backlog": publish_backlog, "sprint": publish_sprint, "assignments": publish_assignments,
              "infra": publish_infra}
