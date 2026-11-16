# Data Model: Burndown report and CSV export

Types follow PostgreSQL 16. Table and column names are proposals; users, boards, memberships and tasks are owned by 001 and 002.

## Sprint (`sprints`)

| Field | Type | Constraint |
|-------|------|-----------|
| id | UUID | primary key (follows the id type used by 001/002) |
| board_id | same type as boards.id | NOT NULL, foreign key to boards, indexed |
| name | text | NOT NULL, 1 to 100 characters |
| start_date | date | NOT NULL |
| end_date | date | NOT NULL, CHECK end_date >= start_date |
| created_by | same type as users.id | NOT NULL |
| created_at | timestamptz | NOT NULL, default now() |
| updated_at | timestamptz | NOT NULL |

Rules:
- No two sprints of the same board may overlap in date range (checked in the service in one transaction; a PostgreSQL exclusion constraint on `(board_id, daterange(start_date, end_date, '[]'))` is the preferred backstop if the `btree_gist` extension is allowed).
- Current sprint of a board: `start_date <= today (UTC) <= end_date`.

## Daily burndown record (`sprint_burndown_records`)

| Field | Type | Constraint |
|-------|------|-----------|
| sprint_id | foreign key to sprints | NOT NULL, ON DELETE CASCADE |
| day | date | NOT NULL, within the sprint's dates |
| remaining_points | integer | NOT NULL, >= 0 |
| total_points | integer | NOT NULL, >= 0 (scope on that day) |
| recorded_at | timestamptz | NOT NULL, default now() |

Primary key: `(sprint_id, day)`. The write is an upsert so the job and the live refresh cannot create duplicates.

## Read-only inputs (not created here)

- `tasks` (002): `board_id`, column (To do / Doing / Done), optional `story_points` (integer, added by 002), and all other task fields for the export.
- `board_members` (001): membership and role.

## Derived values

- remaining_points(day) = SUM(story_points of tasks on the board) minus SUM(story_points of tasks in Done); NULL counts as 0.
- Report row for a day: recorded value; or, for days with no record up to today, the last earlier value; for days after today, empty. If no earlier record exists, the day takes the live value of today only when day = today; earlier days with no record are left empty.
