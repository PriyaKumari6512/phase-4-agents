---

description: "Task list for Tasks and board with live updates"
---

# Tasks: Tasks and board with live updates

**Input**: Design documents from `/specs/002-tasks-board/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md; feature 001-platform-foundation (users, boards, membership, auth, CI, environments) must provide the membership check, the database session and the Redis client.

**Tests**: Included, because the constitution requires tests first for business logic and every user story has an independent test.

**Organization**: Tasks are grouped by user story. Paths start with the repository name: `taskflow-api/` is `acme/taskflow-api`, `taskflow-web/` is `acme/taskflow-web`, `taskflow-infra/` is `acme/taskflow-infra` (layout from implementation-contract.md, partly assumed).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no unfinished dependencies)
- **[Story]**: user story the task belongs to
- Source requirement ids: US1 = FR-1/US-1; US2 = FR-2/US-1; US3 = FR-1/US-1; US4 = FR-2/US-2; US5 = US-2/FR-2/NFR-1; US6 = NFR-4; US7 = FR-1 (hook for FR-5)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Configuration and folders for this feature

- [ ] T001 Add board settings `BOARD_VIEW_CACHE_TTL_SECONDS` (default 60) and `SSE_HEARTBEAT_SECONDS` (default 15) read from environment in taskflow-api/app/core/config.py
- [ ] T002 [P] Create the feature folder taskflow-web/src/features/board/ with taskflow-web/src/features/board/__tests__/setup.ts that registers the axe-core accessibility matcher for Vitest

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Task storage, validation schemas, publish helper, API client and test fixtures needed by every story

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 [P] Create the Task model in taskflow-api/app/models/task.py with columns and constraints from data-model.md: title varchar(200) NOT NULL, description text nullable, due_date date nullable, assignee_id nullable foreign key to users, story_points smallint nullable with check 0 to 100, status varchar(5) NOT NULL default 'todo' with check in ('todo','doing','done'), created_by, created_at, updated_at
- [ ] T004 [P] Create the TaskAssignmentEvent model in taskflow-api/app/models/task_assignment_event.py (id bigint identity, task_id with no foreign key, board_id, assignee_id, assigned_by, created_at)
- [ ] T005 Add the Alembic migration creating `tasks` (index on board_id, status, created_at) and `task_assignment_events` in taskflow-api/migrations/versions/002_tasks_and_assignment_events.py (depends on T003, T004)
- [ ] T006 [P] Create request and response schemas TaskCreate, TaskUpdate, TaskMove, TaskRead and BoardView in taskflow-api/app/schemas/task.py with validation: title trimmed 1 to 200 characters, description at most 10,000 characters, due_date valid date, story_points integer 0 to 100, status one of todo/doing/done
- [ ] T007 [P] Create taskflow-api/app/services/board_events.py with `publish_board_update(board_id, message)` publishing JSON to Redis channel `board:{board_id}` and `invalidate_board_view(board_id)` deleting key `board:{board_id}:view`; Redis errors are logged and never raised to the caller (depends on T001)
- [ ] T008 [P] Create the REST client and TypeScript types for tasks and the board (create, get, update, delete, move, board view) in taskflow-web/src/api/tasks.ts following contracts/api.md
- [ ] T009 [P] Create integration test fixtures in taskflow-api/tests/integration/conftest.py: a board with members A and B, a non-member user, a signed-in test client per user (using the feature 001 auth helpers) and a Redis test instance

**Checkpoint**: Foundation ready; user stories can start

---

## Phase 3: User Story 1 - Create, view, edit and delete tasks (Priority: P1) 🎯 MVP

**Goal**: Board members can create, view, edit and delete tasks through the API; new tasks start in "To do"; non-members are refused.

**Independent Test**: As a board member create a task with a title, edit it to add a due date and an assignee, read it, delete it; as a non-member every call is refused.

### Tests for User Story 1

- [ ] T010 [P] [US1] Unit tests for task schema validation (empty and whitespace title, title over 200, description over 10,000, bad date, story_points -1 and 101) in taskflow-api/tests/unit/test_task_schemas.py
- [ ] T011 [P] [US1] Integration tests for create, get, patch, delete, new task status 'todo', assignee not a board member rejected, non-member refused with 403 in taskflow-api/tests/integration/test_tasks_crud.py

### Implementation for User Story 1

- [ ] T012 [US1] Implement create, get, update and delete in taskflow-api/app/services/task_service.py (sets created_by and updated_at, status 'todo' on create, checks assignee membership, calls `invalidate_board_view` and `publish_board_update` with task.created, task.updated, task.deleted after commit) (depends on T003, T006, T007)
- [ ] T013 [US1] Implement routes POST /boards/{board_id}/tasks, GET, PATCH and DELETE /boards/{board_id}/tasks/{task_id} in taskflow-api/app/api/tasks.py using the feature 001 membership dependency (depends on T012)
- [ ] T014 [US1] Register the tasks router under the /api/v1 prefix in taskflow-api/app/main.py (depends on T013)
- [ ] T015 [US1] Add structured log lines and trace attributes (board_id, task_id, actor_id; no task text) for task operations in taskflow-api/app/api/tasks.py (depends on T013)

**Checkpoint**: Task CRUD works through the API and is independently testable

---

## Phase 4: User Story 2 - See the board with three columns and task cards (Priority: P1)

**Goal**: Opening a board shows To do, Doing and Done columns with task cards (title, due date, assignee, story points).

**Independent Test**: Open a board with tasks in each column and check columns, order and card contents.

### Tests for User Story 2

- [ ] T016 [P] [US2] Integration tests for GET /boards/{board_id}/board (three columns in order, tasks ordered by created_at then id, empty columns, cache filled on first read, cache cleared after a task write, Redis down falls back to the database, non-member 403) in taskflow-api/tests/integration/test_board_view.py
- [ ] T017 [P] [US2] Component tests for BoardPage, Column and TaskCard (three columns in order, empty-state message, due date, assignee and story points on the card, "no longer a member" label) in taskflow-web/src/features/board/__tests__/BoardPage.test.tsx

### Implementation for User Story 2

- [ ] T018 [US2] Implement the board view read with Redis cache (key `board:{board_id}:view`, TTL from config) and database fallback in taskflow-api/app/services/board_view_service.py (depends on T003, T006, T007)
- [ ] T019 [US2] Implement route GET /boards/{board_id}/board in taskflow-api/app/api/board_view.py and register it in taskflow-api/app/main.py (depends on T018, T014)
- [ ] T020 [P] [US2] Create the Column component with heading and empty-state message in taskflow-web/src/features/board/Column.tsx
- [ ] T021 [P] [US2] Create the TaskCard component showing title, due date, assignee name (or "no longer a member") and story points in taskflow-web/src/features/board/TaskCard.tsx
- [ ] T022 [US2] Create the useBoard hook that loads the board snapshot and exposes columns, loading and error state in taskflow-web/src/features/board/useBoard.ts (depends on T008)
- [ ] T023 [US2] Create BoardPage that renders three Column components from useBoard in taskflow-web/src/features/board/BoardPage.tsx (depends on T020, T021, T022)
- [ ] T024 [US2] Register the board route `/boards/:boardId` in taskflow-web/src/routes.tsx (A: routing file location; follow the feature 001 web layout) (depends on T023)

**Checkpoint**: The board can be opened and read

---

## Phase 5: User Story 3 - Create, edit and delete tasks from the board (Priority: P1)

**Goal**: Members create, edit and delete tasks with forms on the board.

**Independent Test**: In the browser create a task with a title, edit it to add a due date and an assignee, see both on the card, delete it.

### Tests for User Story 3

- [ ] T025 [P] [US3] Component tests for TaskForm and delete confirmation (create puts card in "To do", edit shows due date and assignee on the card, inline field errors, cancel keeps the task) in taskflow-web/src/features/board/__tests__/TaskForm.test.tsx

### Implementation for User Story 3

- [ ] T026 [P] [US3] Create the TaskForm component (title, description, due date, assignee select filled from the board members list of feature 001, story points; create and edit modes; field errors) in taskflow-web/src/features/board/TaskForm.tsx
- [ ] T027 [P] [US3] Create the ConfirmDeleteDialog component in taskflow-web/src/features/board/ConfirmDeleteDialog.tsx
- [ ] T028 [US3] Add createTask, updateTask and deleteTask actions to taskflow-web/src/features/board/useBoard.ts (depends on T022)
- [ ] T029 [US3] Add the "New task" button, open-card-to-edit and delete actions that use TaskForm and ConfirmDeleteDialog to taskflow-web/src/features/board/BoardPage.tsx (depends on T023, T026, T027, T028)

**Checkpoint**: A member can manage tasks entirely from the board

---

## Phase 6: User Story 4 - Move tasks between columns (Priority: P1)

**Goal**: Members move a task between columns by dragging or from a menu; the move is saved; failures roll back.

**Independent Test**: Drag a task from "To do" to "Doing", reload, and see it still in "Doing"; repeat using the menu.

### Tests for User Story 4

- [ ] T030 [P] [US4] Integration tests for POST /boards/{board_id}/tasks/{task_id}/move (every column to every other, invalid status 422, non-member 403, last move wins, task.moved message published) in taskflow-api/tests/integration/test_task_move.py
- [ ] T031 [P] [US4] Component tests for drag move, menu move and rollback with error message on failure in taskflow-web/src/features/board/__tests__/BoardMove.test.tsx

### Implementation for User Story 4

- [ ] T032 [US4] Add `move_task` to taskflow-api/app/services/task_service.py (update status and updated_at, invalidate board view, publish task.moved) (depends on T012)
- [ ] T033 [US4] Implement route POST /boards/{board_id}/tasks/{task_id}/move in taskflow-api/app/api/tasks.py (depends on T015, T032)
- [ ] T034 [P] [US4] Create the MoveMenu component ("Move to" with the other two columns) in taskflow-web/src/features/board/MoveMenu.tsx
- [ ] T035 [US4] Add drag source to TaskCard and drop target to Column using native HTML5 drag and drop in taskflow-web/src/features/board/TaskCard.tsx and taskflow-web/src/features/board/Column.tsx (depends on T020, T021)
- [ ] T036 [US4] Add `moveTask` with optimistic update and rollback on error to taskflow-web/src/features/board/useBoard.ts (depends on T028)
- [ ] T037 [US4] Wire MoveMenu and drop handlers to `moveTask` and show the error message on failure in taskflow-web/src/features/board/BoardPage.tsx (depends on T029, T034, T035, T036)

**Checkpoint**: Tasks can be moved and the move persists

---

## Phase 7: User Story 5 - Everyone sees board changes within 5 seconds (Priority: P1)

**Goal**: All viewers of a board see creations, edits, moves and deletions within 5 seconds, with reconnect and fallback.

**Independent Test**: Two sessions on the same board; a move in one shows in the other within 5 seconds with no reload.

### Tests for User Story 5

- [ ] T038 [P] [US5] Integration tests for GET /boards/{board_id}/events (ready event, update events for created, updated, moved and deleted, board isolation, non-member 403, heartbeat comment, works across two API app instances sharing one Redis) in taskflow-api/tests/integration/test_board_events.py
- [ ] T039 [P] [US5] Latency test with 10 simultaneous subscribers asserting every update arrives in under 5 seconds (SC-001) in taskflow-api/tests/integration/test_board_update_latency.py
- [ ] T040 [P] [US5] Unit tests for the web stream client (parsing events, reconnect with backoff 1 s up to 10 s, polling every 3 s while disconnected, snapshot reload after reconnect) in taskflow-web/src/features/board/__tests__/useBoardEvents.test.ts

### Implementation for User Story 5

- [ ] T041 [US5] Add `subscribe_board_updates(board_id)` async generator over Redis pub/sub, with heartbeat comment every `SSE_HEARTBEAT_SECONDS`, to taskflow-api/app/services/board_events.py (depends on T007)
- [ ] T042 [US5] Implement route GET /boards/{board_id}/events returning `text/event-stream` with headers Cache-Control no-cache and X-Accel-Buffering no, membership checked before opening, `ready` event first, in taskflow-api/app/api/board_view.py (depends on T019, T041)
- [ ] T043 [US5] Add metrics (open SSE connections gauge, publish failure counter) and structured logs for connect, disconnect and publish errors in taskflow-api/app/services/board_events.py (depends on T041)
- [ ] T044 [US5] Create the fetch-stream SSE client with Authorization header, reconnect backoff and 3 second polling fallback in taskflow-web/src/features/board/useBoardEvents.ts (depends on T008)
- [ ] T045 [US5] Apply task.created, task.updated, task.moved and task.deleted messages to board state and reload the snapshot on reconnect in taskflow-web/src/features/board/useBoard.ts (depends on T036, T044)
- [ ] T046 [US5] Start the board subscription when BoardPage mounts and show a "reconnecting" indicator in taskflow-web/src/features/board/BoardPage.tsx (depends on T037, T045)

**Checkpoint**: Live updates work end to end

---

## Phase 8: User Story 6 - Use the board and task forms with the keyboard only (Priority: P2)

**Goal**: Everything in this feature is operable by keyboard and meets WCAG 2.1 AA.

**Independent Test**: Without a pointing device create, edit, move and delete a task; the automated accessibility check reports no serious or critical violations.

### Tests for User Story 6

- [ ] T047 [P] [US6] Accessibility tests running axe-core on BoardPage, TaskForm and ConfirmDeleteDialog in taskflow-web/src/features/board/__tests__/accessibility.test.tsx
- [ ] T048 [P] [US6] Keyboard interaction tests (Tab order, Space or Enter to pick up, Left and Right arrows to choose a column, Space or Enter to drop, Escape to cancel, Escape closes form and returns focus, announcements text) in taskflow-web/src/features/board/__tests__/keyboard.test.tsx

### Implementation for User Story 6

- [ ] T049 [P] [US6] Create the LiveAnnouncer component with an `aria-live="polite"` region in taskflow-web/src/features/board/LiveAnnouncer.tsx
- [ ] T050 [US6] Add keyboard pick-up, arrow-key column choice, drop and cancel to the card and column, with accessible names (task title, column) in taskflow-web/src/features/board/TaskCard.tsx and taskflow-web/src/features/board/Column.tsx (depends on T035, T049)
- [ ] T051 [US6] Add focus trap, Escape to close, focus return to the opener, labelled inputs and error text linked with `aria-describedby` in taskflow-web/src/features/board/TaskForm.tsx and taskflow-web/src/features/board/ConfirmDeleteDialog.tsx (depends on T026, T027)
- [ ] T052 [US6] Add landmarks, heading structure, the LiveAnnouncer for moves, remote updates and errors, in taskflow-web/src/features/board/BoardPage.tsx (depends on T046, T049)
- [ ] T053 [P] [US6] Add visible focus styles and sufficient colour contrast (text 4.5:1) for cards, columns and form controls in taskflow-web/src/features/board/board.css (A: styling approach follows feature 001; adapt the file type if different)

**Checkpoint**: The keyboard-only journey passes and the accessibility check is clean

---

## Phase 9: User Story 7 - Task assignment emits an event for notifications (Priority: P2)

**Goal**: Every assignment creates exactly one task-assigned event in the same transaction for feature 005 to consume.

**Independent Test**: Assign and reassign tasks and verify one event each; no event for other edits.

### Tests for User Story 7

- [ ] T054 [P] [US7] Integration tests (event on create with assignee, on first assignment, on reassignment; none when other fields change, when the assignee is unchanged or when cleared; rollback leaves no event) in taskflow-api/tests/integration/test_assignment_events.py

### Implementation for User Story 7

- [ ] T055 [US7] Write a TaskAssignmentEvent row (task, assignee, assigned_by) in the same transaction as create and update when assignee_id changes to a non-null value, in taskflow-api/app/services/task_service.py (depends on T004, T032)
- [ ] T056 [P] [US7] Document the event table and how feature 005 reads it (increasing id cursor, no deletion by consumer) in taskflow-api/docs/task-assignment-events.md

**Checkpoint**: Feature 005 can consume assignment events

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Operations, performance and documentation across stories

- [ ] T057 Add OpenTelemetry spans around database, Redis and publish calls in taskflow-api/app/services/task_service.py and taskflow-api/app/services/board_view_service.py (depends on T055, T018)
- [ ] T058 [P] Confirm the feature 001 health check covers database and Redis, and add the board events route to the metrics dashboard definitions if feature 001 keeps them in code, in taskflow-api/app/api/board_view.py (depends on T042)
- [ ] T059 [P] Set the ingress idle timeout for the path /api/v1/boards/*/events above 15 seconds and disable response buffering in taskflow-infra/k8s/ingress.yaml (A: path and ingress kind owned by feature 001; coordinate)
- [ ] T060 [P] Add a load script for board and task endpoints at 50 requests per second asserting p95 under 300 ms in taskflow-api/tests/load/board_load.py (depends on T042)
- [ ] T061 [P] Update docs for the task, board and SSE endpoints and the story points assumption in taskflow-api/docs/tasks-board.md and taskflow-web/docs/board.md
- [ ] T062 Run the quickstart.md validation in dev and record the result in specs/002-tasks-board/quickstart.md (depends on T046, T052, T055, T059, T060)

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1): none
- Foundational (Phase 2): after Setup; blocks all stories
- US1 (backend CRUD) first; US2 needs the Task model and schemas and the US1 router registration (T014)
- US3 needs US2 (board page) and US1 (API)
- US4 needs US1 backend and the US2/US3 board code
- US5 needs US4 web state (T036) and the US2 backend route file
- US6 needs US3, US4 and US5 UI code
- US7 needs the task service (US1 and US4 changes in `task_service.py`)
- Polish after the stories

### Parallel Opportunities

- Foundational tasks T003, T004, T006, T007, T008, T009 touch different files
- Backend and web work of one story can run in parallel after the Foundational phase (for example T016 and T017, T020 and T021)
- Test tasks marked [P] in a story run in parallel and should fail before the implementation

### Parallel Example: User Story 4

```text
Task T030: integration tests for move in taskflow-api/tests/integration/test_task_move.py
Task T031: component tests for move in taskflow-web/src/features/board/__tests__/BoardMove.test.tsx
Task T034: MoveMenu component in taskflow-web/src/features/board/MoveMenu.tsx
```

## Implementation Strategy

### MVP first

1. Setup and Foundational
2. US1 (task CRUD API), US2 (board view), US3 (forms), US4 (moves): this is FR-1 and FR-2 without live updates
3. US5 (live updates) completes the 5 second promise for the pilot beta (deadline 2026-12-18)
4. Validate each story with its independent test before moving on

### Incremental delivery

1. Each story phase ends with a checkpoint that can be demonstrated
2. US6 (keyboard) and US7 (assignment event, needed by feature 005) follow, and both must land before the beta
3. Open questions assumed (see clarifications.md): story points optional (Q1), no reordering inside a column (Q2), departed assignee kept and labelled (Q3)

## Notes

- Tasks that edit the same file are sequenced with dependencies (task_service.py, TaskCard.tsx, BoardPage.tsx, useBoard.ts)
- Use feature 001 for users, boards, membership, auth and CI; do not recreate them
