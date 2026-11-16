# Tasks: Patient appointments: view, reschedule, cancel

**Input**: Design documents from `/specs/004-patient-appointments/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/patient-appointments.openapi.yaml, quickstart.md

**Tests**: Included. The constitution requires tests first for business logic and an independent test per user story.

**Repositories**: `clinic-api` = brightsmile/clinic-api (Python FastAPI); `clinic-web` = brightsmile/clinic-web (React SPA). Every task names its repo as `(repo: ...)`. Paths are relative to that repo's root and follow the module layout of features 001 to 003.

**Source requirements** (prd.md): FR-015, FR-016, FR-017, FR-018.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1 see appointments (FR-015), US2 cancel (FR-017, FR-018), US3 reschedule (FR-016, FR-018), US4 deep link (FR-015, FR-016, FR-017)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Skeleton files and the contract, in both repositories

- [ ] T001 Create the module skeleton `app/booking/patient_router.py`, `app/booking/patient_service.py`, `app/booking/patient_queries.py`, `app/booking/patient_schemas.py`, `app/booking/change_window.py`, `app/booking/ports.py`, `tests/booking/__init__.py`, and register the empty patient router in `app/main.py` (repo: clinic-api)
- [ ] T002 [P] Create the web skeleton: `src/api/appointments.ts` (typed client for the five operations of the contract, CSRF header on writes, no automatic retry of writes), `src/i18n/appointments.en.ts` (English text and status labels), and the four routes `/appointments`, `/appointments/:id`, `/appointments/:id/change`, `/appointments/:id/done` in `src/routes.tsx` (repo: clinic-web)
- [ ] T003 [P] Merge `specs/004-patient-appointments/contracts/patient-appointments.openapi.yaml` paths and schemas into `contracts/clinic-api-v1.openapi.yaml` so CI contract tests cover them (repo: clinic-api)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The 4-hour rule, ports, schemas, ownership lookup, history writer and metrics used by all stories

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 [P] Write unit tests for the change window in `tests/booking/test_change_window.py`: exactly 4 h before start is allowed, 3 h 59 min is refused, status other than booked is refused, past start is refused, injected clock, comparison in UTC (repo: clinic-api)
- [ ] T005 Implement `can_change(status, start_at, now)` and `change_deadline(start_at)` returning `allowed | within_cutoff | not_upcoming` in `app/booking/change_window.py` (repo: clinic-api) (depends on T004)
- [ ] T006 [P] Define the interfaces `RescheduleRule.check(patient_id)` returning allowed or blocked(reason) and `ChangeNotifier` in `app/booking/ports.py` (repo: clinic-api)
- [ ] T007 Implement `AlwaysAllowRescheduleRule` (Release 1; Release 2 replaces it with the no-show check, FR-025 of prd.md) in `app/noshow_policy/reschedule_rule.py` with a unit test in `tests/booking/test_reschedule_rule.py` (repo: clinic-api) (depends on T006)
- [ ] T008 [P] Define the response and request models `Person`, `Appointment` (with `can_change`, `change_block_reason`, `change_deadline_at`), `Slot`, `ChangeRefusedBody`, `SlotTaken`, `RescheduleRequest` in `app/booking/patient_schemas.py`, exactly as in the OpenAPI fragment; status enum `booked, arrived, no_show, cancelled_by_patient, cancelled_by_clinic` (repo: clinic-api)
- [ ] T009 Implement `get_owned_appointment(session, account_id, appointment_id, for_update=False)` in `app/booking/patient_queries.py`: joins appointment to person to account, returns nothing for an unknown or foreign appointment (callers answer 404), optional row lock (repo: clinic-api) (depends on T008)
- [ ] T010 [P] Extend `app/booking/history.py` with `write_event(session, appointment_id, from_status, to_status, actor, reason)` (actor = patient person id and role `patient`; reason text holds no names) so cancel and reschedule write the `ent-appointment-event` row inside the caller's transaction (repo: clinic-api)
- [ ] T011 [P] Add OpenTelemetry counters `appointment_cancelled`, `appointment_rescheduled`, `change_refused_window`, `reschedule_slot_conflict` and a structured-log helper that never logs names or phones in `app/booking/metrics.py` (repo: clinic-api)

**Checkpoint**: Foundation ready

---

## Phase 3: User Story 1 - See my appointments (Priority: P1) MVP

**Goal**: A signed-in patient lists upcoming and past appointments per person, with status, and opens one; buttons or the clinic phone number show according to the 4-hour rule. (FR-015, FR-017)

**Independent Test**: Quickstart scenario 1: list grouping, IST times, 360 px layout, 3-hour appointment shows the phone number, foreign appointment answers 404.

### Tests for User Story 1

- [ ] T012 [P] [US1] Integration tests for `GET /api/me/appointments` in `tests/booking/test_patient_list.py`: one group in Release 1, upcoming earliest first, past latest first, cancelled and no-show in past, past page of 20 with cursor, empty list (repo: clinic-api)
- [ ] T013 [P] [US1] Access tests in `tests/booking/test_patient_access.py`: another patient's appointment id returns 404 on every operation, no session returns 401, a staff session is refused (repo: clinic-api)
- [ ] T014 [P] [US1] Contract test of `listMyAppointments` and `getMyAppointment` against the OpenAPI fragment in `tests/booking/test_patient_contract.py` (repo: clinic-api)
- [ ] T015 [P] [US1] Screen tests in `src/pages/__tests__/MyAppointmentsPage.test.tsx` and `src/pages/__tests__/AppointmentPage.test.tsx`: grouping, status words, IST formatting, empty state with "Book", buttons versus phone number from `can_change` (repo: clinic-web)

### Implementation for User Story 1

- [ ] T016 [US1] Implement `list_for_account(session, account_id, past_cursor, past_limit)` in `app/booking/patient_queries.py`: appointments of every person on the account, grouped per person; upcoming = status booked and start in the future; past = the rest, page of 20 (repo: clinic-api) (depends on T009)
- [ ] T017 [US1] Implement `list_appointments` and `get_appointment` in `app/booking/patient_service.py`, filling `can_change`, `change_block_reason` (using `can_change` and `RescheduleRule`) and `change_deadline_at`, with clinic phone, dentist and treatment names (repo: clinic-api) (depends on T005, T007, T016)
- [ ] T018 [US1] Implement `GET /api/me/appointments` and `GET /api/appointments/{appointmentId}` in `app/booking/patient_router.py` with session account from the cookie, 404 for foreign ids, no names or phones in logs (repo: clinic-api) (depends on T017)
- [ ] T019 [P] [US1] Create `src/components/AppointmentCard.tsx` and `src/components/ClinicPhoneNotice.tsx` (tel link; tap targets at least 44 px, no sideways scrolling at 360 px) and the status labels in `src/i18n/appointments.en.ts` (repo: clinic-web)
- [ ] T020 [US1] Create `src/pages/MyAppointmentsPage.tsx`: groups per person, upcoming then past, times in `Asia/Kolkata`, empty state (repo: clinic-web) (depends on T019)
- [ ] T021 [US1] Create `src/pages/AppointmentPage.tsx`: details, "Change time" and "Cancel" buttons when `can_change`, otherwise `ClinicPhoneNotice` (repo: clinic-web) (depends on T019)

**Checkpoint**: User Story 1 works and is testable on its own

---

## Phase 4: User Story 2 - Cancel an upcoming appointment (Priority: P1)

**Goal**: Cancel with confirmation until 4 hours before the start; slot free at once; change message in the chosen channel; reminder withdrawn. (FR-017, FR-018)

**Independent Test**: Quickstart scenario 2: cancel 2 days ahead, check status, freed slot, one history row, one message; repeat the cancel; try 3 hours ahead.

### Tests for User Story 2

- [ ] T022 [P] [US2] Integration tests in `tests/booking/test_patient_cancel.py`: success sets `cancelled_by_patient`; slot bookable by another patient right after; one history row; one message row in the appointment channel; repeat returns 200 with no second row; 3 h 59 min returns 409 `within_cutoff` with clinic phone; exactly 4 h succeeds; arrived or no-show refused with `not_upcoming`; message provider down does not fail the cancel (repo: clinic-api)
- [ ] T023 [P] [US2] Tests in `tests/messaging/test_change_messages.py`: cancelled template row created with channel of the appointment, still created when reminders are opted out, pending reminder rows of the appointment cancelled (repo: clinic-api)
- [ ] T024 [P] [US2] Screen tests in `src/pages/__tests__/CancelFlow.test.tsx`: confirm sheet, going back changes nothing, double tap sends one request, 409 `within_cutoff` shows the clinic phone number, Done screen (repo: clinic-web)

### Implementation for User Story 2

- [ ] T025 [P] [US2] Implement `queue_change_message(session, appointment, kind)` for kinds `cancelled` and `rescheduled` in `app/messaging/change_messages.py`: inserts an `ent-message` row (kind `change`, template `appointment_cancelled` or `appointment_rescheduled`, channel of the appointment, send at once, values clinic, dentist, date, time in IST, appointment link) and never opens a provider call (repo: clinic-api)
- [ ] T026 [P] [US2] Implement `cancel_reminders(session, appointment_id)` in `app/messaging/reminder_port.py`: marks pending reminder rows of the appointment cancelled (repo: clinic-api)
- [ ] T027 [P] [US2] Add template ids for `appointment_cancelled` and `appointment_rescheduled` to the configuration in `app/config.py` and write the template texts for DLT and WhatsApp approval in `docs/message-templates/change-messages.md` (English, IST, no personal data beyond the template fields) (repo: clinic-api)
- [ ] T028 [US2] Implement `cancel_appointment` in `app/booking/patient_service.py`: one transaction with row lock, re-check ownership, status and window, set `cancelled_by_patient`, `write_event`, `cancel_reminders`, `queue_change_message`; already cancelled returns the current state and writes nothing; increment metrics (repo: clinic-api) (depends on T005, T010, T011, T017, T025, T026)
- [ ] T029 [US2] Implement `POST /api/appointments/{appointmentId}/cancel` in `app/booking/patient_router.py` returning 200, 404 or 409 with `ChangeRefusedBody` (repo: clinic-api) (depends on T028)
- [ ] T030 [P] [US2] Create `src/components/ConfirmCancelSheet.tsx` with "Confirm" and "Back" (tap targets at least 44 px, disabled after the first tap) (repo: clinic-web)
- [ ] T031 [P] [US2] Create `src/pages/AppointmentDonePage.tsx` for the result of a cancel or a reschedule (new details for a reschedule, link back to "My appointments") (repo: clinic-web)
- [ ] T032 [US2] Wire the cancel action into `src/pages/AppointmentPage.tsx` and `src/api/appointments.ts`: confirm sheet, call, Done screen, refresh on 409 and show the clinic phone number (repo: clinic-web) (depends on T021, T030, T031)

**Checkpoint**: User Stories 1 and 2 work independently

---

## Phase 5: User Story 3 - Reschedule an upcoming appointment (Priority: P2)

**Goal**: Move an appointment to another free slot of the same clinic and treatment with any dentist until 4 hours before; old slot free at once; reminder moved; message sent; policy hook for Release 2. (FR-016, FR-018)

**Independent Test**: Quickstart scenario 3: reschedule 2 days ahead to another dentist, check new time, freed old slot, history reason, reminder and message; race two patients for one slot.

### Tests for User Story 3

- [ ] T033 [P] [US3] Tests for `GET /api/appointments/{appointmentId}/reschedule-slots` in `tests/booking/test_reschedule_slots.py`: same clinic and treatment, any dentist, never the held slot, within the booking horizon, at most 7 days per request, refused inside 4 hours (repo: clinic-api)
- [ ] T034 [P] [US3] Tests for `POST /api/appointments/{appointmentId}/reschedule` in `tests/booking/test_patient_reschedule.py`: success keeps clinic, treatment, channel and id; old slot bookable at once; history reason `rescheduled from ... to ...`; reminder replaced; one message; repeat to the same slot returns 200 with no new rows; window refused 409; blocked rule returns 403 `reschedule_blocked` with clinic phone; slot of another clinic or length returns 422 (repo: clinic-api)
- [ ] T035 [P] [US3] Concurrency test in `tests/booking/test_reschedule_race.py`: two patients take the same slot at once, exactly one succeeds, the loser keeps the original appointment and gets 409 `slot_taken` with `next_slots`; 0 overlapping active appointments over 100 runs (repo: clinic-api)
- [ ] T036 [P] [US3] Screen tests in `src/pages/__tests__/ReschedulePickerPage.test.tsx`: slot list, pick and confirm, `slot_taken` shows the next slots, no free slot shows the clinic phone number, blocked shows the phone number (repo: clinic-web)

### Implementation for User Story 3

- [ ] T037 [P] [US3] Implement `free_slots_for_reschedule(session, appointment, date_from, date_to)` in `app/scheduling/reschedule_slots.py` using the free-slot calculation of feature 002 for the appointment's clinic and treatment with any dentist, honouring the booking horizon (repo: clinic-api)
- [ ] T038 [P] [US3] Implement `recreate_reminder(session, appointment)` in `app/messaging/reminder_port.py`, delegating the timing rules (quiet hours, less than 24 h ahead) to the feature 006 scheduler and cancelling the old row first (repo: clinic-api) (depends on T026)
- [ ] T039 [US3] Implement `list_reschedule_slots` in `app/booking/patient_service.py` and `GET /api/appointments/{appointmentId}/reschedule-slots` in `app/booking/patient_router.py`: 404 foreign, 409 `within_cutoff`, 403 `reschedule_blocked` (repo: clinic-api) (depends on T018, T037)
- [ ] T040 [US3] Implement `reschedule_appointment` in `app/booking/patient_service.py`: one transaction with row lock, ownership, status, window, `RescheduleRule`, validate target slot belongs to the clinic and treatment length, update dentist and times, map SQLSTATE 23P01 to `slot_taken` with next free slots, `write_event`, `recreate_reminder`, `queue_change_message`, metrics (repo: clinic-api) (depends on T028, T037, T038, T039)
- [ ] T041 [US3] Implement `POST /api/appointments/{appointmentId}/reschedule` in `app/booking/patient_router.py` returning 200, 403, 404, 409 or 422 per the contract (repo: clinic-api) (depends on T029, T040)
- [ ] T042 [US3] Create `src/pages/ReschedulePickerPage.tsx` (slot picker): days and slots from `reschedule-slots`, shows dentist name per slot, confirm step, tap targets at least 44 px (repo: clinic-web) (depends on T031)
- [ ] T043 [US3] Wire "Change time" in `src/pages/AppointmentPage.tsx` and error handling in `src/pages/ReschedulePickerPage.tsx` and `src/api/appointments.ts`: `slot_taken` shows next slots and keeps the original, `within_cutoff` and `reschedule_blocked` show `ClinicPhoneNotice`, success goes to the Done screen (repo: clinic-web) (depends on T032, T042)

**Checkpoint**: User Stories 1, 2 and 3 work independently

---

## Phase 6: User Story 4 - Open an appointment from a message link (Priority: P2)

**Goal**: The link in a confirmation, change message or reminder opens the appointment after sign-in, for its owner only. (FR-015, FR-016, FR-017)

**Independent Test**: Quickstart scenario 4: open the link signed out, sign in, land on the appointment; open it as another patient and see "not found".

### Tests for User Story 4

- [ ] T044 [P] [US4] Tests in `src/auth/__tests__/ReturnTo.test.tsx`: signed-out visit of `/appointments/:id` goes to sign-in and returns to the same path afterwards, signed-in visit opens at once, `returnTo` accepts only paths inside the app (no open redirect) (repo: clinic-web)
- [ ] T045 [P] [US4] Test in `tests/messaging/test_appointment_link.py` that confirmation, change and reminder messages carry the link `<web base>/appointments/<appointment id>` (repo: clinic-api)

### Implementation for User Story 4

- [ ] T046 [US4] Create the route guard in `src/auth/ReturnTo.tsx` (stores `returnTo`, sends signed-out users to the sign-in screen of feature 001, returns them after sign-in) and apply it to the four appointment routes in `src/routes.tsx` (repo: clinic-web) (depends on T044)
- [ ] T047 [US4] Show "Appointment not found" with a "Sign out" option in `src/pages/AppointmentPage.tsx` when the API answers 404, without any detail of the appointment (repo: clinic-web) (depends on T021, T046)
- [ ] T048 [US4] Add or extend `appointment_link(appointment_id)` in `app/messaging/links.py` using the configured web base URL and use it in `app/messaging/change_messages.py` (repo: clinic-api) (depends on T025, T045)

**Checkpoint**: All user stories work independently

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T049 [P] Security test matrix in `tests/booking/test_patient_rbac_matrix.py`: every operation with no session, a staff session, the owner and another patient; 0 cross-patient reads (QA-007) (repo: clinic-api)
- [ ] T050 [P] Test in `tests/booking/test_no_pii_in_logs.py` that cancel and reschedule logs contain ids and the correlation id but no name or phone (repo: clinic-api)
- [ ] T051 [P] Check that an index on `(patient_id, start_at)` exists for the list query; if not add an Alembic migration in `alembic/versions/` (forward-only, compatible with the previous release) (repo: clinic-api)
- [ ] T052 [P] Check 360 px layout and 44 px tap targets on all four screens and adjust `src/styles/appointments.css` (repo: clinic-web)
- [ ] T053 Run the quickstart scenarios in `specs/004-patient-appointments/quickstart.md` against staging with sandbox providers, check that 95% of list and appointment screens load in under 2 s and cancel or reschedule is confirmed in under 3 s on a 4G profile (SC-006), and record the result in that file (repo: clinic-api) (depends on T041, T043, T047, T048)

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1) has no dependency.
- Foundational (Phase 2) depends on Setup and blocks all stories.
- User Story 1 (P1) starts after Phase 2.
- User Story 2 (P1) starts after Phase 2; it reuses the service and screens of US1 (T017, T021).
- User Story 3 (P2) builds on US2 (shared service file, Done screen, confirm flow).
- User Story 4 (P2) needs the appointment screen of US1 and the message builder of US2.
- Polish depends on all stories.

### Within Each Story

Tests first and failing, then queries and services, then endpoints, then screens.

### Parallel Opportunities

- T002 and T003; T004, T006, T008, T010, T011 in Phase 2.
- US1 tests T012 to T015 in parallel; T019 in parallel with T016 to T018 (different repos).
- US2: T022 to T024 and T025 to T027, T030, T031 in parallel.
- US3: T033 to T036, T037 and T038 in parallel.
- Backend and web tasks of one story can run in parallel because the contract is fixed.

## Implementation Strategy

1. MVP: Setup, Foundational, US1 (see appointments), then US2 (cancel), which frees chairs.
2. Add US3 (reschedule) and US4 (deep link).
3. Polish and the quickstart run on staging.

Estimate guide: MOD-04 is 4-7 person-days; US1 and US2 each about a quarter, US3 about a third, US4 and polish the rest.
