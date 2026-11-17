"""Bound owned validation workspaces. Caller must hold the provider-cache lease."""
from __future__ import annotations

import os
import re
import shutil
import time
from pathlib import Path

from agent_engine import perf


def prune_validation_cache(root: Path, *, keep: Path) -> list[str]:
    days = float(os.environ.get("PHASE4_IAC_CACHE_TTL_DAYS", "14"))
    limit = int(os.environ.get("PHASE4_IAC_CACHE_MAX_BYTES", str(2 * 1024**3)))
    if days < 0 or limit < 0:
        raise ValueError("cache TTL and byte limit must be nonnegative (zero disables that limit)")
    entries = []
    for directory in (root / "validation").glob("*"):
        marker = directory / ".engine-cache-owned"
        if (directory.is_symlink() or not directory.is_dir() or not re.fullmatch(r"[0-9a-f]{64}", directory.name)
                or marker.is_symlink() or not marker.is_file()
                or marker.read_text(encoding="utf-8") != "phase4-validation-v1\n"):
            continue
        size = sum(p.stat().st_size for p in directory.rglob("*") if p.is_file() and not p.is_symlink())
        entries.append((marker.stat().st_mtime, directory, size))
    total, removed = sum(e[2] for e in entries), []
    for touched, directory, size in sorted(entries):
        if directory == keep:
            continue
        if (days and time.time() - touched > days * 86400) or (limit and total > limit):
            shutil.rmtree(directory)
            total -= size
            removed.append(directory.name)
    perf.event("cache", "validation_retention", removed=len(removed), retained_bytes=total,
               limit_bytes=limit, ttl_days=days)
    return removed
