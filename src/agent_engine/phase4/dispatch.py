"""AI coding-agent dispatch adapters. Provider states are normalized to
queued | running | needs_input | succeeded | failed | timed_out | cancelled."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from agent_engine.phase4.settings import get_settings
from agent_engine.phase4.files import new_id, utcnow

from .trackers.base import HttpClient, TrackerError
from .trackers.github import API_VERSION, github_http

log = logging.getLogger(__name__)
CLAUDE_WORKFLOW = "phase4-claude.yml"

COPILOT_STATES = {"queued": "queued", "in_progress": "running", "completed": "succeeded", "failed": "failed",
                  "idle": "needs_input", "waiting_for_user": "needs_input", "timed_out": "timed_out",
                  "cancelled": "cancelled"}


class DispatchError(RuntimeError):
    pass


class CopilotDispatch:
    """GitHub Copilot cloud agent via the Agent Tasks REST API (public preview).
    Needs a USER token (fine-grained PAT / app user token) with "Agent tasks" read+write; installation tokens fail."""

    provider = "copilot_cloud_agent"

    def __init__(self) -> None:
        tok = get_settings().github_copilot_user_token
        if not tok:
            raise DispatchError("GITHUB_COPILOT_USER_TOKEN is required for Copilot dispatch")
        self.http = HttpClient("https://api.github.com", {"Authorization": f"Bearer {tok}",
                                                         "Accept": "application/vnd.github+json",
                                                         "X-GitHub-Api-Version": API_VERSION})

    def start(self, *, repo: str, base_ref: str, task_id: str, brief: str) -> str:
        r = self.http.post(f"/agents/repos/{repo}/tasks", json={"prompt": brief, "base_ref": base_ref,
                                                               "create_pull_request": True}).json()
        return f"{repo}#{r['id']}"

    def status(self, handle: str) -> tuple[str, str | None]:
        repo, tid = handle.split("#", 1)
        r = self.http.get(f"/agents/repos/{repo}/tasks/{tid}").json()
        pr = None
        for a in r.get("artifacts") or []:
            url = a.get("html_url") or a.get("url") or ""
            if "/pull/" in url:
                pr = url
        return COPILOT_STATES.get(r.get("state", ""), "running"), pr


class ClaudeActionDispatch:
    """anthropics/claude-code-action@v1 through a workflow_dispatch workflow installed by Agent 4."""

    provider = "claude_code_action"

    def __init__(self) -> None:
        self.http = github_http()

    def start(self, *, repo: str, base_ref: str, task_id: str, brief: str) -> str:
        self.http.post(f"/repos/{repo}/actions/workflows/{CLAUDE_WORKFLOW}/dispatches",
                       json={"ref": base_ref, "inputs": {"task_id": task_id, "brief": brief[:60000]}})
        return f"{repo}#{task_id}"

    def status(self, handle: str) -> tuple[str, str | None]:
        repo, task_id = handle.split("#", 1)
        runs = self.http.get(f"/repos/{repo}/actions/workflows/{CLAUDE_WORKFLOW}/runs", params={"per_page": 30}).json()
        run = next((r for r in runs.get("workflow_runs", []) if task_id in (r.get("display_title") or r.get("name") or "")), None)
        if run is None:
            return "queued", None
        pr = None
        try:
            q = self.http.get("/search/issues", params={"q": f"repo:{repo} is:pr {task_id}"}).json()
            pr = next((i["html_url"] for i in q.get("items", [])), None)
        except TrackerError:
            pass
        if run["status"] != "completed":
            return "running", pr
        return ("succeeded" if run.get("conclusion") == "success" else "failed"), pr


class LocalDispatch:
    """Records the dispatch brief as a file (PHASE4_PR_MODE=local): outputs/<project>/publish/dispatch/<task>.json."""

    def __init__(self, provider: str, root: Path) -> None:
        self.provider = provider
        self.root = root

    def start(self, *, repo: str, base_ref: str, task_id: str, brief: str) -> str:
        p = self.root / f"{task_id}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"provider": self.provider, "repo": repo, "base_ref": base_ref, "task_id": task_id,
                                 "brief": brief, "at": utcnow().isoformat()}, indent=2), encoding="utf-8")
        return f"local#{task_id}#{new_id()[:8]}"

    def status(self, handle: str) -> tuple[str, str | None]:
        return "queued", None


def adapter_for(provider: str, local_root: Path):
    s = get_settings()
    if s.phase4_pr_mode != "github":
        return LocalDispatch(provider, local_root)
    if provider == "copilot_cloud_agent":
        return CopilotDispatch()
    if provider == "claude_code_action":
        return ClaudeActionDispatch()
    raise DispatchError(f"unknown provider {provider}")


def brief_for(task, story, spec_dir: str | None, tracker_key: str | None) -> str:
    """Structured brief written from the task - never free-form."""
    lines = [f"# Task {task.item_id}: {task.title}", ""]
    if tracker_key:
        lines.append(f"Tracker key: {tracker_key}")
    lines += ["", "## Description", task.description_md, "", "## Acceptance criteria"]
    lines += [f"- {a.text}" for a in task.acceptance_criteria] or ["- (see story)"]
    lines += ["", "## Definition of Done"] + [f"- {d}" for d in task.definition_of_done]
    lines += ["", "## Files to change"] + [f"- `{p}`" for p in task.file_paths]
    if story:
        lines += ["", f"## Story context ({story.item_id})", story.title]
        lines += [f"- {a.text}" for a in story.acceptance_criteria]
    if spec_dir:
        lines += ["", f"Specification: `{spec_dir}` (spec.md, plan.md, tasks.md) in this repository."]
    lines += ["", "## Rules",
              "- Add or update tests for this change.",
              "- Touch only the files and areas listed above.",
              f"- Open exactly one pull request whose title starts with `[{task.item_id}]`"
              + (f" and references {tracker_key}." if tracker_key else "."),
              "- Do not change CI, infrastructure or secrets files."]
    return "\n".join(lines)


def task_id_in(text: str) -> str | None:
    m = re.search(r"\[(\d{3}-T\d{3,4}[a-z]?)\]", text or "")
    return m.group(1) if m else None
