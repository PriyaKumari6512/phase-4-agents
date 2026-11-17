# Implementation Plan: Family members on a patient account (Release 2)

**Branch**: `008-family-members` | **Date**: 2026-11-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-family-members/spec.md`

## Summary

A signed-in patient adds up to 5 family members (name and birth year) to their account and books for any of them; every appointment names the person it is for (FR-006, US-006). The design follows ADR-0008 (account and person split): `ent-patient-account` is the phone number and `ent-patient` is a person, so a family member is a new `ent-patient` row under the holder's account. `cmp-identity` owns the family-member operations and the check that a person belongs to the caller's account (thr-004). `cmp-booking` takes a person on the booking request, validates it through `cmp-identity`, and returns the person's name in appointment lists. `cmp-messaging` addresses messages to the account's phone and channel and adds the person's name to the message values. `ctr-web` gets a Family screen, a "who is it for" step and person names in the appointment list. Everything is behind a Release 2 feature flag (`family_members`). The 5-limit is enforced inside one database transaction that locks the account row, so concurrent adds cannot exceed it.

## Technical Context

**Language/Version**: Python 3.12 (ctr-clinic-api, repo brightsmile/clinic-api); TypeScript with React (ctr-web, repo brightsmile/clinic-web). From architecture.md section 4.

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic (ctr-clinic-api); React SPA served from a CDN (ctr-web). No new dependency is added.

**Storage**: PostgreSQL 16 (ctr-db). Table of `ent-patient` gets constraints; no new table. Retention follows ent-patient: until deletion on request, anonymised at 24 months idle.

**Testing**: Not named in architecture.md. Assumed: pytest for the API and the test runner of the web repo chosen in feature 001 (platform foundation). Contract tests run against `contracts/clinic-api-v1.openapi.yaml` in CI (architecture section 8). Per-role/per-account authorisation tests are required (QA-007).

**Target Platform**: Managed container service (API), static CDN (web), current Chrome and Safari on Android and iPhone (NFR-001).

**Project Type**: Web application: modular monolith API plus SPA (two repositories).

**Performance Goals**: Booking confirmed within 3 s for 95% of requests and slot list within 2 s (QA-001, QA-002). The person check adds one indexed lookup to a booking; the family list is at most 6 rows.

**Constraints**: Authorisation server-side from the token owner, never from request ids alone (thr-004); only name and birth year stored for a family member (NFR-007, CON-004); no PII in logs (constitution); R2 screens hidden by a feature flag (architecture section 8); inputs validated at boundaries (constitution III); `GET /health` already exists.

**Scale/Scope**: Up to 6 persons per account; about 450 appointments a week now, 1,000 later (NFR-003). 3 screens/changes in ctr-web, 2 new endpoints, 3 extended endpoints.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Tests first for business logic | Limit, duplicate, validation, ownership and flag rules have tests written first; each user story has an independent test (see quickstart.md) | Pass |
| II. Observability | New endpoints emit structured logs with ids and correlation id, metrics and traces; no new service, so health check stays | Pass |
| III. Security baseline | Ownership check is server-side; this changes authorisation, so tasks include an explicit security review; inputs validated; no secrets added | Pass (review task T044 in tasks.md) |
| IV. Traceability | Spec, requirements and tasks carry prd.md ids; every task names file paths | Pass |
| V. Simplicity | No new table, no new service, no new component; the flag is a boolean setting | Pass |
| DoD: no patient data in logs | Names and birth years are never logged (FR-013, SC-007); a test asserts it | Pass |

**Post-design re-check**: Pass. The one design decision that touches an architecture rule is the person's name in messages (thr-013 lists only clinic, dentist, date, time and link as template values). This is recorded as open question Q4 in clarifications.md and A-12 in spec.md.

## Project Structure

### Documentation (this feature)

```text
specs/008-family-members/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── clarifications.md    # Assumed answers to open questions
├── contracts/
│   └── family-members.openapi.yaml   # Additions to api-clinic-api-v1
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (two repositories)

The architecture names the modules but not folder layouts. The layout below is assumed and must be aligned with the scaffolding done in features 001 and 002 (open point in research.md R-6).

```text
clinic-api/                                   # brightsmile/clinic-api (ctr-clinic-api)
├── app/
│   ├── core/
│   │   └── feature_flags.py                  # flag read (reuse if feature 001 has one)
│   └── modules/
│       ├── identity/                         # cmp-identity
│       │   ├── models.py                     # ent-patient (person) constraints
│       │   ├── schemas.py                    # FamilyMemberIn, PersonOut
│       │   ├── family_service.py             # add, list, limit, duplicate, ownership
│       │   ├── family_router.py              # /api/me/people, /api/me/family-members
│       │   └── access.py                     # resolve_person(access_context, person_id)
│       ├── booking/                          # cmp-booking
│       │   ├── schemas.py                    # person_id on the booking request, person in appointment out
│       │   ├── service.py                    # booking for a person
│       │   └── router.py                     # booking and appointment list endpoints
│       └── messaging/                        # cmp-messaging
│           └── templates.py                  # person name value, account-level address
├── alembic/versions/
│   └── 0008_family_members.py                # expand-only migration
├── contracts/
│   └── clinic-api-v1.openapi.yaml            # merged additions
└── tests/
    ├── unit/identity/test_family_service.py
    ├── unit/booking/test_booking_for_person.py
    ├── integration/test_family_authorisation.py
    ├── integration/test_family_limit_concurrency.py
    └── contract/test_family_contract.py

clinic-web/                                   # brightsmile/clinic-web (ctr-web)
└── src/
    ├── features/
    │   ├── flags/useFeatureFlag.ts
    │   ├── family/
    │   │   ├── api.ts
    │   │   ├── FamilyPage.tsx
    │   │   ├── AddFamilyMemberForm.tsx
    │   │   └── FamilyPage.test.tsx
    │   ├── booking/
    │   │   ├── WhoIsItFor.tsx
    │   │   └── WhoIsItFor.test.tsx
    │   └── appointments/
    │       ├── AppointmentList.tsx           # shows person name
    │       └── AppointmentList.test.tsx
    └── i18n/messages.en.ts                   # English catalogue entries
```

**Structure Decision**: Web application with two repositories, as in the constitution. Backend work stays inside the existing modules `identity`, `booking` and `messaging`; no new module.

## Complexity Tracking

No constitution violations to justify.
