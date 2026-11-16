# Data Model: Assignment email notification

## notification_outbox (new table, migration `migrations/versions/005_notification_outbox.py`)

Shared by all notification kinds; this feature uses kind `assignment_email`.

| Column | Type | Constraints / notes |
|---|---|---|
| id | UUID | primary key |
| kind | text | NOT NULL; values: `assignment_email` (F04/F06 add their own kinds) |
| dedupe_key | text | NOT NULL, UNIQUE; for assignments `assignment:<task_id>:<assignee_id>:<assignment_event_id>` |
| recipient_user_id | UUID | NOT NULL, FK users(id) (table owned by F01) |
| payload | JSONB | NOT NULL; assignment: `task_id`, `assigned_by_user_id`, `assignment_event_id` (no email body, no secrets) |
| status | text | NOT NULL, one of `pending`, `sending`, `sent`, `failed`, `skipped`; default `pending` |
| attempts | integer | NOT NULL, default 0 |
| next_attempt_at | timestamptz | NOT NULL, default now() |
| claimed_at | timestamptz | NULL; set when status becomes `sending` |
| last_error | text | NULL; max 500 characters; never contains the provider key or the email body |
| provider_message_id | text | NULL; set when sent |
| created_at | timestamptz | NOT NULL, default now() (assignment commit time) |
| sent_at | timestamptz | NULL |

Indexes: UNIQUE(dedupe_key); INDEX(status, next_attempt_at) for the claim query.

## State transitions

```text
pending --claim--> sending --provider accepted--> sent
                   sending --transient error, attempts < max--> pending (next_attempt_at = now + backoff)
                   sending --permanent error or attempts = max--> failed
                   sending --task deleted / no usable email address--> skipped
sending --claimed_at older than visibility timeout--> sending (reclaimed, attempts + 1)
failed --manual requeue (runbook)--> pending
```

## Validation rules

- `kind`, `dedupe_key`, `recipient_user_id` and `payload` are written only by the enqueue function.
- An enqueue with an existing `dedupe_key` is a no-op (insert on conflict do nothing).
- Terminal states are `sent`, `failed`, `skipped`; `sent` and `skipped` are never retried.
