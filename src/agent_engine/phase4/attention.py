"""What a gate approver should look at: items that did not block the pipeline but need a human decision.

Collected from the stage outputs (never from a model): stories that need attention, open product questions and
deferred criteria (Task Breakdown), stories left out of the plan (Sprint Planning), tasks left unassigned
(Work Allocation) and infrastructure gaps / scanner findings that were accepted as warnings (Infrastructure).
"""
from __future__ import annotations

import json

from agent_engine.phase4 import files


def _read(project: str, rel: str):
    try:
        return files.read_json(project, rel) if files.exists(project, rel) else None
    except (OSError, ValueError, files.ProjectError):
        return None


def open_items(project: str, agent: str) -> list[str]:
    """Human-readable lines for the gate of `agent`; empty when there is nothing to decide."""
    lines: list[str] = []
    if agent == "task-breakdown":
        backlog = _read(project, files.BACKLOG) or {}
        for item in backlog.get("items", []):
            if item.get("needs_attention"):
                lines.append(f"needs attention: {item['item_id']}: {item['needs_attention'][:300]}")
        for item in backlog.get("items", []):
            for q in item.get("open_questions") or []:
                if not q.startswith("NEEDS ATTENTION"):
                    lines.append(f"open question: {item['item_id']}: {q[:300]}")
    elif agent == "sprint-planning":
        plan = _read(project, files.SPRINT_PLAN) or {}
        for d in plan.get("deferred", []) or []:
            if isinstance(d, dict):
                lines.append(f"left out of the plan: {d.get('story_id')}: {d.get('explanation') or d.get('reason_code')}")
    elif agent == "work-allocation":
        plan = _read(project, files.ASSIGNMENTS) or {}
        for u in plan.get("unassigned", []) or []:
            lines.append(f"unassigned: {u.get('task_id')} ({u.get('reason_code')}): {u.get('explanation', '')[:300]}")
    elif agent == "infra-pipeline":
        manifest = _read(project, files.INFRA_MANIFEST) or {}
        for g in manifest.get("gaps", []):
            lines.append(f"infrastructure gap: {g if isinstance(g, str) else json.dumps(g)}"[:400])
        checks = _read(project, files.INFRA_CHECKS) or []
        for c in checks if isinstance(checks, list) else []:
            if c.get("passed"):        # findings the scanner policy accepted as warnings
                for f in c.get("findings") or []:
                    lines.append(f"scanner warning ({c.get('tool')} {f.get('rule_id')}, {f.get('severity')}): "
                                 f"{f.get('file') or ''} {f.get('message', '')}"[:400])
    return lines
