"""Offline summary of a diagnostic session: reads <session>/events/*.jsonl (complete or partial), never calls a
model or the network, and writes <session>/summary.md and summary.json.

Duration accounting. Spans nest and overlap (a tool contains a solver, a pass contains parallel helpers, helper
model calls overlap), so durations are never simply added up as wall time:

* "elapsed" is wall-clock time from start to end of one span;
* "exclusive wall time" splits a stage's elapsed time by category with a priority order — each instant is
  counted once, for the highest-priority category active at that instant (model call > service wait > external
  command > solver > deterministic tool > agent build > file system > diagnostics); what no span covers is
  reported as unattributed;
* "summed work" adds durations and is labelled as such: with concurrency it exceeds elapsed time.

No percentages beyond what the numbers support, no cost estimates.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from agent_engine import perf

PRIORITY = ("model_call", "service_wait", "command", "solver", "tool_exec", "agent_build", "fs", "diagnostics")
CATEGORY_OF_KIND = {"model_call": "model_call", "service_wait": "service_wait", "command": "command",
                    "solver": "solver", "tool_exec": "tool_exec", "tool": "tool_exec", "http": "service_wait",
                    "calendar": "service_wait", "agent_build": "agent_build", "model_setup": "agent_build",
                    "fs": "fs", "diagnostics": "diagnostics", "compute": "tool_exec"}
TOKEN_KEYS = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens", "reasoning_tokens")


# ============================================================================ loading
def load(session_dir: Path) -> dict:
    events, corrupt, files = [], 0, []
    for path in sorted((session_dir / "events").glob("*.jsonl")):
        files.append(path.name)
        with path.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    corrupt += 1          # e.g. the last line of a process that was killed mid-write
                    continue
                rec["_file"] = path.name
                events.append(rec)
    manifests = []
    for path in sorted((session_dir / "manifests").glob("*.json")) if (session_dir / "manifests").is_dir() else []:
        try:
            manifests.append(json.loads(path.read_text(encoding="utf-8")))
        except ValueError:
            corrupt += 1
    incomplete_notes = []
    for path in sorted(session_dir.glob("INCOMPLETE-*.txt")):
        incomplete_notes += [ln for ln in path.read_text(encoding="utf-8", errors="replace").splitlines() if ln]
    return {"events": events, "corrupt_lines": corrupt, "files": files, "manifests": manifests,
            "incomplete_notes": incomplete_notes}


class Span:
    __slots__ = ("id", "parent", "kind", "name", "pid", "file", "start", "end", "dur", "status", "attrs",
                 "error", "error_category", "complete", "children")

    def __init__(self, rec: dict) -> None:
        self.id, self.parent, self.kind, self.name = rec["span"], rec.get("parent"), rec.get("kind"), rec.get("name")
        self.pid, self.file = rec.get("pid"), rec.get("_file")
        self.start = rec["wall"]
        self.end: float | None = None
        self.dur: float | None = None
        self.status = "incomplete"
        self.attrs = dict(rec.get("attrs") or {})
        self.error = self.error_category = None
        self.complete = False
        self.children: list[Span] = []

    @property
    def interval(self) -> tuple[float, float]:
        return self.start, self.end if self.end is not None else self.start


def build(data: dict) -> dict:
    spans: dict[str, Span] = {}
    points, samples = [], []
    last_wall_by_file: dict[str, float] = {}
    for rec in data["events"]:
        last_wall_by_file[rec["_file"]] = max(last_wall_by_file.get(rec["_file"], 0), rec.get("wall", 0))
        ev = rec.get("ev")
        if ev == "span_start":
            spans[rec["span"]] = Span(rec)
        elif ev == "span_end":
            sp = spans.get(rec["span"])
            if sp is None:              # start lost (e.g. writer failed early): rebuild from the end record
                sp = Span({**rec, "wall": rec["wall"] - rec.get("dur", 0)})
                spans[rec["span"]] = sp
            sp.dur = rec.get("dur")
            sp.end = sp.start + (sp.dur or 0)
            sp.status = rec.get("status", "ok")
            sp.attrs.update(rec.get("attrs") or {})
            sp.error, sp.error_category = rec.get("error"), rec.get("error_category")
            sp.complete = True
        elif ev == "sample":
            samples.append(rec)
        elif ev == "event":
            points.append(rec)
    for sp in spans.values():
        if not sp.complete:            # open until the last thing its process wrote
            sp.end = max(sp.start, last_wall_by_file.get(sp.file, sp.start))
            sp.dur = sp.end - sp.start
    for sp in spans.values():
        if sp.parent in spans:
            spans[sp.parent].children.append(sp)
    return {"spans": spans, "points": points, "samples": samples}


def descendants(sp: Span) -> list[Span]:
    out, stack = [], list(sp.children)
    while stack:
        s = stack.pop()
        out.append(s)
        stack.extend(s.children)
    return out


# ============================================================================ interval arithmetic
def union(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    merged: list[list[float]] = []
    for a, b in sorted(i for i in intervals if i[1] > i[0]):
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return [(a, b) for a, b in merged]


def length(intervals: list[tuple[float, float]]) -> float:
    return sum(b - a for a, b in intervals)


def clip(intervals: list[tuple[float, float]], lo: float, hi: float) -> list[tuple[float, float]]:
    return [(max(a, lo), min(b, hi)) for a, b in intervals if min(b, hi) > max(a, lo)]


def subtract(a: list[tuple[float, float]], b: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out = []
    for s, e in a:
        cur = s
        for bs, be in b:
            if be <= cur or bs >= e:
                continue
            if bs > cur:
                out.append((cur, bs))
            cur = max(cur, be)
        if cur < e:
            out.append((cur, e))
    return out


def max_concurrency(intervals: list[tuple[float, float]]) -> int:
    points = sorted([(a, 1) for a, b in intervals] + [(b, -1) for a, b in intervals], key=lambda p: (p[0], p[1]))
    cur = best = 0
    for _, d in points:
        cur += d
        best = max(best, cur)
    return best


def exclusive_breakdown(root: Span, spans: list[Span]) -> dict:
    lo, hi = root.interval
    covered: list[tuple[float, float]] = []
    exclusive, summed, counts = {}, defaultdict(float), defaultdict(int)
    by_cat: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for s in spans:
        cat = CATEGORY_OF_KIND.get(s.kind)
        if cat:
            by_cat[cat].append(s.interval)
            summed[cat] += s.dur or 0
            counts[cat] += 1
    for cat in PRIORITY:
        u = union(clip(by_cat.get(cat, []), lo, hi))
        own = subtract(u, covered)
        exclusive[cat] = round(length(own), 3)
        covered = union(covered + u)
    total = hi - lo
    return {"elapsed_s": round(total, 3), "exclusive_wall_s": exclusive,
            "unattributed_s": round(max(0.0, total - length(covered)), 3),
            "summed_work_s": {k: round(v, 3) for k, v in summed.items()}, "span_counts": dict(counts)}


# ============================================================================ analysis
def _fmt(seconds: float | None) -> str:
    if seconds is None:
        return "-"
    if seconds < 60:
        return f"{seconds:.2f} s" if seconds < 10 else f"{seconds:.1f} s"
    m, s = divmod(int(round(seconds)), 60)
    if m < 60:
        return f"{m} min {s:02d} s"
    h, m = divmod(m, 60)
    return f"{h} h {m:02d} min"


def _iso(wall: float | None) -> str:
    return datetime.fromtimestamp(wall).astimezone().isoformat(timespec="seconds") if wall else "-"


def _parse_iso(text: str | None) -> float | None:
    if not text:
        return None
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return None


def _tokens(calls: list[Span]) -> dict:
    out: dict = {}
    for key in TOKEN_KEYS:
        vals = [c.attrs.get(key) for c in calls]
        reported = [v for v in vals if isinstance(v, (int, float))]
        out[key] = {"sum": sum(reported), "calls_reporting": len(reported), "calls_not_reporting": len(vals) - len(reported)}
    return out


def analyze(session_dir: Path) -> dict:
    data = load(session_dir)
    tree = build(data)
    spans: dict[str, Span] = tree["spans"]
    points = tree["points"]
    all_spans = list(spans.values())
    by_kind: dict[str, list[Span]] = defaultdict(list)
    for s in all_spans:
        by_kind[s.kind].append(s)
    # --- pipelines, active time, human waiting
    pipelines = sorted(by_kind.get("pipeline", []), key=lambda s: s.start)
    # Top-level CLI processes (a stage child runs inside its orchestrator's interval). Each starts where the OS
    # says the process was created (Windows) or where the package import began, both measured in-process.
    roots = [s for s in by_kind.get("process", []) if s.parent not in spans]

    def startup(s: Span) -> float:
        return float(s.attrs.get("since_process_created_s") or s.attrs.get("import_s") or 0)

    active = union([(s.start - startup(s), s.interval[1]) for s in roots])
    walls = [r["wall"] for r in data["events"] if "wall" in r] + [a for a, _ in active]
    first, last = (min(walls), max(walls)) if walls else (None, None)
    waits = _human_waits(points)
    measured_wait = sum(w["wait_s"] for w in waits if w["wait_s"] is not None)

    # --- stages
    children_by_invocation = {s.attrs.get("invocation_id"): s for s in by_kind.get("child", [])}
    stages = []
    for st in sorted(by_kind.get("stage", []), key=lambda s: s.start):
        stages.append(_stage_row(st, children_by_invocation.get(st.attrs.get("invocation_id")), points))

    # --- details
    calls = by_kind.get("model_call", [])
    slow_calls = sorted(calls, key=lambda s: s.dur or 0, reverse=True)[:10]
    big_context = sorted([c for c in calls if isinstance(c.attrs.get("input_tokens"), (int, float))],
                         key=lambda c: c.attrs["input_tokens"], reverse=True)[:10]
    ops = [s for s in all_spans if s.kind in ("tool_exec", "command", "http", "solver", "service_wait")]
    slow_ops = sorted(ops, key=lambda s: s.dur or 0, reverse=True)[:10]
    helpers = sorted(by_kind.get("helper", []), key=lambda s: s.start)
    incomplete = [s for s in all_spans if not s.complete]

    result = {
        "session": session_dir.name, "generated_at": perf.utc_iso(),
        "evidence": {"event_files": data["files"], "events": len(data["events"]), "corrupt_lines": data["corrupt_lines"],
                     "incomplete_notes": data["incomplete_notes"], "manifests": len(data["manifests"])},
        "revisions": _revisions(data["manifests"]),
        "overview": {
            "first_event": _iso(first), "last_event": _iso(last),
            "session_elapsed_s": round(last - first, 3) if walls else None,
            "active_execution_s": round(length(active), 3),
            "active_basis": f"{len(roots)} top-level CLI processes, from process start to exit",
            "startup_s": round(sum(startup(s) for s in roots), 3),
            "human_wait_measured_s": round(measured_wait, 3),
            "human_waits": waits,
            "unexplained_s": round(max(0.0, (last - first) - length(active) - measured_wait), 3) if walls else None,
            "pipelines": [{"pipeline_id": p.attrs.get("pipeline_id"), "start": _iso(p.start), "elapsed_s": round(p.dur or 0, 3),
                           "outcome": p.attrs.get("outcome"), "status": p.status, "complete": p.complete,
                           "test_approve": p.attrs.get("test_approve")} for p in pipelines],
            "status": (pipelines[-1].attrs.get("outcome") or pipelines[-1].status) if pipelines else
                      (stages[-1]["outcome"] if stages else "unknown"),
            "diagnostics_complete": not incomplete and not data["incomplete_notes"] and not data["corrupt_lines"],
        },
        "stages": stages,
        "slowest_model_calls": [_call_row(c, spans) for c in slow_calls],
        "largest_context_calls": [_call_row(c, spans) for c in big_context],
        "slowest_operations": [_op_row(s) for s in slow_ops],
        "helpers": _helpers(helpers),
        "solvers": [_op_row(s) for s in sorted(by_kind.get("solver", []) + by_kind.get("solver_backend", []),
                                                 key=lambda s: s.start)],
        "infrastructure": _infra(by_kind.get("command", []), points),
        "http": _http(by_kind.get("http", []), by_kind.get("service_wait", []), points),
        "filesystem": _group(by_kind.get("fs", []), ("files", "bytes", "files_copied", "bytes_copied", "inputs")),
        "locks": _locks(points),
        "diagnostics_overhead": _group(by_kind.get("diagnostics", []), ()),
        "resources": _resources(by_kind.get("process", []), tree["samples"]),
        "incomplete_spans": [{"kind": s.kind, "name": s.name, "started": _iso(s.start), "open_for_s": round(s.dur or 0, 3),
                              "span": s.id, "pid": s.pid} for s in sorted(incomplete, key=lambda s: s.start)],
        "failures": [{"kind": s.kind, "name": s.name, "status": s.status, "error_category": s.error_category,
                      "error": s.error, "span": s.id, "raw_output": s.attrs.get("raw_output")}
                     for s in sorted(all_spans, key=lambda s: s.start)
                     if s.complete and s.status not in ("ok",) and s.kind != "process"],
        "visibility": _visibility(calls, by_kind.get("agent_build", []), points, stages, waits, incomplete,
                                  has_timefold=bool(by_kind.get("service_wait"))),
    }
    return result


def _revisions(manifests: list[dict]) -> list[dict]:
    seen, out = set(), []
    for m in manifests:
        src = m.get("source") or {}
        key = (src.get("head"), src.get("diff_sha256"), m.get("lockfile_sha256"))
        if src and key not in seen:
            seen.add(key)
            out.append({"head": src.get("head"), "branch": src.get("branch"), "dirty": src.get("dirty"),
                        "diff_sha256": src.get("diff_sha256"), "merge_base_main": src.get("merge_base_main"),
                        "lockfile_sha256": m.get("lockfile_sha256"), "execution_mode": m.get("execution_mode")})
    return out


def _human_waits(points: list[dict]) -> list[dict]:
    starts = [p for p in points if p.get("kind") == "approval_wait_start"]
    decisions = []
    for p in points:
        if p.get("kind") == "gate_decision":
            decisions.append({"gate": p.get("name"), "wall": p["wall"], "automated": p["attrs"].get("automated"),
                              "basis": "gate command event" if not p["attrs"].get("automated") else "automated test approval"})
        elif p.get("kind") == "approval_observed":
            decided = _parse_iso(p["attrs"].get("decided_at"))
            if decided:
                decisions.append({"gate": p.get("name"), "wall": decided, "automated": p["attrs"].get("automated"),
                                  "basis": "approval record decided_at (1 s resolution)"})
    out = []
    for s in sorted(starts, key=lambda p: p["wall"]):
        for gate in s["attrs"].get("gates") or []:
            after = sorted((d for d in decisions if d["gate"] == gate and d["wall"] >= s["wall"] - 1),
                           key=lambda d: (d["wall"], d["basis"] != "gate command event"))
            d = after[0] if after else None
            out.append({"gate": gate, "wait_started": _iso(s["wall"]),
                        "decided": _iso(d["wall"]) if d else None,
                        "wait_s": round(max(0.0, d["wall"] - s["wall"]), 3) if d else None,
                        "basis": d["basis"] if d else "not measured: no decision evidence in this session",
                        "automated": d["automated"] if d else None})
    return out


def _stage_row(st: Span, child: Span | None, points: list[dict]) -> dict:
    desc = descendants(st)
    kinds: dict[str, list[Span]] = defaultdict(list)
    for d in desc:
        kinds[d.kind].append(d)
    passes = kinds.get("pass", [])
    per_kind = {}
    for pk in ("write", "verify", "fix"):
        ps = [p for p in passes if p.attrs.get("pass_kind") == pk]
        per_kind[pk] = {"count": len(ps), "elapsed_s": round(sum(p.dur or 0 for p in ps), 3),
                        "failed": sum(p.status != "ok" for p in ps)}
    calls = kinds.get("model_call", [])
    lo, hi = st.interval
    stage_points = [p for p in points if p.get("pid") == st.pid and lo - 1 <= p["wall"] <= hi + 1]
    verdicts = [p["attrs"] for p in stage_points if p.get("kind") == "verdict"]
    model_http = [p for p in stage_points if p.get("kind") == "http_attempt" and p.get("name") == "model.response"]
    helper_iv = [h.interval for h in kinds.get("helper", [])]
    tools = kinds.get("tool", []) + kinds.get("tool_exec", [])
    usage = next((p["attrs"].get("tokens") for p in stage_points if p.get("kind") == "usage_aggregate"), None)
    return {
        "agent": st.name, "invocation_id": st.attrs.get("invocation_id"), "job_id": st.attrs.get("job_id"),
        "started": _iso(st.start), "elapsed_s": round(st.dur or 0, 3),
        "child_process_elapsed_s": round(child.dur, 3) if child and child.dur is not None else None,
        "child_spawn_s": child.attrs.get("spawn_s") if child else None,
        "outcome": st.attrs.get("status") or st.status, "exit_code": st.attrs.get("exit_code"),
        "report_problem": child.attrs.get("report_problem") if child else None, "complete": st.complete,
        "passes": per_kind, "verdicts": verdicts,
        "model_calls": len(calls), "model_call_errors": sum(c.status != "ok" for c in calls),
        "compaction_calls": sum(bool(c.attrs.get("compaction")) for c in calls),
        "tokens": _tokens(calls), "usage_aggregate": usage, "usage_reconciliation": _reconcile(calls, usage),
        "tool_calls": len(kinds.get("tool", [])), "tool_domain_errors": sum(t.status == "domain_error" for t in tools),
        "deterministic_tool_executions": len(kinds.get("tool_exec", [])),
        "helpers": len(helper_iv), "helper_max_concurrency": max_concurrency(helper_iv),
        "model_http_attempts": len(model_http),
        "model_http_retries_seen": sum(1 for p in model_http if (p["attrs"].get("sdk_retry_count") or 0) > 0),
        "model_http_non_2xx": sum(1 for p in model_http if (p["attrs"].get("status_code") or 0) >= 300),
        "breakdown": exclusive_breakdown(st, desc),
    }


def _reconcile(calls: list[Span], usage: dict | None) -> dict:
    if not usage:
        return {"status": "no aggregate recorded"}
    agg_in = sum((u or {}).get("input_tokens", 0) for u in usage.values())
    agg_out = sum((u or {}).get("output_tokens", 0) for u in usage.values())
    per_in = sum(c.attrs.get("input_tokens") or 0 for c in calls)
    per_out = sum(c.attrs.get("output_tokens") or 0 for c in calls)
    return {"status": "match" if (agg_in, agg_out) == (per_in, per_out) else "mismatch",
            "aggregate": {"input": agg_in, "output": agg_out}, "per_call_sum": {"input": per_in, "output": per_out}}


def _call_row(c: Span, spans: dict[str, Span]) -> dict:
    stage = c
    while stage is not None and stage.kind != "stage":
        stage = spans.get(stage.parent) if stage.parent else None
    return {"elapsed_s": round(c.dur or 0, 3), "model": c.attrs.get("model"), "tier": c.attrs.get("tier"),
            "stage": stage.name if stage else None, "helper_type": c.attrs.get("helper_type"),
            "messages": c.attrs.get("messages"), "compaction": c.attrs.get("compaction"),
            **{k: c.attrs.get(k) for k in TOKEN_KEYS}, "finish_reason": c.attrs.get("finish_reason"),
            "time_to_first_chunk_s": c.attrs.get("time_to_first_chunk_s"), "status": c.status, "span": c.id}


def _op_row(s: Span) -> dict:
    keep = ("tool", "category", "env", "attempt", "exit_code", "timed_out", "status_code", "purpose", "candidate",
            "transformation", "time_limit_s", "workers", "variables", "constraints", "selected", "reason",
            "requested_mode", "polls", "sleep_s", "objective", "best_bound", "core_size", "solver_wall_s",
            "service", "operation", "attempts", "raw_output", "validation_scope", "executor", "feasible")
    attrs = {k: s.attrs[k] for k in keep if k in s.attrs}
    if "status" in s.attrs:
        attrs["result_status"] = s.attrs["status"]
    return {"kind": s.kind, "name": s.name, "elapsed_s": round(s.dur or 0, 3), "status": s.status,
            "complete": s.complete, **attrs}


def _helpers(helpers: list[Span]) -> dict:
    iv = [h.interval for h in helpers]
    t0 = helpers[0].start if helpers else 0
    return {"count": len(helpers), "max_concurrency": max_concurrency(iv),
            "elapsed_union_s": round(length(union(iv)), 3), "summed_s": round(sum(h.dur or 0 for h in helpers), 3),
            "timeline": [{"type": h.attrs.get("subagent_type") or h.name, "start_offset_s": round(h.start - t0, 3),
                          "elapsed_s": round(h.dur or 0, 3), "status": h.status} for h in helpers]}


def _infra(commands: list[Span], points: list[dict]) -> dict:
    groups: dict[tuple, dict] = {}
    for c in commands:
        key = (c.attrs.get("tool") or c.name, c.attrs.get("category"), c.attrs.get("env"), c.attrs.get("attempt"))
        g = groups.setdefault(key, {"tool": key[0], "category": key[1], "env": key[2], "attempt": key[3], "runs": 0,
                                    "elapsed_s": 0.0, "exit_codes": [], "timed_out": 0, "executor": c.attrs.get("executor"),
                                    "raw_outputs": []})
        g["runs"] += 1
        g["elapsed_s"] = round(g["elapsed_s"] + (c.dur or 0), 3)
        g["exit_codes"].append(c.attrs.get("exit_code"))
        g["timed_out"] += bool(c.attrs.get("timed_out"))
        if c.attrs.get("raw_output"):
            g["raw_outputs"].append(c.attrs["raw_output"])
    outcomes = [{"tool": p.get("name"), **{k: p["attrs"].get(k) for k in ("outcome", "passed", "skipped", "findings",
                                                                          "validation_scope", "reason")}}
                for p in points if p.get("kind") == "check_result"]
    return {"commands": sorted(groups.values(), key=lambda g: -g["elapsed_s"]), "check_outcomes": outcomes,
            "env_results": [p["attrs"] | {"tool": p.get("name")} for p in points if p.get("kind") == "check_env"],
            "note": "Static checks of generated files only; nothing here plans, applies or verifies a deployment."}


def _http(http: list[Span], waits: list[Span], points: list[dict]) -> dict:
    groups: dict[str, dict] = {}
    for h in http:
        g = groups.setdefault(h.name, {"name": h.name, "requests": 0, "elapsed_s": 0.0, "statuses": defaultdict(int),
                                       "failed": 0, "attempts": 0, "throttle_wait_s": 0.0, "retry_backoff_s": 0.0})
        g["requests"] += 1
        g["elapsed_s"] = round(g["elapsed_s"] + (h.dur or 0), 3)
        g["statuses"][str(h.attrs.get("status_code"))] += 1
        g["failed"] += h.status != "ok"
        g["attempts"] += h.attrs.get("attempts") or 1
        g["throttle_wait_s"] = round(g["throttle_wait_s"] + (h.attrs.get("throttle_wait_s") or 0), 3)
        g["retry_backoff_s"] = round(g["retry_backoff_s"] + (h.attrs.get("retry_backoff_s") or 0), 3)
    for g in groups.values():
        g["statuses"] = dict(g["statuses"])
    model_attempts = [p for p in points if p.get("kind") == "http_attempt" and p.get("name") == "model.response"]
    per_call: dict = defaultdict(int)
    for p in model_attempts:
        per_call[p["attrs"].get("model_call")] += 1
    return {"requests": sorted(groups.values(), key=lambda g: -g["elapsed_s"]),
            "polling": [_op_row(w) for w in waits],
            "model_transport": {"attempts": len(model_attempts),
                                "statuses": dict(_count(str(p["attrs"].get("status_code")) for p in model_attempts)),
                                "calls_with_multiple_attempts": sum(1 for v in per_call.values() if v > 1),
                                "sdk_retry_attempts": sum(1 for p in model_attempts
                                                          if (p["attrs"].get("sdk_retry_count") or 0) > 0)}}


def _count(items) -> dict:
    out: dict = defaultdict(int)
    for i in items:
        out[i] += 1
    return out


def _group(spans: list[Span], keys: tuple) -> list[dict]:
    groups: dict[str, dict] = {}
    for s in spans:
        g = groups.setdefault(s.name, {"name": s.name, "count": 0, "elapsed_s": 0.0, **{k: 0 for k in keys}})
        g["count"] += 1
        g["elapsed_s"] = round(g["elapsed_s"] + (s.dur or 0), 3)
        for k in keys:
            if isinstance(s.attrs.get(k), (int, float)):
                g[k] += s.attrs[k]
    return sorted(groups.values(), key=lambda g: -g["elapsed_s"])


def _locks(points: list[dict]) -> dict:
    locks = [p["attrs"] for p in points if p.get("kind") == "lock"]
    return {"acquisitions": sum(1 for x in locks if x.get("acquired")), "timeouts": sum(1 for x in locks if not x.get("acquired")),
            "wait_s": round(sum(x.get("wait_s") or 0 for x in locks), 3),
            "max_wait_s": round(max((x.get("wait_s") or 0 for x in locks), default=0), 3),
            "hold_s": round(sum(x.get("hold_s") or 0 for x in locks), 3)}


def _resources(processes: list[Span], samples: list[dict]) -> dict:
    rows = []
    for p in sorted(processes, key=lambda s: s.start):
        rows.append({"process": p.name, "pid": p.pid, "elapsed_s": round(p.dur or 0, 3), "complete": p.complete,
                     **{k: p.attrs.get(k) for k in ("cpu_user_s", "cpu_system_s", "peak_rss_bytes", "children_cpu_user_s",
                                                    "children_cpu_system_s", "import_s", "since_process_created_s",
                                                    "cpu_count", "cpu_affinity")}})
    return {"processes": rows, "samples": len(samples),
            "interval_s": samples[0]["attrs"].get("interval_s") if samples else None,
            "scope": "Each row is one Python process of this run. Docker containers and other child processes are "
                     "not included (on Windows no child CPU is reported at all); host-wide load is not measured."}


def _visibility(calls: list[Span], builds: list[Span], points: list[dict], stages: list[dict], waits: list[dict],
                incomplete: list[Span], has_timefold: bool = False) -> list[str]:
    notes = []
    no_ttft = sum(1 for c in calls if c.attrs.get("time_to_first_chunk_s") is None)
    if calls:
        notes.append(f"Time to first token: observed for {len(calls) - no_ttft} of {len(calls)} model calls; the rest "
                     "were not streamed, so the interface exposes no first-token time for them.")
    unreported = sum(1 for c in calls if not c.attrs.get("usage_reported"))
    if unreported:
        notes.append(f"{unreported} model calls reported no usage at all; their tokens are unknown (not zero).")
    retry = _count(b.attrs.get("retry_visibility", "unknown") for b in builds)
    if retry:
        notes.append("SDK-internal retry visibility per agent build: "
                     + ", ".join(f"{k}: {v}" for k, v in retry.items())
                     + ". Where hooks are not installed, retries inside one model call are invisible (unknown, not zero).")
    if has_timefold:
        notes.append("Timefold queue and solve time inside the service are not reported by it; only the client's "
                     "submit-to-terminal polling time (2 s resolution) is measured.")
    notes.append("Docker container CPU/memory and Docker image pulls are not measured; command spans include them.")
    unmatched = [w for w in waits if w["wait_s"] is None]
    if unmatched:
        notes.append(f"{len(unmatched)} approval waits have no decision evidence in this session (not measured).")
    if not waits:
        notes.append("No approval wait was recorded in this session; human waiting is not measured.")
    mism = [s["agent"] for s in stages if s["usage_reconciliation"].get("status") == "mismatch"]
    if mism:
        notes.append("Per-call token sums differ from the stage aggregate for: " + ", ".join(mism) + ".")
    if incomplete:
        notes.append(f"{len(incomplete)} spans never ended (crash, kill or interruption); they are shown as open until "
                     "their process's last event.")
    return notes


# ============================================================================ Markdown
def to_markdown(r: dict) -> str:
    o = r["overview"]
    L = [f"# Performance summary — session `{r['session']}`", "",
         "How to read this: *elapsed* is wall-clock time. *Exclusive wall time* splits a stage's elapsed time so each "
         "second is counted once (model calls first, then service waits, commands, solvers, tools, agent build, file "
         "work). *Summed work* adds overlapping durations and can exceed elapsed time when work runs in parallel.", ""]
    L += ["## Overview", "",
          f"- Evidence: {r['evidence']['events']} events in {len(r['evidence']['event_files'])} process files, "
          f"{r['evidence']['manifests']} manifests, {r['evidence']['corrupt_lines']} unreadable lines",
          f"- First / last event: {o['first_event']} → {o['last_event']} ({_fmt(o['session_elapsed_s'])})",
          f"- Active execution ({o['active_basis']}): {_fmt(o['active_execution_s'])}, of which interpreter "
          f"start and imports before diagnostics began: {_fmt(o['startup_s'])}",
          f"- Human waiting measured: {_fmt(o['human_wait_measured_s'])}",
          f"- Not explained by either: {_fmt(o['unexplained_s'])} (time between CLI invocations without evidence)",
          f"- Status: **{o['status']}** · diagnostics complete: **{'yes' if o['diagnostics_complete'] else 'NO'}**", ""]
    for rev in r["revisions"]:
        L.append(f"- Source: `{(rev['head'] or '?')[:12]}` on `{rev['branch']}`"
                 f"{' + uncommitted diff ' + rev['diff_sha256'][:12] if rev.get('diff_sha256') else ''}"
                 f" · lockfile {str(rev.get('lockfile_sha256'))[7:19]} · mode {rev.get('execution_mode')}")
    if o["pipelines"]:
        L += ["", "| Pipeline attempt | Started | Elapsed | Outcome | Test approval |", "|---|---|---|---|---|"]
        L += [f"| `{p['pipeline_id']}` | {p['start']} | {_fmt(p['elapsed_s'])} | {p['outcome'] or p['status']}"
              f"{'' if p['complete'] else ' (incomplete)'} | {'yes' if p['test_approve'] else 'no'} |" for p in o["pipelines"]]
    if o["human_waits"]:
        L += ["", "| Gate | Wait started | Decided | Wait | Basis |", "|---|---|---|---|---|"]
        L += [f"| {w['gate']} | {w['wait_started']} | {w['decided'] or '-'} | {_fmt(w['wait_s'])} | {w['basis']} |"
              for w in o["human_waits"]]
    L += ["", "## Stages", "",
          "| Stage | Elapsed | Write / verify / fix (count, elapsed) | Model calls | Input / output / cache-read tokens "
          "| Tool calls (domain errors) | Helpers (max parallel) | Model HTTP retries seen | Outcome |",
          "|---|---|---|---|---|---|---|---|---|"]
    for s in r["stages"]:
        p, t = s["passes"], s["tokens"]
        tok = " / ".join(f"{t[k]['sum']}{'*' if t[k]['calls_not_reporting'] else ''}"
                         for k in ("input_tokens", "output_tokens", "cache_read_tokens"))
        L.append(f"| {s['agent']} | {_fmt(s['elapsed_s'])} | "
                 + " · ".join(f"{p[k]['count']}× {_fmt(p[k]['elapsed_s'])}" for k in ("write", "verify", "fix"))
                 + f" | {s['model_calls']} ({s['model_call_errors']} err) | {tok} | {s['tool_calls']} "
                 f"({s['tool_domain_errors']}) | {s['helpers']} ({s['helper_max_concurrency']}) | "
                 f"{s['model_http_retries_seen']} | {s['outcome']}{'' if s['complete'] else ' (incomplete)'}"
                 f"{' — ' + s['report_problem'] if s.get('report_problem') else ''} |")
    L.append("\n`*` = some calls did not report this token field; the sum covers only calls that did.")
    for s in r["stages"]:
        b = s["breakdown"]
        L += ["", f"### {s['agent']}: where the {_fmt(b['elapsed_s'])} went (exclusive wall time)", ""]
        L += [f"- {cat}: {_fmt(v)}" for cat, v in b["exclusive_wall_s"].items() if v]
        L.append(f"- unattributed (framework, graph and other unmeasured work): {_fmt(b['unattributed_s'])}")
        L.append("- summed work (overlaps counted repeatedly): "
                 + ", ".join(f"{k} {_fmt(v)}" for k, v in sorted(b["summed_work_s"].items(), key=lambda kv: -kv[1])))
        if s["verdicts"]:
            L.append("- verdicts: " + "; ".join(
                f"attempt {v.get('attempt')}: {v.get('effective_status', 'verifier failed')}"
                f" ({v.get('gaps', '?')} gaps{', INCONSISTENT' if v.get('inconsistent') else ''})" for v in s["verdicts"]))
        rec = s["usage_reconciliation"]
        L.append(f"- token reconciliation with report.json totals: {rec.get('status')}")
    L += ["", "## Ten slowest model calls", "", "| Elapsed | Model (tier) | Stage | Helper | Msgs | In / out / cache-read "
          "| First chunk | Finish | Status |", "|---|---|---|---|---|---|---|---|---|"]
    L += [f"| {_fmt(c['elapsed_s'])} | {c['model']} ({c['tier']}) | {c['stage']} | {c['helper_type'] or '-'} | {c['messages']} "
          f"| {c['input_tokens']} / {c['output_tokens']} / {c['cache_read_tokens']} | {_fmt(c['time_to_first_chunk_s'])} "
          f"| {c['finish_reason']} | {c['status']}{' (compaction)' if c['compaction'] else ''} |" for c in r["slowest_model_calls"]]
    L += ["", "## Largest input context (repeated context candidates)", "", "| Input tokens | Cache-read | Model | Stage | Helper | Msgs |",
          "|---|---|---|---|---|---|"]
    L += [f"| {c['input_tokens']} | {c['cache_read_tokens']} | {c['model']} | {c['stage']} | {c['helper_type'] or '-'} | {c['messages']} |"
          for c in r["largest_context_calls"]]
    L += ["", "## Ten slowest tool / command / service operations", "", "| Elapsed | Kind | Name | Details | Status |", "|---|---|---|---|---|"]
    for op in r["slowest_operations"]:
        details = ", ".join(f"{k}={v}" for k, v in op.items() if k not in ("kind", "name", "elapsed_s", "status", "complete"))
        L.append(f"| {_fmt(op['elapsed_s'])} | {op['kind']} | {op['name']} | {details[:160]} | {op['status']} |")
    h = r["helpers"]
    L += ["", "## Helpers", "", f"{h['count']} helper invocations; max running at once: **{h['max_concurrency']}**; "
          f"elapsed while any helper ran: {_fmt(h['elapsed_union_s'])}; summed helper time: {_fmt(h['summed_s'])}.", ""]
    if h["timeline"]:
        L += ["| Start (+s) | Elapsed | Type | Status |", "|---|---|---|---|"]
        L += [f"| +{t['start_offset_s']} | {_fmt(t['elapsed_s'])} | {t['type']} | {t['status']} |" for t in h["timeline"][:60]]
    L += ["", "## Solvers", "", "Main solve, core extraction and each option candidate have separate time limits, so a "
          "sprint_solve call can take longer than the main limit.", "", "| Name | Elapsed | Status | Details |", "|---|---|---|---|"]
    for sv in r["solvers"]:
        details = ", ".join(f"{k}={v}" for k, v in sv.items() if k not in ("kind", "name", "elapsed_s", "status", "complete"))
        L.append(f"| {sv['name']} | {_fmt(sv['elapsed_s'])} | {sv.get('result_status', sv['status'])} | {details[:200]} |")
    inf = r["infrastructure"]
    L += ["", "## Infrastructure checks", "", inf["note"], "", "| Tool | Category | Env | Attempt | Runs | Elapsed | Exit codes | Timeouts | Executor |",
          "|---|---|---|---|---|---|---|---|---|"]
    L += [f"| {g['tool']} | {g['category']} | {g['env'] or '-'} | {g['attempt']} | {g['runs']} | {_fmt(g['elapsed_s'])} | "
          f"{g['exit_codes']} | {g['timed_out']} | {g['executor']} |" for g in inf["commands"]]
    if inf["check_outcomes"]:
        L += ["", "| Check | Outcome | Passed | Skipped | Findings | Scope |", "|---|---|---|---|---|---|"]
        L += [f"| {c['tool']} | {c['outcome']} | {c['passed']} | {c['skipped']} | {c['findings']} | {c['validation_scope']} |"
              for c in inf["check_outcomes"]]
    ht = r["http"]
    L += ["", "## HTTP, polling and retries", "", "| Request | Count | Elapsed | Statuses | Attempts | Throttle wait | Backoff | Failed |",
          "|---|---|---|---|---|---|---|---|"]
    L += [f"| {g['name']} | {g['requests']} | {_fmt(g['elapsed_s'])} | {g['statuses']} | {g['attempts']} | "
          f"{_fmt(g['throttle_wait_s'])} | {_fmt(g['retry_backoff_s'])} | {g['failed']} |" for g in ht["requests"]]
    mt = ht["model_transport"]
    L += ["", f"Model HTTP attempts seen by transport hooks: {mt['attempts']} (statuses {mt['statuses']}); logical calls "
          f"with more than one attempt: {mt['calls_with_multiple_attempts']}; attempts marked as SDK retries: {mt['sdk_retry_attempts']}."]
    for pw in ht["polling"]:
        L.append(f"- polling {pw['name']}: {_fmt(pw['elapsed_s'])}, polls={pw.get('polls')}, sleeping {_fmt(pw.get('sleep_s'))}")
    L += ["", "## File system, locks and diagnostics overhead", "", "| Operation | Count | Elapsed | Files | Bytes |", "|---|---|---|---|---|"]
    L += [f"| {g['name']} | {g['count']} | {_fmt(g['elapsed_s'])} | {g.get('files', 0) or g.get('files_copied', 0) or '-'} | "
          f"{g.get('bytes', 0) or g.get('bytes_copied', 0) or '-'} |" for g in r["filesystem"]]
    lk = r["locks"]
    L.append(f"\nGlobal write lock: {lk['acquisitions']} acquisitions, waited {_fmt(lk['wait_s'])} in total (max "
             f"{_fmt(lk['max_wait_s'])}), held {_fmt(lk['hold_s'])}, {lk['timeouts']} timeouts.")
    for g in r["diagnostics_overhead"]:
        L.append(f"- diagnostics {g['name']}: {g['count']}× {_fmt(g['elapsed_s'])}")
    res = r["resources"]
    L += ["", "## Resources", "", res["scope"], "", "| Process | Elapsed | CPU user / system | Peak memory | Import time |",
          "|---|---|---|---|---|"]
    L += [f"| {p['process']} | {_fmt(p['elapsed_s'])} | {p.get('cpu_user_s')} / {p.get('cpu_system_s')} s | "
          f"{round(p['peak_rss_bytes'] / 2**20) if p.get('peak_rss_bytes') else '-'} MiB | {_fmt(p.get('import_s'))} |"
          for p in res["processes"]]
    L += ["", "## Failures and incomplete work", ""]
    if r["failures"]:
        L += ["| Kind | Name | Status | Category | Error | Raw output |", "|---|---|---|---|---|---|"]
        L += [f"| {f['kind']} | {f['name']} | {f['status']} | {f['error_category'] or '-'} | {(f['error'] or '')[:120]} | "
              f"{f['raw_output'] or '-'} |" for f in r["failures"][:80]]
    else:
        L.append("No failed spans.")
    if r["incomplete_spans"]:
        L += ["", "Spans that never ended:", ""] + [f"- {s['kind']} `{s['name']}` started {s['started']}, open "
                                                    f"{_fmt(s['open_for_s'])} (span {s['span']})" for s in r["incomplete_spans"]]
    if r["evidence"]["incomplete_notes"]:
        L += ["", "Diagnostics problems:", ""] + [f"- {n}" for n in r["evidence"]["incomplete_notes"]]
    L += ["", "## What is not measured", ""] + [f"- {n}" for n in r["visibility"]]
    return "\n".join(L) + "\n"


# ============================================================================ CLI
def cli(args) -> int:
    base = Path(args.dir) if getattr(args, "dir", None) else perf.resolve_dir()
    if args.perf_command == "list":
        if not base.is_dir():
            print(f"no diagnostics folder at {base}")
            return 0
        for d in sorted(p for p in base.iterdir() if p.is_dir()):
            files = list((d / "events").glob("*.jsonl")) if (d / "events").is_dir() else []
            incomplete = " INCOMPLETE" if list(d.glob("INCOMPLETE-*.txt")) else ""
            print(f"{d.name:40} {len(files):3} process files{incomplete}")
        return 0
    session_dir = base / args.session
    if not (session_dir / "events").is_dir():
        print(f"ERROR: no events for session {args.session!r} under {base}")
        return 1
    result = analyze(session_dir)
    md = to_markdown(result)
    (session_dir / "summary.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    (session_dir / "summary.md").write_text(md, encoding="utf-8")
    print(json.dumps(result, indent=2, default=str) if args.json else md)
    print(f"\nWritten: {session_dir / 'summary.md'} and summary.json", file=sys.stderr)
    return 0
