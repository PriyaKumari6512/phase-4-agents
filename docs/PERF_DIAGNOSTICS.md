# Performance diagnostics

Opt-in, structured evidence of where a Phase 4 run spends its time, why things fail, and how concurrency
actually behaves. Off by default; with it off the engine behaves as before (measured: no difference beyond
noise on the deterministic tool flow).

## Switches

| Variable | Meaning |
|---|---|
| `AGENT_ENGINE_PERF=1` | Turn diagnostics on for this process and every stage child it starts. |
| `AGENT_ENGINE_PERF_SESSION=<id>` | The benchmark case. Keep it the same for every command of one case (orchestrate, gate, resumed orchestrate). Generated if unset. Letters, digits, `.`, `_`, `-`. |
| `AGENT_ENGINE_PERF_DIR=<folder>` | Where sessions go. Default `<AGENT_ENGINE_LOGS_DIR or logs>/perf`. Refused if it overlaps the outputs folder or the agent packs folder (both are agent-readable; outputs are fingerprinted and published). |
| `AGENT_ENGINE_PERF_MODE` | `generation` (default): `phase4 publish` and `orchestrate --publish` are refused while diagnostics are on. `publication`: only for a separately authorized publication benchmark. |
| `AGENT_ENGINE_PERF_SAMPLE_SECONDS` | CPU/memory sampling interval (default 5; 0 = off). |
| `AGENT_ENGINE_PERF_RAW_OUTPUT` | `1` (default) keeps each sandbox command's full output, credentials redacted, under `raw/`; `0` keeps none. |

`AGENT_ENGINE_INVOCATION_ID` is set by the orchestrator for every child, with or without diagnostics; do not set it by hand.

## What is written

```
<perf dir>/<session>/
  events/<time>-<pid>-<rand>.jsonl   one file per process; one JSON object per line
  manifests/pipeline-<id>.json       provenance per orchestrate invocation (full)
  manifests/invocation-<id>.json     per stage child (light: packs, models, settings, input digests)
  raw/<span>-<tool>-<env>-a<n>.txt   full sandbox command output, credentials redacted
  INCOMPLETE-<pid>.txt               present only if diagnostics themselves failed
  summary.md, summary.json           written by `agent-engine perf summarize`
```

Never written: request text, prompts, model output, tool arguments or results, environment values, `.env`,
credentials, calendar contents. Configuration in manifests comes from an explicit allowlist
(`perf_manifest.SAFE_SETTINGS`); credentials appear only as `set`/`unset`, URLs only as `scheme://host:port`.
The project's own files are recorded as digests and sizes. Raw command output can still contain project details
(file names, resource names); keep the perf folder private and out of source control (`logs/` is git-ignored).

### Event fields

Every line: `v, ev (span_start | span_end | event | sample), ts (UTC ISO), wall, mono (perf_counter), pid, seq,
session, pipeline, invocation`. Spans add `span, parent, kind, name, attrs`; ends add `status, dur` (monotonic
seconds) and, on failure, `error_category, error` (sanitized). Span kinds: `process, pipeline, orchestrator,
child, stage, phase, pass, agent_build, model_setup, graph, model_call, tool, helper, tool_exec, compute, solver,
solver_backend, service_wait, command, http, calendar, fs, publish, dispatch, diagnostics`.

Statuses: `ok, error, cancelled, timeout, domain_error` (a tool returned `ERROR:` text without raising),
`blocked` (preflight refused), `failed` (non-zero outcome). A span without an end is reported as incomplete.

## Coverage

| Area | Measured |
|---|---|
| Orchestration | each `orchestrate` invocation (pipeline id), preflight, every assessment (with each stage's decided action), input digests, state saves, child spawn time, time to first output, exit code, report read and its validity, approval-wait start, gate decisions (human via `gate`, or automated `--test-approve`), approvals observed with their recorded time |
| Stage (`run`) | preflight (pack load, inputs, stale approvals), request record, fingerprint before/after (files, bytes), each pass (write/verify/fix, attempt, tier, model), agent build (model construction, summarization middleware incl. profile lookups, graph construction, observed helper models and summarizers, parallel-tool-call restriction, retry visibility), graph execution, verdicts (satisfied, status, gaps count, inconsistency), usage aggregate, run-history copy (files, bytes), report write, Langfuse flush |
| Model calls | one span per logical call: model, provider, tier, safe tuning, message count, helper, graph node, compaction flag, input/output/cache-read/cache-creation/reasoning tokens as reported (null when not), finish reason, first streamed chunk time when streamed, errors/cancellation. HTTP attempts per call through transport hooks on the SDK's `httpx`/`httpx2` clients, with the SDK's retry counter |
| Tools and helpers | every LangChain tool call (input/output size, `ERROR:` text as domain errors), every helper (`task`) invocation with its type; nesting follows LangChain's run tree, so parallel helpers and worker-thread tools keep their own parents |
| Phase 4 tools | each tool body (`tool_exec`); backlog: per-feature parsing, enrichment replay (re-applied, dropped, errors), save sizes, similarity, validation sections (hierarchy, cycles with iteration count, transitive reduction, rules, duplicates incl. whether skipped by the 1,500-task limit, waves/critical path), counts of features/epics/stories/tasks/blocking/warnings; sprint: inputs, calendar, capacity simulation, solver input, main solve, core extraction, each option candidate (transformation, status), forecast, write; allocation: inputs, eligibility counts (eligible/ineligible/shadow, outcome-history reads), availability, profiles, backend selection and reason, Timefold submit/poll (count, statuses, sleep)/score analysis, local CP-SAT, write; infra: render per env, file writes, manifest re-hash, every sandbox command (tool, category, env, attempt, executor, timeout, exit code, timed out, output sizes, raw file, cleanup), check outcomes with their validation scope, secret scan, reports |
| HTTP | calendars (no IDs or contents), Timefold, Terraform registry, trackers/GitHub (attempts, throttle wait, retry backoff), PR creation, AI dispatch |
| Files and locks | fingerprinting, history copies, report and plan writes, global write-lock wait and hold time |
| Resources | per Python process: CPU user/system, working set / peak memory, CPU count, interpreter start + import time |

## Visibility limits (also listed in every summary)

* First-token time exists only for calls that deliver streamed chunks to callbacks; whether a call does depends on
  the provider adapter and LangGraph's stream mode, so the summary counts how many calls exposed it.
* SDK-internal retries are visible only where transport hooks attached (`retry_visibility` on each agent build);
  elsewhere they are unknown, not zero.
* Timefold reports no queue or solve time; only the client's polling view (2 s resolution) is measured.
* Docker containers' CPU/memory and image pulls are inside command spans, not broken down.
* Human waiting is measured only from an approval-wait event to a gate decision event in the same session;
  time between invocations without that evidence is reported as unexplained.

## Offline summary

```
python -m agent_engine perf list
python -m agent_engine perf summarize --session <id> [--json]
```

Reads complete or partial sessions (a killed process's half-written last line is skipped and counted), never calls
a model or the network. Elapsed time, exclusive wall time (each second counted once, by priority: model call >
service wait > command > solver > tool > agent build > file system > diagnostics; the rest is unattributed) and
summed work (overlaps counted repeatedly) are reported separately.

## Overhead

`scripts/perf_overhead.py` repeats offline cases with diagnostics off and on, alternating. On the development
machine (Windows 11, 9 runs each, medians): deterministic Phase 4 tool flow 0.342 s off / 0.339 s on (within
noise, ranges overlap); one orchestrated stage of a fake-model graph +5 ms; a standalone `run` +0.33 s (its full
manifest runs git and docker); an empty span about 21 µs. Each `orchestrate` invocation also writes one full
manifest (about 0.3 s, recorded as a `diagnostics` span and listed in the summary).
