# Implementation Plan: Patient appointments: view, reschedule, cancel

**Branch**: `004-patient-appointments` | **Date**: 2026-11-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-patient-appointments/spec.md`

## Summary

A signed-in patient lists their upcoming and past appointments (grouped per person of the account), opens one, and cancels or reschedules it until 4 hours before the start; inside 4 hours the screen shows the clinic's phone number. The freed slot is bookable at once and the patient gets a change message in the channel chosen for the appointment. The reschedule/cancel link in messages deep-links to the appointment after sign-in.

Approach (architecture.md, ADR-0001 modular monolith): the work lives in `cmp-booking` of `ctr-clinic-api` (4-hour rule, list, cancel, reschedule, history) and in `ctr-web` (four screens). `cmp-booking` uses `cmp-scheduling` for free slots and the clinic phone number, `cmp-messaging` for the change message and for withdrawing and recreating reminder rows, and a `RescheduleRule` interface that `cmp-noshow-policy` implements in Release 2 (always allows in Release 1). Cancel and reschedule run in one database transaction with the appointment row lock, the history row (`ent-appointment-event`) and the message and reminder row changes. The no-overlap exclusion constraint (ADR-0003) decides races and covers active statuses only, so a cancelled appointment frees its slot at once.

## Technical Context

**Language/Version**: Python 3.12 (ctr-clinic-api, repo brightsmile/clinic-api); TypeScript with React (ctr-web, repo brightsmile/clinic-web)

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic (clinic-api); React SPA served from CDN (clinic-web). No new dependency is added.

**Storage**: PostgreSQL 16 (ctr-db) with `btree_gist`; no new table. Uses `ent-appointment`, `ent-appointment-event`, `ent-message` (feature 003 / 006 schemas) and reads `ent-clinic` (phone), `ent-dentist`, `ent-treatment-type`, `ent-patient`, `ent-patient-account`.

**Testing**: pytest with the project's FastAPI test client against PostgreSQL for clinic-api (constitution: tests first for business logic); the web repo's existing test runner for screens; contract tests against `contracts/clinic-api-v1.openapi.yaml` in CI.

**Target Platform**: Linux container service (API); current Chrome and Safari on Android and iPhone (web)

**Project Type**: web application: backend API plus React SPA

**Performance Goals**: list and appointment screens within 2 s and cancel or reschedule confirmed within 3 s for 95% of requests on 4G (NFR-002, QA-001, QA-002); freed slot visible to the next slot query at once (same transaction commit)

**Constraints**: 4-hour rule enforced on the server (online only; reception has no cut-off, feature 005); times stored in UTC, shown in IST (NFR-008); tap targets at least 44 px, no sideways scrolling (NFR-001, NFR-010); no patient name or phone in logs; CSRF header on writes and cookie session (ADR-0004); writes are never retried automatically by the client (rel-005)

**Scale/Scope**: about 450 appointments a week now, 1,000 later; 100 concurrent users design peak; 4 screens, 4 endpoints plus a slot endpoint; MOD-04 estimate 4-7 person-days

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Tests first for business logic | Tasks put tests (4-hour rule, cancel, reschedule, RBAC, race) before the implementation in each story; each story has an independent test | Pass |
| II. Observability | Structured logs with correlation id, OpenTelemetry counters for cancel, reschedule, refused-by-window and slot-conflict; no new service so the existing `GET /health` stays | Pass |
| III. Security baseline | Ownership check from the token's account on every operation (thr-004, thr-007); "not found" instead of "forbidden" (no enumeration); CSRF header on writes; inputs validated by schemas; no secrets | Pass |
| IV. Traceability | Spec items cite FR-015 to FR-018; every task names exact paths | Pass |
| V. Simplicity | No new table, no new service; the no-show hook is one small interface with one implementation; no speculative abstractions | Pass |

Post-design re-check (after Phase 1): still Pass. No violations, so Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/004-patient-appointments/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── clarifications.md
├── contracts/
│   └── patient-appointments.openapi.yaml
├── checklists/requirements.md
└── tasks.md
```

### Source Code (two repositories)

Paths follow the module layout set by features 001 to 003; where a file already exists it is extended.

```text
# repo: brightsmile/clinic-api  (ctr-clinic-api)
app/
├── booking/                       # cmp-booking
│   ├── change_window.py           # 4-hour rule (pure function, IST/UTC safe)
│   ├── patient_schemas.py         # request/response models
│   ├── patient_queries.py         # list per person, get owned appointment
│   ├── patient_service.py         # list, get, cancel, reschedule (one transaction each)
│   ├── patient_router.py          # /api/me/appointments, /api/appointments/{id}/...
│   ├── history.py                 # writes ent-appointment-event (extended)
│   └── ports.py                   # RescheduleRule, ChangeNotifier interfaces
├── noshow_policy/
│   └── reschedule_rule.py         # R1: AlwaysAllowRescheduleRule (R2 replaces)
├── messaging/
│   ├── change_messages.py         # change message rows: cancelled, rescheduled
│   └── reminder_port.py           # cancel_reminders, recreate_reminder (timing rules: feature 006)
├── scheduling/
│   └── reschedule_slots.py        # free slots for same clinic and treatment, any dentist
tests/booking/                     # unit, integration, contract tests of this feature

# repo: brightsmile/clinic-web  (ctr-web)
src/
├── api/appointments.ts            # calls to the API
├── pages/
│   ├── MyAppointmentsPage.tsx
│   ├── AppointmentPage.tsx
│   ├── ReschedulePickerPage.tsx   # slot picker
│   └── AppointmentDonePage.tsx
├── components/
│   ├── AppointmentCard.tsx
│   ├── ClinicPhoneNotice.tsx
│   └── ConfirmCancelSheet.tsx
├── auth/ReturnTo.tsx              # deep link: sign-in then back to the link
└── i18n/appointments.en.ts        # English text and status labels
```

**Structure Decision**: web application split across the two repositories named in the constitution. Backend work stays inside existing module boundaries (`cmp-booking`, `cmp-messaging`, `cmp-scheduling`, `cmp-noshow-policy`); calls between modules are in-process, as in the component view of architecture.md.

## Key design decisions

1. **Change window**: `can_change = status == booked and now <= start - 4h` (inclusive, Q1). One function in `change_window.py`, used by the list/detail response and by both write operations, so screen and server never disagree. Time source is injectable for tests.
2. **Ownership**: the account id comes from the session token; queries join appointment to person to account. Not owned or unknown returns 404 (Q2).
3. **Cancel**: `SELECT ... FOR UPDATE` on the appointment, re-check status and window, set status `cancelled_by_patient`, insert history row, withdraw reminders, insert change message row, commit. If already `cancelled_by_patient`, return the current state with 200 and write nothing (FR-016 idempotence).
4. **Reschedule**: same lock; check window and `RescheduleRule`; update dentist and start/end in place (appointment id and deep link stay valid); the exclusion constraint rejects a taken slot (SQLSTATE 23P01), which is rolled back and returned as 409 `slot_taken` with the next free slots; insert history row with reason `rescheduled` and old and new start; replace the reminder; insert change message row. If the appointment is already at the requested dentist and start, return 200 with no new rows.
5. **Messages**: rows are committed with the change and sent by the dispatcher (ADR-0002), so a provider outage never blocks the change. Channel comes from the appointment; reminder opt-out does not stop change messages (prd.md FR-031).
6. **Reminders**: this feature calls `cancel_reminders` and `recreate_reminder` on the messaging port; the quiet-hours and "less than 24 hours ahead" rules stay in feature 006 (prd.md FR-028).
7. **R2 hook**: `RescheduleRule.check(patient_id) -> allowed | blocked(reason)`; R1 implementation always allows; `cmp-noshow-policy` replaces it in R2 without touching `cmp-booking`.
8. **List per person**: response is a list of `{person, upcoming[], past[]}`; R1 returns one group.
9. **Web**: four routes (`/appointments`, `/appointments/:id`, `/appointments/:id/change`, `/appointments/:id/done`); a route guard stores `returnTo` and sends signed-out users to sign-in (feature 001), then back.

## Dependencies

- Feature 001: patient session, CSRF, access context (account id).
- Feature 002: free-slot calculation, clinic phone, booking horizon.
- Feature 003: appointment table, exclusion constraint, history writer, booking horizon setting.
- Feature 006: reminder row timing; template registration for the two change messages is done by this feature (templates cancelled and rescheduled), approved by the provider as part of DLT/WhatsApp registration (RSK-001).

## Complexity Tracking

No constitution violations.
