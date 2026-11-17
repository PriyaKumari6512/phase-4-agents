# Contract: Outbox enqueue (internal service, no HTTP route)

Module: `app/services/notification_outbox.py` in acme/taskflow-api. Called by 002-tasks-board in the assignment transaction.

```text
enqueue_assignment_notification(session, *, task_id, assignee_id, assigned_by_user_id, assignment_event_id) -> bool
```

- Runs in the caller's database session and transaction; does not commit.
- Writes one `notification_outbox` row: kind `assignment_email`, `dedupe_key = assignment:<task_id>:<assignee_id>:<assignment_event_id>`, status `pending`, `next_attempt_at = now()`.
- Returns `True` when a row was inserted, `False` when the dedupe key already existed (no error).
- Must be called only when the assignee actually changed (including a new task created with an assignee); caller generates a new `assignment_event_id` (UUID) per change.
- Self-assignment (assignee_id = assigned_by_user_id) is enqueued like any other (open question Q1).

Worker-side API (same module): `claim_due(session, limit, now)`, `mark_sent(...)`, `mark_retry(...)`, `mark_failed(...)`, `mark_skipped(...)`; reused by F04/F06 for other kinds.
