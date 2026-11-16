# Tasks: Online booking by patients (MOD-03)

**Input**: Design documents from `/specs/003-online-booking/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/online-booking.openapi.yaml, quickstart.md

**Tests**: Requested. The constitution requires tests first for business logic, and the spec has three test stories (US4, US5, US6). Test tasks come before implementation tasks in each story.

**Organization**: Tasks are grouped by user story. Every task names its repo: **clinic-api** (brightsmile/clinic-api, ctr-clinic-api) or **clinic-web** (brightsmile/clinic-web, ctr-web). Paths are relative to that repo's root, except `specs/...` paths which are relative to the project root.

## Format: `- [ ] T### [P] [USn] Description with file path. Repo: clinic-api|clinic-web.`

- **[P]**: can run in parallel (different files, no unfinished dependency)
- **[USn]**: user story label (story phases only)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Module and feature folders in both repos

- [ ] T001 [P] Create the cmp-booking module skeleton `app/modules/booking/__init__.py` and `app/modules/booking/settings.py` (`booking_horizon_days`: integer, default 30, minimum 1, maximum 90, read from application configuration) and the empty test folders `tests/booking/unit`, `tests/booking/contract`, `tests/booking/integration`, `tests/booking/concurrency`, `tests/booking/performance`. Repo: clinic-api.
- [ ] T002 [P] Create the web feature folder `src/features/booking/` with `index.ts` exporting the booking routes (`/book`, `/book/slots`, `/book/confirm`, `/book/done`) and the test folder `src/features/booking/__tests__/`. Repo: clinic-web.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Tables, ports, schemas, fixtures, telemetry and the web API client that every story needs

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 Define the three in-process ports in `app/modules/booking/ports.py`: `SlotSource` (free slots for a clinic, treatment and dentist or all dentists in a time range; check treatment is bookable online; check dentist works at clinic; implemented by cmp-scheduling, MOD-02), `BookingMessages` (create confirmation and reminder rows inside the caller's transaction; implemented by feature 006) with a stub that writes nothing, and `BlockPolicy.is_blocked(person_id) -> bool` with the default `AlwaysAllowBlockPolicy` returning False (cmp-noshow-policy, Release 2). Repo: clinic-api.
- [ ] T004 [P] Create SQLAlchemy models `Appointment`, `AppointmentEvent` and `BookingRequest` in `app/modules/booking/models.py` exactly as in data-model.md: status is one of `booked`, `arrived`, `no_show`, `cancelled_by_patient`, `cancelled_by_clinic` (check constraint); channel is one of `sms`, `whatsapp`; `end_at > start_at`; `appointment_event.reason` at most 200 characters; `booking_request` primary key (patient_account_id, idempotency_key). Repo: clinic-api.
- [ ] T005 Write the Alembic migration `alembic/versions/0003_online_booking.py`: `CREATE EXTENSION IF NOT EXISTS btree_gist`, the three tables, the exclusion constraint `appointment_no_overlap` (`EXCLUDE USING gist (dentist_id WITH =, tstzrange(start_at, end_at, '[)') WITH &&) WHERE (status NOT IN ('cancelled_by_patient', 'cancelled_by_clinic'))`), and the indexes `appointment_patient_start_idx` (patient_id, start_at), `appointment_clinic_start_idx` (clinic_id, start_at) and an index on (appointment_id, at) for events; forward-only and compatible with the previous release. Repo: clinic-api. (depends on T004)
- [ ] T006 [P] Create request and response models in `app/modules/booking/schemas.py` from `specs/003-online-booking/contracts/online-booking.openapi.yaml`: `BookingOptions`, `Slot`, `SlotList` (at most 10 slots), `BookingRequest`, `Appointment`, `SlotTaken`; reject unknown fields and invalid UUIDs at the boundary. Repo: clinic-api.
- [ ] T007 [P] Create test fixtures in `tests/booking/conftest.py` and `tests/booking/fakes.py`: PostgreSQL database with migrations applied, a signed-in patient fixture (account and own person), a second patient, a fake `SlotSource` with 2 dentists, 1 clinic and the three online treatment types, and a recording `BookingMessages` fake. Repo: clinic-api.
- [ ] T008 [P] Add telemetry in `app/modules/booking/telemetry.py`: structured log helper carrying only ids and the correlation id (no patient name or phone number), OpenTelemetry counters `booking_outcome{result=booked|slot_taken|replayed|refused}` and latency histograms for the slots and booking operations. Repo: clinic-api.
- [ ] T009 [P] Create the API client `src/features/booking/api.ts`: functions for `GET /api/booking/options`, `GET /api/booking/slots`, `POST /api/appointments`; timeout 10 s; `X-CSRF-Token` header on writes; a new `Idempotency-Key` UUID per confirm attempt; writes are never retried automatically; reads retried once. Repo: clinic-web.
- [ ] T010 [P] Create `src/features/booking/bookingState.ts` holding the patient's choices (clinic, treatment, dentist or first available, day, slot, channel) across screens and the Back button, cleared after "booked". Repo: clinic-web.

**Checkpoint**: Foundation ready; user stories can start

---

## Phase 3: User Story 1 - Find a free slot (Priority: P1) MVP

**Goal**: A signed-in patient chooses clinic, online treatment and dentist or "first available" and sees free slots within the horizon.

**Independent Test**: Sign in, choose a clinic, "Check-up" and "first available": at most 10 earliest slots with dentists appear in time order; a named dentist and day shows only that dentist's slots; day 31 is not offered.

### Tests for User Story 1

- [ ] T011 [P] [US1] Unit tests in `tests/booking/unit/test_slots.py`: only online treatment types offered; "first available" merges all dentists and returns at most 10 earliest first; named dentist and day; horizon is today plus the setting inclusive (1 March allows 31 March); dentist not at the clinic gives a validation error; a past slot is never returned; empty day returns `next_free_date`. Repo: clinic-api.
- [ ] T012 [P] [US1] Contract tests for `GET /api/booking/options` and `GET /api/booking/slots` (200, 401 unsigned, 422 outside horizon or non-online treatment) against `specs/003-online-booking/contracts/online-booking.openapi.yaml` in `tests/booking/contract/test_slots_contract.py`. Repo: clinic-api.

### Implementation for User Story 1

- [ ] T013 [US1] Implement the patient slot lookup in `app/modules/booking/slots.py`: horizon check, `SlotSource` calls for one dentist and day or for all clinic dentists, merge and top 10, `next_free_date` for an empty named-dentist day, options built from cmp-scheduling and the signed-in patient. Repo: clinic-api. (depends on T003, T006)
- [ ] T014 [US1] Add `GET /api/booking/options` and `GET /api/booking/slots` to `app/modules/booking/router.py` and register the router in `app/main.py`; patient role required, input validated, telemetry from T008. Repo: clinic-api. (depends on T013, T008)
- [ ] T015 [P] [US1] Build the "who and what" screen `src/features/booking/WhoAndWhatScreen.tsx`: own name pre-selected as the person (Q1), clinic, treatment (online types only) and dentist or "first available" on one screen. Repo: clinic-web.
- [ ] T016 [P] [US1] Build the slot picker `src/features/booking/SlotPickerScreen.tsx`: day choice from today to today plus `horizon_days`, slot buttons with dentist name and IST time, empty-day message with the next day that has slots, clinic phone shown when no slot exists in the horizon. Repo: clinic-web.
- [ ] T017 [US1] Add `src/features/booking/BookingGuard.tsx`: a patient who is not signed in is sent to sign-in (feature 001) and returns to the same step with choices kept. Repo: clinic-web. (depends on T010)
- [ ] T018 [P] [US1] Screen tests in `src/features/booking/__tests__/who-and-slots.test.tsx`: treatment list, "first available" list, day limits, empty day, unsigned redirect. Repo: clinic-web. (depends on T015, T016, T017)

**Checkpoint**: US1 works alone against the fake or real scheduling source

---

## Phase 4: User Story 2 - Confirm and see the booking (Priority: P1)

**Goal**: The patient picks SMS or WhatsApp, confirms and sees the booked appointment; the booking, history entry and message rows are saved in one step.

**Independent Test**: Confirm a free slot: one appointment `booked`, one `booked` history entry with actor and time, message rows requested, "booked" screen shows details; a repeat with the same retry key gives the same appointment.

### Tests for User Story 2

- [ ] T019 [P] [US2] Unit tests in `tests/booking/unit/test_authorisation.py`: request naming another patient's person gives 403 and books nothing; unsigned gives 401; a booking beyond the horizon gives 422; default `BlockPolicy` always allows; a blocking policy fake gives 403. Repo: clinic-api.
- [ ] T020 [P] [US2] Integration test in `tests/booking/integration/test_book.py`: happy path creates appointment `booked`, one `appointment_event` (from null to `booked`, actor, time), message rows through the recording `BookingMessages` fake; a failing messaging provider (stub raising outside the transaction) does not undo the booking; no patient name or phone in captured logs. Repo: clinic-api.
- [ ] T021 [P] [US2] Contract tests for `POST /api/appointments` (201, 200 replay, 401, 403, 422) in `tests/booking/contract/test_book_contract.py`. Repo: clinic-api.
- [ ] T022 [P] [US2] Integration test in `tests/booking/integration/test_idempotency.py`: same key and body twice gives one appointment and the same answer (201 then 200); same key with a different body gives 422; a different key for the same slot is treated as a new attempt. Repo: clinic-api.

### Implementation for User Story 2

- [ ] T023 [US2] Implement `book()` in `app/modules/booking/service.py`: validate horizon, online treatment, dentist at clinic and that the person is the signed-in account holder's own; call `BlockPolicy`; in one transaction insert the `booking_request` row, the `appointment` (status `booked`, end = start plus treatment duration, `booked_by` from session), the first `appointment_event` and call `BookingMessages`; no provider call in the request. Repo: clinic-api. (depends on T003, T004, T005, T006, T008)
- [ ] T024 [US2] Add retry-key handling in `app/modules/booking/service.py`: look up (patient account, key); same fingerprint returns the stored appointment; different fingerprint raises a validation error. Repo: clinic-api. (depends on T023)
- [ ] T025 [US2] Add `POST /api/appointments` to `app/modules/booking/router.py`: required `Idempotency-Key` and CSRF header, 201 for new and 200 for replay, error mapping for 401, 403, 422. Repo: clinic-api. (depends on T024)
- [ ] T026 [P] [US2] Build `src/features/booking/ConfirmScreen.tsx`: summary of person, clinic, dentist, treatment, date and time (IST), SMS or WhatsApp choice with SMS as default (or the patient's default from options), Confirm button that disables while the request runs, new retry key per attempt, 10 s timeout message "result unknown, check your appointments" with no automatic retry. Repo: clinic-web.
- [ ] T027 [P] [US2] Build `src/features/booking/BookedScreen.tsx` showing clinic, dentist, treatment, date, time (IST) and channel, and clear the saved choices. Repo: clinic-web.
- [ ] T028 [P] [US2] Screen tests in `src/features/booking/__tests__/confirm-booked.test.tsx`: SMS default, double tap sends one request, timeout message and no retry, booked details. Repo: clinic-web. (depends on T026, T027)

**Checkpoint**: US1 and US2 give a complete happy-path booking

---

## Phase 5: User Story 3 - A slot is never booked twice (Priority: P1)

**Goal**: A lost race gives "slot just taken" with the next free slots, without starting over.

**Independent Test**: Two patients confirm the same slot at once; one wins, the other sees the message and the next free slots, and only one active appointment exists.

### Tests for User Story 3

- [ ] T029 [P] [US3] Integration tests in `tests/booking/integration/test_conflict.py`: two sessions same slot (one 201, one 409); partly overlapping slot refused; adjacent slots both succeed; cancelled appointment slot can be booked; slot lost to leave gives 409; 409 carries at most 10 next slots for the same clinic, treatment and dentist choice; same retry key repeated after 409 returns 409 again (Q2). Repo: clinic-api.
- [ ] T030 [P] [US3] Contract test for the 409 `SlotTaken` body in `tests/booking/contract/test_conflict_contract.py`. Repo: clinic-api.

### Implementation for User Story 3

- [ ] T031 [US3] In `app/modules/booking/service.py` handle the exclusion violation (SQLSTATE 23P01 on `appointment_no_overlap`): roll back, record outcome `slot_taken` for the retry key in its own short transaction, read the next free slots through `SlotSource`, raise `SlotTaken`; also re-check the slot is still free before the insert so a slot lost to leave gives the same answer. Repo: clinic-api. (depends on T024)
- [ ] T032 [US3] Map `SlotTaken` to HTTP 409 with the `SlotTaken` body in `app/modules/booking/router.py` and count `booking_outcome{result=slot_taken}`. Repo: clinic-api. (depends on T031)
- [ ] T033 [US3] Show the "this slot was just taken" message with the next free slots on the same screen in `src/features/booking/ConfirmScreen.tsx` and `src/features/booking/SlotPickerScreen.tsx`, keeping all other choices and using a new retry key for the next pick. Repo: clinic-web. (depends on T026, T016, T032)
- [ ] T034 [P] [US3] Screen test in `src/features/booking/__tests__/slot-taken.test.tsx`: a 409 shows the message and up to 10 slots, picking one and confirming sends a new retry key and succeeds. Repo: clinic-web. (depends on T033)

**Checkpoint**: Core booking flow complete and race-safe

---

## Phase 6: User Story 4 - Prove no double booking under load (Priority: P2)

**Goal**: Evidence that 0 overlapping active appointments occur in 1,000 concurrent-attempt runs (QA-003).

**Independent Test**: Run `pytest tests/booking/concurrency -m concurrency`; the report shows 0 overlaps in 100% of runs.

- [ ] T035 [US4] Write the concurrency test `tests/booking/concurrency/test_no_overlap.py` (marker `concurrency`): per run at least 30 simultaneous booking attempts on one dentist and slot, plus attempts on overlapping and adjacent slots, plus the same retry key sent several times at once; after each run assert exactly one winner per slot and count overlapping active appointments with a SQL check; 1,000 runs. Repo: clinic-api. (depends on T032)
- [ ] T036 [P] [US4] Write the report helper `tests/booking/concurrency/report.py` that writes runs, attempts, successes, conflicts and overlaps found to `specs/003-online-booking/reports/concurrency.md`. Repo: clinic-api. (depends on T035)
- [ ] T037 [US4] Run the suite against a PostgreSQL instance with two API instances (staging profile), attach the report and fix any overlap found. Repo: clinic-api. (depends on T036)

**Checkpoint**: QA-003 evidence recorded

---

## Phase 7: User Story 5 - Prove booking speed on a phone network (Priority: P2)

**Goal**: Evidence for QA-001 and QA-002 (2 s slots, 3 s booking for 95% of requests on 4G; server p95 500 ms and 800 ms).

**Independent Test**: Run the load script with 100 users and the 4G profile; the report states pass or fail.

- [ ] T038 [P] [US5] Write a data seeder `tests/booking/performance/seed_data.py` creating 3 clinics, 10 dentists with working hours and a year of appointments (at least 52,000 rows). Repo: clinic-api.
- [ ] T039 [US5] Write the load script `tests/booking/performance/run_load.py` (arguments `--users`, `--profile 4g`): 100 concurrent simulated patients doing options, "first available" slots, named-dentist slots and bookings, an added network delay for the 4G profile, p95 for server time and round trip written to `specs/003-online-booking/reports/performance.md`. Repo: clinic-api. (depends on T032, T038)
- [ ] T040 [US5] Run the load script against staging, record the report, and if a limit is missed add or adjust indexes or queries in `alembic/versions/0003_online_booking.py` or `app/modules/booking/slots.py` and run again. Repo: clinic-api. (depends on T039)

**Checkpoint**: QA-001 and QA-002 evidence recorded

---

## Phase 8: User Story 6 - Booking works on a phone for a new patient (Priority: P2)

**Goal**: 5 screens or fewer after sign-in, tap targets at least 44 px, no sideways scrolling on current Chrome and Safari on Android and iPhone.

**Independent Test**: Run the layout tests and the device checklist; all items pass.

- [ ] T041 [US6] Write the mobile-first styles `src/features/booking/booking.css` and apply them in the four screens: single column from 320 px width, buttons, slot buttons, links and fields at least 44 px by 44 px, no fixed widths above the viewport. Repo: clinic-web. (depends on T015, T016, T026, T027)
- [ ] T042 [P] [US6] Layout tests in `src/features/booking/__tests__/mobile-layout.test.tsx`: the flow after sign-in has 4 screens (who and what, slot picker, confirm, booked); every interactive element is at least 44 px; no horizontal overflow at 320, 360 and 390 px; Back keeps earlier choices; all text English with IST times. Repo: clinic-web. (depends on T041)
- [ ] T043 [P] [US6] Write the device checklist `src/features/booking/__tests__/mobile-acceptance.md` covering current Chrome and Safari on Android and iPhone: screen count, tap size, sideways scrolling, Back, slow 4G, slot-taken case. Repo: clinic-web.
- [ ] T044 [US6] Run the checklist on the four browser and device combinations, record the results in `src/features/booking/__tests__/mobile-acceptance-results.md` and fix findings in `src/features/booking/booking.css`. Repo: clinic-web. (depends on T042, T043)

**Checkpoint**: NFR-001 and NFR-010 evidence recorded

---

## Phase 9: Polish & Cross-Cutting Concerns

- [ ] T045 [P] Merge the three operations and their schemas from `specs/003-online-booking/contracts/online-booking.openapi.yaml` into `contracts/clinic-api-v1.openapi.yaml` (api-clinic-api-v1) and run the contract tests. Repo: clinic-api.
- [ ] T046 [P] Add removal of `booking_request` rows older than 24 hours in `app/modules/booking/retention.py` and register it with the existing scheduled jobs in `app/main.py`, with a test in `tests/booking/integration/test_retention.py`. Repo: clinic-api.
- [ ] T047 [P] Record the authentication and authorisation review of the booking endpoints (person taken from the session, 403 on other ids, CSRF header, no personal data in logs, no new secrets) in `specs/003-online-booking/reports/security-review.md`. Repo: clinic-api.
- [ ] T048 Run the steps of `specs/003-online-booking/quickstart.md` end to end on staging and note the result in `specs/003-online-booking/reports/quickstart-run.md`. Repo: clinic-api. (depends on T037, T040, T044)

---

## Dependencies & Execution Order

- Setup (Phase 1) then Foundational (Phase 2) block everything.
- US1 starts after Phase 2. US2 needs the models and migration (Phase 2) and its screens use the US1 state, but the API part can run in parallel with US1. US3 builds on US2 (T031 depends on T024). US4, US5 and US6 need US3 (US6 needs the four screens of US1 and US2).
- Order by priority: US1, US2, US3 (P1), then US4, US5, US6 (P2, can run in parallel), then Polish.
- Cross-feature: needs feature 001 (sign-in and session), MOD-02 (`SlotSource` implementation), feature 006 (`BookingMessages` implementation); the ports and fakes let this feature proceed without them. Feature 005 later adds status changes on the tables created in T005.

### Parallel Example: Phase 2

```text
T004 models, T006 schemas, T007 fixtures, T008 telemetry (clinic-api)
T009 api client, T010 booking state (clinic-web)
```

### Parallel Example: User Story 1

```text
T011 unit tests and T012 contract tests (clinic-api) with T015 and T016 screens (clinic-web)
```

## Implementation Strategy

1. MVP: Phases 1 and 2, US1 and US2 (happy path), then US3 immediately; no release without the race protection.
2. Run US4, US5 and US6 in parallel while the three P1 stories are being integrated.
3. Polish and the quickstart run on staging before the Release 1 date.

## Notes

- Estimate guide: MOD-03 is 9 to 14 person-days (scope/estimate.md).
- Suggested split: backend-heavy tasks (Foundational, US2 and US3 service, US4, US5) to one developer with Python and PostgreSQL skills; web tasks (US1 and US2 screens, US6) to a React and CSS developer.
