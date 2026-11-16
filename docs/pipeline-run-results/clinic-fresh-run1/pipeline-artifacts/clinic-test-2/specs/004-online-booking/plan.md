# Implementation Plan: Patient online booking

**Branch**: `004-online-booking` | **Date**: 2026-11-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-online-booking/spec.md`

## Summary

A signed-in patient books an online treatment (check-up, cleaning, consultation; 30 minutes) at a clinic with a named dentist or "first available", for a free slot in the next 30 days. The booking module (`cmp-booking`) owns the appointment and its history. The decision on who wins a contested slot is made by the database: an exclusion constraint on (dentist, time range) for active appointments (ADR-0003, `btree_gist`). The insert of the appointment, its history row, the confirmation and reminder rows (through a messaging port) and the remembered channel is one transaction. A lost race returns HTTP 409 `slot_taken` with the next free slots. A request key (`Idempotency-Key`) makes a retry return the original booking. Confirmation messages are sent after commit by the dispatcher of feature 007, not inside the request (QA-002). The web app (`ctr-web`) adds four patient screens: who and what, slot picker, confirm, booked (4 screens after sign-in, within the NFR-010 limit of 5). The feature also delivers the concurrency test (QA-003: 0 overlapping active appointments in 100% of 1,000 runs) and a performance check for NFR-002 (QA-001, QA-002).

## Technical Context

**Language/Version**: Python 3.12 (ctr-clinic-api); TypeScript with React (ctr-web) — from architecture.md section 4.

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic (ctr-clinic-api); React SPA served from CDN (ctr-web); OpenTelemetry for logs, metrics and traces (constitution II). No new runtime dependency is introduced by this feature.

**Storage**: PostgreSQL 16 with the `btree_gist` extension (ctr-db). New tables `appointment`, `appointment_event`, `booking_request`; new column `preferred_channel` on the patient account table (owned by cmp-identity).

**Testing**: Test runner not named in architecture.md. Assumption: pytest with pytest-asyncio and httpx for the API and the concurrency test; the web project's own unit-test runner (set up by feature 001, assumed Vitest with React Testing Library) for screens; contract tests against `contracts/clinic-api-v1.openapi.yaml` (CI step in architecture section 8). Open question for feature 001 to confirm.

**Target Platform**: Linux container on the managed container service (ctr-clinic-api); static site on CDN (ctr-web); patients use current Chrome and Safari on Android and iPhone.

**Project Type**: web application (two repositories: `brightsmile/clinic-api`, `brightsmile/clinic-web`).

**Performance Goals**: Free slots shown within 2 s and booking confirmed within 3 s for 95% of requests on 4G (NFR-002; QA-001, QA-002). Server p95 at most 500 ms for the slot list and at most 800 ms for a booking. Design peak about 35 requests/s (100 concurrent patients, one request every 3 s).

**Constraints**: Confirmation sent after commit, never inside the request. Booking insert, history row, message rows and channel update in one transaction. Authorisation from the token owner, never from request ids (thr-004). No patient name, phone or birth year in logs. Times stored in UTC and shown in IST. English only. Writes are never retried automatically by the web client (the `Idempotency-Key` allows a safe manual retry).

**Scale/Scope**: 2 clinics now (3 later), 6 dentists (10 later), about 450 appointments a week (1,000 later); 4 screens; 2 endpoints plus one options read; 3 tables.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Tests first for business logic | Every story has an independent test; unit tests for booking rules and contract tests are written before or with code (see tasks.md); QA-003 concurrency test is its own story | Pass |
| II. Observability | New endpoints emit structured logs, OpenTelemetry metrics (booking attempts, slot-taken, durations) and traces; the existing `GET /health` is reused and not duplicated | Pass |
| III. Security baseline | Patient taken from the token; inputs validated at the boundary; no secrets added; authorisation-affecting code (patient dependency use) flagged for review in tasks | Pass |
| IV. Traceability | Spec stories and requirements carry prd.md ids; each task names exact file paths | Pass |
| V. Simplicity | No new library, no cache, no queue; one table for idempotency; the no-show and messaging ports are thin interfaces with stub implementations because features 007 and 009 are separate | Pass |
| Technology constraints | architecture.md followed (modular monolith, FastAPI, PostgreSQL exclusion constraint, React SPA) | Pass |
| Definition of Done | No patient data in logs (test task T063); unit and contract tests in CI | Pass |

Re-check after Phase 1 design: Pass. No complexity violations.

## Phase 0 and Phase 1 artifacts

- [research.md](research.md): decisions and open assumptions.
- [data-model.md](data-model.md): tables, constraint, transaction steps and state rules.
- [contracts/booking-api.openapi.yaml](contracts/booking-api.openapi.yaml): the operations this feature adds to `api-clinic-api-v1`.
- [quickstart.md](quickstart.md): how to validate the feature end to end.

## Project Structure

### Documentation (this feature)

```text
specs/004-online-booking/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── clarifications.md    # Assumed answers to open questions Q1-Q3
├── contracts/
│   └── booking-api.openapi.yaml
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (two repositories)

The module layout follows architecture.md (one module per component inside the one FastAPI deployable). Paths of other features' modules are assumed from the component names; the feature that owns them confirms the exact file.

```text
brightsmile/clinic-api
├── app/
│   ├── booking/                      # cmp-booking (this feature owns)
│   │   ├── __init__.py
│   │   ├── models.py                 # Appointment, AppointmentEvent, BookingRequest (SQLAlchemy)
│   │   ├── schemas.py                # request and response models
│   │   ├── router.py                 # /api/booking/options, /slots, /appointments
│   │   ├── service.py                # book_online(), next_slots_after_conflict()
│   │   ├── idempotency.py            # request key handling
│   │   ├── errors.py                 # SlotTaken, NotBookableOnline, BookingBlocked, KeyReused
│   │   ├── ports.py                  # PolicyPort (blocked?), MessagingPort, SchedulingPort protocols
│   │   ├── adapters.py               # default NotBlockedPolicy, NoopMessaging until features 009 and 007
│   │   └── telemetry.py              # metrics and span names, no PII
│   ├── scheduling/                   # cmp-scheduling (feature 003 owns; consumed here)
│   │   └── slots.py                  # list_free_slots(), is_slot_free(), online treatment lookup
│   └── identity/                     # cmp-identity (feature 002 owns; consumed and extended here)
│       ├── access.py                 # patient access context from the token (consumed)
│       └── channel.py                # get and set preferred channel (added here)
├── migrations/versions/
│   ├── 004a_booking_tables.py        # btree_gist, appointment, appointment_event, booking_request, constraint
│   └── 004b_patient_channel.py       # preferred_channel column on the patient account table
└── tests/
    ├── unit/booking/
    ├── contract/booking/
    ├── integration/booking/
    ├── concurrency/booking/          # QA-003
    └── performance/booking/          # NFR-002 (QA-001, QA-002)

brightsmile/clinic-web
└── src/
    ├── app/routes.tsx                # adds the /book routes (edited)
    └── features/booking/
        ├── api.ts
        ├── types.ts
        ├── BookingFlowContext.tsx
        ├── pages/WhoAndWhatPage.tsx
        ├── pages/SlotPickerPage.tsx
        ├── pages/ConfirmPage.tsx
        ├── pages/BookedPage.tsx
        ├── components/ClinicTreatmentForm.tsx
        ├── components/DentistChoice.tsx
        ├── components/DayStrip.tsx
        ├── components/SlotList.tsx
        ├── components/ChannelChoice.tsx
        ├── components/SlotTakenNotice.tsx
        ├── components/BlockedNotice.tsx
        └── __tests__/
```

**Structure Decision**: Web application layout over the two repositories named in the constitution, one module directory per architecture component. The concurrency and performance tests sit in the API repository's `tests/` tree and run in CI (architecture section 8).

## Key design points

1. **Winner decided by the database.** `appointment_no_overlap` is `EXCLUDE USING gist (dentist_id WITH =, tstzrange(start_at, end_at, '[)') WITH &&) WHERE (status IN ('booked','arrived','no_show'))`. The application checks that the slot is free first (to give a fast, clear answer), but only the constraint is trusted. The application user has no DDL rights (thr-011).
2. **One transaction.** In order: claim the request key, insert the appointment, insert the first history row, call `MessagingPort.enqueue_booking_messages(...)` (rows for confirmation and reminder, created by feature 007), update the remembered channel, commit. Any failure rolls back everything.
3. **Slot taken.** The exclusion violation (SQLSTATE 23P01) is mapped to HTTP 409 `slot_taken`. After rollback, in a fresh read, the next free slots are returned (top 10, same clinic, treatment and dentist choice, from the taken slot's time).
4. **Idempotency.** `Idempotency-Key` header is required on `POST /api/booking/appointments`. The pair (patient account, key) is unique. A repeat with the same body returns the stored appointment (HTTP 200 with header `Idempotent-Replay: true`); a repeat with a different body returns 422 `idempotency_key_reused`.
5. **After commit.** The request does not call a provider. The dispatcher of feature 007 claims the message rows after commit (ADR-0002). Until feature 007 exists the messaging port is a no-op, so bookings work and the confirmation is simply not sent.
6. **Blocked check.** `PolicyPort.is_blocked(person_id)` is called on the slot read and again inside the booking step. The default adapter returns not blocked. Feature 009 replaces the adapter.
7. **Authorisation.** The patient and account come from the access context of cmp-identity; the booking request carries no patient id in the MVP.
8. **Performance.** Slot list: one clinic, one date range per request, indexed by dentist and time; "first available" limited to 10 slots (QA-001 tactic). Booking: about 8 queries, no external calls (QA-002 tactic).
9. **Web.** Four screens; one page state held in a flow context; the channel preference is preselected from the options read; "slot taken" returns the patient to the slot picker with the new slots and a notice, keeping clinic, treatment and channel.

## Dependencies on other features

| Needs | From | If missing |
|---|---|---|
| Signed-in patient access context, patient account and person tables | feature 002 (cmp-identity) | Blocking: cannot authorise or link a patient |
| Clinics, dentists, treatment types (online flag), free-slot calculation, 30-day horizon setting | feature 003 (cmp-scheduling) | Blocking: no slots to offer |
| Confirmation and reminder rows, dispatcher | feature 007 (cmp-messaging) | Port is a no-op; no message is sent |
| "Is blocked?" answer | feature 009 (cmp-noshow-policy) | Default adapter answers not blocked |
| Web app shell, routing, English catalogue, IST formatting, CI | feature 001 | Blocking for screens |
| Appointment list and reschedule or cancel | feature 005 | Not needed here |

## Complexity Tracking

No constitution violations.
