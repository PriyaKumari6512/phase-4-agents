# Implementation Plan: Family members on a patient account

**Branch**: `007-family-members` (no git branch) | **Date**: 2027-03-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/007-family-members/spec.md`

## Summary

A signed-in patient manages up to 5 family members (name, birth year) on their account, chooses who a visit is for in the booking flow, and sees the appointments of every person on the account with the person's name. The work extends `cmp-identity` (family-member operations, account-scoped access check, erasure of every person), `cmp-booking` (booking names the person; appointment list includes the account's people), and the web app (family screen, "who is this for" step, person name in the list). The account/person split (ADR-0008) already exists from feature 001, so there is no new entity, only the family-member lifecycle on `ent-patient`. Release 2 screens and operations are behind a feature flag. Q-007 is open; the plan follows the PRD default (SA-001, ASM-001, RSK-003).

## Technical Context

**Language/Version**: Python 3.12 (ctr-clinic-api); TypeScript with React (ctr-web) (architecture.md section 4)

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic (API); React SPA served from CDN (web). No new libraries.

**Storage**: PostgreSQL 16 (ctr-db): `ent-patient` and `ent-patient-account` (owned by cmp-identity), `ent-appointment.patient` (owned by cmp-booking)

**Testing**: pytest with contract tests against `contracts/clinic-api-v1.openapi.yaml` (API); the web repo's existing unit and component test runner (the constitution requires tests first for business logic). Per-role access tests (QA-007).

**Target Platform**: Linux container service (API); current Chrome and Safari on Android and iPhone (web, NFR-001)

**Project Type**: web application, two repositories: `brightsmile/clinic-api` (backend) and `brightsmile/clinic-web` (frontend)

**Performance Goals**: family list and family changes are small, indexed single-account queries, well within the slot (2 s) and booking (3 s) targets of NFR-002; booking with a person adds no extra round trip

**Constraints**: account holder plus at most 5 active family members, enforced under concurrency; no name or birth year in logs (NFR-007, constitution DoD); person ids from requests are never trusted, authorisation uses the token's account (thr-004); Release 2 feature flag; English only, IST (NFR-008); tap targets at least 44 px, no sideways scrolling (NFR-001, NFR-010)

**Scale/Scope**: at most 6 people per account; 3 clinics and 1,000 appointments a week later (NFR-003); 2 repos, 1 migration, 4 new endpoints, 2 changed endpoints, 3 screens or steps

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I. Tests first for business logic | Limit of 5, validation, account scoping and erasure have tests written first; each user story has an independent test (spec.md) | Pass |
| II. Observability | New endpoints emit structured logs with ids and correlation id only; existing `GET /health` unchanged | Pass |
| III. Security baseline | Inputs validated at the boundary; authorisation from the token's account on every operation; no secrets added; access-control changes get explicit review (task T036 in Polish) | Pass |
| IV. Traceability | Spec stories and requirements cite `FR-006` and related ids; every task names exact file paths and its repo | Pass |
| V. Simplicity | No new table, no new service, no new library; the account/person split is reused; flag is one setting | Pass |
| Technology constraints | Only technologies named in architecture.md; repos `brightsmile/clinic-api` and `brightsmile/clinic-web` | Pass |
| Definition of Done: no patient data in logs | Test that scans captured logs for family-member name and birth year (US4) | Pass |

Post-design re-check (after Phase 1): still Pass. One new column and one index only; no new component.

## Project Structure

### Documentation (this feature)

```text
specs/007-family-members/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── clarifications.md    # Assumed answers (Q1 = prd Q-007, Q2, Q3)
├── contracts/
│   └── family-members.openapi.yaml   # additions to api-clinic-api-v1
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (two repositories)

Paths follow the modular-monolith layout of architecture.md (one Python package per capability module). Where feature 001, 003 or 004 already created a file, this feature edits it; the exact existing file names are confirmed in task T001 before editing.

```text
brightsmile/clinic-api/
├── app/
│   ├── core/
│   │   └── settings.py                      # FAMILY_MEMBERS_ENABLED flag
│   └── modules/
│       ├── identity/                        # cmp-identity
│       │   ├── family_service.py            # add, edit, remove, list; limit and validation
│       │   ├── family_router.py             # /api/patient/family-members, /api/patient/people
│       │   ├── access.py                    # person_belongs_to_account(): account-scoped access check
│       │   └── erasure.py                   # erasure covers every person of the account
│       └── booking/                         # cmp-booking
│           ├── booking_service.py           # booking takes patient (person) id, checks account
│           └── appointment_list.py          # list includes all persons of the account, with person name
├── migrations/versions/
│   └── 0007_family_members.py               # is_account_holder, removed_at, unique index
└── tests/
    ├── unit/identity/test_family_service.py
    ├── unit/booking/test_booking_for_person.py
    ├── contract/test_family_members_contract.py
    └── integration/test_account_scoping.py

brightsmile/clinic-web/
└── src/
    ├── features/family/
    │   ├── FamilyMembersPage.tsx            # list, add, edit, remove
    │   ├── FamilyMemberForm.tsx             # name and birth year with field errors
    │   └── familyApi.ts
    ├── features/booking/
    │   └── WhoAndWhatStep.tsx               # "who is this for" choice added to feature 003's step
    ├── features/appointments/
    │   └── AppointmentList.tsx              # shows person name (feature 004's list)
    ├── config/featureFlags.ts               # family_members flag read from the API
    └── tests/
        ├── family/FamilyMembersPage.test.tsx
        └── booking/WhoAndWhatStep.test.tsx
```

**Structure Decision**: web application with two repositories; backend work in `brightsmile/clinic-api` (modules `identity` and `booking`), frontend in `brightsmile/clinic-web`.

## Complexity Tracking

No constitution violations; nothing to justify.
