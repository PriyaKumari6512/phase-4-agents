# Feature Specification: Burndown report and CSV export

**Feature Branch**: `008-reports-export`

**Created**: 2026-01-01

**Status**: Draft

**Input**: User description: "Burndown report and CSV export. FR-8, FR-9, US-8, US-9 (goal G3: managers can answer 'are we on track?' without a status meeting). This feature owns the sprint model, the burndown report and the CSV export, behind the flags FEATURE_BURNDOWN and FEATURE_CSV_EXPORT."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Manager sets a sprint on a board (Priority: P1)

A team manager defines a sprint for a board by giving it a start date and an end date. The sprint is the time window the burndown report covers. This is the minimum needed for the report: the PRD does not say how sprints are created or managed, so this story covers only a minimal sprint with a name, a start date and an end date. (source: FR-8, US-8)

**Why this priority**: The burndown report cannot show anything without a sprint. It is the smallest slice that unblocks User Story 2.

**Independent Test**: Can be fully tested by a manager creating a sprint on a board, reading it back, editing its end date, and a non-manager member being refused. It delivers the sprint that the report needs.

**Acceptance Scenarios**:

1. **Given** a board and a manager who is a member of it, **When** the manager creates a sprint with a name, a start date and an end date on or after the start date, **Then** the sprint is saved and shown as the board's current sprint while today falls between the two dates.
2. **Given** a board that already has a sprint overlapping the requested dates, **When** a manager creates another sprint with overlapping dates, **Then** the request is rejected with a clear message and nothing is saved.
3. **Given** a sprint end date earlier than its start date, **When** the manager submits it, **Then** the request is rejected with a validation message.
4. **Given** a board member who is not a manager, **When** they try to create or edit a sprint, **Then** the request is refused and no data changes.
5. **Given** a user who is not a member of the board, **When** they request that board's sprints, **Then** the request is refused and nothing about the board is revealed.

---

### User Story 2 - Manager reads the burndown report (Priority: P2)

A team manager opens a burndown report for a board and sees the remaining story points for each day of the current sprint, so they can tell whether the team will finish on time without a status meeting. The chart is also readable as a table and works with the keyboard only. (source: FR-8, US-8)

**Assumption and open question**: Assumed: only the Done column counts toward the burndown. The PRD open question "is Done the only column that counts?" is not decided here (open question Q1, see clarifications.md).

**Why this priority**: It delivers goal G3 ("are we on track?") and is a Should in the PRD. It depends on User Story 1.

**Independent Test**: Can be fully tested by creating a board with a sprint and tasks that have story points, moving some to Done, and checking the remaining points per day on the report (the value for the current day comes from live task data, the values for past days from daily records).

**Acceptance Scenarios**:

1. **Given** a board with a current sprint, **When** a board member opens the report, **Then** they see the remaining story points for each day of the sprint, from the start date to the end date, with future days left empty.
2. **Given** a sprint with tasks totalling 20 story points and tasks worth 5 points moved to Done today, **When** the report is opened, **Then** today's remaining points are 15.
3. **Given** a day in the sprint for which no daily record exists, **When** the report is shown, **Then** the last known value is carried forward for that day and the day is not shown as zero.
4. **Given** a board without a current sprint, **When** a member opens the report, **Then** they see an empty state that says no sprint is set, instead of an error or an empty chart.
5. **Given** a task without story points, **When** the report is computed, **Then** that task counts as 0 points.
6. **Given** the report page, **When** a user navigates it with the keyboard only, **Then** they can reach the chart and read the same values as a table.
7. **Given** a user who is not a member of the board, **When** they request that board's report, **Then** the request is refused.
8. **Given** the flag `FEATURE_BURNDOWN` is off, **When** anyone requests the sprint or burndown endpoints, **Then** the feature is not available and the report entry point is not shown.

---

### User Story 3 - Manager exports board data as CSV (Priority: P3)

A team manager clicks Export on a board and downloads a CSV file with one row per task and one column for every task field, so they can analyse the data elsewhere. The file must be safe to open in a spreadsheet and must contain only that board's tasks. (source: FR-9, US-9)

**Why this priority**: It is a Could in the PRD. It is independent of the sprint and the report.

**Independent Test**: Can be fully tested by exporting a board with several tasks (including awkward text such as commas, quotes, line breaks and a leading `=`), and checking row count, columns, quoting and that no task from another board appears.

**Acceptance Scenarios**:

1. **Given** a board with N tasks, **When** a board member clicks Export, **Then** a CSV file is downloaded with a header row and exactly N task rows.
2. **Given** the task model, **When** the file is produced, **Then** it has one column for every task field, including story points and the column the task is in.
3. **Given** a task title or description containing commas, double quotes or line breaks, **When** it is exported, **Then** the cell is quoted so the file parses back to the original text.
4. **Given** a task text field that begins with `=`, `+`, `-`, `@`, a tab or a carriage return, **When** it is exported, **Then** the cell is neutralised so a spreadsheet does not run it as a formula, and the visible text is still readable.
5. **Given** two boards with tasks, **When** a member exports one board, **Then** the file contains no task from the other board.
6. **Given** a board with no tasks, **When** a member exports it, **Then** the file contains the header row only.
7. **Given** a user who is not a member of the board, **When** they request the export, **Then** the request is refused and no file is produced.
8. **Given** the flag `FEATURE_CSV_EXPORT` is off, **When** anyone requests the export, **Then** the feature is not available and the Export button is not shown.

---

### Edge Cases

- A sprint starts today: the report shows one data point (today) with the full scope remaining.
- A sprint has ended: the report still shows the whole sprint window with the last recorded values; it never extends past the end date.
- Story points are changed or tasks are added or deleted during the sprint: earlier days keep their recorded value; today's value reflects the live data.
- A task is moved out of Done again: today's remaining points go back up; past days are not rewritten.
- A task is deleted: it stops counting from that day on.
- A board with a very large number of tasks (the PRD's search scale is 10,000 tasks): the export contains every task and is not truncated.
- Text with non-ASCII characters: exported and read back unchanged (UTF-8).
- The daily record for a day was missed (for example an outage): the report carries forward the last known value (User Story 2, scenario 3).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST let a manager create and edit a sprint on a board with a name, a start date and an end date, and MUST reject an end date earlier than the start date and sprints that overlap an existing sprint on the same board. (source: FR-8, US-8)
- **FR-002**: The system MUST treat the sprint whose date range contains today as the board's current sprint, and at most one sprint can be current for a board. (source: FR-8)
- **FR-003**: The system MUST provide a burndown report per board that lists, for every day of the current sprint from start date to end date, the remaining story points, leaving days after today empty. (source: FR-8, US-8)
- **FR-004**: The system MUST compute remaining points as the total story points of the board's tasks minus the story points of tasks in the Done column, counting a task with no story points as 0. (source: FR-8; assumption A1, open question Q1)
- **FR-005**: The system MUST record the remaining points for each day of a sprint so past days are not changed by later edits, MUST carry forward the last known value for a day with no record, and MUST compute today's value from live task data when the report is opened. (source: FR-8)
- **FR-006**: The system MUST show the burndown as a chart together with an equivalent table, usable with the keyboard only. (source: FR-8, NFR-4)
- **FR-007**: The system MUST show an empty state when the board has no current sprint. (source: FR-8, US-8)
- **FR-008**: The system MUST let a board member download a CSV export of a board with a header row and one row per task, containing every task field. (source: FR-9, US-9)
- **FR-009**: The system MUST quote CSV cells that contain commas, double quotes or line breaks, and MUST encode the file as UTF-8. (source: FR-9)
- **FR-010**: The system MUST neutralise CSV cells that start with `=`, `+`, `-`, `@`, a tab or a carriage return so spreadsheets do not run them as formulas. (source: FR-9, NFR-3; assumption A5)
- **FR-011**: The system MUST allow the sprint, burndown and CSV endpoints only for members of the board, and MUST NOT return or reveal data of any other board. (source: NFR-3)
- **FR-012**: The system MUST restrict creating and editing sprints to board managers; viewing the report and exporting are open to any board member. (source: FR-8, FR-9; assumptions A3 and A4, open question Q2)
- **FR-013**: The system MUST make the sprint and burndown capability available only when the flag `FEATURE_BURNDOWN` is on, and the CSV export only when `FEATURE_CSV_EXPORT` is on; each flag is independent and defaults to off in production. (source: FR-8, FR-9)

### Key Entities *(include if feature involves data)*

- **Sprint**: A time window on one board. Attributes: name, start date, end date. Belongs to one board. At most one is current at a time.
- **Daily burndown record**: The remaining story points of one sprint on one day. Written once per day and kept as history.
- **Task (owned by 002-tasks-board)**: Read-only here. This feature uses its story points (optional field, added by 002-tasks-board), its column (Done or not) and all of its fields for the export.
- **Board and membership (owned by 001)**: Read-only here. Used to decide who may see the report and export, and who is a manager.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A manager can open a board's burndown report and read the remaining points for every day of the sprint within one page view, with no status meeting needed.
- **SC-002**: For a sprint with known task data, the remaining points on the report equal the hand-calculated values on 100% of tested days.
- **SC-003**: 100% of exports contain exactly one row per task of the exported board and no task from another board.
- **SC-004**: 100% of exported cells starting with a formula character are neutralised in testing.
- **SC-005**: The report and the Export action can be used with the keyboard only, with no mouse step required.
- **SC-006**: A board of 10,000 tasks exports completely, with no truncated or missing rows.
- **SC-007**: Requests from users who are not board members get no board data in 100% of tested cases.

## Assumptions

- **A1**: Only the Done column counts toward the burndown ("remaining" = total points minus points in Done). The PRD leaves this as an open question (Q1); it is not decided here.
- **A2**: A task's story points are an optional field on the task, added by 002-tasks-board. This feature does not add or edit story points. A task with no points counts as 0.
- **A3**: The sprint is a minimal entity (name, start date, end date), set by a manager. The PRD does not define how sprints are created or managed. Tasks are not assigned to a sprint individually: all tasks on the board count toward the current sprint.
- **A4**: The manager role is not defined in architecture.md. Assumed: a manager is a board member with a manager role provided by 001-platform-foundation membership (if 001 provides no roles, the board owner is the manager). Open question Q2 covers whether reports should be limited to managers.
- **A5**: Guarding against CSV injection and keeping data inside one board follow from NFR-3 and are assumed requirements, not stated in the PRD.
- **A6**: Day boundaries use UTC dates, since the PRD defines no board time zone (open question Q3).
- **A7**: The daily record is written by a scheduled daily job plus a refresh of today's value when the report is opened. This is a design choice detailed in plan.md.
- **A8**: The CSV columns are the task model's fields as defined by 002-tasks-board at implementation time; the exact list is not fixed here.
- **A9**: An ideal (straight-line) comparison and forecast are out of scope; the report shows remaining points per day only, as FR-8 states.
- **A10**: Dependencies: 001-platform-foundation (users, boards, membership, auth) and 002-tasks-board (task model, columns, board UI).
