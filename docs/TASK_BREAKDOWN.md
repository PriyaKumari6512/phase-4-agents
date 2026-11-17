# Task Breakdown (PDLC Phase 4, step 4.1)

Task Breakdown takes the stories the product team approved at Gate 2 and splits each into the technical tasks a
team builds: FE, BE, DB, DevOps and QA, each with an estimate, acceptance criteria and dependencies. The Tech Lead
reviews the result at gate P4-G1. Stories, their acceptance criteria and their priorities are never rewritten.

Code: `src/agent_engine/phase4/story_import.py`, `task_breakdown.py`, `backlog.py`; instructions:
`agents/task-breakdown/system_prompt.md` (generation) and `agents/task-breakdown/validator/system_prompt.md` (review).

## Inputs

| Input | Where it comes from |
|---|---|
| `phase4/stories.json` | The approved stories, read from Jira with read-only requests (`agent-engine phase4 import-stories`, or automatically by the orchestrator). See [PHASE4.md](PHASE4.md) for `JIRA_STORY_JQL` and related settings. |
| `gates/G3A.approved.json`, `gates/G3B.approved.json` | Human approval of the designs (`designs/designs.md`) and the architecture (`architecture.md`). Task Breakdown does not run without both, or after either file changed. |
| `architecture.md`, `prd.md` | The approved architecture, and the PRD that defines the A-, PD-, NFR- and FR- ids stories refer to. |
| `phase4/project.json` | Definition of Done, story point scale, hours per point, code repositories. |
| `phase4/history.json` (optional) | Resolved tickets, offered as analogies for estimates. |

## How it runs

1. **One structured call per story.** The model returns the story's tasks: discipline, title, description, 1–3
   testable criteria, which story acceptance criteria each task covers, file paths and repo only where the
   architecture defines them, hours (at most 16), in-story dependencies, skills, confidence, open questions.
   The shared part of every call (instructions, settings, skill list, full architecture and PRD) is one cached
   prompt prefix; the first call runs alone so the others read the cache.
2. **Checks on every answer**, in code: every story acceptance criterion covered, ids and dependencies valid and
   acyclic, hours within limits, real repos and skill tags. A failing answer is retried once with the errors.
3. **One cross-story call** over a compact index of all stories and tasks: dependencies between stories' tasks
   (added at confidence 0.6 or more, otherwise an open question) and the same work planned in two stories (merged
   under one owner at 0.8 or more, same discipline, never QA). Jira "blocks" links become story dependencies.
4. **Assembly in code**: ids `<story key>-Tnn`, the project's Definition of Done on every task, story points kept
   from Jira or derived from the task hours, requirement coverage, story waves and the critical path.

Every result is retained under `.engine-task-breakdown/` by an exact digest of what produced it. An unchanged story
is never sent again; a reviewer request that names story keys regenerates only those stories.

## Validation

1. **Deterministic checks** (`backlog.py`) always run. Blocking: a missing approved story, a story without tasks, a
   task without discipline, criteria or skills, an uncovered story acceptance criterion, a task over 16 h, dependency
   cycles among human/tracker links, stale inputs. Warnings: effort that points to a different size than the Jira
   points, vague task criteria, approved stories above the size limit, PRD ids no imported story traces, possible
   duplicates, open questions.
2. **A light model review** looks only at what the checks flag (low-confidence hours, vague criteria, effort
   mismatches). Nothing flagged means no call. Blocking findings go to the fix pass; warnings go to the Tech Lead.
3. **Fix**: only the affected stories are sent back, with the findings. A failed check escalates the fix pass to
   the frontier model (`model = ["strong", "frontier"]`, at most 2 rounds). A repair that changes nothing stops the
   run as partial for the Tech Lead.

## Output and publishing

`backlog/backlog.json` and `backlog/backlog.md` (stories with their tasks, the issues found and the open questions).
After P4-G1, `agent-engine phase4 publish backlog` creates the tasks as **Jira sub-tasks of the existing stories**
and links dependent tasks; epics and stories are never created, edited, linked or closed
([PIPELINE_JIRA.md](PIPELINE_JIRA.md)).

## Limits

The shared stage budget still applies: `AGENT_ENGINE_BREAKDOWN_MAX_CALLS`, `..._MAX_INPUT_TOKENS`,
`..._MAX_OUTPUT_TOKENS`, `..._TIMEOUT_SECONDS`. Story calls run with `AGENT_ENGINE_HELPER_CONCURRENCY` (default 9),
reviews with `AGENT_ENGINE_BREAKDOWN_REVIEW_CONCURRENCY` (default 4).
