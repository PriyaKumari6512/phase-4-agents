# Tasks: Burndown report and CSV export

**Input**: Design documents from `/specs/008-reports-export/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/reports-api.md, quickstart.md. Depends on 001-platform-foundation (auth, membership, base migration setup) and 002-tasks-board (task model with optional `story_points`, columns, board UI).

**Tests**: Included. The constitution requires tests first for business logic and an independent test per story.

**Organization**: Tasks are grouped by user story. Paths are relative to the repository named in each task: taskflow-api (`app/`, `migrations/`, `tests/`), taskflow-web (`src/`), taskflow-infra (`k8s/`). Paths marked (A) are assumptions from the implementation contract.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story the task belongs to (US1, US2, US3)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Flags and test folders for this feature

- [ ] T001 Add settings `FEATURE_BURNDOWN` and `FEATURE_CSV_EXPORT` (read from env `FEATURE_<NAME>`, default off) to `app/core/config.py` in taskflow-api
- [ ] T002 [P] Create test packages `tests/unit/reports/__init__.py`, `tests/integration/reports/__init__.py` and `tests/contract/reports/__init__.py` in taskflow-api

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Sprint data model shared by User Story 1 and User Story 2

**CRITICAL**: No sprint or burndown work can begin until this phase is complete

- [ ] T003 Create the Sprint model in `app/models/sprint.py` with fields name (text, "1 to 100 characters"), start_date (date, NOT NULL), end_date (date, NOT NULL, CHECK end_date >= start_date), board_id (foreign key to boards, NOT NULL, indexed), created_by, created_at, updated_at
- [ ] T004 [P] Create the SprintBurndownRecord model in `app/models/sprint_burndown_record.py` with primary key (sprint_id, day), remaining_points (integer, NOT NULL, ">= 0"), total_points (integer, NOT NULL, ">= 0"), recorded_at, and ON DELETE CASCADE to sprints
- [ ] T005 Create the Alembic migration for `sprints` and `sprint_burndown_records` (and the overlap backstop constraint where `btree_gist` is allowed) in `migrations/versions/008_sprints_and_burndown_records.py` (depends on T003, T004)
- [ ] T006 [P] Create pydantic schemas SprintCreate, SprintUpdate and SprintRead in `app/schemas/sprint.py` (name 1 to 100 characters, ISO dates, end_date not before start_date)

**Checkpoint**: Sprint tables and schemas ready

---

## Phase 3: User Story 1 - Manager sets a sprint on a board (Priority: P1)

**Goal**: A manager creates and edits a sprint (name, start date, end date) on a board; members can read it. (source: FR-8, US-8)

**Independent Test**: Create a sprint as manager, read it back as member, edit its end date, get 409 on overlap, 422 on bad dates, 403 for a non-manager and for a non-member, 404 when `FEATURE_BURNDOWN` is off.

### Tests for User Story 1

- [ ] T007 [P] [US1] Unit tests for sprint validation, overlap detection and current-sprint selection in `tests/unit/reports/test_sprint_service.py`
- [ ] T008 [P] [US1] Integration and contract tests for POST/PATCH/GET sprint endpoints (201, 403 member, 403 outsider, 409, 422, flag off 404) in `tests/integration/reports/test_sprints_api.py`

### Implementation for User Story 1

- [ ] T009 [US1] Implement SprintService (create, update, list, current sprint by UTC date, overlap check in one transaction) in `app/services/sprint_service.py` (depends on T003, T006, T007)
- [ ] T010 [US1] Implement the sprint router with `/api/v1/boards/{board_id}/sprints` endpoints, `FEATURE_BURNDOWN` guard (404 when off), board-membership check from 001 and manager-only writes in `app/api/sprints.py`
- [ ] T011 [US1] Register the sprint router in `app/main.py` (depends on T010)
- [ ] T012 [P] [US1] Add sprint API client functions (list, create, update) in `src/api/reports.ts` in taskflow-web
- [ ] T013 [US1] Build the keyboard-accessible SprintForm with labelled fields and inline validation messages in `src/features/reports/SprintForm.tsx` (depends on T012)
- [ ] T014 [P] [US1] Component test for SprintForm validation and keyboard submit in `src/features/reports/SprintForm.test.tsx`

**Checkpoint**: Sprints can be managed through the API and form

---

## Phase 4: User Story 2 - Manager reads the burndown report (Priority: P2)

**Goal**: A board member sees remaining story points per day of the current sprint, as a chart and an equivalent table, using the keyboard only. (source: FR-8, US-8)

**Independent Test**: With a sprint and tasks worth 20 points of which 5 are Done, the report shows 15 remaining today; missing days carry forward; a board without a sprint shows the empty state; a non-member is refused. Assumption: only Done counts (open question Q1).

### Tests for User Story 2

- [ ] T015 [P] [US2] Unit tests for remaining-points calculation (null points count 0, Done only), carry-forward of missing days, empty future days and no-sprint case in `tests/unit/reports/test_burndown_service.py`
- [ ] T016 [P] [US2] Integration and contract tests for `GET /api/v1/boards/{board_id}/reports/burndown` (member 200, outsider 403, no sprint, flag off 404, other boards' tasks excluded) in `tests/integration/reports/test_burndown_api.py`
- [ ] T017 [P] [US2] Integration test for the daily snapshot job (writes the record for the day, upsert is idempotent, skips boards without a current sprint) in `tests/integration/reports/test_burndown_snapshot_job.py`

### Implementation for User Story 2

- [ ] T018 [P] [US2] Create the BurndownResponse schema (days with day, remaining_points, total_points, nullable for future days, `counts_done_only`) in `app/schemas/burndown.py`
- [ ] T019 [US2] Implement BurndownService (live remaining points for today, upsert of today's record, carry-forward, empty future days) in `app/services/burndown_service.py` (depends on T004, T009, T015, T018)
- [ ] T020 [US2] Implement the burndown router `GET /api/v1/boards/{board_id}/reports/burndown` with `FEATURE_BURNDOWN` guard and board-membership check in `app/api/reports.py` (depends on T019)
- [ ] T021 [US2] Register the reports router in `app/main.py` (depends on T011, T020)
- [ ] T022 [US2] Implement the daily snapshot job entry point that records the day's remaining points for each board with a current sprint in `app/worker/jobs/burndown_snapshot.py` (depends on T017, T019)
- [ ] T023 [P] [US2] Add the daily CronJob that runs the worker image with the snapshot job command in `k8s/burndown-snapshot-cronjob.yaml` in taskflow-infra (depends on T022)
- [ ] T024 [US2] Add the burndown API client function in `src/api/reports.ts` in taskflow-web (depends on T012)
- [ ] T025 [P] [US2] Build BurndownChart as an SVG line chart with an accessible name and focusable data points in `src/features/reports/BurndownChart.tsx`
- [ ] T026 [P] [US2] Build BurndownTable with the same per-day values as the chart in `src/features/reports/BurndownTable.tsx`
- [ ] T027 [US2] Build BurndownPage with chart, table, empty state when no sprint is set, the SprintForm for managers, and a note that only the Done column counts, in `src/features/reports/BurndownPage.tsx` (depends on T013, T024, T025, T026)
- [ ] T028 [US2] Add the report route and a "Burndown" link in the board header, shown only when the API does not answer 404 for the feature, in `src/features/reports/routes.tsx` and `src/features/board/BoardHeader.tsx` (A, header owned by 002-tasks-board) (depends on T027)
- [ ] T029 [P] [US2] Component tests for BurndownPage, chart/table parity, empty state and keyboard-only navigation in `src/features/reports/BurndownPage.test.tsx`

**Checkpoint**: Burndown report works end to end

---

## Phase 5: User Story 3 - Manager exports board data as CSV (Priority: P3)

**Goal**: A board member downloads a CSV with one row per task and a column for every task field, safe for spreadsheets and limited to that board. (source: FR-9, US-9)

**Independent Test**: Export a board with awkward text (comma, quote, line break, leading `=`); verify row count, quoting, neutralised formula cells, no tasks from another board, header-only for an empty board, 403 for an outsider, 404 when `FEATURE_CSV_EXPORT` is off.

### Tests for User Story 3

- [ ] T030 [P] [US3] Unit tests for CSV quoting, UTF-8 output and formula neutralising of `=`, `+`, `-`, `@`, tab and carriage return in `tests/unit/reports/test_csv_export_service.py`
- [ ] T031 [P] [US3] Integration and contract tests for `GET /api/v1/boards/{board_id}/export/csv` (row count, all columns, cross-board isolation, empty board, outsider 403, flag off 404, 10,000 tasks complete) in `tests/integration/reports/test_export_api.py`

### Implementation for User Story 3

- [ ] T032 [US3] Implement CsvExportService that streams rows filtered by board_id, takes columns from the task model's field list, and neutralises formula cells, in `app/services/csv_export_service.py` (depends on T030)
- [ ] T033 [US3] Implement the export router with `FEATURE_CSV_EXPORT` guard, board-membership check, `text/csv; charset=utf-8` streaming response and attachment filename in `app/api/export.py` (depends on T032)
- [ ] T034 [US3] Register the export router in `app/main.py` (depends on T021, T033)
- [ ] T035 [US3] Add the CSV download client function in `src/api/reports.ts` in taskflow-web (depends on T024)
- [ ] T036 [US3] Build the keyboard-accessible ExportButton that downloads the file and shows an error message on failure in `src/features/reports/ExportButton.tsx` (depends on T035)
- [ ] T037 [US3] Add the ExportButton to the board header, hidden when the feature answers 404, in `src/features/board/BoardHeader.tsx` (A, header owned by 002-tasks-board) (depends on T028, T036)
- [ ] T038 [P] [US3] Component test for ExportButton (download, error, keyboard activation) in `src/features/reports/ExportButton.test.tsx`

**Checkpoint**: CSV export works end to end

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Observability, security review, documentation, validation

- [ ] T039 Add structured logs (board id, user id, result, duration; no task content) and request and error metrics to `app/api/sprints.py`, `app/api/reports.py`, `app/api/export.py` and a per-run success or failure log and metric to `app/worker/jobs/burndown_snapshot.py` (depends on T010, T020, T022, T033)
- [ ] T040 [P] Write the security review notes (membership and manager checks, cross-board isolation, CSV injection, flag-off behaviour) in `specs/008-reports-export/checklists/security.md`
- [ ] T041 [P] Document the endpoints, flags, daily job and the assumptions Q1, Q2, Q3 in `docs/reports-export.md` in taskflow-api (A)
- [ ] T042 Run the scenarios in `specs/008-reports-export/quickstart.md` and record the results in `specs/008-reports-export/checklists/quickstart-results.md` (depends on T028, T037, T039)

---

## Dependencies & Execution Order

- Setup (T001-T002) has no dependencies. Foundational (T003-T006) follows and blocks all stories.
- US1 (sprints) comes first because US2 reads sprints: T009 is used by T019.
- US2 depends on US1 service and router registration (T011); US3 is independent of US1 and US2 on the API side, but registers its router in `app/main.py` after T021 and shares `src/api/reports.ts` and `src/features/board/BoardHeader.tsx` with earlier tasks (T024, T028).
- Polish depends on the stories it covers.

## Parallel Examples

- After Phase 2: T007, T008 and T012 in parallel.
- US2: T015, T016, T017, T018 in parallel; then T025, T026, T029.
- US3: T030 and T031 in parallel; the API part (T030-T034) can run while the web part of US2 is built.

## Implementation Strategy

1. Setup and Foundational, then US1 (sprints), then US2 (burndown): this is the MVP for goal G3.
2. US3 (CSV export) is a Could and can ship later behind `FEATURE_CSV_EXPORT`.
3. Release each story behind its flag, off by default in prod.

## Notes

- Open questions assumed: Q1 Done-only counting, Q2 manager scope, Q3 UTC days (see clarifications.md).
- Task fields in the CSV follow the 002-tasks-board model at implementation time.
