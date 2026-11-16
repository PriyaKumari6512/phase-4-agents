# Contract: Task search API

Prefix `/api/v1` (assumed per implementation contract). Auth: bearer token (assumed), required.

## GET /api/v1/search/tasks

Query parameters:

| Name | Type | Rules |
|---|---|---|
| q | string | required, trimmed, 1-200 characters (200 assumed), treated as plain text |
| board_id | id | optional; must be a board the caller is a member of |
| limit | integer | optional, default 20, 1-50 |
| offset | integer | optional, default 0, >= 0 |

Response 200:

```json
{
  "items": [
    {"task_id": "...", "title": "...", "board_id": "...", "board_name": "...", "column": "To do",
     "excerpt": "... <mark>match</mark> ...", "rank": 0.42}
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

Errors: 401 not authenticated; 404 `board_id` not a member board (same body whether the board exists or not); 422 empty/too long query or invalid paging.

Headers: `X-Search-Cache: hit|miss` (diagnostic, no task content).

Guarantees: only tasks of the caller's member boards; title matches ranked above description-only matches; ties broken by task id for a stable order.
