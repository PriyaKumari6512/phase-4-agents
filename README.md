# agent-engine

Runs a team's AI agents (PRD Writer, UX Flow, Test Case, ...) on one shared harness.

**An agent is a folder, not code.** Each agent lives in `agents/<name>/` as a
`system_prompt.md` (what it does, in plain English) and an `agent.toml`
(model, tools, who checks its work). Its validator sits next to it in
`agents/<name>/validator/`. One person owns one folder, so the team builds
agents in parallel without touching each other's files.

Split out of `agent-harness` (the backend code agent), keeping only what a
non-coding agent needs, and with no shell at all.

```
agent-engine/
  agents/                     # one folder per agent  <- the team works here
    prd/
      agent.toml              # PRD Writer
      system_prompt.md
      validator/
        agent.toml            # Requirements Validator (judges the PRD)
        system_prompt.md
    task-breakdown/           # PDLC Phase 4, agent 1 (spec-kit skills + subagents)
    sprint-planning/          # PDLC Phase 4, agent 2
    work-allocation/          # PDLC Phase 4, agent 3
    infra-pipeline/           # PDLC Phase 4, agent 4 (golden-path catalog in knowledge/)
  examples/requirements/      # sample client requirements to try
  examples/phase4/            # sample Phase 4 project inputs
  services/                   # optional containers for Phase 4 (Timefold solver, IaC sandbox, Atlantis image)
  src/agent_engine/           # the engine (platform owner works here)
  src/agent_engine/phase4/    # Phase 4 tools, contracts and publishing
  tests/
  outputs/                    # created on first run: one folder per project
  logs/                       # created on first run
```

**Phase 4 (Task, Sprint & Environment Setup)** — four agents that turn a PRD and an architecture into a
backlog, a sprint plan, task assignments and infrastructure, each behind a human gate. Inputs, outputs, gates and
commands: [docs/PHASE4.md](docs/PHASE4.md).

---

## 1. Setup

Needs [uv](https://docs.astral.sh/uv/) and Python 3.13 (uv installs it).

```bash
cd agent-engine
cp .env.example .env
```

Fill in **one** model provider in `.env` (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`
or `OPENROUTER_API_KEY`). The variable names are the same as `agent-harness`,
so its `.env` can be copied as-is. Values with spaces must be quoted
(`SDLC_AGENT_GIT_USER_NAME="Xccelera Generator"`).

```bash
uv sync
```

Check it works:

```bash
uv run python -m pytest -q
uv run agent-engine list
```

`list` should print `prd` and `prd/validator`, with their inputs and outputs.

**Windows notes**

- If `uv sync` fails with a hardlink error (common on Desktop/OneDrive
  folders), run `UV_LINK_MODE=copy uv sync`.
- If `uv run agent-engine` is blocked by Windows Application Control, use
  `uv run python -m agent_engine` instead, with the same arguments.

**WSL notes**

Don't share the Windows `.venv` with WSL. Give WSL its own environment:

```bash
export UV_PROJECT_ENVIRONMENT=$HOME/.venvs/agent-engine
uv sync
```

---

## 2. Run the example

The repo ships a sample requirement: a gym chain (FitZone) that wants an
online membership app. See `examples/requirements/gym-membership.md`.

```bash
uv run agent-engine run "Client requirement: $(cat examples/requirements/gym-membership.md)" --agent prd --project-name gym-app
```

It takes about 2 minutes. What happens:

1. The request is saved to `outputs/gym-app/requests.md` as **Request 1**.
2. The **PRD Writer** (`agents/prd`) writes `outputs/gym-app/prd.md`.
3. Its **validator** (`agents/prd/validator`) reads `requests.md` and `prd.md`
   and returns a **verdict**.
4. If the verdict has gaps, they go back to the PRD Writer for a fix, then
   the validator checks again (up to `max_fix_loops` times).
5. A summary is printed and saved to `outputs/gym-app/report.json`.

Example end of output:

```
=== prd/validator verdict (attempt 1): success ===
All seven sections are present; every client need maps to a user story and
functional requirement ...

Status: success  |  time: 108s
Pass write  prd            strong anthropic:claude-sonnet-5-5
Pass verify prd/validator  strong anthropic:claude-sonnet-5-5
Tokens claude-sonnet-5-5: input=67268 output=9985 total=77253
Report: outputs/gym-app/report.json
```

### What a verdict means

The validator does not write anything. It judges the output and answers in a
fixed format:

| Field | Meaning |
|---|---|
| `satisfied` | `true` = output is complete and correct. The run stops. |
| `status_so_far` | `success`, `partial` (exists but has gaps) or `fail` (missing / empty). |
| `gaps` | Concrete fixes, e.g. "US-4 has no acceptance criteria". Sent back to the writer. |
| `summary` | Two or three sentences on what was checked. |

### Client feedback: run the same agent again

Same `--agent`, same `--project-name`, feedback as the request:

```bash
uv run agent-engine run "Client feedback: send reminders on WhatsApp only, no SMS. Add a 7-day free trial plan." --agent prd --project-name gym-app
```

The feedback is saved as **Request 2**. The PRD Writer reads its previous
`prd.md` and changes only what the feedback needs; the validator checks the
PRD against **every** request (the original requirement and the feedback),
so nothing from Request 1 gets lost.

### Where everything lands

| Path | What |
|---|---|
| `outputs/<project>/prd.md` | The agent's output |
| `outputs/<project>/requests.md` | Every request for this project, oldest first |
| `outputs/<project>/report.json` | The latest run: status, verdict, model used per pass, time, tokens, files it created / changed / deleted |
| `outputs/<project>/runs/<job-id>/` | Every run: its `report.json` and, under `files/`, a copy of each file it created or changed, so earlier versions are never lost |
| `outputs/<project>/logs/<job-id>.log` | This run's log |
| `logs/deepagent.log` | Full transcript of every agent |
| Langfuse (`LANGFUSE_HOST`) | Every model call, tokens and cost, if Langfuse is configured |

### Client files (PDF, screenshots, Word, ...)

When the client sends files instead of text, add them to the project first:

```bash
uv run agent-engine add-inputs "FitZone RFP.pdf" brd.docx whiteboard.png --project-name gym-app
```

```
Round 1: outputs/gym-app/inputs/round-1
  FitZone RFP.pdf                          read directly
  brd.docx                                 converted to brd.docx.md
  whiteboard.png                           read directly
```

Each call starts a new round (`round-1`, `round-2`, ...), e.g. the client's
answers to your questions; `--round N` adds to an existing one. Agents can
read `inputs/` but never change it, and an uploaded file is never
overwritten.

| File | What agents read |
|---|---|
| PDF, PNG, JPG, GIF, WebP | The file itself: the model sees the pages / image |
| Text (`.txt`, `.md`, `.csv`, transcripts, ...) | The file itself |
| Word `.docx`, Excel `.xlsx`, PowerPoint `.pptx`, email `.eml` / `.msg` | A Markdown copy next to it (`brd.docx.md`) |
| Old Office (`.doc`, `.xls`, `.ppt`), HEIC, audio, video | Nothing: the command says what to upload instead |

---

## 3. Add a new agent

Copy the PRD agent and edit the two files:

```bash
cp -r agents/prd agents/ux-flow
```

```
agents/ux-flow/
  agent.toml
  system_prompt.md          # what the UX Flow agent does
  validator/
    agent.toml              # keep returns = "verdict"
    system_prompt.md        # what to check
```

```toml
# agents/ux-flow/agent.toml
description = "UX Flow: turns a signed-off PRD into user flows."
model = "strong"
filesystem = ["ls", "read_file", "write_file", "edit_file", "glob", "grep"]
verifier = "ux-flow/validator"
max_fix_loops = 2

[input]
description = "A signed-off PRD for the project."
files = ["prd.md"]              # produced by the prd agent

[output]
description = "User flows for every Must user story."
files = ["ux-flows.md"]
```

Run it with `--agent ux-flow`. No Python needed. A typo in any key, tool or
model name fails before any model call, with a message naming it.

**TOML gotcha:** every plain key (`model`, `verifier`, ...) must come
*before* the first `[input]` / `[output]` table. A key written after
`[output]` belongs to that table, and the engine rejects it
("unknown key 'verifier' in [output]").

### Input and output

`[input]` and `[output]` say what the agent takes and what it produces.
File paths are inside the project's output folder (`outputs/<project>/`).

- **Before the run:** if a declared input file is missing, the engine stops
  with no model call and tells you which agent produces it:
  `ERROR: ux-flow needs outputs/gym-app/prd.md, which doesn't exist yet. Run --agent prd on this project first.`
- **During the run:** the agent is told which files to read and which to
  produce.
- **After the run:** if a declared output file wasn't created, the run fails
  without paying for the validator.
- `uv run agent-engine list` shows every agent's inputs and outputs, so the
  chain between agents is visible:

  ```
  prd                      PRD Writer: turns a client requirement into a PRD.
                           in: (request only)  ->  out: prd.md
  ux-flow                  UX Flow: turns a signed-off PRD into user flows.
                           in: prd.md  ->  out: ux-flows.md
  ```

Tips for the prompt:

- Say exactly which file to write (`/outputs/<project-name>/ux-flows.md`).
- Say what to do if that file already exists (read it and improve it).
- List the required sections, so the validator can check them.
- Tell it never to invent facts: unknowns go into assumptions/open questions.

### Human approval gates

A gate is a point where a named person approves a set of files before the
next agents may use them. Gates are defined once in `gates.toml`:

```toml
[G1]
description = "Scope: the requirements and scope documents"
files = ["requirements/register.md", "scope/scope.md"]
```

An agent that must wait for G1 lists its approval file as an input:

```toml
[input]
files = ["scope/scope.md", "gates/G1.approved.json"]
```

Record a decision (the UI's API will do this later):

```bash
uv run agent-engine gate G1 --project-name gym-app --decision approved \
    --approver "Priya" --approver-role "Delivery Manager" --submitted-by "Rahul"
```

- `--decision`: `approved`, `changes_requested` or `rejected`. Every
  decision is appended to `gates/history.jsonl`.
- `approved` writes `gates/G1.approved.json`, which pins the exact version
  (sha256) of every file it approved. Any other decision removes it.
- The approver can't be the person who submitted the work (maker-checker).
- The waiting agent refuses to run until G1 is approved, and again if an
  approved file changes afterwards, until G1 is approved again.
- Agents can read `gates/` but never write it.

### `agent.toml` reference

| Key | Meaning |
|---|---|
| `description` | One line, shown by `list`. |
| `model` | `"strong"` (default), `"fast"`, or a list like `["fast", "strong"]`. |
| `filesystem` | File tools the agent gets: `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`. Omitted = all. Validators get read-only ones. |
| `tools` | Extra tools by name from the registry (see section 5). |
| `knowledge` | A folder inside the agent with reference docs (templates, standards), readable at `/knowledge/`. |
| `returns = "verdict"` | Makes this agent a judge: it replies with a verdict instead of text. Every validator needs it. |
| `verifier` | The judge that checks this agent, e.g. `"prd/validator"`. |
| `max_fix_loops` | How many fix passes the agent gets after a failed verdict. |
| `request_history` | `"project"` (default): the agent and its validator read the project's shared `requests.md`. `"agent"`: the agent keeps its own `requests/<agent>.md`, so requests made to other agents on the same project don't count as its requirements. |
| `[input]` `description`, `files` | What the agent takes: the request it expects, and files from other agents it needs. |
| `[output]` `description`, `files` | What the agent produces. Checked after the run. |

---

## 4. Models

`"strong"` and `"fast"` are tiers. Which real model each one is comes from
`.env`, once for every agent:

```
SDLC_AGENT_STRONG_MODEL=anthropic:claude-sonnet-5-5
SDLC_AGENT_FAST_MODEL=anthropic:claude-haiku-4-5-20251001
```

Set both or neither; without them the provider's defaults are used. Changing
a model for all agents is one line here, not 40 edits.

**Rule of thumb:** `strong` for agents that think, write or judge (PRD,
architecture, security, every validator); `fast` for simple, repetitive
work (release notes, bug triage).

### Switching models inside one agent

```toml
model = ["fast", "strong"]
```

This is an escalation order. The first pass runs on `fast`. The next pass
moves to `strong` when the verdict is not satisfied, or when the model call
fails (rate limit, outage). Each pass's model is printed and stored in
`report.json` under `passes`.

Measure before using it: on the gym example the PRD Writer on
`["fast", "strong"]` needed two fix passes and about 14x the tokens of plain
`"strong"`. It pays off only where `fast` usually passes first time.

---

## 5. Tools

Agents get the built-in file tools (section 3). An extra tool (Jira, Figma,
a scanner) is Python written once by the platform owner, then picked by name
in any `agent.toml`. The registry is `TOOLS` in `src/agent_engine/agent.py`
(empty today).

1. Write the tool, e.g. `src/agent_engine/tools/jira.py`:

   ```python
   import os

   import httpx
   from langchain_core.tools import tool


   @tool
   def jira_get_issue(issue_key: str) -> str:
       """Fetch a Jira issue's summary, status and description, e.g. issue_key="FIT-12"."""
       r = httpx.get(
           f"{os.environ['JIRA_URL']}/rest/api/3/issue/{issue_key}",
           auth=(os.environ["JIRA_EMAIL"], os.environ["JIRA_API_TOKEN"]),
           timeout=30,
       )
       if r.status_code != 200:
           return f"ERROR: Jira returned {r.status_code} for {issue_key}"
       f = r.json()["fields"]
       return f"{issue_key}: {f['summary']} [{f['status']['name']}]"


   def get_tools() -> list:
       return [jira_get_issue] if os.environ.get("JIRA_URL") else []
   ```

2. Register it: `TOOLS = {"jira": jira.get_tools}`.
3. Use it: `tools = ["jira"]` in the agent's `agent.toml`.

The docstring is what the model reads to decide when to call the tool, so
write it clearly. Return error text instead of raising. Credentials stay in
the tool's code and `.env`; the agent only sees the arguments and the result.
Keep read and write tools separate, and give validators read tools only.

---

## 6. Safety, the same for every agent

- **No shell.** The backend cannot run commands, so no agent (nor the helper
  subagent deepagents adds) gets an `execute` tool, and nothing can read API
  keys from the environment. A test checks this for every agent.
- **Writes only under `/outputs/`**, and never inside a project's `inputs/`
  (uploaded client files) or `gates/` (human approvals), enforced in code
  (`guardrails.py`).
- **Agent names can't escape `agents/`** (`..` and absolute paths are refused).
- **One global write lock** (`locking.py`) and automatic context compaction.
- **The helper subagent gets the same rules.** deepagents' `task` helper is
  given the agent's own file tools, the write guard and the lock; a test
  checks this for every agent.

## 7. Known limits

- Agents run one at a time; there is no orchestrator chaining PRD → design →
  code. Gate decisions are recorded by hand with `agent-engine gate` until
  the UI's API does it, and re-running with feedback is manual.
- No per-run token budget. Each graph pass has a configurable 1800-second
  deadline; sandbox commands and validation have separate bounded budgets.
  Watch `report.json` / Langfuse. Cancellation cannot forcibly stop an already
  running Python worker thread.
- An agent that makes many small edits re-sends its whole context each time,
  which is the main cost driver (see the escalation numbers above).

## 8. Tests

```bash
uv run python -m pytest -q
```

They need no API key and make no model calls.

## 9. Performance diagnostics

`AGENT_ENGINE_PERF=1` records structured timing evidence (model calls, tools,
helpers, solvers, sandbox commands, HTTP, approvals) as JSON Lines outside the
project folders; `agent-engine perf summarize --session <id>` turns it into a
report offline. Off by default. See [docs/PERF_DIAGNOSTICS.md](docs/PERF_DIAGNOSTICS.md)
and, for a benchmark of a real project, [docs/PERF_BENCHMARK_RUNBOOK.md](docs/PERF_BENCHMARK_RUNBOOK.md).

The reliability fixes, validation evidence, remaining gaps, and checkout/run
instructions are in [docs/FIXES_AND_VALIDATION.md](docs/FIXES_AND_VALIDATION.md).
After generated workflows are merged and run, `agent-engine phase4 check-ci
--project-name YOUR-PROJECT` records actual CI readiness. `agent-engine phase4
reconcile --project-name YOUR-PROJECT` refreshes coding-agent outcomes. Neither
command starts coding jobs or applies infrastructure.
