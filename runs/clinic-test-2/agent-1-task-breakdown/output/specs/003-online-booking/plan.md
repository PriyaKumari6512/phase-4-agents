# Implementation Plan: Online booking by patients (MOD-03)

**Branch**: `003-online-booking` | **Date**: 2027-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-online-booking/spec.md`

## Summary

A signed-in patient books a 30-minute online treatment: clinic, treatment type, dentist or "first available", then a free slot within the next 30 days. The booking is one database transaction that inserts the appointment, its first "booked" history entry and the message rows (confirmation and reminder). A PostgreSQL exclusion constraint on (dentist, time range) for active appointments decides the winner of any race (ADR-0003); the loser gets HTTP 409 with the next free slots. A retry key makes repeats safe. The confirmation is delivered after commit by the dispatcher, never in the request. The web app has four screens: who and what, slot picker, confirm, booked. Three test stories prove 0 overlaps in 1,000 concurrent runs (QA-003), speed (QA-001/002) and mobile usability (QA-010).

Source ids: FR-011, FR-012, NFR-001, NFR-002, NFR-010 (prd.md); QA-001, QA-002, QA-003, QA-010; ASM-010; ADR-0003.

## Technical Context

**Language/Version**: Python 3.12 (ctr-clinic-api, repo brightsmile/clinic-api); TypeScript with React (ctr-web, repo brightsmile/clinic-web)

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic (api); React SPA (web). No other libraries are introduced by this feature.

**Storage**: PostgreSQL 16 with `btree_gist` (ctr-db); tables `appointment`, `appointment_event`, `booking_request` created here

**Testing**: pytest for the api (unit, contract against the OpenAPI file, integration against PostgreSQL, concurrency and load scripts in Python); the web repo's own test runner for screen tests (the runner is set by the web repo and is not named in architecture.md); mobile acceptance is a device checklist run on current Chrome and Safari on Android and iPhone

**Target Platform**: Linux container (api); static site on CDN viewed in current Chrome and Safari on Android and iPhone (web)

**Project Type**: web application (two repos: clinic-api, clinic-web)

**Performance Goals**: free slots shown within 2 s and booking confirmed within 3 s for 95% of requests on 4G; server p95 <= 500 ms for slots and <= 800 ms for booking at 100 concurrent users (QA-001, QA-002)

**Constraints**: 0 overlapping active appointments for one dentist in 1,000 concurrent-attempt runs (QA-003); client timeout 10 s; booking writes never retried automatically; confirmation sent after commit; "first available" returns the top 10; patient may book only for their own account (server-side); no patient name or phone number in logs; all times IST for display, UTC in storage

**Scale/Scope**: 30 patients booking at once now, designed for 100; 3 clinics, 10 dentists, 1,000 appointments a week later; 4 screens, 3 endpoints, 3 tables

## Constitution Check

*GATE: passed before Phase 0 and again after Phase 1.*

| Principle | Check | Result |
|---|---|---|
| I. Tests first | Every story has an independent test; tests are listed before implementation in each story phase of tasks.md | Pass |
| II. Observability | Booking and slot endpoints emit structured logs (ids and a correlation id only), booking outcome counters and latency metrics (OpenTelemetry); new routes sit behind the existing `GET /health` service | Pass |
| III. Security baseline | Server-side authorisation: person taken from the signed-in session, request ids never trusted; inputs validated at the boundary; CSRF header on writes; no secrets added | Pass |
| IV. Traceability | Stories and requirements carry prd ids; every task names exact file paths and repo | Pass |
| V. Simplicity | No broker, no cache, no new library; one database transaction; one small table for retry keys; the "blocked" check is a one-method interface, not a framework | Pass |

Technology: only those named in architecture.md (FastAPI, SQLAlchemy, Alembic, PostgreSQL with btree_gist, React SPA). No violations; Complexity Tracking not needed.

## Project Structure

### Documentation (this feature)

```text
specs/003-online-booking/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── clarifications.md
├── contracts/
│   └── online-booking.openapi.yaml
├── checklists/requirements.md
└── tasks.md
```

### Source Code

```text
# repo brightsmile/clinic-api  (cmp-booking in ctr-clinic-api)
app/modules/booking/
├── __init__.py
├── models.py            # Appointment, AppointmentEvent, BookingRequest (SQLAlchemy)
├── schemas.py           # request/response models
├── ports.py             # SlotSource (cmp-scheduling), BookingMessages (cmp-messaging), BlockPolicy (cmp-noshow-policy)
├── slots.py             # patient slot lookup, "first available" top 10, horizon check
├── service.py           # book(): checks, transaction, conflict handling, idempotency
├── router.py            # GET /api/booking/options, GET /api/booking/slots, POST /api/appointments
└── settings.py          # booking_horizon_days (default 30)
alembic/versions/0003_online_booking.py
tests/booking/
├── unit/                # horizon, first available, block-policy default, authorisation
├── contract/            # against contracts/online-booking.openapi.yaml
├── integration/         # booking, conflict, idempotency, history, message rows
├── concurrency/         # QA-003 runs
└── performance/         # QA-001, QA-002 load script

# repo brightsmile/clinic-web  (ctr-web)
src/features/booking/
├── api.ts               # calls /api/booking/* and POST /api/appointments, 10 s timeout, no auto retry
├── bookingState.ts      # choices kept across screens and Back
├── WhoAndWhatScreen.tsx
├── SlotPickerScreen.tsx
├── ConfirmScreen.tsx
├── BookedScreen.tsx
├── booking.css          # mobile-first, 44 px targets
└── __tests__/           # screen tests and mobile acceptance checklist
```

**Structure Decision**: web application over two repos. All API code lives in the existing module folder for cmp-booking; the web app gets one feature folder. Slot calculation stays in cmp-scheduling (MOD-02); this feature adds only the patient-facing lookup on top of it.

## Phase 0 and Phase 1 outputs

- [research.md](research.md): decisions on the exclusion constraint, retry key, conflict answer, "first available", the three ports, load-test approach.
- [data-model.md](data-model.md): the three tables, constraint, indexes, status values.
- [contracts/online-booking.openapi.yaml](contracts/online-booking.openapi.yaml): the three operations added to api-clinic-api-v1.
- [quickstart.md](quickstart.md): how to run the happy path, the race and the performance check.

## Dependencies on other features

| Needs | From | If not ready |
|---|---|---|
| Patient session and the signed-in person (account holder) | feature 001 (identity, MOD-01) | Tests use a fake signed-in patient fixture |
| Free-slot calculation, clinics, dentists, treatment types with online flag | MOD-02 (scheduling) | `SlotSource` port with an in-memory fake for tests |
| Create confirmation and reminder message rows in the same transaction | feature 006 (messaging, MOD-07) | `BookingMessages` port with a stub that writes nothing; replaced by 006's adapter |
| Later status changes and history screen | feature 005 | This feature only writes the "booked" entry |
| "Is patient blocked" | cmp-noshow-policy (R2) | `BlockPolicy` default returns "not blocked" |

## Estimate note

scope/estimate.md gives MOD-03 as 9 to 14 person-days. The task list is sized to stay in that range at 6 hours per story point; the three test stories are kept small by reusing the same fixtures.
