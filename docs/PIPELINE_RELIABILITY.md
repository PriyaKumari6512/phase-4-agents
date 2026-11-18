# Pipeline reliability: what stops the pipeline and what is only reported

Phase 4 should finish with its issues reported instead of stopping on them. These rules decide which is which.

| Situation | Behaviour | Where |
|---|---|---|
| A new run | Starts fresh and depends only on its inputs. A stage is skipped only when its last run succeeded and every input it read is byte-for-byte unchanged (a pure cache). Outputs without a recorded run are regenerated, not adopted. | `phase4/orchestrator.py` `assess` |
| Saved recovery state (interrupted repairs, reviews, parallel merges) | Used only with `--resume` (`phase4 orchestrate`) or `PHASE4_RESUME=true` (`pipeline`). Without it an unfinished parallel session is not replayed; its evidence stays under `logs/parallel`. | `orchestrator.py`, `parallel_stages.py` |
| Deterministic checks fail (backlog, sprint, allocation, infra checks) | Block: a fix pass runs, then the stage stops with the open gaps. | `cli._deterministic_gaps` |
| A model reviewer finds problems | Never blocks. The findings become warnings in `<stage folder>/review-notes.json` and are shown to the gate approver. No fix loop is spent on opinions. | `cli._record_review_notes` |
| A story conflicts with the PRD, or a product decision is missing | The criterion is deferred with a reason starting `DECISION NEEDED:` and becomes an open question for the Tech Lead. Silent deferral is still rejected. | `task_breakdown.check_breakdown`, Task Breakdown prompt |
| One story still fails its checks after its retry | That story is marked `needs_attention` (no tasks, an open question); the other stories finish. Sprint Planning leaves it out with the reason. The next run retries only that story. | `task_breakdown._results`, `backlog._validate`, `sprint._prechecks` |
| Checkov findings | Only `fail_on` severities (default high/critical) block. Unscored checks take `unreported_severity` (default medium, a warning). Findings in downloaded modules (`.external_modules/`) are reported, never blocking. Policy: `agents/infra-pipeline/knowledge/catalog/checkov-policy.json` (initial list; the DevOps Lead reviews and extends it). | `sandbox._checkov_result` |
| Infra repair | Small targeted edits only: each edit replaces exact text that occurs once, at most 12 edits of at most 40 lines; no Terraform block may disappear. Whole-file rewrites are refused. | `infra_pipeline.repair`, `apply_edits` |
| Hosting target or cloud not in the catalog (e.g. serverless) | A gap report: the intent is kept, everything the catalog covers is generated, the uncovered workloads are listed in `infra/manifest.json` gaps. | `infra.set_intent`, `infra.render` |
| Input problems (missing PRD/architecture, unapproved G3A/G3B, invalid project.json or stories, members without skills, roadmap releases without a date, no code repos) | Checked before any model call; the run stops once with the complete list. Stories without acceptance criteria are warnings. | `phase4/preflight.py` |
| Rate limit or transient provider error | The stage is run again, fresh, after the reset time or a doubling backoff, up to `AGENT_ENGINE_PROVIDER_RETRIES` (3). A reset beyond `AGENT_ENGINE_RATE_LIMIT_MAX_WAIT_SECONDS` (1800) stops with the reason; nothing from the failed attempt is merged. | `orchestrator._provider_retry` |
| Parallel merge refused or rolled back | All or nothing: nothing was merged, and Task Breakdown and Infrastructure run again one after the other. | `orchestrator._orchestrate_once` |

Gate approvers see, for each pending gate, the reviewer notes and the open items (`phase4/attention.py`): stories that
need attention, open questions and decisions needed, stories left out of the plan, unassigned tasks, infrastructure
gaps and scanner warnings.

`tests/test_phase4_e2e.py` runs all four agents through the orchestrator with a fake model and injected failures
(one bad story, scanner findings, a rate limit, a "blocking" reviewer opinion) and proves the pipeline finishes with
the issues reported. It runs in CI on every pull request and push (`.github/workflows/tests.yml`).
