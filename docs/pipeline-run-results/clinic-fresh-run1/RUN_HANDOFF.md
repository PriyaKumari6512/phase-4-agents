# Run handoff: `clinic-fresh-run1`

Written by the assistant that implemented the instrumentation and ran the pipeline, from its own session history.
Nothing here was recomputed from the result files. **(O)** = directly observed in the session. **(U)** = uncertain,
inferred, or a guess I made at the time.

**Correction to the framing of this task:** the run did **not** complete successfully. It stopped with the
orchestrator waiting at gate `P4-G4` (exit code 2) because the Infra & Pipeline stage ended `partial`. Details below.

## 1. What was implemented

Opt-in performance diagnostics plus four small outcome-integrity corrections, as requested in the task "Prepare This
Repository for an Evidence-Based Pipeline Performance Investigation". Documented in `docs/PERF_DIAGNOSTICS.md` and
`docs/PERF_BENCHMARK_RUNBOOK.md`.

- **New files:** `src/agent_engine/perf.py`, `perf_callbacks.py`, `perf_manifest.py`, `perf_summary.py`;
  `tests/test_perf_diagnostics.py`, `tests/test_outcome_integrity.py`; `scripts/perf_overhead.py`; the two docs above.
- **Edited (timing spans added):** `cli.py`, `agent.py`, `history.py`, `locking.py`, `__init__.py`, and under
  `phase4/`: `orchestrator.py`, `tools.py`, `backlog.py`, `speckit.py`, `sprint.py`, `sprint_model.py`, `capacity.py`,
  `calendars.py`, `allocation.py`, `alloc_solver.py`, `infra.py`, `sandbox.py`, `publish.py`, `github_api.py`,
  `cli.py`, `trackers/base.py`, `contracts.py`; plus `README.md` and `.env.example`.
- **Outcome-integrity corrections (behaviour changes):**
  1. The orchestrator accepts a child's `report.json` only if it carries that invocation's id and agrees with the exit code.
  2. A verdict with `satisfied=false` and `status_so_far=success` is treated as `partial`; declared outputs are re-checked after fix passes.
  3. A sprint solve ending `UNKNOWN`/`MODEL_INVALID` no longer overwrites `sprint-plan.json`; `sprint_check` flags such plans.
  4. Sandbox checks parse complete output (previously the last 20,000 characters), classify each check
     (`passed/findings/tool_unavailable/skipped/timeout/parse_error/execution_error`), and the manifest gains
     `validation_complete` and `checks_incomplete`. The existing gate policy (`checks_passed`) is unchanged.
- Models, providers, prompts, validators, fix-loop limits, solver settings and concurrency were not changed.

## 2. Branch and revision

- **(O)** Original: `main` at `b855f74`, with uncommitted and untracked Phase 4 work in the working tree.
- **(O)** Branch `chore/pipeline-performance-instrumentation` in a separate git worktree
  (`C:\Users\admin\Desktop\agent-sprint-planner\phase4-agent-engine-perf`).
- **(O)** Commit `b3da492` is a **verbatim snapshot of that uncommitted work** copied from the main working tree
  (about 16.7k lines: the whole `phase4/` package, agent packs, docs, tests, services). Without it the worktree
  would not contain the code. Commit `782bbdb` is the instrumentation and corrections. The run manifests record
  source revision `782bbdb4db4a`. **A PR to `main` therefore shows both commits.**
- **(O)** The original checkout's `git status`/`git diff` fingerprints were identical before and after my work.
- This results commit (documentation and evidence copies) was made after the run; no application code changed after it.

## 3. Commands executed (in order, abridged to the ones that matter)

1. `git worktree add -b chore/pipeline-performance-instrumentation ../phase4-agent-engine-perf HEAD`; applied the main working tree's tracked diff and copied its untracked source folders; committed as `b3da492`.
2. `uv` was not on PATH. Created `.venv` with `python -m venv --without-pip` and two `.pth` files (the original venv's `site-packages`, and the worktree `src`).
3. `pytest -q` (baseline, before changes), repeatedly during development, and after the final edits.
4. `scripts/perf_overhead.py --runs 7`, then `--runs 9`.
5. A CLI smoke test with diagnostics on in a scratch folder: `phase4 init`, `phase4 orchestrate --plan`, `phase4 publish backlog` (refused as designed in generation-only mode), `perf list`, `perf summarize`.
6. Committed `782bbdb`.
7. Run preparation (when asked to run the pipeline): started Docker Desktop; hard-linked the worktree's `.env` to the original `.env`; copied `prd.md`, `architecture.md`, `phase4/project.json` from the original `outputs\clinic-test-2` into `perf-bench\run-1\outputs\clinic-test-2`.
8. `orchestrate.ps1 -Plan` (dry run, no model calls), then `orchestrate.ps1` (real run, no auto-approval), then, after the user chose to auto-approve, `orchestrate.ps1 -TestApprove`.
9. `agent-engine perf summarize --session clinic-fresh-run1` (run several times as the run progressed).

`orchestrate.ps1` (included in `console/`) sets: `AGENT_ENGINE_OUTPUTS_DIR`, `AGENT_ENGINE_LOGS_DIR`,
`AGENT_ENGINE_PERF=1`, `AGENT_ENGINE_PERF_SESSION=clinic-fresh-run1`, `AGENT_ENGINE_PERF_MODE=generation`,
`PHASE4_PR_MODE=local`, then runs `python -m agent_engine phase4 orchestrate --project-name clinic-test-2 --sprint 1`
(`--test-approve` for the continuation).

## 4. Stages run

All four, in the orchestrator's order: `task-breakdown`, `infra-pipeline`, `sprint-planning`, `work-allocation`.
Nothing was published, dispatched or applied. The real `clinic-test-2` folder was not modified.

## 5. What I directly observed

Figures below were read from live event output and the generated `summary.md`/`summary.json` during the session; the
authoritative values are in the collected files.

- **(O) task-breakdown:** `success`; 1 write, 1 review (0 gaps), 0 fix passes. 9 `speckit-feature` helpers ran
  concurrently, then 9 `backlog-enricher` helpers. `backlog_build` returned `ERROR:` text three times (spec-kit task-line
  format at `specs/001-platform-foundation` line 382 and `specs/002-identity-access` line 274); the agent continued.
- **(O) infra-pipeline:** `partial`. `infra_set_intent` returned a schema error once (`notes` not a list). `infra_validate`
  ran three times. Each time `tofu_validate` reported findings (2, then 3, then 3) and `checkov` reported 21 findings;
  other checks passed. The raw outputs for the `tofu_validate` runs show the AWS provider plugin failing to start
  ("Unrecognized remote plugin message ... Failed to read any lines from plugin's stdout") for dev, stg and prod. The validator's
  fourth model call ran about 4 min 54 s, produced 64,000 output tokens with finish reason `max_tokens`, and the verdict
  JSON could not be parsed (`StructuredOutputValidationError`); the stage ended `partial` with no fix pass.
- **(O) sprint-planning:** `success`. The main CP-SAT solve was `INFEASIBLE`; the solver tested many candidate relaxations
  (my live count reached 64 infeasible, followed by one `FEASIBLE` that used its full 5 s limit). The validator accepted the
  plan on the first review.
- **(O) work-allocation:** `success`. Timefold was unreachable (`auto` mode), so the local CP-SAT backend was used. Verdicts:
  partial (4 gaps), partial (2 gaps), success (0 gaps); 1 write, 3 reviews, 2 fixes.
- **(O) gates:** `P4-G1`, `P4-G2`, `P4-G3` were approved by the orchestrator's `--test-approve` (recorded as
  "Orchestrator (automated test approval)", not a human sign-off). `P4-G4` was not approved. The run ended with
  "WAITING for gates ['P4-G4']", exit code 2.
- **(O)** All model calls used `anthropic:claude-sonnet-5-5`. The summary reported 0 failed model calls.
- **(O)** The summary reports `diagnostics complete: yes` and per-call token sums matching each stage's `report.json`.

## 6. Problems, warnings, interruptions, workarounds

- **(O)** Docker Desktop was not running when I started; I started it and waited for the daemon.
- **(O)** `uv` unavailable (see section 3).
- **(O)** Python buffered the redirected console output, so the first console-log watcher saw nothing and expired;
  I replaced it with a watcher that reads the diagnostics event files (`tools/watch_events.py`).
- **(O)** One shell command using bare `python` with a heredoc hung and was stopped.
- **(O)** The first `orchestrate` run had no auto-approval and stopped at the infra failure. I offered options; the user chose
  to continue with auto-approval, and I ran the `-TestApprove` continuation.
- **(O)** The `--test-approve` run does not approve a stage that ended `partial`; that is why `P4-G4` stayed pending.
- **(O)** During development: a test failed on a missing span attribute (fixed); a test used `httpx` while the installed
  Anthropic SDK uses `httpx2` (hooks and test changed); one assertion expected 10 skipped checks but 12 were correct (test
  fixed); the on/off artifact-equivalence test was intermittent because the local allocation solver breaks ties differently
  between runs even with diagnostics off (the test now compares status, objective, assigned/unassigned sets, planned hours).
- **(O)** This packaging task: one tool call was interrupted by the user before it wrote anything; I re-ran it after
  checking the target folder was empty.
- **(U)** My live commentary during the run contained guesses (for example about what the last solver candidates were, and
  possible causes of the plugin failure); the guess about candidates was corrected live. In my end-of-run message I stated
  "66" solver candidates; I had not verified that total (the watcher output showed 64 infeasible then one feasible).

## 7. Changes I made in response to problems

None to application code during the run. Changes in response to development-time problems are listed in section 6.

## 8. Tests and checks actually run

- **(O)** Baseline before changes: 135 passed (about 23 s).
- **(O)** After adding instrumentation and the new tests, final full run: **173 passed** (about 46 s).
  `tests/test_perf_diagnostics.py` (17 tests) and `tests/test_outcome_integrity.py` (21 tests) are new.
  The new tests use fake models, mocked HTTP and temporary folders; no paid calls.
- **(O)** `scripts/perf_overhead.py` (9 runs each, medians, offline): deterministic Phase 4 flow 0.342 s off / 0.339 s on;
  one orchestrated stage of a fake-model graph 0.114 s / 0.120 s; standalone `run` 0.116 s / 0.444 s; 100,000 empty spans
  0.029 s / 2.10 s.
- **(O)** A secret scan of the collected copies (this task): 0 matches.
- **Terminal output of these test and overhead runs was not saved to files**, so it is not in the evidence folder;
  the numbers above are from my session. I did not rerun them for this packaging step.

## 9. Completion status and known limitations

- The pipeline reached `P4-G4` waiting (exit 2). It did **not** complete: infra ended `partial` and was never approved.
- Known limitations of this run (separately known): gates `P4-G1..G3` are test approvals; Timefold was not used; human
  approval waiting was not measured (no human decision occurred); the sandbox ran in Docker; `conftest` runs only the
  policy library's own unit tests.
- Remaining product limitation noted earlier: `checks_passed` still counts skipped checks as not failing.

## 10. Observations not preserved in the collected files

- Docker details I read at the time: Docker Desktop VM reported about 8.2 GB memory and 8 CPUs; **25 other containers were
  running**; the `phase4-tofu-plugin-cache` volume was created 2026-11-05; Docker server 29.8.2.
- My observation that the interval between work-allocation finishing and its approval record was about 57 s, versus 8-19 s
  for earlier stages (derived from the live watcher timestamps; the underlying events are in the files).
- The live commentary exchanged during the run (not saved).

## 11. Requested diagnostic output known not to have been produced

- Human approval waiting time (no human gate decision; the `P4-G4` wait has no end).
- Time to first token: the summary's slowest-call table showed no first-chunk values.
- Timefold queue/solve time (service not used and not reported by the service).
- Docker container CPU/memory and Docker child-process CPU on Windows.
- Test-suite and overhead-script terminal output as files.

## 12. Not recorded or cannot be established from my observations

- Why the AWS provider plugin failed to start (hypotheses such as memory pressure or a damaged cached binary were **not tested**).
- Why the validator's fourth call generated 64,000 tokens.
- The cause of the roughly 60 s process-exit gap after the last stage (hypotheses not tested or instrumented).
- The severities of the 21 `checkov` findings and the content of the raw outputs beyond the plugin error text above.
- Whether SDK-internal model retries were fully observable in this run (the summary reported 0 model HTTP retries seen;
  I did not verify that the transport hooks attached for every model instance).
- Whether the repository this PR targets is private; the evidence includes project documents and file/team names.
