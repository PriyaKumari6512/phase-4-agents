---

description: "Task list for Reception day view, check-in, no-show and dentist day"
---

# Tasks: Reception day view, check-in, no-show and dentist day

**Input**: Design documents from `/specs/006-reception-dentist-day/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/reception-dentist-day.openapi.yaml, quickstart.md

**Tests**: Included. The constitution (principle I) requires tests before or with the implementation, so each story starts with its tests, which must fail before the implementation.

**Organization**: Tasks are grouped by user story so each can be implemented and tested independently.

## Format: `- [ ] T### [P?] [Story] Description with file path`

- **[P]**: Can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: Which user story the task belongs to (US1–US7)
- Paths starting `app/`, `alembic/`, `tests/`, `contracts/`, `docs/` are in the repository brightsmile/clinic-api; paths starting `src/` and `tests/reception/`, `tests/dentist/` are in brightsmile/clinic-web.

## Path Conventions

- **clinic-api**: `app/modules/<component>/`, `tests/unit|integration|contract|performance/`
- **clinic-web**: `src/features/reception/`, `src/features/dentist/`, `src/routes/`, `tests/reception/`, `tests/dentist/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project skeleton for this feature

- [ ] T001 Create the reception package with `app/modules/reception/__init__.py` and `app/modules/reception/router.py` (an aggregating router, no routes yet) and register it under `/api` in `app/main.py`
- [ ] T002 [P] Create the web feature folders with `src/features/reception/index.ts` and `src/features/dentist/index.ts` (empty exports) in brightsmile/clinic-web
- [ ] T003 [P] Merge the paths and schemas of `specs/006-reception-dentist-day/contracts/reception-dentist-day.openapi.yaml` into `contracts/clinic-api-v1.openapi.yaml` in brightsmile/clinic-api

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Clinic scoping, status rules and the status-change service that every story uses

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 [P] Write role and scoping tests in `tests/integration/reception/test_scoping.py`: receptionist of clinic A gets 404 for a clinic B appointment id, dentist and patient accounts get 403 on reception routes, a deactivated receptionist is refused on the next request, clinic is never read from the request
- [ ] T005 [P] Write unit tests for the status rules in `tests/unit/reception/test_status_rules.py`: arrived only when status booked and date is today IST; no-show only when booked and `now >= start + 15 minutes` and before midnight IST after start (test 14:59 vs 15:00, and 23:59 vs 00:00); undo only when no-show and same IST date; reschedule and cancel only from booked; `allowed_actions` list
- [ ] T006 Implement the receptionist clinic scope and dentist own-day scope in `app/modules/identity/access.py` (dependencies `require_receptionist` returning the clinic id from the staff account, `require_dentist` returning the dentist id; a helper that adds the clinic filter to appointment queries) (depends on T004)
- [ ] T007 Implement the pure status rules in `app/modules/reception/status_rules.py` using IST dates and UTC storage (depends on T005)
- [ ] T008 [P] Write integration tests for the status service in `tests/integration/reception/test_status_service.py`: conditional update on expected status, 409 with current status when stale, event row written in the same transaction with actor and time, clinic filter applied
- [ ] T009 Implement `app/modules/booking/status_service.py` (`change_status` with `UPDATE … WHERE id AND clinic_id AND status = expected`, inserts the row in ent-appointment-event with from and to status, actor and time) (depends on T006, T007, T008)
- [ ] T010 [P] Add the Alembic migration `alembic/versions/<rev>_appointment_clinic_start_index.py` creating `ix_appointment_clinic_start` on `(clinic_id, start_at)` only if feature 004 has not created an equivalent index
- [ ] T011 [P] Add role route guards for receptionist and dentist in `src/routes/guards.tsx` in brightsmile/clinic-web
- [ ] T012 [P] Add IST date and time formatting helpers (times shown in IST, English) in `src/lib/istDate.ts` in brightsmile/clinic-web

**Checkpoint**: Foundation ready - user story implementation can begin

---

## Phase 3: User Story 1 - See the day of my clinic (Priority: P1) 🎯 MVP

**Goal**: A receptionist sees the day view of their own clinic, one column per dentist, can change day, and opens an appointment panel.

**Independent Test**: Sign in as a receptionist of clinic A with seeded data for both clinics; the view shows only clinic A, one column per dentist, other days work, and the panel opens.

### Tests for User Story 1

- [ ] T013 [P] [US1] Contract test for `GET /api/reception/day` and `GET /api/reception/appointments/{id}` in `tests/contract/test_reception_day_contract.py`
- [ ] T014 [P] [US1] Integration test in `tests/integration/reception/test_day_view.py`: one column per dentist working that day, a dentist working at both clinics shows clinic A appointments only, a dentist on leave all day with an appointment keeps a column, cancelled appointments not listed, Sunday returns no columns, invalid date returns 400, name, phone, treatment and status present
- [ ] T015 [P] [US1] Component test in `tests/reception/DayViewPage.test.tsx`: columns render, next and previous day and date pick reload, 30-second refresh keeps the open panel, empty-day message

### Implementation for User Story 1

- [ ] T016 [P] [US1] Create the response models DayView, DayColumn, DayAppointment and AppointmentPanel (with `allowed_actions`, `no_show_allowed_from`, `history`) in `app/modules/reception/schemas_day.py`
- [ ] T017 [US1] Implement the day view query for one clinic and one IST date (appointments, patient name and phone, treatment, status, working-hours columns, cancelled excluded) in `app/modules/reception/day_view.py` (depends on T006, T007, T010, T014, T016)
- [ ] T018 [US1] Implement `GET /reception/day` and `GET /reception/appointments/{id}` in `app/modules/reception/routes_day.py` and include the router in `app/modules/reception/router.py` (depends on T017)
- [ ] T019 [P] [US1] Create the day view API client in `src/features/reception/dayApi.ts`
- [ ] T020 [US1] Build the day view screen (columns, appointment cards, date navigation, 30-second polling and manual refresh) in `src/features/reception/DayViewPage.tsx` (depends on T012, T015, T019)
- [ ] T021 [US1] Build the appointment panel (details, history, only the actions listed in `allowed_actions`, stays open on refresh) in `src/features/reception/AppointmentPanel.tsx` (depends on T019, T020)
- [ ] T022 [US1] Register the reception route behind the receptionist guard in `src/routes/index.tsx` (depends on T011, T020)

**Checkpoint**: User Story 1 is functional and testable on its own

---

## Phase 4: User Story 2 - Mark a patient as arrived (Priority: P1)

**Goal**: A receptionist marks a booked appointment of today as arrived.

**Independent Test**: Mark a booked appointment of today arrived and see status, actor and time; a future appointment, another clinic's appointment and a stale status are refused.

### Tests for User Story 2

- [ ] T023 [P] [US2] Integration test in `tests/integration/reception/test_arrived.py`: success writes event with actor and time, future date 422, other clinic 404, stale expected status 409 with current status
- [ ] T024 [P] [US2] Component test in `tests/reception/AppointmentPanelArrived.test.tsx`: Arrived offered only when allowed, reached in 3 clicks or fewer from the day view, conflict message and refresh on 409

### Implementation for User Story 2

- [ ] T025 [P] [US2] Create StatusChange and StatusConflict models in `app/modules/reception/schemas_status.py`
- [ ] T026 [US2] Implement `POST /reception/appointments/{id}/arrived` in `app/modules/reception/routes_status.py` using `status_service.change_status` and include it in `app/modules/reception/router.py` (depends on T009, T018, T023, T025)
- [ ] T027 [P] [US2] Create the status API client with `markArrived` in `src/features/reception/statusApi.ts`
- [ ] T028 [US2] Add the Arrived action and the conflict handling to `src/features/reception/AppointmentPanel.tsx` (depends on T021, T024, T027)

**Checkpoint**: User Stories 1 and 2 work independently

---

## Phase 5: User Story 3 - Mark a no-show and undo it the same day (Priority: P1)

**Goal**: No-show from 15 minutes after the start until the end of that day, with same-day undo.

**Independent Test**: With an appointment that started 20 minutes ago, mark no-show and undo; at 10 minutes, on the next day, and for arrived or cancelled appointments, the system refuses.

### Tests for User Story 3

- [ ] T029 [P] [US3] Integration test in `tests/integration/reception/test_no_show.py`: allowed at start+15 minutes, refused at start+10 minutes with `allowed_from`, refused after midnight IST, undo same day returns to booked with an event row, undo refused next day, refused for arrived and cancelled, stale status 409
- [ ] T030 [P] [US3] Component test in `tests/reception/AppointmentPanelNoShow.test.tsx`: No-show and Undo shown only per `allowed_actions`, hint shows the time from which no-show is allowed

### Implementation for User Story 3

- [ ] T031 [US3] Add `POST /reception/appointments/{id}/no-show` and `POST /reception/appointments/{id}/undo-no-show` (422 body with `allowed_from`) to `app/modules/reception/routes_status.py` (depends on T026, T029)
- [ ] T032 [US3] Add `markNoShow` and `undoNoShow` to `src/features/reception/statusApi.ts` (depends on T027)
- [ ] T033 [US3] Add the No-show and Undo actions and the allowed-from hint to `src/features/reception/AppointmentPanel.tsx` (depends on T028, T030, T032)

**Checkpoint**: User Stories 1–3 work independently

---

## Phase 6: User Story 4 - Find or create a patient (Priority: P1)

**Goal**: Reception finds a patient by phone or name across all patients (name and phone only), or creates one.

**Independent Test**: Search by phone digits and by name, create a patient, and try a duplicate phone and invalid input.

### Tests for User Story 4

- [ ] T034 [P] [US4] Integration test in `tests/integration/reception/test_patient_search.py`: at least 3 characters (400 otherwise, at most 64), at most 20 results ordered by name, results have only id, name and phone, a patient with appointments only at clinic B is found without those appointments, create returns 201, existing phone returns 200 with the existing patient, invalid name or phone returns 400
- [ ] T035 [P] [US4] Component test in `tests/reception/PatientSearch.test.tsx`: search, no-match create form, duplicate-phone offer, validation messages

### Implementation for User Story 4

- [ ] T036 [P] [US4] Create PatientHit and the create request model (name 1–100 characters after trimming, phone valid as in sign-in) in `app/modules/reception/schemas_patients.py`
- [ ] T037 [US4] Implement `find_patients(q, limit=20)` (case-insensitive contains on name and phone digits, no new extension) and `find_or_create_by_phone` (account and first person in one transaction) in `app/modules/identity/patient_service.py` (depends on T034)
- [ ] T038 [US4] Implement reception-side validation and mapping (minimum 3, maximum 64 characters, name and phone only in results) in `app/modules/reception/patient_search.py` (depends on T036, T037)
- [ ] T039 [US4] Implement `GET /reception/patients` and `POST /reception/patients` in `app/modules/reception/routes_patients.py` and include it in `app/modules/reception/router.py` (depends on T006, T038)
- [ ] T040 [P] [US4] Create the patient API client in `src/features/reception/patientApi.ts`
- [ ] T041 [US4] Build the patient search and create screen in `src/features/reception/PatientSearch.tsx` (depends on T035, T040)

**Checkpoint**: User Stories 1–4 work independently

---

## Phase 7: User Story 5 - Book a patient, including long treatments and walk-ins (Priority: P1)

**Goal**: Reception books any treatment type, including 60 and 90 minute types and walk-ins, with no cut-off, and never double books.

**Independent Test**: Book a 90-minute treatment for tomorrow and a walk-in today; two parallel requests for one slot yield one booking and one "slot taken" answer.

### Tests for User Story 5

- [ ] T042 [P] [US5] Integration test in `tests/integration/reception/test_reception_booking.py`: reception-only type accepted, slot 2 hours ahead accepted, date 45 days ahead accepted, walk-in creates booked then arrived events, slot too short or in a break refused, dentist not at this clinic 404, idempotency key retry does not book twice, messaging stub receives one request
- [ ] T043 [P] [US5] Concurrency test in `tests/integration/reception/test_booking_concurrency.py`: parallel reception and online attempts on one slot leave 0 overlapping active appointments for one dentist, loser gets 409 `slot_taken` with next free slots
- [ ] T044 [P] [US5] Component test in `tests/reception/BookForPatient.test.tsx`: treatment, dentist, date and slot choice, walk-in option, slot-taken message with next free slots

### Implementation for User Story 5

- [ ] T045 [P] [US5] Create the booking request and response models in `app/modules/reception/schemas_booking.py`
- [ ] T046 [P] [US5] Add a no-op messaging interface (`booking_created`, `booking_changed`, `booking_cancelled`) in `app/modules/messaging/interface.py` only if feature 007 has not added it
- [ ] T047 [US5] Implement reception booking (no 4-hour cut-off, no 30-day horizon, idempotency key, one transaction for appointment and event rows, walk-in as booked then arrived, exclusion-constraint conflict mapped to `slot_taken` with next free slots, messaging request after commit) in `app/modules/booking/reception_service.py` (depends on T009, T042, T043, T045, T046)
- [ ] T048 [US5] Implement `GET /reception/slots` (free slots of the receptionist's clinic for any active treatment type, via cmp-scheduling) and `POST /reception/appointments` in `app/modules/reception/routes_booking.py` and include it in `app/modules/reception/router.py` (depends on T047)
- [ ] T049 [P] [US5] Create the booking API client in `src/features/reception/bookingApi.ts`
- [ ] T050 [US5] Build the book-for-patient screen (selected patient, treatment, dentist, date, slot list, walk-in option, slot-taken handling) in `src/features/reception/BookForPatient.tsx` (depends on T041, T044, T049)
- [ ] T051 [US5] Add the free-slot "Book" entry and the walk-in entry to `src/features/reception/DayViewPage.tsx` (depends on T020, T050)

**Checkpoint**: User Stories 1–5 work independently

---

## Phase 8: User Story 6 - Reschedule or cancel for a patient (Priority: P2)

**Goal**: Reception moves or cancels appointments of its clinic with no cut-off; a cancel records who asked.

**Independent Test**: Move an appointment to another dentist's free slot; cancel once as "patient asked" and once as "clinic"; arrived and no-show appointments cannot be moved or cancelled.

### Tests for User Story 6

- [ ] T052 [P] [US6] Integration test in `tests/integration/reception/test_reception_change.py`: reschedule keeps clinic and treatment and frees the old slot at once, allowed 1 hour before start, `cancelled_by=patient` gives cancelled by the patient, `clinic` gives cancelled by the clinic, missing `cancelled_by` returns 400, arrived and no-show refused, other clinic 404, slot taken on reschedule returns 409 with next free slots, messaging stub receives a change or cancel request
- [ ] T053 [P] [US6] Component test in `tests/reception/CancelAndMove.test.tsx`: cancel dialog has no preselected option, move mode of the booking screen, conflict messages

### Implementation for User Story 6

- [ ] T054 [US6] Add reschedule and cancel (same transaction as the event row, reason "moved by reception" or "cancelled at reception", messaging request after commit) to `app/modules/booking/reception_service.py` (depends on T047, T052)
- [ ] T055 [US6] Add `POST /reception/appointments/{id}/reschedule` and `POST /reception/appointments/{id}/cancel` to `app/modules/reception/routes_booking.py` (depends on T048, T054)
- [ ] T056 [US6] Add `reschedule` and `cancel` to `src/features/reception/bookingApi.ts` (depends on T049)
- [ ] T057 [P] [US6] Build the cancel dialog with the required "patient asked / clinic cancelled" choice in `src/features/reception/CancelDialog.tsx`
- [ ] T058 [US6] Add a move mode (same clinic, any dentist, same treatment) to `src/features/reception/BookForPatient.tsx` (depends on T050, T053, T056)
- [ ] T059 [US6] Add the Reschedule and Cancel actions to `src/features/reception/AppointmentPanel.tsx` (depends on T033, T057, T058)

**Checkpoint**: User Stories 1–6 work independently

---

## Phase 9: User Story 7 - Dentist sees their own day (Priority: P2)

**Goal**: A dentist sees their own appointments for today at each clinic they work at, read only.

**Independent Test**: Sign in as a dentist working at both clinics; both clinics' own appointments appear, none of other dentists', no phone numbers, no action possible.

### Tests for User Story 7

- [ ] T060 [P] [US7] Integration test in `tests/integration/reception/test_dentist_day.py`: grouped by clinic, own appointments only, no phone number in the response, cancelled not listed, empty day, receptionist and patient get 403, every reception write route returns 403 for a dentist
- [ ] T061 [P] [US7] Component test in `tests/dentist/MyDayPage.test.tsx`: grouping by clinic, empty message, no action controls, no horizontal overflow at phone width

### Implementation for User Story 7

- [ ] T062 [P] [US7] Create the MyDay response models in `app/modules/reception/schemas_dentist.py`
- [ ] T063 [US7] Implement the dentist's day query across clinics for today IST in `app/modules/reception/dentist_day.py` (depends on T006, T060, T062)
- [ ] T064 [US7] Implement `GET /dentist/my-day` in `app/modules/reception/routes_dentist.py` and include it in `app/modules/reception/router.py` (depends on T063)
- [ ] T065 [P] [US7] Create the dentist API client in `src/features/dentist/api.ts`
- [ ] T066 [US7] Build the read-only "my day" screen, readable on a phone and a desktop browser, in `src/features/dentist/MyDayPage.tsx` (depends on T012, T061, T065)
- [ ] T067 [US7] Register the dentist route behind the dentist guard in `src/routes/index.tsx` (depends on T022, T066)

**Checkpoint**: All user stories are independently functional

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Checks that span stories

- [ ] T068 [P] Add a logging test in `tests/integration/reception/test_no_pii_in_logs.py` proving that name, phone and birth year do not appear in logs for search, create, booking, status change and the day views
- [ ] T069 Add structured logs, metrics and traces (OpenTelemetry) for the new endpoints with ids and correlation id only in `app/modules/reception/router.py` (depends on T039, T048, T055, T064)
- [ ] T070 [P] Add a day-view performance test in `tests/performance/test_day_view_load.py` (6 dentist columns × 16 appointments, payload about 15 KB, server p95 at or under 500 ms, 10 sessions refreshing every 30 s)
- [ ] T071 Run contract tests for every endpoint of this feature against `contracts/clinic-api-v1.openapi.yaml` in `tests/contract/test_reception_contract.py` and fix any difference (depends on T003, T018, T026, T031, T039, T055, T064)
- [ ] T072 Review the clinic-scoping and role changes (constitution principle III) and record the result in `specs/006-reception-dentist-day/checklists/security-review.md` (depends on T004, T006, T071)
- [ ] T073 [P] Write the paper-diary dry-run runbook for reception (typing in future appointments of both clinics, comparing each day with the paper diary, SA-005, RSK-010, SC-007) in `docs/runbooks/paper-diary-dry-run.md` in brightsmile/clinic-api
- [ ] T074 Agree with feature 007 whether messages are sent for appointments typed in before go-live (open question Q3) and record the decision in `specs/006-reception-dentist-day/clarifications.md`
- [ ] T075 Run the validation scenarios in `specs/006-reception-dentist-day/quickstart.md` and record the outcome in `specs/006-reception-dentist-day/checklists/requirements.md` (depends on T067, T069, T070, T071)
- [ ] T076 Run a usability check with reception staff booking a returning patient by phone number (target under 2 minutes, SC-003) and record the result in `specs/006-reception-dentist-day/checklists/usability-check.md` (depends on T051, T059)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies
- **Foundational (Phase 2)**: depends on Setup; blocks all user stories
- **User Stories (Phase 3–9)**: depend on Foundational
  - US2 and US3 build on the day view and panel of US1 (same screen) but their API parts only need Foundational and the day routes file
  - US5 builds on US4 (selected patient) in the web screen; the API parts are independent
  - US6 builds on US5's booking service and on US3's panel
  - US7 is independent of US2–US6
- **Polish (Phase 10)**: depends on the stories it checks

### Within Each User Story

- Tests first, and they must fail before the implementation
- Models/schemas, then services, then endpoints, then web client, then screens

### Parallel Opportunities

- T002, T003 together; T004, T005, T008, T010, T011, T012 together
- Tests of one story run in parallel (for example T013, T014, T015)
- After Foundational, a backend developer can take US1 → US2 → US3 while another takes US4 → US5 and a third takes US7
- Web clients (T019, T027, T040, T049, T065) are separate files and can be built together

---

## Parallel Example: User Story 1

```text
Task: "Contract test for GET /api/reception/day in tests/contract/test_reception_day_contract.py"
Task: "Integration test in tests/integration/reception/test_day_view.py"
Task: "Component test in tests/reception/DayViewPage.test.tsx"
Task: "Create the response models in app/modules/reception/schemas_day.py"
Task: "Create the day view API client in src/features/reception/dayApi.ts"
```

---

## Implementation Strategy

### MVP First

1. Phase 1 and Phase 2
2. Phase 3 (US1): reception can see the day instead of the paper diary
3. Phases 4–6 (US2–US4): check-in, no-show and patient search
4. Phase 7 (US5): reception booking, needed for the paper-diary entry before go-live and for the dry run
5. Phases 8–9 (US6, US7), then Phase 10

### Incremental Delivery

Each story adds value without breaking the earlier ones; stop at any checkpoint to validate that story on its own. All stories are MVP (Must) for 1 March 2027; the paper-diary dry run (T073) needs US1, US4 and US5 at least a week before go-live.

---

## Notes

- The P marker: tasks touch different files and have no unfinished dependency
- Every status and booking change writes an event row with actor and time (spec FR-010, FR-014)
- Never log patient name, phone number or birth year
- Commit after each task or logical group
