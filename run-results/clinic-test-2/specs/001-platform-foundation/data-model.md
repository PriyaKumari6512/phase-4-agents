# Data Model: Platform foundation

Migration: `migrations/versions/0001_users_boards_memberships.py` (Alembic, PostgreSQL 16). Later features add their own migrations.

## users
| Field | Type | Constraints |
|---|---|---|
| id | UUID | primary key |
| email | text | required, unique (case-insensitive), max 254 chars |
| display_name | text | required, max 100 chars |
| password_hash | text | required, salted one-way hash, never returned by the API |
| time_zone | text | nullable, IANA name (reserved for F06) |
| created_at | timestamptz | required, default now |

## boards
| Field | Type | Constraints |
|---|---|---|
| id | UUID | primary key |
| name | text | required, 1-100 chars |
| created_by | UUID | required, FK users.id |
| created_at | timestamptz | required, default now |

## board_memberships
| Field | Type | Constraints |
|---|---|---|
| id | UUID | primary key |
| board_id | UUID | required, FK boards.id, on delete cascade |
| user_id | UUID | required, FK users.id, on delete cascade |
| role | text | required, one of `owner`, `member` |
| created_at | timestamptz | required, default now |

Unique constraint (board_id, user_id). Index on user_id (list "my boards") and on board_id.

## Rules and state
- Creating a board creates an `owner` membership for the creator in the same transaction.
- A board must keep at least one owner (removing or demoting the last owner is refused).
- Access rule: a user may read or change board-scoped data only if a membership row (board_id, user_id) exists.

## Non-database state
- Login failure counters in Redis: key `login_fail:<email>:<ip>`, expiry 15 minutes.
