# Work Allocation (PDLC Phase 4, step 4.3)

The Engineering Manager reviews one sprint's assignment plan at P4-G3. Approved upstream artifacts are read-only.

## Inputs

The approved sprint plan, backlog and project settings supply tasks, team skills, AI capabilities, calendar and PTO. Optional skill profiles add git ownership evidence; agent outcomes control shadow mode. AI requires approved, operational repository CI evidence less than 24 hours old.

## Execution

`work_allocation.py` drives preparation, checked structured judgement, the existing Timefold/CP-SAT solver and deterministic explanations. The default tier is fast, escalating to strong after failed checks. One structured call judges only AI candidates; no candidates means no call. Reviewer feedback uses one additional checked call for pins, vetoes and AI blocks. Answers are retried once on invalid IDs or generic reasons and retained by exact digest, including model and prompt identity.

Security/payment skills, DB/DevOps discipline, shared work, cross-story foundations, sensitive keywords and `human_only_components` route to humans. Missing files, open questions, missing/oversized estimates and unready CI remain hard blockers. Pins cannot bypass safety or skill rules.

The solver enforces skills, capacity, dependencies and review budget. Its displayed cost and skill scores explain evidence; cost is not a separate solver objective. Explanations state measured fit, ownership, load and a feasible alternative rather than inventing why another worker lost.

## Validation and output

`allocation.check` checks provenance, task coverage, pins/vetoes, schedules, skills, AI hard rules and outcomes. Worker kinds, capacities and actual loads are recomputed from authoritative inputs. Generic eligibility text receives a light flagged-only review. Unchanged repairs stop for the manager.

Outputs: `allocation/problem.json`, `allocation/assignments.json`, `allocation/assignments.md`; retained judgement lives in `.engine-work-allocation/`.

## Publication and Phase 5

`phase4 publish assignments` publishes human assignees and ownership explanation comments. AI owners are recorded explicitly in comments without dispatch or an invented bot account. Publication is idempotent. `phase4 dispatch` is a separate Phase 5 operation requiring all four current Phase 4 approvals, operational CI, dependency completion and worker concurrency. Existing dispatch adapters are retained.

## Verification limits

Unit and CLI tests use fake models, local trackers and blocked HTTP. No live Jira writes, provider dispatches or paid model calls were used for this alignment.

Publication also requires every Phase 4 checkpoint and final G4 approval; see [PHASE4.md](PHASE4.md). Phase 5 dispatch additionally requires current environment readiness.
