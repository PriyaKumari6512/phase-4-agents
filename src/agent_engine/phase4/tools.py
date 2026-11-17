"""Phase 4 tools, registered in agent.TOOLS under the names a pack lists in `tools = [...]`.

Every tool takes `project` (the <project-name> in /outputs/<project-name>/), reads and writes only that project's
files, returns JSON text, and returns "ERROR: ..." instead of raising so the model can correct itself.
Validators get the read-only `*-check` sets.
"""

from __future__ import annotations

import logging
import json
import hashlib
from typing import Callable

from langchain_core.tools import tool

from agent_engine import perf
from agent_engine.phase4 import allocation, files, infra, sprint

logger = logging.getLogger(__name__)


def _run(name: str, fn: Callable[[], str]) -> str:
    from agent_engine.stage_controls import active_stage_budget
    if (budget := active_stage_budget.get()) is not None:
        budget.check()
    with perf.span("tool_exec", name, tool=name) as sp:
        try:
            result = fn()
        except files.ProjectError as e:
            result = f"ERROR: {e}"
            sp.set_status("domain_error", result, "project_error")
        except Exception as e:  # a tool bug must reach the model as text, not crash the run
            logger.exception("phase4 tool failed")
            result = f"ERROR: {type(e).__name__}: {e}"
            sp.set_status("domain_error", result, "tool_exception:" + perf.classify_error(e))
        original_chars = len(result)
        # Whitespace is not domain data. Keep every field and error, but avoid paying
        # for pretty-printing these JSON responses on every subsequent model turn.
        try:
            result = json.dumps(json.loads(result), ensure_ascii=False, separators=(",", ":"))
        except (ValueError, TypeError):
            pass
        sp.set(output_chars=len(result), original_output_chars=original_chars)
        return result


# ============================================================================ backlog (read-only)
@tool
def backlog_view(project: str, epic_id: str = "", level: str = "", item_ids: list[str] | None = None,
                 offset: int = 0, limit: int = 100, details: bool = True,
                 max_chars: int = 24000, expected_sha256: str = "") -> str:
    """Read exact backlog records scoped to one epic, level or item IDs. Paginated; never silently truncates.
    Use details=false for a compact planning index; details=true includes every field of selected items.
    Follow next_offset until null. max_chars bounds item payload (one oversized item is returned whole).
    expected_sha256 optionally rejects pages from a changed snapshot; restart pagination if it changes.
    This avoids repeatedly reading the complete backlog JSON for one feature's work."""
    def view():
        from agent_engine.phase4.contracts import Backlog
        selected_epic = epic_id
        # Hash exactly the bytes parsed, not a second read that may race enrichment.
        raw = files.path(project, files.BACKLOG).read_bytes()
        b = Backlog.model_validate_json(raw)
        if not 1000 <= max_chars <= 200000:
            raise files.ProjectError("max_chars must be between 1000 and 200000")
        if offset < 0 or not 1 <= limit <= 200 or level not in ("", "epic", "story", "task"):
            raise files.ProjectError("offset must be >=0, limit 1..200, level epic/story/task or empty")
        children = {i.item_id for i in b.items if i.parent_id == selected_epic}
        rows = [i for i in b.items if (not selected_epic or i.item_id == selected_epic or i.parent_id == selected_epic or i.parent_id in children)
                and (not level or i.level == level) and (not item_ids or i.item_id in item_ids)]
        digest = (hashlib.sha256(raw).hexdigest() if not (selected_epic or level or item_ids) else
                  hashlib.sha256(json.dumps([i.model_dump(mode="json") for i in rows],
                                             sort_keys=True).encode()).hexdigest())
        if expected_sha256 and expected_sha256 != digest:
            raise files.ProjectError("selected backlog records changed since the previous page; restart pagination")
        page = rows[offset:offset + limit]
        compact = ("item_id", "level", "parent_id", "title", "priority", "moscow", "estimate", "dependencies", "source_refs", "open_questions")
        selected, size = [], 2
        for item in page:
            value = item.model_dump(mode="json") if details else item.model_dump(mode="json", include=set(compact))
            length = len(json.dumps(value, ensure_ascii=False, separators=(",", ":"))) + 1
            if selected and size + length > max_chars:
                break
            selected.append(value)
            size += length
        end = offset + len(selected)
        return json.dumps({"backlog_sha256": digest, "total": len(rows),
                           "next_offset": end if end < len(rows) else None,
                           "oversized_item": size > max_chars, "items": selected})
    return _run("backlog_view", view)


@tool
def sprint_capacity(project: str, as_of: str = "") -> str:
    """Sprint windows for the planning horizon from phase4/project.json (calendar, holidays, PTO, allocation,
    ceremonies, maintenance reserve) and Monte Carlo capacity from phase4/history.json: P50 and P85 story points
    per sprint. Also lists stories that cannot be planned (unestimated, too large). as_of: YYYY-MM-DD, default
    today. Writes sprint/capacity.json."""
    return _run("sprint_capacity", lambda: sprint.capacity_report(project, as_of or None))


@tool
def sprint_solve(project: str, business_values: dict[str, int], pins: dict[str, int] | None = None,
                 relax: list[str] | None = None, as_of: str = "") -> str:
    """Plan sprints with the CP-SAT solver. business_values: {story_id: 1..10} (value to users/business; missing
    stories keep their previous value or 5). pins: {story_id: sprint_index, 0 = out of horizon} from the approver.
    relax: 'changes' strings of an infeasibility option the approver chose. The solver maximizes WSJF under
    capacity (P50 hard, above P85 penalized), dependencies, hard deadlines, must-haves and plan stability; when
    infeasible it returns the conflicting constraints and options it verified to be feasible. Writes
    sprint/sprint-plan.json and sprint-plan.md."""
    return _run("sprint_solve", lambda: sprint.solve(project, business_values, pins, relax, as_of or None))


@tool
def sprint_annotate(project: str, goals: dict[str, str], deferral_explanations: dict[str, str] | None = None,
                    summary_md: str = "") -> str:
    """Write a goal for every sprint with stories ({sprint_index: goal}), optional plain-language explanations for
    deferred stories ({story_id: text}), and a short summary for the approver. Updates sprint-plan.json and
    sprint-plan.md."""
    return _run("sprint_annotate", lambda: sprint.annotate(project, goals, deferral_explanations, summary_md))


@tool
def sprint_check(project: str) -> str:
    """Read-only: checks sprint/sprint-plan.json against the backlog (capacity, dependency order, every story
    planned or deferred, goals written, built from the current backlog)."""
    return _run("sprint_check", lambda: sprint.check(project))


# ============================================================================ allocation (Agent 3)
@tool
def allocation_prepare(project: str, sprint_index: int = 1) -> str:
    """Load one sprint of sprint/sprint-plan.json: its tasks, the hard rules for AI agents (acceptance criteria,
    at most 4 files, estimate within the agent limit, no sensitive area, no open questions, repository CI approved
    at gate P4-G4), team availability and skills, skill gaps and capacity shortfalls. ai_candidates are the tasks
    that need your eligibility verdict. Writes allocation/problem.json."""
    return _run("allocation_prepare", lambda: allocation.prepare(project, sprint_index))


@tool
def allocation_solve(project: str, sprint_index: int = 1, ai_verdicts: dict[str, dict] | None = None,
                     pins: dict[str, str] | None = None, vetoes: dict[str, list[str]] | None = None,
                     block_ai: list[str] | None = None) -> str:
    """Assign the sprint's tasks with the Timefold task-assigning solver (local CP-SAT when the service is down):
    required skills hard, capacity hard, code ownership affinity, priorities, balanced load; non-AI-eligible tasks
    only go to humans. ai_verdicts: {task_id: {"eligible": bool, "reason": str}} for the ai_candidates.
    pins {task_id: worker_id}, vetoes {task_id: [worker_ids]}, block_ai [task_ids] come from the approver.
    Writes allocation/assignments.json and assignments.md; returns each assignment with its score breakdown and
    runner-up."""
    return _run("allocation_solve", lambda: allocation.solve(project, sprint_index, ai_verdicts, pins, vetoes, block_ai))


@tool
def allocation_annotate(project: str, explanations: dict[str, str]) -> str:
    """Write one plain sentence per assigned task explaining the choice ({task_id: text}), from its score
    breakdown (skill fit, ownership, load, cost) and runner-up. Updates assignments.json and assignments.md."""
    return _run("allocation_annotate", lambda: allocation.annotate(project, explanations))


@tool
def allocation_check(project: str) -> str:
    """Read-only: checks allocation/assignments.json (built from the current sprint plan, every task assigned or
    explained as unassigned, AI only on eligible tasks, explanations present, capacity)."""
    return _run("allocation_check", lambda: allocation.check(project))


# ============================================================================ infra (Agent 4)
@tool
def infra_set_intent(project: str, intent: dict) -> str:
    """Record what the architecture needs: {cloud aws|azure|gcp, regions, environments [dev, stg, prod],
    deploy_target kubernetes|serverless|vm, slos {name: text}, monthly_budget_usd, notes, components: [{component_id,
    name, kind service|frontend|worker|database|cache|queue|object_storage|cdn|external_api|other, needs (from
    k8s_workload, public_endpoint, postgres, mysql, redis, queue, object_storage, container_registry, cdn, external),
    size_class small|medium|large, public_endpoint, exposes_http, data_classification public|internal|confidential|
    restricted, runtime, repo, depends_on [component_ids], secrets [extra secret env var names the component needs,
    e.g. EMAIL_PROVIDER_API_KEY; database/cache/queue URLs come from depends_on], source (where in
    architecture.md)}]}. A component that shares another component's image (same repo) gets no container_registry
    need of its own. Checks it against
    the catalog and org rules and writes infra/intent.json."""
    return _run("infra_set_intent", lambda: infra.set_intent(project, intent))


@tool
def infra_render(project: str) -> str:
    """Render the golden-path catalog for infra/intent.json into infra/repo/ (OpenTofu per environment, Argo CD,
    Helm values, ExternalSecrets, alerts, Atlantis, drift workflow, CODEOWNERS) and infra/ci/<owner>__<repo>/ (CI
    workflows per code repository). Overwrites earlier output. Writes infra/manifest.json and returns gaps."""
    return _run("infra_render", lambda: infra.render(project))


@tool
def infra_validate(project: str) -> str:
    """Run the IaC sandbox checks (tofu fmt/validate, tflint, trivy, checkov, actionlint, helm lint, kubeconform,
    gitleaks, conftest policy tests) on infra/repo and the CI workflows, scan for secret-like values, score risk,
    and write infra/checks.json, infra/manifest.json and infra/PR.md. Returns failing findings to repair."""
    return _run("infra_validate", lambda: infra.validate(project))


@tool
def infra_registry_versions(source: str) -> str:
    """Published versions of a Terraform registry module, newest first, e.g. source
    'terraform-aws-modules/eks/aws'. Read-only."""
    return _run("infra_registry_versions", lambda: infra.registry_versions(source))


@tool
def infra_check(project: str) -> str:
    """Read-only: checks infra/manifest.json against the files on disk and infra/checks.json (intent unchanged,
    files unchanged since validation, checks passed, PR.md present)."""
    return _run("infra_check", lambda: infra.check(project))


_ALL = [backlog_view, sprint_capacity, sprint_solve, sprint_annotate, sprint_check,
        allocation_prepare, allocation_solve, allocation_annotate, allocation_check, infra_set_intent, infra_render,
        infra_validate, infra_registry_versions, infra_check]
def _invalid_arguments(error: Exception) -> str:
    return f"ERROR: invalid arguments: {error}"


for _t in _ALL:
    # Wrong argument types are reported back to the model instead of aborting the whole run.
    _t.handle_validation_error = _invalid_arguments
    _t.handle_tool_error = True

TOOL_FACTORIES: dict[str, Callable[[], list]] = {
    "phase4-sprint": lambda: [backlog_view, sprint_capacity, sprint_solve, sprint_annotate],
    "phase4-sprint-check": lambda: [sprint_check],
    "phase4-allocation": lambda: [backlog_view, allocation_prepare, allocation_solve, allocation_annotate],
    "phase4-allocation-check": lambda: [allocation_check],
    "phase4-infra": lambda: [infra_set_intent, infra_render, infra_validate, infra_registry_versions],
    "phase4-infra-check": lambda: [infra_check, infra_registry_versions],
}
