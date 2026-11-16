# Implementation Plan: Reception day view, check-in, no-shows and dentist day (MOD-05)

**Branch**: `005-reception-day` | **Date**: 2027-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-reception-day/spec.md`

## Summary

Release 1 feature MOD-05 (deadline DL-1 2027-02-22). Reception runs the day of one clinic: a day view with one column per working dentist, arrived and no-show (from 15 minutes after start until the end of the day in IST, undoable the same day), patient search and creation across all patients, reception-side booking, moving and cancelling without the 4-hour rule (including reception-only 60/90-minute types and walk-ins), and a read-only "my day" for dentists. Every status change is written to the appointment history with who and when (FR-024).

Approach (from architecture.md): `cmp-reception` in `ctr-clinic-api` serves the day view, dentist day, patient search/create and the arrive / no-show / undo endpoints. It calls `cmp-booking`, which owns appointments and applies the status rules and the history write in one transaction, and the reception-side book / move / cancel without the 4-hour rule. `cmp-identity` supplies the access context (role, clinic, dentist id) and owns patients. `cmp-scheduling` supplies working hours, treatment types and free slots. The same database exclusion constraint on overlapping appointments (ADR-0003) prevents double booking. `ctr-web` gets the reception screens (day view, appointment panel, book for patient, patient search) and the dentist's "my day". Messages after a reception change are requested from `cmp-messaging` (feature 006).

## Technical Context

**Language/Version**: Python 3.12 (ctr-clinic-api, repo `brightsmile/clinic-api`); TypeScript with React (ctr-web, repo `brightsmile/clinic-web`)

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic (ctr-clinic-api); React SPA (ctr-web). No new libraries.

**Storage**: PostgreSQL 16 (ctr-db) with `btree_gist`. Uses `ent-appointment`, `ent-appointment-event` (table created by feature 003), `ent-patient-account`, `ent-patient`. No new table; see data-model.md.

**Testing**: automated tests for business logic written first (constitution I): unit tests for the status rules and IST day boundaries, integration tests against PostgreSQL for each endpoint and role, contract tests against `contracts/clinic-api-v1.openapi.yaml`, a concurrency test for the no-overlap rule, component tests in ctr-web with the runner set up by the web scaffold. The backend runner is the one set up by the clinic-api scaffold (pytest).

**Target Platform**: Linux container (ctr-clinic-api); desktop browser for reception, phone or PC browser for the dentist (ctr-web, current Chrome and Safari)

**Project Type**: web application (modular monolith API plus React SPA)

**Performance Goals**: day view for 6 columns about 15 KB and under 2 s for 95% of requests (server p95 at most 500 ms, QA-001 / NFR-002); status actions under 1 s server side

**Constraints**: reception screens available 08:00 to 20:00 Monday to Saturday (QA-005, NFR-004); clinic scoping enforced server side in every operation (QA-007, NFR-006); all times stored in UTC, day boundaries and the no-show window in IST (NFR-008); no patient name or phone in logs (constitution DoD); writes are never retried automatically (rel-005)

**Scale/Scope**: 2 clinics now, 3 later; up to 6 dentist columns of about 16 appointments; about 450 appointments a week (1,000 later); 5 user stories, about 12 endpoints, 5 screens

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Tests first for business logic | Tests precede implementation in every story phase; every story has an independent test in spec.md | Pass |
| II. Observability | New endpoints emit structured logs, metrics and traces (OpenTelemetry); `GET /health` already exists in ctr-clinic-api; task T053 adds spans and counters for status changes | Pass |
| III. Security baseline | No secrets; RBAC and clinic scoping from the server-side access context; inputs validated at the boundary (phone, name, dates, enums). Authorisation changes are limited to using the access context of feature 001; review requested | Pass |
| IV. Traceability | Every user story and FR in spec.md carries its prd.md ids; every task names its file path and repo | Pass |
| V. Simplicity | No new tables, no cache, no queue, no new library; optimistic concurrency by conditional update instead of a version column | Pass |

Post-design re-check (after Phase 1): Pass. No violations, so Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/005-reception-day/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── clarifications.md    # Assumed answers (Q-015 walk-in, undo of arrived)
├── contracts/
│   └── reception-day.openapi.yaml   # Paths added to api-clinic-api-v1
├── checklists/requirements.md
└── tasks.md             # Phase 2 output
```

### Source Code

Two repositories (architecture section 13). Paths follow the module layout of the clinic-api scaffold (`app/modules/<component>/`); if the scaffold from feature 001 differs, tasks keep the same relative layout under its root.

```text
# repo: brightsmile/clinic-api (ctr-clinic-api)
app/
├── core/
│   └── time_ist.py                      # IST day start/end, injectable clock
├── modules/
│   ├── reception/                       # cmp-reception
│   │   ├── router.py                    # day view, dentist day, router wiring
│   │   ├── status_router.py             # arrive, no-show, undo
│   │   ├── patient_router.py            # patient search, create
│   │   ├── booking_router.py            # slots, book, move, cancel (reception)
│   │   ├── dentist_router.py            # GET /api/dentist/my-day
│   │   ├── day_view.py                  # day view query
│   │   ├── dentist_day.py               # dentist's own day query
│   │   ├── access.py                    # receptionist / dentist access helpers
│   │   ├── schemas.py
│   │   └── telemetry.py
│   ├── booking/                         # cmp-booking
│   │   ├── status_rules.py              # statuses, allowed transitions, no-show window
│   │   ├── status_service.py            # change_status + history row, one transaction
│   │   ├── reception_service.py         # reception book, move, cancel (no 4-hour rule)
│   │   └── history_router.py            # GET appointment history
│   ├── scheduling/slots.py              # reception variant of free slots (feature 002 file)
│   └── identity/patient_service.py      # search and create patient (cmp-identity)
tests/
├── unit/
├── integration/
├── contract/
└── security/

# repo: brightsmile/clinic-web (ctr-web)
src/
├── features/
│   ├── reception/
│   │   ├── api/                         # API clients
│   │   ├── DayViewPage.tsx
│   │   ├── AppointmentPanel.tsx
│   │   ├── BookForPatient.tsx
│   │   └── PatientSearch.tsx
│   └── dentist/
│       ├── api/
│       └── MyDayPage.tsx
└── app/routes.tsx
```

**Structure Decision**: Web application with two repositories as fixed by the architecture. Backend logic is split between `cmp-reception` (read models and routing for reception and dentist screens) and `cmp-booking` (status rules, history and reception-side booking), matching the component table in architecture.md. Screens live in ctr-web under feature folders.

## Complexity Tracking

No constitution violations; nothing to justify.
