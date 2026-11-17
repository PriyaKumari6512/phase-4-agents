# API Contract: Tasks and board

Prefix `/api/v1` (assumption from implementation-contract). All routes need a signed-in user (mechanism from feature 001) and board membership; a non-member receives 403 (or 404 if feature 001 hides board existence; follow feature 001). Errors use the error body format defined by feature 001.

## Task representation

```json
{
  "id": "uuid",
  "board_id": "uuid",
  "title": "string (1-200)",
  "description": "string|null (<=10000)",
  "due_date": "YYYY-MM-DD|null",
  "assignee_id": "uuid|null",
  "assignee": {"id": "uuid", "name": "string", "is_member": true},
  "story_points": "integer 0-100|null",
  "status": "todo|doing|done",
  "created_by": "uuid",
  "created_at": "ISO 8601",
  "updated_at": "ISO 8601"
}
```

## Routes

| Method and path | Purpose | Success | Errors |
|---|---|---|---|
| `POST /boards/{board_id}/tasks` | Create task (body: title, optional description, due_date, assignee_id, story_points). Status is always `todo`. | 201 task | 403, 404, 422 |
| `GET /boards/{board_id}/tasks/{task_id}` | View one task | 200 task | 403, 404 |
| `PATCH /boards/{board_id}/tasks/{task_id}` | Edit title, description, due_date, assignee_id, story_points (partial; null clears optional fields) | 200 task | 403, 404, 422 |
| `DELETE /boards/{board_id}/tasks/{task_id}` | Delete task | 204 | 403, 404 |
| `POST /boards/{board_id}/tasks/{task_id}/move` | Body `{"status": "todo|doing|done"}`; moves the task | 200 task | 403, 404, 422 |
| `GET /boards/{board_id}/board` | Board view: `{board_id, columns: [{status, label, tasks: [task...]}]}` with the three columns in order | 200 | 403, 404 |
| `GET /boards/{board_id}/events` | SSE stream of board updates | 200 `text/event-stream` | 401, 403, 404 |

## SSE stream

- `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `X-Accel-Buffering: no`.
- First event `event: ready` after subscription is active (client then fetches/refreshes the snapshot so nothing is missed between snapshot and subscription).
- Update events: `event: board.update`, `data:` one JSON message:

```json
{"type": "task.created|task.updated|task.moved|task.deleted",
 "board_id": "uuid", "task": {"...task representation, or {id} for deleted"},
 "actor_id": "uuid", "at": "ISO 8601"}
```

- Heartbeat comment line `: ping` every 15 seconds.
- No replay: after a reconnect the client reloads `GET /boards/{board_id}/board`.

## Redis

- Publish to channel `board:{board_id}` the same JSON message as above, after commit and cache invalidation.

## Task-assigned event (internal hook for feature 005)

Row in `task_assignment_events` (see data-model.md); no HTTP surface.
