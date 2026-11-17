# Research: Tasks and board with live updates

All decisions follow architecture.md and implementation-contract.md. Items marked (A) are assumptions.

## R1. Delivery of board updates
- Decision: SSE endpoint `GET /api/v1/boards/{board_id}/events` in taskflow-api; each API replica subscribes to the Redis channel `board:{board_id}` while it has at least one viewer, and forwards messages to its connected clients. Writers publish after the database commit.
- Rationale: architecture.md decides SSE backed by Redis pub/sub; Redis pub/sub makes it work across replicas (FR-009). Latency is well below 5 s.
- Alternatives: WebSockets (not in architecture); in-process fan-out (breaks with several replicas); polling only (kept only as fallback).

## R2. Message content
- Decision: small JSON messages `{type: task.created|task.updated|task.moved|task.deleted, board_id, task (full task for created/updated/moved, id for deleted), actor_id, at}`; the SSE `id` is a timestamp-based counter. No replay buffer.
- Rationale: full task makes the client update without refetching. Replay would add storage; instead, on reconnect the client reloads the board snapshot (FR-010).
- Alternatives: Redis streams with replay (more infra, not needed for 5 s goal).

## R3. SSE authentication (A)
- Decision: auth is a bearer token (A, implementation-contract). The browser `EventSource` cannot send headers, so the web client reads the stream with `fetch` and a stream reader, sending the Authorization header. Membership is checked with the F01 dependency before the stream opens.
- Rationale: avoids tokens in URLs (which land in logs; Security baseline). If F01 chooses cookie sessions this becomes simpler and `EventSource` may be used; revisit then.
- Alternatives: token in query string (logging risk); short-lived stream ticket endpoint (extra moving part).

## R4. Keep-alive and proxy behaviour
- Decision: send an SSE comment heartbeat every 15 s and set headers `Cache-Control: no-cache` and `X-Accel-Buffering: no`. Ingress idle timeout for the SSE path must exceed 15 s; to be set in taskflow-infra by feature 001 (noted as dependency).
- Alternatives: none needed.

## R5. Board read cache
- Decision: cache the board view in Redis under `board:{board_id}:view` with a 60 s TTL; every task write deletes the key before publishing. Cache misses read from PostgreSQL.
- Rationale: architecture says Redis caches board reads; delete-on-write satisfies FR-012. A failed Redis call falls back to the database.
- Alternatives: write-through cache (more code for no gain).

## R6. Concurrency
- Decision: last write wins, no version column; `updated_at` is set on every change. Moves are a single-column update.
- Rationale: spec edge cases accept last-write-wins; keeps scope small (Simplicity).

## R7. Moving tasks in the UI
- Decision: native HTML5 drag and drop for pointer users, plus a "Move to" menu button on each card and a keyboard pick-up/drop mode (Space or Enter to pick up, Left/Right arrows to choose a column, Space or Enter to drop, Escape to cancel) with an `aria-live` announcer. Optimistic update with rollback on error.
- Rationale: no extra dependency; keyboard path is required by NFR-4 and drag alone is not accessible (WCAG 2.5.7 is WCAG 2.2, but a non-drag alternative is good practice).
- Alternatives: a drag-and-drop library (new dependency not in architecture).

## R8. Task-assigned event for feature 005
- Decision: table `task_assignment_events` written in the same database transaction as the assignment change (task id, board id, assignee id, assigned by, created at). Feature 005 reads new rows (by increasing id) and writes its own notification outbox. Event is written when the assignee changes to a non-null user, including on create; not when the assignee is cleared.
- Rationale: transactional, so exactly one event per assignment even if the API crashes; works across the API/worker process boundary (the worker is a separate process in the same image).
- Alternatives: in-process callback (lost on crash, not visible to the worker); Redis pub/sub (not durable).

## R9. Story points (A, open question Q1)
- Decision: nullable smallint `story_points` with check 0 to 100. Shown on card when set.

## R10. Fixed columns
- Decision: columns are a fixed enumeration `todo`, `doing`, `done` stored in the task row (`status`), with display labels "To do", "Doing", "Done". No columns table.
- Rationale: PRD fixes exactly three columns; a table would be speculative.

## R11. Polling fallback
- Decision: if the stream fails to connect or breaks, the web client retries with exponential backoff (1 s up to 10 s) and, while disconnected, reloads the board snapshot every 3 s so the 5-second promise holds.

## R12. Authorisation reuse
- Decision: use the board-membership dependency/function from feature 001 (`app/core/auth.py`, exact name to be confirmed against feature 001's contract); this feature adds no auth logic.
