# Implementation Plan: Clinics, dentist hours, leave, treatments and free slots

**Branch**: `003-clinic-schedule-setup` | **Date**: 2026-11-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-clinic-schedule-setup/spec.md`

## Summary

Build the `cmp-scheduling` module of ctr-clinic-api and the staff screens in ctr-web that let the practice manager keep clinics, dentists, treatment types, weekly working hours with breaks and leave as data, and that give reception a "to move" list for their own clinic. The same module computes free slots (working hours minus breaks, leave and booked appointments, on the hour or half hour) for one clinic and one date range per request, and "first available" (top 10, paginated). Appointments are read through an in-process port that cmp-booking implements later; until then a stand-in returns none. Approach and trade-offs are in [research.md](research.md).

Covers prd.md: FR-001, FR-007, FR-008, FR-009, FR-010 (architecture QA-001, QA-011; assumptions ASM-010, PD-002).

## Technical Context

**Language/Version**: Python 3.12 (ctr-clinic-api); TypeScript with React (ctr-web) — from architecture.md section 4 and 13

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic (ctr-clinic-api); React SPA (ctr-web). No other libraries are introduced by this feature.

**Storage**: PostgreSQL 16 (ctr-db); entities ent-clinic, ent-dentist, ent-treatment-type, ent-working-hours (with breaks), ent-leave, plus one small settings table for the booking horizon. Times stored in UTC (timestamptz); weekly hours stored as IST wall-clock times of day.

**Testing**: pytest (unit, integration against PostgreSQL, contract tests against `contracts/clinic-api-v1.openapi.yaml`, a performance test); the web app's own test runner set up by the platform feature for component tests

**Target Platform**: Linux container (managed container service, 2 replicas); desktop Chrome/Safari for the staff screens

**Project Type**: web application (API module in clinic-api repo + screens in clinic-web repo)

**Performance Goals**: free slots within 2 s for 95% of requests on 4G (QA-001) = server p95 ≤ 500 ms (architecture section 10) at 100 concurrent users, about 35 requests/s design peak, for 3 clinics, 10 dentists, 1,000 appointments a week

**Constraints**: slots computed for one clinic and one date range (at most 31 days) per request; index on dentist and time; no cache (architecture section 3); times stored UTC and shown IST; no PII (names, phones) in logs; role checks on the server through cmp-identity's access context; read of appointments only through cmp-booking's in-process interface

**Scale/Scope**: 2 clinics today, 3 later; 6 dentists today, 10 later; about 450 to 1,000 appointments a week; 4 staff screens plus a reception to-move screen; 6 user stories

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Result |
|---|---|---|
| I. Tests first for business logic | Slot maths, overlap validation, to-move selection and role checks have tests written before or with the code; each user story has an independent test | Pass: test tasks precede implementation tasks in every story |
| II. Observability | Structured logs, metrics (slot-calculation duration) and traces for new endpoints; health check unchanged | Pass: task for timing metric and log fields; `GET /health` is owned by the platform feature |
| III. Security baseline | No secrets in code; inputs validated at boundaries; authorisation changes reviewed | Pass: Pydantic validation at the API edge; role checks via access context; no new secrets; no authorisation model changes (uses feature 002's) |
| IV. Traceability | Requirements and stories keep prd.md ids; every task names exact file paths | Pass |
| V. Simplicity | Smallest design; no speculative abstractions | Pass: no cache, no queue, no new tables beyond the five entities, their break rows and a settings row; one port for appointments |
| Technology constraints | Follow architecture.md; repos brightsmile/clinic-api and brightsmile/clinic-web | Pass: modular monolith module `cmp-scheduling`, in-process call to cmp-booking, REST under `/api` |
| Definition of Done | No patient data in logs; unit and contract tests in CI | Pass: logging test for to-move endpoints; contract tests |

Post-design re-check (after Phase 1): still passes. The only addition beyond the architecture's entity list is a settings row for the booking horizon, which architecture.md requires ("a setting", ASM-010).

## Project Structure

### Documentation (this feature)

```text
specs/003-clinic-schedule-setup/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── clarifications.md    # Assumed answers to open questions
├── contracts/
│   └── scheduling-api.openapi.yaml   # Operations added to clinic-api-v1
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

The two repositories are separate; paths below are prefixed with the repository folder name.

```text
clinic-api/                                   # brightsmile/clinic-api
├── app/modules/scheduling/
│   ├── __init__.py
│   ├── models.py            # SQLAlchemy: Clinic, Dentist, TreatmentType, WorkingHours, WorkingBreak, Leave, SchedulingSetting
│   ├── schemas_catalog.py   # request and response models: clinics, dentists
│   ├── schemas_treatments.py, schemas_hours.py, schemas_leave.py, schemas_slots.py
│   ├── access.py            # thin adapter over cmp-identity's access context (manager-only, own-clinic checks)
│   ├── ports.py             # AppointmentsPort (in-process interface for cmp-booking) and the empty stand-in
│   ├── ist.py               # IST and UTC helpers
│   ├── telemetry.py         # PII-free logging helpers, slot-duration metric
│   ├── router.py            # aggregates the REST routes under /api
│   ├── repository.py        # queries (indexed by dentist and time)
│   ├── api/                 # catalog.py, treatments.py, hours.py, leave.py, to_move.py, slots.py
│   ├── services/
│   │   ├── catalog.py       # clinics, dentists
│   │   ├── treatments.py    # treatment types
│   │   ├── hours.py         # weekly hours, breaks, overlap rules
│   │   ├── leave.py         # leave
│   │   ├── to_move.py       # to-move list
│   │   ├── slot_math.py     # pure interval functions
│   │   ├── slots.py         # free slots
│   │   └── first_available.py
│   └── jobs.py              # 24-month leave retention job
├── alembic/versions/xxxx_scheduling.py          # tables, indexes, 3 online treatment types, horizon setting
├── contracts/clinic-api-v1.openapi.yaml          # scheduling operations added
└── tests/scheduling/
    ├── unit/                 # slot_math, hours validation, to-move selection
    ├── integration/          # API + PostgreSQL, role tests
    ├── contract/             # against the OpenAPI file
    └── perf/                 # 100 concurrent users, p95 check

clinic-web/                                   # brightsmile/clinic-web
└── src/features/scheduling/
    ├── api.ts                # calls to /api scheduling routes
    ├── types.ts
    ├── time.ts               # IST display helpers
    ├── components/           # WeeklyHoursEditor, BreakRows, ToMoveTable
    ├── pages/                # ClinicsPage, DentistsHoursPage, LeavePage, TreatmentsPage, ToMovePage
    └── __tests__/
```

**Structure Decision**: web application split across the two repositories named in the constitution. The API module lives under `app/modules/scheduling/` following the architecture's one-module-per-component rule; screens live under one feature folder in the SPA. Exact base folders (`app/`, `src/`) follow the scaffolding made by the platform foundation feature (001); if its layout differs, only the path prefixes change.

## Complexity Tracking

No constitution violations to justify.
