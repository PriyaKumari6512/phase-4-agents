# Tasks: Daily due-tomorrow digest

**Input**: Design documents from `/specs/006-daily-digest/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/timezone-api.md

**Tests**: Included, because the constitution requires tests first for business logic. Write each test first and see it fail.

**Organization**: Tasks are grouped by user story. Repositories: `acme/taskflow-api` (paths starting `app/`, `migrations/`, `tests/`), `acme/taskflow-web` (paths starting `src/`), `acme/taskflow-infra` (paths starting `k8s/`). Paths marked (A) are assumptions from the implementation contract.

**Reuse**: The email client and worker skeleton (`app/worker/`) belong to feature 005; users, boards, membership and tasks belong to features 001 and 002. Do not recreate them.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Feature flag and test fixture.

- [ ] T001 Add the `FEATURE_DIGEST` flag (read from env `FEATURE_DIGEST`, default off) to the settings in app/core/config.py
- [ ] T002 [P] Add a recording fake of the feature-005 email client and a controllable clock fixture in tests/conftest.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema shared by all stories.

**CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T003 Create the Alembic migration migrations/versions/006_user_timezone_digest_deliveries.py adding `users.timezone` (text, nullable, "IANA zone name, max length 64") and table `digest_deliveries` with unique `(user_id, local_date)` and index `(local_date, status)` per data-model.md
- [ ] T004 [P] Add the nullable `timezone` column to the User model in app/models/user.py (depends on T003)
- [ ] T005 [P] Create the DigestDelivery model in app/models/digest_delivery.py with fields id, user_id, local_date, status ("one of claimed, sent, failed"), attempts ("default 1, maximum 3"), task_count, claimed_at, sent_at, last_error (depends on T003)

**Checkpoint**: Schema ready; user stories can begin.

---

## Phase 3: User Story 1 - Receive a daily digest of tasks due tomorrow (Priority: P1) 🎯 MVP

**Goal**: A user with open tasks due tomorrow gets one email at or after 08:00 local time listing them; users with none get nothing.

**Independent Test**: With a user in `Europe/Berlin` and two open tasks due tomorrow, run the job at 08:00 Berlin time and verify one email listing both tasks (quickstart steps 2, 3, 5, 9).

### Tests for User Story 1

- [ ] T006 [P] [US1] Integration test for the due-tomorrow query (open only, assignee only, member boards only, cap 50 with "more" count) in tests/integration/test_digest_query.py
- [ ] T007 [P] [US1] Unit test for email composition (grouped by board, title, board, due date, "+N more" line, no email when empty) in tests/unit/test_digest_email.py
- [ ] T008 [P] [US1] Integration test for the job: one email at 08:00 local, none before, none without tasks, none with the flag off, skip when preferences turn the digest off, in tests/integration/test_daily_digest_job.py

### Implementation for User Story 1

- [ ] T009 [P] [US1] Implement local-time helpers in app/services/digest_schedule.py: local now from a UTC instant and an IANA zone, UTC fallback for NULL, "due" test `local time >= 08:00`, tomorrow as local date plus one calendar day
- [ ] T010 [P] [US1] Implement the users-and-tasks query in app/services/digest_query.py joining tasks, boards and board membership, status not Done, due date equal to tomorrow, ordered by board name then title, limit 50 (depends on T004)
- [ ] T011 [P] [US1] Implement digest subject and text body rendering in app/services/digest_email.py
- [ ] T012 [P] [US1] Implement `digest_allowed(user_id)` in app/services/digest_preferences.py: True when `FEATURE_NOTIFICATION_PREFS` is off or the preferences service of feature 007 is absent, otherwise ask the preferences service
- [ ] T013 [US1] Implement the digest job in app/worker/jobs/daily_digest.py: exit when `FEATURE_DIGEST` is off, evaluate every user, send through the feature-005 email client when due, allowed and tasks exist; register it in the worker entry point of feature 005 (depends on T009, T010, T011, T012)
- [ ] T014 [US1] Add structured logs, metrics (evaluated, sent, skipped, failed) and a trace span for each run, and a last-successful-run health signal for the CronJob, in app/worker/jobs/daily_digest.py (depends on T013)
- [ ] T015 [P] [US1] Add the CronJob manifest running the notify-worker image with the digest command every 5 minutes, `concurrencyPolicy: Forbid`, secrets via External Secrets, in k8s/notify-worker/digest-cronjob.yaml

**Checkpoint**: User Story 1 works and is testable on its own (time zone set directly in the database).

---

## Phase 4: User Story 2 - Capture and change my time zone (Priority: P1)

**Goal**: A user can view and set their IANA time zone; invalid values are rejected.

**Independent Test**: Set `Asia/Kolkata` via the settings screen or API, read it back; `Nowhere/City` returns 422 (quickstart step 8).

### Tests for User Story 2

- [ ] T016 [P] [US2] Contract test for GET and PUT `/api/v1/users/me/timezone` (200, 401, 422, own profile only) in tests/contract/test_timezone_api.py
- [ ] T021 [P] [US2] Component test for the time zone control (browser zone pre-selected, save, error shown, keyboard-only operation) in src/features/digest/TimeZoneSetting.test.tsx

### Implementation for User Story 2

- [ ] T017 [P] [US2] Create request and response schemas in app/schemas/timezone.py validating "required string, at most 64 characters, member of the IANA zone database"
- [ ] T018 [US2] Implement the GET and PUT endpoints in app/api/timezone.py updating only the authenticated user's `timezone` (depends on T004, T017)
- [ ] T019 [US2] Register the timezone router under the `/api/v1` prefix in app/main.py (A) (depends on T018)
- [ ] T020 [P] [US2] Add the API client functions getTimeZone and setTimeZone in src/api/timezone.ts
- [ ] T022 [US2] Implement the time zone control with a labelled, keyboard-operable select pre-filled from the browser zone when none is stored, hidden when the digest flag is off, in src/features/digest/TimeZoneSetting.tsx (depends on T020, T021)
- [ ] T023 [US2] Mount the control in the user settings screen at src/features/settings/SettingsPage.tsx (A; the settings screen is owned by feature 001) (depends on T022)

**Checkpoint**: Users can set their time zone; User Stories 1 and 2 work together.

---

## Phase 5: User Story 3 - Exactly one digest per user per day, correct across DST (Priority: P2)

**Goal**: No duplicate and no skipped digests, across parallel runs, restarts, retries and clock changes.

**Independent Test**: Run the job repeatedly and in parallel with a fake clock across DST dates and check one `sent` record and one email per user per date (quickstart steps 4, 6, 7).

### Tests for User Story 3

- [ ] T024 [P] [US3] Unit tests for DST: spring forward and fall back in `Europe/Berlin` and `America/New_York`, 30-minute DST in `Australia/Lord_Howe`, no DST in `Asia/Kolkata`, catch-up after downtime on the same local date, no back-fill of past dates, in tests/unit/test_digest_schedule.py
- [ ] T025 [P] [US3] Integration test that repeated and parallel job runs and a restart yield one email and one `sent` row per user and date, in tests/integration/test_digest_exactly_once.py
- [ ] T026 [P] [US3] Integration test for retry: provider failure retried on later ticks up to 3 attempts then left `failed`; a stuck `claimed` row is not re-sent, in tests/integration/test_digest_retry.py

### Implementation for User Story 3

- [ ] T027 [US3] Implement claim, mark sent, mark failed and re-claim (`attempts < 3`) with `INSERT ... ON CONFLICT DO NOTHING` on `(user_id, local_date)` in app/services/digest_delivery.py (depends on T005)
- [ ] T028 [US3] Make app/services/digest_schedule.py DST-safe and catch-up aware so that the unit tests in T024 pass (depends on T009, T024)
- [ ] T029 [US3] Wrap each send in the claim and status updates in app/worker/jobs/daily_digest.py, storing `task_count` and `sent_at` (depends on T013, T027, T028)
- [ ] T030 [US3] Add retry handling and a log line and metric for stuck `claimed` rows in app/worker/jobs/daily_digest.py (depends on T029)

**Checkpoint**: All three stories work together; delivery is exactly-once.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T031 [P] Document the scheduler, flag, time zone behaviour, assumptions Q1-Q3 and stuck-claim handling in docs/daily-digest.md
- [ ] T032 Run the quickstart.md validation scenarios against dev with `FEATURE_DIGEST` enabled (depends on T015, T023, T030)
- [ ] T033 Security review of the time zone endpoint, the membership filter in app/services/digest_query.py and absence of secrets in k8s/notify-worker/digest-cronjob.yaml (depends on T032)

---

## Dependencies & Execution Order

- Setup (T001-T002) first; Foundational (T003-T005) blocks all stories.
- US1 and US2 are independent after Foundational (both need the `timezone` column, T004). US3 builds on the job from US1 (T013) and the schedule helpers (T009).
- Within each story: tests first, then models/helpers, services, job or endpoint, integration.
- Polish after the stories.

## Parallel Example

```text
After Foundational:
  US1: T006, T007, T008 together, then T009, T010, T011, T012, T015 together
  US2: T016, T017, T020, T021 together
  US3: T024, T025, T026 together
```

## Implementation Strategy

- MVP: Setup, Foundational, User Story 1 (with the time zone set in the database or UTC fallback), then User Story 2 so users can set their zone; both are P1.
- User Story 3 must be done before `FEATURE_DIGEST` is enabled in prod, because without it the job could duplicate emails when runs overlap.
- Keep the flag off in prod until stg validation (T032).

## Notes

- Open questions Q1-Q3 are assumed (see clarifications.md).
- Reuse the feature-005 email client and worker skeleton; do not add a second integration.
