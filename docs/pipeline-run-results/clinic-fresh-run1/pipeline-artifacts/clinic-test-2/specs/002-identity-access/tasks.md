---

description: "Task list for Sign-in, roles and staff accounts"
---

# Tasks: Sign-in, roles and staff accounts

**Input**: Design documents from `/specs/002-identity-access/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/identity-api.yaml, quickstart.md

**Tests**: Requested. The constitution requires tests first for business logic, and QA-007 requires automated per-role tests for every operation. Write each test first and see it fail before the implementation task.

**Organization**: Tasks are grouped by user story. Paths start with `clinic-api/` (repo brightsmile/clinic-api) or `clinic-web/` (repo brightsmile/clinic-web).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story the task belongs to (US1 to US7)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Module skeleton and settings

- [ ] T001 Create the identity module skeleton in `clinic-api/app/identity/__init__.py` and the test package in `clinic-api/tests/identity/__init__.py`
- [ ] T002 [P] Create `clinic-api/app/identity/settings.py` with the limits as settings (code length 6, code validity 10 minutes, 5 tries, 15-minute lock, 10 requests per network address per hour, 5 per phone per hour, 1,000 codes per day, staff 5 failures and 15-minute lock, password minimum 10, patient session 7 days, staff 8 hours and 30 minutes idle) and the names of the secrets read from environment variables (token signing key, code-hash key, IP-hash key, allowed origin)
- [ ] T003 [P] Create the web module entry `clinic-web/src/identity/index.ts` exporting the identity screens and session helpers

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Tables, tokens, request security, ports and the access context that every story needs

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 [P] Write token tests in `clinic-api/tests/identity/test_tokens.py`: cookie flags `HttpOnly`, `Secure`, `SameSite=Strict`; claims hold user id and role only plus time claims; tampered or expired token rejected; patient valid 7 days from last use; staff invalid after 8 hours or 30 minutes idle
- [ ] T005 [P] Write request-security tests in `clinic-api/tests/identity/test_security_origin_csrf.py`: write requests without the CSRF header or with a wrong or missing `Origin` are refused; reads are allowed; plain HTTP is refused
- [ ] T006 [P] Write password tests in `clinic-api/tests/identity/test_passwords.py`: fewer than 10 characters rejected, argon2id hash verifies, wrong password fails, unknown-user path costs the same verify
- [ ] T007 [P] Write access-context tests in `clinic-api/tests/identity/test_access_context.py`: role, clinic and active flag are re-read from the database on every request; a deactivated user is refused at the next request; role claim in a tampered token is ignored
- [ ] T008 [P] Create test fixtures in `clinic-api/tests/identity/conftest.py`: test database session, a fake `MessageSender` that records codes, a controllable clock, factories for staff, patient accounts and persons, and a client that adds the CSRF header and Origin
- [ ] T009 Create the four models in `clinic-api/app/identity/models.py` exactly per data-model.md: `StaffAccount` (username unique case-insensitive; role enum receptionist|dentist|manager; clinic_id required for receptionist and null otherwise; dentist_id required for dentist; password_hash argon2id; failed_attempts int; locked_until nullable; active bool; deactivated_at nullable), `PatientAccount` (phone unique, E.164; preferred_channel enum sms|whatsapp default sms; reminders_opt_out bool default false; active bool; erasure_requested_at and erased_at nullable; last_seen_at), `Patient` (account_id FK; name; birth_year smallint nullable; is_account_holder bool, exactly one per account; active bool), `OtpChallenge` (phone; code_hash; ip_hash; created_at; expires_at = created_at + 10 minutes; attempts int max 5; locked_until nullable; verified_at nullable; consumed_at nullable)
- [ ] T010 Create the forward-only Alembic migration `clinic-api/migrations/versions/002_identity_tables.py` for the four tables with their unique constraints, the check constraints for role-specific columns and an index on `otp_challenge(phone, created_at)` and `otp_challenge(ip_hash, created_at)` (depends on T009)
- [ ] T011 [P] Implement argon2id hashing, verification and the 10-character policy in `clinic-api/app/identity/passwords.py`
- [ ] T012 [P] Implement signed-JWT cookie issue and read, sliding last-activity, patient 7-day and staff 8-hour/30-minute rules in `clinic-api/app/identity/tokens.py`
- [ ] T013 [P] Implement the CSRF header check (double submit with a companion cookie), the `Origin` check on writes and the HTTPS-only and HSTS headers in `clinic-api/app/identity/security.py`
- [ ] T014 [P] Define the ports `MessageSender`, `AppointmentAnonymiser`, `FutureAppointments` and `MessageEraser` with no-op default adapters in `clinic-api/app/identity/ports.py`
- [ ] T015 [P] Create request and response schemas from `contracts/identity-api.yaml` in `clinic-api/app/identity/schemas.py`, with input validation (phone normalised to E.164, name non-empty, password minimum length)
- [ ] T016 [P] Implement a log filter that removes names, phone numbers, birth years and codes from log records, and structured logging with a correlation id, in `clinic-api/app/identity/log_scrub.py`
- [ ] T017 Implement `AccessContext` and the FastAPI dependency in `clinic-api/app/identity/access.py`: read the token owner, re-read role, clinic, dentist link, patient account, person ids and active flag from the database on each request, refuse unauthenticated and inactive users (depends on T009 and T012)
- [ ] T018 Create the router stubs `clinic-api/app/identity/api/__init__.py`, `clinic-api/app/identity/api/auth_routes.py`, `clinic-api/app/identity/api/staff_routes.py` and `clinic-api/app/identity/api/patient_admin_routes.py`, with the CSRF/Origin dependency on every router, and register the router and log filter in `clinic-api/app/main.py` (depends on T013, T015, T016 and T017)
- [ ] T019 [P] Create the API client with the CSRF header and the session state with role guard in `clinic-web/src/identity/api.ts` and `clinic-web/src/identity/session.tsx`

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Patient signs in with a phone code (Priority: P1) 🎯 MVP

**Goal**: A returning patient signs in with phone and SMS code, with correct handling of wrong, expired and locked codes and a 7-day session. (source: FR-002, NFR-006)

**Independent Test**: With the fake message sender, request a code, verify it and reach a signed-in session; then wrong, expired, 5-wrong lock, per-address throttle and daily cap cases.

### Tests for User Story 1 ⚠️

- [ ] T020 [P] [US1] Write tests for `clinic-api/app/identity/otp_service.py` in `clinic-api/tests/identity/test_otp_service.py`: code is 6 digits and stored only as a hash; valid 10 minutes; only the newest code is valid; 5 wrong tries lock the phone for 15 minutes even for a correct or new code; per-address (10 per hour), per-phone (5 per hour) and daily (1,000) limits refuse without sending; a send failure does not count as a wrong try; phone numbers with +91 or spaces map to the same account
- [ ] T021 [P] [US1] Write API tests for `/api/auth/patient/code`, `/api/auth/patient/verify`, `/api/auth/me` and `/api/auth/logout` in `clinic-api/tests/identity/test_patient_signin_api.py`, including status codes and error codes `code_wrong`, `code_expired`, `locked`, `throttled`, `send_failed`, and the 7-day session
- [ ] T022 [P] [US1] Write component tests in `clinic-web/tests/identity/PatientSignIn.test.tsx`: phone then code steps, "wrong code" and "expired" messages with a send-new-code button, wait message after 5 wrong tries, no sideways scroll at 360 px, tap targets at least 44 px

### Implementation for User Story 1

- [ ] T023 [US1] Implement code issue, verify, tries, locks, per-address and per-phone throttles and the daily cap in `clinic-api/app/identity/otp_service.py` (depends on T009, T014 and T002)
- [ ] T024 [US1] Implement existing-patient sign-in and session start (update last_seen_at, issue cookie) in `clinic-api/app/identity/patient_auth_service.py` (depends on T023 and T012)
- [ ] T025 [US1] Implement `POST /api/auth/patient/code`, `POST /api/auth/patient/verify`, `GET /api/auth/me` and `POST /api/auth/logout` in `clinic-api/app/identity/api/auth_routes.py` (depends on T024 and T018)
- [ ] T026 [US1] Build the phone and code steps with error and wait messages in `clinic-web/src/identity/PatientSignIn.tsx` (depends on T019)

**Checkpoint**: A returning patient can sign in and out

---

## Phase 4: User Story 2 - New patient creates an account (Priority: P1)

**Goal**: A new phone number gets an account only after the code is verified and a name is given. (source: FR-002, NFR-007)

**Independent Test**: Verify a code for an unknown phone, check no account exists, give a name, check one account and one person row.

### Tests for User Story 2 ⚠️

- [ ] T027 [P] [US2] Write tests in `clinic-api/tests/identity/test_patient_registration.py`: verify gives `needs_name`, nothing is created before the name, empty name refused, wrong or expired code creates nothing, an existing phone never gets a second account, registration cookie expires after 10 minutes and works once
- [ ] T028 [P] [US2] Write component tests in `clinic-web/tests/identity/PatientRegistration.test.tsx` for the name step and the empty-name message

### Implementation for User Story 2

- [ ] T029 [US2] Add registration (create account and account-holder person in one transaction, consume the challenge) to `clinic-api/app/identity/patient_auth_service.py` (depends on T024)
- [ ] T030 [US2] Add `POST /api/auth/patient/register` and the registration cookie to `clinic-api/app/identity/api/auth_routes.py` (depends on T025 and T029)
- [ ] T031 [US2] Add the name step to `clinic-web/src/identity/PatientSignIn.tsx` (depends on T026)

**Checkpoint**: New and returning patients can sign in

---

## Phase 5: User Story 3 - Staff sign in with username and password (Priority: P1)

**Goal**: Receptionists, dentists and the manager sign in; lockout after 5 failures for 15 minutes; 8-hour and 30-minute idle session limits; password change. (source: FR-003, NFR-006)

**Independent Test**: Sign in as a staff account in test data with right and wrong passwords; check lockout, idle and maximum session ends and password change.

### Tests for User Story 3 ⚠️

- [ ] T032 [P] [US3] Write tests in `clinic-api/tests/identity/test_staff_signin.py`: success lands on role, same error for unknown user, wrong password and deactivated account, 5 failures lock for 15 minutes, counter resets on success, own password change needs the current password and the 10-character minimum
- [ ] T033 [P] [US3] Write tests in `clinic-api/tests/identity/test_staff_session_expiry.py`: refused after 30 minutes idle and after 8 hours from sign-in, using the controllable clock
- [ ] T034 [P] [US3] Write component tests in `clinic-web/tests/identity/StaffSignIn.test.tsx` for the sign-in form, error and lock messages, role redirect, and the password change form

### Implementation for User Story 3

- [ ] T035 [US3] Implement staff sign-in, failure counting, lockout, uniform error and own password change in `clinic-api/app/identity/staff_auth_service.py` (depends on T009, T011 and T012)
- [ ] T036 [US3] Add `POST /api/auth/staff/login` and `POST /api/auth/staff/password` to `clinic-api/app/identity/api/auth_routes.py` (depends on T025 and T035)
- [ ] T037 [P] [US3] Build the staff sign-in screen in `clinic-web/src/identity/StaffSignIn.tsx`
- [ ] T038 [P] [US3] Build the change-password screen in `clinic-web/src/identity/ChangePassword.tsx`

**Checkpoint**: Staff can sign in

---

## Phase 6: User Story 4 - Each role sees only what it needs (Priority: P1)

**Goal**: One server-side access context decides what each role may see, with clinic scoping and patient/family scoping; receptionists can search all patients. (source: FR-004, NFR-006)

**Independent Test**: The per-role operation matrix and the cross-clinic and cross-patient tests all pass with 0 cross reads.

### Tests for User Story 4 ⚠️

- [ ] T039 [P] [US4] Write the per-role matrix in `clinic-api/tests/identity/test_role_matrix.py`: a registry of every protected operation of this feature with the allowed roles, run for patient, receptionist, dentist, manager and anonymous; new operations from other features add rows
- [ ] T040 [P] [US4] Write scoping tests in `clinic-api/tests/identity/test_scoping.py`: a patient cannot read another person's data, a patient sees own and family persons, a receptionist of clinic A is refused clinic B, a dentist is limited to own day and read only, the manager reaches both clinics, request ids never widen access, 0 cross-clinic and 0 cross-patient reads
- [ ] T041 [P] [US4] Write tests in `clinic-api/tests/identity/test_unauthenticated_and_csrf.py`: every identity route except sign-in refuses missing, expired or tampered cookies and writes without CSRF header or Origin
- [ ] T042 [P] [US4] Write component tests in `clinic-web/tests/identity/RoleGuard.test.tsx` for role-based routes and redirect to the right sign-in

### Implementation for User Story 4

- [ ] T043 [US4] Add scoping methods to `clinic-api/app/identity/access.py`: `require_role`, `scope_clinic`, `can_access_clinic`, `can_access_patient`, `person_ids`, so other modules never decide from request ids alone (depends on T017)
- [ ] T044 [US4] Implement patient-account search by phone number or name for receptionist and manager in `clinic-api/app/identity/patient_admin_service.py` (depends on T043)
- [ ] T045 [US4] Add `GET /api/patients/search` to `clinic-api/app/identity/api/patient_admin_routes.py` (depends on T044 and T018)
- [ ] T046 [P] [US4] Add role-guarded routes and the post-sign-in redirect per role in `clinic-web/src/routes/identity.tsx` (depends on T019)
- [ ] T047 [P] [US4] Build the patient search screen in `clinic-web/src/identity/PatientSearch.tsx` (depends on T019)

**Checkpoint**: Role separation proven by tests

---

## Phase 7: User Story 5 - Practice manager manages staff accounts (Priority: P1)

**Goal**: The manager creates receptionist and dentist accounts, assigns receptionists to a clinic, resets passwords and deactivates accounts with immediate effect. (source: FR-005, NFR-006)

**Independent Test**: As the manager create a receptionist, sign in as them, deactivate, and see the open session refused.

### Tests for User Story 5 ⚠️

- [ ] T048 [P] [US5] Write tests in `clinic-api/tests/identity/test_staff_admin_api.py`: create receptionist with clinic and dentist with dentist link, duplicate username refused, password under 10 characters refused, change clinic effective at once, deactivate refuses sign-in and open sessions at once, reactivate, manager password reset, only the manager may do these, the last active manager cannot be deactivated, bootstrap creates the first manager
- [ ] T049 [P] [US5] Write component tests in `clinic-web/tests/identity/StaffAdmin.test.tsx` for create, assign clinic, deactivate and reset password

### Implementation for User Story 5

- [ ] T050 [US5] Implement create, update, assign clinic, deactivate, activate and password reset in `clinic-api/app/identity/staff_service.py` (depends on T009, T011 and T043)
- [ ] T051 [US5] Implement `GET/POST /api/staff`, `PATCH /api/staff/{id}`, `POST /api/staff/{id}/deactivate`, `/activate` and `/password` in `clinic-api/app/identity/api/staff_routes.py` (depends on T050 and T018)
- [ ] T052 [P] [US5] Build the staff screen in `clinic-web/src/identity/StaffAdmin.tsx` (depends on T019)
- [ ] T053 [US5] Create the set-up command that creates the first manager account from a secret supplied by the environment in `clinic-api/app/identity/bootstrap.py` (depends on T050)

**Checkpoint**: The manager can run staff accounts

---

## Phase 8: User Story 6 - Practice manager erases a patient's data on request (Priority: P2)

**Goal**: Erasure on request anonymises person, account and messages within 30 days, keeps anonymised appointment rows, and retention jobs delete old sign-in codes. (source: NFR-007)

**Independent Test**: Erase a patient with a family member and appointments; no name, phone or birth year remains; appointment counts unchanged; no PII in logs.

### Tests for User Story 6 ⚠️

- [ ] T054 [P] [US6] Write tests in `clinic-api/tests/identity/test_erasure.py`: request recorded with date, sign-in blocked, person rows and account anonymised together, ports called for appointments and messages, a failing port leaves the request pending and the daily retry completes it, non-manager refused, future-appointment count shown in the preview, and the stored columns of the four tables are exactly those in data-model.md (no clinical data, FR-021)
- [ ] T055 [P] [US6] Write tests in `clinic-api/tests/identity/test_retention_jobs.py`: sign-in codes older than 24 hours deleted, patient accounts idle 24 months anonymised, staff accounts anonymised 24 months after deactivation, pending erasures older than 20 days raise an alert
- [ ] T056 [P] [US6] Write tests in `clinic-api/tests/identity/test_no_pii_in_logs.py` that run sign-in, registration, staff admin and erasure and assert no name, phone, birth year or code appears in captured logs
- [ ] T057 [P] [US6] Write component tests in `clinic-web/tests/identity/ErasureAdmin.test.tsx` for finding a patient, the preview with future appointments and the confirmation

### Implementation for User Story 6

- [ ] T058 [US6] Implement erasure (record request, deactivate, anonymise persons and account in one transaction, call the ports, set erased_at, retry pending) in `clinic-api/app/identity/erasure_service.py` (depends on T009, T014 and T044)
- [ ] T059 [US6] Implement the retention jobs and register them and the erasure retry at application start in `clinic-api/app/identity/retention_jobs.py` and `clinic-api/app/main.py` (depends on T058)
- [ ] T060 [US6] Add `GET` and `POST /api/patient-accounts/{id}/erasure` to `clinic-api/app/identity/api/patient_admin_routes.py` (depends on T045 and T058)
- [ ] T061 [US6] Build the erasure admin screen in `clinic-web/src/identity/ErasureAdmin.tsx` (depends on T047)

**Checkpoint**: Erasure on request works and personal data is purged on schedule

---

## Phase 9: User Story 7 - Reception deactivates a patient account (Priority: P3)

**Goal**: Reception can deactivate a patient account and the manager can reactivate it. (source: NFR-006)

**Independent Test**: Deactivate a test patient account as a receptionist; the patient's session is refused at once.

### Tests for User Story 7 ⚠️

- [ ] T062 [P] [US7] Write tests in `clinic-api/tests/identity/test_patient_deactivation.py`: receptionist and manager may deactivate, dentist and patient refused, deactivated patient cannot sign in and open sessions are refused at once, only the manager reactivates
- [ ] T063 [P] [US7] Write component tests in `clinic-web/tests/identity/PatientSearch.test.tsx` for the deactivate and reactivate buttons by role

### Implementation for User Story 7

- [ ] T064 [US7] Add deactivate and reactivate (who and when recorded) to `clinic-api/app/identity/patient_admin_service.py` (depends on T044)
- [ ] T065 [US7] Add `POST /api/patient-accounts/{id}/deactivate` and `/reactivate` to `clinic-api/app/identity/api/patient_admin_routes.py` (depends on T060 and T064)
- [ ] T066 [US7] Add the deactivate and reactivate buttons to `clinic-web/src/identity/PatientSearch.tsx` (depends on T047)

**Checkpoint**: All user stories are complete

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Contract, observability, security review and final validation

- [ ] T067 [P] Merge the identity operations of `specs/002-identity-access/contracts/identity-api.yaml` into `clinic-api/contracts/clinic-api-v1.openapi.yaml`
- [ ] T068 [P] Add a contract test that runs every identity operation against the merged contract in `clinic-api/tests/identity/test_contract.py` (depends on T067)
- [ ] T069 [P] Add structured events, metrics (sign-in success, failure, lockout, throttled, code sent) and traces without PII in `clinic-api/app/identity/observability.py`, and a readiness check of the identity tables
- [ ] T070 [P] Write the security review checklist for authentication and authorisation changes (constitution III; ASVS L1 items covered, thr-001 to thr-009) in `clinic-api/docs/identity-security-review.md`
- [ ] T071 Run the scenarios of `specs/002-identity-access/quickstart.md` against staging and record results in that file (depends on T068)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies
- **Foundational (Phase 2)**: depends on Setup; blocks all stories
- **US1 to US3 (P1)**: depend on Foundational. US2 builds on US1 files; US3 is independent of US1/US2 except the shared `auth_routes.py` (T036 depends on T025)
- **US4 (P1)**: depends on Foundational; its search and scoping are used by US5, US6 and US7
- **US5 (P1)**: depends on US4 (T043)
- **US6 (P2)** and **US7 (P3)**: depend on US4 (T044, T045); US7 routes depend on US6 routes (same file)
- **Polish**: depends on all stories

### Parallel Opportunities

- Tests of a story (marked [P]) run in parallel; backend and web tasks of a story run in parallel
- T011 to T016 in Foundational run in parallel
- After Foundational, US1, US3 and US4 can be built by different developers

### Parallel Example: User Story 1

```bash
Task: "Write tests for otp_service in clinic-api/tests/identity/test_otp_service.py"
Task: "Write API tests in clinic-api/tests/identity/test_patient_signin_api.py"
Task: "Write component tests in clinic-web/tests/identity/PatientSignIn.test.tsx"
```

---

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational
2. Complete US1 and US2 (patient sign-in and registration), validate with the quickstart
3. Add US3 (staff sign-in) and US4 (role separation), then US5 (staff accounts): the P1 set needed for go-live on 1 March 2027
4. Add US6 (erasure) before go-live, then US7

### Incremental Delivery

Each story is demonstrable on its own: patient sign-in, registration, staff sign-in, role matrix, staff admin, erasure, patient deactivation.

---

## Notes

- The P marker: tasks touch different files and have no unfinished dependencies
- Each test task must fail before the implementation task starts
- Authentication and authorisation changes need explicit review (constitution III); T070 is the checklist for it
- No name, phone number, birth year or code may be written to logs
