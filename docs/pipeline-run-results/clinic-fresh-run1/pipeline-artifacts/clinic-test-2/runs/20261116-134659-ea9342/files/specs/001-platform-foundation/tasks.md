---

description: "Task list for Platform foundation, delivery and non-functional baseline"
---

# Tasks: Platform foundation, delivery and non-functional baseline

**Input**: Design documents from `/specs/001-platform-foundation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/platform-api.openapi.yaml, quickstart.md

**Tests**: Included. The constitution requires tests first for business logic and an independent test per story; test tasks come before implementation inside each story.

**Organization**: Tasks are grouped by user story. Paths start with the repository folder name: `clinic-api/` is brightsmile/clinic-api, `clinic-web/` is brightsmile/clinic-web, `clinic-infra/` is brightsmile/clinic-infra.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story the task belongs to (US1 to US10)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the three repositories and their basic structure (source: NFR-009)

- [ ] T001 [P] Create the API repository skeleton with Python 3.12 project file, FastAPI, SQLAlchemy, Alembic dependencies and a README with build, test and local-run steps in clinic-api/pyproject.toml and clinic-api/README.md
- [ ] T002 [P] Create the web repository skeleton (React + TypeScript SPA, test runner, build scripts) with a README in clinic-web/package.json, clinic-web/tsconfig.json and clinic-web/README.md
- [ ] T003 [P] Create the infrastructure repository layout (modules, envs/dev, envs/staging, envs/prod, monitoring, docs, scripts, tests) with a README in clinic-infra/README.md
- [ ] T004 [P] Configure linting, formatting and pre-commit hooks for the API in clinic-api/ruff.toml and clinic-api/.pre-commit-config.yaml
- [ ] T005 [P] Configure linting and formatting for the web app in clinic-web/eslint.config.js and clinic-web/.prettierrc
- [ ] T006 Scaffold the 8 empty module packages (identity, scheduling, booking, reception, noshow_policy, messaging, channel_adapters, reporting) per ADR-0001 in clinic-api/src/clinic_api/modules/identity/__init__.py, clinic-api/src/clinic_api/modules/scheduling/__init__.py, clinic-api/src/clinic_api/modules/booking/__init__.py, clinic-api/src/clinic_api/modules/reception/__init__.py, clinic-api/src/clinic_api/modules/noshow_policy/__init__.py, clinic-api/src/clinic_api/modules/messaging/__init__.py, clinic-api/src/clinic_api/modules/channel_adapters/__init__.py and clinic-api/src/clinic_api/modules/reporting/__init__.py (depends on T001)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core API and web skeleton that every user story builds on

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T007 Implement environment-variable settings (database URL, token signing key and provider keys read from the environment only, no defaults for secrets) in clinic-api/src/clinic_api/config.py (depends on T001)
- [ ] T008 Implement the SQLAlchemy engine and session with a connection pool and a 5 s statement timeout in clinic-api/src/clinic_api/db/session.py (depends on T007)
- [ ] T009 Implement the FastAPI app factory with interactive documentation at `/docs` in clinic-api/src/clinic_api/main.py (depends on T007)
- [ ] T010 [P] Set up the Alembic migration framework (forward-only, migration user URL from environment) in clinic-api/alembic.ini and clinic-api/migrations/env.py (depends on T001)
- [ ] T011 [P] Create the API container image definition (non-root user, no secrets baked in, listens on port 8000) in clinic-api/Dockerfile (depends on T001)
- [ ] T012 [P] Create the API contract file with the `/health` and `/api/v1/feature-flags` operations from specs/001-platform-foundation/contracts/platform-api.openapi.yaml in clinic-api/contracts/clinic-api-v1.openapi.yaml (depends on T001)
- [ ] T013 [P] Implement the web app bootstrap with a router in clinic-web/src/main.tsx and clinic-web/src/App.tsx (depends on T002)
- [ ] T014 [P] Implement the API client (base path `/api`, 10 s timeout, read requests retried once, write requests never retried automatically) in clinic-web/src/api/client.ts (depends on T002)

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Every change is built, tested and shipped safely (Priority: P1) 🎯 MVP

**Goal**: One repeatable pipeline per repository from commit to production, with rollback (source: NFR-009, NFR-004)

**Independent Test**: Push a trivial commit to each repository and confirm every stage runs in order; a failing test, a contract mismatch or a HIGH image-scan finding stops the pipeline; a failing health check triggers rollback to the previous release. Staging deploy stages need the staging environment from User Story 2.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T015 [P] [US1] Contract test that runs schema-based checks of the running API against `clinic-api/contracts/clinic-api-v1.openapi.yaml` in clinic-api/tests/contract/test_openapi_contract.py
- [ ] T016 [P] [US1] Unit test that fails any migration that drops or renames a column or table or adds a non-null column without a default (expand/contract rule) in clinic-api/tests/unit/test_migrations_forward_only.py
- [ ] T017 [P] [US1] Smoke test of health, sign-in with a test code, and book and cancel against sandbox providers (steps for features not yet built are skipped with a reason) in clinic-api/tests/smoke/test_staging_smoke.py

### Implementation for User Story 1

- [ ] T018 [US1] Create the API CI workflow: build, unit tests, contract tests, image scan that fails on HIGH findings, and secret scan in clinic-api/.github/workflows/ci.yml (depends on T015, T016)
- [ ] T019 [US1] Create the migration runner that applies Alembic migrations with the migration user from environment variables in clinic-api/scripts/run_migrations.sh (depends on T010)
- [ ] T020 [US1] Create the deploy workflow: deploy to staging, run the smoke test, then replace production one replica at a time behind the health check in clinic-api/.github/workflows/deploy.yml (depends on T017, T018, T019)
- [ ] T021 [US1] Create the post-deploy gate that polls `GET /health` and calls the rollback script when it fails in clinic-api/scripts/post_deploy_gate.py (depends on T020)
- [ ] T022 [P] [US1] Create the web CI workflow: build, unit tests and publish in clinic-web/.github/workflows/ci.yml
- [ ] T023 [US1] Create the publish script that uploads each build under its version and keeps the previous build for rollback in clinic-web/scripts/publish.sh (depends on T022)
- [ ] T024 [P] [US1] Create the rollback script (redeploy previous API image and previous web build) and the rollback runbook with the three triggers (health fails, 5xx above 2% for 5 minutes, reminder lag above 15 minutes) in clinic-infra/scripts/rollback.sh and clinic-infra/docs/rollback.md

**Checkpoint**: Pipelines exist for both repositories and the rollback path is written down

---

## Phase 4: User Story 2 - Dev, staging and production environments with managed secrets (Priority: P1)

**Goal**: Three environments hosting the web app, API and edge, with secrets from a secret store (source: NFR-004, NFR-003, NFR-009)

**Independent Test**: Create each environment from `clinic-infra`, deploy an API and web build, call the health check through the public route, and confirm no secret appears in repositories, images or logs.

### Tests for User Story 2

- [ ] T025 [P] [US2] Environment check script that calls the health check through the edge for an environment and searches repositories, images and logs for secret values in clinic-infra/tests/env_check.sh

### Implementation for User Story 2

- [ ] T026 [US2] Record the hosting decision (India region, managed container service, managed PostgreSQL 16, CDN; provider and placeholder domain, with open question Q1) in clinic-infra/docs/hosting-decision.md
- [ ] T027 [P] [US2] Create the secret store module for database credentials, provider keys, webhook secrets and token signing key, passed to the API as environment variables in clinic-infra/modules/secrets/main.tf (depends on T026)
- [ ] T028 [P] [US2] Create the static web hosting and CDN module in clinic-infra/modules/web-hosting/main.tf (depends on T026)
- [ ] T029 [P] [US2] Create the container service module (1 replica in dev and staging; in production 2 replicas in zones A and B, scale 2 to 4 on CPU above 60%, `GET /health` check, secrets as environment variables) in clinic-infra/modules/container-service/main.tf (depends on T026)
- [ ] T030 [P] [US2] Create the edge module (CDN, load balancer and web application firewall routing `/api` to the API, HTTPS only) in clinic-infra/modules/edge/main.tf (depends on T026)
- [ ] T031 [US2] Create the dev environment (smallest tiers) in clinic-infra/envs/dev/main.tf (depends on T027, T028, T029, T030)
- [ ] T032 [US2] Create the staging environment (smallest tiers, sandbox accounts for the SMS and WhatsApp providers via secret placeholders) in clinic-infra/envs/staging/main.tf (depends on T027, T028, T029, T030)
- [ ] T033 [US2] Create the production environment (edge with WAF, 2 to 4 replicas in two zones, clinic domain as a variable) in clinic-infra/envs/prod/main.tf (depends on T027, T028, T029, T030)
- [ ] T034 [US2] Write and run the replica and zone loss rehearsal and record the result in clinic-infra/docs/failover-test.md (depends on T033)
- [ ] T035 [P] [US2] Create the secret scan workflow for the infrastructure repository in clinic-infra/.github/workflows/secret-scan.yml

**Checkpoint**: Environments exist and are reachable through the edge

---

## Phase 5: User Story 3 - Database baseline, migrations, backups and a tested restore (Priority: P1)

**Goal**: A managed database with a repeatable baseline migration, encrypted backups and a rehearsed restore within RPO 15 minutes and RTO 1 hour (source: NFR-004, NFR-003)

**Independent Test**: Apply migrations to an empty database twice, confirm `btree_gist` exists and the application user cannot change structure; then restore from a snapshot plus archived logs and record the time taken and data age.

### Tests for User Story 3

- [ ] T036 [P] [US3] Integration test that applies migrations twice to an empty PostgreSQL 16 database and checks the `btree_gist` extension exists in clinic-api/tests/integration/test_migrations.py
- [ ] T037 [P] [US3] Integration test that the application user can read and write but gets a permission error on any DDL statement in clinic-api/tests/integration/test_app_user_privileges.py

### Implementation for User Story 3

- [ ] T038 [US3] Create the baseline migration (`CREATE EXTENSION IF NOT EXISTS btree_gist`, default privileges so the application user has data access only, all timestamps `timestamptz` in UTC) in clinic-api/migrations/versions/0001_baseline.py (depends on T010, T036, T037)
- [ ] T039 [P] [US3] Create the database module (PostgreSQL 16 with `btree_gist`, encryption at rest, continuous log archiving with point-in-time restore, daily snapshot kept 14 days encrypted, separate migration and application users) in clinic-infra/modules/database/main.tf
- [ ] T040 [US3] Create the dev and staging databases (single node, no standby) in clinic-infra/envs/dev/database.tf and clinic-infra/envs/staging/database.tf (depends on T039)
- [ ] T041 [US3] Create the production database (primary in zone A with a synchronous standby in zone B) in clinic-infra/envs/prod/database.tf (depends on T039)
- [ ] T042 [US3] Write the restore runbook (steps, RPO 15 minutes, RTO 1 hour, record template with date, snapshot, point in time, duration, result) in clinic-infra/docs/restore-runbook.md (depends on T039)
- [ ] T043 [US3] Create the restore rehearsal script that restores into a new instance and prints the duration and age of the newest restored data in clinic-infra/scripts/restore_rehearsal.sh (depends on T042)
- [ ] T044 [US3] Run the restore rehearsal and the standby failover test in staging-like production and record both results in clinic-infra/docs/restore-runbook.md (depends on T041, T043)

**Checkpoint**: Database baseline exists and restore is proven

---

## Phase 6: User Story 4 - A patient uses every screen comfortably on a phone (Priority: P1)

**Goal**: A plain, mobile-first shell with 44 px tap targets, no sideways scrolling and a booking journey of 5 screens or fewer after sign-in (source: NFR-001, NFR-010)

**Independent Test**: Open the sample patient screens in current Chrome and Safari on an Android phone and an iPhone; check for sideways scrolling, measure tap targets and count the journey screens.

### Tests for User Story 4

- [ ] T045 [P] [US4] Automated responsive check at 320, 360, 390 and 412 px in Chromium and WebKit that fails on horizontal overflow or any interactive element smaller than 44 x 44 px in clinic-web/tests/responsive/patient-layout.spec.ts
- [ ] T046 [P] [US4] Unit test that the booking journey lists at most 5 screens after sign-in in clinic-web/tests/unit/booking-journey.test.ts

### Implementation for User Story 4

- [ ] T047 [P] [US4] Create mobile-first base styles (fluid width, no fixed widths above the viewport, readable type, minimum 44 px for controls) in clinic-web/src/styles/base.css
- [ ] T048 [P] [US4] Create the Button component with a minimum 44 x 44 px target in clinic-web/src/components/Button.tsx
- [ ] T049 [P] [US4] Create the TextField component with a minimum 44 px height and label in clinic-web/src/components/TextField.tsx
- [ ] T050 [P] [US4] Create the ListRow component with a minimum 44 px row height in clinic-web/src/components/ListRow.tsx
- [ ] T051 [US4] Create the patient layout using the shared components in clinic-web/src/layout/PatientLayout.tsx (depends on T047, T048, T049, T050)
- [ ] T052 [US4] Define the booking journey screens (who and what, slot picker, confirm, booked) as the screen budget in clinic-web/src/journeys/booking-journey.ts
- [ ] T053 [US4] Create the placeholder patient screens for the journey in clinic-web/src/routes/patient/SignInPlaceholder.tsx, clinic-web/src/routes/patient/WhoAndWhat.tsx, clinic-web/src/routes/patient/SlotPicker.tsx, clinic-web/src/routes/patient/Confirm.tsx and clinic-web/src/routes/patient/Booked.tsx (depends on T051, T052)
- [ ] T054 [P] [US4] Create the plain notices for an unsupported browser and for an unreachable API in clinic-web/src/components/UnsupportedBrowserNotice.tsx and clinic-web/src/components/ApiDownNotice.tsx
- [ ] T055 [US4] Load each patient screen lazily so the sign-in screen does not wait for other screens in clinic-web/src/App.tsx (depends on T013, T053)
- [ ] T056 [US4] Create the responsive check workflow that fails the build on T045 failures in clinic-web/.github/workflows/responsive.yml (depends on T045)
- [ ] T057 [P] [US4] Write the real-device check procedure and results table (Android Chrome, iPhone Safari) in clinic-web/docs/device-check.md

**Checkpoint**: Patient shell passes automated checks and the device pass is documented

---

## Phase 7: User Story 5 - All screens and messages are in English with times in India time (Priority: P2)

**Goal**: One English catalogue and correct IST display of UTC-stored times (source: NFR-008)

**Independent Test**: Display a known UTC moment on a patient and a reception screen and compare with the expected IST time, including a UTC/IST date boundary.

### Tests for User Story 5

- [ ] T058 [P] [US5] Unit test that formats 2027-02-28T19:00:00Z as 1 March 2027 00:30 IST and that IST form input is converted to UTC in clinic-web/tests/unit/ist.test.ts
- [ ] T059 [P] [US5] Unit test of UTC storage and IST conversion helpers, including a UTC/IST date boundary, in clinic-api/tests/unit/test_clock.py
- [ ] T060 [P] [US5] Unit test that every catalogue key used in the code exists in the catalogue in clinic-web/tests/unit/catalogue.test.ts

### Implementation for User Story 5

- [ ] T061 [P] [US5] Create the single English message catalogue in clinic-web/src/i18n/en.ts
- [ ] T062 [US5] Create the `t()` helper that reads only from the catalogue and fails on a missing key in clinic-web/src/i18n/t.ts (depends on T061)
- [ ] T063 [P] [US5] Implement IST formatting from UTC and IST input parsing with the fixed UTC+05:30 offset in clinic-web/src/time/ist.ts
- [ ] T064 [P] [US5] Implement UTC storage and IST conversion helpers in clinic-api/src/clinic_api/core/clock.py
- [ ] T065 [P] [US5] Create the English message catalogue for API messages in clinic-api/src/clinic_api/core/messages.py
- [ ] T066 [US5] Add a lint rule that rejects hard-coded display text in screens in clinic-web/eslint.config.js (depends on T062)
- [ ] T067 [US5] Make the placeholder patient screens read all text from the catalogue and show times through the IST helper in clinic-web/src/routes/patient/SignInPlaceholder.tsx, clinic-web/src/routes/patient/WhoAndWhat.tsx, clinic-web/src/routes/patient/SlotPicker.tsx, clinic-web/src/routes/patient/Confirm.tsx and clinic-web/src/routes/patient/Booked.tsx (depends on T053, T062, T063)

**Checkpoint**: Text and time rules are enforced by tests and lint

---

## Phase 8: User Story 6 - Reception and the practice manager get a desktop layout that is available in clinic hours (Priority: P2)

**Goal**: A wide-screen staff layout with role navigation, available 08:00 to 20:00 IST Monday to Saturday (source: NFR-001, NFR-004)

**Independent Test**: Open the staff area at 1280 px and the dentist day page at 390 px; run the reception-hours probe over a clinic day; deploy during clinic hours and see no outage.

### Tests for User Story 6

- [ ] T068 [P] [US6] Responsive check that the staff layout uses a wide screen at 1280 px and the dentist day page has no sideways scrolling at 390 px in clinic-web/tests/responsive/staff-layout.spec.ts

### Implementation for User Story 6

- [ ] T069 [P] [US6] Define the role navigation (receptionist, dentist, practice manager) that later features fill in in clinic-web/src/layout/staffNav.ts
- [ ] T070 [US6] Create the staff layout with role navigation in clinic-web/src/layout/StaffLayout.tsx (depends on T047, T069)
- [ ] T071 [US6] Create the placeholder staff routes in clinic-web/src/routes/staff/ReceptionHome.tsx, clinic-web/src/routes/staff/DentistDay.tsx and clinic-web/src/routes/staff/ManagerHome.tsx (depends on T070)
- [ ] T072 [P] [US6] Create the reception-hours probe that runs 08:00 to 20:00 IST Monday to Saturday in clinic-infra/monitoring/probes/reception-hours.tf
- [ ] T073 [US6] Create the rolling-deploy availability check that polls the reception route during a deploy and fails on any gap in clinic-infra/tests/rolling_deploy_check.sh (depends on T020, T033)

**Checkpoint**: Staff layout works on desktop and phone and reception hours are probed

---

## Phase 9: User Story 7 - The team sees problems before patients do (Priority: P2)

**Goal**: PII-free structured logs, health check, minute probes, response-time measurement and alerts (source: NFR-004, NFR-003)

**Independent Test**: Follow a request's correlation id through the logs, find no seeded name, phone number or birth year, and see an alert when the staging API is stopped.

### Tests for User Story 7

- [ ] T074 [P] [US7] Unit test that seeds a name, phone number and birth year into a request and fails if any appears in captured logs in clinic-api/tests/unit/test_logging_no_pii.py
- [ ] T075 [P] [US7] Unit test that every request gets a correlation id that is returned in a response header and carried in log lines in clinic-api/tests/unit/test_correlation.py
- [ ] T076 [P] [US7] Contract test of `GET /health` for 200 (database ok) and 503 (database unreachable) in clinic-api/tests/contract/test_health_contract.py

### Implementation for User Story 7

- [ ] T077 [P] [US7] Implement the correlation-id middleware in clinic-api/src/clinic_api/observability/correlation.py
- [ ] T078 [US7] Implement structured JSON logging that logs ids and the correlation id, masks known personal data fields and never logs request bodies in clinic-api/src/clinic_api/observability/logging.py (depends on T077)
- [ ] T079 [P] [US7] Set up OpenTelemetry traces and metrics export in clinic-api/src/clinic_api/observability/telemetry.py
- [ ] T080 [P] [US7] Record request timing per route group (free slots, booking) for the p95 measures in clinic-api/src/clinic_api/observability/metrics.py
- [ ] T081 [US7] Implement `GET /health` returning API and database status in clinic-api/src/clinic_api/api/health.py (depends on T009, T076)
- [ ] T082 [US7] Wire the middleware, logging, telemetry and the health router into the app in clinic-api/src/clinic_api/main.py (depends on T078, T079, T080, T081)
- [ ] T083 [P] [US7] Create the online-booking probe that runs every minute and calls the health check and the free-slot read (stub read until the scheduling feature exists) in clinic-infra/monitoring/probes/online-booking.tf
- [ ] T084 [P] [US7] Create alerts for a failing health check and for monthly availability below 99.5% in clinic-infra/monitoring/alerts/availability.tf
- [ ] T085 [P] [US7] Create the alert and rollback trigger for 5xx above 2% for 5 minutes in clinic-infra/monitoring/alerts/error-rate.tf
- [ ] T086 [P] [US7] Create the alert for reminder lag above 10 minutes and the rollback trigger for lag above 15 minutes in clinic-infra/monitoring/alerts/reminder-lag.tf
- [ ] T087 [P] [US7] Create the alert channels (shared delivery-team channel and email, business hours; open question Q3) in clinic-infra/monitoring/alerts/channels.tf
- [ ] T088 [US7] Create the SLO dashboards (free slots 2 s for 95% with server p95 at most 500 ms, booking 3 s for 95% with server p95 at most 800 ms) in clinic-infra/monitoring/dashboards/slo.tf (depends on T080)
- [ ] T089 [P] [US7] Unit test of the monthly SLO report calculations (availability, reception hours, p95, reminders on time, reminders for cancelled) in clinic-infra/monitoring/slo-report/test_report.py
- [ ] T090 [US7] Implement the monthly SLO report in clinic-infra/monitoring/slo-report/report.py (depends on T072, T083, T089)

**Checkpoint**: The team can see, measure and be alerted

---

## Phase 10: User Story 8 - Release 2 screens stay hidden until they are ready (Priority: P2)

**Goal**: Database-backed switches that hide Release 2 screens and actions until turned on, with an audit of changes (source: NFR-009)

**Independent Test**: With a switch off the sample R2 route and API action are unavailable; turn it on in staging with the admin tool and it appears with no deploy and one change row recorded.

### Tests for User Story 8

- [ ] T091 [P] [US8] Unit test that the flag endpoint lists all switches as booleans and the guard refuses an action with the switch off in clinic-api/tests/unit/test_feature_flags.py
- [ ] T092 [P] [US8] Integration test that changing a switch writes one `feature_flag_change` row with old value, new value, operator and UTC time in the same transaction in clinic-api/tests/integration/test_flag_change_audit.py
- [ ] T093 [P] [US8] Unit test that the web app hides a route and menu entry when its switch is off in clinic-web/tests/unit/useFlags.test.ts

### Implementation for User Story 8

- [ ] T094 [US8] Create migration 0002 with `feature_flag` (key text primary key, lowercase words with dots; enabled boolean default false; description text; updated_at timestamptz UTC; updated_by text operator id) and `feature_flag_change` (id bigint primary key; key text foreign key to feature_flag; old_value boolean; new_value boolean; changed_by text; changed_at timestamptz UTC), seeding `r2.family-members`, `r2.noshow-block`, `r2.noshow-report`, `r2.reminders-failed-list` and `r2.sms-fallback` as off in clinic-api/migrations/versions/0002_feature_flags.py (depends on T038)
- [ ] T095 [US8] Create the feature flag models in clinic-api/src/clinic_api/db/models/feature_flag.py (depends on T094)
- [ ] T096 [US8] Implement `GET /api/v1/feature-flags` in clinic-api/src/clinic_api/api/feature_flags.py (depends on T095)
- [ ] T097 [US8] Implement the flag guard dependency that answers "not found" for an action whose switch is off in clinic-api/src/clinic_api/api/flag_guard.py (depends on T095)
- [ ] T098 [US8] Implement the admin tool that sets a switch and records who and when in clinic-api/src/clinic_api/tools/set_flag.py (depends on T095)
- [ ] T099 [US8] Implement the flags hook that reads the endpoint in clinic-web/src/flags/useFlags.ts (depends on T096)
- [ ] T100 [US8] Implement the route and menu guard that hides Release 2 screens when their switch is off in clinic-web/src/routes/RequireFlag.tsx (depends on T099)
- [ ] T101 [US8] Register the feature flags router in the app in clinic-api/src/clinic_api/main.py (depends on T082, T096)

**Checkpoint**: Release 2 work can merge safely behind switches

---

## Phase 11: User Story 9 - The service handles 100 concurrent users and a third clinic as data (Priority: P2)

**Goal**: Repeatable proof of the response-time targets at 100 concurrent users and with 3 clinics, 10 dentists and 1,000 appointments a week (source: NFR-003)

**Independent Test**: Run the load test against production-sized staging with today's data, then with the scale data set; read the stored reports.

**Note**: Slot and booking requests need the scheduling and booking features (003 and 004). Until they exist the load test runs against stub endpoints, and it is re-run before UAT.

- [ ] T102 [P] [US9] Create the load test for 100 concurrent virtual users at about 35 requests/s on the free-slot and booking paths, including a 30-patients-at-once booking scenario, asserting server p95 of at most 500 ms (free slots) and 800 ms (booking), which leaves time for 4G to meet 2 s and 3 s for 95% (SC-008), in clinic-api/tests/load/load_test.py
- [ ] T103 [P] [US9] Create the scale data seeder for 3 clinics, 10 dentists and 1,000 appointments a week for a year using synthetic names and phone numbers in clinic-api/tests/load/seed_scale_data.py
- [ ] T104 [P] [US9] Create the check that adds a third clinic and a tenth dentist through data only, with no code, schema change or deploy, and sees them offered to patients in clinic-api/tests/load/test_third_clinic_as_data.py
- [ ] T105 [US9] Create the report writer that stores date, environment size, data set, users, p95 per route and error count in clinic-api/tests/load/report.py (depends on T102)
- [ ] T106 [P] [US9] Define the staging size equal to production for load tests in clinic-infra/envs/staging/load-test.tfvars
- [ ] T107 [US9] Run the load test with today's data (30 patients at once, then 100 users) and store the report in clinic-api/tests/load/reports/today.md (depends on T102, T105, T106)
- [ ] T108 [US9] Run the load test with the scale data set and the third-clinic check and store the report in clinic-api/tests/load/reports/scale.md (depends on T103, T104, T107)

**Checkpoint**: NFR-003 is verified and recorded

---

## Phase 12: User Story 10 - Release 1 is checked off as ready for UAT and go-live (Priority: P1)

**Goal**: A go-live readiness checklist with owner, due date, status and evidence, reviewed on 2027-02-22 and closed with a go/no-go on 2027-03-01 (source: NFR-009)

**Independent Test**: Walk the checklist in staging: every item has an owner, a status and evidence, or a recorded risk, and the 2027-02-22 review can make a go/no-go call.

- [ ] T109 [P] [US10] Create the readiness checklist with items for pipeline and rollback rehearsal, environments and secrets, restore test, responsive checks on Chrome and Safari on Android and iPhone, English and IST checks, SLO probes and alerts, load test, Release 2 switches off, provider accounts and registrations (owned by the messaging feature), domain and hosting confirmed, and the paper-diary dry run (owned by reception) in clinic-infra/docs/go-live-readiness.md
- [ ] T110 [P] [US10] Create the practice manager sign-off template for trying each flow in clinic-infra/docs/uat-signoff.md
- [ ] T111 [P] [US10] Create the go/no-go record template (decision, who, when) in clinic-infra/docs/go-no-go.md
- [ ] T112 [US10] Hold the 2027-02-22 readiness review and update every item's status, evidence or recorded risk with owner and plan in clinic-infra/docs/go-live-readiness.md (depends on T109)
- [ ] T113 [US10] Close the checklist on 2027-03-01 with the go/no-go decision, who decided and when in clinic-infra/docs/go-no-go.md (depends on T111, T112)
- [ ] T114 [US10] Confirm that all Release 2 switches are off in production and record it in clinic-infra/docs/go-live-readiness.md (depends on T094, T098, T109)

**Checkpoint**: Release 1 readiness is visible and decided

---

## Phase 13: Polish & Cross-Cutting Concerns

**Purpose**: Improvements and evidence that span several stories

- [ ] T115 [P] Update the READMEs with final run, test, deploy and rollback instructions in clinic-api/README.md, clinic-web/README.md and clinic-infra/README.md
- [ ] T116 Rehearse a rollback in staging (failing health check leads to the previous API image and web build within 15 minutes) and record the result in clinic-infra/docs/rollback.md (depends on T021, T023, T024, T032)
- [ ] T117 [P] Review the secret scan, image scan and log checks for HIGH findings and record the outcome in clinic-infra/docs/security-review.md
- [ ] T118 Run every scenario in specs/001-platform-foundation/quickstart.md and record results in clinic-infra/docs/quickstart-validation.md (depends on T044, T057, T090, T101, T108)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup; blocks all user stories
- **User Stories (Phase 3 to 12)**: Depend on Foundational. They are independent except where a task names a dependency:
  - US1 deploy stages need the staging environment (US2: T032) to run; the pipeline files themselves are independent
  - US3 database environment files need the same modules and providers decided in US2 (T026)
  - US5 T067 edits the screens made in US4 (T053)
  - US6 T070 reuses styles from US4 (T047); T073 needs the deploy workflow (T020) and production (T033)
  - US7 T090 needs the probes from US6 (T072) and US7 (T083)
  - US8 T094 follows the baseline migration (T038); T101 follows T082
  - US9 runs against staging (US2) and, for real slot and booking paths, features 003 and 004
  - US10 T114 needs the switches from US8
- **Polish (Phase 13)**: After the stories it touches

### Within Each User Story

- Tests first and failing, then models/modules, then endpoints and screens, then integration

### Parallel Opportunities

- All Setup tasks marked [P], and Foundational T010 to T014
- Within each story, all test tasks marked [P], the four environment modules T027 to T030, observability tasks T077, T079, T080 and alerts T083 to T087
- US1 to US4 can run in parallel with different people (delivery/devops on US1 to US3; frontend on US4)

---

## Parallel Example: User Story 4

```bash
# Launch all tests for User Story 4 together:
Task: "Automated responsive check in clinic-web/tests/responsive/patient-layout.spec.ts"
Task: "Unit test of the booking journey in clinic-web/tests/unit/booking-journey.test.ts"

# Launch all shared components together:
Task: "Create the Button component in clinic-web/src/components/Button.tsx"
Task: "Create the TextField component in clinic-web/src/components/TextField.tsx"
Task: "Create the ListRow component in clinic-web/src/components/ListRow.tsx"
```

---

## Implementation Strategy

### MVP First (User Stories 1 to 3)

1. Complete Phase 1 (Setup) and Phase 2 (Foundational)
2. Complete User Story 1 (pipeline), User Story 2 (environments) and User Story 3 (database): other features can then deploy and store data
3. **STOP and VALIDATE**: push a commit through to staging and run the restore rehearsal

### Incremental Delivery

1. Add User Story 4 and 5 (patient shell, English and IST) so patient screens can be built
2. Add User Story 6 and 8 (staff shell, feature switches) so reception and Release 2 work can be built
3. Add User Story 7 (observability) before UAT so the targets are measured
4. Add User Story 9 (load and scale) when features 003 and 004 are in staging, and User Story 10 (readiness) tracked from the start and reviewed on 2027-02-22

---

## Notes

- The P marker means different files and no dependencies
- The Story label maps the task to a user story for traceability
- Each user story is independently testable unless the dependencies section says otherwise
- Verify tests fail before implementing
- Open questions Q1 to Q3 are recorded in clarifications.md
