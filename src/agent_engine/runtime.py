"""Project ownership and atomic persistence shared by the CLI and domain tools."""
from __future__ import annotations

import contextvars
import json
import os
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path

active_project: contextvars.ContextVar[str | None] = contextvars.ContextVar("active_project", default=None)
active_inputs: contextvars.ContextVar[frozenset[str]] = contextvars.ContextVar("active_inputs", default=frozenset())
managed_outputs: contextvars.ContextVar[frozenset[str]] = contextvars.ContextVar("managed_outputs", default=frozenset())
_locks: dict[str, threading.RLock] = {}
_guard = threading.Lock()
_owned = threading.local()


@contextmanager
def project_scope(project: str):
    from agent_engine.phase4.calendars import snapshot_cache
    calendar_token = snapshot_cache.set({})
    token = active_project.set(project)
    input_token = active_inputs.set(frozenset())
    managed_token = managed_outputs.set(frozenset())
    try:
        yield
    finally:
        active_project.reset(token)
        active_inputs.reset(input_token)
        managed_outputs.reset(managed_token)
        snapshot_cache.reset(calendar_token)


def atomic_text(path: Path, text: str) -> None:
    """Readers see either the old complete file or the new complete file, on every OS."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        os.chmod(tmp, (path.stat().st_mode & 0o777) if path.exists() else 0o644)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def atomic_json(path: Path, value) -> None:
    atomic_text(path, json.dumps(value, indent=2, default=str) + "\n")


@contextmanager
def project_lock(root: Path, name: str = "job", timeout: float = 120):
    """OS-released lease plus an in-process RLock; no stale lock-file deletion races.

    Callers that launch stage children use a separate 'orchestrator' lease. A parent
    never holds the job lease while waiting for a child that needs that same lease.
    """
    key = str(root.resolve()) + ":" + name
    held = getattr(_owned, "held", set())
    if key in held:
        yield
        return
    with _guard:
        lock = _locks.setdefault(key, threading.RLock())
    if not lock.acquire(timeout=timeout):
        raise TimeoutError(f"project {root.name} is busy ({name})")
    handle = None
    try:
        root.mkdir(parents=True, exist_ok=True)
        handle = (root / f".engine-{name}.lock").open("a+b")
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        deadline = time.monotonic() + timeout
        while True:
            try:
                if os.name == "nt":
                    import msvcrt
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except (BlockingIOError, OSError):
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"project {root.name} is busy ({name})") from None
                time.sleep(0.05)
        _owned.held = held | {key}
        yield
    finally:
        _owned.held = held
        if handle is not None:
            handle.close()
        lock.release()
