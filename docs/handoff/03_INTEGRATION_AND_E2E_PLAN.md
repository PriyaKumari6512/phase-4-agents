# Phase 4 integration, end-to-end run and tuning — plan

Self-contained plan for the last part of aligning PDLC Phase 4 in `https://github.com/PriyaKumari6512/phase-4-agents`
(branch `feat/task-breakdown-from-approved-stories`). Do this **after** all four agents match the spec
(`01_WORK_ALLOCATION_PLAN.md`, `02_INFRA_PIPELINE_PLAN.md`). Background and the spec summary are in
`docs/handoff/00_START_HERE.md`.

## 1. Gate and flow alignment (decide, then implement)

The spec has **one** human gate at the end of Phase 4:

> G4 — Plan & environment approval. Approvers: Tech Lead (task breakdown); Engineering Manager / Scrum Master (sprint
> plan & work allocation); DevOps Lead + Solution Architect (environments & pipelines). Inputs: tasks, sprint plan,
> assignments, environments. Changes requested → back to 4.1 / 4.4. Rejected → back to 3A / 3B.
> Workflow order 4.1 → 4.2 → 4.3 → 4.4 → G4 → 5.1.

The code has **four** gates (`gates.toml`): P4-G1 backlog (Tech Lead), P4-G2 sprint plan (Scrum Master / Engineering
Manager), P4-G3 assignments (Engineering Manager), P4-G4 infra (currently "platform engineer"). Each later agent waits
for the previous gate, and Infra runs in parallel with Task Breakdown. The product owner chose to keep P4-G1 while the
other agents were reviewed; the decision now is:

- **Option A (spec-literal):** one G4 gate covering all four outputs with the four named approvers (each approves
  their part; maker-checker preserved). Agents run 4.1 → 4.4 without intermediate human stops; publishing happens only
  after G4. Changes requested route back to 4.1 (task/sprint/allocation issues) or 4.4 (environment issues).
- **Option B (current, documented deviation):** keep per-agent gates as checkpoints, and add a final G4 that requires
  all four approvals before anything is published or dispatched.

*(Recommended: Option B for safety during adoption, renaming the gates to "G4 part 1–4" in the docs, with publishing
and Phase 5 dispatch refusing until every part is approved.)* Also make sure a **rejected** gate routes back to design
(3A/3B) — already done for the Task Breakdown gate.

Order note: the spec runs Infra (4.4) after Work Allocation (4.3); the code runs Infra early because Work Allocation
needs CI readiness for AI agents. Keep the early start, but document why.

## 2. Deferred items carried from the finished components

| Item | Component | What to do |
|---|---|---|
| UI designs and API spec not given to the model | Task Breakdown | Add `designs/designs.md` and any `api/openapi.*` to the cached prompt prefix in `task_breakdown.prompt_prefix` and to `source_manifest` |
| Budgets are loose defaults | Task Breakdown | `AGENT_ENGINE_BREAKDOWN_MAX_CALLS` (1000), `..._MAX_INPUT_TOKENS` (30M), `..._MAX_OUTPUT_TOKENS` (2M): set from measured usage after the end-to-end run (expected scale: about 2–3 calls per story) |
| Capacity by discipline | Sprint Planning | Optional: FE/BE/DB/DevOps/QA hours per sprint from team roles (the solver's removed per-skill cap could come back keyed by discipline) |
| Live checks not yet run | Task Breakdown | Cross-story pass, light review, `frontier` escalation and Jira sub-task creation have only been tested with fakes |
| Live checks not yet run | Sprint Planning | A full run on real stories; sprint publishing (with sprint reuse) to Jira |
| Work Allocation prompt says "delivery manager" | Work Allocation | Covered by `01_WORK_ALLOCATION_PLAN.md` step 2 |

## 3. End-to-end run on dummy data (local tracker first)

Goal: see all four agents and the gates work together, with no Jira writes.

1. **Prepare a dummy project** under `outputs/<name>/` (git-ignored):
   - `phase4/project.json` from `examples/phase4/taskflow/phase4/project.json` (team, calendar, code repos, AI agents);
     add `release_deadlines` for the dummy releases.
   - `prd.md`, `architecture.md` (with components, data, APIs, deployment, NFRs), `designs/designs.md`.
   - `phase4/stories.json` hand-written in the `StorySnapshot` format (`agent-engine phase4 schemas --out schemas`
     writes the JSON Schema): 8–15 stories across 2 epics and 2–3 releases, with acceptance criteria ids, MoSCoW,
     ranks, a few "blocks" links. Use `source: "file"`.
2. Approve the design gates (human step, maker-checker):
   ```bash
   uv run agent-engine gate G3A --project-name <name> --decision approved --approver "Design Lead" --submitted-by "UX agent"
   uv run agent-engine gate G3B --project-name <name> --decision approved --approver "Architect" --submitted-by "Architecture agent"
   ```
3. Run with the local tracker (`PHASE4_TRACKER=local` in the shell, or unset Jira settings):
   ```bash
   uv run agent-engine phase4 orchestrate --project-name <name> --plan
   uv run agent-engine phase4 orchestrate --project-name <name>
   ```
   Approve each gate when it stops (or use `--test-approve` only for a dry run; it is recorded as NOT a human sign-off),
   then `orchestrate --publish` writes tracker files under `outputs/<name>/tracker/`.
4. **Check:** every story has tasks covering its acceptance criteria; the sprint plan follows release → MoSCoW →
   Rank and shows a release plan; assignments route risky tasks to humans; infra renders dev/qa/stg/prod with a
   runbook; every report's `tokens` and `elapsed_seconds` recorded (see `report.json`, `runs/`, `logs/`).

## 4. Live run on the Jira test project (after the dummy run is clean)

1. Fix `.env`: `JIRA_EMAIL` = the account in `JIRA_USER_EMAIL`; `JIRA_PROJECT_KEY=GT`; `JIRA_BOARD_ID=3`;
   `PHASE4_TRACKER=jira`. **Never point it at GR** (the reference project) for runs that publish.
2. Put a few approved stories in GT in the same format as GR (description sections Acceptance criteria / Notes /
   Traceability, "Approved at gate G2" line, labels, fix versions, story points in "Story point estimate").
3. `uv run agent-engine phase4 import-stories --project-name <name>` (read-only) → check `phase4/stories.json`.
4. `uv run agent-engine phase4 orchestrate --project-name <name>`; approve gates with real names; then
   `--publish`. Verify in Jira: sub-tasks under the stories (labels `phase4`, `discipline-*`, estimate in the
   description), dependency links between tasks, stories moved into sprints (existing sprints reused), assignees set,
   no AI dispatch in Phase 4.
5. Record measured usage per stage (calls, input/output tokens, cache reads, minutes).

## 5. Tuning (after the live run)

- Set `AGENT_ENGINE_BREAKDOWN_*` budgets to ~2× the measured usage; add equivalent limits for the other code-driven
  stages if they lack one; keep "budget stop = partial, never approved".
- Revisit concurrency (`AGENT_ENGINE_HELPER_CONCURRENCY`, review concurrency) from measured latency and rate limits.
- Confirm prompt-cache hit rates (cache reads in the usage report) and that unchanged reruns make no model calls.

## 6. Definition of done for Phase 4
- All four agents match their spreadsheet rows (inputs, responsibilities, outputs, tiers, reviewers).
- The gate model is decided and implemented (section 1); nothing is published or dispatched without the required
  human approvals.
- A dummy end-to-end run and a live run on the test Jira project both succeed, with measured cost and time recorded
  in a short report under `docs/`.
- Budgets tuned from that data; all tests pass; work committed and pushed.
