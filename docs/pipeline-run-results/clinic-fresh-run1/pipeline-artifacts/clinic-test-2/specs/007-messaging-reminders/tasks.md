---

description: "Task list for Confirmations, reminders, STOP and SMS fallback"
---

# Tasks: Confirmations, reminders, STOP and SMS fallback

**Input**: Design documents from `/specs/007-messaging-reminders/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (messaging-api.openapi.yaml, messaging-facade.md), quickstart.md

**Tests**: Included. The constitution (principle I) requires business-logic tests before or with the implementation; test tasks come first in each story and must fail before the implementation.

**Organization**: Tasks are grouped by user story. User Stories 1-7 are the MVP (Must, go-live 1 March 2027). User Stories 8-9 are Release 2 (Should, about 2-3 weeks later) and are kept in their own phases, migration, files and feature flag.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on unfinished tasks)
- **[Story]**: Which user story the task belongs to (US1 ... US9)
- Paths start with the repository: `brightsmile/clinic-api` is written `clinic-api/`, `brightsmile/clinic-web` is written `clinic-web/`

## Path Conventions

- API: `clinic-api/app/modules/<module>/`, tests in `clinic-api/tests/`, migrations in `clinic-api/alembic/versions/`
- Web: `clinic-web/src/`
- Feature documents: `specs/007-messaging-reminders/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Module skeletons, settings and test doubles

- [ ] T001 Create the module packages `clinic-api/app/modules/messaging/__init__.py`, `clinic-api/app/modules/channel_adapters/__init__.py`, `clinic-api/tests/messaging/__init__.py`, `clinic-api/tests/channel_adapters/__init__.py`
- [ ] T002 [P] Add messaging settings in `clinic-api/app/modules/messaging/config.py`: dispatcher cycle 30 s, claim batch 50, provider timeout 5 s, attempts 3 with waits 5 s and 30 s, breaker threshold 5 failures in 60 s with 30 s pause, `WHATSAPP_SMS_FALLBACK_ENABLED` default true, `PUBLIC_BASE_URL`, provider mode (sandbox or live); secrets (provider keys, webhook secrets) read from environment variables only
- [ ] T003 [P] Create the fake provider for tests (configurable latency, transient and permanent errors, signed delivery receipts and STOP replies, replays) in `clinic-api/tests/fakes/fake_provider.py`
- [ ] T004 [P] Create the fake clock and fake booking and identity data fixtures in `clinic-api/tests/messaging/conftest.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Message table, adapters, resilience, template guard, dispatcher and webhook skeleton that every story needs

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 [P] Write model and constraint tests (unique `dedupe_key`, one live reminder per appointment, unique `(channel, provider_message_id)`, status enum values) in `clinic-api/tests/messaging/test_message_model.py`
- [ ] T006 Create migration `clinic-api/alembic/versions/007_01_messages.py` for table `messages` exactly as in data-model.md: kind enum (`sign_in_code`, `confirmation`, `change_notice`, `reminder`), channel enum (`sms`, `whatsapp`), status enum (`queued`, `sending`, `sent`, `delivered`, `failed`, `skipped`, `cancelled`), `appointment_id` nullable (null for `sign_in_code`), `params` and `rendered_text` nullable (null for `sign_in_code`), `dedupe_key` unique, partial index on `(send_at)` where `status = 'queued'`, partial unique index on `(appointment_id)` where `kind = 'reminder'` and `status in ('queued','sending')`, index on `(created_at)` and on `(patient_account_id, status)` (depends on T005)
- [ ] T007 Implement the `Message` model and repository (claim query with `FOR UPDATE SKIP LOCKED`, forward-only status transitions, insert with `ON CONFLICT (dedupe_key) DO NOTHING`) in `clinic-api/app/modules/messaging/models.py` and `clinic-api/app/modules/messaging/repository.py` (depends on T006)
- [ ] T008 [P] Write tests for the channel port types and error mapping (transient vs permanent) in `clinic-api/tests/channel_adapters/test_base.py`
- [ ] T009 [P] Implement `ChannelPort`, `ProviderResult` and `ProviderEvent` in `clinic-api/app/modules/channel_adapters/base.py` and error classes in `clinic-api/app/modules/channel_adapters/errors.py` (depends on T008)
- [ ] T010 [P] Write tests for HMAC signature verification (valid, wrong, missing header, tampered body, constant-time compare) in `clinic-api/tests/channel_adapters/test_signature.py`
- [ ] T011 [P] Implement HMAC-SHA256 verification over the raw body in `clinic-api/app/modules/channel_adapters/signature.py` (depends on T010)
- [ ] T012 [P] Write tests for retry and circuit breaker (3 attempts with waits 5 s and 30 s, no retry on permanent error, breaker opens after 5 failures in 60 s, half-open after pause) in `clinic-api/tests/messaging/test_resilience.py`
- [ ] T013 [P] Implement retry with backoff and the per-provider circuit breaker in `clinic-api/app/modules/messaging/resilience.py` (depends on T012)
- [ ] T014 [P] Write tests for the template renderer (renders English text with IST date and time; refuses a key and channel with no configured template id or without approved status; rejects any variable outside clinic, dentist, treatment, date, time, link) in `clinic-api/tests/messaging/test_templates.py`
- [ ] T015 Create the single English catalogue with draft text for template keys `sign_in_code` (SMS only), `confirmation`, `change_cancelled`, `change_rescheduled`, `reminder` (reminder and change texts use clinic, dentist, date, time, link; confirmation adds treatment) in `clinic-api/app/modules/messaging/catalogue_en.yaml`, the id and approval-status mapping per key and channel in `clinic-api/config/message_templates.yaml`, and the renderer in `clinic-api/app/modules/messaging/templates.py` (depends on T014)
- [ ] T016 [P] Write SMS adapter tests (template id mapping, error mapping, receipt and inbound-reply parsing, signature check) in `clinic-api/tests/channel_adapters/test_sms_adapter.py`
- [ ] T017 Implement the SMS provider adapter (send with 5 s timeout, client reference = message id, parse webhook, verify signature) in `clinic-api/app/modules/channel_adapters/sms.py` (depends on T009, T011, T016)
- [ ] T018 [P] Write WhatsApp adapter tests (approved template mapping, error mapping, receipt parsing, signature check) in `clinic-api/tests/channel_adapters/test_whatsapp_adapter.py`
- [ ] T019 Implement the WhatsApp provider adapter in `clinic-api/app/modules/channel_adapters/whatsapp.py` (depends on T009, T011, T018)
- [ ] T020 [P] Define the read ports to the booking and identity modules (`get_appointment_snapshot`, `list_upcoming_booked`, `list_booked_starting_between`, account lookups) in `clinic-api/app/modules/messaging/ports.py` as in contracts/messaging-facade.md
- [ ] T021 [P] Write tests for `find_account_by_phone`, `get_reminders_enabled`, `set_reminders_enabled` in `clinic-api/tests/identity/test_reminder_preferences.py`
- [ ] T022 Implement the identity functions on the `reminders_opt_out` flag of the patient account (use the column from feature 002; add it to `clinic-api/alembic/versions/007_01_messages.py` only if feature 002 did not create it) in `clinic-api/app/modules/identity/reminder_preferences.py` (depends on T021)
- [ ] T023 [P] Write dispatcher tests (claim with two dispatchers sends once, send only when `send_at` is due, re-check skips non-booked or started appointments and opted-out accounts for reminders only, retries use the backoff, breaker open returns rows to `queued`, permanent error ends `failed`, no approved template ends `skipped` with reason `no_template`) in `clinic-api/tests/messaging/test_dispatcher.py`
- [ ] T024 Implement the dispatcher (30 s cycle, claim, re-check, render, send through the adapter, record result) in `clinic-api/app/modules/messaging/dispatcher.py` (depends on T007, T013, T015, T017, T019, T020, T022, T023)
- [ ] T025 [P] Write a log scrub test that runs the dispatcher and webhooks with a fake patient and asserts no name, phone number or message text in captured logs in `clinic-api/tests/messaging/test_no_pii_in_logs.py`
- [ ] T026 Add structured logging with ids only, metrics (`messages_total`, `provider_errors_total`, `breaker_open`, `dispatcher_last_cycle_timestamp`) and OpenTelemetry spans for dispatch and webhooks in `clinic-api/app/modules/messaging/metrics.py` (depends on T025)
- [ ] T027 [P] Write webhook security tests (unsigned or wrongly signed request returns 401 and changes nothing, valid unknown message id returns 200 and is ignored, bad JSON returns 400, no cookie session or CSRF header needed) in `clinic-api/tests/messaging/test_webhooks_security.py`
- [ ] T028 Implement the webhook router `POST /api/webhooks/sms` and `POST /api/webhooks/whatsapp` (verify signature, parse through the adapter, hand events to registered handlers, answer quickly) in `clinic-api/app/modules/messaging/webhooks.py` (depends on T017, T019, T026, T027)
- [ ] T029 Start the dispatcher with the application and report its last cycle time in `GET /health` in `clinic-api/app/main.py` (depends on T024, T026, T028)

**Checkpoint**: Foundation ready - a queued row inserted by a test is sent through the fake provider; stories can start

---

## Phase 3: User Story 1 - Patient gets a confirmation when booking or changing (Priority: P1) 🎯 MVP

**Goal**: Every saved booking has its confirmation queued in the same transaction and sent in the chosen channel; cancel and reschedule send a change notice.

**Independent Test**: Book, cancel and reschedule against the fake provider for SMS and WhatsApp; check one message each with the required content and that a rolled-back booking leaves no message.

### Tests for User Story 1

- [ ] T030 [P] [US1] Write tests that the confirmation and change notice rows are created in the caller's transaction with the six confirmation items, in the appointment's channel, with a unique `dedupe_key` (repeat call creates nothing), and that a rollback leaves no row, in `clinic-api/tests/messaging/test_confirmation.py`
- [ ] T031 [P] [US1] Write a contract test of the facade functions in contracts/messaging-facade.md (`on_booking_created`, `on_appointment_cancelled`, `on_appointment_rescheduled`) in `clinic-api/tests/contract/test_messaging_facade_contract.py`

### Implementation for User Story 1

- [ ] T032 [US1] Build the template parameters (clinic, dentist, treatment, date and time in IST, link `PUBLIC_BASE_URL/appointments/<id>` with no personal data in the link) in `clinic-api/app/modules/messaging/params.py` (depends on T020)
- [ ] T033 [US1] Implement `create_confirmation` and `create_change_notice` in `clinic-api/app/modules/messaging/confirmations.py` (depends on T007, T030, T032)
- [ ] T034 [US1] Implement the facade `on_booking_created`, `on_appointment_cancelled` and `on_appointment_rescheduled` (confirmation and change-notice parts) in `clinic-api/app/modules/messaging/service.py` (depends on T031, T033)
- [ ] T035 [US1] Write and pass an end-to-end test: booking commit, dispatcher cycle, fake provider receives the confirmation within 30 s for SMS and WhatsApp, and the provider-down case sends it after recovery, in `clinic-api/tests/messaging/test_confirmation_dispatch.py` (depends on T024, T034)

**Checkpoint**: User Story 1 works on its own

---

## Phase 4: User Story 2 - Patient gets a reminder 24 hours before, never at night (Priority: P1)

**Goal**: A reminder row with the quiet-hours-adjusted send time exists for every appointment booked 24 hours or more ahead and is sent with clinic, dentist, date, time and a reschedule or cancel link.

**Independent Test**: With the fake clock, create appointments due in daytime, 21:00-24:00 and 00:00-08:00, and bookings made near the due time; check send times and content.

### Tests for User Story 2

- [ ] T036 [P] [US2] Write table tests for `compute_schedule(start_at, now)` covering the spec cases: due 11:00, 22:30, 03:00, 08:00 (sent at 08:00), 21:00 (sent at 20:00), booked Mon 20:30 for Tue 22:00 (at once), booked Mon 21:15 for Tue 22:00 (Tue 08:00), exactly 24 h ahead (reminder created), under 24 h (none), IST in `clinic-api/tests/messaging/test_timing.py`
- [ ] T037 [P] [US2] Write tests that exactly one reminder row is created per eligible appointment in the appointment's channel with params clinic, dentist, date, time and link, in `clinic-api/tests/messaging/test_reminder_creation.py`

### Implementation for User Story 2

- [ ] T038 [US2] Implement the pure function `compute_schedule` (zoneinfo Asia/Kolkata; quiet hours 21:00-08:00; rules FR-005, FR-006, FR-010) in `clinic-api/app/modules/messaging/timing.py` (depends on T036)
- [ ] T039 [US2] Implement `create_reminder` (dedupe key `reminder:<appointment_id>:<start_at>`, `due_at` and `send_at` from `compute_schedule`) in `clinic-api/app/modules/messaging/reminders.py` (depends on T032, T037, T038, T007)
- [ ] T040 [US2] Call `create_reminder` from `on_booking_created` and `on_appointment_rescheduled` in `clinic-api/app/modules/messaging/service.py` (depends on T034, T039)
- [ ] T041 [US2] Write and pass the dispatch test with the fake clock showing each reminder sent at its adjusted time in the chosen channel and not before, in `clinic-api/tests/messaging/test_reminder_dispatch.py` (depends on T024, T040)

**Checkpoint**: Reminders are scheduled and sent on time

---

## Phase 5: User Story 3 - No wrong reminders: cancelled, rescheduled and short-notice appointments (Priority: P1)

**Goal**: No reminder for cancelled appointments, one reminder for a rescheduled appointment's new time, none for bookings under 24 hours ahead.

**Independent Test**: Cancel, reschedule and short-notice-book around due times with the fake clock; check what is sent.

### Tests for User Story 3

- [ ] T042 [P] [US3] Write tests for cancel before and at due time (queued row `cancelled`, race with the send-time re-check gives `skipped`), reschedule at least 24 h away (old `cancelled`, exactly one live reminder), reschedule under 24 h (none), reschedule after the reminder was sent (new reminder), short-notice booking (none), in `clinic-api/tests/messaging/test_reminder_suppression.py`

### Implementation for User Story 3

- [ ] T043 [US3] Implement `cancel_live_reminders` (queued and sending-not-yet-sent rows of the appointment set to `cancelled`) in `clinic-api/app/modules/messaging/reminders.py` (depends on T039, T042)
- [ ] T044 [US3] Call `cancel_live_reminders` from `on_appointment_cancelled` and `on_appointment_rescheduled` before new rows are created in `clinic-api/app/modules/messaging/service.py` (depends on T040, T043)
- [ ] T045 [US3] Verify the dispatcher re-check against T042 (status booked, start in the future, reason codes `appointment_not_booked` and `start_passed`) and fix gaps in `clinic-api/app/modules/messaging/dispatcher.py` (depends on T024, T042)

**Checkpoint**: Stories 1-3 together give correct reminders

---

## Phase 6: User Story 4 - Patient or reception can stop reminders (Priority: P1)

**Goal**: A signed STOP reply or a reception action switches reminders off at once; confirmations, change notices and sign-in codes still go out; reception can switch them back on.

**Independent Test**: Post a signed STOP from a test number, check queued reminders are skipped and a new booking is confirmed; repeat through the reception route.

### Tests for User Story 4

- [ ] T046 [P] [US4] Write STOP tests (signed STOP case-insensitive and trimmed from a known number sets the flag, other text ignored, unknown number ignored, unsigned rejected, queued reminder skipped, confirmation and change notice still sent, effective before the next send) in `clinic-api/tests/messaging/test_stop.py`
- [ ] T047 [P] [US4] Write route tests for `PUT /api/patient-accounts/{accountId}/reminders` (reception and manager allowed, patient and dentist get 403, unknown account 404, switching on re-creates reminders for future appointments 24 h or more away) in `clinic-api/tests/identity/test_reminders_route.py`

### Implementation for User Story 4

- [ ] T048 [US4] Implement the STOP handler (inbound text equals STOP, find account by phone, `set_reminders_enabled(false)`, log ids only) and register it for SMS inbound events in `clinic-api/app/modules/messaging/stop_handler.py` (depends on T022, T028, T046)
- [ ] T049 [US4] Implement the reminders switch route with role and clinic checks through the access context in `clinic-api/app/modules/identity/routes_reminders.py` (depends on T022, T047)
- [ ] T050 [US4] Implement `ensure_reminders` (create missing reminders for booked appointments 24 h or more away whose account has not opted out) and `reinstate_reminders` (calls it for one account through `list_upcoming_booked`) in `clinic-api/app/modules/messaging/reminders.py`, expose `reinstate_reminders` on the facade in `clinic-api/app/modules/messaging/service.py`, and call it from the route in `clinic-api/app/modules/identity/routes_reminders.py` (depends on T020, T039, T044, T049)
- [ ] T051 [P] [US4] Write component tests for the reminders switch (shows state, confirms, calls the API, shows error) in `clinic-web/src/components/reception/RemindersToggle.test.tsx`
- [ ] T052 [US4] Implement `RemindersToggle` and the API client function `setRemindersEnabled` in `clinic-web/src/components/reception/RemindersToggle.tsx` and `clinic-web/src/api/messagingApi.ts`; it is placed in the reception patient panel built by feature 006 (depends on T051)

**Checkpoint**: STOP and reception switch work

---

## Phase 7: User Story 5 - Reminders are on time and compliant, even when a provider has problems (Priority: P1)

**Goal**: 99% of reminders within 15 minutes of the adjusted time; no duplicates; lag alert; nightly reconciliation; template-only sending; 90-day retention.

**Independent Test**: Run the simulated day against a slow, failing and replaying fake provider.

### Tests for User Story 5

- [ ] T053 [P] [US5] Write receipt tests (delivered and failed receipts update status, replay changes nothing, failed after delivered ignored, unknown id ignored) in `clinic-api/tests/messaging/test_receipts.py`
- [ ] T054 [P] [US5] Write nightly job and retention tests (stuck `sending` rows older than 10 minutes return to `queued`, queued reminders of non-booked appointments cancelled, missing reminders created for booked appointments 24 h or more away and not opted out, messages older than 90 days deleted, `purge_account_messages` deletes an account's messages, counts reported, only one replica runs) in `clinic-api/tests/messaging/test_nightly_job.py`
- [ ] T055 [P] [US5] Write tests for the lag gauge (age of the oldest due unsent row; over 10 minutes marks the alert condition) in `clinic-api/tests/messaging/test_lag_metric.py`
- [ ] T056 [P] [US5] Write compliance tests (every send call used an approved template id of the right channel, provider call carries only the phone number and the allowed parameters, nothing sent without a template) in `clinic-api/tests/messaging/test_compliance.py`

### Implementation for User Story 5

- [ ] T057 [US5] Implement receipt handling (match by provider message id, forward-only status, idempotent) and register it for SMS and WhatsApp events in `clinic-api/app/modules/messaging/receipts.py` (depends on T028, T053)
- [ ] T058 [US5] Implement retention (`delete_older_than(90 days)` and `purge_account_messages`) in `clinic-api/app/modules/messaging/retention.py` (depends on T007, T054)
- [ ] T059 [US5] Implement the nightly reconciliation job JOB-005 at 03:00 IST guarded by a database advisory lock, using `ensure_reminders` from `clinic-api/app/modules/messaging/reminders.py`, and schedule it with the app in `clinic-api/app/modules/messaging/jobs.py` and `clinic-api/app/main.py` (depends on T029, T050, T054, T058)
- [ ] T060 [US5] Add the `reminder_lag_seconds` gauge to `clinic-api/app/modules/messaging/metrics.py` and the alert rule for lag over 10 minutes in `clinic-api/ops/alerts/messaging-alerts.yaml` (depends on T026, T055)
- [ ] T061 [US5] Write and pass the simulated-day timeliness test (at least 99% of reminders sent within 15 minutes of `send_at` with slow and failing provider periods, none for cancelled appointments) in `clinic-api/tests/messaging/test_timeliness_simulation.py` (depends on T041, T044, T060)

**Checkpoint**: Reliability and compliance targets are testable

---

## Phase 8: User Story 6 - Provider accounts and templates are registered and ready before go-live (Priority: P1)

**Goal**: Templates written and submitted early; sandbox accounts in staging; a readiness check tells whether go-live is blocked. Start this phase on day 1: it has long external lead times (RSK-001) and only the code tasks depend on earlier phases.

**Independent Test**: The readiness check lists unapproved templates; staging sends only to sandbox accounts.

### Tests for User Story 6

- [ ] T062 [P] [US6] Write readiness tests (lists templates not approved or without id, passes when all approved, exit code non-zero when blocked) in `clinic-api/tests/messaging/test_readiness.py`
- [ ] T063 [P] [US6] Write tests that staging configuration refuses live provider mode and that sandbox template ids are used in staging, in `clinic-api/tests/messaging/test_sandbox_guard.py`

### Implementation for User Story 6

- [ ] T064 [P] [US6] Write the template catalogue document (one English text per kind and channel, allowed variables, SMS text in DLT format, WhatsApp category, who submits) in `clinic-api/docs/messaging/template-catalogue.md`
- [ ] T065 [P] [US6] Create the onboarding tracker (provider selection, SMS provider and WhatsApp provider accounts, DLT entity, sender ID and template registration, WhatsApp template approval, sandbox accounts in weeks 1-2; owner clinic or us, submission date, status; ASM-009 checks: delivery-receipt webhook, inbound reply forwarding, client reference support, variable length limits) in `clinic-api/docs/messaging/onboarding-tracker.md`
- [ ] T066 [US6] Implement the go-live readiness check as `python -m app.modules.messaging.readiness` in `clinic-api/app/modules/messaging/readiness.py` (depends on T015, T062)
- [ ] T067 [US6] Implement the sandbox guard and the staging template mapping in `clinic-api/app/modules/messaging/config.py` and `clinic-api/config/message_templates.staging.yaml` (depends on T002, T063)
- [ ] T068 [US6] Capture real sandbox payloads (receipts, STOP reply, error responses) as fixtures and align the two adapters once the providers are chosen, in `clinic-api/tests/fixtures/providers/` and `clinic-api/app/modules/channel_adapters/sms.py`, `clinic-api/app/modules/channel_adapters/whatsapp.py` (depends on T017, T019, T065)

**Checkpoint**: Go-live blockers are visible and tracked

---

## Phase 9: User Story 7 - Sign-in code is sent by SMS straight away (Priority: P1)

**Goal**: Feature 002 can send the SMS sign-in code during the request and learn the result at once.

**Independent Test**: Call `send_sign_in_code` against the fake provider up and down.

### Tests for User Story 7

- [ ] T069 [P] [US7] Write tests for `send_sign_in_code` (accepted result, provider down returns `failed` within the 5 s timeout and nothing queued, breaker open returns `failed` at once, not stopped by the reminders-off flag, row has no code and no text, code absent from logs) and a contract test of the signature in contracts/messaging-facade.md in `clinic-api/tests/messaging/test_sign_in_code.py`

### Implementation for User Story 7

- [ ] T070 [US7] Implement `send_sign_in_code(phone_e164, code) -> SendResult` (one attempt, 5 s timeout, shared SMS breaker, row with status and provider id only) in `clinic-api/app/modules/messaging/sign_in_code.py` (depends on T007, T013, T015, T017, T069)

**Checkpoint**: MVP stories 1-7 complete; MVP can ship without Phase 10 and Phase 11

---

## Phase 10: User Story 8 - Undelivered WhatsApp reminder is sent once by SMS (Release 2) (Priority: P2)

**Goal**: Behind the switch (default on), a failed WhatsApp reminder is sent once by SMS; if that fails, the appointment is marked "reminder failed".

**Independent Test**: Fail WhatsApp then SMS in the fake provider with the switch on and off.

### Tests for User Story 8

- [ ] T071 [P] [US8] Write fallback tests (WhatsApp final failure or failed receipt creates one SMS, replayed receipt creates no second, SMS failure sets `reminder_failed_at` on the original reminder, switch off marks failed at once, SMS-chosen reminder failure marks failed, fallback skipped after STOP or cancel, delivered WhatsApp creates none) in `clinic-api/tests/messaging/test_fallback.py`

### Implementation for User Story 8

- [ ] T072 [US8] Create expand-only migration `clinic-api/alembic/versions/007_02_reminder_fallback.py` adding `original_message_id` (uuid, nullable, FK to `messages.id`, unique) and `reminder_failed_at` (timestamptz, nullable) and the partial index on `(reminder_failed_at)` where not null, and exclude rows with `original_message_id` set from the live-reminder partial unique index (depends on T006)
- [ ] T073 [US8] Add the two columns to the `Message` model in `clinic-api/app/modules/messaging/models.py` (depends on T007, T072)
- [ ] T074 [US8] Implement the fallback (`INSERT ... ON CONFLICT (original_message_id) DO NOTHING`, switch read at failure time, set `reminder_failed_at` on the root reminder when no permitted channel remains) in `clinic-api/app/modules/messaging/fallback.py` (depends on T024, T071, T073)
- [ ] T075 [US8] Call the fallback from the dispatcher on final failure and from receipt handling on a failed receipt in `clinic-api/app/modules/messaging/dispatcher.py` and `clinic-api/app/modules/messaging/receipts.py` (depends on T057, T074)

**Checkpoint**: Release 2 fallback works and can be switched off by configuration

---

## Phase 11: User Story 9 - Reception sees tomorrow's failed reminders (Release 2) (Priority: P2)

**Goal**: The "Reminders failed" screen lists tomorrow's appointments, at the receptionist's clinic, whose reminder failed.

**Independent Test**: Seed tomorrow's appointments in several states at two clinics and open the list as receptionist and manager.

### Tests for User Story 9

- [ ] T076 [P] [US9] Write tests for the list (tomorrow in IST only, status booked only, own clinic only for receptionist, both clinics for manager, delivered, queued and never-reminded excluded, 404 when the flag is off, 403 for other roles, response fields as in contracts/messaging-api.openapi.yaml) in `clinic-api/tests/reception/test_reminders_failed.py`
- [ ] T079 [P] [US9] Write component tests for the screen (list, empty state, error state, hidden when flag off) in `clinic-web/src/pages/reception/RemindersFailedPage.test.tsx`

### Implementation for User Story 9

- [ ] T077 [US9] Implement the list query and `GET /api/reception/reminders-failed` behind the flag `r2_reminders_failed` in `clinic-api/app/modules/reception/reminders_failed.py` (depends on T020, T073, T076)
- [ ] T078 [P] [US9] Add the flag `r2_reminders_failed` (default off) in `clinic-web/src/config/flags.ts`
- [ ] T080 [US9] Add `listRemindersFailed` to the API client in `clinic-web/src/api/messagingApi.ts` (depends on T052, T077)
- [ ] T081 [US9] Implement the "Reminders failed" screen and its route in `clinic-web/src/pages/reception/RemindersFailedPage.tsx` and `clinic-web/src/routes.tsx` (depends on T078, T079, T080)

**Checkpoint**: Release 2 complete

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: Contracts, documentation, security review and end-to-end validation

- [ ] T082 [P] Write the contract test of the webhook, reminders switch and reception list operations against `specs/007-messaging-reminders/contracts/messaging-api.openapi.yaml` in `clinic-api/tests/contract/test_messaging_contract.py` (depends on T028, T049, T077)
- [ ] T083 Merge the messaging operations into `clinic-api/contracts/clinic-api-v1.openapi.yaml` (depends on T082)
- [ ] T084 [P] Write the runbook (lag alert, breaker open, provider outage, fallback switch, STOP handling, edge rate limit required for both webhook paths, secrets rotation) in `clinic-api/docs/messaging/runbook.md`
- [ ] T085 Record the security review of the webhook endpoints, the reminders switch and the reception list (signature, no session, rate limit, PII handling, role checks) in `clinic-api/docs/messaging/security-review.md` (depends on T028, T049, T077)
- [ ] T086 Write the staging smoke test (book and cancel against the sandbox providers, confirmation and change notice arrive, reminder row created) in `clinic-api/tests/e2e/test_messaging_smoke.py` (depends on T035, T067, T070)
- [ ] T087 Run the validation scenarios in `specs/007-messaging-reminders/quickstart.md` and record the result in the same file (depends on T061, T075, T081, T086)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: depends on Setup; blocks Stories 1-5, 7, 8, 9.
- **User Story 6 (Phase 8)**: documentation tasks T064 and T065 have no code dependencies and should start on day 1, in parallel with everything; T066 and T067 need Phase 2.
- **Stories 1-5 and 7**: after Phase 2. Story 2 builds on `service.py` from Story 1; Story 3 on Story 2; Story 5 timeliness test needs Stories 2 and 3; Story 4 needs `reminders.py` from Story 2.
- **Stories 8 and 9 (Release 2)**: after Phase 2 and Story 5's receipts (T057); Story 9 needs Story 8's migration (T072, T073).
- **Polish**: after the stories it checks.

### User Story Dependencies

- US1: after Phase 2.
- US2: after US1 (shares `service.py`).
- US3: after US2.
- US4: after US2 (`reminders.py`), and Phase 2 (`webhooks.py`, identity functions).
- US5: receipts and lag after Phase 2; nightly job after US4's `reinstate_reminders`.
- US6: documentation any time; code after Phase 2.
- US7: after Phase 2 only.
- US8 (R2): after Phase 2 and US5 receipts.
- US9 (R2): after US8 migration and model.

### Within Each Story

- Tests first and failing, then models, services, endpoints, integration.

### Parallel Opportunities

- T002, T003, T004; T005, T008, T010, T012, T014, T016, T018, T020, T021 in Phase 2.
- Day-1 parallel track: T064, T065 (provider and template work with the clinic).
- After Phase 2: US1, US6 code and US7 can run in parallel by different developers; US8 and US9 after the MVP stories.

## Parallel Example: Foundational phase

```text
Task: "Write tests for the channel port types in clinic-api/tests/channel_adapters/test_base.py"
Task: "Write tests for HMAC signature verification in clinic-api/tests/channel_adapters/test_signature.py"
Task: "Write tests for retry and circuit breaker in clinic-api/tests/messaging/test_resilience.py"
Task: "Write tests for the template renderer in clinic-api/tests/messaging/test_templates.py"
```

## Implementation Strategy

### MVP First

1. Start T064 and T065 (templates and provider onboarding) immediately; they carry the external risk RSK-001.
2. Phases 1 and 2.
3. US1 (confirmation), then US2 and US3 (reminders), then US4 (STOP), US5 (reliability), US7 (sign-in code; unblocks feature 002 early if staffed in parallel right after Phase 2).
4. Validate with quickstart section 1 and ship the MVP on 1 March 2027.

### Release 2

1. US8 (fallback, switch default on), then US9 (list), hidden behind `r2_reminders_failed` until ready, about 2-3 weeks after go-live.

## Notes

- The P marker: tasks touch different files and have no unfinished dependency.
- Every task names its files; shared files (`service.py`, `reminders.py`, `dispatcher.py`, `messaging/config.py`, `messagingApi.ts`, `main.py`) are edited by several tasks only through explicit dependencies.
- Never log patient names, phone numbers or message text.
- Verify tests fail before implementing.
