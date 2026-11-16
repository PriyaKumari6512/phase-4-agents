# Tasks: Platform, sign-in, roles and clinics (MOD-01)

**Input**: Design documents from `/specs/001-platform-identity/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/identity-api.openapi.yaml, quickstart.md

**Tests**: Included. The constitution requires tests first for business logic and an independent test per story. Write each story's test tasks first and see them fail before the implementation.

**Organization**: Setup, Foundational (the shared foundation), then one phase per user story in priority order, then Polish.

**Repositories**: `clinic-api` = `brightsmile/clinic-api` (Python 3.12, FastAPI, SQLAlchemy, Alembic); `clinic-web` = `brightsmile/clinic-web` (React and TypeScript). Every task says which repository it changes; paths start with the repository folder name.

## Format: `- [ ] T### [P?] [US#] Description with file path`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[US#]**: the user story of `spec.md` (story phases only)
- `(depends on T###)` at the end names a needed task that is not directly before it

## Source requirements (prd.md ids)

| Story / phase | prd.md ids |
|---|---|
| Foundation (Setup, Foundational) | NFR-006, NFR-009 |
| US1 Patient sign-in with phone code | FR-002, NFR-006 |
| US2 Staff sign-in | FR-003, NFR-006 |
| US3 Roles see only what they need | FR-004, NFR-006 |
| US4 Staff account management | FR-005, NFR-006 |
| US5 Clinics and dentists as data | FR-001 |
| US6 Erasure on request | NFR-007 |
| US7 Retention job | NFR-007 |
| Polish (release readiness) | NFR-006, NFR-007, NFR-009 |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Both repositories start, build and test in CI.

- [ ] T001 [P] In clinic-api, create the project skeleton from plan.md: `clinic-api/pyproject.toml` (Python 3.12; FastAPI, SQLAlchemy, Alembic, an argon2 library, a JWT library, OpenTelemetry packages, pytest), empty packages `clinic-api/app/__init__.py`, `clinic-api/app/identity/__init__.py`, `clinic-api/app/scheduling/__init__.py`, `clinic-api/app/jobs/__init__.py`, test folders `clinic-api/tests/unit/`, `clinic-api/tests/contract/`, `clinic-api/tests/integration/`, and `clinic-api/Dockerfile` (port 8000, no secrets in the image)
- [ ] T002 [P] In clinic-web, create the React and TypeScript single-page app skeleton: `clinic-web/package.json`, `clinic-web/tsconfig.json`, `clinic-web/index.html`, `clinic-web/src/main.tsx`, `clinic-web/src/App.tsx` and the unit-test runner configuration in `clinic-web/package.json`; the web app holds no data and calls only `/api`
- [ ] T003 [P] In clinic-api, add linting and formatting configuration in `clinic-api/pyproject.toml` and the CI workflow `clinic-api/.github/workflows/ci.yml` (build, unit tests, contract tests, integration tests against a PostgreSQL 16 service container, image scan placeholder step)
- [ ] T004 [P] In clinic-web, add linting and formatting configuration in `clinic-web/package.json` and the CI workflow `clinic-web/.github/workflows/ci.yml` (build, unit tests)
- [ ] T005 [P] In clinic-api, copy `specs/001-platform-identity/contracts/identity-api.openapi.yaml` to `clinic-api/contracts/clinic-api-v1.openapi.yaml` as the start of contract `api-clinic-api-v1` (version 1.0.0); later features add their paths to this file

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The foundation every other feature builds on: configuration, database migrations, health endpoint, logging, error model, the session framework, the access (RBAC and clinic scope) framework, and the web client base.

**CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T006 [P] In clinic-api, implement settings from environment variables in `clinic-api/app/config.py`: `DATABASE_URL`, `JWT_SIGNING_KEY`, `HASH_SECRET`, `ALLOWED_ORIGINS`, `COOKIE_SECURE` (default true), `REQUIRE_HTTPS` (default true), `SMS_SENDER` (default `fake`), `OTP_TTL_MINUTES=10`, `OTP_MAX_WRONG=5`, `LOCK_MINUTES=15`, `CODES_PER_IP_PER_HOUR=10`, `CODES_PER_PHONE_PER_DAY=10`, `STAFF_SESSION_HOURS=8`, `STAFF_IDLE_MINUTES=30`, `PATIENT_SESSION_DAYS=7`, `STAFF_MIN_PASSWORD=10`, `RETENTION_ENABLED` (default true); startup fails with a clear message when a secret is missing; no secret has a default value in code
- [ ] T007 In clinic-api, set up the database layer and migrations: `clinic-api/app/db.py` (engine, session dependency, statement timeout 5 s), `clinic-api/alembic.ini`, `clinic-api/migrations/env.py` reading `DATABASE_URL` (depends on T001, T006)
- [ ] T008 [P] In clinic-api, write the failing test `clinic-api/tests/unit/test_logging_pii.py`: a log line containing a name, a phone number or a birth year field is masked or refused by the log filter, and every line carries `correlation_id`
- [ ] T009 In clinic-api, implement `clinic-api/app/logging_setup.py`: JSON structured logs, correlation id middleware, a filter that masks phone-number-like values and drops fields named `name`, `phone`, `birth_year`, and OpenTelemetry logs, metrics and traces set-up (constitution principle II) (depends on T008)
- [ ] T010 [P] In clinic-api, implement the error model in `clinic-api/app/errors.py`: JSON body `{code, message, retry_after_seconds?, tries_left?}` with the codes of `contracts/identity-api.openapi.yaml` (NOT_SIGNED_IN 401, FORBIDDEN 403, validation 422), plain English messages
- [ ] T011 In clinic-api, implement `GET /health` in `clinic-api/app/health.py` (200 `{status, database, version}` after a trivial database query, 503 when the database is unreachable, no authentication, answers within 1 second) and the app factory in `clinic-api/app/main.py` wiring settings, logging, error handlers, the `/api` router prefix and `/docs` (depends on T006, T007, T009, T010)
- [ ] T012 In clinic-api, create shared test fixtures in `clinic-api/tests/conftest.py`: PostgreSQL 16 test database with migrations applied, API test client, `FakeSmsSender` outbox fixture, controllable clock, and factories for a staff account of each role, a patient account, a clinic, and a session cookie for any of them (depends on T007, T011)
- [ ] T013 In clinic-api, add the integration test `clinic-api/tests/integration/test_health.py` (200 with database ok; 503 when the engine is pointed at a closed port) (depends on T012)
- [ ] T014 [P] In clinic-api, define the scheduling models in `clinic-api/app/scheduling/models.py`: `clinic` (`name` text NOT NULL unique case-insensitive, 1 to 80 chars; `address` 1 to 300; `phone` 5 to 20; `active` default true), `dentist` (`name` 1 to 120 chars; `active` default true; `deactivated_at`; `anonymised_at`), `dentist_clinic_day` (`weekday` smallint CHECK 0 to 6, UNIQUE (dentist_id, weekday))
- [ ] T015 In clinic-api, write migration `clinic-api/migrations/versions/0001_scheduling_clinics_dentists.py` creating the three scheduling tables and an idempotent seed of the clinics Indiranagar and Whitefield (active, placeholder address and phone), plus `clinic-api/app/scheduling/seed.py` with the same seed for tests (depends on T007, T014)
- [ ] T016 [P] In clinic-api, define the identity models in `clinic-api/app/identity/models.py` exactly as `data-model.md`: `staff_account` (unique `lower(username)`; CHECK `clinic_id` NOT NULL when role = receptionist; CHECK `dentist_id` NOT NULL and unique when role = dentist; `failed_attempts` default 0; `locked_until`), `patient_account` (`phone` NOT NULL UNIQUE; `preferred_channel` `sms` or `whatsapp` default `sms`; `reminders_opt_out` default false), `patient` (`name` 1 to 120; `birth_year` NULL, CHECK 1900 to current year; partial UNIQUE index one `is_account_holder` per account), `otp_challenge` (`phone` UNIQUE; `wrong_tries` 0 to 5; `locked_until`; `verified_at`), `auth_session` (CHECK exactly one owner column set), `sign_in_throttle` (UNIQUE (kind, key_hash, window_start)), `erasure_request` (`due_at` = `requested_at` + 30 days)
- [ ] T017 In clinic-api, write migration `clinic-api/migrations/versions/0002_identity_accounts.py` creating `staff_account`, `patient_account`, `patient` and `otp_challenge` with the constraints of T016 (depends on T015, T016)
- [ ] T018 In clinic-api, write migration `clinic-api/migrations/versions/0003_identity_sessions_throttle_erasure.py` creating `auth_session`, `sign_in_throttle` and `erasure_request` with indexes on `auth_session(staff_account_id)`, `auth_session(patient_account_id)` and `sign_in_throttle(kind, key_hash, window_start)` (depends on T017)
- [ ] T019 In clinic-api, add `clinic-api/tests/integration/test_migrations.py`: upgrade to head on an empty database, seed present, every CHECK and UNIQUE constraint of T016 rejects a bad row, and the previous revision still upgrades (depends on T012, T018)
- [ ] T020 [P] In clinic-api, write the failing tests `clinic-api/tests/unit/test_sessions.py` (staff expire at the earlier of 8 hours after sign-in and 30 minutes idle; patient expires 7 days after last use; `last_used_at` refreshed at most once a minute; revoked session refused; owner inactive refused; tampered or expired JWT refused; cookie flags `HttpOnly`, `Secure`, `SameSite=Strict`) and `clinic-api/tests/unit/test_security_middleware.py` (write without header `X-Requested-With: brightsmile` refused; Origin not in `ALLOWED_ORIGINS` refused; reads unaffected; plain HTTP refused when `REQUIRE_HTTPS=true`)
- [ ] T021 In clinic-api, implement `clinic-api/app/identity/sessions.py`: create session row and signed JWT carrying only `jti` and owner id, set and clear the `bs_session` cookie, validate (load row and owner, apply the expiry rules), refresh, revoke one session, revoke all sessions of an owner (depends on T016, T018, T020)
- [ ] T022 In clinic-api, implement `clinic-api/app/identity/security.py`: middleware for the CSRF header and Origin check on POST, PUT, PATCH, DELETE and the HTTPS check using `X-Forwarded-Proto`; register it in `clinic-api/app/main.py` (depends on T011, T020)
- [ ] T023 [P] In clinic-api, write the failing tests `clinic-api/tests/unit/test_access.py`: `AccessContext` is built from the session owner only; role, clinic ids and active flag are re-read from the database on every call; receptionist `clinic_ids` is its one clinic; dentist `clinic_ids` come from its dentist record; manager sees all clinics; patient `patient_ids` are the persons of its account; `require_role`, `require_clinic` and `clinic_filter` behave as `research.md` R7 says; ids from the request never widen scope
- [ ] T024 In clinic-api, implement `clinic-api/app/identity/access.py`: `AccessContext` dataclass and the FastAPI dependencies `current_access`, `require_staff`, `require_role(*roles)`, `require_manager`, and the helpers of T023; unsigned callers get NOT_SIGNED_IN (needs security review) (depends on T016, T021, T023)
- [ ] T025 [P] In clinic-web, implement the API client in `clinic-web/src/api/client.ts`: base path `/api`, credentials included, header `X-Requested-With: brightsmile` on every write, JSON error mapping to `{code, message, retry_after_seconds, tries_left}`, redirect to the right sign-in on NOT_SIGNED_IN (depends on T002)
- [ ] T026 [P] In clinic-web, implement the session base: `clinic-web/src/auth/SessionContext.tsx` (loads `GET /api/me`, exposes role and clinic ids, sign-out), `clinic-web/src/auth/RequireRole.tsx` (route guard by role) and the route table in `clinic-web/src/App.tsx` (depends on T025)

**Checkpoint**: Foundation ready. `GET /health` answers, migrations run from empty, sessions and the access context work; the user stories can start in parallel.

---

## Phase 3: User Story 1 - A patient signs in with a phone number and a code (Priority: P1) 🎯 MVP

**Goal**: A patient signs in with phone and SMS code, a new number creates an account after the name is given, code limits and the 15-minute wait work, the session lasts 7 days from last use. (source: FR-002, NFR-006)

**Independent Test**: With the fake SMS sender, request a code, verify it, register a new patient, check `GET /api/me`; give 5 wrong codes and see the 15-minute wait; exceed the per-IP limit and see no SMS in the outbox.

### Tests for User Story 1 (write first, see them fail)

- [ ] T027 [P] [US1] In clinic-api, write unit tests `clinic-api/tests/unit/test_phone.py` (accepts `9876543210` and `+91 98765 43210`, stores `+91` plus 10 digits starting 6 to 9, refuses others), `clinic-api/tests/unit/test_throttle.py` (per-IP and per-phone-per-day counters, window rollover, keys stored hashed) and `clinic-api/tests/unit/test_otp_service.py` (6 digits, stored as keyed hash, valid 10 minutes, newest code replaces the older one but keeps `wrong_tries` and `locked_until`, 5th wrong try locks for 15 minutes, right code during lock refused, expired code, SMS failure does not count as a wrong try)
- [ ] T028 [P] [US1] In clinic-api, write `clinic-api/tests/integration/test_patient_sign_in.py` (existing patient signs in; new patient gets `name_required` then registers; two parallel registrations for one phone create one account; wrong, expired, locked and too-many-codes answers carry the contract's error codes and `tries_left` / `retry_after_seconds`; patient session still valid after 6 days idle and refused after 7) and `clinic-api/tests/contract/test_patient_auth_contract.py` against `/auth/patient/*` in `contracts/clinic-api-v1.openapi.yaml`

### Implementation for User Story 1

- [ ] T029 [P] [US1] In clinic-api, implement phone normalisation in `clinic-api/app/identity/phone.py`
- [ ] T030 [P] [US1] In clinic-api, implement the SMS sender port in `clinic-api/app/identity/sms_port.py`: `SmsSender` protocol `send_code(phone, code) -> SendResult` and `FakeSmsSender` with an in-memory outbox, chosen by `SMS_SENDER`; the real provider adapter is added later by the messaging features (ADR-0006)
- [ ] T031 [US1] In clinic-api, implement the throttle in `clinic-api/app/identity/throttle.py`: increment and check `sign_in_throttle` rows for `ip_hour` and `phone_day` with HMAC keys using `HASH_SECRET`; refuse before any SMS is sent (depends on T018)
- [ ] T032 [US1] In clinic-api, implement `clinic-api/app/identity/otp_service.py`: issue (normalise phone, check lock, check throttle, generate with `secrets`, upsert `otp_challenge`, send through the port), verify (expiry, constant-time compare, count wrong tries, lock 15 minutes at 5, mark `verified_at` when no account exists) (depends on T029, T030, T031)
- [ ] T033 [US1] In clinic-api, implement `clinic-api/app/identity/patient_accounts_service.py`: sign in an existing account (update `last_used_at`), create `patient_account` plus its account-holder `patient` in one transaction only for a phone verified within the last 10 minutes, race-safe on the unique phone (depends on T016)
- [ ] T034 [US1] In clinic-api, implement `clinic-api/app/identity/patient_auth_router.py` with `POST /api/auth/patient/code-requests` (202, 422, 423, 429, 502), `POST /api/auth/patient/code-verifications` and `POST /api/auth/patient/registration` per the contract, set the session cookie through `sessions.py`, log ids only, and include the router in `clinic-api/app/main.py` (needs security review) (depends on T021, T032, T033)
- [ ] T035 [P] [US1] In clinic-web, build `clinic-web/src/pages/patient/SignInPage.tsx` (phone step, code step with "send a new code", name step for new patients, plain English messages for wrong code with tries left, expired code, 15-minute wait with the time to try again, too many codes with the clinic phone number), add the route `/sign-in` in `clinic-web/src/App.tsx`, and a test `clinic-web/src/tests/SignInPage.test.tsx` (depends on T026)

**Checkpoint**: A patient can sign in and register; US1 testable alone.

---

## Phase 4: User Story 2 - Staff sign in with a username and password (Priority: P1)

**Goal**: Receptionists, dentists and the practice manager sign in with username and password (10 characters minimum), lockout after 5 failures for 15 minutes, 8-hour and 30-minute-idle sessions, sign-out. (source: FR-003, NFR-006)

**Independent Test**: Seed a manager, sign in, change the password, fail 5 times and see the lock, let a session idle past 30 minutes and see it refused, sign out and reuse the cookie.

### Tests for User Story 2 (write first, see them fail)

- [ ] T036 [P] [US2] In clinic-api, write unit tests `clinic-api/tests/unit/test_passwords.py` (argon2id hash, verify, "at least 10 characters" enforced at 9 and 10, hash never equals the password) and `clinic-api/tests/unit/test_staff_auth_service.py` (same message for unknown user and wrong password, 5 failures lock for 15 minutes, right password during lock refused, success resets the counter, inactive account refused, username compared case-insensitively)
- [ ] T037 [P] [US2] In clinic-api, write `clinic-api/tests/integration/test_staff_sign_in.py` (sign-in, lock, idle 30 minutes, absolute 8 hours, sign-out ends the session, `must_change_password` flag, password change ends other sessions) and `clinic-api/tests/contract/test_staff_auth_contract.py` against `/auth/staff/*` and `/auth/sign-out`

### Implementation for User Story 2

- [ ] T038 [P] [US2] In clinic-api, implement `clinic-api/app/identity/passwords.py`: argon2id hash and verify, `validate_staff_password` raising a plain English error under `STAFF_MIN_PASSWORD` characters, and a dummy verify for unknown usernames
- [ ] T039 [US2] In clinic-api, implement `clinic-api/app/identity/staff_auth_service.py`: authenticate (lookup lower-case username, lock check, verify, failure counting and `locked_until`, reset on success), change own password (verify current, validate new, revoke other sessions) (depends on T038, T021)
- [ ] T040 [US2] In clinic-api, implement `clinic-api/app/identity/staff_auth_router.py` with `POST /api/auth/staff/sign-in`, `PUT /api/auth/staff/password` and `POST /api/auth/sign-out` (any role) per the contract, and include it in `clinic-api/app/main.py` (needs security review) (depends on T039)
- [ ] T041 [US2] In clinic-api, implement the idempotent first-manager seed `clinic-api/app/identity/seed.py` (`python -m app.identity.seed`) reading `SEED_MANAGER_USERNAME` and `SEED_MANAGER_PASSWORD` from the environment, `must_change_password=true`, refusing a password under 10 characters (depends on T038, T017)
- [ ] T042 [P] [US2] In clinic-web, build `clinic-web/src/pages/staff/StaffSignInPage.tsx` (username, password, wrong credentials message, locked message with minutes left, redirect to the role's home or to the password change page when `must_change_password`), route `/staff/sign-in` in `clinic-web/src/App.tsx`, and test `clinic-web/src/tests/StaffSignInPage.test.tsx` (depends on T026)
- [ ] T043 [P] [US2] In clinic-web, build `clinic-web/src/pages/staff/ChangePasswordPage.tsx` (current and new password, "at least 10 characters" message) with test `clinic-web/src/tests/ChangePasswordPage.test.tsx` (depends on T026)

**Checkpoint**: Staff can sign in; US1 and US2 work independently.

---

## Phase 5: User Story 3 - Each role sees only what it needs (Priority: P1)

**Goal**: Every request is authorised on the server from the signed-in owner's role, clinic and active flag; receptionists see their own clinic only; dentists read only; manager sees all; deactivation acts at once; other modules reuse the framework. (source: FR-004, NFR-006)

**Independent Test**: One account per role calls the same protected operations and gets exactly the allowed results; a receptionist sending the other clinic's id is refused; a deactivated account is refused on its next request.

### Tests for User Story 3 (write first, see them fail)

- [ ] T044 [P] [US3] In clinic-api, write `clinic-api/tests/integration/test_role_scope_matrix.py` (table of role x operation: `GET /api/me`, `GET /api/clinics`, `GET /api/dentists`, `GET /api/patients?q=`, a write on `/api/clinics`; receptionist gets only own clinic and is refused on the other clinic's id; dentist is read only; patient cannot pass another patient's id; unsigned gets 401; patient search finds patients of any clinic for a receptionist) and `clinic-api/tests/contract/test_me_clinics_dentists_contract.py` against `/me`, `/patients`, `GET /clinics`, `GET /dentists`
- [ ] T045 [P] [US3] In clinic-api, write `clinic-api/tests/integration/test_deactivation_immediacy.py`: deactivating an account, changing a receptionist's clinic, or changing a role takes effect on the very next request with the same cookie (0 requests accepted after deactivation)

### Implementation for User Story 3

- [ ] T046 [US3] In clinic-api, implement the read side of scheduling in `clinic-api/app/scheduling/schemas.py` and `clinic-api/app/scheduling/service.py`: `list_clinics(ctx)` (patient: active clinics; receptionist: own clinic; dentist: clinics of its record; manager: all) and `list_dentists(ctx)` (receptionist: dentists working at own clinic; dentist: self; manager: all; patient: active dentists), each returning `clinic_days`, all scope taken from `AccessContext` (depends on T014, T024)
- [ ] T047 [US3] In clinic-api, implement `GET /api/clinics` and `GET /api/dentists` in `clinic-api/app/scheduling/router.py` and include the router in `clinic-api/app/main.py` (depends on T046)
- [ ] T048 [P] [US3] In clinic-api, implement `GET /api/me` in `clinic-api/app/identity/me_router.py` returning kind, id, name, role, `clinic_ids` and `must_change_password` read fresh from the database, and include it in `clinic-api/app/main.py` (depends on T024)
- [ ] T049 [P] [US3] In clinic-api, implement `GET /api/patients?q=` in `clinic-api/app/identity/patients_router.py`: receptionist and manager only, minimum 3 characters, matches phone digits or name, escapes wildcard characters, returns id, name and phone only (no appointments, which stay clinic-scoped in their own module), ignores anonymised patients (ASM-011) (depends on T024)
- [ ] T050 [P] [US3] In clinic-api, document how every module must authorise in `clinic-api/docs/access-framework.md`: use `AccessContext`, never trust ids from the request alone, use `clinic_filter`, the role table of FR-004 of the PRD, and the rule that an authentication or authorisation change needs security review (depends on T024)
- [ ] T051 [P] [US3] In clinic-web, build `clinic-web/src/pages/RoleHome.tsx` showing the links each role may use (patient: sign-in state; receptionist: own clinic name; dentist: own clinics; manager: staff, clinics and dentists, erasure) with route guards from `clinic-web/src/auth/RequireRole.tsx` in `clinic-web/src/App.tsx`, and test `clinic-web/src/tests/RoleHome.test.tsx` (depends on T026, T048)

**Checkpoint**: Role separation proven by tests; other modules can build on it.

---

## Phase 6: User Story 4 - The practice manager manages staff accounts (Priority: P1)

**Goal**: The manager creates, edits, deactivates, reactivates staff accounts, assigns receptionists to a clinic, links dentists, resets passwords; deactivation acts at once. (source: FR-005, NFR-006)

**Independent Test**: As manager create a receptionist for Whitefield, sign in as them and see Whitefield only, deactivate them and see sign-in and the old session refused.

### Tests for User Story 4 (write first, see them fail)

- [ ] T052 [P] [US4] In clinic-api, write unit tests `clinic-api/tests/unit/test_staff_accounts_service.py`: receptionist needs a clinic; dentist needs a dentist record not already linked; username unique case-insensitively; password at least 10 characters; the last active manager cannot be deactivated; deactivation revokes all the person's sessions; reset clears `failed_attempts` and `locked_until`, sets `must_change_password` and revokes sessions
- [ ] T053 [P] [US4] In clinic-api, write `clinic-api/tests/integration/test_staff_accounts_api.py` (manager creates, lists, edits, deactivates, reactivates, resets; receptionist, dentist and patient get 403 on every operation; a deactivated person cannot sign in) and `clinic-api/tests/contract/test_staff_accounts_contract.py` against `/staff-accounts*`

### Implementation for User Story 4

- [ ] T054 [US4] In clinic-api, implement `clinic-api/app/identity/staff_accounts_service.py`: create, update name and clinic, deactivate (set `deactivated_at`, revoke sessions), reactivate, reset password, and the last-manager guard, with the field rules of `data-model.md` (depends on T038, T021, T016)
- [ ] T055 [US4] In clinic-api, implement `clinic-api/app/identity/staff_accounts_router.py` with `GET` and `POST /api/staff-accounts`, `PATCH /api/staff-accounts/{account_id}` and `POST /api/staff-accounts/{account_id}/password-reset`, all through `require_manager`, error codes USERNAME_TAKEN and LAST_MANAGER, and include it in `clinic-api/app/main.py` (needs security review) (depends on T054, T024)
- [ ] T056 [P] [US4] In clinic-web, build `clinic-web/src/pages/manager/StaffAccountsPage.tsx` (list, create form with role, clinic or dentist, temporary password; deactivate, reactivate, reset password; messages for taken username and last manager), route `/manager/staff` in `clinic-web/src/App.tsx`, and test `clinic-web/src/tests/StaffAccountsPage.test.tsx` (depends on T026, T047)

**Checkpoint**: Staff are managed without developer help.

---

## Phase 7: User Story 5 - The system holds the clinics and the dentists (Priority: P1)

**Goal**: Two clinics exist from the start; the manager adds clinics and dentists, sets the weekdays a dentist works at each clinic, deactivates them; a third clinic needs no deployment. (source: FR-001)

**Independent Test**: Fresh database lists Indiranagar and Whitefield; as manager add a third clinic and a dentist with Monday at Indiranagar and Thursday at Whitefield; a second clinic on the same Monday is refused.

### Tests for User Story 5 (write first, see them fail)

- [ ] T057 [P] [US5] In clinic-api, write unit tests `clinic-api/tests/unit/test_scheduling_service.py`: clinic name unique case-insensitively; one clinic per dentist per weekday (`DENTIST_DOUBLE_DAY`); weekday 0 to 6; inactive clinic and inactive dentist excluded from the lists patients and receptionists use while existing references stay readable; deactivating a clinic reports how many receptionists are still assigned to it
- [ ] T058 [P] [US5] In clinic-api, write `clinic-api/tests/integration/test_clinics_dentists_admin.py` (both seeded clinics present on a fresh database; manager adds a third clinic and it shows in `GET /api/clinics` at once; dentist at two clinics on different days; same weekday twice gives 409; receptionist, dentist and patient get 403 on every write) and `clinic-api/tests/contract/test_clinics_dentists_contract.py` against `/clinics*` and `/dentists*`

### Implementation for User Story 5

- [ ] T059 [US5] In clinic-api, extend `clinic-api/app/scheduling/service.py` with `create_clinic`, `update_clinic` (including deactivate and the count of assigned receptionists in the answer), `create_dentist`, `update_dentist` and `set_clinic_days` (replace the list in one transaction), keeping the field rules of `data-model.md` (depends on T046)
- [ ] T060 [US5] In clinic-api, extend `clinic-api/app/scheduling/router.py` with `POST /api/clinics`, `PATCH /api/clinics/{clinic_id}`, `POST /api/dentists`, `PATCH /api/dentists/{dentist_id}` and `PUT /api/dentists/{dentist_id}/clinic-days`, all writes through `require_manager`, error codes CLINIC_NAME_TAKEN and DENTIST_DOUBLE_DAY (depends on T047, T059)
- [ ] T061 [P] [US5] In clinic-web, build `clinic-web/src/pages/manager/ClinicsDentistsPage.tsx` (clinics with add, edit, deactivate; dentists with add, deactivate, and a weekday-by-clinic picker; warning when receptionists are still assigned to a deactivated clinic), route `/manager/clinics` in `clinic-web/src/App.tsx`, and test `clinic-web/src/tests/ClinicsDentistsPage.test.tsx` (depends on T026, T047)

**Checkpoint**: Clinics and dentists are data; a third clinic is added in the screens (QA-011).

---

## Phase 8: User Story 6 - A patient's data is erased on request (Priority: P2)

**Goal**: The manager records an erasure request (due in 30 days, overdue flagged) and carries it out by anonymising the person and account, ending sessions and anonymising messages through a step later features add. (source: NFR-007)

**Independent Test**: Create a patient, record and execute an erasure, check name, phone and birth year are gone, the old session is refused and the same phone can sign up as a new account.

### Tests for User Story 6 (write first, see them fail)

- [ ] T062 [P] [US6] In clinic-api, write unit tests `clinic-api/tests/unit/test_erasure_service.py`: record sets `due_at` = `requested_at` + 30 days; execute replaces name by "Erased patient", birth year by null, phone by `erased-<id>`, resets channel, revokes sessions, sets `anonymised_at`; running it twice is safe; registered extra steps run; overdue flag when open and past `due_at`; log lines hold the account id only
- [ ] T063 [P] [US6] In clinic-api, write `clinic-api/tests/integration/test_erasure_api.py` (manager records and executes; unknown phone gives ACCOUNT_NOT_FOUND; second execution gives ALREADY_DONE; receptionist, dentist and patient get 403; the old phone signs up as a brand-new account) and `clinic-api/tests/contract/test_erasure_contract.py` against `/erasure-requests*`

### Implementation for User Story 6

- [ ] T064 [US6] In clinic-api, implement the registries in `clinic-api/app/jobs/registry.py`: `register_erasure_step(name, fn)` and `register_retention_rule(name, fn)` so later features (messages, appointments) add their steps without changing identity code
- [ ] T065 [US6] In clinic-api, implement `clinic-api/app/identity/erasure_service.py`: `record_request(phone, manager)`, `execute(request_id, manager)` anonymising `patient`, `patient_account`, deleting the `otp_challenge` row of that phone, revoking sessions, running registered steps in order, all in one transaction, and `list_requests()` with the overdue flag (needs security review) (depends on T064, T021, T016)
- [ ] T066 [US6] In clinic-api, implement `clinic-api/app/identity/erasure_router.py` with `GET` and `POST /api/erasure-requests` and `POST /api/erasure-requests/{request_id}/execution`, manager only, and include it in `clinic-api/app/main.py` (depends on T065, T024)
- [ ] T067 [P] [US6] In clinic-web, build `clinic-web/src/pages/manager/ErasurePage.tsx` (find by phone, record request, list with due date and overdue flag, "Carry out erasure" with a confirmation step), route `/manager/erasure` in `clinic-web/src/App.tsx`, and test `clinic-web/src/tests/ErasurePage.test.tsx` (depends on T026)

**Checkpoint**: Erasure on request works end to end (QA-008).

---

## Phase 9: User Story 7 - Old identity data is cleaned up automatically (Priority: P3)

**Goal**: A daily idempotent job deletes sign-in codes and throttle rows after 24 hours, anonymises staff and dentists 24 months after deactivation and patient accounts unused for 24 months, and runs rules registered by later features. (source: NFR-007)

**Independent Test**: Insert back-dated rows, run the job twice, and see only the old data change.

- [ ] T068 [P] [US7] In clinic-api, write `clinic-api/tests/integration/test_retention_job.py`: code older than 24 hours deleted; throttle rows older than 24 hours deleted; staff and dentist deactivated 24 months ago anonymised and still inactive; patient account unused for 24 months anonymised like an erasure; records inside the period untouched; a second run changes nothing; a rule registered through `registry.py` is executed; two concurrent runs do not overlap
- [ ] T069 [US7] In clinic-api, implement `clinic-api/app/jobs/retention.py` with the rules of T068, a PostgreSQL advisory lock, one transaction per rule so a failure resumes cleanly, and the command-line entry `python -m app.jobs.retention` (depends on T064, T065, T018)
- [ ] T070 [US7] In clinic-api, start the daily retention trigger with the app in `clinic-api/app/main.py` (one run per day, off when `RETENTION_ENABLED=false`, the setting defined in `clinic-api/app/config.py`) (depends on T069, T011)

**Checkpoint**: Identity data follows the retention rules (ASM-012).

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Whole-feature checks and release readiness for Release 1 (go-live 1 March 2027, deadline DL-1 2027-02-22).

- [ ] T071 [P] In clinic-api, add `clinic-api/tests/integration/test_no_pii_in_logs.py` running the sign-in, staff, role, account, clinic, erasure and retention flows with log capture and failing on any name, phone number or birth year in a log line (Definition of Done) (depends on T034, T040, T055, T060, T066, T069)
- [ ] T072 [P] In clinic-api, add `clinic-api/tests/integration/test_access_query_count.py` asserting an authenticated request costs at most 3 indexed reads for the access check (depends on T024, T047)
- [ ] T073 [P] In clinic-api, write the security review notes `clinic-api/docs/security-review-identity.md` mapping threats thr-001, thr-002, thr-004, thr-005, thr-007, thr-009 and thr-015 to the code and tests of this feature, with HTTPS, cookie flags and password rules confirmed, for the required review of authentication changes (depends on T034, T040, T055)
- [ ] T074 [P] In clinic-api, add `clinic-api/.env.example` (variable names only, no values) and `clinic-api/docs/configuration.md` describing every setting of `clinic-api/app/config.py` and noting that hosting and domain are open (Q-008) (depends on T070)
- [ ] T075 In clinic-api, finish `clinic-api/contracts/clinic-api-v1.openapi.yaml` so it matches every implemented endpoint of this feature, and run the full contract suite in `clinic-api/tests/contract/` in CI (depends on T034, T040, T047, T055, T060, T066)
- [ ] T076 Run every scenario of `specs/001-platform-identity/quickstart.md` against a clean environment and record the results in `clinic-api/docs/quickstart-run-MOD-01.md` (depends on T071, T075, T035, T042, T056, T061, T067)
- [ ] T077 Write the Release 1 readiness checklist for this module in `clinic-api/docs/release-1-readiness-mod-01.md` (NFR-009): migrations 0001 to 0003 apply on an empty database, seeds run, health check, HTTPS and `Secure` cookie settings, first manager seeded, retention job on, test results of T076, open items, deadline DL-1 2027-02-22 against go-live 1 March 2027 (depends on T076)

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: no dependencies; T001 to T005 run in parallel.
- **Foundational (Phase 2)**: needs Setup; blocks all stories.
- **User stories (Phases 3 to 9)**: all need Foundational. US1 and US2 are independent of each other. US3 needs the access framework only (T024), and its tests build sessions from fixtures. US4 reuses `passwords.py` from US2 (T038). US5 builds on the scheduling read side of US3 (T046, T047). US6 needs the registry (T064) and is used by US7. US7 needs US6's erasure service.
- **Polish (Phase 10)**: after the stories it checks.

### User story order and independence

```text
Foundational ─┬─ US1 (patient sign-in)
              ├─ US2 (staff sign-in) ──┐
              ├─ US3 (roles, reads) ───┼─ US4 (staff accounts)  [needs T038 from US2]
              │                        └─ US5 (clinics, dentists writes) [needs T046-T047 from US3]
              └─ US6 (erasure) ─── US7 (retention)
```

### Within each story

Tests first (they fail), then models and services, then endpoints, then the web screen.

### Parallel example: User Story 1

```text
T027 unit tests (phone, throttle, otp)        T028 integration and contract tests
T029 phone.py        T030 sms_port.py         T035 SignInPage.tsx (clinic-web)
```

### Parallel example: after Foundational

```text
Developer A: US1 (T027-T035)      Developer B: US2 (T036-T043)      Developer C: US3 (T044-T051)
```

## Implementation Strategy

### MVP first

1. Phases 1 and 2 (foundation, health, sessions, access framework).
2. US1 and US2 (both sign-ins), then US3 (roles), then US4 and US5 (staff and clinics). That is the Release 1 core.
3. Validate with the quickstart scenarios 1 to 11 before US6 and US7.

### Incremental delivery

Foundation, then each story is testable and demonstrable alone; US6 and US7 follow and must be finished with Polish by the deadline DL-1 (2027-02-22), seven days before go-live on 1 March 2027 (NFR-009).

## Notes

- Q-007, Q-008 and Q-015 are assumed as recorded in `clarifications.md`; no task depends on their answers.
- The real SMS provider adapter, DLT template and delivery tracking are not in this feature; the code goes through the `SmsSender` port (T030).
- Family members (PRD FR-006) are a Release 2 feature; this feature only builds the account/person split (T016, T033).
- No clinical data is stored and no patient data is written to logs (T008, T009, T071).
