# Implementation Plan: Tasks and board with live updates

**Branch**: `002-tasks-board` | **Date**: 2026-01-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-tasks-board/spec.md`

## Summary

Add the task model and CRUD, the three fixed board columns, moving tasks, live board updates and the board UI with keyboard support. Backend in `acme/taskflow-api` (FastAPI, PostgreSQL 16, Redis 7): tasks are stored in PostgreSQL; every write commits, invalidates the cached board read, then publishes a board update on a Redis pub/sub channel; an SSE endpoint per board relays the channel to connected viewers (architecture.md key decision). Frontend in `acme/taskflow-web` (React): board page with three columns, task form, move by drag or keyboard, SSE subscription with automatic reconnect and a polling fallback. Assignment changes write a task-assigned event row in the same transaction for feature 005 to consume. Users, boards, membership, auth and the membership check are reused from feature 001.

## Technical Context

**Language/Version**: Python 3.12 (taskflow-api); Node 22 with React (taskflow-web); TypeScript assumed for the web (A: not stated in architecture.md; plain JavaScript is acceptable if feature 001 set up the web repo that way)

**Primary Dependencies**: FastAPI; SQLAlchemy and Alembic for models and migrations (A per implementation-contract: Alembic under `migrations/`); a Redis client library with asyncio pub/sub (A); React with no extra drag-and-drop library (native pointer drag plus own keyboard handling, see research.md)

**Storage**: PostgreSQL 16 (system of record for tasks and assignment events); Redis 7 (board read cache and pub/sub channel)

**Testing**: pytest with an API test client for backend unit and integration tests; Vitest and React Testing Library for web components; axe-core based accessibility check in component tests (A: test tools are not named in architecture.md)

**Target Platform**: Linux containers on EKS (dev, stg, prod); modern evergreen desktop browsers

**Project Type**: web application (taskflow-api + taskflow-web, two repositories)

**Performance Goals**: API p95 300 ms (architecture service levels); board updates visible to all viewers within 5 seconds (NFR-1); peak 50 requests per second across the system

**Constraints**: only board members may read tasks or subscribe (NFR-3); no secrets in code; inputs validated at the boundary; must work with several API replicas (Redis pub/sub, not in-process fan-out); error rate under 1%

**Scale/Scope**: about 200 teams of 5 to 30 people; boards in the hundreds of tasks (assumption); about 10 simultaneous viewers per board in the acceptance test

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | How |
|---|---|---|
| I. Tests first for business logic | Pass | Each story phase starts with test tasks; each story has an independent test in spec.md |
| II. Observability | Pass | Structured logs, metrics (open SSE connections, publish failures) and traces for new endpoints; health check coverage via the F01 mechanism (see the Polish phase of tasks.md) |
| III. Security baseline | Pass | Membership check on every endpoint and the SSE stream; validation in Pydantic schemas; no secrets, Redis URL read from config in `app/core/config.py` |
| IV. Traceability | Pass | Source ids in spec; every task names file paths |
| V. Simplicity | Pass | No new infrastructure, no drag-and-drop library, no event replay buffer, no reorder inside columns |

Post-design re-check: Pass. The one added table (`task_assignment_events`) is required by FR-014 and avoids a second messaging system.

## Project Structure

### Documentation (this feature)

```text
specs/002-tasks-board/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── clarifications.md
├── contracts/
│   └── api.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (two repositories, paths follow implementation-contract.md)

```text
acme/taskflow-api
├── app/
│   ├── api/
│   │   ├── tasks.py              # task CRUD + move routes
│   │   └── board_view.py         # GET board (columns) + SSE events route
│   ├── models/
│   │   ├── task.py               # Task
│   │   └── task_assignment_event.py
│   ├── schemas/task.py           # request/response models, validation
│   ├── services/
│   │   ├── task_service.py       # create/update/move/delete, assignment event
│   │   ├── board_view_service.py # board read with Redis cache
│   │   └── board_events.py       # publish + subscribe via Redis pub/sub
│   └── core/                     # config, auth, db, redis: owned by feature 001, reused
├── migrations/versions/          # one new Alembic migration for this feature
└── tests/{unit,integration}/

acme/taskflow-web
└── src/
    ├── api/tasks.ts              # REST client for tasks and board
    └── features/board/
        ├── BoardPage.tsx
        ├── Column.tsx
        ├── TaskCard.tsx
        ├── TaskForm.tsx
        ├── ConfirmDeleteDialog.tsx
        ├── MoveMenu.tsx
        ├── useBoard.ts           # state, optimistic move, apply events
        ├── useBoardEvents.ts     # SSE client, reconnect, polling fallback
        ├── LiveAnnouncer.tsx     # aria-live region
        └── __tests__/
```

**Structure Decision**: web application split across the two existing repositories. Routes use the `/api/v1` prefix; the SSE path is `/api/v1/boards/{board_id}/events`. No feature flag: this feature is the core of the beta and ships on. The hook for feature 005 is the `task_assignment_events` table.

## Complexity Tracking

No constitution violations to justify.
