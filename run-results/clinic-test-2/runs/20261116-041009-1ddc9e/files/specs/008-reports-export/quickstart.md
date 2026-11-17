# Quickstart: validating Burndown report and CSV export

## Prerequisites

- 001 (auth, boards, membership) and 002 (tasks with optional `story_points`, columns) are deployed in the environment.
- Migration for this feature applied (`migrations/`).
- Env: `FEATURE_BURNDOWN=true`, `FEATURE_CSV_EXPORT=true` (default off in prod).
- Two users on one board (one manager, one member) and a third user who is not on the board; a second board with tasks.

## Scenario 1: Sprint (User Story 1)

1. As the manager, create a sprint with start today and end in 9 days: expect 201 and it appears as `current`.
2. Create an overlapping sprint: expect 409. Send an end date before the start: expect 422.
3. As the plain member, create a sprint: expect 403. As the outsider, list sprints: expect 403.

## Scenario 2: Burndown (User Story 2)

1. Add tasks worth 20 story points on the board; move 5 points to Done.
2. Open the report as a member: expect today's `remaining_points` = 15 and later days null.
3. Run the daily job command, then check the stored record for the day.
4. Remove the record of an earlier day: expect the report to carry forward the last known value.
5. Open a board without a sprint: expect the empty state.
6. In the web app, tab to the chart and to the table with the keyboard only; both show the same values.
7. Set `FEATURE_BURNDOWN=false`: expect 404 and no report link.

## Scenario 3: CSV (User Story 3)

1. Create a task titled `=1+1`, one with a comma and a quote in the description, and one with a line break.
2. Export as a member: expect a header plus one row per task and no tasks from the second board.
3. Open the file in a spreadsheet: expect no formula to run and the other texts to read back unchanged.
4. Export an empty board: expect the header only. Export as the outsider: expect 403.
5. Set `FEATURE_CSV_EXPORT=false`: expect 404 and no Export button.

## Automated checks

- API: `pytest tests/` (unit, integration, contract folders for this feature).
- Web: the repo's web test run for `src/features/reports/`.
