# Data Model: Tasks and board with live updates

Referenced from feature 001 (not created here): `users(id)`, `boards(id)`, board membership (`board_id`, `user_id`).

## Table `tasks` (new, migration in `migrations/versions/`)

| Column | Type | Constraints |
|---|---|---|
| id | UUID | primary key (A: key type follows feature 001's convention) |
| board_id | same type as boards.id | NOT NULL, foreign key to boards, ON DELETE CASCADE |
| title | varchar(200) | NOT NULL, not blank after trimming |
| description | text | nullable, at most 10,000 characters (validated at the API) |
| due_date | date | nullable |
| assignee_id | same type as users.id | nullable, foreign key to users; must be a board member when set (validated at the API) |
| story_points | smallint | nullable, check 0 <= story_points <= 100 (assumption A2) |
| status | varchar(5) | NOT NULL, default 'todo', check in ('todo', 'doing', 'done') |
| created_by | same type as users.id | NOT NULL, foreign key to users |
| created_at | timestamptz | NOT NULL, default now() |
| updated_at | timestamptz | NOT NULL, default now(), set on every change |

Indexes: `(board_id, status, created_at)` for the board view; `(assignee_id)` for later features. The full-text index for search belongs to feature 003 and is not created here.

Ordering inside a column: `created_at` ascending, then `id` (assumption A4).

### State transitions

`status` may change from any value to any other of `todo`, `doing`, `done` (no restricted flow). New tasks start as `todo`.

## Table `task_assignment_events` (new)

| Column | Type | Constraints |
|---|---|---|
| id | bigint | primary key, generated identity, increasing (consumer cursor) |
| task_id | same type as tasks.id | NOT NULL; no foreign key so the event survives task deletion |
| board_id | same type as boards.id | NOT NULL |
| assignee_id | same type as users.id | NOT NULL |
| assigned_by | same type as users.id | NOT NULL |
| created_at | timestamptz | NOT NULL, default now() |

Written in the same transaction as the task create or assignee change. Consumed by feature 005 (which keeps its own processing state). Retention is not defined (open for feature 005).

## Redis keys (no schema)

- `board:{board_id}:view`: cached board view JSON, TTL 60 s, deleted on every task write.
- Channel `board:{board_id}`: board update messages (see contracts/api.md).

## Validation summary

- title: required, trimmed, 1 to 200 characters.
- description: optional, up to 10,000 characters.
- due_date: optional ISO date (past dates allowed).
- assignee_id: optional, must be a member of the board.
- story_points: optional integer 0 to 100.
- status (on move): one of `todo`, `doing`, `done`.
