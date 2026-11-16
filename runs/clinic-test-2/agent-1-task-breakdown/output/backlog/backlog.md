# Backlog v1 — clinic-test-2

10 epics · 79 stories · 484 tasks · 271 story points · 0 blocking issues

## Issues

- **warning** `open_questions`: 46 items have open questions for the reviewer

## Coverage of prd.md

- NFR-005: S-006-US3, S-006-US4, S-006-US7, S-SETUP-006, S-FOUND-006, S-POLISH-006
- FR-001: S-001-US5
- FR-002: S-001-US1, S-006-US6
- FR-003: S-001-US2
- FR-004: S-001-US3, S-007-US2, S-007-US3, S-009-US4
- FR-005: S-001-US4
- FR-006: S-007-US1, S-007-US2, S-007-US3, S-007-US4, S-SETUP-007, S-FOUND-007, S-POLISH-007
- FR-007: S-002-US2
- FR-008: S-002-US4
- FR-009: S-002-US1
- FR-010: S-002-US3
- FR-011: S-003-US1, S-003-US2, S-SETUP-003, S-FOUND-003, S-POLISH-003
- FR-012: S-003-US3, S-003-US4, S-SETUP-003, S-FOUND-003, S-POLISH-003
- FR-013: S-006-US1, S-FOUND-006
- FR-014: S-006-US2
- FR-015: S-004-US1, S-004-US4, S-SETUP-004, S-FOUND-004, S-POLISH-004, S-007-US3
- FR-016: S-004-US3, S-004-US4, S-SETUP-004, S-FOUND-004, S-POLISH-004, S-007-US3
- FR-017: S-004-US1, S-004-US2, S-004-US3, S-004-US4, S-SETUP-004, S-FOUND-004, S-POLISH-004, S-007-US3
- FR-018: S-004-US2, S-004-US3, S-SETUP-004, S-FOUND-004, S-POLISH-004, S-006-US4
- FR-019: S-005-US1, S-SETUP-005, S-POLISH-005
- FR-020: S-005-US3, S-005-US4, S-SETUP-005, S-POLISH-005
- FR-021: S-005-US2, S-005-US4, S-SETUP-005, S-FOUND-005
- FR-022: S-005-US2, S-SETUP-005, S-FOUND-005
- FR-023: S-005-US5, S-SETUP-005, S-POLISH-005
- FR-024: S-005-US1, S-005-US2, S-005-US4, S-SETUP-005, S-FOUND-005, S-POLISH-005
- FR-025: S-008-US1, S-008-US4
- FR-026: S-008-US2, S-008-US3, S-008-US4
- FR-027: S-006-US3, S-006-US7
- FR-028: S-006-US4
- FR-029: S-009-US1, S-009-US2, S-009-US3, S-SETUP-009, S-FOUND-009, S-POLISH-009
- FR-030: S-006-US3
- FR-031: S-006-US5
- FR-032: S-010-US1, S-010-US2, S-010-US3, S-SETUP-010, S-FOUND-010, S-POLISH-010
- FR-033: S-009-US4, S-009-US5, S-SETUP-009, S-POLISH-009
- NFR-001: S-003-US6, S-SETUP-003, S-FOUND-003, S-POLISH-003
- NFR-002: S-002-US3, S-003-US1, S-003-US2, S-003-US4, S-003-US5, S-SETUP-003, S-FOUND-003, S-POLISH-003
- NFR-003: S-002-US2, S-002-US3
- NFR-004: S-POLISH-001, S-POLISH-003
- NFR-006: S-001-US1, S-001-US2, S-001-US3, S-001-US4, S-SETUP-001, S-FOUND-001, S-POLISH-001, S-009-US4
- NFR-007: S-001-US6, S-001-US7, S-POLISH-001, S-007-US4, S-POLISH-007
- NFR-008: S-006-US2, S-006-US3, S-006-US6, S-006-US7, S-FOUND-006, S-POLISH-006
- NFR-009: S-SETUP-001, S-FOUND-001, S-POLISH-001
- NFR-010: S-003-US2, S-003-US6, S-SETUP-003, S-FOUND-003, S-POLISH-003
- NFR-011: S-006-US2, S-006-US5, S-006-US6, S-006-US7, S-SETUP-006, S-FOUND-006, S-POLISH-006

Critical path: S-SETUP-001 → S-FOUND-001 → S-FOUND-003 → S-003-US2 → S-006-US1 → S-006-US2 → S-006-US3 → S-006-US4 → S-006-US5 → S-006-US7 → S-POLISH-006

## E-001 Platform, sign-in, roles and clinics (MOD-01)

Clinics and dentists data, patient phone-code sign-in, staff password sign-in, role-based visibility, staff account management, erasure on request. RELEASE 1 (DL-1, due 2027-02-22, hard). PRD ids: FR-001, FR-002, FR-003, FR-004, FR-005.

### S-001-US1 A patient signs in with a phone number and a code — P1/must · 5 SP (low, llm)

As a Patient (P-01) booking from my phone, I want to sign in with my mobile number and a 6-digit code sent by SMS, and be registered on first use with my name so that I can book and manage visits without a password or a phone call, and stay signed in for 7 days.
Depends on: S-FOUND-001 · Sources: FR-002, NFR-006

- [AC-S-001-US1-1] Given a phone number that already has an account, When the patient asks for a code and enters the correct code within 10 minutes, Then the patient is signed in and sees their name
- [AC-S-001-US1-2] Given a phone number with no account, When the patient enters the correct code, Then the system asks for their name, and after the name is given an account is created and the patient is signed in
- [AC-S-001-US1-3] Given a code was sent, When the patient enters a wrong code, Then the system says the code is wrong, says how many tries are left, and offers to send a new code
- [AC-S-001-US1-4] Given a code was sent more than 10 minutes ago, When the patient enters it, Then the system says the code has expired and offers a new code
- [AC-S-001-US1-5] Given a patient has entered 5 wrong codes for a phone number, When they try again or ask for a new code within 15 minutes, Then the system refuses and says when they can try again; after 15 minutes they can ask for a new code
- [AC-S-001-US1-6] Given a signed-in patient who last used the site 6 days ago, When they open the site, Then they are still signed in
- [AC-S-001-US1-7] Given a signed-in patient who last used the site more than 7 days ago, When they open the site, Then they must sign in again
- [AC-S-001-US1-8] Given too many codes were requested from one network address in a short time, or the daily limit of codes for one phone number is used up, When another code is requested, Then the system refuses without sending an SMS and says to try later or phone the clinic

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T027 | In clinic-api, write unit tests `clinic-api/tests/unit/test_phone.py` (accepts ` | 3.5 | qa-automation, auth-security | no | - |
| 001-T028 | In clinic-api, write `clinic-api/tests/integration/test_patient_sign_in.py` (exi | 4.5 | qa-automation, auth-security | no | - |
| 001-T029 | In clinic-api, implement phone normalisation in `clinic-api/app/identity/phone.p | 1.5 | backend-python | yes | - |
| 001-T030 | In clinic-api, implement the SMS sender port in `clinic-api/app/identity/sms_por | 1.5 | backend-python, messaging | yes | - |
| 001-T031 | In clinic-api, implement the throttle in `clinic-api/app/identity/throttle.py`:  | 3.0 | backend-python, auth-security | no | 001-T018 |
| 001-T032 | In clinic-api, implement `clinic-api/app/identity/otp_service.py`: issue (normal | 5.0 | backend-python, auth-security | no | 001-T029, 001-T030, 001-T031 |
| 001-T033 | In clinic-api, implement `clinic-api/app/identity/patient_accounts_service.py`:  | 3.0 | backend-python, postgres | no | 001-T016 |
| 001-T034 | In clinic-api, implement `clinic-api/app/identity/patient_auth_router.py` with ` | 4.0 | api-design, auth-security | no | 001-T021, 001-T032, 001-T033 |
| 001-T035 | In clinic-web, build `clinic-web/src/pages/patient/SignInPage.tsx` (phone step,  | 4.0 | frontend-react, frontend-css | no | 001-T026 |

### S-001-US2 Staff sign in with a username and password — P1/must · 3 SP (low, llm)

As a Receptionist, dentist or practice manager (P-02, P-03, P-04), I want to sign in with a username and a password of at least 10 characters and be locked out after repeated failures so that I can reach the screens for my role while the clinic's accounts stay protected.
Depends on: S-FOUND-001 · Sources: FR-003, NFR-006

- [AC-S-001-US2-1] Given an active staff account, When the person enters the correct username and password, Then they are signed in and the system tells the web app their role and (for receptionists) their clinic
- [AC-S-001-US2-2] Given an active staff account, When the person enters a wrong password, Then the system says the username or password is wrong, without saying which one
- [AC-S-001-US2-3] Given 5 wrong passwords in a row for one username, When the person tries again within 15 minutes (even with the right password), Then the sign-in is refused with a message that the account is locked and for how long
- [AC-S-001-US2-4] Given a password shorter than 10 characters, When it is set for a staff account, Then the system rejects it and says the minimum length
- [AC-S-001-US2-5] Given a signed-in staff member idle for 30 minutes, or signed in for 8 hours, When they make a request, Then the session is refused and they must sign in again
- [AC-S-001-US2-6] Given a signed-in user, When they sign out, Then the session ends at once and cannot be reused

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T036 | In clinic-api, write unit tests `clinic-api/tests/unit/test_passwords.py` (argon | 2.5 | qa-automation, auth-security | no | - |
| 001-T037 | In clinic-api, write `clinic-api/tests/integration/test_staff_sign_in.py` (sign- | 3.0 | qa-automation, auth-security | no | - |
| 001-T038 | In clinic-api, implement `clinic-api/app/identity/passwords.py`: argon2id hash a | 1.0 | backend-python, auth-security | no | - |
| 001-T039 | In clinic-api, implement `clinic-api/app/identity/staff_auth_service.py`: authen | 3.0 | backend-python, auth-security | no | 001-T038, 001-T021 |
| 001-T040 | In clinic-api, implement `clinic-api/app/identity/staff_auth_router.py` with `PO | 2.5 | api-design, auth-security | no | 001-T039 |
| 001-T041 | In clinic-api, implement the idempotent first-manager seed `clinic-api/app/ident | 1.0 | backend-python, auth-security | no | 001-T038, 001-T017 |
| 001-T042 | In clinic-web, build `clinic-web/src/pages/staff/StaffSignInPage.tsx` (username, | 3.0 | frontend-react | no | 001-T026 |
| 001-T043 | In clinic-web, build `clinic-web/src/pages/staff/ChangePasswordPage.tsx` (curren | 2.0 | frontend-react | no | 001-T026 |

### S-001-US3 Each role sees only what it needs — P1/must · 3 SP (low, llm)

As a Practice manager (P-04) responsible for patient privacy across both clinics, I want every request to be authorised on the server from the signed-in person's role, clinic and active flag so that receptionists see only their own clinic, dentists read only, patients reach only their own data, and a deactivated person is locked out at once.
Depends on: S-FOUND-001 · Sources: FR-004, NFR-006

- [AC-S-001-US3-1] Given a receptionist of Indiranagar, When they ask for the clinic list or for data of Whitefield, Then they see Indiranagar only and Whitefield is refused
- [AC-S-001-US3-2] Given a practice manager, When they ask for the clinic list, Then they see both clinics and the settings screens
- [AC-S-001-US3-3] Given a dentist, When they ask for their own day or clinics, Then it is allowed read only, and any change request is refused
- [AC-S-001-US3-4] Given a patient, When they ask for another patient's data, or send a patient id that is not theirs, Then the request is refused; only data owned by the signed-in person is returned
- [AC-S-001-US3-5] Given a signed-in person whose account was just deactivated or whose role changed, When they make their next request, Then it is refused or handled with the new role at once, without waiting for the session to expire
- [AC-S-001-US3-6] Given any write request from a browser, When it lacks the anti-forgery header or comes from another origin, Then it is refused
- [AC-S-001-US3-7] Given an unsigned visitor, When they call any protected operation, Then they get a "sign in" answer and no data
- [AC-S-001-US3-8] Given a receptionist, When they search for a patient by phone number or name, Then patients of any clinic can be found, but appointments shown with the patient are limited to their own clinic

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T044 | In clinic-api, write `clinic-api/tests/integration/test_role_scope_matrix.py` (t | 3.5 | qa-automation, auth-security | no | - |
| 001-T045 | In clinic-api, write `clinic-api/tests/integration/test_deactivation_immediacy.p | 1.5 | qa-automation, auth-security | no | - |
| 001-T046 | In clinic-api, implement the read side of scheduling in `clinic-api/app/scheduli | 3.0 | backend-python, auth-security | no | 001-T014, 001-T024 |
| 001-T047 | In clinic-api, implement `GET /api/clinics` and `GET /api/dentists` in `clinic-a | 1.5 | api-design, backend-python | no | 001-T046 |
| 001-T048 | In clinic-api, implement `GET /api/me` in `clinic-api/app/identity/me_router.py` | 1.0 | api-design, auth-security | no | 001-T024 |
| 001-T049 | In clinic-api, implement `GET /api/patients?q=` in `clinic-api/app/identity/pati | 2.5 | backend-python, postgres | no | 001-T024 |
| 001-T050 | In clinic-api, document how every module must authorise in `clinic-api/docs/acce | 1.5 | docs, auth-security | yes | 001-T024 |
| 001-T051 | In clinic-web, build `clinic-web/src/pages/RoleHome.tsx` showing the links each  | 3.5 | frontend-react, frontend-css | no | 001-T026, 001-T048 |

### S-001-US4 The practice manager manages staff accounts — P1/must · 3 SP (low, llm)

As a Practice manager (P-04), I want to create, edit, deactivate and reactivate receptionist and dentist accounts, assign receptionists to a clinic and reset passwords so that staff can get in and leavers are locked out at once without any developer help.
Depends on: S-001-US2 · Sources: FR-005, NFR-006

- [AC-S-001-US4-1] Given a signed-in manager, When they create a receptionist with a username, name, a password of at least 10 characters and a clinic, Then the account exists, is active and can sign in
- [AC-S-001-US4-2] Given a signed-in manager, When they create a receptionist without a clinic, Then the system refuses and says a clinic is required
- [AC-S-001-US4-3] Given a username already in use, When the manager creates another account with it, Then the system refuses and says the username is taken
- [AC-S-001-US4-4] Given an active staff account that is signed in, When the manager deactivates it, Then the next request from that person is refused and they cannot sign in again until reactivated
- [AC-S-001-US4-5] Given a receptionist or dentist, When they try to create, change or deactivate an account, Then the request is refused
- [AC-S-001-US4-6] Given the manager is the only active manager, When they try to deactivate themselves, Then the system refuses so the practice cannot lock itself out
- [AC-S-001-US4-7] Given a staff member forgot their password, When the manager resets it to a new temporary password of at least 10 characters, Then the old password stops working and the person's failed-attempt lock is cleared

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T052 | In clinic-api, write unit tests `clinic-api/tests/unit/test_staff_accounts_servi | 3.0 | qa-automation, auth-security | no | - |
| 001-T053 | In clinic-api, write `clinic-api/tests/integration/test_staff_accounts_api.py` ( | 4.0 | qa-automation, api-design | no | - |
| 001-T054 | In clinic-api, implement `clinic-api/app/identity/staff_accounts_service.py`: cr | 3.5 | backend-python, auth-security | no | 001-T038, 001-T021, 001-T016 |
| 001-T055 | In clinic-api, implement `clinic-api/app/identity/staff_accounts_router.py` with | 3.0 | api-design, auth-security | no | 001-T054, 001-T024 |
| 001-T056 | In clinic-web, build `clinic-web/src/pages/manager/StaffAccountsPage.tsx` (list, | 4.5 | frontend-react, frontend-css | no | 001-T026, 001-T047 |

### S-001-US5 The system holds the clinics and the dentists — P1/must · 3 SP (low, llm)

As a Practice manager (P-04), I want to keep clinics and dentists as data, including which weekdays each dentist works at which clinic so that a third clinic or a new dentist can be added in the staff screens without a software change.
Depends on: S-001-US3 · Sources: FR-001

- [AC-S-001-US5-1] Given a new installation, When the clinic list is read, Then Indiranagar and Whitefield are present and active
- [AC-S-001-US5-2] Given a signed-in manager, When they add a clinic with a name, address and phone number, Then it appears in the clinic list at once for all roles that may see it, without a deployment
- [AC-S-001-US5-3] Given a signed-in manager, When they add a dentist and set Monday at Indiranagar and Thursday at Whitefield, Then the dentist is listed at both clinics, only on those days
- [AC-S-001-US5-4] Given a dentist already has a day at one clinic, When the manager assigns the same weekday at a second clinic, Then the system refuses, because a dentist is in one place on one day
- [AC-S-001-US5-5] Given a manager deactivates a clinic or a dentist, When the lists are read for booking, Then the inactive one is not offered, while existing records that point to it stay readable
- [AC-S-001-US5-6] Given a receptionist, When they ask to add a clinic or a dentist, Then the request is refused

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T057 | In clinic-api, write unit tests `clinic-api/tests/unit/test_scheduling_service.p | 2.5 | qa-automation, backend-python | yes | - |
| 001-T058 | In clinic-api, write `clinic-api/tests/integration/test_clinics_dentists_admin.p | 3.5 | qa-automation, api-design | yes | - |
| 001-T059 | In clinic-api, extend `clinic-api/app/scheduling/service.py` with `create_clinic | 3.5 | backend-python, postgres | yes | 001-T046 |
| 001-T060 | In clinic-api, extend `clinic-api/app/scheduling/router.py` with `POST /api/clin | 3.0 | api-design, backend-python | yes | 001-T047, 001-T059 |
| 001-T061 | In clinic-web, build `clinic-web/src/pages/manager/ClinicsDentistsPage.tsx` (cli | 5.5 | frontend-react, frontend-css | no | 001-T026, 001-T047 |

### S-001-US6 A patient's data is erased on request — P1/must · 3 SP (low, llm)

As a Practice manager (P-04) handling a patient's request to delete their data, I want to record an erasure request, see its 30-day due date and carry out the erasure so that the patient's name, phone number and birth year are removed within 30 days as the privacy rule requires.
Depends on: S-FOUND-001 · Sources: NFR-007

- [AC-S-001-US6-1] Given a signed-in manager and a patient account, When the manager records an erasure request, Then the request is stored with its date and a due date 30 days later and is listed as open
- [AC-S-001-US6-2] Given an open erasure request, When the manager runs the erasure, Then the patient's name, phone number and birth year are replaced by anonymous values, their sessions end, and the request is marked done with the date
- [AC-S-001-US6-3] Given an erased patient's former phone number, When that number signs in again, Then a brand-new account is created after the code is verified; nothing of the old data returns
- [AC-S-001-US6-4] Given an open request that is more than 30 days old, When the manager opens the list, Then it is flagged as overdue
- [AC-S-001-US6-5] Given a receptionist, dentist or patient, When they try to record or run an erasure, Then it is refused
- [AC-S-001-US6-6] Given an erasure ran, When logs and audit records are read, Then they contain the erased person's id only, never name or phone number

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T062 | In clinic-api, write unit tests `clinic-api/tests/unit/test_erasure_service.py`: | 3.0 | qa-automation, backend-python | yes | - |
| 001-T063 | In clinic-api, write `clinic-api/tests/integration/test_erasure_api.py` (manager | 3.5 | qa-automation, api-design | no | - |
| 001-T064 | In clinic-api, implement the registries in `clinic-api/app/jobs/registry.py`: `r | 1.5 | backend-python | yes | - |
| 001-T065 | In clinic-api, implement `clinic-api/app/identity/erasure_service.py`: `record_r | 4.5 | backend-python, postgres | no | 001-T064, 001-T021, 001-T016 |
| 001-T066 | In clinic-api, implement `clinic-api/app/identity/erasure_router.py` with `GET`  | 2.0 | api-design, backend-python | no | 001-T065, 001-T024 |
| 001-T067 | In clinic-web, build `clinic-web/src/pages/manager/ErasurePage.tsx` (find by pho | 3.5 | frontend-react | yes | 001-T026 |

### S-001-US7 Old identity data is cleaned up automatically — P1/must · 2 SP (low, llm)

As a Practice manager (P-04) accountable for the clinic's data protection, I want a daily job that deletes old sign-in codes and anonymises long-unused personal data, and lets later features add their own retention rules so that the system keeps only what it needs, as the privacy rule requires, without manual clean-up.
Depends on: S-001-US6 · Sources: NFR-007

- [AC-S-001-US7-1] Given a sign-in code created more than 24 hours ago, When the daily job runs, Then it is deleted
- [AC-S-001-US7-2] Given a staff account deactivated more than 24 months ago, When the daily job runs, Then its name is anonymised and the account stays deactivated
- [AC-S-001-US7-3] Given a patient account not used for 24 months, When the daily job runs, Then its personal data is anonymised in the same way as an erasure
- [AC-S-001-US7-4] Given a record inside its retention period, When the daily job runs, Then it is not changed
- [AC-S-001-US7-5] Given the daily job fails half-way, When it is run again, Then it finishes the work without double effects

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T068 | In clinic-api, write `clinic-api/tests/integration/test_retention_job.py`: code  | 4.0 | qa-automation, postgres | yes | - |
| 001-T069 | In clinic-api, implement `clinic-api/app/jobs/retention.py` with the rules of T0 | 5.5 | backend-python, postgres | no | 001-T064, 001-T065, 001-T018 |
| 001-T070 | In clinic-api, start the daily retention trigger with the app in `clinic-api/app | 2.5 | backend-python | yes | 001-T069, 001-T011 |

### S-SETUP-001 Platform, sign-in, roles and clinics (MOD-01): Setup — P1/must · 2 SP (low, llm)

Depends on: - · Sources: E-001, NFR-006, NFR-009

- [AC-S-SETUP-001-1] Given the setup tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T001 | In clinic-api, create the project skeleton from plan.md: `clinic-api/pyproject.t | 3.0 | backend-python, devops-ci | no | - |
| 001-T002 | In clinic-web, create the React and TypeScript single-page app skeleton: `clinic | 2.5 | frontend-react | no | - |
| 001-T003 | In clinic-api, add linting and formatting configuration in `clinic-api/pyproject | 3.0 | devops-ci, backend-python | no | - |
| 001-T004 | In clinic-web, add linting and formatting configuration in `clinic-web/package.j | 2.0 | devops-ci, frontend-react | no | - |
| 001-T005 | In clinic-api, copy `specs/001-platform-identity/contracts/identity-api.openapi. | 1.5 | api-design | yes | - |

### S-FOUND-001 Platform, sign-in, roles and clinics (MOD-01): Foundational prerequisites — P1/must · 8 SP (low, llm)

Depends on: S-SETUP-001 · Sources: E-001, NFR-006, NFR-009

- [AC-S-FOUND-001-1] Given the foundational prerequisites tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T006 | In clinic-api, implement settings from environment variables in `clinic-api/app/ | 2.0 | backend-python, auth-security | no | - |
| 001-T007 | In clinic-api, set up the database layer and migrations: `clinic-api/app/db.py`  | 1.5 | postgres, backend-python | no | 001-T001, 001-T006 |
| 001-T008 | In clinic-api, write the failing test `clinic-api/tests/unit/test_logging_pii.py | 1.0 | qa-automation, backend-python | yes | - |
| 001-T009 | In clinic-api, implement `clinic-api/app/logging_setup.py`: JSON structured logs | 2.5 | observability, backend-python | yes | 001-T008 |
| 001-T010 | In clinic-api, implement the error model in `clinic-api/app/errors.py`: JSON bod | 1.0 | backend-python, api-design | yes | - |
| 001-T011 | In clinic-api, implement `GET /health` in `clinic-api/app/health.py` (200 `{stat | 2.0 | backend-python, api-design | yes | 001-T006, 001-T007, 001-T009, 001-T010 |
| 001-T012 | In clinic-api, create shared test fixtures in `clinic-api/tests/conftest.py`: Po | 3.5 | qa-automation, postgres | yes | 001-T007, 001-T011 |
| 001-T013 | In clinic-api, add the integration test `clinic-api/tests/integration/test_healt | 1.0 | qa-automation, backend-python | yes | 001-T012 |
| 001-T014 | In clinic-api, define the scheduling models in `clinic-api/app/scheduling/models | 1.5 | data-modeling, postgres | yes | - |
| 001-T015 | In clinic-api, write migration `clinic-api/migrations/versions/0001_scheduling_c | 2.0 | postgres, data-modeling | no | 001-T007, 001-T014 |
| 001-T016 | In clinic-api, define the identity models in `clinic-api/app/identity/models.py` | 3.5 | data-modeling, auth-security | no | - |
| 001-T017 | In clinic-api, write migration `clinic-api/migrations/versions/0002_identity_acc | 2.0 | postgres, data-modeling | no | 001-T015, 001-T016 |
| 001-T018 | In clinic-api, write migration `clinic-api/migrations/versions/0003_identity_ses | 1.5 | postgres, data-modeling | no | 001-T017 |
| 001-T019 | In clinic-api, add `clinic-api/tests/integration/test_migrations.py`: upgrade to | 2.5 | qa-automation, postgres | no | 001-T012, 001-T018 |
| 001-T020 | In clinic-api, write the failing tests `clinic-api/tests/unit/test_sessions.py`  | 3.0 | qa-automation, auth-security | no | - |
| 001-T021 | In clinic-api, implement `clinic-api/app/identity/sessions.py`: create session r | 4.0 | auth-security, backend-python | no | 001-T016, 001-T018, 001-T020 |
| 001-T022 | In clinic-api, implement `clinic-api/app/identity/security.py`: middleware for t | 2.5 | auth-security, backend-python | no | 001-T011, 001-T020 |
| 001-T023 | In clinic-api, write the failing tests `clinic-api/tests/unit/test_access.py`: ` | 2.5 | qa-automation, auth-security | no | - |
| 001-T024 | In clinic-api, implement `clinic-api/app/identity/access.py`: `AccessContext` da | 3.5 | auth-security, backend-python | no | 001-T016, 001-T021, 001-T023 |
| 001-T025 | In clinic-web, implement the API client in `clinic-web/src/api/client.ts`: base  | 2.0 | frontend-react, api-design | yes | 001-T002 |
| 001-T026 | In clinic-web, implement the session base: `clinic-web/src/auth/SessionContext.t | 3.0 | frontend-react | no | 001-T025 |

### S-POLISH-001 Platform, sign-in, roles and clinics (MOD-01): Polish & cross-cutting concerns — P1/must · 2 SP (low, llm)

Depends on: S-001-US1, S-001-US4, S-001-US5, S-001-US7 · Sources: E-001, NFR-006, NFR-007, NFR-009, NFR-004

- [AC-S-POLISH-001-1] Given the polish & cross-cutting concerns tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T071 | In clinic-api, add `clinic-api/tests/integration/test_no_pii_in_logs.py` running | 2.0 | qa-automation, observability | yes | 001-T034, 001-T040, 001-T055, 001-T060, 001-T066, 001-T069 |
| 001-T072 | In clinic-api, add `clinic-api/tests/integration/test_access_query_count.py` ass | 1.5 | qa-automation, postgres | yes | 001-T024, 001-T047 |
| 001-T073 | In clinic-api, write the security review notes `clinic-api/docs/security-review- | 2.0 | auth-security, docs | no | 001-T034, 001-T040, 001-T055 |
| 001-T074 | In clinic-api, add `clinic-api/.env.example` (variable names only, no values) an | 1.0 | docs, devops-ci | no | 001-T070 |
| 001-T075 | In clinic-api, finish `clinic-api/contracts/clinic-api-v1.openapi.yaml` so it ma | 2.0 | api-design, qa-automation | yes | 001-T034, 001-T040, 001-T047, 001-T055, 001-T060, 001-T066 |
| 001-T076 | Run every scenario of `specs/001-platform-identity/quickstart.md` against a clea | 2.5 | qa-automation | no | 001-T071, 001-T075, 001-T035, 001-T042, 001-T056, 001-T061, 001-T067 |
| 001-T077 | Write the Release 1 readiness checklist for this module in `clinic-api/docs/rele | 1.0 | docs, devops-ci | no | 001-T076 |

## E-002 Dentist schedules, treatments and free slots

Weekly hours and breaks, leave with to-move list, treatment types, free-slot calculation. RELEASE 1 (DL-1, due 2027-02-22, hard). PRD ids: FR-007, FR-008, FR-009, FR-010.

### S-002-US1 Manage treatment types — P1/must · 3 SP (low, llm)

As a practice manager, I want to keep the list of treatment types with their duration and online flag so that free slots have the right length and patients can book online only the types the clinic allows.
Depends on: S-FOUND-002 · Sources: FR-009

- [AC-S-002-US1-1] Given a new system, When the practice manager opens the treatments screen, Then the list shows check-up, cleaning and consultation as online, 30 minutes each, and at least root canal and extraction as reception-only with 60 or 90 minutes
- [AC-S-002-US1-2] Given the treatments screen, When the manager adds a type with a name, a duration of 30, 60 or 90 minutes and the online flag, Then the type is saved and appears in the list at once
- [AC-S-002-US1-3] Given an existing type, When the manager changes its duration or online flag, Then the change applies to new slot searches and new bookings, and appointments already booked keep their own start and end times
- [AC-S-002-US1-4] Given an active type, When the manager switches it off, Then it no longer appears for booking, and appointments already booked with it are unchanged
- [AC-S-002-US1-5] Given a type name that already exists (ignoring capital letters), or a duration that is not 30, 60 or 90 minutes, When the manager saves, Then the save is refused with a message that names the problem
- [AC-S-002-US1-6] Given a signed-in patient, When they read the treatment list, Then they see only active online types; a receptionist sees all active types
- [AC-S-002-US1-7] Given a user who is not the practice manager, When they try to add or change a type, Then the request is refused

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 002-T011 | Unit tests for treatment rules (duration only 30, 60 or 90; duplicate name ignor | 1.5 | qa-automation, backend-python | yes | - |
| 002-T012 | API tests for `GET/POST /treatment-types` and `PATCH /treatment-types/{id}` (see | 2.5 | qa-automation, api-design | yes | - |
| 002-T013 | Create the treatment Pydantic schemas (`TreatmentType`, `TreatmentTypeInput`, `T | 1.0 | backend-python, api-design | yes | - |
| 002-T014 | Implement the treatment service (list by role, create, edit, switch off, `get_tr | 2.5 | backend-python, postgres | yes | 002-T006, 002-T013 |
| 002-T015 | Implement the treatment endpoints per `contracts/scheduling-api.openapi.yaml` in | 2.0 | backend-python, api-design | yes | 002-T014 |
| 002-T016 | Create the typed client for the treatment endpoints in repo clinic-web at `src/f | 1.0 | frontend-react | yes | - |
| 002-T017 | Build the treatments screen (table with name, minutes, online flag, active; add  | 4.5 | frontend-react, frontend-css | no | 002-T016 |
| 002-T018 | Component test for the treatments screen (list, add, edit, switch off, error sho | 3.0 | frontend-react, qa-automation | yes | 002-T017 |

### S-002-US2 Set weekly working hours and breaks — P1/must · 5 SP (low, llm)

As a practice manager, I want to set each dentist's weekly working hours and breaks per clinic, in India time so that free slots exist only when the dentist works, and a new clinic or dentist can be added as data without a release.
Depends on: S-FOUND-002 · Sources: FR-007, NFR-003

- [AC-S-002-US2-1] Given a dentist and a clinic with no hours, When the manager saves Monday 09:00–17:00 with a break 13:00–14:00, Then the weekly hours show that day with the break and the same values are returned on reload
- [AC-S-002-US2-2] Given hours for a dentist at one clinic, When the manager sets other weekdays at a second clinic, Then both sets are kept and shown per clinic
- [AC-S-002-US2-3] Given hours for a weekday, When the manager changes the start, end or breaks, Then new slot searches use the new hours and appointments already booked are not moved or cancelled
- [AC-S-002-US2-4] Given a weekday entry, When the end is not after the start, or a break lies outside the working day or overlaps another break, Then the save is refused with a message
- [AC-S-002-US2-5] Given a dentist with hours at clinic A on Monday 09:00–13:00, When the manager sets Monday hours at clinic B that overlap 09:00–13:00, Then the save is refused because one dentist cannot be at two clinics at once
- [AC-S-002-US2-6] Given a weekday with hours, When the manager removes that weekday, Then the dentist offers no slots at that clinic on that weekday
- [AC-S-002-US2-7] Given a newly added third clinic and a new dentist (added as data by the staff screens of feature 001), When the manager sets their hours, Then their slots become available with no software release
- [AC-S-002-US2-8] Given a user who is not the practice manager, When they try to change hours, Then the request is refused

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 002-T019 | Unit tests for hours validation (end after start, break inside the day, breaks n | 2.5 | qa-automation, backend-python | yes | - |
| 002-T020 | API tests for `GET /dentists/{id}/working-hours` and `PUT /dentists/{id}/clinics | 4.0 | qa-automation, api-design | yes | - |
| 002-T021 | API test that hours can be set for a clinic and a dentist created at run time th | 2.0 | qa-automation, api-design | yes | - |
| 002-T022 | Create the hours Pydantic schemas (`WorkingHoursInput`, `WorkingHours`, `TimeRan | 1.5 | backend-python, api-design | yes | - |
| 002-T023 | Implement the hours service (replace the set for one dentist and clinic in one t | 5.5 | backend-python, postgres | no | 002-T006, 002-T022 |
| 002-T024 | Implement the hours endpoints in repo clinic-api at `app/scheduling/routers/hour | 2.5 | backend-python, api-design | yes | 002-T023 |
| 002-T025 | Create the typed client for the hours endpoints in repo clinic-web at `src/featu | 1.5 | frontend-react | yes | - |
| 002-T026 | Build the "dentists and hours" screen (choose dentist and clinic, one row per we | 7.5 | frontend-react, frontend-css | no | 002-T025 |
| 002-T027 | Component test for the hours screen (set, edit, remove a weekday, overlap error) | 3.0 | frontend-react, qa-automation | yes | 002-T026 |

### S-002-US3 Find free slots and first available — P1/must · 8 SP (low, llm)

As a patient or receptionist booking a visit, I want a live list of free slots for a clinic, a treatment and a date range, and the 10 earliest slots across the clinic's dentists so that I can pick a time that really fits and is bookable at once.
Depends on: S-002-US1, S-002-US2 · Sources: FR-010, NFR-003, NFR-002

- [AC-S-002-US3-1] Given a dentist working 09:00–17:00 with a break 13:00–14:00 at a clinic and no bookings, When free slots are requested for a 30-minute type on that day, Then slots start every half hour from 09:00 to 16:30 except those inside 13:00–14:00
- [AC-S-002-US3-2] Given a 60-minute or 90-minute type, When free slots are requested, Then only starts where the full duration fits before the end of the day and before the next break, leave or booked appointment are returned (for example 12:30 is not offered for 60 minutes when the break starts at 13:00)
- [AC-S-002-US3-3] Given a booked appointment 10:00–10:30, When free slots are requested, Then the 10:00 slot is not offered, and a 60-minute type is not offered at 09:30 or 10:00
- [AC-S-002-US3-4] Given leave covering part of the day, When free slots are requested, Then no slot overlaps the leave
- [AC-S-002-US3-5] Given an appointment is cancelled, When free slots are requested again, Then its slot appears at once
- [AC-S-002-US3-6] Given a patient asks for slots, When the range goes past today plus the booking horizon (30 days) or starts in the past, Then only slots from now to the horizon are returned (1 March shows up to 31 March)
- [AC-S-002-US3-7] Given a clinic with several dentists, When "first available" is requested for a treatment type, Then the 10 earliest free slots across those dentists are returned in time order, each with its dentist
- [AC-S-002-US3-8] Given a treatment type that is not bookable online, When a patient asks for its slots, Then the request is refused; a receptionist or manager can ask for it
- [AC-S-002-US3-9] Given a receptionist of clinic A, When they ask for slots of clinic B, Then the request is refused
- [AC-S-002-US3-10] Given 3 clinics, 10 dentists and 1,000 appointments a week, When 100 users ask for free slots at the same time, Then 95% of the answers come back fast enough for the slot list to show within 2 seconds on a 4G phone
- [AC-S-002-US3-11] Given a request with a date range longer than 31 days, When slots are asked, Then the request is refused with a message

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 002-T028 | Unit tests for the slot engine (30, 60 and 90-minute fits, break, leave, booked  | 6.0 | qa-automation, backend-python | no | - |
| 002-T029 | API tests for `GET /clinics/{id}/slots` and `/slots/first-available` (online-onl | 6.0 | qa-automation, api-design | no | - |
| 002-T030 | API test that a clinic and a dentist added as data (third clinic, seventh dentis | 2.5 | qa-automation, api-design | yes | - |
| 002-T031 | Create the slot Pydantic schemas (`FreeSlot` and query parameters) in repo clini | 1.5 | backend-python, api-design | yes | - |
| 002-T032 | Implement the pure slot engine (per dentist and IST date: working window minus b | 9.0 | backend-python | no | 002-T028 |
| 002-T033 | Implement the slot service in repo clinic-api at `app/scheduling/services/slots. | 9.0 | backend-python, postgres | no | 002-T007, 002-T014, 002-T023, 002-T032 |
| 002-T034 | Implement the slot endpoints with the timing metric and ids-only logging in repo | 5.0 | backend-python, api-design | no | 002-T009, 002-T033 |
| 002-T035 | Write the load test and its seed (3 clinics, 10 dentists, 1,000 fake appointment | 9.0 | qa-automation, postgres | no | 002-T034 |

### S-002-US4 Record dentist leave and list appointments to move — P1/must · 5 SP (low, llm)

As a practice manager, I want to record a dentist's leave, whole or part days, and see the booked appointments inside it so that no slots are offered while the dentist is away and reception can phone and move the affected patients.
Depends on: S-002-US3 · Sources: FR-008

- [AC-S-002-US4-1] Given a dentist with hours, When the manager records whole-day leave for a date range, Then no free slots are offered for that dentist on those days at any clinic
- [AC-S-002-US4-2] Given a dentist, When the manager records part-day leave from 14:00 to 17:00, Then slots in that time are not offered and slots before and after are
- [AC-S-002-US4-3] Given appointments already booked in the leave time, When the leave is saved, Then those appointments are listed with patient name, phone number, clinic, treatment and start time, and each stays booked and unchanged
- [AC-S-002-US4-4] Given a leave with a "to move" list, When reception moves or cancels one of those appointments and the list is opened again, Then that appointment is no longer on it
- [AC-S-002-US4-5] Given a receptionist of clinic A, When they open the list, Then they see only appointments at clinic A; the manager sees all clinics
- [AC-S-002-US4-6] Given leave, When the manager changes its dates or times, Then the list and the slots follow the new times; when the manager deletes it, the slots in that time are offered again
- [AC-S-002-US4-7] Given a leave whose end is not after its start, or that overlaps another leave of the same dentist, When the manager saves, Then the save is refused with a message
- [AC-S-002-US4-8] Given leave that ended more than 24 months ago, When the yearly clean-up runs, Then it is deleted; newer leave stays
- [AC-S-002-US4-9] Given a user who is not the practice manager, When they try to record leave, Then the request is refused

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 002-T036 | Unit tests for leave rules (end after start, whole-day IST to UTC conversion, pa | 2.0 | qa-automation, backend-python | yes | - |
| 002-T037 | API tests for leave create, list, change, delete (201 with the to-move list, 409 | 3.5 | qa-automation, api-design | yes | - |
| 002-T038 | API tests for `GET /leave/{id}/appointments-to-move` (patient, phone, clinic, tr | 3.5 | qa-automation, api-design | yes | - |
| 002-T039 | Unit test for the 24-month leave retention job (older than 24 months after end d | 1.5 | qa-automation, backend-python | yes | - |
| 002-T040 | Create the leave Pydantic schemas (`LeaveInput`, `Leave`, `AppointmentToMove`, ` | 1.0 | backend-python, api-design | yes | - |
| 002-T041 | Implement the leave service (create, change, delete, list; whole days converted  | 5.0 | backend-python, postgres | no | 002-T006, 002-T007, 002-T040 |
| 002-T042 | Implement the leave endpoints in repo clinic-api at `app/scheduling/routers/leav | 2.5 | backend-python, api-design | yes | 002-T041 |
| 002-T043 | Implement the daily leave retention job in repo clinic-api at `app/scheduling/jo | 2.5 | backend-python | yes | 002-T039, 002-T010 |
| 002-T044 | Create the typed client for the leave endpoints in repo clinic-web at `src/featu | 1.0 | frontend-react | yes | - |
| 002-T045 | Build the leave screen (choose dentist, whole days or part day in India time, le | 5.0 | frontend-react, frontend-css | no | 002-T044 |
| 002-T046 | Component test for the leave screen (whole day, part day, appointments to move s | 2.5 | frontend-react, qa-automation | yes | 002-T045 |

### S-SETUP-002 Dentist schedules, treatments and free slots: Setup — P1/must · 1 SP (low, llm)

Depends on: - · Sources: E-002

- [AC-S-SETUP-002-1] Given the setup tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 002-T001 | Create the scheduling package skeleton in repo clinic-api: `app/scheduling/__ini | 3.0 | backend-python | yes | - |
| 002-T002 | Create the scheduling feature skeleton in repo clinic-web: `src/features/schedul | 3.0 | frontend-react | yes | - |

### S-FOUND-002 Dentist schedules, treatments and free slots: Foundational prerequisites — P1/must · 5 SP (low, llm)

Depends on: S-SETUP-002, S-FOUND-001 · Sources: E-002

- [AC-S-FOUND-002-1] Given the foundational prerequisites tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 002-T003 | Create the `TreatmentType` SQLAlchemy model in repo clinic-api at `app/schedulin | 3.0 | data-modeling, backend-python | yes | - |
| 002-T004 | Create the `WorkingHours` and `WorkingHoursBreak` models in repo clinic-api at ` | 4.0 | data-modeling, backend-python | yes | - |
| 002-T005 | Create the `Leave` model in repo clinic-api at `app/scheduling/models/leave.py`  | 3.0 | data-modeling, backend-python | yes | - |
| 002-T006 | Write the Alembic migration in repo clinic-api at `alembic/versions/<rev>_schedu | 6.0 | postgres, backend-python | no | 002-T003, 002-T004, 002-T005 |
| 002-T007 | Define the `AppointmentReader` protocol, `AppointmentBrief` dataclass, `register | 3.0 | backend-python, qa-automation | yes | - |
| 002-T008 | Build the authorisation dependencies in repo clinic-api at `app/scheduling/depen | 6.0 | auth-security, backend-python | no | - |
| 002-T009 | Add the structured-logging helper (ids only, never patient name, phone or birth  | 4.0 | backend-python, observability | yes | - |
| 002-T010 | Register the scheduling routers package in repo clinic-api at `app/scheduling/ro | 1.0 | backend-python | yes | 002-T008 |

### S-POLISH-002 Dentist schedules, treatments and free slots: Polish & cross-cutting concerns — P1/must · 2 SP (low, llm)

Depends on: S-002-US4 · Sources: E-002

- [AC-S-POLISH-002-1] Given the polish & cross-cutting concerns tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 002-T047 | Contract tests of every scheduling endpoint against `specs/002-schedules-slots/c | 3.5 | qa-automation, api-design | yes | 002-T015, 002-T024, 002-T034, 002-T042 |
| 002-T048 | Merge the scheduling paths and schemas into the shared API contract in repo clin | 1.5 | api-design | yes | 002-T047 |
| 002-T049 | Role matrix test (patient, receptionist of own and other clinic, dentist, manage | 2.5 | qa-automation, auth-security | no | 002-T015, 002-T024, 002-T034, 002-T042 |
| 002-T050 | Log scan test: run the API tests with a test patient and assert that no log line | 1.5 | qa-automation, backend-python | yes | 002-T042 |
| 002-T051 | Run the quickstart scenarios in `specs/002-schedules-slots/quickstart.md` agains | 3.0 | qa-automation, devops-ci | no | 002-T035, 002-T046, 002-T047 |

## E-003 Online booking by patients (MOD-03)

Patient books clinic, online treatment, dentist or first available, free slot within 30 days; no double booking. RELEASE 1 (DL-1, due 2027-02-22, hard). PRD ids: FR-011, FR-012.

### S-003-US1 Find a free slot — P1/must · 5 SP (low, llm)

As a patient (P-01) booking from a phone, I want to choose a clinic, an online treatment and a dentist or "first available" and see the free slots in the next 30 days so that I can pick a time that suits me without phoning the clinic.
Depends on: S-FOUND-003, S-002-US3 · Sources: FR-011, NFR-002

- [AC-S-003-US1-1] Given a signed-in patient on the "who and what" screen, When they open the treatment list for a clinic, Then only online-bookable treatment types (check-up, cleaning, consultation) are offered, and reception-only types are not
- [AC-S-003-US1-2] Given a clinic with several dentists who have free slots, When the patient chooses "first available", Then the system shows the earliest free slots across that clinic's dentists (at most 10, earliest first), each with dentist name, date and time
- [AC-S-003-US1-3] Given a patient who chose a named dentist, When they pick a day, Then the free slots of that dentist for that day are shown, on the hour or half hour
- [AC-S-003-US1-4] Given today is 1 March, When the patient looks at days, Then days from 1 March up to and including 31 March can be chosen and later days cannot (the window is today plus 30 days, a setting)
- [AC-S-003-US1-5] Given a day with no free slots, When the patient picks it, Then the screen says no slots are free that day and suggests the next day that has free slots
- [AC-S-003-US1-6] Given a patient who is not signed in, When they ask for slots, Then they are sent to sign in first (feature 001) and return to the same choice afterwards

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 003-T011 | Unit tests in `tests/booking/unit/test_slots.py`: only online treatment types of | 3.0 | qa-automation, backend-python | yes | - |
| 003-T012 | Contract tests for `GET /api/booking/options` and `GET /api/booking/slots` (200, | 3.0 | qa-automation, api-design | yes | - |
| 003-T013 | Implement the patient slot lookup in `app/modules/booking/slots.py`: horizon che | 5.0 | backend-python, api-design | no | 003-T003, 003-T006 |
| 003-T014 | Add `GET /api/booking/options` and `GET /api/booking/slots` to `app/modules/book | 3.0 | backend-python, api-design | no | 003-T013, 003-T008 |
| 003-T015 | Build the "who and what" screen `src/features/booking/WhoAndWhatScreen.tsx`: own | 4.0 | frontend-react, frontend-css | yes | - |
| 003-T016 | Build the slot picker `src/features/booking/SlotPickerScreen.tsx`: day choice fr | 5.0 | frontend-react, frontend-css | no | - |
| 003-T017 | Add `src/features/booking/BookingGuard.tsx`: a patient who is not signed in is s | 3.0 | frontend-react, auth-security | no | 003-T010 |
| 003-T018 | Screen tests in `src/features/booking/__tests__/who-and-slots.test.tsx`: treatme | 3.0 | frontend-react, qa-automation | yes | 003-T015, 003-T016, 003-T017 |

### S-003-US2 Confirm and see the booking — P1/must · 8 SP (low, llm)

As a patient (P-01) booking from a phone, I want to choose SMS or WhatsApp, confirm my slot and see the booked appointment so that I know my visit is booked and get my confirmation in the channel I read.
Depends on: S-FOUND-003, S-001-US1 · Sources: FR-011, NFR-002, NFR-010

- [AC-S-003-US2-1] Given a patient who picked a free slot, When they choose SMS or WhatsApp and confirm, Then the appointment is saved with status "booked" for their own account and the "booked" screen shows clinic, dentist, treatment, date, time and the chosen channel
- [AC-S-003-US2-2] Given a first-time booker, When the confirm screen opens, Then SMS is pre-selected as the default channel
- [AC-S-003-US2-3] Given a successful booking, When it is saved, Then one history entry "booked" with the patient as actor and the time is saved together with it, and a confirmation message request and the reminder record are saved in the same step
- [AC-S-003-US2-4] Given a successful booking, When the messaging provider is slow or down, Then the patient still sees the "booked" screen and the booking stays
- [AC-S-003-US2-5] Given the patient taps "Confirm" twice or their phone retries the request (same booking attempt), When the system receives both, Then only one appointment exists and both answers show that same appointment
- [AC-S-003-US2-6] Given a request that names another patient's account, When a patient submits it, Then it is refused and nothing is booked (a patient books only for their own account)
- [AC-S-003-US2-7] Given the "is this patient blocked" check, When a booking is made in Release 1, Then the check always allows booking (the real block arrives in Release 2)
- [AC-S-003-US2-8] Given a slow network, When no answer arrives within 10 seconds, Then the patient is told the result is unknown and is offered to check their appointments before trying again; the booking is never retried automatically

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 003-T019 | Unit tests in `tests/booking/unit/test_authorisation.py`: request naming another | 2.5 | qa-automation, auth-security | no | - |
| 003-T020 | Integration test in `tests/booking/integration/test_book.py`: happy path creates | 4.0 | qa-automation, postgres | yes | - |
| 003-T021 | Contract tests for `POST /api/appointments` (201, 200 replay, 401, 403, 422) in  | 2.5 | qa-automation, api-design | yes | - |
| 003-T022 | Integration test in `tests/booking/integration/test_idempotency.py`: same key an | 3.0 | qa-automation, postgres | yes | - |
| 003-T023 | Implement `book()` in `app/modules/booking/service.py`: validate horizon, online | 8.0 | backend-python, postgres | no | 003-T003, 003-T004, 003-T005, 003-T006, 003-T008 |
| 003-T024 | Add retry-key handling in `app/modules/booking/service.py`: look up (patient acc | 4.0 | backend-python, api-design | no | 003-T023 |
| 003-T025 | Add `POST /api/appointments` to `app/modules/booking/router.py`: required `Idemp | 3.0 | backend-python, auth-security | no | 003-T024 |
| 003-T026 | Build `src/features/booking/ConfirmScreen.tsx`: summary of person, clinic, denti | 5.0 | frontend-react, frontend-css | no | - |
| 003-T027 | Build `src/features/booking/BookedScreen.tsx` showing clinic, dentist, treatment | 2.5 | frontend-react | yes | - |
| 003-T028 | Screen tests in `src/features/booking/__tests__/confirm-booked.test.tsx`: SMS de | 3.5 | frontend-react, qa-automation | yes | 003-T026, 003-T027 |

### S-003-US3 A slot is never booked twice — P1/must · 5 SP (low, llm)

As a patient (P-01) booking from a phone, I want to be told when someone else takes my slot and to see the next free slots straight away so that I can pick again without starting over and am never double-booked.
Depends on: S-FOUND-003 · Sources: FR-012

- [AC-S-003-US3-1] Given two patients who confirm the same free slot at the same time, When both requests are processed, Then exactly one appointment is created and the other patient is told the slot was just taken
- [AC-S-003-US3-2] Given a patient told the slot was taken, When the message appears, Then the next free slots for the same clinic, treatment and dentist choice are shown on the same screen and the patient can pick one and confirm
- [AC-S-003-US3-3] Given a slot taken after "first available", When the patient is shown next free slots, Then they come from across the clinic's dentists again (at most 10)
- [AC-S-003-US3-4] Given a slot that overlaps part of another active appointment of the same dentist, When a booking is attempted, Then it is refused in the same way, not only when start times are equal
- [AC-S-003-US3-5] Given a cancelled appointment, When another patient books its slot, Then the booking succeeds (only active appointments block a slot)
- [AC-S-003-US3-6] Given a slot that is no longer free for a reason other than a booking (for example, leave was added), When the patient confirms, Then the patient gets the same "slot no longer available" message with next free slots

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 003-T029 | Integration tests in `tests/booking/integration/test_conflict.py`: two sessions  | 6.0 | qa-automation, postgres | no | - |
| 003-T030 | Contract test for the 409 `SlotTaken` body in `tests/booking/contract/test_confl | 2.0 | qa-automation, api-design | yes | - |
| 003-T031 | In `app/modules/booking/service.py` handle the exclusion violation (SQLSTATE 23P | 7.0 | backend-python, postgres | no | 003-T024 |
| 003-T032 | Map `SlotTaken` to HTTP 409 with the `SlotTaken` body in `app/modules/booking/ro | 2.5 | backend-python, api-design | yes | 003-T031 |
| 003-T033 | Show the "this slot was just taken" message with the next free slots on the same | 4.5 | frontend-react, frontend-css | no | 003-T026, 003-T016, 003-T032 |
| 003-T034 | Screen test in `src/features/booking/__tests__/slot-taken.test.tsx`: a 409 shows | 3.0 | frontend-react, qa-automation | yes | 003-T033 |

### S-003-US4 Prove no double booking under load — P1/must · 3 SP (low, llm)

As a practice manager (P-04) accountable for the clinics, I want automated proof that no two active appointments ever overlap for one dentist under simultaneous booking attempts so that reception never has to resolve a double booking at go-live.
Depends on: S-FOUND-003 · Sources: FR-012, NFR-002

- [AC-S-003-US4-1] Given a free slot and at least 30 simultaneous booking attempts for it, When a run finishes, Then exactly one attempt succeeded, all others got "slot taken", and 0 overlapping active appointments exist
- [AC-S-003-US4-2] Given 1,000 such runs, When all finish, Then 0 overlapping active appointments were found in 100% of runs
- [AC-S-003-US4-3] Given the same booking attempt sent several times at once with the same retry key, When the run finishes, Then exactly one appointment exists
- [AC-S-003-US4-4] Given the test report, When reviewed, Then it lists the number of runs, attempts, successes, conflicts and overlaps found

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 003-T035 | Write the concurrency test `tests/booking/concurrency/test_no_overlap.py` (marke | 7.0 | qa-automation, postgres | no | 003-T032 |
| 003-T036 | Write the report helper `tests/booking/concurrency/report.py` that writes runs,  | 2.5 | qa-automation, docs | yes | 003-T035 |
| 003-T037 | Run the suite against a PostgreSQL instance with two API instances (staging prof | 6.0 | qa-automation, devops-ci | no | 003-T036 |

### S-003-US5 Prove booking speed on a phone network — P1/must · 3 SP (low, llm)

As a patient (P-01) on a 4G phone, I want free slots within 2 seconds and my booking confirmed within 3 seconds so that booking stays quicker than phoning the clinic.
Depends on: S-FOUND-003 · Sources: NFR-002

- [AC-S-003-US5-1] Given 100 concurrent simulated patients on a 4G profile, When they open the slot picker, Then free slots are shown within 2 seconds for 95% of requests (server share at most 500 ms at the 95th percentile)
- [AC-S-003-US5-2] Given the same load, When patients confirm bookings, Then the confirmation is shown within 3 seconds for 95% of requests (server share at most 800 ms at the 95th percentile)
- [AC-S-003-US5-3] Given the "first available" view for a clinic with all dentists, When it is requested under load, Then it returns at most 10 slots and meets scenario 1
- [AC-S-003-US5-4] Given the test report, When reviewed, Then it states pass or fail against these limits and the data volume used (at least a year of appointments for 3 clinics and 10 dentists)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 003-T038 | Write a data seeder `tests/booking/performance/seed_data.py` creating 3 clinics, | 3.0 | qa-automation, postgres | yes | - |
| 003-T039 | Write the load script `tests/booking/performance/run_load.py` (arguments `--user | 6.0 | qa-automation, backend-python | no | 003-T032, 003-T038 |
| 003-T040 | Run the load script against staging, record the report, and if a limit is missed | 6.0 | qa-automation, postgres | no | 003-T039 |

### S-003-US6 Booking works on a phone for a new patient — P1/must · 3 SP (low, llm)

As a new patient (P-01) using an Android phone or an iPhone, I want to book in 5 screens or fewer with large tap targets and no sideways scrolling so that I can book without help from reception.
Depends on: S-FOUND-003 · Sources: NFR-001, NFR-010

- [AC-S-003-US6-1] Given a new patient who has just signed in, When they book a visit, Then they reach the "booked" screen after 5 screens or fewer (who and what, slot picker, confirm, booked)
- [AC-S-003-US6-2] Given every patient screen in this flow, When viewed on current Chrome and Safari on Android and iPhone at widths from 320 px, Then there is no sideways scrolling
- [AC-S-003-US6-3] Given every button, link, slot and field in this flow, When measured, Then each tap target is at least 44 px high and wide
- [AC-S-003-US6-4] Given "Back" is used on the phone, When the patient returns from a later screen, Then their earlier choices are still filled in
- [AC-S-003-US6-5] Given all texts and times in the flow, When viewed, Then they are in English and times are in India time (IST)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 003-T041 | Write the mobile-first styles `src/features/booking/booking.css` and apply them  | 5.0 | frontend-css, frontend-react | no | 003-T015, 003-T016, 003-T026, 003-T027 |
| 003-T042 | Layout tests in `src/features/booking/__tests__/mobile-layout.test.tsx`: the flo | 4.0 | frontend-react, qa-automation | yes | 003-T041 |
| 003-T043 | Write the device checklist `src/features/booking/__tests__/mobile-acceptance.md` | 2.0 | docs, qa-automation | yes | - |
| 003-T044 | Run the checklist on the four browser and device combinations, record the result | 5.0 | qa-automation, frontend-css | no | 003-T042, 003-T043 |

### S-SETUP-003 Online booking by patients (MOD-03): Setup — P1/must · 1 SP (low, llm)

Depends on: - · Sources: E-003, FR-011, FR-012, NFR-001, NFR-002, NFR-010

- [AC-S-SETUP-003-1] Given the setup tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 003-T001 | Create the cmp-booking module skeleton `app/modules/booking/__init__.py` and `ap | 1.5 | backend-python, qa-automation | yes | - |
| 003-T002 | Create the web feature folder `src/features/booking/` with `index.ts` exporting  | 1.0 | frontend-react | yes | - |

### S-FOUND-003 Online booking by patients (MOD-03): Foundational prerequisites — P1/must · 5 SP (low, llm)

Depends on: S-SETUP-003, S-FOUND-001 · Sources: E-003, FR-011, FR-012, NFR-001, NFR-002, NFR-010

- [AC-S-FOUND-003-1] Given the foundational prerequisites tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 003-T003 | Define the three in-process ports in `app/modules/booking/ports.py`: `SlotSource | 4.0 | backend-python, api-design | no | - |
| 003-T004 | Create SQLAlchemy models `Appointment`, `AppointmentEvent` and `BookingRequest`  | 4.0 | backend-python, data-modeling | yes | - |
| 003-T005 | Write the Alembic migration `alembic/versions/0003_online_booking.py`: `CREATE E | 5.0 | postgres, backend-python | no | 003-T004 |
| 003-T006 | Create request and response models in `app/modules/booking/schemas.py` from `spe | 3.0 | backend-python, api-design | yes | - |
| 003-T007 | Create test fixtures in `tests/booking/conftest.py` and `tests/booking/fakes.py` | 5.0 | qa-automation, backend-python | no | - |
| 003-T008 | Add telemetry in `app/modules/booking/telemetry.py`: structured log helper carry | 3.0 | observability, backend-python | yes | - |
| 003-T009 | Create the API client `src/features/booking/api.ts`: functions for `GET /api/boo | 3.0 | frontend-react, api-design | no | - |
| 003-T010 | Create `src/features/booking/bookingState.ts` holding the patient's choices (cli | 2.0 | frontend-react | yes | - |

### S-POLISH-003 Online booking by patients (MOD-03): Polish & cross-cutting concerns — P1/must · 2 SP (low, llm)

Depends on: S-003-US1, S-003-US2, S-003-US3, S-003-US4, S-003-US5, S-003-US6 · Sources: E-003, FR-011, FR-012, NFR-001, NFR-002, NFR-010, NFR-004

- [AC-S-POLISH-003-1] Given the polish & cross-cutting concerns tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 003-T045 | Merge the three operations and their schemas from `specs/003-online-booking/cont | 2.0 | api-design, docs | yes | - |
| 003-T046 | Add removal of `booking_request` rows older than 24 hours in `app/modules/bookin | 3.0 | backend-python, postgres | yes | - |
| 003-T047 | Record the authentication and authorisation review of the booking endpoints (per | 2.5 | auth-security, docs | no | - |
| 003-T048 | Run the steps of `specs/003-online-booking/quickstart.md` end to end on staging  | 3.0 | qa-automation, devops-ci | no | 003-T037, 003-T040, 003-T044 |

## E-004 Patient appointments: view, reschedule, cancel

My appointments list, reschedule and cancel until 4 hours before, freed slot, change messages. RELEASE 1 (DL-1, due 2027-02-22, hard). PRD ids: FR-015, FR-016, FR-017, FR-018.

### S-004-US1 See my appointments — P1/must · 5 SP (low, llm)

As a patient (P-01) signed in on my phone, I want to see my upcoming and past appointments with their status and open one so that I can check a booking, and change or cancel it, without phoning reception.
Depends on: S-FOUND-004 · Sources: FR-015, FR-017

- [AC-S-004-US1-1] Given a signed-in patient with upcoming and past appointments, When they open "My appointments", Then they see the upcoming ones first (earliest first) and the past ones below (latest first), each with clinic, dentist, treatment, date, time in IST and status. (source: FR-015)
- [AC-S-004-US1-2] Given a patient with a cancelled appointment and an appointment marked arrived or no-show, When they open "My appointments", Then those appear in the past group with the status shown in plain words (for example "Cancelled by you", "Cancelled by the clinic", "Attended", "Missed"). (source: FR-015)
- [AC-S-004-US1-3] Given a patient with no appointments, When they open "My appointments", Then they see a short message and a "Book" button. (source: FR-015)
- [AC-S-004-US1-4] Given a signed-in patient, When they ask for the appointment of another patient (by changing the id in the address), Then the system answers as if it does not exist and shows no data of that other patient. (source: FR-015)
- [AC-S-004-US1-5] Given an upcoming appointment that starts in more than 4 hours, When the patient opens it, Then the buttons "Change time" and "Cancel" are shown. **Given** one that starts in 4 hours or less, **When** the patient opens it, **Then** the buttons are replaced by the clinic's phone number. (source: FR-015, FR-017)
- [AC-S-004-US1-6] Given a phone with a screen 360 px wide, When the patient uses these screens, Then the page needs no sideways scrolling and every button has a tap target of at least 44 px (the same measures as task 004-T052). (source: FR-015)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 004-T012 | Integration tests for `GET /api/me/appointments` in `tests/booking/test_patient_ | 3.5 | qa-automation, backend-python | yes | - |
| 004-T013 | Access tests in `tests/booking/test_patient_access.py`: another patient's appoin | 2.0 | qa-automation, auth-security | no | - |
| 004-T014 | Contract test of `listMyAppointments` and `getMyAppointment` against the OpenAPI | 2.0 | qa-automation, api-design | yes | - |
| 004-T015 | Screen tests in `src/pages/__tests__/MyAppointmentsPage.test.tsx` and `src/pages | 3.5 | frontend-react, qa-automation | yes | - |
| 004-T016 | Implement `list_for_account(session, account_id, past_cursor, past_limit)` in `a | 3.0 | postgres, backend-python | yes | 004-T009 |
| 004-T017 | Implement `list_appointments` and `get_appointment` in `app/booking/patient_serv | 3.5 | backend-python | yes | 004-T005, 004-T007, 004-T016 |
| 004-T018 | Implement `GET /api/me/appointments` and `GET /api/appointments/{appointmentId}` | 3.0 | api-design, backend-python | no | 004-T017 |
| 004-T019 | Create `src/components/AppointmentCard.tsx` and `src/components/ClinicPhoneNotic | 3.0 | frontend-react, frontend-css | yes | - |
| 004-T020 | Create `src/pages/MyAppointmentsPage.tsx`: groups per person, upcoming then past | 3.0 | frontend-react | yes | 004-T019 |
| 004-T021 | Create `src/pages/AppointmentPage.tsx`: details, "Change time" and "Cancel" butt | 3.5 | frontend-react | yes | 004-T019 |

### S-004-US2 Cancel an upcoming appointment — P1/must · 5 SP (low, llm)

As a patient (P-01) with an upcoming appointment I cannot attend, I want to cancel it myself with a confirmation until 4 hours before the start so that the slot is freed for others at once and I get a message in my chosen channel without phoning reception.
Depends on: S-FOUND-004 · Sources: FR-017, FR-018

- [AC-S-004-US2-1] Given an upcoming appointment more than 4 hours away, When the patient chooses "Cancel" and confirms, Then the appointment status becomes "cancelled by the patient", the "Done" screen shows the result, and a record of who cancelled and when is kept. (source: FR-017)
- [AC-S-004-US2-2] Given a cancelled appointment, When another patient looks for slots of that dentist at that time, Then the slot is offered at once and can be booked. (source: FR-018)
- [AC-S-004-US2-3] Given a cancelled appointment, When the cancel is done, Then the patient gets a message in the channel chosen for that appointment stating clinic, dentist, date and time of the cancelled visit, and no reminder is sent for it. (source: FR-018)
- [AC-S-004-US2-4] Given an appointment 4 hours or less away, When the patient opens it, Then no "Cancel" button is shown, the clinic phone number is shown, and a cancel request made some other way is refused with the same phone number in the answer. (source: FR-017)
- [AC-S-004-US2-5] Given the patient chooses "Cancel", When they do not confirm (they go back), Then nothing changes. (source: FR-017)
- [AC-S-004-US2-6] Given the patient taps "Confirm" twice, When the second request arrives, Then the appointment is cancelled once, one message is sent, and the patient sees the same "Done" screen. (source: FR-017, FR-018)
- [AC-S-004-US2-7] Given the message provider is unavailable, When the patient cancels, Then the cancel still succeeds and the message is sent later. (source: FR-018)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 004-T022 | Integration tests in `tests/booking/test_patient_cancel.py`: success sets `cance | 5.0 | qa-automation, backend-python | no | - |
| 004-T023 | Tests in `tests/messaging/test_change_messages.py`: cancelled template row creat | 2.5 | qa-automation, messaging | yes | - |
| 004-T024 | Screen tests in `src/pages/__tests__/CancelFlow.test.tsx`: confirm sheet, going  | 2.5 | frontend-react, qa-automation | yes | - |
| 004-T025 | Implement `queue_change_message(session, appointment, kind)` for kinds `cancelle | 3.0 | messaging, backend-python | yes | - |
| 004-T026 | Implement `cancel_reminders(session, appointment_id)` in `app/messaging/reminder | 1.5 | messaging, backend-python | yes | - |
| 004-T027 | Add template ids for `appointment_cancelled` and `appointment_rescheduled` to th | 2.0 | backend-python, docs | yes | - |
| 004-T028 | Implement `cancel_appointment` in `app/booking/patient_service.py`: one transact | 6.0 | backend-python, postgres | no | 004-T005, 004-T010, 004-T011, 004-T017, 004-T025, 004-T026 |
| 004-T029 | Implement `POST /api/appointments/{appointmentId}/cancel` in `app/booking/patien | 1.5 | api-design, backend-python | yes | 004-T028 |
| 004-T030 | Create `src/components/ConfirmCancelSheet.tsx` with "Confirm" and "Back" (tap ta | 1.5 | frontend-react, frontend-css | yes | - |
| 004-T031 | Create `src/pages/AppointmentDonePage.tsx` for the result of a cancel or a resch | 2.0 | frontend-react | yes | - |
| 004-T032 | Wire the cancel action into `src/pages/AppointmentPage.tsx` and `src/api/appoint | 2.5 | frontend-react | yes | 004-T021, 004-T030, 004-T031 |

### S-004-US3 Reschedule an upcoming appointment — P1/must · 8 SP (low, llm)

As a patient (P-01) who cannot make my appointment time, I want to move it to another free slot of the same clinic and treatment until 4 hours before so that I keep my visit instead of cancelling, the old slot is freed at once and I get a message in my chosen channel.
Depends on: S-FOUND-004, S-002-US3 · Sources: FR-016, FR-018, FR-017

- [AC-S-004-US3-1] Given an upcoming appointment more than 4 hours away, When the patient chooses "Change time", Then they see free slots for the same clinic and treatment from any dentist, within the same booking horizon as new bookings, never the slot they already hold. (source: FR-016)
- [AC-S-004-US3-2] Given the patient picks a free slot and confirms, When the change is saved, Then the appointment has the new date, time and dentist, keeps its clinic, treatment and channel, and the "Done" screen shows the new details. (source: FR-016)
- [AC-S-004-US3-3] Given the change is saved, When another patient looks for slots, Then the old slot is offered at once. (source: FR-018)
- [AC-S-004-US3-4] Given the change is saved, When messages are created, Then the patient gets a message in the channel chosen for that appointment with the new clinic, dentist, date and time, and the old reminder is withdrawn so that only a reminder for the new time can exist. (source: FR-016, FR-018)
- [AC-S-004-US3-5] Given another patient takes the chosen slot while this patient is choosing, When the patient confirms, Then nothing changes, the patient is told the slot was just taken and is shown the next free slots, and keeps their original appointment. (source: FR-016)
- [AC-S-004-US3-6] Given an appointment 4 hours or less away, When the patient opens it, Then no "Change time" button is shown, the clinic phone number is shown, and a change request made some other way is refused. (source: FR-016, FR-017)
- [AC-S-004-US3-7] Given the no-show policy says a patient may not reschedule, When the patient chooses "Change time", Then the page shows the clinic phone number instead. In Release 1 the policy always allows. (source: FR-016)
- [AC-S-004-US3-8] Given a reschedule, When the history is read, Then it shows who changed the appointment, when, and the old and new time. (source: FR-016, FR-018)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 004-T033 | Tests for `GET /api/appointments/{appointmentId}/reschedule-slots` in `tests/boo | 3.0 | qa-automation, backend-python | yes | - |
| 004-T034 | Tests for `POST /api/appointments/{appointmentId}/reschedule` in `tests/booking/ | 5.0 | qa-automation, backend-python | no | - |
| 004-T035 | Concurrency test in `tests/booking/test_reschedule_race.py`: two patients take t | 4.0 | qa-automation, postgres | yes | - |
| 004-T036 | Screen tests in `src/pages/__tests__/ReschedulePickerPage.test.tsx`: slot list,  | 3.0 | frontend-react, qa-automation | yes | - |
| 004-T037 | Implement `free_slots_for_reschedule(session, appointment, date_from, date_to)`  | 5.0 | backend-python, postgres | no | - |
| 004-T038 | Implement `recreate_reminder(session, appointment)` in `app/messaging/reminder_p | 3.5 | messaging, backend-python | yes | 004-T026 |
| 004-T039 | Implement `list_reschedule_slots` in `app/booking/patient_service.py` and `GET / | 3.5 | api-design, backend-python | yes | 004-T018, 004-T037 |
| 004-T040 | Implement `reschedule_appointment` in `app/booking/patient_service.py`: one tran | 9.0 | backend-python, postgres | no | 004-T028, 004-T037, 004-T038, 004-T039 |
| 004-T041 | Implement `POST /api/appointments/{appointmentId}/reschedule` in `app/booking/pa | 2.5 | api-design, backend-python | yes | 004-T029, 004-T040 |
| 004-T042 | Create `src/pages/ReschedulePickerPage.tsx` (slot picker): days and slots from ` | 5.0 | frontend-react, frontend-css | no | 004-T031 |
| 004-T043 | Wire "Change time" in `src/pages/AppointmentPage.tsx` and error handling in `src | 4.5 | frontend-react | no | 004-T032, 004-T042 |

### S-004-US4 Open an appointment from a message link — P1/must · 2 SP (low, llm)

As a patient (P-01) reading a confirmation, change or reminder message, I want the link in the message to open my appointment after I sign in so that I can change or cancel in one tap, and nobody else can open it.
Depends on: S-FOUND-004 · Sources: FR-015, FR-016, FR-017

- [AC-S-004-US4-1] Given a patient who is not signed in, When they open the appointment link, Then they are asked to sign in and, after signing in, the appointment screen opens. (source: FR-015)
- [AC-S-004-US4-2] Given a signed-in patient, When they open the link of their own appointment, Then the appointment screen opens at once with the buttons or the phone number according to the 4-hour rule. (source: FR-015, FR-017)
- [AC-S-004-US4-3] Given a patient signed in as someone else, When they open the link, Then they see "appointment not found" and no data of the appointment. (source: FR-015)
- [AC-S-004-US4-4] Given a link to a cancelled or past appointment, When the patient opens it, Then the appointment screen shows its status without buttons. (source: FR-015)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 004-T044 | Tests in `src/auth/__tests__/ReturnTo.test.tsx`: signed-out visit of `/appointme | 3.0 | frontend-react, qa-automation | no | - |
| 004-T045 | Test in `tests/messaging/test_appointment_link.py` that confirmation, change and | 2.0 | qa-automation, messaging | yes | - |
| 004-T046 | Create the route guard in `src/auth/ReturnTo.tsx` (stores `returnTo`, sends sign | 3.5 | frontend-react, auth-security | no | 004-T044 |
| 004-T047 | Show "Appointment not found" with a "Sign out" option in `src/pages/AppointmentP | 1.5 | frontend-react | yes | 004-T021, 004-T046 |
| 004-T048 | Add or extend `appointment_link(appointment_id)` in `app/messaging/links.py` usi | 2.0 | messaging, backend-python | yes | 004-T025, 004-T045 |

### S-SETUP-004 Patient appointments: view, reschedule, cancel: Setup — P1/must · 1 SP (low, llm)

Depends on: - · Sources: E-004, FR-015, FR-016, FR-017, FR-018

- [AC-S-SETUP-004-1] Given the setup tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 004-T001 | Create the module skeleton `app/booking/patient_router.py`, `app/booking/patient | 1.5 | backend-python | no | - |
| 004-T002 | Create the web skeleton: `src/api/appointments.ts` (typed client for the five op | 3.0 | frontend-react, api-design | yes | - |
| 004-T003 | Merge `specs/004-patient-appointments/contracts/patient-appointments.openapi.yam | 1.5 | api-design | yes | - |

### S-FOUND-004 Patient appointments: view, reschedule, cancel: Foundational prerequisites — P1/must · 3 SP (low, llm)

Depends on: S-SETUP-004, S-FOUND-003 · Sources: E-004, FR-015, FR-016, FR-017, FR-018

- [AC-S-FOUND-004-1] Given the foundational prerequisites tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 004-T004 | Write unit tests for the change window in `tests/booking/test_change_window.py`: | 2.5 | qa-automation, backend-python | yes | - |
| 004-T005 | Implement `can_change(status, start_at, now)` and `change_deadline(start_at)` re | 1.5 | backend-python | yes | 004-T004 |
| 004-T006 | Define the interfaces `RescheduleRule.check(patient_id)` returning allowed or bl | 1.0 | backend-python | yes | - |
| 004-T007 | Implement `AlwaysAllowRescheduleRule` (Release 1; Release 2 replaces it with the | 1.5 | backend-python | yes | 004-T006 |
| 004-T008 | Define the response and request models `Person`, `Appointment` (with `can_change | 2.5 | api-design, backend-python | yes | - |
| 004-T009 | Implement `get_owned_appointment(session, account_id, appointment_id, for_update | 3.5 | postgres, backend-python | no | 004-T008 |
| 004-T010 | Extend `app/booking/history.py` with `write_event(session, appointment_id, from_ | 2.5 | backend-python, postgres | yes | - |
| 004-T011 | Add OpenTelemetry counters `appointment_cancelled`, `appointment_rescheduled`, ` | 3.0 | backend-python | yes | - |

### S-POLISH-004 Patient appointments: view, reschedule, cancel: Polish & cross-cutting concerns — P1/must · 2 SP (low, llm)

Depends on: S-004-US1, S-004-US2, S-004-US3, S-004-US4 · Sources: E-004, FR-015, FR-016, FR-017, FR-018

- [AC-S-POLISH-004-1] Given the polish & cross-cutting concerns tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 004-T049 | Security test matrix in `tests/booking/test_patient_rbac_matrix.py`: every opera | 3.0 | qa-automation, auth-security | no | - |
| 004-T050 | Test in `tests/booking/test_no_pii_in_logs.py` that cancel and reschedule logs c | 2.0 | qa-automation, backend-python | yes | - |
| 004-T051 | Check that an index on `(patient_id, start_at)` exists for the list query; if no | 1.5 | postgres, backend-python | no | - |
| 004-T052 | Check 360 px layout and 44 px tap targets on all four screens and adjust `src/st | 1.5 | frontend-css, frontend-react | yes | - |
| 004-T053 | Run the quickstart scenarios in `specs/004-patient-appointments/quickstart.md` a | 4.0 | qa-automation, docs | no | 004-T041, 004-T043, 004-T047, 004-T048 |

## E-005 Reception day view, check-in, no-shows and dentist day (MOD-05)

Reception day view, book/reschedule/cancel for patients, patient search/create, arrived, no-show and undo, dentist own day, status history. RELEASE 1 (DL-1, due 2027-02-22, hard). PRD ids: FR-019, FR-020, FR-021, FR-022, FR-023, FR-024.

### S-005-US1 Reception sees the day of their clinic — P1/must · 5 SP (low, llm)

As a receptionist (P-02), I want to see today's day view of my clinic with one column per working dentist and move to other days so that I can see every dentist's day at a glance and run the desk without the paper diary.
Depends on: S-FOUND-005 · Sources: FR-019, FR-024

- [AC-S-005-US1-1] Given a receptionist of clinic A is signed in and three dentists work at clinic A today, When they open the day view, Then today's date in India time is shown with exactly three columns, one per dentist, each listing that dentist's appointments in time order. (source: FR-019)
- [AC-S-005-US1-2] Given an appointment exists, When it appears in the day view, Then it shows patient name, phone number, treatment and status, and the status is one of booked, arrived, no-show, cancelled by the patient or cancelled by the clinic. (source: FR-019, FR-024)
- [AC-S-005-US1-3] Given a dentist has no working hours at clinic A on the chosen day, When the receptionist views that day, Then that dentist has no column. (source: FR-019)
- [AC-S-005-US1-4] Given the day view of today, When the receptionist moves to the next day, the previous day or a chosen date, Then the columns and appointments of that day are shown. (source: FR-019)
- [AC-S-005-US1-5] Given appointments exist at clinic B, When the receptionist of clinic A opens any day or asks for a clinic B appointment directly, Then none of clinic B's appointments are shown and a direct request is refused. (source: FR-019, FR-004)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 005-T012 | Contract test for `GET /api/reception/day` against `contracts/clinic-api-v1.open | 2.0 | qa-automation, api-design | yes | - |
| 005-T013 | Integration test for the day view: one column per dentist with hours that day, n | 4.0 | qa-automation, postgres | yes | - |
| 005-T014 | Implement the day view read model (dentists with working hours at the clinic on  | 7.0 | backend-python, postgres | no | 005-T011 |
| 005-T015 | Add the `DayView` schemas to `app/modules/reception/schemas.py` and the route `G | 3.0 | backend-python, api-design | yes | 005-T014 |
| 005-T016 | Add the day view API client `getDayView(date)` and types in `src/features/recept | 1.5 | frontend-react | yes | - |
| 005-T017 | Build the day view screen with one column per dentist, appointment cards (patien | 8.5 | frontend-react, frontend-css | no | 005-T016 |
| 005-T018 | Component test for the day view (columns, status badges, date navigation, empty  | 3.0 | qa-automation, frontend-react | yes | - |
| 005-T019 | Make `/reception` the landing route of the receptionist role after sign-in in `s | 1.0 | frontend-react | no | 005-T017 |

### S-005-US2 Reception marks arrived and no-show, and can undo — P1/must · 5 SP (low, llm)

As a receptionist (P-02), I want to mark a patient arrived, mark a no-show from 15 minutes after the start until the end of the day, and undo it that day so that no-show data is correct and every status change shows who made it and when.
Depends on: S-FOUND-005 · Sources: FR-021, FR-022, FR-024

- [AC-S-005-US2-1] Given a booked appointment of the receptionist's clinic, When the receptionist marks the patient as arrived, Then the status becomes arrived and the day view shows it. (source: FR-021)
- [AC-S-005-US2-2] Given a booked appointment that started 15 minutes ago or more today, When the receptionist marks a no-show, Then the status becomes no-show. (source: FR-022)
- [AC-S-005-US2-3] Given a booked appointment that started less than 15 minutes ago, or has not started yet, When the receptionist tries to mark a no-show, Then the request is refused with a message that says from which time it is allowed, and the status stays booked. (source: FR-022)
- [AC-S-005-US2-4] Given an appointment on an earlier day that is still booked, When the receptionist tries to mark a no-show, Then the request is refused because the day has ended. (source: FR-022)
- [AC-S-005-US2-5] Given an appointment marked no-show today, When the receptionist undoes it the same day, Then the status returns to booked; **and when** the day has ended, **Then** undo is refused. (source: FR-022)
- [AC-S-005-US2-6] Given any status change (arrived, no-show, undo, cancel), When it is made, Then the change is stored with the previous and new status, the staff member who made it and the time, and that history can be read for the appointment. (source: FR-024)
- [AC-S-005-US2-7] Given an appointment that is arrived, no-show or cancelled, When a change is attempted that the status rules do not allow (for example marking an arrived patient a no-show, or arriving a cancelled appointment), Then it is refused and nothing is changed. (source: FR-024, FR-021, FR-022)
- [AC-S-005-US2-8] Given two receptionists act on the same appointment at the same time, When both save, Then one change is kept, the other is told the appointment was changed and sees the current status. (source: FR-024)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 005-T020 | Integration tests for `arrive`, `no-show` and `undo` (15-minute boundary, tomorr | 6.0 | qa-automation, postgres | no | - |
| 005-T021 | Implement `POST /api/reception/appointments/{id}/arrive`, `/no-show` and `/undo` | 6.0 | backend-python, api-design | no | 005-T009, 005-T011 |
| 005-T022 | Implement `GET /api/reception/appointments/{id}/history` (who, from, to, when, r | 3.0 | backend-python, api-design | yes | 005-T021 |
| 005-T023 | Add API clients `markArrived`, `markNoShow`, `undoStatus`, `getHistory` in `src/ | 1.5 | frontend-react | yes | - |
| 005-T024 | Build the appointment panel with Arrived, No-show (disabled with the allowed-fro | 6.0 | frontend-react, frontend-css | no | 005-T023 |
| 005-T025 | Open the appointment panel from an appointment card in `src/features/reception/D | 3.0 | frontend-react | yes | 005-T017, 005-T024 |
| 005-T026 | Component test for the panel (button states by time, undo, conflict message, his | 4.5 | qa-automation, frontend-react | no | - |

### S-005-US3 Reception finds or creates a patient — P1/must · 5 SP (low, llm)

As a receptionist (P-02), I want to find a patient by phone number or name, or create one with name and phone number so that I can book phone callers and walk-ins quickly without creating duplicates.
Depends on: S-FOUND-005 · Sources: FR-020

- [AC-S-005-US3-1] Given patients exist, When the receptionist enters a phone number or part of one (at least 4 digits), Then the matching patients are listed with name and phone number. (source: FR-020)
- [AC-S-005-US3-2] Given patients exist, When the receptionist enters part of a name (at least 2 letters), Then the matching patients are listed with name and phone number, ordered by best match. (source: FR-020)
- [AC-S-005-US3-3] Given a patient who has only booked at the other clinic, When the receptionist searches for them, Then they are found, and no appointment of the other clinic is shown. (source: FR-020, FR-004)
- [AC-S-005-US3-4] Given no patient matches, When the receptionist enters a name and a phone number and saves, Then a patient is created and selected for booking. (source: FR-020)
- [AC-S-005-US3-5] Given a phone number that already belongs to a patient account, When the receptionist tries to create a patient with that phone number, Then the existing patient is offered instead of a duplicate. (source: FR-020)
- [AC-S-005-US3-6] Given a missing name, or a phone number that is not a valid Indian mobile number, When the receptionist saves, Then the form shows what must be corrected and nothing is created. (source: FR-020)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 005-T027 | Integration tests for search (4+ digits, 2+ letters, +91 and spaces normalised,  | 5.0 | qa-automation, postgres | no | - |
| 005-T028 | Add or reuse `normalise_indian_mobile(raw)` (10 digits starting 6 to 9, optional | 2.0 | backend-python | yes | - |
| 005-T029 | Implement `search_patients(q)` (phone suffix match or name contains, case-insens | 6.0 | backend-python, postgres | no | 005-T028 |
| 005-T030 | Implement `GET /api/reception/patients/search?q=` and `POST /api/reception/patie | 3.5 | backend-python, api-design | no | 005-T011, 005-T029 |
| 005-T031 | Add API clients `searchPatients(q)` and `createPatient(name, phone)` in `src/fea | 1.5 | frontend-react | yes | - |
| 005-T032 | Build the patient search component with debounced search, result list (name and  | 8.0 | frontend-react, frontend-css | no | 005-T031 |
| 005-T033 | Component test for patient search and create (short query hint, results, duplica | 4.0 | qa-automation, frontend-react | yes | - |

### S-005-US4 Reception books, moves and cancels for patients — P1/must · 8 SP (low, llm)

As a receptionist (P-02), I want to book any treatment (including reception-only types and walk-ins), and move or cancel appointments for patients without the 4-hour cut-off so that phone and walk-in patients are served and the paper-diary appointments can be typed in before go-live.
Depends on: S-FOUND-005, S-002-US3 · Sources: FR-020, FR-021, FR-024

- [AC-S-005-US4-1] Given a selected patient, When the receptionist picks any active treatment type (online or reception-only), a dentist of their clinic and a free slot and confirms, Then the appointment is booked in the clinic for that dentist and appears at once in the day view. (source: FR-020)
- [AC-S-005-US4-2] Given a slot starts in less than 4 hours, When the receptionist books, moves or cancels an appointment in it, Then the action is allowed, because reception has no 4-hour cut-off. (source: FR-020)
- [AC-S-005-US4-3] Given a patient who walks in, When the receptionist books a free slot and chooses "walk-in", Then a normal appointment is created with status arrived and it counts like any other appointment. (source: FR-020, FR-021, FR-024)
- [AC-S-005-US4-4] Given the slot is taken by another booking while the receptionist is choosing, When they confirm, Then nothing is double booked, they are told the slot is taken and are shown the next free slots. (source: FR-020)
- [AC-S-005-US4-5] Given a booked appointment, When the receptionist moves it to another free slot of the same or another dentist at their clinic, Then the old slot is free at once, the appointment keeps its patient and treatment, and the move is recorded in the history. (source: FR-020, FR-024)
- [AC-S-005-US4-6] Given a booked appointment, When the receptionist cancels it and states that the patient asked, Then the status becomes cancelled by the patient; **and when** the clinic cancelled, **Then** the status becomes cancelled by the clinic. In both cases the slot is free at once. (source: FR-020, FR-024)
- [AC-S-005-US4-7] Given a booking, move or cancel by reception, When it is saved, Then the patient gets the confirmation or change message in their channel, as delivered by the messages feature (006); a failure to send does not undo the booking. (source: FR-020)
- [AC-S-005-US4-8] Given the appointment belongs to the other clinic, When the receptionist tries to move or cancel it, Then it is refused. (source: FR-020, FR-004)
- [AC-S-005-US4-9] Given a typed-in future appointment before go-live (paper diary), When the receptionist books it, Then it works the same as any booking, so the dry run in the week before go-live can use these screens. (source: FR-020)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 005-T034 | Integration tests for reception booking: any active type, no 4-hour or 30-day li | 6.0 | qa-automation, postgres | no | - |
| 005-T035 | Concurrency test: 1,000 simultaneous attempts on one slot from reception and onl | 3.0 | qa-automation, postgres | yes | - |
| 005-T036 | Define the messaging port `notify_confirmation(appointment_id)` and `notify_chan | 1.5 | backend-python, messaging | yes | - |
| 005-T037 | Add an audience option "reception" to the free-slot calculation (all active trea | 4.0 | backend-python, postgres | yes | - |
| 005-T038 | Implement reception `book` (walk-in inserts with status arrived), `move` and `ca | 11.0 | backend-python, postgres | no | 005-T009, 005-T036, 005-T037 |
| 005-T039 | Implement `GET /api/reception/slots`, `POST /api/reception/appointments`, `/{id} | 4.0 | backend-python, api-design | yes | 005-T011, 005-T038 |
| 005-T040 | Add API clients `getReceptionSlots`, `bookForPatient` (sends Idempotency-Key), ` | 1.5 | frontend-react | yes | - |
| 005-T041 | Build the "book for patient" screen: selected patient from the patient search, a | 7.5 | frontend-react, frontend-css | no | 005-T032, 005-T040 |
| 005-T042 | Add Move (opens the slot picker) and Cancel (dialog "patient asked" or "clinic c | 4.0 | frontend-react | yes | 005-T024, 005-T041 |
| 005-T043 | Add a "New booking" button and a click-on-free-time entry that open the book-for | 2.5 | frontend-react | yes | 005-T025, 005-T041 |
| 005-T044 | Component test for the book-for-patient screen and the cancel dialog (walk-in, c | 3.0 | qa-automation, frontend-react | yes | - |

### S-005-US5 Dentist sees their own day, read only — P1/must · 3 SP (low, llm)

As a dentist (P-03), I want to see my own appointments for the day at each clinic where I work, read only, on phone or PC so that I know each patient and treatment of my day without asking reception.
Depends on: S-FOUND-005 · Sources: FR-023

- [AC-S-005-US5-1] Given a dentist works at clinic A in the morning and clinic B in the afternoon today, When they open "my day", Then the appointments of both clinics are shown, grouped by clinic, in time order. (source: FR-023)
- [AC-S-005-US5-2] Given an appointment, When it is shown, Then it has time, patient name, treatment and status, and no change action is offered. (source: FR-023)
- [AC-S-005-US5-3] Given a dentist signed in, When they try to change an appointment or to read another dentist's day, Then the request is refused. (source: FR-023, FR-004)
- [AC-S-005-US5-4] Given a phone-sized screen, When the dentist opens "my day", Then it is readable without sideways scrolling. (source: FR-023)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 005-T045 | Integration tests for `GET /api/dentist/my-day`: two clinics grouped, only own a | 3.0 | qa-automation, postgres | no | - |
| 005-T046 | Implement the dentist day read model (own appointments for the date grouped by c | 3.0 | backend-python, postgres | yes | 005-T011 |
| 005-T047 | Implement `GET /api/dentist/my-day?date=` (dentist only) in `app/modules/recepti | 2.0 | backend-python, api-design | yes | 005-T046 |
| 005-T048 | Add the API client `getMyDay(date)` in `src/features/dentist/api/myDay.ts` (repo | 1.0 | frontend-react | yes | - |
| 005-T049 | Build the read-only mobile-first "my day" screen grouped by clinic with day navi | 5.0 | frontend-react, frontend-css | no | 005-T048 |
| 005-T050 | Make `/my-day` the landing route of the dentist role in `src/app/routes.tsx` (re | 1.0 | frontend-react | no | 005-T019, 005-T049 |
| 005-T051 | Component test for "my day" (two clinics, no actions, narrow screen layout) in ` | 3.0 | qa-automation, frontend-react | yes | - |

### S-SETUP-005 Reception day view, check-in, no-shows and dentist day (MOD-05): Setup — P1/must · 1 SP (low, llm)

Depends on: - · Sources: E-005, FR-019, FR-020, FR-021, FR-022, FR-023, FR-024

- [AC-S-SETUP-005-1] Given the setup tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 005-T001 | Create the cmp-reception package with empty `app/modules/reception/__init__.py`, | 3.0 | backend-python | yes | - |
| 005-T002 | Create the feature folders `src/features/reception/api/` and `src/features/denti | 3.0 | frontend-react | yes | - |

### S-FOUND-005 Reception day view, check-in, no-shows and dentist day (MOD-05): Foundational prerequisites — P1/must · 5 SP (low, llm)

Depends on: S-SETUP-005, S-FOUND-003 · Sources: E-005, FR-021, FR-022, FR-024

- [AC-S-FOUND-005-1] Given the foundational prerequisites tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 005-T003 | Write unit tests for IST day boundaries and the injectable clock (start and end  | 2.5 | qa-automation, backend-python | yes | - |
| 005-T004 | Implement `ist_date_of`, `end_of_ist_day` and an injectable `now()` clock with z | 2.5 | backend-python | yes | - |
| 005-T005 | Write unit tests for the status transition table and the no-show window (14 minu | 3.5 | qa-automation, backend-python | yes | - |
| 005-T006 | Implement the five statuses `booked`, `arrived`, `no_show`, `cancelled_by_patien | 3.5 | backend-python | yes | 005-T004 |
| 005-T007 | Add an Alembic migration `migrations/versions/005_reception_status_and_index.py` | 3.0 | postgres, backend-python | no | 005-T006 |
| 005-T008 | Write integration tests for `change_status`: the conditional update succeeds onc | 4.0 | qa-automation, postgres | yes | - |
| 005-T009 | Implement `change_status(appointment_id, expected_from, to_status, actor, reason | 6.0 | backend-python, postgres | no | 005-T006, 005-T007 |
| 005-T010 | Write unit tests for the access helpers: a receptionist gets the clinic id from  | 2.0 | qa-automation, auth-security | no | - |
| 005-T011 | Implement `require_receptionist()` and `require_dentist()` on top of the cmp-ide | 3.0 | backend-python, auth-security | no | 005-T010 |

### S-POLISH-005 Reception day view, check-in, no-shows and dentist day (MOD-05): Polish & cross-cutting concerns — P1/must · 3 SP (low, llm)

Depends on: S-005-US1, S-005-US2, S-005-US3, S-005-US4, S-005-US5 · Sources: E-005, FR-019, FR-020, FR-023, FR-024

- [AC-S-POLISH-005-1] Given the polish & cross-cutting concerns tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 005-T052 | Role and clinic matrix test: every endpoint of this feature as receptionist of e | 4.5 | qa-automation, auth-security | no | - |
| 005-T053 | Add OpenTelemetry spans, a counter of status changes by status and structured lo | 3.0 | backend-python, observability | no | - |
| 005-T054 | Merge the paths and schemas of `specs/005-reception-day/contracts/reception-day. | 2.0 | api-design, backend-python | yes | 005-T039, 005-T047 |
| 005-T055 | Performance test for the day view with 6 columns of 16 appointments (payload abo | 3.5 | qa-automation, postgres | yes | - |
| 005-T056 | Write the paper-diary dry-run guide (typing a week of future appointments per cl | 2.5 | docs | yes | - |
| 005-T057 | Run the scenarios of `specs/005-reception-day/quickstart.md` against staging and | 2.5 | qa-automation, devops-ci | no | 005-T043, 005-T050, 005-T054 |

## E-006 Confirmations, reminders and opt-out via SMS and WhatsApp

Channel choice, booking confirmation, 24-hour reminder with quiet hours, skip rules, reminder content with link, STOP opt-out, DLT/template compliance. RELEASE 1 (DL-1, due 2027-02-22, hard). PRD ids: FR-013, FR-014, FR-027, FR-028, FR-030, FR-031.

### S-006-US1 Choose SMS or WhatsApp when booking — P1/must · 3 SP (low, llm)

As a patient booking an appointment, I want to choose SMS or WhatsApp on the confirm screen and have my last choice pre-selected next time so that I receive messages about my appointment in the channel I actually use.
Depends on: S-FOUND-006, S-003-US2 · Sources: FR-013

- [AC-S-006-US1-1] Given a patient who has never booked, When they reach the confirm screen, Then SMS is pre-selected and WhatsApp can be chosen instead
- [AC-S-006-US1-2] Given a patient who chose WhatsApp on their last booking, When they reach the confirm screen of a new booking, Then WhatsApp is pre-selected
- [AC-S-006-US1-3] Given a patient who confirms a booking with a channel, When the booking is saved, Then the appointment records that channel and it becomes the patient's remembered choice
- [AC-S-006-US1-4] Given a patient who chose WhatsApp for an appointment, When messages about it are sent, Then they go only to WhatsApp, never to both channels

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 006-T013 | Write integration tests for `GET /api/me/preferences` (default `sms`), booking w | 3.0 | qa-automation, api-design | yes | - |
| 006-T014 | Implement `GET /api/me/preferences` in `src/clinic_api/identity/api.py` returnin | 2.0 | backend-python, api-design | yes | - |
| 006-T015 | Add required `channel` (`sms/whatsapp`) to the booking request and appointment,  | 4.0 | backend-python, api-design | no | 006-T010, 006-T014 |
| 006-T016 | Write component tests for the channel choice (default SMS, pre-selects the retur | 2.0 | frontend-react, qa-automation | yes | - |
| 006-T017 | Implement the `ChannelChoice` radio group in `src/features/booking/ChannelChoice | 4.0 | frontend-react, frontend-css | yes | 006-T015 |
| 006-T018 | Add `ChannelChoice` to the confirm screen and send `channel` with the booking re | 3.0 | frontend-react | yes | 006-T017 |

### S-006-US2 Immediate booking confirmation — P1/must · 8 SP (low, llm)

As a patient who has just booked, I want to get a confirmation in my chosen channel with clinic, dentist, treatment, date, time and a link so that I know my booking exists and can open it.
Depends on: S-006-US1 · Sources: FR-014, NFR-008, NFR-011

- [AC-S-006-US2-1] Given a patient confirms a booking with SMS, When the booking is saved, Then a confirmation SMS is sent within 1 minute giving clinic, dentist, treatment, date, time in IST and a link to the appointment
- [AC-S-006-US2-2] Given a patient confirms a booking with WhatsApp, When the booking is saved, Then the confirmation is sent as an approved WhatsApp template message with the same details
- [AC-S-006-US2-3] Given the booking fails (for example the slot was just taken), When the patient sees the "slot taken" answer, Then no confirmation is sent
- [AC-S-006-US2-4] Given the provider is down when the booking is saved, When the patient confirms, Then the booking still succeeds and the confirmation stays queued and is retried
- [AC-S-006-US2-5] Given a patient who has switched reminders off, When they book, Then the confirmation is still sent

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 006-T019 | Write unit tests for confirmation rendering (five details, IST, English, only te | 3.0 | qa-automation, backend-python | yes | - |
| 006-T020 | Write integration tests that the confirmation row is committed with the booking, | 5.0 | qa-automation, postgres | no | - |
| 006-T021 | Implement the SMS adapter (send through registered template id, variable mapping | 5.0 | messaging, backend-python | no | - |
| 006-T022 | Implement the WhatsApp adapter (approved template send, variable mapping, error  | 5.0 | messaging, backend-python | no | - |
| 006-T023 | Write adapter tests against the fake provider server (request shape holds only t | 4.0 | qa-automation, messaging | yes | - |
| 006-T024 | Add the `confirmation` template variables and rendering to `src/clinic_api/messa | 4.0 | backend-python | yes | 006-T009 |
| 006-T025 | Implement `MessagingService.on_booked` creating the confirmation row (due now, c | 4.0 | backend-python, postgres | yes | 006-T012, 006-T024 |
| 006-T026 | Implement the dispatcher core in `src/clinic_api/messaging/dispatcher.py`: claim | 9.0 | backend-python, postgres | no | 006-T008, 006-T021, 006-T022, 006-T025 |
| 006-T027 | Start the dispatcher every 30 s in the application lifespan in `src/clinic_api/m | 2.0 | backend-python | yes | 006-T026 |
| 006-T028 | Call `MessagingService.on_booked` inside the booking transaction in `src/clinic_ | 3.0 | backend-python | no | 006-T015, 006-T025 |
| 006-T029 | Write an integration test that two dispatchers claim the same due rows once only | 4.0 | qa-automation, postgres | yes | - |

### S-006-US3 Reminder 24 hours before, with quiet hours — P1/must · 3 SP (low, llm)

As a patient with an upcoming appointment, I want to get one reminder 24 hours before, not in the night, with a link to reschedule or cancel so that I remember the appointment or change it in time, which reduces no-shows.
Depends on: S-006-US2 · Sources: FR-027, FR-030, NFR-005, NFR-008

- [AC-S-006-US3-1] Given an appointment tomorrow at 14:00 booked a week ago, When the due time (today 14:00) arrives, Then the reminder is sent within 15 minutes in the chosen channel with clinic, dentist, date, time (IST) and a link to reschedule or cancel
- [AC-S-006-US3-2] Given an appointment whose reminder is due at 22:30 IST, When the booking is saved, Then the reminder is scheduled for 20:00 IST the same evening
- [AC-S-006-US3-3] Given an appointment whose reminder is due at 03:00 IST, When the booking is saved, Then the reminder is scheduled for 20:00 IST the evening before the due time
- [AC-S-006-US3-4] Given a reminder whose adjusted 20:00 time has already passed when the booking is made, When the booking is saved, Then the reminder goes at once if it is outside 21:00-08:00 IST, otherwise at 08:00 IST
- [AC-S-006-US3-5] Given an appointment booked less than 24 hours before it starts, When the booking is saved, Then no reminder is created and only the confirmation is sent
- [AC-S-006-US3-6] Given the reminder link, When the patient opens it, Then it opens that appointment where they can reschedule or cancel

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 006-T030 | Write table-driven unit tests for the quiet-hours and 24-hour rule (due 14:00; 2 | 4.0 | qa-automation, backend-python | yes | - |
| 006-T031 | Implement the pure function `plan_reminder(start_utc, booked_at_utc, settings)`  | 4.0 | backend-python | yes | - |
| 006-T032 | Add the `reminder` template (clinic, dentist, date, time, link to reschedule or  | 2.0 | backend-python, messaging | yes | 006-T031 |
| 006-T033 | Extend `MessagingService.on_booked` in `src/clinic_api/messaging/service.py` to  | 3.0 | backend-python | yes | 006-T025, 006-T031, 006-T032 |
| 006-T034 | Write integration tests that the reminder is created with the booking, sent with | 5.0 | qa-automation, postgres | no | - |

### S-006-US4 Reminders follow changes; change notices — P1/must · 3 SP (low, llm)

As a patient who cancels or reschedules an appointment, I want no reminder for a cancelled appointment, one reminder for the new time after a reschedule, and a notice telling me what changed so that I am not confused by wrong reminders and know my change was saved.
Depends on: S-006-US3, S-004-US2, S-004-US3 · Sources: FR-028, NFR-005, FR-018

- [AC-S-006-US4-1] Given a booked appointment with a pending reminder, When the patient or reception cancels it, Then the pending reminder is cancelled in the same change and never sent
- [AC-S-006-US4-2] Given a reminder already claimed for sending, When the appointment is found cancelled at the last re-check, Then the reminder is not sent
- [AC-S-006-US4-3] Given a booked appointment with a pending reminder, When it is rescheduled, Then the old reminder is cancelled and exactly one new reminder is scheduled for the new time (quiet-hours rule and less-than-24-hours rule apply)
- [AC-S-006-US4-4] Given a cancel or reschedule, When it is saved, Then the patient receives a notice in the chosen channel with the clinic, dentist, date and time (new date and time for a reschedule), even if reminders are switched off
- [AC-S-006-US4-5] Given a reschedule to a time less than 24 hours ahead, When it is saved, Then no reminder is created and only the change notice is sent

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 006-T035 | Write integration tests for cancel, reschedule (including to less than 24 h ahea | 5.0 | qa-automation, postgres | no | - |
| 006-T036 | Add the `change_notice` templates (cancelled; rescheduled with new date and time | 2.0 | backend-python, messaging | yes | - |
| 006-T037 | Implement `MessagingService.on_cancelled` and `on_rescheduled` (cancel pending r | 6.0 | backend-python, postgres | no | 006-T033, 006-T036 |
| 006-T038 | Add the send-time re-check to `src/clinic_api/messaging/dispatcher.py`: before s | 3.0 | backend-python | yes | 006-T026 |
| 006-T039 | Call `on_cancelled` and `on_rescheduled` inside the patient and reception cancel | 2.0 | backend-python | no | 006-T037 |

### S-006-US5 Stop reminders by replying STOP or through reception — P1/must · 5 SP (low, llm)

As a patient who does not want reminders, I want to stop them by replying STOP or by asking reception, while still getting confirmations and change notices so that I stay in control of the messages I get.
Depends on: S-006-US4 · Sources: FR-031, NFR-011

- [AC-S-006-US5-1] Given a patient with pending reminders, When the provider forwards their STOP reply, Then the patient's reminders are switched off at once and their pending reminders are cancelled (honoured well within 1 hour)
- [AC-S-006-US5-2] Given reminders switched off, When the patient books or changes an appointment, Then the confirmation or change notice is still sent and no reminder is created
- [AC-S-006-US5-3] Given a receptionist on the patient's record screen, When they switch reminders off, Then the same effect applies as for STOP and the change is recorded with who did it and when
- [AC-S-006-US5-4] Given a receptionist, When they switch reminders back on at the patient's request, Then future bookings get reminders again
- [AC-S-006-US5-5] Given an incoming STOP webhook without a valid signature or from an unknown sender, When it is received, Then it is rejected and nothing changes
- [AC-S-006-US5-6] Given the same STOP webhook delivered twice, When it is processed, Then the result is the same as once

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 006-T040 | Write tests for STOP parsing (case and spacing), signed and unsigned webhook cal | 5.0 | qa-automation, auth-security | no | - |
| 006-T041 | Implement constant-time HMAC-SHA256 verification of the raw body in `src/clinic_ | 2.0 | auth-security, backend-python | no | - |
| 006-T042 | Implement inbound reply parsing (`STOP` after trim and upper-case) in `src/clini | 2.0 | messaging, backend-python | yes | 006-T021 |
| 006-T043 | Implement `MessagingService.set_reminders(account, enabled, source, actor)` sett | 4.0 | backend-python, postgres | yes | 006-T037 |
| 006-T044 | Implement `POST /api/webhooks/sms` for inbound STOP (verify signature, 401 on fa | 5.0 | api-design, auth-security | no | 006-T041, 006-T042, 006-T043 |
| 006-T045 | Implement `PUT /api/patient-accounts/{accountId}/reminders` for receptionist and | 5.0 | api-design, auth-security | no | 006-T043 |
| 006-T046 | Write a component test for the reminders toggle (shows state, source and time; c | 2.0 | frontend-react, qa-automation | yes | - |
| 006-T047 | Implement `ReminderToggle` in `src/features/reception/ReminderToggle.tsx` with t | 5.0 | frontend-react, frontend-css | no | 006-T045 |

### S-006-US6 Sign-in codes sent by SMS — P1/must · 2 SP (low, llm)

As a patient signing in, I want to receive my sign-in code by SMS and get a clear answer if it cannot be sent so that I can sign in and book.
Depends on: S-006-US2 · Sources: NFR-011, NFR-008, FR-002

- [AC-S-006-US6-1] Given a valid phone number and sign-in allowed, When the patient asks for a code, Then one SMS with the code is sent through the registered code template before the request returns
- [AC-S-006-US6-2] Given the provider is slow or failing, When the patient asks for a code, Then the request ends within the provider timeout with a clear "could not send, try again" answer and the failure is recorded without the code or the phone number in logs
- [AC-S-006-US6-3] Given a sign-in code message, When it is stored, Then the code itself is not kept in readable form after sending

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 006-T048 | Write tests for `send_code` (one SMS via the code template, success and failure  | 3.0 | qa-automation, backend-python | yes | - |
| 006-T049 | Add the `code` template to `src/clinic_api/messaging/catalogue.py` and implement | 5.0 | backend-python, messaging | no | 006-T012, 006-T021 |
| 006-T050 | Call `send_code` from the sign-in code request and map failure to the "could not | 4.0 | backend-python, auth-security | no | 006-T049 |

### S-006-US7 Reliable and compliant delivery operations — P1/must · 8 SP (low, llm)

As a member of the operations team running the booking system, I want retries, a circuit breaker, delivery receipts, a lag alert, a nightly repair job and 90-day retention so that due messages go out on time (99% within 15 minutes), only through approved templates, and stuck ones are found before patients notice.
Depends on: S-006-US5 · Sources: NFR-005, NFR-011, NFR-008, FR-027

- [AC-S-006-US7-1] Given due messages, When the dispatcher runs every 30 seconds, Then each due message is claimed by exactly one worker, sent once, and marked sent with the provider message id
- [AC-S-006-US7-2] Given a provider error, When a send fails, Then it is retried up to 3 attempts in all, with waits of 5 s and 30 s, and a provider call never lasts more than 5 s
- [AC-S-006-US7-3] Given 5 provider failures within 1 minute, When the next message is due, Then sending to that provider pauses (message stays queued) and resumes after a probe succeeds
- [AC-S-006-US7-4] Given a delivery receipt (SMS or WhatsApp) with a valid signature, When it arrives, Then the message status is updated; the same receipt twice, or one for an unknown message id, changes nothing
- [AC-S-006-US7-5] Given a due message still unsent 10 minutes after its scheduled time, When the monitor runs, Then an alert is raised
- [AC-S-006-US7-6] Given the nightly check, When it finds a due reminder without a message row, or a stuck row for a booked appointment, Then it creates or requeues it and logs the repair; it never sends for a cancelled appointment
- [AC-S-006-US7-7] Given any outgoing message, When it is built, Then it uses the template id from configuration for that kind and channel and sends only clinic, dentist, date, time and link as template values
- [AC-S-006-US7-8] Given message rows older than 90 days, When the retention job runs, Then they are deleted

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 006-T051 | Write unit tests for the circuit breaker (opens after 5 failures in 60 s, half-o | 4.0 | qa-automation, backend-python | yes | - |
| 006-T052 | Implement the per-provider circuit breaker in `src/clinic_api/channel_adapters/b | 4.0 | backend-python | yes | - |
| 006-T053 | Add retry with backoff 5 s and 30 s, attempt counting, lease expiry handling, br | 8.0 | backend-python, postgres | no | 006-T038, 006-T052 |
| 006-T054 | Write tests for receipts: valid SMS and WhatsApp receipts update status, repeats | 5.0 | qa-automation, auth-security | no | - |
| 006-T055 | Implement the WhatsApp receipt parser in `src/clinic_api/channel_adapters/whatsa | 4.0 | messaging, backend-python | yes | 006-T042 |
| 006-T056 | Implement receipt handling (idempotent on `provider_message_id`, forward-only st | 6.0 | api-design, auth-security | no | 006-T044, 006-T055 |
| 006-T057 | Record the metrics `messaging.reminder_lag_seconds`, `messaging.send_total{resul | 4.0 | observability, backend-python | no | 006-T053 |
| 006-T058 | Write tests for the nightly job (creates a missing reminder for a booked, opted- | 5.0 | qa-automation, postgres | no | - |
| 006-T059 | Implement the nightly reconciliation and 90-day retention job (JOB-005) with a P | 8.0 | backend-python, postgres | no | 006-T037, 006-T053 |

### S-SETUP-006 Confirmations, reminders and opt-out via SMS and WhatsApp: Setup — P1/must · 2 SP (low, llm)

Depends on: - · Sources: E-006, NFR-011, NFR-005

- [AC-S-SETUP-006-1] Given the messaging and channel_adapters packages, When the settings module is loaded, Then the template map, quiet hours, provider switches (default sandbox) and webhook secrets are available from configuration and environment
- [AC-S-SETUP-006-2] Given the test fixtures, When a test uses the frozen IST clock and the fake provider server, Then latency and failures can be controlled and signed webhooks can be produced
- [AC-S-SETUP-006-3] Given docs/messaging-providers.md, When the clinic reads it, Then the DLT sender ID, templates, WhatsApp templates, variables, test accounts and owners are listed

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 006-T001 | Create the packages `src/clinic_api/messaging/` and `src/clinic_api/channel_adap | 3.0 | backend-python | no | - |
| 006-T002 | Create test fixtures in `tests/fixtures/messaging.py`: frozen IST clock, fake pr | 5.0 | qa-automation, backend-python | no | - |
| 006-T003 | Write the provider onboarding checklist `docs/messaging-providers.md` listing DL | 3.0 | docs, messaging | no | - |

### S-FOUND-006 Confirmations, reminders and opt-out via SMS and WhatsApp: Foundational prerequisites — P1/must · 5 SP (low, llm)

Depends on: S-SETUP-006, S-FOUND-001 · Sources: E-006, NFR-011, NFR-005, NFR-008, FR-013

- [AC-S-FOUND-006-1] Given the migration, When it is applied to an empty database, Then table message, the account preference columns and appointment.channel exist with the constraints of data-model.md
- [AC-S-FOUND-006-2] Given a (kind, appointment, version) key, When a message row is created twice, Then only one row exists
- [AC-S-FOUND-006-3] Given the registry and sandbox adapters, When provider switches are 'sandbox', Then the adapter per channel is returned and records the sent messages
- [AC-S-FOUND-006-4] Given a (kind, channel) without a template id, When the app starts in production, Then startup fails

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 006-T004 | Create forward-only Alembic migration `alembic/versions/0006_messaging.py` for t | 5.0 | postgres, data-modeling | no | - |
| 006-T005 | Implement the Message ORM model and `MessageKind`, `Channel`, `MessageStatus` en | 3.0 | backend-python, data-modeling | yes | 006-T004 |
| 006-T006 | Define `ChannelPort`, `OutboundMessage`, `SendResult` (accepted id or error clas | 2.0 | backend-python, api-design | yes | 006-T005 |
| 006-T007 | Implement sandbox SMS and WhatsApp adapters (fixed latency, switchable failures, | 3.0 | backend-python, messaging | yes | 006-T006 |
| 006-T008 | Implement provider selection by configuration switch in `src/clinic_api/channel_ | 2.0 | backend-python | yes | 006-T006, 006-T007 |
| 006-T009 | Implement the single English message catalogue with IST date/time formatting (UT | 4.0 | backend-python | yes | - |
| 006-T010 | Add `preferred_channel` and the reminders opt-out fields to the patient account  | 3.0 | backend-python, postgres | yes | 006-T004 |
| 006-T011 | Add a log filter that removes phone numbers, names and rendered text from messag | 2.0 | backend-python, observability | yes | - |
| 006-T012 | Implement idempotent message row creation (`INSERT ... ON CONFLICT DO NOTHING` o | 3.0 | backend-python, postgres | yes | 006-T005, 006-T009 |

### S-POLISH-006 Confirmations, reminders and opt-out via SMS and WhatsApp: Polish & cross-cutting concerns — P1/must · 3 SP (low, llm)

Depends on: S-006-US6, S-006-US7 · Sources: E-006, NFR-005, NFR-011, NFR-008

- [AC-S-POLISH-006-1] Given the OpenAPI file, When contract tests run, Then the preferences, booking channel, reception reminders and two webhook operations match the implementation
- [AC-S-POLISH-006-2] Given 1,000 due reminders and a slow sandbox provider, When the load test runs, Then 99% are sent within 15 minutes of scheduled_at
- [AC-S-POLISH-006-3] Given any messaging log line, error body or metric label, When the privacy test runs, Then none contains a phone number, name or rendered text
- [AC-S-POLISH-006-4] Given the quickstart scenarios, When they are run on staging with sandbox providers, Then results are recorded in quickstart.md

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 006-T060 | Add the new operations (preferences, booking `channel`, reception reminders, two | 4.0 | api-design, qa-automation | yes | - |
| 006-T061 | Write a test that fails if any messaging log line, error body or metric label co | 2.0 | qa-automation, backend-python | yes | 006-T011 |
| 006-T062 | Write a load test with 1,000 due reminders and a slow sandbox provider that chec | 6.0 | qa-automation, backend-python | no | 006-T053, 006-T057 |
| 006-T063 | Run the quickstart.md scenarios against staging with sandbox providers and recor | 4.0 | qa-automation, docs | no | 006-T039, 006-T047, 006-T050, 006-T059 |
| 006-T064 | Review the DLT and WhatsApp template texts in `src/clinic_api/messaging/catalogu | 2.0 | docs, messaging | no | 006-T049 |

## E-007 Family members on a patient account

Patient adds up to 5 family members and books for any of them. RELEASE 2 (DL-2, due 2027-03-19, not hard). PRD ids: FR-006.

### S-007-US1 Add and manage family members — P2/should · 5 SP (low, llm)

As a patient (P-01) who books for relatives from one phone number, I want to add, correct and remove up to 5 family members on my account so that I can later book visits for them without a separate sign-in.
Depends on: S-FOUND-007, S-001-US1 · Sources: FR-006, SA-001

- [AC-S-007-US1-1] Given a signed-in patient with fewer than 5 family members, When they add a family member with a valid name and a valid birth year, Then the person appears in the family list and can be chosen in later screens. (source: FR-006)
- [AC-S-007-US1-2] Given a patient who already has 5 family members, When they try to add another, Then the system refuses, explains that 5 is the limit, and the list is unchanged. (source: FR-006, SA-001)
- [AC-S-007-US1-3] Given a patient adding a family member, When the name is empty, or the birth year is not a four-digit year, is in the future, or is more than 120 years ago, Then the system shows what is wrong next to the field and saves nothing. (source: FR-006)
- [AC-S-007-US1-4] Given a patient with a family member, When they correct the name or birth year, Then the change is saved and shown in the list and on that person's appointments. (source: FR-006)
- [AC-S-007-US1-5] Given a family member with no upcoming booked appointment, When the patient removes them, Then they leave the list, can no longer be chosen for new bookings, and the patient can add another family member in their place. (source: FR-006)
- [AC-S-007-US1-6] Given a family member with an upcoming booked appointment, When the patient tries to remove them, Then the system refuses and says to cancel those appointments first. (source: FR-006; Assumed, open question Q2)
- [AC-S-007-US1-7] Given the family feature is switched off, When any patient opens their account, Then no family screens or links are visible and the family operations are refused. (source: FR-006)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 007-T008 | [repo: clinic-api] Unit tests for limit of 5 (including two simultaneous adds),  | 3.0 | qa-automation, backend-python | yes | - |
| 007-T009 | [repo: clinic-api] Contract tests for `GET /api/patient/people`, `POST /api/pati | 2.0 | qa-automation, api-design | yes | 007-T007 |
| 007-T010 | [repo: clinic-web] Component tests for the family list, the add form with field  | 2.5 | frontend-react, qa-automation | yes | - |
| 007-T011 | [repo: clinic-api] Implement add, edit, remove and list in `app/modules/identity | 5.0 | backend-python, postgres | no | 007-T003, 007-T004, 007-T008 |
| 007-T012 | [repo: clinic-api] Implement the endpoints of the contract in `app/modules/ident | 3.0 | backend-python, api-design | no | 007-T005, 007-T011 |
| 007-T013 | [repo: clinic-web] Add the API client for the family endpoints in `src/features/ | 1.5 | frontend-react | yes | - |
| 007-T014 | [repo: clinic-web] Build the add/edit form with name and birth year and inline f | 3.0 | frontend-react, frontend-css | yes | - |
| 007-T015 | [repo: clinic-web] Build the family page (list with holder first, add, edit, rem | 4.0 | frontend-react, frontend-css | no | 007-T013, 007-T014 |
| 007-T016 | [repo: clinic-web] Add the "Family members" link on the account screen in `src/f | 1.5 | frontend-react | yes | 007-T006, 007-T015 |

### S-007-US2 Choose who the visit is for when booking — P2/should · 3 SP (low, llm)

As a patient (P-01) with family members on my account, I want to choose who the visit is for when I book so that the appointment is saved and shown under the right person.
Depends on: S-FOUND-007, S-003-US2 · Sources: FR-006, FR-004

- [AC-S-007-US2-1] Given a signed-in patient with at least one family member, When they reach the "who and what" step, Then they see themselves and each family member as choices, with "myself" pre-selected. (source: FR-006)
- [AC-S-007-US2-2] Given a patient who chose a family member, When they confirm the booking, Then the appointment is saved for that person and the booked screen and the appointment page name that person. (source: FR-006, REQ-003)
- [AC-S-007-US2-3] Given a patient who has no family members, When they book, Then the visit is for themselves and no "who" choice is asked. (source: FR-006)
- [AC-S-007-US2-4] Given a request to book for a person who is not on the patient's own account (for example a changed id), When the booking is submitted, Then the system refuses it and no appointment is created. (source: FR-006, FR-004)
- [AC-S-007-US2-5] Given a family member who was removed, When the patient books, Then that person is not offered and a booking for them is refused. (source: FR-006)
- [AC-S-007-US2-6] Given a family member who is blocked online after repeat no-shows, When the patient chooses them, Then the block message from the no-show rules applies to that person only, not to the account holder or other members. (source: FR-006; PD-007 handled by feature 006)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 007-T017 | [repo: clinic-api] Unit tests: booking with `patient_id` of a family member, def | 3.0 | qa-automation, backend-python | yes | - |
| 007-T018 | [repo: clinic-web] Component tests: choices "myself" plus each active family mem | 2.0 | frontend-react, qa-automation | yes | - |
| 007-T019 | [repo: clinic-api] Accept an optional person id in the booking flow in `app/modu | 4.0 | backend-python, auth-security | no | 007-T004, 007-T017 |
| 007-T020 | [repo: clinic-api] Add `patient_id` to the booking request schema and map `perso | 1.5 | backend-python, api-design | yes | 007-T007, 007-T019 |
| 007-T021 | [repo: clinic-web] Add the "who is this for" choice to the "who and what" step i | 4.0 | frontend-react | yes | 007-T013, 007-T018, 007-T020 |
| 007-T022 | [repo: clinic-web] Show the name of the person the visit is for on the booked sc | 1.5 | frontend-react | yes | 007-T021 |

### S-007-US3 See family members' appointments, and only those — P2/should · 3 SP (low, llm)

As a patient (P-01) who books for relatives, I want to see my own and my family members' appointments with the person's name, and nobody else's so that I can trust and manage the bookings I made while others cannot see my family's data.
Depends on: S-FOUND-007, S-004-US1 · Sources: FR-006, FR-015, FR-004, FR-016, FR-017

- [AC-S-007-US3-1] Given an account with appointments for the holder and for two family members, When the patient opens "My appointments", Then all of them are listed with status and the name of the person each is for. (source: FR-015, FR-006)
- [AC-S-007-US3-2] Given two different accounts, When one patient opens an appointment of the other account, by list or by direct link, Then the system refuses and reveals nothing about it. (source: FR-004, FR-006)
- [AC-S-007-US3-3] Given a family member who was removed but had past appointments, When the patient opens the list, Then the past appointments are still shown with that person's name. (source: FR-006; Assumed, open question Q2)
- [AC-S-007-US3-4] Given an account with family appointments, When the patient reschedules or cancels one of them within the usual 4-hour rule, Then it works exactly as for their own appointments. (source: FR-006, FR-016, FR-017)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 007-T023 | [repo: clinic-api] Integration tests per operation (list, view, reschedule, canc | 4.0 | qa-automation, auth-security | no | - |
| 007-T024 | [repo: clinic-web] Component tests that each list row shows the person's name, i | 1.5 | frontend-react, qa-automation | yes | - |
| 007-T025 | [repo: clinic-api] List appointments of all persons of the signed-in account (ho | 3.0 | backend-python, postgres | no | 007-T004, 007-T023 |
| 007-T026 | [repo: clinic-api] Add `app/modules/booking/appointment_access.py` that applies  | 3.0 | backend-python, auth-security | no | 007-T004, 007-T020, 007-T023 |
| 007-T027 | [repo: clinic-web] Show the person's name on each row of the list in `src/featur | 1.5 | frontend-react | yes | 007-T024, 007-T025 |
| 007-T028 | [repo: clinic-web] Show the person's name on the appointment page in `src/featur | 1.0 | frontend-react | yes | 007-T027 |

### S-007-US4 Erase family member data and keep it out of logs — P2/should · 2 SP (low, llm)

As a patient (P-01) asking for my data to be deleted, I want my family members' names and birth years erased with my account and never written to logs so that the clinic keeps its privacy promise (DPDP Act) for everyone I booked for.
Depends on: S-FOUND-007 · Sources: FR-006, NFR-007

- [AC-S-007-US4-1] Given an account with family members, When the practice manager runs erasure for that account on request, Then every family member's name and birth year are removed or anonymised, and their appointments remain without a personal link. (source: NFR-007, FR-006)
- [AC-S-007-US4-2] Given a family member added, edited, removed or booked for, When the logs of that action are inspected, Then they contain ids and a correlation id but no name or birth year. (source: NFR-007, FR-006)
- [AC-S-007-US4-3] Given an account erased on request, When the patient signs in again with the same phone number, Then it is treated as a new account with no family members. (source: NFR-007)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 007-T029 | [repo: clinic-api] Unit tests: erasure clears name and birth year of the holder  | 2.5 | qa-automation, backend-python | yes | - |
| 007-T030 | [repo: clinic-api] Add a log-capture fixture in `tests/conftest.py` and a test i | 3.0 | qa-automation, backend-python | yes | - |
| 007-T031 | [repo: clinic-api] Extend the erasure operation in `app/modules/identity/erasure | 3.0 | backend-python, postgres | no | 007-T029 |
| 007-T032 | [repo: clinic-api] Make the log lines in `app/modules/identity/family_service.py | 2.0 | backend-python | yes | 007-T012, 007-T030 |
| 007-T033 | [repo: clinic-web] Make sure the family form and client do not write names or bi | 1.0 | frontend-react | yes | 007-T013, 007-T014 |

### S-SETUP-007 Family members on a patient account: Setup — P2/should · 1 SP (low, llm)

Depends on: - · Sources: E-007, FR-006

- [AC-S-SETUP-007-1] Given the setup tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 007-T001 | [repo: clinic-api, clinic-web] Confirm the real file names of the patient models | 1.5 | docs | no | - |

### S-FOUND-007 Family members on a patient account: Foundational prerequisites — P2/should · 2 SP (low, llm)

Depends on: S-SETUP-007 · Sources: E-007, FR-006

- [AC-S-FOUND-007-1] Given the foundational prerequisites tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 007-T002 | [repo: clinic-api] Add the setting `FAMILY_MEMBERS_ENABLED` (boolean, default fa | 0.5 | backend-python | yes | - |
| 007-T003 | [repo: clinic-api] Write the forward-only Alembic migration `migrations/versions | 3.0 | postgres, data-modeling | no | - |
| 007-T004 | [repo: clinic-api] Implement `person_belongs_to_account(account_id, patient_id,  | 2.0 | auth-security, backend-python | no | - |
| 007-T005 | [repo: clinic-api] Return `features.family_members` (from T002) in the signed-in | 1.0 | backend-python, api-design | no | 007-T002 |
| 007-T006 | [repo: clinic-web] Read `features.family_members` from the session response and  | 1.0 | frontend-react | yes | 007-T005 |
| 007-T007 | [repo: clinic-api] Merge the additions of `specs/007-family-members/contracts/fa | 2.0 | api-design | yes | - |

### S-POLISH-007 Family members on a patient account: Polish & cross-cutting concerns — P2/should · 2 SP (low, llm)

Depends on: S-007-US1, S-007-US2, S-007-US3, S-007-US4 · Sources: E-007, FR-006, NFR-007

- [AC-S-POLISH-007-1] Given the polish & cross-cutting concerns tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 007-T034 | [repo: clinic-api] Document the endpoints, the flag, the limit of 5, the soft-re | 1.5 | docs | yes | - |
| 007-T035 | [repo: clinic-api] Add an end-to-end test with `FAMILY_MEMBERS_ENABLED=false`: n | 2.5 | qa-automation, backend-python | yes | - |
| 007-T036 | [repo: clinic-api] Record the explicit security review of the access-control cha | 2.0 | auth-security, docs | no | 007-T026, 007-T035 |
| 007-T037 | Run the six scenarios of `specs/007-family-members/quickstart.md` in dev with bo | 2.5 | qa-automation | no | 007-T036 |

## E-008 Repeat no-show block

Two no-shows in 6 months block online booking and rescheduling; reception sees and lifts the block. RELEASE 2 (DL-2, due 2027-03-19, not hard). PRD ids: FR-025, FR-026.

### S-008-US1 A repeat no-show patient cannot book or reschedule online — P2/should · 5 SP (low, llm)

As a patient (or the account holder booking for a family member), I want to be told clearly when online booking or rescheduling is not available for me and to get the clinic's phone number so that I know to phone the clinic, while my existing appointments stay as they are.
Depends on: S-FOUND-008, S-005-US2, S-003-US2 · Sources: FR-025

- [AC-S-008-US1-1] Given a patient has 2 no-shows within the last 6 months, When they reach the slot-choosing step of online booking for a clinic, Then the page says online booking is not available and shows that clinic's phone number, and no slot can be confirmed
- [AC-S-008-US1-2] Given a patient has 2 no-shows within the last 6 months and an upcoming appointment, When they try to reschedule it online, Then the change is refused, the page says to phone the clinic and shows the clinic's phone number, and the appointment keeps its original time and status
- [AC-S-008-US1-3] Given a blocked patient has other upcoming appointments, When they open their appointment list, Then all those appointments are still listed as booked and can still be cancelled online within the normal cancel rule
- [AC-S-008-US1-4] Given a family member has 2 no-shows and the account holder has none, When the account holder books for themselves, Then the booking succeeds; **and When** they book for the family member, **Then** it is refused with the phone-the-clinic message
- [AC-S-008-US1-5] Given a patient has only 1 no-show in the last 6 months, or has 2 no-shows of which one is older than 6 months, When they book or reschedule online, Then it succeeds
- [AC-S-008-US1-6] Given a patient is blocked, When a receptionist books or reschedules an appointment for them, Then it succeeds with no block check
- [AC-S-008-US1-7] Given a patient whose 2 counted no-shows were the only reason for the block, When the older of the two passes 6 months of age, Then the next online booking attempt succeeds without any staff action

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 008-T008 | Write integration tests in tests/noshow_policy/test_booking_block.py: blocked pe | 4.0 | qa-automation, backend-python | yes | - |
| 008-T009 | Replace the always-allow hook with `noshow_policy.is_blocked` on online book and | 4.0 | backend-python, api-design | no | 008-T007 |
| 008-T010 | Replace the always-allow hook with `noshow_policy.is_blocked` on online reschedu | 3.0 | backend-python, api-design | no | 008-T007 |
| 008-T011 | Add schemas in app/noshow_policy/schemas.py and read-only `GET /api/booking-elig | 4.0 | api-design, backend-python | no | 008-T007 |
| 008-T012 | Write contract test for `/api/booking-eligibility` and the 403 body against spec | 2.0 | qa-automation, api-design | yes | 008-T011 |
| 008-T013 | Create `BlockedNotice` component (online booking not available, clinic phone as  | 3.0 | frontend-react, frontend-css | yes | - |
| 008-T014 | Call the eligibility endpoint on entering the slot picker and show `BlockedNotic | 4.0 | frontend-react | yes | 008-T011, 008-T013, 008-T002 |
| 008-T015 | Handle the blocked refusal on the reschedule slot picker in src/pages/patient/Re | 3.0 | frontend-react | yes | 008-T013, 008-T002 |
| 008-T016 | Write web tests for the blocked flows (slot picker, confirm refusal, reschedule, | 3.0 | qa-automation, frontend-react | yes | 008-T014, 008-T015 |

### S-008-US2 Reception sees who is blocked — P2/should · 3 SP (low, llm)

As a receptionist, I want to see at a glance which patients are blocked from online booking, since when, and which no-shows count so that I can decide whether to lift the block when the patient phones.
Depends on: S-008-US1 · Sources: FR-026

- [AC-S-008-US2-1] Given a blocked patient has an appointment in the clinic's day view, When the receptionist opens the day view, Then that appointment shows a "Blocked from online booking" marker
- [AC-S-008-US2-2] Given a blocked patient, When the receptionist opens the appointment panel or finds the patient by phone number or name in patient search, Then the blocked state, the date the block started and the counted no-show dates are shown
- [AC-S-008-US2-3] Given a patient that is not blocked, When the receptionist views the same screens, Then no blocked marker is shown
- [AC-S-008-US2-4] Given a family member is blocked but the account holder is not, When the receptionist searches by the shared phone number, Then only the family member's entry shows the blocked marker
- [AC-S-008-US2-5] Given the feature is switched off for the release, When a receptionist opens any screen, Then no blocked marker or lift control appears

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 008-T017 | Write API tests in tests/noshow_policy/test_reception_view.py: `no_show_blocked` | 3.0 | qa-automation, backend-python | yes | - |
| 008-T018 | Add `GET /api/reception/patients/{patient_id}/no-show-block` returning block sta | 2.0 | api-design, backend-python | no | 008-T011 |
| 008-T019 | Add `no_show_blocked` to day-view appointment items in app/reception/day_view.py | 3.0 | backend-python, postgres | yes | 008-T007 |
| 008-T020 | Add `no_show_blocked` to patient search results in app/reception/patient_search. | 2.0 | backend-python | yes | 008-T007 |
| 008-T021 | Create `BlockedBadge` component ("Blocked from online booking") with test in src | 2.0 | frontend-react, frontend-css | yes | - |
| 008-T022 | Show `BlockedBadge` on day-view appointments and patient-search results in src/p | 3.0 | frontend-react | yes | 008-T019, 008-T020, 008-T021, 008-T002 |
| 008-T023 | Show block start date and counted no-show dates in the appointment panel in src/ | 3.0 | frontend-react | yes | 008-T018, 008-T021 |

### S-008-US3 Reception lifts a block and the count restarts — P2/should · 2 SP (low, llm)

As a receptionist, I want to lift a patient's block when the patient phones and the clinic agrees, so the count starts again from zero so that the patient can book and reschedule online straight away, and the lift is recorded with who and when.
Depends on: S-008-US2 · Sources: FR-026

- [AC-S-008-US3-1] Given a blocked patient, When the receptionist chooses "Lift block" and confirms, Then the blocked marker disappears and the lift is recorded with the receptionist's name and the time
- [AC-S-008-US3-2] Given a block has just been lifted, When the patient books or reschedules online, Then it succeeds
- [AC-S-008-US3-3] Given a block was lifted, When the patient then gets 1 new no-show, Then they are not blocked; **and When** they get a second new no-show, **Then** they are blocked again
- [AC-S-008-US3-4] Given a patient is not blocked, When a receptionist looks at the patient, Then no lift control is offered, and a direct lift request is refused
- [AC-S-008-US3-5] Given a user who is not a receptionist (a patient, a dentist), When they try to lift a block, Then it is refused

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 008-T024 | Write tests in tests/noshow_policy/test_lift.py: lift records staff id and time; | 3.0 | qa-automation, backend-python | yes | - |
| 008-T025 | Implement `lift(person_id, staff_id)` in app/noshow_policy/service.py as one con | 2.0 | backend-python, postgres | yes | 008-T007 |
| 008-T026 | Add `POST /api/reception/patients/{patient_id}/no-show-block/lift` in app/noshow | 2.0 | api-design, auth-security | no | 008-T018, 008-T025 |
| 008-T027 | Create `LiftBlockDialog` (confirm, then call lift, show result and error when al | 2.5 | frontend-react | yes | - |
| 008-T028 | Offer "Lift block" with `LiftBlockDialog` in the appointment panel and patient s | 2.5 | frontend-react | yes | 008-T023, 008-T026, 008-T027 |

### S-008-US4 The block follows no-show corrections — P2/should · 2 SP (low, llm)

As a receptionist, I want the patient's block to be recalculated the moment I mark or undo a no-show so that a second no-show blocks at once and a mistaken no-show undone the same day does not leave the patient wrongly blocked.
Depends on: S-FOUND-008 · Sources: FR-025, FR-026

- [AC-S-008-US4-1] Given a patient has 1 no-show in the last 6 months, When a receptionist marks a second no-show for them, Then the patient is blocked from online booking immediately
- [AC-S-008-US4-2] Given a patient was blocked by their second no-show, When the receptionist undoes that no-show the same day, Then the patient is no longer blocked
- [AC-S-008-US4-3] Given a patient was blocked, lifted, and then had one new no-show, When that no-show is undone, Then the count is zero and nothing else changes
- [AC-S-008-US4-4] Given a patient has no-shows for appointments of different family members, When a no-show is marked or undone, Then only the person the appointment was for is recounted

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 008-T029 | Write tests in tests/noshow_policy/test_status_events.py: marking the second no- | 4.0 | qa-automation, backend-python | yes | - |
| 008-T030 | Call `noshow_policy.recalculate(person_id)` inside the transaction of no-show ma | 3.0 | backend-python | no | 008-T007 |
| 008-T031 | Make recalculate safe under concurrent calls in app/noshow_policy/service.py: on | 5.0 | backend-python, postgres | no | 008-T030 |

### S-SETUP-008 Repeat no-show block: Setup — P2/should · 1 SP (low, llm)

Depends on: - · Sources: E-008

- [AC-S-SETUP-008-1] Given the setup tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 008-T001 | Add setting `noshow_block_enabled` (boolean, default false) in app/config.py and | 3.5 | backend-python, api-design | no | - |
| 008-T002 | Read the flag from the API response and expose a `useNoShowBlockEnabled` hook in | 2.5 | frontend-react | yes | - |

### S-FOUND-008 Repeat no-show block: Foundational prerequisites — P2/should · 3 SP (low, llm)

Depends on: S-SETUP-008 · Sources: E-008

- [AC-S-FOUND-008-1] Given the foundational prerequisites tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 008-T003 | Create SQLAlchemy model `NoShowBlock` in app/noshow_policy/models.py with fields | 2.0 | data-modeling, backend-python | no | - |
| 008-T004 | Create Alembic migration for table `no_show_block` in alembic/versions/20261113_ | 3.0 | postgres, data-modeling | no | 008-T003 |
| 008-T005 | Implement repository functions in app/noshow_policy/repository.py: count_no_show | 5.0 | backend-python, postgres | no | 008-T003 |
| 008-T006 | Write unit tests first for the rules in tests/noshow_policy/test_service.py: 1 n | 4.0 | qa-automation, backend-python | yes | - |
| 008-T007 | Implement service in app/noshow_policy/service.py with public interface exported | 4.0 | backend-python | no | 008-T005, 008-T006 |

### S-POLISH-008 Repeat no-show block: Polish & cross-cutting concerns — P2/should · 3 SP (low, llm)

Depends on: S-008-US3, S-008-US4 · Sources: E-008

- [AC-S-POLISH-008-1] Given the polish & cross-cutting concerns tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 008-T032 | Add structured logs, counters (blocks created, lifts, refused bookings) and trac | 3.0 | observability, backend-python | yes | - |
| 008-T033 | Write log test proving no patient name, phone or birth year is logged when check | 2.0 | qa-automation, backend-python | yes | 008-T032 |
| 008-T034 | Write authorisation tests in tests/noshow_policy/test_authz.py: a patient cannot | 3.0 | qa-automation, auth-security | no | 008-T026 |
| 008-T035 | Merge the operations and schemas of specs/008-noshow-block/contracts/noshow-bloc | 2.0 | api-design, docs | yes | 008-T026 |
| 008-T036 | Include table `no_show_block` in the 24-month retention job and in erasure on re | 3.0 | backend-python, postgres | no | 008-T004 |
| 008-T037 | Run every scenario of specs/008-noshow-block/quickstart.md in staging with the f | 5.0 | qa-automation, devops-ci | no | 008-T016, 008-T028, 008-T031, 008-T035 |

## E-009 WhatsApp to SMS fallback and reminders-failed list

Undelivered WhatsApp falls back once to SMS behind a switch; reminder failed state; reception list of tomorrow's failed reminders. RELEASE 2 (DL-2, due 2027-03-19, not hard). PRD ids: FR-029, FR-033.

### S-009-US1 A failed WhatsApp reminder is sent once by SMS — P2/should · 5 SP (low, llm)

As a patient who chose WhatsApp for messages, I want my appointment reminder to be sent once by SMS when WhatsApp cannot deliver it so that I am still reminded and do not miss my appointment.
Depends on: S-FOUND-009, S-006-US3 · Sources: FR-029

- [AC-S-009-US1-1] Given a due WhatsApp reminder for a booked appointment and the fallback switch on, When the WhatsApp provider returns an error on all 3 attempts, Then one SMS reminder with the same content is created and sent to the patient's phone number
- [AC-S-009-US1-2] Given a WhatsApp reminder that was accepted by the provider, When a failed delivery receipt arrives later, Then one SMS reminder is created and sent
- [AC-S-009-US1-3] Given a WhatsApp reminder that already has its SMS fallback, When the same failed receipt is received again (replayed), Then no second SMS is created or sent
- [AC-S-009-US1-4] Given a WhatsApp reminder that was delivered, When a delivery receipt arrives, Then no SMS is sent
- [AC-S-009-US1-5] Given an SMS fallback has been sent, When it is delivered, Then the appointment is not marked "reminder failed"

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 009-T008 | Unit tests for the fallback (error after 3 attempts, failed receipt, delivered o | 5.0 | qa-automation, backend-python | no | - |
| 009-T009 | Integration tests for the signed rel-010 webhook with replayed and concurrent fa | 6.0 | qa-automation, messaging | no | - |
| 009-T010 | Implement `handle_final_whatsapp_failure(message_id)` in app/messaging/fallback. | 7.0 | backend-python, messaging | no | 009-T005, 009-T006 |
| 009-T011 | Call the fallback after the third failed attempt of a WhatsApp reminder in app/m | 3.0 | backend-python, messaging | yes | 009-T010 |
| 009-T012 | Handle the failed WhatsApp receipt in app/messaging/webhooks.py (rel-010): call  | 6.0 | backend-python, messaging | no | 009-T010 |
| 009-T013 | Map the fallback SMS to the registered reminder SMS template in app/channel_adap | 3.0 | backend-python, messaging | yes | 009-T010 |

### S-009-US2 The fallback respects STOP, cancellations and the switch — P2/should · 3 SP (low, llm)

As a patient who has switched reminders off (and as the clinic paying for messages), I want the fallback never to send an SMS after STOP, for a cancelled appointment, or when the fallback is switched off so that my opt-out is respected and the clinic can disable the extra-cost fallback without a new release.
Depends on: S-FOUND-009 · Sources: FR-029

- [AC-S-009-US2-1] Given a failed WhatsApp reminder for a patient who has switched reminders off (STOP or by reception), When the fallback would run, Then no SMS is created
- [AC-S-009-US2-2] Given a failed WhatsApp reminder whose appointment has been cancelled, When the fallback would run, Then no SMS is created
- [AC-S-009-US2-3] Given the fallback switch is off, When a WhatsApp reminder finally fails, Then no SMS is created and the appointment is marked "reminder failed" so reception can phone the patient
- [AC-S-009-US2-4] Given the system is installed without any setting for the switch, When a WhatsApp reminder finally fails, Then the fallback behaves as on
- [AC-S-009-US2-5] Given the switch was turned off while an SMS fallback was waiting to be sent, When the sending is due, Then the SMS is not sent and the appointment is marked "reminder failed"

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 009-T014 | Tests for opt-out, cancelled appointment, switch off (marked "reminder failed"), | 5.0 | qa-automation, backend-python | no | - |
| 009-T015 | Add the guards to app/messaging/fallback.py: reminders opt-out read through cmp- | 8.0 | backend-python, messaging | no | 009-T010, 009-T001, 009-T007 |
| 009-T016 | Re-check the switch, opt-out and appointment status when the dispatcher is about | 5.0 | backend-python, messaging | no | 009-T011, 009-T015 |

### S-009-US3 An appointment is marked "reminder failed" when the SMS also fails — P2/should · 3 SP (low, llm)

As a receptionist, I want an appointment to be marked reminder failed when neither WhatsApp nor the SMS fallback could be delivered so that nobody assumes the patient was reminded and I know whom to phone.
Depends on: S-FOUND-009 · Sources: FR-029

- [AC-S-009-US3-1] Given an SMS fallback for a failed WhatsApp reminder, When the SMS provider returns an error on all attempts, Then the appointment is marked "reminder failed"
- [AC-S-009-US3-2] Given an SMS fallback accepted by the provider, When a failed delivery receipt arrives, Then the appointment is marked "reminder failed"
- [AC-S-009-US3-3] Given an appointment already marked "reminder failed", When the same failed receipt is received again, Then the mark is unchanged and no further message is sent
- [AC-S-009-US3-4] Given the appointment was cancelled before the SMS failed, When the SMS failure is recorded, Then the appointment is not shown as "reminder failed" to reception
- [AC-S-009-US3-5] Given a "reminder failed" mark, When a later delivery receipt says the earlier message was in fact delivered, Then the mark is removed

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 009-T017 | Tests for marking after SMS error, after failed SMS receipt, replayed receipt, c | 5.0 | qa-automation, backend-python | no | - |
| 009-T018 | Keep the mark only for booked appointments: read the appointment status through  | 4.0 | backend-python | yes | 009-T007 |
| 009-T019 | Mark "reminder failed" when the SMS fallback fails after its attempts in app/mes | 4.0 | backend-python, messaging | yes | 009-T016, 009-T018 |
| 009-T020 | Handle failed and delivered SMS receipts in app/messaging/webhooks.py (rel-009): | 5.0 | backend-python, messaging | no | 009-T012, 009-T018 |

### S-009-US4 Reception gets tomorrow's reminders-failed list — P2/should · 3 SP (low, llm)

As a receptionist, I want the list of tomorrow's appointments at my clinic whose reminder failed, with patient name, phone, time, dentist and treatment so that I can phone those patients in the afternoon and avoid no-shows.
Depends on: S-FOUND-009, S-005-US1 · Sources: FR-033, FR-004, NFR-006

- [AC-S-009-US4-1] Given tomorrow has 3 booked appointments at the receptionist's clinic marked "reminder failed", When the receptionist requests the list, Then all 3 are listed in time order with patient name, phone number, time, dentist and treatment
- [AC-S-009-US4-2] Given an appointment marked "reminder failed" at another clinic, When a receptionist of this clinic requests the list, Then it is not shown
- [AC-S-009-US4-3] Given an appointment marked "reminder failed" for a day other than tomorrow, When the list is requested, Then it is not shown
- [AC-S-009-US4-4] Given a "reminder failed" appointment that has since been cancelled, When the list is requested, Then it is not shown
- [AC-S-009-US4-5] Given no reminders failed, When the list is requested, Then an empty list is returned, not an error
- [AC-S-009-US4-6] Given a patient, dentist or practice manager signs in, When they request the list, Then the request is refused

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 009-T021 | Contract test for `GET /api/reception/reminders-failed` against contracts/clinic | 2.5 | qa-automation, api-design | yes | 009-T022 |
| 009-T022 | Add the path and `ReminderFailedItem` schema from specs/009-sms-fallback-failed- | 2.5 | api-design | yes | - |
| 009-T023 | Integration tests for clinic scoping, tomorrow in IST, cancelled appointment exc | 5.0 | qa-automation, backend-python | no | - |
| 009-T024 | Add `reminder_failed_appointments(clinic_id, day_start, day_end)` (one row per b | 3.5 | backend-python, postgres | yes | 009-T018 |
| 009-T025 | Add `GET /api/reception/reminders-failed` in app/reception/router.py and respons | 4.5 | backend-python, api-design | no | 009-T024, 009-T022 |

### S-009-US5 "Reminders failed" screen for reception — P2/should · 3 SP (low, llm)

As a receptionist, I want a Reminders failed screen for tomorrow showing the patients to phone so that I can work down the list in my afternoon routine.
Depends on: S-FOUND-009 · Sources: FR-033

- [AC-S-009-US5-1] Given the Release 2 flag is on and a receptionist is signed in, When they open "Reminders failed", Then tomorrow's failed reminders of their clinic are shown with a phone number per patient
- [AC-S-009-US5-2] Given the Release 2 flag is off, When a receptionist uses the application, Then no "Reminders failed" entry is shown and its address shows the standard not-found page
- [AC-S-009-US5-3] Given there are none, When the screen opens, Then a plain message says no reminders failed for tomorrow
- [AC-S-009-US5-4] Given the list cannot be loaded, When the screen opens, Then an error message with a retry action is shown
- [AC-S-009-US5-5] Given a dentist, patient or practice manager is signed in, When they browse the application, Then they see no "Reminders failed" entry

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 009-T026 | Component tests for list, empty state, error state with retry and phone numbers  | 3.5 | frontend-react, qa-automation | yes | - |
| 009-T027 | Route tests for flag off (no entry, not-found page) and non-receptionist roles ( | 2.5 | frontend-react, qa-automation | yes | - |
| 009-T028 | Add the API client and types for the list in src/api/remindersFailed.ts per cont | 2.0 | frontend-react, api-design | yes | - |
| 009-T029 | Build the "Reminders failed" page with tomorrow's date, a table of time, patient | 6.0 | frontend-react, frontend-css | no | 009-T028 |
| 009-T030 | Register the route and navigation entry for receptionists only, shown only when  | 4.0 | frontend-react | no | 009-T029, 009-T002 |

### S-SETUP-009 WhatsApp to SMS fallback and reminders-failed list: Setup — P2/should · 1 SP (low, llm)

Depends on: - · Sources: E-009, FR-029, FR-033

- [AC-S-SETUP-009-1] Given the setup tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 009-T001 | Add the setting `REMINDER_SMS_FALLBACK_ENABLED` (boolean, default true when unse | 3.5 | backend-python | yes | - |
| 009-T002 | Add the Release 2 screens flag `r2Screens` (reuse it if another R2 feature alrea | 2.5 | frontend-react | yes | - |

### S-FOUND-009 WhatsApp to SMS fallback and reminders-failed list: Foundational prerequisites — P2/should · 3 SP (low, llm)

Depends on: S-SETUP-009 · Sources: E-009, FR-029

- [AC-S-FOUND-009-1] Given the foundational prerequisites tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 009-T003 | Add a forward-only, expand-only Alembic migration alembic/versions/0xx_message_s | 4.0 | postgres, backend-python | no | - |
| 009-T004 | Update the `ent-message` model in app/messaging/models.py with `fallback_of_mess | 2.0 | backend-python, data-modeling | no | 009-T003 |
| 009-T005 | Add `create_fallback_once(original_message_id)` in app/messaging/repository.py:  | 4.5 | backend-python, postgres | no | 009-T004 |
| 009-T006 | Add the fallback decision log and OpenTelemetry counter (sent, skipped_opt_out,  | 3.5 | backend-python, observability | yes | - |
| 009-T007 | Add `mark_reminder_failed(message_id)` (idempotent, no change when already marke | 4.0 | backend-python | no | 009-T004 |

### S-POLISH-009 WhatsApp to SMS fallback and reminders-failed list: Polish & cross-cutting concerns — P2/should · 2 SP (low, llm)

Depends on: S-009-US1, S-009-US2, S-009-US3, S-009-US4, S-009-US5 · Sources: E-009, FR-029, FR-033

- [AC-S-POLISH-009-1] Given the polish & cross-cutting concerns tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 009-T031 | Test that fallback and list code paths write no patient name or phone to logs in | 3.0 | qa-automation, backend-python | yes | - |
| 009-T032 | Write the runbook for the switch, the extra message charges and open question Q1 | 2.0 | docs | yes | - |
| 009-T033 | Test that the 90-day message retention job also removes fallback and `reminder_f | 3.0 | qa-automation, backend-python | yes | 009-T004 |
| 009-T034 | Run the quickstart.md scenarios against staging with sandbox providers and the R | 4.0 | qa-automation, devops-ci | no | 009-T020, 009-T025, 009-T030 |

## E-010 No-show report per clinic and month

Manager sees no-shows and rate per clinic for the last 12 months, on screen. RELEASE 2 (DL-2, due 2027-03-19, not hard). PRD ids: FR-032.

### S-010-US1 Monthly no-show figures per clinic — P2/should · 3 SP (low, llm)

As a practice manager, I want the number of no-shows and the no-show rate for each clinic and each of the last 12 months so that I can see where no-shows happen and whether they fall, and a baseline is available to set a target.
Depends on: S-FOUND-010, S-005-US2 · Sources: FR-032

- [AC-S-010-US1-1] Given a clinic had 40 appointments in a month, of which 4 were no-shows, 6 were cancelled by the patient and 2 were cancelled by the clinic, When the practice manager requests the report, Then that clinic and month show 4 no-shows and a rate of 4 ÷ 32 = 12.5%. (source: FR-032)
- [AC-S-010-US1-2] Given a walk-in that was booked at reception and marked arrived, and another walk-in marked as a no-show, When the report is requested, Then both are counted in the denominator and the no-show is counted as a no-show. (source: FR-032)
- [AC-S-010-US1-3] Given two clinics, When the report is requested, Then each clinic has its own row of 12 months and the figures of one clinic never include appointments of the other. (source: FR-032)
- [AC-S-010-US1-4] Given an appointment starting at 23:30 IST on the last day of a month (which is already the next day in UTC), When the report is requested, Then it is counted in the IST month it started in. (source: FR-032)
- [AC-S-010-US1-5] Given an appointment in the 12-month window whose patient details have been anonymised (after 24 months, or after a deletion request), When the report is requested, Then it still counts in its month and status. (source: FR-032)
- [AC-S-010-US1-6] Given a clinic with no appointments, or only cancelled appointments, in a month, When the report is requested, Then that month shows 0 no-shows and no rate (not a division error). (source: FR-032)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 010-T006 | Unit tests for the window (current IST month plus 11 before, newest first, only  | 2.0 | qa-automation, backend-python | yes | - |
| 010-T007 | Integration test of the count query against PostgreSQL in `tests/integration/boo | 4.0 | postgres, qa-automation | yes | - |
| 010-T008 | Contract test that the response of `GET /api/reports/no-shows` matches `contract | 1.5 | api-design, qa-automation | yes | 010-T005 |
| 010-T009 | Implement the read-only function `count_appointments_by_clinic_month(window_star | 3.0 | postgres, backend-python | yes | - |
| 010-T010 | Implement the pure functions `report_window(now)` and `no_show_rate(no_shows, no | 1.5 | backend-python | yes | - |
| 010-T011 | Implement `ReportService.build_report()` in `app/modules/reporting/service.py`:  | 3.0 | backend-python | yes | 010-T004, 010-T009, 010-T010 |
| 010-T012 | Implement `GET /api/reports/no-shows` returning `NoShowReport` in `app/modules/r | 1.5 | backend-python, api-design | yes | 010-T003, 010-T011 |
| 010-T013 | Add structured logging (`report_generated` with correlation id, clinic count and | 1.5 | backend-python, observability | yes | 010-T012 |

### S-010-US2 No-show report screen for the practice manager — P2/should · 2 SP (low, llm)

As a practice manager, I want to open a read-only no-show report screen from the staff menu showing a 12-month table per clinic so that I can read each clinic's no-shows and rate at a glance without exporting anything.
Depends on: S-010-US1 · Sources: FR-032

- [AC-S-010-US2-1] Given the practice manager is signed in and the report is switched on, When they open the no-show report from the menu, Then they see every clinic with 12 monthly rows showing no-shows, non-cancelled appointments and rate. (source: FR-032)
- [AC-S-010-US2-2] Given a month with no rate (no non-cancelled appointments), When the table is shown, Then the rate cell shows a dash and not 0% or an error. (source: FR-032)
- [AC-S-010-US2-3] Given a third clinic has been added as data, When the screen is opened, Then the third clinic appears without any change to the screen. (source: FR-032)
- [AC-S-010-US2-4] Given the report is switched off, When the practice manager looks at the menu or opens the screen address directly, Then the screen is not offered and the address shows "not found". (source: FR-032)
- [AC-S-010-US2-5] Given the figures cannot be loaded, When the screen is opened, Then the manager sees a plain error message with a retry button, and no partial figures. (source: FR-032)
- [AC-S-010-US2-6] Given the report screen, When the manager looks for a download or print-to-file option, Then there is none: the report is on screen only. (source: FR-032)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 010-T014 | Integration test that the endpoint answers 404 when `noshow_report_enabled` is f | 1.0 | qa-automation, backend-python | yes | - |
| 010-T015 | Component tests with a mocked API in `src/pages/NoShowReport/NoShowReportPage.te | 2.5 | qa-automation, frontend-react | yes | - |
| 010-T016 | Add the flag dependency (404 when `noshow_report_enabled` is false) in `app/modu | 1.0 | backend-python, api-design | yes | 010-T012 |
| 010-T017 | Add the API client `getNoShowReport()` and its types, matching `contracts/no-sho | 1.0 | frontend-react, api-design | yes | - |
| 010-T018 | Build the page in `src/pages/NoShowReport/NoShowReportPage.tsx`: one table per c | 4.0 | frontend-react, frontend-css | yes | 010-T017 |
| 010-T019 | Add the route and the "No-show report" menu entry, both shown only when `noShowR | 2.5 | frontend-react | yes | 010-T002, 010-T018 |

### S-010-US3 Only the practice manager can read the report — P2/should · 2 SP (low, llm)

As a practice manager, I want the no-show report to be visible and readable only by me, not by receptionists, dentists, patients or unsigned callers so that management figures stay confidential and the roles rule (FR-004) is kept.
Depends on: S-010-US2 · Sources: FR-032

- [AC-S-010-US3-1] Given a receptionist is signed in, When they request the report directly, Then the request is refused and no figures are returned. (source: FR-032)
- [AC-S-010-US3-2] Given a dentist or a patient is signed in, When they request the report directly, Then the request is refused. (source: FR-032)
- [AC-S-010-US3-3] Given nobody is signed in, When the report is requested, Then the request is refused as not signed in. (source: FR-032)
- [AC-S-010-US3-4] Given a receptionist or a dentist is signed in, When they look at the menu, Then there is no no-show report entry. (source: FR-032)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 010-T020 | Role matrix integration test in `tests/integration/reporting/test_noshow_report_ | 3.5 | qa-automation, auth-security | no | - |
| 010-T021 | Component test that the menu entry is shown only to the practice manager when th | 1.5 | qa-automation, frontend-react | no | - |
| 010-T022 | Add the practice-manager-only dependency (role and active flag re-read through t | 4.5 | backend-python, auth-security | no | 010-T016 |
| 010-T023 | Show the menu entry and allow the route only for the practice manager role in `s | 2.5 | frontend-react, auth-security | no | 010-T019 |

### S-SETUP-010 No-show report per clinic and month: Setup — P2/should · 1 SP (low, llm)

Depends on: - · Sources: E-010, FR-032

- [AC-S-SETUP-010-1] Given the setup tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 010-T001 | Check the real layout of `app/modules/` and the appointment status values in `ap | 1.5 | backend-python | yes | - |
| 010-T002 | Add the flag `noShowReportEnabled` (build-time, default `false`) in `src/config/ | 0.5 | frontend-react | yes | - |

### S-FOUND-010 No-show report per clinic and month: Foundational prerequisites — P2/should · 1 SP (low, llm)

Depends on: S-SETUP-010 · Sources: E-010, FR-032

- [AC-S-FOUND-010-1] Given the foundational prerequisites tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 010-T003 | Create the `cmp-reporting` module shell: `app/modules/reporting/__init__.py` and | 1.5 | backend-python | yes | 010-T001 |
| 010-T004 | Define the response models `NoShowReport`, `ClinicNoShowReport` and `MonthlyNoSh | 2.0 | backend-python, data-modeling | yes | - |
| 010-T005 | Merge the path `/api/reports/no-shows` and its schemas from `specs/010-noshow-re | 1.5 | api-design | yes | - |

### S-POLISH-010 No-show report per clinic and month: Polish & cross-cutting concerns — P2/should · 1 SP (low, llm)

Depends on: S-010-US3 · Sources: E-010, FR-032

- [AC-S-POLISH-010-1] Given the polish & cross-cutting concerns tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 010-T024 | Performance test in `tests/integration/reporting/test_noshow_report_perf.py`: 3  | 3.0 | qa-automation, postgres | yes | 010-T012 |
| 010-T025 | Write `docs/noshow-report.md`: the flag settings in both repos, how to switch th | 1.5 | docs | yes | - |
| 010-T026 | Run the quickstart.md scenarios 1 to 3 against local clinic-api and clinic-web a | 1.5 | qa-automation | no | 010-T013, 010-T022, 010-T023 |

## Open questions

- E-001: ESTIMATE CHECK (scope/estimate.md, 1 SP = 6 h, 8 h per person-day): E-001 = 34 SP = 204 h = 25.5 pd against MOD-01 10-15 pd (1.7-2.6x the range). MOD-01 in estimate.md also includes family members (now E-007, 18 SP = 13.5 pd): E-001 + E-007 = 52 SP = 39 pd against 10-15 pd (2.6-3.9x). LARGE GAP: re-baseline or cut scope (decision for the Delivery Manager). Backlog figures are low-confidence LLM estimates with no analogy tickets.
- E-001: RELEASE 1 RECONCILIATION (request scope = DL-1, FR-001..FR-005, FR-007..FR-024, FR-027, FR-028, FR-030, FR-031 = E-001..E-006): backlog 201 SP = 150.75 pd. scope/estimate.md Release 1: modules MOD-01..05 and MOD-07 = 55-86 pd raw, 104-185 pd with cross-cutting work and 30% contingency. Backlog vs raw module effort: 1.75-2.7x. Backlog vs the 104-185 pd range: inside it, in the upper half. But (a) estimate.md's Release 1 includes all of MOD-01 and MOD-07, i.e. family members (E-007) and the SMS fallback / failed list (E-009), which the request puts in Release 2; like for like the backlog is 201 + 18 + 23 = 242 SP = 181.5 pd, which is 98% of the 185 pd high end; (b) backlog tasks cover build, test and docs; no UX design task and almost no DevOps task exists, and no PM/BA or contingency is included, whereas the 104-185 pd range includes them. FLAG: Release 1 is at or over the high end of the Phase 2 estimate on a like-for-like basis; re-baseline or cut scope before commitment to DL-1 (hard). Excluding the Setup, Foundational and Polish stories (74 SP in all ten epics), Release 1 user stories alone are 148 SP = 111 pd.
- E-001: FULL SCOPE RECONCILIATION: backlog 271 SP = 203.25 pd (10 epics). estimate.md: module effort 61-96 pd (backlog is 2.1-3.3x), with cross-cutting and contingency 115-206 pd (backlog is at the top end, without UX, PM/BA, most DevOps or contingency). Per-epic figures are in the open questions of each epic (E-001..E-010).
- S-FOUND-001: Q-008: hosting and domain are not decided; foundation is container-ready and configured by environment only, so no task waits for the answer.
- S-POLISH-001: Q-008: hosting and domain are open; the readiness checklist (T077) cannot confirm production HTTPS settings until the provider is chosen.
- E-002: ESTIMATE CHECK (scope/estimate.md, 1 SP = 6 h, 8 h per person-day): E-002 = 29 SP = 174 h = 21.75 pd against MOD-02 8-12 pd (1.8-2.7x the range; above the high end). Flag: re-baseline or cut scope (decision for the Delivery Manager).
- S-002-US3: Performance scenario (p95 within 2 s on 4G) depends on the AppointmentReader implementation delivered by feature 003; the load test uses fake appointments until then.
- S-002-US4: spec.md marks this story P2, but PRD FR-008 and architecture.md list it as Must in Release 1 (DL-1, hard): set to P1/must here; confirm with the product owner.
- S-002-US4: The to-move list needs the real AppointmentReader from feature 003; until then the story is verified only with the fake reader.
- S-FOUND-002: Requires feature 001 (clinic and dentist tables, RBAC) to be merged first; the exact RBAC dependency API of cmp-identity is not yet fixed.
- S-POLISH-002: Polish was generated as P3/could; raised to P1/must because the contract, role-matrix and no-PII-in-logs checks are part of the Definition of Done for the R1 hard deadline DL-1.
- E-003: ESTIMATE CHECK (scope/estimate.md, 1 SP = 6 h, 8 h per person-day): E-003 = 35 SP = 210 h = 26.25 pd against MOD-03 9-14 pd (1.9-2.9x the range; above the high end). Includes two load/performance proof stories (S-003-US4, S-003-US5; 6 SP) for NFR-001/NFR-002, which estimate.md does not list separately. Flag: re-baseline or cut scope (decision for the Delivery Manager).
- S-POLISH-003: NFR-004 (99.5% monthly availability, reception 08:00-20:00 Mon-Sat) is a proposal (PD-008) with no dedicated task: it is met by deployment/monitoring set-up. Who owns the availability monitor and alert in clinic-infra?
- E-004: ESTIMATE CHECK (scope/estimate.md, 1 SP = 6 h, 8 h per person-day): E-004 = 26 SP = 156 h = 19.5 pd against MOD-04 4-7 pd (2.8-4.9x the range). LARGE GAP, the biggest ratio in Release 1: re-baseline or cut scope (decision for the Delivery Manager).
- E-005: ESTIMATE CHECK (scope/estimate.md, 1 SP = 6 h, 8 h per person-day): E-005 = 35 SP = 210 h = 26.25 pd against MOD-05 9-14 pd (1.9-2.9x the range; above the high end). Flag: re-baseline or cut scope (decision for the Delivery Manager).
- S-005-US1: T012 checks the contract in contracts/clinic-api-v1.openapi.yaml, but the reception paths are only merged into that file in T054 (Polish); decide whether T012 tests the feature contract file reception-day.openapi.yaml until then.
- S-005-US2: Undo of 'arrived' back to booked on the same day (spec-local FR-011, assumption Q2) is not in the PRD (FR-021/FR-022 only allow undoing a no-show). It is covered by the same /undo endpoint and status table, not a separate task; treat as could-have and confirm with the client (clarifications.md Q2). Scenario 5 and 7 tests in T020 must follow the confirmed answer.
- S-005-US4: Q-015 (how walk-ins are recorded) is still open; the story assumes a normal appointment with status arrived and reason 'walk-in' (ASM-004).
- S-005-US4: Messages to the patient depend on feature 006: T036 defines a no-op port until 006 is merged, so AC 7 is only fully verifiable after 006. Confirm the merge order.
- S-005-US4: T037 changes the slot calculation owned by feature 002 and T038 builds on the feature 003 insert path; agree with those epics who owns shared code to avoid duplicate work.
- S-005-US5: Spec marks this story P2, but FR-023 is in Release 1 (DL-1, hard 2027-02-22), so it is set to P1/must as instructed; confirm.
- S-FOUND-005: Arrived -> booked same-day correction (spec-local FR-011, assumption Q2) is not in PRD FR-021/FR-022/FR-024; it is built into the transition table (T005/T006) and is not a separate task. Could-have: confirm with the client before UAT; removing it only deletes one transition row and its tests.
- S-POLISH-005: Polish was set to P3/could by the importer; the RBAC matrix, contract merge, performance test and the paper-diary dry run guide (SA-005) are needed before go-live DL-1, so it is set to P1/must.
- E-006: Q-009 (night-time reminder time) is open: the spec uses the default SA-003/PD-004 (quiet hours 21:00-08:00, 20:00 evening send, 08:00 fallback). Quiet hours, 20:00 and 08:00 are configuration values so a different answer needs no code change.
- E-006: SMS and WhatsApp providers are not selected (ASM-009): sandbox adapters only; real adapters (T021, T022, receipt/STOP parsers, signatures) must be re-checked against the chosen providers' real API and assume receipt webhooks, STOP forwarding and a test account in weeks 1-2.
- E-006: DLT sender ID/template registration (DEP-001) and WhatsApp template approval (DEP-002) are done by the clinic with our help (A-005); late approval (RSK-001) is the main schedule risk for the 2027-02-22 UAT date.
- E-006: The spec reads STOP from the SMS channel only (the WhatsApp webhook carries receipts, not inbound text). A WhatsApp-only patient can stop reminders via reception or by replying STOP to an SMS. Does NFR-011 / FR-031 ('replying STOP') accept this? To confirm with the client.
- E-006: ESTIMATE CHECK (scope/estimate.md, 1 SP = 6 h, 8 h per person-day): E-006 = 42 SP = 252 h = 31.5 pd against MOD-07 15-24 pd (1.3-2.1x the range; above the high end). MOD-07 in estimate.md also covers the fallback and failed list (now E-009, 23 SP = 17.25 pd): E-006 + E-009 = 65 SP = 48.75 pd against 15-24 pd (2.0-3.25x). LARGE GAP: re-baseline or cut scope (decision for the Delivery Manager).
- S-006-US2: SMS and WhatsApp providers are not selected (ASM-009): the real SMS and WhatsApp adapters (T021, T022) can only be finished against a chosen provider's API; estimate assumes a standard template-send HTTP API.
- S-006-US2: DLT sender/template registration (DEP-001) and WhatsApp template approval (DEP-002) must be done before real confirmations can go out in production (RSK-001); sandbox providers are used until then.
- S-006-US2: The confirmation link points to the appointment page of feature 004; the link format and sign-in deep link need agreeing with E-004.
- S-006-US3: Q-009 is open: the quiet-hours rule (21:00-08:00, 20:00 evening, 08:00 fallback) is the default of SA-003/PD-004; plan_reminder takes all times from settings. If the client answers differently, only settings and the table-driven test cases change.
- S-006-US3: The reminder link opens the appointment page of feature 004 (reschedule or cancel); behaviour for a cancelled or past appointment is owned by E-004.
- S-006-US4: Q-009 is open: the reschedule and less-than-24-hours cases use the same default quiet-hours rule.
- S-006-US4: Hooks on_cancelled/on_rescheduled must be called inside the cancel and reschedule transactions owned by feature 004 (E-004) and reception (E-005); the integration needs those epics' code to exist.
- S-006-US5: The spec reads STOP from the SMS channel only (the architecture's WhatsApp webhook carries delivery receipts, not inbound text). A patient who chose WhatsApp can stop reminders through reception, or by replying STOP to an SMS such as the sign-in code SMS. Does the client accept this reading of FR-031/NFR-011? A WhatsApp STOP is later work once the provider forwards it (ASM-009).
- S-006-US5: SMS provider not selected (ASM-009): the inbound STOP payload format and HMAC signature scheme are assumed until a provider is chosen.
- S-006-US5: SA-001: opt-out is per account (one phone number); confirm with client together with Q-007 for family members.
- S-006-US6: Sign-in codes need a DLT-registered code template (DEP-001): without approval real sign-in cannot go live on 2027-02-22 (RSK-001).
- S-006-US6: SMS provider not selected (ASM-009): the code is sent through the sandbox adapter until then.
- S-006-US6: Code rules (10 min, 5 tries, 15 min wait) are in E-001; this story only supplies sending and the error answer.
- S-006-US7: SMS and WhatsApp providers are not selected (ASM-009): receipt payloads, signature scheme and rate-limit behaviour are assumed; parsers (T055) and webhooks (T056) need a re-check against the chosen provider.
- S-006-US7: Alert rule ops/alerts/messaging.yaml (T057) must be wired by the infra repo (brightsmile/clinic-infra); no owner or date yet.
- S-006-US7: DLT/template approval (DEP-001/002) is not a build task but gates real sends; retention of rendered text is 90 days (ASM-012).
- S-SETUP-006: SMS and WhatsApp providers are not selected (ASM-009): provider names and field names stay behind the sandbox adapter and settings until chosen.
- S-SETUP-006: DLT registration (DEP-001) and WhatsApp template approval (DEP-002) are owned by the clinic with our help (A-005); the checklist T003 has no named owners or dates yet.
- S-FOUND-006: Q-009 is open: quiet hours and send times live in settings (default PD-004) so the catalogue and schedule stay unchanged if the answer differs.
- S-FOUND-006: SMS and WhatsApp providers are not selected (ASM-009): only the port and sandbox adapters are built in this phase.
- S-FOUND-006: Message table migration and appointment.channel NOT NULL touch tables owned by features 001/003: migration order must be agreed with those epics.
- S-POLISH-006: Template text review (T064) can only be final once DLT and WhatsApp templates (DEP-001/002) are registered or approved; real-provider verification cannot be done with sandbox providers.
- S-POLISH-006: The load test target (99% within 15 min, NFR-005) is run against a sandbox provider; real provider limits are unknown until a provider is chosen (ASM-009).
- 006-T044: Priority raised to P1/must to match story S-006-US5 (FR-031 is Release 1, must). The 1 s (p95) response time is a proposed measure, not stated in prd.md or architecture.md (they say 'always answers quickly' and 'STOP honoured within 1 hour'); to confirm with the team.
- E-007: ESTIMATE CHECK (scope/estimate.md, 1 SP = 6 h, 8 h per person-day): estimate.md has no separate line for family members; they are a driver of MOD-01 (10-15 pd, Q-007 default) and estimate.md lists SA-001 under MOD-01, MOD-03 and MOD-06. Backlog: E-007 = 18 SP = 108 h = 13.5 pd, which alone is within the whole of MOD-01's range, and E-001 + E-007 = 39 pd against 10-15 pd (see E-001). Flag: re-baseline or cut scope (decision for the Delivery Manager). Note estimate.md treats family members as part of Release 1 (MOD-01); the request puts FR-006 in Release 2.
- E-007: RELEASE 2 RECONCILIATION (request scope = DL-2, due 2027-03-19, not hard: FR-006, FR-025, FR-026, FR-029, FR-032, FR-033 = E-007..E-010): backlog 70 SP = 52.5 pd (E-007 13.5 + E-008 14.25 + E-009 17.25 + E-010 7.5). scope/estimate.md Release 2 covers only MOD-06 and MOD-08: 6-10 pd raw, 12-22 pd with cross-cutting and contingency. Backlog vs 12-22 pd: 2.4-4.4x. Like for like (E-008 + E-010 only = 29 SP = 21.75 pd) the backlog is at the top of 12-22 pd, and 2.2-3.6x the raw 6-10 pd, without UX, PM/BA or contingency. estimate.md has no figure for family members (E-007) or the SMS fallback and failed list (E-009), which it counts in Release 1. FLAG: Release 2 as requested is not covered by the Phase 2 estimate; re-baseline (or add a change request for E-007 and E-009) before DL-2 is committed.
- S-007-US1: Q-007 (PRD): can one phone number book for family members? Spec assumes yes (SA-001, ASM-001). If answered 'separate sign-ins', sign-in and cmp-identity change, MOD-01 grows 2-4 person-days (RSK-003) and this story must be reworked.
- S-007-US1: Q2 (spec, assumed): removing a family member is refused while an upcoming booked appointment exists; otherwise soft-remove. To be confirmed by the client.
- S-007-US1: Q3 (spec, assumed): the limit of 5 counts family members only, the account holder is extra (up to 6 people). To be confirmed.
- S-007-US2: Q-007 (PRD): if one phone number cannot book for family members, the account/person model and this booking step change (RSK-003).
- S-007-US3: Q-007 (PRD): if separate sign-ins are needed per family member, account scoping of appointments changes (RSK-003).
- S-007-US3: Q2 (spec, assumed): past appointments of a removed family member stay visible to the account.
- S-007-US4: Q-007 (PRD): erasure and the account/person split would be revisited if family members need own sign-ins (RSK-003).
- S-FOUND-007: Q-007 (PRD): the person/account schema and access helper assume one account per phone number; revisit if the client answers differently.
- E-008: ESTIMATE CHECK (scope/estimate.md, 1 SP = 6 h, 8 h per person-day): E-008 = 19 SP = 114 h = 14.25 pd against MOD-06 3-5 pd (2.9-4.75x the range). LARGE GAP: re-baseline or cut scope (decision for the Delivery Manager).
- S-008-US1: Q3 (clarifications.md): phone shown is that of the clinic of the booking or appointment concerned - assumed, not confirmed by a user.
- S-008-US1: Paths app/booking/online.py, app/booking/reschedule.py and src/pages/patient/* belong to features 003/004 and are to be confirmed against their merged code.
- S-008-US1: Q-007 (family members on one phone) is open in the PRD; default followed: family members are separate persons (PD-007).
- S-008-US2: Paths app/reception/day_view.py, app/reception/patient_search.py and src/pages/reception/* belong to feature 005 and are to be confirmed against its merged code.
- S-008-US4: Q1 (clarifications.md): undoing the no-show that caused a block removes it at once - assumed, not confirmed by a user.
- S-008-US4: Q2 (clarifications.md): the block ends by itself when no-shows age past 6 months (rolling window) - assumed.
- S-008-US4: app/reception/status.py belongs to feature 005, which must call recalculate; path to be confirmed.
- E-009: ISS-001: the client has not agreed to the WhatsApp->SMS fallback (adds message charges); built behind REMINDER_SMS_FALLBACK_ENABLED, default on (SA-008, ASM-005, RSK-005). Client must confirm; change the default only if the answer is no.
- E-009: ESTIMATE CHECK (scope/estimate.md): estimate.md has no separate line for the fallback and failed list; they are part of MOD-07 'Reminders and messages', 15-24 person-days (L, medium confidence; drivers include 'fallback to SMS' and 'delivery failures'). Backlog: E-009 = 23 SP = 138 h = 17.25 pd (8 h/day); E-006 + E-009 together = 65 SP = 48.75 pd against MOD-07 15-24 pd, i.e. 2.0-3.25x. LARGE GAP: re-baseline or cut scope. No split of MOD-07 between E-006 and E-009 exists in estimate.md. Also note estimate.md puts MOD-07 entirely in Release 1, while the request puts E-009 (FR-029, FR-033) in Release 2.
- S-009-US1: ISS-001: the client has not agreed to the WhatsApp->SMS fallback (message charges); built behind a switch, default on (SA-008).
- S-009-US2: ISS-001: the client has not agreed to the WhatsApp->SMS fallback; the switch REMINDER_SMS_FALLBACK_ENABLED (default on) is the mitigation.
- E-010: ESTIMATE CHECK (scope/estimate.md, 1 SP = 6 h, 8 h per person-day): E-010 = 10 SP = 60 h = 7.5 pd against MOD-08 3-5 pd (1.5-2.5x the range; above the high end). Flag: re-baseline or cut scope (decision for the Delivery Manager).
- S-010-US1: Q-015 (open): walk-ins are counted like any other appointment (assumption SA-004); confirm with the practice manager.
- S-010-US1: Q3 (open): the 12 months are the current (partial) month plus the 11 before; confirm.
- S-010-US2: Q3 (open): the current month is shown as the latest row, labelled 'month so far'; confirm.
- S-010-US3: Ship order: the Release 2 flags must not be switched on in production before this story is done, because until then the endpoint is open to any signed-in role.
