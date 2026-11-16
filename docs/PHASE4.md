# PDLC Phase 4 — Task, Sprint & Environment Setup

Four agents in the agent-engine format (one folder each under `agents/`, each with its own validator), built on
deepagents. Each one combines the model's judgement with tools for everything that must be exact:

| Agent | Folder | The model decides | Tools compute (`src/agent_engine/phase4/`) |
|---|---|---|---|
| 1 Task Breakdown | `agents/task-breakdown/` | feature split, specs and plans (github spec-kit 1.3.0 skills), estimates by analogy, task acceptance criteria, skills, AI proposals, cross-feature dependencies | spec-kit scripts without a shell, spec-kit parser, backlog build, TF-IDF reference tickets, story→task hour roll-up, DAG/coverage/size validation |
| 2 Sprint Planning | `agents/sprint-planning/` | business value per story, which option to recommend, sprint goals, explanations | calendar + PTO availability, Monte Carlo P50/P85 velocity, WSJF, OR-Tools CP-SAT packing, infeasibility cores and verified options |
| 3 Work Allocation | `agents/work-allocation/` | which tasks are safe for an AI coding agent, one-line explanation per assignment | hard AI rules, capacity and review budget, Timefold task-assigning service (local CP-SAT fallback), score breakdown, runner-up, post-checks |
| 4 Infra & Pipeline | `agents/infra-pipeline/` | infra intent from architecture.md, repairing files that fail checks | golden-path catalog rendering (OpenTofu, Argo CD, Helm, ExternalSecrets, PrometheusRule, Atlantis, CI), 10 sandbox checks, secret scan, risk score, PR text |

Deepagents features used: **skills** (spec-kit's own `SKILL.md` files, loaded from `agents/task-breakdown/skills/`),
**named subagents** (`speckit-feature` runs spec-kit for one feature, `backlog-enricher` enriches one epic; the agent
starts them in parallel with the `task` tool), **knowledge** (the infra catalog at `/knowledge/catalog/`),
summarization and the engine's write guard and lock on every subagent.

## Inputs and outputs

All paths are inside the project folder `outputs/<project>/`. "Gate" files are written only by
`agent-engine gate ...` (a human decision); agents can read them, never write them.

| Agent | Reads (declared inputs; the run refuses if one is missing) | Also reads if present | Writes (declared outputs) | Also writes |
|---|---|---|---|---|
| 1 Task Breakdown | `prd.md` (from the `prd` agent), `architecture.md`, `phase4/project.json` | `phase4/history.json`, `requests/task-breakdown.md` | `backlog/backlog.json`, `backlog/backlog.md` | `specs/NNN-name/{spec,plan,tasks}.md` (+ research, data-model, contracts, clarifications), `.specify/`, `backlog/features.json`, `backlog/enrichments.json` |
| 2 Sprint Planning | `backlog/backlog.json`, `gates/P4-G1.approved.json`, `phase4/project.json` | `phase4/history.json`, previous `sprint/sprint-plan.json` | `sprint/sprint-plan.json`, `sprint/sprint-plan.md` | `sprint/capacity.json` |
| 3 Work Allocation | `sprint/sprint-plan.json`, `gates/P4-G2.approved.json`, `backlog/backlog.json`, `phase4/project.json` | `phase4/skill-profiles.json`, `phase4/agent-outcomes.json`, `infra/manifest.json` + `gates/P4-G4.approved.json` (CI-ready repos) | `allocation/assignments.json`, `allocation/assignments.md` | `allocation/problem.json` |
| 4 Infra & Pipeline | `architecture.md`, `phase4/project.json` | — | `infra/intent.json`, `infra/manifest.json`, `infra/checks.json`, `infra/PR.md` | `infra/repo/**` (infra repository files), `infra/ci/<owner>__<repo>/**` (CI per code repo) |

The file formats are Pydantic models in `src/agent_engine/phase4/contracts.py`; `agent-engine phase4 schemas`
writes them as JSON Schema.

### `phase4/project.json` (human input)

Project name, tracker (`local`, `jira`, `linear`, `github`), `code_repos`, `infra_repo`, `team` (id, name, email,
tracker account, GitHub login, role, allocation %, hours/day, declared skills, PTO days), `ai_agents` (Copilot coding
agent / Claude Code Action, skills, limits), `calendar` (sprint length, first sprint start, horizon, holidays,
ceremonies), `definition_of_done`, `story_point_scale`, `hours_per_story_point`, `maintenance_capacity_pct`,
`max_story_points_per_story`, `deadlines` (prd.md requirement ids + date, hard or soft), `ai_min_recorded_outcomes`
(AI agents work in shadow mode until this many outcomes are recorded; default 20, the example uses 0).

## Flow and gates

```
prd agent ──► prd.md ─┐
architecture.md ──────┼─► task-breakdown ──► backlog/ ──[P4-G1]──► sprint-planning ──► sprint/ ──[P4-G2]──►
phase4/project.json ──┘                                                                                    │
                                    work-allocation (one sprint) ──► allocation/ ──[P4-G3]──► publish      ◄┘
architecture.md ──► infra-pipeline ──► infra/ ──[P4-G4]──► publish infra ──► CI-ready repos for work-allocation
```

| Gate (`gates.toml`) | Approves | Typical approver | After approval |
|---|---|---|---|
| P4-G1 | `backlog/backlog.json` | product owner / tech lead | `agent-engine phase4 publish backlog`; sprint-planning may run |
| P4-G2 | `sprint/sprint-plan.json` | delivery manager | `phase4 publish sprint`; work-allocation may run |
| P4-G3 | `allocation/assignments.json` | engineering manager | `phase4 publish assignments` (assignees + AI dispatch) |
| P4-G4 | `infra/intent.json`, `infra/manifest.json` | platform engineer | `phase4 publish infra` (infra PR + CI PRs; Atlantis applies after merge) |

An approval pins the sha256 of the approved files: if a file changes afterwards, the next agent and `publish`
refuse until the gate is approved again. Feedback works the engine's way: `--decision changes_requested`, then run
the same agent again with the feedback as the request (it reads its request history and changes only what is
needed). Infra runs in parallel with the other three; Work Allocation only gives tasks to AI agents for
repositories whose CI was approved at P4-G4.

## Commands

```bash
uv sync                                               # Python 3.13 env with ortools, networkx, ...
uv run agent-engine phase4 init --project-name taskflow --example taskflow    # sample inputs into outputs/taskflow/
uv run agent-engine run "Break prd.md down into a backlog." --agent task-breakdown --project-name taskflow
uv run agent-engine gate P4-G1 --project-name taskflow --decision approved --approver "Priya" --submitted-by "Rahul"
uv run agent-engine phase4 publish backlog --project-name taskflow
uv run agent-engine run "Plan the sprints." --agent sprint-planning --project-name taskflow
uv run agent-engine gate P4-G2 --project-name taskflow --decision approved --approver "Dana" --submitted-by "Rahul"
uv run agent-engine run "Assign sprint 1." --agent work-allocation --project-name taskflow
uv run agent-engine run "Set up dev, stg and prod." --agent infra-pipeline --project-name taskflow
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
  file tools, skills, write guard and lock as the built-in helper.
- `TOOLS` registers the Phase 4 tool sets (`phase4-*`); the Phase 4 code lives in `src/agent_engine/phase4/`.
- `agent-engine phase4 ...` CLI commands (init, publish, mine-profiles, schemas), which never call a model.
- The tool `infra_validate` runs fixed check commands in the sandbox image. The agent itself still has no shell
  and cannot choose a command; this is the one place Phase 4 executes programs, and it is worth confirming with
  the platform owner.

## Verified live (Claude subscription, `outputs/bookmarks-live`, small 3-requirement PRD)

| Agent | Time | Input tokens | Validator | Result |
|---|---|---|---|---|
| Task Breakdown | 9.4 min | 3.5 M | partial → fixed → success | spec-kit for 3 features in parallel subagents; 3 epics, 13 stories, 48 tasks, 26 SP, all PRD ids covered |
| Sprint Planning | 1.3 min | ~0.2 M | success | CP-SAT OPTIMAL, 2 sprints, nothing deferred, deadline met |
| Infra & Pipeline | 13.6 min | 0.3 M | success | 44 files, all 10 sandbox checks pass, risk 50, 1 infra PR + 2 CI PRs (local mode) |
| Work Allocation | 4.0 min | 1.1 M | partial → fixed → success | Timefold service, 34 tasks assigned, 2 unassigned (skill gaps), capacity respected |

Gates P4-G1..G4 were approved with `agent-engine gate` and every `phase4 publish` ran in local mode (tracker files,
PR folders). Token use is driven by deepagents re-sending context on every tool call; Task Breakdown is the most
expensive because of spec-kit's long skills.

## Not verified here

Jira, Linear and GitHub publishing, Copilot / Claude Code dispatch and GitHub pull requests are ported from the
earlier Phase 4 implementation but need credentials and were not run; `PHASE4_PR_MODE=local` and the `local`
tracker write everything as files instead.
