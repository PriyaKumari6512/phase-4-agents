"""Static validation of generated infrastructure in the IaC sandbox image (services/iac-sandbox).

Runs inside the sandbox image (no cloud credentials, no docker socket). Falls back to locally installed tools.
A tool that is unavailable is reported as skipped - never as passed - and the gate summary says so.

Every check carries an `outcome` that says what actually happened:

  passed            the tool ran to completion and reported nothing
  findings          the tool ran to completion and reported findings
  tool_unavailable  the tool is not installed here (skipped)
  skipped           deliberately not run here (sandbox off, registry unreachable, nothing to check)
  timeout           the command hit its time limit (skipped: not checked)
  parse_error       the tool exited normally but its output could not be read (skipped: not checked)
  execution_error   the tool could not run or failed for its own reasons (failing, never "passed")

None of this is deployment validation: these are static checks of generated files. `conftest verify` runs the
policy library's own unit tests; policies are evaluated against a real plan only in Atlantis.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from agent_engine import perf
from agent_engine.phase4.contracts import CheckResult, Finding
from agent_engine.phase4.settings import get_settings

log = logging.getLogger(__name__)
SEVERITY = {"CRITICAL": "critical", "HIGH": "high", "MEDIUM": "medium", "LOW": "low", "UNKNOWN": "info"}
DISPLAY_CHARS = 20000          # what a finding message may quote; parsing always sees the complete output
EXEC_FAILURE_CODES = (125, 126, 127)   # docker could not start the container / command not executable / not found
# What each check covers, for diagnostics: none of them deploys or plans anything.
SCOPE = {"tofu_fmt": "formatting", "tofu_validate": "static: tofu init + validate per environment (no plan, no credentials)",
         "tflint": "static lint", "trivy": "static misconfiguration scan", "checkov": "static misconfiguration scan",
         "actionlint": "workflow lint", "helm_lint": "chart lint + rendered manifest schema",
         "kubeconform": "manifest schema", "gitleaks": "secret scan of generated files",
         "conftest": "policy library unit tests only (no evaluation of a generated plan)"}


@dataclass
class CmdResult:
    code: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def text(self) -> str:
        return self.stdout + "\n" + self.stderr

    def display(self, chars: int = DISPLAY_CHARS) -> str:
        return self.text[-chars:]


def _docker_image_ok() -> bool:
    image = get_settings().phase4_iac_sandbox_image
    with perf.span("command", "docker.image_inspect", category="docker_image_inspect", image=image) as sp:
        if not shutil.which("docker"):
            sp.set(docker_cli=False, available=False)
            return False
        r = subprocess.run(["docker", "image", "inspect", image, "--format", "{{.Id}}"],
                           capture_output=True, text=True)
        sp.set(docker_cli=True, available=r.returncode == 0, exit_code=r.returncode,
               image_id=r.stdout.strip()[:80] if r.returncode == 0 else None)
        return r.returncode == 0


REGISTRY_PROBE = "curl -sS -m 15 -o /dev/null https://registry.opentofu.org/.well-known/terraform.json"
NETWORK_ERRORS = ("request failed", "Error accessing remote module registry", "no such host", "i/o timeout",
                  "lookup registry", "timeout after", "TLS handshake timeout", "connection refused")


def _exec(cmd: str, workdir: Path, use_docker: bool, timeout: int = 300, *, tool: str = "", category: str = "",
          env: str | None = None, attempt: int = 1) -> CmdResult:
    """Runs one sandbox command and returns its complete output. One diagnostic span per command."""
    name = f"phase4-sbx-{uuid.uuid4().hex[:10]}"
    with perf.span("command", f"sandbox.{tool or category}", tool=tool, category=category, env=env, attempt=attempt,
                   executor="docker" if use_docker else "local", timeout_s=timeout,
                   validation_scope=SCOPE.get(tool)) as sp:
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
            result = CmdResult(p.returncode, p.stdout or "", p.stderr or "")
        except subprocess.TimeoutExpired as exc:
            cleanup = "not needed"
            if use_docker:   # killing the docker client does not stop the container
                rm = subprocess.run(["docker", "rm", "-f", name], capture_output=True)
                cleanup = "container removed" if rm.returncode == 0 else f"docker rm exit {rm.returncode}"
            partial = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            result = CmdResult(124, partial, f"timeout after {timeout}s", timed_out=True)
            sp.set(cleanup=cleanup)
        raw = perf.write_raw(sp.id, f"{tool or category}-{env or 'all'}-a{attempt}",
                             f"$ {cmd}\nexit={result.code} timed_out={result.timed_out}\n--- stdout ---\n"
                             f"{result.stdout}\n--- stderr ---\n{result.stderr}\n")
        sp.set(exit_code=result.code, timed_out=result.timed_out, stdout_bytes=len(result.stdout),
               stderr_bytes=len(result.stderr), raw_output=raw)
        if result.timed_out:
            sp.set_status("timeout", f"timeout after {timeout}s", "timeout")
    return result


def _run(cmd: str, workdir: Path, use_docker: bool, timeout: int = 300) -> tuple[int, str]:
    """(exit code, bounded combined output); (124, "timeout after Ns") on a timeout."""
    r = _exec(cmd, workdir, use_docker, timeout, category="adhoc")
    return (124, f"timeout after {timeout}s") if r.timed_out else (r.code, r.display())


CACHE_VOLUME = "phase4-tofu-plugin-cache"


@lru_cache(maxsize=1)
def _ensure_cache_volume() -> None:
    """A new named volume is owned by root; the sandbox runs as an unprivileged user."""
    with perf.span("command", "sandbox.cache_volume_setup", category="cache_setup", volume=CACHE_VOLUME) as sp:
        r = subprocess.run(["docker", "run", "--rm", "--user", "0", "-v", f"{CACHE_VOLUME}:/tofu-cache",
                            get_settings().phase4_iac_sandbox_image, "sh", "-c", "chown $(stat -c %u /home/*/ | head -1) /tofu-cache"
                            " 2>/dev/null || chmod 777 /tofu-cache"], capture_output=True, timeout=120)
        sp.set(exit_code=r.returncode)


def _network_failure(out: str) -> bool:
    return any(s in out for s in NETWORK_ERRORS)


def _available(tool: str, use_docker: bool) -> bool:
    return use_docker or shutil.which(tool) is not None


def parse_json(stdout: str, fallback: str = "", openers: str = "{[", max_tries: int = 50):
    """The first complete JSON value in the output, decoded from the full text (never a truncated tail).
    Scanners may print a banner before it or warnings after it. None when there is none."""
    decoder = json.JSONDecoder()
    for text in (stdout, fallback):
        if not text:
            continue
        positions = sorted(p for p in (text.find(c) for c in openers) if p != -1)
        tries = 0
        idx = positions[0] if positions else -1
        while idx != -1 and tries < max_tries:
            tries += 1
            try:
                value, _ = decoder.raw_decode(text, idx)
                return value
            except json.JSONDecodeError:
                nxt = [p for p in (text.find(c, idx + 1) for c in openers) if p != -1]
                idx = min(nxt) if nxt else -1
    return None


def _check(tool: str, outcome: str, *, passed: bool, summary: str, findings: list[Finding] | None = None,
           skipped: bool = False) -> CheckResult:
    result = CheckResult(tool=tool, passed=passed, skipped=skipped, summary=summary, findings=findings or [],
                         outcome=outcome)
    perf.event("check_result", tool, outcome=outcome, passed=passed, skipped=skipped, findings=len(findings or []),
               validation_scope=SCOPE.get(tool))
    return result


def _exec_failure(tool: str, r: CmdResult) -> CheckResult:
    """The tool could not run or failed for its own reasons: failing, with the reason, never 'passed'."""
    return _check(tool, "execution_error", passed=False, summary=f"{tool} could not run (exit {r.code}); not checked",
                  findings=[Finding(rule_id="execution_error", severity="high", message=r.display()[-1500:])])


def _parse_failure(tool: str, r: CmdResult) -> CheckResult:
    return _check(tool, "parse_error", passed=False, skipped=True,
                  summary=f"{tool} output could not be parsed (exit {r.code}); not checked")


ALL_TOOLS = ("tofu_fmt", "tofu_validate", "tflint", "trivy", "checkov", "actionlint", "helm_lint", "kubeconform",
             "gitleaks", "conftest")


def run_checks(workdir: Path, envs: list[str], *, include_init: bool = True,
               only: set[str] | None = None) -> list[CheckResult]:
    """`only` limits the run to some tools (e.g. {"actionlint"} for a code repo's CI workflows)."""
    tools = [t for t in ALL_TOOLS if only is None or t in only]
    with perf.span("phase", "sandbox.run_checks", tools=len(tools), environments=len(envs),
                   mode=get_settings().phase4_iac_sandbox_mode) as sp:
        if get_settings().phase4_iac_sandbox_mode == "off":
            sp.set(executor="none")
            return [_check(t, "skipped", passed=False, skipped=True,
                           summary="sandbox disabled (PHASE4_IAC_SANDBOX_MODE=off)") for t in tools]
        use_docker = _docker_image_ok()
        sp.set(executor="docker" if use_docker else "local")
        results = _run_checks(workdir, envs, tools, include_init, use_docker)
        sp.set(outcomes={r.tool: r.outcome for r in results})
        return results


def _run_checks(workdir: Path, envs: list[str], tools: list[str], include_init: bool, use_docker: bool) -> list[CheckResult]:
    results: list[CheckResult] = []

    def skipped(tool: str, why: str = "") -> CheckResult:
        return _check(tool, "tool_unavailable" if not why else "skipped", passed=False, skipped=True,
                      summary=why or f"{tool} not available in this environment")

    def want(tool: str) -> bool:
        return tool in tools

    # tofu fmt + validate
    if want("tofu_fmt") or want("tofu_validate"):
        if _available("tofu", use_docker):
            if want("tofu_fmt"):
                r = _exec("tofu fmt -check -recursive -diff", workdir, use_docker, tool="tofu_fmt", category="fmt")
                if r.timed_out:
                    results.append(_check("tofu_fmt", "timeout", passed=False, skipped=True,
                                          summary="tofu_fmt timed out after 300s; not checked"))
                elif r.code in EXEC_FAILURE_CODES:
                    results.append(_exec_failure("tofu_fmt", r))
                elif r.code == 0:
                    results.append(_check("tofu_fmt", "passed", passed=True, summary="formatted"))
                else:
                    results.append(_check("tofu_fmt", "findings", passed=False, summary="fmt diff",
                                          findings=[Finding(rule_id="fmt", severity="low", message=r.display()[-3000:])]))
            if include_init and want("tofu_validate"):
                results.append(_validate_envs(workdir, envs, use_docker))
        else:
            results += [skipped(t) for t in ("tofu_fmt", "tofu_validate") if want(t)]
    results += _other_checks(workdir, use_docker, want, skipped)
    return results


def _validate_envs(workdir: Path, envs: list[str], use_docker: bool) -> CheckResult:
    """tofu init + validate per environment. Needs the module registry: when it cannot be reached the check is
    reported as skipped (a network problem is not a finding in the generated code)."""
    probe = _exec(REGISTRY_PROBE, workdir, use_docker, timeout=30, tool="tofu_validate", category="registry_probe")
    if probe.code != 0:
        return _check("tofu_validate", "skipped", passed=False, skipped=True,
                      summary="module registry unreachable from the sandbox; tofu validate not run")
    fails, network = [], []
    for env in envs:
        d = f"envs/{env}/core"
        if not (workdir / d).exists():
            perf.event("check_env", "tofu_validate", env=env, outcome="skipped", reason="no envs/<env>/core folder")
            continue
        # .terraform (downloaded providers/modules) is removed afterwards: never scanned, never committed
        for attempt in (1, 2):     # retry once on transient registry/network errors
            r = _exec(f"cd {d} && tofu init -backend=false -input=false -no-color >/dev/null && "
                      "tofu validate -no-color -json; rc=$?; rm -rf .terraform .terraform.lock.hcl; exit $rc",
                      workdir, use_docker, timeout=300, tool="tofu_validate", category="init_validate", env=env,
                      attempt=attempt)
            code, out = (124, f"timeout after 300s") if r.timed_out else (r.code, r.text)
            # the container removes these itself, except when it is killed on a timeout
            with perf.span("fs", "sandbox.cleanup", env=env):
                shutil.rmtree(workdir / d / ".terraform", ignore_errors=True)
                (workdir / d / ".terraform.lock.hcl").unlink(missing_ok=True)
            if code == 0 or not _network_failure(out):
                break
        if code != 0 and _network_failure(out):
            network.append(env)
            perf.event("check_env", "tofu_validate", env=env, outcome="network_error", attempts=attempt)
            continue
        data = parse_json(r.stdout)
        diags = data.get("diagnostics", []) if isinstance(data, dict) else None
        if diags is None:
            diags = [] if code == 0 else [{"severity": "error", "summary": r.display()[-2000:]}]
        env_errors = 0
        for dg in diags:
            if dg.get("severity") == "error":
                env_errors += 1
                fails.append(Finding(rule_id="validate", severity="high", file=(dg.get("range") or {}).get("filename", d),
                                     message=f"{dg.get('summary')}: {dg.get('detail', '')}"[:1500]))
        if code != 0 and not diags:
            env_errors += 1
            fails.append(Finding(rule_id="init", severity="high", file=d, message=out[-1500:]))
        perf.event("check_env", "tofu_validate", env=env, attempts=attempt, exit_code=code, errors=env_errors,
                   outcome="valid" if not env_errors else "errors", parsed=isinstance(data, dict))
    if network and not fails:
        return _check("tofu_validate", "skipped", passed=False, skipped=True,
                      summary=f"registry/network errors during tofu init for {', '.join(network)}; not validated")
    summary = "valid" if not fails else f"{len(fails)} errors"
    if network:
        summary += f" (not validated, network errors: {', '.join(network)})"
    return _check("tofu_validate", "findings" if fails else "passed", passed=not fails, findings=fails, summary=summary)


def _other_checks(workdir: Path, use_docker: bool, want, skipped) -> list[CheckResult]:
    results: list[CheckResult] = []

    def run(tool: str, cmd: str, timeout: int = 300) -> CmdResult | None:
        """None when the command timed out: reported as skipped, never as passed."""
        r = _exec(cmd, workdir, use_docker, timeout=timeout, tool=tool, category="scan")
        if r.timed_out:
            results.append(_check(tool, "timeout", passed=False, skipped=True,
                                  summary=f"{tool} timed out after {timeout}s; not checked"))
            return None
        return r

    if want("tflint"):
        if not _available("tflint", use_docker):
            results.append(skipped("tflint"))
        elif r := run("tflint", "tflint --recursive --format json --minimum-failure-severity=error"):
            data = parse_json(r.stdout, r.text, openers="{")
            if r.code in EXEC_FAILURE_CODES or (not isinstance(data, dict) and r.code != 0):
                results.append(_exec_failure("tflint", r))
            elif not isinstance(data, dict):
                results.append(_parse_failure("tflint", r))
            else:
                f = []
                for i in data.get("issues") or []:
                    try:
                        f.append(Finding(rule_id=i["rule"]["name"],
                                         severity="medium" if i["rule"]["severity"] == "warning" else "high",
                                         file=i["range"]["filename"], message=i["message"]))
                    except (KeyError, TypeError):
                        continue
                if r.code != 0 and not f:     # exit != 0 with no issues: tflint's own errors (config, plugins)
                    results.append(_exec_failure("tflint", r))
                else:
                    results.append(_check("tflint", "findings" if f else "passed", passed=r.code == 0, findings=f,
                                          summary=f"{len(f)} issues"))

    if want("trivy"):
        if not _available("trivy", use_docker):
            results.append(skipped("trivy"))
        elif r := run("trivy", "trivy config --quiet --format json --severity HIGH,CRITICAL .", 600):
            data = parse_json(r.stdout, r.text, openers="{")
            if r.code in EXEC_FAILURE_CODES or (not isinstance(data, dict) and r.code != 0):
                results.append(_exec_failure("trivy", r))
            elif not isinstance(data, dict):
                results.append(_parse_failure("trivy", r))
            else:
                f = []
                for res in data.get("Results", []) or []:
                    for m in res.get("Misconfigurations", []) or []:
                        f.append(Finding(rule_id=m.get("ID", "trivy"), severity=SEVERITY.get(m.get("Severity", "UNKNOWN"), "info"),
                                         file=res.get("Target"), message=m.get("Title", "")))
                results.append(_check("trivy", "findings" if f else "passed", passed=not f, findings=f,
                                      summary=f"{len(f)} HIGH/CRITICAL"))

    if want("checkov"):
        if not _available("checkov", use_docker):
            results.append(skipped("checkov"))
        elif r := run("checkov", "checkov -d . --framework terraform --compact --quiet -o json --soft-fail", 600):
            data = parse_json(r.stdout, r.text)
            if r.code in EXEC_FAILURE_CODES or (not isinstance(data, (dict, list)) and r.code != 0):
                results.append(_exec_failure("checkov", r))
            elif not isinstance(data, (dict, list)):
                results.append(_parse_failure("checkov", r))
            else:
                f = []
                blocks = data if isinstance(data, list) else [data]
                for b in blocks:
                    if not isinstance(b, dict):
                        continue
                    for fc in (b.get("results") or {}).get("failed_checks", []):
                        sev = (fc.get("severity") or "MEDIUM").upper()
                        f.append(Finding(rule_id=fc.get("check_id", "checkov"), severity=SEVERITY.get(sev, "medium"),
                                         file=fc.get("file_path"), message=fc.get("check_name", "")))
                high = [x for x in f if x.severity in ("high", "critical")]
                perf.event("check_detail", "checkov", resource_count=_first_key(blocks, "resource_count"),
                           parsing_errors=_first_key(blocks, "parsing_errors"))
                results.append(_check("checkov", "findings" if f else "passed", passed=not high, findings=f[:200],
                                      summary=f"{len(f)} failed checks ({len(high)} high/critical)"))

    if want("actionlint"):
        if not _available("actionlint", use_docker):
            results.append(skipped("actionlint"))
        elif (workdir / ".github" / "workflows").exists():
            if r := run("actionlint", "actionlint -no-color .github/workflows/*.yml"):
                if r.code == 0:
                    results.append(_check("actionlint", "passed", passed=True, summary="ok"))
                elif r.code == 1:
                    results.append(_check("actionlint", "findings", passed=False, summary="errors",
                                          findings=[Finding(rule_id="actionlint", severity="medium", message=r.display()[-3000:])]))
                else:          # 2 bad usage, 3 fatal, 125-127 not runnable
                    results.append(_exec_failure("actionlint", r))
        else:
            perf.event("check_result", "actionlint", outcome="not_run", reason="no .github/workflows folder")

    if want("helm_lint") or want("kubeconform"):
        if not _available("helm", use_docker) or not (workdir / "gitops" / "charts" / "app").exists():
            results += [skipped(t) for t in ("helm_lint", "kubeconform") if want(t)]
        else:
            if want("helm_lint") and (r := run("helm_lint", "helm lint gitops/charts/app && helm template gitops/charts/app | "
                                               "kubeconform -strict -summary -ignore-missing-schemas")):
                results.append(_simple("helm_lint", r, "helm"))
            # Helm values files are not manifests; validate only Kubernetes resources we generate
            if want("kubeconform") and (r := run("kubeconform", "find gitops -name '*.yaml' -not -path '*/charts/*' "
                                                 "-not -name 'values.yaml' | xargs -r kubeconform -strict -summary "
                                                 "-ignore-missing-schemas")):
                results.append(_simple("kubeconform", r, "kubeconform"))

    if want("gitleaks"):
        if not _available("gitleaks", use_docker):
            results.append(skipped("gitleaks"))
        elif r := run("gitleaks", "gitleaks detect --no-git --source . --redact --no-banner --exit-code 1"):
            if r.code == 0:
                results.append(_check("gitleaks", "passed", passed=True, summary="no secrets"))
            elif r.code == 1:          # --exit-code 1: leaks found
                results.append(_check("gitleaks", "findings", passed=False, summary="possible secrets found",
                                      findings=[Finding(rule_id="gitleaks", severity="critical", message=r.display()[-2000:])]))
            else:
                results.append(_exec_failure("gitleaks", r))

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
                if r.code == 0:
                    results.append(_check("conftest", "passed", passed=True,
                                          summary="policy unit tests pass (plan-time evaluation runs in Atlantis)"))
                elif r.code in EXEC_FAILURE_CODES:
                    results.append(_exec_failure("conftest", r))
                else:
                    results.append(_check("conftest", "findings", passed=False, summary="policy tests failing",
                                          findings=[Finding(rule_id="conftest", severity="high", message=r.display()[-3000:])]))
    return results


def _simple(tool: str, r: CmdResult, rule: str) -> CheckResult:
    if r.code == 0:
        return _check(tool, "passed", passed=True, summary="ok")
    if r.code in EXEC_FAILURE_CODES:
        return _exec_failure(tool, r)
    return _check(tool, "findings", passed=False, summary="errors",
                  findings=[Finding(rule_id=rule, severity="medium", message=r.display()[-3000:])])


def _first_key(blocks: list, key: str):
    for b in blocks:
        if isinstance(b, dict):
            if key in b:
                return b[key]
            summary = b.get("summary")
            if isinstance(summary, dict) and key in summary:
                return summary[key]
    return None


def incomplete(results: list[CheckResult]) -> list[str]:
    """Checks that did not run to completion here, as 'tool: outcome'."""
    return [f"{r.tool}: {r.outcome or ('skipped' if r.skipped else 'unknown')}" for r in results
            if r.skipped or r.outcome in ("execution_error", "parse_error", "timeout", "tool_unavailable", "skipped")]


def blocking(results: list[CheckResult]) -> list[CheckResult]:
    return [r for r in results if not r.passed and not r.skipped and r.tool not in ("tofu_fmt",)]
