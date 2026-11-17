# Performance controls and the next real-API run

These changes preserve the backlog/plan/assignment schemas, constraints, gate decisions and required checks.
They do not promise identical model wording or measured API savings. No live model run was available locally.
Use the same input bytes, model settings, planning date and external services for comparisons. Keep previous
run evidence; never compare an old clinic input with a new TaskFlow input as if only the code changed.

## What changed

| Improvement | Implementation and benefit | Cost or limitation |
| --- | --- | --- |
| Less repeated context | Task Breakdown passes authoritative source paths and requirement ids rather than duplicating source text in task messages. Parent uses a compact story index before fetching full related records. Helpers return short receipts. All successful JSON tool responses remove serialization whitespace without deleting fields. | Helpers must still read applicable requirements and global constraints. Model behavior and actual token savings require a real run. No model downgrade or acceptance-criteria truncation. |
| Smaller backlog reads | `backlog_view` pages default to 24,000 item-payload characters; always follow `next_offset`. Full item records remain available. One oversized record is returned whole with `oversized_item=true`. Optional `expected_sha256` detects changed pages. | Character count is not a token count or a strict whole-message ceiling. Concurrent enrichment can change the digest; restart a consistent read rather than combining revisions. |
| Reuse completed generation | Durable phase records let orchestration resume review/repair from saved source/artifact hashes. Reviewer configuration and runtime fixes can trigger fresh review without repeating generation. | Changed generation inputs/artifacts invalidate strict reuse. Checkpoints never approve a gate. See [PIPELINE_RECOVERY.md](PIPELINE_RECOVERY.md). |
| Download reuse and retention | Byte-identical infrastructure reuses existing module workspaces. A provider-cache lease prevents concurrent host plugin-cache writers and eviction during use. Owned inactive validation workspaces expire after 14 days or are removed oldest-first above 2 GiB. Docker provider volume identity is stable per cache root/user; unrelated scanners no longer create provider volumes. | Limits are soft, applied before validation, and exclude the active workspace, legacy unmarked directories, local shared plugin binaries and Docker volume contents. Those require operator disk monitoring/maintenance. No `docker system prune`. Initialization across projects sharing a cache is serialized. Old volumes are not automatically deleted. |
| Bounded helpers | `AGENT_ENGINE_HELPER_CONCURRENCY` remains 9 by default; accepts 1–32. Performance events record slot wait time, hold time, active count and peak. | Lower concurrency can reduce rate-limit pressure but increase elapsed time. Higher concurrency can increase memory use, request bursts and retry costs. No automatic tuning. |
| Stage overlap | `phase4 orchestrate --parallel-independent` overlaps only runnable Task Breakdown and Infrastructure. Children have separate output/log roots. Original project lease, source/output hashes, per-stage ownership and conflict checks protect a durable, replayable merge; normal I/O failures attempt rollback. Both histories/logs and isolated source trees are retained. | Off by default. Requires extra disk/RAM and API capacity. Interrupted merges replay from retained intent/output hashes and before-merge copies; this is not a power-loss-atomic transaction. Downstream stages still wait for their gates. Independent runnable work may continue; dependent stages and approvals remain blocked as required. |
| Scanner overlap | `PHASE4_IAC_CHECK_CONCURRENCY=2` (range 1–4, default 1) runs independent checks against private copies of one snapshot. Tofu fmt/validate stay in one group. Shared deadline propagates to threads; result order is stable; changed sources invalidate results. | Additional copies and tool processes consume resources. Symlinked workdirs are rejected in parallel mode. Missing tools remain missing; copying or queued checks can consume the time budget. |
| Solver diagnostics | `sprint/solver-diagnostics.json` records status/time, objective/bound, required dependency closure, scaled demand/capacity, skill bounds, assumption core and each attempted repair option's status/proof/time. UNKNOWN remains UNKNOWN. Candidate pruning now uses the same scaled arithmetic as CP-SAT. | Necessary capacity bounds do not prove feasibility. An assumption core need not be minimal. Dependencies can share a sprint, so this does not invent a duration-based critical path. Solver workers/time limits and optimization objective stay unchanged. |

## Run with evidence

Set these in your existing environment (replace the session name for each run):

```dotenv
AGENT_ENGINE_PERF=1
AGENT_ENGINE_PERF_SESSION=performance-controls-run-1
AGENT_ENGINE_PERF_MODE=generation
AGENT_ENGINE_HELPER_CONCURRENCY=4
PHASE4_IAC_CHECK_CONCURRENCY=2
```

The values 4 and 2 are starting experiments, not proven optimal settings. Leave scanner concurrency at 1
and omit the stage-overlap flag to isolate context/retry changes first. Keep real API credentials in your
existing secret/environment setup. Transcript-size settings only limit logs; they do not limit model tokens.

```bash
uv sync --locked
uv run agent-engine phase4 orchestrate --project-name YOUR_PROJECT --parallel-independent
uv run agent-engine perf summarize --session performance-controls-run-1
```

Review/approve gates through the existing workflow, then resume orchestration. Do not use test approvals
for production, do not manually relabel partial runs as successful, and do not publish benchmark runs.
An existing completed project may do no work; benchmark from independent copies of the same original inputs.

If semantic verification fails due to a connection error, use the **exact original request**, for example:

```bash
uv run agent-engine run 'Break prd.md down into a backlog.' --agent task-breakdown \
  --project-name YOUR_PROJECT --resume-verification
```

Use the original request recorded in the failed report if different. Never edit checkpoint hashes to force reuse.
For inspected manual corrections use `--review-existing`; changed source inputs may require rebuilding affected
work. Orchestration reads retained completion records, but successful review still requires normal human gate
approval. See [PIPELINE_RECOVERY.md](PIPELINE_RECOVERY.md) for recovery commands and conflict handling.

## What to retain and compare

- Per-run reports/history, generated artifacts, input hashes and model configuration.
- The performance session's manifests, event files, summaries and redacted command output.
- `logs/parallel/<id>/`: both child workspaces/logs, before-merge copy and result metadata. Treat these as
  sensitive project data; retain as needed and remove old completed sessions when no process uses them.
- `sprint/solver-diagnostics.json`, especially for infeasible or timed-out runs.

Compare stage/pass elapsed times, tool-response sizes, helper wait/hold times, input/output/cached token
counts when the provider supplies them, retries, API errors, peak resources and scanner outcomes. Calculate
cost from the actual provider/model pricing, including cached tokens separately; context characters alone
cannot establish a dollar saving. Check requirement coverage, acceptance criteria, estimates, dependency
correctness and gate readiness before treating a lower token count as an improvement.

## Validation scope

Automated Python tests cover domain pipeline behavior plus the new pagination, retry invalidation,
concurrency/failure cleanup, isolation/merge rollback, retention ownership and solver-bound regressions.
They use controlled model substitutes, not paid API calls. Real LLM semantic quality, provider rate limits,
Docker provider downloads and the complete production scanner set still need your configured environment.

Local validation on 2026-11-16: **220 Python tests passed**, including the existing end-to-end artifact
equivalence test with performance instrumentation on and off. A real local sequential/parallel scanner
comparison on the retained TaskFlow infrastructure returned identical check records: Conftest policy tests
passed; Helm lint succeeded but the combined Helm/schema check reported an execution error because
`kubeconform` was unavailable. This partial check is not evidence of full infrastructure readiness or a
representative pipeline speedup. No real API/token-cost reduction has been measured for this branch.
