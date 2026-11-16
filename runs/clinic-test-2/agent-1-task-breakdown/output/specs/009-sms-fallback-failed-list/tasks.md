---

description: "Task list for WhatsApp to SMS fallback and reminders-failed list"
---

# Tasks: WhatsApp to SMS fallback and reminders-failed list

**Input**: Design documents from `/specs/009-sms-fallback-failed-list/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/reminders-failed.openapi.yaml, quickstart.md. Feature 006 (dispatcher, `ent-message`, adapters, webhooks) must be in place.

**Tests**: Included, because the constitution requires business logic tests first. Write each story's tests first and see them fail.

**Organization**: Tasks are grouped by user story. Repo names: `brightsmile/clinic-api` (backend, ctr-clinic-api) and `brightsmile/clinic-web` (ctr-web). File paths follow the layout in plan.md and are adjusted to feature 006's real layout when implementing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story the task belongs to
- Every task names its repo and exact file path

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Settings and flags that stories read

- [ ] T001 [P] Add the setting `REMINDER_SMS_FALLBACK_ENABLED` (boolean, default true when unset) to app/core/config.py and document it in .env.example (repo: brightsmile/clinic-api)
- [ ] T002 [P] Add the Release 2 screens flag `r2Screens` (reuse it if another R2 feature already added it) in src/config/featureFlags.ts (repo: brightsmile/clinic-web)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data and shared helpers every story uses

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 Add a forward-only, expand-only Alembic migration alembic/versions/0xx_message_sms_fallback.py: nullable `fallback_of_message_id` UUID foreign key to `ent-message.id` with a UNIQUE index, new status value `reminder_failed`, partial index on (kind, status, appointment_id) where status = 'reminder_failed' (repo: brightsmile/clinic-api)
- [ ] T004 Update the `ent-message` model in app/messaging/models.py with `fallback_of_message_id` (nullable, unique) and status `reminder_failed` per data-model.md (repo: brightsmile/clinic-api) (depends on T003)
- [ ] T005 Add `create_fallback_once(original_message_id)` in app/messaging/repository.py: insert with ON CONFLICT DO NOTHING on `fallback_of_message_id`, returns the new row or nothing when one exists (repo: brightsmile/clinic-api) (depends on T004)
- [ ] T006 [P] Add the fallback decision log and OpenTelemetry counter (sent, skipped_opt_out, skipped_cancelled, skipped_switch_off, marked_failed; message ids only, no name or phone) in app/messaging/fallback_metrics.py (repo: brightsmile/clinic-api)
- [ ] T007 Add `mark_reminder_failed(message_id)` (idempotent, no change when already marked) and `clear_on_delivered(message_id)` in app/messaging/reminder_state.py (repo: brightsmile/clinic-api) (depends on T004)

**Checkpoint**: Foundation ready

---

## Phase 3: User Story 1 - A failed WhatsApp reminder is sent once by SMS (Priority: P1) 🎯 MVP

**Goal**: A finally failed WhatsApp reminder produces exactly one SMS reminder.

**Independent Test**: Fail a WhatsApp reminder by provider error after 3 attempts and by failed receipt; one SMS exists and is sent; replayed receipts add none.

### Tests for User Story 1

- [ ] T008 [P] [US1] Unit tests for the fallback (error after 3 attempts, failed receipt, delivered original, failed after delivered ignored, one SMS only) in tests/messaging/test_fallback_service.py (repo: brightsmile/clinic-api)
- [ ] T009 [P] [US1] Integration tests for the signed rel-010 webhook with replayed and concurrent failed receipts producing one SMS in tests/messaging/test_webhook_fallback.py (repo: brightsmile/clinic-api)

### Implementation for User Story 1

- [ ] T010 [US1] Implement `handle_final_whatsapp_failure(message_id)` in app/messaging/fallback.py: in one transaction set the original `failed`, call `create_fallback_once`, create an SMS reminder (same content, channel sms, due now) only when a row was inserted, and record the decision (repo: brightsmile/clinic-api) (depends on T005, T006)
- [ ] T011 [US1] Call the fallback after the third failed attempt of a WhatsApp reminder in app/messaging/dispatcher.py (repo: brightsmile/clinic-api) (depends on T010)
- [ ] T012 [US1] Handle the failed WhatsApp receipt in app/messaging/webhooks.py (rel-010): call the fallback, ignore it when the message is already delivered, stay idempotent on provider message id (repo: brightsmile/clinic-api) (depends on T010)
- [ ] T013 [US1] Map the fallback SMS to the registered reminder SMS template in app/channel_adapters/sms_templates.py so it carries clinic, dentist, date, time and link (repo: brightsmile/clinic-api) (depends on T010)

**Checkpoint**: User Story 1 works on its own

---

## Phase 4: User Story 2 - The fallback respects STOP, cancellations and the switch (Priority: P2)

**Goal**: No SMS to opted-out patients or for cancelled appointments; the switch turns the fallback off.

**Independent Test**: Fail WhatsApp reminders for an opted-out patient, a cancelled appointment, with the switch off and with no setting; check the SMS and marks.

### Tests for User Story 2

- [ ] T014 [P] [US2] Tests for opt-out, cancelled appointment, switch off (marked "reminder failed"), unset switch (behaves as on) and switch turned off before the SMS is sent in tests/messaging/test_fallback_guards.py (repo: brightsmile/clinic-api)

### Implementation for User Story 2

- [ ] T015 [US2] Add the guards to app/messaging/fallback.py: reminders opt-out read through cmp-identity, appointment status read through cmp-booking, the T001 setting; opt-out and cancelled skip with no mark; switch off or no valid SMS number call `mark_reminder_failed`; each outcome recorded with the T006 helper (repo: brightsmile/clinic-api) (depends on T010, T001, T007)
- [ ] T016 [US2] Re-check the switch, opt-out and appointment status when the dispatcher is about to send a fallback SMS in app/messaging/dispatcher.py; on a switch-off, mark "reminder failed" instead of sending (repo: brightsmile/clinic-api) (depends on T011, T015)

**Checkpoint**: Guards and switch work on their own

---

## Phase 5: User Story 3 - An appointment is marked "reminder failed" when the SMS also fails (Priority: P1)

**Goal**: A failed SMS fallback marks the appointment "reminder failed", once.

**Independent Test**: Fail WhatsApp and then the SMS fallback by error and by receipt; the mark appears once and replays change nothing; a delivered receipt clears it.

### Tests for User Story 3

- [ ] T017 [P] [US3] Tests for marking after SMS error, after failed SMS receipt, replayed receipt, cancelled appointment not marked, and mark cleared by a delivered receipt in tests/messaging/test_reminder_failed.py (repo: brightsmile/clinic-api)

### Implementation for User Story 3

- [ ] T018 [US3] Keep the mark only for booked appointments: read the appointment status through cmp-booking in `mark_reminder_failed` and clear the mark on a later delivered receipt in app/messaging/reminder_state.py (repo: brightsmile/clinic-api) (depends on T007)
- [ ] T019 [US3] Mark "reminder failed" when the SMS fallback fails after its attempts in app/messaging/dispatcher.py (repo: brightsmile/clinic-api) (depends on T016, T018)
- [ ] T020 [US3] Handle failed and delivered SMS receipts in app/messaging/webhooks.py (rel-009): failed marks "reminder failed", delivered clears it, both idempotent on provider message id (repo: brightsmile/clinic-api) (depends on T012, T018)

**Checkpoint**: Failures are visible in the data

---

## Phase 6: User Story 4 - Reception gets tomorrow's reminders-failed list (Priority: P2)

**Goal**: A receptionist gets the list of their clinic's tomorrow appointments with a failed reminder.

**Independent Test**: Appointments at two clinics on several days, some marked; a receptionist of clinic A sees only clinic A's marked, booked appointments for tomorrow, in time order; other roles are refused.

### Tests for User Story 4

- [ ] T021 [US4] Contract test for `GET /api/reception/reminders-failed` against contracts/clinic-api-v1.openapi.yaml in tests/contract/test_reminders_failed_contract.py (repo: brightsmile/clinic-api) (depends on T022)
- [ ] T022 [P] [US4] Add the path and `ReminderFailedItem` schema from specs/009-sms-fallback-failed-list/contracts/reminders-failed.openapi.yaml to contracts/clinic-api-v1.openapi.yaml and bump the minor version (repo: brightsmile/clinic-api)
- [ ] T023 [P] [US4] Integration tests for clinic scoping, tomorrow in IST, cancelled appointment excluded, empty list, ordering, refusal of patient, dentist and practice manager, and a 50-row list answering within 500 ms server-side (SC-004) in tests/reception/test_reminders_failed.py (repo: brightsmile/clinic-api)

### Implementation for User Story 4

- [ ] T024 [US4] Add `reminder_failed_appointments(clinic_id, day_start, day_end)` (one row per booked appointment, ordered by start time) to the cmp-messaging interface in app/messaging/api.py (repo: brightsmile/clinic-api) (depends on T018)
- [ ] T025 [US4] Add `GET /api/reception/reminders-failed` in app/reception/router.py and response models in app/reception/schemas.py: receptionist only, clinic from the access context, tomorrow computed in IST, no name or phone in logs (repo: brightsmile/clinic-api) (depends on T024, T022)

**Checkpoint**: The list is available through the API

---

## Phase 7: User Story 5 - "Reminders failed" screen for reception (Priority: P3)

**Goal**: Reception opens "Reminders failed" and sees whom to phone; hidden until Release 2 is on.

**Independent Test**: Sign in as a receptionist with the flag on and off; the entry and route exist only when on; the rows match the API.

### Tests for User Story 5

- [ ] T026 [P] [US5] Component tests for list, empty state, error state with retry and phone numbers in src/pages/reception/__tests__/RemindersFailedPage.test.tsx (repo: brightsmile/clinic-web)
- [ ] T027 [P] [US5] Route tests for flag off (no entry, not-found page) and non-receptionist roles (no entry) in src/routes/__tests__/receptionRoutes.test.tsx (repo: brightsmile/clinic-web)

### Implementation for User Story 5

- [ ] T028 [P] [US5] Add the API client and types for the list in src/api/remindersFailed.ts per contracts/reminders-failed.openapi.yaml (repo: brightsmile/clinic-web)
- [ ] T029 [US5] Build the "Reminders failed" page with tomorrow's date, a table of time, patient, phone (tel link), dentist and treatment, the empty message and the error state with retry in src/pages/reception/RemindersFailedPage.tsx (repo: brightsmile/clinic-web) (depends on T028)
- [ ] T030 [US5] Register the route and navigation entry for receptionists only, shown only when `r2Screens` is on, in src/routes/receptionRoutes.tsx (repo: brightsmile/clinic-web) (depends on T029, T002)

**Checkpoint**: All user stories work

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T031 [P] Test that fallback and list code paths write no patient name or phone to logs in tests/messaging/test_no_pii_logs.py (repo: brightsmile/clinic-api)
- [ ] T032 [P] Write the runbook for the switch, the extra message charges and open question Q1 (client agreement) in docs/runbook-sms-fallback.md (repo: brightsmile/clinic-api)
- [ ] T033 [P] Test that the 90-day message retention job also removes fallback and `reminder_failed` rows in tests/messaging/test_retention_fallback.py (repo: brightsmile/clinic-api) (depends on T004)
- [ ] T034 Run the quickstart.md scenarios against staging with sandbox providers and the Release 2 flag on and off, and record the result in specs/009-sms-fallback-failed-list/quickstart.md (repo: brightsmile/clinic-api) (depends on T020, T025, T030)

---

## Dependencies & Execution Order

- Setup, then Foundational (blocks all stories).
- US1 first (the fallback itself). US2 builds on US1 (guards in the same service). US3 builds on US2's dispatcher changes. US4 needs US3's mark. US5 needs the US4 contract and API.
- Order by priority: US1 and US3 (P1), US2 and US4 (P2), US5 (P3). US1 and US3 must go in order of the shared files (dispatcher.py, webhooks.py).
- Backend tasks are in brightsmile/clinic-api; US5 is in brightsmile/clinic-web and can start from the contract once T022 is done.

## Parallel Opportunities

- T001 and T002; T006 beside T003-T005.
- Tests of one story: T008 with T009; T021 with T022 and T023 (T021 needs T022 to pass).
- US5 (web) tasks T026, T027, T028 in parallel with US4 implementation once T022 is done.
- Polish T031, T032, T033.

## Implementation Strategy

- MVP: Setup, Foundational and US1 (fallback sends once), then US3 so failures become visible, then US2 (switch and guards must ship together with US1 in release, as the client has not agreed), then US4 and US5 behind the Release 2 flag.
- Delivery target 2027-03-19 (not hard). Release with the switch default on; change the default only if the client answers Q1 with "no".
