# Assignments — BrightSmile Booking Sprint 1 (v1)

> ## NOT READY FOR GATE P4-G3: nothing to approve
>
> **The empty task table below is not a failure to assign.** The sprint plan (`sprint/sprint-plan.md`, v1) is **INFEASIBLE**. It commits **0 stories to sprint 1** (and to every other sprint). All 83 stories sit in its **Deferred** list as `deadline_infeasible`. With no sprint 1 tasks, the allocation tool had nothing to assign, so `assignments` is empty.
>
> **Gate P4-G3 cannot be approved yet.** There is no allocation to review until the sprint plan is feasible and sprint 1 has stories. Please do not read this file as a ready allocation.
>
> ### Impact on the team in sprint 1
> All 10 workers are fully idle, with 0 planned hours against their capacity:
> - 8 humans: 12.2 to 48.6 h each (Arjun, Meera, Sanjay, Priya and Kavya 48.6 h; Rohan 24.3 h; Neha 27.0 h; Vikram 12.2 h).
> - 2 AI agents (claude-code, copilot): 36 h each.
>
> ### Why the plan is infeasible (from the sprint plan)
> - Release 1 must-haves (DL-1, hard deadline 2027-02-22) are about 302 SP.
> - Sprints 1-7 offer about 236 SP at P50 and 189 SP at P85. That leaves a **capacity shortfall of about 66 SP at P50**.
> - The capacity figures are a cold-start estimate with low confidence.
> - This shortfall is in the sprint plan's story points. The allocation tool's own `skill_gaps` and `capacity_shortfall` are empty only because it received no tasks. It has not checked skills or hours for any task. Skill coverage of the real work is still unchecked.
> - No repository is marked CI-ready yet (`ci_ready_repos` is empty in `problem.json`). That also blocks AI eligibility once there are tasks.
>
> ### What has to happen (upstream, not in allocation)
> 1. **Delivery manager or approver:** choose **OPT-1 (`capacity:x1.3`)**, the only verified-feasible option in the sprint plan, or another way to close the ~66 SP gap. OPT-1 would fit about 307 SP at P50 and leave 8 stories unplanned, but sprints would likely still run above P85.
> 2. **Confirm the 1 March go-live date.**
> 3. **Sprint planning** re-runs with the matching `changes` string and produces a feasible plan with stories in sprint 1.
> 4. **Work allocation** then re-runs for sprint 1. It will judge AI eligibility, solve, explain each assignment, and report any skill gaps or shortfalls for real tasks. Then P4-G3 can be reviewed.
>
> ### Where to trace the empty result
> - `sprint/sprint-plan.md`: the top summary (INFEASIBLE, recommended OPT-1, "Need from you") and the **Deferred** section listing all 83 stories as `deadline_infeasible`.
> - `allocation/assignments.json`: `assignments`, `unassigned`, `eligibility` and per-task explanations are empty because no tasks were supplied, not because tasks were rejected.
> - Pending decision: OPT-1 or another option, plus the go-live confirmation (above).

Solver: local_cpsat · SOLVING_COMPLETED · objective=-0

| Worker | Kind | Planned h | Capacity h |
|---|---|---|---|
| Arjun | human | 0.0 | 48.6 |
| Meera | human | 0.0 | 48.6 |
| Sanjay | human | 0.0 | 48.6 |
| Priya | human | 0.0 | 48.6 |
| Kavya | human | 0.0 | 48.6 |
| Rohan | human | 0.0 | 24.3 |
| Neha | human | 0.0 | 27.0 |
| Vikram | human | 0.0 | 12.2 |
| claude-code | ai_agent | 0.0 | 36.0 |
| copilot | ai_agent | 0.0 | 36.0 |

| Task | Title | Assignee | Hours | Why | Runner-up |
|---|---|---|---|---|---|

_No tasks in sprint 1: the sprint plan is INFEASIBLE and defers all 83 stories (`deadline_infeasible`). See the note at the top. Re-run allocation after sprint planning is re-run with a feasible option._
