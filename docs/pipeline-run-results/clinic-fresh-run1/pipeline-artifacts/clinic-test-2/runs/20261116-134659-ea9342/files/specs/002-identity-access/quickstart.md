# Quickstart: validating Sign-in, roles and staff accounts

Prerequisites: PostgreSQL 16 with migrations applied; environment variables from the secret store (token signing key, code-hash key, IP-hash key, allowed origin); a fake `MessageSender` registered for tests/staging; one clinic and one dentist from the scheduling feature (or test fixtures); an initial manager account created at set-up.

Run: backend tests in `clinic-api/tests/identity/` with pytest; web component tests in `clinic-web/tests/identity/`; contract tests against `contracts/identity-api.yaml` (merged into `contracts/clinic-api-v1.openapi.yaml`).

## Scenarios (expected outcomes)
1. **Patient sign-in (US1)**: POST `/api/auth/patient/code` with a known phone, read the code from the fake sender, POST `/api/auth/patient/verify`; expect 200 `needs_name=false` and a session cookie (`HttpOnly`, `Secure`, `SameSite=Strict`). A wrong code gives 400 `code_wrong`; after 10 minutes 400 `code_expired`; the 5th wrong code then any attempt within 15 minutes gives 429 `locked`.
2. **New patient (US2)**: use an unknown phone; verify gives `needs_name=true` and no account row; POST `/api/auth/patient/register` with a name gives 201 and one account plus one person row.
3. **Staff sign-in (US3)**: POST `/api/auth/staff/login`; wrong password 5 times then right password gives 429 for 15 minutes; a 9-character password is refused on create; idle for 30 minutes (use a test clock) forces sign-in again.
4. **Role matrix (US4)**: run `pytest clinic-api/tests/identity/test_role_matrix.py`; expect every role/operation pair to match the matrix and zero cross-clinic or cross-patient reads.
5. **Staff accounts (US5)**: as manager create a receptionist for clinic A, sign in as them, deactivate, and call `/api/auth/me` with the old cookie; expect 401 immediately.
6. **Erasure (US6)**: create a patient with a family member and appointments (fixtures), POST `/api/patient-accounts/{id}/erasure`; expect 202, and afterwards no name, phone or birth year in `patient_account`, `patient` or messages, with appointment rows unchanged in count. Check logs contain no PII.
7. **Patient deactivation (US7)**: as receptionist deactivate a patient account; the patient's open session gets 401.
8. **Web**: open the sign-in screen on a 360 px wide viewport; no sideways scroll; tap targets at least 44 px; wrong/expired code messages shown with a "send new code" button; wait message shown after 5 wrong tries.
