"""Streams compact status lines from a diagnostics session's events (live, unbuffered)."""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

events_dir = Path(sys.argv[1])
heartbeat_s = float(sys.argv[2]) if len(sys.argv) > 2 else 120
offsets: dict[Path, int] = {}
partial: dict[Path, str] = {}
counts = {"model_calls": 0, "model_errors": 0, "in_tok": 0, "out_tok": 0, "cache_read": 0, "tools": 0,
          "tool_errors": 0, "helpers_running": 0}
open_helpers: set[str] = set()
current_stage = "-"
last_beat = time.time()
started = time.time()


def out(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def dur(e):
    d = e.get("dur") or 0
    return f"{d:.0f}s" if d < 120 else f"{d / 60:.1f}min"


def handle(e: dict) -> None:
    global current_stage
    ev, kind, name, a = e.get("ev"), e.get("kind"), e.get("name"), e.get("attrs") or {}
    status = e.get("status")
    if ev == "span_start":
        if kind == "pipeline":
            out(f"PIPELINE start (test_approve={a.get('test_approve')})")
        elif kind == "stage":
            current_stage = name
            out(f"STAGE START {name}")
        elif kind == "pass":
            out(f"  pass start  {name} attempt {a.get('attempt')} ({a.get('model_tier')}: {a.get('model')})")
        elif kind == "helper":
            open_helpers.add(e["span"])
            out(f"    helper start {name} (running now: {len(open_helpers)})")
        elif kind == "command" and a.get("tool"):
            out(f"    sandbox {a.get('tool')} {a.get('category')} env={a.get('env') or '-'} attempt={a.get('attempt')}")
    elif ev == "span_end":
        if kind == "model_call":
            counts["model_calls"] += 1
            counts["in_tok"] += a.get("input_tokens") or 0
            counts["out_tok"] += a.get("output_tokens") or 0
            counts["cache_read"] += a.get("cache_read_tokens") or 0
            if status != "ok":
                counts["model_errors"] += 1
                out(f"    MODEL CALL {status}: {e.get('error_category')} {(e.get('error') or '')[:160]}")
        elif kind in ("tool", "tool_exec"):
            if kind == "tool":
                counts["tools"] += 1
            if status not in ("ok", None) and kind == "tool":
                counts["tool_errors"] += 1
                out(f"    tool {name} -> {status}: {(e.get('error') or '')[:140]}")
        elif kind == "helper":
            open_helpers.discard(e["span"])
            out(f"    helper end   {name} {status} after {dur(e)} (running now: {len(open_helpers)})")
        elif kind == "pass":
            out(f"  pass end    {name} {status} after {dur(e)}" + (f" — {e.get('error')[:160]}" if e.get("error") else ""))
        elif kind == "stage":
            out(f"STAGE END   {name}: {a.get('status')} exit={a.get('exit_code')} after {dur(e)} "
                f"(write {a.get('writes')}, verify {a.get('verifies')}, fix {a.get('fixes')})")
        elif kind == "child" and status != "ok":
            out(f"CHILD {name} {status}: {a.get('report_problem') or e.get('error') or ''}")
        elif kind == "solver" and name in ("sprint.cpsat", "allocation.cpsat", "sprint.core_extraction"):
            out(f"    solver {name} {a.get('purpose', '')} -> {a.get('status')} in {e.get('dur', 0):.1f}s")
        elif kind == "solver_backend":
            out(f"    allocation backend {a.get('selected')} ({a.get('reason')}) -> {a.get('status')}")
        elif kind == "pipeline":
            out(f"PIPELINE end: {a.get('outcome')} after {dur(e)}")
        elif kind == "process" and status != "ok":
            out(f"PROCESS {name} ended {status} exit={a.get('exit_code')}")
    elif ev == "event":
        if kind == "verdict":
            if a.get("verifier_failed"):
                out(f"  VERDICT attempt {a.get('attempt')}: verifier FAILED {a.get('error', '')[:140]}")
            else:
                out(f"  VERDICT attempt {a.get('attempt')}: {a.get('effective_status')} (satisfied={a.get('satisfied')}, "
                    f"gaps={a.get('gaps')}{', INCONSISTENT' if a.get('inconsistent') else ''})")
        elif kind == "gate_decision":
            out(f"GATE {name} {a.get('decision')} ({'automated TEST approval' if a.get('automated') else 'human'})")
        elif kind == "approval_wait_start":
            out(f"WAITING for gates {a.get('gates')}")
        elif kind == "check_result":
            out(f"    check {name}: {a.get('outcome')} findings={a.get('findings')}")
        elif kind == "solver_unsuccessful":
            out(f"    SOLVER UNSUCCESSFUL {a}")
        elif kind == "http_attempt" and name == "model.response" and (a.get("status_code") or 200) >= 400:
            out(f"    model HTTP {a.get('status_code')} (sdk retry #{a.get('sdk_retry_count')}, retry-after {a.get('retry_after')})")


if len(sys.argv) > 3 and sys.argv[3] == "tail" and events_dir.is_dir():
    for f in events_dir.glob("*.jsonl"):
        offsets[f] = f.stat().st_size          # report only what happens from now on
out(f"watching {events_dir}")
while True:
    if events_dir.is_dir():
        for f in sorted(events_dir.glob("*.jsonl")):
            pos = offsets.get(f, 0)
            size = f.stat().st_size
            if size <= pos:
                continue
            with f.open("r", encoding="utf-8", errors="replace") as fh:
                fh.seek(pos)
                chunk = fh.read()
                offsets[f] = fh.tell()
            data = partial.pop(f, "") + chunk
            lines = data.split("\n")
            if not data.endswith("\n"):
                partial[f] = lines.pop()
            for line in lines:
                if line.strip():
                    try:
                        handle(json.loads(line))
                    except ValueError:
                        pass
    if time.time() - last_beat >= heartbeat_s:
        last_beat = time.time()
        c = counts
        out(f"heartbeat: stage={current_stage} | model calls {c['model_calls']} ({c['model_errors']} err) | "
            f"tokens in {c['in_tok']:,} / out {c['out_tok']:,} / cache-read {c['cache_read']:,} | "
            f"tool calls {c['tools']} ({c['tool_errors']} err) | helpers running {len(open_helpers)}")
    time.sleep(2)
