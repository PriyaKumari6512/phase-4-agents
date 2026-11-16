# Implementation Plan: Reception day view, check-in, no-show and dentist day

**Branch**: `006-reception-dentist-day` | **Date**: 2026-11-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-reception-dentist-day/spec.md`

## Summary

Build the reception and dentist day screens and their API (module `cmp-reception`), plus the reception-side booking, move, cancel and status-change operations in `cmp-booking`. The day view is one read per clinic and date (about 15 KB for 6 dentist columns of about 16 appointments). Arrived, no-show and undo are status changes done by `cmp-booking`, each writing a row in `ent-appointment-event` with actor and time, using a conditional update so a stale screen cannot overwrite a newer status. Reception booking uses the same insert path as online booking, so the database exclusion constraint (ADR-0003) is the one guarantee against double booking; only the 4-hour cut-off and the 30-day horizon are skipped. Clinic scoping is taken from the staff account through `cmp-identity`'s access context, never from ids in the request. Messages for reception changes are requested from `cmp-messaging` (feature 007) and are not built here.

## Technical Context

**Language/Version**: Python 3.12 (ctr-clinic-api); TypeScript with React (ctr-web) — as named in architecture.md

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic (ctr-clinic-api); React SPA (ctr-web). No new libraries or services.

**Storage**: PostgreSQL 16 (ctr-db) with `btree_gist` already in place for ADR-0003. Entities used: ent-appointment, ent-appointment-event, ent-patient, ent-patient-account, ent-staff-account, ent-clinic, ent-dentist, ent-treatment-type, ent-working-hours, ent-leave (read).

**Testing**: pytest for unit, integration (real PostgreSQL for the constraint and concurrency) and contract tests against `contracts/clinic-api-v1.openapi.yaml`; per-role tests for every operation (QA-007); front-end component tests for the screens. Test tooling names for ctr-web are decided in feature 001.

**Target Platform**: Reception screens: current desktop Chrome or Safari at the reception PC (A-001, A-002). Dentist screen: phone or clinic PC browser. Server: managed container service (ADR-0005).

**Project Type**: Web application: ctr-clinic-api (repo brightsmile/clinic-api) and ctr-web (repo brightsmile/clinic-web).

**Performance Goals**: Day view for 6 columns × about 16 appointments loads within 2 s for 95% of loads (SC-001, our proposal from NFR-002); server p95 for the day view ≤ 500 ms; a status change ≤ 800 ms server p95 (same as a booking). Design peak is about 10 reception sessions refreshing every 30 s, about 0.3 requests/s (architecture capacity estimate).

**Constraints**: Reception screens available 08:00–20:00 Monday to Saturday (QA-005); times stored in UTC and shown in IST; English only; no patient name, phone or birth year in logs; writes carry the CSRF header (ADR-0004) and are never retried automatically (rel-005); read retried once.

**Scale/Scope**: 2 clinics, 6 dentists, about 450 appointments a week now; 3 clinics, 10 dentists, 1,000 a week later (QA-006). 7 user stories, about 11 endpoints, 5 screens (day view, appointment panel, book for patient, patient search, my day).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | How |
|---|---|---|
| I. Tests first for business logic | Pass | Each story has an independent test; tasks put tests before implementation: the 15-minute and end-of-day rules, status conflicts, the no-overlap constraint under concurrency, clinic scoping per role. |
| II. Observability | Pass | New endpoints emit structured logs, metrics and traces (OpenTelemetry) with ids and correlation id; `GET /health` already exists from feature 001. |
| III. Security baseline | Pass | No secrets added. Inputs validated at the boundary (date, query, phone, ids). Authorisation changes are limited to using the access context; review is requested for the scoping code. |
| IV. Traceability | Pass | Every story and requirement cites prd.md ids; every task names exact file paths. |
| V. Simplicity | Pass | No new service, table, cache, queue or extension. One new index only if missing. |
| Definition of Done: no patient data in logs | Pass | A logging test checks that name and phone do not appear in log output for search, create and booking. |

Re-check after Phase 1 design: still pass. Complexity Tracking: no violations.

## Project Structure

### Documentation (this feature)

```text
specs/006-reception-dentist-day/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── clarifications.md
├── contracts/
│   └── reception-dentist-day.openapi.yaml
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

The module layout follows the one set up by feature 001 (one package per architecture component under `app/modules/`); paths below are the intended ones for this feature.

```text
# brightsmile/clinic-api  (ctr-clinic-api)
app/modules/reception/
├── router.py            # aggregates the sub-routers under /api
├── routes_day.py        # GET /reception/day, GET /reception/appointments/{id}
├── routes_status.py     # arrived, no-show, undo-no-show
├── routes_patients.py   # GET and POST /reception/patients
├── routes_booking.py    # slots, book, reschedule, cancel
├── routes_dentist.py    # GET /dentist/my-day
├── schemas_day.py, schemas_status.py, schemas_patients.py, schemas_booking.py, schemas_dentist.py
├── day_view.py          # day view query for one clinic and date
├── dentist_day.py       # dentist's own day, grouped by clinic
├── patient_search.py    # validation and mapping for patient search
└── status_rules.py      # 15-minute and same-day rules (pure functions, IST)
app/modules/booking/
├── reception_service.py # book, walk-in, reschedule, cancel without cut-off
└── status_service.py    # arrived, no-show, undo; conditional update + event row
app/modules/identity/
├── access.py            # receptionist clinic scope, dentist own-day (extended)
└── patient_service.py   # find patients, find or create by phone (extended)
app/modules/messaging/
└── interface.py         # no-op interface only if feature 007 has not added it
alembic/versions/
└── <rev>_appointment_clinic_start_index.py
tests/
├── unit/reception/      # status_rules
├── integration/reception/  # day view, status changes, booking, concurrency, scoping, logging
├── contract/            # reception endpoint tests vs the OpenAPI file
└── performance/         # day view load

# brightsmile/clinic-web  (ctr-web)
src/features/reception/
├── DayViewPage.tsx
├── AppointmentPanel.tsx
├── BookForPatient.tsx
├── CancelDialog.tsx
├── PatientSearch.tsx
└── dayApi.ts, statusApi.ts, patientApi.ts, bookingApi.ts
src/features/dentist/
├── MyDayPage.tsx
└── api.ts
src/routes/              # guards.tsx and index.tsx (extended)
src/lib/istDate.ts       # IST formatting helpers
tests/reception/, tests/dentist/   # component tests for the five screens
```

**Structure Decision**: Web application, two repositories as named in the constitution. Backend code goes in the existing modules `reception`, `booking` and `identity`; the web code goes in two feature folders. `cmp-reception` never writes appointments itself: it calls `cmp-booking` in process (architecture rel: cmp-reception → cmp-booking).

## Design Notes

- **Clinic scoping**: the receptionist's clinic comes from the staff account loaded on each request (ADR-0004); endpoints take no clinic id. Appointment ids from the request are looked up with `clinic_id = receptionist's clinic` in the same query; a miss returns 404, so another clinic's data is not revealed (thr-004, thr-007). Patient search is the one cross-clinic read (ASM-011) and returns only name and phone.
- **Status rules** (`status_rules.py`, pure and unit-tested): arrived — status booked and appointment date = today IST; no-show — status booked and `now ≥ start + 15 min` and `now < next midnight IST after start`; undo — status no-show and today IST = appointment date. The same rules decide which actions the panel offers (returned as `allowed_actions`) and are re-checked on submit.
- **Stale status**: the update is `UPDATE … SET status = :new WHERE id = :id AND clinic_id = :clinic AND status = :expected`; zero rows means 409 with the current status. The event row is inserted in the same transaction.
- **Booking**: one transaction inserts the appointment and its event row (and the arrived event for a walk-in) and asks `cmp-messaging` for the confirmation and reminder rows; on exclusion-constraint violation, 409 with the next free slots (QA-003). An idempotency key on the request prevents a retried click from booking twice (QA-003 tactic).
- **Reschedule**: update of dentist and time on the same row in one transaction with an event row (reason "moved by reception"); same constraint; messaging asked to replace the reminder and send a change notice.
- **Cancel**: status becomes `cancelled by the patient` or `cancelled by the clinic` from the receptionist's choice (ASM-014); the slot is free at once because the exclusion constraint covers active statuses only.
- **Day view**: one query joins appointments, patients (name, phone) and treatment types for one clinic and one IST date range, plus working hours for the columns; cancelled appointments are excluded from the columns. Index on clinic and start time. The web app polls every 30 s.
- **Dentist day**: appointments where `dentist_id` is the dentist linked to the staff account, today IST, at every clinic; response has no phone number and no write endpoints for the dentist role.

## Complexity Tracking

No constitution violations to justify.
