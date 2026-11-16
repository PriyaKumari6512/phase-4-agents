# Assignments — BrightSmile Booking Sprint 1 (v3)

Solver: timefold · SOLVING_COMPLETED · 0hard/0medium/-16494360soft

**Read the load table in "Sprint 1 load and decisions for P4-G3" below.** In this solver table, "Capacity h" is the hours left after the pinned tasks, not the full capacity, so Kavya and Priya look over-full here although they are at 85% and 80%. All 79 tasks are assigned.

| Worker | Kind | Planned h | Capacity h (left after pins) |
|---|---|---|---|
| Arjun | human | 38.0 | 48.6 |
| Meera | human | 30.5 | 45.6 |
| Sanjay | human | 33.5 | 43.1 |
| Priya | human | 39.0 | 37.1 |
| Kavya | human | 41.5 | 34.1 |
| Rohan | human | 0.0 | 24.3 |
| Neha | human | 4.5 | 22.5 |
| Vikram | human | 5.0 | 7.2 |
| claude-code | ai_agent | 6.5 | 35.0 |
| copilot | ai_agent | 6.0 | 36.0 |

| Task | Title | Assignee | Hours | Why | Runner-up |
|---|---|---|---|---|---|
| 001-T008 | In clinic-api, write the failing test `clinic-api/tests/unit/test_logg | claude-code | 1.0 | Claude Code writes this one-file test because its two criteria are concrete and it needs no human judgement; Copilot was equally qualified and the runner-up, so lower cost decided, and a human reviews the PR. | copilot |
| 001-T013 | In clinic-api, add the integration test `clinic-api/tests/integration/ | claude-code | 1.0 | Claude Code writes this one-file health-check test (two concrete outcomes, 1 h, test only) once 001-T012 provides the test database, and a human reviews the PR; it moves off Kavya, who is at about 85% load; Copilot would be equally qualified. | - |
| 002-T001 | Create the scheduling package skeleton in repo clinic-api: `app/schedu | claude-code | 3.0 | Claude Code takes this two-file package skeleton because its defaults (30, 31 and an env override) are checkable by a unit test; Copilot was equally qualified and the runner-up, so lower cost decided. | copilot |
| 001-T064 | In clinic-api, implement the registries in `clinic-api/app/jobs/regist | claude-code | 1.5 | Claude Code takes this single small registry module with two concrete criteria; Copilot was equally qualified and the runner-up, so lower cost decided, and a human reviews the PR. | copilot |
| 005-T001 | Create the cmp-reception package with empty `app/modules/reception/__i | copilot | 3.0 | Copilot creates this empty reception package (4 files, 3 h, both criteria checked by app start and CI); Claude Code was equally qualified and the runner-up, so the work is split between the two agents, and a human reviews the PR. | claude-code |
| 001-T062 | In clinic-api, write unit tests `clinic-api/tests/unit/test_erasure_se | copilot | 3.0 | Copilot writes this single unit-test file with exact expected values (due date plus 30 days, replacement strings, idempotence); Claude Code was equally qualified and the runner-up, and a human reviews the tests against the erasure rules. | claude-code |
| 001-T038 | In clinic-api, implement `clinic-api/app/identity/passwords.py`: argon | Arjun | 1.0 | Arjun does password hashing because it is auth-sensitive and he is the only person with auth-security; there is no runner-up. | - |
| 001-T014 | In clinic-api, define the scheduling models in `clinic-api/app/schedul | Arjun | 1.5 | Arjun defines these models because the case-insensitive unique constraint needs data-modeling and postgres, which neither AI agent has and nobody else on the team has together; there is no runner-up. | - |
| 001-T006 | In clinic-api, implement settings from environment variables in `clini | Arjun | 2.0 | Arjun implements the settings because they hold the JWT and hash secrets, which are a sensitive area, and he has both backend-python and auth-security; there is no runner-up. | - |
| 001-T015 | In clinic-api, write migration `clinic-api/migrations/versions/0001_sc | Arjun | 2.0 | Arjun writes this migration with seed data because migrations are human-only and he has postgres and data-modeling; there is no runner-up. | - |
| 001-T017 | In clinic-api, write migration `clinic-api/migrations/versions/0002_id | Arjun | 2.0 | Arjun writes the account-table migration because migrations are human-only and he is the only person with both postgres and data-modeling; there is no runner-up. | - |
| 001-T018 | In clinic-api, write migration `clinic-api/migrations/versions/0003_id | Arjun | 1.5 | Arjun writes the sessions, throttle and erasure migration because migrations are human-only and he is the only person with both postgres and data-modeling; there is no runner-up. | - |
| 001-T041 | In clinic-api, implement the idempotent first-manager seed `clinic-api | Arjun | 1.0 | Arjun writes the first-manager seed because it reads credentials from the environment and he is the only person with auth-security; there is no runner-up. | - |
| 001-T022 | In clinic-api, implement `clinic-api/app/identity/security.py`: middle | Arjun | 2.5 | Arjun writes the CSRF, Origin and HTTPS middleware because it is security-critical and he is the only person with auth-security and backend-python; there is no runner-up. | - |
| 001-T016 | In clinic-api, define the identity models in `clinic-api/app/identity/ | Arjun | 3.5 | Arjun defines the identity models because role constraints are a sensitive area and he is the only person with data-modeling; there is no runner-up. | - |
| 001-T040 | In clinic-api, implement `clinic-api/app/identity/staff_auth_router.py | Arjun | 2.5 | Arjun implements the staff sign-in and password endpoints because they are auth-sensitive and he has auth-security and api-design; there is no runner-up. | - |
| 001-T048 | In clinic-api, implement `GET /api/me` in `clinic-api/app/identity/me_ | Arjun | 1.0 | Arjun implements GET /api/me because it reads identity state and he has auth-security and api-design; there is no runner-up. | - |
| 001-T046 | In clinic-api, implement the read side of scheduling in `clinic-api/ap | Arjun | 3.0 | Arjun implements the role-scoped reads because they are authorisation logic and he is the only person with auth-security plus backend-python; there is no runner-up. | - |
| 001-T024 | In clinic-api, implement `clinic-api/app/identity/access.py`: `AccessC | Arjun | 3.5 | Arjun writes the access-control dependencies because they are the authorisation core and he is the only person with auth-security; there is no runner-up. | - |
| 001-T039 | In clinic-api, implement `clinic-api/app/identity/staff_auth_service.p | Arjun | 3.0 | Arjun implements staff authentication with lockout because it is auth-sensitive and he is the only person with auth-security; there is no runner-up. | - |
| 003-T004 | Create SQLAlchemy models `Appointment`, `AppointmentEvent` and `Bookin | Arjun | 4.0 | Arjun defines the booking models because they need data-modeling and postgres together, which only he has and neither AI agent has; there is no runner-up. | - |
| 001-T021 | In clinic-api, implement `clinic-api/app/identity/sessions.py`: create | Arjun | 4.0 | Arjun implements session and JWT cookie handling because it is auth-sensitive and he is the only person with auth-security and backend-python; there is no runner-up. | - |
| 004-T001 | Create the module skeleton `app/booking/patient_router.py`, `app/booki | Kavya | 1.5 | Kavya creates this skeleton because its 8 files are over the 4-file limit for AI, and she has backend-python at about 85% load; Meera was the runner-up. | Meera |
| 001-T012 | In clinic-api, create shared test fixtures in `clinic-api/tests/confte | Kavya | 3.5 | Kavya writes the test fixtures because she has qa-automation, with Vikram giving about 1 h on the PostgreSQL service in CI, since nobody holds qa-automation and postgres together. | - |
| 001-T019 | In clinic-api, add `clinic-api/tests/integration/test_migrations.py`:  | Kavya | 2.5 | Kavya writes the migration tests because she has qa-automation, with Sanjay giving about 0.5 h on the constraint cases, since nobody holds qa-automation and postgres together. | - |
| 001-T036 | In clinic-api, write unit tests `clinic-api/tests/unit/test_passwords. | Kavya | 2.5 | Kavya writes the password unit tests because she has qa-automation, and Arjun, who wrote the code under test, reviews for about 0.5 h, since nobody holds qa-automation and auth-security together. | - |
| 001-T037 | In clinic-api, write `clinic-api/tests/integration/test_staff_sign_in. | Kavya | 3.0 | Kavya writes the staff sign-in integration tests because she has qa-automation, and Arjun reviews for about 0.5 h, since nobody holds qa-automation and auth-security together. | - |
| 001-T020 | In clinic-api, write the failing tests `clinic-api/tests/unit/test_ses | Kavya | 3.0 | Kavya writes the session and CSRF tests because she has qa-automation, and Arjun, who owns the sessions and security code, reviews for about 0.5 h. | - |
| 004-T007 | Implement `AlwaysAllowRescheduleRule` (Release 1; Release 2 replaces i | Kavya | 1.5 | Kavya implements this small reschedule rule and its unit test because she has backend-python and room at about 85% load; Meera was the runner-up. | Meera |
| 004-T005 | Implement `can_change(status, start_at, now)` and `change_deadline(sta | Kavya | 1.5 | Kavya implements the change-window logic because she has backend-python and has the matching tests 004-T004 in the same area; Meera was the runner-up. | Meera |
| 003-T001 | Create the cmp-booking module skeleton `app/modules/booking/__init__.p | Kavya | 1.5 | Kavya creates this small booking skeleton and settings (2 files, 1.5 h), as she has backend-python and qa-automation; Priya was the runner-up. | Priya |
| 004-T004 | Write unit tests for the change window in `tests/booking/test_change_w | Kavya | 2.5 | Kavya writes the change-window unit tests because she has qa-automation and is writing the logic they test (004-T005); Priya was the runner-up. | Priya |
| 004-T011 | Add OpenTelemetry counters `appointment_cancelled`, `appointment_resch | Kavya | 3.0 | Kavya adds the counters and log helper that must never log names or phones because it is a privacy-sensitive change that stays with a person; Meera was the runner-up. | Meera |
| 003-T007 | Create test fixtures in `tests/booking/conftest.py` and `tests/booking | Kavya | 5.0 | Kavya builds the booking test fixtures because 5 h is over the 4 h AI limit and she is the QA lead with qa-automation; Priya was the runner-up. | Priya |
| 006-T001 | Create the packages `src/clinic_api/messaging/` and `src/clinic_api/ch | Kavya | 3.0 | Kavya creates the messaging packages and provider settings because provider settings are a sensitive area and she has the spare capacity; Meera was the runner-up. | Meera |
| 006-T002 | Create test fixtures in `tests/fixtures/messaging.py`: frozen IST cloc | Kavya | 5.0 | Kavya builds the messaging test fixtures because 5 h is over the 4 h AI limit and she has qa-automation; Priya was the runner-up. | Priya |
| 001-T070 | In clinic-api, start the daily retention trigger with the app in `clin | Kavya | 2.5 | Kavya wires the daily retention trigger into main.py because it can run twice across replicas and triggers deletion of personal data, so it stays with a person; Meera was the runner-up. | Meera |
| 004-T008 | Define the response and request models `Person`, `Appointment` (with ` | Meera | 2.5 | Meera defines the request and response models because they need api-design, which neither AI agent has, and she is at about 63% load; Sanjay was the runner-up. | Sanjay |
| 003-T008 | Add telemetry in `app/modules/booking/telemetry.py`: structured log he | Meera | 3.0 | Meera writes the booking telemetry because she has backend-python and low load, with Vikram giving about 1 h on OpenTelemetry, since only Vikram has observability and no AI agent has it. | - |
| 003-T010 | Create `src/features/booking/bookingState.ts` holding the patient's ch | Meera | 2.0 | Meera builds the booking state store in clinic-web because she has frontend-react at about 63% load; Sanjay was the runner-up. | Sanjay |
| 001-T005 | In clinic-api, copy `specs/001-platform-identity/contracts/identity-ap | Meera | 1.5 | Meera copies the contract file because it needs api-design, which neither AI agent has, and she is at about 63% load; Sanjay was the runner-up. | Sanjay |
| 001-T007 | In clinic-api, set up the database layer and migrations: `clinic-api/a | Meera | 1.5 | Meera sets up the database layer and migrations because it is a sensitive area and she has backend-python and postgres; Sanjay was the runner-up. | Sanjay |
| 001-T043 | In clinic-web, build `clinic-web/src/pages/staff/ChangePasswordPage.ts | Meera | 2.0 | Meera builds the change-password page because it is auth-related and she has frontend-react; Sanjay was the runner-up. | Sanjay |
| 004-T002 | Create the web skeleton: `src/api/appointments.ts` (typed client for t | Meera | 3.0 | Meera builds the appointments web skeleton because she has frontend-react and api-design at about 63% load; Sanjay was the runner-up. | Sanjay |
| 001-T042 | In clinic-web, build `clinic-web/src/pages/staff/StaffSignInPage.tsx`  | Meera | 3.0 | Meera builds the staff sign-in page because it is auth-related and she has frontend-react; Sanjay was the runner-up. | Sanjay |
| 003-T005 | Write the Alembic migration `alembic/versions/0003_online_booking.py`: | Meera | 5.0 | Meera writes the booking migration because 5 h with an exclusion constraint is over the 4 h AI limit and she has postgres; Sanjay was the runner-up. | Sanjay |
| 001-T047 | In clinic-api, implement `GET /api/clinics` and `GET /api/dentists` in | Meera | 1.5 | Meera implements GET /api/clinics and /api/dentists because they are role-scoped endpoints that stay with a person and she has api-design and backend-python; Sanjay was the runner-up. | Sanjay |
| 001-T069 | In clinic-api, implement `clinic-api/app/jobs/retention.py` with the r | Meera | 5.5 | Meera implements the retention job because 5.5 h is over the 4 h AI limit and it handles personal data, and she has backend-python and postgres; Sanjay was the runner-up. | Sanjay |
| 001-T050 | In clinic-api, document how every module must authorise in `clinic-api | Neha | 1.5 | Neha writes the access-framework doc because she is the idle docs person, and Arjun reviews for about 0.5 h, since nobody holds docs and auth-security together. | - |
| 006-T003 | Write the provider onboarding checklist `docs/messaging-providers.md`  | Neha | 3.0 | Neha writes the provider checklist because she is the project manager who can get the owners and dates from the client and providers, with Sanjay giving about 0.5 h on messaging; an AI agent must not invent those facts. | - |
| 001-T010 | In clinic-api, implement the error model in `clinic-api/app/errors.py` | Priya | 1.0 | Priya implements the error model because it needs api-design, which neither AI agent has, and she is at about 80% load; Meera was the runner-up. | Meera |
| 001-T068 | In clinic-api, write `clinic-api/tests/integration/test_retention_job. | Priya | 4.0 | Priya writes the retention job test because she has qa-automation, and Meera, who owns the job under test (001-T069), reviews for about 0.5 h, since nobody holds qa-automation and postgres together. | - |
| 001-T044 | In clinic-api, write `clinic-api/tests/integration/test_role_scope_mat | Priya | 3.5 | Priya writes the role-scope matrix tests because she has qa-automation, and Arjun reviews for about 0.5 h, since nobody holds qa-automation and auth-security together. | - |
| 001-T045 | In clinic-api, write `clinic-api/tests/integration/test_deactivation_i | Priya | 1.5 | Priya writes the deactivation tests because she has qa-automation, and Arjun reviews for about 0.5 h, since nobody holds qa-automation and auth-security together. | - |
| 001-T023 | In clinic-api, write the failing tests `clinic-api/tests/unit/test_acc | Priya | 2.5 | Priya writes the access-context tests because she has qa-automation, and Arjun, who owns 001-T024, reviews for about 0.5 h. | - |
| 004-T003 | Merge `specs/004-patient-appointments/contracts/patient-appointments.o | Priya | 1.5 | Priya merges the appointment contract because it needs api-design, which neither AI agent has; Meera was the runner-up. | Meera |
| 001-T025 | In clinic-web, implement the API client in `clinic-web/src/api/client. | Priya | 2.0 | Priya implements the web API client because the sign-in redirect and auth boundary are not fixed by the criteria, and she has frontend-react and api-design; Meera was the runner-up. | Meera |
| 001-T011 | In clinic-api, implement `GET /health` in `clinic-api/app/health.py` ( | Priya | 2.0 | Priya implements the health endpoint because it touches infrastructure and stays with a person, and she has backend-python and api-design; Meera was the runner-up. | Meera |
| 003-T006 | Create request and response models in `app/modules/booking/schemas.py` | Priya | 3.0 | Priya writes the booking schemas from the contract because they need api-design, which neither AI agent has; Meera was the runner-up. | Meera |
| 003-T009 | Create the API client `src/features/booking/api.ts`: functions for `GE | Priya | 3.0 | Priya builds the booking API client because she has frontend-react and api-design; Meera was the runner-up. | Meera |
| 001-T026 | In clinic-web, implement the session base: `clinic-web/src/auth/Sessio | Priya | 3.0 | Priya builds the web session base because it is auth-sensitive and she has frontend-react; Meera was the runner-up. | Meera |
| 002-T002 | Create the scheduling feature skeleton in repo clinic-web: `src/featur | Priya | 3.0 | Priya creates the scheduling web skeleton because she has frontend-react, and clinic-web CI is not yet approved so it cannot go to AI; Meera was the runner-up. | Meera |
| 001-T051 | In clinic-web, build `clinic-web/src/pages/RoleHome.tsx` showing the l | Priya | 3.5 | Priya builds the role-home page because it depends on role rules and she has frontend-react and frontend-css; Meera was the runner-up. | Meera |
| 001-T066 | In clinic-api, implement `clinic-api/app/identity/erasure_router.py` w | Priya | 2.0 | Priya implements the manager-only erasure endpoints because they delete personal data and she has api-design and backend-python; Meera was the runner-up. | Meera |
| 001-T063 | In clinic-api, write `clinic-api/tests/integration/test_erasure_api.py | Priya | 3.5 | Priya writes the erasure API tests because they cover manager-only deletion of personal data and she is the only person with qa-automation plus api-design; there is no runner-up. | - |
| 004-T006 | Define the interfaces `RescheduleRule.check(patient_id)` returning all | Sanjay | 1.0 | Sanjay defines these small interfaces because he has backend-python at about 69% load; Meera was the runner-up. | Meera |
| 001-T001 | In clinic-api, create the project skeleton from plan.md: `clinic-api/p | Sanjay | 3.0 | Sanjay creates the project skeleton first because he has backend-python and spare capacity, with Vikram giving about 0.5 h on the toolchain and CI layout, since nobody holds backend-python and devops-ci together. | - |
| 001-T009 | In clinic-api, implement `clinic-api/app/logging_setup.py`: JSON struc | Sanjay | 2.5 | Sanjay implements logging and OpenTelemetry because he has backend-python, with Vikram giving about 1 h on exporters, since only Vikram has observability and no AI agent has it. | - |
| 003-T002 | Create the web feature folder `src/features/booking/` with `index.ts`  | Sanjay | 1.0 | Sanjay creates the booking feature folder because he has frontend-react at about 69% load, and clinic-web CI is not yet approved so it cannot go to AI; Meera was the runner-up. | Meera |
| 001-T002 | In clinic-web, create the React and TypeScript single-page app skeleto | Sanjay | 2.5 | Sanjay creates the web app skeleton because it has more than 4 files, over the AI limit, and he has frontend-react; Meera was the runner-up. | Meera |
| 004-T010 | Extend `app/booking/history.py` with `write_event(session, appointment | Sanjay | 2.5 | Sanjay extends the appointment history writer because it writes audit rows, a sensitive area, and he has backend-python and postgres; Meera was the runner-up. | Meera |
| 005-T002 | Create the feature folders `src/features/reception/api/` and `src/feat | Sanjay | 3.0 | Sanjay creates the reception web skeleton because he has frontend-react, and clinic-web CI is not yet approved so it cannot go to AI; Meera was the runner-up. | Meera |
| 004-T009 | Implement `get_owned_appointment(session, account_id, appointment_id,  | Sanjay | 3.5 | Sanjay implements the ownership-checked appointment query because it is authorisation logic and he has postgres and backend-python; Meera was the runner-up. | Meera |
| 003-T003 | Define the three in-process ports in `app/modules/booking/ports.py`: ` | Sanjay | 4.0 | Sanjay defines the booking ports because 4 h of design judgement stays with a person and he has backend-python and api-design; Meera was the runner-up. | Meera |
| 001-T049 | In clinic-api, implement `GET /api/patients?q=` in `clinic-api/app/ide | Sanjay | 2.5 | Sanjay implements patient search because it exposes personal data under role rules and he has backend-python and postgres; Meera was the runner-up. | Meera |
| 001-T067 | In clinic-web, build `clinic-web/src/pages/manager/ErasurePage.tsx` (f | Sanjay | 3.5 | Sanjay builds the erasure page because it is an irreversible UI whose criteria cover only part of the page, and he has frontend-react; Meera was the runner-up. | Meera |
| 001-T065 | In clinic-api, implement `clinic-api/app/identity/erasure_service.py`: | Sanjay | 4.5 | Sanjay implements the erasure service because 4.5 h is over the AI limit and it handles personal data, and he has backend-python and postgres; Meera was the runner-up. | Meera |
| 001-T003 | In clinic-api, add linting and formatting configuration in `clinic-api | Vikram | 3.0 | Vikram writes the clinic-api CI workflow because he is the only person with devops-ci, with Sanjay giving about 0.5 h on the lint and test layout; this task gates everything else. | - |
| 001-T004 | In clinic-web, add linting and formatting configuration in `clinic-web | Vikram | 2.0 | Vikram writes the clinic-web CI workflow because he is the only person with devops-ci, with Meera giving about 0.5 h on package.json; this task gates everything else. | - |

## Unassigned tasks

None. All 79 sprint 1 tasks have an assignee in `assignments.json` (version 3): 73 tasks for people (192.0 h) and 6 for AI agents (12.5 h).

The 16 tasks left unassigned in version 2 failed because each needs two skills in one person (for example devops-ci and backend-python), and no person has those pairs. The word `human` in the old message was not a skill; it only marked the task as human-only. I fixed the cause: the owners from the earlier owner/pair table were applied as pins, and the second skill is covered by a named reviewer or pair (table below). The solver cannot count pair hours, so they appear only in this note.

## Sprint 1 load and decisions for P4-G3

### Load per person, including pair and review hours

| Person | Task h (in assignments.json) | Pair or review h (not in solver) | Total h | Capacity h | Load |
|---|---|---|---|---|---|
| Arjun | 38.0 | 3.5 (reviews tests 001-T020, T023, T036, T037, T044, T045, and doc 001-T050) | 41.5 | 48.6 | 85% |
| Kavya | 41.5 | 0 | 41.5 | 48.6 | 85% |
| Priya | 39.0 | 0 | 39.0 | 48.6 | 80% |
| Sanjay | 33.5 | 1.5 (001-T003, 001-T019, 006-T003) | 35.0 | 48.6 | 72% |
| Meera | 30.5 | 1.0 (001-T004, 001-T068) | 31.5 | 48.6 | 65% |
| Vikram | 5.0 | 3.5 (001-T001, 001-T009, 001-T012, 003-T008) | 8.5 | 12.2 | 70% |
| Neha | 4.5 | 0 | 4.5 | 27.0 | 17% |
| Rohan | 0.0 | 0 | 0.0 | 24.3 | 0% |
| Claude Code | 6.5 | human PR review about 0.5 h per task | 6.5 | 35.0 | 19% |
| Copilot | 6.0 | human PR review about 0.5 h per task | 6.0 | 36.0 | 17% |

- Vikram and Neha now have work. Both were at 0 h before.
- Rohan stays at 0 h. No sprint 1 task needs ux-design, so there is nothing to give him. He can review the usability of 001-T042, T043, T051 and T067.
- The six AI pull requests need about 3 h of human review in total. Meera and Sanjay have the most room, so they should take it.
- Kavya and Arjun are the most loaded. Arjun's auth chain (001-T038, T039, T021, T024, T040) is long, so a delay there delays the sprint goal. Kavya can be eased with decision 2 below.

### Pairs that cover the missing skill combinations

| Task | Owner | Second person | Why |
|---|---|---|---|
| 001-T001 | Sanjay (backend-python) | Vikram 0.5 h on toolchain and CI layout | Only Vikram has devops-ci |
| 001-T003 | Vikram (devops-ci) | Sanjay 0.5 h on lint and tests | Python side of CI |
| 001-T004 | Vikram | Meera 0.5 h on package.json | She owns the web skeleton 001-T002 |
| 001-T009, 003-T008 | Sanjay, Meera (backend-python) | Vikram 1.0 h each on OpenTelemetry | Only Vikram has observability |
| 001-T012 | Kavya (qa-automation) | Vikram 1.0 h on the PostgreSQL service in CI | qa-automation and postgres are never in one person |
| 001-T019 | Kavya | Sanjay 0.5 h on constraint cases | Same |
| 001-T068 | Priya | Meera 0.5 h; she owns the job under test | Same |
| 001-T020, T023, T036, T037, T044, T045 | Kavya or Priya (qa-automation) | Arjun 0.5 h each | Only Arjun has auth-security |
| 001-T050 | Neha (docs) | Arjun 0.5 h | Same |
| 006-T003 | Neha (docs) | Sanjay 0.5 h on messaging | She can get owners and dates from the client |

The tasks 001-T001, T003 and T004 gate everything else. Order: 001-T001 on day 1, then 001-T003 and 001-T004 in parallel. The AI tasks should wait for 001-T003 to merge. Skills held by one person only: devops-ci, observability, terraform and kubernetes (Vikram); auth-security and data-modeling (Arjun). Training a second person in each would remove the key-person risk.

### Decision 1: five clinic-api tasks blocked by a wrong repo tag (approver override needed)

This is the only note on the tool mapping. The eligibility tool reads each task's `repo` field in `backlog/backlog.json`. For 13 clinic-api tasks that field says `brightsmile/clinic-web` (003-T001, T003, T004, T006, T008; 004-T003, T004, T005, T006, T007, T008, T009, T011), although their descriptions and file paths are clinic-api. The tool therefore applies the clinic-web CI rule and does not offer them to AI. The clinic-api CI is approved.

I did not edit `backlog.json`: it belongs to the backlog agent and `sprint-plan.json` records its hash, so an edit would break the match. Two ways to fix it:

- The backlog agent corrects the `repo` field of those 13 tasks, and sprint 1 is re-run. Only five of them would then go to AI (the other eight need api-design, data-modeling, postgres or observability, or involve privacy or ownership checks, so they stay with people).
- Or the approver gives an explicit override now. I recommend pinning: 003-T001 to Copilot, 004-T004 and 004-T005 to Claude Code, 004-T007 to Copilot, and 004-T006 to Claude Code. All five are small (1.0 to 2.5 h, 8.0 h in total), have concrete criteria and need only backend-python or qa-automation. If approved, Kavya drops to about 34.5 h (71%) and Sanjay to about 34.0 h (70%). Until then they stay with the people named in the table.

### Decision 2: sprint scope is 35 SP against P85 of 28.4 (planner and approver decision)

With every task assigned, the hours fit: the highest person load is 85% and the 192 h of human work is well below the 306.5 h of human capacity. Hours are therefore not the limit; the risk is velocity. 35 SP holds only if velocity reaches P50 (35.4).

The first to slip, by lowest WSJF and not needed for the sprint goal, are S-001-US6 (erasure, 3 SP, tasks 001-T062 to T067, 18.0 h) and S-001-US7 (retention, 2 SP, tasks 001-T068 to T070, 12.0 h). Dropping both gives 30 SP, which is still 1.6 SP above P85, and frees 25.5 h of human time: on task hours alone, Priya to about 61%, Sanjay 52%, Meera 51%, Kavya 80%, Arjun unchanged at 85%. I cannot remove tasks from the sprint with my tools. The sprint planner must re-plan if the approver chooses this, and I will re-run the allocation.

### Other eligibility notes

- 001-T013 is now with Claude Code. It is a one-file test with two concrete outcomes and runs after 001-T012. Keeping it with Kavya only for cost balance was not a valid reason.
- 001-T005, 001-T010 and 001-T014 are self-contained enough for AI, but they need api-design or data-modeling and postgres, which neither AI agent has, so they stay with people.
- 001-T009 and 001-T070 are not given to AI. 001-T009 is app-wide middleware with an untestable OpenTelemetry criterion and needs observability. 001-T070 starts a daily scheduler that can run twice across replicas and triggers deletion of personal data.
- 001-T068 has a bare `registry.py` in its file scope that the backlog agent should correct to `clinic-api/app/jobs/registry.py`.

## AI eligibility

- 005-T001: eligible — Empty reception package plus one router registration; 4 files, 3 h, both criteria checked by app start and CI; no auth, data or product decision.
- 002-T001: eligible — Skeleton package and settings with two defaults (30, 31) and an env override; criteria testable by a unit test; two files.
- 001-T005: eligible — Copy of an existing contract file; checkable by OpenAPI validation and path diff; no logic. Needs api-design, which neither agent has.
- 001-T062: eligible — Single unit-test file with three exact-value criteria; test only, no production change.
- 001-T064: eligible — One small registry module with two concrete criteria; self-contained.
- 001-T008: eligible — One test file, 1 h, two concrete criteria on masking and correlation_id; no auth or secrets.
- 001-T010: eligible — Single module with codes defined by the contract and two concrete criteria. Needs api-design, which neither agent has.
- 001-T013: eligible — One small integration test file, 1 h, two concrete outcomes (200 with db ok; 503 on a closed port), test only. It must start after 001-T012 provides the test database, which is sequencing, not a reason to keep it human.
- 001-T014: eligible — One models file with fully specified columns and constraints. Needs data-modeling and postgres, which neither agent has.
