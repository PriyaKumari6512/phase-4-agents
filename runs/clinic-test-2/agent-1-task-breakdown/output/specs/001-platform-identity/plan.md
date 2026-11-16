# Implementation Plan: Platform, sign-in, roles and clinics (MOD-01)

**Branch**: `001-platform-identity` | **Date**: 2026-11-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-platform-identity/spec.md`

## Summary

Build the base every other feature stands on and the identity features of Release 1: patient phone-code sign-in
with throttling, staff username/password sign-in with lockout, cookie sessions, a server-side access framework
(role, clinic scoping, active flag re-read on every request), staff account management by the practice manager,
clinics and dentists as data (Indiranagar and Whitefield seeded), erasure on request and retention jobs. The code
lives in two repositories: `brightsmile/clinic-api` (components `cmp-identity` and the data-only part of
`cmp-scheduling` inside `ctr-clinic-api`) and `brightsmile/clinic-web` (`ctr-web`). The database is `ctr-db`
(PostgreSQL 16). The SMS code goes out through an SMS sender port with a fake adapter; the real provider adapter
belongs to the messaging features (ADR-0006).

Requirement ids covered: FR-001 to FR-005, NFR-006, NFR-007, NFR-009 (from `prd.md`).

## Technical Context

**Language/Version**: Python 3.12 (`clinic-api`); TypeScript with React (`clinic-web`). From `architecture.md`, section 4 (containers).

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic (architecture, `ctr-clinic-api`); argon2id password hashing and signed JWT in an `HttpOnly`, `Secure`, `SameSite=Strict` cookie (architecture, section 9); OpenTelemetry for logs, metrics and traces (constitution, principle II); React single-page app (architecture, `ctr-web`). No other framework is introduced.

**Storage**: PostgreSQL 16 (`ctr-db`); all tables are owned by `ctr-clinic-api`; forward-only, backward-compatible Alembic migrations (architecture, section 8).

**Testing**: Automated unit tests, API contract tests against this feature's OpenAPI file, and integration tests against a real PostgreSQL 16, run in CI (constitution: tests first for business logic, every story has an independent test; Definition of Done: unit and contract tests pass in CI). Python tests use `pytest`; the web app uses the unit-test runner set up in its repo (task T002).

**Target Platform**: `ctr-clinic-api` as one container, port 8000, `GET /health`, Swagger at `/docs`; `ctr-web` as static files on a CDN. Hosting and domain are open (Q-008) and do not affect the code.

**Project Type**: Web application: API repo plus single-page web repo.

**Performance Goals**: Authenticated requests add at most 3 indexed reads for the access check (account, session, scope); the design peak is about 35 requests per second (architecture, section 10). Health check answers in under 1 second (SC-007).

**Constraints**: All traffic over HTTPS (NFR-006); staff passwords at least 10 characters; code limits 10 minutes / 5 tries / 15-minute wait; staff sessions 8 hours or 30 minutes idle; patient session 7 days from last use (ASM-008); no patient data (name, phone, birth year) in logs (constitution, Definition of Done); no secrets in code (constitution, principle III); erase within 30 days (NFR-007).

**Scale/Scope**: 2 clinics now, 3 later; 6 dentists now, 10 later; about 450 appointments a week; a few hundred patient accounts in the first months. 7 user stories plus a foundation; about 25 endpoints; 7 screens in `clinic-web`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | How this plan complies | Status |
|---|---|---|
| I. Tests first for business logic | Every user story has an independent test and tasks list the tests before the implementation; OTP, lockout, session and access rules are unit-tested | Pass |
| II. Observability | Structured JSON logs with a correlation id, OpenTelemetry set-up and `GET /health` are Foundational tasks; the new endpoints are covered by it | Pass |
| III. Security baseline | No secrets in code (all from environment); input validation by request schemas at the boundary; authentication and authorisation changes are marked "needs security review" in the tasks | Pass |
| IV. Traceability | Spec stories and requirements carry `(source: ...)`; every task names exact file paths and the repository | Pass |
| V. Simplicity | One session table instead of a cache or broker; per-IP and per-phone throttle in the database; no extra service (architecture: no cache, no broker); the account/person split is the only forward-looking structure and is required by ADR-0008 | Pass |
| Definition of Done: no patient data in logs | A log filter test fails if a name, phone or birth year appears in any log line (tasks T008, T009, T071) | Pass |

No violations, so Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-platform-identity/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── clarifications.md    # Assumed answers to open questions Q-007, Q-008, Q-015
├── contracts/
│   └── identity-api.openapi.yaml   # Phase 1 output (endpoints of this feature)
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (two repositories)

```text
clinic-api/                          # repo brightsmile/clinic-api (ctr-clinic-api)
├── pyproject.toml
├── alembic.ini
├── Dockerfile
├── migrations/
│   ├── env.py
│   └── versions/
│       ├── 0001_scheduling_clinics_dentists.py
│       ├── 0002_identity_accounts.py
│       └── 0003_identity_sessions_throttle_erasure.py
├── app/
│   ├── main.py                      # app factory, routers, middleware
│   ├── config.py                    # settings from environment
│   ├── db.py                        # engine, session
│   ├── logging_setup.py             # JSON logs, correlation id, PII filter, OpenTelemetry
│   ├── health.py                    # GET /health
│   ├── errors.py                    # error model
│   ├── identity/                    # cmp-identity
│   │   ├── models.py                # staff_account, patient_account, patient, otp_challenge, auth_session, sign_in_throttle, erasure_request
│   │   ├── schemas.py
│   │   ├── phone.py                 # phone normalisation
│   │   ├── sms_port.py              # SmsSender port + FakeSmsSender
│   │   ├── otp_service.py           # code issue, verify, lock
│   │   ├── throttle.py              # per-IP and per-phone daily limits
│   │   ├── passwords.py             # argon2id, minimum length
│   │   ├── sessions.py              # JWT, cookie, idle and absolute expiry, revoke
│   │   ├── security.py              # CSRF header and Origin check middleware
│   │   ├── access.py                # AccessContext, role and clinic scope, require_* dependencies
│   │   ├── patient_accounts_service.py  # sign in, create account and holder person
│   │   ├── patient_auth_router.py
│   │   ├── staff_auth_service.py    # authenticate, lockout, change own password
│   │   ├── staff_auth_router.py     # sign-in, password change, sign-out
│   │   ├── staff_accounts_service.py
│   │   ├── staff_accounts_router.py
│   │   ├── me_router.py             # GET /api/me
│   │   ├── patients_router.py       # patient search for reception and manager
│   │   ├── erasure_service.py
│   │   ├── erasure_router.py
│   │   └── seed.py                  # first manager account
│   ├── scheduling/                  # cmp-scheduling (data only in this feature)
│   │   ├── models.py                # clinic, dentist, dentist_clinic_day
│   │   ├── schemas.py
│   │   ├── service.py
│   │   ├── router.py
│   │   └── seed.py                  # Indiranagar and Whitefield
│   └── jobs/
│       ├── registry.py              # retention rules registry (later features add rules)
│       └── retention.py             # daily job entry point
└── tests/
    ├── unit/
    ├── contract/
    └── integration/

clinic-web/                          # repo brightsmile/clinic-web (ctr-web)
├── package.json
└── src/
    ├── main.tsx
    ├── api/client.ts                # fetch wrapper, CSRF header, error mapping
    ├── auth/SessionContext.tsx      # who am I, role guard
    ├── auth/RequireRole.tsx
    ├── pages/patient/SignInPage.tsx
    ├── pages/staff/StaffSignInPage.tsx
    ├── pages/staff/ChangePasswordPage.tsx
    ├── pages/manager/StaffAccountsPage.tsx
    ├── pages/manager/ClinicsDentistsPage.tsx
    ├── pages/manager/ErasurePage.tsx
    └── tests/
```

**Structure Decision**: Web application with two repositories exactly as `architecture.md` names them. The API is
one modular monolith: `app/identity` is `cmp-identity` and `app/scheduling` is `cmp-scheduling` (clinics and
dentists only; hours, leave, treatments and slots come with MOD-02). Other modules call `app/identity/access.py`
for authorisation (architecture, section 9). The retention job registry sits in `app/jobs` because later features
register rules there.

## Design decisions (summary; details in research.md)

1. **Sessions**: the cookie holds a signed JWT with the session id and owner id only. A row in `auth_session` backs it, so sign-out and idle expiry work at once (needed because 30-minute idle and "session cannot be reused after sign-out" cannot be done by a stateless token alone). The owner's role, clinic and active flag are read from the database on every request.
2. **One-time codes**: 6 digits from a secure random source, stored as a keyed hash, one row per phone number (a new code replaces the old one but keeps the wrong-try count and lock), valid 10 minutes.
3. **Throttle**: per-phone lock lives in `otp_challenge`; per-IP and per-phone daily request limits live in `sign_in_throttle` (database, not memory, so two replicas agree). IP and phone keys are stored hashed.
4. **Staff passwords**: argon2id, minimum 10 characters, failed attempts and `locked_until` on the account.
5. **Access framework**: `AccessContext` (account kind, id, role, clinic ids, patient ids it may see) built per request; module code asks `ctx.require_role(...)`, `ctx.require_clinic(clinic_id)` and uses `ctx.clinic_filter()`; request ids alone are never trusted.
6. **Account/person split**: `patient_account` (phone) and `patient` (person); the holder is created with the account, family members come later (Q-007, ADR-0008).
7. **Erasure and retention**: anonymise in place (RSK-007); a registry of erasure steps and retention rules lets messages and appointments add their own.
8. **SMS**: `SmsSender` port with a fake adapter now; the provider adapter is added by the messaging features.

## Complexity Tracking

No constitution violations; nothing to justify.
