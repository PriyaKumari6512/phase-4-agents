# Quickstart: validating Tasks and board

Prerequisites: feature 001 deployed in `dev` (users, a board with at least two members, sign-in); PostgreSQL 16 and Redis 7 reachable; this feature's migration applied (`alembic upgrade head` in taskflow-api).

## 1. Backend tests
- In taskflow-api run `pytest tests/unit tests/integration` (covers CRUD, validation, membership refusal, move, assignment event, SSE with two subscribers).

## 2. Create and move (User Stories 1, 3 and 4 of spec.md)
1. Sign in as member A and create a task with a title on the board; call `GET /api/v1/boards/{id}/board`.
   Expected: the task is in the `todo` column.
2. `PATCH` the task with a due date and `assignee_id` of member B.
   Expected: 200, both fields returned; one row in `task_assignment_events`.
3. `POST .../move` with `{"status": "doing"}`.
   Expected: the task is in `doing` on the next board read.

## 3. Live updates (US5)
1. Open the board in two browsers as members A and B.
2. As A, drag the card from "To do" to "Doing".
   Expected: B sees the card in "Doing" within 5 seconds with no reload.
3. Stop and restart the stream (network off then on in dev tools) and change a task meanwhile.
   Expected: after reconnect B sees the current state.
4. As a non-member, call `GET /api/v1/boards/{id}/events`.
   Expected: 403 and no data.

## 4. Keyboard only (US6)
- Using only the keyboard: Tab to the board, open the new-task form, create a task, pick it up with Space, press Right arrow, drop with Space, confirm the screen reader announcement text, delete it.
- Run the axe check in `src/features/board/__tests__` (`vitest run`). Expected: no serious or critical violations.

## 5. Performance
- Run the load script against `dev` at 50 requests per second on board and task endpoints. Expected: p95 under 300 ms.
