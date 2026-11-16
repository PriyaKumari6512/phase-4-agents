# Performance summary — session `clinic-fresh-run1`

How to read this: *elapsed* is wall-clock time. *Exclusive wall time* splits a stage's elapsed time so each second is counted once (model calls first, then service waits, commands, solvers, tools, agent build, file work). *Summed work* adds overlapping durations and can exceed elapsed time when work runs in parallel.

## Overview

- Evidence: 5754 events in 7 process files, 6 manifests, 0 unreadable lines
- First / last event: 2026-11-16T13:46:11+05:30 → 2026-11-16T14:40:32+05:30 (54 min 22 s)
- Active execution (3 top-level CLI processes, from process start to exit): 51 min 15 s, of which interpreter start and imports before diagnostics began: 36.9 s
- Human waiting measured: 0.00 s
- Not explained by either: 3 min 07 s (time between CLI invocations without evidence)
- Status: **waiting** · diagnostics complete: **yes**

- Source: `782bbdb4db4a` on `chore/pipeline-performance-instrumentation` · lockfile 87e5b9a6378e · mode generation_only

| Pipeline attempt | Started | Elapsed | Outcome | Test approval |
|---|---|---|---|---|
| `0b279729cff94289` | 2026-11-16T13:46:28+05:30 | 0.00 s | waiting | no |
| `935ac8d715e949cd` | 2026-11-16T13:46:49+05:30 | 43 min 08 s | failed | no |
| `0f7fba588127425c` | 2026-11-16T14:33:02+05:30 | 7 min 30 s | waiting | yes |

| Gate | Wait started | Decided | Wait | Basis |
|---|---|---|---|---|
| P4-G4 | 2026-11-16T14:40:32+05:30 | - | - | not measured: no decision evidence in this session |

## Stages

| Stage | Elapsed | Write / verify / fix (count, elapsed) | Model calls | Input / output / cache-read tokens | Tool calls (domain errors) | Helpers (max parallel) | Model HTTP retries seen | Outcome |
|---|---|---|---|---|---|---|---|---|
| task-breakdown | 16 min 38 s | 1× 16 min 02 s · 1× 35.4 s · 0× 0.00 s | 265 (0 err) | 19113588 / 714407 / 16732333 | 550 (6) | 18 (9) | 0 | success |
| infra-pipeline | 25 min 59 s | 1× 20 min 54 s · 1× 5 min 05 s · 0× 0.00 s | 21 (0 err) | 837313 / 76364 / 639096 | 51 (2) | 0 (0) | 0 | partial |
| sprint-planning | 2 min 48 s | 1× 2 min 05 s · 1× 42.4 s · 0× 0.00 s | 26 (0 err) | 1019031 / 16771 / 848352 | 48 (0) | 1 (1) | 0 | success |
| work-allocation | 3 min 20 s | 1× 22.7 s · 3× 1 min 15 s · 2× 1 min 21 s | 34 (0 err) | 369882 / 13365 / 286240 | 74 (0) | 0 (0) | 0 | success |

`*` = some calls did not report this token field; the sum covers only calls that did.

### task-breakdown: where the 16 min 38 s went (exclusive wall time)

- model_call: 16 min 31 s
- tool_exec: 5.02 s
- agent_build: 0.49 s
- fs: 0.36 s
- diagnostics: 0.01 s
- unattributed (framework, graph and other unmeasured work): 1.19 s
- summed work (overlaps counted repeatedly): model_call 1 h 21 min, tool_exec 1 min 15 s, fs 1.55 s, agent_build 0.97 s, diagnostics 0.01 s
- verdicts: attempt 1: success (0 gaps)
- token reconciliation with report.json totals: match

### infra-pipeline: where the 25 min 59 s went (exclusive wall time)

- model_call: 6 min 33 s
- service_wait: 0.38 s
- command: 19 min 22 s
- tool_exec: 1.69 s
- agent_build: 0.70 s
- fs: 0.28 s
- diagnostics: 0.08 s
- unattributed (framework, graph and other unmeasured work): 0.84 s
- summed work (overlaps counted repeatedly): tool_exec 38 min 51 s, command 19 min 23 s, model_call 6 min 33 s, agent_build 1.40 s, service_wait 1.37 s, fs 1.09 s, diagnostics 0.08 s
- verdicts: attempt 1: verifier failed (? gaps)
- token reconciliation with report.json totals: match

### sprint-planning: where the 2 min 48 s went (exclusive wall time)

- model_call: 2 min 19 s
- solver: 25.2 s
- tool_exec: 2.53 s
- agent_build: 0.31 s
- fs: 0.15 s
- diagnostics: 0.04 s
- unattributed (framework, graph and other unmeasured work): 0.46 s
- summed work (overlaps counted repeatedly): model_call 2 min 19 s, solver 1 min 12 s, tool_exec 53.8 s, agent_build 0.62 s, fs 0.15 s, diagnostics 0.04 s, service_wait 0.00 s
- verdicts: attempt 1: success (0 gaps)
- token reconciliation with report.json totals: match

### work-allocation: where the 3 min 20 s went (exclusive wall time)

- model_call: 2 min 27 s
- service_wait: 4.16 s
- solver: 0.01 s
- tool_exec: 18.1 s
- agent_build: 1.24 s
- fs: 18.5 s
- diagnostics: 0.02 s
- unattributed (framework, graph and other unmeasured work): 11.2 s
- summed work (overlaps counted repeatedly): model_call 2 min 27 s, tool_exec 35.5 s, fs 18.6 s, service_wait 4.16 s, agent_build 2.44 s, diagnostics 0.02 s, solver 0.01 s
- verdicts: attempt 1: partial (4 gaps); attempt 2: partial (2 gaps); attempt 3: success (0 gaps)
- token reconciliation with report.json totals: match

## Ten slowest model calls

| Elapsed | Model (tier) | Stage | Helper | Msgs | In / out / cache-read | First chunk | Finish | Status |
|---|---|---|---|---|---|---|---|---|
| 4 min 54 s | claude-sonnet-5-5 (strong) | infra-pipeline | - | 18 | 43255 / 64000 / 38535 | - | max_tokens | ok |
| 2 min 33 s | claude-sonnet-5-5 (strong) | task-breakdown | speckit-feature | 35 | 99248 / 21313 / 97634 | - | tool_use | ok |
| 2 min 30 s | claude-sonnet-5-5 (strong) | task-breakdown | speckit-feature | 38 | 118184 / 25233 / 113940 | - | tool_use | ok |
| 2 min 12 s | claude-sonnet-5-5 (strong) | task-breakdown | speckit-feature | 21 | 71580 / 19356 / 64361 | - | tool_use | ok |
| 2 min 07 s | claude-sonnet-5-5 (strong) | task-breakdown | speckit-feature | 23 | 95439 / 17687 / 88103 | - | tool_use | ok |
| 1 min 55 s | claude-sonnet-5-5 (strong) | task-breakdown | speckit-feature | 46 | 134677 / 19175 / 130431 | - | tool_use | ok |
| 1 min 50 s | claude-sonnet-5-5 (strong) | task-breakdown | speckit-feature | 21 | 78089 / 15610 / 70866 | - | tool_use | ok |
| 1 min 41 s | claude-sonnet-5-5 (strong) | task-breakdown | speckit-feature | 41 | 142678 / 16669 / 138426 | - | tool_use | ok |
| 1 min 38 s | claude-sonnet-5-5 (strong) | task-breakdown | speckit-feature | 32 | 105787 / 14009 / 104176 | - | tool_use | ok |
| 1 min 36 s | claude-sonnet-5-5 (strong) | task-breakdown | speckit-feature | 19 | 78141 / 14290 / 76752 | - | tool_use | ok |

## Largest input context (repeated context candidates)

| Input tokens | Cache-read | Model | Stage | Helper | Msgs |
|---|---|---|---|---|---|
| 170625 | 168913 | claude-sonnet-5-5 | task-breakdown | speckit-feature | 74 |
| 168915 | 164666 | claude-sonnet-5-5 | task-breakdown | speckit-feature | 72 |
| 166698 | 164027 | claude-sonnet-5-5 | task-breakdown | speckit-feature | 51 |
| 164668 | 162476 | claude-sonnet-5-5 | task-breakdown | speckit-feature | 59 |
| 164029 | 142676 | claude-sonnet-5-5 | task-breakdown | speckit-feature | 45 |
| 162478 | 158702 | claude-sonnet-5-5 | task-breakdown | speckit-feature | 54 |
| 158704 | 158449 | claude-sonnet-5-5 | task-breakdown | speckit-feature | 51 |
| 158616 | 154687 | claude-sonnet-5-5 | task-breakdown | speckit-feature | 59 |
| 158451 | 134675 | claude-sonnet-5-5 | task-breakdown | speckit-feature | 49 |
| 154689 | 154445 | claude-sonnet-5-5 | task-breakdown | speckit-feature | 51 |

## Ten slowest tool / command / service operations

| Elapsed | Kind | Name | Details | Status |
|---|---|---|---|---|
| 9 min 33 s | tool_exec | infra_validate | tool=infra_validate | ok |
| 5 min 03 s | tool_exec | infra_validate | tool=infra_validate | ok |
| 4 min 47 s | tool_exec | infra_validate | tool=infra_validate | ok |
| 3 min 34 s | command | sandbox.tofu_validate | tool=tofu_validate, category=init_validate, env=prod, attempt=2, exit_code=1, timed_out=False, raw_output=raw/c077f23b220546de-tofu_validate-prod-a2.txt, valida | ok |
| 2 min 30 s | command | sandbox.tofu_validate | tool=tofu_validate, category=init_validate, env=prod, attempt=1, exit_code=1, timed_out=False, raw_output=raw/20804fb3d57a4ebd-tofu_validate-prod-a1.txt, valida | ok |
| 1 min 31 s | command | sandbox.tofu_validate | tool=tofu_validate, category=init_validate, env=dev, attempt=1, exit_code=1, timed_out=False, raw_output=raw/fa7f32dd119d40a4-tofu_validate-dev-a1.txt, validati | ok |
| 1 min 22 s | command | sandbox.tofu_validate | tool=tofu_validate, category=init_validate, env=dev, attempt=1, exit_code=1, timed_out=False, raw_output=raw/fd564ad359834d2e-tofu_validate-dev-a1.txt, validati | ok |
| 1 min 22 s | command | sandbox.tofu_validate | tool=tofu_validate, category=init_validate, env=stg, attempt=1, exit_code=1, timed_out=False, raw_output=raw/4081888c6c6f45cc-tofu_validate-stg-a1.txt, validati | ok |
| 1 min 22 s | command | sandbox.tofu_validate | tool=tofu_validate, category=init_validate, env=prod, attempt=1, exit_code=1, timed_out=False, raw_output=raw/3d7261099d1b4717-tofu_validate-prod-a1.txt, valida | ok |
| 1 min 18 s | command | sandbox.tofu_validate | tool=tofu_validate, category=init_validate, env=stg, attempt=1, exit_code=1, timed_out=False, raw_output=raw/877b358aae4e4a56-tofu_validate-stg-a1.txt, validati | ok |

## Helpers

19 helper invocations; max running at once: **9**; elapsed while any helper ran: 13 min 42 s; summed helper time: 1 h 19 min.

| Start (+s) | Elapsed | Type | Status |
|---|---|---|---|
| +0.0 | 5 min 58 s | speckit-feature | ok |
| +0.0 | 4 min 31 s | speckit-feature | ok |
| +0.001 | 6 min 07 s | speckit-feature | ok |
| +0.002 | 4 min 33 s | speckit-feature | ok |
| +0.002 | 5 min 49 s | speckit-feature | ok |
| +0.002 | 4 min 56 s | speckit-feature | ok |
| +0.002 | 6 min 09 s | speckit-feature | ok |
| +0.004 | 8 min 55 s | speckit-feature | ok |
| +0.004 | 3 min 55 s | speckit-feature | ok |
| +561.261 | 3 min 03 s | backlog-enricher | ok |
| +561.261 | 4 min 15 s | backlog-enricher | ok |
| +561.261 | 4 min 08 s | backlog-enricher | ok |
| +561.262 | 2 min 24 s | backlog-enricher | ok |
| +561.286 | 2 min 39 s | backlog-enricher | ok |
| +561.288 | 2 min 35 s | backlog-enricher | ok |
| +561.288 | 2 min 26 s | backlog-enricher | ok |
| +561.289 | 3 min 27 s | backlog-enricher | ok |
| +561.296 | 3 min 28 s | backlog-enricher | ok |
| +2715.527 | 31.9 s | general-purpose | ok |

## Solvers

Main solve, core extraction and each option candidate have separate time limits, so a sprint_solve call can take longer than the main limit.

| Name | Elapsed | Status | Details |
|---|---|---|---|
| sprint.cpsat | 0.27 s | INFEASIBLE | purpose=main, time_limit_s=10.0, workers=8, variables=914, constraints=773, objective=None, best_bound=None, solver_wall_s=0.2588, result_status=INFEASIBLE |
| sprint.core_extraction | 0.26 s | INFEASIBLE | time_limit_s=10.0, workers=1, core_size=61, solver_wall_s=0.2592, result_status=INFEASIBLE |
| sprint.verified_options | 24.7 s | ok | attempts=65 |
| sprint.candidate | 0.36 s | INFEASIBLE | candidate=1, transformation=relax:deadline:DL-1:+1, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.34 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=914, constraints=773, objective=None, best_bound=None, solver_wall_s=0.3356, result_status=INFEASIBLE |
| sprint.candidate | 0.31 s | INFEASIBLE | candidate=2, transformation=relax:deadline:DL-1:+2, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.29 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=914, constraints=773, objective=None, best_bound=None, solver_wall_s=0.2881, result_status=INFEASIBLE |
| sprint.candidate | 0.36 s | INFEASIBLE | candidate=3, transformation=soften:deadline:DL-1, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.34 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=663, objective=None, best_bound=None, solver_wall_s=0.3397, result_status=INFEASIBLE |
| sprint.candidate | 0.57 s | INFEASIBLE | candidate=4, transformation=downgrade:must:S-001-US1, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.51 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.5102, result_status=INFEASIBLE |
| sprint.candidate | 0.30 s | INFEASIBLE | candidate=5, transformation=downgrade:must:S-001-US10, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.27 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2646, result_status=INFEASIBLE |
| sprint.candidate | 0.28 s | INFEASIBLE | candidate=6, transformation=downgrade:must:S-001-US2, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.21 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2074, result_status=INFEASIBLE |
| sprint.candidate | 0.27 s | INFEASIBLE | candidate=7, transformation=downgrade:must:S-001-US3, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.23 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2343, result_status=INFEASIBLE |
| sprint.candidate | 0.35 s | INFEASIBLE | candidate=8, transformation=downgrade:must:S-001-US4, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.31 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.3107, result_status=INFEASIBLE |
| sprint.candidate | 0.26 s | INFEASIBLE | candidate=9, transformation=downgrade:must:S-001-US5, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.24 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2365, result_status=INFEASIBLE |
| sprint.candidate | 0.23 s | INFEASIBLE | candidate=10, transformation=downgrade:must:S-001-US6, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.21 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2107, result_status=INFEASIBLE |
| sprint.candidate | 0.43 s | INFEASIBLE | candidate=11, transformation=downgrade:must:S-001-US7, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.35 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.3497, result_status=INFEASIBLE |
| sprint.candidate | 0.34 s | INFEASIBLE | candidate=12, transformation=downgrade:must:S-001-US8, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.31 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.3087, result_status=INFEASIBLE |
| sprint.candidate | 0.33 s | INFEASIBLE | candidate=13, transformation=downgrade:must:S-002-US1, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.30 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2996, result_status=INFEASIBLE |
| sprint.candidate | 0.32 s | INFEASIBLE | candidate=14, transformation=downgrade:must:S-002-US2, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.28 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2817, result_status=INFEASIBLE |
| sprint.candidate | 0.35 s | INFEASIBLE | candidate=15, transformation=downgrade:must:S-002-US3, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.32 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.3161, result_status=INFEASIBLE |
| sprint.candidate | 0.23 s | INFEASIBLE | candidate=16, transformation=downgrade:must:S-002-US4, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.20 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2044, result_status=INFEASIBLE |
| sprint.candidate | 0.29 s | INFEASIBLE | candidate=17, transformation=downgrade:must:S-002-US5, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.26 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2574, result_status=INFEASIBLE |
| sprint.candidate | 0.28 s | INFEASIBLE | candidate=18, transformation=downgrade:must:S-002-US6, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.25 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2463, result_status=INFEASIBLE |
| sprint.candidate | 0.27 s | INFEASIBLE | candidate=19, transformation=downgrade:must:S-003-US1, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.22 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2217, result_status=INFEASIBLE |
| sprint.candidate | 0.22 s | INFEASIBLE | candidate=20, transformation=downgrade:must:S-003-US2, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.20 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.1969, result_status=INFEASIBLE |
| sprint.candidate | 0.30 s | INFEASIBLE | candidate=21, transformation=downgrade:must:S-003-US3, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.27 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2648, result_status=INFEASIBLE |
| sprint.candidate | 0.33 s | INFEASIBLE | candidate=22, transformation=downgrade:must:S-003-US4, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.28 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2807, result_status=INFEASIBLE |
| sprint.candidate | 0.28 s | INFEASIBLE | candidate=23, transformation=downgrade:must:S-003-US5, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.25 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2489, result_status=INFEASIBLE |
| sprint.candidate | 0.21 s | INFEASIBLE | candidate=24, transformation=downgrade:must:S-003-US6, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.19 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.1856, result_status=INFEASIBLE |
| sprint.candidate | 0.24 s | INFEASIBLE | candidate=25, transformation=downgrade:must:S-004-US1, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.22 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2195, result_status=INFEASIBLE |
| sprint.candidate | 0.25 s | INFEASIBLE | candidate=26, transformation=downgrade:must:S-004-US2, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.23 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2286, result_status=INFEASIBLE |
| sprint.candidate | 0.24 s | INFEASIBLE | candidate=27, transformation=downgrade:must:S-004-US3, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.21 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2118, result_status=INFEASIBLE |
| sprint.candidate | 0.31 s | INFEASIBLE | candidate=28, transformation=downgrade:must:S-004-US4, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.23 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.235, result_status=INFEASIBLE |
| sprint.candidate | 0.27 s | INFEASIBLE | candidate=29, transformation=downgrade:must:S-005-US1, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.24 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.238, result_status=INFEASIBLE |
| sprint.candidate | 0.25 s | INFEASIBLE | candidate=30, transformation=downgrade:must:S-005-US2, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.22 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2172, result_status=INFEASIBLE |
| sprint.candidate | 0.29 s | INFEASIBLE | candidate=31, transformation=downgrade:must:S-005-US3, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.27 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2645, result_status=INFEASIBLE |
| sprint.candidate | 0.35 s | INFEASIBLE | candidate=32, transformation=downgrade:must:S-005-US4, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.30 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.3034, result_status=INFEASIBLE |
| sprint.candidate | 0.33 s | INFEASIBLE | candidate=33, transformation=downgrade:must:S-006-US1, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.30 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2994, result_status=INFEASIBLE |
| sprint.candidate | 0.29 s | INFEASIBLE | candidate=34, transformation=downgrade:must:S-006-US2, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.26 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2603, result_status=INFEASIBLE |
| sprint.candidate | 0.27 s | INFEASIBLE | candidate=35, transformation=downgrade:must:S-006-US3, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.24 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2379, result_status=INFEASIBLE |
| sprint.candidate | 0.23 s | INFEASIBLE | candidate=36, transformation=downgrade:must:S-006-US4, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.21 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2088, result_status=INFEASIBLE |
| sprint.candidate | 0.28 s | INFEASIBLE | candidate=37, transformation=downgrade:must:S-006-US5, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.26 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2545, result_status=INFEASIBLE |
| sprint.candidate | 0.42 s | INFEASIBLE | candidate=38, transformation=downgrade:must:S-006-US6, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.36 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.3549, result_status=INFEASIBLE |
| sprint.candidate | 0.31 s | INFEASIBLE | candidate=39, transformation=downgrade:must:S-006-US7, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.28 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2791, result_status=INFEASIBLE |
| sprint.candidate | 0.31 s | INFEASIBLE | candidate=40, transformation=downgrade:must:S-007-US1, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.27 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2717, result_status=INFEASIBLE |
| sprint.candidate | 0.49 s | INFEASIBLE | candidate=41, transformation=downgrade:must:S-007-US2, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.47 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.4663, result_status=INFEASIBLE |
| sprint.candidate | 0.39 s | INFEASIBLE | candidate=42, transformation=downgrade:must:S-007-US3, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.35 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.3533, result_status=INFEASIBLE |
| sprint.candidate | 0.35 s | INFEASIBLE | candidate=43, transformation=downgrade:must:S-007-US4, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.30 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.3036, result_status=INFEASIBLE |
| sprint.candidate | 0.32 s | INFEASIBLE | candidate=44, transformation=downgrade:must:S-007-US5, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.28 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2774, result_status=INFEASIBLE |
| sprint.candidate | 0.30 s | INFEASIBLE | candidate=45, transformation=downgrade:must:S-007-US6, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.27 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2698, result_status=INFEASIBLE |
| sprint.candidate | 0.36 s | INFEASIBLE | candidate=46, transformation=downgrade:must:S-007-US7, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.32 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.3231, result_status=INFEASIBLE |
| sprint.candidate | 0.40 s | INFEASIBLE | candidate=47, transformation=downgrade:must:S-FOUND-001, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.36 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.3628, result_status=INFEASIBLE |
| sprint.candidate | 0.29 s | INFEASIBLE | candidate=48, transformation=downgrade:must:S-FOUND-002, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.27 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2677, result_status=INFEASIBLE |
| sprint.candidate | 0.31 s | INFEASIBLE | candidate=49, transformation=downgrade:must:S-FOUND-003, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.27 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.274, result_status=INFEASIBLE |
| sprint.candidate | 0.36 s | INFEASIBLE | candidate=50, transformation=downgrade:must:S-FOUND-004, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.34 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.338, result_status=INFEASIBLE |
| sprint.candidate | 0.24 s | INFEASIBLE | candidate=51, transformation=downgrade:must:S-FOUND-005, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.22 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2161, result_status=INFEASIBLE |
| sprint.candidate | 0.22 s | INFEASIBLE | candidate=52, transformation=downgrade:must:S-FOUND-006, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.20 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.1948, result_status=INFEASIBLE |
| sprint.candidate | 0.39 s | INFEASIBLE | candidate=53, transformation=downgrade:must:S-FOUND-007, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.36 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.3595, result_status=INFEASIBLE |
| sprint.candidate | 0.33 s | INFEASIBLE | candidate=54, transformation=downgrade:must:S-POLISH-002, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.29 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2863, result_status=INFEASIBLE |
| sprint.candidate | 0.25 s | INFEASIBLE | candidate=55, transformation=downgrade:must:S-POLISH-006, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.22 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2192, result_status=INFEASIBLE |
| sprint.candidate | 0.22 s | INFEASIBLE | candidate=56, transformation=downgrade:must:S-POLISH-007, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.19 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.1932, result_status=INFEASIBLE |
| sprint.candidate | 0.22 s | INFEASIBLE | candidate=57, transformation=downgrade:must:S-SETUP-001, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.20 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.1978, result_status=INFEASIBLE |
| sprint.candidate | 0.23 s | INFEASIBLE | candidate=58, transformation=downgrade:must:S-SETUP-002, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.20 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.1984, result_status=INFEASIBLE |
| sprint.candidate | 0.25 s | INFEASIBLE | candidate=59, transformation=downgrade:must:S-SETUP-003, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.22 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2215, result_status=INFEASIBLE |
| sprint.candidate | 0.23 s | INFEASIBLE | candidate=60, transformation=downgrade:must:S-SETUP-004, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.20 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.1976, result_status=INFEASIBLE |
| sprint.candidate | 0.24 s | INFEASIBLE | candidate=61, transformation=downgrade:must:S-SETUP-005, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.22 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.2196, result_status=INFEASIBLE |
| sprint.candidate | 0.34 s | INFEASIBLE | candidate=62, transformation=downgrade:must:S-SETUP-006, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.31 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.3087, result_status=INFEASIBLE |
| sprint.candidate | 0.44 s | INFEASIBLE | candidate=63, transformation=downgrade:must:S-SETUP-007, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.32 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=913, constraints=772, objective=None, best_bound=None, solver_wall_s=0.3232, result_status=INFEASIBLE |
| sprint.candidate | 0.31 s | INFEASIBLE | candidate=64, transformation=capacity:x1.15, feasible=False, result_status=INFEASIBLE |
| sprint.cpsat | 0.26 s | INFEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=914, constraints=773, objective=None, best_bound=None, solver_wall_s=0.2564, result_status=INFEASIBLE |
| sprint.candidate | 5.04 s | FEASIBLE | candidate=65, transformation=capacity:x1.3, feasible=True, result_status=FEASIBLE |
| sprint.cpsat | 5.01 s | FEASIBLE | purpose=candidate, time_limit_s=5.0, workers=8, variables=914, constraints=773, objective=51842.0, best_bound=54024.0, solver_wall_s=5.01, result_status=FEASIBLE |
| allocation | 4.18 s | SOLVING_COMPLETED | selected=local_cpsat, reason=auto: service unreachable, requested_mode=auto, result_status=SOLVING_COMPLETED |
| allocation.cpsat | 0.01 s | OPTIMAL | time_limit_s=20.0, variables=2, constraints=20, solver_wall_s=0.0134, result_status=OPTIMAL |

## Infrastructure checks

Static checks of generated files only; nothing here plans, applies or verifies a deployment.

| Tool | Category | Env | Attempt | Runs | Elapsed | Exit codes | Timeouts | Executor |
|---|---|---|---|---|---|---|---|---|
| tofu_validate | init_validate | prod | 1 | 3 | 5 min 06 s | [1, 1, 1] | 0 | docker |
| tofu_validate | init_validate | dev | 1 | 3 | 4 min 09 s | [1, 1, 1] | 0 | docker |
| tofu_validate | init_validate | stg | 1 | 3 | 3 min 54 s | [1, 1, 1] | 0 | docker |
| tofu_validate | init_validate | prod | 2 | 1 | 3 min 34 s | [1] | 0 | docker |
| trivy | scan | - | 1 | 3 | 1 min 24 s | [0, 0, 0] | 0 | docker |
| checkov | scan | - | 1 | 3 | 38.6 s | [0, 0, 0] | 0 | docker |
| helm_lint | scan | - | 1 | 3 | 6.66 s | [0, 0, 0] | 0 | docker |
| tflint | scan | - | 1 | 3 | 4.73 s | [0, 0, 0] | 0 | docker |
| gitleaks | scan | - | 1 | 3 | 4.72 s | [0, 0, 0] | 0 | docker |
| kubeconform | scan | - | 1 | 3 | 4.61 s | [0, 0, 0] | 0 | docker |
| actionlint | scan | - | 1 | 6 | 4.11 s | [0, 0, 0, 0, 0, 0] | 0 | docker |
| tofu_fmt | fmt | - | 1 | 3 | 3.70 s | [0, 0, 0] | 0 | docker |
| conftest | scan | - | 1 | 3 | 3.36 s | [0, 0, 0] | 0 | docker |
| tofu_validate | registry_probe | - | 1 | 3 | 3.14 s | [0, 0, 0] | 0 | docker |
| docker.image_inspect | docker_image_inspect | - | None | 6 | 1.38 s | [0, 0, 0, 0, 0, 0] | 0 | None |
| sandbox.cache_volume_setup | cache_setup | - | None | 1 | 0.92 s | [0] | 0 | None |

| Check | Outcome | Passed | Skipped | Findings | Scope |
|---|---|---|---|---|---|
| tofu_fmt | passed | True | False | 0 | formatting |
| tofu_validate | findings | False | False | 2 | static: tofu init + validate per environment (no plan, no credentials) |
| tflint | passed | True | False | 0 | static lint |
| trivy | passed | True | False | 0 | static misconfiguration scan |
| checkov | findings | True | False | 21 | static misconfiguration scan |
| actionlint | passed | True | False | 0 | workflow lint |
| helm_lint | passed | True | False | 0 | chart lint + rendered manifest schema |
| kubeconform | passed | True | False | 0 | manifest schema |
| gitleaks | passed | True | False | 0 | secret scan of generated files |
| conftest | passed | True | False | 0 | policy library unit tests only (no evaluation of a generated plan) |
| actionlint | passed | True | False | 0 | workflow lint |
| tofu_fmt | passed | True | False | 0 | formatting |
| tofu_validate | findings | False | False | 3 | static: tofu init + validate per environment (no plan, no credentials) |
| tflint | passed | True | False | 0 | static lint |
| trivy | passed | True | False | 0 | static misconfiguration scan |
| checkov | findings | True | False | 21 | static misconfiguration scan |
| actionlint | passed | True | False | 0 | workflow lint |
| helm_lint | passed | True | False | 0 | chart lint + rendered manifest schema |
| kubeconform | passed | True | False | 0 | manifest schema |
| gitleaks | passed | True | False | 0 | secret scan of generated files |
| conftest | passed | True | False | 0 | policy library unit tests only (no evaluation of a generated plan) |
| actionlint | passed | True | False | 0 | workflow lint |
| tofu_fmt | passed | True | False | 0 | formatting |
| tofu_validate | findings | False | False | 3 | static: tofu init + validate per environment (no plan, no credentials) |
| tflint | passed | True | False | 0 | static lint |
| trivy | passed | True | False | 0 | static misconfiguration scan |
| checkov | findings | True | False | 21 | static misconfiguration scan |
| actionlint | passed | True | False | 0 | workflow lint |
| helm_lint | passed | True | False | 0 | chart lint + rendered manifest schema |
| kubeconform | passed | True | False | 0 | manifest schema |
| gitleaks | passed | True | False | 0 | secret scan of generated files |
| conftest | passed | True | False | 0 | policy library unit tests only (no evaluation of a generated plan) |
| actionlint | passed | True | False | 0 | workflow lint |

## HTTP, polling and retries

| Request | Count | Elapsed | Statuses | Attempts | Throttle wait | Backoff | Failed |
|---|---|---|---|---|---|---|---|
| timefold.availability_probe | 1 | 4.16 s | {'None': 1} | 1 | 0.00 s | 0.00 s | 0 |
| terraform_registry.module_versions | 4 | 1.37 s | {'200': 4} | 4 | 0.00 s | 0.00 s | 0 |

Model HTTP attempts seen by transport hooks: 346 (statuses {'200': 346}); logical calls with more than one attempt: 0; attempts marked as SDK retries: 0.

## File system, locks and diagnostics overhead

| Operation | Count | Elapsed | Files | Bytes |
|---|---|---|---|---|
| copy_run_history | 4 | 10.2 s | 130 | 3737052 |
| fingerprint | 8 | 6.74 s | 850 | 26398880 |
| input_digests | 23 | 6.48 s | - | - |
| write_report | 4 | 2.39 s | - | - |
| backlog.save | 32 | 0.83 s | - | 65215712 |
| infra.refresh_manifest_hashes | 3 | 0.59 s | 81 | - |
| read_child_report | 4 | 0.57 s | - | - |
| save_orchestrator_state | 12 | 0.56 s | - | - |
| backlog.write_validated | 9 | 0.35 s | - | - |
| infra.write_rendered_files | 2 | 0.20 s | 54 | 66466 |
| infra.write_reports | 3 | 0.01 s | - | - |
| sandbox.cleanup | 10 | 0.01 s | - | - |
| record_request | 4 | 0.01 s | - | - |
| sprint.write_plan | 1 | 0.01 s | - | - |
| allocation.write_assignments | 1 | 0.00 s | - | - |

Global write lock: 186 acquisitions, waited 6.12 s in total (max 0.25 s), held 3.05 s, 0 timeouts.
- diagnostics manifest: 6× 1.08 s
- diagnostics langfuse_flush: 4× 0.00 s

## Resources

Each row is one Python process of this run. Docker containers and other child processes are not included (on Windows no child CPU is reported at all); host-wide load is not measured.

| Process | Elapsed | CPU user / system | Peak memory | Import time |
|---|---|---|---|---|
| phase4 orchestrate | 0.01 s | 5.453 / 4.766 s | 211 MiB | 17.6 s |
| phase4 orchestrate | 43 min 08 s | 4.734 / 3.109 s | 213 MiB | 11.3 s |
| run | 16 min 38 s | 47.719 / 22.875 s | 357 MiB | 9.16 s |
| run | 25 min 59 s | 12.156 / 7.047 s | 232 MiB | 17.8 s |
| phase4 orchestrate | 7 min 30 s | 3.406 / 2.078 s | 216 MiB | 8.08 s |
| run | 2 min 48 s | 27.641 / 3.172 s | 256 MiB | 7.19 s |
| run | 3 min 27 s | 10.391 / 3.969 s | 247 MiB | 5.69 s |

## Failures and incomplete work

| Kind | Name | Status | Category | Error | Raw output |
|---|---|---|---|---|---|
| pipeline | clinic-test-2 | failed | pipeline_outcome |  | - |
| tool | backlog_build | domain_error | tool_error_text | ERROR: specs/001-platform-foundation: line 382: task line does not match the spec-kit format: '- [P] tasks = different f | - |
| tool_exec | backlog_build | domain_error | project_error | ERROR: specs/001-platform-foundation: line 382: task line does not match the spec-kit format: '- [P] tasks = different f | - |
| compute | backlog.parse_feature | error | project_error | ProjectError: specs/001-platform-foundation: line 382: task line does not match the spec-kit format: '- [P] tasks = diff | - |
| tool | backlog_build | domain_error | tool_error_text | ERROR: specs/001-platform-foundation: line 382: task line does not match the spec-kit format: '- [P] tasks = different f | - |
| tool_exec | backlog_build | domain_error | project_error | ERROR: specs/001-platform-foundation: line 382: task line does not match the spec-kit format: '- [P] tasks = different f | - |
| compute | backlog.parse_feature | error | project_error | ProjectError: specs/001-platform-foundation: line 382: task line does not match the spec-kit format: '- [P] tasks = diff | - |
| tool | backlog_build | domain_error | tool_error_text | ERROR: specs/002-identity-access: line 274: task line does not match the spec-kit format: '- [P] tasks touch different f | - |
| tool_exec | backlog_build | domain_error | project_error | ERROR: specs/002-identity-access: line 274: task line does not match the spec-kit format: '- [P] tasks touch different f | - |
| compute | backlog.parse_feature | error | project_error | ProjectError: specs/002-identity-access: line 274: task line does not match the spec-kit format: '- [P] tasks touch diff | - |
| child | infra-pipeline | failed | stage_outcome | stage ended partial | - |
| stage | infra-pipeline | failed | exit_code |  | - |
| tool | infra_set_intent | domain_error | tool_error_text | ERROR: intent does not match the schema: 1 validation error for InfraIntent notes Input should be a valid list [type=lis | - |
| tool_exec | infra_set_intent | domain_error | project_error | ERROR: intent does not match the schema: 1 validation error for InfraIntent notes Input should be a valid list [type=lis | - |
| pass | infra-pipeline/validator:verify | error | other | StructuredOutputValidationError: Failed to parse structured output for tool 'Verdict': Native structured output expected | - |
| graph | infra-pipeline/validator-verify | error | other | StructuredOutputValidationError: Failed to parse structured output for tool 'Verdict': Native structured output expected | - |

## What is not measured

- Time to first token: observed for 0 of 346 model calls; the rest were not streamed, so the interface exposes no first-token time for them.
- SDK-internal retry visibility per agent build: installed: 12. Where hooks are not installed, retries inside one model call are invisible (unknown, not zero).
- Docker container CPU/memory and Docker image pulls are not measured; command spans include them.
- 1 approval waits have no decision evidence in this session (not measured).
