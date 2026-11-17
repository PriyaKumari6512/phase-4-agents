# Data Model: Daily due-tomorrow digest

Migration: `migrations/versions/006_user_timezone_digest_deliveries.py` (one migration per feature).

## users (owned by feature 001, one column added here)

| Field | Type | Rules |
|---|---|---|
| timezone | text, nullable | IANA zone name, max length 64; must be a member of the zone database; NULL means UTC |

## digest_deliveries (new)

| Field | Type | Rules |
|---|---|---|
| id | uuid | primary key |
| user_id | uuid | not null, foreign key to users.id, on delete cascade |
| local_date | date | not null; the user's local calendar date of the run |
| status | text | not null; one of `claimed`, `sent`, `failed` |
| attempts | integer | not null, default 1, maximum 3 |
| task_count | integer | not null, default 0; tasks listed |
| claimed_at | timestamptz | not null |
| sent_at | timestamptz | nullable; set when status is `sent` |
| last_error | text | nullable; provider error class, no email body, no secrets |

Constraints and indexes:
- Unique `(user_id, local_date)`: the exactly-once guarantee.
- Index on `(local_date, status)` for operations and metrics.

## State transitions

```text
(no row) --claim--> claimed --provider accepted--> sent
                    claimed --definite provider error--> failed
failed --re-claim, attempts < 3--> claimed
claimed (stuck, outcome unknown) --> not retried; logged and counted
```

## Not stored

Digest content is computed from tasks at send time. The email body is not persisted.
