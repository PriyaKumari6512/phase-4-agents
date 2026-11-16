"""Deterministic parsers for spec-kit 1.3.0 spec.md and tasks.md. They never guess: unknown formats are errors."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

PHASE_RE = re.compile(r"^##\s+Phase\s+(\d+)\s*:\s*(.*)$")
TASK_RE = re.compile(r"^-\s*\[[ xX]\]\s+(T\d{3,4})\s+(\[P\]\s+)?(\[US(\d+)\]\s+)?(.+)$")
DEPENDS_RE = re.compile(r"\((?:depends on|after|requires)\s+([T\d,\s and]+)\)", re.I)
PATH_RE = re.compile(r"(?<![\w/.-])((?:[\w.-]+/)+[\w.-]+\.[A-Za-z0-9]+|[\w-]+\.(?:py|ts|tsx|js|jsx|go|java|kt|sql|md|yaml|yml|json|toml|tf|css|html))(?![\w/])")
STORY_HEAD_RE = re.compile(r"^###\s+User Story\s+(\d+)\s*[-–—:]\s*(.+?)\s*\(Priority:\s*(P\d)\)\s*(?:🎯.*)?$")
SCENARIO_RE = re.compile(r"^\s*\d+\.\s+\*\*Given\*\*\s*(.+?),?\s+\*\*When\*\*\s*(.+?),?\s+\*\*Then\*\*\s*(.+?)\s*$")
FR_RE = re.compile(r"^\s*-\s+\*\*(FR-\d+)\*\*:\s*(.+)$")
SOURCE_RE = re.compile(r"\(source:\s*([A-Z]+-\d+(?:\s*,\s*[A-Z]+-\d+)*)\)", re.I)
REQ_ID_RE = re.compile(r"\b((?:FR|NFR|US|DS|ARCH)-\d{1,4})\b")


class SpeckitFormatError(ValueError):
    pass


@dataclass
class RawTask:
    task_id: str
    parallel: bool
    story_num: int | None
    text: str
    phase_num: int
    phase_kind: str
    depends_on: list[str] = field(default_factory=list)
    paths: list[str] = field(default_factory=list)


@dataclass
class RawStory:
    num: int
    title: str
    priority: str
    body: str
    scenarios: list[tuple[str, str, str]]
    source_ids: list[str]


@dataclass
class RawSpec:
    title: str
    stories: list[RawStory]
    functional_requirements: list[tuple[str, str, list[str]]]  # (local FR id, text, source ids)
    source_ids: list[str]


def phase_kind(title: str) -> str:
    t = title.strip().lower()
    if t.startswith("setup"):
        return "setup"
    if t.startswith("foundational"):
        return "foundational"
    if "user story" in t:
        return "user_story"
    if t.startswith("polish"):
        return "polish"
    return "unknown"


def parse_tasks_md(md: str) -> list[RawTask]:
    tasks: list[RawTask] = []
    errors: list[str] = []
    phase_num, kind = 0, None
    for i, line in enumerate(md.splitlines(), 1):
        if m := PHASE_RE.match(line.strip()):
            phase_num, kind = int(m.group(1)), phase_kind(m.group(2))
            if kind == "unknown":
                errors.append(f"line {i}: unrecognized phase heading {line.strip()!r}")
            continue
        stripped = line.strip()
        if not stripped.startswith("- ["):
            continue
        if kind is None:
            continue  # checklist outside phases (e.g. in an intro) is not a task
        m = TASK_RE.match(stripped)
        if not m:
            errors.append(f"line {i}: task line does not match the spec-kit format: {stripped[:120]!r}")
            continue
        text = m.group(5).strip()
        deps: list[str] = []
        if dm := DEPENDS_RE.search(text):
            deps = re.findall(r"T\d{3,4}", dm.group(1))
        story = int(m.group(4)) if m.group(4) else None
        if kind == "user_story" and story is None:
            errors.append(f"line {i}: task in a user-story phase without [US#] label")
        tasks.append(RawTask(task_id=m.group(1), parallel=bool(m.group(2)), story_num=story, text=text,
                             phase_num=phase_num, phase_kind=kind, depends_on=deps,
                             paths=list(dict.fromkeys(PATH_RE.findall(text)))))
    if errors:
        raise SpeckitFormatError("; ".join(errors[:20]))
    if not tasks:
        raise SpeckitFormatError("tasks.md contains no tasks")
    ids = [t.task_id for t in tasks]
    if len(ids) != len(set(ids)):
        raise SpeckitFormatError("duplicate task ids in tasks.md")
    return tasks


def parse_spec_md(md: str) -> RawSpec:
    lines = md.splitlines()
    title = next((l.split(":", 1)[1].strip() for l in lines if l.startswith("# ") and ":" in l), "")
    if not title:
        title = next((l[2:].strip() for l in lines if l.startswith("# ")), "Feature")
    stories: list[RawStory] = []
    frs: list[tuple[str, str, list[str]]] = []
    cur: RawStory | None = None
    body: list[str] = []

    def close() -> None:
        nonlocal cur, body
        if cur:
            text = "\n".join(body).strip()
            cur.body = text
            cur.source_ids = list(dict.fromkeys(_sources(text)))
            stories.append(cur)
        cur, body = None, []

    for line in lines:
        if m := STORY_HEAD_RE.match(line.strip()):
            close()
            cur = RawStory(num=int(m.group(1)), title=m.group(2).strip(), priority=m.group(3), body="",
                           scenarios=[], source_ids=[])
            continue
        if cur and (line.startswith("## ") or line.startswith("### ")):
            close()
        if cur is not None:
            body.append(line)
            if sm := SCENARIO_RE.match(line):
                cur.scenarios.append((sm.group(1).strip(" ,"), sm.group(2).strip(" ,"), sm.group(3).strip(" .")))
        if fm := FR_RE.match(line):
            frs.append((fm.group(1), fm.group(2).strip(), _sources(fm.group(2))))
    close()
    if not stories:
        raise SpeckitFormatError("spec.md contains no '### User Story N - Title (Priority: Pn)' sections")
    seen, duplicates = set(), set()
    for story in stories:
        if story.num in seen:
            duplicates.add(story.num)
        seen.add(story.num)
    if duplicates:
        raise SpeckitFormatError(f"duplicate user story numbers in spec.md: {sorted(duplicates)}")
    all_sources = list(dict.fromkeys(s for st in stories for s in st.source_ids) |
                       dict.fromkeys(s for _, _, ss in frs for s in ss))
    return RawSpec(title=title, stories=stories, functional_requirements=frs, source_ids=all_sources)


def _sources(text: str) -> list[str]:
    out: list[str] = []
    for m in SOURCE_RE.finditer(text):
        out += [s.strip().upper() for s in m.group(1).split(",")]
    return out


def strip_markup(text: str) -> str:
    text = DEPENDS_RE.sub("", text)
    text = SOURCE_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()
