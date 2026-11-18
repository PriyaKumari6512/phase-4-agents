"""Agent 4 (Infrastructure & Pipeline Setup): the deterministic parts around the agent's judgement.

  set_intent         the agent's reading of architecture.md (components, needs, sizes) -> checks -> infra/intent.json
  render             golden-path catalog templates (OpenTofu modules, Argo CD ApplicationSet, Helm values,
                     ExternalSecrets, PrometheusRules, Atlantis, drift workflow, CODEOWNERS, CI per code repo)
                     -> infra/repo/** + infra/ci/<owner>__<repo>/** + infra/manifest.json
  validate           tofu fmt/validate, tflint, trivy, checkov, actionlint, helm lint, kubeconform, gitleaks,
                     conftest in the IaC sandbox -> infra/checks.json, risk score, infra/PR.md
  registry_versions  published versions of a Terraform registry module (read-only)
  check              read-only consistency check for the validator

The agent may repair generated files with edit_file between render and validate; the manifest marks every file
whose content differs from what the catalog rendered as `agent_edited`, so reviewers see each change. Nothing here
applies infrastructure: Atlantis does, after a human approves the pull request.
"""

from __future__ import annotations

import json
import re
import shutil
from functools import lru_cache
from pathlib import Path

import httpx
import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from agent_engine import perf
from agent_engine.phase4 import files, sandbox
from agent_engine.phase4.contracts import (
    CheckResult,
    InfraIntent,
    InfraManifest,
    ManifestFile,
    ProjectSettings,
    SecretRef,
)
from agent_engine.phase4.settings import get_settings

ENV_CIDR = {"qa": "10.40.0.0/16", "dev": "10.10.0.0/16", "stg": "10.20.0.0/16", "prod": "10.30.0.0/16"}
# minimum replicas per size class and environment; autoscaling max = min x MAX_FACTOR
REPLICAS = {"small": {"qa": 1, "dev": 1, "stg": 1, "prod": 2}, "medium": {"qa": 1, "dev": 1, "stg": 2, "prod": 3},
            "large": {"qa": 2, "dev": 2, "stg": 2, "prod": 4}}
MAX_FACTOR = {"small": 2, "medium": 3, "large": 3}
RUNTIME_RE = re.compile(r"(python|node|java)[^0-9]*([0-9]+(?:\.[0-9]+)?)?", re.I)
DEPENDENCY_SECRET = {"database": "DATABASE_URL", "cache": "REDIS_URL", "queue": "QUEUE_URL"}
# deploy target -> the need a service/worker uses to run there. Other targets have no workload template.
WORKLOAD_NEED = {"kubernetes": "k8s_workload", "ecs_fargate": "ecs_service"}
WORKLOAD_NEEDS = set(WORKLOAD_NEED.values())
APP_PORT, HEALTH_PATH = 8080, "/healthz"
GITOPS_TOOLS = {"helm_lint", "kubeconform"}     # Kubernetes manifests only; nothing to check on ECS


def parse_runtime(runtime: str | None) -> tuple[str, str]:
    """'Python 3.12, FastAPI' -> ('python', '3.12'); 'node22' -> ('node', '22'); unknown -> ('', '')."""
    m = RUNTIME_RE.search(runtime or "")
    return (m.group(1).lower(), m.group(2) or "") if m else ("", "")


def image_owner(c, components) -> object | None:
    """The component whose container image `c` runs: itself if it has a registry, else the one in its repo that has."""
    if "container_registry" in c.needs:
        return c
    return next((o for o in components if o.repo and o.repo == c.repo and "container_registry" in o.needs), None)
ACTIONS = {"checkout": "actions/checkout@v6", "aws_credentials": "aws-actions/configure-aws-credentials@v6",
           "setup_opentofu": "opentofu/setup-opentofu@v2", "setup_python": "actions/setup-python@v5",
           "setup_node": "actions/setup-node@v4", "setup_java": "actions/setup-java@v4",
           "claude_code_action": "anthropics/claude-code-action@v1"}
TOFU_VERSION = "1.13.2"
PLATFORM_ROLES = ("devops", "platform", "sre")
SECRET_PATTERNS = [re.compile(p) for p in (
    r"AKIA[0-9A-Z]{16}", r"ASIA[0-9A-Z]{16}", r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    # a whole key named password/secret/token/api_key with a literal value (not envFromSecret, not ${var})
    r"(?i)\b(password|secret|token|api[_-]?key)\b\"?\s*[:=]\s*\"[^\"$\{]{6,}\"", r"sk-ant-[A-Za-z0-9_\-]{10,}",
    r"ghp_[A-Za-z0-9]{30,}", r"xox[abp]-[A-Za-z0-9-]{10,}")]


def catalog_dir() -> Path:
    return Path(get_settings().phase4_infra_catalog_dir)


@lru_cache
def _catalog(path: str) -> dict:
    return yaml.safe_load((Path(path) / "catalog.yaml").read_text(encoding="utf-8"))


def load_catalog() -> dict:
    return yaml.safe_load((catalog_dir() / "catalog.yaml").read_text(encoding="utf-8"))


def source_hashes(project):
    from agent_engine.perf_manifest import tree_digest
    return {files.ARCHITECTURE: files.file_sha(project, files.ARCHITECTURE),
            files.PROJECT_SETTINGS: files.file_sha(project, files.PROJECT_SETTINGS),
            "catalog": tree_digest(catalog_dir()).get("sha256", "missing")}


def _jinja() -> Environment:
    return Environment(loader=FileSystemLoader(str(catalog_dir() / "templates")), undefined=StrictUndefined,
                       keep_trailing_newline=True, trim_blocks=False)


def _entry(cloud: str, need: str) -> dict | None:
    for t in load_catalog()["templates"]:
        a = t["applies_to"]
        if a["need"] == need and a["cloud"] in (cloud, "any"):
            return t
    return None


def ident(name: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", name.lower()).strip("_") or "x"


def repo_dir_name(repo: str) -> str:
    return repo.replace("/", "__")


# ============================================================================ intent
def set_intent(project: str, intent: dict) -> str:
    try:
        it = InfraIntent.model_validate(intent)
    except Exception as e:
        raise files.ProjectError(f"intent does not match the schema: {e}") from e
    settings = files.read_json(project, files.PROJECT_SETTINGS, ProjectSettings)
    problems, warnings = [], []
    ids = [c.component_id for c in it.components]
    names = [ident(c.name) for c in it.components]
    if len(names) != len(set(names)):
        problems.append("component names collide after Terraform/Kubernetes normalization")
    if len(it.regions) != 1:
        problems.append("this catalog supports exactly one region; multiple regions require an explicit topology")
    architecture = files.read_text(project, files.ARCHITECTURE) if files.exists(project, files.ARCHITECTURE) else ""
    if it.deploy_target == "kubernetes" and any("k8s_workload" in c.needs for c in it.components) and re.search(r"\b(?:no|not|without)\s+kubernetes\b", architecture, re.I):
        problems.append("architecture explicitly excludes Kubernetes; do not substitute EKS for an unsupported managed-container target")
    if len(set(ids)) != len(ids):
        problems.append("component_id values must be unique")
    for c in it.components:
        for d in c.depends_on:
            if d not in ids:
                problems.append(f"{c.component_id} depends on unknown component {d}")
        if c.data_classification == "restricted" and c.public_endpoint:
            problems.append(f"{c.name} handles restricted data and must not have a public endpoint")
        if c.kind == "database" and not ({"postgres", "mysql"} & set(c.needs)):
            problems.append(f"{c.name} is a database but needs neither postgres nor mysql")
        for target, need in WORKLOAD_NEED.items():
            if need in c.needs and it.deploy_target != target:
                problems.append(f"{c.name} needs {need} but deploy_target is {it.deploy_target}")
        if "cdn" in c.needs and "object_storage" not in c.needs:
            problems.append(f"{c.name} needs cdn: this catalog serves static sites from the component's own "
                            "bucket, so it also needs object_storage")
        if c.public_endpoint and "public_endpoint" not in c.needs:
            warnings.append(f"{c.name}: public_endpoint is true but 'public_endpoint' is not in needs")
        if c.repo and settings.code_repos and c.repo not in settings.code_repos:
            warnings.append(f"{c.name}: repo {c.repo} is not in phase4/project.json code_repos")
        for need in c.needs:
            if need not in ("public_endpoint", "external", "k8s_workload") and _entry(it.cloud, need) is None:
                warnings.append(f"{c.name}: no catalog template for '{need}' on {it.cloud}; it will be listed as a gap")
    allowed = set(load_catalog()["defaults"]["allowed_regions"])
    for r in it.regions:
        if r not in allowed:
            problems.append(f"region {r} is not on the org allow-list {sorted(allowed)}")
    # Hosting the catalog does not cover is a gap report for the platform team, not a failure: the intent is kept,
    # everything the catalog does cover is generated, and the rest is listed in manifest.json gaps.
    if it.cloud != "aws":
        warnings.append(f"cloud {it.cloud}: this catalog only implements AWS; no substitute topology is generated "
                        "(reported as a gap)")
    if it.deploy_target not in WORKLOAD_NEED and any(c.kind in ("service", "worker") for c in it.components):
        warnings.append(f"deploy_target {it.deploy_target} has no workload template in this catalog; its services "
                        "and workers are reported as gaps")
    workload = WORKLOAD_NEED.get(it.deploy_target)
    for c in it.components:
        if workload and c.kind in ("service", "worker") and workload not in c.needs:
            warnings.append(f"{c.name}: a {c.kind} on {it.deploy_target} normally needs {workload}; "
                            "without it nothing runs it")
    if problems:
        raise files.ProjectError("intent rejected: " + "; ".join(problems))
    files.write_json(project, files.INFRA_INTENT, it)
    return json.dumps({"written": files.virtual(project, files.INFRA_INTENT), "components": len(it.components),
                       "warnings": warnings})


# ============================================================================ render
class _Out:
    def __init__(self) -> None:
        self.files: dict[str, str] = {}
        self.origins: dict[str, tuple[str, str | None]] = {}
        self.secrets: list[SecretRef] = []
        self.gaps: list[str] = []
        self.stateful: list[str] = []
        self.modules: dict[str, dict] = {}     # catalog entry id -> its module pin, for every module rendered

    def add(self, path: str, content: str, origin: str, template: str | None) -> None:
        self.files[path] = content
        self.origins[path] = (origin, template)


def _slo_error_rate(slos: dict[str, str]) -> float:
    for k, v in slos.items():
        if "error" in k.lower():
            m = re.search(r"([\d.]+)\s*%", v)
            if m:
                return round(float(m.group(1)) / 100, 4)
    return 0.01


def _slo_p95(slos: dict[str, str]) -> float:
    for k, v in slos.items():
        if "latency" in k.lower() or "p95" in k.lower():
            m = re.search(r"([\d.]+)\s*(ms|s)", v)
            if m:
                return round(float(m.group(1)) / (1000 if m.group(2) == "ms" else 1), 3)
    return 0.5


def _render_env(out: _Out, project: str, settings: ProjectSettings, it: InfraIntent, env: str) -> None:
    j = _jinja()
    cat = load_catalog()
    region = it.regions[0]
    size_of = {c.component_id: cat["size_classes"][c.size_class] for c in it.components}
    largest = max((c.size_class for c in it.components), key=["small", "medium", "large"].index, default="small")
    blocks = [j.get_template("terraform/aws/base.tf.j2").render(
        project=project, environment=env, region=region, owner=settings.project_name,
        vpc_cidr=ENV_CIDR.get(env, "10.40.0.0/16"), state_bucket=f"{project}-tfstate")]
    ecs = [c for c in it.components if "ecs_service" in c.needs] if it.deploy_target == "ecs_fargate" else []
    # API services first so their /api/* rule wins over a public frontend's catch-all.
    public_ecs = sorted((c for c in ecs if c.public_endpoint and c.exposes_http), key=lambda c: c.kind != "service")
    core = ["network"]
    if it.deploy_target == "kubernetes" and any("k8s_workload" in c.needs for c in it.components):
        core.append("k8s_cluster")
    if ecs:
        core.append("ecs_cluster")
    for need in core:
        e = _entry("aws", need)
        blocks.append(j.get_template(e["template"]).render(module=e["module"], size=cat["size_classes"][largest]))
        out.modules[e["id"]] = e["module"]
    cdn = _entry("aws", "cdn")
    if cdn and cdn.get("edge_template") and any("cdn" in c.needs for c in it.components):
        blocks.append(j.get_template(cdn["edge_template"]).render())
    if public_ecs:
        e = _entry("aws", "load_balancer")
        blocks.append(j.get_template(e["template"]).render(module=e["module"], services=[
            {"name": ident(c.name), "prefix": ident(c.name).replace("_", "")[:5] or "app", "port": APP_PORT,
             "health": HEALTH_PATH, "path": _route(c)}
            for c in public_ecs]))
        out.modules[e["id"]] = e["module"]
        if env == it.environments[0]:
            out.gaps.append("public services: set certificate_arn (ACM, HTTPS listener) per environment and point DNS at "
                            "the load balancer; listener rules route " + ", ".join(
                                f"{_route(c)} to {c.name}" for c in public_ecs) + " - adjust if the API uses other paths")
    for c in it.components:
        name = ident(c.name)
        for need in c.needs:
            if need in ("k8s_workload", "ecs_service", "public_endpoint", "external"):
                continue
            if need == "container_registry" and env != it.environments[0]:
                continue  # shared registry has one state owner, not one conflicting owner per environment
            e = _entry("aws", need)
            if e is None:
                out.gaps.append(f"{c.name}: no catalog template for '{need}' (left for human follow-up)")
                continue
            if "module" not in e and not e["template"].startswith("terraform/"):
                continue  # rendered outside Terraform (Kubernetes manifests)
            blocks.append(j.get_template(e["template"]).render(module=e.get("module"), size=size_of[c.component_id],
                                                                 name=name, component=ident(c.name).replace("_", "-"), db_name=name[:60]))
            if "module" in e:
                out.modules[e["id"]] = e["module"]
            if e.get("stateful"):
                out.stateful.append(f"{env}:{e['id']}:{c.name}")
            if need == "cdn" and env == it.environments[0]:
                out.gaps.append(f"{c.name}: static site on CloudFront; the workflow that uploads its build to the bucket "
                                "and invalidates the CDN is not generated, and custom DNS/certificate are not set")
    if ecs:
        blocks += _render_ecs(out, project, it, env, ecs, size_of)
    out.add(f"envs/{env}/core/main.tf", "\n".join(blocks), "module_call", "aws-core")
    if it.deploy_target != "kubernetes":
        return
    repo_url = f"https://github.com/{settings.infra_repo}.git" if settings.infra_repo else "REPLACE_WITH_INFRA_REPO_URL"
    out.add(f"gitops/applicationsets/{project}-{env}.yaml",
            j.get_template("gitops/applicationset.yaml.j2").render(project=project, environment=env, repo_url=repo_url),
            "template", "k8s-workload")
    out.add(f"gitops/applicationsets/{project}-{env}-platform.yaml",
            j.get_template("gitops/platform-application.yaml.j2").render(project=project, environment=env, repo_url=repo_url),
            "template", "observability")
    out.add(f"gitops/platform/{env}/access.yaml", j.get_template("gitops/access.yaml.j2").render(
        project=project, environment=env), "template", "access")
    out.add(f"gitops/platform/{env}/clustersecretstore.yaml",
            j.get_template("gitops/clustersecretstore.yaml.j2").render(region=region), "template", "external-secrets")
    by_id = {c.component_id: c for c in it.components}
    for c in it.components:
        if "k8s_workload" not in c.needs:
            continue
        name = ident(c.name).replace("_", "-")
        keys = [DEPENDENCY_SECRET[by_id[d].kind] for d in c.depends_on if d in by_id and by_id[d].kind in DEPENDENCY_SECRET]
        keys += [k for k in c.secrets if k not in keys]
        secrets = [SecretRef(name=k, store="aws_secrets_manager", path=f"/{project}/{env}/{name}/{k}") for k in keys]
        secret_name = f"{name}-env" if secrets else ""
        out.secrets += secrets
        owner = image_owner(c, it.components)
        if owner is None:
            out.gaps.append(f"{c.name}: no component in its repository builds a container image "
                            "(add container_registry to its needs)")
        image = ident((owner or c).name).replace("_", "-")
        shares_image = owner is not None and owner is not c
        if shares_image and env == it.environments[0]:
            out.gaps.append(f"{c.name} runs the {image} image: set its start command in "
                            f"gitops/apps/{name}/<env>/values.yaml (args)")
        if c.public_endpoint and env == it.environments[0]:
            out.gaps.append(f"{c.name} is public: set ingress.host and ingress.certificateArn in "
                            f"gitops/apps/{name}/<env>/values.yaml; the AWS Load Balancer Controller and DNS come "
                            "from the platform bootstrap")
        replicas = REPLICAS[c.size_class][env]
        out.add(f"gitops/apps/{name}/{env}/values.yaml",
                j.get_template("gitops/app-values.yaml.j2").render(
                    component=name, environment=env, image_repository=f"ECR_REGISTRY/{project}/{image}",
                    image_name=image, args='["TODO-start-command"]' if shares_image else "",
                    replicas=replicas, max_replicas=replicas * MAX_FACTOR[c.size_class], http=c.exposes_http,
                    public=c.public_endpoint and c.exposes_http, secret_name=secret_name), "template", "k8s-workload")
        if secrets:
            out.add(f"gitops/apps/{name}/{env}/externalsecret.yaml",
                    j.get_template("gitops/externalsecret.yaml.j2").render(
                        secret_name=secret_name, project=project, environment=env, secrets=secrets),
                    "template", "external-secrets")
        out.add(f"gitops/platform/{env}/alerts/{name}.yaml",
                j.get_template("gitops/prometheusrule.yaml.j2").render(
                    component=name, project=project, environment=env,
                    alert_prefix="".join(p.capitalize() for p in name.split("-")), http=c.exposes_http,
                    error_rate=_slo_error_rate(it.slos), p95_seconds=_slo_p95(it.slos)), "template", "observability")


def _route(c) -> str:
    return "/api/*" if c.kind == "service" else "/*"


def _render_ecs(out: _Out, project: str, it: InfraIntent, env: str, ecs: list, size_of: dict) -> list[str]:
    """ECS Fargate services and the env's image digest file (the only file promotion changes)."""
    j, e = _jinja(), _entry("aws", "ecs_service")
    by_id = {c.component_id: c for c in it.components}
    blocks, digests = [], {}
    for c in ecs:
        name, component = ident(c.name), ident(c.name).replace("_", "-")
        keys = [DEPENDENCY_SECRET[by_id[d].kind] for d in c.depends_on if d in by_id and by_id[d].kind in DEPENDENCY_SECRET]
        keys += [k for k in c.secrets if k not in keys]
        secrets = [SecretRef(name=k, store="aws_secrets_manager", path=f"/{project}/{env}/{component}/{k}") for k in keys]
        out.secrets += secrets
        owner = image_owner(c, it.components)
        if owner is None:
            out.gaps.append(f"{c.name}: no component in its repository builds a container image "
                            "(add container_registry to its needs)")
        image = ident((owner or c).name).replace("_", "-")
        digests[image] = "sha256:" + "0" * 64
        shares_image = owner is not None and owner is not c
        if shares_image and env == it.environments[0]:
            out.gaps.append(f"{c.name} runs the {image} image: set its command in envs/<env>/core/main.tf (module svc_{name})")
        replicas = REPLICAS[c.size_class][env]
        size = size_of[c.component_id]
        blocks.append(j.get_template(e["template"]).render(
            module=e["module"], name=name, component=component, image=image,
            command='["TODO-start-command"]' if shares_image else "", cpu=size["task_cpu"], memory=size["task_memory"],
            replicas=replicas, max_replicas=replicas * MAX_FACTOR[c.size_class], http=c.exposes_http,
            public=c.public_endpoint and c.exposes_http, port=APP_PORT,
            secrets=[{"key": s.name, "path": s.path} for s in secrets],
            error_rate=_slo_error_rate(it.slos), p95_seconds=_slo_p95(it.slos)))
        out.modules[e["id"]] = e["module"]
    out.add(f"envs/{env}/core/images.auto.tfvars.json", json.dumps({"image_digests": digests}, indent=2) + "\n",
            "generated", "promotion")
    return blocks


def accepted_checkov_risks() -> list[str]:
    accepted = catalog_dir() / "templates" / "repo" / "checkov.yaml"
    if not accepted.is_file():
        return []
    return [str(x) for x in (yaml.safe_load(accepted.read_text(encoding="utf-8")) or {}).get("skip-check", [])]


def render(project: str) -> str:
    """Re-renders everything from intent.json. Overwrites infra/repo and infra/ci (agent edits there are lost)."""
    settings = files.read_json(project, files.PROJECT_SETTINGS, ProjectSettings)
    it = files.read_json(project, files.INFRA_INTENT, InfraIntent)
    j = _jinja()
    out = _Out()
    if it.cloud != "aws":
        out.gaps.append(f"cloud {it.cloud}: the catalog only has AWS entries; infrastructure not generated")
    else:
        out.gaps.append(f"bootstrap: create the remote state bucket '{project}-tfstate' (versioned, encrypted) once per account")
        for env in it.environments:
            with perf.span("compute", "infra.render_env", env=env, components=len(it.components)):
                _render_env(out, project, settings, it, env)
        kubernetes = it.deploy_target == "kubernetes"
        if it.deploy_target not in WORKLOAD_NEED:
            for c in it.components:
                if c.kind in ("service", "worker"):
                    out.gaps.append(f"{c.name}: hosting target '{it.deploy_target}' is not in the catalog; nothing "
                                    "runs this workload. Provision it by hand or add a catalog template.")
        if kubernetes:
            chart_dir = catalog_dir() / "templates" / "gitops" / "chart"
            for p in sorted(chart_dir.rglob("*")):
                if p.is_file():
                    out.add(f"gitops/charts/app/{p.relative_to(chart_dir).as_posix()}", p.read_text(encoding="utf-8"),
                            "template", "k8s-workload")
            out.gaps.append(f"bootstrap: register Argo CD clusters named {', '.join(project + '-' + e for e in it.environments)}; install platform CRDs before syncing platform applications")
        else:
            out.gaps.append("alarms: connect the generated CloudWatch alarms to the team's on-call SNS topic (alarm_actions)")
        out.gaps.append(f"shared container registries are owned only by {it.environments[0]}/core state; apply that state before image builds for other environments")
        owners = [m.github_login for m in settings.team if m.github_login and m.role.lower() in PLATFORM_ROLES]
        out.add(".trivyignore", (catalog_dir() / "templates" / "repo" / "trivyignore").read_text(encoding="utf-8"),
                "template", None)
        accepted = catalog_dir() / "templates" / "repo" / "checkov.yaml"
        if accepted.is_file():  # platform-owned accepted checkov risks; none in the default catalog
            out.add(".checkov.yaml", accepted.read_text(encoding="utf-8"), "template", "accepted-risks")
            out.gaps.append("checkov: the catalog accepts these checks as known risks (.checkov.yaml skip-check); "
                            "review the list and its justification: " + ", ".join(accepted_checkov_risks()))
        out.add("atlantis.yaml", j.get_template("repo/atlantis.yaml.j2").render(
            project=project, environments=it.environments), "template", None)
        out.add(".github/workflows/drift.yml", j.get_template("repo/drift.yml.j2").render(
            environments=it.environments, actions=ACTIONS, tofu_version=TOFU_VERSION, region=it.regions[0]),
            "template", None)
        for document in ("RUNBOOK", "BRANCHING"):
            out.add(f"docs/{document}.md", j.get_template(f"repo/{document}.md.j2").render(
                project=project, environments=it.environments, kubernetes=kubernetes), "template", document.lower())
        out.add("CODEOWNERS", j.get_template("repo/CODEOWNERS.j2").render(
            platform_team=" @".join(owners) if owners else "platform-team",
            prod_approvers=" @".join(owners[1:] or owners) if owners else "prod-approvers"), "template", None)
        if not owners:
            out.gaps.append("CODEOWNERS: nobody in phase4/project.json has role devops/platform/sre; replace the "
                            "@platform-team placeholders")
        if kubernetes:
            out.gaps.append("platform add-ons (external-secrets operator, kube-prometheus-stack, OpenTelemetry Collector) "
                            "are installed by the platform team's cluster bootstrap; their chart versions are not pinned here")
        for mod in out.modules.values():
            if not mod.get("verified"):
                out.gaps.append(f"module {mod['source']} {mod['version']} is a version range, not a verified pin; "
                                "confirm it with infra_registry_versions")
        for name in ("promote.py", "verify-build.py", "verify-protection.py"):
            out.add(f"scripts/{name}", (catalog_dir() / "templates/repo" / name).read_text(), "template", "promotion")
        out.add(".github/workflows/promote.yml", (catalog_dir() / "templates/repo/promote.yml").read_text(), "template", "promotion")
        images = {}
        repositories = {}
        for component in it.components:
            owner = image_owner(component, it.components)
            if WORKLOAD_NEEDS & set(component.needs) and owner:
                name = ident(owner.name).replace("_", "-")
                images.setdefault(name, []).append(ident(component.name).replace("_", "-"))
                repositories[name] = owner.repo
        out.add("promotion.json", json.dumps({"deploy_target": it.deploy_target, "environments": it.environments, "images": images,
                                               "repositories": repositories}, indent=2), "generated", "promotion")
        out.gaps.append("Configure GitHub Environments: QA Lead for qa; client sign-off for stg; go/no-go plus DevOps Lead for prod. Enforce protected main and required PR reviews. Configure the GitOps GitHub App; bootstrap digest placeholders cannot be deployed.")
    # CI per code repo: one workflow per container image (+ Claude Code dispatch workflow when that agent is enabled)
    claude = any(a.provider == "claude_code_action" and a.enabled for a in settings.ai_agents)
    ci: dict[str, dict[str, str]] = {}
    for c in it.components:
        if c.kind not in ("service", "frontend", "worker") or not c.repo or image_owner(c, it.components) is not c:
            continue
        name = ident(c.name).replace("_", "-")
        lang, version = parse_runtime(c.runtime)
        if not lang:
            out.gaps.append(f"{c.name}: runtime {c.runtime!r} has no standard CI template; its workflow fails until "
                            "build steps are added")
        repo_files = ci.setdefault(c.repo, {})
        repo_files[f".github/workflows/ci-{name}.yml"] = j.get_template("repo/ci.yml.j2").render(
            component=name, runtime=c.runtime or "unknown", runtime_lang=lang, runtime_version=version,
            actions=ACTIONS, region=it.regions[0], project=project, reusable_workflow=None)
        repo_files[".github/workflows/promote-dev.yml"] = (catalog_dir() / "templates/repo/notify.yml").read_text().replace("__INFRA_REPO__", settings.infra_repo)
        if claude:
            repo_files[".github/workflows/phase4-claude.yml"] = j.get_template("repo/phase4-claude.yml.j2").render(
                actions=ACTIONS)
    write_span = perf.span("fs", "infra.write_rendered_files", files=len(out.files) + sum(len(v) for v in ci.values()),
                           bytes=sum(len(c) for c in out.files.values()))
    with write_span:
        manifest_files = _write_rendered(project, out, ci)
    manifest = InfraManifest(project=project, intent_sha256=files.file_sha(project, files.INFRA_INTENT), source_hashes=source_hashes(project),
                             infra_repo=settings.infra_repo, environments=it.environments, files=manifest_files,
                             ci_repos=sorted(ci), secrets_refs=out.secrets, stateful_resources=out.stateful,
                             gaps=list(dict.fromkeys(out.gaps)), generated_at=files.utcnow())
    files.write_json(project, files.INFRA_MANIFEST, manifest)
    return json.dumps({"written": files.virtual(project, files.INFRA_MANIFEST), "files": len(manifest_files),
                       "infra_repo_dir": files.virtual(project, files.INFRA_REPO_DIR),
                       "ci_repos": sorted(ci), "secrets_refs": len(out.secrets), "gaps": manifest.gaps,
                       "next": "call infra_validate; repair failing files with edit_file, then validate again"})


def _write_rendered(project: str, out: _Out, ci: dict[str, dict[str, str]]) -> list[ManifestFile]:
    root = files.path(project, "infra", write=True)
    for sub in ("repo", "ci"):
        shutil.rmtree(root / sub, ignore_errors=True)
    manifest_files = []
    for rel, content in sorted(out.files.items()):
        files.write_text(project, f"{files.INFRA_REPO_DIR}/{rel}", content)
        origin, tmpl = out.origins[rel]
        sha = files.sha256_text(content)
        manifest_files.append(ManifestFile(path=f"repo/{rel}", sha256=sha, origin=origin, template_ref=tmpl,
                                           rendered_sha256=sha))
    for repo, rf in sorted(ci.items()):
        for rel, content in sorted(rf.items()):
            files.write_text(project, f"{files.INFRA_CI_DIR}/{repo_dir_name(repo)}/{rel}", content)
            sha = files.sha256_text(content)
            manifest_files.append(ManifestFile(path=f"ci/{repo_dir_name(repo)}/{rel}", sha256=sha, origin="template",
                                               template_ref="ci", rendered_sha256=sha))
    return manifest_files


# ============================================================================ validate
def _refresh_manifest(project: str, manifest: InfraManifest) -> list[str]:
    """Re-hashes files on disk; marks agent edits; returns files that disappeared."""
    gone = []
    for f in manifest.files:
        p = files.path(project, f"infra/{f.path}")
        if not p.is_file():
            gone.append(f.path)
            continue
        f.sha256 = files.sha256_file(p)
        if f.sha256 != f.rendered_sha256:
            f.origin = "agent_edited"
    return gone


def _risk(manifest: InfraManifest, checks: list[CheckResult], it: InfraIntent) -> tuple[int, list[str]]:
    score, why = 0, []
    if manifest.stateful_resources:
        score += 25
        why.append(f"{len(manifest.stateful_resources)} stateful resources (databases, caches, buckets)")
    public = [c.name for c in it.components if c.public_endpoint]
    if public:
        score += 15
        why.append(f"public endpoints: {', '.join(public)}")
    if "prod" in it.environments:
        score += 10
        why.append("includes prod")
    failed = [c.tool for c in checks if not c.passed and not c.skipped]
    skipped = [c.tool for c in checks if c.skipped]
    if failed:
        score += 30
        why.append(f"failing checks: {', '.join(failed)}")
    if skipped:
        score += 10
        why.append(f"checks not run here: {', '.join(skipped)}")
    edited = [f.path for f in manifest.files if f.origin == "agent_edited"]
    if edited:
        score += 10
        why.append(f"{len(edited)} files edited by the agent after rendering")
    return min(100, score), why


def validate(project: str) -> str:
    manifest = files.read_json(project, files.INFRA_MANIFEST, InfraManifest)
    if manifest.source_hashes != source_hashes(project):
        raise files.ProjectError("infrastructure source inputs/catalog changed or lack provenance; re-render before validation")
    it = files.read_json(project, files.INFRA_INTENT, InfraIntent)
    with perf.span("fs", "infra.refresh_manifest_hashes", files=len(manifest.files)):
        gone = _refresh_manifest(project, manifest)
    workdir = files.path(project, files.INFRA_REPO_DIR)
    only = None if it.deploy_target == "kubernetes" else set(sandbox.ALL_TOOLS) - GITOPS_TOOLS
    checks = sandbox.run_checks(workdir, list(it.environments), only=only) if workdir.is_dir() else []
    ci_root = files.path(project, files.INFRA_CI_DIR)
    ci_findings = []
    ci_incomplete = []
    if ci_root.is_dir():
        for repo_dir in sorted(p for p in ci_root.iterdir() if p.is_dir()):
            with perf.span("phase", "infra.ci_repo_checks"):
                ci_results = sandbox.run_checks(repo_dir, [], include_init=False, only={"actionlint"})
            for res in ci_results:
                if not res.passed and not res.skipped:
                    ci_findings += res.findings
            ci_incomplete += [f"ci/{repo_dir.name} {x}" for x in sandbox.incomplete(ci_results)]
    if ci_findings:
        for c in checks:
            if c.tool == "actionlint":
                c.passed, c.findings, c.summary = False, c.findings + ci_findings, "errors in CI workflows"
    with perf.span("compute", "infra.secret_scan", files=len(manifest.files)) as sp:
        secret_hits = []
        for f in manifest.files:
            p = files.path(project, f"infra/{f.path}")
            if p.is_file():
                text = p.read_text(encoding="utf-8", errors="replace")
                if any(pat.search(text) for pat in SECRET_PATTERNS):
                    secret_hits.append(f.path)
        sp.set(hits=len(secret_hits))
    files.write_json(project, files.INFRA_CHECKS, [c.model_dump(mode="json") for c in checks])
    manifest.checks_passed = not deployment_problems(project, manifest) and bool(checks) and all(c.passed and not c.skipped for c in checks) and not ci_incomplete and not secret_hits and not gone
    manifest.checks_skipped = [c.tool for c in checks if c.skipped]
    manifest.checks_incomplete = sandbox.incomplete(checks) + ci_incomplete
    manifest.validation_complete = bool(checks) and not manifest.checks_incomplete
    manifest.risk_score, manifest.risk_reasons = _risk(manifest, checks, it)
    if secret_hits:
        manifest.risk_reasons.append(f"secret-like values in: {', '.join(secret_hits)}")
    with perf.span("fs", "infra.write_reports") as sp:
        files.write_json(project, files.INFRA_MANIFEST, manifest)
        files.write_text(project, files.INFRA_PR, render_pr(project, manifest, checks, it))
        sp.set(checks_passed=manifest.checks_passed, validation_complete=manifest.validation_complete,
               incomplete=len(manifest.checks_incomplete), risk_score=manifest.risk_score)
    failing = [c for c in checks if not c.passed and not c.skipped]
    return json.dumps({
        "checks_passed": manifest.checks_passed, "risk_score": manifest.risk_score,
        "validation_complete": manifest.validation_complete, "incomplete": manifest.checks_incomplete,
        "failing": [{"tool": c.tool, "summary": c.summary, "findings": [x.model_dump() for x in c.findings[:15]]}
                    for c in failing],
        "skipped": manifest.checks_skipped, "secret_like_values": secret_hits, "missing_files": gone,
        "agent_edited": [f.path for f in manifest.files if f.origin == "agent_edited"],
        "written": [files.virtual(project, files.INFRA_CHECKS), files.virtual(project, files.INFRA_MANIFEST),
                    files.virtual(project, files.INFRA_PR)]})


def render_pr(project: str, m: InfraManifest, checks: list[CheckResult], it: InfraIntent) -> str:
    lines = [f"# Infrastructure for {project}: {', '.join(m.environments)}", "",
             f"Generated by PDLC Phase 4 from `architecture.md` through `infra/intent.json` and the golden-path "
             f"catalog. Target repo: `{m.infra_repo or '(set infra_repo in phase4/project.json)'}`. Nothing is applied "
             "until this PR is merged and Atlantis applies it per environment.", "",
             f"**Risk score: {m.risk_score}/100**" + (f" — {'; '.join(m.risk_reasons)}" if m.risk_reasons else ""), "",
             "## Components", "", "| Component | Kind | Needs | Size | Public | Repo |", "|---|---|---|---|---|---|"]
    lines += [f"| {c.name} | {c.kind} | {', '.join(c.needs)} | {c.size_class} | {'yes' if c.public_endpoint else 'no'} "
              f"| {c.repo or '-'} |" for c in it.components]
    lines += ["", "## Checks", "", "| Tool | Result | Summary |", "|---|---|---|"]
    lines += [f"| {c.tool} | {'skipped' if c.skipped else ('pass' if c.passed else 'FAIL')} | {c.summary} |" for c in checks]
    if files.exists(project, f"{files.INFRA_REPO_DIR}/.checkov.yaml"):
        lines += ["", "## Accepted checkov risks (catalog .checkov.yaml)", "",
                  "These checks are skipped by the platform's accepted-risk list; each needs a recorded justification.", ""]
        lines += [f"- `{c}`" for c in accepted_checkov_risks()]
    if m.secrets_refs:
        lines += ["", "## Secrets to create (references only, never values)", ""]
        lines += [f"- `{s.name}` in {s.store} at `{s.path}`" for s in m.secrets_refs]
    if m.stateful_resources:
        lines += ["", "## Stateful resources", ""] + [f"- {s}" for s in m.stateful_resources]
    edited = [f.path for f in m.files if f.origin == "agent_edited"]
    if edited:
        lines += ["", "## Files changed by the agent after rendering", ""] + [f"- `{p}`" for p in edited]
    if m.ci_repos:
        lines += ["", "## CI pull requests", ""] + [f"- `{r}`: workflows under `infra/ci/{repo_dir_name(r)}/`" for r in m.ci_repos]
    lines += ["", "## Operational documentation", "", "- `docs/BRANCHING.md`", "- `docs/RUNBOOK.md`"]
    if m.gaps:
        lines += ["", "## Gaps for a human", ""] + [f"- {g}" for g in m.gaps]
    readiness_file = "phase4/environment-readiness.json"
    lines += ["", "## Environment readiness", ""]
    if files.exists(project, readiness_file):
        evidence = files.read_json(project, readiness_file)
        current = evidence.get("manifest_sha256") == files.file_sha(project, files.INFRA_MANIFEST)
        lines.append(f"Read-only evidence: {'ready' if current and evidence.get('ready') else 'not ready or stale'}; see `{readiness_file}`. Approval alone does not prove provisioning.")
    else:
        lines.append("Not checked. Run phase4 check-environments; reviewed PRs are not provisioning evidence.")
    if it.notes:
        lines += ["", "## Notes from the architecture", ""] + [f"- {n}" for n in it.notes]
    return "\n".join(lines) + "\n"


# ============================================================================ registry / check
def registry_versions(source: str, limit: int = 10) -> str:
    parts = source.strip().split("/")
    if len(parts) != 3 or not all(re.fullmatch(r"[A-Za-z0-9_.-]+", p) for p in parts):
        raise files.ProjectError("source must look like 'terraform-aws-modules/vpc/aws'")
    url = f"{get_settings().phase4_terraform_registry_url.rstrip('/')}/v1/modules/{'/'.join(parts)}/versions"
    with perf.http_span("terraform_registry", "module_versions", "GET", url, include_path=True) as sp:
        try:
            r = httpx.get(url, timeout=20)
            perf.http_result(sp, r)
            r.raise_for_status()
        except httpx.HTTPError as e:
            # Returned to the model as JSON (not "ERROR:" text): a failed lookup, recorded as such here.
            sp.set_status("error", perf.error_summary(e), perf.classify_error(e))
            return json.dumps({"source": source, "error": f"registry lookup failed: {e}"})
    versions = [v["version"] for m in r.json().get("modules", []) for v in m.get("versions", [])]
    def key(v: str):
        return tuple(int(x) if x.isdigit() else 0 for x in re.split(r"[.-]", v)[:3])
    versions = sorted(set(versions), key=key, reverse=True)
    return json.dumps({"source": source, "latest": versions[:1], "recent": versions[:limit]})


def deployment_problems(project: str, manifest: InfraManifest) -> list[str]:
    """Local policy checks independent of scanners, including immutable image references."""
    problems = []
    for entry in manifest.files:
        if entry.path.startswith("repo/gitops/apps/") and entry.path.endswith("/values.yaml"):
            if not files.exists(project, "infra/" + entry.path):
                continue
            try:
                values = yaml.safe_load(files.read_text(project, "infra/" + entry.path))
                image = values.get("image", {})
                if "tag" in image or not re.fullmatch(r"sha256:[0-9a-f]{64}", str(image.get("digest", ""))):
                    problems.append(f"{entry.path}: image must pin a sha256 digest, never a mutable tag")
            except (ValueError, AttributeError, yaml.YAMLError):
                problems.append(f"{entry.path}: invalid application values")
        elif entry.path.startswith("repo/envs/") and entry.path.endswith("/images.auto.tfvars.json"):
            if not files.exists(project, "infra/" + entry.path):
                continue
            try:
                digests = json.loads(files.read_text(project, "infra/" + entry.path))["image_digests"]
                for image, digest in digests.items():
                    if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(digest)):
                        problems.append(f"{entry.path}: {image} must pin a sha256 digest, never a mutable tag")
            except (ValueError, KeyError, TypeError, AttributeError):
                problems.append(f"{entry.path}: invalid image digests")
    return problems


def check(project: str) -> str:
    manifest = files.read_json(project, files.INFRA_MANIFEST, InfraManifest)
    it = files.read_json(project, files.INFRA_INTENT, InfraIntent)
    problems, warnings = [], []
    if manifest.source_hashes != source_hashes(project):
        problems.append("architecture, project settings or catalog provenance is missing/stale; re-render and validate")
    if manifest.intent_sha256 != files.file_sha(project, files.INFRA_INTENT):
        problems.append("intent.json changed after rendering; re-run infra_render and infra_validate")
    for f in manifest.files:
        p = files.path(project, f"infra/{f.path}")
        if not p.is_file():
            problems.append(f"missing generated file infra/{f.path}")
        elif files.sha256_file(p) != f.sha256:
            problems.append(f"infra/{f.path} changed after the last infra_validate")
    if not files.exists(project, files.INFRA_CHECKS):
        problems.append("infra/checks.json missing: infra_validate was not run")
    if not manifest.checks_passed:
        problems.append("checks did not all pass (see infra/checks.json)")
    if manifest.validation_complete is not True:
        problems.append("required static validation is incomplete")
    if manifest.checks_skipped:
        warnings.append(f"checks not run in this environment: {', '.join(manifest.checks_skipped)}")
    if manifest.checks_incomplete:
        warnings.append("validation incomplete (static checks that did not run to completion): "
                        + ", ".join(manifest.checks_incomplete))
    problems.extend(deployment_problems(project, manifest))
    covered = {c.component_id for c in it.components}
    if not covered:
        problems.append("intent has no components")
    if not files.exists(project, files.INFRA_PR):
        problems.append("infra/PR.md missing")
    return json.dumps({"ok": not problems, "problems": problems, "warnings": warnings,
                       "risk_score": manifest.risk_score, "gaps": manifest.gaps})
