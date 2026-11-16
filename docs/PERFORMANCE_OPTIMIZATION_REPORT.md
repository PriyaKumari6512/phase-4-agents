# Performance Optimization and Production Reliability Report

## Document purpose

This report explains how the existing system works, where it spends time, where optimization is possible, what must be fixed before optimization is safe, and how another engineer can verify the findings. It is written to be read independently of the original review conversation.

- **Repository:** <https://github.com/PriyaKumari6512/phase-4-agents>
- **Reviewed commit:** `373565a2ba7e276c162d1c471e1495747f7ea1f6`
- **Review date:** 16 November 2026
- **Scope:** Python agent harness, all Phase 4 tool modules, agent packs and prompts, Java allocation service, infrastructure templates and policies, tracker and dispatch adapters, tests, build configuration, and committed run evidence.
- **Restriction followed:** analysis only. No existing repository code or configuration was edited. Scratch verification scripts and build/test copies were outside the checkout.
- **Final integrity check:** all 373 tracked files matched the reviewed commit, and `git status --porcelain` was empty.

All repository links below point to the reviewed commit. A finding should be rechecked if the implementation changes.

## 1. Executive assessment in plain language

The project already has a useful foundation: language models make judgments, and Python or Java tools do much of the exact parsing, calculation, optimization, rendering, and checking. Keeping that separation is sensible.

The pipeline is slow in the saved examples, but the evidence does **not** support the claim that every part is slow. Several deterministic checks finish in a fraction of a second. The saved runs instead show large cumulative model-input volumes and repeated writer, reviewer, and repair passes. Infrastructure validation also has code paths that can wait for many minutes. Its exact share of a real run could not be measured from the committed artifacts.

The most important practical conclusions are:

1. **Measure each pass, model call, helper, tool, and wait before promising a speed improvement.** Current reports provide totals but not the detailed breakdown needed to prove the largest bottleneck.
2. **Reduce repeated work and repeated context reading.** The clinic backlog is about 1.68 MB. Repeatedly reading large files and reviewing the whole output can amplify input volume over many model calls.
3. **Preserve existing internal parallelism.** Task Breakdown already asks for parallel feature generation and parallel epic enrichment. “Parallelize the subagents” is therefore not a new recommendation by itself.
4. **Task Breakdown and Infrastructure can potentially overlap.** Their main input branches are independent. Shared reports, project state, artifact history, and resource limits must be fixed before running them concurrently.
5. **Infrastructure checks can potentially overlap.** They need a frozen source snapshot or isolated working copies so initialization and cleanup do not interfere with scanners.
6. **Do not replace Timefold with the current local allocator as a quick speed fix.** Their capacity rules and optimization objectives differ. Switching can change assignments and produce a different schedule.
7. **Do not make a faster pipeline by skipping required output or review.** Removing specifications, validators, checks, or AI safeguards would change functionality.
8. **Fix correctness and approval integrity first.** This audit reproduced false success, invalid pinned assignments, lost backlog enrichments, publication of unapproved infrastructure bytes, and overwriting of human tracker edits. Faster execution would make these problems happen faster.

**Production assessment:** not production-ready yet. That assessment is based on demonstrated defects, not on a preference for a different framework.

## 2. How to read the evidence

### 2.1 Evidence labels

| Label | Meaning |
|---|---|
| **Recorded measurement** | A value found in a committed execution artifact. It describes that saved run, not necessarily this commit's current runtime behavior. |
| **Fresh measurement** | A value measured during this review in the review environment. Small timings are observations, not stable performance guarantees. |
| **Reproduced defect** | An isolated execution demonstrated the behavior against the reviewed source. External responses were mocked where stated. |
| **Code-verified behavior** | The implementation directly establishes the behavior, even if no live external service was used. |
| **Hypothesis** | A likely contributor or improvement that needs measurement before its benefit can be claimed. |
| **Conditional risk** | A problem that depends on deployment conditions, scale, or an external system. |
| **Unknown** | Available evidence cannot establish the answer. The report identifies what would resolve it. |

### 2.2 What was actually run

| Verification | Result | Important limit |
|---|---|---|
| Locked Python dependency installation | Successful | Installation does not prove external service compatibility. |
| Existing Python test suite | 135 passed in 18.47 seconds; two deprecation warnings | No live model-quality evaluation. Phase 4 tests use local allocation and disable the infrastructure sandbox. |
| Java service compilation and tests in a separate copy | 40 tests reported: 38 passed, 2 skipped; no failures | `mvn test` is not a complete Docker/deployment or all integration-test verification. |
| Python wheel build | Successful | Agent packs and `gates.toml` were absent from the wheel. |
| Helm lint and representative workload-values rendering | Successful | This does not establish deployment readiness or coverage of every generated values file. |
| Supplied Conftest policy unit tests | 9 passed | A separate policy evaluation still accepted a synthetic unsafe plan. |
| Isolated verification probes | Confirmed the principal findings in this report | These were local probes, not attacks on live services. |
| Original checkout integrity | Clean; all 373 tracked files unchanged | Scratch scripts, downloads, and test output were outside the repository. |

No live LLM pipeline was started. No tracker issues were created or changed. No coding agent was dispatched. No infrastructure was applied. No PR was published.

### 2.3 Limits on historical evidence

The repository includes an older `docs/CODEBASE_AUDIT.md`. It contains useful leads, but it describes an earlier implementation and references logs and output folders that are not all committed here. Its statement that there is no orchestrator is contradicted by the current code.

This report independently checked the current implementation. Historical claims without their underlying evidence were not adopted as fresh measurements. In particular, this report does not claim to have measured a 55-minute Infrastructure run or a multi-day run: the corresponding raw Phase 4 report/log evidence was not present in the reviewed artifact set.

## 3. What the system actually contains

### 3.1 Agents and supporting components

There are five writer packs and five corresponding validator packs:

| Writer | What it does | Main output |
|---|---|---|
| PRD | Turns requirements and feedback into a product requirements document | `prd.md` |
| Task Breakdown | Produces feature specifications and an estimated, dependency-checked backlog | `specs/**`, `backlog/**` |
| Sprint Planning | Calculates capacity and places stories into sprints | `sprint/**` |
| Work Allocation | Assigns one sprint's tasks to people and AI workers | `allocation/**` |
| Infrastructure and Pipeline | Generates infrastructure, GitOps, and CI files and runs checks | `infra/**` |

Task Breakdown declares two named helper types: `speckit-feature` and `backlog-enricher`. The harness also provides a general-purpose helper. The number of actual helper invocations is chosen through model tool calls; it is not a fixed number of agents.

The architecture documents in the sample data were generated by earlier systems. This repository does not implement every agent named in those older reports.

### 3.2 Main execution path

```text
Requirement / uploaded documents
    -> PRD writer
    -> PRD validator and possible fixes
    -> prd.md

prd.md + architecture.md + project settings
    -> Task Breakdown
       -> initialize specification workspace
       -> decide feature split
       -> generate each feature's specifications
       -> build backlog
       -> enrich epics
       -> add cross-feature dependencies
       -> validate and repair
    -> Task Breakdown validator and possible fixes
    -> P4-G1 approval
    -> Sprint Planning
       -> capacity calculation
       -> business-value judgments
       -> CP-SAT solve
       -> goals and explanations
    -> Sprint validator and possible fixes
    -> P4-G2 approval
    -> Work Allocation
       -> prepare tasks and eligibility
       -> judge AI candidates
       -> Timefold or local CP-SAT solve
       -> assignment explanations
    -> Allocation validator and possible fixes
    -> P4-G3 approval

architecture.md + project settings
    -> Infrastructure and Pipeline
       -> interpret intent
       -> render catalog templates
       -> run checks
       -> repair and check again
    -> Infrastructure validator and possible fixes
    -> P4-G4 approval

Approved artifacts
    -> explicit publishing
    -> tracker items, sprint placement, assignees, coding-agent dispatch, infrastructure/CI PRs
```

The Infrastructure approval also influences whether Work Allocation considers a repository eligible for AI work.

### 3.3 What runs sequentially, concurrently, or conditionally

| Area | Actual behavior |
|---|---|
| Phase 4 orchestrator | Picks one runnable stage at a time. Current order is Task Breakdown, Infrastructure, Sprint Planning, Work Allocation. |
| Writer and validator | Ordered: the validator judges the writer's current output. A fix follows a failed verdict, then another review. |
| Feature generation | Task Breakdown's prompt asks for all needed feature helpers in one message so they can run together. This is a requested strategy, not a guarantee that every provider/run uses the same concurrency. |
| Inside one feature | Specification, plan, task generation, and analysis are ordered because later files depend on earlier files. |
| Epic enrichment | Prompt requests parallel enrichment. Actual shared backlog updates are protected by a process-local reentrant lock. |
| Infrastructure environment initialization | Sequential environment loop, with a possible retry per environment. |
| Other infrastructure checks | Sequential commands. Docker mode starts a container for individual commands. |
| Infeasibility options | Candidate solves are attempted sequentially. |
| Allocation backend | Timefold is used when explicitly requested or when auto mode's availability probe succeeds. Otherwise local CP-SAT is used. |
| Publishing | Explicit commands. Orchestrator publication order is backlog, sprint, assignments, then infrastructure. |

**Source evidence:** [agent graph construction][src-agent], [CLI run loop][src-cli], [orchestrator][src-orchestrator], [Task Breakdown prompt][prompt-task], [specification helper prompt][prompt-feature], [backlog tools][src-backlog], [sandbox checks][src-sandbox].

## 4. Measured performance evidence

### 4.1 Saved Phase 4 runs

| Saved run | Recorded elapsed time | Approximate minutes | Input tokens | Output tokens | Result |
|---|---:|---:|---:|---:|---|
| Task Breakdown | 1,328.0 seconds | 22.13 | 20,487,709 | 701,618 | Success after three validator attempts |
| Sprint Planning, first run | 725.7 seconds | 12.10 | 4,302,385 | 66,891 | Partial after three validator attempts |
| Work Allocation | 870.6 seconds | 14.51 | 3,218,025 | 101,225 | Success after three validator attempts |

Evidence files:

- [Task Breakdown report][run-task]
- [Sprint Planning partial-run report][run-sprint]
- [Work Allocation report][run-allocation]

These are **separate runs**, not one complete measured end-to-end execution. The later successful sprint output has no matching run report in this artifact set. There is no Infrastructure output/report alongside its committed Phase 4 inputs.

Do not add these numbers and describe the result as the full pipeline time. Human approval waits, later runs, Infrastructure execution, publication, and other waiting time are not completely represented.

### 4.2 What the token totals mean

The reports aggregate token use across model calls, helper activity, reviews, and fixes. The large input totals do not mean that one request contained millions of unique tokens.

Approximate recorded cache-read shares:

| Run | Cache-read input tokens | Share of recorded input tokens |
|---|---:|---:|
| Task Breakdown | 17,711,615 | 86.45% |
| Sprint Planning partial run | 3,675,038 | 85.42% |
| Work Allocation | 2,776,087 | 86.27% |

This supports investigating repeated context processing. It does not establish the dollar cost, the model provider's actual cache latency, or the percentage of wall time attributable to cache reads.

Task Breakdown also records a small fast-model entry of 786 input and 360 output tokens. Its main recorded work uses the strong model. The current code gives named helpers default framework summarization unless explicitly overridden; the parent fast-model summarizer is not automatically supplied to those helper specifications.

### 4.3 Dataset size

The saved clinic backlog has:

| Property | Value |
|---|---:|
| Epics | 10 |
| Stories | 79 |
| Tasks | 484 |
| Total items | 573 |
| JSON file size | 1,675,710 bytes |

Evidence: [saved clinic backlog][clinic-backlog].

Why this matters: a helper asked to read `backlog.json` receives a large shared artifact even when it needs only one epic. Repeating this across helpers, reviews, and fixes can increase model input volume. The exact amount wasted requires per-call traces.

### 4.4 Fresh offline timings

| Operation | Observed time | Interpretation |
|---|---:|---|
| Clinic backlog deterministic validation, read-only | About 0.218 seconds | The current deterministic backlog checker is not a major standalone delay on this saved dataset. |
| Clinic sprint consistency check | About 0.0322 seconds | The checker itself is inexpensive on this saved plan. |
| Small bookmark-fixture sprint solve | About 0.030–0.032 seconds | Small feasible instances can solve quickly. This is not a benchmark of large/infeasible cases. |
| Full existing Python suite | 18.47 seconds | This is suite time, not production pipeline time. |

The saved successful clinic sprint plan records an `OPTIMAL` solve taking 0.217 seconds. The saved partial-run plan records a `FEASIBLE` solve taking 10.003 seconds. Solver difficulty is instance-dependent.

Evidence: [successful clinic sprint plan][clinic-sprint], [partial-run plan][clinic-partial-plan].

### 4.5 What cannot yet be concluded

The repository does not provide enough timing detail to calculate:

- the exact percentage of each run spent generating model output;
- time spent reading large artifacts versus reasoning;
- time consumed by each helper;
- time spent in each review or fix pass;
- retry and rate-limit waiting time per run;
- cold versus warm infrastructure download time;
- the dominant infrastructure scanner;
- publication time for a real tracker;
- a defensible percentage speedup for any proposed change.

Any statement such as “parallelism will make this twice as fast” would be unsupported.

## 5. Why time can accumulate

### 5.1 Repeated writer, reviewer, and repair executions

Every main writer pack allows two fix loops. A run can execute:

```text
write -> verify -> fix -> verify -> fix -> verify
```

That is six graph executions, not six model calls. Each execution can involve multiple model calls and tool operations.

Each pass is built anew, and later passes are instructed to reread existing output and request history. There is no durable graph checkpoint configured for exact continuation of an interrupted pass.

**Evidence:** the three saved Phase 4 reports each record three validator attempts; [CLI `_run` and `run_pass`][src-cli]; [agent construction][src-agent].

**Optimization implication:** improve first-pass correctness, avoid making a model rediscover deterministic failures, and make repairs focus on the affected artifacts. Do not remove the semantic reviewer as an unproven shortcut.

### 5.2 Large context and large tool replies

Examples in the current flow:

- feature/enrichment helpers read shared JSON;
- specification helpers read several skill instructions and templates;
- sprint solving returns story information and deferrals;
- allocation solving returns assignments, score details, and runner-up information;
- validators inspect source requirements and generated artifacts again.

The reports show high aggregate input-token counts. Large repeated context is therefore a supported target for investigation, but the exact latency contribution is still a hypothesis.

**Evidence:** [tool interfaces][src-tools], [backlog helper prompt][prompt-enricher], [saved reports][run-root].

### 5.3 Infrastructure validation has long sequential waits

Current behavior includes:

- `tofu init` followed by validation for each environment;
- a possible second attempt on a recognized network failure;
- 300-second command timeouts for initialization attempts;
- 600-second limits for Trivy and Checkov commands;
- separate command/container starts;
- removal of downloaded working-directory state after initialization;
- a shared provider plugin cache, but no retained module working directory.

For three environments:

```text
3 environments × 2 attempts × 300 seconds = 1,800 seconds
```

This is a **code-derived upper bound for initialization attempts**, not a measured Infrastructure runtime. Other checks can add time.

A timeout returns text beginning with `timeout after`. That same text is included in the network-error markers, so a timeout can be retried and later reported as a skipped validation. This is both a latency and a result-integrity issue.

**Evidence:** [sandbox `_run`, `_validate_envs`, and `_other_checks`][src-sandbox].

### 5.4 Infeasibility diagnosis has a larger budget than the main solve

A sprint solve can run:

1. the initial CP-SAT solve;
2. a second single-worker solve to obtain an assumption core;
3. several candidate relaxation solves.

The default main solve limit is 10 seconds. Candidate solves use a separate default limit of 5 seconds each. There is no single overall tool deadline covering the whole sequence.

**Implication:** the model's “10-second solve” does not bound the complete `sprint_solve` tool call. Hard instances and many unsuccessful candidates can take longer.

**Evidence:** [sprint model `solve` and `verified_options`][src-sprint-model].

### 5.5 Allocation performs repeated reads and scans

The allocation flow:

- calculates availability in preparation and again in solving;
- can request calendar data repeatedly;
- reads outcome data repeatedly for task/provider combinations;
- repeatedly filters ownership rows for worker/path combinations;
- repeatedly scans backlog tasks by parent story;
- uses a service probe, job submission, polling, and optional score-analysis request when Timefold is selected.

**Implication:** pre-indexing and per-solve snapshots can remove repeated deterministic work. Whether that materially reduces a full agent run must be measured; the saved run may be dominated by model work.

**Evidence:** [allocation `_agent_success`, `_ownership`, `_ctx`, `_window`, and `solve`][src-allocation], [Timefold client][src-alloc-solver].

### 5.6 Publishing is deliberately slow and sequential

The HTTP client has a default one-second minimum interval for write operations. Publishing a large backlog can require issue creation, parent links, dependencies, sprint movement, assignment, and comments.

The PR publisher reads and writes files individually through the Contents API. A large infrastructure change set therefore causes many network operations and commits.

**Implication:** network round trips and request limits can dominate publication. This was not measured against a live tracker. Changes to commit granularity or visible operation order require explicit contract decisions.

**Evidence:** [HTTP client][src-http], [publishing][src-publish], [PR publishing][src-github-api].

## 6. Optimization opportunities, with feasibility and safeguards

The opportunities below are proposals, not claims that changes have already been implemented.

### O01. Add detailed timing before changing execution strategy

**Problem:** aggregate reports cannot identify the exact slowest operation.

**Proposed improvement:** record timing for stage, pass, model call, helper, tool, retry, queue wait, and external request. Include token categories, solver status, and immutable input fingerprints. Keep detailed data separate from the concise user-facing report.

**Why it helps:** the team can distinguish expensive model generation from slow downloads, retries, solver search, and publication.

**Behavior preservation:** add observation without changing model prompts, constraints, or outputs. Do not log credentials or uncontrolled full document content simply to measure time.

**Validation:** reconcile child spans with the overall duration; quantify overlap without double-counting it. Keep parent wall time separate from summed concurrent worker time.

**Effort/risk:** medium effort, low functional risk. This should precede claims about percentage speedups.

### O02. Give agents focused access to relevant items

**Problem:** helpers need a small part of a large backlog but are directed toward the complete file.

**Proposed improvement:** provide focused reads by item IDs, epic, level, and required fields. Return counts and identifiers when details are unnecessary, while keeping full evidence available on demand.

**Expected benefit:** fewer repeated input tokens and less irrelevant material in model context.

**Trade-off:** overly narrow context can hide cross-feature dependencies or acceptance requirements.

**Behavior preservation:** preserve the complete artifact contracts and ensure semantic review can still inspect all relevant requirements. Retain a cross-feature review stage. Do not drop specification or acceptance evidence.

**Validation:** compare requirement coverage, task IDs, dependencies, eligibility, quality of explanations, review gaps, token use, and wall time on the same examples. Exact LLM text equality cannot be assumed.

**Evidence:** 1.68 MB clinic backlog and recorded multi-million-token totals; [backlog helper prompt][prompt-enricher].

### O03. Run reliable deterministic checks before paying for model review

**Problem:** a model reviewer can spend calls discovering errors a tool can identify immediately.

**Proposed improvement:** invoke a trustworthy deterministic check at the writer/reviewer boundary and feed precise failures back to the writer. Keep the semantic reviewer for requirement interpretation, unsupported assumptions, meaningful goals, and explanation accuracy.

**Expected benefit:** fewer unnecessary review calls and shorter repair cycles.

**Prerequisite:** fix the checkers first. Current checks can accept invalid plans, exempt unsafe pins, or treat skipped checks as successful.

**Behavior preservation:** do not turn a successful mechanical check into automatic semantic approval. Preserve the human gates.

**Validation:** ensure all existing semantic review criteria remain represented, and compare false-negative rates on known bad artifacts.

### O04. Make repair passes narrow and recoverable

**Problem:** a fix pass starts a new graph and rereads large shared context.

**Proposed improvement:** persist the failed checks, affected item IDs/files, and current input snapshot. Limit repair scope to those items, then rerun the affected mechanical checks and required semantic review.

**Expected benefit:** less repeated analysis and smaller changes between review attempts.

**Trade-off:** a local repair can affect another artifact, so dependency invalidation must remain complete.

**Behavior preservation:** preserve all output files and review requirements. Revalidate downstream artifacts when their sources change.

**Prerequisite:** transactional artifact updates and trustworthy provenance.

### O05. Overlap Task Breakdown and Infrastructure

**Problem:** the orchestrator currently waits for Task Breakdown before starting Infrastructure even though the main inputs are independent.

**Feasibility:** Task Breakdown consumes PRD and architecture; Infrastructure consumes architecture and settings. Their output branches are mostly separate.

**Proposed improvement:** schedule these branches concurrently against the same frozen input snapshot, with separate job reports and artifact ownership.

**What must be fixed first:** shared latest-report use, project-state writes, run-history attribution, cross-process locking, approval handling, and provider/resource budgets.

**Behavior preservation:** do not let a new schedule change the Infra approval/readiness state seen by Allocation. If the original allocation would see CI readiness, wait for the equivalent state before running it.

**Expected benefit:** overlap independent branch time. No numeric gain can be established because a matching Infrastructure timing is unavailable.

**Simplified timing model:** excluding human waits, the current generation sum is approximately `T_task + T_infra + T_sprint + T_allocation`. If Allocation must wait for Infrastructure readiness, a possible parallel critical path is approximately `max(T_infra, T_task + T_sprint) + T_allocation`. Gates and shared resources can make actual time longer.

**Evidence:** [orchestrator stages and runnable selection][src-orchestrator].

### O06. Verify and bound the parallelism already requested inside Task Breakdown

**Problem:** the prompt requests parallel feature helpers and epic helpers, but there is no application-level concurrency budget or detailed helper timing.

**Proposed improvement:** verify actual scheduling for the selected model/provider; limit concurrent helpers based on quota, CPU, memory, and error rate.

**Important existing behavior:** the Codex subscription adapter forces `parallel_tool_calls = false`. The prompt's request for multiple task calls in one message should therefore not be assumed to work identically in that mode.

**Behavior preservation:** keep each feature's specification -> plan -> tasks -> analysis order. Keep the barrier before global backlog construction and cross-feature dependency analysis.

**Expected benefit:** more predictable throughput and fewer quota failures. Increasing concurrency may make performance worse if it causes rate limits or memory pressure.

**Evidence:** [Task Breakdown prompt][prompt-task], [subscription payload handling][src-subscription].

### O07. Keep epic judgment parallel but merge shared backlog updates safely

**Problem:** model work can be independent by epic, but each update reads and rewrites shared files under a process-local lock.

**Proposed improvement:** let independent helpers produce validated update deltas concurrently, then merge those deltas in a defined order against a versioned backlog snapshot.

**Expected benefit:** preserve model concurrency while reducing accidental conflicts and repeated full-file operations.

**Behavior preservation:** reject conflicting updates; preserve stable IDs, dependencies, estimates, and enrichment replay. Do not remove the existing lock before a safe replacement exists.

**Prerequisite:** fix partial updates and split/rebuild data loss.

### O08. Parallelize independent infrastructure checks on a frozen source snapshot

**Problem:** independent scanners currently run one after another.

**Proposed improvement:** run a small bounded set of checks concurrently, or use a single sandbox lifecycle with independent subprocesses and per-tool result files.

**Expected benefit:** total check time can approach the slowest independent branch rather than the sum of branches.

**Side effects to handle:** Tofu initialization creates and removes working files; policy verification creates a temporary policy directory; scanners may read those files; caches and downloads consume shared resources.

**Behavior preservation:** scan identical source bytes, preserve every required check and finding, and merge results in stable tool order. Use isolated working copies where commands mutate their workspace.

**Validation:** compare normalized findings and failure statuses between sequential and concurrent runs, including timeout, cancellation, unavailable-tool, and malformed-output cases.

**Evidence:** [sandbox implementation][src-sandbox].

### O09. Cache module/provider downloads and reuse unchanged validation safely

**Problem:** repeated initialization downloads work that is not retained, while provider caching alone does not retain module working directories.

**Proposed improvement:** cache verified module/provider artifacts using a complete key: module version, provider version, platform, lock data, relevant configuration, and tool version. Cache check results only against the full source/tool/policy fingerprint.

**Expected benefit:** faster repeated validation and repair rounds, especially on cold networks.

**Trade-off:** bad cache keys can reuse an outdated dependency or hide a real change.

**Behavior preservation:** never reuse a previous 'passed' result for different bytes or policies. Preserve reproducibility and dependency locking.

**Concurrency note:** current OpenTofu documentation describes best-effort cache concurrency safety. Still test the actual version, storage, and parallel-download pattern used here.

**Evidence:** [sandbox cache and cleanup][src-sandbox]; [OpenTofu cache documentation][ref-tofu-cache].

### O10. Correct timeout classification and introduce one overall tool budget

**Problem:** a 300-second initialization timeout can be classified as a network error, retried, and ultimately counted as skipped. Solver option analysis also has multiple separate budgets.

**Proposed improvement:** distinguish timeout, transient transport failure, invalid input, scanner failure, and completed checks. Give each tool one overall deadline with smaller sub-budgets and bounded retry eligibility.

**Expected benefit:** lower worst-case waiting time and clearer failures.

**Behavior preservation:** do not report less validation as success. Preserve the last valid artifact if the attempt fails. Retry only operations known to be safe or reconciled.

**Validation:** inject timeouts and interrupted commands; verify cleanup, reported status, and retention of the prior good artifact.

### O11. Evaluate infeasibility options with controlled parallelism

**Problem:** candidate fixes are solved sequentially, each with its own budget.

**Feasibility:** candidate models are independent when built from the same immutable input.

**Proposed improvement:** test a small number concurrently, using a total CPU budget and stable collection order. Reduce unnecessary candidate duplication.

**Critical prerequisite:** the candidate transformation must match the actual selected relaxation. Currently deadline softening does not.

**Trade-off:** each solve defaults to eight workers. Running several in parallel can oversubscribe the host. The review Java runtime reported only two available CPUs.

**Behavior preservation:** retain original candidate ordering and option IDs; ensure feasible-option impacts come from the exact model that will be applied.

### O12. Precompute allocation lookups once per solve

**Problem:** outcomes and ownership are repeatedly read or filtered.

**Proposed improvement:** load outcomes once, group them by provider/task type, and index ownership by repository/path/worker. Index tasks by story. Reuse parsed immutable data within one solve.

**Expected benefit:** fewer file reads and repeated scans. This is a local optimization, not a claim that it will eliminate a 14-minute model run.

**Behavior preservation:** use the same snapshot for all calculations. Fix repository-ambiguous ownership matching and per-worker eligibility before caching the wrong result.

**Validation:** compare inputs, assignments, eligibility, explanations, and runner-up choices before and after indexing.

### O13. Reuse calendar snapshots carefully

**Problem:** preparation and solving can repeat token acquisition and availability requests.

**Proposed improvement:** use a timestamped planning snapshot for a defined planning attempt and reuse credentials/tokens within their valid lifetime.

**Trade-off:** calendars can change. Reusing an old snapshot can change planning correctness.

**Behavior preservation:** make snapshot time and refresh policy explicit; do not silently turn a calendar failure into full availability. Keep timezone handling consistent.

**Validation:** test changed calendar data, failed requests, expired tokens, and planning across a date boundary.

### O14. Make similarity calculations sparse if scale justifies it

**Problem:** custom TF-IDF creates a dense document-by-vocabulary matrix, and duplicate checking creates a dense pairwise similarity matrix. Duplicate checking stops above 1,500 tasks.

**Proposed improvement:** evaluate sparse matrix construction and bounded pair generation with the same tokenization, weighting, normalization, and thresholds.

**Expected benefit:** reduced memory and potentially better performance for larger inputs.

**Why it is not first priority:** fresh clinic backlog validation was approximately 0.218 seconds.

**Behavior preservation:** compare similarity scores near the 0.92 duplicate threshold and 0.2 analogy threshold, reference selection, and ordering. An embedding model would change semantics and is not a drop-in performance fix.

**Evidence:** [text similarity][src-textsim], [backlog validation and analogy][src-backlog].

### O15. Improve publication efficiency only after publication safety

**Problem:** many sequential requests, full mapping rewrites, and one-file-at-a-time PR commits.

**Proposed improvement:** avoid unnecessary repeated lookups within a publication attempt, retain stable metadata caches, and investigate provider bulk operations. For a multi-file PR, consider the Git Trees API followed by one commit/reference update.

**Important constraint:** commit granularity and externally visible operation order are observable behavior. A move from many commits to one commit is a publishing-contract change, even if final files match.

**Prerequisite:** fix approval-byte checks, persistent human overrides, destination-scoped IDs, and crash reconciliation. Do not simply parallelize POST requests.

**Validation:** simulate response loss after successful creation and concurrent publication; check for duplicate issues, links, comments, sprints, and dispatches.

**Evidence:** [publishing][src-publish], [PR helper][src-github-api], [Git Trees API][ref-git-trees], [safe retry guidance][ref-idempotency].

### O16. Stream input conversion and bound resource use

**Problem:** Excel conversion collects all rows before applying the row-display limit. Text detection reads the entire file before taking a prefix.

**Proposed improvement:** inspect a bounded byte prefix for text detection and process spreadsheet rows incrementally with explicit limits. Bound archive/document expansion.

**Expected benefit:** less memory and fewer avoidable large-input failures.

**Behavior preservation:** retain the documented visible-row behavior and truncation notice. If resource limits change accepted input sizes, document that as an input-policy change.

**Evidence:** [input conversion][src-inputs].

### O17. Avoid rebuilding unchanged local model metadata unnecessarily

**Problem:** each pass constructs model clients/graphs, and profile-based compaction setup performs profile resolution separately for its triggers.

**Proposed improvement:** measure construction cost, then reuse immutable provider profiles or configuration results within a process where safe.

**Expected benefit:** likely small compared with model generation, but easy to measure.

**Trade-off:** model/auth settings can change, and clients may carry state or credentials. Do not cache across incompatible auth contexts.

**Evidence:** [model setup][src-model], [agent construction][src-agent].

### O18. Consider typed workflows for fixed planning stages only after equivalence is established

**Problem:** Sprint Planning and Allocation have mostly fixed mechanical steps, but a model repeatedly chooses tool calls to coordinate them.

**Alternative:** use explicit workflow steps for calculations, and structured model calls for the actual judgments and explanations.

**Expected benefit:** fewer orchestration turns and more predictable failure handling.

**Why this is not an immediate safe change:** the agent currently handles arbitrary feedback and uses an open-ended reviewer. Replacing that behavior may remove capabilities.

**Behavior preservation:** reuse the existing file schemas, solvers, outputs, semantic review, and feedback cases. Prove equivalence on representative requests before switching.

## 7. Correctness findings that must constrain optimization

These findings are included because they directly affect whether caching, concurrency, fallback, and faster publication can preserve behavior. Several are release blockers independent of speed.

### F01. Protected gate paths and other projects are writable

- **Status:** reproduced; critical approval-boundary defect.
- **Evidence:** the real middleware/backend accepted `/outputs/bm/./gates/FORGED.approved.json` and `/outputs/other/leak.txt`.
- **Root cause:** the guard checks path components before canonicalizing `.`; the backend is rooted at all projects rather than the active project. Domain tools also accept a caller-selected project.
- **Impact on optimization:** concurrent or compromised agent activity can affect another job or forge approvals. More parallelism is unsafe before isolation is fixed.
- **Recommendation:** bind filesystem and tool access to the active project; canonicalize paths and enforce containment at the backend boundary; validate the exact approval artifact set. Empty approval artifact maps must not pass vacuously.
- **Source:** [guardrails][src-guard], [backend][src-backend], [project files][src-files], [gates][src-gates].

### F02. Contradictory review verdicts can report success

- **Status:** reproduced schema acceptance; verified success handling.
- **Evidence:** `Verdict(satisfied=False, status_so_far='success', gaps=['missing required output'], ...)` is accepted.
- **Root cause:** verdict fields have no cross-field invariant; exit status follows the status string. Declared outputs are not rechecked after every fix.
- **Impact:** a faster review path can produce false success.
- **Recommendation:** make satisfaction/status/gaps consistent and recheck final artifacts. An unchanged artifact can legitimately satisfy an idempotent request; do not require rewrites merely to prove execution.
- **Source:** [Verdict and construction][src-agent], [CLI verification][src-cli].

### F03. An old report can make a failed child look successful

- **Status:** reproduced with a mocked child process.
- **Evidence:** child exit code 1 plus an old success report returned `{status: success, exit_code: 1}`.
- **Root cause:** report selection is based on agent name, without a new invocation/job identity; orchestration trusts status without requiring a successful child exit.
- **Impact:** separate or concurrent stage execution can consume the wrong result.
- **Recommendation:** use unique invocation records and require consistent process/report outcomes.
- **Source:** [orchestrator `run_agent`][src-orchestrator].

### F04. Incremental invalidation omits inputs the implementation really uses

- **Status:** reproduced and code-verified.
- **Evidence:** changing `team`/`ai_agents` did not change Infrastructure's input digest. Editing `specs/.../tasks.md` did not change Task Breakdown's input digest.
- **Other gaps:** calendar date progression is not represented; catalog/pack changes are not fully tracked; stage output existence uses gate files, not all pack outputs.
- **Impact:** caching or resume can retain stale CODEOWNERS, workflows, backlog, or planning windows. Missing Markdown/check/PR artifacts can be overlooked.
- **Recommendation:** derive invalidation from actual stage dependencies and the full declared output contract.
- **Source:** [orchestrator stages/digests/assessment][src-orchestrator], [Infrastructure rendering][src-infra].

### F05. Locking and recovery do not cover a complete job

- **Status:** code-verified.
- **Evidence:** filesystem lock is process-local; direct domain-tool writes bypass it. Backlog has its own process-local lock. Reports, orchestration state, approval records, and publishing mappings are direct file writes.
- **Other gaps:** no configured durable graph checkpoint; no explicit overall model-pass/token budget; a failure while saving history/report can interfere with final cleanup.
- **Impact:** interleaved writes, misleading run history, damaged state, or repeated work after interruption.
- **Recommendation:** project/job ownership, atomic writes, staged artifact promotion, durable recovery, and bounded cancellation. Preserve a prior valid artifact on failed attempts.
- **Source:** [locking][src-locking], [history][src-history], [CLI][src-cli], [agent construction][src-agent].

### F06. Backlog updates can partially apply and split enrichment can disappear

- **Status:** three reproduced failures.
- **Evidence:** invalid story points returned an error but a description mutation persisted; an invalid task enum was reported applied and broke the next read; split-child acceptance criteria changed from one to zero after rebuild.
- **Root cause:** mutation occurs before all checks finish; assignment validation is disabled; child enrichments are removed before split children are recreated; replay errors are not handled as an atomic transaction.
- **Impact:** repair loops can repeatedly recreate lost work, waste tokens, or approve inconsistent data.
- **Recommendation:** validate candidate updates before committing them and rebuild split topology before replaying child updates.
- **Source:** [backlog build/apply/update][src-backlog].

### F07. Title equality is not enough to reuse an enrichment

- **Status:** code-verified.
- **Evidence:** enrichments survive when item title remains equal, even if specification content changes. Backlog source hashes omit feature spec/task files.
- **Impact:** cached estimates and AI proposals can be stale despite apparently stable IDs.
- **Recommendation:** use relevant content fingerprints and explicitly re-evaluate affected judgments.
- **Source:** [backlog build][src-backlog].

### F08. Backlog validation and critical-path analysis have gaps

- **Status:** code-verified.
- **Findings:** duplicate item IDs collapse in `by_id`; read-only checking repairs an in-memory copy; blocking automatic coverage excludes NFR prefixes; critical-path edge weighting omits the starting node's effort; duplicate checks are skipped above 1,500 tasks.
- **Impact:** downstream prioritization and validation can be based on a different or incomplete interpretation of the saved artifact.
- **Recommendation:** distinguish repair from checking, reject duplicate IDs, define coverage explicitly, and calculate node-weighted critical paths correctly.
- **Source:** [backlog validation][src-backlog], [contracts][src-contracts].

### F09. UNKNOWN solving can overwrite a valid plan with an empty one

- **Status:** reproduced using an injected unsuccessful solver result.
- **Evidence:** `UNKNOWN` replaced the prior plan, placed zero stories, and produced `check_ok: true` after annotation. `MODEL_INVALID` follows the same missing-placement fallback path.
- **Impact:** a short timeout used for speed can destroy a valid plan and appear acceptable.
- **Recommendation:** unsuccessful attempts must not replace the last valid plan; validate solver status and complete story accounting independently.
- **Source:** [sprint solve/check][src-sprint].

### F10. Relaxation candidates do not match actual application consistently

- **Status:** reproduced and code-verified.
- **Evidence:** removing a hard deadline for candidate evaluation placed a sample story outside the plan; applying the advertised soft deadline placed it in sprint 1 because penalties differ.
- **Additional defect:** relaxed solver capacities are not propagated to saved sprint-slot capacities, so saved checks can disagree with the solved model.
- **Impact:** parallel option evaluation or cached options can preserve misleading impacts rather than real results.
- **Recommendation:** use exactly the same transformation for evaluating and applying an option; persist effective capacities.
- **Source:** [sprint model options][src-sprint-model], [sprint relaxation][src-sprint].

### F11. Invalid settings can hang or break planning

- **Status:** invalid-value acceptance reproduced; consequences established in code.
- **Evidence:** project schema accepted sprint length 0 and hours per point 0.
- **Consequence:** zero sprint length prevents the window-advance loop from progressing; zero hours per point divides by zero.
- **Recommendation:** validate positive durations/scales, valid collections, and unique worker/feature identifiers before model or solver execution.
- **Source:** [contracts][src-contracts], [capacity][src-capacity].

### F12. Availability and forecasts are internally inconsistent

- **Status:** code-verified.
- **Findings:** elapsed active-sprint days are counted; existing assigned tracker work is not deducted; maintenance reserve is omitted in the history-based forecast branch; simulation returns a 60-sprint boundary without marking unfinished samples; calendar failures become empty unavailability; member timezones are stored but not used in day calculations.
- **Impact:** faster cached planning can be more confidently wrong.
- **Recommendation:** explicit snapshot times, remaining-capacity accounting, consistent reserve treatment, visible calendar uncertainty, and censored forecast reporting.
- **Source:** [capacity][src-capacity], [calendars][src-calendars], [tracker methods][src-trackers].

### F13. Pins bypass hard allocation rules

- **Status:** reproduced; high-severity correctness defect.
- **Evidence:** task `001-T001` was pinned to `claude-code`, explicitly blocked from AI and vetoed for that worker, yet assigned; recorded eligibility was false and allocation checker returned `ok: true`.
- **Root cause:** pinned tasks are removed from the solver and appended directly; AI post-checks exempt pins. Capacity reporting also mixes original and remaining capacity.
- **Impact:** neither backend optimization nor faster dispatch is safe if pins can override hard constraints.
- **Recommendation:** validate pins against all hard rules before solving and keep original capacity distinct from remaining capacity.
- **Source:** [allocation solve/check][src-allocation].

### F14. Dependency timing uses nominal offsets, not actual predecessor completion

- **Status:** code-verified.
- **Evidence:** earliest starts are calculated before worker assignment; neither backend receives a real cross-worker task-dependency contract. Story precedence is not fully expanded into same-sprint task timing.
- **Impact:** affinity changes or prior work can delay a predecessor, while a dependent task starts using the old offset; a predecessor can remain unassigned while a dependent task is assigned.
- **Recommendation:** enforce actual precedence and blocked-dependency behavior in both backends, with independent schedule validation. Otherwise the contract must explicitly stop claiming an executable schedule.
- **Source:** [allocation task graph][src-allocation], [solver inputs][src-alloc-solver].

### F15. Timefold and local CP-SAT are not equivalent

- **Status:** capacity difference reproduced; objective difference code-verified.

| Rule | Timefold implementation | Local implementation |
|---|---|---|
| Capacity | Employee's last task end must fit capacity | Sum of assigned durations must fit capacity |
| Idle time due to minimum start | Included in finishing time | Not included in capacity constraint |
| Objective levels | Lexicographic hard/medium/soft | One weighted scalar objective |
| Priorities | Weighted task completion time | Priority reward and post-solve ordering |
| Workload objective | Squared employee finishing times | Maximum utilization ratio |

- **Reproduction:** a 60-minute local task starting at minute 100 was assigned to a worker with capacity 60; it ended at minute 160.
- **Impact:** changing backend for speed changes feasibility and potentially assignments.
- **Recommendation:** establish a canonical constraint/objective contract and differential tests before automatic interchangeability or service removal.
- **Source:** [local allocator][src-alloc-solver], [Java constraint provider][java-constraints], [Java employee capacity][java-employee], [Timefold score documentation][ref-timefold].

### F16. AI limits and ownership are not evaluated per correct worker/repository

- **Status:** code-verified; cross-repository ownership ambiguity reproduced.
- **Findings:** eligibility uses the largest enabled worker task limit and combined provider outcome evidence; assignment can go to a different provider; required skills are truncated to three; ownership lookup ignores repository.
- **Impact:** a quick eligibility cache can incorrectly permit work or rank an unrelated owner.
- **Recommendation:** evaluate task/worker pairs, retain all required skills, and key ownership by repository/path/worker.
- **Source:** [allocation eligibility and ownership][src-allocation], [profile mining][src-profiles].

### F17. Auto allocation fallback does not handle failure after a healthy probe

- **Status:** reproduced with mocked service failure.
- **Evidence:** a true availability probe followed by `solve_timefold` raising propagated `RuntimeError: service failed`; it did not use the fallback.
- **Other issues:** poll GET does not call `raise_for_status`; readiness accepts responses below 500; polling uses a fixed 600-second deadline; optional score-analysis request failures are swallowed.
- **Impact:** slow/failed service calls can consume time without a clear recovery outcome.
- **Recommendation:** explicit readiness, checked poll responses, budget-derived deadlines, cleanup, and reconciliation of submitted jobs. Any fallback must respect F15.
- **Source:** [Timefold client][src-alloc-solver].

### F18. Ten skipped infrastructure checks produce overall success

- **Status:** reproduced.
- **Evidence:** sandbox off resulted in ten skipped checks, `checks_passed: true`, and `infra_check.ok: true`.
- **Root cause:** aggregate success accepts `passed or skipped` for every check.
- **Impact:** disabling checks would make execution appear faster and successful, but would remove assurance.
- **Recommendation:** separate preview/no-observed-failure from required-check completion; define production validation requirements explicitly.
- **Source:** [Infrastructure validate/check][src-infra].

### F19. A scanner execution failure can be parsed as no findings

- **Status:** Checkov case reproduced; other parse risks code-verified.
- **Evidence:** simulated exit code 1 and non-JSON text made Checkov report `passed: true`, zero findings. The corresponding Trivy failure was correctly marked failed in that probe; this report does not claim the two behaved identically.
- **Other risks:** output is truncated to its last 20,000 characters before JSON parsing; timeout may become skipped; generated per-environment values are not all checked; pipeline exit propagation is incomplete.
- **Impact:** faster parallel scanning is unsafe unless every result is trustworthy.
- **Recommendation:** complete result files, validated schema, checked exit status, separate timeout/error states, and representative seeded scanner failures.
- **Source:** [sandbox parsing][src-sandbox].

### F20. Passing policy unit tests do not mean generated infrastructure was checked

- **Status:** reproduced.
- **Evidence:** all nine supplied unit tests passed. A synthetic plan with `var.region = sa-east-1` and IPv6 SSH ingress from `::/0` was accepted by policy evaluation.
- **Root cause:** allowed-region rule expects a constant provider expression; generated providers use a variable. Ingress rules check IPv4. `conftest verify` only tests policy code, not the generated infrastructure plan.
- **Recommendation:** test real plan shapes and IPv6; distinguish policy-library tests from plan evaluation.
- **Source:** [policy library][src-policy], [sandbox invocation][src-sandbox], [AWS base template][template-base].

### F21. Generated GitOps files do not form a complete deployment path

- **Status:** code-verified, with representative Helm rendering.
- **Evidence:** a workload references `api-env`; its ExternalSecret is generated beside the values file, but the chart/ApplicationSet path does not include that file. Separate alerts/platform resources lack another generated application path.
- **Other issues:** all environments target the same in-cluster Kubernetes destination; separate environment states create the same ECR repository names when account/region are shared; only the first requested region is used; sanitized name collisions are unchecked; empty region lists are accepted; workload resource sizing is not fully tied to size classes.
- **Known placeholders:** DNS, certificates, image promotion, startup command, and bootstrap add-ons are explicitly called out by the implementation and remain prerequisites.
- **Impact:** passing syntax checks is not deployment success; caching them cannot establish readiness.
- **Recommendation:** explicit application ownership for every resource, correct cluster targeting, shared-resource ownership, and input capability checks.
- **Source:** [Infrastructure rendering][src-infra], [GitOps templates][templates-gitops], [ECR template][template-ecr], [Argo Helm documentation][ref-argo].

### F22. Atlantis image references a missing policy directory

- **Status:** code-verified build-context blocker; no Docker build was performed.
- **Evidence:** `COPY policies/ /home/atlantis/policies/` has no matching `services/atlantis/policies/` in the service build context. Other COPY paths indicate that service directory is the intended context.
- **Additional dependency:** the configured plan webhook receiver is not implemented in this repository.
- **Recommendation:** correct artifact/build-context delivery and identify the receiver as an explicit external dependency; verify the image and plan/policy path.
- **Source:** [Atlantis Dockerfile][atlantis-docker], [Atlantis configuration][atlantis-config].

### F23. Publication can send unapproved infrastructure bytes

- **Status:** reproduced; high-severity integrity defect.
- **Evidence sequence:** render -> validate -> approve intent/manifest -> replace a generated file without changing the manifest -> publish locally. Approval remained valid and replacement bytes were published.
- **Additional reproduction:** a downstream sprint gate was accepted after its upstream backlog approval had become stale.
- **Root cause:** publisher checks approved metadata, then reads mutable current files without checking all outgoing hashes/provenance.
- **Recommendation:** publish an immutable approved snapshot or verify every outgoing byte and relevant upstream dependency immediately before publication.
- **Source:** [gate requirement and infra publication][src-publish].

### F24. Human tracker edits are preserved once, then overwritten

- **Status:** reproduced with the local tracker.
- **Evidence:** human title override was listed as preserved on one update; a later generated update had no preserved field and final title became `Generated 3`.
- **Root cause:** preserved human content is saved as the new comparison baseline, which later looks engine-owned. Adoption after a lost mapping has an unknown baseline as well.
- **Impact:** retrying or speeding publication can overwrite a person's work.
- **Recommendation:** separate desired generated baseline, observed remote state, and explicit human overrides; handle unknown baselines conservatively.
- **Source:** [three-way merge and ensure][src-publish].

### F25. Exactly-once publishing is not guaranteed

- **Status:** code-verified failure windows; no live duplication test performed.
- **Evidence:** remote POST and local mapping save are separate; POST retry can occur before reconciliation; comments/sprints/dispatches lack one universal idempotency contract; mappings use tracker kind rather than complete destination identity.
- **Impact:** crashes, response loss, concurrent publishers, or changing destination can create duplicates or use incorrect IDs.
- **Recommendation:** destination-scoped state, operation intent/status, safe serialization, provider idempotency where available, and reconciliation of ambiguous outcomes.
- **Source:** [publication mapping][src-publish], [HTTP retry client][src-http], [safe retry reference][ref-idempotency].

### F26. Generated-and-approved CI is mistaken for operational CI readiness

- **Status:** code-verified.
- **Evidence:** CI readiness checks approved manifest membership, not merged workflows or successful runs. Orchestrator publishes assignments before infrastructure/CI PRs. Dispatch ignores planned starts, dependencies, and configured worker concurrency. Status methods have no integrated outcome writer/reconciliation caller.
- **Impact:** more parallel dispatch can start work before CI exists or before prerequisites finish. Default shadow mode cannot progress without externally supplied outcomes.
- **Recommendation:** separate generated, approved, published, merged, and operational states; durable dispatch queue; enforce WIP/dependencies; record outcomes.
- **Source:** [CI readiness][src-allocation], [assignment publication][src-publish], [dispatch adapters][src-dispatch], [orchestrator publishing][src-orchestrator].

### F27. Tracker synchronization does not fully reflect local changes

- **Status:** code-verified; external API compatibility not live-tested.
- **Examples:** later GitHub point updates are suppressed by comparisons normalized to `None`; returning a story to backlog does not clear all child iterations; removed dependency links remain; parent/label changes are outside owned updates; removed/reintroduced issues are not explicitly reopened; some Linear queries do not paginate.
- **Jira-specific uncertainty:** link direction is marked unverified in source and the referenced integration test is absent. A sandbox create/read-back is needed, using Atlassian's documented linking model.
- **Recommendation:** define field/relation ownership and test repeated lifecycle updates for each adapter.
- **Source:** [tracker adapters][src-trackers], [publication fields][src-publish], [Jira link model][ref-jira].

### F28. Built wheel does not include required top-level deployment assets

- **Status:** reproduced wheel inspection.
- **Evidence:** wheel build succeeded; 63 entries were inspected. Package taxonomy and spec templates were present, but `agents/` and `gates.toml` were absent. Default paths are derived from package installation location.
- **Impact:** checkout/editable runs can work while a standalone wheel installation cannot find its default packs/gates.
- **Recommendation:** package the assets or explicitly supply and validate an external versioned asset bundle. Include an installed-wheel smoke test.
- **Source:** [build configuration][src-pyproject], [default path configuration][src-config].

### Additional supporting findings

| Component | Finding | Relevant action |
|---|---|---|
| PRD and semantic review | Clear writer/reviewer responsibilities exist, but deterministic tests do not establish real output quality. | Keep requirement-grounded evaluation when optimizing model work. |
| Input conversion | All spreadsheet rows are materialized before truncation; text detection reads whole files. | See O16. |
| Logging | Full arguments and generated content are persisted without a clear retention boundary. | Bounded/redacted logging and retention; preserve useful timing. |
| Observability | Aggregated tokens and elapsed time are useful but insufficient for critical-path attribution. | See O01. |
| Subscription adapters | Private SDK internals, custom headers, and payload rewrites are version-sensitive. | Lockfile-tied compatibility tests; do not assume a new SDK is equivalent. |
| Helper configuration | Parent custom summarization is not explicitly passed to named helpers. | Measure and explicitly configure the intended helper summarizer before claiming savings. |
| Profile mining | Ownership repository context is discarded at lookup; skill evidence aggregation also needs an explicit refresh policy. | Fix lookup context and define snapshot validity. |
| Java service | Domain/reference validation and constraint tests are useful and passed. | Retain them; add Python/Java parity and client contract tests. |
| Solver UI | Uses escaping and origin checks in relevant rendering/integration paths. | Browser behavior and deployment exposure remain unverified. |
| Sandbox | Docker path avoids forwarding cloud credentials, but bridge networking is not registry-restricted; local fallback inherits host environment. | Treat isolation as deployment-dependent and verify required boundaries. |
| CI | Python suite runs with lockfile; Java, real scanner, image-build, and tracker-contract coverage are missing from this workflow. | Extend checks specifically around the demonstrated gaps. |

## 8. Objective comparison of implementation alternatives

| Existing implementation | Alternative | When it is justified | Why it is not automatic |
|---|---|---|---|
| File-based run state | LangGraph checkpointer and staged artifacts, optionally SQLite for job/publication state | Recovery and atomic state are needed. | A distributed workflow platform is not established as necessary for this CLI's current scale. |
| Custom shell-free spec-kit helper | Upstream scripts in a constrained environment | Exact upstream compatibility is needed. | Current narrow adapter avoids arbitrary shell exposure; keep it if supported behavior is explicit and tested. |
| Dense NumPy TF-IDF | Sparse matrices and established text-vectorization tooling | Larger vocabulary/history causes measurable memory/time pressure. | Current clinic validation is fast; similarity semantics must remain equal. |
| Timefold plus local CP-SAT | One canonical allocator or tested common semantics | Maintenance or service overhead warrants consolidation. | Current backends disagree; consolidation can change assignments. |
| Minimal Markdown-to-ADF conversion | Markdown parser plus an ADF renderer | Nested formatting fidelity becomes required. | Extra dependencies are unnecessary if the limited documented subset is sufficient. |
| Per-file Contents API commits | Git tree/commit/reference operations | Atomic change-set publication and fewer round trips are needed. | Commit history changes; agree on that external contract. |
| Private subscription SDK adaptations | Maintained provider-supported integration | A functionally equivalent supported integration is available. | Account-specific availability and compatibility were not established. |
| Open-ended coordination for fixed math stages | Typed workflow with structured judgment calls | O18 evaluations show equal functionality and lower overhead. | Arbitrary feedback and semantic review must be preserved. |

## 9. Safe implementation sequence and priority

Relative effort: **S** = localized, **M** = several modules, **L** = execution/state architecture. These are not schedule commitments.

| Order | Work | Reason | Effort | Dependencies / change risk |
|---|---|---|---|---|
| P0 | F01 project/path isolation and approval structure | Restores the approval trust boundary. | M | Foundational; moderate risk. |
| P0 | F23 exact approved-byte publication and provenance | Prevents unreviewed or stale publication. | M | Low to moderate risk. |
| P0 | F13/F16 pins and per-worker hard eligibility | Prevents invalid assignments. | M | Define non-overridable rules; moderate risk. |
| P0 | F18–F20 real validation completion and parser correctness | Prevents false assurance. | M | Must precede scan caching/concurrency. |
| P1 | F02/F03/F09 outcome handling | Prevents false success and loss of valid plans. | S–M | Low functional risk when defect behavior is explicitly specified. |
| P1 | F06–F08 backlog atomicity, replay, and graph checks | Stops corruption and repeated repair work. | M | Needed before parallel update merging. |
| P1 | F14/F15 actual precedence and backend parity | Makes schedules and fallback trustworthy. | L | Requires a canonical contract; high change risk. |
| P1 | F24/F25/F27 publishing state and human-edit protection | Prevents overwrites and duplicate external work. | M–L | Needed before publication concurrency. |
| P1 | F21/F22 complete infrastructure deployment path | Makes generated artifacts usable. | M | External bootstrap/receiver dependencies. |
| P1 | F04/F10–F12 invalidation, effective relaxations, capacity | Prevents stale/invalid planning and hangs. | M | Required before broad caching. |
| P2 | F05 job ownership, atomic state, recovery, budgets | Enables reliable long-running and concurrent execution. | L | Prerequisite for O05. |
| P2 | F26 readiness and dispatch reconciliation | Makes AI execution controllable. | L | Depends on safe publication and allocation. |
| P2 | F28 deployment assets and targeted CI | Makes installation and verification reproducible. | S–M | Low risk. |
| P2 | O01 detailed instrumentation | Establishes defensible performance baselines. | M | Can start alongside localized correctness fixes. |
| P2 | O02/O04/O09/O12 remove repeated work | Targets context, repair, downloads, lookups. | M | Validate unchanged functional contracts. |
| P3 | O05/O08/O11 bounded concurrency | Shortens independent branches. | M–L | Depends on isolation, trustworthy results, and measured resource budgets. |
| P3 | O14/O15/O18 structural alternatives | Addresses larger-scale overhead. | M–L | Only if measurements justify added complexity and equivalence is demonstrated. |

### Suggested rollout boundaries

1. Establish regression cases for the reproduced defects.
2. Repair integrity/correctness without changing performance strategy.
3. Add timings and capture baseline runs.
4. Optimize repeated local work and infrastructure downloads.
5. Reduce model context with quality evaluations.
6. Introduce one concurrency change at a time.
7. Re-measure after each change; keep only changes whose functionality and quality hold.

A defect fix deliberately changes a defective behavior. A performance optimization should preserve a correct behavior. Keep those changes separate so reviewers can understand the acceptance criteria.

## 10. Measurement plan for the engineer receiving this report

### 10.1 Required timing fields

Capture at least:

| Field | Purpose |
|---|---|
| Commit, dependency lock hash, pack/catalog/policy versions | Establish comparable code and tool inputs. |
| Project input fingerprint and planning date | Prevent accidental comparison of different work. |
| Job, stage, pass, helper, tool IDs | Attribute work to the right execution. |
| Start/end and duration | Build the real critical path. |
| Queue, retry, and rate-limit wait | Separate useful work from waiting. |
| Model/provider/auth mode and effective tuning | Explain different model behavior. |
| Input/cache/output tokens per call | Locate repeated context and generation volume. |
| Solver main/core/candidate durations, status, bound, worker count | Separate search difficulty from orchestration. |
| Scanner command/tool version, environment, cache state, execution status | Identify download, startup, parse, or findings delays. |
| External request count, operation kind, retries | Quantify publication overhead. |
| CPU, peak memory, disk/network pressure | Determine a safe concurrency limit. |

Do not sum concurrent spans and call the result wall-clock time. Report both total work and critical-path elapsed time.

### 10.2 Baseline cases

Use the bookmark fixture for a small case and an appropriately sanitized clinic dataset for the larger case. Add a deliberately infeasible sprint instance and infrastructure with seeded failures.

For each experiment, keep inputs, provider/model, auth mode, planning date, solver settings, and relevant cache condition controlled. Start with several repeated runs and report median plus spread; expand only if variance makes the result inconclusive.

Track:

- total run time and stage critical path;
- model input/output/cache tokens;
- number and duration of review/fix passes;
- requirement coverage and unsupported assumptions;
- solver validity and relevant business constraints;
- assignment eligibility, capacity, and precedence;
- scanner coverage and findings;
- duplicate publication or human-edit conflicts;
- failure/recovery behavior.

### 10.3 Specific optimization experiments

| Experiment | Compare | Keep unchanged | Reject the change if |
|---|---|---|---|
| Focused epic reads | Full shared reads vs targeted item access | Requirements, artifacts, semantic review | Coverage/dependency quality falls or required evidence disappears. |
| Deterministic pre-review | Existing review order vs pre-check plus semantic review | Review criteria and gates | Mechanical success bypasses semantic review or false success rises. |
| Infrastructure cache | Cold vs warm verified downloads | Versions, lock data, source bytes | Different dependencies or stale results are reused. |
| Concurrent scanners | Sequential vs bounded concurrency | Snapshot, tools, policies, findings | Findings/status differ or cleanup races occur. |
| Concurrent Task/Infra | Sequential vs isolated branches | Inputs, readiness seen by Allocation, publication contract | History/report attribution changes or allocation inputs differ. |
| Allocation indexes | Repeated scans vs indexed snapshot | Eligibility and scoring behavior | Assignments or evidence change unexpectedly. |
| Sparse similarity | Dense vs sparse exact formulation | Tokenization, thresholds, reference ordering | Threshold classifications or references change. |
| Solver candidate concurrency | Sequential vs bounded candidates | Exact transformations, order, IDs | Options differ because of changed semantics or oversubscription. |

### 10.4 Failure cases that matter for this code

- Child exits before writing a new report while an old success report exists.
- Solver returns UNKNOWN or MODEL_INVALID with an existing valid plan.
- A malformed backlog update contains both valid and invalid fields.
- A split child is enriched and then rebuilt.
- A pin conflicts with an AI block, veto, skill, capacity, or worker limit.
- A dependent task's predecessor is delayed or unassigned.
- A scanner exits nonzero, emits invalid/truncated JSON, or times out.
- Docker/tooling is unavailable.
- Generated infrastructure bytes change after approval.
- Upstream artifacts change after a downstream gate is approved.
- External create succeeds but the response or mapping save is lost.
- A human edit is followed by two or more generated updates.
- Two executions try to work on the same project.
- Calendar data changes or fails across planning calls.
- Cancellation occurs while a container or solver job is running.

These are specific to observed execution paths; they are not a generic production checklist.

## 11. Reproduction evidence recorded during this review

The excerpts below summarize the actual isolated probe results. They contain no live service changes or credentials.

### 11.1 Filesystem protection

```json
[
  {"path": "/outputs/bm/./gates/FORGED.approved.json", "written": true},
  {"path": "/outputs/other/leak.txt", "written": true}
]
```

The probe passed a write through the actual guard and actual filesystem backend against temporary project directories.

### 11.2 Backlog partial update and split rebuild

```json
{
  "partial_update": {
    "errors": ["S-001-US1: story_points must be one of [1, 2, 3, 5, 8, 13], got 4"],
    "mutation_written": true,
    "lost_on_rebuild": true
  },
  "split_enrichment": {
    "before_acs": 1,
    "after_acs": 0,
    "dropped": ["001-T010a"]
  }
}
```

A separate invalid-enum update returned `{"applied": 1, "errors": []}`, followed by `ProjectError` on the next typed read.

### 11.3 Invalid pinned AI assignment

```json
{
  "task": "001-T001",
  "assigned_to": "claude-code",
  "eligibility": {
    "eligible": false,
    "reason": "AI blocked by the approver",
    "shadow": false
  },
  "validator": {
    "ok": true,
    "problems": [],
    "engine": "local_cpsat"
  }
}
```

The task was both AI-blocked and vetoed for the pinned worker. The real local allocation flow still appended the pin.

### 11.4 Skipped checks and unapproved publication

```json
{
  "infra_skipped": {"passed": true, "skipped_count": 10, "check": true},
  "publish_unapproved_infra": {
    "gate_valid": true,
    "substituted_bytes_published": true
  },
  "publish_stale_upstream": {
    "upstream_stale": true,
    "downstream_gate_accepted": true
  }
}
```

Publication used local PR-output mode. No GitHub PR was created.

### 11.5 Human-edit overwrite

```json
{
  "first_preserved": ["title"],
  "second_preserved": [],
  "final_title": "Generated 3"
}
```

The remote side was the local tracker adapter, which exercises the shared merge logic without contacting a real tracker.

### 11.6 UNKNOWN solve and invalid configuration

```json
{
  "unknown_sprint": {
    "result": "UNKNOWN",
    "placed": 0,
    "replaced_previous": true,
    "check_ok": true
  },
  "invalid_config_accepted": {
    "sprint_length_days": 0,
    "hours_per_point": 0.0
  }
}
```

UNKNOWN was injected to exercise failure handling; it was not described as a naturally observed timeout on that fixture.

### 11.7 Scanner parse failure

```json
[
  {"tool": "trivy", "passed": false, "summary": "1 HIGH/CRITICAL"},
  {"tool": "checkov", "passed": true, "summary": "0 failed checks (0 high/critical)"}
]
```

Both command responses were simulated as exit code 1 with text `not JSON: scanner internal error`. The difference demonstrates the actual Checkov false-success path.

### 11.8 Local allocator capacity semantics

```json
{
  "assigned": {"w": [["t", 100]]},
  "capacity": 60,
  "end_time": 160
}
```

The task's duration was 60 minutes. The local model counted duration but not the idle period before minute 100. Java capacity code uses final end time.

### 11.9 Stale process report, omitted invalidation, and option mismatch

```text
stale_child_report:
  status = success
  exit_code = 1

infra_team_ai_digest_unchanged = true
spec_edit_digest_unchanged = true

soften_option_semantics:
  verified_candidate = {"s": 0}
  actual_soft = {"s": 1}

auto_no_failure_fallback:
  RuntimeError: service failed
```

The child process, unsuccessful remote solver, and small relaxation case used controlled simulations. Input-digest behavior used the real digest function.

### 11.10 Policy evaluation

The supplied policy library's nine unit tests passed. The additional synthetic plan had:

```text
variables.region.value = sa-east-1
provider region expression references var.region
security group ingress from IPv6 ::/0 to port 22
```

Conftest plan evaluation reported no failures. This is evidence of policy coverage gaps, not evidence that unsafe infrastructure was actually deployed.

### 11.11 Test and repository-integrity summaries

```text
Python: 135 passed, 2 warnings, 18.47 seconds.
Java: 40 tests reported, 0 failures, 0 errors, 2 skipped; BUILD SUCCESS.
Helm: 1 chart linted, 0 failed; representative values rendered.
Policy unit tests: 9 passed, 0 failures.
Tracked files: 373.
Changed tracked files: [].
Working-tree status: empty.
```

## 12. What must remain unchanged during performance work

Preserve:

- existing accepted input and output schemas and required artifact paths;
- required specification, plan, task, backlog, sprint, assignment, and infrastructure artifacts;
- requirement coverage and source traceability;
- hard dependencies, deadlines, skills, worker limits, capacity, AI blocks, and vetoes;
- review and approval meaning;
- stable IDs and replay behavior;
- human edits and intended tracker ownership rules;
- publication destinations, approved bytes, and safe retry behavior;
- failure reporting and retention of prior valid outputs;
- supported feedback and repeat-request behavior.

A new cache, parallel worker, model choice, or solver implementation is acceptable only after evidence shows it preserves those requirements. Changes to commit history, timing of external dispatch, or supported input limits must be reviewed as externally observable contract changes.

## 13. Unresolved evidence and explicit limits

| Unknown | Why it remains unknown | Evidence needed |
|---|---|---|
| Exact model/tool/wait percentages | Saved reports contain aggregate values, not complete timings. | Per-call/per-tool/per-helper spans. |
| Real end-to-end wall time | Available reports are separate partial stage histories. | One correlated pipeline run including gates and publication. |
| Current live LLM quality | No live model pipeline was launched in this review. | Representative quality evaluations with source-grounded rubrics. |
| Infrastructure's dominant runtime operation | Matching Phase 4 Infra output/report is absent. | Cold/warm check timings by tool/environment. |
| Exact useful helper concurrency | Model/provider scheduling and quota behavior vary. | Traces for the configured provider and auth mode. |
| Live tracker semantics | Adapters were not run against sandbox tenants. | Create/read-back/update lifecycle tests per provider. |
| Actual deployment topology | Bootstrap, accounts, clusters, DNS, and external services are not established here. | Versioned deployment configuration and a controlled deployment rehearsal. |
| Full network/sandbox isolation | Local fallback and Docker deployment differ. | Tests of the actual deployed isolation profile. |
| Browser behavior | Solver UI was read but not browser-tested. | Headless/visible browser flow checks where relevant. |
| Guaranteed speedup | No implemented optimization was benchmarked. | Before/after tests with identical functional acceptance criteria. |

## 14. External research and why it applies here

External resources inform the recommendations; they do not establish what this repository implements.

| Official source | Specific relevance |
|---|---|
| [LangGraph persistence][ref-langgraph] | The harness lacks a configured durable checkpoint. Established checkpointing can support recovery, while staged files address tool side effects. |
| [Timefold constraints and scores][ref-timefold] | Confirms lexicographic score semantics, supporting the finding that the scalar local objective is not automatically equivalent. |
| [OpenTofu validation][ref-tofu-validate] | Explains the scope of validation and initialization without backend access. Static validation is not a successful cloud apply. |
| [OpenTofu CLI cache configuration][ref-tofu-cache] | Relevant to provider download reuse and version-specific concurrent cache behavior. |
| [GitHub Git Trees API][ref-git-trees] | Provides an established way to construct a complete multi-file change set before committing/updating a branch. |
| [AWS safe idempotent retries][ref-idempotency] | Directly applicable to remote creation followed by local mapping writes and ambiguous retries. |
| [Argo CD Helm behavior][ref-argo] | Explains chart/value rendering and why separate generated resources require a deployment source. |
| [GitHub agent responsibility guidance][ref-ai-review] | Supports independent testing and human review; another AI review can miss defects or produce false positives. |
| [Atlassian issue linking model][ref-jira] | Needed to validate actual dependency direction through create/read-back. |

## 15. Source index

### Repository and runtime evidence

- [Reviewed repository revision][repo]
- [Committed Phase 4 run artifacts][run-root]
- [Task Breakdown report][run-task]
- [Sprint Planning partial-run report][run-sprint]
- [Work Allocation report][run-allocation]
- [Clinic backlog][clinic-backlog]
- [Successful clinic sprint plan][clinic-sprint]
- [Partial-run sprint plan][clinic-partial-plan]

### Implementation references

- [Agent packs, graph construction, and Verdict][src-agent]
- [CLI writer/reviewer/fix loop][src-cli]
- [Orchestrator][src-orchestrator]
- [Filesystem guard][src-guard]
- [Backend routing][src-backend]
- [Filesystem locking][src-locking]
- [Approval gates][src-gates]
- [History and fingerprints][src-history]
- [Model setup][src-model]
- [Subscription model adapters][src-subscription]
- [Input conversion][src-inputs]
- [Logging][src-logging]
- [Phase 4 contracts][src-contracts]
- [Project files][src-files]
- [Tool interfaces][src-tools]
- [Specification helper adapter][src-speckit]
- [Backlog processing][src-backlog]
- [Text similarity][src-textsim]
- [Sprint processing][src-sprint]
- [Sprint solver][src-sprint-model]
- [Capacity simulation][src-capacity]
- [Calendars][src-calendars]
- [Allocation processing][src-allocation]
- [Allocation solver clients and local model][src-alloc-solver]
- [Skill/ownership mining][src-profiles]
- [Infrastructure rendering and validation][src-infra]
- [Infrastructure sandbox][src-sandbox]
- [Publishing][src-publish]
- [Tracker adapters][src-trackers]
- [HTTP retries/throttling][src-http]
- [PR publication][src-github-api]
- [Coding-agent dispatch][src-dispatch]
- [Java constraints][java-constraints]
- [Java employee/capacity model][java-employee]
- [Infrastructure policies][src-policy]
- [GitOps templates][templates-gitops]
- [Atlantis Dockerfile][atlantis-docker]
- [Atlantis configuration][atlantis-config]
- [Build/dependency configuration][src-pyproject]
- [Default filesystem configuration][src-config]
- [CI workflow][src-ci]

[repo]: https://github.com/PriyaKumari6512/phase-4-agents/tree/373565a2ba7e276c162d1c471e1495747f7ea1f6
[run-root]: https://github.com/PriyaKumari6512/phase-4-agents/tree/373565a2ba7e276c162d1c471e1495747f7ea1f6/runs/clinic-test-2
[run-task]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/runs/clinic-test-2/agent-1-task-breakdown/output/report.json
[run-sprint]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/runs/clinic-test-2/agent-2-sprint-planning/output-run-1-partial/report.json
[run-allocation]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/runs/clinic-test-2/agent-3-work-allocation/output/report.json
[clinic-backlog]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/runs/clinic-test-2/agent-1-task-breakdown/output/backlog/backlog.json
[clinic-sprint]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/runs/clinic-test-2/agent-2-sprint-planning/output/sprint/sprint-plan.json
[clinic-partial-plan]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/runs/clinic-test-2/agent-2-sprint-planning/output-run-1-partial/sprint/sprint-plan.json
[src-agent]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/agent.py
[src-cli]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/cli.py
[src-orchestrator]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/phase4/orchestrator.py
[src-guard]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/guardrails.py
[src-backend]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/backends.py
[src-locking]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/locking.py
[src-gates]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/gates.py
[src-history]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/history.py
[src-model]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/model_setup.py
[src-subscription]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/subscription_models.py
[src-inputs]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/inputs.py
[src-logging]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/logging_setup.py
[src-contracts]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/phase4/contracts.py
[src-files]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/phase4/files.py
[src-tools]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/phase4/tools.py
[src-speckit]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/phase4/speckit.py
[src-backlog]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/phase4/backlog.py
[src-textsim]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/phase4/textsim.py
[src-sprint]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/phase4/sprint.py
[src-sprint-model]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/phase4/sprint_model.py
[src-capacity]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/phase4/capacity.py
[src-calendars]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/phase4/calendars.py
[src-allocation]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/phase4/allocation.py
[src-alloc-solver]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/phase4/alloc_solver.py
[src-profiles]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/phase4/profiles.py
[src-infra]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/phase4/infra.py
[src-sandbox]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/phase4/sandbox.py
[src-publish]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/phase4/publish.py
[src-trackers]: https://github.com/PriyaKumari6512/phase-4-agents/tree/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/phase4/trackers
[src-http]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/phase4/trackers/base.py
[src-github-api]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/phase4/github_api.py
[src-dispatch]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/phase4/dispatch.py
[java-constraints]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/services/allocation-solver/src/main/java/org/acme/taskassigning/solver/TaskAssigningConstraintProvider.java
[java-employee]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/services/allocation-solver/src/main/java/org/acme/taskassigning/domain/Employee.java
[src-policy]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/agents/infra-pipeline/knowledge/catalog/policies/phase4.rego
[templates-gitops]: https://github.com/PriyaKumari6512/phase-4-agents/tree/373565a2ba7e276c162d1c471e1495747f7ea1f6/agents/infra-pipeline/knowledge/catalog/templates/gitops
[template-base]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/agents/infra-pipeline/knowledge/catalog/templates/terraform/aws/base.tf.j2
[template-ecr]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/agents/infra-pipeline/knowledge/catalog/templates/terraform/aws/ecr.tf.j2
[atlantis-docker]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/services/atlantis/Dockerfile
[atlantis-config]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/services/atlantis/repos.yaml
[prompt-task]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/agents/task-breakdown/system_prompt.md
[prompt-feature]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/agents/task-breakdown/subagents/speckit-feature.md
[prompt-enricher]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/agents/task-breakdown/subagents/backlog-enricher.md
[src-pyproject]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/pyproject.toml
[src-config]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/src/agent_engine/config.py
[src-ci]: https://github.com/PriyaKumari6512/phase-4-agents/blob/373565a2ba7e276c162d1c471e1495747f7ea1f6/.github/workflows/tests.yml
[ref-langgraph]: https://docs.langchain.com/oss/python/langgraph/persistence
[ref-timefold]: https://docs.timefold.ai/timefold-solver/latest/constraints-and-score/overview
[ref-tofu-validate]: https://opentofu.org/docs/cli/commands/validate/
[ref-tofu-cache]: https://opentofu.org/docs/cli/config/config-file/
[ref-git-trees]: https://docs.github.com/en/rest/git/trees
[ref-idempotency]: https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/
[ref-argo]: https://argo-cd.readthedocs.io/en/stable/user-guide/helm/
[ref-ai-review]: https://docs.github.com/en/copilot/responsible-use/agents
[ref-jira]: https://developer.atlassian.com/cloud/jira/platform/issue-linking-model/
