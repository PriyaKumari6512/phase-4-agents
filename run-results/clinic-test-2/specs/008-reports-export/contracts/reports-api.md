# Contract: Sprints, burndown and CSV export API

Prefix `/api/v1` (contract assumption). All endpoints require an authenticated board member (NFR-3); non-members get 403 (or 404 where the board must not be revealed, following the F01 convention). JSON, except the export.

## Sprints (flag FEATURE_BURNDOWN; flag off returns 404)

### POST /api/v1/boards/{board_id}/sprints
Manager only. Body: `{ "name": string (1-100), "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD" }`.
- 201: `{ "id", "board_id", "name", "start_date", "end_date" }`
- 403: not a manager / not a member
- 409: dates overlap another sprint on the board
- 422: end_date before start_date, or invalid input

### PATCH /api/v1/boards/{board_id}/sprints/{sprint_id}
Manager only. Same fields, all optional. Responses as above; 404 if the sprint is not on that board.

### GET /api/v1/boards/{board_id}/sprints
Board member. 200: `{ "current": Sprint | null, "sprints": [Sprint] }`.

## Burndown (flag FEATURE_BURNDOWN)

### GET /api/v1/boards/{board_id}/reports/burndown
Board member. 200:
```json
{
  "board_id": "...",
  "sprint": { "id": "...", "name": "...", "start_date": "...", "end_date": "..." },
  "days": [
    { "day": "YYYY-MM-DD", "remaining_points": 15, "total_points": 20 },
    { "day": "YYYY-MM-DD", "remaining_points": null, "total_points": null }
  ],
  "counts_done_only": true
}
```
- `days` lists every day from start to end; days after today have null values.
- 200 with `"sprint": null` and `"days": []` when there is no current sprint.
- 403 not a member; 404 flag off.

## CSV export (flag FEATURE_CSV_EXPORT)

### GET /api/v1/boards/{board_id}/export/csv
Board member. 200, `Content-Type: text/csv; charset=utf-8`, `Content-Disposition: attachment; filename="board-{board_id}-tasks.csv"`.
- Header row plus one row per task of this board; one column per task field.
- Cells quoted per RFC 4180; cells starting with `=`, `+`, `-`, `@`, tab or CR in text fields are prefixed with `'`.
- 403 not a member; 404 flag off or unknown board.

## Cross-cutting

- Each endpoint logs structured events (board id, user id, result, duration) and counts requests and errors as metrics; no task content is logged.
