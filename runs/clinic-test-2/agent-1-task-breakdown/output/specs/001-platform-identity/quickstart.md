# Quickstart: validating Platform, sign-in, roles and clinics (MOD-01)

A run guide, not an implementation guide. Contract: [contracts/identity-api.openapi.yaml](./contracts/identity-api.openapi.yaml).
Tables: [data-model.md](./data-model.md).

## Prerequisites

- Python 3.12 and a PostgreSQL 16 database (local container is fine); Node.js for `clinic-web`.
- Environment variables for `clinic-api` (no values in the repository): `DATABASE_URL`, `JWT_SIGNING_KEY`, `HASH_SECRET` (keys the code hash and the IP/phone hashes), `ALLOWED_ORIGINS`, `COOKIE_SECURE` (`false` only on a developer machine), `REQUIRE_HTTPS`, `SMS_SENDER=fake`, `SEED_MANAGER_USERNAME`, `SEED_MANAGER_PASSWORD`.

## Set up

1. In `clinic-api`: apply the migrations (`alembic upgrade head`); this also seeds Indiranagar and Whitefield.
2. Seed the first manager: `python -m app.identity.seed`.
3. Start the API on port 8000 and the web app (`clinic-web`) pointing at it.

## Validation scenarios

| # | Story | Steps | Expected |
|---|---|---|---|
| 1 | Foundation | `GET /health` | 200 with `status: ok` in under 1 second; stop the database and see 503 |
| 2 | US1 | `POST /api/auth/patient/code-requests` with a new phone; read the code from the fake sender's outbox; `POST .../code-verifications`; then `POST .../registration` with a name | Session cookie set; `GET /api/me` shows the patient |
| 3 | US1 | Verify with 5 wrong codes, then the right code | 5th wrong gives 423 with `retry_after_seconds` about 900; the right code is still refused until the lock ends |
| 4 | US1 | Request more than the per-IP limit | 429, nothing in the fake outbox |
| 5 | US2 | `POST /api/auth/staff/sign-in` as the seeded manager, then change the password (`PUT /api/auth/staff/password`) | Signed in; `must_change_password` true until changed |
| 6 | US2 | 5 wrong passwords, then the right one | 423 `ACCOUNT_LOCKED`; after the lock time (use the test clock) sign-in works |
| 7 | US4 | As manager create a receptionist for Whitefield; sign in as that receptionist | `GET /api/me` shows Whitefield |
| 8 | US3 | As that receptionist `GET /api/clinics`; try `PATCH /api/clinics/{indiranagar}` and `POST /api/staff-accounts` | Only Whitefield listed; both writes 403 |
| 9 | US3 | Send a write without the `X-Requested-With` header, or with another `Origin` | 403 |
| 10 | US4 | As manager deactivate the receptionist; use the receptionist's old cookie | 401 or 403 on the very next request; sign-in refused |
| 11 | US5 | As manager `POST /api/clinics` for a third clinic and `POST /api/dentists`; set Monday at Indiranagar and Thursday at Whitefield; then try Monday at Whitefield too | Both listed; the double Monday gives 409 `DENTIST_DOUBLE_DAY` |
| 12 | US6 | As manager `POST /api/erasure-requests` for a patient's phone, then `POST .../execution` | Name, phone and birth year anonymised; old session refused; `due_at` is 30 days after `requested_at` |
| 13 | US7 | Insert back-dated rows; run `python -m app.jobs.retention` twice | Old codes gone, old deactivated staff anonymised, recent rows unchanged, second run changes nothing |
| 14 | Logs | Run scenarios 2 to 12 with log capture | No name, phone or birth year in any log line |

## Automated checks

- `pytest` in `clinic-api`: unit tests (codes, throttle, passwords, sessions, access), contract tests against the OpenAPI file, integration tests on PostgreSQL 16 (migrations up from empty, seed, scenarios above).
- Unit tests in `clinic-web` for the sign-in, staff, clinics and erasure screens.
- CI runs both; the contract test fails if an endpoint differs from the contract.
