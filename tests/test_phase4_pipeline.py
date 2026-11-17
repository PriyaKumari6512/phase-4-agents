"""Phase 4 tools end to end, without a model: the test plays the agents' judgement (the task breakdown of the
approved stories, business values, AI verdicts, intent) and checks the deterministic parts, the gates and publishing.
"""

import json
import shutil
from pathlib import Path

import pytest

from agent_engine import config, gates
from agent_engine.phase4 import allocation, backlog, files, infra, publish, sprint
from agent_engine.phase4.contracts import AssignmentPlan, Backlog, SprintPlan
from agent_engine.phase4.contracts import CheckResult

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "phase4" / "bookmarks"
EXAMPLE = ROOT / "examples" / "phase4" / "taskflow"
AS_OF = "2026-11-05"
P = "bm"
PO = {"name": "Priya", "role": "Product Owner"}
DEV = {"name": "Rahul"}


def mock_passed_checks(monkeypatch):
    """A unit-test fixture, not evidence that real external scanners ran."""
    from agent_engine.phase4 import sandbox
    monkeypatch.setattr(sandbox, "run_checks", lambda wd, envs, **kw: [
        CheckResult(tool=t, passed=True, outcome="passed", summary="mock scanner result")
        for t in sandbox.ALL_TOOLS if kw.get("only") is None or t in kw["only"]])


def seed_ci_evidence(project):
    from agent_engine.phase4.contracts import InfraManifest
    m = files.read_json(project, files.INFRA_MANIFEST, InfraManifest)
    files.write_json(project, "phase4/ci-readiness.json", {repo: {
        "success": True, "head_sha": "test-head", "workflow_run_ids": [1],
        "manifest_sha256": files.file_sha(project, files.INFRA_MANIFEST), "observed_at": files.utcnow().isoformat()}
        for repo in m.ci_repos})


@pytest.fixture
def proj(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setenv("PHASE4_ALLOCATION_SOLVER_MODE", "local")
    monkeypatch.setenv("PHASE4_IAC_SANDBOX_MODE", "off")
    monkeypatch.setenv("PHASE4_PR_MODE", "local")
    root = tmp_path / "outputs" / P
    shutil.copytree(FIXTURE, root)
    (root / "phase4").mkdir()
    for name in ("project.json", "history.json"):
        shutil.copy(EXAMPLE / "phase4" / name, root / "phase4" / name)
    from phase4_helpers import make_design_ready
    make_design_ready(root)
    return root


def approve(root: Path, gate: str) -> None:
    gates.record_decision(root, gates.load_gates()[gate], "approved", PO, DEV)


def built(project_root: Path) -> None:
    """The approved stories and their task breakdown (what Task Breakdown produces), without a model."""
    from phase4_helpers import build_story_backlog
    build_story_backlog(project_root)


def test_story_backlog_is_validated_with_coverage_waves_and_critical_path(proj):
    built(proj)
    report = json.loads(backlog.validate_report(P))
    assert report["ready_for_review"] and report["stories"] == 3 and report["tasks"] == 12
    b = files.read_json(P, files.BACKLOG, Backlog)
    assert b.coverage["FR-001"] == ["BM-2"] and b.critical_path == ["BM-2", "BM-3"]
    assert [d.on_id for d in b.by_id()["BM-3"].dependencies] == ["BM-2"]
    assert (proj / "backlog/backlog.md").read_text(encoding="utf-8").startswith("# Backlog v")


def test_a_legacy_backlog_must_be_rebuilt(proj):
    built(proj)
    doc = json.loads((proj / files.BACKLOG).read_text(encoding="utf-8"))
    doc["sources"] = {"prd.md": "x"}
    (proj / files.BACKLOG).write_text(json.dumps(doc), encoding="utf-8")
    _, issues = backlog.validate(P)
    assert [i.rule for i in issues] == ["legacy_backlog"]


def test_full_phase4_flow_through_gates_and_publishing(proj):
    # ---- Agent 1
    built(proj)
    assert json.loads(backlog.validate_report(P))["ready_for_review"]
    with pytest.raises(publish.PublishError, match="P4-G1 is not approved"):
        publish.publish_backlog(P)
    approve(proj, "P4-G1")
    # ---- Agent 2
    cap = json.loads(sprint.capacity_report(P, AS_OF))
    assert cap["sprints"][0]["capacity_p50"] > 0 and cap["unestimated_stories"] == []
    b = files.read_json(P, files.BACKLOG, Backlog)
    values = {s.item_id: (8 if s.moscow == "must" else 5) for s in b.stories()}
    plan = json.loads(sprint.solve(P, values, as_of=AS_OF))
    assert plan["solver"] in ("OPTIMAL", "FEASIBLE")
    assert not json.loads(sprint.check(P))["ok"]           # goals not written yet
    goals = {str(s["sprint_index"]): f"Users can do {s['sprint_index']}" for s in plan["sprints"] if s["stories"]}
    sprint.annotate(P, goals, {}, "Plan for review.")
    chk = json.loads(sprint.check(P))
    assert chk["ok"], chk["problems"]
    sp = files.read_json(P, files.SPRINT_PLAN, SprintPlan)
    placed = {sid: s.sprint_index for s in sp.sprints for sid in s.story_ids}
    by = b.by_id()
    for sid, k in placed.items():                           # dependency order holds
        for d in by[sid].dependencies:
            if d.on_id in placed:
                assert placed[d.on_id] <= k
    approve(proj, "P4-G2")
    # ---- Agent 3 (no infra approval yet: no repository is CI-ready, so nothing may go to AI)
    first = next(s.sprint_index for s in sp.sprints if s.story_ids)
    prep = json.loads(allocation.prepare(P, first))
    assert prep["ai_candidates"] == [] and prep["tasks"] > 0
    out = json.loads(allocation.solve(P, first))
    assert out["engine"] == "local_cpsat" and all(a["worker_kind"] == "human" for a in out["assignments"])
    allocation.annotate(P, {a["task_id"]: f"{a['worker']} has the skills." for a in out["assignments"]})
    chk = json.loads(allocation.check(P))
    assert chk["ok"], chk["problems"]
    ap = files.read_json(P, files.ASSIGNMENTS, AssignmentPlan)
    for w in ap.workers:                                    # capacity is a hard rule
        assert w["planned_hours"] <= w["capacity_hours"] + 0.05
    approve(proj, "P4-G3")
    # ---- publish (local tracker), twice: the second run creates nothing
    r1 = publish.publish_backlog(P)
    assert r1["created"] == len(b.items) and r1["links"] > 0
    r2 = publish.publish_backlog(P)
    assert r2["created"] == 0 and r2["updated_or_unchanged"] == len(b.items)
    s1 = publish.publish_sprint(P)
    assert s1["sprints"] >= 1 and s1["missing_in_tracker"] == []
    a1 = publish.publish_assignments(P)
    assert a1["assigned"] == len(ap.assignments)
    items = json.loads((proj / "tracker/items.json").read_text(encoding="utf-8"))
    assert sum(1 for i in items if i["assignee"]) == len(ap.assignments)
    assert publish.publish_assignments(P)["assigned"] == 0  # idempotent


def _intent():
    return {"cloud": "aws", "regions": ["us-east-1"], "environments": ["dev", "prod"], "deploy_target": "kubernetes",
            "slos": {"api_latency_p95": "300ms", "error_rate": "1%"}, "components": [
                {"component_id": "ARCH-001", "name": "taskflow-api", "kind": "service", "needs": ["k8s_workload", "container_registry"],
                 "exposes_http": True, "data_classification": "confidential", "runtime": "Python 3.12, FastAPI",
                 "repo": "acme/taskflow-api", "depends_on": ["ARCH-003", "ARCH-004"]},
                {"component_id": "ARCH-002", "name": "taskflow-web", "kind": "frontend",
                 "needs": ["k8s_workload", "container_registry", "public_endpoint"], "public_endpoint": True,
                 "exposes_http": True, "data_classification": "public", "runtime": "Node 22, React",
                 "repo": "acme/taskflow-web", "depends_on": ["ARCH-001"]},
                {"component_id": "ARCH-005", "name": "notify-worker", "kind": "worker", "needs": ["k8s_workload"],
                 "runtime": "Python 3.12", "repo": "acme/taskflow-api", "depends_on": ["ARCH-003"],
                 "secrets": ["EMAIL_PROVIDER_API_KEY"]},
                {"component_id": "ARCH-003", "name": "taskflow-db", "kind": "database", "needs": ["postgres"],
                 "data_classification": "confidential"},
                {"component_id": "ARCH-004", "name": "taskflow-cache", "kind": "cache", "needs": ["redis"]},
                {"component_id": "ARCH-006", "name": "jobs", "kind": "queue", "needs": ["queue"]}]}


def test_infra_intent_render_validate_publish_and_ci_readiness(proj, monkeypatch):
    bad = _intent()
    bad["components"][2]["public_endpoint"] = True
    bad["components"][2]["data_classification"] = "restricted"
    with pytest.raises(files.ProjectError, match="restricted data"):
        infra.set_intent(P, bad)
    infra.set_intent(P, _intent())
    r = json.loads(infra.render(P))
    assert r["ci_repos"] == ["acme/taskflow-api", "acme/taskflow-web"] and r["secrets_refs"] > 0
    for rel in ("infra/repo/envs/dev/core/main.tf", "infra/repo/envs/prod/core/main.tf", "infra/repo/atlantis.yaml",
                "infra/repo/gitops/apps/taskflow-api/dev/externalsecret.yaml",
                "infra/ci/acme__taskflow-api/.github/workflows/ci-taskflow-api.yml",
                "infra/ci/acme__taskflow-api/.github/workflows/phase4-claude.yml"):
        assert (proj / rel).is_file(), rel
    main_tf = (proj / "infra/repo/envs/dev/core/main.tf").read_text(encoding="utf-8")
    assert 'module "queue_jobs"' in main_tf and "terraform-aws-modules/sqs/aws" in main_tf
    # CI: one workflow per image, runtime version parsed from free text; the worker shares the API image
    api_ci = (proj / "infra/ci/acme__taskflow-api/.github/workflows/ci-taskflow-api.yml").read_text(encoding="utf-8")
    assert 'python-version: "3.12"' in api_ci
    assert 'node-version: "22"' in (proj / "infra/ci/acme__taskflow-web/.github/workflows/ci-taskflow-web.yml").read_text(encoding="utf-8")
    assert not (proj / "infra/ci/acme__taskflow-api/.github/workflows/ci-notify-worker.yml").exists()
    worker = (proj / "infra/repo/gitops/apps/notify-worker/prod/values.yaml").read_text(encoding="utf-8")
    assert "taskflow-api\"" in worker and "args:" in worker and "http: false" in worker and "ingress" not in worker
    web = (proj / "infra/repo/gitops/apps/taskflow-web/prod/values.yaml").read_text(encoding="utf-8")
    assert "ingress:\n  enabled: true" in web and "replicas: 2" in web
    assert "EMAIL_PROVIDER_API_KEY" in (proj / "infra/repo/gitops/apps/notify-worker/dev/externalsecret.yaml").read_text(encoding="utf-8")
    gaps = " ".join(r["gaps"])
    assert "start command" in gaps and "ingress.host" in gaps and "image promotion" in gaps
    v = json.loads(infra.validate(P))
    assert not v["checks_passed"] and len(v["skipped"]) == 10
    assert v["agent_edited"] == []                            # nothing edited yet (and no CRLF hash drift)
    # an agent repair is tracked in the manifest
    tf = proj / "infra/repo/envs/dev/core/main.tf"
    tf.write_text(tf.read_text(encoding="utf-8") + "\n# reviewed\n", encoding="utf-8")
    assert "repo/envs/dev/core/main.tf" in json.loads(infra.validate(P))["agent_edited"]
    assert not json.loads(infra.check(P))["ok"]
    assert "Risk score" in (proj / "infra/PR.md").read_text(encoding="utf-8")
    approve(proj, "P4-G4")
    with pytest.raises(publish.PublishError, match="not fully validated"):
        publish.publish_infra(P)
    mock_passed_checks(monkeypatch)
    assert json.loads(infra.validate(P))["checks_passed"]
    approve(proj, "P4-G4")
    prs = publish.publish_infra(P)["pull_requests"]
    assert {p["repo"] for p in prs} == {"acme/taskflow-infra", "acme/taskflow-api", "acme/taskflow-web"}
    assert all(Path(p["local_path"], "PR.md").is_file() for p in prs)
    assert allocation.ci_ready_repos(P) == set()  # generated/approved is not operational CI
    seed_ci_evidence(P)
    assert allocation.ci_ready_repos(P) == {"acme/taskflow-api", "acme/taskflow-web"}
    # changing an approved file makes the approval stale: CI is no longer considered ready
    (proj / "infra/intent.json").write_text((proj / "infra/intent.json").read_text(encoding="utf-8") + " ", encoding="utf-8")
    assert allocation.ci_ready_repos(P) == set()


def test_ai_agents_only_get_eligible_tasks_once_ci_is_operational(proj, monkeypatch):
    built(proj)
    b = files.read_json(P, files.BACKLOG, Backlog)
    small = [t for t in b.items if t.level == "task" and t.file_paths and len(t.file_paths) <= 4
             and t.estimate.hours <= 4
             and not any(w in f"{t.title} {' '.join(t.file_paths)}".lower() for w in allocation.RISKY)][:3]
    approve(proj, "P4-G1")
    vals = {s.item_id: 5 for s in b.stories()}
    sprint.solve(P, vals, as_of=AS_OF)
    infra.set_intent(P, _intent())
    infra.render(P)
    mock_passed_checks(monkeypatch)
    infra.validate(P)
    approve(proj, "P4-G4")
    seed_ci_evidence(P)
    sp = files.read_json(P, files.SPRINT_PLAN, SprintPlan)
    sprint_of = {sid: s.sprint_index for s in sp.sprints for sid in s.story_ids}
    k = sprint_of[small[0].parent_id]
    prep = json.loads(allocation.prepare(P, k))
    candidates = {c["task_id"] for c in prep["ai_candidates"]}
    assert small[0].item_id in candidates
    out = json.loads(allocation.solve(P, k, ai_verdicts={t: {"eligible": True, "reason": "local, tested change"}
                                                        for t in candidates}))
    ap = files.read_json(P, files.ASSIGNMENTS, AssignmentPlan)
    for a in ap.assignments:
        if a.worker_kind == "ai_agent":
            assert ap.eligibility[a.task_id].eligible
    assert {a["task_id"] for a in out["assignments"]} | {u["task_id"] for u in out["unassigned"]} >= candidates
