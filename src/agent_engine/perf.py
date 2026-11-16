"""Opt-in structured performance diagnostics: JSON Lines events for one benchmark session.

Off by default. With ``AGENT_ENGINE_PERF=1`` every process of a run (the orchestrator and each
``agent-engine run`` child it starts) appends events to its own file under

    <AGENT_ENGINE_PERF_DIR or LOGS_DIR/perf>/<session>/events/<pid>-<start>-<rand>.jsonl

so concurrent processes never share a file handle. Inside a process one background thread drains a
queue and owns the file: helpers, worker-thread tools and the event loop only enqueue.

Correlation: ``session`` (the benchmark case, AGENT_ENGINE_PERF_SESSION, kept across CLI invocations and
approval stops), ``pipeline`` (one ``phase4 orchestrate`` invocation), ``invocation`` (one stage child /
``run``), then span ids with explicit parents. The active span lives in a ContextVar, never in one mutable
global, so parallel helpers (asyncio tasks) and synchronous tools (worker threads, which LangChain starts
with a copy of the caller's context) each see their own parent.

When disabled every public function returns at its first line and nothing is written. When the
diagnostics themselves fail (disk full, unwritable folder) the application's outcome is preserved: the
failure is counted, one bounded warning goes to stderr, and the session is marked incomplete.

Never logged: request text, prompts, tool arguments or outputs, environment values, credentials. Raw
command output, when kept, goes to ``raw/`` after known credentials are redacted.
"""

from __future__ import annotations

import asyncio
import atexit
import contextvars
import itertools
import json
import os
import queue
import re
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_engine import config

ENV_ENABLED = "AGENT_ENGINE_PERF"
ENV_DIR = "AGENT_ENGINE_PERF_DIR"
ENV_SESSION = "AGENT_ENGINE_PERF_SESSION"
ENV_PIPELINE = "AGENT_ENGINE_PERF_PIPELINE_ID"
ENV_PARENT_SPAN = "AGENT_ENGINE_PERF_PARENT_SPAN"
ENV_SAMPLE_SECONDS = "AGENT_ENGINE_PERF_SAMPLE_SECONDS"
ENV_RAW = "AGENT_ENGINE_PERF_RAW_OUTPUT"      # 1 (default when enabled) | 0: keep redacted raw command output
ENV_MODE = "AGENT_ENGINE_PERF_MODE"           # generation (default) | publication
# Set by the orchestrator for every child it starts, with or without diagnostics: the child stamps it into
# report.json so the orchestrator never mistakes an older report for the result of this invocation.
ENV_INVOCATION = "AGENT_ENGINE_INVOCATION_ID"

SCHEMA_VERSION = 1
DEFAULT_SAMPLE_SECONDS = 5.0
MAX_ERROR_CHARS = 300
_TRUE = {"1", "true", "yes", "on"}


def _env_true(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    return default if value is None or value.strip() == "" else value.strip().lower() in _TRUE


def new_id(n: int = 16) -> str:
    return uuid.uuid4().hex[:n]


def utc_iso(wall: float | None = None) -> str:
    return datetime.fromtimestamp(time.time() if wall is None else wall, timezone.utc).isoformat(timespec="microseconds")


# ============================================================================ redaction
_SECRET_PATTERNS = [re.compile(p) for p in (
    r"sk-ant-[A-Za-z0-9_\-]{8,}", r"\bsk-[A-Za-z0-9_\-]{16,}", r"gh[pousr]_[A-Za-z0-9]{20,}", r"github_pat_[A-Za-z0-9_]{20,}",
    r"xox[abposr]-[A-Za-z0-9-]{10,}", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b", r"lin_api_[A-Za-z0-9]{16,}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----",
    r"(?i)\bbearer\s+[A-Za-z0-9._~+/=\-]{12,}", r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{5,}",
    r"(?i)\b(password|passwd|secret|token|api[_-]?key|access[_-]?key)\b(\"?\s*[:=]\s*)\"?[^\s\"',;]{6,}",
)]
_SECRET_ENV_NAME = re.compile(r"(API_KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|PRIVATE_KEY|SA_JSON|ACCESS_KEY)", re.I)
_secret_values: list[str] | None = None


def _known_secret_values() -> list[str]:
    """Values of credential-like environment variables, longest first, for literal redaction. Read lazily and
    kept only in memory: they are used to scrub, never written."""
    global _secret_values
    if _secret_values is None:
        values = {v.strip() for k, v in os.environ.items() if _SECRET_ENV_NAME.search(k) and v and len(v.strip()) >= 8}
        _secret_values = sorted(values, key=len, reverse=True)
    return _secret_values


def redact(text: str) -> str:
    """Removes known credential values and credential-shaped strings."""
    if not text:
        return text
    for value in _known_secret_values():
        if value in text:
            text = text.replace(value, "[REDACTED]")
    for pat in _SECRET_PATTERNS:
        text = pat.sub(lambda m: (m.group(1) + m.group(2) + "[REDACTED]") if m.re.groups >= 2 and m.group(2) else "[REDACTED]",
                       text)
    return text


def classify_error(exc: BaseException) -> str:
    """A small, stable error category from the exception type (and message for rate limits)."""
    names = {c.__name__ for c in type(exc).__mro__}
    message = str(exc)
    if names & {"CancelledError", "KeyboardInterrupt"}:
        return "cancelled"
    if "SUBSCRIPTION_RATE_LIMITED" in message or any("RateLimit" in n for n in names) or "rate_limit" in message:
        return "rate_limit"
    if any("Timeout" in n for n in names):
        return "timeout"
    if names & {"ConnectError", "NetworkError", "APIConnectionError", "ConnectionError", "RemoteProtocolError"}:
        return "connection"
    if names & {"HTTPStatusError", "APIStatusError", "TrackerError"}:
        return "http_status"
    if "ProjectError" in names:
        return "project_error"
    if names & {"ValidationError", "ValueError", "TypeError", "KeyError"}:
        return "validation"
    return "other"


def error_summary(exc: BaseException | str) -> str:
    text = exc if isinstance(exc, str) else f"{type(exc).__name__}: {exc}"
    return redact(" ".join(str(text).split()))[:MAX_ERROR_CHARS]


def status_for(exc: BaseException) -> str:
    category = classify_error(exc)
    return {"cancelled": "cancelled", "timeout": "timeout"}.get(category, "error")


# ============================================================================ writer
_STOP = object()


class _Writer:
    """One file, one thread. ``put`` never blocks or raises; a failure is counted and reported once."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.queue: queue.SimpleQueue = queue.SimpleQueue()
        self.failed = False
        self.error: str | None = None
        self.dropped = 0
        self.written = 0
        self._warned = False
        self._thread = threading.Thread(target=self._loop, name="agent-engine-perf-writer", daemon=True)
        self._thread.start()

    def put(self, record: dict) -> None:
        if self.failed:
            self.dropped += 1
            return
        self.queue.put(record)

    def _fail(self, exc: BaseException) -> None:
        self.failed = True
        self.error = error_summary(exc)
        if not self._warned:
            self._warned = True
            try:
                sys.stderr.write(f"\n[perf] WARNING: diagnostics could not be written to {self.path} ({self.error}); "
                                 "this diagnostic run is INCOMPLETE. The run itself continues unchanged.\n")
            except Exception:  # noqa: BLE001
                pass
            _mark_incomplete(f"writer failed for {self.path.name}: {self.error}")

    def _loop(self) -> None:
        handle = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            handle = self.path.open("a", encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            self._fail(exc)
        stop = False
        while not stop:
            record = self.queue.get()
            batch = [record]
            while len(batch) < 1000:
                try:
                    batch.append(self.queue.get_nowait())
                except queue.Empty:
                    break
            lines = []
            for rec in batch:
                if rec is _STOP:
                    stop = True
                    continue
                if self.failed or handle is None:
                    self.dropped += 1
                    continue
                try:
                    lines.append(json.dumps(rec, default=str, ensure_ascii=False))
                except Exception:  # noqa: BLE001  (an unserializable attribute must not lose the event)
                    lines.append(json.dumps({k: str(v) for k, v in rec.items()}, ensure_ascii=False))
            if lines and handle is not None and not self.failed:
                try:
                    handle.write("\n".join(lines) + "\n")
                    handle.flush()
                    self.written += len(lines)
                except Exception as exc:  # noqa: BLE001
                    self.dropped += len(lines)
                    self._fail(exc)
        if handle is not None:
            try:
                handle.close()
            except Exception:  # noqa: BLE001
                pass

    def close(self, timeout: float = 10.0) -> None:
        self.queue.put(_STOP)
        self._thread.join(timeout)


# ============================================================================ state
class _State:
    def __init__(self) -> None:
        self.enabled = False
        self.session: str | None = None
        self.pipeline: str | None = None
        self.invocation: str | None = None
        self.root_parent: str | None = None
        self.dir: Path | None = None
        self.writer: _Writer | None = None
        self.process_span: Span | None = None
        self.sampler: _Sampler | None = None
        self.problems: list[str] = []
        self.raw_output = True
        self.open_spans: dict[str, tuple[str, str]] = {}
        self.lock = threading.Lock()


_S = _State()
_seq = itertools.count()
_PID = os.getpid()
_current: contextvars.ContextVar[str | None] = contextvars.ContextVar("agent_engine_perf_span", default=None)
# The model call in progress in this task, so a transport hook can attribute an HTTP attempt to it.
current_model_call: contextvars.ContextVar[str | None] = contextvars.ContextVar("agent_engine_perf_model_call",
                                                                                   default=None)


def enabled() -> bool:
    return _S.enabled


def session_dir() -> Path | None:
    return (_S.dir / _S.session) if _S.enabled and _S.dir and _S.session else None


def ids() -> dict:
    return {"session": _S.session, "pipeline": _S.pipeline, "invocation": _S.invocation}


def resolve_dir() -> Path:
    raw = os.environ.get(ENV_DIR)
    return Path(raw) if raw else Path(config.LOGS_DIR) / "perf"


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except (ValueError, OSError):
        return False


def separation_problems(perf_dir: Path) -> list[str]:
    """Diagnostics must stay out of what agents can read (/outputs/ = OUTPUTS_DIR, packs' knowledge and skills
    under AGENTS_DIR), what history fingerprints (project folders) and what gets published (project folders)."""
    problems = []
    outputs, agents = Path(config.OUTPUTS_DIR), Path(config.AGENTS_DIR)
    if _inside(perf_dir, outputs) or _inside(outputs, perf_dir):
        problems.append(f"diagnostics folder {perf_dir} overlaps the outputs folder {outputs} (agent-readable, "
                        "fingerprinted and published)")
    if _inside(perf_dir, agents) or _inside(agents, perf_dir):
        problems.append(f"diagnostics folder {perf_dir} overlaps the agent packs folder {agents} (agent-readable)")
    return problems


def _mark_incomplete(reason: str) -> None:
    _S.problems.append(reason)
    d = session_dir()
    if d is None:
        return
    try:
        d.mkdir(parents=True, exist_ok=True)
        with (d / f"INCOMPLETE-{_PID}.txt").open("a", encoding="utf-8") as f:
            f.write(f"{utc_iso()} {reason}\n")
    except Exception:  # noqa: BLE001
        pass


def init(command: str, *, force: bool | None = None, perf_dir: Path | None = None) -> bool:
    """Starts diagnostics for this process if AGENT_ENGINE_PERF is on. Returns whether they are on."""
    if _S.enabled:
        return True
    on = _env_true(ENV_ENABLED) if force is None else force
    if not on:
        return False
    target = perf_dir or resolve_dir()
    problems = separation_problems(target)
    if problems:
        sys.stderr.write("[perf] WARNING: diagnostics NOT enabled: " + "; ".join(problems)
                         + f". Set {ENV_DIR} to a folder outside them.\n")
        return False
    session = os.environ.get(ENV_SESSION) or f"{time.strftime('%Y%m%d-%H%M%S')}-{new_id(6)}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,80}", session):
        sys.stderr.write(f"[perf] WARNING: diagnostics NOT enabled: {ENV_SESSION}={session!r} must be letters, digits, "
                         "'.', '_' or '-'.\n")
        return False
    os.environ[ENV_SESSION] = session          # children started from here join the same session
    _S.session, _S.dir = session, target
    _S.pipeline = os.environ.get(ENV_PIPELINE) or None
    _S.invocation = os.environ.get(ENV_INVOCATION) or None
    _S.root_parent = os.environ.get(ENV_PARENT_SPAN) or None
    _S.raw_output = _env_true(ENV_RAW, default=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    events = target / session / "events" / f"{stamp}-{_PID}-{new_id(6)}.jsonl"
    _S.writer = _Writer(events)
    _S.enabled = True
    startup = _startup_timing()
    _S.process_span = start_span("process", command, parent=_S.root_parent,
                                 attrs={"argv_command": command, "python": sys.version.split()[0],
                                        "platform": sys.platform, "cpu_count": os.cpu_count(),
                                        "cpu_affinity": _affinity(), **startup})
    _current.set(_S.process_span.id)
    interval = float(os.environ.get(ENV_SAMPLE_SECONDS) or DEFAULT_SAMPLE_SECONDS)
    if interval > 0:
        _S.sampler = _Sampler(interval)
    atexit.register(shutdown)
    return True


def set_pipeline(pipeline_id: str) -> None:
    """The orchestrator owns the pipeline id; its children read it from the environment."""
    if not _S.enabled:
        return
    _S.pipeline = pipeline_id
    os.environ[ENV_PIPELINE] = pipeline_id


def child_env(parent_span: str | None) -> dict[str, str]:
    """Environment additions that put a child process into this session under ``parent_span``."""
    if not _S.enabled:
        return {}
    env = {ENV_ENABLED: "1", ENV_SESSION: _S.session or "", ENV_DIR: str(_S.dir)}
    if _S.pipeline:
        env[ENV_PIPELINE] = _S.pipeline
    if parent_span:
        env[ENV_PARENT_SPAN] = parent_span
    return env


def shutdown(exit_code: int | None = None) -> None:
    """Ends the process span, stops the sampler and drains the writer. Safe to call twice."""
    if not _S.enabled:
        return
    try:
        if _S.sampler is not None:
            _S.sampler.stop()
        if _S.process_span is not None and not _S.process_span.ended:
            open_spans = dict(_S.open_spans)
            open_spans.pop(_S.process_span.id, None)
            _S.process_span.end("ok" if not exit_code else "error",
                                exit_code=exit_code, open_child_spans=len(open_spans), **_resources())
        writer = _S.writer
        if writer is not None:
            if writer.failed or writer.dropped:
                _mark_incomplete(f"{writer.dropped} events dropped ({writer.error})")
            writer.close()
            if writer.dropped:
                try:
                    sys.stderr.write(f"[perf] WARNING: {writer.dropped} diagnostic events were not written "
                                     f"({writer.error}); the diagnostic run is incomplete.\n")
                except Exception:  # noqa: BLE001
                    pass
    finally:
        _S.enabled = False


def reset_for_tests() -> None:
    shutdown()
    global _S, _secret_values
    _S = _State()
    _secret_values = None
    _current.set(None)
    current_model_call.set(None)


# ============================================================================ events and spans
def _task_name() -> str | None:
    try:
        task = asyncio.current_task()
    except RuntimeError:
        return None
    return task.get_name() if task is not None else None


def _emit(ev: str, record: dict) -> None:
    writer = _S.writer
    if writer is None:
        return
    wall = time.time()
    record.update(v=SCHEMA_VERSION, ev=ev, ts=utc_iso(wall), wall=wall, mono=time.perf_counter(), pid=_PID,
                  seq=next(_seq), session=_S.session, pipeline=_S.pipeline, invocation=_S.invocation)
    writer.put(record)


def current_span_id() -> str | None:
    return _current.get() if _S.enabled else None


class Span:
    __slots__ = ("id", "parent", "kind", "name", "t0", "attrs", "ended", "_status", "_error", "_category", "_token")

    def __init__(self, kind: str, name: str, parent: str | None, attrs: dict) -> None:
        self.id = new_id()
        self.parent = parent
        self.kind = kind
        self.name = name
        self.t0 = time.perf_counter()
        self.attrs: dict = dict(attrs)       # the end record carries the start attributes too
        self.ended = False
        self._status: str | None = None
        self._error: str | None = None
        self._category: str | None = None
        self._token = None
        with _S.lock:
            _S.open_spans[self.id] = (kind, name)
        _emit("span_start", {"span": self.id, "parent": parent, "kind": kind, "name": name, "attrs": attrs,
                             "thread": threading.current_thread().name, "task": _task_name()})

    def set(self, **attrs: Any) -> "Span":
        self.attrs.update(attrs)
        return self

    def incr(self, key: str, by: float = 1) -> None:
        self.attrs[key] = self.attrs.get(key, 0) + by

    def set_status(self, status: str, error: str | None = None, category: str | None = None) -> None:
        """Overrides the status the span ends with (e.g. 'domain_error' for a tool that returned ERROR text)."""
        self._status, self._error, self._category = status, error, category

    def end(self, status: str = "ok", error: str | None = None, error_category: str | None = None, **attrs: Any) -> None:
        if self.ended:
            return
        self.ended = True
        dur = time.perf_counter() - self.t0
        self.attrs.update(attrs)
        if self._status is not None and status == "ok":
            status, error, error_category = self._status, self._error, self._category
        with _S.lock:
            _S.open_spans.pop(self.id, None)
        record = {"span": self.id, "parent": self.parent, "kind": self.kind, "name": self.name, "status": status,
                  "dur": dur, "attrs": self.attrs}
        if error is not None:
            record["error"] = error_summary(error)
        if error_category is not None:
            record["error_category"] = error_category
        _emit("span_end", record)

    def fail(self, exc: BaseException, **attrs: Any) -> None:
        self.end(status_for(exc), error=error_summary(exc), error_category=classify_error(exc), **attrs)

    # context-manager form: activates the span for code running inside the block
    def __enter__(self) -> "Span":
        self._token = _current.set(self.id)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if self._token is not None:
            try:
                _current.reset(self._token)
            except ValueError:   # exited in another context; restore the parent explicitly
                _current.set(self.parent)
            self._token = None
        if exc is not None:
            self.fail(exc)
        else:
            self.end()
        return False


class _NoopSpan:
    __slots__ = ()
    id = None
    parent = None
    ended = True
    attrs: dict = {}

    def set(self, **attrs: Any) -> "_NoopSpan":
        return self

    def incr(self, key: str, by: float = 1) -> None:
        pass

    def set_status(self, *a: Any, **k: Any) -> None:
        pass

    def end(self, *a: Any, **k: Any) -> None:
        pass

    def fail(self, *a: Any, **k: Any) -> None:
        pass

    def __enter__(self) -> "_NoopSpan":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


NOOP = _NoopSpan()
_UNSET = object()


def start_span(kind: str, name: str, *, parent: Any = _UNSET, attrs: dict | None = None) -> Span | _NoopSpan:
    """A span that is NOT activated: for callbacks and code that ends it elsewhere."""
    if not _S.enabled:
        return NOOP
    return Span(kind, name, _current.get() if parent is _UNSET else parent, dict(attrs or {}))


def span(kind: str, name: str, *, parent: Any = _UNSET, **attrs: Any) -> Span | _NoopSpan:
    """``with perf.span("solver", "sprint.main", stories=12) as sp: ...`` — activated for the block."""
    if not _S.enabled:
        return NOOP
    return Span(kind, name, _current.get() if parent is _UNSET else parent, attrs)


def event(kind: str, name: str, **attrs: Any) -> None:
    if not _S.enabled:
        return
    _emit("event", {"span": None, "parent": _current.get(), "kind": kind, "name": name, "attrs": attrs})


def activate(span_id: str | None) -> contextvars.Token:
    return _current.set(span_id)


def deactivate(token: contextvars.Token, fallback: str | None = None) -> None:
    try:
        _current.reset(token)
    except ValueError:
        _current.set(fallback)


# ============================================================================ raw outputs
def write_raw(span_id: str | None, label: str, text: str) -> str | None:
    """Keeps a command's complete output (credentials redacted) in raw/, returns its path relative to the
    session folder, or None when diagnostics or raw output are off."""
    d = session_dir()
    if d is None or not _S.raw_output or not span_id:
        return None
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", label)[:60]
    rel = f"raw/{span_id}-{safe}.txt"
    try:
        (d / "raw").mkdir(parents=True, exist_ok=True)
        (d / rel).write_text(redact(text), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        _mark_incomplete(f"raw output {rel} not written: {error_summary(exc)}")
        return None
    return rel


def url_parts(url: str) -> dict:
    """Host and path of a URL, without user info, query string or fragment."""
    try:
        import httpx

        u = httpx.URL(str(url))
        return {"host": u.host, "path": u.path}
    except Exception:  # noqa: BLE001
        return {"host": None, "path": None}


def http_span(service: str, operation: str, method: str, url: str, *, include_path: bool = False,
              **attrs: Any) -> Span | _NoopSpan:
    """A span for one logical HTTP request. Only the host (and the path where the caller says it holds no
    personal data) is kept; never headers, query strings or bodies."""
    if not _S.enabled:
        return NOOP
    parts = url_parts(url)
    if not include_path:
        parts.pop("path", None)
    return span("http", f"{service}.{operation}", service=service, operation=operation, method=method, **parts, **attrs)


def http_result(sp: Span | _NoopSpan, response: Any) -> None:
    if not _S.enabled or sp is NOOP:
        return
    try:
        size = len(response.content)
    except Exception:  # noqa: BLE001  (streamed or unread body)
        size = None
    sp.set(status_code=getattr(response, "status_code", None), response_bytes=size)


# ============================================================================ resources
def _affinity() -> int | None:
    try:
        return len(os.sched_getaffinity(0))  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        return None


def _windows_memory() -> dict:
    import ctypes
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

    counters = Counters()
    counters.cb = ctypes.sizeof(Counters)
    kernel32 = ctypes.WinDLL("kernel32")
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.WinDLL("psapi")
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    if not psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        return {}
    return {"rss_bytes": int(counters.WorkingSetSize), "peak_rss_bytes": int(counters.PeakWorkingSetSize)}


def _resources() -> dict:
    """This Python process only: CPU seconds and memory. Children (docker CLI, bash) are separate processes;
    containers run inside the Docker VM and are not visible here."""
    out: dict = {}
    try:
        t = os.times()
        out.update(cpu_user_s=round(t.user, 3), cpu_system_s=round(t.system, 3))
        if sys.platform != "win32":
            out.update(children_cpu_user_s=round(t.children_user, 3), children_cpu_system_s=round(t.children_system, 3))
    except Exception:  # noqa: BLE001
        pass
    try:
        if sys.platform == "win32":
            out.update(_windows_memory())
        else:
            import resource

            scale = 1 if sys.platform == "darwin" else 1024
            out["peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * scale
            out["children_peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss * scale
    except Exception:  # noqa: BLE001
        pass
    return out


def _startup_timing() -> dict:
    """Package import time, and interpreter start to here where the OS says when the process was created."""
    out: dict = {}
    t0 = getattr(sys.modules.get("agent_engine"), "_IMPORT_T0", None)
    if isinstance(t0, float):
        out["import_s"] = round(time.perf_counter() - t0, 4)
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            ft = [wintypes.FILETIME() for _ in range(4)]
            kernel32 = ctypes.WinDLL("kernel32")
            kernel32.GetCurrentProcess.restype = wintypes.HANDLE
            if kernel32.GetProcessTimes(kernel32.GetCurrentProcess(), *[ctypes.byref(f) for f in ft]):
                created = (ft[0].dwHighDateTime << 32 | ft[0].dwLowDateTime) / 1e7 - 11644473600
                out["since_process_created_s"] = round(time.time() - created, 4)
        except Exception:  # noqa: BLE001
            pass
    return out


class _Sampler:
    """Background samples of this process's CPU and memory every ``interval`` seconds."""

    def __init__(self, interval: float) -> None:
        self.interval = interval
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="agent-engine-perf-sampler", daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                _emit("sample", {"span": None, "parent": None, "kind": "resource", "name": "process",
                                 "attrs": {"interval_s": self.interval, "threads": threading.active_count(),
                                           **_resources()}})
            except Exception:  # noqa: BLE001
                pass

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(2)


def publication_blocked() -> str | None:
    """A diagnostic run is generation-only unless AGENT_ENGINE_PERF_MODE=publication was chosen explicitly."""
    if not _S.enabled:
        return None
    mode = (os.environ.get(ENV_MODE) or "generation").strip().lower()
    if mode == "publication":
        return None
    return (f"diagnostics are on in generation-only mode ({ENV_MODE}={mode}); publishing and coding-agent dispatch "
            f"are refused. Set {ENV_MODE}=publication only for a separately authorized publication benchmark.")
