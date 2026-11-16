"""Jira Cloud adapter: REST v3 + Agile REST 1.0."""
from __future__ import annotations

import logging
import re
from datetime import date, datetime, time, timezone
from functools import cached_property

from agent_engine.phase4.contracts import TrackerConfig
from agent_engine.phase4.settings import get_settings

from .adf import adf_to_text, markdown_to_adf
from .base import ExtObj, HttpClient, TrackerAdapter, TrackerError

log = logging.getLogger(__name__)


class JiraTracker(TrackerAdapter):
    kind = "jira"
    system = "jira"

    def __init__(self, cfg: TrackerConfig, http: HttpClient | None = None) -> None:
        s = get_settings()
        if not (s.jira_email and s.jira_api_token) and http is None:
            raise TrackerError("JIRA_EMAIL and JIRA_API_TOKEN are required for the Jira tracker")
        self.cfg = cfg
        self.http = http or HttpClient(cfg.jira_base_url.rstrip("/"), {"Accept": "application/json"},
                                       auth=(s.jira_email, s.jira_api_token))

    # ---- discovery ----
    @cached_property
    def issue_types(self) -> dict[str, str]:
        r = self.http.get(f"/rest/api/3/issue/createmeta/{self.cfg.jira_project_key}/issuetypes").json()
        values = r.get("issueTypes") or r.get("values") or []
        out: dict[str, str] = {}
        for t in values:
            name = t["name"].lower()
            if t.get("subtask"):
                out.setdefault("task", t["id"])
            elif name == "epic":
                out["epic"] = t["id"]
            elif name == "story":
                out["story"] = t["id"]
        missing = {"epic", "story", "task"} - set(out)
        if missing:
            raise TrackerError(f"Jira project lacks issue types for {missing}: {[t['name'] for t in values]}")
        return out

    @cached_property
    def estimation_field(self) -> str | None:
        cfg = self.http.get(f"/rest/agile/1.0/board/{self.cfg.jira_board_id}/configuration").json()
        return ((cfg.get("estimation") or {}).get("field") or {}).get("fieldId")

    # ---- issues ----
    def _fields(self, payload: dict) -> dict:
        f: dict = {}
        if "title" in payload:
            f["summary"] = payload["title"][:254]
        if "body_md" in payload:
            f["description"] = markdown_to_adf(payload["body_md"])
        if payload.get("story_points") is not None and self.estimation_field:
            f[self.estimation_field] = payload["story_points"]
        if payload.get("hours") is not None:
            f["timetracking"] = {"originalEstimate": f"{max(1, round(payload['hours']))}h"}
        if "parent_id" in payload:
            f["parent"] = {"id": payload["parent_id"]} if payload["parent_id"] else None
        if "labels" in payload:
            f["labels"] = payload["labels"]
        return f

    def create(self, payload: dict) -> ExtObj:
        fields = self._fields(payload) | {
            "project": {"key": self.cfg.jira_project_key},
            "issuetype": {"id": self.issue_types[payload["level"]]},
            "labels": [l.replace(" ", "-") for l in payload.get("labels", [])] + [payload["_marker"]],
        }
        fields.pop("parent", None)
        if payload.get("parent_id"):
            fields["parent"] = {"id": payload["parent_id"]}
        try:
            r = self.http.post("/rest/api/3/issue", json={"fields": fields}).json()
        except TrackerError as exc:
            if "timetracking" in str(exc) and re.search(r" -> (400|422):", str(exc)):
                fields.pop("timetracking", None)
                r = self.http.post("/rest/api/3/issue", json={"fields": fields}).json()
            else:
                raise
        return ExtObj(id=r["id"], key=r["key"])

    def update(self, external_id: str, fields: dict) -> None:
        body = self._fields(fields)
        if "labels" in body:
            current = self.http.get(f"/rest/api/3/issue/{external_id}", params={"fields": "labels"}).json()["fields"]
            body["labels"] += [x for x in current.get("labels", []) if re.fullmatch(r"p4-[0-9a-f]{8}", x)]
        if body:
            self.http.put(f"/rest/api/3/issue/{external_id}", json={"fields": body})

    def get_fields(self, external_id: str) -> dict:
        names = ["summary", "description", "timetracking", "labels", "parent"] + ([self.estimation_field] if self.estimation_field else [])
        r = self.http.get(f"/rest/api/3/issue/{external_id}", params={"fields": ",".join(names)}).json()["fields"]
        est = (r.get("timetracking") or {}).get("originalEstimateSeconds")
        return {"title": r.get("summary"), "body_md": adf_to_text(r.get("description")),
                "story_points": r.get(self.estimation_field) if self.estimation_field else None,
                "hours": est / 3600 if est else None, "parent_id": (r.get("parent") or {}).get("id"),
                "labels": [x for x in r.get("labels", []) if not re.fullmatch(r"p4-[0-9a-f]{8}", x)]}

    def comparable(self, field: str, value):
        if field == "body_md" and isinstance(value, str):
            return adf_to_text(markdown_to_adf(value))
        if field == "hours" and value is not None:
            return float(max(1, round(value)))
        return value

    def _search(self, jql: str, fields: list[str], limit: int = 1000) -> list[dict]:
        out, token = [], None
        while True:
            body = {"jql": jql, "fields": fields, "maxResults": min(100, limit - len(out))}
            if token:
                body["nextPageToken"] = token
            r = self.http.post("/rest/api/3/search/jql", json=body).json()
            out.extend(r.get("issues", []))
            token = r.get("nextPageToken")
            if not token or r.get("isLast") or len(out) >= limit:
                return out

    def find_by_marker(self, marker: str, level: str | None = None) -> ExtObj | None:
        hits = self._search(f'project = "{self.cfg.jira_project_key}" AND labels = "{marker}"', ["summary"], 1)
        return ExtObj(id=hits[0]["id"], key=hits[0]["key"]) if hits else None

    def add_blocks(self, blocker_id: str, blocked_id: str) -> None:
        # REST creation endpoints take the source of the outward verb as inwardIssue;
        # GET(blocker).issuelinks must then expose blocked as outwardIssue.
        # https://developer.atlassian.com/cloud/jira/platform/issue-linking-model/
        self.http.post("/rest/api/3/issueLink", json={"type": {"name": "Blocks"},
                                                      "inwardIssue": {"id": blocker_id},
                                                      "outwardIssue": {"id": blocked_id}})
        if blocked_id not in self.blocks_of(blocker_id):
            raise TrackerError("Jira dependency read-back did not confirm blocker -> blocked; inspect the created link before retrying")

    def blocks_of(self, issue_id: str) -> list[str]:
        links = self.http.get(f"/rest/api/3/issue/{issue_id}", params={"fields": "issuelinks"}).json()["fields"]["issuelinks"]
        return [l["outwardIssue"]["id"] for l in links if l["type"]["name"] == "Blocks" and "outwardIssue" in l]

    def remove_blocks(self, blocker_id: str, blocked_id: str) -> None:
        links = self.http.get(f"/rest/api/3/issue/{blocker_id}", params={"fields": "issuelinks"}).json()["fields"]["issuelinks"]
        for link in links:
            if link["type"]["name"] == "Blocks" and (link.get("outwardIssue") or {}).get("id") == blocked_id:
                self.http.delete(f"/rest/api/3/issueLink/{link['id']}")

    def reopen_item(self, issue_id: str) -> None:
        transitions = self.http.get(f"/rest/api/3/issue/{issue_id}/transitions").json().get("transitions", [])
        opened = next((t for t in transitions if (t.get("to", {}).get("statusCategory") or {}).get("key") != "done"), None)
        if not opened:
            raise TrackerError(f"no reopen transition for {issue_id}")
        self.http.post(f"/rest/api/3/issue/{issue_id}/transitions", json={"transition": {"id": opened["id"]}})

    def item_done(self, issue_id: str) -> bool:
        f = self.http.get(f"/rest/api/3/issue/{issue_id}", params={"fields": "status"}).json()["fields"]
        return f["status"]["statusCategory"]["key"] == "done"

    def add_comment(self, issue_id: str, text: str) -> None:
        self.http.post(f"/rest/api/3/issue/{issue_id}/comment", json={"body": markdown_to_adf(text)})

    def close_item(self, issue_id: str, reason: str) -> None:
        self.add_comment(issue_id, f"Closed by Phase 4: {reason}")
        ts = self.http.get(f"/rest/api/3/issue/{issue_id}/transitions").json().get("transitions", [])
        done = next((t for t in ts if (t.get("to", {}).get("statusCategory", {}) or {}).get("key") == "done"), None)
        if done:
            self.http.post(f"/rest/api/3/issue/{issue_id}/transitions", json={"transition": {"id": done["id"]}})
        else:
            log.warning("no done transition for %s; left open with comment", issue_id)

    # ---- sprints ----
    def create_sprint(self, name: str, start: date, end: date, goal: str) -> ExtObj:
        iso = lambda d, t: datetime.combine(d, t, tzinfo=timezone.utc).isoformat()  # noqa: E731
        r = self.http.post("/rest/agile/1.0/sprint", json={
            "name": name[:30], "originBoardId": self.cfg.jira_board_id, "startDate": iso(start, time(9)),
            "endDate": iso(end, time(17)), "goal": goal[:1000]}).json()
        return ExtObj(id=str(r["id"]), key=r.get("name"))

    def move_to_sprint(self, sprint_id: str, issue_ids: list[str]) -> None:
        for i in range(0, len(issue_ids), 50):
            self.http.post(f"/rest/agile/1.0/sprint/{sprint_id}/issue", json={"issues": issue_ids[i:i + 50]})

    def move_to_backlog(self, issue_ids: list[str]) -> None:
        for i in range(0, len(issue_ids), 50):
            self.http.post("/rest/agile/1.0/backlog/issue", json={"issues": issue_ids[i:i + 50]})

    def assign(self, issue_id: str, account_id: str | None) -> None:
        self.http.put(f"/rest/api/3/issue/{issue_id}/assignee", json={"accountId": account_id})

    # ---- history ----
    def closed_sprints(self, limit: int = 12) -> list[dict]:
        sprints, start = [], 0
        while True:
            r = self.http.get(f"/rest/agile/1.0/board/{self.cfg.jira_board_id}/sprint",
                              params={"state": "closed", "startAt": start, "maxResults": 50}).json()
            sprints.extend(r.get("values", []))
            if r.get("isLast", True):
                break
            start += len(r.get("values", []))
        sprints = sorted(sprints, key=lambda s: s.get("completeDate") or s.get("endDate") or "")[-limit:]
        out = []
        sp = self.estimation_field
        for spr in sprints:
            issues, st = [], 0
            while True:
                r = self.http.get(f"/rest/agile/1.0/sprint/{spr['id']}/issue",
                                  params={"fields": f"status,resolutiondate,{sp or 'summary'}", "startAt": st,
                                          "maxResults": 100}).json()
                issues.extend(r.get("issues", []))
                if st + len(r.get("issues", [])) >= r.get("total", 0) or not r.get("issues"):
                    break
                st += len(r["issues"])
            end = (spr.get("completeDate") or spr.get("endDate") or "")[:10]
            pts = lambda i: float((i["fields"].get(sp) or 0) if sp else 1)  # noqa: E731
            done = [i for i in issues if i["fields"]["status"]["statusCategory"]["key"] == "done"
                    and (i["fields"].get("resolutiondate") or "")[:10] <= end]
            out.append({"external_sprint_id": str(spr["id"]), "name": spr["name"],
                        "start_date": (spr.get("startDate") or end)[:10], "end_date": end,
                        "committed_points": sum(pts(i) for i in issues),
                        "completed_points": sum(pts(i) for i in done), "completed_items": len(done),
                        "available_person_days": None})
        return out

    def resolved_tickets(self, since: date) -> list[dict]:
        sp = self.estimation_field
        fields = ["summary", "description", "issuetype", "created", "resolutiondate", "components"] + ([sp] if sp else [])
        rows = self._search(f'project = "{self.cfg.jira_project_key}" AND statusCategory = Done AND resolved >= "{since}"',
                            fields)
        out = []
        for i in rows:
            f = i["fields"]
            created, resolved = f.get("created"), f.get("resolutiondate")
            cycle = None
            if created and resolved:
                cycle = (datetime.fromisoformat(resolved[:19]) - datetime.fromisoformat(created[:19])).days
            out.append({"ticket_key": i["key"], "title": f.get("summary", ""),
                        "body": adf_to_text(f.get("description"))[:2000], "issue_type": f["issuetype"]["name"],
                        "story_points": f.get(sp) if sp else None, "cycle_days": cycle,
                        "components": [c["name"] for c in f.get("components") or []], "resolved_at": resolved})
        return out

    def open_work(self) -> list[dict]:
        sp = self.estimation_field
        rows = self._search(f'project = "{self.cfg.jira_project_key}" AND assignee is not EMPTY AND statusCategory != Done',
                            ["assignee", "timetracking", "issuetype"] + ([sp] if sp else []))
        out = []
        for i in rows:
            f = i["fields"]
            est = (f.get("timetracking") or {}).get("remainingEstimateSeconds")
            out.append({"account": f["assignee"]["accountId"], "issue_id": i["id"],
                        "points": float(f.get(sp) or 0) if sp else 0.0, "hours": est / 3600 if est else None,
                        "subtask": bool((f.get("issuetype") or {}).get("subtask"))})
        return out
