---

description: "Task list for Notification preferences (F07)"
---

# Tasks: Notification preferences

**Input**: Design documents from `/specs/007-notification-prefs/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included (constitution principle I: tests first for business logic; every story has an independent test).

**Organization**: Tasks are grouped by user story. Paths: API repo `acme/taskflow-api` (`app/`, `migrations/`, `tests/`), web repo `acme/taskflow-web` (`src/`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Feature flag and web folder

- [ ] T001 Add the `FEATURE_NOTIFICATION_PREFS` flag (read from the environment, default off) to `app/core/config.py` in acme/taskflow-api
- [ ] T002 [P] Create the web feature folder with an empty `src/features/notification-prefs/index.ts` in acme/taskflow-web

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data model, schemas, constants and window calculation used by all stories

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 Create the Alembic migration `migrations/versions/007_notification_prefs.py` creating `notification_channels`, `notification_frequencies` and `notification_preferences` exactly as in data-model.md (code varchar(32) primary key; `notification_type` varchar(32) check in `assignment`, `mention`, `digest`; `enabled` boolean not null default true; `frequency_code` not null default `immediate`; unique (`user_id`, `notification_type`, `channel_code`); index on `user_id`) and seeding `email`, `immediate` (0), `hourly` (60), `daily` (1440)
- [ ] T004 [P] Create the SQLAlchemy models `NotificationChannel`, `NotificationFrequency` and `NotificationPreference` in `app/models/notification_preference.py`
- [ ] T005 [P] Create the request and response schemas matching `contracts/notification-preferences-api.md` in `app/schemas/notification_preferences.py`
- [ ] T006 [P] Define the notification type constants (`assignment`, `mention`, `digest`, with label and `supports_frequency`; digest has `supports_frequency = false`) in `app/services/notification_types.py`
- [ ] T007 [P] Write unit tests for window ends (hourly ends at the next top of the hour; daily ends at the next 08:00 in the user's time zone; 08:00 UTC when the time zone is unknown) in `tests/services/test_notification_windows.py`
- [ ] T008 Implement `window_end(frequency, now, user_time_zone)` in `app/services/notification_windows.py` (depends on T007)
- [ ] T009 [P] Write a migration and model test (seed rows exist, unique constraint, check constraint on type, cascade on user delete) in `tests/models/test_notification_preference_model.py` (depends on T003, T004)

**Checkpoint**: Foundation ready

---

## Phase 3: User Story 1 - Choose which notifications I receive (Priority: P1) MVP

**Goal**: A user reads, changes and saves on/off per notification type (email only) through the API and a keyboard-usable settings page, behind the flag.

**Independent Test**: Sign in, switch "Mention" off on the settings page, reload; "Mention" is off and the rest unchanged; repeat with the keyboard only; with the flag off the endpoints answer 404.

**Open question Q1 (assumed, see clarifications.md)**: email is the only channel; channels are configuration data.

### Tests for User Story 1

- [ ] T010 [P] [US1] Write API contract tests (GET defaults with all types on; PUT persists; another user's data is untouched; 401 unauthenticated; 404 flag off; 422 unknown type or channel and nothing saved) in `tests/api/test_notification_preferences_api.py`
- [ ] T011 [P] [US1] Write service unit tests for `get_preferences` (defaults filled in) and `save_preferences` (atomic replace, own user only) in `tests/services/test_notification_preferences_service.py`
- [ ] T012 [P] [US1] Write component tests (renders every type, toggles and saves, shows confirmation and error message, keyboard-only operation, no automated accessibility violations) in `src/features/notification-prefs/NotificationPrefsPage.test.tsx`

### Implementation for User Story 1

- [ ] T013 [US1] Implement `get_preferences(user_id)` and `save_preferences(user_id, payload)` in `app/services/notification_preferences.py`, validating type and channel against configuration (depends on T004, T005, T006)
- [ ] T014 [US1] Implement the router with `GET` and `PUT /api/v1/users/me/notification-preferences`, current-user only, 404 when the flag is off, in `app/api/notification_preferences.py` (depends on T013)
- [ ] T015 [US1] Register the router in the application entry point `app/main.py` (depends on T014)
- [ ] T016 [P] [US1] Create the API client `getPreferences` and `savePreferences` in `src/api/notificationPreferences.ts`
- [ ] T017 [US1] Build the settings page with one labelled checkbox per type, a save button, a polite live region for save status and visible focus in `src/features/notification-prefs/NotificationPrefsPage.tsx` (depends on T016)
- [ ] T018 [US1] Add the settings route and a settings link shown only when the preferences request succeeds in `src/routes.tsx` (depends on T017)

**Checkpoint**: User Story 1 is functional and testable on its own

---

## Phase 4: User Story 2 - Choose how often I am notified (Priority: P2)

**Goal**: A user picks a frequency per type; held notifications are combined into one summary email at the end of the window.

**Independent Test**: Set "Mention" to hourly, trigger three mentions in the hour; one summary email with three mentions is sent at the end of the hour and none immediately.

**Open questions (assumed)**: Q1 (frequencies are configuration data seeded with immediate, hourly, daily) and Q2 (assignment may be delayed or switched off only by explicit user choice).

### Tests for User Story 2

- [ ] T019 [P] [US2] Write service tests for frequency validation (disabled or unknown frequency rejected; digest accepts only `immediate`; stored frequency that is now disabled reads as `immediate`) in `tests/services/test_notification_frequency_validation.py`
- [ ] T020 [P] [US2] Write worker tests (three held mentions in one window produce one summary email; none sent before the window ends; held items of a type switched off are dropped) in `tests/worker/test_send_notification_summaries.py`
- [ ] T021 [P] [US2] Write component tests for the frequency control (only enabled frequencies offered, `immediate` preselected, keyboard operable, digest shows on/off only) in `src/features/notification-prefs/FrequencySelect.test.tsx`

### Implementation for User Story 2

- [ ] T022 [US2] Extend `save_preferences` and `get_preferences` with frequency validation and the disabled-frequency fallback in `app/services/notification_preferences.py` (depends on T013, T019)
- [ ] T023 [P] [US2] Build the summary email content (grouped list per user, type and window) in `app/services/notification_summary.py`
- [ ] T024 [US2] Implement the notify-worker job that finds due held notifications in the 005 outbox, groups them by user, type and window, and sends one summary through the 005 email client, in `app/worker/jobs/send_notification_summaries.py` (depends on T008, T020, T023)
- [ ] T025 [US2] Drop the held outbox notifications of a type when the user switches that type off, in `app/services/notification_preferences.py` (depends on T022, T024)
- [ ] T026 [US2] Add the native frequency select per type (labelled, keyboard operable, hidden for digest) in `src/features/notification-prefs/FrequencySelect.tsx` and use it in `src/features/notification-prefs/NotificationPrefsPage.tsx` (depends on T017, T021)

**Checkpoint**: User Stories 1 and 2 work independently

---

## Phase 5: User Story 3 - Senders respect my preferences (Priority: P2)

**Goal**: The assignment, digest and mention senders consult one decision operation and send now, later or not at all.

**Independent Test**: With "Assignment" off for user A and on for user B, assign a task to each; only B gets an email; with the flag off both get one.

**Open question Q1 (assumed)**: the decision takes the channel as input so a new channel needs no sender change.

### Tests for User Story 3

- [ ] T027 [P] [US3] Write unit tests for `resolve_delivery` (off gives skip; no row gives send_now; flag off gives send_now; hourly gives send_later with the window end; read error gives send_now with a log entry and the `notification_prefs_fallback_total` metric) in `tests/services/test_resolve_delivery.py`
- [ ] T028 [P] [US3] Write integration tests for the three senders (assignment off for A and on for B; digest off; mention hourly is held; flag off sends as before) in `tests/integration/test_senders_respect_preferences.py`

### Implementation for User Story 3

- [ ] T029 [US3] Implement `resolve_delivery(user_id, notification_type, channel, now)` as in `contracts/delivery-decision.md` in `app/services/notification_preferences.py` (depends on T008, T013, T027)
- [ ] T030 [US3] Call `resolve_delivery` in the assignment email sender owned by 005 (module under `app/services/` or `app/worker/jobs/`, exact file taken from 005's tasks); on `send_later` store the notification in the outbox as held (depends on T029)
- [ ] T031 [US3] Call `resolve_delivery` in the daily digest sender owned by 006 (module under `app/worker/jobs/`, exact file taken from 006's tasks) (depends on T029)
- [ ] T032 [US3] Call `resolve_delivery` in the mention sender owned by 004 (module under `app/services/`, exact file taken from 004's tasks); on `send_later` store the notification in the outbox as held (depends on T029)

**Checkpoint**: All user stories are functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Observability, health, docs, accessibility and performance

- [ ] T033 Add structured logs for each preference change and each non-default decision in `app/services/notification_preferences.py` (depends on T029)
- [ ] T034 Add the health check `GET /api/v1/notification-preferences/health` to `app/api/notification_preferences.py` and a test in `tests/api/test_notification_preferences_health.py` (depends on T014)
- [ ] T035 [P] Add a latency test for GET and PUT preferences against the p95 300 ms service level in `tests/perf/test_notification_prefs_latency.py` (depends on T014)
- [ ] T036 [P] Record a manual keyboard-only and WCAG 2.1 AA check of the settings page in `docs/notification-preferences.md` together with the feature description and the open question Q1
- [ ] T037 Run the validation scenarios in `specs/007-notification-prefs/quickstart.md` and record the result in `docs/notification-preferences.md` (depends on T018, T026, T032)

---

## Dependencies & Execution Order

- Setup (Phase 1) has no dependencies; Foundational (Phase 2) depends on it and blocks all stories.
- US1 starts after Phase 2. US2 depends on US1 service and page tasks (T013, T017). US3 depends on T013 and T008 and is otherwise independent of US2.
- Within a story: tests first, then models/services, then endpoints/UI.
- US3 tasks T030-T032 edit modules owned by features 005, 006 and 004; they are coordinated with those features and need those modules to exist.
- Polish depends on the stories it covers.

## Parallel Example

```text
Phase 2: T004, T005, T006, T007 together
US1: T010, T011, T012, T016 together
US2: T019, T020, T021, T023 together
US3: T027, T028 together; T030, T031, T032 together after T029
```

## Implementation Strategy

- MVP: Phase 1, Phase 2, then User Story 1 (stored preferences and settings page).
- Then US3 (senders honour preferences; this is what gives preferences an effect), then US2 (frequency and summary emails).
- Each story is tested independently and released behind `FEATURE_NOTIFICATION_PREFS`.
