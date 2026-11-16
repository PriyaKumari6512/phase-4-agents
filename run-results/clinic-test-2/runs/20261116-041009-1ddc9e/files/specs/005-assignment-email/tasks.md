# Tasks: Assignment email notification

**Input**: Design documents from `specs/005-assignment-email/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included (constitution principle I: tests first for business logic). Write each story's tests first and see them fail.

**Organization**: Tasks are grouped by user story. Repository `acme/taskflow-api` unless the path says `acme/taskflow-infra`. Source ids: FR-5, US-5 (goal G2).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story the task belongs to (US1, US2, US3)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Settings and package skeleton for the notify-worker.

- [ ] T001 [P] Add settings `EMAIL_PROVIDER_API_KEY`, `EMAIL_PROVIDER_BASE_URL`, `EMAIL_FROM_ADDRESS`, `WEB_BASE_URL`, `NOTIFY_POLL_INTERVAL_SECONDS` (default 5), `NOTIFY_MAX_ATTEMPTS` (default 6), `NOTIFY_CLAIM_TIMEOUT_SECONDS` (default 120), all read from environment, to `app/core/config.py`
- [ ] T002 [P] Create the package skeleton `app/worker/__init__.py`, `app/worker/jobs/__init__.py`, `app/worker/templates/__init__.py`, `tests/worker/__init__.py`, `tests/fakes/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Outbox table, email provider client, outbox service, worker entrypoint and secret wiring shared by all stories (and reused by F04, F06, F07).

**CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T003 Create Alembic migration `migrations/versions/005_notification_outbox.py` for table `notification_outbox` exactly as in data-model.md (columns id, kind, dedupe_key UNIQUE NOT NULL, recipient_user_id FK users(id), payload JSONB, status one of pending|sending|sent|failed|skipped default pending, attempts default 0, next_attempt_at, claimed_at, last_error max 500 characters, provider_message_id, created_at, sent_at; index on (status, next_attempt_at))
- [ ] T004 Create the `NotificationOutbox` model in `app/models/notification_outbox.py` and export it in `app/models/__init__.py` (depends on T003)
- [ ] T005 [P] Implement the provider-agnostic `EmailClient`, `EmailMessage`, `SendResult`, `TransientEmailError`, `PermanentEmailError` per contracts/email-provider-client.md in `app/services/email_client.py` (10 s timeout, never logs key or body) (depends on T001)
- [ ] T006 [P] Create `FakeEmailClient` (records messages, can fail transiently or permanently on demand) in `tests/fakes/fake_email_client.py` (depends on T005)
- [ ] T007 Implement `enqueue_assignment_notification`, `claim_due`, `mark_sent`, `mark_retry`, `mark_failed`, `mark_skipped` per contracts/outbox-enqueue.md in `app/services/notification_outbox.py` (depends on T004)
- [ ] T008 Create the notify-worker entrypoint `app/worker/main.py` (`python -m app.worker.main`: load settings, poll loop every `NOTIFY_POLL_INTERVAL_SECONDS`, graceful stop on SIGTERM) (depends on T001)
- [ ] T009 [P] Wire the email provider key into the worker pod in acme/taskflow-infra: create `k8s/notify-worker/external-secret.yaml` (ExternalSecret reading the provider key from AWS Secrets Manager through the store owned by 001-platform-foundation) and set the env var `EMAIL_PROVIDER_API_KEY` plus the container command `python -m app.worker.main` in `k8s/notify-worker/deployment.yaml` (deployment owned by 001-platform-foundation)

**Checkpoint**: Foundation ready.

---

## Phase 3: User Story 1 - Assignee is emailed when a task is assigned (Priority: P1) 🎯 MVP

**Goal**: An assignee gets one email with task details within 1 minute of an assignment. (source: US-5, FR-5)

**Independent Test**: Assign a task with the fake email client; exactly one email to the assignee is sent in under 60 s.

### Tests for User Story 1

- [ ] T010 [P] [US1] Integration test that assigning a task (on create and on reassignment) writes one `assignment_email` outbox row in the same transaction, none when the assignee is unchanged, and one for self-assignment, in `tests/integration/test_assignment_enqueue.py`
- [ ] T011 [P] [US1] Unit test of the email content (title, board, assigner, due date, link, HTML escaping, no line breaks in subject) in `tests/worker/test_assignment_email_template.py`
- [ ] T012 [P] [US1] Unit test of the send job with `FakeEmailClient` (one message to the assignee only, outbox row becomes `sent` with provider_message_id) in `tests/worker/test_send_assignment_email.py`

### Implementation for User Story 1

- [ ] T013 [US1] Implement subject and body rendering per contracts/assignment-email.md in `app/worker/templates/assignment_email.py` (depends on T011)
- [ ] T014 [US1] Implement the job that loads task, board, assignee and assigner, renders the email and calls `EmailClient` in `app/worker/jobs/send_assignment_email.py` (depends on T013)
- [ ] T015 [US1] Implement the dispatcher that claims due outbox rows and calls the job by `kind`, marking `sent` on success, in `app/worker/outbox_dispatcher.py` (depends on T014)
- [ ] T016 [US1] Run the dispatcher from the poll loop in `app/worker/main.py` (depends on T015)
- [ ] T017 [US1] Call `enqueue_assignment_notification` with a new `assignment_event_id` inside the task create and assignee-change transaction in `app/services/tasks.py` (file owned by 002-tasks-board; coordinate) (depends on T007)
- [ ] T018 [US1] Latency test: assignment saved to email handed to the client takes under 60 s with a 5 s poll interval, in `tests/worker/test_assignment_latency.py` (depends on T016)

**Checkpoint**: Assignment emails work end to end.

---

## Phase 4: User Story 2 - One email per assignment, none lost (Priority: P1)

**Goal**: No duplicates and no silent losses under repeats, concurrency, restarts and provider failures. (source: US-5, FR-5, G2)

**Independent Test**: Duplicate enqueue, two concurrent workers, a crash mid-send and a flaky provider all end with exactly one email per assignment.

### Tests for User Story 2

- [ ] T019 [P] [US2] Test that enqueueing the same assignment event twice yields one row and returns False the second time in `tests/services/test_notification_outbox_idempotency.py`
- [ ] T020 [P] [US2] Test that two dispatchers running concurrently on PostgreSQL send each notification once in `tests/worker/test_outbox_concurrency.py`
- [ ] T021 [P] [US2] Test retry with backoff (5 s, 15 s, 60 s, 5 min, 15 min), maximum 6 attempts, and permanent error going straight to `failed` in `tests/worker/test_outbox_retry.py`
- [ ] T022 [P] [US2] Test that a row left in `sending` longer than `NOTIFY_CLAIM_TIMEOUT_SECONDS` is reclaimed and sent once, and that emails queued while the worker was stopped are sent on restart, in `tests/worker/test_crash_recovery.py`
- [ ] T023 [P] [US2] Test that a deleted task or an assignee without a usable email address ends as `skipped` with a reason and sends nothing in `tests/worker/test_send_skip.py`

### Implementation for User Story 2

- [ ] T024 [US2] Make enqueue insert-on-conflict-do-nothing on `dedupe_key` and return whether a row was inserted in `app/services/notification_outbox.py` (depends on T019)
- [ ] T025 [US2] Make `claim_due` use `FOR UPDATE SKIP LOCKED`, set `sending` and `claimed_at`, and reclaim stale `sending` rows (counting an attempt) in `app/services/notification_outbox.py` (depends on T024)
- [ ] T026 [US2] Implement transient-error rescheduling with the backoff list, maximum attempts and `failed` with `last_error` (truncated to 500 characters, no key, no body) in `app/worker/outbox_dispatcher.py` (depends on T015, T021)
- [ ] T027 [US2] Classify provider responses (timeout, connection error, 429, 5xx as transient; other 4xx as permanent) and pass `dedupe_key` as the provider idempotency key when supported in `app/services/email_client.py` (depends on T005)
- [ ] T028 [US2] Implement skip rules (task deleted, no usable assignee address) in `app/worker/jobs/send_assignment_email.py` (depends on T014, T023)

**Checkpoint**: Delivery is effectively once and nothing is lost.

---

## Phase 5: User Story 3 - Operators can see delivery health and failures (Priority: P2)

**Goal**: Logs, metrics, health check and alerts for assignment email delivery. (source: US-5, FR-5, G2)

**Independent Test**: With failing provider calls and delayed processing, metrics, logs and the alert condition show the problem; no secret or body appears.

### Tests for User Story 3

- [ ] T029 [P] [US3] Test that outcomes (sent, retry, failed, skipped), the assignment-to-send duration and the oldest-pending-age metric are emitted and that logs contain no key or email body in `tests/worker/test_telemetry.py`

### Implementation for User Story 3

- [ ] T030 [US3] Implement structured logging, OpenTelemetry metrics (`notify_outcome_total`, `notify_send_latency_seconds`, `notify_oldest_pending_age_seconds`) and traces in `app/worker/telemetry.py` (depends on T029)
- [ ] T031 [US3] Instrument the dispatcher with the telemetry module in `app/worker/outbox_dispatcher.py` (depends on T026, T030)
- [ ] T032 [P] [US3] Implement the heartbeat file updated on each poll loop in `app/worker/health.py` and call it from `app/worker/main.py` (depends on T008)
- [ ] T033 [P] [US3] Add a liveness exec probe on the heartbeat age to `k8s/notify-worker/deployment.yaml` in acme/taskflow-infra (depends on T032)
- [ ] T034 [P] [US3] Add alert rules (oldest pending notification older than 45 s, any `failed` notification, send error rate) for the observability stack owned by 001-platform-foundation in `terraform/observability/notify-worker-alerts.tf` in acme/taskflow-infra (depends on T030)
- [ ] T035 [P] [US3] Write the operator runbook (reading `notification_outbox` states, requeueing a `failed` row, provider outage handling) in `docs/runbooks/notify-worker.md`

**Checkpoint**: Delivery health is visible and alerting.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T036 [P] Test that the provider key and email bodies never appear in worker logs or error messages in `tests/worker/test_no_secret_logging.py`
- [ ] T037 [P] Document the outbox, client and worker for reuse by F04, F06 and F07, the retry policy and the assumptions Q1 to Q3 in `docs/notifications.md`
- [ ] T038 Run the quickstart validation on dev and record the result in `specs/005-assignment-email/quickstart.md`

---

## Dependencies & Execution Order

- Setup (Phase 1) has no dependencies. Foundational (Phase 2) depends on Setup and blocks all stories.
- US1 and US2 depend on Foundational; US2 builds on the dispatcher from US1 (T015) for T026. US3 depends on the dispatcher (T015, T025/T026 for T031).
- External: T017 needs the assignment path of 002-tasks-board; T009, T033, T034 need the cluster, External Secrets store and observability stack of 001-platform-foundation.
- Polish depends on all stories.

## Parallel Example

- Phase 3 tests T010, T011 and T012 can be written together.
- Phase 4 tests T019 to T023 can be written together.
- T033, T034 and T035 are independent files.

## Implementation Strategy

1. MVP: Phases 1 to 3 give working assignment emails.
2. Add Phase 4 before enabling in prod (duplicates and loss protection).
3. Add Phase 5 for production monitoring, then Phase 6.
