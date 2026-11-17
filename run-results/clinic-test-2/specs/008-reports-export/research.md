# Research: Burndown report and CSV export

## R1: How to get remaining points per past day

- **Decision**: Store one record per sprint day (`sprint_burndown_records`), written by a daily job; refresh today's value live when the report is opened; carry forward the last known value for missing days.
- **Rationale**: The task model (002) keeps no move history, so history cannot be rebuilt on read. Live refresh of today keeps the report correct if the job runs late.
- **Alternatives considered**:
  - Rebuild from a task event log: needs a history table owned by 002 that is not in scope or defined.
  - Write a record on every task change: couples this feature to 002's write path and adds load to every move.
  - Compute only today's value: fails US-8 (per day).

## R2: Which tasks and points count

- **Decision**: All tasks on the board count toward the current sprint; Done-column points are burned; null points are 0.
- **Rationale**: PRD defines no sprint-task link and leaves "is Done the only column?" open (Q1). Assuming Done only is the simplest reading and is recorded as an open question.
- **Alternatives considered**: Per-task sprint assignment (more scope, not requested); partial credit for Doing (no rule defined).

## R3: Day boundary

- **Decision**: UTC dates (Q3).
- **Rationale**: No board time zone exists. Per-user time zones belong to F06 and would make records differ per viewer.
- **Alternatives considered**: Per-user or per-board time zone.

## R4: Chart rendering and accessibility

- **Decision**: Plain SVG in a React component plus an HTML table with the same data; both reachable by keyboard; the table is the accessible equivalent (WCAG 2.1 AA, NFR-4).
- **Rationale**: architecture.md names no charting library; a small SVG line avoids a new dependency (simplicity).
- **Alternatives considered**: A third-party chart library (not named by the architecture, would need review).

## R5: CSV generation and safety

- **Decision**: Stream rows from a database cursor through Python's `csv` writer; prefix a single quote to cells starting with `=`, `+`, `-`, `@`, tab or CR; filter by `board_id` in the query.
- **Rationale**: Python's standard library handles RFC 4180 quoting; streaming avoids loading 10,000 tasks in memory; the sanitiser addresses OWASP's CSV injection guidance (assumption A5).
- **Alternatives considered**: Building the file in memory (memory spike); background job with email link (not requested, notifications owned elsewhere).
- **Known trade-off**: A leading quote changes negative numbers in text fields to text; numeric columns (story points) are written without the prefix because they are numbers, not free text.

## R6: Scheduling the daily job

- **Decision**: Kubernetes CronJob with the worker image and a different command (A).
- **Rationale**: Architecture says the worker shares the API image. The digest scheduler (F06) is not guaranteed to exist first, so this feature does not depend on it.
- **Alternatives considered**: Reuse F06 scheduler (deployment-only change later).

## R7: Feature flags

- **Decision**: Env flags `FEATURE_BURNDOWN` and `FEATURE_CSV_EXPORT` read in `app/core/config.py`; routers return 404 when off.
- **Rationale**: Mechanism fixed by the implementation contract.
