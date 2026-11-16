"""Skill and code-ownership evidence from git history -> phase4/skill-profiles.json (used by Work Allocation).

Aggregated levels only, never productivity scores. Needs the optional `mining` extra (PyDriller):
`uv sync --extra mining`, then `agent-engine phase4 mine-profiles --project-name P --repo <clone> --name org/repo`.
"""
from __future__ import annotations

import fnmatch
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent_engine.phase4 import files, skills_taxonomy
from agent_engine.phase4.allocation import path_prefix
from agent_engine.phase4.contracts import ProjectSettings

HALF_LIFE_DAYS = 180


def _decay(when: datetime, now: datetime) -> float:
    return 0.5 ** (max(0.0, (now - when).total_seconds() / 86400) / HALF_LIFE_DAYS)


def _member_by_identity(settings: ProjectSettings) -> dict[str, str]:
    out = {m.email.lower(): m.member_id for m in settings.team}
    for m in settings.team:
        if m.github_login:
            out[m.github_login.lower()] = m.member_id
        out.setdefault(m.display_name.lower(), m.member_id)
    return out


def parse_codeowners(repo_dir: Path) -> list[tuple[str, list[str]]]:
    for loc in (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"):
        p = repo_dir / loc
        if p.exists():
            rules = []
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.split("#", 1)[0].strip()
                if line:
                    pat, *owners = line.split()
                    rules.append((pat, [o.lstrip("@").lower() for o in owners]))
            return rules
    return []


def codeowners_for(path: str, rules: list[tuple[str, list[str]]]) -> list[str]:
    """Last matching pattern wins (GitHub semantics)."""
    owners: list[str] = []
    for pat, who in rules:
        p = pat.lstrip("/")
        if p.endswith("/"):
            p += "*"
        if fnmatch.fnmatch(path, p) or fnmatch.fnmatch(path, f"*/{p}") or path.startswith(pat.strip("/") + "/"):
            owners = who
    return owners


def mine_repo(project: str, repo_dir: Path, repo_name: str, months: int = 12) -> dict:
    try:
        from pydriller import Repository
    except ImportError as e:
        raise files.ProjectError("PyDriller is not installed: run `uv sync --extra mining`") from e
    settings = files.read_json(project, files.PROJECT_SETTINGS, ProjectSettings)
    who = _member_by_identity(settings)
    now = datetime.now(timezone.utc)
    skill_score: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    area_commits: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for c in Repository(str(repo_dir), since=now - timedelta(days=30 * months)).traverse_commits():
        member = who.get((c.author.email or "").lower()) or who.get((c.author.name or "").lower())
        if not member:
            continue
        w = _decay(c.author_date.astimezone(timezone.utc), now)
        for f in c.modified_files:
            path = (f.new_path or f.old_path or "").replace("\\", "/")
            if not path:
                continue
            area_commits[path_prefix(path)][member] += w
            for tag in skills_taxonomy.from_path(path):
                skill_score[member][tag] += w
    data = files.read_json(project, files.SKILL_PROFILES) if files.exists(project, files.SKILL_PROFILES) else {}
    skills = data.setdefault("skills", {})
    for member, tags in skill_score.items():
        mine = skills.setdefault(member, {})
        for tag, score in tags.items():
            level = 1 - math.exp(-score / 5)       # saturating: ~0.86 after 10 recent commits touching the skill
            mine[tag] = round(max(mine.get(tag, 0.0), level), 3)
    rules = parse_codeowners(repo_dir)
    by_id = {m.member_id: m for m in settings.team}
    rows = [r for r in data.get("ownership", []) if r.get("repo") != repo_name]
    for area, per_member in area_commits.items():
        total = sum(per_member.values()) or 1
        owners = codeowners_for(area + "x", rules)
        for member, v in per_member.items():
            m = by_id[member]
            rows.append({"repo": repo_name, "path_prefix": area, "worker_id": member,
                         "commit_share": round(v / total, 3), "line_share": 0.0,
                         "is_codeowner": bool({(m.github_login or "").lower(), m.email.lower()} & set(owners))})
    data["ownership"] = rows
    data["mined_at"] = now.isoformat(timespec="seconds")
    files.write_json(project, files.SKILL_PROFILES, data)
    return {"members_with_evidence": len(skill_score), "areas": len(area_commits), "ownership_rows": len(rows),
            "written": str(files.path(project, files.SKILL_PROFILES))}
