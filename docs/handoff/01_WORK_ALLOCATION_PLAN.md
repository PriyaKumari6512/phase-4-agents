# Work Allocation (PDLC Phase 4, step 4.3) — review and fix plan

Self-contained plan for aligning the **Work Allocation** agent of `https://github.com/PriyaKumari6512/phase-4-agents`
(branch `feat/task-breakdown-from-approved-stories`) with the product specification. Background, the full Phase 4
spec and the working method are in `docs/handoff/00_START_HERE.md`; the two finished components
(`docs/TASK_BREAKDOWN.md`, `docs/SPRINT_PLANNING.md`) show the target style.

## 1. What the specification asks for

| | |
|---|---|
| Step | 4.3 — "Assign each task to an AI agent or human" (after 4.2 Sprint Planning, before 4.4 Infra, then gate G4) |
| Model tier | **S** (small/fast); escalate only when output fails checks |
| Responsibilities | • Recommend owner per task: AI agent or human developer • Match by task type, skills, capacity and risk level • **Route high-risk tasks (security, payments, core architecture) to humans by default** |
| Inputs | Sprint plan, team skills matrix, agent capabilities |
| Output | Task assignment plan |
| Output reviewed by | Engineering Manager (G4 approvers: Engineering Manager / Scrum Master for sprint plan & work allocation) |
| Human-in-the-loop rule 8 | "Security, payments and core architecture tasks are assigned to humans by default (Work Allocation Agent)." |
| Brownfield | "…assign owners" in Jira |
| Next step | 5.1 (Phase 5): the **Orchestrator** dispatches sprint tasks to the assigned agents / developers |

## 2. Where the code is

- Pack: `agents/work-allocation/agent.toml` (`model = "strong"`, tools `phase4-allocation`, write-capable filesystem),
  `system_prompt.md`, `validator/agent.toml` (`strong`, tool `phase4-allocation-check`), `validator/system_prompt.md`.
- Deterministic code: `src/agent_engine/phase4/allocation.py` (`prepare`, `solve`, `annotate`, `check`, `render_md`,
  `hard_checks`, `RISKY` keywords, `ci_ready_repos`), `alloc_solver.py` (Timefold service with local CP-SAT fallback),
  `profiles.py` (`phase4 mine-profiles`: git-mined skills and code ownership → `phase4/skill-profiles.json`),
  `readiness.py` (CI readiness and AI-agent outcome reconciliation), `dispatch.py` (AI briefs and dispatch adapters).
- Tools: `src/agent_engine/phase4/tools.py` (`allocation_prepare`, `allocation_solve`, `allocation_annotate`,
  `allocation_check`, plus `backlog_view`).
- Orchestrator stage: `src/agent_engine/phase4/orchestrator.py` (`STAGES`, `work-allocation`, gate `P4-G3`, needs `P4-G2`).
- Publishing: `publish_assignments` in `src/agent_engine/phase4/publish.py` (assigns Jira sub-tasks and **dispatches
  AI tasks** to Copilot coding agent / Claude Code Action).
- Contracts: `AssignmentPlan`, `Assignment`, `AIAgentWorker`, `TeamMember` in `src/agent_engine/phase4/contracts.py`.
- Tests: `tests/test_phase4_pipeline.py` (full flow), `tests/test_pipeline_jira.py`, `tests/test_production_regressions.py`.
- Recorded run (old implementation): Work Allocation took 4.0 min and 1.1M input tokens on a 3-requirement demo.

## 3. Review findings

### Wrong (does not match the spec)
1. **Model tier:** the pack uses `strong` (Sonnet) for the agent and its validator; the spec says **S**. The model's
   remaining judgement (is a task safe for an AI agent? one-line explanations) is light.
2. **"Core architecture" is not routed to humans.** Risk routing is a keyword list (`RISKY`: auth, payment,
   migration, terraform, secret, ...) matched against title/description/paths. Security and payments are partly
   covered by keywords; core architecture (shared foundations, cross-cutting modules, schema changes) is not. The new
   backlog carries structured signals that should drive this deterministically: task `discipline` (DB, DevOps),
   skill tags (`auth-security`, `payments`), tasks shared across stories (the cross-story merge note "Shared work:"),
   and cross-story dependencies.
3. **Phase boundary:** `publish_assignments` dispatches AI tasks (opens provider work) right after P4-G3. The spec puts
   dispatch in **Phase 5 (5.1, Orchestrator)** after the combined G4 gate. Phase 4 should publish the assignment plan
   (assignees in Jira) only.
4. **Labels:** the prompt says "delivery manager"; the spec says Engineering Manager (with Scrum Master).
5. **Stale references to the retired Task Breakdown:** the problem file still shows `agent1_ai_proposal` (Task Breakdown
   no longer proposes AI eligibility; every task has `ai_eligible = false`, reason "Decided by the Work Allocation
   agent"); a hard-check message says "Agent 1 sets `repo` per feature or task".

### Extra
- A full Sonnet validator on every run after the deterministic `allocation_check`, with up to 2 fix rounds.
- The model has `write_file` / `edit_file` though it must never edit the plan.
- AI dispatch at publish time (see wrong #3).

### Correct and worth keeping
- Hard AI rules before any model judgement: acceptance criteria present, ≤ 4 named files, hours under the agent's
  limit, sensitive areas, open questions, a code repository, **CI approved and operational for that repository**.
- Skills matrix: declared skills in `phase4/project.json` blended with git-mined evidence and code ownership.
- AI agent capabilities (`ai_agents`: skills, max hours, concurrency) and **shadow mode** until
  `ai_min_recorded_outcomes` real outcomes are recorded.
- Timefold task-assigning service with a local CP-SAT fallback; capacity and review budget as hard rules; score
  breakdown, runner-up and post-checks.
- Pins, vetoes and "keep away from AI" lists from the approver.

### Things to watch with the new backlog (from Task Breakdown)
- Task ids are now `<JIRA-KEY>-Tnn` (e.g. `GR-9-T01`); `dispatch.task_id_in` was already updated.
- Tasks often have **empty `file_paths`** (Task Breakdown only sets paths the architecture defines) and many have
  **open questions** — both hard rules then exclude almost every task from AI. That is safe, but the product owner
  should confirm it is the intended default (see decisions).
- Task `discipline` (FE/BE/DB/DevOps/QA) and `type` are available; `type` maps FE→ui, BE/DB→feature, DevOps→infra,
  QA→test.

### Optimizations
- Make it code-driven like Task Breakdown and Sprint Planning: code runs `prepare` → hard rules → solver → runner-up;
  **one small-model structured call** returns AI-eligibility verdicts for the candidates and one explanation per
  assignment. Removes the tool loop (~1.1M tokens → a few thousand).
- Deterministic review plus a light review only of flagged text (generic AI reasons, explanations that contradict
  the score breakdown).

## 4. Decisions to ask the product owner first

1. **Open questions and missing file paths:** keep them as hard blockers for AI (safest; few AI tasks until the
   architecture names files), or allow AI on tasks whose open questions are only informational? *(Recommended: keep
   as blockers.)*
2. **AI dispatch:** move dispatch out of Phase 4 (publish only assignees; dispatch becomes a separate Phase 5 command
   run after G4), or keep it behind an explicit opt-in flag? *(Recommended: separate command, off by default.)*
3. **"Core architecture" definition:** which signals count — DB/DevOps discipline, `auth-security`/`payments` skills,
   shared-work tasks, tasks other stories depend on, specific architecture components listed in `project.json`?
   *(Recommended: all of these, plus an optional `human_only_components` list in `project.json`.)*

## 5. Fix plan (one step at a time; each step: code → tests → full suite green)

**Step 1 — Risk routing from structured signals**
- Add `risk_reasons(task, backlog, settings)` in `allocation.py`: discipline DB/DevOps; skills `auth-security`,
  `payments`; shared-work tasks; tasks with dependants in other stories; components in an optional
  `ProjectSettings.human_only_components`; plus the existing keywords. A non-empty result makes the task human-only
  with the reason recorded (`hard_rule_failed`).
- Done when: unit tests cover each signal; the bookmarks fixture's DB task and any auth task are human-only.

**Step 2 — Clean up stale fields and labels**
- Drop `agent1_ai_proposal` from `allocation/problem.json`; reword the `repo` message; "delivery manager" →
  "Engineering Manager / Scrum Master" in prompts; P4-G3 description in `gates.toml` says Engineering Manager.

**Step 3 — Code-driven stage with one small-model call**
- New `src/agent_engine/phase4/work_allocation.py` with `generate`, `review`, `repair`, `operation_model`, following
  `sprint_planning.py`. `generate`: (if the request is not the default "Assign sprint N.") one small call turns a
  reviewer's request into pins / vetoes / block-AI lists, checked against real task and worker ids → `prepare` →
  **one structured call** with schema `{verdicts: [{task_id, eligible, reason}], explanations: [{task_id, text}]}`
  for the AI candidates and assignments → checked (verdicts only for candidates, specific reasons, an explanation for
  every assignment) and retried once → `solve` → `annotate`. Use `phase4/structured.py`.
  Note: explanations depend on the solver result, so either run two small calls (verdicts → solve → explanations) or
  ask for verdicts first and generate explanations deterministically from the score breakdown (cheaper; recommended).
- Register in `STRUCTURED_STAGES` (`src/agent_engine/cli.py`); add the module to `recovery.py` domain lists.
- Pack: `model = ["fast", "strong"]`, `filesystem = ["ls", "read_file"]`, no tools; validator `model = "fast"`, no
  tools. Rewrite both prompts for the new jobs (no tools mentioned).
- Done when: a CLI run with a fake model passes write + verify on the `fast` tier with no deep agent built.

**Step 4 — Validation**
- `review`: deterministic `allocation.check` (capacity, skills, AI rules, CI readiness, every task assigned or
  explained) → problems make it partial; flag generic AI reasons ("looks simple", < 15 chars) and explanations that
  contradict the score breakdown (claims ownership with ownership 0, wrong runner-up) → light review with the
  validator prompt only for flagged items; fix escalates `fast` → `strong`; a fix that changes nothing stops.

**Step 5 — Publish assignments only; dispatch separately**
- `publish_assignments` assigns Jira sub-tasks (human assignees via `tracker_account_id` / `JIRA_ACCOUNT_MAP`) and
  writes explanation comments; AI dispatch moves to a new `agent-engine phase4 dispatch` (or Phase 5) command that
  refuses until the plan's gate is approved and CI is operational. Keep the existing dispatch code and tests, just
  moved behind the command.

**Step 6 — Clean-up, docs, tests**
- Remove the `allocation_*` agent tools / `phase4-allocation*` tool sets once nothing uses them (keep `backlog_view`
  only if another pack still uses it). Write `docs/WORK_ALLOCATION.md`; update `docs/PHASE4.md`.
- Tests: risk signals, the single call and its checks, request → pins/vetoes, flagged-only review, escalation through
  the CLI, publish without dispatch.

## 6. Acceptance criteria for "Work Allocation complete"
- Every task in the chosen sprint is assigned to a person or an AI agent, or listed as unassigned with a reason.
- Security, payments and core-architecture tasks are never given to an AI agent by default.
- Runs on tier S; the model never edits files; one structured call per run (plus one for a reviewer request).
- Deterministic checks first; model review only of flagged text; escalation on failure.
- Phase 4 publishing assigns owners in Jira and does not dispatch AI work.
- All tests pass; the component is committed and pushed as one commit.
