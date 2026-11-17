---

description: "Task list for feature 005 - Patient appointment list, reschedule, cancel and status history"
---

# Tasks: Patient appointment list, reschedule, cancel and status history

**Input**: Design documents from `/specs/005-manage-appointments/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/appointments.openapi.yaml, quickstart.md

**Tests**: Requested. The constitution requires tests first for business logic and an independent test for every user story; write each test task before its implementation and see it fail.

**Organization**: Grouped by user story. Backend paths are in repository brightsmile/clinic-api (written `clinic-api/...`), frontend paths in brightsmile/clinic-web (written `clinic-web/...`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1..US5)
- Every task names the exact file path

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Folders and contract in place

- [ ] T001 Create or confirm the backend test packages `clinic-api/tests/unit/booking/__init__.py`, `clinic-api/tests/api/booking/__init__.py` and `clinic-api/tests/contract/__init__.py`
- [ ] T002 [P] Create the web feature folder `clinic-web/src/features/appointments/index.ts` and the test folder `clinic-web/tests/appointments/.gitkeep`
- [ ] T003 [P] Merge the paths and schemas of `specs/005-manage-appointments/contracts/appointments.openapi.yaml` into `clinic-api/contracts/clinic-api-v1.openapi.yaml` without changing other operations

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Statuses, 4-hour rule, table, call-only interfaces, schemas and the router that every story needs

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 [P] Write the failing unit test for the 4-hour rule in `clinic-api/tests/unit/booking/test_cutoff.py`: exactly 4 h 00 min before the UTC start is allowed, 3 h 59 min 59 s is refused, and a start just after midnight IST is handled on UTC times
- [ ] T005 [P] Write the failing unit test in `clinic-api/tests/unit/booking/test_statuses.py` that exactly five statuses exist: `booked`, `arrived`, `no_show`, `cancelled_by_patient`, `cancelled_by_clinic`
- [ ] T006 Implement the five statuses, actor kinds (`patient`, `staff`, `system`) and reason constants in `clinic-api/app/modules/booking/statuses.py` (depends on T005)
- [ ] T007 Implement `can_change_online(starts_at_utc, now_utc)` with the 4-hour rule in `clinic-api/app/modules/booking/cutoff.py` (depends on T004)
- [ ] T008 Write Alembic migration `clinic-api/alembic/versions/0005_appointment_event.py`: create `appointment_event` (id uuid PK; appointment_id FK to appointment(id); from_status and to_status text NOT NULL with CHECK in (`booked`, `arrived`, `no_show`, `cancelled_by_patient`, `cancelled_by_clinic`); actor_kind text NOT NULL CHECK in (`patient`, `staff`, `system`); actor_id uuid NOT NULL; occurred_at timestamptz NOT NULL default now(); reason text NOT NULL; from_starts_at, to_starts_at timestamptz NULL; from_dentist_id, to_dentist_id uuid NULL; idempotency_key text NULL), index `(appointment_id, occurred_at)`, unique `(appointment_id, idempotency_key)` where key is not null, add the same status CHECK on `appointment.status` only if missing, and grant the application role INSERT and SELECT only (no UPDATE or DELETE) (depends on T006)
- [ ] T009 Add the `AppointmentEvent` model to `clinic-api/app/modules/booking/models.py` matching T008 (depends on T008)
- [ ] T010 [P] Add the no-show policy interface `is_blocked(person_id) -> bool` returning `False` until feature 009 in `clinic-api/app/modules/noshow_policy/interface.py`
- [ ] T011 [P] Add the call-only messaging interface (`create_change_notice`, `cancel_reminder`, `replace_reminder`, all taking the open database session, owned by feature 007) and a test double in `clinic-api/app/modules/messaging/interface.py`
- [ ] T012 [P] Add the call-only scheduling interface (`list_free_slots(clinic_id, treatment_type_id, from_date, to_date)` and `get_clinic_phone(clinic_id)`) in `clinic-api/app/modules/scheduling/interface.py`
- [ ] T013 Define the response and error schemas (`Appointment`, `Slot`, `NotChangeableError`, `SlotTakenError`) from the contract in `clinic-api/app/modules/booking/schemas.py` (depends on T006)
- [ ] T014 [P] Add structured logging and counters (cancel, reschedule, refused by cut-off, slot taken) that carry ids only, never names, phones or birth years, in `clinic-api/app/modules/booking/observability.py`
- [ ] T015 Create the patient router skeleton with a dependency that takes the owner from the signed-in session only, 404 for appointments outside the account, and 409 error mapping, and register it in the app, in `clinic-api/app/modules/booking/router_patient.py` (depends on T013, T014)
- [ ] T016 [P] Add the API client with the CSRF header on writes in `clinic-web/src/features/appointments/api.ts` and the UTC-to-IST formatter in `clinic-web/src/features/appointments/time.ts`
- [ ] T017 [P] Register the routes `/appointments`, `/appointments/:id`, `/appointments/:id/change` and `/appointments/:id/done` with placeholders in `clinic-web/src/routes/appointments.tsx`

**Checkpoint**: Foundation ready - user stories can begin

---

## Phase 3: User Story 1 - See my upcoming and past appointments (Priority: P1) 🎯 MVP

**Goal**: A signed-in patient sees upcoming and past appointments of their account with status, and opens one.

**Independent Test**: Seed an account with upcoming, past, cancelled and no-show appointments and a second account; sign in and list; the other account's appointment is absent and gives 404 by id.

### Tests for User Story 1

- [ ] T018 [P] [US1] Write the failing API test for `GET /api/appointments` (order, status, IST-ready times, `when` filter, empty list, other account absent) in `clinic-api/tests/api/booking/test_list_appointments.py`
- [ ] T019 [P] [US1] Write the failing API test for `GET /api/appointments/{id}` returning 404 for another account's appointment and the phone and `canChange`/`canCancel` flags for the owner in `clinic-api/tests/api/booking/test_get_appointment_owner.py`
- [ ] T020 [P] [US1] Write the failing web test for the list screen (upcoming first, status labels, empty state with "Book") in `clinic-web/tests/appointments/MyAppointmentsPage.test.tsx`
- [ ] T021 [P] [US1] Write the failing web test that the appointment screen shows the clinic phone and no buttons when `canChange` and `canCancel` are false in `clinic-web/tests/appointments/AppointmentPage.test.tsx`

### Implementation for User Story 1

- [ ] T022 [US1] Implement `list_for_account` and `get_for_account` (selects by person -> account of the token owner; computes `canChange`, `canCancel`, `changeBlockedReason` with `cutoff.py` and the policy interface) in `clinic-api/app/modules/booking/manage_service.py` (depends on T007, T009, T010, T012, T018, T019)
- [ ] T023 [US1] Implement the list and get endpoints in `clinic-api/app/modules/booking/router_patient.py` (depends on T015, T022)
- [ ] T024 [P] [US1] Build the list screen in `clinic-web/src/features/appointments/MyAppointmentsPage.tsx` (depends on T016, T020)
- [ ] T025 [P] [US1] Build the appointment screen showing detail, status, and the clinic phone when no action is allowed in `clinic-web/src/features/appointments/AppointmentPage.tsx` (depends on T016, T021)

**Checkpoint**: User Story 1 works on its own

---

## Phase 4: User Story 2 - Every status change records who and when (Priority: P1)

**Goal**: One shared status-change operation that writes the appointment change and its history row together, accepts only the five statuses, and records the actor.

**Independent Test**: Through `change_status`, cancel as patient, cancel by reception with and without "patient asked", mark arrived and no-show; read history; an invalid status is refused by the database; a failed change leaves nothing.

### Tests for User Story 2

- [ ] T026 [P] [US2] Write the failing unit test for `record_event` (from, to, actor kind and id, UTC time, reason, optional old/new time and dentist) in `clinic-api/tests/unit/booking/test_history.py`
- [ ] T027 [P] [US2] Write the failing unit test for `change_status` including ASM-014 (reception cancel with patient-asked gives `cancelled_by_patient`, otherwise `cancelled_by_clinic`) and refused transitions in `clinic-api/tests/unit/booking/test_status_service.py`
- [ ] T028 [P] [US2] Write the failing database test: a status outside the five is refused by the CHECK, the application role cannot UPDATE or DELETE `appointment_event`, and a forced failure leaves neither status nor event in `clinic-api/tests/api/booking/test_history_db.py`
- [ ] T029 [P] [US2] Write the failing test that the retention function removes event rows with their appointment's personal link only after 24 months in `clinic-api/tests/unit/booking/test_event_retention.py`

### Implementation for User Story 2

- [ ] T030 [US2] Implement `record_event` (insert only) in `clinic-api/app/modules/booking/history.py` (depends on T009, T026)
- [ ] T031 [US2] Implement `change_status(session, appointment_id, to_status, actor, reason, patient_asked)` that locks the row (`SELECT ... FOR UPDATE`), validates the transition from data-model.md, updates the status and writes the event in the caller's transaction in `clinic-api/app/modules/booking/status_service.py` (depends on T030, T027)
- [ ] T032 [US2] Implement the retention function for event rows, run by the maintenance role, in `clinic-api/app/modules/booking/retention.py` (depends on T009, T029)

**Checkpoint**: Stories 1 and 2 both work; cancel and reschedule can now record history

---

## Phase 5: User Story 3 - Cancel an upcoming appointment (Priority: P1)

**Goal**: A patient cancels until 4 hours before the start; the slot is free at once; a message is created in the same transaction; inside 4 hours only the clinic phone is shown.

**Independent Test**: Cancel one appointment more than 4 hours ahead and one at 3 h 59 min; the first is `cancelled_by_patient` with history, a free slot and one message row; the second is refused with the phone; repeating the first cancel changes nothing.

### Tests for User Story 3

- [ ] T033 [P] [US3] Write the failing API test for `POST /api/appointments/{id}/cancel` (200 at 4 h 00 min, 409 `too_late` with clinic phone at 3 h 59 min, 409 `not_booked` for arrived/no-show/cancelled, 404 for another account, slot appears in free slots at once) in `clinic-api/tests/api/booking/test_cancel.py`
- [ ] T034 [P] [US3] Write the failing test that a cancel is atomic (a failing messaging double leaves status, event and reminder unchanged) and idempotent (second request gives the same 200, one event, one message) in `clinic-api/tests/api/booking/test_cancel_atomic.py`
- [ ] T035 [P] [US3] Write the failing web test for Cancel, confirm and the done screen in `clinic-web/tests/appointments/CancelFlow.test.tsx`

### Implementation for User Story 3

- [ ] T036 [US3] Implement `cancel_online` (re-check cut-off on the server, `change_status` to `cancelled_by_patient` with reason `patient_request`, `cancel_reminder`, `create_change_notice` for the appointment's channel, one transaction, message sent after commit) in `clinic-api/app/modules/booking/manage_service.py` (depends on T011, T022, T031, T033, T034)
- [ ] T037 [US3] Implement `POST /api/appointments/{id}/cancel` with the contract's 200/404/409 answers in `clinic-api/app/modules/booking/router_patient.py` (depends on T023, T036)
- [ ] T038 [P] [US3] Build the done screen shared by cancel and reschedule in `clinic-web/src/features/appointments/DonePage.tsx` (depends on T016)
- [ ] T039 [US3] Add the Cancel button, the confirm step and the refused-too-late state with the clinic phone to `clinic-web/src/features/appointments/AppointmentPage.tsx` (depends on T025, T035, T037, T038)

**Checkpoint**: Cancel works end to end

---

## Phase 6: User Story 4 - Reschedule an upcoming appointment (Priority: P1)

**Goal**: A patient moves an appointment to another free slot (same clinic and treatment, any dentist) until 4 hours before the original start, atomically with its history and reminder change, blocked patients refused.

**Independent Test**: Reschedule to another dentist's free slot; the appointment holds the new slot, the old slot is free, one event row has the old and new time, the reminder is replaced and one message exists; a taken slot gives `slot_taken` with next slots; a blocked policy refuses.

### Tests for User Story 4

- [ ] T040 [P] [US4] Write the failing API test for slots and reschedule (same clinic and treatment only, any dentist, 30-day horizon, same time answered as unchanged, repeat with the same `Idempotency-Key` returns the first result, 422 for a slot not offered) in `clinic-api/tests/api/booking/test_reschedule.py`
- [ ] T041 [P] [US4] Write the failing test that a blocked policy double gives 409 `blocked`, a start inside 4 hours gives 409 `too_late`, and the original booking stays in both cases in `clinic-api/tests/api/booking/test_reschedule_rules.py`
- [ ] T042 [P] [US4] Write the failing concurrency test: 1,000 concurrent reschedule and booking attempts on one dentist leave 0 overlapping active appointments, and the loser gets `slot_taken` with next slots, in `clinic-api/tests/api/booking/test_reschedule_concurrency.py`
- [ ] T043 [P] [US4] Write the failing web test for the slot picker, confirm, slot-taken message and blocked message in `clinic-web/tests/appointments/SlotPickerPage.test.tsx`

### Implementation for User Story 4

- [ ] T044 [US4] Implement `list_reschedule_slots` (checks owner, status and cut-off, then calls `list_free_slots` for the same clinic and treatment, any dentist) in `clinic-api/app/modules/booking/manage_service.py` (depends on T022, T036, T040)
- [ ] T045 [US4] Implement `reschedule_online` (lock row, check state, cut-off and `is_blocked`, update dentist and times so the exclusion constraint decides, map the violation to `slot_taken` with next slots, `record_event` with old/new time and dentist and the idempotency key, `replace_reminder`, `create_change_notice`, one transaction) in `clinic-api/app/modules/booking/manage_service.py` (depends on T044, T031, T041, T042)
- [ ] T046 [US4] Implement `GET /api/appointments/{id}/slots` and `POST /api/appointments/{id}/reschedule` (with `Idempotency-Key`) in `clinic-api/app/modules/booking/router_patient.py` (depends on T037, T045)
- [ ] T047 [P] [US4] Build the slot picker screen (free slots grouped by day in IST, confirm, slot-taken state showing next slots, blocked state showing the clinic phone) in `clinic-web/src/features/appointments/SlotPickerPage.tsx` (depends on T016, T043)
- [ ] T048 [US4] Add the "Change time" button linking to the slot picker and wire the done screen to the new details in `clinic-web/src/features/appointments/AppointmentPage.tsx` (depends on T039, T046, T047)

**Checkpoint**: Reschedule works end to end

---

## Phase 7: User Story 5 - Open my appointment from the message link (Priority: P2)

**Goal**: The link in a confirmation or reminder opens the appointment after sign-in, for its owner only.

**Independent Test**: Open `/appointments/{id}` signed out, sign in as the owner and land on it; as another patient get "not found".

### Tests for User Story 5

- [ ] T049 [P] [US5] Write the failing web test that a signed-out visit to `/appointments/:id` goes to sign-in and returns to that appointment, and a 404 shows "not found" with no appointment data, in `clinic-web/tests/appointments/MessageLink.test.tsx`

### Implementation for User Story 5

- [ ] T050 [P] [US5] Implement keeping the target route through sign-in (a `next` value limited to same-site `/appointments/` paths) in `clinic-web/src/features/appointments/returnTo.ts` (depends on T049)
- [ ] T051 [US5] Make the `/appointments/:id` route require a session, use `returnTo.ts`, and render read-only for cancelled or past appointments in `clinic-web/src/routes/appointments.tsx` (depends on T017, T025, T050)

**Checkpoint**: All user stories work

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Contract, security, privacy, performance and quickstart checks

- [ ] T052 [P] Write contract tests for all five operations against `clinic-api/contracts/clinic-api-v1.openapi.yaml` in `clinic-api/tests/contract/test_appointments_contract.py`
- [ ] T053 [P] Write the cross-patient authorisation matrix test for all five operations (owner from session; ids in the request never grant access) in `clinic-api/tests/api/booking/test_authz_matrix.py`
- [ ] T054 [P] Write a test that captures log output of list, cancel and reschedule and asserts no name, phone number or birth year appears in `clinic-api/tests/unit/booking/test_logging_no_pii.py`
- [ ] T055 [P] Write a latency check that list and slots meet 2 s and cancel and reschedule meet 3 s at p95 under 100 concurrent users in `clinic-api/tests/perf/test_appointments_latency.py`
- [ ] T056 [P] Style the four screens mobile-first (tap targets at least 44 px, no sideways scrolling) in `clinic-web/src/features/appointments/appointments.css`
- [ ] T057 Run the scenarios in `specs/005-manage-appointments/quickstart.md` and record any gaps at the end of that file (depends on T048, T051, T052, T053)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none
- **Foundational (Phase 2)**: after Setup; blocks all stories
- **US1 (Phase 3)**: after Foundational
- **US2 (Phase 4)**: after Foundational; independent of US1
- **US3 (Phase 5)**: after US1 (service and screen) and US2 (`change_status`)
- **US4 (Phase 6)**: after US3 (shares `manage_service.py`, `router_patient.py`, `AppointmentPage.tsx`)
- **US5 (Phase 7)**: after US1; can run beside US3 and US4
- **Polish (Phase 8)**: after all stories

### Within Each Story

Tests first and failing, then models and services, then endpoints, then screens.

### Parallel Opportunities

- T004, T005 together; T010, T011, T012, T014, T016, T017 together after T006
- US1 and US2 can be built in parallel by two people
- Backend and web tasks of a story run in parallel once the contract (T003) is merged

## Parallel Example: User Story 1

```text
Task: "Write the failing API test for GET /api/appointments in clinic-api/tests/api/booking/test_list_appointments.py"
Task: "Write the failing web test for the list screen in clinic-web/tests/appointments/MyAppointmentsPage.test.tsx"
```

## Implementation Strategy

### MVP First

1. Setup and Foundational
2. US1 (list) and US2 (history) in parallel
3. US3 (cancel), then US4 (reschedule): both are Must for 1 March 2027
4. Validate with the quickstart; US5 can follow if time is short, since "My appointments" gives the same access

### Incremental Delivery

Each phase leaves the system working: list, then history, then cancel, then reschedule, then message links.

## Notes

- Feature 006 (reception) calls `change_status`; feature 007 supplies the real messaging; feature 009 replaces the `is_blocked` stub; feature 008 adds family members to the account list without code change here
- This change touches authorisation: request a review of T015, T022 and T053 before release (constitution principle III)
- Commit after each task or logical group
