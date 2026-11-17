# Sprint Planning (PDLC Phase 4, step 4.2)

Sprint Planning places the approved stories into sprints by priority, dependencies, capacity and release deadlines,
writes a goal for each sprint and a release plan, and hands the result to the Scrum Master / Engineering Manager at
gate P4-G2. Stories move as a whole (their sub-tasks follow them in Jira).

Code: `src/agent_engine/phase4/sprint.py` (planning), `sprint_model.py` (CP-SAT), `capacity.py`, `calendars.py`,
`sprint_planning.py` (the stage), `story_import.py` (Jira history). Instructions:
`agents/sprint-planning/system_prompt.md` and `agents/sprint-planning/validator/system_prompt.md`.

## Inputs

| Input | Where it comes from |
|---|---|
| `backlog/backlog.json` (approved at P4-G1) | Task Breakdown: stories with points, dependencies, `release` (fix version) and `rank` (Jira Rank), plus the roadmap (`releases`, in order, with Jira release dates). |
| `phase4/project.json` | Team, calendar, holidays, PTO, ceremonies, maintenance share, `deadlines` (by requirement id) and `release_deadlines` (fallback date per release; a Jira version date wins). |
| `phase4/history.json` (optional) | Velocity: with Jira, refreshed from the board's last 12 closed sprints (`source: "jira"`); a hand-made file is never overwritten. Without enough history, capacity is a stated low-confidence estimate. |
| A reviewer's request (optional) | Pins ("keep GR-30 out", "GR-12 in sprint 1") or a chosen option ("we choose OPT-2"). |

Design approval is project-wide: once G3A is approved (before Task Breakdown), every imported story counts as
design-approved.

## How it runs

1. **Priority, in code:** roadmap release (MVP before R2 ...), then MoSCoW, then Jira Rank — the order Phase 2
   approved. Nobody re-scores stories. Each story's value to the solver is points × weight (100 down to 1), so a
   higher-priority point is always worth more than a lower-priority one.
2. **Capacity:** sprint windows from the calendar, availability after holidays and PTO, P50/P85 story points per
   sprint from velocity history.
3. **Packing (CP-SAT):** capacity at P50 is hard and load above P85 is penalized; dependencies (including those
   between stories' tasks), dated releases and requirement deadlines (soft unless marked hard), must-haves, pins and
   stability against the previous plan. When nothing fits, the solver names the conflicting constraints and offers
   options it verified (move a deadline, treat it as soft, downgrade a must-have, unpin, add capacity).
4. **Release plan:** per release its stories and points, last sprint and planned finish, P50/P85 forecast dates,
   deadline and status (on track, late, incomplete, no deadline).
5. **One small-model call** writes a goal per sprint, plain deferral explanations, a short summary and, when the
   plan is infeasible, the recommended option. The answer is checked (goals for every sprint with stories, no
   invented sprints or deferrals, an infeasible plan must recommend one of its options) and retried once.
   A reviewer's request is first turned into pins or an option choice by one more small call, checked against
   real story ids, the sprint range and the plan's own options.

## Validation

1. **Deterministic checks** (`sprint.check`): capacity, dependency order, every story planned or deferred once,
   goals present, stale backlog or settings, hard release deadlines (problems); load above P85, late or incomplete
   releases, P85 forecasts past a deadline, deferred must-haves, an earlier-release must-have deferred while later
   releases are planned (warnings). An infeasible plan waits for the approver's choice.
2. **A light review** only of text the rules flag: goals that name story keys, repeat titles or list several
   outcomes; deferral explanations that are empty, generic or do not match their reason. Nothing flagged: no call.
3. **Fix:** re-plan and rewrite the text with the findings, escalated to the mid-tier model
   (`model = ["fast", "strong"]`, at most 2 rounds); a fix that changes nothing stops for the Scrum Master.

## Output and publishing

`sprint/sprint-plan.json` and `sprint/sprint-plan.md`: sprints with stories, goals and capacity, the release plan,
deferrals with reasons, the forecast, the approved priority order, assumptions and, when infeasible, the options.
After P4-G2, `agent-engine phase4 publish sprint` moves the stories into Jira sprints, **reusing sprints that already
exist on the board** (same start date, an active sprint covering the start, same name, then undated future sprints
in order) and filling only their empty dates and goal ([PIPELINE_JIRA.md](PIPELINE_JIRA.md)).
