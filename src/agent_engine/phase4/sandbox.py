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
import contextvars
import hashlib
import os
import re
import shlex
import time
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from agent_engine import perf
from agent_engine.runtime import project_lock
from agent_engine.phase4.contracts import CheckResult, Finding
from agent_engine.phase4.settings import get_settings

log = logging.getLogger(__name__)
SEVERITY = {"CRITICAL": "critical", "HIGH": "high", "MEDIUM": "medium", "LOW": "low", "UNKNOWN": "info"}
DISPLAY_CHARS = 20000          # what a finding message may quote; parsing always sees the complete output
EXEC_FAILURE_CODES = (125, 126, 127)   # docker could not start the container / command not executable / not found
_budget_deadline = contextvars.ContextVar("sandbox_deadline", default=None)
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
        remaining = (_budget_deadline.get() or (time.monotonic() + timeout)) - time.monotonic()
        if remaining <= 0:
            sp.set_status("timeout", "overall validation budget exhausted", "timeout")
            return CmdResult(124, "", "overall validation budget exhausted", timed_out=True)
        timeout = min(timeout, max(1, int(remaining)))
        # Providers are downloaded once into a shared plugin cache, not again for every environment and every run.
        # In Docker the cache is a named volume: provider binaries cannot run from a Windows bind mount.
        if use_docker:
            uid, gid = _sandbox_identity()
            cache_args = []
            if tool == "tofu_validate":
                volume = _cache_volume(workdir)
                _ensure_cache_volume(volume, uid, gid, get_settings().phase4_iac_sandbox_image)
                cache_args = ["-v", f"{volume}:/tofu-cache", "-e", "TF_PLUGIN_CACHE_DIR=/tofu-cache"]
            full = ["docker", "run", "--rm", "--name", name, "--network", "bridge", "-v", f"{workdir.resolve()}:/work",
                    "--user", f"{uid}:{gid}", "-e", "HOME=/tmp/phase4-home",
                    *cache_args,
                    "-e", "TF_PLUGIN_CACHE_MAY_BREAK_DEPENDENCY_LOCK_FILE=true",
                "-w", "/work", get_settings().phase4_iac_sandbox_image, "bash", "-o", "pipefail", "-c",
                "mkdir -p /tmp/phase4-home && " + cmd]
        else:
            cache = Path(get_settings().phase4_iac_cache_dir) / "tofu-plugins"
            cache.mkdir(parents=True, exist_ok=True)
            full = ["bash", "-o", "pipefail", "-c", f"export TF_PLUGIN_CACHE_DIR={shlex.quote(cache.resolve().as_posix())} "
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


def _sandbox_identity() -> tuple[int, int]:
    # Match Linux bind-mount ownership; Docker Desktop maps the sandbox user's
    # permissions on Windows/macOS. Never make host directories world-writable.
    return (os.getuid(), os.getgid()) if sys.platform.startswith("linux") else (1000, 1000)


def _cache_volume(workdir: Path) -> str:
    # One volume per cache root/user, protected by the provider-cache lease.
    # Scanner snapshots must not create an unbounded number of Docker volumes.
    key = hashlib.sha256(str(Path(get_settings().phase4_iac_cache_dir).resolve()).encode()).hexdigest()[:20]
    return f"phase4-tofu-{_sandbox_identity()[0]}-{key}"


@lru_cache(maxsize=128)
def _ensure_cache_volume(volume: str, uid: int, gid: int, image: str) -> None:
    with perf.span("command", "sandbox.cache_volume_setup", category="cache_setup", volume=volume) as sp:
        r = subprocess.run(["docker", "run", "--rm", "--user", "0", "-v", f"{volume}:/tofu-cache",
                            image, "chown", f"{uid}:{gid}", "/tofu-cache"], capture_output=True, timeout=30)
        sp.set(exit_code=r.returncode)
        if r.returncode:
            raise RuntimeError("could not initialize the sandbox provider cache")


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
        budget = float(os.environ.get("PHASE4_IAC_TOTAL_BUDGET_SECONDS", "900"))
        if not 1 <= budget <= 7200:
            raise ValueError("PHASE4_IAC_TOTAL_BUDGET_SECONDS must be between 1 and 7200")
        token = _budget_deadline.set(time.monotonic() + budget)
        try:
            workers = int(os.environ.get("PHASE4_IAC_CHECK_CONCURRENCY", "1"))
            if not 1 <= workers <= 4:
                raise ValueError("PHASE4_IAC_CHECK_CONCURRENCY must be between 1 and 4")
            results = (_parallel_checks(workdir, envs, tools, include_init, use_docker, workers)
                       if workers > 1 else _run_checks(workdir, envs, tools, include_init, use_docker))
        finally:
            _budget_deadline.reset(token)
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
                try:
                    results.append(_validate_envs(workdir, envs, use_docker))
                except TimeoutError:
                    results.append(_check("tofu_validate", "timeout", passed=False, skipped=True,
                                          summary="validation budget exhausted waiting for provider-cache lease"))
        else:
            results += [skipped(t) for t in ("tofu_fmt", "tofu_validate") if want(t)]
    results += _other_checks(workdir, use_docker, want, skipped)
    return results


def _parallel_checks(workdir: Path, envs: list[str], tools: list[str], include_init: bool,
                     use_docker: bool, workers: int) -> list[CheckResult]:
    """Each scanner sees the same bytes and owns its temporary files; ordered results."""
    def digest():
        return {p.relative_to(workdir).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in workdir.rglob("*") if p.is_file() and not p.name.startswith(".engine-")}
    if any(p.is_symlink() for p in workdir.rglob("*")):
        raise ValueError("parallel checks require a workdir without symlinks")
    before = digest()
    groups = [[t for t in tools if t.startswith("tofu_")]] + [[t] for t in tools if not t.startswith("tofu_")]
    groups = [g for g in groups if g]
    with tempfile.TemporaryDirectory(prefix="phase4-scans-") as temp:
        frozen = Path(temp) / "source"
        shutil.copytree(workdir, frozen)
        def check(group):
            # Only active workers allocate a copy, bounding simultaneous disk use.
            with tempfile.TemporaryDirectory(dir=temp, prefix="worker-") as worker:
                target = Path(worker) / "source"
                shutil.copytree(frozen, target)
                return _run_checks(target, envs, group, include_init, use_docker)
        if digest() != before:
            raise ValueError("infrastructure changed while taking scanner snapshot; retry")
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="iac-check") as pool:
            futures = [pool.submit(contextvars.copy_context().run, check, group) for group in groups]
            results = [item for future in futures for item in future.result()]
    if digest() != before:
        return [_check(t, "execution_error", passed=False,
                       summary="source changed during validation; results discarded; retry") for t in tools]
    return sorted(results, key=lambda r: tools.index(r.tool))


def _validate_envs(workdir: Path, envs: list[str], use_docker: bool) -> CheckResult:
    """tofu init + validate per environment. Needs the module registry: when it cannot be reached the check is
    reported as skipped (a network problem is not a finding in the generated code)."""
    # Keep download state OUTSIDE generated/published files. Re-run validation every
    # time; only downloaded modules/providers are reused on byte-identical inputs.
    h = hashlib.sha256()
    sources = [p for p in workdir.rglob("*") if p.is_file()
               and not any(x in (".terraform", ".git") or x.startswith(".engine-") for x in p.relative_to(workdir).parts)]
    for p in sorted(sources, key=lambda p: p.relative_to(workdir).as_posix()):
        h.update(p.relative_to(workdir).as_posix().encode() + b"\0" + p.read_bytes() + b"\0")
    cache_root = Path(get_settings().phase4_iac_cache_dir)
    cache = cache_root / "validation" / h.hexdigest()
    # All validation initializations share the host plugin cache. Its lease also
    # serializes retention so no in-use directory or lock inode can be removed.
    remaining = max(0, (_budget_deadline.get() or time.monotonic() + 900) - time.monotonic())
    with project_lock(cache_root, "provider-cache", timeout=remaining), project_lock(cache, "validation"):
        from agent_engine.phase4.cache_retention import prune_validation_cache
        prune_validation_cache(cache_root, keep=cache)
        for p in sources:
            dest = cache / p.relative_to(workdir)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.is_file() or dest.read_bytes() != p.read_bytes():
                shutil.copyfile(p, dest)
        marker = cache / ".engine-cache-owned"
        marker.write_text("phase4-validation-v1\n", encoding="utf-8")
        try:
            return _validate_cached_envs(cache, envs, use_docker)
        finally:
            marker.touch()


def _validate_cached_envs(workdir: Path, envs: list[str], use_docker: bool) -> CheckResult:
    probe = _exec(REGISTRY_PROBE, workdir, use_docker, timeout=30, tool="tofu_validate", category="registry_probe")
    if probe.timed_out:
        return _check("tofu_validate", "timeout", passed=False, skipped=True, summary="registry probe timed out")
    if probe.code != 0:
        return _check("tofu_validate", "skipped", passed=False, skipped=True,
                      summary="module registry unreachable from the sandbox; tofu validate not run")
    fails, network = [], []
    checked = 0
    for env in envs:
        d = f"envs/{env}/core"
        if not (workdir / d).exists():
            perf.event("check_env", "tofu_validate", env=env, outcome="skipped", reason="no envs/<env>/core folder")
            network.append(f"{env}: missing environment directory")
            continue
        # Download state stays in this leased cache workspace, outside published files.
        for attempt in (1, 2):     # retry once on transient registry/network errors
            r = _exec(f"cd {shlex.quote(d)} && tofu init -backend=false -input=false -no-color",
                      workdir, use_docker, timeout=300, tool="tofu_validate", category="init", env=env,
                      attempt=attempt)
            code, out = (124, f"timeout after 300s") if r.timed_out else (r.code, r.text)
            if r.timed_out:
                return _check("tofu_validate", "timeout", passed=False, skipped=True, summary=f"{env}: init timed out; remaining environments not validated")
            if code == 0 or not _network_failure(out):
                break
        if code != 0 and _network_failure(out):
            network.append(env)
            perf.event("check_env", "tofu_validate", env=env, outcome="network_error", attempts=attempt)
            continue
        if code != 0:
            return _exec_failure("tofu_validate", r)
        r = _exec(f"cd {shlex.quote(d)} && tofu validate -no-color -json", workdir, use_docker,
                  timeout=120, tool="tofu_validate", category="validate", env=env)
        code, out = r.code, r.text
        if r.timed_out:
            return _check("tofu_validate", "timeout", passed=False, skipped=True, summary=f"{env}: validate timed out")
        if any(s in out.lower() for s in ("unrecognized remote plugin", "failed to instantiate provider", "failed to read schema", "failed to load plugin")):
            return _exec_failure("tofu_validate", r)
        data = parse_json(r.stdout)
        if not isinstance(data, dict) or not isinstance(data.get("diagnostics"), list) or not isinstance(data.get("valid"), bool):
            return _parse_failure("tofu_validate", r)
        checked += 1
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
    if network or not checked:
        return _check("tofu_validate", "skipped", passed=False, skipped=True,
                      findings=fails, summary=f"incomplete environment validation: {', '.join(network) or 'no environments checked'}")
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
            elif not isinstance(data, dict) or not isinstance(data.get("issues"), list) or not isinstance(data.get("errors"), list):
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
                if data.get("errors") or (r.code != 0 and not f):
                    results.append(_exec_failure("tflint", r))
                else:
                    results.append(_check("tflint", "findings" if f else "passed", passed=r.code == 0, findings=f,
                                          summary=f"{len(f)} issues"))

    if want("trivy"):
        if not _available("trivy", use_docker):
            results.append(skipped("trivy"))
        elif r := run("trivy", "trivy config --quiet --format json --severity HIGH,CRITICAL .", 600):
            data = parse_json(r.stdout, r.text, openers="{")
            if r.code != 0:
                results.append(_exec_failure("trivy", r))
            elif not isinstance(data, dict) or not isinstance(data.get("Results"), list):
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
            results.append(_checkov_result(r))

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
            schema = os.environ.get("PHASE4_KUBERNETES_SCHEMA_LOCATION", "")
            schema_args = " -schema-location default" + (" -schema-location " + shlex.quote(schema) if schema else "")
            if want("helm_lint"):
                values = sorted(workdir.glob("gitops/apps/*/*/values.yaml"))
                commands = ["helm lint gitops/charts/app"]
                for value in values or [None]:
                    arg = " -f " + shlex.quote(value.relative_to(workdir).as_posix()) if value else ""
                    commands.append("helm template gitops/charts/app" + arg + " | kubeconform -strict -summary -ignore-missing-schemas" + schema_args)
                if r := run("helm_lint", " && ".join(commands)):
                    results.append(_schema_result("helm_lint", r))
            if want("kubeconform"):
                cmd = "find gitops -name '*.yaml' -not -path '*/charts/*' -not -name 'values.yaml' -print0 | xargs -0 -r kubeconform -strict -summary -ignore-missing-schemas" + schema_args
                if r := run("kubeconform", cmd):
                    results.append(_schema_result("kubeconform", r))

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


def _checkov_result(r: CmdResult) -> CheckResult:
    if r.code != 0:
        return _exec_failure("checkov", r)
    data = parse_json(r.stdout, r.text)
    blocks = data if isinstance(data, list) else [data]
    if not blocks or any(not isinstance(b, dict) or not isinstance(b.get("results"), dict)
                         or not isinstance(b["results"].get("failed_checks"), list) for b in blocks):
        return _parse_failure("checkov", r)
    findings, unknown = [], 0
    for b in blocks:
        for fc in b["results"]["failed_checks"]:
            if not isinstance(fc, dict):
                return _parse_failure("checkov", r)
            unknown += not bool(fc.get("severity"))
            sev = SEVERITY.get(str(fc.get("severity", "")).upper(), "medium")
            findings.append(Finding(rule_id=fc.get("check_id", "checkov"), severity=sev, file=fc.get("file_path"),
                                    message=("[severity unreported; review required] " if not fc.get("severity") else "") + fc.get("check_name", "")))
    incomplete_scan = any((b.get("summary") or {}).get("parsing_errors") for b in blocks) or "Failed to download module" in r.stderr
    high = sum(f.severity in ("high", "critical") for f in findings)
    return _check("checkov", "execution_error" if incomplete_scan else "findings" if findings else "passed",
                  passed=not high and not unknown and not incomplete_scan, findings=findings[:200],
                  summary=f"{len(findings)} findings; {unknown} severity unreported; coverage {'incomplete' if incomplete_scan else 'reported'}")


def _schema_result(tool: str, r: CmdResult) -> CheckResult:
    if r.code != 0:
        return _simple(tool, r, tool)
    counts = re.findall(r"Valid:\s*(\d+), Invalid:\s*(\d+), Errors:\s*(\d+), Skipped:\s*(\d+)", r.text)
    if not counts:
        return _parse_failure(tool, r)
    valid, invalid, errors, skipped = map(sum, zip(*(tuple(map(int, c)) for c in counts)))
    if skipped or valid == 0:
        return _check(tool, "skipped", passed=False, skipped=True,
                      summary=f"{valid} validated, {skipped} skipped; supply missing CRD schemas using PHASE4_KUBERNETES_SCHEMA_LOCATION")
    return _check(tool, "findings" if invalid or errors else "passed", passed=not invalid and not errors,
                  summary=f"{valid} validated, {invalid} invalid, {errors} errors")
