# Backlog v1 — clinic-test-2

9 epics · 83 stories · 648 tasks · 381 story points · 0 blocking issues

## Issues

- **warning** `open_questions`: 17 items have open questions for the reviewer

## Coverage of prd.md

- NFR-005: S-007-US3, S-007-US5, S-SETUP-007, S-FOUND-007, S-POLISH-007
- FR-001: S-003-US1, S-003-US3, S-003-US4, S-SETUP-003, S-FOUND-003, S-POLISH-003
- FR-002: S-002-US1, S-002-US2, S-SETUP-002, S-FOUND-002
- FR-003: S-002-US3, S-SETUP-002, S-FOUND-002
- FR-004: S-002-US4, S-002-US5, S-002-US6, S-002-US7, S-FOUND-002, S-POLISH-002, S-008-US2, S-008-US3, S-FOUND-008
- FR-005: S-002-US3, S-002-US4, S-002-US5, S-FOUND-002
- FR-006: S-008-US1, S-008-US2, S-008-US3, S-008-US4, S-SETUP-008, S-FOUND-008, S-POLISH-008
- FR-007: S-003-US3, S-SETUP-003, S-FOUND-003, S-POLISH-003
- FR-008: S-003-US3, S-003-US4, S-003-US5, S-003-US6, S-SETUP-003, S-FOUND-003, S-POLISH-003
- FR-009: S-003-US2, S-003-US4, S-SETUP-003, S-FOUND-003, S-POLISH-003
- FR-010: S-003-US2, S-003-US4, S-003-US5, S-SETUP-003, S-FOUND-003, S-POLISH-003
- FR-011: S-004-US1, S-SETUP-004, S-FOUND-004, S-POLISH-004
- FR-012: S-004-US2, S-004-US4, S-SETUP-004, S-FOUND-004, S-POLISH-004
- FR-013: S-004-US3, S-SETUP-004, S-FOUND-004
- FR-014: S-007-US1, S-008-US4
- FR-015: S-005-US1, S-005-US5, S-POLISH-005, S-008-US3
- FR-016: S-005-US4, S-005-US5, S-POLISH-005
- FR-017: S-005-US3, S-005-US5, S-FOUND-005, S-POLISH-005
- FR-018: S-005-US3, S-005-US4, S-FOUND-005, S-POLISH-005, S-007-US1
- FR-019: S-006-US1, S-SETUP-006, S-FOUND-006, S-POLISH-006
- FR-020: S-006-US4, S-006-US5, S-006-US6, S-SETUP-006, S-FOUND-006, S-POLISH-006
- FR-021: S-006-US2, S-SETUP-006, S-FOUND-006, S-POLISH-006
- FR-022: S-006-US3, S-SETUP-006, S-FOUND-006, S-POLISH-006
- FR-023: S-006-US7, S-SETUP-006, S-FOUND-006, S-POLISH-006
- FR-024: S-005-US1, S-005-US2, S-005-US3, S-005-US4, S-SETUP-005, S-FOUND-005, S-POLISH-005
- FR-025: S-009-US1, S-SETUP-009, S-FOUND-009, S-POLISH-009
- FR-026: S-009-US2, S-SETUP-009, S-FOUND-009, S-POLISH-009
- FR-027: S-007-US2, S-008-US4
- FR-028: S-007-US3, S-007-US8, S-007-US9
- FR-029: S-007-US8
- FR-030: S-007-US2
- FR-031: S-007-US1, S-007-US4, S-007-US7, S-007-US8, S-008-US4
- FR-032: S-009-US3, S-SETUP-009, S-FOUND-009, S-POLISH-009
- FR-033: S-007-US9
- NFR-001: S-001-US4, S-001-US6
- NFR-002: S-004-US1, S-004-US4, S-004-US5, S-SETUP-004, S-FOUND-004
- NFR-003: S-001-US2, S-001-US3, S-001-US7, S-001-US9
- NFR-004: S-001-US1, S-001-US2, S-001-US3, S-001-US6, S-001-US7, S-FOUND-001, S-POLISH-001
- NFR-006: S-002-US1, S-002-US3, S-002-US4, S-002-US5, S-002-US7, S-SETUP-002, S-FOUND-002, S-POLISH-002, S-008-US2, S-008-US3, S-FOUND-008, S-POLISH-008
- NFR-007: S-002-US2, S-002-US6, S-FOUND-002, S-POLISH-002, S-008-US1, S-POLISH-008
- NFR-008: S-001-US5
- NFR-009: S-001-US1, S-001-US2, S-001-US8, S-001-US10, S-SETUP-001, S-FOUND-001, S-POLISH-001
- NFR-010: S-001-US4, S-004-US1, S-POLISH-004
- NFR-011: S-007-US4, S-007-US5, S-007-US6, S-007-US7, S-SETUP-007, S-FOUND-007, S-POLISH-007

Critical path: S-SETUP-001 → S-FOUND-001 → S-FOUND-002 → S-FOUND-003 → S-003-US4 → S-004-US1 → S-007-US1 → S-007-US2 → S-007-US3 → S-007-US4 → S-007-US5 → S-007-US8 → S-007-US9 → S-POLISH-007

## E-001 Platform foundation, delivery and non-functional baseline

Repos, CI/CD, environments, database, web app shell, observability, load/availability/localisation baselines, go-live readiness.

### S-001-US1 Every change is built, tested and shipped safely — P1/must · 8 SP (low, llm)

As a member of the delivery team, I want each commit to the API and web repositories built, tested, scanned and deployed through one repeatable pipeline with a rehearsed rollback so that Release 1 can ship on 1 March 2027 without manual, error-prone steps and a bad release can be undone quickly.
Depends on: S-FOUND-001 · Sources: NFR-009, NFR-004

- [AC-S-001-US1-1] Given a commit to the API repository, When the pipeline runs, Then it builds, runs unit tests, runs contract tests against the published API contract, scans the image, deploys to staging, runs the smoke test (health, sign-in with a test code, book and cancel against sandbox providers) and only then replaces production one replica at a time behind the health check
- [AC-S-001-US1-2] Given a failing unit test, a contract test that no longer matches the API contract, or a HIGH image-scan finding, When the pipeline runs, Then the pipeline stops and nothing is deployed to staging or production
- [AC-S-001-US1-3] Given a commit to the web repository, When the pipeline runs, Then the web app is built and published separately from the API and the previous published build is kept
- [AC-S-001-US1-4] Given a new release in production, When the health check fails, or server errors exceed 2% for 5 minutes, or reminder lag exceeds 15 minutes, Then the team can roll back by redeploying the previous API image and the previous web build, and the rollback steps are documented and rehearsed once in staging
- [AC-S-001-US1-5] Given a database change in a release, When the pipeline deploys it, Then the change only adds or relaxes structures (expand) and stays compatible with the previous release; removals happen in a later release (contract)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T015 | Contract test that runs schema-based checks of the running API against `clinic-a | 4.0 | qa-automation, api-design | yes | - |
| 001-T016 | Unit test that fails any migration that drops or renames a column or table or ad | 4.0 | qa-automation, postgres | no | - |
| 001-T017 | Smoke test of health, sign-in with a test code, and book and cancel against sand | 5.0 | qa-automation, backend-python | no | - |
| 001-T018 | Create the API CI workflow: build, unit tests, contract tests, image scan that f | 6.0 | devops-ci | no | 001-T015, 001-T016 |
| 001-T019 | Create the migration runner that applies Alembic migrations with the migration u | 3.0 | devops-ci, postgres | no | 001-T010 |
| 001-T020 | Create the deploy workflow: deploy to staging, run the smoke test, then replace  | 8.0 | devops-ci | no | 001-T017, 001-T018, 001-T019 |
| 001-T021 | Create the post-deploy gate that polls `GET /health` and calls the rollback scri | 4.0 | devops-ci, backend-python | no | 001-T020 |
| 001-T022 | Create the web CI workflow: build, unit tests and publish in clinic-web/.github/ | 4.0 | devops-ci, frontend-react | no | - |
| 001-T023 | Create the publish script that uploads each build under its version and keeps th | 3.0 | devops-ci | no | 001-T022 |
| 001-T024 | Create the rollback script (redeploy previous API image and previous web build)  | 5.0 | devops-ci, docs | no | - |

### S-001-US2 Dev, staging and production environments with managed secrets — P1/must · 8 SP (low, llm)

As a member of the delivery team, I want separate dev, staging and production environments, each with the API, web app and database, with secrets kept in a secret store so that we can test safely and production stays available and protected.
Depends on: S-FOUND-001 · Sources: NFR-004, NFR-003, NFR-009

- [AC-S-001-US2-1] Given the infrastructure repository, When an environment is created, Then dev, staging and production each host the web app (static, behind a CDN), the API and the database, with dev and staging on the smallest tiers and staging using sandbox accounts for the SMS and WhatsApp providers
- [AC-S-001-US2-2] Given production, When a visitor opens the site, Then the web app is served from the CDN, requests under `/api` are routed through the load balancer and web application firewall to the API, and all traffic uses HTTPS
- [AC-S-001-US2-3] Given production, When one API replica or one zone is lost, Then the other replica keeps serving online booking, and under sustained CPU above 60% the API scales between 2 and 4 replicas
- [AC-S-001-US2-4] Given the secret store holds the database credentials, provider keys, webhook secrets and token signing key, When the API starts in any environment, Then it receives them as environment variables and no secret is present in code, images or configuration files
- [AC-S-001-US2-5] Given the clinic has not yet confirmed a hosting provider or domain, When environments are created, Then they use an India cloud region chosen by the delivery team and a placeholder domain until the clinic supplies theirs (Assumed: see open question Q1)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T025 | Environment check script that calls the health check through the edge for an env | 4.0 | devops-ci, qa-automation | no | - |
| 001-T026 | Record the hosting decision (India region, managed container service, managed Po | 3.0 | docs, devops-ci | no | - |
| 001-T027 | Create the secret store module for database credentials, provider keys, webhook  | 5.0 | terraform | no | 001-T026 |
| 001-T028 | Create the static web hosting and CDN module in clinic-infra/modules/web-hosting | 4.0 | terraform | no | 001-T026 |
| 001-T029 | Create the container service module (1 replica in dev and staging; in production | 6.0 | terraform, kubernetes | no | 001-T026 |
| 001-T030 | Create the edge module (CDN, load balancer and web application firewall routing  | 6.0 | terraform | no | 001-T026 |
| 001-T031 | Create the dev environment (smallest tiers) in clinic-infra/envs/dev/main.tf | 3.0 | terraform | no | 001-T027, 001-T028, 001-T029, 001-T030 |
| 001-T032 | Create the staging environment (smallest tiers, sandbox accounts for the SMS and | 3.0 | terraform | no | 001-T027, 001-T028, 001-T029, 001-T030 |
| 001-T033 | Create the production environment (edge with WAF, 2 to 4 replicas in two zones,  | 5.0 | terraform | no | 001-T027, 001-T028, 001-T029, 001-T030 |
| 001-T034 | Write and run the replica and zone loss rehearsal and record the result in clini | 5.0 | devops-ci, qa-automation | no | 001-T033 |
| 001-T035 | Create the secret scan workflow for the infrastructure repository in clinic-infr | 2.0 | devops-ci | no | - |

### S-001-US3 Database baseline, migrations, backups and a tested restore — P1/must · 8 SP (low, llm)

As a member of the delivery team, I want a managed database with a first migration, a repeatable migration process, encrypted backups and a rehearsed restore so that appointment data is never lost beyond 15 minutes and service can be restored within 1 hour.
Depends on: S-FOUND-001 · Sources: NFR-004, NFR-003

- [AC-S-001-US3-1] Given an empty database in any environment, When the migrations are applied, Then the baseline schema is created, including the extension needed to prevent overlapping appointments for one dentist, and the migration can be applied again without error
- [AC-S-001-US3-2] Given the application's database user, When it connects, Then it can read and write data but cannot change the database structure; structure changes run under a separate migration user
- [AC-S-001-US3-3] Given production, When one day passes, Then a snapshot is taken and kept 14 days, backups and archived logs are encrypted, and logs are archived continuously so any point in time can be restored
- [AC-S-001-US3-4] Given a backup, When the delivery team restores it to a new database before go-live, Then the restored data is at most 15 minutes older than the chosen point (RPO) and the restore completes within 1 hour (RTO); the date, duration and result are recorded in the readiness checklist
- [AC-S-001-US3-5] Given production, When the primary database node fails, Then the synchronous standby in the second zone takes over without losing committed data

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T036 | Integration test that applies migrations twice to an empty PostgreSQL 16 databas | 3.0 | postgres, qa-automation | no | - |
| 001-T037 | Integration test that the application user can read and write but gets a permiss | 3.0 | postgres, qa-automation | no | - |
| 001-T038 | Create the baseline migration (`CREATE EXTENSION IF NOT EXISTS btree_gist`, defa | 4.0 | postgres, data-modeling | no | 001-T010, 001-T036, 001-T037 |
| 001-T039 | Create the database module (PostgreSQL 16 with `btree_gist`, encryption at rest, | 8.0 | terraform, postgres | no | - |
| 001-T040 | Create the dev and staging databases (single node, no standby) in clinic-infra/e | 3.0 | terraform, postgres | no | 001-T039 |
| 001-T041 | Create the production database (primary in zone A with a synchronous standby in  | 4.0 | terraform, postgres | no | 001-T039 |
| 001-T042 | Write the restore runbook (steps, RPO 15 minutes, RTO 1 hour, record template wi | 3.0 | docs, postgres | no | 001-T039 |
| 001-T043 | Create the restore rehearsal script that restores into a new instance and prints | 4.0 | devops-ci, postgres | no | 001-T042 |
| 001-T044 | Run the restore rehearsal and the standby failover test in staging-like producti | 5.0 | devops-ci, postgres | no | 001-T041, 001-T043 |

### S-001-US4 A patient uses every screen comfortably on a phone — P1/must · 5 SP (low, llm)

As a patient booking from my phone, I want a plain, mobile-friendly website that needs no install, with big tap targets and no sideways scrolling so that I can book at any age in Chrome or Safari on my Android phone or iPhone.
Depends on: S-FOUND-001 · Sources: NFR-001, NFR-010

- [AC-S-001-US4-1] Given the web app shell, When I open any patient screen on a phone-width display in current Chrome or Safari on Android or iPhone, Then the page fits the width with no sideways scrolling and nothing needs to be installed
- [AC-S-001-US4-2] Given any tappable control on a patient screen (buttons, links, form fields, list rows), When its size is measured, Then it is at least 44 px by 44 px
- [AC-S-001-US4-3] Given the booking journey defined in the shell (who and what, slot picker, confirm, booked), When screens are counted after sign-in, Then a new patient reaches a booked appointment in 5 screens or fewer
- [AC-S-001-US4-4] Given an automated responsive check, When the pipeline runs, Then it fails any patient screen that scrolls sideways or has a tap target smaller than 44 px
- [AC-S-001-US4-5] Given a patient with slow 4G, When the shell loads, Then the sign-in screen is usable without waiting for unrelated screens (the app loads only what the screen needs)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T045 | Automated responsive check at 320, 360, 390 and 412 px in Chromium and WebKit th | 5.0 | qa-automation, frontend-react | no | - |
| 001-T046 | Unit test that the booking journey lists at most 5 screens after sign-in in clin | 2.0 | frontend-react, qa-automation | yes | - |
| 001-T047 | Create mobile-first base styles (fluid width, no fixed widths above the viewport | 3.0 | frontend-css | yes | - |
| 001-T048 | Create the Button component with a minimum 44 x 44 px target in clinic-web/src/c | 2.0 | frontend-react, frontend-css | yes | - |
| 001-T049 | Create the TextField component with a minimum 44 px height and label in clinic-w | 2.0 | frontend-react, frontend-css | yes | - |
| 001-T050 | Create the ListRow component with a minimum 44 px row height in clinic-web/src/c | 2.0 | frontend-react, frontend-css | yes | - |
| 001-T051 | Create the patient layout using the shared components in clinic-web/src/layout/P | 3.0 | frontend-react, frontend-css | yes | 001-T047, 001-T048, 001-T049, 001-T050 |
| 001-T052 | Define the booking journey screens (who and what, slot picker, confirm, booked)  | 2.0 | frontend-react | yes | 001-T051 |
| 001-T053 | Create the placeholder patient screens for the journey in clinic-web/src/routes/ | 5.0 | frontend-react, frontend-css | no | 001-T051, 001-T052 |
| 001-T054 | Create the plain notices for an unsupported browser and for an unreachable API i | 3.0 | frontend-react | yes | - |
| 001-T055 | Load each patient screen lazily so the sign-in screen does not wait for other sc | 2.0 | frontend-react | yes | 001-T013, 001-T053 |
| 001-T056 | Create the responsive check workflow that fails the build on T045 failures in cl | 2.0 | devops-ci, qa-automation | no | 001-T045 |
| 001-T057 | Write the real-device check procedure and results table (Android Chrome, iPhone  | 4.0 | qa-automation, docs | no | - |

### S-001-US5 All screens and messages are in English with times in India time — P2/must · 5 SP (low, llm)

As a patient or receptionist, I want every screen and message in plain English and every time shown in India time (IST) so that I never have to convert times or guess what a message means.
Depends on: S-FOUND-001 · Sources: NFR-008

- [AC-S-001-US5-1] Given a time stored in universal time (UTC), When it is shown on any screen or in any message, Then it appears as India time (IST, UTC+05:30) with the correct date, including when the UTC date and the IST date differ
- [AC-S-001-US5-2] Given any screen text or message wording, When it is reviewed, Then it comes from one English message catalogue and no text is typed directly into a screen or message
- [AC-S-001-US5-3] Given a person enters a date or time in a form, When it is saved, Then it is interpreted as IST and stored as UTC
- [AC-S-001-US5-4] Given the automated checks, When a string is missing from the catalogue or a screen shows a time without a timezone conversion, Then the check fails

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T058 | Unit test that formats 2027-02-28T19:00:00Z as 1 March 2027 00:30 IST and that I | 2.0 | frontend-react, qa-automation | yes | - |
| 001-T059 | Unit test of UTC storage and IST conversion helpers, including a UTC/IST date bo | 2.0 | backend-python, qa-automation | yes | - |
| 001-T060 | Unit test that every catalogue key used in the code exists in the catalogue in c | 2.0 | frontend-react, qa-automation | yes | - |
| 001-T061 | Create the single English message catalogue in clinic-web/src/i18n/en.ts | 3.0 | frontend-react | yes | - |
| 001-T062 | Create the `t()` helper that reads only from the catalogue and fails on a missin | 2.0 | frontend-react | yes | 001-T061 |
| 001-T063 | Implement IST formatting from UTC and IST input parsing with the fixed UTC+05:30 | 3.0 | frontend-react | yes | - |
| 001-T064 | Implement UTC storage and IST conversion helpers in clinic-api/src/clinic_api/co | 2.0 | backend-python | yes | - |
| 001-T065 | Create the English message catalogue for API messages in clinic-api/src/clinic_a | 2.0 | backend-python | yes | - |
| 001-T066 | Add a lint rule that rejects hard-coded display text in screens in clinic-web/es | 3.0 | frontend-react, devops-ci | yes | 001-T062 |
| 001-T067 | Make the placeholder patient screens read all text from the catalogue and show t | 4.0 | frontend-react | no | 001-T053, 001-T062, 001-T063 |

### S-001-US6 Reception and the practice manager get a desktop layout that is available in clinic hours — P2/must · 3 SP (low, llm)

As a receptionist or practice manager using a desktop browser, I want a wide-screen layout with navigation for my role that is available during clinic hours (08:00 to 20:00 IST, Monday to Saturday) so that I can run the day from the reception PC without interruptions, including during deploys.
Depends on: S-FOUND-001 · Sources: NFR-001, NFR-004

- [AC-S-001-US6-1] Given a desktop browser, When I open the staff area, Then I see a wide-screen layout with a navigation area for my role (receptionist, dentist, practice manager) that later features fill with their screens
- [AC-S-001-US6-2] Given a phone, When a dentist opens "my day", Then the staff layout also fits without sideways scrolling (the dentist may use a phone)
- [AC-S-001-US6-3] Given a clinic day (08:00 to 20:00 IST, Monday to Saturday), When the reception screens are probed, Then availability over the month is reported against the 99.5% target
- [AC-S-001-US6-4] Given a planned release during clinic hours, When it is deployed, Then the rolling replacement keeps reception screens available (no full outage)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T068 | Responsive check that the staff layout uses a wide screen at 1280 px and the den | 3.0 | qa-automation, frontend-react | yes | - |
| 001-T069 | Define the role navigation (receptionist, dentist, practice manager) that later  | 2.0 | frontend-react | yes | - |
| 001-T070 | Create the staff layout with role navigation in clinic-web/src/layout/StaffLayou | 4.0 | frontend-react, frontend-css | yes | 001-T047, 001-T069 |
| 001-T071 | Create the placeholder staff routes in clinic-web/src/routes/staff/ReceptionHome | 3.0 | frontend-react | yes | 001-T070 |
| 001-T072 | Create the reception-hours probe that runs 08:00 to 20:00 IST Monday to Saturday | 4.0 | observability, terraform | no | - |
| 001-T073 | Create the rolling-deploy availability check that polls the reception route duri | 4.0 | devops-ci, qa-automation | no | 001-T020, 001-T033 |

### S-001-US7 The team sees problems before patients do — P2/must · 8 SP (low, llm)

As a member of the delivery team, I want structured logs without personal data, a health check, minute-by-minute availability probes, response-time measurement and alerts so that we find and fix problems before the clinics notice and can prove the targets are met.
Depends on: S-FOUND-001 · Sources: NFR-004, NFR-003

- [AC-S-001-US7-1] Given the API is running, When `GET /health` is called, Then it reports whether the API and its database connection are working, and the interactive API documentation is reachable at `/docs`
- [AC-S-001-US7-2] Given any request, When it is logged, Then the log carries ids and a correlation id and never contains a name, phone number or birth year; an automated test seeds personal data and fails if it appears in logs
- [AC-S-001-US7-3] Given the production site, When a probe runs every minute reading the health check and the free-slot list, Then the result is recorded and monthly availability is calculated against 99.5%
- [AC-S-001-US7-4] Given the free-slot list and booking confirmation, When requests are measured, Then 95% of free-slot requests finish within 2 s and 95% of booking confirmations within 3 s as seen by a phone on 4G, with server-side p95 at most 500 ms and 800 ms respectively
- [AC-S-001-US7-5] Given a deploy, When health fails, 5xx exceeds 2% for 5 minutes, or reminder lag exceeds 15 minutes, Then the rollback alert fires; an alert also fires when reminder lag exceeds 10 minutes (Assumed: alerts go to the delivery team's shared channel, see open question Q3)
- [AC-S-001-US7-6] Given the monthly SLO report, When it is produced, Then it shows booking availability, reception-hours availability, slot and booking speed, reminders sent within 15 minutes (99%) and reminders sent for cancelled appointments (0)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T074 | Unit test that seeds a name, phone number and birth year into a request and fail | 3.0 | qa-automation, backend-python | yes | - |
| 001-T075 | Unit test that every request gets a correlation id that is returned in a respons | 2.0 | qa-automation, backend-python | yes | - |
| 001-T076 | Contract test of `GET /health` for 200 (database ok) and 503 (database unreachab | 2.0 | api-design, qa-automation | yes | - |
| 001-T077 | Implement the correlation-id middleware in clinic-api/src/clinic_api/observabili | 2.0 | backend-python, observability | yes | - |
| 001-T078 | Implement structured JSON logging that logs ids and the correlation id, masks kn | 4.0 | backend-python, observability | yes | 001-T077 |
| 001-T079 | Set up OpenTelemetry traces and metrics export in clinic-api/src/clinic_api/obse | 4.0 | observability, backend-python | yes | - |
| 001-T080 | Record request timing per route group (free slots, booking) for the p95 measures | 3.0 | observability, backend-python | yes | - |
| 001-T081 | Implement `GET /health` returning API and database status in clinic-api/src/clin | 3.0 | backend-python, api-design | yes | 001-T009, 001-T076 |
| 001-T082 | Wire the middleware, logging, telemetry and the health router into the app in cl | 2.0 | backend-python | yes | 001-T078, 001-T079, 001-T080, 001-T081 |
| 001-T083 | Create the online-booking probe that runs every minute and calls the health chec | 4.0 | observability, terraform | no | - |
| 001-T084 | Create alerts for a failing health check and for monthly availability below 99.5 | 3.0 | observability, terraform | no | - |
| 001-T085 | Create the alert and rollback trigger for 5xx above 2% for 5 minutes in clinic-i | 3.0 | observability, terraform | no | - |
| 001-T086 | Create the alert for reminder lag above 10 minutes and the rollback trigger for  | 3.0 | observability, terraform | no | - |
| 001-T087 | Create the alert channels (shared delivery-team channel and email, business hour | 3.0 | observability, terraform | no | - |
| 001-T088 | Create the SLO dashboards (free slots 2 s for 95% with server p95 at most 500 ms | 5.0 | observability, terraform | no | 001-T080 |
| 001-T089 | Unit test of the monthly SLO report calculations (availability, reception hours, | 4.0 | backend-python, qa-automation | yes | - |
| 001-T090 | Implement the monthly SLO report in clinic-infra/monitoring/slo-report/report.py | 6.0 | backend-python, observability | no | 001-T072, 001-T083, 001-T089 |

### S-001-US8 Release 2 screens stay hidden until they are ready — P2/must · 5 SP (low, llm)

As a practice manager, I want the Release 2 features (family members, no-show block, no-show report, reminders-failed list and SMS fallback) to stay invisible to patients and staff until they are switched on so that Release 1 goes live on 1 March 2027 without half-finished screens.
Depends on: S-FOUND-001 · Sources: NFR-009

- [AC-S-001-US8-1] Given a Release 2 screen or action, When its switch is off, Then no menu entry, route or API action for it is visible or usable to patients or staff
- [AC-S-001-US8-2] Given the switch for a feature is turned on in staging, When a user opens the app, Then the feature appears without a new deploy, and turning it off hides it again
- [AC-S-001-US8-3] Given production at go-live, When the switch settings are reviewed, Then all Release 2 switches are off and the setting is recorded in the readiness checklist
- [AC-S-001-US8-4] Given the switch is changed, When it is read, Then who changed it and when is recorded

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T091 | Unit test that the flag endpoint lists all switches as booleans and the guard re | 3.0 | backend-python, qa-automation | yes | - |
| 001-T092 | Integration test that changing a switch writes one `feature_flag_change` row wit | 3.0 | postgres, qa-automation | no | - |
| 001-T093 | Unit test that the web app hides a route and menu entry when its switch is off i | 2.0 | frontend-react, qa-automation | yes | - |
| 001-T094 | Create migration 0002 with `feature_flag` (key text primary key, lowercase words | 4.0 | postgres, data-modeling | no | 001-T038 |
| 001-T095 | Create the feature flag models in clinic-api/src/clinic_api/db/models/feature_fl | 2.0 | backend-python, postgres | yes | 001-T094 |
| 001-T096 | Implement `GET /api/v1/feature-flags` in clinic-api/src/clinic_api/api/feature_f | 3.0 | backend-python, api-design | yes | 001-T095 |
| 001-T097 | Implement the flag guard dependency that answers "not found" for an action whose | 3.0 | backend-python, api-design | yes | 001-T095 |
| 001-T098 | Implement the admin tool that sets a switch and records who and when in clinic-a | 3.0 | backend-python, postgres | yes | 001-T095 |
| 001-T099 | Implement the flags hook that reads the endpoint in clinic-web/src/flags/useFlag | 2.0 | frontend-react | yes | 001-T096 |
| 001-T100 | Implement the route and menu guard that hides Release 2 screens when their switc | 3.0 | frontend-react | yes | 001-T099 |
| 001-T101 | Register the feature flags router in the app in clinic-api/src/clinic_api/main.p | 1.0 | backend-python | yes | 001-T082, 001-T096 |

### S-001-US9 The service handles 100 concurrent users and a third clinic as data — P2/should · 5 SP (low, llm)

As a practice manager, I want proof that the service copes with today's clinics, with 30 patients booking at once, and with a third clinic and 1,000 appointments a week so that the business can grow without a rebuild.
Depends on: S-FOUND-001 · Sources: NFR-003

- [AC-S-001-US9-1] Given staging sized like production and today's data (2 clinics, 6 dentists, about 450 appointments a week), When 30 simulated patients book at once, Then the free-slot and booking targets (2 s and 3 s for 95%) are met
- [AC-S-001-US9-2] Given the same environment, When 100 concurrent simulated users run for at least 10 minutes at about 35 requests per second, Then the free-slot and booking targets are still met and there are no errors other than "slot taken"
- [AC-S-001-US9-3] Given a data set of 3 clinics, 10 dentists and 1,000 appointments a week for a year, When the load test runs again, Then the targets are still met with no change to the application code or the data structures
- [AC-S-001-US9-4] Given a third clinic and a tenth dentist are added through the setup screens or data load, When patients open the site, Then they are offered without a deploy
- [AC-S-001-US9-5] Given the load test results, When they are reviewed, Then they are recorded in the readiness checklist with the date and the environment size

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T102 | Create the load test for 100 concurrent virtual users at about 35 requests/s on  | 6.0 | qa-automation, backend-python | no | - |
| 001-T103 | Create the scale data seeder for 3 clinics, 10 dentists and 1,000 appointments a | 4.0 | backend-python, postgres | yes | - |
| 001-T104 | Create the check that adds a third clinic and a tenth dentist through data only, | 3.0 | qa-automation, backend-python | yes | - |
| 001-T105 | Create the report writer that stores date, environment size, data set, users, p9 | 3.0 | qa-automation, backend-python | yes | 001-T102 |
| 001-T106 | Define the staging size equal to production for load tests in clinic-infra/envs/ | 1.0 | terraform | no | - |
| 001-T107 | Run the load test with today's data (30 patients at once, then 100 users) and st | 4.0 | qa-automation, devops-ci | no | 001-T102, 001-T105, 001-T106 |
| 001-T108 | Run the load test with the scale data set and the third-clinic check and store t | 4.0 | qa-automation, devops-ci | no | 001-T103, 001-T104, 001-T107 |

### S-001-US10 Release 1 is checked off as ready for UAT and go-live — P1/must · 2 SP (low, llm)

As a practice manager, I want a go-live readiness checklist that the delivery team completes before the user acceptance test and go-live so that I can sign off by trying each flow and be confident Release 1 can go live on 1 March 2027.
Depends on: S-FOUND-001 · Sources: NFR-009

- [AC-S-001-US10-1] Given the checklist, When it is reviewed, Then each item shows an owner, a due date, a status (not started, in progress, done) and a link to evidence
- [AC-S-001-US10-2] Given the readiness date 2027-02-22, When the checklist is reviewed, Then it covers: pipeline and rollback rehearsal, environments and secrets, restore test result, responsive check results on Chrome and Safari on Android and iPhone, English and IST checks, SLO probes and alerts running, load test result, Release 2 switches off, provider sandbox and production accounts and registrations status (owned by the messaging feature), domain and hosting confirmed, and the paper-diary dry run (owned by reception)
- [AC-S-001-US10-3] Given an item is not done by the readiness date, When the checklist is reviewed, Then it is marked as a risk with an owner and a plan so the date is not silently missed
- [AC-S-001-US10-4] Given go-live day 2027-03-01, When the checklist is closed, Then the go or no-go decision, who made it and when are recorded
- [AC-S-001-US10-5] Given the practice manager signs off by trying each flow, When they finish, Then their sign-off is recorded against the checklist (A-006)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T109 | Create the readiness checklist with items for pipeline and rollback rehearsal, e | 3.0 | docs | yes | - |
| 001-T110 | Create the practice manager sign-off template for trying each flow in clinic-inf | 1.0 | docs | yes | - |
| 001-T111 | Create the go/no-go record template (decision, who, when) in clinic-infra/docs/g | 1.0 | docs | yes | - |
| 001-T112 | Hold the 2027-02-22 readiness review and update every item's status, evidence or | 3.0 | docs | no | 001-T109 |
| 001-T113 | Close the checklist on 2027-03-01 with the go/no-go decision, who decided and wh | 1.0 | docs | no | 001-T111, 001-T112 |
| 001-T114 | Confirm that all Release 2 switches are off in production and record it in clini | 1.0 | devops-ci, docs | no | 001-T094, 001-T098, 001-T109 |

### S-SETUP-001 Platform foundation, delivery and non-functional baseline: Setup — P1/must · 3 SP (low, llm)

Depends on: - · Sources: E-001, NFR-009

- [AC-S-SETUP-001-1] Given the setup tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T001 | Create the API repository skeleton with Python 3.12 project file, FastAPI, SQLAl | 3.0 | backend-python, docs | yes | - |
| 001-T002 | Create the web repository skeleton (React + TypeScript SPA, test runner, build s | 3.0 | frontend-react, docs | yes | - |
| 001-T003 | Create the infrastructure repository layout (modules, envs/dev, envs/staging, en | 2.0 | terraform, docs | no | - |
| 001-T004 | Configure linting, formatting and pre-commit hooks for the API in clinic-api/ruf | 2.0 | backend-python, devops-ci | yes | - |
| 001-T005 | Configure linting and formatting for the web app in clinic-web/eslint.config.js  | 2.0 | frontend-react, devops-ci | yes | - |
| 001-T006 | Scaffold the 8 empty module packages (identity, scheduling, booking, reception,  | 2.0 | backend-python, api-design | no | 001-T001 |

### S-FOUND-001 Platform foundation, delivery and non-functional baseline: Foundational prerequisites — P1/must · 5 SP (low, llm)

Depends on: S-SETUP-001 · Sources: E-001, NFR-009, NFR-004

- [AC-S-FOUND-001-1] Given the foundational prerequisites tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T007 | Implement environment-variable settings (database URL, token signing key and pro | 3.0 | backend-python, auth-security | no | 001-T001 |
| 001-T008 | Implement the SQLAlchemy engine and session with a connection pool and a 5 s sta | 3.0 | backend-python, postgres | yes | 001-T007 |
| 001-T009 | Implement the FastAPI app factory with interactive documentation at `/docs` in c | 3.0 | backend-python, api-design | yes | 001-T007 |
| 001-T010 | Set up the Alembic migration framework (forward-only, migration user URL from en | 3.0 | postgres, backend-python | no | 001-T001 |
| 001-T011 | Create the API container image definition (non-root user, no secrets baked in, l | 3.0 | devops-ci, backend-python | no | 001-T001 |
| 001-T012 | Create the API contract file with the `/health` and `/api/v1/feature-flags` oper | 3.0 | api-design | yes | 001-T001 |
| 001-T013 | Implement the web app bootstrap with a router in clinic-web/src/main.tsx and cli | 3.0 | frontend-react | yes | 001-T002 |
| 001-T014 | Implement the API client (base path `/api`, 10 s timeout, read requests retried  | 4.0 | frontend-react, api-design | yes | 001-T002 |

### S-POLISH-001 Platform foundation, delivery and non-functional baseline: Polish & cross-cutting concerns — P2/should · 3 SP (low, llm)

Depends on: S-001-US1, S-001-US2, S-001-US3, S-001-US4, S-001-US5, S-001-US6, S-001-US7, S-001-US8, S-001-US9, S-001-US10 · Sources: E-001, NFR-009, NFR-004

- [AC-S-POLISH-001-1] Given the polish & cross-cutting concerns tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T115 | Update the READMEs with final run, test, deploy and rollback instructions in cli | 3.0 | docs | yes | - |
| 001-T116 | Rehearse a rollback in staging (failing health check leads to the previous API i | 4.0 | devops-ci, qa-automation | no | 001-T021, 001-T023, 001-T024, 001-T032 |
| 001-T117 | Review the secret scan, image scan and log checks for HIGH findings and record t | 3.0 | devops-ci, docs | no | - |
| 001-T118 | Run every scenario in specs/001-platform-foundation/quickstart.md and record res | 6.0 | qa-automation, docs | no | 001-T044, 001-T057, 001-T090, 001-T101, 001-T108 |

## E-002 Sign-in, roles and staff accounts

Patient phone-code sign-in, staff password sign-in, role-based visibility with clinic scoping, staff account management, privacy and erasure.

### S-002-US1 Patient signs in with a phone code — P1/must · 5 SP (low, llm)

As a patient (P-01) booking from my phone, I want to sign in with my phone number and an SMS code, with clear messages for a wrong or expired code so that I can reach my appointments without a password and stay signed in for 7 days, while my account is protected from guessing and code floods.
Depends on: S-FOUND-002, S-007-US7 · Sources: FR-002, NFR-006

- [AC-S-002-US1-1] Given a patient account exists for a phone number, When the patient enters the number and asks for a code, Then a 6-digit code is sent by SMS and the screen asks for the code. (source: FR-002)
- [AC-S-002-US1-2] Given a code was sent less than 10 minutes ago, When the patient enters it correctly, Then the patient is signed in and sees their own appointments area. (source: FR-002)
- [AC-S-002-US1-3] Given a code was sent, When the patient enters a wrong code, Then the screen says the code is wrong, shows how to get a new code, and the wrong try is counted. (source: FR-002)
- [AC-S-002-US1-4] Given a code was sent more than 10 minutes ago, When the patient enters it, Then the screen says the code has expired and offers a new code. (source: FR-002)
- [AC-S-002-US1-5] Given a patient has entered 5 wrong codes for a phone number, When they try again within 15 minutes (with the old or a new code), Then the system refuses and says to wait, and after 15 minutes a new code can be requested. (source: FR-002, NFR-006)
- [AC-S-002-US1-6] Given a patient has not used the site for less than 7 days, When they return, Then they are still signed in; **Given** 7 days without use, **Then** they must sign in again. (source: FR-002)
- [AC-S-002-US1-7] Given a single network address or a single day has produced too many code requests, When another code is requested, Then the request is refused without sending an SMS. (source: NFR-006)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 002-T020 | Write tests for `clinic-api/app/identity/otp_service.py` in `clinic-api/tests/id | 4.5 | qa-automation, auth-security | no | - |
| 002-T021 | Write API tests for `/api/auth/patient/code`, `/api/auth/patient/verify`, `/api/ | 4.0 | qa-automation, api-design | no | - |
| 002-T022 | Write component tests in `clinic-web/tests/identity/PatientSignIn.test.tsx`: pho | 3.5 | qa-automation, frontend-react | no | - |
| 002-T023 | Implement code issue, verify, tries, locks, per-address and per-phone throttles  | 6.0 | backend-python, auth-security | no | 002-T009, 002-T014, 002-T002 |
| 002-T024 | Implement existing-patient sign-in and session start (update last_seen_at, issue | 3.0 | backend-python, auth-security | no | 002-T023, 002-T012 |
| 002-T025 | Implement `POST /api/auth/patient/code`, `POST /api/auth/patient/verify`, `GET / | 4.0 | api-design, backend-python | no | 002-T024, 002-T018 |
| 002-T026 | Build the phone and code steps with error and wait messages in `clinic-web/src/i | 5.0 | frontend-react, frontend-css | no | 002-T019 |

### S-002-US2 New patient creates an account — P1/must · 3 SP (low, llm)

As a new patient (P-01) with a phone number BrightSmile does not know yet, I want to verify my code, give my name and get an account created so that I can book online without calling the clinic, and no account or personal data is stored for a number that never verified.
Depends on: S-002-US1 · Sources: FR-002, NFR-007

- [AC-S-002-US2-1] Given a phone number with no account, When the patient verifies a correct code, Then the screen asks for their name and no account exists yet. (source: FR-002)
- [AC-S-002-US2-2] Given the code is verified for a new number, When the patient gives a name, Then one account for that phone number and one person record with that name are created and the patient is signed in. (source: FR-002, NFR-007)
- [AC-S-002-US2-3] Given the code for a new number is wrong or expired, When the patient continues, Then no account is created. (source: FR-002)
- [AC-S-002-US2-4] Given the name is empty, When the patient submits, Then the screen asks for a name and creates nothing. (source: FR-002)
- [AC-S-002-US2-5] Given an account already exists for the phone number, When a patient signs in with it, Then no second account is created. (source: FR-002)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 002-T027 | Write tests in `clinic-api/tests/identity/test_patient_registration.py`: verify  | 3.0 | qa-automation, auth-security | no | - |
| 002-T028 | Write component tests in `clinic-web/tests/identity/PatientRegistration.test.tsx | 2.5 | qa-automation, frontend-react | no | - |
| 002-T029 | Add registration (create account and account-holder person in one transaction, c | 4.0 | backend-python, postgres | no | 002-T024 |
| 002-T030 | Add `POST /api/auth/patient/register` and the registration cookie to `clinic-api | 4.0 | api-design, backend-python | no | 002-T025, 002-T029 |
| 002-T031 | Add the name step to `clinic-web/src/identity/PatientSignIn.tsx` | 4.5 | frontend-react | no | 002-T026 |

### S-002-US3 Staff sign in with username and password — P1/must · 5 SP (low, llm)

As a staff member (receptionist P-02, dentist P-03 or practice manager P-04), I want to sign in with my username and password and change my own password so that I reach the screen for my role, and patient data is protected by lockout, session limits and a 10-character password minimum.
Depends on: S-002-US1 · Sources: FR-003, NFR-006, FR-005

- [AC-S-002-US3-1] Given an active staff account, When the person enters the correct username and password, Then they are signed in and land on the screen for their role. (source: FR-003)
- [AC-S-002-US3-2] Given an active staff account, When a wrong password is entered, Then the screen says the username or password is wrong without saying which one. (source: FR-003, NFR-006)
- [AC-S-002-US3-3] Given 5 failed sign-ins for a username, When a sixth is tried within 15 minutes (even with the right password), Then it is refused with a message to wait; after 15 minutes sign-in works again. (source: NFR-006)
- [AC-S-002-US3-4] Given a staff member is signed in, When 30 minutes pass without use or 8 hours pass since sign-in, Then the next request requires signing in again. (source: FR-003)
- [AC-S-002-US3-5] Given a password is set or changed, When it has fewer than 10 characters, Then it is rejected. (source: NFR-006)
- [AC-S-002-US3-6] Given any screen or call, When it is reached over plain HTTP, Then it is not served; all traffic is over HTTPS. (source: NFR-006)
- [AC-S-002-US3-7] Given a signed-in staff member, When they change their own password (giving the current one) or the manager sets a new password for them, Then the new password works at the next sign-in and the old one does not. (source: FR-003, FR-005)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 002-T032 | Write tests in `clinic-api/tests/identity/test_staff_signin.py`: success lands o | 5.0 | qa-automation, auth-security | no | - |
| 002-T033 | Write tests in `clinic-api/tests/identity/test_staff_session_expiry.py`: refused | 3.0 | qa-automation, auth-security | no | - |
| 002-T034 | Write component tests in `clinic-web/tests/identity/StaffSignIn.test.tsx` for th | 4.0 | qa-automation, frontend-react | no | - |
| 002-T035 | Implement staff sign-in, failure counting, lockout, uniform error and own passwo | 6.0 | backend-python, auth-security | no | 002-T009, 002-T011, 002-T012 |
| 002-T036 | Add `POST /api/auth/staff/login` and `POST /api/auth/staff/password` to `clinic- | 4.0 | api-design, backend-python | no | 002-T025, 002-T035 |
| 002-T037 | Build the staff sign-in screen in `clinic-web/src/identity/StaffSignIn.tsx` | 4.5 | frontend-react | no | - |
| 002-T038 | Build the change-password screen in `clinic-web/src/identity/ChangePassword.tsx` | 3.5 | frontend-react | no | - |

### S-002-US4 Each role sees only what it needs — P1/must · 8 SP (low, llm)

As a practice manager (P-04) responsible for patient data, I want every request to be authorised on the server from the signed-in person's role, clinic and patient scope, never from ids in the request so that receptionists, dentists and patients can reach only the data their role allows, with zero cross-clinic or cross-patient reads.
Depends on: S-FOUND-002 · Sources: FR-004, NFR-006, FR-005

- [AC-S-002-US4-1] Given a patient is signed in, When they ask for an appointment of a person who is not themselves or one of their family members, Then the system refuses it as if it did not exist. (source: FR-004, NFR-006)
- [AC-S-002-US4-2] Given a receptionist of clinic A, When they ask for or change an appointment of clinic B, Then the system refuses. (source: FR-004, NFR-006)
- [AC-S-002-US4-3] Given a receptionist of clinic A, When they search patients by phone number or name, Then they find patients regardless of clinic but see appointments of clinic A only. (source: FR-004)
- [AC-S-002-US4-4] Given a dentist is signed in, When they ask for another dentist's day or try to change anything, Then the system refuses. (source: FR-004)
- [AC-S-002-US4-5] Given the practice manager is signed in, When they open data of either clinic or the settings, Then it is allowed. (source: FR-004)
- [AC-S-002-US4-6] Given a person's role, clinic or active flag changed since they signed in, When they make their next request, Then the current values apply at once. (source: FR-004, FR-005)
- [AC-S-002-US4-7] Given a request without sign-in, or one that changes data without coming from the BrightSmile website, When it is made, Then it is refused. (source: NFR-006)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 002-T039 | Write the per-role matrix in `clinic-api/tests/identity/test_role_matrix.py`: a  | 6.0 | qa-automation, auth-security | no | - |
| 002-T040 | Write scoping tests in `clinic-api/tests/identity/test_scoping.py`: a patient ca | 7.0 | qa-automation, auth-security | no | - |
| 002-T041 | Write tests in `clinic-api/tests/identity/test_unauthenticated_and_csrf.py`: eve | 4.0 | qa-automation, auth-security | no | - |
| 002-T042 | Write component tests in `clinic-web/tests/identity/RoleGuard.test.tsx` for role | 4.0 | qa-automation, frontend-react | no | - |
| 002-T043 | Add scoping methods to `clinic-api/app/identity/access.py`: `require_role`, `sco | 7.0 | backend-python, auth-security | no | 002-T017 |
| 002-T044 | Implement patient-account search by phone number or name for receptionist and ma | 5.0 | backend-python, postgres | no | 002-T043 |
| 002-T045 | Add `GET /api/patients/search` to `clinic-api/app/identity/api/patient_admin_rou | 4.0 | api-design, backend-python | no | 002-T044, 002-T018 |
| 002-T046 | Add role-guarded routes and the post-sign-in redirect per role in `clinic-web/sr | 5.0 | frontend-react, auth-security | no | 002-T019 |
| 002-T047 | Build the patient search screen in `clinic-web/src/identity/PatientSearch.tsx` | 6.0 | frontend-react | no | 002-T019 |

### S-002-US5 Practice manager manages staff accounts — P1/must · 5 SP (low, llm)

As a practice manager (P-04), I want to create receptionist and dentist accounts, assign receptionists to a clinic, reset passwords and deactivate accounts so that the right people can use reception and dentist screens and a person who leaves loses access at once.
Depends on: S-002-US4 · Sources: FR-005, FR-004, NFR-006

- [AC-S-002-US5-1] Given the manager is on the staff screen, When they create a receptionist with name, username, initial password and clinic, Then the account exists, is active and is assigned to that clinic. (source: FR-005)
- [AC-S-002-US5-2] Given the manager creates a dentist account, When it is saved, Then the dentist can sign in and see their own day. (source: FR-005)
- [AC-S-002-US5-3] Given a receptionist is assigned to one clinic, When the manager assigns them to another clinic, Then the receptionist's access follows the new clinic at once. (source: FR-005, FR-004)
- [AC-S-002-US5-4] Given an active staff account, When the manager deactivates it, Then the person cannot sign in and an existing session is refused on its next request. (source: FR-005)
- [AC-S-002-US5-5] Given a username already exists, When the manager creates another with the same username, Then the system refuses. (source: FR-005)
- [AC-S-002-US5-6] Given a person who is not the practice manager, When they try to create, change or deactivate a staff account, Then the system refuses. (source: FR-005, FR-004)
- [AC-S-002-US5-7] Given the manager is the only active manager, When they try to deactivate their own account, Then the system refuses. (source: FR-005)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 002-T048 | Write tests in `clinic-api/tests/identity/test_staff_admin_api.py`: create recep | 6.0 | qa-automation, auth-security | no | - |
| 002-T049 | Write component tests in `clinic-web/tests/identity/StaffAdmin.test.tsx` for cre | 3.0 | qa-automation, frontend-react | no | - |
| 002-T050 | Implement create, update, assign clinic, deactivate, activate and password reset | 6.0 | backend-python, auth-security | no | 002-T009, 002-T011, 002-T043 |
| 002-T051 | Implement `GET/POST /api/staff`, `PATCH /api/staff/{id}`, `POST /api/staff/{id}/ | 5.0 | api-design, backend-python | no | 002-T050, 002-T018 |
| 002-T052 | Build the staff screen in `clinic-web/src/identity/StaffAdmin.tsx` | 6.0 | frontend-react | no | 002-T019 |
| 002-T053 | Create the set-up command that creates the first manager account from a secret s | 4.0 | backend-python, auth-security | no | 002-T050 |

### S-002-US6 Practice manager erases a patient's data on request — P1/must · 8 SP (low, llm)

As a practice manager (P-04), I want to erase a patient's personal data on request within 30 days and have old sign-in codes and idle accounts purged on schedule so that BrightSmile complies with the DPDP Act while appointment counts stay correct.
Depends on: S-002-US4 · Sources: NFR-007, FR-004

- [AC-S-002-US6-1] Given the manager is on the erasure screen, When they find a patient account by phone number and confirm erasure, Then the request is recorded with its date and the account can no longer sign in. (source: NFR-007)
- [AC-S-002-US6-2] Given an erasure was confirmed, When the process completes (within 30 days of the request), Then the account, the person records of the account holder and family members, and the stored messages hold no name, phone number or birth year. (source: NFR-007)
- [AC-S-002-US6-3] Given the erased patient had appointments, When erasure completes, Then the appointment rows remain without any personal link. (source: NFR-007)
- [AC-S-002-US6-4] Given the system stores personal data, When the stored fields are reviewed, Then only name, phone number, family members' names and birth years, appointments, treatment type and message choice are held; no clinical data. (source: NFR-007)
- [AC-S-002-US6-5] Given a signed-in user who is not the practice manager, When they try to use erasure, Then it is refused. (source: NFR-007, FR-004)
- [AC-S-002-US6-6] Given logs are inspected, When any sign-in or erasure activity is searched, Then no name, phone number or birth year appears. (source: NFR-007)
- [AC-S-002-US6-7] Given sign-in codes and old personal data exist, When retention periods pass (sign-in codes 24 hours, accounts idle for 24 months, staff 24 months after deactivation), Then they are deleted or anonymised; messages (90 days) and appointments (24 months) follow the same rule in the features that own them. (source: NFR-007)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 002-T054 | Write tests in `clinic-api/tests/identity/test_erasure.py`: request recorded wit | 7.0 | qa-automation, postgres | no | - |
| 002-T055 | Write tests in `clinic-api/tests/identity/test_retention_jobs.py`: sign-in codes | 5.0 | qa-automation, backend-python | no | - |
| 002-T056 | Write tests in `clinic-api/tests/identity/test_no_pii_in_logs.py` that run sign- | 4.0 | qa-automation, auth-security | no | - |
| 002-T057 | Write component tests in `clinic-web/tests/identity/ErasureAdmin.test.tsx` for f | 3.5 | qa-automation, frontend-react | yes | - |
| 002-T058 | Implement erasure (record request, deactivate, anonymise persons and account in  | 11.0 | backend-python, postgres | no | 002-T009, 002-T014, 002-T044 |
| 002-T059 | Implement the retention jobs and register them and the erasure retry at applicat | 7.0 | backend-python, postgres | no | 002-T058 |
| 002-T060 | Add `GET` and `POST /api/patient-accounts/{id}/erasure` to `clinic-api/app/ident | 4.0 | api-design, backend-python | no | 002-T045, 002-T058 |
| 002-T061 | Build the erasure admin screen in `clinic-web/src/identity/ErasureAdmin.tsx` | 5.5 | frontend-react | no | 002-T047 |

### S-002-US7 Reception deactivates a patient account — P3/should · 2 SP (low, llm)

As a receptionist (P-02), I want to deactivate a patient account when a phone number was taken over or the patient asks so that nobody can sign in with that account, which is the agreed mitigation for the accepted SIM-swap risk.
Depends on: S-002-US6 · Sources: NFR-006, FR-004

- [AC-S-002-US7-1] Given a receptionist finds a patient account by phone number or name, When they deactivate it, Then the patient cannot sign in and an open session is refused on its next request. (source: NFR-006)
- [AC-S-002-US7-2] Given a deactivated patient account, When the practice manager reactivates it, Then the patient can sign in again. (source: NFR-006)
- [AC-S-002-US7-3] Given a dentist or a patient, When they try to deactivate a patient account, Then it is refused. (source: NFR-006, FR-004)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 002-T062 | Write tests in `clinic-api/tests/identity/test_patient_deactivation.py`: recepti | 3.0 | qa-automation, auth-security | no | - |
| 002-T063 | Write component tests in `clinic-web/tests/identity/PatientSearch.test.tsx` for  | 2.0 | qa-automation, frontend-react | no | - |
| 002-T064 | Add deactivate and reactivate (who and when recorded) to `clinic-api/app/identit | 2.5 | backend-python | no | 002-T044 |
| 002-T065 | Add `POST /api/patient-accounts/{id}/deactivate` and `/reactivate` to `clinic-ap | 2.5 | api-design, backend-python | no | 002-T060, 002-T064 |
| 002-T066 | Add the deactivate and reactivate buttons to `clinic-web/src/identity/PatientSea | 2.0 | frontend-react | yes | 002-T047 |

### S-SETUP-002 Sign-in, roles and staff accounts: Setup — P1/must · 1 SP (low, llm)

Depends on: - · Sources: E-002, FR-002, FR-003, NFR-006

- [AC-S-SETUP-002-1] Given the setup tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 002-T001 | Create the identity module skeleton in `clinic-api/app/identity/__init__.py` and | 1.5 | backend-python | yes | - |
| 002-T002 | Create `clinic-api/app/identity/settings.py` with the limits as settings (code l | 3.0 | backend-python, auth-security | no | - |
| 002-T003 | Create the web module entry `clinic-web/src/identity/index.ts` exporting the ide | 1.5 | frontend-react | yes | - |

### S-FOUND-002 Sign-in, roles and staff accounts: Foundational prerequisites — P1/must · 8 SP (low, llm)

Depends on: S-SETUP-002, S-FOUND-001 · Sources: E-002, FR-002, FR-003, FR-004, FR-005, NFR-006, NFR-007

- [AC-S-FOUND-002-1] Given the foundational prerequisites tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 002-T004 | Write token tests in `clinic-api/tests/identity/test_tokens.py`: cookie flags `H | 3.5 | qa-automation, auth-security | no | - |
| 002-T005 | Write request-security tests in `clinic-api/tests/identity/test_security_origin_ | 2.5 | qa-automation, auth-security | no | - |
| 002-T006 | Write password tests in `clinic-api/tests/identity/test_passwords.py`: fewer tha | 2.0 | qa-automation, auth-security | no | - |
| 002-T007 | Write access-context tests in `clinic-api/tests/identity/test_access_context.py` | 3.0 | qa-automation, auth-security | no | - |
| 002-T008 | Create test fixtures in `clinic-api/tests/identity/conftest.py`: test database s | 3.5 | qa-automation, backend-python | no | - |
| 002-T009 | Create the four models in `clinic-api/app/identity/models.py` exactly per data-m | 4.5 | data-modeling, postgres | no | - |
| 002-T010 | Create the forward-only Alembic migration `clinic-api/migrations/versions/002_id | 3.0 | postgres, backend-python | no | 002-T009 |
| 002-T011 | Implement argon2id hashing, verification and the 10-character policy in `clinic- | 2.0 | backend-python, auth-security | no | - |
| 002-T012 | Implement signed-JWT cookie issue and read, sliding last-activity, patient 7-day | 4.5 | backend-python, auth-security | no | - |
| 002-T013 | Implement the CSRF header check (double submit with a companion cookie), the `Or | 3.5 | backend-python, auth-security | no | - |
| 002-T014 | Define the ports `MessageSender`, `AppointmentAnonymiser`, `FutureAppointments`  | 2.0 | backend-python | yes | - |
| 002-T015 | Create request and response schemas from `contracts/identity-api.yaml` in `clini | 3.0 | api-design, backend-python | no | - |
| 002-T016 | Implement a log filter that removes names, phone numbers, birth years and codes  | 3.5 | backend-python, observability | yes | - |
| 002-T017 | Implement `AccessContext` and the FastAPI dependency in `clinic-api/app/identity | 4.5 | backend-python, auth-security | no | 002-T009, 002-T012 |
| 002-T018 | Create the router stubs `clinic-api/app/identity/api/__init__.py`, `clinic-api/a | 3.0 | backend-python, api-design | no | 002-T013, 002-T015, 002-T016, 002-T017 |
| 002-T019 | Create the API client with the CSRF header and the session state with role guard | 3.5 | frontend-react, auth-security | no | - |

### S-POLISH-002 Sign-in, roles and staff accounts: Polish & cross-cutting concerns — P1/must · 3 SP (low, llm)

Depends on: S-002-US2, S-002-US3, S-002-US5, S-002-US7 · Sources: E-002, NFR-006, NFR-007, FR-004

- [AC-S-POLISH-002-1] Given the polish & cross-cutting concerns tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 002-T067 | Merge the identity operations of `specs/002-identity-access/contracts/identity-a | 3.0 | api-design | yes | - |
| 002-T068 | Add a contract test that runs every identity operation against the merged contra | 4.0 | qa-automation, api-design | yes | 002-T067 |
| 002-T069 | Add structured events, metrics (sign-in success, failure, lockout, throttled, co | 5.0 | observability, backend-python | no | - |
| 002-T070 | Write the security review checklist for authentication and authorisation changes | 3.0 | auth-security, docs | no | - |
| 002-T071 | Run the scenarios of `specs/002-identity-access/quickstart.md` against staging a | 3.0 | qa-automation | no | 002-T068 |

## E-003 Clinics, dentist hours, leave, treatments and free slots

Clinics and dentists as data, weekly hours and breaks, leave with to-move list, treatment types, free-slot calculation.

### S-003-US1 Clinics and dentists held as data — P1/must · 5 SP (low, llm)

As a practice manager, I want to add, edit and deactivate clinics and dentists in the staff screens so that a third clinic can open and be offered to patients and reception with no code change and no deploy.
Depends on: S-FOUND-003 · Sources: FR-001

- [AC-S-003-US1-1] Given the practice manager is signed in and 2 active clinics exist, When they add a clinic with a name, address and phone number, Then the clinic is saved as active and appears in the clinic list for all roles without any deploy. (source: FR-001)
- [AC-S-003-US1-2] Given a dentist exists, When the manager edits the dentist's name or marks the dentist inactive, Then the change is saved and an inactive dentist is no longer offered for new bookings. (source: FR-001)
- [AC-S-003-US1-3] Given a clinic or dentist that has appointments, When the manager marks it inactive, Then existing appointments are kept unchanged and the record is not deleted. (source: FR-001)
- [AC-S-003-US1-4] Given a signed-in receptionist, dentist or patient, When they try to add, edit or deactivate a clinic or a dentist, Then the system refuses and nothing changes. (source: FR-001)
- [AC-S-003-US1-5] Given a clinic name already in use by an active clinic, When the manager saves a second clinic with the same name, Then the system refuses it and says why. (source: FR-001)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 003-T018 | Write contract tests for `GET/POST /api/clinics`, `PATCH /api/clinics/{clinicId} | 2.0 | qa-automation, api-design | yes | - |
| 003-T019 | Write integration tests (add third clinic visible to patient at once, inactive c | 3.5 | qa-automation, backend-python | yes | - |
| 003-T020 | Create request and response schemas for clinics and dentists (name, address, pho | 1.5 | backend-python, api-design | yes | - |
| 003-T021 | Implement clinic and dentist create, edit, deactivate and list (patients see act | 3.0 | backend-python, postgres | yes | 003-T011, 003-T020 |
| 003-T022 | Implement the clinic and dentist routes with manager-only writes in `clinic-api/ | 2.5 | backend-python, auth-security | no | 003-T021, 003-T012 |
| 003-T023 | Build the Clinics page (clinic list and form, dentist list and form, active togg | 4.5 | frontend-react, frontend-css | no | 003-T015 |
| 003-T024 | Write component tests for the Clinics page (add clinic, deactivate, server refus | 2.5 | qa-automation, frontend-react | yes | - |

### S-003-US2 Treatment types with duration and online flag — P1/must · 3 SP (low, llm)

As a practice manager, I want to maintain treatment types with a duration and an online flag so that patients can book only suitable treatments online and every slot is as long as the treatment needs.
Depends on: S-FOUND-003 · Sources: FR-009, FR-010

- [AC-S-003-US2-1] Given the system is set up, When any signed-in user asks for the treatment list, Then check-up, cleaning and consultation are present as online types of 30 minutes each. (source: FR-009)
- [AC-S-003-US2-2] Given the manager is signed in, When they add a treatment type with a name, a duration and the online flag off, Then the type is saved and is visible to reception but not to patients. (source: FR-009)
- [AC-S-003-US2-3] Given a treatment type, When the manager changes its duration or online flag, Then the change applies to slots and bookings made from then on and does not change existing appointments. (source: FR-009)
- [AC-S-003-US2-4] Given a treatment type, When the manager marks it inactive, Then it is no longer offered for new bookings and existing appointments keep it. (source: FR-009)
- [AC-S-003-US2-5] Given a duration that is not a positive multiple of 30 minutes, When the manager saves a treatment type, Then the system refuses it and says why. (source: FR-009, FR-010)
- [AC-S-003-US2-6] Given a signed-in receptionist, dentist or patient, When they try to add or edit a treatment type, Then the system refuses it. (source: FR-009)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 003-T025 | Write contract tests for `GET/POST /api/treatment-types` and `PATCH /api/treatme | 2.5 | qa-automation, api-design | yes | - |
| 003-T026 | Write integration tests (3 online types present at start, role-based list, durat | 3.5 | qa-automation, backend-python | yes | - |
| 003-T027 | Create treatment-type schemas (`durationMinutes` a positive multiple of 30; `onl | 1.5 | backend-python, api-design | yes | - |
| 003-T028 | Implement treatment-type create, edit, deactivate and role-filtered list (patien | 3.0 | backend-python, postgres | yes | 003-T011, 003-T027 |
| 003-T029 | Implement the treatment-type routes in `clinic-api/app/modules/scheduling/api/tr | 2.0 | backend-python, auth-security | no | 003-T028, 003-T012 |
| 003-T030 | Build the Treatments page (table, add and edit form, online toggle, active toggl | 4.0 | frontend-react, frontend-css | no | 003-T015 |
| 003-T031 | Write component tests for the Treatments page (add 90-minute reception-only type | 2.0 | qa-automation, frontend-react | yes | - |

### S-003-US3 Weekly working hours and breaks per dentist per clinic — P1/must · 5 SP (low, llm)

As a practice manager, I want to set each dentist's weekly working hours and breaks at each clinic so that free slots match when dentists really work, including dentists who split the week between two clinics.
Depends on: S-FOUND-003 · Sources: FR-007, FR-001, FR-008

- [AC-S-003-US3-1] Given a dentist and a clinic, When the manager sets Monday 09:00–17:00 with a break 13:00–14:00, Then the hours and the break are saved and shown again when the week is opened. (source: FR-007)
- [AC-S-003-US3-2] Given a dentist who works Monday at clinic A, When the manager adds Thursday hours at clinic B, Then both are kept and the dentist is shown as working at both clinics on those days. (source: FR-001, FR-007)
- [AC-S-003-US3-3] Given a dentist with hours at clinic A on Monday 09:00–17:00, When the manager saves Monday 15:00–19:00 for the same dentist at clinic B, Then the system refuses it because the dentist cannot be at two clinics at the same time. (source: FR-001, FR-007)
- [AC-S-003-US3-4] Given a weekday's hours, When the manager enters an end that is not after the start, a break outside the hours, or two overlapping breaks, Then the system refuses it and names the problem. (source: FR-007)
- [AC-S-003-US3-5] Given a dentist with weekly hours, When the manager removes a weekday's hours (a day off), Then that weekday no longer produces free slots for that dentist at that clinic. (source: FR-007)
- [AC-S-003-US3-6] Given a signed-in receptionist, dentist or patient, When they try to change weekly hours, Then the system refuses it. A receptionist or dentist may read hours. (source: FR-007)
- [AC-S-003-US3-7] Given appointments already booked outside newly changed hours, When the manager saves the change, Then the hours are saved and the system does not move or cancel those appointments. (source: FR-007, FR-008)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 003-T032 | Write unit tests for hours validation (end after start, break inside window, bre | 2.5 | qa-automation, backend-python | yes | - |
| 003-T033 | Write integration tests (PUT then GET returns the same week, day off by omitting | 4.0 | qa-automation, backend-python | no | - |
| 003-T034 | Write contract tests for `GET/PUT /api/dentists/{dentistId}/clinics/{clinicId}/h | 2.0 | qa-automation, api-design | yes | - |
| 003-T035 | Create weekly-hours schemas (`weekday` 0 to 6, `start` and `end` as HH:MM, `brea | 1.5 | backend-python, api-design | yes | - |
| 003-T036 | Implement the validation rules and the replace-whole-week save in one transactio | 5.0 | backend-python, postgres | no | 003-T011, 003-T035 |
| 003-T037 | Implement `GET` and `PUT` hours routes (manager writes; manager, reception of th | 2.5 | backend-python, auth-security | no | 003-T036, 003-T012 |
| 003-T038 | Add `clinicIds` (clinics where the dentist has hours) and the `clinicId` filter  | 2.0 | backend-python, postgres | yes | 003-T021, 003-T036 |
| 003-T039 | Build the WeeklyHoursEditor and break rows component (seven weekdays, start and  | 5.0 | frontend-react, frontend-css | no | 003-T016 |
| 003-T040 | Build the Dentists and hours page (pick dentist and clinic, load and save the we | 4.0 | frontend-react | no | 003-T039, 003-T015 |
| 003-T041 | Write component tests for the editor and page (save week, break outside hours sh | 2.5 | qa-automation, frontend-react | yes | - |

### S-003-US4 Free slots for a clinic, dentist and treatment — P1/must · 8 SP (low, llm)

As a patient booking online (or receptionist booking for a caller), I want to see the free slots for a clinic, dentist and treatment, and the first available times so that I can pick a time that is really free, and see it within 2 seconds.
Depends on: S-FOUND-003 · Sources: FR-010, FR-001, FR-008, FR-009

- [AC-S-003-US4-1] Given a dentist working Monday 09:00–17:00 at a clinic with a break 13:00–14:00, When free 30-minute slots are requested for that Monday, Then slots start at 09:00, 09:30 and so on on the hour or half hour, none start in 13:00–13:59, and the last one starts at 16:30. (source: FR-010)
- [AC-S-003-US4-2] Given the same dentist with an appointment booked 10:00–10:30, When slots are requested, Then the 10:00 slot is not offered and 10:30 is. (source: FR-010)
- [AC-S-003-US4-3] Given the same dentist is booked at another clinic on that Monday at 11:00–11:30, When slots are requested for this clinic, Then the 11:00 slot is not offered. (source: FR-010, FR-001)
- [AC-S-003-US4-4] Given leave recorded for that dentist from 15:00 to 16:00 on that Monday, When slots are requested, Then no slot overlaps 15:00–16:00. (source: FR-010, FR-008)
- [AC-S-003-US4-5] Given a 90-minute treatment, When slots are requested, Then a slot is offered only if the whole 90 minutes fit in working time without touching a break, leave or booked appointment. (source: FR-010, FR-009)
- [AC-S-003-US4-6] Given a signed-in patient, When they ask for slots, Then only online treatment types are accepted, only slots from now up to the end of the booking horizon are returned, and only active clinics and dentists are included. (source: FR-010, FR-009)
- [AC-S-003-US4-7] Given a clinic with several dentists, When "first available" is requested, Then the 10 earliest free slots across the clinic's dentists are returned in time order, each with its dentist, and asking for the next page returns the following 10. (source: FR-010)
- [AC-S-003-US4-8] Given a date range with no free slot, When slots are requested, Then an empty list is returned (not an error). (source: FR-010)
- [AC-S-003-US4-9] Given a request for slots at a clinic or dentist that is inactive, or a treatment type that is inactive, When it is made, Then no slots are returned. (source: FR-010, FR-001)
- [AC-S-003-US4-10] Given a booking made by another part of the system just before the request, When slots are requested, Then that appointment is already excluded. (source: FR-010)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 003-T042 | Write unit tests for the pure slot maths (hour and half-hour grid, 09:15 start g | 4.0 | qa-automation, backend-python | yes | - |
| 003-T043 | Write unit tests for first available (time order across dentists, tie-break by d | 3.0 | qa-automation, backend-python | yes | - |
| 003-T044 | Write integration tests (patient sees only online types and only within today pl | 4.0 | qa-automation, backend-python | yes | - |
| 003-T045 | Write contract tests for `GET /api/clinics/{clinicId}/slots` and `GET /api/clini | 2.0 | qa-automation, api-design | yes | - |
| 003-T046 | Implement the pure interval functions (subtract intervals, grid walk on :00 and  | 4.0 | backend-python | yes | - |
| 003-T047 | Add the slot queries (one query each for the clinic's dentists' hours with break | 3.0 | postgres, backend-python | yes | 003-T011 |
| 003-T048 | Implement free-slot calculation for one clinic, one date range (at most 31 days) | 6.0 | backend-python, postgres | no | 003-T046, 003-T047, 003-T006 |
| 003-T049 | Implement first available (walk forward in windows, merge in time order, 10 per  | 5.0 | backend-python | no | 003-T048 |
| 003-T050 | Create slot request and response schemas (`Slot`, `SlotPage` with `page`, `pageS | 1.5 | backend-python, api-design | yes | 003-T049 |
| 003-T051 | Implement the slots routes with role rules (patient online types only; reception | 4.0 | backend-python, auth-security | no | 003-T048, 003-T049, 003-T050, 003-T010, 003-T012 |
| 003-T052 | Write the performance test (seed 3 clinics, 10 dentists, 1,000 appointments a we | 4.0 | qa-automation, postgres | no | 003-T051 |

### S-003-US5 Record dentist leave — P2/must · 5 SP (low, llm)

As a practice manager, I want to record a dentist's whole-day or part-day leave and see the appointments that overlap it so that patients are not left booked with an absent dentist and reception can move them.
Depends on: S-FOUND-003 · Sources: FR-008, FR-010

- [AC-S-003-US5-1] Given a dentist, When the manager records leave for whole days from a first day to a last day, Then the leave is saved from the start of the first day to the end of the last day in India time. (source: FR-008)
- [AC-S-003-US5-2] Given a dentist, When the manager records part-day leave with a date, a start time and an end time, Then the leave is saved for exactly that time. (source: FR-008)
- [AC-S-003-US5-3] Given booked appointments that overlap the new leave, When the leave is saved, Then the response and screen list each of those appointments (date, time, clinic, patient name, phone number, treatment) and the system does not change any of them. (source: FR-008)
- [AC-S-003-US5-4] Given an appointment that only partly overlaps the leave, When the leave is saved, Then that appointment is listed too. (source: FR-008)
- [AC-S-003-US5-5] Given cancelled appointments or appointments outside the leave time, When the leave is saved, Then they are not listed. (source: FR-008)
- [AC-S-003-US5-6] Given saved leave, When free slots are requested for those days, Then no slot overlaps the leave. (source: FR-008, FR-010)
- [AC-S-003-US5-7] Given a leave end that is not after its start, or a leave that has already ended, When the manager saves it, Then the system refuses it and says why. (source: FR-008)
- [AC-S-003-US5-8] Given leave entered by mistake, When the manager deletes it, Then slots in that time come back and the appointments are no longer on any to-move list because of it. (source: FR-008)
- [AC-S-003-US5-9] Given a signed-in receptionist, dentist or patient, When they try to record or delete leave, Then the system refuses it. (source: FR-008)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 003-T053 | Write unit tests for leave intervals (whole days to 00:00 IST first day through  | 2.0 | qa-automation, backend-python | yes | - |
| 003-T054 | Write unit tests for the 24-month leave retention job (removes only leave ended  | 1.5 | qa-automation, backend-python | yes | - |
| 003-T055 | Write integration tests (create returns overlapping booked appointments includin | 4.0 | qa-automation, backend-python | yes | - |
| 003-T056 | Write contract tests for `GET/POST /api/dentists/{dentistId}/leave` and `DELETE  | 2.0 | qa-automation, api-design | yes | - |
| 003-T057 | Create leave schemas (whole days `firstDay`, `lastDay`; part day `date`, `startT | 1.5 | backend-python, api-design | yes | - |
| 003-T058 | Implement leave create, list and delete with the IST to UTC conversion in `clini | 4.0 | backend-python, postgres | yes | 003-T009, 003-T011, 003-T057 |
| 003-T059 | Implement the to-move selection for a leave (booked, overlapping `appt.start < l | 4.0 | backend-python | yes | 003-T006, 003-T058 |
| 003-T060 | Implement the leave routes (manager only; create answers with `leave` and `toMov | 3.0 | backend-python, auth-security | no | 003-T058, 003-T059, 003-T012 |
| 003-T061 | Implement the daily 24-month leave retention job and register it with the API's  | 3.0 | backend-python | yes | 003-T058 |
| 003-T062 | Build the ToMoveTable component (date, time IST, clinic, dentist, patient name,  | 3.0 | frontend-react, frontend-css | yes | 003-T016 |
| 003-T063 | Build the Leave page (dentist picker, whole-day or part-day form, leave list wit | 4.0 | frontend-react | no | 003-T062, 003-T015 |
| 003-T064 | Write component tests for the Leave page (whole day, part day, to-move shown, de | 2.5 | qa-automation, frontend-react | yes | - |

### S-003-US6 Reception sees the appointments to move — P2/must · 3 SP (low, llm)

As a receptionist, I want to open a To move list for my own clinic so that I can phone patients whose appointments fall in a dentist's leave and move their visits.
Depends on: S-FOUND-003 · Sources: FR-008

- [AC-S-003-US6-1] Given leave that covers booked appointments at the receptionist's clinic, When the receptionist opens the to-move list, Then those appointments are listed with date, time, dentist, patient name, phone number and treatment, earliest first. (source: FR-008)
- [AC-S-003-US6-2] Given leave that also covers appointments at another clinic, When the receptionist asks for the list, Then only their own clinic's appointments are returned, and asking for another clinic is refused. (source: FR-008)
- [AC-S-003-US6-3] Given an appointment on the list, When it is moved to a time outside the leave or cancelled, Then it no longer appears on the next read. (source: FR-008)
- [AC-S-003-US6-4] Given nothing to move, When the list is opened, Then it says there is nothing to move. (source: FR-008)
- [AC-S-003-US6-5] Given the practice manager is signed in, When they ask for the to-move list of any clinic, Then it is returned. (source: FR-008)
- [AC-S-003-US6-6] Given a patient or dentist role, When they ask for the to-move list, Then the system refuses it. (source: FR-008)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 003-T065 | Write integration tests (own clinic only, other clinic 403, patient and dentist  | 3.0 | qa-automation, backend-python | yes | - |
| 003-T066 | Write contract tests for `GET /api/clinics/{clinicId}/to-move` in `clinic-api/te | 1.5 | qa-automation, api-design | yes | - |
| 003-T067 | Add the clinic-level to-move query (all leave of the clinic's dentists, booked a | 2.5 | backend-python, postgres | yes | 003-T059 |
| 003-T068 | Implement the to-move route with own-clinic scoping through the access adapter i | 2.5 | backend-python, auth-security | no | 003-T067, 003-T007, 003-T012 |
| 003-T069 | Build the To move page (reception sees own clinic; manager has a clinic picker;  | 4.0 | frontend-react | no | 003-T062, 003-T015 |
| 003-T070 | Register all five pages in the route table with role-based visibility (manager:  | 2.5 | frontend-react, auth-security | no | 003-T017, 003-T023, 003-T030, 003-T040, 003-T063, 003-T069 |
| 003-T071 | Write component tests for the To move page and role-based menu in `clinic-web/sr | 2.5 | qa-automation, frontend-react | yes | - |

### S-SETUP-003 Clinics, dentist hours, leave, treatments and free slots: Setup — P1/must · 1 SP (low, llm)

Depends on: - · Sources: E-003, FR-001, FR-007, FR-008, FR-009, FR-010

- [AC-S-SETUP-003-1] Given the setup tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 003-T001 | Create the cmp-scheduling module skeleton with empty `__init__.py` files in `cli | 1.0 | backend-python | yes | - |
| 003-T002 | Add the scheduling paths and schemas from `specs/003-clinic-schedule-setup/contr | 2.0 | api-design | yes | - |
| 003-T003 | Create TypeScript types for Clinic, Dentist, TreatmentType, WeeklyHours, Leave,  | 2.0 | frontend-react | yes | - |

### S-FOUND-003 Clinics, dentist hours, leave, treatments and free slots: Foundational prerequisites — P1/must · 8 SP (low, llm)

Depends on: S-SETUP-003, S-FOUND-002 · Sources: E-003, FR-001, FR-007, FR-008, FR-009, FR-010

- [AC-S-FOUND-003-1] Given the foundational prerequisites tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 003-T004 | Create SQLAlchemy models Clinic, Dentist, TreatmentType, WorkingHours, WorkingBr | 6.0 | data-modeling, backend-python | no | - |
| 003-T005 | Create the Alembic migration in `clinic-api/alembic/versions/0003_scheduling.py` | 5.0 | postgres, backend-python | no | 003-T004 |
| 003-T006 | Define the AppointmentsPort protocol (`busy_intervals(dentist_ids, start, end)`  | 2.0 | backend-python, api-design | yes | - |
| 003-T007 | Create the access adapter over cmp-identity's access context with `require_manag | 4.0 | auth-security, backend-python | no | - |
| 003-T008 | Write unit tests for IST conversion (date plus IST time of day to UTC instant, w | 2.0 | qa-automation, backend-python | yes | - |
| 003-T009 | Implement the IST helpers in `clinic-api/app/modules/scheduling/ist.py` so T008  | 2.0 | backend-python | yes | - |
| 003-T010 | Add structured logging helpers (ids and correlation id only, never names or phon | 3.0 | observability, backend-python | yes | - |
| 003-T011 | Create the repository base (session handling and the `booking_horizon_days` read | 2.0 | backend-python, postgres | yes | 003-T004 |
| 003-T012 | Create the scheduling router aggregator and register it with the application in  | 1.5 | backend-python, api-design | yes | 003-T007 |
| 003-T013 | Create pytest fixtures (database session, manager, receptionist per clinic, dent | 5.0 | qa-automation, backend-python | no | 003-T006 |
| 003-T014 | Write a reusable port contract test run against `EmptyAppointments` and the fake | 3.0 | qa-automation, backend-python | yes | 003-T006 |
| 003-T015 | Create the API client wrapper for the scheduling routes (cookie session, CSRF he | 3.0 | frontend-react, auth-security | no | 003-T003 |
| 003-T016 | Create IST display and input helpers in `clinic-web/src/features/scheduling/time | 2.0 | frontend-react | yes | - |
| 003-T017 | Create the route table with an empty page list for the scheduling screens in `cl | 1.0 | frontend-react | yes | - |

### S-POLISH-003 Clinics, dentist hours, leave, treatments and free slots: Polish & cross-cutting concerns — P2/should · 3 SP (low, llm)

Depends on: S-003-US1, S-003-US2, S-003-US3, S-003-US4, S-003-US5, S-003-US6 · Sources: E-003, FR-001, FR-007, FR-008, FR-009, FR-010

- [AC-S-POLISH-003-1] Given the polish & cross-cutting concerns tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 003-T072 | Write a role-matrix test that calls every scheduling route as manager, reception | 4.0 | qa-automation, auth-security | no | - |
| 003-T073 | Write a test that captures log output of the leave, to-move and slots routes and | 3.0 | qa-automation, observability | yes | - |
| 003-T074 | Write the third-clinic-as-data test (add clinic, dentist, hours through the API  | 3.0 | qa-automation, backend-python | yes | - |
| 003-T075 | Document the AppointmentsPort for the cmp-booking team (methods, status rules, i | 2.0 | docs | yes | - |
| 003-T076 | Reconcile `clinic-api/contracts/clinic-api-v1.openapi.yaml` with the implemented | 3.0 | api-design, qa-automation | no | 003-T022, 003-T029, 003-T037, 003-T051, 003-T060, 003-T068 |
| 003-T077 | Run the validation scenarios in `specs/003-clinic-schedule-setup/quickstart.md`, | 5.0 | qa-automation, docs | no | 003-T052, 003-T070, 003-T072, 003-T073, 003-T074 |

## E-004 Patient online booking

Patient books a slot online (clinic, treatment, dentist or first available), never double-booked, with channel choice remembered.

### S-004-US1 Book a free slot online — P1/must · 8 SP (low, llm)

As a patient (P-01) booking from a phone, I want to book a free slot online by choosing a clinic, an online treatment and a dentist or "first available" so that I get an appointment without phoning the clinic during clinic hours.
Depends on: S-FOUND-004, S-003-US4, S-002-US1 · Sources: FR-011, NFR-002, NFR-010

- [AC-S-004-US1-1] Given a signed-in patient on the first booking screen, When they choose themselves, a clinic and "check-up", Then they can continue to the dentist and slot step, and only the online treatment types (check-up, cleaning, consultation) are offered
- [AC-S-004-US1-2] Given a clinic with several dentists working in the next 30 days, When the patient chooses "first available", Then the earliest free slots across all that clinic's dentists are shown, each with its dentist and time, soonest first
- [AC-S-004-US1-3] Given a patient who chose a named dentist, When they open the day picker, Then only days from today to 30 days after today are offered (1 March shows up to 31 March), and the free slots of that dentist for the chosen day are listed, each on the hour or half hour
- [AC-S-004-US1-4] Given a patient on the confirm screen with a free slot, When they confirm, Then one appointment is created with status "booked" for that patient, clinic, dentist, treatment, start and end, and the booked screen shows clinic, dentist, treatment, date and time in India time
- [AC-S-004-US1-5] Given a confirmed booking, When it is saved, Then a request to send the booking confirmation in the patient's chosen channel is recorded together with the booking (so it cannot be lost) for the confirmation feature, and the patient's screen does not wait for the message to be delivered
- [AC-S-004-US1-6] Given a patient who is not signed in, When they try to open or submit any booking step, Then they are sent to sign-in and nothing is booked
- [AC-S-004-US1-7] Given a patient who asks to book a treatment that patients cannot book online (for example a root canal), When the request reaches the system, Then it is refused with a clear message to phone the clinic, and nothing is booked
- [AC-S-004-US1-8] Given a patient for whom the repeat no-show check (feature 009) says "blocked", When they start to book, Then the page says online booking is not available and shows the clinic's phone number. Until feature 009 exists the check always says "not blocked"
- [AC-S-004-US1-9] Given a new patient who has just signed in, When they book, Then they reach the booked screen in 5 screens or fewer, every tap target is at least 44 px, and no screen needs sideways scrolling on a phone

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 004-T017 | Contract tests for `GET /api/booking/options` and `GET /api/booking/slots` (name | 2.0 | qa-automation, api-design | yes | - |
| 004-T018 | Contract tests for `POST /api/booking/appointments` success 201, 401, 403 blocke | 2.0 | qa-automation, api-design | yes | - |
| 004-T019 | Unit tests for the booking rules (online treatment types only, inactive clinic o | 3.0 | qa-automation, backend-python | yes | - |
| 004-T020 | Integration test: book with a named dentist and with first available, one `appoi | 4.0 | qa-automation, postgres | yes | - |
| 004-T021 | Web test of the four-screen flow, 5 screens or fewer after sign-in, blocked noti | 4.0 | qa-automation, frontend-react | yes | - |
| 004-T022 | Implement `get_options` (clinics, dentists, online treatment types, who = accoun | 3.0 | backend-python | yes | 004-T010 |
| 004-T023 | Implement `book_online` (validate input, blocked check, slot-free fast path, ins | 5.0 | backend-python, postgres | no | 004-T022, 004-T006 |
| 004-T024 | Implement the operations `GET /booking/options`, `GET /booking/slots` and `POST  | 3.0 | backend-python, api-design | no | 004-T012, 004-T023 |
| 004-T025 | Build the who-and-what screen with the clinic and treatment form (online types o | 3.0 | frontend-react, frontend-css | yes | - |
| 004-T026 | Build the dentist choice (named or first available), day strip (today to 30 days | 4.0 | frontend-react, frontend-css | yes | - |
| 004-T027 | Build the slot picker screen in `clinic-web/src/features/booking/pages/SlotPicke | 2.0 | frontend-react | yes | 004-T026 |
| 004-T028 | Build the blocked notice showing the clinic phone number in `clinic-web/src/feat | 2.0 | frontend-react | yes | - |
| 004-T029 | Build the confirm screen (summary of clinic, dentist, treatment, date and time i | 3.0 | frontend-react | yes | 004-T016, 004-T027 |
| 004-T030 | Build the booked screen (clinic, dentist, treatment, date and time in IST) in `c | 2.0 | frontend-react | yes | - |
| 004-T031 | Add the `/book` routes for the four screens, with redirect to sign-in when not s | 2.0 | frontend-react, auth-security | no | 004-T025, 004-T027, 004-T029, 004-T030 |
| 004-T032 | Add structured logs (ids and a correlation id only, never name, phone or birth y | 2.0 | backend-python, observability | yes | 004-T023 |

### S-004-US2 A slot is never booked twice — P1/must · 5 SP (low, llm)

As a patient (P-01) booking from a phone, I want to be told at once when a slot was just taken, see the next free slots, and have a repeated confirm book only once so that I never get a double or duplicate booking and can pick another time without starting again.
Depends on: S-FOUND-004 · Sources: FR-012

- [AC-S-004-US2-1] Given two patients who both chose the same dentist and slot, When both confirm at nearly the same time, Then exactly one booking is made and the other patient is told the slot was just taken
- [AC-S-004-US2-2] Given a patient told the slot is taken, When the message is shown, Then it comes with the next free slots (same clinic, treatment and dentist choice as before) and the patient can choose one and confirm without re-entering clinic or treatment
- [AC-S-004-US2-3] Given a patient who confirms and the screen does not respond, When the same confirm request is sent again with the same request key, Then the system returns the original booking and does not create a second appointment
- [AC-S-004-US2-4] Given a slot that is already booked, When a booking for it arrives by any route, Then it is never saved as a second active appointment for that dentist
- [AC-S-004-US2-5] Given a dentist who already has an active appointment (including a longer one made by reception), When a booking is requested whose time overlaps it even in part, Then it is refused as "slot taken"
- [AC-S-004-US2-6] Given a patient who is told "slot taken" and there are no further free slots in the next 30 days for their choice, When the answer is shown, Then the patient is told no slots are free and offered the clinic's phone number

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 004-T033 | Unit tests for key format (1 to 64 characters of letters, digits and hyphen), re | 2.0 | qa-automation, backend-python | yes | - |
| 004-T034 | Integration test: second booking of a taken slot returns `slot_taken` with up to | 3.0 | qa-automation, postgres | yes | - |
| 004-T035 | Integration test: repeated request with the same key and body returns the origin | 3.0 | qa-automation, postgres | yes | - |
| 004-T036 | Contract tests for 409 `slot_taken` body, 200 replay with header `Idempotent-Rep | 2.0 | qa-automation, api-design | yes | - |
| 004-T037 | Web test: "slot taken" returns to the slot picker with the new slots, a notice,  | 3.0 | qa-automation, frontend-react | yes | - |
| 004-T038 | Implement the request key claim (`INSERT ... ON CONFLICT DO NOTHING` on `(patien | 3.0 | backend-python, postgres | yes | 004-T006 |
| 004-T039 | In `book_online` claim the key first, map the exclusion violation (SQLSTATE 23P0 | 4.0 | backend-python, postgres | no | 004-T023, 004-T038 |
| 004-T040 | Require the `Idempotency-Key` header, return 409 with `next_slots`, return 200 w | 3.0 | backend-python, api-design | yes | 004-T024, 004-T039 |
| 004-T041 | Build the slot-taken notice in `clinic-web/src/features/booking/components/SlotT | 2.0 | frontend-react | yes | - |
| 004-T042 | Send a new `Idempotency-Key` per confirm and reuse it only for a retry of the sa | 3.0 | frontend-react | yes | 004-T016, 004-T027, 004-T041 |
| 004-T043 | Show "no free slots" with the clinic phone number when the next-slot list is emp | 2.0 | frontend-react | yes | 004-T026 |

### S-004-US3 Choose SMS or WhatsApp, remembered for next time — P1/must · 3 SP (low, llm)

As a patient (P-01) booking from a phone, I want to choose SMS or WhatsApp for messages about my appointment and have the choice remembered for next time so that I get messages in the channel I prefer without choosing it again every time.
Depends on: S-FOUND-004, S-002-US2 · Sources: FR-013

- [AC-S-004-US3-1] Given a patient who has never booked online, When the confirm screen opens, Then SMS is selected
- [AC-S-004-US3-2] Given a patient who selects WhatsApp and confirms, When the booking is saved, Then the appointment holds channel WhatsApp and the patient's remembered choice becomes WhatsApp
- [AC-S-004-US3-3] Given a patient whose remembered choice is WhatsApp, When they start another booking, Then the confirm screen starts with WhatsApp selected and they can change it
- [AC-S-004-US3-4] Given a booking that fails because the slot was taken, When the patient is shown other slots, Then their channel choice on screen is kept, and the remembered choice changes only when a booking is confirmed
- [AC-S-004-US3-5] Given a channel value other than SMS or WhatsApp in a request, When it is submitted, Then it is refused and nothing is booked

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 004-T044 | Unit tests for channel values (only `sms` or `whatsapp`, default `sms`) in `clin | 1.0 | qa-automation, backend-python | yes | - |
| 004-T045 | Integration test: `preferred_channel` default `sms`, set on confirmed booking, u | 3.0 | qa-automation, postgres | yes | - |
| 004-T046 | Web test: channel preselected from the options, changeable, kept after "slot tak | 3.0 | qa-automation, frontend-react | yes | - |
| 004-T047 | Implement `get_preferred_channel` and `set_preferred_channel` on the patient acc | 2.0 | backend-python | yes | - |
| 004-T048 | Set the remembered channel inside the booking transaction and return `preferred_ | 4.0 | backend-python | yes | 004-T039, 004-T047 |
| 004-T049 | Build the SMS or WhatsApp choice (two 44 px options) in `clinic-web/src/features | 2.0 | frontend-react, frontend-css | yes | - |
| 004-T050 | Add the channel choice to the confirm screen, preselected from `preferred_channe | 3.0 | frontend-react | yes | 004-T029, 004-T048, 004-T049 |

### S-004-US4 Prove that concurrent bookings never overlap — P1/must · 5 SP (low, llm)

As a member of the delivery team, I want to run a repeatable test in which many patients try to book the same dentist and slot at once so that we can prove before the 1 March 2027 go-live that no dentist ever has two overlapping appointments (QA-003).
Depends on: S-FOUND-004 · Sources: FR-012, NFR-002

- [AC-S-004-US4-1] Given a free slot and 30 simultaneous booking attempts for it, When all complete, Then exactly one is booked, 29 are told "slot taken", and 0 overlapping active appointments exist for that dentist
- [AC-S-004-US4-2] Given 1,000 concurrent-attempt runs, When the suite finishes, Then 0 overlapping active appointments for one dentist are found in 100% of the runs
- [AC-S-004-US4-3] Given a run that includes up to 100 simultaneous attempts (the design load), When it finishes, Then the same result holds
- [AC-S-004-US4-4] Given repeated attempts that carry the same request key, When the run finishes, Then they produce one appointment each, not more
- [AC-S-004-US4-5] Given the test is part of the delivery pipeline, When it fails, Then the release is stopped

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 004-T051 | Build the concurrency harness (barrier-synchronised attempts on separate connect | 8.0 | qa-automation, backend-python | no | - |
| 004-T052 | Test: 30 simultaneous attempts on one slot give exactly 1 booked and 29 `slot_ta | 3.0 | qa-automation, backend-python | yes | 004-T051 |
| 004-T053 | Test: 1,000 runs with 2 to 100 simultaneous attempts, some runs mixing a longer  | 7.0 | qa-automation, backend-python | no | 004-T051 |
| 004-T054 | Test: simultaneous attempts that share one request key produce one appointment p | 4.0 | qa-automation, backend-python | yes | 004-T051 |
| 004-T055 | Add the concurrency suite as a release-blocking step in the pipeline file `clini | 3.0 | devops-ci | no | 004-T053 |
| 004-T056 | Run the suite on staging-like infrastructure and record runs, failures and maxim | 5.0 | qa-automation, docs | no | 004-T052, 004-T053, 004-T054 |

### S-004-US5 Booking is quick on a phone network — P2/should · 5 SP (low, llm)

As a patient (P-01) on a 4G phone, I want free slots to appear within 2 seconds and my confirmed booking within 3 seconds so that I do not give up on a slow screen and book online instead of phoning.
Depends on: S-FOUND-004, S-003-US4 · Sources: NFR-002

- [AC-S-004-US5-1] Given 100 concurrent simulated patients, When they open the slot picker, Then 95% of slot lists are shown within 2 seconds on a 4G-like connection, and the server answers 95% within 500 ms
- [AC-S-004-US5-2] Given the same load, When patients confirm bookings, Then 95% of confirmations are shown within 3 seconds on a 4G-like connection, and the server answers 95% within 800 ms
- [AC-S-004-US5-3] Given a booking is confirmed, When the request is timed, Then the time to send the confirmation message is not part of it (the message is sent after the booking is saved)
- [AC-S-004-US5-4] Given the check runs on a pull request or before release, When a target is missed, Then the report names which target and the release owner sees it
- [AC-S-004-US5-5] Given a "first available" request across all dentists of a clinic, When it is timed, Then it also meets the 2 second target

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 004-T057 | Create the load-data seed (2 clinics, 6 dentists, 30 days of hours, 450 appointm | 5.0 | backend-python, qa-automation | no | - |
| 004-T058 | Create the load script (100 concurrent simulated patients, one request about eve | 8.0 | backend-python, qa-automation | no | 004-T057 |
| 004-T059 | Define the thresholds (slot list p95 at most 500 ms, booking p95 at most 800 ms, | 3.0 | backend-python, qa-automation | yes | - |
| 004-T060 | Test that the slot read and the booking insert use the `(dentist_id, start_at)`  | 3.0 | qa-automation, postgres | yes | - |
| 004-T061 | Write the client-side 4G check (Fast 4G profile, Chrome and Safari, 20 slot view | 4.0 | docs, qa-automation | yes | - |
| 004-T062 | Run the load script and the 4G check on staging and record results against NFR-0 | 7.0 | qa-automation, docs | no | 004-T058, 004-T059, 004-T061 |

### S-SETUP-004 Patient online booking: Setup — P1/must · 1 SP (low, llm)

Depends on: - · Sources: E-004, FR-011, FR-012, FR-013, NFR-002

- [AC-S-SETUP-004-1] Given the setup tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 004-T001 | Create the booking module package `clinic-api/app/booking/__init__.py` and the t | 2.0 | backend-python, qa-automation | no | - |
| 004-T002 | Create the web feature folder entry `clinic-web/src/features/booking/index.ts` e | 1.0 | frontend-react | yes | - |
| 004-T003 | Register the pytest markers `concurrency` and `performance` in `clinic-api/pypro | 1.0 | qa-automation | yes | - |

### S-FOUND-004 Patient online booking: Foundational prerequisites — P1/must · 5 SP (low, llm)

Depends on: S-SETUP-004, S-FOUND-001 · Sources: E-004, FR-011, FR-012, FR-013, NFR-002

- [AC-S-FOUND-004-1] Given the foundational prerequisites tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 004-T004 | Write Alembic migration `clinic-api/migrations/versions/004a_booking_tables.py`: | 4.0 | postgres, data-modeling | no | - |
| 004-T005 | Write Alembic migration `clinic-api/migrations/versions/004b_patient_channel.py` | 2.0 | postgres | no | 004-T004 |
| 004-T006 | Create SQLAlchemy models `Appointment`, `AppointmentEvent`, `BookingRequest` in  | 2.0 | backend-python, data-modeling | yes | 004-T004 |
| 004-T007 | Create domain errors `SlotTaken`, `NotBookableOnline`, `BookingBlocked`, `Idempo | 1.0 | backend-python | yes | - |
| 004-T008 | Create request and response models from `contracts/booking-api.openapi.yaml` (ch | 2.0 | api-design, backend-python | yes | - |
| 004-T009 | Define the `PolicyPort` (`is_blocked(patient_id)`), `MessagingPort` (`enqueue_bo | 2.0 | backend-python | yes | - |
| 004-T010 | Implement the default adapters `NotBlockedPolicy` (always false), `NoopMessaging | 2.0 | backend-python | yes | 004-T009 |
| 004-T011 | Create metrics (booking attempts, booked, slot_taken, replays, duration histogra | 2.0 | observability, backend-python | yes | - |
| 004-T012 | Create the router skeleton with the patient access dependency from `app/identity | 3.0 | backend-python, auth-security | no | 004-T008 |
| 004-T013 | Create integration fixtures (PostgreSQL 16 with `btree_gist`, two clinics, three | 3.0 | qa-automation, postgres | no | 004-T004, 004-T006 |
| 004-T014 | Merge the operations and schemas of `specs/004-online-booking/contracts/booking- | 2.0 | api-design | yes | - |
| 004-T015 | Create TypeScript types and the API client (`getOptions`, `listSlots`, `bookAppo | 3.0 | frontend-react, api-design | yes | - |
| 004-T016 | Create the booking flow state (who, clinic, treatment, dentist choice, day, slot | 2.0 | frontend-react | yes | 004-T015 |

### S-POLISH-004 Patient online booking: Polish & cross-cutting concerns — P2/should · 3 SP (low, llm)

Depends on: S-004-US1, S-004-US2, S-004-US3, S-004-US4, S-004-US5 · Sources: E-004, FR-011, FR-012, NFR-010

- [AC-S-POLISH-004-1] Given the polish & cross-cutting concerns tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 004-T063 | Test that no patient name, phone number or birth year appears in logs for any bo | 3.0 | qa-automation, backend-python | yes | - |
| 004-T064 | Test authorisation from the token owner only (a request carrying another patient | 5.0 | qa-automation, auth-security | no | - |
| 004-T065 | Record the screen checks (4 screens, tap targets at least 44 px, no sideways scr | 3.0 | qa-automation, docs | no | - |
| 004-T066 | Request the constitution III review of authorisation-affecting code and record t | 2.0 | docs, auth-security | no | 004-T064 |
| 004-T067 | Run the quickstart validation scenarios 1 to 8 and record the result in `specs/0 | 5.0 | qa-automation, docs | no | 004-T056, 004-T062, 004-T065 |

## E-005 Patient appointment list, reschedule, cancel and status history

Patient sees appointments, reschedules and cancels until 4 hours before, freed slot reusable, status history with actor.

### S-005-US1 See my upcoming and past appointments — P1/must · 3 SP (low, llm)

As a patient, I want to see my upcoming and past appointments with their status so that I can check my visits and open one to manage it without phoning the clinic.
Depends on: S-FOUND-005, S-004-US1 · Sources: FR-015, FR-024

- [AC-S-005-US1-1] Given a signed-in patient with two upcoming and three past appointments, When they open "My appointments", Then the upcoming ones are listed soonest first and the past ones most recent first, each with clinic, dentist, treatment, date, time in IST and status
- [AC-S-005-US1-2] Given an account that also holds appointments for another person on the same account, When the account holder opens the list, Then those appointments appear too and each shows the name of the person it is for
- [AC-S-005-US1-3] Given another patient's appointment exists, When the signed-in patient requests the list or opens that appointment by its identifier, Then it is not shown and the request is refused as not found
- [AC-S-005-US1-4] Given a patient with no appointments, When they open the list, Then a plain message says there are none and offers "Book"
- [AC-S-005-US1-5] Given an appointment cancelled by the clinic, When the patient views the list, Then it appears in the past/cancelled part with the status "cancelled by the clinic"

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 005-T018 | Write the failing API test for `GET /api/appointments` (order, status, IST-ready | 2.0 | qa-automation, backend-python | yes | - |
| 005-T019 | Write the failing API test for `GET /api/appointments/{id}` returning 404 for an | 1.5 | qa-automation, backend-python | yes | - |
| 005-T020 | Write the failing web test for the list screen (upcoming first, status labels, e | 2.0 | qa-automation, frontend-react | yes | - |
| 005-T021 | Write the failing web test that the appointment screen shows the clinic phone an | 1.5 | qa-automation, frontend-react | yes | - |
| 005-T022 | Implement `list_for_account` and `get_for_account` (selects by person -> account | 4.0 | backend-python, postgres | no | 005-T007, 005-T009, 005-T010, 005-T012, 005-T018, 005-T019 |
| 005-T023 | Implement the list and get endpoints in `clinic-api/app/modules/booking/router_p | 2.0 | backend-python, api-design | no | 005-T015, 005-T022 |
| 005-T024 | Build the list screen in `clinic-web/src/features/appointments/MyAppointmentsPag | 2.5 | frontend-react | yes | 005-T016, 005-T020 |
| 005-T025 | Build the appointment screen showing detail, status, and the clinic phone when n | 2.5 | frontend-react | yes | 005-T016, 005-T021 |

### S-005-US2 Every status change records who and when — P1/must · 3 SP (low, llm)

As a clinic receptionist, I want every appointment status change and reschedule recorded with who made it, when and why so that a patient cannot dispute a cancellation and the clinic can trust its history.
Depends on: S-FOUND-005 · Sources: FR-024

- [AC-S-005-US2-1] Given a booked appointment, When the patient cancels it, Then a history entry exists with from status "booked", to status "cancelled by the patient", the patient as actor, the time of the change and the reason "patient request"
- [AC-S-005-US2-2] Given a booked appointment, When a patient reschedules it, Then a history entry records the old and new time and dentist, with status booked before and after, the patient as actor and the time
- [AC-S-005-US2-3] Given a receptionist cancels at a patient's request, When the change is saved through the shared status operation, Then the new status is "cancelled by the patient" and the actor is the receptionist; when the clinic itself cancels it is "cancelled by the clinic"
- [AC-S-005-US2-4] Given any code path tries to write a status outside the five allowed values, When it is saved, Then the data store refuses it
- [AC-S-005-US2-5] Given a status change fails, When the transaction ends, Then neither the new status nor a history entry is stored (both or neither)
- [AC-S-005-US2-6] Given history older than 24 months, When the retention job runs, Then history is removed on the same schedule as its appointment's personal link

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 005-T026 | Write the failing unit test for `record_event` (from, to, actor kind and id, UTC | 1.5 | qa-automation, backend-python | yes | - |
| 005-T027 | Write the failing unit test for `change_status` including ASM-014 (reception can | 2.0 | qa-automation, backend-python | yes | - |
| 005-T028 | Write the failing database test: a status outside the five is refused by the CHE | 3.0 | qa-automation, postgres | no | - |
| 005-T029 | Write the failing test that the retention function removes event rows with their | 1.5 | qa-automation, backend-python | yes | - |
| 005-T030 | Implement `record_event` (insert only) in `clinic-api/app/modules/booking/histor | 2.0 | backend-python | yes | 005-T009, 005-T026 |
| 005-T031 | Implement `change_status(session, appointment_id, to_status, actor, reason, pati | 5.0 | backend-python, postgres | no | 005-T030, 005-T027 |
| 005-T032 | Implement the retention function for event rows, run by the maintenance role, in | 3.0 | backend-python, postgres | no | 005-T009, 005-T029 |

### S-005-US3 Cancel an upcoming appointment — P1/must · 5 SP (low, llm)

As a patient, I want to cancel an upcoming appointment until 4 hours before it starts so that the slot is freed for others and I get a confirmation message, or I am told to phone the clinic when it is too late.
Depends on: S-FOUND-005, S-004-US1 · Sources: FR-017, FR-018, FR-024

- [AC-S-005-US3-1] Given a booked appointment starting in more than 4 hours, When the patient taps "Cancel" and confirms, Then the status becomes "cancelled by the patient", the done screen is shown, and the slot appears again in the free slots straight away
- [AC-S-005-US3-2] Given a successful cancel, When it is saved, Then the patient receives a cancellation message in the channel chosen for that appointment, and no reminder is sent for it
- [AC-S-005-US3-3] Given a booked appointment starting in less than 4 hours, When the patient opens it, Then no Cancel or Change time button is shown and the clinic's phone number is shown instead
- [AC-S-005-US3-4] Given the patient kept the screen open past the cut-off, When they confirm a cancel less than 4 hours before the start, Then the request is refused, nothing changes, and the clinic's phone number is shown
- [AC-S-005-US3-5] Given an appointment that is already cancelled, arrived or no-show, When the patient opens it, Then no Cancel or Change time button is shown
- [AC-S-005-US3-6] Given the patient taps Cancel twice, or sends the request again after a slow network, When the second request arrives, Then the appointment is cancelled once, one message is created and the patient sees the same result

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 005-T033 | Write the failing API test for `POST /api/appointments/{id}/cancel` (200 at 4 h  | 4.0 | qa-automation, backend-python | yes | - |
| 005-T034 | Write the failing test that a cancel is atomic (a failing messaging double leave | 4.0 | qa-automation, backend-python | yes | - |
| 005-T035 | Write the failing web test for Cancel, confirm and the done screen in `clinic-we | 3.0 | qa-automation, frontend-react | yes | - |
| 005-T036 | Implement `cancel_online` (re-check cut-off on the server, `change_status` to `c | 8.0 | backend-python, messaging | no | 005-T011, 005-T022, 005-T031, 005-T033, 005-T034 |
| 005-T037 | Implement `POST /api/appointments/{id}/cancel` with the contract's 200/404/409 a | 2.0 | backend-python, api-design | yes | 005-T023, 005-T036 |
| 005-T038 | Build the done screen shared by cancel and reschedule in `clinic-web/src/feature | 3.0 | frontend-react | yes | 005-T016 |
| 005-T039 | Add the Cancel button, the confirm step and the refused-too-late state with the  | 4.0 | frontend-react | yes | 005-T025, 005-T035, 005-T037, 005-T038 |

### S-005-US4 Reschedule an upcoming appointment — P1/must · 8 SP (low, llm)

As a patient, I want to move an upcoming appointment to another free slot at the same clinic for the same treatment so that I keep my visit instead of losing it, with the old slot freed and a message confirming the new time.
Depends on: S-FOUND-005, S-004-US2, S-003-US4 · Sources: FR-016, FR-018, FR-024

- [AC-S-005-US4-1] Given a booked appointment starting in more than 4 hours, When the patient taps "Change time", Then the slot picker shows free slots at the same clinic for the same treatment, for any dentist working there, and no other clinic or treatment
- [AC-S-005-US4-2] Given the patient picks a free slot and confirms, When the change is saved, Then the same appointment now has the new time and dentist, its status stays "booked", the done screen shows the new details, and the old slot is bookable at once
- [AC-S-005-US4-3] Given a successful reschedule, When it is saved, Then the patient receives a message in the chosen channel with the new details, the reminder for the old time is withdrawn and a reminder exists for the new time only (by feature 007)
- [AC-S-005-US4-4] Given two people confirm the same slot at once, When the second confirm arrives, Then it is refused with a "slot just taken" answer, the patient's original appointment is untouched, and the next free slots are shown
- [AC-S-005-US4-5] Given an appointment starting in less than 4 hours, When the patient asks to reschedule, Then the request is refused and the clinic's phone number is shown
- [AC-S-005-US4-6] Given the no-show policy answers "blocked" for this patient, When they try to reschedule, Then the request is refused with a message to phone the clinic, and their existing booking stays booked
- [AC-S-005-US4-7] Given the reschedule cannot be completed (for example the message cannot be created), When the error occurs, Then the appointment stays at its old time and nothing is half-saved
- [AC-S-005-US4-8] Given the patient picks the slot they already hold, When they confirm, Then nothing changes and the patient is told it is the same time

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 005-T040 | Write the failing API test for slots and reschedule (same clinic and treatment o | 5.0 | qa-automation, backend-python | no | - |
| 005-T041 | Write the failing test that a blocked policy double gives 409 `blocked`, a start | 3.0 | qa-automation, backend-python | yes | - |
| 005-T042 | Write the failing concurrency test: 1,000 concurrent reschedule and booking atte | 6.0 | qa-automation, postgres | no | - |
| 005-T043 | Write the failing web test for the slot picker, confirm, slot-taken message and  | 3.0 | qa-automation, frontend-react | yes | - |
| 005-T044 | Implement `list_reschedule_slots` (checks owner, status and cut-off, then calls  | 4.0 | backend-python | yes | 005-T022, 005-T036, 005-T040 |
| 005-T045 | Implement `reschedule_online` (lock row, check state, cut-off and `is_blocked`,  | 12.0 | backend-python, postgres | no | 005-T044, 005-T031, 005-T041, 005-T042 |
| 005-T046 | Implement `GET /api/appointments/{id}/slots` and `POST /api/appointments/{id}/re | 3.0 | backend-python, api-design | yes | 005-T037, 005-T045 |
| 005-T047 | Build the slot picker screen (free slots grouped by day in IST, confirm, slot-ta | 7.0 | frontend-react, frontend-css | no | 005-T016, 005-T043 |
| 005-T048 | Add the "Change time" button linking to the slot picker and wire the done screen | 4.0 | frontend-react | yes | 005-T039, 005-T046, 005-T047 |

### S-005-US5 Open my appointment from the message link — P2/should · 2 SP (low, llm)

As a patient, I want to open my appointment from the link in a confirmation or reminder message, after signing in so that I can reach the right appointment in one tap and no one else can see it.
Depends on: S-FOUND-005 · Sources: FR-015, FR-016, FR-017

- [AC-S-005-US5-1] Given a signed-out patient opens an appointment link, When they finish sign-in, Then they are taken to that appointment and not to the home page
- [AC-S-005-US5-2] Given a signed-in patient opens a link to an appointment on their account, When the page loads, Then the appointment screen shows with the buttons or phone number that apply
- [AC-S-005-US5-3] Given a signed-in patient opens a link to an appointment on another account, When the page loads, Then nothing about it is shown and the answer is "not found"
- [AC-S-005-US5-4] Given a link for an appointment that is cancelled or in the past, When the owner opens it, Then the appointment is shown read only with its status

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 005-T049 | Write the failing web test that a signed-out visit to `/appointments/:id` goes t | 3.0 | qa-automation, frontend-react | yes | - |
| 005-T050 | Implement keeping the target route through sign-in (a `next` value limited to sa | 3.0 | frontend-react, auth-security | no | 005-T049 |
| 005-T051 | Make the `/appointments/:id` route require a session, use `returnTo.ts`, and ren | 5.0 | frontend-react | no | 005-T017, 005-T025, 005-T050 |

### S-SETUP-005 Patient appointment list, reschedule, cancel and status history: Setup — P1/must · 1 SP (low, llm)

Depends on: - · Sources: E-005, FR-024

- [AC-S-SETUP-005-1] Given the setup tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 005-T001 | Create or confirm the backend test packages `clinic-api/tests/unit/booking/__ini | 1.5 | qa-automation, backend-python | yes | - |
| 005-T002 | Create the web feature folder `clinic-web/src/features/appointments/index.ts` an | 1.5 | frontend-react | yes | - |
| 005-T003 | Merge the paths and schemas of `specs/005-manage-appointments/contracts/appointm | 3.0 | api-design | yes | - |

### S-FOUND-005 Patient appointment list, reschedule, cancel and status history: Foundational prerequisites — P1/must · 5 SP (low, llm)

Depends on: S-SETUP-005 · Sources: E-005, FR-017, FR-018, FR-024

- [AC-S-FOUND-005-1] Given the foundational prerequisites tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 005-T004 | Write the failing unit test for the 4-hour rule in `clinic-api/tests/unit/bookin | 2.0 | qa-automation, backend-python | yes | - |
| 005-T005 | Write the failing unit test in `clinic-api/tests/unit/booking/test_statuses.py`  | 1.0 | qa-automation, backend-python | yes | - |
| 005-T006 | Implement the five statuses, actor kinds (`patient`, `staff`, `system`) and reas | 1.5 | backend-python | yes | 005-T005 |
| 005-T007 | Implement `can_change_online(starts_at_utc, now_utc)` with the 4-hour rule in `c | 1.5 | backend-python | yes | 005-T004 |
| 005-T008 | Write Alembic migration `clinic-api/alembic/versions/0005_appointment_event.py`: | 5.0 | postgres, backend-python | no | 005-T006 |
| 005-T009 | Add the `AppointmentEvent` model to `clinic-api/app/modules/booking/models.py` m | 2.0 | backend-python, data-modeling | yes | 005-T008 |
| 005-T010 | Add the no-show policy interface `is_blocked(person_id) -> bool` returning `Fals | 1.0 | backend-python | yes | - |
| 005-T011 | Add the call-only messaging interface (`create_change_notice`, `cancel_reminder` | 2.5 | backend-python, messaging | yes | - |
| 005-T012 | Add the call-only scheduling interface (`list_free_slots(clinic_id, treatment_ty | 2.0 | backend-python, api-design | yes | - |
| 005-T013 | Define the response and error schemas (`Appointment`, `Slot`, `NotChangeableErro | 2.5 | backend-python, api-design | yes | 005-T006 |
| 005-T014 | Add structured logging and counters (cancel, reschedule, refused by cut-off, slo | 2.5 | backend-python | yes | - |
| 005-T015 | Create the patient router skeleton with a dependency that takes the owner from t | 4.0 | backend-python, auth-security | no | 005-T013, 005-T014 |
| 005-T016 | Add the API client with the CSRF header on writes in `clinic-web/src/features/ap | 2.0 | frontend-react | yes | - |
| 005-T017 | Register the routes `/appointments`, `/appointments/:id`, `/appointments/:id/cha | 1.0 | frontend-react | yes | - |

### S-POLISH-005 Patient appointment list, reschedule, cancel and status history: Polish & cross-cutting concerns — P2/should · 3 SP (low, llm)

Depends on: S-005-US1, S-005-US2, S-005-US3, S-005-US4, S-005-US5 · Sources: E-005, FR-015, FR-016, FR-017, FR-018, FR-024

- [AC-S-POLISH-005-1] Given the polish & cross-cutting concerns tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 005-T052 | Write contract tests for all five operations against `clinic-api/contracts/clini | 4.0 | qa-automation, api-design | yes | - |
| 005-T053 | Write the cross-patient authorisation matrix test for all five operations (owner | 4.0 | qa-automation, auth-security | yes | - |
| 005-T054 | Write a test that captures log output of list, cancel and reschedule and asserts | 2.0 | qa-automation, backend-python | yes | - |
| 005-T055 | Write a latency check that list and slots meet 2 s and cancel and reschedule mee | 3.0 | qa-automation, backend-python | yes | - |
| 005-T056 | Style the four screens mobile-first (tap targets at least 44 px, no sideways scr | 3.0 | frontend-css | yes | - |
| 005-T057 | Run the scenarios in `specs/005-manage-appointments/quickstart.md` and record an | 2.0 | qa-automation, docs | no | 005-T048, 005-T051, 005-T052, 005-T053 |

## E-006 Reception day view, check-in, no-show and dentist day

Reception day view per clinic, book/move/cancel for callers and walk-ins, arrived, no-show and undo; dentist read-only day.

### S-006-US1 See the day of my clinic — P1/must · 8 SP (low, llm)

As a receptionist at one clinic, I want to see today's day view of my clinic with one column per dentist and move to other days so that I can run the day from one screen instead of the paper diary.
Depends on: S-FOUND-006, S-FOUND-004, S-003-US3 · Sources: FR-019

- [AC-S-006-US1-1] Given a receptionist of clinic A and three dentists with working hours at clinic A today, When they sign in, Then they see today's date (IST) with three columns, one per dentist, each listing that dentist's appointments in time order with patient name, phone number, treatment and status. (source: FR-019)
- [AC-S-006-US1-2] Given a dentist who works at both clinics today, When the receptionist of clinic A opens the day view, Then the column shows only that dentist's appointments at clinic A. (source: FR-019)
- [AC-S-006-US1-3] Given the day view for today, When the receptionist chooses next day, previous day or picks a date, Then the view shows that date's columns and appointments for their clinic. (source: FR-019)
- [AC-S-006-US1-4] Given a date on which no dentist works at the clinic and no appointment exists (for example a Sunday), When the receptionist opens it, Then the view says no dentists are working that day. (source: FR-019)
- [AC-S-006-US1-5] Given the day view is open, When another receptionist books or changes an appointment, Then the change appears within about 30 seconds without the receptionist reloading. (source: FR-019)
- [AC-S-006-US1-6] Given an appointment in the view, When the receptionist selects it, Then an appointment panel opens with the details and only the actions that apply to its current status and time. (source: FR-019)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 006-T013 | Contract test for `GET /api/reception/day` and `GET /api/reception/appointments/ | 2.4 | qa-automation, api-design | yes | - |
| 006-T014 | Integration test in `tests/integration/reception/test_day_view.py`: one column p | 4.8 | qa-automation, backend-python | no | - |
| 006-T015 | Component test in `tests/reception/DayViewPage.test.tsx`: columns render, next a | 4.8 | qa-automation, frontend-react | no | - |
| 006-T016 | Create the response models DayView, DayColumn, DayAppointment and AppointmentPan | 2.4 | backend-python, api-design | yes | - |
| 006-T017 | Implement the day view query for one clinic and one IST date (appointments, pati | 7.2 | backend-python, postgres | no | 006-T006, 006-T007, 006-T010, 006-T014, 006-T016 |
| 006-T018 | Implement `GET /reception/day` and `GET /reception/appointments/{id}` in `app/mo | 4.8 | backend-python, api-design | no | 006-T017 |
| 006-T019 | Create the day view API client in `src/features/reception/dayApi.ts` | 2.4 | frontend-react | yes | - |
| 006-T020 | Build the day view screen (columns, appointment cards, date navigation, 30-secon | 9.6 | frontend-react, frontend-css | no | 006-T012, 006-T015, 006-T019 |
| 006-T021 | Build the appointment panel (details, history, only the actions listed in `allow | 7.2 | frontend-react | no | 006-T019, 006-T020 |
| 006-T022 | Register the reception route behind the receptionist guard in `src/routes/index. | 2.4 | frontend-react | yes | 006-T011, 006-T020 |

### S-006-US2 Mark a patient as arrived — P1/must · 3 SP (low, llm)

As a receptionist at one clinic, I want to mark a booked patient as arrived when they check in so that the day view shows who is here and the check-in is recorded with who and when.
Depends on: S-FOUND-006, S-005-US2 · Sources: FR-021

- [AC-S-006-US2-1] Given a booked appointment today at the receptionist's clinic, When the receptionist marks it arrived, Then its status becomes arrived in the day view and the change records the receptionist and the time. (source: FR-021)
- [AC-S-006-US2-2] Given an appointment on a future date, When the receptionist opens its panel, Then "Arrived" is not offered. (source: FR-021)
- [AC-S-006-US2-3] Given an appointment already changed by another receptionist (for example cancelled), When the receptionist tries to mark it arrived, Then the system refuses, says the appointment's current status and refreshes the view. (source: FR-021)
- [AC-S-006-US2-4] Given an appointment of the other clinic, When the receptionist tries to mark it arrived by any means, Then the system refuses and nothing changes. (source: FR-021)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 006-T023 | Integration test in `tests/integration/reception/test_arrived.py`: success write | 3.6 | qa-automation, backend-python | yes | - |
| 006-T024 | Component test in `tests/reception/AppointmentPanelArrived.test.tsx`: Arrived of | 3.6 | qa-automation, frontend-react | yes | - |
| 006-T025 | Create StatusChange and StatusConflict models in `app/modules/reception/schemas_ | 1.8 | backend-python | yes | - |
| 006-T026 | Implement `POST /reception/appointments/{id}/arrived` in `app/modules/reception/ | 3.6 | backend-python, api-design | no | 006-T009, 006-T018, 006-T023, 006-T025 |
| 006-T027 | Create the status API client with `markArrived` in `src/features/reception/statu | 1.8 | frontend-react | yes | - |
| 006-T028 | Add the Arrived action and the conflict handling to `src/features/reception/Appo | 3.6 | frontend-react | yes | 006-T021, 006-T024, 006-T027 |

### S-006-US3 Mark a no-show and undo it the same day — P1/must · 3 SP (low, llm)

As a receptionist at one clinic, I want to mark a no-show from 15 minutes after the start and undo it the same day so that no-shows are recorded reliably and mistakes can be fixed.
Depends on: S-FOUND-006, S-005-US2 · Sources: FR-022

- [AC-S-006-US3-1] Given a booked appointment that started 15 minutes ago or more today, When the receptionist marks it a no-show, Then the status becomes no-show and the change records who and when. (source: FR-022)
- [AC-S-006-US3-2] Given a booked appointment that started less than 15 minutes ago, When the receptionist opens its panel, Then "No-show" is not offered and an attempt through the system is refused with the time from which it is allowed. (source: FR-022)
- [AC-S-006-US3-3] Given an appointment marked no-show today, When the receptionist chooses undo on the same day, Then the status returns to booked and the undo records who and when. (source: FR-022)
- [AC-S-006-US3-4] Given an appointment of a day that has ended (after midnight IST), When the receptionist tries to mark a no-show or undo one, Then the system refuses. (source: FR-022)
- [AC-S-006-US3-5] Given an appointment with status arrived, cancelled by the patient or cancelled by the clinic, When the receptionist tries to mark it a no-show, Then the system refuses. (source: FR-022)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 006-T029 | Integration test in `tests/integration/reception/test_no_show.py`: allowed at st | 4.9 | qa-automation, backend-python | no | - |
| 006-T030 | Component test in `tests/reception/AppointmentPanelNoShow.test.tsx`: No-show and | 3.3 | qa-automation, frontend-react | yes | - |
| 006-T031 | Add `POST /reception/appointments/{id}/no-show` and `POST /reception/appointment | 4.9 | backend-python, api-design | no | 006-T026, 006-T029 |
| 006-T032 | Add `markNoShow` and `undoNoShow` to `src/features/reception/statusApi.ts` | 1.6 | frontend-react | yes | 006-T027 |
| 006-T033 | Add the No-show and Undo actions and the allowed-from hint to `src/features/rece | 3.3 | frontend-react | yes | 006-T028, 006-T030, 006-T032 |

### S-006-US4 Find or create a patient — P1/must · 5 SP (low, llm)

As a receptionist at one clinic, I want to find a patient by phone number or name, or create one with name and phone number so that I can start a phone or walk-in booking without creating duplicates.
Depends on: S-FOUND-006, S-002-US4 · Sources: FR-020

- [AC-S-006-US4-1] Given existing patients, When the receptionist searches by part of a phone number or name, Then matching patients are listed with name and phone number only. (source: FR-020)
- [AC-S-006-US4-2] Given a patient who has appointments only at the other clinic, When the receptionist searches for them, Then the patient is found, but no appointment of the other clinic is shown. (source: FR-020)
- [AC-S-006-US4-3] Given no match, When the receptionist enters a name and a phone number, Then a new patient is created and selected for booking. (source: FR-020)
- [AC-S-006-US4-4] Given a phone number that already has an account, When the receptionist tries to create a patient with it, Then the system offers the existing patient instead of creating a duplicate. (source: FR-020)
- [AC-S-006-US4-5] Given a missing name or a phone number that is not valid, When the receptionist saves, Then the system says what to correct and creates nothing. (source: FR-020)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 006-T034 | Integration test in `tests/integration/reception/test_patient_search.py`: at lea | 5.0 | qa-automation, backend-python | no | - |
| 006-T035 | Component test in `tests/reception/PatientSearch.test.tsx`: search, no-match cre | 3.3 | qa-automation, frontend-react | yes | - |
| 006-T036 | Create PatientHit and the create request model (name 1–100 characters after trim | 1.7 | backend-python, api-design | yes | - |
| 006-T037 | Implement `find_patients(q, limit=20)` (case-insensitive contains on name and ph | 5.0 | backend-python, postgres | no | 006-T034 |
| 006-T038 | Implement reception-side validation and mapping (minimum 3, maximum 64 character | 3.3 | backend-python | yes | 006-T036, 006-T037 |
| 006-T039 | Implement `GET /reception/patients` and `POST /reception/patients` in `app/modul | 3.3 | backend-python, api-design | yes | 006-T006, 006-T038 |
| 006-T040 | Create the patient API client in `src/features/reception/patientApi.ts` | 1.7 | frontend-react | yes | - |
| 006-T041 | Build the patient search and create screen in `src/features/reception/PatientSea | 6.7 | frontend-react, frontend-css | no | 006-T035, 006-T040 |

### S-006-US5 Book a patient, including long treatments and walk-ins — P1/must · 8 SP (low, llm)

As a receptionist at one clinic, I want to book any treatment type, including 60 and 90 minute types and walk-ins, with no cut-off so that phone and walk-in patients are booked without double bookings and the paper diary can be typed in before go-live.
Depends on: S-FOUND-006, S-004-US2, S-003-US4 · Sources: FR-020

- [AC-S-006-US5-1] Given a selected patient, When the receptionist chooses a reception-only treatment type (60 or 90 minutes), a dentist and a free slot long enough, Then the appointment is booked at the receptionist's clinic and appears in the dentist's column. (source: FR-020)
- [AC-S-006-US5-2] Given a free slot that starts in 2 hours, When the receptionist books it, Then it is booked, because there is no 4-hour cut-off for reception. (source: FR-020)
- [AC-S-006-US5-3] Given a patient who is present and not booked, When the receptionist books a free slot as a walk-in, Then the appointment is created as a normal appointment and its status is arrived. (source: FR-020)
- [AC-S-006-US5-4] Given two receptionists confirm the same slot at once, When both submit, Then one booking succeeds and the other is told the slot is taken and sees the next free slots. (source: FR-020)
- [AC-S-006-US5-5] Given a free slot on a date more than 30 days ahead, When the receptionist books it, Then the booking is accepted (the 30-day limit applies to online booking only), which also allows typing in the paper diary before go-live. (source: FR-020)
- [AC-S-006-US5-6] Given a slot that is not free (break, leave, existing appointment, or too short for the treatment), When the receptionist looks for slots, Then it is not offered. (source: FR-020)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 006-T042 | Integration test in `tests/integration/reception/test_reception_booking.py`: rec | 5.5 | qa-automation, backend-python | no | - |
| 006-T043 | Concurrency test in `tests/integration/reception/test_booking_concurrency.py`: p | 5.5 | qa-automation, postgres | no | - |
| 006-T044 | Component test in `tests/reception/BookForPatient.test.tsx`: treatment, dentist, | 3.7 | qa-automation, frontend-react | no | - |
| 006-T045 | Create the booking request and response models in `app/modules/reception/schemas | 1.8 | backend-python, api-design | yes | - |
| 006-T046 | Add a no-op messaging interface (`booking_created`, `booking_changed`, `booking_ | 1.8 | backend-python, messaging | yes | - |
| 006-T047 | Implement reception booking (no 4-hour cut-off, no 30-day horizon, idempotency k | 9.2 | backend-python, postgres | no | 006-T009, 006-T042, 006-T043, 006-T045, 006-T046 |
| 006-T048 | Implement `GET /reception/slots` (free slots of the receptionist's clinic for an | 5.5 | backend-python, api-design | no | 006-T047 |
| 006-T049 | Create the booking API client in `src/features/reception/bookingApi.ts` | 1.8 | frontend-react | yes | - |
| 006-T050 | Build the book-for-patient screen (selected patient, treatment, dentist, date, s | 9.2 | frontend-react, frontend-css | no | 006-T041, 006-T044, 006-T049 |
| 006-T051 | Add the free-slot "Book" entry and the walk-in entry to `src/features/reception/ | 3.7 | frontend-react | no | 006-T020, 006-T050 |

### S-006-US6 Reschedule or cancel for a patient — P1/must · 5 SP (low, llm)

As a receptionist at one clinic, I want to move or cancel a patient's appointment at any time, stating whether the patient or the clinic cancelled so that phone changes are handled at once, the freed slot is reusable and the patient is told.
Depends on: S-FOUND-006, S-005-US2 · Sources: FR-020

- [AC-S-006-US6-1] Given a booked appointment at the receptionist's clinic, When they pick another free slot (same clinic, any dentist) and confirm, Then the appointment moves, the old slot is free at once, and the change records who and when. (source: FR-020)
- [AC-S-006-US6-2] Given an appointment starting in 1 hour, When the receptionist reschedules or cancels it, Then it is allowed. (source: FR-020)
- [AC-S-006-US6-3] Given a cancel, When the receptionist states that the patient asked, Then the status becomes cancelled by the patient. (source: FR-020)
- [AC-S-006-US6-4] Given a cancel, When the receptionist states that the clinic cancelled, Then the status becomes cancelled by the clinic. (source: FR-020)
- [AC-S-006-US6-5] Given a rescheduled or cancelled appointment, When the change is saved, Then the patient notice and reminder change are requested from messaging (feature 007). (source: FR-020)
- [AC-S-006-US6-6] Given an appointment that is arrived or no-show, When the receptionist opens its panel, Then reschedule and cancel are not offered. (source: FR-020)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 006-T052 | Integration test in `tests/integration/reception/test_reception_change.py`: resc | 5.0 | qa-automation, backend-python | no | - |
| 006-T053 | Component test in `tests/reception/CancelAndMove.test.tsx`: cancel dialog has no | 3.3 | qa-automation, frontend-react | yes | - |
| 006-T054 | Add reschedule and cancel (same transaction as the event row, reason "moved by r | 5.0 | backend-python, postgres | no | 006-T047, 006-T052 |
| 006-T055 | Add `POST /reception/appointments/{id}/reschedule` and `POST /reception/appointm | 3.3 | backend-python, api-design | yes | 006-T048, 006-T054 |
| 006-T056 | Add `reschedule` and `cancel` to `src/features/reception/bookingApi.ts` | 1.7 | frontend-react | yes | 006-T049 |
| 006-T057 | Build the cancel dialog with the required "patient asked / clinic cancelled" cho | 3.3 | frontend-react | yes | - |
| 006-T058 | Add a move mode (same clinic, any dentist, same treatment) to `src/features/rece | 5.0 | frontend-react | no | 006-T050, 006-T053, 006-T056 |
| 006-T059 | Add the Reschedule and Cancel actions to `src/features/reception/AppointmentPane | 3.3 | frontend-react | yes | 006-T033, 006-T057, 006-T058 |

### S-006-US7 Dentist sees their own day — P1/must · 5 SP (low, llm)

As a dentist at one or both clinics, I want to see my own appointments for today at each clinic, read only, on a phone or the clinic PC so that I know each patient and treatment without looking at the paper diary.
Depends on: S-FOUND-006, S-002-US3 · Sources: FR-023

- [AC-S-006-US7-1] Given a dentist who works at clinic A in the morning and clinic B in the afternoon today, When they sign in, Then they see today's appointments grouped by clinic, each with time, patient name, treatment and status. (source: FR-023)
- [AC-S-006-US7-2] Given other dentists have appointments today, When the dentist opens their day, Then none of the other dentists' appointments are shown. (source: FR-023)
- [AC-S-006-US7-3] Given the dentist's day, When they look for any way to change an appointment, Then none exists, and a change request from a dentist account is refused. (source: FR-023)
- [AC-S-006-US7-4] Given a dentist with no appointments today, When they sign in, Then the screen says there are no appointments today. (source: FR-023)
- [AC-S-006-US7-5] Given a phone-size screen, When the dentist opens their day, Then it is readable without sideways scrolling. (source: FR-023)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 006-T060 | Integration test in `tests/integration/reception/test_dentist_day.py`: grouped b | 4.3 | qa-automation, backend-python | no | - |
| 006-T061 | Component test in `tests/dentist/MyDayPage.test.tsx`: grouping by clinic, empty  | 4.3 | qa-automation, frontend-react | no | - |
| 006-T062 | Create the MyDay response models in `app/modules/reception/schemas_dentist.py` | 2.1 | backend-python, api-design | yes | - |
| 006-T063 | Implement the dentist's day query across clinics for today IST in `app/modules/r | 6.4 | backend-python, postgres | no | 006-T006, 006-T060, 006-T062 |
| 006-T064 | Implement `GET /dentist/my-day` in `app/modules/reception/routes_dentist.py` and | 2.1 | backend-python, api-design | yes | 006-T063 |
| 006-T065 | Create the dentist API client in `src/features/dentist/api.ts` | 2.1 | frontend-react | yes | - |
| 006-T066 | Build the read-only "my day" screen, readable on a phone and a desktop browser,  | 6.4 | frontend-react, frontend-css | no | 006-T012, 006-T061, 006-T065 |
| 006-T067 | Register the dentist route behind the dentist guard in `src/routes/index.tsx` | 2.1 | frontend-react | yes | 006-T022, 006-T066 |

### S-SETUP-006 Reception day view, check-in, no-show and dentist day: Setup — P1/must · 2 SP (low, llm)

Depends on: - · Sources: E-006, FR-019, FR-020, FR-021, FR-022, FR-023

- [AC-S-SETUP-006-1] Given the setup tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 006-T001 | Create the reception package with `app/modules/reception/__init__.py` and `app/m | 3.0 | backend-python | yes | - |
| 006-T002 | Create the web feature folders with `src/features/reception/index.ts` and `src/f | 3.0 | frontend-react | yes | - |
| 006-T003 | Merge the paths and schemas of `specs/006-reception-dentist-day/contracts/recept | 6.0 | api-design | no | - |

### S-FOUND-006 Reception day view, check-in, no-show and dentist day: Foundational prerequisites — P1/must · 5 SP (low, llm)

Depends on: S-SETUP-006 · Sources: E-006, FR-019, FR-020, FR-021, FR-022, FR-023

- [AC-S-FOUND-006-1] Given the foundational prerequisites tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 006-T004 | Write role and scoping tests in `tests/integration/reception/test_scoping.py`: r | 3.3 | qa-automation, auth-security | no | - |
| 006-T005 | Write unit tests for the status rules in `tests/unit/reception/test_status_rules | 3.3 | qa-automation, backend-python | yes | - |
| 006-T006 | Implement the receptionist clinic scope and dentist own-day scope in `app/module | 4.4 | auth-security, backend-python | no | 006-T004 |
| 006-T007 | Implement the pure status rules in `app/modules/reception/status_rules.py` using | 3.3 | backend-python | yes | 006-T005 |
| 006-T008 | Write integration tests for the status service in `tests/integration/reception/t | 3.3 | qa-automation, postgres | yes | - |
| 006-T009 | Implement `app/modules/booking/status_service.py` (`change_status` with `UPDATE  | 5.6 | backend-python, postgres | no | 006-T006, 006-T007, 006-T008 |
| 006-T010 | Add the Alembic migration `alembic/versions/<rev>_appointment_clinic_start_index | 2.2 | postgres | no | - |
| 006-T011 | Add role route guards for receptionist and dentist in `src/routes/guards.tsx` in | 2.2 | frontend-react, auth-security | no | - |
| 006-T012 | Add IST date and time formatting helpers (times shown in IST, English) in `src/l | 2.2 | frontend-react | yes | - |

### S-POLISH-006 Reception day view, check-in, no-show and dentist day: Polish & cross-cutting concerns — P1/must · 5 SP (low, llm)

Depends on: S-006-US1, S-006-US2, S-006-US3, S-006-US4, S-006-US5, S-006-US6, S-006-US7 · Sources: E-006, FR-019, FR-020, FR-021, FR-022, FR-023

- [AC-S-POLISH-006-1] Given the polish & cross-cutting concerns tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 006-T068 | Add a logging test in `tests/integration/reception/test_no_pii_in_logs.py` provi | 3.0 | qa-automation, observability | yes | - |
| 006-T069 | Add structured logs, metrics and traces (OpenTelemetry) for the new endpoints wi | 3.0 | observability, backend-python | yes | 006-T039, 006-T048, 006-T055, 006-T064 |
| 006-T070 | Add a day-view performance test in `tests/performance/test_day_view_load.py` (6  | 4.5 | qa-automation, backend-python | no | - |
| 006-T071 | Run contract tests for every endpoint of this feature against `contracts/clinic- | 4.5 | qa-automation, api-design | no | 006-T003, 006-T018, 006-T026, 006-T031, 006-T039, 006-T055, 006-T064 |
| 006-T072 | Review the clinic-scoping and role changes (constitution principle III) and reco | 3.0 | auth-security, docs | no | 006-T004, 006-T006, 006-T071 |
| 006-T073 | Write the paper-diary dry-run runbook for reception (typing in future appointmen | 3.0 | docs | no | - |
| 006-T074 | Agree with feature 007 whether messages are sent for appointments typed in befor | 1.5 | docs | no | 006-T072 |
| 006-T075 | Run the validation scenarios in `specs/006-reception-dentist-day/quickstart.md`  | 3.0 | qa-automation | no | 006-T067, 006-T069, 006-T070, 006-T071 |
| 006-T076 | Run a usability check with reception staff booking a returning patient by phone  | 4.5 | ux-design, qa-automation | no | 006-T051, 006-T059 |

## E-007 Confirmations, reminders, STOP and SMS fallback

Message templates, confirmations, 24-hour reminders with quiet hours, channel adapters for SMS/WhatsApp, STOP, WhatsApp-to-SMS fallback, reminders-failed list.

### S-007-US1 Patient gets a confirmation when booking or changing — P1/must · 5 SP (low, llm)

As a patient, I want to receive a confirmation in my chosen channel when I book, cancel or reschedule an appointment so that I have proof of the booking (clinic, dentist, treatment, date, time, link) and know exactly what changed.
Depends on: S-004-US1 · Sources: FR-014, FR-031, FR-018

- [AC-S-007-US1-1] Given a patient who chose SMS, When the booking is saved, Then one SMS confirmation is sent within about 30 seconds with the clinic, dentist, treatment, date, time (in IST) and a link to the appointment. (source: FR-014)
- [AC-S-007-US1-2] Given a patient who chose WhatsApp, When the booking is saved, Then the confirmation is sent through WhatsApp with the same content. (source: FR-014)
- [AC-S-007-US1-3] Given a booking that fails (for example the slot was taken), When the patient is told the slot is gone, Then no confirmation is sent. (source: FR-014)
- [AC-S-007-US1-4] Given the message provider is down when a booking is made, When the booking is saved, Then the booking still succeeds and the confirmation is sent as soon as the provider recovers. (source: FR-014)
- [AC-S-007-US1-5] Given a patient who has switched reminders off, When they book, Then they still receive the confirmation. (source: FR-031)
- [AC-S-007-US1-6] Given an appointment that is cancelled or rescheduled, When the change is saved, Then one change notice is sent in the chosen channel (for a reschedule it shows the new clinic, dentist, date and time). (source: FR-018, FR-031)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 007-T030 | Write tests that the confirmation and change notice rows are created in the call | 5.0 | qa-automation, backend-python | no | - |
| 007-T031 | Write a contract test of the facade functions in contracts/messaging-facade.md ( | 3.5 | qa-automation, api-design | yes | - |
| 007-T032 | Build the template parameters (clinic, dentist, treatment, date and time in IST, | 4.0 | backend-python | yes | 007-T020 |
| 007-T033 | Implement `create_confirmation` and `create_change_notice` in `clinic-api/app/mo | 5.0 | backend-python, postgres | no | 007-T007, 007-T030, 007-T032 |
| 007-T034 | Implement the facade `on_booking_created`, `on_appointment_cancelled` and `on_ap | 7.0 | backend-python, api-design | no | 007-T031, 007-T033 |
| 007-T035 | Write and pass an end-to-end test: booking commit, dispatcher cycle, fake provid | 5.5 | qa-automation, backend-python | no | 007-T024, 007-T034 |

### S-007-US2 Patient gets a reminder 24 hours before, never at night — P1/must · 5 SP (low, llm)

As a patient, I want to get a reminder 24 hours before my appointment, never between 21:00 and 08:00 so that I remember to attend or reschedule without being messaged at night.
Depends on: S-007-US1 · Sources: FR-027, FR-030

- [AC-S-007-US2-1] Given an appointment on Tuesday 11:00, When Monday 11:00 IST arrives, Then one reminder is sent in the chosen channel stating clinic, dentist, date, time and a link to reschedule or cancel. (source: FR-027, FR-030)
- [AC-S-007-US2-2] Given an appointment on Tuesday 22:30 (reminder due Monday 22:30), When Monday 20:00 IST arrives, Then the reminder is sent at 20:00 on Monday. (source: FR-027)
- [AC-S-007-US2-3] Given an appointment on Tuesday 03:00 (reminder due Monday 03:00), When Sunday 20:00 IST arrives, Then the reminder is sent at Sunday 20:00, the evening before the due day. (source: FR-027)
- [AC-S-007-US2-4] Given an appointment on Tuesday 08:00 (reminder due Monday 08:00, the end of quiet hours), When Monday 08:00 IST arrives, Then the reminder is sent at 08:00. (source: FR-027)
- [AC-S-007-US2-5] Given a booking made on Monday 20:30 for Tuesday 22:00 (due Monday 22:00, adjusted time 20:00 already passed, now outside quiet hours), When the booking is saved, Then the reminder is sent at once. (source: FR-027)
- [AC-S-007-US2-6] Given a booking made on Monday 21:15 for Tuesday 22:00 (adjusted time passed, now inside quiet hours), When the booking is saved, Then the reminder is sent at 08:00 on Tuesday. (source: FR-027)
- [AC-S-007-US2-7] Given a reminder, When it is built, Then the time shown is in IST and the text comes from the single English catalogue. (source: FR-030)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 007-T036 | Write table tests for `compute_schedule(start_at, now)` covering the spec cases: | 5.5 | qa-automation, backend-python | no | - |
| 007-T037 | Write tests that exactly one reminder row is created per eligible appointment in | 3.5 | qa-automation, backend-python | yes | - |
| 007-T038 | Implement the pure function `compute_schedule` (zoneinfo Asia/Kolkata; quiet hou | 6.0 | backend-python | no | 007-T036 |
| 007-T039 | Implement `create_reminder` (dedupe key `reminder:<appointment_id>:<start_at>`,  | 5.5 | backend-python, postgres | no | 007-T032, 007-T037, 007-T038, 007-T007 |
| 007-T040 | Call `create_reminder` from `on_booking_created` and `on_appointment_rescheduled | 3.0 | backend-python | yes | 007-T034, 007-T039 |
| 007-T041 | Write and pass the dispatch test with the fake clock showing each reminder sent  | 6.5 | qa-automation, backend-python | no | 007-T024, 007-T040 |

### S-007-US3 No wrong reminders: cancelled, rescheduled and short-notice appointments — P1/must · 3 SP (low, llm)

As a patient, I want never to be reminded of an appointment that was cancelled, moved or booked at short notice so that I am not confused by wrong reminders and keep trusting the clinic's messages.
Depends on: S-007-US2 · Sources: FR-028, NFR-005

- [AC-S-007-US3-1] Given an appointment with a queued reminder, When the appointment is cancelled by the patient, by reception or by the clinic, Then the reminder is never sent. (source: FR-028)
- [AC-S-007-US3-2] Given a reminder that is due now but not yet sent, When the appointment is cancelled one second before the send attempt, Then the send is skipped because the appointment is checked again immediately before sending. (source: FR-028, NFR-005)
- [AC-S-007-US3-3] Given an appointment with a queued reminder, When it is rescheduled to a new time at least 24 hours away, Then the old reminder is dropped and exactly one reminder exists, for the new time. (source: FR-028)
- [AC-S-007-US3-4] Given an appointment rescheduled to a time less than 24 hours away, When the change is saved, Then the old reminder is dropped, no new reminder is created and only the change notice is sent. (source: FR-028)
- [AC-S-007-US3-5] Given an appointment booked less than 24 hours before its start, When the booking is saved, Then only the confirmation is sent and no reminder is ever created. (source: FR-028)
- [AC-S-007-US3-6] Given a reminder that has already been sent, When the appointment is later rescheduled, Then a new reminder is created for the new time (if 24 hours or more away). (source: FR-028)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 007-T042 | Write tests for cancel before and at due time (queued row `cancelled`, race with | 6.0 | qa-automation, backend-python | no | - |
| 007-T043 | Implement `cancel_live_reminders` (queued and sending-not-yet-sent rows of the a | 4.0 | backend-python, postgres | yes | 007-T039, 007-T042 |
| 007-T044 | Call `cancel_live_reminders` from `on_appointment_cancelled` and `on_appointment | 2.5 | backend-python | yes | 007-T040, 007-T043 |
| 007-T045 | Verify the dispatcher re-check against T042 (status booked, start in the future, | 5.5 | backend-python | no | 007-T024, 007-T042 |

### S-007-US4 Patient or reception can stop reminders — P1/must · 8 SP (low, llm)

As a patient, I want to stop reminders by replying STOP or by asking reception to switch them off so that I am no longer messaged when I do not want to be, while still getting confirmations and sign-in codes.
Depends on: S-007-US2 · Sources: FR-031, NFR-011

- [AC-S-007-US4-1] Given a patient with a queued reminder, When a genuine STOP reply from their phone number is received, Then their reminders are switched off and the queued reminder is not sent. (source: FR-031)
- [AC-S-007-US4-2] Given reception is on the patient's record, When the receptionist switches reminders off, Then no further reminders are sent for that patient account. (source: FR-031)
- [AC-S-007-US4-3] Given reminders are off for a patient, When the patient books, reschedules or cancels, Then the confirmation or change notice is still sent. (source: FR-031)
- [AC-S-007-US4-4] Given a STOP reply, When it is received, Then it takes effect within 1 hour at the latest (the design target is at once). (source: NFR-011)
- [AC-S-007-US4-5] Given a STOP notification that is not properly signed or comes from a number with no account, When it arrives, Then it is rejected or ignored and no setting changes. (source: FR-031, NFR-011)
- [AC-S-007-US4-6] Given reminders are off, When reception switches them back on at the patient's request, Then reminders are sent again for appointments that are still 24 hours or more away. (source: FR-031; see Assumptions)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 007-T046 | Write STOP tests (signed STOP case-insensitive and trimmed from a known number s | 8.0 | qa-automation, messaging | no | - |
| 007-T047 | Write route tests for `PUT /api/patient-accounts/{accountId}/reminders` (recepti | 6.0 | qa-automation, api-design | no | - |
| 007-T048 | Implement the STOP handler (inbound text equals STOP, find account by phone, `se | 6.0 | backend-python, messaging | no | 007-T022, 007-T028, 007-T046 |
| 007-T049 | Implement the reminders switch route with role and clinic checks through the acc | 6.0 | backend-python, auth-security | no | 007-T022, 007-T047 |
| 007-T050 | Implement `ensure_reminders` (create missing reminders for booked appointments 2 | 9.0 | backend-python, postgres | no | 007-T020, 007-T039, 007-T044, 007-T049 |
| 007-T051 | Write component tests for the reminders switch (shows state, confirms, calls the | 4.0 | qa-automation, frontend-react | yes | - |
| 007-T052 | Implement `RemindersToggle` and the API client function `setRemindersEnabled` in | 9.0 | frontend-react | no | 007-T051 |

### S-007-US5 Reminders are on time and compliant, even when a provider has problems — P1/must · 8 SP (low, llm)

As a practice manager, I want due reminders to go out within 15 minutes, once only, through registered templates, even when a provider is slow or down so that no-shows fall and the clinic stays compliant with Indian messaging rules.
Depends on: S-007-US3 · Sources: NFR-005, NFR-011

- [AC-S-007-US5-1] Given normal load, When reminders fall due, Then at least 99% in a month are sent within 15 minutes of their adjusted due time. (source: NFR-005)
- [AC-S-007-US5-2] Given the provider times out or errors, When a message is sent, Then it is retried (3 attempts, waiting 5 s then 30 s between them) and stays queued if the provider is still unavailable, rather than being dropped. (source: NFR-005)
- [AC-S-007-US5-3] Given many consecutive provider failures (5 within 1 minute), When further messages are due, Then sending to that provider pauses briefly and messages stay queued, and sending resumes when the provider recovers. (source: NFR-005)
- [AC-S-007-US5-4] Given the same message is processed twice (restart, two API instances, repeated provider notification), When it is sent, Then the patient receives it only once, and a repeated delivery receipt changes nothing. (source: NFR-005)
- [AC-S-007-US5-5] Given the oldest due, unsent message is more than 10 minutes late, When the lag is measured, Then an alert is raised. (source: NFR-005)
- [AC-S-007-US5-6] Given the nightly check, When it finds an appointment that should have a reminder but has none, or a message stuck in progress, Then it repairs it and reports the count. (source: NFR-005)
- [AC-S-007-US5-7] Given any message to be sent, When its kind and channel have no approved template configured, Then it is not sent and the problem is reported; SMS goes only through the registered sender ID and DLT templates, and WhatsApp only through approved templates. (source: NFR-011)
- [AC-S-007-US5-8] Given a provider call, When it is made, Then only the templated values (clinic, dentist, date, time, link) and the phone number are sent, and no patient name, phone number or message text appears in logs. (source: NFR-011)
- [AC-S-007-US5-9] Given a delivery receipt that is unsigned or refers to an unknown message, When it arrives, Then it is rejected or ignored. (source: NFR-011)
- [AC-S-007-US5-10] Given messages older than 90 days, When the retention job runs, Then they are deleted. (source: NFR-011)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 007-T053 | Write receipt tests (delivered and failed receipts update status, replay changes | 4.0 | qa-automation, backend-python | yes | - |
| 007-T054 | Write nightly job and retention tests (stuck `sending` rows older than 10 minute | 6.5 | qa-automation, postgres | no | - |
| 007-T055 | Write tests for the lag gauge (age of the oldest due unsent row; over 10 minutes | 3.0 | qa-automation, observability | yes | - |
| 007-T056 | Write compliance tests (every send call used an approved template id of the righ | 5.5 | qa-automation, messaging | no | - |
| 007-T057 | Implement receipt handling (match by provider message id, forward-only status, i | 5.0 | backend-python, messaging | no | 007-T028, 007-T053 |
| 007-T058 | Implement retention (`delete_older_than(90 days)` and `purge_account_messages`)  | 4.0 | backend-python, postgres | no | 007-T007, 007-T054 |
| 007-T059 | Implement the nightly reconciliation job JOB-005 at 03:00 IST guarded by a datab | 7.0 | backend-python, postgres | no | 007-T029, 007-T050, 007-T054, 007-T058 |
| 007-T060 | Add the `reminder_lag_seconds` gauge to `clinic-api/app/modules/messaging/metric | 4.0 | observability, devops-ci | no | 007-T026, 007-T055 |
| 007-T061 | Write and pass the simulated-day timeliness test (at least 99% of reminders sent | 9.0 | qa-automation, backend-python | no | 007-T041, 007-T044, 007-T060 |

### S-007-US6 Provider accounts and templates are registered and ready before go-live — P1/must · 5 SP (low, llm)

As a delivery team member, I want the SMS and WhatsApp provider accounts, DLT registration and templates submitted early, with sandbox accounts in staging and a go-live readiness check so that confirmations, reminders and sign-in codes can go live on 1 March 2027 without being blocked by approvals.
Depends on: S-FOUND-007 · Sources: NFR-011

- [AC-S-007-US6-1] Given the message kinds and channels, When the template catalogue is reviewed, Then there is one English template for each kind and channel in use, each using only the allowed fields, ready for submission. (source: NFR-011)
- [AC-S-007-US6-2] Given the catalogue, When the clinic (with our help) submits DLT registration and the WhatsApp templates, Then each submission, date, owner and status is tracked. (source: NFR-011)
- [AC-S-007-US6-3] Given staging, When a booking is made, Then messages go to provider sandbox accounts and never to real patients. (source: NFR-011)
- [AC-S-007-US6-4] Given the production configuration, When the readiness check runs, Then it lists any template that is not approved or has no identifier configured, and the go-live decision uses that list. (source: NFR-011)
- [AC-S-007-US6-5] Given the chosen providers are not yet decided, When the work starts, Then the provider-specific parts are isolated in one adapter per provider so a provider can be replaced without changing the rest. (source: NFR-011; see Assumptions)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 007-T062 | Write readiness tests (lists templates not approved or without id, passes when a | 3.0 | qa-automation, backend-python | yes | - |
| 007-T063 | Write tests that staging configuration refuses live provider mode and that sandb | 3.0 | qa-automation, backend-python | yes | - |
| 007-T064 | Write the template catalogue document (one English text per kind and channel, al | 4.0 | docs, messaging | yes | - |
| 007-T065 | Create the onboarding tracker (provider selection, SMS provider and WhatsApp pro | 4.0 | docs, messaging | yes | - |
| 007-T066 | Implement the go-live readiness check as `python -m app.modules.messaging.readin | 5.0 | backend-python, messaging | no | 007-T015, 007-T062 |
| 007-T067 | Implement the sandbox guard and the staging template mapping in `clinic-api/app/ | 4.0 | backend-python, devops-ci | no | 007-T002, 007-T063 |
| 007-T068 | Capture real sandbox payloads (receipts, STOP reply, error responses) as fixture | 7.0 | backend-python, messaging | no | 007-T017, 007-T019, 007-T065 |

### S-007-US7 Sign-in code is sent by SMS straight away — P1/must · 3 SP (low, llm)

As a patient, I want my sign-in code to be sent by SMS straight away and to be told at once if it could not be sent so that I can sign in and book without waiting for a code that may never arrive.
Depends on: S-FOUND-007 · Sources: NFR-011, FR-031

- [AC-S-007-US7-1] Given the sign-in feature requests a code for a phone number, When the request is made, Then the SMS is sent during that request and the caller learns at once whether the provider accepted it. (source: NFR-011)
- [AC-S-007-US7-2] Given the SMS provider is down or times out, When a code is requested, Then the caller gets a clear "could not send" result within the timeout and the code is not queued for later delivery. (source: NFR-011)
- [AC-S-007-US7-3] Given a sign-in code message, When it is recorded, Then the code itself is not kept in readable form in the message record or any log. (source: NFR-011)
- [AC-S-007-US7-4] Given a patient who has switched reminders off, When they request a code, Then the code is still sent. (source: FR-031)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 007-T069 | Write tests for `send_sign_in_code` (accepted result, provider down returns `fai | 7.0 | qa-automation, backend-python | no | - |
| 007-T070 | Implement `send_sign_in_code(phone_e164, code) -> SendResult` (one attempt, 5 s  | 11.0 | backend-python, auth-security | no | 007-T007, 007-T013, 007-T015, 007-T017, 007-T069 |

### S-007-US8 Undelivered WhatsApp reminder is sent once by SMS (Release 2) — P2/should · 5 SP (low, llm)

As a patient, I want a WhatsApp reminder that could not be delivered to be sent once by SMS instead so that I still get my reminder and do not miss the appointment.
Depends on: S-007-US5 · Sources: FR-029, FR-028, FR-031

- [AC-S-007-US8-1] Given a WhatsApp reminder that cannot be delivered (provider error after retries, or a failed delivery receipt) and the fallback switch on, When the failure is known, Then one SMS reminder with the same content is sent to the same patient. (source: FR-029)
- [AC-S-007-US8-2] Given a failed-receipt notification is repeated or replayed, When it arrives again, Then no second SMS is created. (source: FR-029)
- [AC-S-007-US8-3] Given the SMS fallback also fails, When the failure is known, Then the appointment is marked "reminder failed". (source: FR-029)
- [AC-S-007-US8-4] Given the fallback switch is off, When a WhatsApp reminder cannot be delivered, Then no SMS is sent and the appointment is marked "reminder failed". (source: FR-029; see Assumptions)
- [AC-S-007-US8-5] Given a patient who chose SMS and the SMS reminder fails, When the failure is known, Then the appointment is marked "reminder failed" and no other message is sent. (source: FR-029)
- [AC-S-007-US8-6] Given the fallback SMS is sent, When the patient has replied STOP in the meantime or the appointment has been cancelled, Then the SMS is not sent. (source: FR-029, FR-028, FR-031)
- [AC-S-007-US8-7] Given a WhatsApp reminder that is delivered, When the receipt arrives, Then no SMS is sent. (source: FR-029)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 007-T071 | Write fallback tests (WhatsApp final failure or failed receipt creates one SMS,  | 7.0 | qa-automation, backend-python | no | - |
| 007-T072 | Create expand-only migration `clinic-api/alembic/versions/007_02_reminder_fallba | 4.5 | postgres, data-modeling | no | 007-T006 |
| 007-T073 | Add the two columns to the `Message` model in `clinic-api/app/modules/messaging/ | 2.5 | backend-python, postgres | yes | 007-T007, 007-T072 |
| 007-T074 | Implement the fallback (`INSERT ... ON CONFLICT (original_message_id) DO NOTHING | 9.0 | backend-python, messaging | no | 007-T024, 007-T071, 007-T073 |
| 007-T075 | Call the fallback from the dispatcher on final failure and from receipt handling | 7.0 | backend-python | no | 007-T057, 007-T074 |

### S-007-US9 Reception sees tomorrow's failed reminders (Release 2) — P2/should · 5 SP (low, llm)

As a receptionist, I want to open a "Reminders failed" screen listing tomorrow's appointments at my clinic whose reminder could not be delivered so that I can phone those patients in the afternoon and avoid no-shows.
Depends on: S-007-US8, S-006-US1 · Sources: FR-033, FR-028

- [AC-S-007-US9-1] Given tomorrow has appointments marked "reminder failed", When a receptionist opens "Reminders failed", Then they see exactly those appointments at their own clinic with time, patient name, phone number, dentist, treatment and chosen channel. (source: FR-033)
- [AC-S-007-US9-2] Given a failed-reminder appointment is cancelled, When the list is refreshed, Then it no longer appears. (source: FR-033)
- [AC-S-007-US9-3] Given a receptionist of one clinic, When they open the list, Then they never see another clinic's appointments; the practice manager sees both clinics. (source: FR-033)
- [AC-S-007-US9-4] Given appointments whose reminders were delivered, are still queued, or were never created (booked less than 24 hours ahead), When the list is shown, Then they do not appear. (source: FR-033, FR-028)
- [AC-S-007-US9-5] Given no reminder failed for tomorrow, When the list is opened, Then an empty state says so. (source: FR-033)
- [AC-S-007-US9-6] Given the Release 2 feature flag is off, When a user looks for the screen, Then it is not shown. (source: FR-033)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 007-T076 | Write tests for the list (tomorrow in IST only, status booked only, own clinic o | 5.5 | qa-automation, api-design | no | - |
| 007-T079 | Write component tests for the screen (list, empty state, error state, hidden whe | 5.0 | qa-automation, frontend-react | no | - |
| 007-T077 | Implement the list query and `GET /api/reception/reminders-failed` behind the fl | 7.5 | backend-python, api-design | no | 007-T020, 007-T073, 007-T076 |
| 007-T078 | Add the flag `r2_reminders_failed` (default off) in `clinic-web/src/config/flags | 1.0 | frontend-react | yes | - |
| 007-T080 | Add `listRemindersFailed` to the API client in `clinic-web/src/api/messagingApi. | 2.5 | frontend-react, api-design | yes | 007-T052, 007-T077 |
| 007-T081 | Implement the "Reminders failed" screen and its route in `clinic-web/src/pages/r | 8.5 | frontend-react, frontend-css | no | 007-T078, 007-T079, 007-T080 |

### S-SETUP-007 Confirmations, reminders, STOP and SMS fallback: Setup — P1/must · 2 SP (low, llm)

Depends on: - · Sources: E-007, NFR-005, NFR-011

- [AC-S-SETUP-007-1] Given the setup tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 007-T001 | Create the module packages `clinic-api/app/modules/messaging/__init__.py`, `clin | 1.0 | backend-python | yes | - |
| 007-T002 | Add messaging settings in `clinic-api/app/modules/messaging/config.py`: dispatch | 3.0 | backend-python, auth-security | no | - |
| 007-T003 | Create the fake provider for tests (configurable latency, transient and permanen | 5.0 | qa-automation, backend-python | no | - |
| 007-T004 | Create the fake clock and fake booking and identity data fixtures in `clinic-api | 3.0 | qa-automation, backend-python | yes | - |

### S-FOUND-007 Confirmations, reminders, STOP and SMS fallback: Foundational prerequisites — P1/must · 13 SP (low, llm)

Depends on: S-SETUP-007 · Sources: E-007, NFR-005, NFR-011

- [AC-S-FOUND-007-1] Given the foundational prerequisites tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 007-T005 | Write model and constraint tests (unique `dedupe_key`, one live reminder per app | 2.1 | qa-automation, postgres | yes | - |
| 007-T006 | Create migration `clinic-api/alembic/versions/007_01_messages.py` for table `mes | 4.3 | postgres, data-modeling | no | 007-T005 |
| 007-T007 | Implement the `Message` model and repository (claim query with `FOR UPDATE SKIP  | 5.3 | backend-python, postgres | no | 007-T006 |
| 007-T008 | Write tests for the channel port types and error mapping (transient vs permanent | 1.6 | qa-automation, backend-python | yes | - |
| 007-T009 | Implement `ChannelPort`, `ProviderResult` and `ProviderEvent` in `clinic-api/app | 2.1 | backend-python | yes | 007-T008 |
| 007-T010 | Write tests for HMAC signature verification (valid, wrong, missing header, tampe | 1.6 | qa-automation, auth-security | yes | - |
| 007-T011 | Implement HMAC-SHA256 verification over the raw body in `clinic-api/app/modules/ | 2.1 | auth-security, backend-python | no | 007-T010 |
| 007-T012 | Write tests for retry and circuit breaker (3 attempts with waits 5 s and 30 s, n | 2.7 | qa-automation, backend-python | yes | - |
| 007-T013 | Implement retry with backoff and the per-provider circuit breaker in `clinic-api | 4.3 | backend-python | no | 007-T012 |
| 007-T014 | Write tests for the template renderer (renders English text with IST date and ti | 2.1 | qa-automation, backend-python | yes | - |
| 007-T015 | Create the single English catalogue with draft text for template keys `sign_in_c | 4.3 | backend-python, messaging | no | 007-T014 |
| 007-T016 | Write SMS adapter tests (template id mapping, error mapping, receipt and inbound | 2.1 | qa-automation, messaging | yes | - |
| 007-T017 | Implement the SMS provider adapter (send with 5 s timeout, client reference = me | 5.3 | backend-python, messaging | no | 007-T009, 007-T011, 007-T016 |
| 007-T018 | Write WhatsApp adapter tests (approved template mapping, error mapping, receipt  | 2.1 | qa-automation, messaging | yes | - |
| 007-T019 | Implement the WhatsApp provider adapter in `clinic-api/app/modules/channel_adapt | 4.3 | backend-python, messaging | no | 007-T009, 007-T011, 007-T018 |
| 007-T020 | Define the read ports to the booking and identity modules (`get_appointment_snap | 2.1 | backend-python, api-design | yes | - |
| 007-T021 | Write tests for `find_account_by_phone`, `get_reminders_enabled`, `set_reminders | 1.6 | qa-automation, backend-python | yes | - |
| 007-T022 | Implement the identity functions on the `reminders_opt_out` flag of the patient  | 3.2 | backend-python, postgres | no | 007-T021 |
| 007-T023 | Write dispatcher tests (claim with two dispatchers sends once, send only when `s | 4.3 | qa-automation, backend-python | no | - |
| 007-T024 | Implement the dispatcher (30 s cycle, claim, re-check, render, send through the  | 7.5 | backend-python, messaging | no | 007-T007, 007-T013, 007-T015, 007-T017, 007-T019, 007-T020, 007-T022, 007-T023 |
| 007-T025 | Write a log scrub test that runs the dispatcher and webhooks with a fake patient | 1.6 | qa-automation, backend-python | yes | - |
| 007-T026 | Add structured logging with ids only, metrics (`messages_total`, `provider_error | 3.2 | observability, backend-python | yes | 007-T025 |
| 007-T027 | Write webhook security tests (unsigned or wrongly signed request returns 401 and | 2.1 | qa-automation, auth-security | no | - |
| 007-T028 | Implement the webhook router `POST /api/webhooks/sms` and `POST /api/webhooks/wh | 4.3 | backend-python, api-design | no | 007-T017, 007-T019, 007-T026, 007-T027 |
| 007-T029 | Start the dispatcher with the application and report its last cycle time in `GET | 1.6 | backend-python, observability | yes | 007-T024, 007-T026, 007-T028 |

### S-POLISH-007 Confirmations, reminders, STOP and SMS fallback: Polish & cross-cutting concerns — P1/must · 5 SP (low, llm)

Depends on: S-007-US4, S-007-US6, S-007-US9 · Sources: E-007, NFR-005, NFR-011

- [AC-S-POLISH-007-1] Given the polish & cross-cutting concerns tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 007-T082 | Write the contract test of the webhook, reminders switch and reception list oper | 5.0 | qa-automation, api-design | no | 007-T028, 007-T049, 007-T077 |
| 007-T083 | Merge the messaging operations into `clinic-api/contracts/clinic-api-v1.openapi. | 3.0 | api-design, docs | yes | 007-T082 |
| 007-T084 | Write the runbook (lag alert, breaker open, provider outage, fallback switch, ST | 4.0 | docs, observability | yes | - |
| 007-T085 | Record the security review of the webhook endpoints, the reminders switch and th | 4.0 | auth-security, docs | no | 007-T028, 007-T049, 007-T077 |
| 007-T086 | Write the staging smoke test (book and cancel against the sandbox providers, con | 5.0 | qa-automation, backend-python | no | 007-T035, 007-T067, 007-T070 |
| 007-T087 | Run the validation scenarios in `specs/007-messaging-reminders/quickstart.md` an | 9.0 | qa-automation, docs | no | 007-T061, 007-T075, 007-T081, 007-T086 |

## E-008 Family members on a patient account (Release 2)

Patient adds up to 5 family members and books for them; each booking names the person.

### S-008-US1 Add family members to my account — P2/should · 5 SP (low, llm)

As a patient (P-01) with a signed-in account, I want to add up to 5 family members (name and birth year) to my account so that I can book and manage visits for my family from one place.
Depends on: S-FOUND-008, S-002-US2 · Sources: FR-006, NFR-007

- [AC-S-008-US1-1] Given a signed-in patient with fewer than 5 family members, When they enter a name and a valid birth year and confirm, Then the family member is saved on their account and appears in the list of people on the account. (source: FR-006)
- [AC-S-008-US1-2] Given a signed-in patient who already has 5 family members, When they try to add another, Then the system refuses, says that 5 family members is the limit, and the list is unchanged. (source: FR-006)
- [AC-S-008-US1-3] Given a signed-in patient on the add screen, When they leave the name empty or enter a birth year that is not a four-digit year in a plausible range, Then the system says what to correct and saves nothing. (source: FR-006)
- [AC-S-008-US1-4] Given a signed-in patient, When they add a family member, Then only a name and a birth year are stored for that person (no phone number, no other personal details). (source: FR-006, NFR-007)
- [AC-S-008-US1-5] Given the family-members feature flag is off, When a patient opens their account or sends a request to add a family member, Then the "Family" screen is not shown and the request is refused. (source: FR-006)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 008-T009 | Unit tests for the add rules (name not empty and trimmed, birth year 1900 to the | 3.0 | qa-automation, backend-python | yes | - |
| 008-T010 | Integration test that two simultaneous adds at 4 family members give exactly one | 3.0 | qa-automation, postgres | yes | - |
| 008-T011 | Contract test of `GET /api/me/people` and `POST /api/me/family-members` against  | 2.0 | qa-automation, api-design | yes | - |
| 008-T012 | Component test of the Family page and form (valid add, limit message, field erro | 3.0 | frontend-react, qa-automation | yes | - |
| 008-T013 | Add the `FamilyMemberIn` schema (name: required, at least 1 character after trim | 1.5 | backend-python, api-design | yes | - |
| 008-T014 | Implement add and list in clinic-api/app/modules/identity/family_service.py: one | 4.0 | backend-python, postgres | no | 008-T005, 008-T009, 008-T013 |
| 008-T015 | Implement `GET /api/me/people` and `POST /api/me/family-members` (201, 409 with  | 3.0 | backend-python, api-design | yes | 008-T007, 008-T014 |
| 008-T016 | Register the family router in clinic-api/app/main.py | 0.5 | backend-python | yes | 008-T015 |
| 008-T017 | Add the API client for the two operations in clinic-web/src/features/family/api. | 1.5 | frontend-react, api-design | yes | - |
| 008-T018 | Add the English texts for the Family screen, limit and field errors in clinic-we | 1.0 | frontend-react | yes | - |
| 008-T019 | Build the add form (name, birth year, 44 px tap targets, no sideways scrolling)  | 3.0 | frontend-react, frontend-css | yes | 008-T017, 008-T018 |
| 008-T020 | Build the Family page listing the holder and family members, hidden when the fla | 3.0 | frontend-react | yes | 008-T002, 008-T012, 008-T019 |
| 008-T021 | Add the Family route and menu link, shown only while the flag is on, in clinic-w | 1.5 | frontend-react | yes | 008-T020 |

### S-008-US2 Choose who the visit is for when booking — P2/should · 5 SP (low, llm)

As a patient (P-01) with family members on my account, I want to choose who the visit is for when I book online so that the appointment and its confirmation name the right family member.
Depends on: S-FOUND-008, S-004-US1 · Sources: FR-006, FR-004, NFR-006

- [AC-S-008-US2-1] Given a signed-in patient with at least one family member and the flag on, When they start a booking, Then they are asked who the visit is for and the choices are themselves and each of their family members. (source: FR-006, US-006)
- [AC-S-008-US2-2] Given the patient chose a family member, When they complete the booking, Then the appointment is saved for that family member, the booked screen and the confirmation name that person, and the booking takes no more screens than a booking for the patient themselves plus the one "who is it for" choice. (source: FR-006)
- [AC-S-008-US2-3] Given a signed-in patient with no family members, When they start a booking, Then the visit is for themselves and no "who is it for" question is shown. (source: FR-006)
- [AC-S-008-US2-4] Given a signed-in patient, When a request names a person who is not on that patient's account, Then the system refuses it and no appointment is created. (source: FR-004, FR-006)
- [AC-S-008-US2-5] Given the family-members flag is off, When a patient books, Then the booking is for the patient themselves and no family choice is offered. (source: FR-006)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 008-T022 | Unit tests: booking with `person_id` saves the appointment for that person, abse | 3.0 | qa-automation, backend-python | yes | - |
| 008-T023 | Integration test that a booking naming a person of another account, or a made-up | 3.0 | qa-automation, auth-security | no | - |
| 008-T024 | Component test of the "who is it for" step (hidden without family members, lists | 2.0 | frontend-react, qa-automation | yes | - |
| 008-T025 | Add optional `person_id` to the booking request and `person {id, name}` to the b | 1.5 | backend-python, api-design | yes | - |
| 008-T026 | Book for the chosen person: call `resolve_person`, store the person on the appoi | 5.0 | backend-python, auth-security | no | 008-T006, 008-T022, 008-T025 |
| 008-T027 | Pass the access context to the service, answer 404 for a person outside the acco | 3.0 | backend-python, auth-security | no | 008-T001, 008-T023, 008-T026 |
| 008-T028 | Build the "who is it for" step in clinic-web/src/features/booking/WhoIsItFor.tsx | 3.0 | frontend-react, frontend-css | yes | 008-T017, 008-T024 |
| 008-T029 | Put the step first in the booking flow, skipped for a patient with no family mem | 2.5 | frontend-react | yes | 008-T028 |
| 008-T030 | Show the person's name on the booked screen in clinic-web/src/features/booking/B | 1.5 | frontend-react | yes | 008-T029 |

### S-008-US3 See family members' appointments in my list — P2/should · 3 SP (low, llm)

As a patient (P-01) managing my family's visits, I want to see the appointments of myself and my family members in My appointments, each with the person's name and status so that I can keep track of and change the whole family's visits in one list.
Depends on: S-FOUND-008, S-005-US1 · Sources: FR-006, FR-004, FR-015, NFR-006

- [AC-S-008-US3-1] Given a patient and a family member each have an upcoming appointment, When the patient opens "My appointments", Then both appear, each showing the person it is for and its status. (source: FR-004, FR-015, FR-006)
- [AC-S-008-US3-2] Given a family member has a past appointment, When the patient opens the past appointments, Then it is listed with the family member's name and its status. (source: FR-015)
- [AC-S-008-US3-3] Given two different accounts, When one patient opens their list or asks for an appointment of the other account, Then the other account's appointments are never shown and the request is refused. (source: FR-004, NFR-006)
- [AC-S-008-US3-4] Given a patient opens an appointment of a family member, When they reschedule or cancel it under the rules of the appointment features, Then the same rules apply as for their own appointments. (source: FR-004, FR-015)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 008-T031 | Integration test: list and single-appointment reads cover all persons of the acc | 4.0 | qa-automation, auth-security | no | - |
| 008-T032 | Component test that the list shows each person's name and status in clinic-web/s | 2.0 | frontend-react, qa-automation | yes | - |
| 008-T033 | List and read appointments, and authorise reschedule and cancel (feature 005 rul | 4.0 | backend-python, auth-security | no | 008-T026, 008-T031 |
| 008-T034 | Return `person {id, name}` in the appointment list and detail responses in clini | 2.0 | backend-python, api-design | yes | 008-T027, 008-T033 |
| 008-T035 | Show the person's name next to each appointment in clinic-web/src/features/appoi | 2.0 | frontend-react | yes | 008-T032, 008-T034 |

### S-008-US4 Messages for a family member's visit reach the account's phone — P2/should · 2 SP (low, llm)

As a patient (P-01) who books for a family member, I want confirmations, change notices and reminders for their visit to reach my phone and name the person so that I can tell which family visit each message is about.
Depends on: S-FOUND-008 · Sources: FR-006, FR-014, FR-027, FR-031

- [AC-S-008-US4-1] Given a visit booked for a family member, When the confirmation is sent, Then it goes to the account's phone number in the channel chosen for that booking and names the family member. (source: FR-006, FR-014)
- [AC-S-008-US4-2] Given a reminder is due for a family member's appointment, When it is sent, Then it goes to the account's phone number in the account's channel and names the family member. (source: FR-006, FR-027)
- [AC-S-008-US4-3] Given the account has reminders switched off, When a reminder falls due for a family member's appointment, Then no reminder is sent but confirmations and change notices still are. (source: FR-031)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 008-T036 | Unit tests: messages for a family member's appointment use the account's phone a | 3.0 | qa-automation, messaging | yes | - |
| 008-T037 | Add the `person_name` value to confirmation, change-notice and reminder renderin | 4.0 | backend-python, messaging | no | 008-T026, 008-T036 |
| 008-T038 | Add the `person_name` variable to the template definitions and note the DLT and  | 1.5 | messaging, docs | yes | - |
| 008-T039 | Record the added template value against thr-013 and in the change log in archite | 1.0 | docs | yes | - |

### S-SETUP-008 Family members on a patient account (Release 2): Setup — P2/should · 1 SP (low, llm)

Depends on: - · Sources: E-008, FR-006

- [AC-S-SETUP-008-1] Given the setup tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 008-T001 | Add the boolean setting `family_members` (default off, read per request from con | 2.0 | backend-python | yes | - |
| 008-T002 | Add the `useFeatureFlag` hook that reads flags from the API in clinic-web/src/fe | 4.0 | frontend-react | yes | - |

### S-FOUND-008 Family members on a patient account (Release 2): Foundational prerequisites — P2/should · 2 SP (low, llm)

Depends on: S-SETUP-008 · Sources: E-008, FR-006, FR-004, NFR-006

- [AC-S-FOUND-008-1] Given the foundational prerequisites tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 008-T003 | Write failing unit tests for `resolve_person`: returns a person of the caller's  | 2.0 | qa-automation, backend-python | no | - |
| 008-T004 | Create the expand-only Alembic migration clinic-api/alembic/versions/0008_family | 2.0 | postgres, backend-python | no | - |
| 008-T005 | Update the person (`ent-patient`) model in clinic-api/app/modules/identity/model | 1.5 | backend-python, data-modeling | no | 008-T004 |
| 008-T006 | Implement `resolve_person(access_context, person_id)` in clinic-api/app/modules/ | 2.0 | backend-python, auth-security | no | 008-T003, 008-T005 |
| 008-T007 | Expose the flags to the web app with `GET /api/feature-flags` in clinic-api/app/ | 2.0 | backend-python, api-design | yes | 008-T001 |
| 008-T008 | Merge the additions of specs/008-family-members/contracts/family-members.openapi | 1.5 | api-design | yes | - |

### S-POLISH-008 Family members on a patient account (Release 2): Polish & cross-cutting concerns — P2/should · 3 SP (low, llm)

Depends on: S-008-US1, S-008-US2, S-008-US3, S-008-US4 · Sources: E-008, FR-006, NFR-007, NFR-006

- [AC-S-POLISH-008-1] Given the polish & cross-cutting concerns tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 008-T040 | Write a failing integration test that erasure on request and the 24-month idle a | 2.0 | qa-automation, backend-python | yes | - |
| 008-T041 | Integration test that with the flag off the family endpoints answer 404, family  | 2.0 | qa-automation, backend-python | yes | - |
| 008-T042 | Test that family names and birth years never appear in log output during add, bo | 2.0 | qa-automation, backend-python | yes | - |
| 008-T043 | Make the erasure and idle-anonymisation job cover all persons of an account in c | 3.0 | backend-python, postgres | no | 008-T040 |
| 008-T044 | Review authorisation changes (resolve_person, booking and list scoping, flag-off | 3.0 | auth-security, docs | no | 008-T027, 008-T034, 008-T041 |
| 008-T045 | Run the validation scenarios in specs/008-family-members/quickstart.md in stagin | 3.0 | qa-automation, docs | no | 008-T021, 008-T030, 008-T035, 008-T037, 008-T043, 008-T044 |

## E-009 Repeat no-show block and no-show report (Release 2)

Block online booking after 2 no-shows in 6 months, lift by reception, monthly no-show report per clinic.

### S-009-US1 A patient with 2 recent no-shows cannot book or reschedule online — P2/should · 8 SP (low, llm)

As a patient (P-01) who books for myself or a family member, I want to be told clearly, with the clinic's phone number, when online booking or rescheduling is not available to me after 2 no-shows in 6 months, while my existing bookings stay so that I know to phone the clinic, and the clinic's repeat no-shows are discouraged without losing appointments I already have.
Depends on: S-FOUND-009, S-004-US1, S-005-US4, S-006-US3 · Sources: FR-025

- [AC-S-009-US1-1] Given a patient with 2 no-shows in the last 6 months, When they reach the step where they choose a dentist and slot, Then the system says online booking is not available and shows the phone number of the clinic they chose, and no booking is created
- [AC-S-009-US1-2] Given a patient with 2 no-shows in the last 6 months and an upcoming booking, When they try to reschedule it online, Then the system says online rescheduling is not available and shows the phone number of that appointment's clinic, and the booking stays unchanged
- [AC-S-009-US1-3] Given a patient with 2 no-shows in the last 6 months and upcoming bookings, When they view their appointments, Then all existing bookings are still listed and none is cancelled or changed by the block
- [AC-S-009-US1-4] Given an account holder with a family member who has 2 no-shows in the last 6 months, When the account holder books online for themselves, Then the booking is accepted; **When** they try to book for that family member, **Then** it is refused as in scenario 1
- [AC-S-009-US1-5] Given a patient with 1 no-show in the last 6 months, When they book or reschedule online, Then the booking proceeds as normal
- [AC-S-009-US1-6] Given a patient whose older no-show falls out of the 6-month window so that fewer than 2 remain in the window, When they try to book online, Then the booking proceeds as normal without anyone lifting anything
- [AC-S-009-US1-7] Given the Release 2 feature flag is off, When a patient with 2 no-shows in the last 6 months books or reschedules, Then the booking behaves as before this feature (not blocked)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 009-T009 | Unit tests for the policy rules in clinic-api/tests/unit/test_noshow_policy_serv | 3.0 | qa-automation, backend-python | yes | - |
| 009-T010 | Contract tests in clinic-api/tests/contract/test_booking_eligibility.py for `GET | 3.0 | qa-automation, api-design | yes | - |
| 009-T011 | Integration tests in clinic-api/tests/integration/test_online_block.py: blocked  | 4.0 | qa-automation, backend-python | no | - |
| 009-T012 | Component test for the notice in clinic-web/tests/BlockedNotice.test.tsx: shows  | 2.0 | frontend-react, qa-automation | yes | - |
| 009-T013 | Create eligibility and error schemas in clinic-api/app/modules/noshow_policy/sch | 1.5 | backend-python, api-design | yes | - |
| 009-T014 | Implement `is_blocked`, `on_no_show_marked` and `on_no_show_undone` in clinic-ap | 5.0 | backend-python, postgres | no | 009-T006, 009-T008, 009-T009 |
| 009-T015 | Add structured logs and counters for refusals and block starts in clinic-api/app | 2.0 | backend-python, observability | yes | 009-T014 |
| 009-T016 | Wire the real policy behind the existing booking interface in clinic-api/app/mod | 2.0 | backend-python | yes | 009-T014 |
| 009-T017 | Call `on_no_show_marked` and `on_no_show_undone` inside the status-change transa | 2.0 | backend-python | yes | 009-T014 |
| 009-T018 | Refuse blocked online booking confirm and online reschedule with HTTP 403 `ONLIN | 4.0 | backend-python, api-design | no | 009-T016 |
| 009-T019 | Add `GET /api/booking-eligibility` in clinic-api/app/modules/booking/router.py,  | 3.0 | backend-python, auth-security | no | 009-T013, 009-T018 |
| 009-T020 | Create the BlockedNotice component in clinic-web/src/components/BlockedNotice.ts | 2.0 | frontend-react, frontend-css | yes | - |
| 009-T021 | Show the notice in the slot step and handle a 403 `ONLINE_BOOKING_BLOCKED` on co | 3.0 | frontend-react | yes | 009-T019, 009-T020 |
| 009-T022 | Show the notice on the reschedule screen and handle the 403 on confirm in clinic | 2.5 | frontend-react | yes | 009-T018, 009-T020 |

### S-009-US2 Reception sees a block and lifts it — P2/should · 3 SP (low, llm)

As a receptionist (P-02), I want to see that a patient is blocked from online booking and to lift the block when the clinic agrees so that a blocked patient who phones can book online again, the count restarts from zero, and who lifted it and when is on record.
Depends on: S-FOUND-009, S-006-US1 · Sources: FR-026

- [AC-S-009-US2-1] Given a blocked patient, When a receptionist opens that patient's record or an appointment panel for that patient, Then the screen clearly shows the patient is blocked from online booking and since when
- [AC-S-009-US2-2] Given a blocked patient, When the receptionist lifts the block, Then the patient can book and reschedule online straight away, and the system records the receptionist and the time of the lift
- [AC-S-009-US2-3] Given a patient whose block was just lifted, When one new no-show is recorded, Then the patient is not blocked; **When** a second new no-show is recorded after the lift, **Then** the patient is blocked again
- [AC-S-009-US2-4] Given a patient who had 2 no-shows before a lift and none after, When the system counts their no-shows, Then the count is zero
- [AC-S-009-US2-5] Given a patient who is not blocked, When a receptionist opens their record, Then no lift action is offered
- [AC-S-009-US2-6] Given a blocked patient, When a receptionist books an appointment for them at the desk or by phone, Then the booking is accepted, because the block applies to online booking and rescheduling only
- [AC-S-009-US2-7] Given a patient is blocked because of a no-show marked today, When the receptionist undoes that no-show the same day and the patient then has fewer than 2 no-shows in the window, Then the block no longer applies and no lift record is created

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 009-T023 | Unit tests for lifting in clinic-api/tests/unit/test_noshow_lift.py: lift sets ` | 2.5 | qa-automation, backend-python | yes | - |
| 009-T024 | Contract tests in clinic-api/tests/contract/test_noshow_block_endpoints.py for ` | 2.0 | qa-automation, api-design | no | - |
| 009-T025 | Integration tests in clinic-api/tests/integration/test_reception_block.py: a rec | 3.0 | qa-automation, backend-python | yes | - |
| 009-T026 | Component test for the banner in clinic-web/tests/BlockBanner.test.tsx: shows "b | 1.5 | frontend-react, qa-automation | yes | - |
| 009-T027 | Implement `get_block_state` and `lift` in clinic-api/app/modules/noshow_policy/s | 3.0 | backend-python, postgres | yes | 009-T014, 009-T023 |
| 009-T028 | Add the block state and lift endpoints in clinic-api/app/modules/reception/route | 2.5 | backend-python, auth-security | no | 009-T027, 009-T024 |
| 009-T029 | Create the API client in clinic-web/src/services/noshowBlock.ts for the state an | 1.5 | frontend-react, api-design | yes | - |
| 009-T030 | Create the BlockBanner component with the Lift action in clinic-web/src/componen | 2.0 | frontend-react, frontend-css | yes | - |
| 009-T031 | Show the banner in the reception patient panel in clinic-web/src/pages/reception | 2.5 | frontend-react | yes | 009-T028, 009-T029, 009-T030 |

### S-009-US3 The practice manager reads the no-show report per clinic and month — P2/should · 5 SP (low, llm)

As a practice manager (P-04), I want to see, per clinic and per month for the last 12 months, the number of no-shows and the no-show rate on screen so that I know the clinic's real no-show figure and can judge whether reminders and the block are working.
Depends on: S-FOUND-009, S-006-US3 · Sources: FR-032

- [AC-S-009-US3-1] Given the practice manager is signed in, When they open the no-show report, Then they see one row per clinic and month for the last 12 months, each with the number of no-shows and the no-show rate
- [AC-S-009-US3-2] Given a clinic-month with 40 appointments of which 4 were cancelled by the patient, 2 cancelled by the clinic and 3 are no-shows, When the report is shown, Then the rate is 3 divided by 34 (appointments not cancelled), shown as a percentage, and the no-show count is 3
- [AC-S-009-US3-3] Given a walk-in booked as a normal appointment and marked arrived, When the report counts that month, Then the walk-in is counted among the appointments that were not cancelled
- [AC-S-009-US3-4] Given a clinic-month with no appointments that were not cancelled, When the report is shown, Then the count is 0 and the rate is shown as "no appointments" rather than as a number or an error
- [AC-S-009-US3-5] Given a patient whose personal data was deleted on request and whose appointment rows were anonymised, When the report is shown, Then the counts and rates are the same as before the deletion
- [AC-S-009-US3-6] Given a receptionist or a patient or a dentist is signed in, When they try to open the report, Then access is refused
- [AC-S-009-US3-7] Given the report is open, When the manager looks for a way to download or export it, Then none is offered
- [AC-S-009-US3-8] Given the Release 2 feature flag is off, When the practice manager looks at the menu, Then the report screen is not shown

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 009-T032 | Unit tests for the monthly counts query in clinic-api/tests/unit/test_monthly_co | 2.5 | qa-automation, postgres | yes | - |
| 009-T033 | Unit tests for the report service in clinic-api/tests/unit/test_report_service.p | 2.5 | qa-automation, backend-python | yes | - |
| 009-T034 | Contract tests in clinic-api/tests/contract/test_noshow_report.py for `GET /api/ | 2.0 | qa-automation, api-design | no | - |
| 009-T035 | Integration test in clinic-api/tests/integration/test_report_anonymised.py: afte | 2.5 | qa-automation, postgres | yes | - |
| 009-T036 | Component test for the report screen in clinic-web/tests/NoShowReport.test.tsx:  | 2.0 | frontend-react, qa-automation | yes | - |
| 009-T037 | Implement `monthly_counts(months)` as one grouped query by clinic and IST calend | 4.0 | backend-python, postgres | no | 009-T008, 009-T032 |
| 009-T038 | Create the report response schemas in clinic-api/app/modules/reporting/schemas.p | 1.0 | backend-python, api-design | yes | - |
| 009-T039 | Implement the 12-month report in clinic-api/app/modules/reporting/service.py: re | 3.5 | backend-python | yes | 009-T033, 009-T037, 009-T038 |
| 009-T040 | Add `GET /api/reports/no-shows` for the practice manager role only in clinic-api | 2.5 | backend-python, auth-security | no | 009-T016, 009-T039, 009-T034 |
| 009-T041 | Create the API client in clinic-web/src/services/reports.ts | 1.0 | frontend-react, api-design | yes | - |
| 009-T042 | Create the report screen in clinic-web/src/pages/manager/NoShowReport.tsx: rows  | 3.5 | frontend-react, frontend-css | yes | 009-T036, 009-T041 |
| 009-T043 | Add the report route and manager menu entry, hidden when the flag is off, in cli | 1.5 | frontend-react | yes | 009-T042 |

### S-SETUP-009 Repeat no-show block and no-show report (Release 2): Setup — P2/should · 1 SP (low, llm)

Depends on: - · Sources: E-009, FR-025, FR-026, FR-032

- [AC-S-SETUP-009-1] Given the setup tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 009-T001 | Find the existing "is blocked?" interface in clinic-api/app/modules/booking/bloc | 2.0 | backend-python | no | - |
| 009-T002 | Create empty module packages clinic-api/app/modules/noshow_policy/__init__.py an | 0.5 | backend-python | yes | - |
| 009-T003 | Register the Release 2 flag `r2_noshow_block_report` (default off) in clinic-api | 1.0 | backend-python, frontend-react | yes | - |

### S-FOUND-009 Repeat no-show block and no-show report (Release 2): Foundational prerequisites — P2/should · 2 SP (low, llm)

Depends on: S-SETUP-009 · Sources: E-009, FR-025, FR-026, FR-032

- [AC-S-FOUND-009-1] Given the foundational prerequisites tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 009-T004 | Create the Alembic migration clinic-api/migrations/versions/009a_no_show_block.p | 2.5 | postgres, data-modeling | no | - |
| 009-T005 | Create the Alembic migration clinic-api/migrations/versions/009b_no_show_count_i | 1.5 | postgres | no | 009-T004 |
| 009-T006 | Create the `NoShowBlock` SQLAlchemy model in clinic-api/app/modules/noshow_polic | 1.5 | backend-python, data-modeling | yes | 009-T004 |
| 009-T007 | Write failing unit tests for counting in clinic-api/tests/unit/test_no_show_stat | 2.5 | qa-automation, backend-python | yes | - |
| 009-T008 | Implement `count_no_shows(patient_id, now, marked_after)` in clinic-api/app/modu | 3.0 | backend-python, postgres | yes | 009-T006, 009-T007 |

### S-POLISH-009 Repeat no-show block and no-show report (Release 2): Polish & cross-cutting concerns — P2/should · 3 SP (low, llm)

Depends on: S-009-US1, S-009-US2, S-009-US3 · Sources: E-009, FR-025, FR-026, FR-032

- [AC-S-POLISH-009-1] Given the polish & cross-cutting concerns tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 009-T044 | Security review of the authorisation changes (receptionist-only lift, manager-on | 3.0 | auth-security, docs | no | - |
| 009-T045 | Test that logs and metrics from the new code hold no name, phone or birth year i | 2.0 | qa-automation, backend-python | yes | - |
| 009-T046 | Regression run of the existing online booking and reschedule tests from features | 3.0 | qa-automation, backend-python | yes | - |
| 009-T047 | Merge the operations of specs/009-noshow-block-report/contracts/noshow-block-rep | 2.0 | api-design, docs | yes | 009-T044 |
| 009-T048 | Add 24-month retention for `no_show_block` rows to the existing retention job in | 2.0 | backend-python, postgres | yes | 009-T004 |
| 009-T049 | Check that the block check keeps booking confirmation inside the 800 ms server p | 3.0 | qa-automation, backend-python | yes | 009-T018 |
| 009-T050 | Run the manual scenarios in specs/009-noshow-block-report/quickstart.md and note | 2.0 | qa-automation, docs | no | 009-T049 |

## Open questions

- S-001-US2: Q1: hosting provider and domain are not confirmed by the clinic; assumed an India-region provider chosen by the delivery team and a placeholder domain. Confirm before staging is set up.
- S-001-US7: Q3: alert recipients and any out-of-hours rota are not defined; assumed the shared delivery-team channel and email, business hours only. Revisit before 2027-02-22.
- S-001-US9: Real free-slot and booking paths exist only after features 003 and 004; until then the load test runs against stub endpoints and must be re-run before UAT.
- S-002-US3: Assumed no self-service password reset by email or SMS (staff have no email stored); the manager resets passwords. Confirm with the clinic (spec Q3).
- S-002-US6: Priority raised from should/P2 to must/P1: NFR-007 is a DPDP Act requirement and the spec says it must be ready by go-live on 1 March 2027 (not listed in DL-1 requirement ids). Confirm with the PM.
- S-POLISH-002: Priority raised from could/P3 to must/P1: the contract merge and contract test feed the CI contract-test stage, and the security review and staging run are needed before UAT on 2027-02-22.
- S-004-US4: Priority raised from P2/should to P1/must: FR-012 is in the hard Release 1 deadline DL-1 and the spec says the proof is needed before go-live. Confirm.
- S-004-US5: The 2 s / 3 s and 500 ms / 800 ms targets are our proposals (PD-008, ASM-006); confirm with the client at the gate.
- S-POLISH-004: Priority raised from P3/could to P2/should: it holds the DoD checks (no patient data in logs, authorisation) needed before go-live. Confirm.
- S-006-US6: Moscow raised from should to must: FR-020 is Must in Release 1 (DL-1, due 2027-02-22).
- S-006-US7: Moscow raised from should to must: FR-023 is Must in Release 1 (DL-1, due 2027-02-22).
- S-POLISH-006: Q3: are messages sent for appointments typed in before go-live? Needs a decision with feature 007 (task 006-T074).
- S-POLISH-006: Moscow/priority raised to must/P1: the paper-diary dry run (006-T073) must finish at least a week before the 1 March 2027 go-live and the review/contract checks gate DL-1.
- S-007-US6: Which SMS and WhatsApp providers are chosen? Adapter alignment (T068) and the effort of this story depend on it (RSK-001, ASM-009).
- S-007-US6: Start T064 and T065 on day 1: DLT and WhatsApp approval lead times are outside our control.
- S-007-US8: The client has not agreed to the SMS fallback (ISS-001, ASM-005); it is built behind WHATSAPP_SMS_FALLBACK_ENABLED, default on. Confirm before Release 2 (DL-2).
- S-FOUND-007: At 13 points this is the maximum; if the team prefers smaller pieces, split along the checkpoint: (a) message table, repository and tests; (b) channel adapters, signature and resilience; (c) template guard, dispatcher, webhooks and health.
- S-008-US1: Q1 (Q-007 open): assumed no separate sign-ins for family members; if needed, sign-in and identity change (about 2-4 person-days).
- S-008-US1: Q2: edit and remove of a family member are assumed out of Release 2 (PRD specifies add only).
- S-008-US1: Q3: assumed the limit of 5 counts family members only, not the account holder.
- S-008-US4: Q4: if the registered SMS/WhatsApp templates cannot carry the person's name in time, messages fall back to the appointment link only; needs feature 007 and DLT/WhatsApp template approval.
