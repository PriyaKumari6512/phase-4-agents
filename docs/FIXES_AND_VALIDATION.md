# Phase 4 reliability and performance fixes

This branch starts from the latest recorded-run/instrumentation commit,
`94dcb9ce872fe2ee8ffb7231e7ec7d11b3bdf2bb`. It keeps the previous audit and recorded
run unchanged. This document describes the new code, its checks, and its limits.
It does not claim the entire system is perfect or that a faster paid run has been measured.

## Pull and run

Use a separate checkout if your existing checkout has local changes. Keep your
existing credentials private; do not commit `.env`, provider state or credentials.

```bash
git fetch origin fix/phase4-reliability-performance
git switch --track origin/fix/phase4-reliability-performance
uv sync --locked
uv run python -m pytest -q
docker build -f services/iac-sandbox/Dockerfile -t phase4/iac-sandbox:dev services/iac-sandbox
```

If this branch already exists locally, switch to it and use `git pull --ff-only`.
Build Atlantis from the repository root with
`docker build -f services/atlantis/Dockerfile -t phase4-atlantis:dev .`.
Build the two images sequentially on small disks. On Linux, sandbox containers
use the host UID/GID for writable bind mounts. Docker Desktop uses UID/GID 1000.

On a network with a company HTTPS inspection proxy, the two image builds accept
`--secret id=build-ca,src=/path/to/public-ca-bundle.pem`. Supply a trusted public
CA certificate bundle, never a private key. Certificate verification stays enabled.
Normal networks need no secret. The scripts currently download Linux AMD64 tools;
other architectures need an explicitly tested platform/image.

For a new measured generation run, use a fresh project folder containing the
original inputs and optional history/profile/outcome inputs, without generated
plans, approvals, or previous orchestrator state. Point `AGENT_ENGINE_OUTPUTS_DIR`
to that fresh output root **before** starting the process. Retain the same project
name and inputs when comparing with the old run. In bash:

```bash
export AGENT_ENGINE_PERF=1
export AGENT_ENGINE_PERF_SESSION=phase4-fixes-run1
export AGENT_ENGINE_PERF_MODE=generation
export PHASE4_PR_MODE=local
uv run agent-engine phase4 orchestrate --project-name YOUR-PROJECT --plan
uv run agent-engine phase4 orchestrate --project-name YOUR-PROJECT
```

PowerShell uses `$env:NAME = "value"` instead of `export NAME=value`.
Use the existing documented human gate commands when the orchestrator stops, then
repeat the orchestrate command. Do not automatically approve an infeasible plan
or incomplete infrastructure validation. `--test-approve` records test approvals;
publication rejects those approvals. No `--publish` is needed for a benchmark.
Run `uv run agent-engine perf summarize --session phase4-fixes-run1` after the run.
See `PERF_DIAGNOSTICS.md` for artifact locations and available summary options.

The CLI names, normal output locations and planning stages remain. New optional
provenance fields bind plans to project settings and infrastructure to its source
inputs/catalog. Old artifacts without those fields need regeneration and fresh
approval. Existing approvals are not silently upgraded. Changes which previously
reported false success now stop with a concrete reason.

## What the recorded run actually establishes

Evidence is in `pipeline-run-results/clinic-fresh-run1/`. Its 345 recorded file
hashes were checked before editing; those evidence files are not modified here.
The run contains 5,754 events and 346 matched model request/response hooks, all
HTTP 200, with no observed retries. The recorded pipeline did **not** complete
production validation: infrastructure ended partial and the final orchestration
waited for P4-G4. Earlier approvals were automated test approvals.

Stage elapsed times were approximately 998s Task Breakdown, 1559s Infrastructure,
168s Sprint Planning, and 200s Allocation. Parent/child process times and report
totals are different intervals; they must not be added as independent work.
Task Breakdown already ran nine feature helpers and nine enrichment helpers
concurrently. Its 265 model calls used about 19.1 million input tokens and
714,407 output tokens; model wait, rather than local Python computation, dominated.
Infrastructure's repeated validation calls spent about 16m46s in OpenTofu commands.
The large validator response was truncated and invalid as JSON. Sprint planning
was infeasible with all 83 stories deferred. Allocation had zero tasks, so that run
cannot benchmark a meaningful allocation solve or coding-agent throughput.

The recorded 1.3x capacity option has a regression test using the real saved
project/backlog. Before the fix the solver used scaled capacity but saved base
capacity; its own checker rejected the resulting sprints. The new test solves,
annotates and checks the resulting nonempty plan successfully.

## Prior correctness findings: disposition

IDs refer to `PERFORMANCE_OPTIMIZATION_REPORT.md`. “Fixed” means the identified
implementation defect is addressed; it does not imply every external integration
has been exercised with production accounts.

| ID | Change and evidence location | Remaining limit |
|---|---|---|
| F01 | Canonical paths, active-project disk routing/domain binding, protected engine/input/managed output files. `guardrails.py`, `backends.py`, `phase4/files.py`; adversarial backend regressions. | Host users with direct filesystem access remain trusted. |
| F02 | Contradictory verdicts cannot report success; declared outputs rechecked after repairs. `cli.py`, `agent.py`; outcome integrity tests. | Semantic review remains model-based. |
| F03 | Child exit status and invocation identity must match the fresh report. `orchestrator.py`; child failure regressions. | A crashed process may require a new stage run. |
| F04 | Digest actual settings, generated spec inputs, pack/catalog/gate bytes, planning date and operational evidence; require all declared outputs. `orchestrator.py`. | Remote calendar changes require a fresh run/snapshot; there is no remote change subscription. |
| F05 | OS project leases, atomic single-file replacement, model/pass/command budgets, cleanup on failure. `runtime.py`, `cli.py`, `agent.py`, `sandbox.py`. | No multi-file transaction journal or graph checkpoint/resume within a failed pass. Direct concurrent library mutation needs the same project lease. |
| F06 | Validate copied backlog updates before committing; preserve split-child enrichment on rebuild and preserve prior files on replay errors. `backlog.py`; transaction/rebuild regressions. | The backlog and enrichment files are each atomic, not one crash-atomic multi-file transaction. |
| F07 | Content fingerprints include requirements, architecture, settings, features, specs and task files. Changed content invalidates reused judgment even when titles match. `backlog.py`. | Regenerating invalidated judgment still costs model calls. |
| F08 | NFR coverage, duplicate ID rejection, saved-artifact repair detection, node-weighted critical path. `backlog.py`, `contracts.py`. | Duplicate similarity analysis explicitly warns when skipped above 1500 tasks. |
| F09 | UNKNOWN/MODEL_INVALID cannot replace a valid saved plan with an empty apparent success. `sprint.py`, `sprint_model.py`; outcome tests. | Genuine infeasibility still requires a scope/date/capacity decision. |
| F10 | Effective scaled capacity is saved; soft-deadline option/application use the same penalty semantics; impossible capacity options can be pruned. `sprint.py`, `sprint_model.py`; real-run regression. | Capacity multipliers require real staffing/availability; they do not create worker hours. |
| F11 | Reject zero/negative durations, invalid point scales, duplicate identities and invalid modes/time limits before costly execution. `contracts.py`, `settings.py`, CLI preflight. | Input schemas cannot validate business assumptions. |
| F12 | Remaining active-sprint days, historical maintenance reserve, explicit unfinished forecast samples, calendar request limits/time zones and warning propagation. `capacity.py`, `calendars.py`. | External committed tracker work is still not automatically deducted. Microsoft full-day buckets remain UTC and are explicitly marked uncertain for non-UTC workers. |
| F13 | Pins must satisfy hard skills, vetoes and AI eligibility. `allocation.py`, `alloc_solver.py`; pin regression. | Impossible pins fail; they are not silently relaxed. |
| F14 | Actual predecessor IDs/end times enforced by CP-SAT and Java; independent post-solve schedule validation. `allocation.py`, `alloc_solver.py`, Java constraint provider; Python/Java precedence tests. | Allocation minutes are an abstract working-time schedule, not a wall-clock availability calendar. |
| F15 | Both backends enforce finishing time/capacity, actual precedence, complete accounting and pins; independently validate their results. | Objectives remain different. Selecting another backend can choose different valid assignments; no objective-equivalence or identical-output claim. |
| F16 | Worker/provider-specific eligibility/limits, all required skills, repository-scoped ownership and precomputed lookup tables. `allocation.py`. | Reliability evidence still depends on supplied/reconciled outcomes. |
| F17 | Healthy probe followed by failed solve can fall back in auto mode; explicit Timefold mode fails clearly; checked polls, configured deadline and best-effort remote cancellation. `alloc_solver.py`; fallback regression. | Cancellation failure needs server reconciliation; backend objectives differ as F15 explains. |
| F18 | Skipped/unavailable checks cannot satisfy infrastructure completion; CLI stops without a paid semantic review of known incomplete validation. `infra.py`, `cli.py`; skipped-check regression. | Requires actual installed tools and reachable registries. |
| F19 | Validate complete scanner JSON shapes and exit codes; keep raw output; treat absent Checkov severity/module downloads and skipped Kubernetes resources explicitly. `sandbox.py`; malformed-output regressions. | Findings without severity need review; missing CRD schemas remain incomplete. |
| F20 | Correct variable-region resolution, IPv6 ingress and unsafe web-port ranges; lint/render environment values separately; label policy unit-test scope accurately. Rego library and `sandbox.py`. | `conftest verify` tests the library only. A real `tofu plan` is still required in Atlantis before apply. |
| F21 | GitOps includes adjacent ExternalSecrets and environment platform applications; environment-specific cluster names; one ECR state owner; reject unsupported clouds/targets/multiple regions/name collisions. `infra.py`, GitOps templates. | Cluster registration, required operators/CRDs, bootstrap/apply order and application-specific sizing remain deployment prerequisites. No fabricated ECS/CDN/WAF implementation. |
| F22 | Atlantis root build context copies the actual policy directory; plan webhook optional unless configured, and requires its secret when enabled. `services/atlantis/`. | An enabled receiver is external. Image builds need network trust, disk and AMD64 support. |
| F23 | Exact gate/project/artifact sets, upstream approvals, source/settings hashes and outgoing infrastructure-byte hashes required before publication. Snapshot outgoing bytes before API calls. `gates.py`, `publish.py`, `infra.py`; approved-byte regression. | Files changed by an external host process during an active run are outside CLI lease ownership. |
| F24 | Keep generated comparison baselines instead of human content; unknown adoption baselines treated conservatively. `publish.py`; three consecutive human-override regressions. | Human overrides can intentionally differ from a new local plan. |
| F25 | Project publication lease, destination-scoped tracker mappings, project/task dispatch identity, pending-operation records, no blind POST retries, marker adoption. `publish.py`, `trackers/base.py`. | No universal exactly-once guarantee across providers. Ambiguous comments/sprints/dispatches stop for reconciliation rather than risking duplicates. |
| F26 | Operational workflow/head/run evidence, refresh before live AI dispatch, predecessor completion/planned start/WIP checks, outcome reconciliation. `readiness.py`, `allocation.py`, `publish.py`; failed readiness evidence regression. | Requires merged CI and provider permissions. A completed coding job is not a merged PR. External provider contracts need sandbox validation. |
| F27 | Parent/label updates, child/backlog iteration clearing, removed dependency reconciliation, reopened items, paginated provider collections, GitHub point read-back; Jira dependency direction checked after creation. `trackers/`, `publish.py`. | Live provider compatibility, custom Jira link types/workflows and tenant permissions remain unverified. Read-back mismatch stops instead of guessing another link. |
| F28 | Single-source assets bundled at wheel build; installed defaults use packaged assets and writable CWD outputs. `build_backend.py`, `config.py`, CI wheel smoke test. | Concurrent builds inside one source checkout deliberately fail instead of racing over temporary assets. |

The tracker field/link changes follow the provider-specific contracts, rather than
assuming all APIs behave alike. Jira link interpretation is described in
[Atlassian's linking model](https://developer.atlassian.com/cloud/jira/platform/issue-linking-model/).
The code checks the created relationship by reading it back; this is particularly
important because the create endpoint's field names are easy to invert.

## Prior optimization opportunities: disposition

| ID | Implemented now or deliberately deferred | Expected benefit and trade-off |
|---|---|---|
| O01 | Retain detailed instrumentation; fix invalid sampling configuration, signed URL redaction and double-counted tool failures; observe explicit helper model transports and cleanup. | Better attribution. No streaming TTFT or Docker OOM/CPU/memory proof is available from the old run. |
| O02 | Read-only scoped/paginated backlog tool; epic-local enrichment and focused story inputs; shared implementation contract before feature fan-out. | Less repeated context. Actual token/quality improvement must be measured on the next run. |
| O03 | Deterministic checks before semantic reviewer. Known infeasibility/incomplete validation stops early. | Avoids model review of already provably blocked artifacts; still retains semantic review for valid artifacts. |
| O04 | Narrow format checks before helper completion; bounded verdict retry/token output; preserve reports and cleanup. | Less avoidable late repair and invalid typed output. Full checkpointed graph recovery deferred. |
| O05 | Do not overlap whole Task/Infra stages yet. | Both touch project artifacts/logging/gates; safe staging/merge and a critical-path comparison are prerequisites. |
| O06 | Bound existing helper fan-out (default 9); test real maximum concurrent task handlers. | Prevents uncontrolled bursts. Higher concurrency or changing summarizers/models requires a quality/rate-limit experiment. |
| O07 | Validate backlog patches transactionally under existing shared mutation lock. | Preserve current parallel judgment with serialized safe merges; multi-process library callers still need the project lease. |
| O08 | Keep infrastructure scanners sequential. | Parallelization needs frozen inputs and isolated temporary workspaces; concurrent downloads/scans can worsen resource pressure. |
| O09 | Source-content-addressed validation workspaces reuse module/provider downloads, outside published output; re-run checks each time. | Avoids repeated downloads on unchanged inputs without treating stale check results as valid. Cache uses disk and needs retention management. |
| O10 | Per-command timeout classification, total validation budget, stop repeated provider-startup failures. | Bounds repeated failure time and preserves the actual failure reason. A timeout is never a pass. |
| O11 | Prune provably impossible capacity candidates; retain sequential solver search. | Avoid some unnecessary solves. Parallel native solvers need a shared CPU/memory budget and objective/timeout equivalence checks. |
| O12 | Precompute worker/area ownership and AI outcome lookups during allocation. | Removes repeated scans without changing lookup semantics. Zero-task old run cannot quantify savings. |
| O13 | One calendar snapshot per job, explicit request batching and date ranges. | Reuse identical reads within a run while a new run refreshes availability. No persistent stale calendar cache. |
| O14 | Retain current similarity implementation and make its large-input skip explicit. | Sparse/top-k replacement only after a large-backlog profile shows value and matching thresholds/rankings are checked. |
| O15 | Publication safety first; serialize mutations and reconcile existing mappings/links. | Avoid duplicates/overwrites. Concurrent provider writes intentionally deferred. |
| O16 | Bounded text detection read and streaming XLSX row retention. | Lower memory on large uploads while preserving displayed-row limit and omitted-row count. Workbook is still fully traversed to count omitted rows. |
| O17 | Retain existing model metadata caching; no extra invalidation-sensitive cache layer. | No evidence that metadata lookup is a meaningful part of this run's critical path. |
| O18 | Retain existing orchestration and reviewer contracts. | Replacing agent math stages with a new framework needs a behavior-equivalence benchmark; not justified by a zero-task allocation run. |

## Work still needed before a production claim

1. **Resolve the real clinic architecture/capacity decisions.** The architecture
   excludes Kubernetes, while this catalog implements Kubernetes workloads. The
   new code refuses that substitution. Add and verify the required workload
   target or obtain an explicit architecture decision. The recorded deadline
   demand (302 must-have points versus about 236 points before the deadline) also
   cannot be solved by code pretending there are more people. Decide scope, date
   or real availability, then regenerate plans and approvals.
2. **Run the paid pipeline in its configured environment.** Keep inputs/models
   comparable and record changed prompts/options. Confirm nonempty sprint and
   allocation outputs, semantic quality, all scanner outcomes, actual token use,
   and parent/child critical-path times. Compare total wall time and total cost;
   summed parallel call times are not elapsed time. No percentage speedup is
   promised here.
3. **Diagnose the original provider startup failure on that host.** Use the new
   init/validate spans and raw stdout/stderr; collect Docker memory/CPU, container
   exit/OOM state, executable permissions and registry/network failures. The old
   evidence does not establish an OOM root cause. Reusing downloads and changing
   ownership cannot prove the original host problem is gone.
4. **Exercise external integrations in test projects.** Verify GitHub Projects,
   Jira/Linear estimates/parents/labels/dependency direction, calendar time zones,
   missing permissions, response loss and outcome/merged-PR reconciliation.
   Local/mock tests are not live API acceptance evidence.
5. **Account for other committed work before staffing decisions.** The existing
   tracker `open_work` facility does not consistently map all providers' work to
   member/sprint hours and is not deducted automatically. A reliable implementation
   needs explicit identity, remaining effort, time window and exclusion of this
   plan's own tickets to prevent double-counting. Do not subtract arbitrary hours.
6. **Finish stronger crash recovery if required operationally.** Single-file
   writes and leases are implemented. Multi-file journal/recovery, checkpointed
   graph resumption, bounded cache retention, cancellation of synchronous worker
   threads and complete adapter HTTP-client lifecycle management remain work.
7. **Recover ambiguous remote operations deliberately.** Inspect
   `publish/external-ids.json` for `pending` records, then check the exact remote
   destination for the marker/comment/sprint/job. Adopt a confirmed remote object
   or clear only the confirmed-not-created pending operation under exclusive
   project ownership. Never delete the whole mapping to retry. Do not blindly
   retry a response-lost create. Provider-specific automated recovery needs
   explicit remote identity/idempotency support.

## Validation

Automated Python tests include the full local Phase 4 flow through gates and
publishing, nonempty planning/allocation, adversarial approval/write/publication
cases, mocked external readiness, provider error recovery, helper concurrency,
resource cleanup and the recorded clinic capacity regression. External scanners
are explicitly mocked in tests which require a successful scan; those tests are
not presented as real scanner evidence.

Final executed counts, build checks and material environment limitations are
recorded in the pull request and `validation-results.json` next to this document.
CI also runs Python tests, an installed-wheel smoke test outside the checkout,
Java tests, Rego tests, and separate infrastructure image builds.
