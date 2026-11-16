---

description: "Task list for Repeat no-show block and no-show report (Release 2)"
---

# Tasks: Repeat no-show block and no-show report (Release 2)

**Input**: Design documents from `/specs/009-noshow-block-report/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/noshow-block-report.openapi.yaml, quickstart.md

**Tests**: Included. The constitution requires tests first for business logic, so each story starts with tests that must fail before the code is written.

**Organization**: Tasks are grouped by user story so each can be built and tested on its own. Paths are relative to the two repositories: `clinic-api/` is brightsmile/clinic-api and `clinic-web/` is brightsmile/clinic-web.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story the task belongs to (US1, US2, US3)
- Exact file paths are in every description

## Path Conventions

- **Backend**: `clinic-api/app/modules/<component>/`, tests in `clinic-api/tests/`
- **Frontend**: `clinic-web/src/pages`, `clinic-web/src/components`, `clinic-web/src/services`, tests in `clinic-web/tests/`
- Paths follow plan.md and must be aligned with the scaffold of feature 001 and the files of features 004 to 006 (task T001)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm where existing code lives and create the two new modules and the flag

- [ ] T001 Find the existing "is blocked?" interface in clinic-api/app/modules/booking/block_port.py (from features 004 and 005), the status-change function in clinic-api/app/modules/booking/service.py, the release flag helper in clinic-api/app/flags.py and the web route file in clinic-web/src/routes.tsx, and record the real paths and names in specs/009-noshow-block-report/research.md under R-009
- [ ] T002 [P] Create empty module packages clinic-api/app/modules/noshow_policy/__init__.py and clinic-api/app/modules/reporting/__init__.py
- [ ] T003 [P] Register the Release 2 flag `r2_noshow_block_report` (default off) in clinic-api/app/flags.py and clinic-web/src/flags.ts

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The table and the no-show counting that the block and the report both rely on

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Create the Alembic migration clinic-api/migrations/versions/009a_no_show_block.py for table `no_show_block` with `id` uuid primary key, `patient_id` uuid not null, `blocked_at` timestamptz not null, `lifted_by` uuid null, `lifted_at` timestamptz null; check "`lifted_by` and `lifted_at` are both null or both set"; unique partial index on `patient_id` where `lifted_at` is null; index on `(patient_id, lifted_at)`
- [ ] T005 Create the Alembic migration clinic-api/migrations/versions/009b_no_show_count_index.py adding an index on the appointment table over `(patient_id, status, start_at)` for the count query (depends on T004)
- [ ] T006 [P] Create the `NoShowBlock` SQLAlchemy model in clinic-api/app/modules/noshow_policy/models.py matching T004 (depends on T004)
- [ ] T007 [P] Write failing unit tests for counting in clinic-api/tests/unit/test_no_show_stats.py: counts only status no-show; only start time within the last 6 months; only no-shows marked after the latest `lifted_at`; an undone no-show does not count; counted per person, so a family member's no-show is not counted for the account holder
- [ ] T008 Implement `count_no_shows(patient_id, now, marked_after)` in clinic-api/app/modules/booking/no_show_stats.py, using the time of the latest change to no-show from the appointment history (depends on T006, T007)

**Checkpoint**: Foundation ready - the table exists and no-shows can be counted per person

---

## Phase 3: User Story 1 - A patient with 2 no-shows in the last 6 months cannot book or reschedule online (Priority: P1) 🎯 MVP

**Goal**: A person with 2 counted no-shows is refused online booking and rescheduling with the clinic's phone number; existing bookings stay; counts are per person.

**Independent Test**: Record 2 no-shows within 6 months for one test person, then try to book and to reschedule online: both are refused with the clinic phone number, existing bookings remain and can be cancelled, the account holder is not blocked, and with the flag off nothing is refused. (source: FR-025, PD-007)

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T009 [P] [US1] Unit tests for the policy rules in clinic-api/tests/unit/test_noshow_policy_service.py: blocked at 2 and not at 1; 6-month ageing; per person; flag off returns not blocked; a no-show mark that reaches 2 opens a block row; a no-show mark that stays at 2 or more does not open a second row; an undo that leaves under 2 removes the open row without a lift record
- [ ] T010 [P] [US1] Contract tests in clinic-api/tests/contract/test_booking_eligibility.py for `GET /api/booking-eligibility` (200 with `blocked` and `clinic_phone`, 403 for a person outside the signed-in account, 404 with the flag off) and for the 403 body `ONLINE_BOOKING_BLOCKED` with `clinic_phone` on booking confirm and reschedule
- [ ] T011 [P] [US1] Integration tests in clinic-api/tests/integration/test_online_block.py: blocked person refused on confirm and on reschedule and no appointment is created or changed; a block that starts after the slot step is still refused on confirm; existing bookings still listed; online cancel still works; family member blocked but account holder not; reception booking for a blocked person is accepted; flag off behaves as before
- [ ] T012 [P] [US1] Component test for the notice in clinic-web/tests/BlockedNotice.test.tsx: shows "online booking is not available" and the clinic phone number, no confirm button

### Implementation for User Story 1

- [ ] T013 [P] [US1] Create eligibility and error schemas in clinic-api/app/modules/noshow_policy/schemas.py following contracts/noshow-block-report.openapi.yaml
- [ ] T014 [US1] Implement `is_blocked`, `on_no_show_marked` and `on_no_show_undone` in clinic-api/app/modules/noshow_policy/service.py: blocked when the count is 2 or more and the flag is on; open a row (or reset `blocked_at` of a stale open row) when a mark takes a person from under 2 to 2 or more; delete the open row on an undo that leaves under 2, with no lift record (depends on T006, T008, T009)
- [ ] T015 [US1] Add structured logs and counters for refusals and block starts in clinic-api/app/modules/noshow_policy/service.py, with person id, clinic id and correlation id only and no name, phone or birth year (depends on T014)
- [ ] T016 [US1] Wire the real policy behind the existing booking interface in clinic-api/app/modules/booking/block_port.py and clinic-api/app/main.py, keeping the interface signature unchanged (depends on T014)
- [ ] T017 [US1] Call `on_no_show_marked` and `on_no_show_undone` inside the status-change transaction in clinic-api/app/modules/booking/service.py (depends on T014)
- [ ] T018 [US1] Refuse blocked online booking confirm and online reschedule with HTTP 403 `ONLINE_BOOKING_BLOCKED` and the clinic phone from the clinic of the booking or of the appointment, checked inside the same transaction, and leave cancel and reception operations untouched, in clinic-api/app/modules/booking/router.py (depends on T016)
- [ ] T019 [US1] Add `GET /api/booking-eligibility` in clinic-api/app/modules/booking/router.py, allowing only persons in the signed-in patient's own account (depends on T013, T018)
- [ ] T020 [P] [US1] Create the BlockedNotice component in clinic-web/src/components/BlockedNotice.tsx
- [ ] T021 [US1] Show the notice in the slot step and handle a 403 `ONLINE_BOOKING_BLOCKED` on confirm in clinic-web/src/pages/booking/SlotPicker.tsx, hidden when the flag is off (depends on T019, T020)
- [ ] T022 [US1] Show the notice on the reschedule screen and handle the 403 on confirm in clinic-web/src/pages/booking/Reschedule.tsx (depends on T018, T020)

**Checkpoint**: User Story 1 works on its own: blocked persons cannot book or reschedule online, existing bookings stay

---

## Phase 4: User Story 2 - Reception sees a block and lifts it (Priority: P1)

**Goal**: A receptionist sees that a patient is blocked and can lift the block; lifting restarts the count from zero and records who and when.

**Independent Test**: Block a test patient, open the patient panel as a receptionist, see the banner, lift, confirm the patient can book online, the lift shows the receptionist and time, and one new no-show does not block but a second does. (source: FR-026)

Depends on User Story 1 for the policy service (T014).

### Tests for User Story 2 ⚠️

- [ ] T023 [P] [US2] Unit tests for lifting in clinic-api/tests/unit/test_noshow_lift.py: lift sets `lifted_by` and `lifted_at`; count restarts from zero; one new no-show does not block and a second does; lifting a patient who is not blocked is refused; two simultaneous lifts produce one lift record
- [ ] T024 [P] [US2] Contract tests in clinic-api/tests/contract/test_noshow_block_endpoints.py for `GET /api/patients/{patient_id}/no-show-block` and `POST /api/patients/{patient_id}/no-show-block/lift` (200, 403 for non-receptionists, 404 for unknown patient or flag off, 409 when not blocked)
- [ ] T025 [P] [US2] Integration tests in clinic-api/tests/integration/test_reception_block.py: a receptionist of either clinic can see and lift a block for a patient they find; the lift is recorded with their staff account; booking at the desk for a blocked patient works; undo of the no-show that created the block removes the block without a lift record
- [ ] T026 [P] [US2] Component test for the banner in clinic-web/tests/BlockBanner.test.tsx: shows "blocked online since <date>" and a Lift button only when blocked

### Implementation for User Story 2

- [ ] T027 [US2] Implement `get_block_state` and `lift` in clinic-api/app/modules/noshow_policy/service.py: read the open row with `SELECT ... FOR UPDATE`, set `lifted_by` and `lifted_at`, return 409 when there is no open effective block, and log the lift with receptionist id and person id only (depends on T014, T023)
- [ ] T028 [US2] Add the block state and lift endpoints in clinic-api/app/modules/reception/router.py, receptionist role only, 404 when the flag is off (depends on T027, T024)
- [ ] T029 [P] [US2] Create the API client in clinic-web/src/services/noshowBlock.ts for the state and lift operations
- [ ] T030 [P] [US2] Create the BlockBanner component with the Lift action in clinic-web/src/components/BlockBanner.tsx
- [ ] T031 [US2] Show the banner in the reception patient panel in clinic-web/src/pages/reception/PatientPanel.tsx, hidden when the flag is off (depends on T028, T029, T030)

**Checkpoint**: User Stories 1 and 2 both work: blocks can be seen and lifted

---

## Phase 5: User Story 3 - The practice manager reads the no-show report per clinic and month (Priority: P2)

**Goal**: The practice manager sees, per clinic and month for the last 12 months, the number of no-shows and the no-show rate, on screen only.

**Independent Test**: Seed appointments with a known mix, open the report as the practice manager and compare each clinic-month with hand counts; other roles are refused; no export exists. (source: FR-032)

Depends only on the Foundational phase (and on T016 for the shared `main.py`).

### Tests for User Story 3 ⚠️

- [ ] T032 [P] [US3] Unit tests for the monthly counts query in clinic-api/tests/unit/test_monthly_counts.py: cancelled by the patient and cancelled by the clinic left out of `not_cancelled`; walk-ins included; IST month boundaries; the current month is included; no patient columns are read
- [ ] T033 [P] [US3] Unit tests for the report service in clinic-api/tests/unit/test_report_service.py: 12 months per clinic with zero rows filled in; a clinic with no rows still appears (a third clinic added as data); `rate` is null when `not_cancelled` is 0; current month flagged `month_in_progress`
- [ ] T034 [P] [US3] Contract tests in clinic-api/tests/contract/test_noshow_report.py for `GET /api/reports/no-shows` (200 for the practice manager, 403 for receptionist, dentist and patient, 404 with the flag off) and that no export operation exists
- [ ] T035 [P] [US3] Integration test in clinic-api/tests/integration/test_report_anonymised.py: after a deletion on request anonymises a patient's appointment rows, every report figure is unchanged
- [ ] T036 [P] [US3] Component test for the report screen in clinic-web/tests/NoShowReport.test.tsx: one row per clinic and month, "month so far" label, "no appointments" when the rate is empty, and no export or download control

### Implementation for User Story 3

- [ ] T037 [US3] Implement `monthly_counts(months)` as one grouped query by clinic and IST calendar month in clinic-api/app/modules/booking/no_show_stats.py (depends on T008, T032)
- [ ] T038 [P] [US3] Create the report response schemas in clinic-api/app/modules/reporting/schemas.py following contracts/noshow-block-report.openapi.yaml
- [ ] T039 [US3] Implement the 12-month report in clinic-api/app/modules/reporting/service.py: read counts through cmp-booking, take the clinic list from cmp-scheduling, fill zeros, compute the rate as no-shows divided by not-cancelled appointments (depends on T033, T037, T038)
- [ ] T040 [US3] Add `GET /api/reports/no-shows` for the practice manager role only in clinic-api/app/modules/reporting/router.py and register it in clinic-api/app/main.py, with a log line carrying the user id and 404 when the flag is off (depends on T016, T039, T034)
- [ ] T041 [P] [US3] Create the API client in clinic-web/src/services/reports.ts
- [ ] T042 [US3] Create the report screen in clinic-web/src/pages/manager/NoShowReport.tsx: rows per clinic and month, count and percentage, "month so far" label, no export control (depends on T036, T041)
- [ ] T043 [US3] Add the report route and manager menu entry, hidden when the flag is off, in clinic-web/src/routes.tsx (depends on T042)

**Checkpoint**: All three stories work on their own

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Review, regression and clean-up across the stories

- [ ] T044 Security review of the authorisation changes (receptionist-only lift, manager-only report, patient limited to own account persons) recorded in specs/009-noshow-block-report/checklists/security-review.md
- [ ] T045 [P] Test that logs and metrics from the new code hold no name, phone or birth year in clinic-api/tests/unit/test_no_pii_in_logs.py
- [ ] T046 [P] Regression run of the existing online booking and reschedule tests from features 004 and 005 with the flag off, as clinic-api/tests/integration/test_flag_off_regression.py (SC-007)
- [ ] T047 Merge the operations of specs/009-noshow-block-report/contracts/noshow-block-report.openapi.yaml into clinic-api/contracts/clinic-api-v1.openapi.yaml
- [ ] T048 Add 24-month retention for `no_show_block` rows to the existing retention job in clinic-api/app/jobs/retention.py (depends on T004)
- [ ] T049 Check that the block check keeps booking confirmation inside the 800 ms server p95 budget (QA-002) with a timing test in clinic-api/tests/integration/test_block_check_timing.py (depends on T018)
- [ ] T050 Run the manual scenarios in specs/009-noshow-block-report/quickstart.md and note the result in specs/009-noshow-block-report/checklists/requirements.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup; blocks all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational
- **User Story 2 (Phase 4)**: Depends on Foundational and on the policy service from User Story 1 (T014)
- **User Story 3 (Phase 5)**: Depends on Foundational (T008) and on T016 for the shared `main.py`; otherwise independent of stories 1 and 2
- **Polish (Phase 6)**: Depends on the stories being complete

### Within Each User Story

- Tests are written first and must fail
- Models and schemas before services, services before endpoints, endpoints before web screens

### Parallel Opportunities

- T002 and T003 in Setup; T006 and T007 in Foundational
- All test tasks of a story (marked [P]) can run together
- After T014, User Story 2 backend and User Story 3 backend can proceed in parallel; the web pieces of each story are separate files

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit tests for the policy rules in clinic-api/tests/unit/test_noshow_policy_service.py"
Task: "Contract tests in clinic-api/tests/contract/test_booking_eligibility.py"
Task: "Integration tests in clinic-api/tests/integration/test_online_block.py"
Task: "Component test for the notice in clinic-web/tests/BlockedNotice.test.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2
2. Complete Phase 3 (User Story 1)
3. Stop and validate: blocked persons are refused, existing bookings stay
4. Do not switch the flag on for patients before User Story 2 is done, because a block without a lift cannot be undone by reception

### Incremental Delivery

1. Setup and Foundational
2. User Story 1, then User Story 2 (ship together behind the flag)
3. User Story 3 (report), which can be released before or after the block
4. Polish, then switch the flag on once the data is ready (due 2027-03-19)

### Parallel Team Strategy

1. One developer does Setup and Foundational
2. Then developer A takes User Story 1, then 2; developer B takes User Story 3 backend and web

---

## Notes

- The P marker: tasks = different files, no dependencies
- Open questions Q1 to Q3 have assumed answers in clarifications.md; tasks T014, T027 and T037 follow them
- Commit after each task or logical group
