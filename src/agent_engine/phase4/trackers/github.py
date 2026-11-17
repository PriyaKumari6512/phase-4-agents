"""GitHub Issues + Projects v2 adapter.

External id = issue number (string). Sub-issue and dependency endpoints need the issue's REST *id*,
which is looked up from the number.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from functools import cached_property, lru_cache

from agent_engine.phase4.contracts import TrackerConfig
from agent_engine.phase4.settings import get_settings

from .base import ExtObj, HttpClient, TrackerAdapter, TrackerError

API_VERSION = "2026-03-10"
MARKER_RE = re.compile(r"\n?<!-- p4:(p4-[0-9a-f]{8}) -->")


def github_http(token: str | None = None) -> HttpClient:
    tok = token or get_settings().github_token
    if not tok:
        raise TrackerError("GITHUB_TOKEN is required for GitHub operations")
    return HttpClient("https://api.github.com", {"Authorization": f"Bearer {tok}",
                                                 "Accept": "application/vnd.github+json",
                                                 "X-GitHub-Api-Version": API_VERSION})


class GitHubTracker(TrackerAdapter):
    kind = "github"
    system = "github"

    def __init__(self, cfg: TrackerConfig, http: HttpClient | None = None) -> None:
        self.cfg = cfg
        self.http = http or github_http()
        self.repo = f"/repos/{cfg.github_owner}/{cfg.github_repo}"

    def gql(self, query: str, variables: dict | None = None) -> dict:
        r = self.http.post("/graphql", json={"query": query, "variables": variables or {}}).json()
        if r.get("errors"):
            raise TrackerError(f"GitHub GraphQL error: {r['errors']}")
        return r["data"]

    @lru_cache(maxsize=4096)
    def _issue(self, number: str) -> dict:
        return self.http.get(f"{self.repo}/issues/{number}").json()

    # ---- project (optional) ----
    @cached_property
    def project(self) -> dict | None:
        if not self.cfg.github_project_number:
            return None
        q = """query($o:String!,$n:Int!){ organization(login:$o){ projectV2(number:$n){ id fields(first:50){ nodes{
                 ... on ProjectV2Field{ id name dataType }
                 ... on ProjectV2IterationField{ id name configuration{ iterations{ id title startDate duration }
                     completedIterations{ id title startDate duration } } } } } } } }"""
        try:
            owner = self.gql(q, {"o": self.cfg.github_owner, "n": self.cfg.github_project_number}).get("organization")
            p = owner.get("projectV2") if owner else None
        except TrackerError:
            p = None
        if p is None:
            q2 = q.replace("organization(login:$o)", "user(login:$o)")
            owner = self.gql(q2, {"o": self.cfg.github_owner, "n": self.cfg.github_project_number}).get("user")
            p = owner.get("projectV2") if owner else None
        if p is None:
            raise TrackerError("GitHub project was not found or is not accessible to this token")
        fields = {f["name"]: f for f in p["fields"]["nodes"] if f}
        iteration = next((f for f in fields.values() if "configuration" in f), None)
        points = next((f for n, f in fields.items() if n.lower() in ("story points", "points", "estimate")
                       and f.get("dataType") == "NUMBER"), None)
        return {"id": p["id"], "iteration": iteration, "points": points}

    def _project_item(self, number: str) -> str:
        node = self._issue(number)["node_id"]
        d = self.gql("mutation($p:ID!,$c:ID!){ addProjectV2ItemById(input:{projectId:$p, contentId:$c}){ item{ id } } }",
                     {"p": self.project["id"], "c": node})
        return d["addProjectV2ItemById"]["item"]["id"]

    def _set_points(self, number: str, points: float | None) -> None:
        if points is None or not self.project or not self.project["points"]:
            return
        self.gql("""mutation($p:ID!,$i:ID!,$f:ID!,$v:Float!){ updateProjectV2ItemFieldValue(input:{projectId:$p,
                 itemId:$i, fieldId:$f, value:{ number:$v } }){ projectV2Item{ id } } }""",
                 {"p": self.project["id"], "i": self._project_item(number), "f": self.project["points"]["id"],
                  "v": float(points)})

    # ---- issues ----
    def create(self, payload: dict) -> ExtObj:
        body = payload.get("body_md", "") + f"\n<!-- p4:{payload['_marker']} -->"
        labels = list(dict.fromkeys(payload.get("labels", []) + [payload["_marker"]]))
        r = self.http.post(f"{self.repo}/issues", json={"title": payload["title"], "body": body, "labels": labels}).json()
        number = str(r["number"])
        if payload.get("parent_id"):
            self.http.post(f"{self.repo}/issues/{payload['parent_id']}/sub_issues", json={"sub_issue_id": r["id"]})
        self._set_points(number, payload.get("story_points"))
        return ExtObj(id=number, key=f"#{number}")

    def update(self, external_id: str, fields: dict) -> None:
        body = {}
        if "title" in fields:
            body["title"] = fields["title"]
        if "body_md" in fields:
            current = self.http.get(f"{self.repo}/issues/{external_id}").json().get("body") or ""
            m = MARKER_RE.search(current)
            body["body"] = fields["body_md"] + (m.group(0) if m else "")
        if body:
            self.http.patch(f"{self.repo}/issues/{external_id}", json=body)
        if "labels" in fields:
            current = self.http.get(f"{self.repo}/issues/{external_id}").json()
            markers = [x["name"] for x in current.get("labels", []) if re.fullmatch(r"p4-[0-9a-f]{8}", x["name"])]
            self.http.patch(f"{self.repo}/issues/{external_id}", json={"labels": fields["labels"] + markers})
        if "parent_id" in fields:
            if fields["parent_id"]:
                self.http.post(f"{self.repo}/issues/{fields['parent_id']}/sub_issues",
                               json={"sub_issue_id": self._issue(external_id)["id"], "replace_parent": True})
            else:
                parent = self._parent(external_id)
                if parent:
                    self.http.delete(f"{self.repo}/issues/{parent}/sub_issue", json={"sub_issue_id": self._issue(external_id)["id"]})
        if "story_points" in fields:
            self._set_points(external_id, fields["story_points"])

    def get_fields(self, external_id: str) -> dict:
        r = self.http.get(f"{self.repo}/issues/{external_id}").json()
        points = None
        if self.project and self.project["points"]:
            after = None
            while True:
                result = self.gql("""query($id:ID!,$name:String!,$after:String){ node(id:$id){ ... on Issue{
                    projectItems(first:100,after:$after){ pageInfo{hasNextPage endCursor} nodes{ project{id}
                    fieldValueByName(name:$name){ ... on ProjectV2ItemFieldNumberValue{ number } } } } } } }""",
                    {"id": r["node_id"], "name": self.project["points"]["name"], "after": after})
                page = result["node"]["projectItems"]
                item = next((n for n in page["nodes"] if n["project"]["id"] == self.project["id"]), None)
                if item is not None:
                    points = (item.get("fieldValueByName") or {}).get("number")
                    break
                if not page["pageInfo"]["hasNextPage"]:
                    break
                after = page["pageInfo"]["endCursor"]
        return {"title": r["title"], "body_md": MARKER_RE.sub("", r.get("body") or ""), "story_points": points,
                "hours": None, "parent_id": self._parent(external_id),
                "labels": [x["name"] for x in r.get("labels", []) if not re.fullmatch(r"p4-[0-9a-f]{8}", x["name"])]}

    def _parent(self, number):
        try:
            return str(self.http.get(f"{self.repo}/issues/{number}/parent").json()["number"])
        except TrackerError as exc:
            if "-> 404" in str(exc):
                return None
            raise

    def comparable(self, field: str, value):
        return None if field == "hours" or (field == "story_points" and (not self.project or not self.project["points"])) else value

    def _children(self, number):
        out, page = [], 1
        while True:
            batch = self.http.get(f"{self.repo}/issues/{number}/sub_issues", params={"per_page": 100, "page": page}).json()
            out.extend(str(s["number"]) for s in batch)
            if len(batch) < 100:
                return out
            page += 1

    def find_by_marker(self, marker: str, level: str | None = None) -> ExtObj | None:
        r = self.http.get(f"{self.repo}/issues", params={"labels": marker, "state": "all", "per_page": 5}).json()
        return ExtObj(id=str(r[0]["number"]), key=f"#{r[0]['number']}") if r else None

    def add_blocks(self, blocker_id: str, blocked_id: str) -> None:
        self.http.post(f"{self.repo}/issues/{blocked_id}/dependencies/blocked_by",
                       json={"issue_id": self._issue(blocker_id)["id"]})

    def blocks_of(self, issue_id: str) -> list[str]:
        out, page = [], 1
        while True:
            batch = self.http.get(f"{self.repo}/issues/{issue_id}/dependencies/blocking", params={"per_page":100, "page":page}).json()
            out.extend(str(i["number"]) for i in batch)
            if len(batch) < 100:
                return out
            page += 1

    def remove_blocks(self, blocker_id: str, blocked_id: str) -> None:
        self.http.delete(f"{self.repo}/issues/{blocked_id}/dependencies/blocked_by/{self._issue(blocker_id)['id']}")

    def reopen_item(self, issue_id: str) -> None:
        self.http.patch(f"{self.repo}/issues/{issue_id}", json={"state": "open"})

    def item_done(self, issue_id: str) -> bool:
        return self.http.get(f"{self.repo}/issues/{issue_id}").json().get("state") == "closed"

    def add_comment(self, issue_id: str, text: str) -> None:
        self.http.post(f"{self.repo}/issues/{issue_id}/comments", json={"body": text})

    def close_item(self, issue_id: str, reason: str) -> None:
        self.add_comment(issue_id, f"Closed by Phase 4: {reason}")
        self.http.patch(f"{self.repo}/issues/{issue_id}", json={"state": "closed", "state_reason": "not_planned"})

    # ---- iterations ----
    def create_sprint(self, name: str, start: date, end: date, goal: str) -> ExtObj:
        if not self.project or not self.project["iteration"]:
            raise TrackerError("GitHub sprints need a Projects v2 project with an iteration field "
                               "(set tracker.github_project_number)")
        for it in self.project["iteration"]["configuration"]["iterations"]:
            if it["startDate"] == start.isoformat():
                return ExtObj(id=it["id"], key=it["title"])
        raise TrackerError(f"no iteration starting {start} in the project's iteration field; add iterations in the "
                           "project settings to match the sprint calendar (Phase 4 does not rewrite iteration config)")

    def move_to_sprint(self, sprint_id: str, issue_ids: list[str]) -> None:
        for n in issue_ids:
            for target in [n] + self._children(n):
                self.gql("""mutation($p:ID!,$i:ID!,$f:ID!,$v:String!){ updateProjectV2ItemFieldValue(input:{projectId:$p,
                         itemId:$i, fieldId:$f, value:{ iterationId:$v } }){ projectV2Item{ id } } }""",
                         {"p": self.project["id"], "i": self._project_item(target),
                          "f": self.project["iteration"]["id"], "v": sprint_id})

    def move_to_backlog(self, issue_ids: list[str]) -> None:
        for n in issue_ids:
            for target in [n] + self._children(n):
                self.gql("""mutation($p:ID!,$i:ID!,$f:ID!){ clearProjectV2ItemFieldValue(input:{projectId:$p, itemId:$i,
                         fieldId:$f}){ projectV2Item{ id } } }""",
                         {"p": self.project["id"], "i": self._project_item(target), "f": self.project["iteration"]["id"]})

    def assign(self, issue_id: str, account_id: str | None) -> None:
        self.http.patch(f"{self.repo}/issues/{issue_id}", json={"assignees": [account_id] if account_id else []})

    # ---- history ----
    def closed_sprints(self, limit: int = 12) -> list[dict]:
        if not self.project or not self.project["iteration"]:
            return []
        items, after = [], None
        while True:
            d = self.gql("""query($p:ID!,$a:String){ node(id:$p){ ... on ProjectV2{ items(first:100, after:$a){
                pageInfo{ hasNextPage endCursor } nodes{ content{ ... on Issue{ state closedAt } }
                fieldValues(first:20){ nodes{ ... on ProjectV2ItemFieldIterationValue{ iterationId }
                ... on ProjectV2ItemFieldNumberValue{ number field{ ... on ProjectV2Field{ name } } } } } } } } } }""",
                         {"p": self.project["id"], "a": after})
            page = d["node"]["items"]
            items.extend(page["nodes"])
            if not page["pageInfo"]["hasNextPage"]:
                break
            after = page["pageInfo"]["endCursor"]
        out = []
        for it in self.project["iteration"]["configuration"]["completedIterations"][:limit]:
            start = date.fromisoformat(it["startDate"])
            end = date.fromordinal(start.toordinal() + it["duration"] - 1)
            committed = completed = 0.0
            n_done = 0
            for node in items:
                vals = node["fieldValues"]["nodes"]
                if not any(v.get("iterationId") == it["id"] for v in vals):
                    continue
                pts = next((v["number"] for v in vals if "number" in v), 1.0) or 1.0
                committed += pts
                c = node.get("content") or {}
                if c.get("state") == "CLOSED" and (c.get("closedAt") or "")[:10] <= end.isoformat():
                    completed += pts
                    n_done += 1
            out.append({"external_sprint_id": it["id"], "name": it["title"], "start_date": start.isoformat(),
                        "end_date": end.isoformat(), "committed_points": committed, "completed_points": completed,
                        "completed_items": n_done, "available_person_days": None})
        return out

    def resolved_tickets(self, since: date) -> list[dict]:
        out, page = [], 1
        while True:
            r = self.http.get(f"{self.repo}/issues", params={"state": "closed", "since": since.isoformat(),
                                                              "per_page": 100, "page": page}).json()
            for i in r:
                if "pull_request" in i or not i.get("closed_at") or i["closed_at"][:10] < since.isoformat():
                    continue
                cycle = (datetime.fromisoformat(i["closed_at"][:19]) - datetime.fromisoformat(i["created_at"][:19])).days
                out.append({"ticket_key": f"#{i['number']}", "title": i["title"],
                            "body": MARKER_RE.sub("", i.get("body") or "")[:2000], "issue_type": "issue",
                            "story_points": None, "cycle_days": cycle,
                            "components": [l["name"] for l in i.get("labels", [])], "resolved_at": i["closed_at"]})
            if len(r) < 100:
                return out
            page += 1
