# Contract: Comments API

Prefix `/api/v1` (A, implementation contract). JSON. Bearer session auth (A). All endpoints require the caller to be a member of the task's board (NFR-3) and `FEATURE_COMMENTS` on; otherwise 404 when the flag is off.

## GET /api/v1/tasks/{task_id}/comments

Query: `limit` (default 100, max 200, A), `offset` (default 0).

200 response:

```json
{
  "items": [
    {
      "id": "uuid",
      "task_id": "uuid",
      "author": {"id": "uuid", "username": "bob", "display_name": "Bob"},
      "body": "Please review, @alice",
      "mentions": [{"user_id": "uuid", "username": "alice"}],
      "created_at": "2026-01-01T10:00:00Z"
    }
  ],
  "total": 1
}
```

Errors: 401 not authenticated; 403 or 404 caller is not a board member (the same response for a task that does not exist, so existence is not revealed; A); 404 flag off.

## POST /api/v1/tasks/{task_id}/comments

Request: `{"body": "text"}`.

201 response: the created comment (same shape as above). Mentions are resolved on the server; only current board members appear in `mentions`.

Errors: 400/422 empty or whitespace-only body, or body over 5,000 characters; 401; 403/404 as above; 404 flag off.

Side effect: for each distinct mentioned member other than the author, one `mention` notification request is written to the F05 outbox in the same transaction.

The task route shape depends on feature 002 and is an assumption (A); align it with F02 before implementation.
