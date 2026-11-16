---

description: "Task list for Patient online booking"
---

# Tasks: Patient online booking

**Input**: Design documents from `/specs/004-online-booking/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/booking-api.openapi.yaml, quickstart.md

**Tests**: Included. The constitution requires business-logic tests before or with the code, and the spec asks for a concurrency test (QA-003) and a performance check (NFR-002).

**Organization**: Tasks are grouped by user story. Paths: `clinic-api/` is repository `brightsmile/clinic-api`; `clinic-web/` is repository `brightsmile/clinic-web`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: User story the task belongs to (US1 to US5)
- Every task names its exact file paths

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Module and folder skeletons in both repositories

- [ ] T001 Create the booking module package `clinic-api/app/booking/__init__.py` and the test packages `clinic-api/tests/unit/booking/__init__.py`, `clinic-api/tests/contract/booking/__init__.py`, `clinic-api/tests/integration/booking/__init__.py`, `clinic-api/tests/concurrency/booking/__init__.py`, `clinic-api/tests/performance/booking/__init__.py`
- [ ] T002 [P] Create the web feature folder entry `clinic-web/src/features/booking/index.ts` exporting the booking routes
- [ ] T003 [P] Register the pytest markers `concurrency` and `performance` in `clinic-api/pyproject.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Tables, constraint, ports, schemas and shared web client that every story needs

**CRITICAL**: No user story work can begin until this phase is complete. Needs features 001, 002 and 003 in place (patient access context, clinic, dentist and treatment tables, free-slot function).

- [ ] T004 Write Alembic migration `clinic-api/migrations/versions/004a_booking_tables.py`: `CREATE EXTENSION IF NOT EXISTS btree_gist`; table `appointment` (id uuid primary key; clinic_id, dentist_id, patient_id, treatment_type_id uuid not null; start_at and end_at timestamptz not null with check `end_at > start_at`; status text not null default `booked` with check in (`booked`,`arrived`,`no_show`,`cancelled_by_patient`,`cancelled_by_clinic`); channel text not null with check in (`sms`,`whatsapp`); booked_by_actor_type text not null; booked_by_id uuid not null; created_at, updated_at timestamptz not null); constraint `appointment_no_overlap` as `EXCLUDE USING gist (dentist_id WITH =, tstzrange(start_at, end_at, '[)') WITH &&) WHERE (status IN ('booked','arrived','no_show'))`; indexes `(dentist_id, start_at)`, `(patient_id, start_at)`, `(clinic_id, start_at)`; table `appointment_event` (id, appointment_id, from_status null, to_status not null, actor_type not null, actor_id null, occurred_at not null, reason null; index `(appointment_id, occurred_at)`); table `booking_request` (id, patient_account_id, idempotency_key text 1 to 64 characters, request_fingerprint, appointment_id deferred foreign key, created_at; unique `(patient_account_id, idempotency_key)`). Forward-only, no DDL rights for the application user.
- [ ] T005 [P] Write Alembic migration `clinic-api/migrations/versions/004b_patient_channel.py` adding `preferred_channel` text not null default `sms` with check in (`sms`,`whatsapp`) to the patient account table, only if the column is not already there (depends on T004)
- [ ] T006 Create SQLAlchemy models `Appointment`, `AppointmentEvent`, `BookingRequest` in `clinic-api/app/booking/models.py` matching data-model.md (depends on T004)
- [ ] T007 [P] Create domain errors `SlotTaken`, `NotBookableOnline`, `BookingBlocked`, `IdempotencyKeyReused`, `OutsideBookingWindow` in `clinic-api/app/booking/errors.py`
- [ ] T008 [P] Create request and response models from `contracts/booking-api.openapi.yaml` (channel only `sms` or `whatsapp`, Idempotency-Key 1 to 64 characters of letters, digits and hyphen) in `clinic-api/app/booking/schemas.py`
- [ ] T009 [P] Define the `PolicyPort` (`is_blocked(patient_id)`), `MessagingPort` (`enqueue_booking_messages(session, appointment)`) and `SchedulingPort` (free slots, slot-free check, online treatment lookup) protocols in `clinic-api/app/booking/ports.py`
- [ ] T010 Implement the default adapters `NotBlockedPolicy` (always false), `NoopMessaging` (does nothing until feature 007) and `SchedulingAdapter` calling `app/scheduling/slots.py` in `clinic-api/app/booking/adapters.py` (depends on T009)
- [ ] T011 [P] Create metrics (booking attempts, booked, slot_taken, replays, duration histograms) and span names, with no patient data in attributes, in `clinic-api/app/booking/telemetry.py`
- [ ] T012 Create the router skeleton with the patient access dependency from `app/identity/access.py` (patient taken from the token only) in `clinic-api/app/booking/router.py` and include it under `/api` in `clinic-api/app/main.py` (depends on T008)
- [ ] T013 [P] Create integration fixtures (PostgreSQL 16 with `btree_gist`, two clinics, three dentists with hours in the next 30 days, online and reception-only treatment types, signed-in test patients A and B) in `clinic-api/tests/integration/booking/conftest.py` (depends on T004, T006)
- [ ] T014 [P] Merge the operations and schemas of `specs/004-online-booking/contracts/booking-api.openapi.yaml` into `clinic-api/contracts/clinic-api-v1.openapi.yaml`
- [ ] T015 [P] Create TypeScript types and the API client (`getOptions`, `listSlots`, `bookAppointment`) using the cookie session and CSRF header from the app shell in `clinic-web/src/features/booking/types.ts` and `clinic-web/src/features/booking/api.ts`
- [ ] T016 Create the booking flow state (who, clinic, treatment, dentist choice, day, slot, channel) in `clinic-web/src/features/booking/BookingFlowContext.tsx` (depends on T015)

**Checkpoint**: Foundation ready; user stories can start.

---

## Phase 3: User Story 1 - Book a free slot online (Priority: P1) MVP

**Goal**: A signed-in patient books a free slot with a named dentist or "first available" and sees the booked screen.

**Independent Test**: Sign in as a test patient, book a check-up with a named dentist and a cleaning with "first available"; both are saved with the right clinic, dentist, start and end and a confirmation request is made (quickstart scenarios 1, 2 and 6).

### Tests for User Story 1

> Write these first and see them fail.

- [ ] T017 [P] [US1] Contract tests for `GET /api/booking/options` and `GET /api/booking/slots` (named dentist, first available limited to 10, 30-day window, 401, 403 blocked, 422) in `clinic-api/tests/contract/booking/test_options_slots_contract.py`
- [ ] T018 [P] [US1] Contract tests for `POST /api/booking/appointments` success 201, 401, 403 blocked with clinic phone and 422 not bookable online or outside window in `clinic-api/tests/contract/booking/test_book_contract.py`
- [ ] T019 [P] [US1] Unit tests for the booking rules (online treatment types only, inactive clinic or treatment refused, dentist must work at the clinic, window today to 30 days after, half-hour grid, no past start, patient from the token and never from the request, blocked answer stops booking) in `clinic-api/tests/unit/booking/test_book_rules.py`
- [ ] T020 [P] [US1] Integration test: book with a named dentist and with first available, one `appointment` row and one `appointment_event` row each, messaging port called once in the same transaction, in `clinic-api/tests/integration/booking/test_book_online.py`
- [ ] T021 [P] [US1] Web test of the four-screen flow, 5 screens or fewer after sign-in, blocked notice and refusal message, in `clinic-web/src/features/booking/__tests__/bookingFlow.test.tsx`

### Implementation for User Story 1

- [ ] T022 [US1] Implement `get_options` (clinics, dentists, online treatment types, who = account holder only) and `list_slots` (blocked check, window clamp to the 30-day horizon, first-available top 10) in `clinic-api/app/booking/service.py` (depends on T010)
- [ ] T023 [US1] Implement `book_online` (validate input, blocked check, slot-free fast path, insert `appointment` with status `booked`, insert first `appointment_event`, call `MessagingPort.enqueue_booking_messages`, one transaction) in `clinic-api/app/booking/service.py` (depends on T022, T006)
- [ ] T024 [US1] Implement the operations `GET /booking/options`, `GET /booking/slots` and `POST /booking/appointments` and the error mapping (401, 403 with clinic phone, 422) in `clinic-api/app/booking/router.py` (depends on T012, T023)
- [ ] T025 [P] [US1] Build the who-and-what screen with the clinic and treatment form (online types only, 44 px tap targets, no sideways scrolling) in `clinic-web/src/features/booking/pages/WhoAndWhatPage.tsx` and `clinic-web/src/features/booking/components/ClinicTreatmentForm.tsx`
- [ ] T026 [P] [US1] Build the dentist choice (named or first available), day strip (today to 30 days after) and slot list in `clinic-web/src/features/booking/components/DentistChoice.tsx`, `clinic-web/src/features/booking/components/DayStrip.tsx` and `clinic-web/src/features/booking/components/SlotList.tsx`
- [ ] T027 [US1] Build the slot picker screen in `clinic-web/src/features/booking/pages/SlotPickerPage.tsx` (depends on T026)
- [ ] T028 [P] [US1] Build the blocked notice showing the clinic phone number in `clinic-web/src/features/booking/components/BlockedNotice.tsx`
- [ ] T029 [US1] Build the confirm screen (summary of clinic, dentist, treatment, date and time in IST; confirm button; channel fixed to SMS until User Story 3) in `clinic-web/src/features/booking/pages/ConfirmPage.tsx` (depends on T016, T027)
- [ ] T030 [P] [US1] Build the booked screen (clinic, dentist, treatment, date and time in IST) in `clinic-web/src/features/booking/pages/BookedPage.tsx`
- [ ] T031 [US1] Add the `/book` routes for the four screens, with redirect to sign-in when not signed in, in `clinic-web/src/app/routes.tsx` (depends on T025, T027, T029, T030)
- [ ] T032 [US1] Add structured logs (ids and a correlation id only, never name, phone or birth year), metrics and spans to the booking path in `clinic-api/app/booking/service.py` using `clinic-api/app/booking/telemetry.py` (depends on T023)

**Checkpoint**: User Story 1 works on its own with SMS and the no-op messaging port.

---

## Phase 4: User Story 2 - A slot is never booked twice (Priority: P1)

**Goal**: A lost race gets "slot taken" with the next free slots; a repeated confirm books once.

**Independent Test**: Two patients confirm the same slot, one wins and the other sees "slot taken" with next slots; the same request sent twice gives one appointment (quickstart scenarios 3 and 4).

### Tests for User Story 2

- [ ] T033 [P] [US2] Unit tests for key format (1 to 64 characters of letters, digits and hyphen), request fingerprint and reuse with a different body in `clinic-api/tests/unit/booking/test_idempotency.py`
- [ ] T034 [P] [US2] Integration test: second booking of a taken slot returns `slot_taken` with up to 10 next slots for the same clinic, treatment and dentist choice, and leaves no extra rows, in `clinic-api/tests/integration/booking/test_slot_taken.py`
- [ ] T035 [P] [US2] Integration test: repeated request with the same key and body returns the original booking, a different body gives 422 `idempotency_key_reused`, and two simultaneous requests with one key book once, in `clinic-api/tests/integration/booking/test_idempotency.py`
- [ ] T036 [P] [US2] Contract tests for 409 `slot_taken` body, 200 replay with header `Idempotent-Replay: true` and missing key giving 422 in `clinic-api/tests/contract/booking/test_book_conflict_contract.py`
- [ ] T037 [P] [US2] Web test: "slot taken" returns to the slot picker with the new slots, a notice, and clinic and treatment kept, in `clinic-web/src/features/booking/__tests__/slotTaken.test.tsx`

### Implementation for User Story 2

- [ ] T038 [US2] Implement the request key claim (`INSERT ... ON CONFLICT DO NOTHING` on `(patient_account_id, idempotency_key)`) and replay lookup in `clinic-api/app/booking/idempotency.py` (depends on T006)
- [ ] T039 [US2] In `book_online` claim the key first, map the exclusion violation (SQLSTATE 23P01) and a failed slot-free check to `SlotTaken`, roll back, then read up to 10 next free slots from the taken slot's start in `clinic-api/app/booking/service.py` (`next_slots_after_conflict`) (depends on T023, T038)
- [ ] T040 [US2] Require the `Idempotency-Key` header, return 409 with `next_slots`, return 200 with `Idempotent-Replay: true` on replay in `clinic-api/app/booking/router.py` (depends on T024, T039)
- [ ] T041 [P] [US2] Build the slot-taken notice in `clinic-web/src/features/booking/components/SlotTakenNotice.tsx`
- [ ] T042 [US2] Send a new `Idempotency-Key` per confirm and reuse it only for a retry of the same confirm in `clinic-web/src/features/booking/api.ts`, and handle 409 by returning to the picker with the next slots in `clinic-web/src/features/booking/BookingFlowContext.tsx` and `clinic-web/src/features/booking/pages/SlotPickerPage.tsx` (depends on T016, T027, T041)
- [ ] T043 [US2] Show "no free slots" with the clinic phone number when the next-slot list is empty in `clinic-web/src/features/booking/components/SlotList.tsx` (depends on T026)

**Checkpoint**: Stories 1 and 2 work; no double booking and no duplicate on retry.

---

## Phase 5: User Story 3 - Choose SMS or WhatsApp, remembered for next time (Priority: P1)

**Goal**: The patient chooses SMS or WhatsApp at confirm; SMS first; the choice is remembered.

**Independent Test**: A new patient sees SMS; chooses WhatsApp and confirms; the next booking starts on WhatsApp; a failed booking does not change it (quickstart scenario 5).

### Tests for User Story 3

- [ ] T044 [P] [US3] Unit tests for channel values (only `sms` or `whatsapp`, default `sms`) in `clinic-api/tests/unit/booking/test_channel.py`
- [ ] T045 [P] [US3] Integration test: `preferred_channel` default `sms`, set on confirmed booking, unchanged after a `slot_taken` failure, appointment holds its own channel, in `clinic-api/tests/integration/booking/test_remembered_channel.py`
- [ ] T046 [P] [US3] Web test: channel preselected from the options, changeable, kept after "slot taken", in `clinic-web/src/features/booking/__tests__/channelChoice.test.tsx`

### Implementation for User Story 3

- [ ] T047 [US3] Implement `get_preferred_channel` and `set_preferred_channel` on the patient account in `clinic-api/app/identity/channel.py`
- [ ] T048 [US3] Set the remembered channel inside the booking transaction and return `preferred_channel` from `get_options` in `clinic-api/app/booking/service.py` (depends on T039, T047)
- [ ] T049 [P] [US3] Build the SMS or WhatsApp choice (two 44 px options) in `clinic-web/src/features/booking/components/ChannelChoice.tsx`
- [ ] T050 [US3] Add the channel choice to the confirm screen, preselected from `preferred_channel` and sent with the booking, in `clinic-web/src/features/booking/pages/ConfirmPage.tsx` (depends on T029, T048, T049)

**Checkpoint**: Stories 1 to 3 give the complete patient booking flow.

---

## Phase 6: User Story 4 - Prove that concurrent bookings never overlap (Priority: P2)

**Goal**: A repeatable test shows 0 overlapping active appointments for one dentist in 100% of 1,000 concurrent-attempt runs (QA-003).

**Independent Test**: Run `pytest tests/concurrency/booking -m concurrency`; every run ends with one winner per contested slot and 0 overlaps (quickstart scenario 7).

- [ ] T051 [US4] Build the concurrency harness (barrier-synchronised attempts on separate connections, builder for dentist, slot and test patients, overlap check query over all active appointments per dentist) in `clinic-api/tests/concurrency/booking/harness.py`
- [ ] T052 [P] [US4] Test: 30 simultaneous attempts on one slot give exactly 1 booked and 29 `slot_taken` in `clinic-api/tests/concurrency/booking/test_one_winner.py` (depends on T051)
- [ ] T053 [P] [US4] Test: 1,000 runs with 2 to 100 simultaneous attempts, some runs mixing a longer overlapping booking, assert 0 overlapping active appointments in 100% of runs, in `clinic-api/tests/concurrency/booking/test_no_overlap_1000_runs.py` (depends on T051)
- [ ] T054 [P] [US4] Test: simultaneous attempts that share one request key produce one appointment per key in `clinic-api/tests/concurrency/booking/test_same_key_concurrent.py` (depends on T051)
- [ ] T055 [US4] Add the concurrency suite as a release-blocking step in the pipeline file `clinic-api/ci/pipeline.yml` (file created by feature 001; path to confirm) (depends on T053)
- [ ] T056 [US4] Run the suite on staging-like infrastructure and record runs, failures and maximum attempts in `specs/004-online-booking/checklists/concurrency-results.md` (depends on T052, T053, T054)

**Checkpoint**: QA-003 evidence exists.

---

## Phase 7: User Story 5 - Booking is quick on a phone network (Priority: P2)

**Goal**: Show free slots within 2 s and confirm within 3 s for 95% of requests on 4G at 100 concurrent patients (NFR-002; QA-001, QA-002).

**Independent Test**: Run the load script and the 4G client check; the report meets server p95 at most 500 ms (slots) and 800 ms (booking) and client 2 s and 3 s (quickstart scenario 8).

- [ ] T057 [US5] Create the load-data seed (2 clinics, 6 dentists, 30 days of hours, 450 appointments a week of existing bookings) in `clinic-api/tests/performance/booking/seed_load_data.py`
- [ ] T058 [US5] Create the load script (100 concurrent simulated patients, one request about every 3 s, mix of slot reads, first-available reads and bookings with unique keys, p50 and p95 per operation) in `clinic-api/tests/performance/booking/run_load.py` (depends on T057)
- [ ] T059 [P] [US5] Define the thresholds (slot list p95 at most 500 ms, booking p95 at most 800 ms, first available included) and fail the run when missed in `clinic-api/tests/performance/booking/thresholds.py`
- [ ] T060 [P] [US5] Test that the slot read and the booking insert use the `(dentist_id, start_at)` index (query plan check) in `clinic-api/tests/performance/booking/test_slot_query_plan.py`
- [ ] T061 [P] [US5] Write the client-side 4G check (Fast 4G profile, Chrome and Safari, 20 slot views and 20 bookings, slots within 2 s and booked screen within 3 s for 95%) in `specs/004-online-booking/checklists/performance-4g.md`
- [ ] T062 [US5] Run the load script and the 4G check on staging and record results against NFR-002 in `specs/004-online-booking/checklists/performance-results.md` (depends on T058, T059, T061)

**Checkpoint**: NFR-002 evidence exists, or the missed target is named.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Security, privacy and screen checks that cover several stories

- [ ] T063 [P] Test that no patient name, phone number or birth year appears in logs for any booking step in `clinic-api/tests/unit/booking/test_no_pii_in_logs.py`
- [ ] T064 [P] Test authorisation from the token owner only (a request carrying another patient's id is ignored or refused, staff and anonymous callers refused, booking never touches another patient's data) in `clinic-api/tests/integration/booking/test_authorisation.py`
- [ ] T065 [P] Record the screen checks (4 screens, tap targets at least 44 px, no sideways scrolling on Chrome and Safari on Android and iPhone) in `specs/004-online-booking/checklists/screens-nfr010.md`
- [ ] T066 Request the constitution III review of authorisation-affecting code and record the outcome in `specs/004-online-booking/checklists/security-review.md` (depends on T064)
- [ ] T067 Run the quickstart validation scenarios 1 to 8 and record the result in `specs/004-online-booking/checklists/quickstart-results.md` (depends on T056, T062, T065)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none.
- **Foundational (Phase 2)**: needs Phase 1 and features 001, 002 and 003; blocks all stories.
- **US1 (Phase 3)**: after Phase 2. MVP.
- **US2 (Phase 4)**: after Phase 2; builds on US1's `book_online` and router (T039 depends on T023, T040 on T024).
- **US3 (Phase 5)**: after Phase 2; T048 builds on T039, T050 on T029.
- **US4 (Phase 6)**: needs the booking endpoint and service of US1 and US2 to exist (T053 meaningful after T039).
- **US5 (Phase 7)**: needs US1 and US2 working on staging data.
- **Polish (Phase 8)**: after the stories it covers.

### User Story Dependencies

- US1 has no dependency on other stories.
- US2 and US3 extend US1's service; each is independently testable once US1 code exists.
- US4 and US5 verify US1 and US2.

### Within Each User Story

- Tests first, and they must fail before implementation.
- Models and ports before services; services before endpoints; backend before web screens that call it.

### Parallel Opportunities

- T002, T003 together; T005, T007, T008, T009, T011, T014, T015 together after their prerequisites.
- All test tasks of one story (for example T017 to T021) in parallel.
- Web components (T025, T026, T028, T030) in parallel with the backend tasks T022 to T024.
- T052, T053, T054 in parallel after T051; T059, T060, T061 in parallel.

## Parallel Example: User Story 1

```text
Task: "Contract tests for options and slots in clinic-api/tests/contract/booking/test_options_slots_contract.py"
Task: "Contract tests for booking in clinic-api/tests/contract/booking/test_book_contract.py"
Task: "Unit tests for booking rules in clinic-api/tests/unit/booking/test_book_rules.py"
Task: "Who-and-what screen in clinic-web/src/features/booking/pages/WhoAndWhatPage.tsx"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 and Phase 2.
2. Phase 3 (User Story 1).
3. Stop and validate with quickstart scenarios 1, 2 and 6.

### Incremental Delivery

1. Add User Story 2 (no double booking, retry-safe) and User Story 3 (channel) to complete the go-live flow.
2. Add User Story 4 (QA-003 evidence) and User Story 5 (NFR-002 evidence) before the UAT-ready date of 22 February 2027 so misses can be fixed before the 1 March 2027 go-live.
3. Finish with Polish.

## Notes

- Ports let this feature ship before features 007 (messaging) and 009 (no-show policy); replacing an adapter needs no change to `service.py`.
- Paths of modules owned by features 001, 002 and 003 (`app/main.py`, `app/identity/access.py`, `app/scheduling/slots.py`, `ci/pipeline.yml`) are assumed from the architecture and to be confirmed.
- Never log patient name, phone number or birth year.
