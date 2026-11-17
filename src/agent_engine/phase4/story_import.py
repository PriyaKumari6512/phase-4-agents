"""Approved stories -> phase4/stories.json (Task Breakdown's main input).

The PDLC has the User Story agent write and a human approve the stories (Gate 2) before Phase 4. Task Breakdown
splits those stories into tasks; it does not write its own. This module reads them from the tracker with read-only
requests and stores an exact, content-only snapshot:

  * Jira: GET /rest/api/3/search/jql with JIRA_STORY_JQL (default: the project's Story issues in the "To Do"
    status category). Only stories whose description carries the approval marker (default "Approved at gate G2",
    PHASE4_STORY_APPROVAL_MARKER, empty = no check) are kept; the others are listed under `excluded`.
  * Any other tracker: a hand-made phase4/stories.json is validated and used as-is.

The description is parsed by its headings (Acceptance criteria / Notes / Traceability); criteria keep their own ids
(US-001.AC1). JIRA_ACCEPTANCE_FIELD_ID reads criteria from a custom field instead. Story points are read from
JIRA_STORY_POINTS_FIELD_ID, else from the populated field named "Story point estimate" or "Story Points".
"""
from __future__ import annotations

import json
import os
import re

from agent_engine.phase4 import files
from agent_engine.phase4.contracts import (
    ImportedCriterion,
    ImportedEpic,
    ImportedStory,
    ProjectSettings,
    StoryExclusion,
    StorySnapshot,
    TrackerKind,
)

DEFAULT_APPROVAL_MARKER = "Approved at gate G2"
POINTS_FIELD_NAMES = ("Story point estimate", "Story Points")
REQ_LABEL_RE = re.compile(r"^(US|FR|NFR|DS)-\d+$")
REQ_TEXT_RE = re.compile(r"\b(?:US|FR|NFR|DS)-\d+\b")
PERSONA_RE = re.compile(r"^P-\d+$")
MOSCOW_RE = re.compile(r"^moscow-(must|should|could|wont)$", re.I)
AC_ID_RE = re.compile(r"^\s*((?:[A-Z][A-Z0-9]*-\d+\.)?AC-?\d+)\s*[:.\-–]\s*(.+)$", re.S)
STATEMENT_RE = re.compile(r"^\s*as\s+.+?\bI\s+want\b", re.I | re.S)
SECTION_ALIASES = {"acceptance criteria": "acceptance", "acceptance": "acceptance", "notes": "notes",
                   "traceability": "traceability"}
FIELDS = ["summary", "description", "labels", "priority", "fixVersions", "components", "parent", "issuelinks",
          "status", "issuetype", "project"]


# ---------------------------------------------------------------------------------------------- description parsing
def _inline(node: dict) -> str:
    if node.get("type") == "text":
        return node.get("text", "")
    if node.get("type") == "hardBreak":
        return "\n"
    if node.get("type") in ("mention", "emoji", "inlineCard"):
        attrs = node.get("attrs") or {}
        return attrs.get("text") or attrs.get("shortName") or attrs.get("url") or ""
    return "".join(_inline(c) for c in node.get("content", []) or [])


def _blocks(adf: dict | None) -> list[tuple[str, str]]:
    """ADF -> ordered (kind, text) blocks: heading, para, item (one per list item)."""
    out: list[tuple[str, str]] = []

    def walk(node: dict) -> None:
        kind = node.get("type")
        if kind == "heading":
            out.append(("heading", _inline(node).strip()))
        elif kind in ("paragraph", "codeBlock", "blockquote", "panel"):
            text = _inline(node).strip()
            if text:
                out.append(("para", text))
        elif kind == "listItem":
            text = " ".join(_inline(c).strip() for c in node.get("content", []) or [] if _inline(c).strip())
            if text:
                out.append(("item", text))
        elif kind == "table":
            for row in node.get("content", []) or []:
                cells = [_inline(c).strip() for c in row.get("content", []) or []]
                if any(cells):
                    out.append(("para", " | ".join(cells)))
        else:
            for child in node.get("content", []) or []:
                walk(child)

    if isinstance(adf, dict):
        walk(adf)
    return out


def _text_blocks(text: str) -> list[tuple[str, str]]:
    """Plain/Markdown descriptions (older Jira, other sources): '### Heading', 'Heading:' lines, '- ' items."""
    out: list[tuple[str, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if m := re.match(r"^#{1,6}\s+(.+?)\s*#*$", line):
            out.append(("heading", m.group(1)))
        elif line.rstrip(":").strip().lower() in SECTION_ALIASES and line.endswith(":"):
            out.append(("heading", line.rstrip(":").strip()))
        elif m := re.match(r"^(?:[-*•]|\d+[.)])\s+(.+)$", line):
            out.append(("item", m.group(1)))
        else:
            out.append(("para", line))
    return out


def _description_blocks(value) -> list[tuple[str, str]]:
    if isinstance(value, dict):
        return _blocks(value)
    if isinstance(value, str):
        return _text_blocks(value)
    return []


def _render(blocks: list[tuple[str, str]]) -> str:
    lines = []
    for kind, text in blocks:
        lines.append(f"### {text}" if kind == "heading" else f"- {text}" if kind == "item" else text)
    return "\n".join(lines)


def _sections(blocks: list[tuple[str, str]]) -> dict[str, list[tuple[str, str]]]:
    sections: dict[str, list[tuple[str, str]]] = {"preamble": []}
    current = "preamble"
    for kind, text in blocks:
        if kind == "heading":
            current = SECTION_ALIASES.get(text.strip().rstrip(":").lower(), "other:" + text.strip())
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append((kind, text))
    return sections


def _criteria(key: str, blocks: list[tuple[str, str]]) -> list[ImportedCriterion]:
    rows = [t for k, t in blocks if k == "item"] or [t for k, t in blocks if k == "para"]
    out, seen = [], set()
    for n, text in enumerate(rows, 1):
        m = AC_ID_RE.match(text)
        ac_id, body = (m.group(1), m.group(2).strip()) if m else (f"{key}.AC{n}", text.strip())
        while ac_id in seen:
            ac_id += "'"
        seen.add(ac_id)
        out.append(ImportedCriterion(ac_id=ac_id, text=" ".join(body.split())))
    return out


# ---------------------------------------------------------------------------------------------- issue -> record
def _points_field(issues: list[dict], names: dict[str, str]) -> str | None:
    configured = os.environ.get("JIRA_STORY_POINTS_FIELD_ID", "").strip()
    if configured:
        return configured
    candidates = [fid for fid, name in names.items() if name in POINTS_FIELD_NAMES]
    if not candidates:
        return None
    filled = {fid: sum(1 for i in issues if (i.get("fields") or {}).get(fid) is not None) for fid in candidates}
    order = {name: n for n, name in enumerate(POINTS_FIELD_NAMES)}
    return max(candidates, key=lambda fid: (filled[fid], -order[names[fid]]))


def parse_story(issue: dict, points_field: str | None = None, acceptance_field: str | None = None,
                approval_marker: str = DEFAULT_APPROVAL_MARKER) -> ImportedStory:
    f = issue.get("fields") or {}
    key = issue["key"]
    blocks = _description_blocks(f.get("description"))
    sections = _sections(blocks)
    preamble = [t for _, t in sections.get("preamble", [])]
    statement = next((t for t in preamble if STATEMENT_RE.match(t)), "")
    if acceptance_field:
        criteria = _criteria(key, _description_blocks(f.get(acceptance_field)))
    else:
        criteria = _criteria(key, sections.get("acceptance", []))
    rendered = _render(blocks)
    labels = list(f.get("labels") or [])
    traceability = "\n".join(t for _, t in sections.get("traceability", []))
    requirement_ids = list(dict.fromkeys([l for l in labels if REQ_LABEL_RE.match(l)] +
                                         REQ_TEXT_RE.findall(traceability)))
    moscow = next((m.group(1).lower() for l in labels if (m := MOSCOW_RE.match(l))), None)
    if moscow is None and (m := re.search(r"MoSCoW\s*[:\-]?\s*(Must|Should|Could|Won'?t)", traceability, re.I)):
        moscow = m.group(1).lower().replace("'", "")
    approval = next((t for _, t in blocks if approval_marker and approval_marker.lower() in t.lower()), None)
    points = f.get(points_field) if points_field else None
    blocks_keys = sorted({l["outwardIssue"]["key"] for l in f.get("issuelinks") or []
                          if "outwardIssue" in l and (l.get("type") or {}).get("outward", "").lower() == "blocks"})
    parent = f.get("parent") or {}
    return ImportedStory(
        key=key, issue_id=str(issue.get("id", "")), summary=(f.get("summary") or "").strip(),
        statement=statement, acceptance_criteria=criteria,
        notes="\n".join(t for _, t in sections.get("notes", [])), traceability=traceability,
        description_md=rendered, labels=labels, requirement_ids=requirement_ids,
        persona_ids=[l for l in labels if PERSONA_RE.match(l)], moscow=moscow,
        priority=(f.get("priority") or {}).get("name"),
        fix_versions=[v.get("name", "") for v in f.get("fixVersions") or []],
        components=[c.get("name", "") for c in f.get("components") or []],
        epic_key=parent.get("key") if (parent.get("fields") or {}).get("issuetype", {}).get("name", "Epic") == "Epic" else None,
        story_points=float(points) if isinstance(points, (int, float)) else None,
        blocks=blocks_keys, status=(f.get("status") or {}).get("name", ""), approval=approval)


def parse_epic(issue: dict) -> ImportedEpic:
    f = issue.get("fields") or {}
    text = _render(_description_blocks(f.get("description")))
    labels = list(f.get("labels") or [])
    return ImportedEpic(key=issue["key"], issue_id=str(issue.get("id", "")), summary=(f.get("summary") or "").strip(),
                        description_md=text, labels=labels,
                        requirement_ids=list(dict.fromkeys(REQ_TEXT_RE.findall(text) +
                                                           [l for l in labels if REQ_LABEL_RE.match(l)])))


# ---------------------------------------------------------------------------------------------- Jira reads
def _search(http, jql: str, fields: list[str], limit: int = 5000) -> tuple[list[dict], dict[str, str]]:
    """Read-only paginated search (GET). Returns issues and the id -> display-name map of their fields."""
    issues: list[dict] = []
    names: dict[str, str] = {}
    token = None
    while True:
        params = {"jql": jql, "fields": ",".join(fields), "maxResults": 100, "expand": "names"}
        if token:
            params["nextPageToken"] = token
        page = http.get("/rest/api/3/search/jql", params=params).json()
        issues.extend(page.get("issues", []))
        names.update(page.get("names") or {})
        token = page.get("nextPageToken")
        if not token or page.get("isLast") or len(issues) >= limit:
            return issues, names


def default_jql(project_key: str) -> str:
    return f'project = "{project_key}" AND issuetype = Story AND statusCategory = "To Do" ORDER BY key ASC'


def _key_order(key: str) -> tuple[str, int]:
    prefix, _, number = key.rpartition("-")
    return prefix, int(number) if number.isdigit() else 0


def import_from_jira(project: str, settings: ProjectSettings, http=None) -> StorySnapshot:
    cfg = settings.tracker
    close = None
    if http is None:
        from agent_engine.phase4.trackers.jira import JiraTracker
        tracker = JiraTracker(cfg)
        http, close = tracker.http, tracker.close
    try:
        jql = os.environ.get("JIRA_STORY_JQL", "").strip() or default_jql(cfg.jira_project_key)
        marker = os.environ.get("PHASE4_STORY_APPROVAL_MARKER", DEFAULT_APPROVAL_MARKER).strip()
        acceptance_field = os.environ.get("JIRA_ACCEPTANCE_FIELD_ID", "").strip() or None
        configured_points = os.environ.get("JIRA_STORY_POINTS_FIELD_ID", "").strip()
        fields = FIELDS + [f for f in (configured_points, acceptance_field) if f]
        if not configured_points:
            fields.append("*navigable")  # custom fields too, to discover the populated story-point field by name
        issues, names = _search(http, jql, fields)
        points_field = _points_field(issues, names)
        stories, excluded = [], []
        for issue in sorted(issues, key=lambda i: _key_order(i["key"])):
            f = issue.get("fields") or {}
            summary = (f.get("summary") or "").strip()
            if (f.get("project") or {}).get("key", cfg.jira_project_key) != cfg.jira_project_key:
                excluded.append(StoryExclusion(key=issue["key"], summary=summary, reason="belongs to another project"))
                continue
            if (f.get("issuetype") or {}).get("name", "Story") != "Story":
                excluded.append(StoryExclusion(key=issue["key"], summary=summary,
                                               reason=f"issue type {(f.get('issuetype') or {}).get('name')} is not a story"))
                continue
            story = parse_story(issue, points_field, acceptance_field, marker)
            if marker and story.approval is None:
                excluded.append(StoryExclusion(key=story.key, summary=summary,
                                               reason=f"description has no approval line ({marker!r})"))
                continue
            stories.append(story)
        epic_keys = sorted({s.epic_key for s in stories if s.epic_key}, key=_key_order)
        epics = []
        if epic_keys:
            found, _ = _search(http, f"key in ({','.join(epic_keys)}) ORDER BY key ASC",
                               ["summary", "description", "labels", "issuetype"])
            epics = [parse_epic(i) for i in sorted(found, key=lambda i: _key_order(i["key"]))]
        if not stories:
            reasons = "; ".join(f"{e.key}: {e.reason}" for e in excluded[:10])
            raise files.ProjectError(f"no approved stories matched JQL {jql!r}" + (f" (excluded {reasons})" if reasons else ""))
        return StorySnapshot(project=project, source="jira", site=cfg.jira_base_url or "",
                             project_key=cfg.jira_project_key or "", jql=jql, story_points_field=points_field,
                             approval_marker=marker, epics=epics, stories=stories, excluded=excluded)
    finally:
        if close:
            close()


# ---------------------------------------------------------------------------------------------- entry point
def import_stories(project: str, http=None) -> dict:
    """Refresh phase4/stories.json from the tracker; write only when its content changed."""
    settings = files.read_json(project, files.PROJECT_SETTINGS, ProjectSettings)
    if settings.tracker.kind != TrackerKind.JIRA:
        if not files.exists(project, files.STORIES):
            raise files.ProjectError(f"{files.STORIES} is missing: import approved stories from Jira "
                                     "(PHASE4_TRACKER=jira) or add the file")
        snapshot = files.read_json(project, files.STORIES, StorySnapshot)
        return _summary(project, snapshot, changed=False)
    snapshot = import_from_jira(project, settings, http)
    text = json.dumps(snapshot.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"
    changed = not files.exists(project, files.STORIES) or files.read_text(project, files.STORIES) != text
    if changed:
        files.write_text(project, files.STORIES, text)
    return _summary(project, snapshot, changed)


def _summary(project: str, snapshot: StorySnapshot, changed: bool) -> dict:
    stories = snapshot.stories
    return {"written": files.virtual(project, files.STORIES), "changed": changed, "source": snapshot.source,
            "stories": len(stories), "epics": len(snapshot.epics),
            "without_acceptance_criteria": [s.key for s in stories if not s.acceptance_criteria],
            "without_story_points": [s.key for s in stories if s.story_points is None],
            "excluded": [e.model_dump() for e in snapshot.excluded]}
