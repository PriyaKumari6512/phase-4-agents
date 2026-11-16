# Tasks: Confirmations, reminders and opt-out via SMS and WhatsApp

**Input**: Design documents from `/specs/006-reminders-messages/` (plan.md, spec.md, research.md, data-model.md, contracts/messaging-api.md, quickstart.md)

**Prerequisites**: plan.md, spec.md. Tests are included because the constitution requires tests first for business logic.

**Repos**: every task names its repo: `clinic-api` = brightsmile/clinic-api (paths under `src/clinic_api/` and `tests/`), `clinic-web` = brightsmile/clinic-web.

**External dependencies (other features, not tasks here)**: booking transaction (feature 003), cancel and reschedule (feature 004), sign-in code flow (feature 001), reception patient record screen (feature 005). Hooks in this feature are written so those features call them.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: user story from spec.md (US1-US7)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Module skeletons, settings and test fixtures

- [ ] T001 [P] Create the packages `src/clinic_api/messaging/` and `src/clinic_api/channel_adapters/` and the settings module `src/clinic_api/messaging/settings.py` with template-id map per (kind, channel), quiet hours 21:00-08:00, evening send 20:00, lead 24 h, provider switches `SMS_PROVIDER` / `WHATSAPP_PROVIDER` (default `sandbox`), webhook secrets read from environment (repo: clinic-api)
- [ ] T002 [P] Create test fixtures in `tests/fixtures/messaging.py`: frozen IST clock, fake provider HTTP server with controllable latency/failures and signed-webhook helper, PostgreSQL session fixture (repo: clinic-api)
- [ ] T003 [P] Write the provider onboarding checklist `docs/messaging-providers.md` listing DLT sender ID and templates, WhatsApp templates to approve (confirmation, change notice, reminder, code), template variables, test accounts for weeks 1-2 and owners, to cover DEP-001, DEP-002, RSK-001 (repo: clinic-api)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data, port, catalogue and message creation used by every story

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Create forward-only Alembic migration `alembic/versions/0006_messaging.py` for table `message` exactly as data-model.md (kind and channel enums, status default `queued`, `attempts` CHECK 0..3, unique `(kind, appointment_id, appointment_version)`, unique `provider_message_id`, partial index on `scheduled_at` where `status='queued'`, nullable `original_message_id`), account columns `preferred_channel NOT NULL DEFAULT 'sms'`, `reminders_opt_out NOT NULL DEFAULT false`, opt-out time/source/by, and `appointment.channel NOT NULL` (repo: clinic-api)
- [ ] T005 Implement the Message ORM model and `MessageKind`, `Channel`, `MessageStatus` enums in `src/clinic_api/messaging/models.py` with the allowed status transitions from data-model.md (repo: clinic-api)
- [ ] T006 Define `ChannelPort`, `OutboundMessage`, `SendResult` (accepted id or error class `transient|permanent|unknown`), `Receipt`, `InboundReply` in `src/clinic_api/channel_adapters/port.py` as in contracts/messaging-api.md (repo: clinic-api)
- [ ] T007 Implement sandbox SMS and WhatsApp adapters (fixed latency, switchable failures, records sent messages) in `src/clinic_api/channel_adapters/sandbox.py` (repo: clinic-api)
- [ ] T008 Implement provider selection by configuration switch in `src/clinic_api/channel_adapters/registry.py` returning the adapter per channel (depends on T006, T007) (repo: clinic-api)
- [ ] T009 [P] Implement the single English message catalogue with IST date/time formatting (UTC stored, `DD Mon YYYY`, `hh:mm AM/PM`), template-id lookup from settings and a startup check that fails in production when a (kind, channel) has no template id, in `src/clinic_api/messaging/catalogue.py` (repo: clinic-api)
- [ ] T010 [P] Add `preferred_channel` and the reminders opt-out fields to the patient account model and read/write helpers in `src/clinic_api/identity/preferences.py` (depends on T004) (repo: clinic-api)
- [ ] T011 [P] Add a log filter that removes phone numbers, names and rendered text from messaging log records and adds correlation id and message id in `src/clinic_api/messaging/logging.py` (repo: clinic-api)
- [ ] T012 Implement idempotent message row creation (`INSERT ... ON CONFLICT DO NOTHING` on the unique key) in `src/clinic_api/messaging/service.py` (depends on T005, T009) (repo: clinic-api)

**Checkpoint**: Foundation ready - user stories can begin

---

## Phase 3: User Story 1 - Choose SMS or WhatsApp when booking (Priority: P1) MVP

**Goal**: The patient picks a channel on the confirm screen; SMS is the first default; the last choice is remembered.

**Independent Test**: Book choosing WhatsApp, start another booking and see WhatsApp pre-selected; a new patient sees SMS.

- [ ] T013 [P] [US1] Write integration tests for `GET /api/me/preferences` (default `sms`), booking with `channel`, rejection of a missing or invalid channel (422) and update of the remembered choice in `tests/integration/identity/test_preferences.py` (repo: clinic-api)
- [ ] T014 [US1] Implement `GET /api/me/preferences` in `src/clinic_api/identity/api.py` returning `{preferredChannel}` for the signed-in patient (repo: clinic-api)
- [ ] T015 [US1] Add required `channel` (`sms|whatsapp`) to the booking request and appointment, and set the account's `preferred_channel` when the booking is saved (a booking made by reception without a channel uses the account's `preferred_channel` and does not change it), in `src/clinic_api/booking/api.py` and `src/clinic_api/booking/service.py` (depends on T010, T014) (repo: clinic-api)
- [ ] T016 [P] [US1] Write component tests for the channel choice (default SMS, pre-selects the returned choice, 44 px targets) in `src/features/booking/ChannelChoice.test.tsx` (repo: clinic-web)
- [ ] T017 [US1] Implement the `ChannelChoice` radio group in `src/features/booking/ChannelChoice.tsx` and the preferences API client in `src/api/preferences.ts` (repo: clinic-web)
- [ ] T018 [US1] Add `ChannelChoice` to the confirm screen and send `channel` with the booking request in `src/features/booking/ConfirmStep.tsx` (depends on T017) (repo: clinic-web)

**Checkpoint**: Channel choice works and is remembered

---

## Phase 4: User Story 2 - Immediate booking confirmation (Priority: P1)

**Goal**: A confirmation is sent after the booking commits, in the chosen channel, without slowing the booking.

**Independent Test**: Book against sandbox providers; within about 30 s a confirmation with clinic, dentist, treatment, date, time (IST) and link is recorded as sent.

- [ ] T019 [P] [US2] Write unit tests for confirmation rendering (five details, IST, English, only templated values passed) in `tests/unit/messaging/test_catalogue.py` (repo: clinic-api)
- [ ] T020 [P] [US2] Write integration tests that the confirmation row is committed with the booking, is absent when the booking fails or the slot is taken, is created once for a retried request, and is still created for an opted-out patient, in `tests/integration/messaging/test_confirmation.py` (repo: clinic-api)
- [ ] T021 [P] [US2] Implement the SMS adapter (send through registered template id, variable mapping, error mapping to transient/permanent/unknown, 5 s timeout) in `src/clinic_api/channel_adapters/sms.py` (repo: clinic-api)
- [ ] T022 [P] [US2] Implement the WhatsApp adapter (approved template send, variable mapping, error mapping, 5 s timeout) in `src/clinic_api/channel_adapters/whatsapp.py` (repo: clinic-api)
- [ ] T023 [P] [US2] Write adapter tests against the fake provider server (request shape holds only template id, phone and template values; error mapping) in `tests/unit/channel_adapters/test_sms_whatsapp.py` (repo: clinic-api)
- [ ] T024 [US2] Add the `confirmation` template variables and rendering to `src/clinic_api/messaging/catalogue.py` and the link builder `src/clinic_api/messaging/links.py` (link to the appointment page of feature 004) (depends on T009) (repo: clinic-api)
- [ ] T025 [US2] Implement `MessagingService.on_booked` creating the confirmation row (due now, channel from the appointment, runs inside the caller's transaction) in `src/clinic_api/messaging/service.py` (depends on T012, T024) (repo: clinic-api)
- [ ] T026 [US2] Implement the dispatcher core in `src/clinic_api/messaging/dispatcher.py`: claim due rows with `FOR UPDATE SKIP LOCKED` (limit 50, lease 2 min), render, send through the registry adapter, store provider message id and status `sent` (depends on T008, T021, T022, T025) (repo: clinic-api)
- [ ] T027 [US2] Start the dispatcher every 30 s in the application lifespan in `src/clinic_api/main.py` (depends on T026) (repo: clinic-api)
- [ ] T028 [US2] Call `MessagingService.on_booked` inside the booking transaction in `src/clinic_api/booking/service.py` after the appointment and its history are written (depends on T015, T025) (repo: clinic-api)
- [ ] T029 [P] [US2] Write an integration test that two dispatchers claim the same due rows once only and that a provider outage leaves the booking successful and the confirmation queued, in `tests/integration/messaging/test_dispatcher_claim.py` (repo: clinic-api)

**Checkpoint**: Booking confirmations flow end to end on sandbox providers

---

## Phase 5: User Story 3 - Reminder 24 hours before, with quiet hours (Priority: P1)

**Goal**: One reminder per appointment, 24 hours ahead, shifted out of 21:00-08:00 IST, none for last-minute bookings.

**Independent Test**: With a frozen clock check the scheduled time for due 14:00, 22:30, 03:00, an already-passed evening and a booking made less than 24 hours ahead.

- [ ] T030 [P] [US3] Write table-driven unit tests for the quiet-hours and 24-hour rule (due 14:00; 21:00 and 08:00 boundaries; 22:30; 03:00; evening already passed outside and inside quiet hours; less than 24 h; changed settings) in `tests/unit/messaging/test_schedule.py` (repo: clinic-api)
- [ ] T031 [US3] Implement the pure function `plan_reminder(start_utc, booked_at_utc, settings)` returning `due_at` and `scheduled_at` or none, in `src/clinic_api/messaging/schedule.py` (repo: clinic-api)
- [ ] T032 [US3] Add the `reminder` template (clinic, dentist, date, time, link to reschedule or cancel) to `src/clinic_api/messaging/catalogue.py` (repo: clinic-api)
- [ ] T033 [US3] Extend `MessagingService.on_booked` in `src/clinic_api/messaging/service.py` to create the reminder row from `plan_reminder` unless reminders are switched off (depends on T025, T031, T032) (repo: clinic-api)
- [ ] T034 [P] [US3] Write integration tests that the reminder is created with the booking, sent within 15 minutes of `scheduled_at` with all required details and link, and not created for a booking less than 24 h ahead, in `tests/integration/messaging/test_reminder_dispatch.py` (repo: clinic-api)

**Checkpoint**: Reminders are scheduled and sent on time

---

## Phase 6: User Story 4 - Reminders follow changes; change notices (Priority: P1)

**Goal**: No reminder for cancelled appointments; a rescheduled appointment has one reminder for its new time; patients get change notices.

**Independent Test**: Book then cancel before the reminder is due: no reminder, cancellation notice sent. Book then reschedule: one reminder for the new time and a change notice.

- [ ] T035 [P] [US4] Write integration tests for cancel, reschedule (including to less than 24 h ahead), clinic-initiated cancel, a reminder already claimed when the appointment is cancelled, and change notices sent despite opt-out, in `tests/integration/messaging/test_changes.py` (repo: clinic-api)
- [ ] T036 [US4] Add the `change_notice` templates (cancelled; rescheduled with new date and time) to `src/clinic_api/messaging/catalogue.py` (repo: clinic-api)
- [ ] T037 [US4] Implement `MessagingService.on_cancelled` and `on_rescheduled` (cancel pending reminder rows, create the change notice, and for reschedule create one new reminder via `plan_reminder` with the incremented appointment version) in `src/clinic_api/messaging/service.py` (depends on T033, T036) (repo: clinic-api)
- [ ] T038 [US4] Add the send-time re-check to `src/clinic_api/messaging/dispatcher.py`: before sending a reminder confirm the appointment is still booked and the account is not opted out, else mark `skipped` with `status_reason` (depends on T026) (repo: clinic-api)
- [ ] T039 [US4] Call `on_cancelled` and `on_rescheduled` inside the patient and reception cancel and reschedule transactions in `src/clinic_api/booking/service.py` (depends on T037) (repo: clinic-api)

**Checkpoint**: Reminders and notices follow every appointment change

---

## Phase 7: User Story 5 - Stop reminders by replying STOP or through reception (Priority: P2)

**Goal**: STOP reply or reception switches reminders off; confirmations and change notices continue.

**Independent Test**: Post a signed STOP webhook, or toggle in reception: pending reminders are cancelled, a new booking still gets a confirmation but no reminder.

- [ ] T040 [P] [US5] Write tests for STOP parsing (case and spacing), signed and unsigned webhook calls, repeated STOP, unknown sender, and the reception endpoint (roles, audit, cancel of pending reminders, switching back on) in `tests/integration/messaging/test_opt_out.py` (repo: clinic-api)
- [ ] T041 [P] [US5] Implement constant-time HMAC-SHA256 verification of the raw body in `src/clinic_api/channel_adapters/signature.py` (repo: clinic-api)
- [ ] T042 [US5] Implement inbound reply parsing (`STOP` after trim and upper-case) in `src/clinic_api/channel_adapters/sms.py` (depends on T021) (repo: clinic-api)
- [ ] T043 [US5] Implement `MessagingService.set_reminders(account, enabled, source, actor)` setting the account flag and cancelling pending reminders in one transaction in `src/clinic_api/messaging/service.py` (depends on T037) (repo: clinic-api)
- [ ] T044 [US5] Implement `POST /api/webhooks/sms` for inbound STOP (verify signature, 401 on failure, idempotent, answers quickly) in `src/clinic_api/messaging/webhooks.py` and register it in `src/clinic_api/main.py` (depends on T041, T042, T043) (repo: clinic-api)
- [ ] T045 [US5] Implement `PUT /api/patient-accounts/{accountId}/reminders` for receptionist and practice manager (dentist gets 403, audited who and when) and add `remindersEnabled` fields to the patient record response in `src/clinic_api/identity/api.py` (depends on T043) (repo: clinic-api)
- [ ] T046 [P] [US5] Write a component test for the reminders toggle (shows state, source and time; calls the endpoint) in `src/features/reception/ReminderToggle.test.tsx` (repo: clinic-web)
- [ ] T047 [US5] Implement `ReminderToggle` in `src/features/reception/ReminderToggle.tsx` with the API client in `src/api/preferences.ts` and place it on the reception patient record screen `src/features/reception/PatientRecord.tsx` (repo: clinic-web)

**Checkpoint**: Opt-out works from both routes

---

## Phase 8: User Story 6 - Sign-in codes sent by SMS (Priority: P2)

**Goal**: Sign-in codes go out by SMS through the registered code template inside the request.

**Independent Test**: Request a code for a test number: one SMS through the code template; a failing provider gives a "try again" answer within the provider timeout.

- [ ] T048 [P] [US6] Write tests for `send_code` (one SMS via the code template, success and failure results, no code or phone in logs, no readable code stored) in `tests/integration/messaging/test_send_code.py` (repo: clinic-api)
- [ ] T049 [US6] Add the `code` template to `src/clinic_api/messaging/catalogue.py` and implement `MessagingService.send_code(phone, code)` (direct adapter call with 5 s timeout, no retry, a `code` message row without rendered text) in `src/clinic_api/messaging/service.py` (depends on T012, T021) (repo: clinic-api)
- [ ] T050 [US6] Call `send_code` from the sign-in code request and map failure to the "could not send, try again" answer in `src/clinic_api/identity/auth.py` (depends on T049) (repo: clinic-api)

**Checkpoint**: Patients receive sign-in codes

---

## Phase 9: User Story 7 - Reliable and compliant delivery operations (Priority: P2)

**Goal**: Retries, breaker, receipts, lag alert, nightly reconciliation and retention keep delivery on time and compliant.

**Independent Test**: Run the dispatcher against a failing sandbox provider and check retries, breaker and queued state; replay receipts; run the nightly job.

- [ ] T051 [P] [US7] Write unit tests for the circuit breaker (opens after 5 failures in 60 s, half-open probe, closes) and for retry timing (3 attempts, waits 5 s and 30 s, permanent errors not retried) in `tests/unit/channel_adapters/test_breaker_retry.py` (repo: clinic-api)
- [ ] T052 [US7] Implement the per-provider circuit breaker in `src/clinic_api/channel_adapters/breaker.py` (repo: clinic-api)
- [ ] T053 [US7] Add retry with backoff 5 s and 30 s, attempt counting, lease expiry handling, breaker integration (rows stay `queued` while open) and permanent-failure marking to `src/clinic_api/messaging/dispatcher.py` (depends on T038, T052) (repo: clinic-api)
- [ ] T054 [P] [US7] Write tests for receipts: valid SMS and WhatsApp receipts update status, repeats and unknown ids change nothing, status never moves backwards, bad signature gives 401, over-limit gives 429, in `tests/integration/messaging/test_receipts.py` (repo: clinic-api)
- [ ] T055 [US7] Implement the WhatsApp receipt parser in `src/clinic_api/channel_adapters/whatsapp.py` and the SMS receipt parser in `src/clinic_api/channel_adapters/sms.py` (depends on T042) (repo: clinic-api)
- [ ] T056 [US7] Implement receipt handling (idempotent on `provider_message_id`, forward-only status) for `POST /api/webhooks/sms` and add `POST /api/webhooks/whatsapp` with a per-IP rate limit in `src/clinic_api/messaging/webhooks.py` (depends on T044, T055) (repo: clinic-api)
- [ ] T057 [US7] Record the metrics `messaging.reminder_lag_seconds`, `messaging.send_total{result}` and `messaging.breaker_state` each dispatcher cycle in `src/clinic_api/messaging/dispatcher.py` and add the alert rule for lag above 600 s in `ops/alerts/messaging.yaml` (hand over to the infra repo for wiring) (depends on T053) (repo: clinic-api)
- [ ] T058 [P] [US7] Write tests for the nightly job (creates a missing reminder for a booked, opted-in appointment 24-48 h ahead, requeues expired leases, cancels queued rows of cancelled appointments, deletes rows older than 90 days, runs once with two replicas) in `tests/integration/messaging/test_jobs.py` (repo: clinic-api)
- [ ] T059 [US7] Implement the nightly reconciliation and 90-day retention job (JOB-005) with a PostgreSQL advisory lock in `src/clinic_api/messaging/jobs.py` and schedule it at 02:00 IST in `src/clinic_api/main.py` (depends on T037, T053) (repo: clinic-api)

**Checkpoint**: Delivery is reliable, observable and compliant

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Contract, privacy, performance and validation across stories

- [ ] T060 [P] Add the new operations (preferences, booking `channel`, reception reminders, two webhooks) to `contracts/clinic-api-v1.openapi.yaml` and write contract tests in `tests/contract/test_messaging_contract.py` (repo: clinic-api)
- [ ] T061 [P] Write a test that fails if any messaging log line, error body or metric label contains a phone number, name or rendered text in `tests/unit/messaging/test_no_pii_in_logs.py` (depends on T011) (repo: clinic-api)
- [ ] T062 Write a load test with 1,000 due reminders and a slow sandbox provider that checks 99% are sent within 15 minutes of `scheduled_at` in `tests/integration/messaging/test_reminder_lag.py` (depends on T053, T057) (repo: clinic-api)
- [ ] T063 Run the quickstart.md scenarios against staging with sandbox providers and record the results in `specs/006-reminders-messages/quickstart.md` (depends on T039, T047, T050, T059) (repo: clinic-api)
- [ ] T064 [P] Review the DLT and WhatsApp template texts in `src/clinic_api/messaging/catalogue.py` against `docs/messaging-providers.md` so each registered or approved template matches variable for variable (depends on T049) (repo: clinic-api)

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1) has no dependencies.
- Foundational (Phase 2) depends on Setup and blocks every user story.
- US1 depends on Foundational only. US2 needs T015 from US1 for the booking hook (T028).
- US3 depends on US2 (service and dispatcher). US4 depends on US3 (reminder rows). US5 depends on US4 (`set_reminders` reuses cancel logic) and on T021. US6 needs only Foundational and T021. US7 depends on US4 (dispatcher re-check) and US5 (webhook route).
- Polish depends on the stories it tests.

### Parallel Opportunities

- Phase 1 tasks T001-T003 in parallel.
- In Phase 2, T009, T010 and T011 run in parallel after T004 and T001.
- In US2, adapters T021 and T022 and tests T019, T020, T023 run in parallel; the front-end tasks of US1 (T016-T018) run in parallel with all back-end stories.
- US5's front-end tasks T046-T047 run in parallel with back-end tasks after the endpoint contract is fixed.
- Tests within a story are written first and fail before implementation.

### Parallel Example: User Story 2

```text
Task: "SMS adapter in src/clinic_api/channel_adapters/sms.py"
Task: "WhatsApp adapter in src/clinic_api/channel_adapters/whatsapp.py"
Task: "Confirmation integration tests in tests/integration/messaging/test_confirmation.py"
```

## Implementation Strategy

### MVP First

1. Setup and Foundational.
2. US1 and US2: channel choice and confirmation (first message in the patient's hands, sandbox providers).
3. US3 and US4: reminders and change handling, which deliver the no-show goal.
4. US5 (STOP, required by NFR-011), US6 (codes), US7 (reliability) before go-live; the dispatcher core in T026 is usable earlier.
5. Polish: contract, privacy, load, quickstart.

### Release 2 (not in this feature)

Feature 009 adds the WhatsApp-to-SMS fallback (FR-029) and the failed-reminder list (FR-033) using `message.original_message_id`, `error_class` and the adapter port prepared here.

## Notes

Tasks marked P touch different files and have no unfinished dependencies.
- Provider names and field names are bound when the providers are chosen (ASM-009); until then sandbox adapters are used.
- Never log phone numbers, names or rendered text (constitution Definition of Done).
