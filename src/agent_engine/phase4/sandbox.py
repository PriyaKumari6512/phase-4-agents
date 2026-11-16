"""Static validation of generated infrastructure in the IaC sandbox image (services/iac-sandbox).

Runs inside the sandbox image (no cloud credentials, no docker socket). Falls back to locally installed tools.
A tool that is unavailable is reported as skipped - never as passed - and the gate summary says so.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
import uuid
from functools import lru_cache
from pathlib import Path

from agent_engine.phase4.contracts import CheckResult, Finding
from agent_engine.phase4.settings import get_settings

log = logging.getLogger(__name__)
SEVERITY = {"CRITICAL": "critical", "HIGH": "high", "MEDIUM": "medium", "LOW": "low", "UNKNOWN": "info"}


def _docker_image_ok() -> bool:
    if not shutil.which("docker"):
        return False
    r = subprocess.run(["docker", "image", "inspect", get_settings().phase4_iac_sandbox_image],
                       capture_output=True, text=True)
    return r.returncode == 0


REGISTRY_PROBE = "curl -sS -m 15 -o /dev/null https://registry.opentofu.org/.well-known/terraform.json"
NETWORK_ERRORS = ("request failed", "Error accessing remote module registry", "no such host", "i/o timeout",
                  "lookup registry", "timeout after", "TLS handshake timeout", "connection refused")


def _run(cmd: str, workdir: Path, use_docker: bool, timeout: int = 300) -> tuple[int, str]:
    name = f"phase4-sbx-{uuid.uuid4().hex[:10]}"
    # Providers are downloaded once into a shared plugin cache, not again for every environment and every run.
    # In Docker the cache is a named volume: provider binaries cannot run from a Windows bind mount.
    if use_docker:
        _ensure_cache_volume()
        full = ["docker", "run", "--rm", "--name", name, "--network", "bridge", "-v", f"{workdir.resolve()}:/work",
                "-v", f"{CACHE_VOLUME}:/tofu-cache", "-e", "TF_PLUGIN_CACHE_DIR=/tofu-cache",
                "-e", "TF_PLUGIN_CACHE_MAY_BREAK_DEPENDENCY_LOCK_FILE=true",
                "-w", "/work", get_settings().phase4_iac_sandbox_image, "sh", "-c", cmd]
    else:
        cache = Path(get_settings().phase4_iac_cache_dir) / "tofu-plugins"
        cache.mkdir(parents=True, exist_ok=True)
        full = ["bash", "-c", f"export TF_PLUGIN_CACHE_DIR='{cache.resolve().as_posix()}' "
                              f"TF_PLUGIN_CACHE_MAY_BREAK_DEPENDENCY_LOCK_FILE=true; {cmd}"]
    try:
        p = subprocess.run(full, cwd=workdir, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=timeout, stdin=subprocess.DEVNULL)
        return p.returncode, (p.stdout + "\n" + p.stderr)[-20000:]
    except subprocess.TimeoutExpired:
        if use_docker:   # killing the docker client does not stop the container
            subprocess.run(["docker", "rm", "-f", name], capture_output=True)
        return 124, f"timeout after {timeout}s"


CACHE_VOLUME = "phase4-tofu-plugin-cache"


@lru_cache(maxsize=1)
def _ensure_cache_volume() -> None:
    """A new named volume is owned by root; the sandbox runs as an unprivileged user."""
    subprocess.run(["docker", "run", "--rm", "--user", "0", "-v", f"{CACHE_VOLUME}:/tofu-cache",
                    get_settings().phase4_iac_sandbox_image, "sh", "-c", "chown $(stat -c %u /home/*/ | head -1) /tofu-cache"
                    " 2>/dev/null || chmod 777 /tofu-cache"], capture_output=True, timeout=120)


def _network_failure(out: str) -> bool:
    return any(s in out for s in NETWORK_ERRORS)


def _available(tool: str, use_docker: bool) -> bool:
    return use_docker or shutil.which(tool) is not None


ALL_TOOLS = ("tofu_fmt", "tofu_validate", "tflint", "trivy", "checkov", "actionlint", "helm_lint", "kubeconform",
             "gitleaks", "conftest")


def run_checks(workdir: Path, envs: list[str], *, include_init: bool = True,
               only: set[str] | None = None) -> list[CheckResult]:
    """`only` limits the run to some tools (e.g. {"actionlint"} for a code repo's CI workflows)."""
    tools = [t for t in ALL_TOOLS if only is None or t in only]
    if get_settings().phase4_iac_sandbox_mode == "off":
        return [CheckResult(tool=t, passed=False, skipped=True, summary="sandbox disabled (PHASE4_IAC_SANDBOX_MODE=off)")
                for t in tools]
    use_docker = _docker_image_ok()
    results: list[CheckResult] = []

    def skipped(tool: str, why: str = "") -> CheckResult:
        return CheckResult(tool=tool, passed=False, skipped=True, summary=why or f"{tool} not available in this environment")

    def want(tool: str) -> bool:
        return tool in tools

    # tofu fmt + validate
    if want("tofu_fmt") or want("tofu_validate"):
        if _available("tofu", use_docker):
            if want("tofu_fmt"):
                code, out = _run("tofu fmt -check -recursive -diff", workdir, use_docker)
                results.append(CheckResult(tool="tofu_fmt", passed=code == 0, summary="formatted" if code == 0 else "fmt diff",
                                           findings=[] if code == 0 else [Finding(rule_id="fmt", severity="low", message=out[-3000:])]))
            if include_init and want("tofu_validate"):
                results.append(_validate_envs(workdir, envs, use_docker))
        else:
            results += [skipped(t) for t in ("tofu_fmt", "tofu_validate") if want(t)]
    results += _other_checks(workdir, use_docker, want, skipped)
    return results


def _validate_envs(workdir: Path, envs: list[str], use_docker: bool) -> CheckResult:
    """tofu init + validate per environment. Needs the module registry: when it cannot be reached the check is
    reported as skipped (a network problem is not a finding in the generated code)."""
    code, out = _run(REGISTRY_PROBE, workdir, use_docker, timeout=30)
    if code != 0:
        return CheckResult(tool="tofu_validate", passed=False, skipped=True,
                           summary="module registry unreachable from the sandbox; tofu validate not run")
    fails, network = [], []
    for env in envs:
        d = f"envs/{env}/core"
        if not (workdir / d).exists():
            continue
        # .terraform (downloaded providers/modules) is removed afterwards: never scanned, never committed
        for _ in range(2):     # retry once on transient registry/network errors
            code, out = _run(f"cd {d} && tofu init -backend=false -input=false -no-color >/dev/null && "
                             "tofu validate -no-color -json; rc=$?; rm -rf .terraform .terraform.lock.hcl; exit $rc",
                             workdir, use_docker, timeout=300)
            # the container removes these itself, except when it is killed on a timeout
            shutil.rmtree(workdir / d / ".terraform", ignore_errors=True)
            (workdir / d / ".terraform.lock.hcl").unlink(missing_ok=True)
            if code == 0 or not _network_failure(out):
                break
        if code != 0 and _network_failure(out):
            network.append(env)
            continue
        try:
            diags = json.loads(out[out.find("{"):]).get("diagnostics", [])
        except (ValueError, json.JSONDecodeError):
            diags = [] if code == 0 else [{"severity": "error", "summary": out[-2000:]}]
        for dg in diags:
            if dg.get("severity") == "error":
                fails.append(Finding(rule_id="validate", severity="high", file=(dg.get("range") or {}).get("filename", d),
                                     message=f"{dg.get('summary')}: {dg.get('detail', '')}"[:1500]))
        if code != 0 and not diags:
            fails.append(Finding(rule_id="init", severity="high", file=d, message=out[-1500:]))
    if network and not fails:
        return CheckResult(tool="tofu_validate", passed=False, skipped=True,
                           summary=f"registry/network errors during tofu init for {', '.join(network)}; not validated")
    summary = "valid" if not fails else f"{len(fails)} errors"
    if network:
        summary += f" (not validated, network errors: {', '.join(network)})"
    return CheckResult(tool="tofu_validate", passed=not fails, findings=fails, summary=summary)


def _other_checks(workdir: Path, use_docker: bool, want, skipped) -> list[CheckResult]:
    results: list[CheckResult] = []

    def run(tool: str, cmd: str, timeout: int = 300) -> tuple[int, str] | None:
        """None when the command timed out: reported as skipped, never as passed."""
        code, out = _run(cmd, workdir, use_docker, timeout=timeout)
        if code == 124 and out.startswith("timeout after"):
            results.append(skipped(tool, f"{tool} timed out after {timeout}s; not checked"))
            return None
        return code, out

    if want("tflint"):
        if not _available("tflint", use_docker):
            results.append(skipped("tflint"))
        elif r := run("tflint", "tflint --recursive --format json --minimum-failure-severity=error"):
            code, out = r
            f = []
            try:
                for i in json.loads(out[out.find("{"):]).get("issues", []):
                    f.append(Finding(rule_id=i["rule"]["name"], severity="medium" if i["rule"]["severity"] == "warning" else "high",
                                     file=i["range"]["filename"], message=i["message"]))
            except (ValueError, json.JSONDecodeError, KeyError):
                pass
            results.append(CheckResult(tool="tflint", passed=code == 0, findings=f, summary=f"{len(f)} issues"))

    if want("trivy"):
        if not _available("trivy", use_docker):
            results.append(skipped("trivy"))
        elif r := run("trivy", "trivy config --quiet --format json --severity HIGH,CRITICAL .", 600):
            code, out = r
            f = []
            try:
                for res in json.loads(out[out.find("{"):]).get("Results", []) or []:
                    for m in res.get("Misconfigurations", []) or []:
                        f.append(Finding(rule_id=m.get("ID", "trivy"), severity=SEVERITY.get(m.get("Severity", "UNKNOWN"), "info"),
                                         file=res.get("Target"), message=m.get("Title", "")))
            except (ValueError, json.JSONDecodeError):
                if code != 0:
                    f.append(Finding(rule_id="trivy", severity="high", message=out[-1500:]))
            results.append(CheckResult(tool="trivy", passed=not f, findings=f, summary=f"{len(f)} HIGH/CRITICAL"))

    if want("checkov"):
        if not _available("checkov", use_docker):
            results.append(skipped("checkov"))
        elif r := run("checkov", "checkov -d . --framework terraform --compact --quiet -o json --soft-fail", 600):
            code, out = r
            f = []
            try:
                data = json.loads(out[out.find("{") if out.strip().startswith("{") else out.find("["):])
                blocks = data if isinstance(data, list) else [data]
                for b in blocks:
                    for fc in (b.get("results") or {}).get("failed_checks", []):
                        sev = (fc.get("severity") or "MEDIUM").upper()
                        f.append(Finding(rule_id=fc.get("check_id", "checkov"), severity=SEVERITY.get(sev, "medium"),
                                         file=fc.get("file_path"), message=fc.get("check_name", "")))
            except (ValueError, json.JSONDecodeError):
                pass
            high = [x for x in f if x.severity in ("high", "critical")]
            results.append(CheckResult(tool="checkov", passed=not high, findings=f[:200],
                                       summary=f"{len(f)} failed checks ({len(high)} high/critical)"))

    if want("actionlint"):
        if not _available("actionlint", use_docker):
            results.append(skipped("actionlint"))
        elif (workdir / ".github" / "workflows").exists():
            if r := run("actionlint", "actionlint -no-color .github/workflows/*.yml"):
                code, out = r
                results.append(CheckResult(tool="actionlint", passed=code == 0, summary="ok" if code == 0 else "errors",
                                           findings=[] if code == 0 else [Finding(rule_id="actionlint", severity="medium", message=out[-3000:])]))

    if want("helm_lint") or want("kubeconform"):
        if not _available("helm", use_docker) or not (workdir / "gitops" / "charts" / "app").exists():
            results += [skipped(t) for t in ("helm_lint", "kubeconform") if want(t)]
        else:
            if want("helm_lint") and (r := run("helm_lint", "helm lint gitops/charts/app && helm template gitops/charts/app | "
                                               "kubeconform -strict -summary -ignore-missing-schemas")):
                code, out = r
                results.append(CheckResult(tool="helm_lint", passed=code == 0, summary="ok" if code == 0 else "errors",
                                           findings=[] if code == 0 else [Finding(rule_id="helm", severity="medium", message=out[-3000:])]))
            # Helm values files are not manifests; validate only Kubernetes resources we generate
            if want("kubeconform") and (r := run("kubeconform", "find gitops -name '*.yaml' -not -path '*/charts/*' "
                                                 "-not -name 'values.yaml' | xargs -r kubeconform -strict -summary "
                                                 "-ignore-missing-schemas")):
                code, out = r
                results.append(CheckResult(tool="kubeconform", passed=code == 0, summary="ok" if code == 0 else "errors",
                                           findings=[] if code == 0 else [Finding(rule_id="kubeconform", severity="medium", message=out[-3000:])]))

    if want("gitleaks"):
        if not _available("gitleaks", use_docker):
            results.append(skipped("gitleaks"))
        elif r := run("gitleaks", "gitleaks detect --no-git --source . --redact --no-banner --exit-code 1"):
            code, out = r
            results.append(CheckResult(tool="gitleaks", passed=code == 0, summary="no secrets" if code == 0 else "possible secrets found",
                                       findings=[] if code == 0 else [Finding(rule_id="gitleaks", severity="critical", message=out[-2000:])]))

    if want("conftest"):
        if not _available("conftest", use_docker):
            results.append(skipped("conftest"))
        else:
            policies = Path(get_settings().phase4_infra_catalog_dir) / "policies"
            tmp = workdir / ".phase4-policies"
            shutil.copytree(policies, tmp, dirs_exist_ok=True)
            try:
                r = run("conftest", "conftest verify --policy .phase4-policies")
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
            if r:
                code, out = r
                results.append(CheckResult(tool="conftest", passed=code == 0,
                                           summary="policy unit tests pass (plan-time evaluation runs in Atlantis)" if code == 0
                                           else "policy tests failing",
                                           findings=[] if code == 0 else [Finding(rule_id="conftest", severity="high", message=out[-3000:])]))
    return results


def blocking(results: list[CheckResult]) -> list[CheckResult]:
    return [r for r in results if not r.passed and not r.skipped and r.tool not in ("tofu_fmt",)]
