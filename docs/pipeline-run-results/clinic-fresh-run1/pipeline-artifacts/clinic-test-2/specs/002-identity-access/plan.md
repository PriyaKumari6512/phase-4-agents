# Implementation Plan: Sign-in, roles and staff accounts

**Branch**: `002-identity-access` | **Date**: 2026-11-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-identity-access/spec.md`

## Summary

Build `cmp-identity` inside `ctr-clinic-api` (Python FastAPI modular monolith) and the matching sign-in and staff screens in `ctr-web`. Patients sign in with a 6-digit SMS code (hashed, 10 minutes, 5 tries, 15-minute lock per phone, per-IP throttle, daily cap); staff sign in with username and argon2id-hashed password (10-character minimum, 5-failure lockout for 15 minutes). Both get a signed JWT in an `HttpOnly`, `Secure`, `SameSite=Strict` cookie with a CSRF header and Origin check on writes (ADR-0004). The token holds user id and role only; role, clinic and active flag are re-read from the database on every request, so deactivation acts at once. An `AccessContext` with clinic scoping is the single authorisation mechanism all other modules call (thr-004, thr-007, thr-009). The practice manager manages staff accounts and runs erasure on request (ASM-013); reception can deactivate a patient account (RSK-009). Code is sent through a message-sending port (the SMS adapter belongs to the messaging feature). Sources: FR-002, FR-003, FR-004, FR-005, NFR-006, NFR-007.

## Technical Context

**Language/Version**: Python 3.12 (ctr-clinic-api); TypeScript with React (ctr-web) — architecture.md section 4

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic (architecture.md). Supporting libraries needed by the architecture's decisions: an argon2id implementation (argon2id is named in architecture section 9) and a JWT signing library (signed JWT, ADR-0004). No technology outside architecture.md is introduced.

**Storage**: PostgreSQL 16 (ctr-db); entities ent-staff-account, ent-patient-account, ent-patient, ent-otp-challenge

**Testing**: pytest for ctr-clinic-api (unit, contract against `contracts/clinic-api-v1.openapi.yaml`, and a per-role test matrix, QA-007); component tests for ctr-web with the test runner set up with the SPA shell (architecture.md does not name one). See research.md R-09.

**Target Platform**: Managed container service behind CDN/WAF in an India region (ADR-0005); web app on CDN, current Chrome and Safari

**Project Type**: web application (backend `brightsmile/clinic-api` + frontend `brightsmile/clinic-web`)

**Performance Goals**: sign-in calls fit within the existing p95 ≤ 500 ms server budget (QA-001); argon2id cost tuned so one verification is about 100–250 ms on 1 vCPU (design peak is about 35 requests/s, sign-ins are a small share)

**Constraints**: all traffic HTTPS; no PII in logs (constitution); no secrets in code (token signing key, code-hash pepper, IP-hash key come from the secret store as environment variables); role/clinic/active re-read per request; erasure within 30 days; retention: OTP 24 hours, messages 90 days, appointments 24 months

**Scale/Scope**: 2 clinics (3 later), 6 dentists, about 10 staff accounts, a few thousand patient accounts; at most 1,000 codes a day (assumed, Q2)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Tests first for business logic | Every story has an independent test; per-role matrix tests written first (tasks list tests before implementation) | Pass |
| II. Observability | Structured logs (ids and correlation id only), metrics for sign-in success/failure/lockout, traces; `GET /health` is owned by the platform feature, identity adds a readiness check of the sign-in tables | Pass |
| III. Security baseline | Secrets from secret store; auth changes flagged for explicit review (task in Polish); inputs validated by schemas at the boundary | Pass |
| IV. Traceability | spec stories and FRs carry prd.md ids; every task names exact paths | Pass |
| V. Simplicity | No new entities beyond the four named; throttle counters derived from OTP challenge rows; no extra cache or queue; one erasure path | Pass |
| Technology constraints | Follows architecture.md; repos brightsmile/clinic-api and brightsmile/clinic-web | Pass |
| Definition of Done: no patient data in logs | Log-scrubbing test (task) | Pass |

Post-design re-check: Pass (see data-model.md; no new entities or technologies added).

## Project Structure

### Documentation (this feature)

```text
specs/002-identity-access/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── clarifications.md
├── contracts/
│   └── identity-api.yaml
├── checklists/requirements.md
└── tasks.md
```

### Source Code (two repositories)

```text
brightsmile/clinic-api  (path prefix clinic-api/)
├── app/
│   ├── main.py                          # existing app; router registration only
│   └── identity/                        # cmp-identity
│       ├── __init__.py
│       ├── models.py                    # StaffAccount, PatientAccount, Patient, OtpChallenge
│       ├── schemas.py                   # request/response schemas
│       ├── settings.py                  # limits (assumed values, Q2), secrets names
│       ├── passwords.py                 # argon2id hash/verify, 10-char policy
│       ├── tokens.py                    # JWT cookie issue/read, idle and absolute expiry
│       ├── security.py                  # CSRF header + Origin check, HTTPS-only headers
│       ├── access.py                    # AccessContext, role and clinic scoping, FastAPI dependency
│       ├── ports.py                     # MessageSender, AppointmentAnonymiser, MessageEraser, FutureAppointments ports
│       ├── otp_service.py               # issue/verify code, tries, locks, throttles, daily cap
│       ├── patient_auth_service.py      # sign-in, registration, patient accounts
│       ├── staff_auth_service.py        # sign-in, lockout, password change
│       ├── staff_service.py             # create/assign/deactivate staff
│       ├── patient_admin_service.py     # search, deactivate/reactivate patient accounts
│       ├── erasure_service.py           # erasure on request, pending retry
│       ├── retention_jobs.py            # OTP purge, idle patient and ex-staff anonymisation
│       ├── log_scrub.py                 # log filter: no names, phones, birth years, codes
│       ├── observability.py             # structured events, metrics, traces, readiness (no PII)
│       ├── bootstrap.py                 # set-up command: first manager account
│       └── api/
│           ├── auth_routes.py           # /api/auth/*
│           ├── staff_routes.py          # /api/staff/*
│           └── patient_admin_routes.py  # /api/patients/search, /api/patient-accounts/*
├── contracts/clinic-api-v1.openapi.yaml # identity operations merged in
├── docs/identity-security-review.md     # review checklist for auth changes
├── migrations/versions/                 # Alembic migration for the four tables
└── tests/identity/                      # unit, contract, role matrix, log-scrub tests

brightsmile/clinic-web  (path prefix clinic-web/)
└── src/
    ├── identity/
    │   ├── api.ts                       # calls to /api/auth, /api/staff, /api/patient-accounts
    │   ├── session.tsx                  # session state, CSRF header, role guard
    │   ├── PatientSignIn.tsx            # phone, code, new patient name
    │   ├── StaffSignIn.tsx
    │   ├── ChangePassword.tsx
    │   ├── StaffAdmin.tsx               # manager: create, assign, deactivate, reset password
    │   ├── PatientSearch.tsx            # reception/manager: find, deactivate/reactivate
    │   └── ErasureAdmin.tsx             # manager: erasure on request
    └── routes/identity.tsx              # routes and role guards
└── tests/identity/                      # component tests
```

**Structure Decision**: Web application with two repositories. All backend code lives in the `app/identity` module (one module per capability, architecture ADR-0001); other modules import only `app/identity/access.py` and `ports.py`. Screens live in `src/identity` in the web app.

## Complexity Tracking

No constitution violations; nothing to justify.
