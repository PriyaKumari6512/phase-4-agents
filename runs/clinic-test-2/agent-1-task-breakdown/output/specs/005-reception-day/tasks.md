---

description: "Task list for MOD-05 Reception day view, check-in, no-shows and dentist day"
---

# Tasks: Reception day view, check-in, no-shows and dentist day (MOD-05)

**Input**: Design documents from `/specs/005-reception-day/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/reception-day.openapi.yaml, quickstart.md. Features 001 (identity, access context), 002 (scheduling, slots) and 003 (appointments, no-overlap rule, history table) provide the base; feature 006 provides the message interface.

**Tests**: Included, because the constitution requires tests first for business logic. Write each test task first and see it fail.

**Organization**: Grouped by user story. Every task states its repo: `clinic-api` (brightsmile/clinic-api) or `clinic-web` (brightsmile/clinic-web). Paths are relative to that repo root.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label (US1 to US5); setup, foundational and polish tasks have none

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Module and feature skeletons in both repos

- [ ] T001 [P] Create the cmp-reception package with empty `app/modules/reception/__init__.py`, `app/modules/reception/router.py` (APIRouter with prefix `/api`) and `app/modules/reception/schemas.py`, and register the router in `app/main.py` (repo: clinic-api)
- [ ] T002 [P] Create the feature folders `src/features/reception/api/` and `src/features/dentist/api/` with placeholder `src/features/reception/index.ts` and `src/features/dentist/index.ts`, and add the lazy route entries `/reception` and `/my-day` in `src/app/routes.tsx` (repo: clinic-web)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: IST day rules, status rules, history writing and access helpers used by every story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 [P] Write unit tests for IST day boundaries and the injectable clock (start and end of an IST day, 23:59:59 IST, UTC conversion across midnight) in `tests/unit/test_time_ist.py` (repo: clinic-api)
- [ ] T004 Implement `ist_date_of`, `end_of_ist_day` and an injectable `now()` clock with zone `Asia/Kolkata` in `app/core/time_ist.py` (repo: clinic-api)
- [ ] T005 [P] Write unit tests for the status transition table and the no-show window (14 minutes refused, 15 minutes allowed, next IST day refused, undo only on the same IST day, cancelled statuses final) in `tests/unit/booking/test_status_rules.py` (repo: clinic-api)
- [ ] T006 Implement the five statuses `booked`, `arrived`, `no_show`, `cancelled_by_patient`, `cancelled_by_clinic`, the allowed-transition table and `check_no_show_window` / `check_undo_window` in `app/modules/booking/status_rules.py`, using `app/core/time_ist.py` (repo: clinic-api) (depends on T004)
- [ ] T007 Add an Alembic migration `migrations/versions/005_reception_status_and_index.py` that extends the status check constraint on `appointment` to the five statuses if missing and adds an index on `(clinic_id, start_at)` for the day view, compatible with the previous release (expand only) (repo: clinic-api; builds on the feature 003 appointment migration)
- [ ] T008 [P] Write integration tests for `change_status`: the conditional update succeeds once, a second change from a stale status returns a conflict, the history row (previous and new status, actor, time, reason) commits in the same transaction and rolls back with it, in `tests/integration/booking/test_status_service.py` (repo: clinic-api)
- [ ] T009 Implement `change_status(appointment_id, expected_from, to_status, actor, reason)` with `UPDATE ... WHERE id = :id AND status = :expected_from` and an insert into `ent-appointment-event` in one transaction in `app/modules/booking/status_service.py` (repo: clinic-api) (depends on T006, T007)
- [ ] T010 [P] Write unit tests for the access helpers: a receptionist gets the clinic id from the database, a dentist gets the dentist id, other roles get 403, an appointment of another clinic gives 404, in `tests/unit/reception/test_access.py` (repo: clinic-api)
- [ ] T011 Implement `require_receptionist()` and `require_dentist()` on top of the cmp-identity access context in `app/modules/reception/access.py` (repo: clinic-api) (depends on T010)

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Reception sees the day of their clinic (Priority: P1) 🎯 MVP

**Goal**: A receptionist sees today's day view of their clinic, one column per working dentist, and can move to other days. (FR-019)

**Independent Test**: Seed one clinic with three working dentists and appointments in several statuses, sign in as its receptionist, view today and other days, and check columns, fields and that the other clinic's appointments are absent.

### Tests for User Story 1

- [ ] T012 [P] [US1] Contract test for `GET /api/reception/day` against `contracts/clinic-api-v1.openapi.yaml` in `tests/contract/test_day_view_contract.py` (repo: clinic-api)
- [ ] T013 [P] [US1] Integration test for the day view: one column per dentist with hours that day, no column without hours, fields name, phone, treatment and status, cancelled shown, other clinic absent and 404 for its appointment, in `tests/integration/reception/test_day_view.py` (repo: clinic-api)

### Implementation for User Story 1

- [ ] T014 [US1] Implement the day view read model (dentists with working hours at the clinic on the date from the cmp-scheduling interface, appointments of the clinic and date joined with patient and treatment, grouped by dentist, ordered by start) in `app/modules/reception/day_view.py` (repo: clinic-api) (depends on T011)
- [ ] T015 [US1] Add the `DayView` schemas to `app/modules/reception/schemas.py` and the route `GET /api/reception/day?date=` (default today in IST, receptionist only) in `app/modules/reception/router.py` (repo: clinic-api)
- [ ] T016 [P] [US1] Add the day view API client `getDayView(date)` and types in `src/features/reception/api/dayView.ts` (repo: clinic-web)
- [ ] T017 [US1] Build the day view screen with one column per dentist, appointment cards (patient name, phone, treatment, status badge), previous day, next day and date picker in `src/features/reception/DayViewPage.tsx` (repo: clinic-web) (depends on T016)
- [ ] T018 [P] [US1] Component test for the day view (columns, status badges, date navigation, empty day message) in `src/features/reception/DayViewPage.test.tsx` (repo: clinic-web)
- [ ] T019 [US1] Make `/reception` the landing route of the receptionist role after sign-in in `src/app/routes.tsx` (repo: clinic-web) (depends on T017)

**Checkpoint**: User Story 1 is functional and testable on its own

---

## Phase 4: User Story 2 - Reception marks arrived and no-show, and can undo (Priority: P1)

**Goal**: Mark arrived, mark no-show from 15 minutes after the start until the end of the day, undo the same day, with who and when recorded for every change. (FR-021, FR-022, FR-024)

**Independent Test**: Appointments that started 5, 20 and 120 minutes ago and one tomorrow: mark arrived, refuse and allow no-show around 15 minutes, undo, refuse after the day ends, read the history.

### Tests for User Story 2

- [ ] T020 [P] [US2] Integration tests for `arrive`, `no-show` and `undo` (15-minute boundary, tomorrow refused, previous day refused, undo same day only, arrived to booked, cancelled refused, other clinic 404, simultaneous change gives `changed_by_other`) and for the history endpoint, in `tests/integration/reception/test_arrive_noshow.py` (repo: clinic-api)

### Implementation for User Story 2

- [ ] T021 [US2] Implement `POST /api/reception/appointments/{id}/arrive`, `/no-show` and `/undo` (clinic-scoped lookup, calls `change_status`, maps rule violations to 409 with `code` and `allowed_from`) in `app/modules/reception/status_router.py` and include it in `app/modules/reception/router.py` (repo: clinic-api) (depends on T009, T011)
- [ ] T022 [US2] Implement `GET /api/reception/appointments/{id}/history` (who, from, to, when, reason; clinic-scoped) in `app/modules/booking/history_router.py` and include it in `app/modules/reception/router.py` (repo: clinic-api) (depends on T021)
- [ ] T023 [P] [US2] Add API clients `markArrived`, `markNoShow`, `undoStatus`, `getHistory` in `src/features/reception/api/statusActions.ts` (repo: clinic-web)
- [ ] T024 [US2] Build the appointment panel with Arrived, No-show (disabled with the allowed-from time before 15 minutes after start) and Undo buttons, status and history list in `src/features/reception/AppointmentPanel.tsx` (repo: clinic-web) (depends on T023)
- [ ] T025 [US2] Open the appointment panel from an appointment card in `src/features/reception/DayViewPage.tsx` and refresh the day view after each action, showing the "changed by someone else" message on conflict (repo: clinic-web) (depends on T017, T024)
- [ ] T026 [P] [US2] Component test for the panel (button states by time, undo, conflict message, history) in `src/features/reception/AppointmentPanel.test.tsx` (repo: clinic-web)

**Checkpoint**: User Stories 1 and 2 work independently

---

## Phase 5: User Story 3 - Reception finds or creates a patient (Priority: P1)

**Goal**: Find a patient by phone number or name across all patients, or create one with name and phone number. (FR-020)

**Independent Test**: Search by full and part phone number and by name, find a patient of the other clinic without seeing appointments, create a patient, try a duplicate phone number.

### Tests for User Story 3

- [ ] T027 [P] [US3] Integration tests for search (4+ digits, 2+ letters, +91 and spaces normalised, cap of 20, patient of the other clinic found with no appointments) and create (valid, duplicate phone returns the existing patient, blank name and invalid phone give 422), in `tests/integration/reception/test_patient_search.py` (repo: clinic-api)

### Implementation for User Story 3

- [ ] T028 [US3] Add or reuse `normalise_indian_mobile(raw)` (10 digits starting 6 to 9, optional +91, stored as +91XXXXXXXXXX) in `app/modules/identity/phone.py` (repo: clinic-api)
- [ ] T029 [US3] Implement `search_patients(q)` (phone suffix match or name contains, case-insensitive, id, name and phone only, at most 20) and `create_patient(name, phone)` (account plus person per ADR-0008, "name 2 to 100 characters", duplicate phone returns the existing one) in `app/modules/identity/patient_service.py` (repo: clinic-api) (depends on T028)
- [ ] T030 [US3] Implement `GET /api/reception/patients/search?q=` and `POST /api/reception/patients` (receptionist only, input validation, no name or phone in logs) in `app/modules/reception/patient_router.py` and include it in `app/modules/reception/router.py` (repo: clinic-api) (depends on T011, T029)
- [ ] T031 [P] [US3] Add API clients `searchPatients(q)` and `createPatient(name, phone)` in `src/features/reception/api/patients.ts` (repo: clinic-web)
- [ ] T032 [US3] Build the patient search component with debounced search, result list (name and phone) and an inline create form with validation messages in `src/features/reception/PatientSearch.tsx` (repo: clinic-web) (depends on T031)
- [ ] T033 [P] [US3] Component test for patient search and create (short query hint, results, duplicate phone message, validation) in `src/features/reception/PatientSearch.test.tsx` (repo: clinic-web)

**Checkpoint**: User Stories 1 to 3 work independently

---

## Phase 6: User Story 4 - Reception books, moves and cancels for patients (Priority: P1)

**Goal**: Book any treatment type (including reception-only and walk-ins), move and cancel without the 4-hour rule; cancel records who asked; messages requested. (FR-020, FR-021, FR-024)

**Independent Test**: Book a 90-minute reception-only treatment 1 hour ahead, book a walk-in (arrived), move one appointment, hit an overlap, cancel one as patient asked and one as clinic cancelled, and check the day view and history.

### Tests for User Story 4

- [ ] T034 [P] [US4] Integration tests for reception booking: any active type, no 4-hour or 30-day limit, walk-in created arrived with reason "walk-in", overlap gives 409 with next slots, move keeps id and writes history, cancel with `asked_by` patient or clinic, other clinic 404, booking kept when the message port fails, repeated Idempotency-Key books once, in `tests/integration/reception/test_reception_booking.py` (repo: clinic-api)
- [ ] T035 [P] [US4] Concurrency test: 1,000 simultaneous attempts on one slot from reception and online give exactly one success and no overlap, in `tests/integration/booking/test_reception_booking_race.py` (repo: clinic-api)

### Implementation for User Story 4

- [ ] T036 [P] [US4] Define the messaging port `notify_confirmation(appointment_id)` and `notify_change(appointment_id)` with a no-op default until feature 006 is merged in `app/modules/booking/notify_port.py` (repo: clinic-api)
- [ ] T037 [P] [US4] Add an audience option "reception" to the free-slot calculation (all active treatment types, no 30-day horizon, already started slots of today selectable, past days refused) in `app/modules/scheduling/slots.py` (repo: clinic-api)
- [ ] T038 [US4] Implement reception `book` (walk-in inserts with status arrived), `move` and `cancel(asked_by)` with the shared insert path and the ADR-0003 constraint, idempotency key, history rows through `change_status`, 409 with next free slots on conflict, and messages requested after commit without failing the request, in `app/modules/booking/reception_service.py` (repo: clinic-api) (depends on T009, T036, T037)
- [ ] T039 [US4] Implement `GET /api/reception/slots`, `POST /api/reception/appointments`, `/{id}/move` and `/{id}/cancel` (receptionist only, clinic from access context, input validation) in `app/modules/reception/booking_router.py` and include it in `app/modules/reception/router.py` (repo: clinic-api) (depends on T011, T038)
- [ ] T040 [P] [US4] Add API clients `getReceptionSlots`, `bookForPatient` (sends Idempotency-Key), `moveAppointment`, `cancelAppointment` in `src/features/reception/api/bookings.ts` (repo: clinic-web)
- [ ] T041 [US4] Build the "book for patient" screen: selected patient from the patient search, any treatment type, dentist, date, slot picker, walk-in switch, "slot just taken" message with next slots, in `src/features/reception/BookForPatient.tsx` (repo: clinic-web) (depends on T032, T040)
- [ ] T042 [US4] Add Move (opens the slot picker) and Cancel (dialog "patient asked" or "clinic cancelled") to the appointment panel in `src/features/reception/AppointmentPanel.tsx` (repo: clinic-web) (depends on T024, T041)
- [ ] T043 [US4] Add a "New booking" button and a click-on-free-time entry that open the book-for-patient screen in `src/features/reception/DayViewPage.tsx` (repo: clinic-web) (depends on T025, T041)
- [ ] T044 [P] [US4] Component test for the book-for-patient screen and the cancel dialog (walk-in, conflict message, asked-by choice) in `src/features/reception/BookForPatient.test.tsx` (repo: clinic-web)

**Checkpoint**: User Stories 1 to 4 work independently

---

## Phase 7: User Story 5 - Dentist sees their own day, read only (Priority: P2)

**Goal**: A dentist sees their own appointments at each clinic they work at that day, read only. (FR-023)

**Independent Test**: A dentist working at both clinics sees both, with only their own appointments and no actions; change requests are refused.

### Tests for User Story 5

- [ ] T045 [P] [US5] Integration tests for `GET /api/dentist/my-day`: two clinics grouped, only own appointments, no phone number in the payload, receptionist 403, dentist POST to arrive 403, other date, in `tests/integration/reception/test_dentist_day.py` (repo: clinic-api)

### Implementation for User Story 5

- [ ] T046 [US5] Implement the dentist day read model (own appointments for the date grouped by clinic, time, patient name, treatment, status) in `app/modules/reception/dentist_day.py` (repo: clinic-api) (depends on T011)
- [ ] T047 [US5] Implement `GET /api/dentist/my-day?date=` (dentist only) in `app/modules/reception/dentist_router.py` and include it in `app/modules/reception/router.py` (repo: clinic-api) (depends on T046)
- [ ] T048 [P] [US5] Add the API client `getMyDay(date)` in `src/features/dentist/api/myDay.ts` (repo: clinic-web)
- [ ] T049 [US5] Build the read-only mobile-first "my day" screen grouped by clinic with day navigation and no action buttons in `src/features/dentist/MyDayPage.tsx` (repo: clinic-web) (depends on T048)
- [ ] T050 [US5] Make `/my-day` the landing route of the dentist role in `src/app/routes.tsx` (repo: clinic-web) (depends on T019, T049)
- [ ] T051 [P] [US5] Component test for "my day" (two clinics, no actions, narrow screen layout) in `src/features/dentist/MyDayPage.test.tsx` (repo: clinic-web)

**Checkpoint**: All user stories work independently

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Security, observability, contract, performance and go-live readiness

- [ ] T052 [P] Role and clinic matrix test: every endpoint of this feature as receptionist of each clinic, dentist, patient, manager and anonymous, with 0 cross-clinic reads, in `tests/security/test_reception_rbac.py` (repo: clinic-api)
- [ ] T053 [P] Add OpenTelemetry spans, a counter of status changes by status and structured logs with ids and correlation id only (no patient name or phone) in `app/modules/reception/telemetry.py` and use them in the routers of `app/modules/reception/` (repo: clinic-api)
- [ ] T054 Merge the paths and schemas of `specs/005-reception-day/contracts/reception-day.openapi.yaml` into `contracts/clinic-api-v1.openapi.yaml` and run the contract tests (repo: clinic-api) (depends on T039, T047)
- [ ] T055 [P] Performance test for the day view with 6 columns of 16 appointments (payload about 15 KB, server p95 at most 500 ms) in `tests/performance/test_day_view_load.py` (repo: clinic-api)
- [ ] T056 [P] Write the paper-diary dry-run guide (typing a week of future appointments per clinic, comparing day views with the paper diary, SA-005) in `docs/reception-dry-run.md` (repo: clinic-api)
- [ ] T057 Run the scenarios of `specs/005-reception-day/quickstart.md` against staging and record the result in `docs/reception-quickstart-result.md` (repo: clinic-api) (depends on T043, T050, T054)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none; T001 and T002 in parallel
- **Foundational (Phase 2)**: after Setup; blocks all stories. T003 to T006 (IST and rules), T007 to T009 (migration and status service), T010 and T011 (access) can run as three parallel lines
- **User Stories (Phase 3 to 7)**: all after Phase 2
- **Polish (Phase 8)**: after the stories

### User Story Dependencies

- **US1**: after Phase 2, no story dependency (MVP)
- **US2**: backend after Phase 2; the panel is opened from the US1 day view (T025 depends on T017)
- **US3**: after Phase 2; independent of US1 and US2
- **US4**: backend after Phase 2 (needs feature 002 slots); screens need US3's patient search (T041) and US2's panel (T042) and US1's day view (T043)
- **US5**: backend after Phase 2; landing route needs US1's route file edit (T050 after T019)

### Within Each Story

- Tests first and failing; then services, endpoints, screens
- Backend and web tasks of a story can proceed in parallel against the contract

### Parallel Opportunities

- US1 backend (T014, T015) and web (T016 to T018); US3 (T027 to T033) and US5 backend (T045 to T047) can all run in parallel with US1 and US2 by different developers
- Test tasks marked [P] in each story run together

## Parallel Example: User Story 4

```text
Task: "Integration tests for reception booking in tests/integration/reception/test_reception_booking.py"
Task: "Concurrency test in tests/integration/booking/test_reception_booking_race.py"
Task: "Messaging port in app/modules/booking/notify_port.py"
Task: "Reception audience option in app/modules/scheduling/slots.py"
Task: "API clients in src/features/reception/api/bookings.ts"
```

## Implementation Strategy

### MVP First

1. Setup and Foundational
2. US1 (day view), then US2 (arrived and no-show): reception can run the day
3. US3 and US4: phone and walk-in booking and the paper-diary typing before the dry run
4. US5: dentist day
5. Polish: RBAC matrix, telemetry, contract merge, performance, quickstart on staging

### Incremental Delivery

Each story is demoable on staging when done. The day view and status actions (US1, US2) can be shown to reception first; US3 and US4 must be ready for the dry run in the week before go-live (DL-1 2027-02-22).

## Notes

- Q-015 (walk-in recording) is assumed as a normal appointment marked arrived; Q2 (undo of arrived) assumed allowed; see clarifications.md
- No patient name, phone or birth year in logs (constitution)
- Commit after each task or logical group
