"""Linear adapter: GraphQL at https://api.linear.app/graphql.

Idempotency: issues are created with a client-supplied UUID derived from the Phase 4 marker
(uuid5), so a marker lookup is a direct ``issue(id:)`` query and no per-item labels are needed.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone
from functools import cached_property

from agent_engine.phase4.contracts import TrackerConfig
from agent_engine.phase4.settings import get_settings

from .base import ExtObj, HttpClient, TrackerAdapter, TrackerError

NAMESPACE = uuid.UUID("6f0c3e8a-4b8f-4a8e-9a55-1f4d6c0e9b21")


class LinearTracker(TrackerAdapter):
    kind = "linear"
    system = "linear"

    def __init__(self, cfg: TrackerConfig, http: HttpClient | None = None) -> None:
        s = get_settings()
        if not s.linear_api_key and http is None:
            raise TrackerError("LINEAR_API_KEY is required for the Linear tracker")
        auth = s.linear_api_key if not s.linear_api_key.lower().startswith("bearer ") else s.linear_api_key
        self.cfg = cfg
        self.http = http or HttpClient("https://api.linear.app", {"Authorization": auth,
                                                                 "Content-Type": "application/json"})

    def gql(self, query: str, variables: dict | None = None) -> dict:
        r = self.http.post("/graphql", json={"query": query, "variables": variables or {}}).json()
        if r.get("errors"):   # Linear can return HTTP 200 with errors
            raise TrackerError(f"Linear GraphQL error: {r['errors']}")
        if any(isinstance(value, dict) and value.get("success") is False for value in (r.get("data") or {}).values()):
            raise TrackerError("Linear mutation returned success=false")
        return r["data"]

    @staticmethod
    def id_for_marker(marker: str) -> str:
        return str(uuid.uuid5(NAMESPACE, marker))

    @cached_property
    def team(self) -> dict:
        return self.gql("""query($id:String!){ team(id:$id){ id issueEstimationType cyclesEnabled
                          states{ nodes{ id type } } } }""", {"id": self.cfg.linear_team_id})["team"]

    # ---- issues ----
    def create(self, payload: dict) -> ExtObj:
        inp = {"id": self.id_for_marker(payload["_marker"]), "teamId": self.cfg.linear_team_id,
               "title": payload["title"], "description": payload.get("body_md", "")}
        if payload.get("parent_id"):
            inp["parentId"] = payload["parent_id"]
        if payload.get("story_points") is not None:
            inp["estimate"] = int(round(payload["story_points"]))
        if payload.get("labels"):
            inp["labelIds"] = self._label_ids(payload["labels"])
        d = self.gql("mutation($i:IssueCreateInput!){ issueCreate(input:$i){ success issue{ id identifier } } }", {"i": inp})
        issue = d["issueCreate"]["issue"]
        return ExtObj(id=issue["id"], key=issue["identifier"])

    def update(self, external_id: str, fields: dict) -> None:
        inp = {}
        if "title" in fields:
            inp["title"] = fields["title"]
        if "body_md" in fields:
            inp["description"] = fields["body_md"]
        if fields.get("story_points") is not None:
            inp["estimate"] = int(round(fields["story_points"]))
        if "parent_id" in fields:
            inp["parentId"] = fields["parent_id"]
        if "labels" in fields:
            inp["labelIds"] = self._label_ids(fields["labels"])
        if inp:
            self.gql("mutation($id:String!,$i:IssueUpdateInput!){ issueUpdate(id:$id,input:$i){ success } }",
                     {"id": external_id, "i": inp})

    def get_fields(self, external_id: str) -> dict:
        i = self.gql("query($id:String!){ issue(id:$id){ title description estimate parent{id} } }", {"id": external_id})["issue"]
        labels, after = [], None
        while True:
            page = self.gql("""query($id:String!,$after:String){issue(id:$id){labels(first:100,after:$after){
                nodes{name} pageInfo{hasNextPage endCursor}}}}""", {"id": external_id, "after": after})["issue"]["labels"]
            labels.extend(x["name"] for x in page["nodes"])
            if not page["pageInfo"]["hasNextPage"]:
                break
            after = page["pageInfo"]["endCursor"]
        return {"title": i["title"], "body_md": i.get("description") or "", "story_points": i.get("estimate"),
                "hours": None, "parent_id": (i.get("parent") or {}).get("id"), "labels": labels}

    @cached_property
    def label_map(self):
        labels, after = {}, None
        while True:
            page = self.gql("""query($after:String){issueLabels(first:100,after:$after){pageInfo{hasNextPage endCursor}
                nodes{id name team{id}}}}""", {"after": after})["issueLabels"]
            for label in page["nodes"]:
                if not label.get("team") or label["team"]["id"] == self.cfg.linear_team_id:
                    labels[label["name"]] = label["id"]
            if not page["pageInfo"]["hasNextPage"]:
                return labels
            after = page["pageInfo"]["endCursor"]

    def _label_ids(self, names):
        out = []
        for name in names:
            if name not in self.label_map:
                label = self.gql("""mutation($i:IssueLabelCreateInput!){issueLabelCreate(input:$i){success issueLabel{id}}}""",
                                 {"i": {"name": name, "teamId": self.cfg.linear_team_id, "color": "#777777"}})["issueLabelCreate"]["issueLabel"]
                self.label_map[name] = label["id"]
            out.append(self.label_map[name])
        return out

    def find_by_marker(self, marker: str, level: str | None = None) -> ExtObj | None:
        try:
            i = self.gql("query($id:String!){ issue(id:$id){ id identifier } }", {"id": self.id_for_marker(marker)})["issue"]
        except TrackerError:
            return None
        return ExtObj(id=i["id"], key=i["identifier"]) if i else None

    def add_blocks(self, blocker_id: str, blocked_id: str) -> None:
        self.gql("mutation($i:IssueRelationCreateInput!){ issueRelationCreate(input:$i){ success } }",
                 {"i": {"issueId": blocker_id, "relatedIssueId": blocked_id, "type": "blocks"}})

    def blocks_of(self, issue_id: str) -> list[str]:
        return [n["relatedIssue"]["id"] for n in self._relations(issue_id) if n["type"] == "blocks"]

    def _relations(self, issue_id):
        out, after = [], None
        while True:
            page = self.gql("""query($id:String!,$after:String){issue(id:$id){relations(first:100,after:$after){
                pageInfo{hasNextPage endCursor} nodes{id type relatedIssue{id}}}}}""", {"id": issue_id, "after": after})["issue"]["relations"]
            out.extend(page["nodes"])
            if not page["pageInfo"]["hasNextPage"]:
                return out
            after = page["pageInfo"]["endCursor"]

    def remove_blocks(self, blocker_id: str, blocked_id: str) -> None:
        for relation in self._relations(blocker_id):
            if relation["type"] == "blocks" and relation["relatedIssue"]["id"] == blocked_id:
                self.gql("mutation($id:String!){issueRelationDelete(id:$id){success}}", {"id": relation["id"]})

    def reopen_item(self, issue_id: str) -> None:
        state = next((s["id"] for s in self.team["states"]["nodes"] if s["type"] in ("backlog", "unstarted")), None)
        if not state:
            raise TrackerError("Linear team has no backlog/unstarted state")
        self.gql("mutation($id:String!,$i:IssueUpdateInput!){issueUpdate(id:$id,input:$i){success}}",
                 {"id": issue_id, "i": {"stateId": state}})

    def item_done(self, issue_id: str) -> bool:
        i = self.gql("query($id:String!){ issue(id:$id){ state{ type } } }", {"id": issue_id})["issue"]
        return i["state"]["type"] in ("completed", "canceled")

    def add_comment(self, issue_id: str, text: str) -> None:
        self.gql("mutation($i:CommentCreateInput!){ commentCreate(input:$i){ success } }",
                 {"i": {"issueId": issue_id, "body": text}})

    def close_item(self, issue_id: str, reason: str) -> None:
        self.add_comment(issue_id, f"Closed by Phase 4: {reason}")
        state = next((s["id"] for s in self.team["states"]["nodes"] if s["type"] == "canceled"), None)
        if state:
            self.gql("mutation($id:String!,$i:IssueUpdateInput!){ issueUpdate(id:$id,input:$i){ success } }",
                     {"id": issue_id, "i": {"stateId": state}})

    # ---- cycles ----
    def _cycles(self) -> list[dict]:
        out, after = [], None
        while True:
            d = self.gql("""query($id:String!,$after:String){ team(id:$id){ cycles(first:100,after:$after){
                pageInfo{hasNextPage endCursor} nodes{ id number name startsAt endsAt
                completedAt isPast scopeHistory completedScopeHistory completedIssueCountHistory } } } }""",
                         {"id": self.cfg.linear_team_id, "after": after})
            page = d["team"]["cycles"]
            out.extend(page["nodes"])
            if not page["pageInfo"]["hasNextPage"]:
                return out
            after = page["pageInfo"]["endCursor"]

    def create_sprint(self, name: str, start: date, end: date, goal: str) -> ExtObj:
        for c in self._cycles():   # teams with automatic cycles already have them: match by dates
            if c["startsAt"][:10] == start.isoformat():
                return ExtObj(id=c["id"], key=str(c["number"]))
        iso = lambda d, t: datetime.combine(d, t, tzinfo=timezone.utc).isoformat()  # noqa: E731
        d = self.gql("mutation($i:CycleCreateInput!){ cycleCreate(input:$i){ success cycle{ id number } } }",
                     {"i": {"teamId": self.cfg.linear_team_id, "startsAt": iso(start, time(0)),
                            "endsAt": iso(end, time(23, 59)), "name": name, "description": goal}})
        c = d["cycleCreate"]["cycle"]
        return ExtObj(id=c["id"], key=str(c["number"]))

    def _set_cycle(self, issue_ids: list[str], cycle_id: str | None) -> None:
        for iid in issue_ids:
            children, after = [], None
            while True:
                kids = self.gql("""query($id:String!,$after:String){ issue(id:$id){ children(first:100,after:$after){
                    pageInfo{hasNextPage endCursor} nodes{id} } } }""", {"id": iid, "after": after})["issue"]["children"]
                children.extend(k["id"] for k in kids["nodes"])
                if not kids["pageInfo"]["hasNextPage"]:
                    break
                after = kids["pageInfo"]["endCursor"]
            for target in [iid] + children:
                self.gql("mutation($id:String!,$i:IssueUpdateInput!){ issueUpdate(id:$id,input:$i){ success } }",
                         {"id": target, "i": {"cycleId": cycle_id}})

    def move_to_sprint(self, sprint_id: str, issue_ids: list[str]) -> None:
        self._set_cycle(issue_ids, sprint_id)

    def move_to_backlog(self, issue_ids: list[str]) -> None:
        self._set_cycle(issue_ids, None)

    def assign(self, issue_id: str, account_id: str | None) -> None:
        self.gql("mutation($id:String!,$i:IssueUpdateInput!){ issueUpdate(id:$id,input:$i){ success } }",
                 {"id": issue_id, "i": {"assigneeId": account_id}})

    # ---- history ----
    def closed_sprints(self, limit: int = 12) -> list[dict]:
        done = [c for c in self._cycles() if c.get("completedAt") or c.get("isPast")]
        done = sorted(done, key=lambda c: c["endsAt"])[-limit:]
        return [{"external_sprint_id": c["id"], "name": c.get("name") or f"Cycle {c['number']}",
                 "start_date": c["startsAt"][:10], "end_date": c["endsAt"][:10],
                 "committed_points": float((c.get("scopeHistory") or [0])[0]),
                 "completed_points": float((c.get("completedScopeHistory") or [0])[-1]),
                 "completed_items": int((c.get("completedIssueCountHistory") or [0])[-1]),
                 "available_person_days": None} for c in done]

    def resolved_tickets(self, since: date) -> list[dict]:
        out, after = [], None
        while True:
            d = self.gql("""query($team:ID!,$since:DateTimeOrDuration!,$after:String){ issues(first:100, after:$after,
                filter:{ team:{ id:{ eq:$team } }, completedAt:{ gte:$since } }){ pageInfo{ hasNextPage endCursor }
                nodes{ identifier title description estimate createdAt completedAt labels{ nodes{ name } } } } }""",
                         {"team": self.cfg.linear_team_id, "since": since.isoformat(), "after": after})
            for n in d["issues"]["nodes"]:
                cycle = None
                if n.get("completedAt") and n.get("createdAt"):
                    cycle = (datetime.fromisoformat(n["completedAt"][:19]) - datetime.fromisoformat(n["createdAt"][:19])).days
                out.append({"ticket_key": n["identifier"], "title": n["title"], "body": (n.get("description") or "")[:2000],
                            "issue_type": "issue", "story_points": n.get("estimate"), "cycle_days": cycle,
                            "components": [l["name"] for l in n["labels"]["nodes"]], "resolved_at": n.get("completedAt")})
            page = d["issues"]["pageInfo"]
            if not page["hasNextPage"]:
                return out
            after = page["endCursor"]
