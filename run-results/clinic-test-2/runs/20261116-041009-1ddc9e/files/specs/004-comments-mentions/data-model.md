# Data Model: Comments and @mentions

Database: PostgreSQL 16. One migration in `migrations/versions/` for this feature. Table and column names are proposals (A).

## comments

| Field | Type | Constraints |
|---|---|---|
| id | UUID | primary key |
| task_id | reference to tasks | required; delete of the task removes its comments (A) |
| author_id | reference to users | required |
| body | text | required, not empty after trimming, maximum 5,000 characters (assumption A5) |
| created_at | timestamp with time zone | required, set by the server |

Index: (task_id, created_at, id) for listing.

## comment_mentions

| Field | Type | Constraints |
|---|---|---|
| comment_id | reference to comments | required; removed with the comment |
| mentioned_user_id | reference to users | required; must be a member of the task's board at post time (checked in the service) |
| created_at | timestamp with time zone | required |

Primary key (comment_id, mentioned_user_id): one mention per member per comment. The author is never stored as a mention.

## Notification request (owned by F05)

A mention notification row in the F05 outbox: recipient user id, kind `mention`, comment id, task id, author id. Created in the same transaction as the comment. Field layout is defined by F05.

## State

Comments are immutable after posting in this release (assumption A3). No state transitions.
