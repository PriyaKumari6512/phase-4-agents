# Data Model: Full-text task search

This feature adds no new table. It adds a column and an index to the `tasks` table owned by 002-tasks-board. Column names of the Task model other than those used here are not assumed.

## tasks (owned by 002-tasks-board) - additions by this feature

| Field | Type | Rules |
|---|---|---|
| search_vector | tsvector, generated always, stored | `setweight(to_tsvector('english', coalesce(title,'')), 'A') || setweight(to_tsvector('english', coalesce(description,'')), 'B')`; never written by the application |

Index: `ix_tasks_search_vector` GIN on `search_vector`.

Assumed existing Task fields used (from 002-tasks-board): `id`, `board_id`, `title`, `description` (nullable), column/status.

## Search result (not persisted)

| Field | Type | Rules |
|---|---|---|
| task_id | id | |
| title | string | |
| board_id / board_name | id / string | board must be one the user is a member of |
| column | string | To do, Doing or Done |
| excerpt | string | `ts_headline` output with matches marked; HTML-escaped by client |
| rank | float | title matches weighted higher than description matches |

## Cache entries (Redis)

| Key | Value | TTL |
|---|---|---|
| `search:v1:{hash}` | JSON result page | `SEARCH_CACHE_TTL_SECONDS` (60 s assumed) |
| `search:ver:{board_id}` | integer counter incremented on task change | none |
