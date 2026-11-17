# Implementation Plan: Patient appointment list, reschedule, cancel and status history

**Branch**: `005-manage-appointments` | **Date**: 2026-11-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-manage-appointments/spec.md`

## Summary

A signed-in patient lists upcoming and past appointments (by account), opens one, and cancels or reschedules it until 4 hours before its start; inside 4 hours the page shows the clinic's phone number. Every status change and reschedule writes an `appointment_event` row (who, when, from/to, reason) in the same transaction as the change, as the architecture requires (thr-006, thr-011). Approach: extend `cmp-booking` in `ctr-clinic-api` with a list query, a status-change service shared with reception (feature 006), and online cancel/reschedule operations that use the same exclusion constraint as booking (ADR-0003). Slot lists come from `cmp-scheduling`; messages and reminder row changes are created through `cmp-messaging` (feature 007) in the same transaction and sent after commit; the no-show block is read through a `cmp-noshow-policy` interface that answers "not blocked" until feature 009. The patient screens (my appointments, appointment, slot picker, done) are added to `ctr-web`. (source: FR-015, FR-016, FR-017, FR-018, FR-024)

## Technical Context

**Language/Version**: Python 3.12 (ctr-clinic-api); TypeScript with React (ctr-web)

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic (ctr-clinic-api); React SPA (ctr-web). No other libraries are named by the architecture.

**Storage**: PostgreSQL 16 with `btree_gist` (ctr-db); entities ent-appointment, ent-appointment-event

**Testing**: pytest for unit, API and contract tests against `contracts/clinic-api-v1.openapi.yaml`, including a concurrency test for the no-overlap constraint; a component/unit test runner for ctr-web as already set by the web repo (not chosen here: Assumed the web repo's existing runner). The architecture names no web test tool.

**Target Platform**: Linux container (managed container service, India region); mobile browsers (current Chrome and Safari) for patient screens

**Project Type**: web application (API + static SPA), two repos: brightsmile/clinic-api and brightsmile/clinic-web

**Performance Goals**: list and slot picker within 2 s for 95% of requests on 4G (QA-001); cancel or reschedule within 3 s for 95% (QA-002)

**Constraints**: times stored in UTC, shown in IST; no patient name, phone or birth year in logs; authorisation from the token owner only (thr-004); cookie JWT with CSRF header on writes (rel-005); writes never retried automatically by the client; messages created in the transaction and sent after commit; history kept 24 months (ASM-012)

**Scale/Scope**: about 450 appointments a week now, 1,000 later; 4 patient screens; 5 API operations; 1 new table

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Tests first for business logic | Every user story has an independent test; the 4-hour boundary, atomicity and concurrency tests are written before the services (tasks list tests first) | Pass |
| II. Observability | New endpoints emit structured logs with ids only, metrics (cancel, reschedule, refused-by-cut-off, slot-taken counters) and traces; no new service, so the existing `GET /health` covers it | Pass |
| III. Security baseline | Owner taken from the session; ids in the request are never trusted; inputs validated at the boundary; no secrets; this change touches authorisation, so it is flagged for explicit review | Pass (review needed) |
| IV. Traceability | Spec and tasks carry prd.md ids; every task names file paths | Pass |
| V. Simplicity | One new table; no new service, queue or cache; policy interface is one function because feature 009 needs it | Pass |
| Definition of Done: no patient data in logs | Logging helper T014 and a test that scans log output (T054) | Pass |

Post-design re-check: still passes; no complexity violations.

## Project Structure

### Documentation (this feature)

```text
specs/005-manage-appointments/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── clarifications.md
├── contracts/
│   └── appointments.openapi.yaml
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
# brightsmile/clinic-api  (ctr-clinic-api, modular monolith)
clinic-api/
├── alembic/versions/
│   └── 0005_appointment_event.py
├── app/modules/booking/                 # cmp-booking
│   ├── models.py                        # Appointment (existing), AppointmentEvent (new)
│   ├── statuses.py                      # the five statuses, actor kinds, reasons
│   ├── cutoff.py                        # 4-hour rule on UTC times
│   ├── history.py                       # writes appointment_event rows
│   ├── status_service.py                # shared status change (also used by feature 006)
│   ├── manage_service.py                # list, get, cancel, reschedule for patients
│   ├── schemas.py
│   └── router_patient.py                # /api/appointments...
├── app/modules/noshow_policy/
│   └── interface.py                     # is_blocked(person_id) -> not blocked until feature 009
├── app/modules/messaging/               # feature 007 owns; called only
│   └── interface.py                     # create_change_notice, replace_reminder (call only)
├── app/modules/scheduling/
│   └── interface.py                     # list_free_slots (call only)
└── tests/
    ├── unit/booking/
    ├── api/booking/
    └── contract/

# brightsmile/clinic-web  (ctr-web, React SPA)
clinic-web/
├── src/features/appointments/
│   ├── api.ts
│   ├── MyAppointmentsPage.tsx
│   ├── AppointmentPage.tsx
│   ├── SlotPickerPage.tsx
│   ├── DonePage.tsx
│   ├── time.ts                          # shows UTC times in IST
│   └── appointments.css
├── src/routes/appointments.tsx          # includes the message-link route /appointments/:id
└── tests/appointments/
```

**Structure Decision**: Web application with two repositories as fixed by the constitution. The backend change lives inside the existing `cmp-booking` module, with call-only interfaces to scheduling, messaging and the no-show policy; the frontend change is one feature folder. Paths are relative to each repository's root and follow the module names in architecture.md; adjust to the repository's existing layout when it is known.

## Complexity Tracking

No constitution violations to justify.
