"""Read operational CI evidence and reconcile coding-agent outcomes. No dispatches."""
from __future__ import annotations

import re
from agent_engine import perf
from agent_engine.phase4 import files
from agent_engine.phase4.contracts import InfraManifest
from agent_engine.phase4.trackers.github import github_http


def check_ci(project: str) -> dict:
    manifest = files.read_json(project, files.INFRA_MANIFEST, InfraManifest)
    http = github_http()
    result = {}
    for repo in manifest.ci_repos:
        errors = []
        result[repo] = {"success": False, "head_sha": None, "workflow_run_ids": [],
                        "manifest_sha256": files.file_sha(project, files.INFRA_MANIFEST),
                        "observed_at": files.utcnow().isoformat(), "errors": errors}
        try:
            info = http.get(f"/repos/{repo}").json()
            branch = info["default_branch"]
            head = http.get(f"/repos/{repo}/commits/{branch}").json()["sha"]
        except Exception as exc:
            errors.append(perf.error_summary(exc))
            continue
        prefix = f"ci/{repo.replace('/', '__')}/.github/workflows/"
        paths = [f.path.removeprefix(prefix) for f in manifest.files if f.path.startswith(prefix)]
        successes, complete = [], bool(paths)
        for path in paths:
            try:
                workflow = http.get(f"/repos/{repo}/actions/workflows/{path}").json()
                if workflow.get("state") != "active":
                    complete = False
                if not path.startswith("ci-"):
                    continue  # dispatch workflow must exist; it needn't have run yet
                runs = http.get(f"/repos/{repo}/actions/workflows/{path}/runs", params={
                    "branch": branch, "event": "push", "head_sha": head, "status": "completed", "per_page": 100}).json()
                latest = next((r for r in runs.get("workflow_runs", []) if r.get("head_sha") == head), None)
                passing = latest if latest and latest.get("conclusion") == "success" else None
                if passing:
                    successes.append(passing["id"])
                else:
                    complete = False
                    errors.append(f"{path}: latest completed push run on the current head has not succeeded")
            except Exception as exc:
                complete = False
                errors.append(f"{path}: {perf.error_summary(exc)}")
        result[repo].update(success=complete and bool(successes), head_sha=head, workflow_run_ids=successes)
    http.close()
    files.write_json(project, "phase4/ci-readiness.json", result)
    return result


def reconcile(project: str) -> dict:
    from agent_engine.phase4 import dispatch
    from agent_engine.phase4.publish import ExternalIds
    from agent_engine.phase4.contracts import Backlog
    from agent_engine.phase4.settings import get_settings
    ids = ExternalIds(project)
    items = files.read_json(project, files.BACKLOG, Backlog).by_id()
    outcomes = files.read_json(project, files.AGENT_OUTCOMES) if files.exists(project, files.AGENT_OUTCOMES) else []
    by_task = {r.get("task_id"): r for r in outcomes if r.get("task_id")}
    statuses = {}
    for task_id, row in list(ids.data.get(ids.namespace("dispatch"), {}).items()):
        payload = dict(row.get("last_payload") or {})
        adapter = dispatch.adapter_for(payload["provider"], files.path(project, "publish/dispatch", write=True))
        state, pr = adapter.status(row["id"])
        merged = False
        if pr and get_settings().phase4_pr_mode == "github":
            match = re.fullmatch(r"https://github.com/([^/]+/[^/]+)/pull/(\d+)", pr)
            if match:
                http = github_http()
                try:
                    merged = bool(http.get(f"/repos/{match[1]}/pulls/{match[2]}").json().get("merged_at"))
                finally:
                    http.close()
        payload.update(status=state, pull_request=pr, merged=merged)
        ids.put("dispatch", task_id, row["id"], None, payload)
        statuses[task_id] = state
        if merged or state in ("failed", "cancelled", "timed_out"):
            by_task[task_id] = {"task_id": task_id, "provider": payload["provider"],
                                "task_type": items[task_id].type if task_id in items else "feature",
                                "outcome": "merged" if merged else state, "observed_at": files.utcnow().isoformat()}
    preserved = [r for r in outcomes if not r.get("task_id")]
    files.write_json(project, files.AGENT_OUTCOMES, [*preserved, *by_task.values()])
    return statuses
