# Implementation Plan: Dentist schedules, treatments and free slots

**Branch**: `002-schedules-slots` | **Date**: 2026-11-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-schedules-slots/spec.md`

## Summary

Module MOD-02 (component `cmp-scheduling` in `ctr-clinic-api`, plus three manager screens in `ctr-web`). The practice manager edits treatment types (FR-009), weekly hours with breaks per dentist per clinic (FR-007) and leave (FR-008). The module computes free slots live for one clinic and one date range (FR-010), including "first available" (top 10) and an in-process interface for the booking feature, and lists booked appointments inside a leave for reception (read through an appointment read interface owned by `cmp-booking`). Approach: SQLAlchemy models and Alembic migration for `treatment_type`, `working_hours`, `working_hours_break`, `leave`; a pure-Python slot engine that subtracts intervals (breaks, leave, booked appointments) from the working windows for the requested range, with one query per data kind per request (no per-dentist loops, no cache); manager-only authorisation through `cmp-identity` RBAC (feature 001). Scale target (NFR-003) is met by data-driven clinics and dentists, indexes on dentist and time, and a load test at 3 clinics / 10 dentists / 100 concurrent users (supports NFR-002).

## Technical Context

**Language/Version**: Python 3.12 (`clinic-api`); TypeScript with React (`clinic-web`)

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic, Pydantic (inside FastAPI); React SPA (architecture.md names no UI library, so none is added)

**Storage**: PostgreSQL 16 (`ctr-db`); times stored as UTC `timestamptz`; recurring weekly hours stored as IST wall-clock `time` plus weekday (see research.md)

**Testing**: pytest for `clinic-api` (unit tests for the slot engine, API tests with a test database, contract tests against the OpenAPI file, a load test script); the web test tooling is whatever `clinic-web` already uses (component tests for the three screens)

**Target Platform**: Linux container (managed container service) for the API; static CDN hosting for the SPA

**Project Type**: web application (two repositories: `brightsmile/clinic-api`, `brightsmile/clinic-web`)

**Performance Goals**: free slots shown within 2 s for 95% of requests on 4G (server p95 at or below 500 ms, architecture SLO); 100 concurrent users; about 35 requests/s design peak

**Constraints**: slots calculated live, no cache (architecture section 3); one clinic and one date range (max 31 days) per request; times UTC in storage and IST on screen; no patient name, phone or birth year in logs; manager-only writes; appointments read only through `cmp-booking`'s interface; no technology outside architecture.md

**Scale/Scope**: now 2 clinics, 6 dentists, about 450 appointments a week; later 3 clinics, 10 dentists, 1,000 a week; 4 user stories, 3 screens, 12 endpoints

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Tests first for business logic | Slot engine, hours and leave validation, treatment rules and the "to move" list each get tests listed before their implementation in tasks.md; every user story has an independent test | Pass |
| II. Observability | Structured logs and an OpenTelemetry timer/metric on the slot endpoints; the app's existing `GET /health` stays; new routers add no new service | Pass |
| III. Security baseline | Manager-only writes through RBAC from feature 001; receptionist clinic scoping; inputs validated by Pydantic at the boundary; no secrets added | Pass |
| IV. Traceability | Spec and tasks cite prd.md ids; each task names its file path and repo | Pass |
| V. Simplicity | One module, no cache, no broker, no extra libraries; leave retention by a simple scheduled job; horizon as one configuration value | Pass |
| Technology constraints | Follows architecture.md (`cmp-scheduling`, FastAPI, SQLAlchemy, Alembic, PostgreSQL 16, React) | Pass |
| Definition of Done | No patient data in logs (polish phase log-scan task), contract tests, acceptance checks | Pass |

Re-check after design (Phase 1): no new violations; Complexity Tracking not needed.

## Project Structure

### Documentation (this feature)

```text
specs/002-schedules-slots/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── scheduling-api.openapi.yaml
│   └── internal-interfaces.md
└── tasks.md
```

### Source Code

Repository `brightsmile/clinic-api` (Python, FastAPI):

```text
app/scheduling/
├── models/
│   ├── clinic.py              # ent-clinic, ent-dentist: created by feature 001, used here
│   ├── dentist.py
│   ├── treatment_type.py      # new
│   ├── working_hours.py       # new (working_hours, working_hours_break)
│   └── leave.py               # new
├── schemas/                   # Pydantic request/response models: treatments.py, hours.py, leave.py, slots.py
├── dependencies.py            # manager-only and clinic-scope dependencies built on cmp-identity
├── observability.py           # structured logging helper (ids only) and slot timing metric
├── ports.py                   # AppointmentReader protocol (implemented by cmp-booking)
├── services/
│   ├── treatments.py
│   ├── hours.py
│   ├── leave.py
│   ├── slot_engine.py         # pure interval maths
│   └── slots.py               # loads data, calls engine, first available, is_slot_free
├── routers/
│   ├── treatments.py
│   ├── hours.py
│   ├── leave.py
│   └── slots.py
├── jobs/leave_retention.py
└── settings.py                # booking_horizon_days (default 30), max_range_days (31)
alembic/versions/<rev>_scheduling.py
tests/scheduling/
├── unit/
├── api/
├── contract/
└── load/
```

Repository `brightsmile/clinic-web` (React SPA):

```text
src/features/scheduling/
├── api/                       # typed clients: treatments.ts, hours.ts, leave.ts
├── time.ts                    # IST formatting helpers
├── routes.tsx                 # the three manager routes
├── TreatmentsPage.tsx
├── DentistHoursPage.tsx
├── LeavePage.tsx
└── __tests__/
```

**Structure Decision**: two repositories as fixed by the constitution; backend code in a `scheduling` package of the modular monolith (one module per architecture component); screens grouped in one web feature folder. Exact parent paths follow the existing repository layout from feature 001; the paths above are relative to each repository root.

## Phases

- **Phase 0 (research.md)**: time storage, interval maths, appointment read interface, horizon setting, treatment seed data, leave retention.
- **Phase 1 (data-model.md, contracts/, quickstart.md)**: entities and constraints, REST contract, internal interfaces for booking, validation walk-through.
- **Dependencies on other features**: feature 001 (RBAC, clinics, dentists, staff accounts); features 003 and 005 (appointments, read interface). This feature defines the `AppointmentReader` port; the booking feature provides the real implementation. Until then tests use a fake reader.

## Complexity Tracking

No constitution violations to justify.
