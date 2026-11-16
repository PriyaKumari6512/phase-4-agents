---

description: "Task list for feature 002: dentist schedules, treatments and free slots"
---

# Tasks: Dentist schedules, treatments and free slots

**Input**: Design documents from `/specs/002-schedules-slots/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included. The constitution requires tests first for business logic; each test task comes before the implementation it covers and must fail first.

**Organization**: Tasks are grouped by user story. Every task names its repository: `clinic-api` (brightsmile/clinic-api, paths relative to its root) or `clinic-web` (brightsmile/clinic-web, paths relative to its root).

**Requirement ids**: US1 = FR-009; US2 = FR-007, NFR-003; US3 = FR-010, NFR-003, NFR-002; US4 = FR-008.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story the task belongs to
- A task that needs another task that is not directly before it ends with `(depends on T00X)`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Package skeletons in both repositories

- [ ] T001 [P] Create the scheduling package skeleton in repo clinic-api: `app/scheduling/__init__.py`, subfolders `models/`, `schemas/`, `services/`, `routers/`, `jobs/`, and `app/scheduling/settings.py` with `booking_horizon_days` (default 30, from application configuration) and `max_range_days` (31)
- [ ] T002 [P] Create the scheduling feature skeleton in repo clinic-web: `src/features/scheduling/api/`, `src/features/scheduling/__tests__/`, `src/features/scheduling/time.ts` (format and parse India time, convert to and from UTC instants) and an empty `src/features/scheduling/routes.tsx`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Tables, the appointment read port, authorisation and logging that every story needs

**CRITICAL**: No user story work can begin until this phase is complete. Requires feature 001 (clinic and dentist tables, RBAC, staff accounts) to be merged.

- [ ] T003 [P] Create the `TreatmentType` SQLAlchemy model in repo clinic-api at `app/scheduling/models/treatment_type.py` (fields per data-model.md: name 1 to 80 characters, unique on `lower(name)`; duration_minutes one of 30, 60, 90; online_bookable; active)
- [ ] T004 [P] Create the `WorkingHours` and `WorkingHoursBreak` models in repo clinic-api at `app/scheduling/models/working_hours.py` (weekday 1 to 7, IST `time` values, end greater than start, unique `(dentist_id, clinic_id, weekday)`, breaks cascade on delete)
- [ ] T005 [P] Create the `Leave` model in repo clinic-api at `app/scheduling/models/leave.py` (UTC `timestamptz` start_at and end_at, end greater than start, whole_day, note up to 200 characters, created_by)
- [ ] T006 Write the Alembic migration in repo clinic-api at `alembic/versions/<rev>_scheduling.py`: tables for T003 to T005, `btree_gist` exclusion constraint on `(dentist_id, tstzrange(start_at, end_at))` for leave, indexes `(clinic_id, weekday)`, `(dentist_id, weekday)` and `(dentist_id, start_at, end_at)`, and the seed of the five treatment types (depends on T003, T004, T005)
- [ ] T007 [P] Define the `AppointmentReader` protocol, `AppointmentBrief` dataclass, `register_appointment_reader` and a default reader that returns no appointments in repo clinic-api at `app/scheduling/ports.py`, and a `FakeAppointmentReader` for tests in `tests/scheduling/fakes.py`
- [ ] T008 [P] Build the authorisation dependencies in repo clinic-api at `app/scheduling/dependencies.py`: `require_manager`, `require_staff_or_patient` and `require_clinic_access(clinic_id)` (receptionist limited to own clinic, patient limited to online types) on top of the cmp-identity RBAC from feature 001
- [ ] T009 [P] Add the structured-logging helper (ids only, never patient name, phone or birth year) and the OpenTelemetry timer `scheduling_slots_seconds` in repo clinic-api at `app/scheduling/observability.py`
- [ ] T010 Register the scheduling routers package in repo clinic-api at `app/scheduling/routers/__init__.py` and include it in the main application file `app/main.py` (depends on T008)

**Checkpoint**: Foundation ready; user stories can start.

---

## Phase 3: User Story 1 - Manage treatment types (Priority: P1) MVP

**Goal**: The practice manager keeps the list of treatment types (duration, online flag, active); patients see only active online types.

**Independent Test**: As manager add a 60-minute reception-only type, change a duration, switch a type off; read the list as manager, receptionist and patient and see the right set for each.

### Tests for User Story 1

- [ ] T011 [P] [US1] Unit tests for treatment rules (duration only 30, 60 or 90; duplicate name ignoring capitals refused; switch off keeps the row) in repo clinic-api at `tests/scheduling/unit/test_treatment_rules.py`
- [ ] T012 [P] [US1] API tests for `GET/POST /treatment-types` and `PATCH /treatment-types/{id}` (seed list, 201, 409, 422, 403 for non-manager, patient sees only active online types, receptionist sees all active) in repo clinic-api at `tests/scheduling/api/test_treatment_types.py`

### Implementation for User Story 1

- [ ] T013 [P] [US1] Create the treatment Pydantic schemas (`TreatmentType`, `TreatmentTypeInput`, `TreatmentTypePatch` with name 1 to 80 characters and duration enum 30, 60, 90) in repo clinic-api at `app/scheduling/schemas/treatments.py`
- [ ] T014 [US1] Implement the treatment service (list by role, create, edit, switch off, `get_treatment_type`) in repo clinic-api at `app/scheduling/services/treatments.py` (depends on T006, T013)
- [ ] T015 [US1] Implement the treatment endpoints per `contracts/scheduling-api.openapi.yaml` in repo clinic-api at `app/scheduling/routers/treatments.py`
- [ ] T016 [P] [US1] Create the typed client for the treatment endpoints in repo clinic-web at `src/features/scheduling/api/treatments.ts`
- [ ] T017 [US1] Build the treatments screen (table with name, minutes, online flag, active; add and edit form; error messages for duplicate name and bad duration) and register its route in repo clinic-web at `src/features/scheduling/TreatmentsPage.tsx` and `src/features/scheduling/routes.tsx` (depends on T016)
- [ ] T018 [US1] Component test for the treatments screen (list, add, edit, switch off, error shown) in repo clinic-web at `src/features/scheduling/__tests__/TreatmentsPage.test.tsx`

**Checkpoint**: User Story 1 works on its own.

---

## Phase 4: User Story 2 - Set weekly working hours and breaks (Priority: P1)

**Goal**: The practice manager sets, per dentist and clinic, the weekly hours and breaks; a third clinic or dentist is data only.

**Independent Test**: Set Monday 09:00-17:00 with a break 13:00-14:00 at one clinic, read it back; an overlapping Monday at another clinic is refused.

### Tests for User Story 2

- [ ] T019 [P] [US2] Unit tests for hours validation (end after start, break inside the day, breaks not overlapping, no overlap with the same dentist's hours at another clinic on a weekday) in repo clinic-api at `tests/scheduling/unit/test_hours_validation.py`
- [ ] T020 [P] [US2] API tests for `GET /dentists/{id}/working-hours` and `PUT /dentists/{id}/clinics/{clinic}/working-hours` (save, reload, replace, remove a weekday, 409 cross-clinic overlap, 422, 403 for non-manager) in repo clinic-api at `tests/scheduling/api/test_working_hours.py`
- [ ] T021 [P] [US2] API test that hours can be set for a clinic and a dentist created at run time through feature 001's services, with no code or configuration change (NFR-003, QA-011) in repo clinic-api at `tests/scheduling/api/test_third_clinic_hours.py`

### Implementation for User Story 2

- [ ] T022 [P] [US2] Create the hours Pydantic schemas (`WorkingHoursInput`, `WorkingHours`, `TimeRange`, "HH:MM" pattern) in repo clinic-api at `app/scheduling/schemas/hours.py`
- [ ] T023 [US2] Implement the hours service (replace the set for one dentist and clinic in one transaction, validation rules, cross-clinic overlap check, list) in repo clinic-api at `app/scheduling/services/hours.py` (depends on T006, T022)
- [ ] T024 [US2] Implement the hours endpoints in repo clinic-api at `app/scheduling/routers/hours.py` (depends on T023)
- [ ] T025 [P] [US2] Create the typed client for the hours endpoints in repo clinic-web at `src/features/scheduling/api/hours.ts`
- [ ] T026 [US2] Build the "dentists and hours" screen (choose dentist and clinic, one row per weekday with start, end and breaks, validation messages, clinic list from data so a third clinic appears without code change) and register its route in repo clinic-web at `src/features/scheduling/DentistHoursPage.tsx` and `src/features/scheduling/routes.tsx` (depends on T025)
- [ ] T027 [US2] Component test for the hours screen (set, edit, remove a weekday, overlap error) in repo clinic-web at `src/features/scheduling/__tests__/DentistHoursPage.test.tsx`

**Checkpoint**: Hours can be set and read back.

---

## Phase 5: User Story 3 - Find free slots and first available (Priority: P1)

**Goal**: Live free-slot lists for one clinic and one date range, "first available" (10 earliest), and the interface booking uses; fast at 3 clinics, 10 dentists and 100 concurrent users.

**Independent Test**: With hours 09:00-17:00, break 13:00-14:00 and a booking at 10:00-10:30 (fake reader) a 30-minute type shows 09:00, 09:30, 10:30 and so on, and nothing in the break; a 90-minute type's last slot is 15:30.

### Tests for User Story 3

- [ ] T028 [P] [US3] Unit tests for the slot engine (30, 60 and 90-minute fits, break, leave, booked appointments, half-open edges, start on :00/:30 with hours such as 09:15, other-clinic bookings and leave block, empty days) in repo clinic-api at `tests/scheduling/unit/test_slot_engine.py`
- [ ] T029 [P] [US3] API tests for `GET /clinics/{id}/slots` and `/slots/first-available` (online-only for patients, horizon clip 1 March to 31 March, past dropped, range over 31 days gives 422, receptionist of another clinic gives 403, freed slot offered at once, 10 slots in time order with dentist) in repo clinic-api at `tests/scheduling/api/test_slots.py`
- [ ] T030 [P] [US3] API test that a clinic and a dentist added as data (third clinic, seventh dentist) offer slots with no code change (NFR-003, QA-011) in repo clinic-api at `tests/scheduling/api/test_third_clinic_slots.py`

### Implementation for User Story 3

- [ ] T031 [P] [US3] Create the slot Pydantic schemas (`FreeSlot` and query parameters) in repo clinic-api at `app/scheduling/schemas/slots.py`
- [ ] T032 [US3] Implement the pure slot engine (per dentist and IST date: working window minus breaks, leave and booked intervals, half-hour grid, duration fit) in repo clinic-api at `app/scheduling/services/slot_engine.py` (depends on T028)
- [ ] T033 [US3] Implement the slot service in repo clinic-api at `app/scheduling/services/slots.py`: one query for hours, one for leave, one `AppointmentReader` call per request, patient horizon and online-type rules, `find_free_slots`, `first_available`, `is_slot_free` (with `exclude_appointment_id`), as in `contracts/internal-interfaces.md` (depends on T007, T014, T023, T032)
- [ ] T034 [US3] Implement the slot endpoints with the timing metric and ids-only logging in repo clinic-api at `app/scheduling/routers/slots.py` (depends on T009, T033)
- [ ] T035 [US3] Write the load test and its seed (3 clinics, 10 dentists, 1,000 fake appointments a week, 100 concurrent users; report p95 per endpoint; check with `EXPLAIN` that hours and leave queries use their indexes) in repo clinic-api at `tests/scheduling/load/slots_load.py` and `tests/scheduling/load/seed.py` (depends on T034)

**Checkpoint**: Slots and first available work; booking can start against the interface.

---

## Phase 6: User Story 4 - Record dentist leave and list appointments to move (Priority: P2)

**Goal**: The manager records and edits leave; slots stop in that time; booked appointments in it are listed for reception, never moved by the system.

**Independent Test**: Book an appointment (fake reader) at Thursday 15:00, record leave 14:00-17:00: the appointment is listed and unchanged, no slot is offered in the leave; delete the leave and the slots return.

Depends on User Story 3 for the slot behaviour and on User Story 2 for hours.

### Tests for User Story 4

- [ ] T036 [P] [US4] Unit tests for leave rules (end after start, whole-day IST to UTC conversion, part-day, overlap with the same dentist's leave refused) in repo clinic-api at `tests/scheduling/unit/test_leave_rules.py`
- [ ] T037 [P] [US4] API tests for leave create, list, change, delete (201 with the to-move list, 409 overlap, 422, 403 for non-manager, slots follow the change) in repo clinic-api at `tests/scheduling/api/test_leave.py`
- [ ] T038 [P] [US4] API tests for `GET /leave/{id}/appointments-to-move` (patient, phone, clinic, treatment, time listed; appointments stay booked; a moved or cancelled one disappears; receptionist sees own clinic only; manager sees all; leave after booking only lists) in repo clinic-api at `tests/scheduling/api/test_appointments_to_move.py`
- [ ] T039 [P] [US4] Unit test for the 24-month leave retention job (older than 24 months after end deleted, newer kept) in repo clinic-api at `tests/scheduling/unit/test_leave_retention.py`

### Implementation for User Story 4

- [ ] T040 [P] [US4] Create the leave Pydantic schemas (`LeaveInput`, `Leave`, `AppointmentToMove`, `LeaveWithConflicts`) in repo clinic-api at `app/scheduling/schemas/leave.py`
- [ ] T041 [US4] Implement the leave service (create, change, delete, list; whole days converted from IST dates; overlap refusal; to-move list read through `AppointmentReader` and filtered by clinic for receptionists) in repo clinic-api at `app/scheduling/services/leave.py` (depends on T006, T007, T040)
- [ ] T042 [US4] Implement the leave endpoints in repo clinic-api at `app/scheduling/routers/leave.py` (depends on T041)
- [ ] T043 [US4] Implement the daily leave retention job in repo clinic-api at `app/scheduling/jobs/leave_retention.py` and register it in the scheduled-jobs registry started with the app in `app/main.py` (depends on T039, T010)
- [ ] T044 [P] [US4] Create the typed client for the leave endpoints in repo clinic-web at `src/features/scheduling/api/leave.ts`
- [ ] T045 [US4] Build the leave screen (choose dentist, whole days or part day in India time, leave list with edit and delete, and the table of appointments to move with patient, phone, clinic, treatment and time) and register its route in repo clinic-web at `src/features/scheduling/LeavePage.tsx` and `src/features/scheduling/routes.tsx` (depends on T044)
- [ ] T046 [US4] Component test for the leave screen (whole day, part day, appointments to move shown, overlap error) in repo clinic-web at `src/features/scheduling/__tests__/LeavePage.test.tsx`

**Checkpoint**: All four user stories work.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Contract, security, privacy and end-to-end checks

- [ ] T047 [P] Contract tests of every scheduling endpoint against `specs/002-schedules-slots/contracts/scheduling-api.openapi.yaml` in repo clinic-api at `tests/scheduling/contract/test_openapi_contract.py` (depends on T015, T024, T034, T042)
- [ ] T048 [P] Merge the scheduling paths and schemas into the shared API contract in repo clinic-api at `contracts/clinic-api-v1.openapi.yaml` (depends on T047)
- [ ] T049 [P] Role matrix test (patient, receptionist of own and other clinic, dentist, manager against every endpoint) in repo clinic-api at `tests/scheduling/api/test_rbac_matrix.py` (depends on T015, T024, T034, T042)
- [ ] T050 [P] Log scan test: run the API tests with a test patient and assert that no log line holds the patient's name or phone number in repo clinic-api at `tests/scheduling/api/test_no_pii_in_logs.py` (depends on T042)
- [ ] T051 Run the quickstart scenarios in `specs/002-schedules-slots/quickstart.md` against staging data and record the load test p95 in `specs/002-schedules-slots/quickstart.md` (depends on T035, T046, T047)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none.
- **Foundational (Phase 2)**: after Setup and after feature 001 is merged; blocks all user stories.
- **User Story 1 (P1)**: after Foundational; no other story.
- **User Story 2 (P1)**: after Foundational; independent of US1.
- **User Story 3 (P1)**: after Foundational, US1 (treatment duration, T014) and US2 (hours, T023).
- **User Story 4 (P2)**: after Foundational and US3 (slots must follow leave).
- **Polish**: after all stories.
- **Other features**: feature 003 uses `find_free_slots`, `first_available` and `is_slot_free` and provides the `AppointmentReader` implementation; feature 005 shows the "to move" list to reception.

### Within Each Story

Tests first (must fail), then schemas, services, endpoints, then web client and screen.

### Parallel Opportunities

- T001 and T002; T003, T004, T005; T007, T008, T009.
- US1 and US2 can run in parallel by two developers (backend and web within each too).
- Test tasks of one story are parallel.

## Parallel Example: User Story 2

```bash
Task: "Unit tests for hours validation in tests/scheduling/unit/test_hours_validation.py"
Task: "API tests for working hours in tests/scheduling/api/test_working_hours.py"
Task: "Hours Pydantic schemas in app/scheduling/schemas/hours.py"
```

## Implementation Strategy

### MVP First

1. Setup, Foundational.
2. US1 and US2 (treatments and hours), then US3 (slots): booking (feature 003) can start once T034 is merged.
3. US4 (leave) before go-live; validate each story with its Independent Test.

### Incremental Delivery

1. Foundation, then US1 (demo treatments screen).
2. US2 (demo hours screen), US3 (demo slots through the API and the load test).
3. US4 (demo leave and the "to move" list with the fake reader, then with the real reader when 003/005 land).

## Notes

Tasks marked P are in different files with no dependencies.
- Appointments are owned by cmp-booking; this feature never writes them.
- No patient name, phone number or birth year in logs.
