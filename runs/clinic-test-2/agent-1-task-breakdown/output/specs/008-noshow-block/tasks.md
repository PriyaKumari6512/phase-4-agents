# Tasks: Repeat no-show block

**Input**: Design documents from `/specs/008-noshow-block/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/noshow-block.openapi.yaml, quickstart.md
**Source requirements**: FR-025, FR-026 (PRD); PD-007
**Tests**: included (constitution principle I: business logic is tested with the code).
**Repos**: `API` = brightsmile/clinic-api, `WEB` = brightsmile/clinic-web. Every task names its repo and exact path. Paths for files owned by features 003, 004 and 005 are to be confirmed against their merged code.

## Format: `- [ ] T### [P?] [US?] Description with file path (repo)`

- **[P]**: can run in parallel (different files, no unfinished dependency)
- **[US#]**: user story from spec.md

## Phase 1: Setup

**Purpose**: the Release 2 feature switch on both sides.

- [ ] T001 [P] Add setting `noshow_block_enabled` (boolean, default false) in app/config.py and return it in the existing signed-in user/config response schema in app/identity/schemas.py (repo: brightsmile/clinic-api; source: FR-025, FR-026)
- [ ] T002 [P] Read the flag from the API response and expose a `useNoShowBlockEnabled` hook in src/features/noshow-block/useNoShowBlockEnabled.ts (repo: brightsmile/clinic-web; source: FR-025, FR-026)

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: the block table and the count / block rules every story uses.

**CRITICAL**: no user story work can start until this phase is complete.

- [ ] T003 Create SQLAlchemy model `NoShowBlock` in app/noshow_policy/models.py with fields id (uuid primary key), patient_id (reference to ent-patient, a person, not the account), blocked_at (timestamp with time zone, UTC, not null), lifted_at (timestamp with time zone, null means open), lifted_by_staff_id (reference to ent-staff-account, null on a system close) (repo: brightsmile/clinic-api; source: FR-025, FR-026, PD-007)
- [ ] T004 Create Alembic migration for table `no_show_block` in alembic/versions/20261113_no_show_block.py with partial unique index on patient_id where lifted_at is null (at most one open block per patient) and index on (patient_id, lifted_at); forward-only, compatible with the previous release (repo: brightsmile/clinic-api) (depends on T003)
- [ ] T005 Implement repository functions in app/noshow_policy/repository.py: count_no_shows(person_id, now) over appointments with status no-show, start >= now minus 6 months, and latest change to no-show in the appointment history after the person's last reception lift; get_open_block; create_block; close_block; latest_reception_lift; reads appointments only through the cmp-booking read interface (repo: brightsmile/clinic-api) (depends on T003)
- [ ] T006 [P] Write unit tests first for the rules in tests/noshow_policy/test_service.py: 1 no-show not blocked; 2 blocked; one of 2 older than 6 months not blocked; family member counted separately from the account holder; 3 no-shows give one open block; count after a reception lift starts at zero; a system close does not reset the count; switch off means never blocked (repo: brightsmile/clinic-api)
- [ ] T007 Implement service in app/noshow_policy/service.py with public interface exported from app/noshow_policy/__init__.py: recalculate(person_id) (create block at count >= 2 and none open; system-close when count < 2), is_blocked(person_id) (open block AND count >= 2, false when the switch is off), block_state(person_id) returning blocked, blocked_at and counted no-show dates (repo: brightsmile/clinic-api) (depends on T005, T006)

**Checkpoint**: block rules available in-process; user stories can start.

---

## Phase 3: User Story 1 - A repeat no-show patient cannot book or reschedule online (Priority: P1)

**Goal**: a blocked person is refused online booking and rescheduling with the clinic phone number; existing bookings stay; reception is not blocked. (source: FR-025, PD-007)

**Independent Test**: two no-shows for one person (recalculate called directly); online book and reschedule are refused with the phone; the account holder can book; the receptionist can still book that person.

- [ ] T008 [P] [US1] Write integration tests in tests/noshow_policy/test_booking_block.py: blocked person refused at slot choice and at final confirm; reschedule refused and appointment unchanged; other upcoming appointments stay booked and cancellable; family member blocked but account holder can book; reception book and reschedule succeed; unblocked person succeeds (repo: brightsmile/clinic-api)
- [ ] T009 [US1] Replace the always-allow hook with `noshow_policy.is_blocked` on online book and the final confirm in app/booking/online.py, returning HTTP 403 `{code: ONLINE_BOOKING_BLOCKED, clinic_phone}` with the phone of the booking's clinic; reception paths are not changed (repo: brightsmile/clinic-api) (depends on T007)
- [ ] T010 [US1] Replace the always-allow hook with `noshow_policy.is_blocked` on online reschedule in app/booking/reschedule.py, same 403 body with the appointment's clinic phone, appointment left unchanged (repo: brightsmile/clinic-api) (depends on T007)
- [ ] T011 [US1] Add schemas in app/noshow_policy/schemas.py and read-only `GET /api/booking-eligibility` (patient_id, clinic_id) in app/noshow_policy/router.py, patient role only and only for persons of the caller's own account; register the router in app/main.py (repo: brightsmile/clinic-api) (depends on T007)
- [ ] T012 [P] [US1] Write contract test for `/api/booking-eligibility` and the 403 body against specs/008-noshow-block/contracts/noshow-block.openapi.yaml in tests/noshow_policy/test_eligibility_contract.py (repo: brightsmile/clinic-api) (depends on T011)
- [ ] T013 [P] [US1] Create `BlockedNotice` component (online booking not available, clinic phone as a tap-to-call link, 44 px tap target, no sideways scrolling) with component test in src/features/noshow-block/BlockedNotice.tsx and src/features/noshow-block/BlockedNotice.test.tsx (repo: brightsmile/clinic-web)
- [ ] T014 [US1] Call the eligibility endpoint on entering the slot picker and show `BlockedNotice` instead of slots when blocked; also handle a 403 `ONLINE_BOOKING_BLOCKED` at confirm, in src/pages/patient/SlotPicker.tsx, hidden when the flag is off (repo: brightsmile/clinic-web) (depends on T011, T013, T002)
- [ ] T015 [US1] Handle the blocked refusal on the reschedule slot picker in src/pages/patient/Reschedule.tsx with `BlockedNotice`, keeping the appointment shown unchanged (repo: brightsmile/clinic-web) (depends on T013, T002)
- [ ] T016 [P] [US1] Write web tests for the blocked flows (slot picker, confirm refusal, reschedule, family member, flag off shows nothing) in src/pages/patient/__tests__/blocked.test.tsx (repo: brightsmile/clinic-web) (depends on T014, T015)

**Checkpoint**: US1 works and is demonstrable on its own.

---

## Phase 4: User Story 2 - Reception sees who is blocked (Priority: P2)

**Goal**: reception sees a blocked marker in the day view and patient search, and block details in the appointment panel. (source: FR-026, PD-007)

**Independent Test**: block a person; the day view, panel and search show the marker for that person only.

- [ ] T017 [P] [US2] Write API tests in tests/noshow_policy/test_reception_view.py: `no_show_blocked` on day-view items and search results; block-state endpoint returns blocked_at and counted no-show dates; family member marked, account holder not; receptionist only; flag off shows false (repo: brightsmile/clinic-api)
- [ ] T018 [US2] Add `GET /api/reception/patients/{patient_id}/no-show-block` returning block state in app/noshow_policy/router.py, receptionist only (repo: brightsmile/clinic-api) (depends on T011)
- [ ] T019 [US2] Add `no_show_blocked` to day-view appointment items in app/reception/day_view.py using one batched lookup per day (no query per appointment) (repo: brightsmile/clinic-api) (depends on T007)
- [ ] T020 [US2] Add `no_show_blocked` to patient search results in app/reception/patient_search.py (repo: brightsmile/clinic-api) (depends on T007)
- [ ] T021 [P] [US2] Create `BlockedBadge` component ("Blocked from online booking") with test in src/features/noshow-block/BlockedBadge.tsx and src/features/noshow-block/BlockedBadge.test.tsx (repo: brightsmile/clinic-web)
- [ ] T022 [US2] Show `BlockedBadge` on day-view appointments and patient-search results in src/pages/reception/DayView.tsx and src/pages/reception/PatientSearch.tsx, hidden when the flag is off (repo: brightsmile/clinic-web) (depends on T019, T020, T021, T002)
- [ ] T023 [US2] Show block start date and counted no-show dates in the appointment panel in src/pages/reception/AppointmentPanel.tsx using the block-state endpoint (repo: brightsmile/clinic-web) (depends on T018, T021)

**Checkpoint**: US1 and US2 both work.

---

## Phase 5: User Story 3 - Reception lifts a block and the count restarts (Priority: P2)

**Goal**: a receptionist lifts a current block; it is recorded with who and when; the count restarts from zero. (source: FR-026)

**Independent Test**: block, lift, book online at once, then 1 new no-show is not blocked and a second one blocks again.

- [ ] T024 [P] [US3] Write tests in tests/noshow_policy/test_lift.py: lift records staff id and time; online booking succeeds at once; old no-shows never count again; 1 new no-show not blocked, 2 blocked; lift when not blocked gives 409; non-receptionist gets 403; two simultaneous lifts record one (repo: brightsmile/clinic-api)
- [ ] T025 [US3] Implement `lift(person_id, staff_id)` in app/noshow_policy/service.py as one conditional update where lifted_at is null, setting lifted_at and lifted_by_staff_id; raise "not blocked" when nothing updated (repo: brightsmile/clinic-api) (depends on T007)
- [ ] T026 [US3] Add `POST /api/reception/patients/{patient_id}/no-show-block/lift` in app/noshow_policy/router.py, receptionist only, 409 when not blocked, returns block state (repo: brightsmile/clinic-api) (depends on T018, T025)
- [ ] T027 [P] [US3] Create `LiftBlockDialog` (confirm, then call lift, show result and error when already lifted) with test in src/features/noshow-block/LiftBlockDialog.tsx and src/features/noshow-block/LiftBlockDialog.test.tsx (repo: brightsmile/clinic-web)
- [ ] T028 [US3] Offer "Lift block" with `LiftBlockDialog` in the appointment panel and patient search in src/pages/reception/AppointmentPanel.tsx and src/pages/reception/PatientSearch.tsx, only for blocked patients and when the flag is on (repo: brightsmile/clinic-web) (depends on T023, T026, T027)

**Checkpoint**: US1, US2 and US3 work.

---

## Phase 6: User Story 4 - The block follows no-show corrections (Priority: P2)

**Goal**: marking or undoing a no-show recalculates the person's block at once. (source: FR-025, FR-026, PD-007)

**Independent Test**: second no-show blocks at once; undo the same day unblocks; only the person the appointment was for is recounted.

- [ ] T029 [P] [US4] Write tests in tests/noshow_policy/test_status_events.py: marking the second no-show blocks in the same transaction; undo of it unblocks and the system-close does not reset the count; undo after a lift leaves count zero; a family member's mark does not change the account holder's state; a failed recalculation rolls back the status change (repo: brightsmile/clinic-api)
- [ ] T030 [US4] Call `noshow_policy.recalculate(person_id)` inside the transaction of no-show marking and of no-show undo in app/reception/status.py, for the appointment's person only (repo: brightsmile/clinic-api) (depends on T007)
- [ ] T031 [US4] Make recalculate safe under concurrent calls in app/noshow_policy/service.py: on a unique-index conflict for the open block, reload and continue instead of failing (repo: brightsmile/clinic-api) (depends on T030)

**Checkpoint**: all four stories work.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T032 [P] Add structured logs, counters (blocks created, lifts, refused bookings) and trace spans in app/noshow_policy/service.py and app/noshow_policy/router.py; ids only, no names, phones or birth years (repo: brightsmile/clinic-api; constitution II, DoD)
- [ ] T033 [P] Write log test proving no patient name, phone or birth year is logged when checking, creating or lifting a block in tests/noshow_policy/test_logging.py (repo: brightsmile/clinic-api) (depends on T032)
- [ ] T034 [P] Write authorisation tests in tests/noshow_policy/test_authz.py: a patient cannot check another account's person; dentist and patient cannot read or lift reception block state (repo: brightsmile/clinic-api) (depends on T026)
- [ ] T035 [P] Merge the operations and schemas of specs/008-noshow-block/contracts/noshow-block.openapi.yaml into contracts/clinic-api-v1.openapi.yaml (repo: brightsmile/clinic-api) (depends on T026)
- [ ] T036 [P] Include table `no_show_block` in the 24-month retention job and in erasure on request in app/retention/jobs.py and app/identity/erasure.py (repo: brightsmile/clinic-api) (depends on T004)
- [ ] T037 Run every scenario of specs/008-noshow-block/quickstart.md in staging with the flag on and off, and record the result in the pull request (repos: brightsmile/clinic-api and brightsmile/clinic-web) (depends on T016, T028, T031, T035)

---

## Dependencies & Execution Order

- Phase 1 has no dependency; Phase 2 follows and blocks all stories.
- US1 (P1) starts after Phase 2. US2 needs the eligibility router from US1 (T011). US3 needs US2's block-state endpoint and panel (T018, T023). US4 needs only Phase 2 and can run in parallel with US2 and US3.
- Tests are written first inside each story (T008, T017, T024, T029) and must fail before the implementation.
- Release order: US1 and US4 together are the minimum that makes the block correct; US2 and US3 give reception the view and the lift.

### Parallel Opportunities

- T001 with T002; T006 with T005.
- In US1: T008, T013 in parallel; API tasks (T009, T010, T011) and web task T013 are separate repos and can proceed together.
- In US2: T017 and T021 in parallel; T019 with T020.
- US4 (T029 to T031) in parallel with US2 and US3.
- Polish tasks T032 to T036 in parallel.

## Implementation Strategy

1. Setup and Foundational (T001 to T007).
2. MVP: US1, with US4 wiring so no-shows create blocks for real (T008 to T016, T029 to T031). Validate with quickstart scenarios 1, 2, 4 and 7.
3. US2 then US3 for reception (T017 to T028). Validate scenarios 3, 5 and 6.
4. Polish and the staging run (T032 to T037); switch on at release R2 (DL-2 2027-03-19, not hard).
