# PDLC Phase 4 — Task, Sprint & Environment Setup

Four code-driven agents in the agent-engine format (one folder each under `agents/`, each with its own validator). Each one combines the model's judgement with tools for everything that must be exact:

| Agent | Folder | The model decides | Tools compute (`src/agent_engine/phase4/`) |
|---|---|---|---|
| 1 Task Breakdown | `agents/task-breakdown/` | per approved story: FE/BE/DB/DevOps/QA tasks, task acceptance criteria, hours, skills, in-story dependencies; across stories: missing dependencies and work planned twice; a light review of flagged items | Jira story import, structured calls with a cached prefix, ids, Jira "blocks" links, story points (kept from Jira or derived from hours), DAG/coverage/size/effort checks, retained results, Jira sub-task publishing ([TASK_BREAKDOWN.md](TASK_BREAKDOWN.md)) |
| 2 Sprint Planning | `agents/sprint-planning/` | sprint goals, deferral explanations, the summary, which verified option to recommend; turning a reviewer's request into pins or an option (small model) | calendar + PTO availability, velocity from Jira closed sprints, Monte Carlo P50/P85, priority from the approved roadmap (release → MoSCoW → Rank), release deadlines, OR-Tools CP-SAT packing, release plan, infeasibility cores and verified options, Jira sprint reuse ([SPRINT_PLANNING.md](SPRINT_PLANNING.md)) |
| 3 Work Allocation | `agents/work-allocation/` | which tasks are safe for an AI coding agent, one-line explanation per assignment | hard AI rules, capacity and review budget, Timefold task-assigning service (local CP-SAT fallback), score breakdown, runner-up, post-checks |
| 4 Infra & Pipeline | `agents/infra-pipeline/` | infra intent from architecture.md, repairing files that fail checks | golden-path catalog rendering (OpenTofu, Argo CD, Helm, ExternalSecrets, PrometheusRule, Atlantis, CI), 10 sandbox checks, secret scan, risk score, PR text |

All four stages use checked structured calls for model judgement. Code owns assembly, solvers, rendering, validation and files. Models receive no write tools. See [TASK_BREAKDOWN.md](TASK_BREAKDOWN.md), [SPRINT_PLANNING.md](SPRINT_PLANNING.md), [WORK_ALLOCATION.md](WORK_ALLOCATION.md) and [INFRA_PIPELINE.md](INFRA_PIPELINE.md).

## Inputs and outputs

All paths are inside the project folder `outputs/<project>/`. "Gate" files are written only by
`agent-engine gate ...` (a human decision); agents can read them, never write them.

| Agent | Reads (declared inputs; the run refuses if one is missing) | Also reads if present | Writes (declared outputs) | Also writes |
|---|---|---|---|---|
| 1 Task Breakdown | `phase4/stories.json` (approved stories, imported from Jira), `prd.md`, `architecture.md`, `phase4/project.json`, `gates/G3A.approved.json`, `gates/G3B.approved.json` | `phase4/history.json`, `requests/task-breakdown.md` | `backlog/backlog.json`, `backlog/backlog.md` | `.engine-task-breakdown/` (retained per-story results, engine-owned) |
| 2 Sprint Planning | `backlog/backlog.json`, `gates/P4-G1.approved.json`, `phase4/project.json` | `phase4/history.json` (refreshed from Jira closed sprints), previous `sprint/sprint-plan.json` | `sprint/sprint-plan.json`, `sprint/sprint-plan.md` | `sprint/capacity.json`, `sprint/solver-diagnostics.json`, `.engine-sprint-planning/` |
| 3 Work Allocation | `sprint/sprint-plan.json`, `gates/P4-G2.approved.json`, `backlog/backlog.json`, `phase4/project.json` | `phase4/skill-profiles.json`, `phase4/agent-outcomes.json`, `infra/manifest.json` + `gates/P4-G4.approved.json` (CI-ready repos) | `allocation/assignments.json`, `allocation/assignments.md` | `allocation/problem.json` |
| 4 Infra & Pipeline | `architecture.md`, `phase4/project.json` | — | `infra/intent.json`, `infra/manifest.json`, `infra/checks.json`, `infra/PR.md` | `infra/repo/**` (infra repository files), `infra/ci/<owner>__<repo>/**` (CI per code repo) |

The file formats are Pydantic models in `src/agent_engine/phase4/contracts.py`; `agent-engine phase4 schemas`
writes them as JSON Schema.

### `phase4/stories.json` (approved stories)

The PDLC has the stories written and approved (Gate 2) before Phase 4; Task Breakdown splits them into tasks and does
not write its own. With `PHASE4_TRACKER=jira` the orchestrator (or `agent-engine phase4 import-stories`) reads them
from Jira with read-only requests before anything runs, and rewrites the file only when Jira's content changed:

| Setting | Default | Meaning |
|---|---|---|
| `JIRA_STORY_JQL` | `project = "<key>" AND issuetype = Story AND statusCategory = "To Do" ORDER BY key ASC` | Which stories to read. |
| `PHASE4_STORY_APPROVAL_MARKER` | `Approved at gate G2` | Text the description must contain; others are listed under `excluded`. Empty = no check. |
| `JIRA_ACCEPTANCE_FIELD_ID` | (none) | Read acceptance criteria from this custom field instead of the description's "Acceptance criteria" heading. |
| `JIRA_STORY_POINTS_FIELD_ID` | auto | Story points field; by default the populated field named "Story point estimate" or "Story Points". |
| `PHASE4_IMPORT_STORIES` | `true` | `false` keeps the existing snapshot without contacting Jira. |

Each story keeps its key, statement, acceptance criteria with their own ids (`US-001.AC1`), notes, traceability,
labels (US/FR/NFR ids, persona, `moscow-*`), fix versions, components, epic, existing story points and "blocks" links.
With another tracker, provide `phase4/stories.json` yourself (`agent-engine phase4 schemas` writes its JSON Schema).

### Design gates G3A and G3B

"Phase 4 starts only when both G3A and G3B are approved." Task Breakdown refuses to run (and the orchestrator stops
before it) until a human has approved `G3A` (`designs/designs.md`: screens, prototype links, design reports) and
`G3B` (`architecture.md`), and neither file changed since. Infra & Pipeline is not blocked by them. A rejected P4-G1
points back to design. These gates are never test-approved by the orchestrator.

### `phase4/project.json` (human input)

Project name, tracker (`local`, `jira`, `linear`, `github`), `code_repos`, `infra_repo`, `team` (id, name, email,
tracker account, GitHub login, role, allocation %, hours/day, declared skills, PTO days), `ai_agents` (Copilot coding
agent / Claude Code Action, skills, limits), `calendar` (sprint length, first sprint start, horizon, holidays,
ceremonies), `definition_of_done`, `story_point_scale`, `hours_per_story_point`, `maintenance_capacity_pct`,
`max_story_points_per_story`, `deadlines` (prd.md requirement ids + date, hard or soft), `release_deadlines`
(fallback date per roadmap release, e.g. `{"release": "MVP", "due_date": "2027-01-29", "hard": true}`; a tracker
version's own release date wins), `ai_min_recorded_outcomes`
(AI agents work in shadow mode until this many outcomes are recorded; default 20, the example uses 0).

## Flow and gates

Task Breakdown → Sprint Planning → Work Allocation remains the planning sequence. Infra starts early so reviewed, operational CI can inform AI eligibility. This is the documented ordering deviation from the spreadsheet; no execution is dispatched in Phase 4.

Keep P4-G1 (Tech Lead), P4-G2 (Scrum Master / Engineering Manager), P4-G3 (Engineering Manager) and P4-G4 (DevOps Lead + Solution Architect) as G4 parts 1–4. Final `G4` binds all seven output artifacts. Every publisher requires every checkpoint plus current final G4, including direct Python publisher calls. Humans still own each decision and maker-checker applies.

The orchestrator waits for final G4 after the four checkpoints. CLI approval of final G4 refuses before its parts are approved. A final changes request routes to P4-G1 for planning issues or P4-G4 for environment/pipeline issues; rejection invalidates both design approvals and returns to G3A/G3B.

`--test-approve` records synthetic decisions, never human sign-off. Automated final G4 cannot authorize live publication. Phase 5 `phase4 dispatch` additionally requires current environment readiness, operational CI, completed predecessors and available worker concurrency.

`phase4 check-environments` records readiness using read-only sources. The generated infra PR/runbook lists missing setup; approved PRs do not establish provisioned environments.

## Commands

Record each checkpoint first and final G4 after all four outputs are reviewed. Publication commands wait for final approval; use `agent-engine gate G4 --project-name taskflow --decision approved --approver "<reviewer>" --submitted-by "<maker>"` with the real participants after review.

```bash
uv sync                                               # Python 3.13 env with ortools, networkx, ...
uv run agent-engine phase4 init --project-name taskflow --example taskflow    # sample inputs into outputs/taskflow/
uv run agent-engine phase4 import-stories --project-name taskflow      # approved stories from Jira (read-only)
uv run agent-engine gate G3A --project-name taskflow --decision approved --approver "Design Lead" --submitted-by "UX agent"
uv run agent-engine gate G3B --project-name taskflow --decision approved --approver "Architect" --submitted-by "Architecture agent"
uv run agent-engine run "Break the approved stories down into tasks." --agent task-breakdown --project-name taskflow
uv run agent-engine gate P4-G1 --project-name taskflow --decision approved --approver "Priya" --submitted-by "Rahul"
uv run agent-engine run "Plan the sprints." --agent sprint-planning --project-name taskflow
uv run agent-engine gate P4-G2 --project-name taskflow --decision approved --approver "Dana" --submitted-by "Rahul"
uv run agent-engine run "Assign sprint 1." --agent work-allocation --project-name taskflow
uv run agent-engine run "Set up dev, qa, stg and prod." --agent infra-pipeline --project-name taskflow
uv run agent-engine phase4 mine-profiles --project-name taskflow --repo ../taskflow-api --name acme/taskflow-api
```

## Orchestrator: the whole job in one command

```bash
uv run agent-engine phase4 orchestrate --project-name taskflow --plan           # what would run (no model call)
uv run agent-engine phase4 orchestrate --project-name taskflow                  # run what is needed, stop at gates
uv run agent-engine phase4 orchestrate --project-name taskflow --sprint 2       # Work Allocation for sprint 2
uv run agent-engine phase4 orchestrate --project-name taskflow --publish        # when all is approved, publish
```

The orchestrator is plain code (`src/agent_engine/phase4/orchestrator.py`), not a model: it reads the project
folder and runs `agent-engine run` for the agent that is needed, so every agent keeps its own validator and gate.
It repeats until everything is done or a human is needed. Exit code 0 = done, 2 = waiting for a human, 1 = failed.

| Situation | What it does |
|---|---|
| An input file is missing | Does not run the agent that needs it; says which file to add. |
| No output yet | Runs the agent (Infra runs next to Task Breakdown; the rest in order). |
| Output ready, gate not approved or stale | Stops and prints the `agent-engine gate ...` command. It never approves by itself. |
| Gate answered `changes_requested` | Runs the owning agent again with the gate comment as the request. |
| An input the agent read changed | Runs only that agent, then each later agent once the gate before it is approved again. A team, calendar or PTO change re-runs Sprint Planning and Work Allocation, not Task Breakdown or Infra. |
| Validator ends partial / fail | Stops and lists the open gaps (no endless retry). Its gate is not test-approved. |
| Subscription rate limit (429) | Stops; the same command resumes later from the same place. |

What each agent last read is kept in `phase4/orchestrator-state.json`; a project run by hand before has none, and its
outputs are taken as up to date. `--test-approve` approves the gates itself for demos and tests; each approval is
recorded as "Orchestrator (automated test approval) — NOT a human sign-off". Use real approvers in production.

Optional services (`docker compose up -d allocation-solver`, `docker compose build iac-sandbox`): without the
Timefold service the local CP-SAT model is used; without the sandbox image checks run with locally installed
tools, and any tool that is missing is reported as skipped (never as passed).

## Settings (`.env`)

The model comes from the engine's settings (`SDLC_AGENT_ANTHROPIC_AUTH_MODE=subscription` +
`SDLC_AGENT_ANTHROPIC_OAUTH_TOKEN`, or `ANTHROPIC_API_KEY`). Phase 4 adds `PHASE4_ALLOCATION_SOLVER_URL`,
`PHASE4_ALLOCATION_SOLVER_MODE` (auto | timefold | local), `PHASE4_IAC_SANDBOX_IMAGE`, `PHASE4_IAC_SANDBOX_MODE`
(auto | off), `PHASE4_PR_MODE` (local | github), and tracker credentials (`JIRA_EMAIL`, `JIRA_API_TOKEN`,
`LINEAR_API_KEY`, `GITHUB_TOKEN`, `GITHUB_COPILOT_USER_TOKEN`).

## Changes to the engine

Small and additive, so other teams' packs are unaffected:
- `agent.toml` accepts `skills = "<folder>"` (Agent Skills, served read-only at `/skills/`) and
  `[subagents.<name>]` tables (`description`, `prompt` file, optional `model`). Named subagents get the same tools,
  file tools, skills, write guard and lock as the built-in helper. (No Phase 4 pack uses them any more.)
- A `frontier` model tier (`SDLC_AGENT_FRONTIER_MODEL`, default Opus for Anthropic) for escalation lists such as
  Task Breakdown's `model = ["strong", "frontier"]`.
- `TOOLS` registers the Phase 4 tool sets (`phase4-*`); the Phase 4 code lives in `src/agent_engine/phase4/`.
- `agent-engine phase4 ...` CLI commands (init, publish, mine-profiles, schemas), which never call a model.
- The tool `infra_validate` runs fixed check commands in the sandbox image. The agent itself still has no shell
  and cannot choose a command; this is the one place Phase 4 executes programs, and it is worth confirming with
  the platform owner.

## Verified live (Claude subscription, `outputs/bookmarks-live`, small 3-requirement PRD)

| Agent | Time | Input tokens | Validator | Result |
|---|---|---|---|---|
| Task Breakdown | 9.4 min | 3.5 M | partial → fixed → success | (retired spec-kit implementation; the story-based one is in [TASK_BREAKDOWN.md](TASK_BREAKDOWN.md)) |
| Sprint Planning | 1.3 min | ~0.2 M | success | (retired agent-loop implementation; the code-driven one is in [SPRINT_PLANNING.md](SPRINT_PLANNING.md)) |
| Infra & Pipeline | 13.6 min | 0.3 M | success | 44 files, all 10 sandbox checks pass, risk 50, 1 infra PR + 2 CI PRs (local mode) |
| Work Allocation | 4.0 min | 1.1 M | partial → fixed → success | Timefold service, 34 tasks assigned, 2 unassigned (skill gaps), capacity respected |

Gates P4-G1..G4 were approved with `agent-engine gate` and every `phase4 publish` ran in local mode (tracker files,
PR folders). Token use is driven by deepagents re-sending context on every tool call.

## Not verified here

Jira, Linear and GitHub publishing, Copilot / Claude Code dispatch and GitHub pull requests are ported from the
earlier Phase 4 implementation but need credentials and were not run; `PHASE4_PR_MODE=local` and the `local`
tracker write everything as files instead.

Work Allocation now uses checked small-model eligibility, structured risk routing and deterministic explanations. See [WORK_ALLOCATION.md](WORK_ALLOCATION.md). Phase 5 execution is explicit through `phase4 dispatch` and requires all four current gate approvals.

Infra now includes QA, immutable-digest promotion, branching/runbook documents, checked intent and bounded repair. See [INFRA_PIPELINE.md](INFRA_PIPELINE.md). Operational evidence is collected by `phase4 check-environments`; missing scanners or readiness sources never count as passed.

## Execution budgets

All structured stages share per-run call/token/time limits across generation, review and repair. Task Breakdown retains its existing BREAKDOWN settings. Other stages use `AGENT_ENGINE_SPRINT_PLANNING_*`, `AGENT_ENGINE_WORK_ALLOCATION_*` and `AGENT_ENGINE_INFRA_PIPELINE_*` with suffixes MAX_CALLS, MAX_INPUT_TOKENS, MAX_OUTPUT_TOKENS and TIMEOUT_SECONDS. Initial defaults are 16 calls, 1M reported input tokens, 64k reported output tokens and 1800 seconds. These are provisional safeguards, not production usage estimates. Budget stops remain partial and never approval. Calibrate from a separately authorized live run; fake-model timings do not justify live token tuning.
