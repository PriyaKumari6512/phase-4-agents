# Phase 4 alignment — handoff (start here)

This folder lets any engineer or AI continue aligning the **PDLC Phase 4 agents** in this repository with the
product specification. Read this file first, then the plan for the component you are working on. Each plan file is
self-contained.

| File | What it is | Status |
|---|---|---|
| `00_START_HERE.md` | Context, specification summary, what is done, how to work | — |
| `01_WORK_ALLOCATION_PLAN.md` | Review findings and step-by-step fix plan for agent 3 (step 4.3) | **next** |
| `02_INFRA_PIPELINE_PLAN.md` | Review findings and step-by-step fix plan for agent 4 (step 4.4) | after 01 |
| `03_INTEGRATION_AND_E2E_PLAN.md` | Phase 4 gate, deferred items, end-to-end run on dummy/real data, tuning | last |

## 1. The repository

- GitHub: `https://github.com/PriyaKumari6512/phase-4-agents`
- Working branch: **`feat/task-breakdown-from-approved-stories`** (branched from `perf/task-breakdown-quality-context`).
  Continue on this branch (or branch from it). Commits so far on top of the base:
  - `70b669b` Rebuild Task Breakdown on approved Jira stories per the PDLC Phase 4 spec
  - `9bc15f8` Align Sprint Planning with the PDLC Phase 4 spec (step 4.2)
- Python 3.13 with `uv`. Setup and checks:
  ```bash
  uv sync
  uv run python -m pytest -q          # 365 tests at the time of writing; all must pass
  uvx ruff check --select F src       # a few pre-existing findings exist in allocation.py / sandbox.py
  uv run agent-engine list            # lists the agent packs
  ```
- Docs that describe the current code: `docs/PHASE4.md` (overview), `docs/TASK_BREAKDOWN.md`,
  `docs/SPRINT_PLANNING.md`, `docs/PIPELINE_JIRA.md`, `docs/PIPELINE_RECOVERY.md`.
  Older reports (`docs/CODEBASE_AUDIT.md`, `docs/PERFORMANCE_OPTIMIZATION_REPORT.md`, `docs/pipeline-run-results/`)
  describe the retired implementation and are kept only as history.

## 2. The specification (source of truth)

The product owner's spreadsheet `PDLC_AI_Agent_Suite.xlsx` defines every agent. It is not in the repository; the
Phase 4 parts that matter are reproduced here.

### Phase 4 — Task, Sprint & Environment Setup (starts only after gates G3A and G3B are approved)

| Step | Agent | Tier | Role and responsibilities | Inputs | Outputs | Output reviewed by |
|---|---|---|---|---|---|---|
| 4.1 | Task Breakdown | M | Split approved stories into FE, BE, DB, DevOps, QA tasks; estimate each task (story points / hours); define dependencies and Definition of Done per task | Approved stories, UI designs, HLD/LLD, API specs | Task list with estimates & dependencies (Jira / Linear) | Tech Lead |
| 4.2 | Sprint Planning | S | Group tasks into sprints by priority, dependencies, velocity; draft sprint goals and capacity plan; plan only tasks whose designs are approved (design runs one sprint ahead) | Task list, team capacity, velocity history, roadmap | Sprint plan, sprint goals, release plan | Scrum Master / Engineering Manager |
| 4.3 | Work Allocation | S | Recommend owner per task: AI agent or human developer; match by task type, skills, capacity and risk level; route high-risk tasks (security, payments, core architecture) to humans by default | Sprint plan, team skills matrix, agent capabilities | Task assignment plan | Engineering Manager |
| 4.4 | Infrastructure & Pipeline Setup | M | Write Infrastructure-as-Code (Terraform or similar) for Dev, QA, Staging, Prod; create CI/CD pipelines and branching strategy; set up secrets management, access controls, monitoring hooks | HLD/LLD, NFRs, client hosting / cloud constraints | IaC scripts, provisioned environments, pipeline definitions, environment runbook | DevOps Lead; Solution Architect |
| G4 | Human gate | — | Plan & environment approval | Tasks, sprint plan, assignments, environments | Approved sprint plan & ready environments | Tech Lead; Engineering Manager / Scrum Master; DevOps Lead; Solution Architect. Changes requested → back to 4.1 / 4.4. Rejected → back to 3A / 3B |

Workflow order in the spec: 4.1 → 4.2 → 4.3 → 4.4 → G4 → 5.1 (the Orchestrator dispatches sprint tasks to the
assigned agents/developers — that is Phase 5, not Phase 4).

### Platform rules that apply to every agent

- **Model tiers:** S = small/fast (cheapest), M = mid-tier (default), F = frontier (most expensive). Each agent has
  a default tier; the router escalates to a bigger model **only when output fails checks** (S → M → F, max 2 retries).
- **How every task runs:** load config and budget → build lean context (relevant chunks only, cached prefix) →
  response cache → pick tier → call → run tools → **validate output with deterministic checks (tests, schema,
  guardrails); on FAIL escalate** → human gate → log everything.
- **Token techniques:** T1 retrieval not whole documents, T2 diffs, T3 prompt caching, T4 response cache, T5 right-size
  the model, T6 batch, T7 structured output and token caps, **T8 deterministic tools first (the LLM only explains and
  fixes)**, T9 context compaction, T10 budgets and alerts.
- **Human-in-the-loop:** agents draft, humans own; every gate is Approve / Request Changes / Reject; nothing is
  auto-approved; maker-checker (the requester cannot approve); confidence flags on low-confidence sections;
  **security, payments and core-architecture tasks go to humans by default (Work Allocation)**; no unreviewed AI code;
  budget stops pause the agent; environment promotion Dev → QA (QA Lead) → Staging/UAT (client) → Prod (go/no-go +
  DevOps Lead); the exact build approved in UAT is the one deployed to production.
- **Brownfield (existing Jira project):** Jira stays the source of truth; Task Breakdown → Sprint Planning → Work
  Allocation "create sub-tasks in Jira, place them in a sprint, assign owners".

## 3. What is already done

### Agent 1 — Task Breakdown (complete against its plan) — see `docs/TASK_BREAKDOWN.md`
- Approved stories are imported read-only from Jira into `phase4/stories.json` (`story_import.py`): statement,
  acceptance criteria with their own ids (`US-001.AC1`), notes, traceability, labels (US/FR ids, persona,
  `moscow-*`), fix versions, components, epic, existing story points, Jira Rank, "blocks" links; plus the project's
  versions (the roadmap) and closed sprints (velocity).
- Task Breakdown requires human approval of **G3A** (`designs/designs.md`) and **G3B** (`architecture.md`).
- Code-driven: one structured model call per story (cached prompt prefix) returns FE/BE/DB/DevOps/QA tasks with
  hours, criteria, coverage of the story's acceptance criteria, dependencies, skills; one cross-story call adds
  dependencies between stories and merges duplicated work; deterministic checks + a light model review only of
  flagged items; fix escalates `strong` → `frontier` (Opus) for affected stories only.
- Publishing creates tasks as **Jira sub-tasks of the existing stories**; epics/stories are never edited.
- spec-kit and the old tool-using agent were removed.

### Agent 2 — Sprint Planning (complete against its plan) — see `docs/SPRINT_PLANNING.md`
- Priority from the approved order (release → MoSCoW → Jira Rank), no model scoring.
- Releases are deadlines (Jira version date, else `release_deadlines` in `phase4/project.json`); the plan includes a
  **release plan** (finish dates, P50/P85 forecasts, status).
- Velocity from Jira closed sprints; capacity from calendar/PTO.
- Code-driven: one small-model (`fast`, Haiku) call writes goals, deferral explanations, summary, recommended option;
  a reviewer's request becomes checked pins / an option choice. Deterministic checks + light review of flagged text;
  fix escalates `fast` → `strong`.
- Publishing reuses existing Jira sprints instead of creating duplicates.

### Shared infrastructure added
- `src/agent_engine/phase4/structured.py`: one structured model call with a cached system prefix (use it).
- `src/agent_engine/cli.py`: `STRUCTURED_STAGES` maps an agent name to the module that runs it in code
  (`generate`, `review`, `repair`, `operation_model`). Add new code-driven stages there.
- Model tiers: `strong`, `fast`, **`frontier`** (`SDLC_AGENT_FRONTIER_MODEL`, default Opus for Anthropic).
- `tests/conftest.py` strips live tracker settings from the environment and **blocks real network** in tests.
- `tests/phase4_helpers.py`: `make_design_ready(root)`, `build_story_backlog(root)` (a story-based backlog for the
  bookmarks fixture without a model).

## 4. How the previous two components were done (repeat this method)

1. **Review against the spec.** For the component's spreadsheet rows, read its pack (`agents/<name>/agent.toml`,
   `system_prompt.md`, `validator/`), its code under `src/agent_engine/phase4/`, the orchestrator stage, publishing,
   and any recorded runs. Report: what is **wrong** (does not match the spec), what is **extra**, what is **correct**,
   and what can be **optimized** (cost, speed, quality).
2. **Ask the product owner** only the decisions that change the plan (offer a recommended option).
3. **Write a step plan** with done-criteria, then implement **one step at a time**: code → tests with fake model /
   fake tracker → full suite green → short report.
4. **Patterns that worked:**
   - Code does everything exact (ids, graphs, solvers, checks); the model only does language or judgement, through
     **one structured call** per item with a cached prefix, checked in code, retried once.
   - Deterministic checks first; a light model review **only of what the checks flag**; nothing flagged = no call.
   - Retain results by an exact digest of what produced them so unchanged work is never sent again.
   - Never let upstream approved artifacts be rewritten (stories, priorities, points set in Jira).
   - Tests never touch the network or live Jira; live checks are read-only and written to a scratch folder.
5. **Commit and push** each component as one commit on the branch, ending the message with the attribution line
   the team uses (previous commits ended with a `Co-Authored-By:` line).

## 5. Environment notes (no secrets here)

- `.env` (git-ignored) holds model and Jira credentials. The engine reads `JIRA_EMAIL`, `JIRA_API_TOKEN`,
  `JIRA_BASE_URL`, `JIRA_PROJECT_KEY`, `JIRA_BOARD_ID`, `PHASE4_TRACKER=jira`. In the owner's `.env` the working
  account is in `JIRA_USER_EMAIL`; **`JIRA_EMAIL` must be set to that same value** before a real run, and
  `JIRA_PROJECT_KEY` / `JIRA_BOARD_ID` must point at the test project.
- Jira projects on that site: **GR** (reference project with 36 approved stories, board 4 — **read-only, never
  modify**) and **GT** (test project, board 3). Story points live in `customfield_10016` ("Story point estimate");
  the board's estimation field `customfield_10036` is empty; Rank is `customfield_10019`; Sub-task screens have no
  time-tracking field.
- Models: `SDLC_AGENT_STRONG_MODEL` (Sonnet), `SDLC_AGENT_FAST_MODEL` (Haiku), optional `SDLC_AGENT_FRONTIER_MODEL`.

## 6. Agreed approach for the rest

- Align **Work Allocation** (01), then **Infra & Pipeline** (02), one component at a time.
- Only after all four agents match the spec, run the whole pipeline end to end on dummy data, then real data (03).
- Tune budgets and limits after that run, from measured usage.
