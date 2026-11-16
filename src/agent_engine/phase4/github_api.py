"""GitHub pull requests for published change sets.

PHASE4_PR_MODE=local writes the PR content (files + PR.md) under the given local folder instead of calling GitHub,
so everything can be reviewed end to end without repository write access.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path

from agent_engine import perf
from agent_engine.phase4.settings import get_settings

from .trackers.base import TrackerError
from .trackers.github import github_http


@dataclass
class PrResult:
    repo: str
    branch: str
    url: str | None
    number: int | None
    local_path: str | None


def open_pr(repo: str, branch: str, files: dict[str, str], title: str, body: str, local_root: Path,
            base: str | None = None) -> PrResult:
    """Create or update branch + PR (idempotent: the same branch updates the open PR)."""
    mode = get_settings().phase4_pr_mode
    with perf.span("publish", "open_pr", mode=mode, files=len(files), operation="pull_request"):
        return _open_pr(repo, branch, files, title, body, local_root, base)


def _open_pr(repo: str, branch: str, files: dict[str, str], title: str, body: str, local_root: Path,
             base: str | None = None) -> PrResult:
    if get_settings().phase4_pr_mode != "github":
        root = local_root / repo.replace("/", "__") / branch.replace("/", "__")
        for path, content in files.items():
            p = root / "files" / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        (root / "PR.md").write_text(f"# {title}\n\nRepository: {repo}\nBranch: {branch}\n\n{body}\n", encoding="utf-8")
        return PrResult(repo, branch, None, None, str(root))
    http = github_http()
    r = f"/repos/{repo}"
    meta = http.get(r).json()
    base = base or meta["default_branch"]
    base_sha = http.get(f"{r}/git/ref/heads/{base}").json()["object"]["sha"]
    try:
        http.post(f"{r}/git/refs", json={"ref": f"refs/heads/{branch}", "sha": base_sha})
    except TrackerError as exc:
        if "Reference already exists" not in str(exc):
            raise
    for path, content in files.items():
        existing = None
        try:
            existing = http.get(f"{r}/contents/{path}", params={"ref": branch}).json().get("sha")
        except TrackerError:
            pass
        payload = {"message": f"phase4: {title} ({path})", "branch": branch,
                   "content": base64.b64encode(content.encode()).decode()}
        if existing:
            payload["sha"] = existing
        http.put(f"{r}/contents/{path}", json=payload)
    owner = repo.split("/")[0]
    prs = http.get(f"{r}/pulls", params={"head": f"{owner}:{branch}", "state": "open"}).json()
    if prs:
        pr = prs[0]
        http.patch(f"{r}/pulls/{pr['number']}", json={"body": body, "title": title})
    else:
        pr = http.post(f"{r}/pulls", json={"title": title, "head": branch, "base": base, "body": body}).json()
    return PrResult(repo, branch, pr["html_url"], pr["number"], None)
