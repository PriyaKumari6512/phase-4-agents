"""Measures what diagnostics cost, offline: no model, network, Docker or publication.

    .venv/Scripts/python scripts/perf_overhead.py [--runs 7]

Cases, each run alternately with diagnostics off and on (so drift affects both equally):

  deterministic  the Phase 4 tool flow of tests/test_outcome_integrity.py (backlog -> sprint CP-SAT ->
                 allocation CP-SAT -> infra render/validate with the sandbox off)
  agent_graph    one stage `run` (as started by the orchestrator, light manifest) of a real deepagents graph on
                 a scripted fake model: 5 model calls, 2 tools, 2 parallel helpers (no artificial sleeps)
  graph_standalone  the same as a standalone `run` (full manifest: git and docker subprocesses)
  span           100,000 empty spans: the per-span cost

Prints median, min-max and the median difference. Single-machine timings are noisy: compare the difference
with the spread before calling anything negligible.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import statistics
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
os.environ.update(PHASE4_ALLOCATION_SOLVER_MODE="local", PHASE4_IAC_SANDBOX_MODE="off", PHASE4_PR_MODE="local")

from agent_engine import agent, backends, cli, config, logging_setup, perf  # noqa: E402


@contextmanager
def patched(pairs):
    saved = [(obj, name, getattr(obj, name)) for obj, name, _ in pairs]
    try:
        for obj, name, value in pairs:
            setattr(obj, name, value)
        yield
    finally:
        for obj, name, value in saved:
            setattr(obj, name, value)


@contextmanager
def diagnostics(on: bool, base: Path, pipeline: bool):
    perf.reset_for_tests()
    os.environ[perf.ENV_SESSION] = f"overhead-{time.time_ns()}"
    os.environ[perf.ENV_SAMPLE_SECONDS] = "5"
    if on:
        assert perf.init("overhead", force=True, perf_dir=base / "perf")
        if pipeline:                       # a stage child of `phase4 orchestrate`: light manifest
            perf.set_pipeline("overhead-pipeline")
    try:
        yield
    finally:
        perf.shutdown()
        perf.reset_for_tests()
        os.environ.pop(perf.ENV_PIPELINE, None)


def deterministic(base: Path) -> None:
    import test_outcome_integrity as t
    from test_phase4_pipeline import EXAMPLE, FIXTURE

    root = base / "outputs" / "bm"
    shutil.copytree(FIXTURE, root)
    (root / "phase4").mkdir()
    for n in ("project.json", "history.json"):
        shutil.copy(EXAMPLE / "phase4" / n, root / "phase4" / n)
    with patched([(config, "OUTPUTS_DIR", base / "outputs")]):
        t._flow(root)


def agent_graph(base: Path) -> None:
    import test_perf_diagnostics as t
    from deepagents.middleware.summarization import SummarizationMiddleware

    packs, outputs = base / "agents", base / "outputs"
    t._pack(packs, "probe", 'tools = ["probe-tools"]')
    script = [m.model_copy(update={"content": "ok"}) if m.content == "helper done" else m for m in t._script()]
    model = t.ScriptedModel(script=t._Script(script))
    agent.TOOLS["probe-tools"] = lambda: [t.probe_tool, t.err_tool]
    with patched([(agent, "AGENTS_DIR", packs), (cli, "OUTPUTS_DIR", outputs), (backends, "OUTPUTS_DIR", outputs),
                  (logging_setup, "OUTPUTS_DIR", outputs), (logging_setup, "LOGS_DIR", base / "logs"),
                  (config, "AGENTS_DIR", packs), (config, "OUTPUTS_DIR", outputs),
                  (cli, "build_langfuse_handler", lambda: None), (cli, "model_spec", lambda tier: f"fake:{tier}"),
                  (agent, "model_spec", lambda tier: f"fake:{tier}"),
                  (agent, "resolve_model_with_retries", lambda spec: model),
                  (agent, "summarization_middleware", lambda spec, fast, backend: SummarizationMiddleware(
                      model=fast, backend=backend, trigger=("tokens", 10**9)))]):
        import contextlib
        import io

        with contextlib.redirect_stdout(io.StringIO()):
            assert asyncio.run(cli._run("overhead check", "probe", "demo")) == 0


def spans(base: Path) -> None:
    for _ in range(100_000):
        with perf.span("compute", "noop"):
            pass


def measure(name: str, fn, runs: int, pipeline: bool = True) -> dict:
    times = {False: [], True: []}
    for i in range(runs * 2):
        on = bool(i % 2)
        base = Path(tempfile.mkdtemp(prefix="perf-overhead-"))
        try:
            with diagnostics(on, base, pipeline):
                t0 = time.perf_counter()
                fn(base)
                times[on].append(time.perf_counter() - t0)
        finally:
            shutil.rmtree(base, ignore_errors=True)
    off, on_ = statistics.median(times[False]), statistics.median(times[True])
    return {"case": name, "runs_each": runs, "off_median_s": round(off, 4), "on_median_s": round(on_, 4),
            "off_range_s": (round(min(times[False]), 4), round(max(times[False]), 4)),
            "on_range_s": (round(min(times[True]), 4), round(max(times[True]), 4)),
            "median_diff_s": round(on_ - off, 4), "median_diff_pct": round(100 * (on_ - off) / off, 1) if off else None}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=7)
    args = parser.parse_args()
    deterministic(Path(tempfile.mkdtemp(prefix="perf-warmup-")))  # warm imports and caches once
    for name, fn, runs, pipeline in (("deterministic", deterministic, args.runs, True),
                                     ("agent_graph", agent_graph, args.runs, True),
                                     ("graph_standalone", agent_graph, args.runs, False),
                                     ("span x100k", spans, 3, True)):
        r = measure(name, fn, runs, pipeline)
        print(f"{r['case']:16} off {r['off_median_s']:.4f}s {r['off_range_s']}  on {r['on_median_s']:.4f}s "
              f"{r['on_range_s']}  diff {r['median_diff_s']:+.4f}s ({r['median_diff_pct']:+}%)")


if __name__ == "__main__":
    main()
