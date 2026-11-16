---

description: "Task list for Clinics, dentist hours, leave, treatments and free slots"
---

# Tasks: Clinics, dentist hours, leave, treatments and free slots

**Input**: Design documents from `/specs/003-clinic-schedule-setup/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included. The constitution requires business logic to be covered by tests written before or with the code, and every user story has an independent test. Write each test first and see it fail.

**Organization**: Tasks are grouped by user story so each can be implemented and tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on unfinished tasks)
- **[Story]**: Which user story the task belongs to (US1 to US6)
- File paths start with the repository folder: `clinic-api/` is brightsmile/clinic-api, `clinic-web/` is brightsmile/clinic-web

## Path Conventions

- API module: `clinic-api/app/modules/scheduling/` (routes in `api/`, logic in `services/`)
- API tests: `clinic-api/tests/scheduling/{unit,integration,contract,perf}/`
- Web feature: `clinic-web/src/features/scheduling/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Module skeleton and shared contract

- [ ] T001 Create the cmp-scheduling module skeleton with empty `__init__.py` files in `clinic-api/app/modules/scheduling/`, `clinic-api/app/modules/scheduling/api/`, `clinic-api/app/modules/scheduling/services/` and the test folders `clinic-api/tests/scheduling/unit/`, `clinic-api/tests/scheduling/integration/`, `clinic-api/tests/scheduling/contract/`, `clinic-api/tests/scheduling/perf/`
- [ ] T002 [P] Add the scheduling paths and schemas from `specs/003-clinic-schedule-setup/contracts/scheduling-api.openapi.yaml` to `clinic-api/contracts/clinic-api-v1.openapi.yaml`
- [ ] T003 [P] Create TypeScript types for Clinic, Dentist, TreatmentType, WeeklyHours, Leave, ToMoveItem, Slot and SlotPage from the contract in `clinic-web/src/features/scheduling/types.ts`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Tables, ports, access checks, time helpers and test fixtures that every story needs

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Create SQLAlchemy models Clinic, Dentist, TreatmentType, WorkingHours, WorkingBreak, Leave and SchedulingSetting in `clinic-api/app/modules/scheduling/models.py` with these constraints from data-model.md: `treatment_type.duration_minutes` greater than 0 and a multiple of 30; `working_hours.weekday` 0 to 6; `working_hours.end_time` greater than `start_time`; `working_break.end_time` greater than `start_time`, break rows cascade on delete of their working_hours; `leave.end_at` greater than `start_at`; unique `(dentist_id, clinic_id, weekday)` on working_hours; times of day are IST wall clock, instants are `timestamptz` UTC
- [ ] T005 Create the Alembic migration in `clinic-api/alembic/versions/0003_scheduling.py` for all tables of T004, the unique index `(dentist_id, clinic_id, weekday)`, index `(clinic_id, weekday)` on working_hours, index `(dentist_id, start_at, end_at)` on leave, a case-insensitive unique index on active clinic name and on active treatment-type name, and data rows: check-up, cleaning and consultation (30 minutes, online, active) and `booking_horizon_days` = 30 (depends on T004)
- [ ] T006 [P] Define the AppointmentsPort protocol (`busy_intervals(dentist_ids, start, end)` for non-cancelled appointments; `booked_overlapping(dentist_id, start, end, clinic_id=None)` for booked appointments with clinic, dentist, times, treatment name, patient name and phone), its data classes and the `EmptyAppointments` stand-in in `clinic-api/app/modules/scheduling/ports.py`
- [ ] T007 [P] Create the access adapter over cmp-identity's access context with `require_manager`, `require_signed_in` and `require_manager_or_own_clinic_reception(clinic_id)` in `clinic-api/app/modules/scheduling/access.py`, deciding scope only from the authenticated context and never from request ids alone
- [ ] T008 [P] Write unit tests for IST conversion (date plus IST time of day to UTC instant, whole-day range to `[00:00 IST first day, 00:00 IST day after last day)`, HH:MM parsing, weekday of an IST date) in `clinic-api/tests/scheduling/unit/test_ist.py`
- [ ] T009 [P] Implement the IST helpers in `clinic-api/app/modules/scheduling/ist.py` so T008 passes
- [ ] T010 [P] Add structured logging helpers (ids and correlation id only, never names or phone numbers), OpenTelemetry spans for the scheduling routes and a slot-request duration histogram in `clinic-api/app/modules/scheduling/telemetry.py`
- [ ] T011 Create the repository base (session handling and the `booking_horizon_days` read) in `clinic-api/app/modules/scheduling/repository.py` (depends on T004)
- [ ] T012 Create the scheduling router aggregator and register it with the application in `clinic-api/app/modules/scheduling/router.py` and `clinic-api/app/main.py` (depends on T007)
- [ ] T013 [P] Create pytest fixtures (database session, manager, receptionist per clinic, dentist and patient sessions, and a fake AppointmentsPort that tests can fill) in `clinic-api/tests/scheduling/conftest.py` (depends on T006)
- [ ] T014 [P] Write a reusable port contract test run against `EmptyAppointments` and the fake, so cmp-booking can reuse it, in `clinic-api/tests/scheduling/contract/test_appointments_port_contract.py` (depends on T006)
- [ ] T015 [P] Create the API client wrapper for the scheduling routes (cookie session, CSRF header on writes, 10-second timeout) in `clinic-web/src/features/scheduling/api.ts` (depends on T003)
- [ ] T016 [P] Create IST display and input helpers in `clinic-web/src/features/scheduling/time.ts`
- [ ] T017 [P] Create the route table with an empty page list for the scheduling screens in `clinic-web/src/features/scheduling/routes.tsx`

**Checkpoint**: Foundation ready; user stories can start

---

## Phase 3: User Story 1 - Clinics and dentists held as data (Priority: P1) 🎯 MVP

**Goal**: The practice manager adds, edits and deactivates clinics and dentists in the staff screens; a third clinic arrives as data with no deploy.

**Independent Test**: As manager, add a third clinic and a dentist; both appear in the lists for all roles at once; mark the clinic inactive and it leaves the list offered to patients; other roles are refused on writes.

### Tests for User Story 1

- [ ] T018 [P] [US1] Write contract tests for `GET/POST /api/clinics`, `PATCH /api/clinics/{clinicId}`, `GET/POST /api/dentists`, `PATCH /api/dentists/{dentistId}` in `clinic-api/tests/scheduling/contract/test_clinics_dentists_contract.py`
- [ ] T019 [P] [US1] Write integration tests (add third clinic visible to patient at once, inactive clinic hidden from patients, existing appointments kept, duplicate active name returns 409, receptionist/dentist/patient writes return 403) in `clinic-api/tests/scheduling/integration/test_clinics_dentists.py`

### Implementation for User Story 1

- [ ] T020 [US1] Create request and response schemas for clinics and dentists (name, address, phone required for a clinic; `name` for a dentist; trimmed non-empty text; limits from data-model.md: clinic name at most 120 characters, address at most 300, phone at most 20; dentist name at most 120) in `clinic-api/app/modules/scheduling/schemas_catalog.py`
- [ ] T021 [US1] Implement clinic and dentist create, edit, deactivate and list (patients see active only; never delete) in `clinic-api/app/modules/scheduling/services/catalog.py` (depends on T011, T020)
- [ ] T022 [US1] Implement the clinic and dentist routes with manager-only writes in `clinic-api/app/modules/scheduling/api/catalog.py` and include them in `clinic-api/app/modules/scheduling/router.py` (depends on T021, T012)
- [ ] T023 [P] [US1] Build the Clinics page (clinic list and form, dentist list and form, active toggle, error messages in English) in `clinic-web/src/features/scheduling/pages/ClinicsPage.tsx` (depends on T015)
- [ ] T024 [P] [US1] Write component tests for the Clinics page (add clinic, deactivate, server refusal shown) in `clinic-web/src/features/scheduling/__tests__/ClinicsPage.test.tsx`

**Checkpoint**: User Story 1 works on its own (clinics and dentists as data)

---

## Phase 4: User Story 2 - Treatment types with duration and online flag (Priority: P1)

**Goal**: Treatment types with duration and online flag, editable by the manager; patients see only active online types.

**Independent Test**: List as patient (3 online types), add "Root canal" 90 minutes online off as manager, see it as reception but not as patient; 45 minutes is refused.

### Tests for User Story 2

- [ ] T025 [P] [US2] Write contract tests for `GET/POST /api/treatment-types` and `PATCH /api/treatment-types/{treatmentTypeId}` in `clinic-api/tests/scheduling/contract/test_treatment_types_contract.py`
- [ ] T026 [P] [US2] Write integration tests (3 online types present at start, role-based list, duration 45 refused with 422, deactivate keeps the record, non-manager writes 403, changed duration does not change existing appointments) in `clinic-api/tests/scheduling/integration/test_treatment_types.py`

### Implementation for User Story 2

- [ ] T027 [US2] Create treatment-type schemas (`durationMinutes` a positive multiple of 30; `online` boolean; name unique among active types) in `clinic-api/app/modules/scheduling/schemas_treatments.py`
- [ ] T028 [US2] Implement treatment-type create, edit, deactivate and role-filtered list (patients: active and online only; reception: all active; manager: optional inactive) in `clinic-api/app/modules/scheduling/services/treatments.py` (depends on T011, T027)
- [ ] T029 [US2] Implement the treatment-type routes in `clinic-api/app/modules/scheduling/api/treatments.py` and include them in `clinic-api/app/modules/scheduling/router.py` (depends on T028, T012)
- [ ] T030 [P] [US2] Build the Treatments page (table, add and edit form, online toggle, active toggle) in `clinic-web/src/features/scheduling/pages/TreatmentsPage.tsx` (depends on T015)
- [ ] T031 [P] [US2] Write component tests for the Treatments page (add 90-minute reception-only type, 45-minute refusal shown) in `clinic-web/src/features/scheduling/__tests__/TreatmentsPage.test.tsx`

**Checkpoint**: User Stories 1 and 2 work independently

---

## Phase 5: User Story 3 - Weekly working hours and breaks per dentist per clinic (Priority: P1)

**Goal**: The manager sets each dentist's weekly hours and breaks at each clinic; a dentist can work at several clinics on set days without overlapping.

**Independent Test**: Set Monday 09:00–17:00 with a 13:00–14:00 break at clinic A and Thursday hours at clinic B; read back; overlapping Monday hours at clinic B are refused.

### Tests for User Story 3

- [ ] T032 [P] [US3] Write unit tests for hours validation (end after start, break inside window, breaks not overlapping, one window per weekday, cross-clinic overlap for one dentist on one weekday refused, disjoint windows accepted) in `clinic-api/tests/scheduling/unit/test_hours_validation.py`
- [ ] T033 [P] [US3] Write integration tests (PUT then GET returns the same week, day off by omitting a weekday, 409 on cross-clinic overlap, 422 on invalid breaks, non-manager PUT 403, reception of the clinic and dentist can GET, existing appointments untouched after a change) in `clinic-api/tests/scheduling/integration/test_weekly_hours.py`
- [ ] T034 [P] [US3] Write contract tests for `GET/PUT /api/dentists/{dentistId}/clinics/{clinicId}/hours` in `clinic-api/tests/scheduling/contract/test_hours_contract.py`

### Implementation for User Story 3

- [ ] T035 [US3] Create weekly-hours schemas (`weekday` 0 to 6, `start` and `end` as HH:MM, `breaks` list, at most one entry per weekday) in `clinic-api/app/modules/scheduling/schemas_hours.py`
- [ ] T036 [US3] Implement the validation rules and the replace-whole-week save in one transaction in `clinic-api/app/modules/scheduling/services/hours.py` (depends on T011, T035)
- [ ] T037 [US3] Implement `GET` and `PUT` hours routes (manager writes; manager, reception of the clinic and dentist read) in `clinic-api/app/modules/scheduling/api/hours.py` and include them in `clinic-api/app/modules/scheduling/router.py` (depends on T036, T012)
- [ ] T038 [US3] Add `clinicIds` (clinics where the dentist has hours) and the `clinicId` filter to the dentist list in `clinic-api/app/modules/scheduling/services/catalog.py` (depends on T021, T036)
- [ ] T039 [P] [US3] Build the WeeklyHoursEditor and break rows component (seven weekdays, start and end, add and remove breaks, inline validation messages) in `clinic-web/src/features/scheduling/components/WeeklyHoursEditor.tsx` (depends on T016)
- [ ] T040 [US3] Build the Dentists and hours page (pick dentist and clinic, load and save the week, show clinics the dentist works at) in `clinic-web/src/features/scheduling/pages/DentistsHoursPage.tsx` (depends on T039, T015)
- [ ] T041 [P] [US3] Write component tests for the editor and page (save week, break outside hours shown as error, 409 message shown) in `clinic-web/src/features/scheduling/__tests__/DentistsHoursPage.test.tsx`

**Checkpoint**: User Stories 1 to 3 work independently; hours exist for slot calculation

---

## Phase 6: User Story 4 - Free slots for a clinic, dentist and treatment (Priority: P1)

**Goal**: Free slots for one clinic and one date range, and "first available" (top 10, paginated), meeting the 2-second target.

**Independent Test**: With hours 09:00–17:00, break 13:00–14:00, leave 15:00–16:00 and a booked 10:00–10:30 appointment on a Monday, the 30-minute slots are exactly the expected starts; 90-minute slots fit fully in free time; first available returns 10 then the next 10.

### Tests for User Story 4

- [ ] T042 [P] [US4] Write unit tests for the pure slot maths (hour and half-hour grid, 09:15 start gives 09:30 first, break, leave, booked appointment, another clinic's appointment, 90-minute fit, slots before now dropped, empty result) in `clinic-api/tests/scheduling/unit/test_slot_math.py`
- [ ] T043 [P] [US4] Write unit tests for first available (time order across dentists, tie-break by dentist id, 10 per page, page 2 continues, `hasMore`, stops early) in `clinic-api/tests/scheduling/unit/test_first_available.py`
- [ ] T044 [P] [US4] Write integration tests (patient sees only online types and only within today plus the horizon, reception any active type, inactive clinic, dentist or type gives no slots, range over 31 days or reversed gives 422, just-booked appointment from the fake port is excluded, leave rows excluded) in `clinic-api/tests/scheduling/integration/test_slots.py`
- [ ] T045 [P] [US4] Write contract tests for `GET /api/clinics/{clinicId}/slots` and `GET /api/clinics/{clinicId}/slots/first-available` in `clinic-api/tests/scheduling/contract/test_slots_contract.py`

### Implementation for User Story 4

- [ ] T046 [US4] Implement the pure interval functions (subtract intervals, grid walk on :00 and :30, fit of treatment length) in `clinic-api/app/modules/scheduling/services/slot_math.py`
- [ ] T047 [US4] Add the slot queries (one query each for the clinic's dentists' hours with breaks, leave overlapping the range, in index order on dentist and time) in `clinic-api/app/modules/scheduling/repository.py` (depends on T011)
- [ ] T048 [US4] Implement free-slot calculation for one clinic, one date range (at most 31 days), optional dentist, with now and horizon limits for patients and appointments read through the port in `clinic-api/app/modules/scheduling/services/slots.py` (depends on T046, T047, T006)
- [ ] T049 [US4] Implement first available (walk forward in windows, merge in time order, 10 per page, stop early) in `clinic-api/app/modules/scheduling/services/first_available.py` (depends on T048)
- [ ] T050 [US4] Create slot request and response schemas (`Slot`, `SlotPage` with `page`, `pageSize` 10, `hasMore`; `from` and `to` dates) in `clinic-api/app/modules/scheduling/schemas_slots.py`
- [ ] T051 [US4] Implement the slots routes with role rules (patient online types only; reception own clinic; manager any) and the duration metric in `clinic-api/app/modules/scheduling/api/slots.py` and include them in `clinic-api/app/modules/scheduling/router.py` (depends on T048, T049, T050, T010, T012)
- [ ] T052 [P] [US4] Write the performance test (seed 3 clinics, 10 dentists, 1,000 appointments a week; 100 concurrent users; assert server p95 at or under 500 ms for slots and first available) in `clinic-api/tests/scheduling/perf/test_slots_perf.py` (depends on T051)

**Checkpoint**: Free slots work; the booking features can start

---

## Phase 7: User Story 5 - Record dentist leave (Priority: P2)

**Goal**: The manager records whole-day or part-day leave; the response lists appointments to move; the system never moves them; slots drop out.

**Independent Test**: Record whole-day leave on a day with 3 booked appointments (fake port): all 3 are listed, none changes, slots that day are empty; part-day leave lists only overlapping ones; delete restores slots.

### Tests for User Story 5

- [ ] T053 [P] [US5] Write unit tests for leave intervals (whole days to 00:00 IST first day through 00:00 IST day after last day as UTC, part day, end not after start refused, already ended refused) in `clinic-api/tests/scheduling/unit/test_leave_intervals.py`
- [ ] T054 [P] [US5] Write unit tests for the 24-month leave retention job (removes only leave ended more than 24 months ago) in `clinic-api/tests/scheduling/unit/test_leave_retention.py`
- [ ] T055 [P] [US5] Write integration tests (create returns overlapping booked appointments including partial overlap, excludes cancelled and non-overlapping, nothing changed in the fake port, slots exclude leave, delete removes it, non-manager 403) in `clinic-api/tests/scheduling/integration/test_leave.py`
- [ ] T056 [P] [US5] Write contract tests for `GET/POST /api/dentists/{dentistId}/leave` and `DELETE /api/leave/{leaveId}` in `clinic-api/tests/scheduling/contract/test_leave_contract.py`

### Implementation for User Story 5

- [ ] T057 [US5] Create leave schemas (whole days `firstDay`, `lastDay`; part day `date`, `startTime`, `endTime`; `end_at` greater than `start_at`; not in the past) in `clinic-api/app/modules/scheduling/schemas_leave.py`
- [ ] T058 [US5] Implement leave create, list and delete with the IST to UTC conversion in `clinic-api/app/modules/scheduling/services/leave.py` (depends on T009, T011, T057)
- [ ] T059 [US5] Implement the to-move selection for a leave (booked, overlapping `appt.start < leave.end and appt.end > leave.start`, future only, across clinics, read only) in `clinic-api/app/modules/scheduling/services/to_move.py` (depends on T006, T058)
- [ ] T060 [US5] Implement the leave routes (manager only; create answers with `leave` and `toMove`) in `clinic-api/app/modules/scheduling/api/leave.py` and include them in `clinic-api/app/modules/scheduling/router.py` (depends on T058, T059, T012)
- [ ] T061 [US5] Implement the daily 24-month leave retention job and register it with the API's scheduled jobs in `clinic-api/app/modules/scheduling/jobs.py` (depends on T058)
- [ ] T062 [P] [US5] Build the ToMoveTable component (date, time IST, clinic, dentist, patient name, phone, treatment; empty message "Nothing to move") in `clinic-web/src/features/scheduling/components/ToMoveTable.tsx` (depends on T016)
- [ ] T063 [US5] Build the Leave page (dentist picker, whole-day or part-day form, leave list with delete, to-move table after saving) in `clinic-web/src/features/scheduling/pages/LeavePage.tsx` (depends on T062, T015)
- [ ] T064 [P] [US5] Write component tests for the Leave page (whole day, part day, to-move shown, delete) in `clinic-web/src/features/scheduling/__tests__/LeavePage.test.tsx`

**Checkpoint**: Leave works and feeds slots and the to-move result

---

## Phase 8: User Story 6 - Reception sees the appointments to move (Priority: P2)

**Goal**: Reception sees the to-move list of their own clinic; manager can see any clinic; the list updates itself.

**Independent Test**: With leave covering 2 appointments at one clinic and 1 at another, the first clinic's receptionist sees 2 and is refused the other clinic; cancel one in the fake and read again to see 1.

### Tests for User Story 6

- [ ] T065 [P] [US6] Write integration tests (own clinic only, other clinic 403, patient and dentist 403, manager any clinic, moved or cancelled appointment drops off, empty list, earliest first) in `clinic-api/tests/scheduling/integration/test_to_move.py`
- [ ] T066 [P] [US6] Write contract tests for `GET /api/clinics/{clinicId}/to-move` in `clinic-api/tests/scheduling/contract/test_to_move_contract.py`

### Implementation for User Story 6

- [ ] T067 [US6] Add the clinic-level to-move query (all leave of the clinic's dentists, booked appointments at that clinic, earliest first) in `clinic-api/app/modules/scheduling/services/to_move.py` (depends on T059)
- [ ] T068 [US6] Implement the to-move route with own-clinic scoping through the access adapter in `clinic-api/app/modules/scheduling/api/to_move.py` and include it in `clinic-api/app/modules/scheduling/router.py` (depends on T067, T007, T012)
- [ ] T069 [US6] Build the To move page (reception sees own clinic; manager has a clinic picker; refresh button) in `clinic-web/src/features/scheduling/pages/ToMovePage.tsx` (depends on T062, T015)
- [ ] T070 [US6] Register all five pages in the route table with role-based visibility (manager: all; reception: To move only; others: none) in `clinic-web/src/features/scheduling/routes.tsx` (depends on T017, T023, T030, T040, T063, T069)
- [ ] T071 [P] [US6] Write component tests for the To move page and role-based menu in `clinic-web/src/features/scheduling/__tests__/ToMovePage.test.tsx`

**Checkpoint**: All six stories work

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Checks that cut across stories

- [ ] T072 [P] Write a role-matrix test that calls every scheduling route as manager, receptionist of each clinic, dentist, patient and anonymous and asserts the allowed and refused results in `clinic-api/tests/scheduling/integration/test_role_matrix.py`
- [ ] T073 [P] Write a test that captures log output of the leave, to-move and slots routes and asserts no patient or dentist name and no phone number appears in `clinic-api/tests/scheduling/integration/test_no_pii_logs.py`
- [ ] T074 [P] Write the third-clinic-as-data test (add clinic, dentist, hours through the API only and see slots for it, with no code change) in `clinic-api/tests/scheduling/integration/test_third_clinic_as_data.py`
- [ ] T075 [P] Document the AppointmentsPort for the cmp-booking team (methods, status rules, index on dentist and time, registration at startup) in `clinic-api/docs/scheduling-appointments-port.md`
- [ ] T076 Reconcile `clinic-api/contracts/clinic-api-v1.openapi.yaml` with the implemented routes and run the full contract suite in `clinic-api/tests/scheduling/contract/` (depends on T022, T029, T037, T051, T060, T068)
- [ ] T077 Run the validation scenarios in `specs/003-clinic-schedule-setup/quickstart.md`, record the p95 result of the performance test and time how long it takes the practice manager to set one full week of hours with breaks (target under 3 minutes, SC-006) (depends on T052, T070, T072, T073, T074)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies
- **Foundational (Phase 2)**: depends on Setup; blocks all user stories
- **User Stories (Phases 3 to 8)**: depend on Foundational
  - US1, US2 and US3 are independent of each other (US3 reads the clinic and dentist tables created in Foundational; its test fixtures create the rows directly)
  - US4 needs hours and treatment rows (fixtures create them), so it can start after Foundational; the full flow is best checked after US1 to US3
  - US5 needs the slot queries (T047) only for its "slots exclude leave" scenario
  - US6 depends on US5 (T059, T062)
- **Polish (Phase 9)**: depends on all stories

### Within Each Story

- Tests first, and see them fail
- Schemas, then services, then routes, then web components and pages

### Parallel Opportunities

- T002 and T003; T006, T007, T008, T010, T013 to T017 in Phase 2
- After Phase 2, US1, US2, US3 and US4 can be built by different people at once
- Tests inside a story are all [P]
- Web components can be built in parallel with API work once the contract is fixed

---

## Parallel Example: User Story 4

```text
# Tests together:
Task: "Unit tests for the pure slot maths in clinic-api/tests/scheduling/unit/test_slot_math.py"
Task: "Unit tests for first available in clinic-api/tests/scheduling/unit/test_first_available.py"
Task: "Integration tests for slots in clinic-api/tests/scheduling/integration/test_slots.py"
Task: "Contract tests for the slots routes in clinic-api/tests/scheduling/contract/test_slots_contract.py"
```

---

## Implementation Strategy

### MVP First

1. Setup and Foundational
2. US1 to US4 (P1): clinics, treatments, hours and free slots; this unblocks the booking features
3. Validate against the quickstart scenarios 1 to 3 and 5
4. Add US5 and US6 (P2): leave and the to-move list, ready before go-live on 1 March 2027

### Incremental Delivery

1. Each story is tested on its own and adds value without breaking the earlier ones
2. The booking feature (cmp-booking) plugs its AppointmentsPort implementation in without changes to this module

---

## Notes

- Spec requirement ids (FR-001 to FR-024 in spec.md) are this feature's own; prd.md ids are in each `(source: ...)`
- cmp-booking, the slot picker screens (feature 004) and the reception day view (feature 006) are not built here
- The access context names in T007 follow feature 002; if they differ only `access.py` changes
