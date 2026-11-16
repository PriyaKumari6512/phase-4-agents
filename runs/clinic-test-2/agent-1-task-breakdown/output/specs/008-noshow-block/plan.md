# Implementation Plan: Repeat no-show block

**Branch**: `008-noshow-block` | **Date**: 2026-11-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/008-noshow-block/spec.md`

## Summary

Release 2 module MOD-06 (source: FR-025, FR-026). Component `cmp-noshow-policy` in `ctr-clinic-api` counts a person's no-shows in a rolling 6 months, keeps the `ent-no-show-block` record, answers "is this person blocked" in-process for `cmp-booking` (online book and reschedule), and lets `cmp-reception` show and lift a block. `cmp-booking` already carries a hook, added by features 003 and 004, that always allows in Release 1; this feature wires the hook to the real answer. `cmp-reception` (feature 005) notifies `cmp-noshow-policy` in the same transaction whenever a no-show is marked or undone, so the state is always recalculated. `ctr-web` shows the phone-the-clinic message and the reception blocked marker and lift control. Everything is behind the Release 2 feature switch `noshow_block_enabled`.

Approach: the person's counted no-shows are read from appointment data (status `no_show`); the block record (`ent-no-show-block`) is created when the count reaches 2 and closed on lift or when the count falls below 2. The check on the booking path is `open block exists AND count >= 2`, so a no-show ageing out needs no job.

## Technical Context

**Language/Version**: Python 3.12 (ctr-clinic-api, repo brightsmile/clinic-api); TypeScript with React (ctr-web, repo brightsmile/clinic-web)

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic (API); React SPA (web). No new dependency. Access context and RBAC from `cmp-identity` (feature 001)

**Storage**: PostgreSQL 16 (ctr-db): one new table for `ent-no-show-block`; reads existing appointment and appointment-event tables owned by `cmp-booking`

**Testing**: pytest with tests written with the code (constitution I); API contract tests against `contracts/clinic-api-v1.openapi.yaml`; component tests for web screens

**Target Platform**: Linux container service (API); modern Chrome and Safari (web; patient screens on phones, reception on desktop)

**Project Type**: web application (API plus SPA), two repositories

**Performance Goals**: the block check adds one indexed count query to the booking and reschedule path; stays inside the booking budget (server p95 <= 800 ms, QA-002) and slot picker budget (p95 <= 500 ms, QA-001)

**Constraints**: strong consistency: block recalculation commits in the same transaction as the status change (architecture section 5); authorisation server side from the token owner (thr-004); no PII in logs; times stored UTC, shown IST; block records kept 24 months; reception never blocked; R2 screens behind the feature switch

**Scale/Scope**: about 450 appointments a week (1,000 later); the count query touches at most a few rows per person; 4 user stories, about 5 to 6 API operations, 3 web surfaces

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Tests first for business logic | Count/block/lift rules have unit tests written with the code; every story has an independent test (see spec) | Pass |
| II. Observability | New endpoints emit structured logs, metrics and traces; counters for blocks created, lifts and refused bookings; no health endpoint added (existing `GET /health`) | Pass |
| III. Security baseline | Lift is receptionist-only, server-side; inputs validated; no secrets; authentication changes: none | Pass |
| IV. Traceability | Every story and requirement cites FR-025 / FR-026 / PD-007; every task lists file paths | Pass |
| V. Simplicity | No new component or service; reuse the existing hook; no job needed for expiry (read-time check) | Pass |
| Technology constraints | Only technologies in architecture.md; repos brightsmile/clinic-api and brightsmile/clinic-web | Pass |
| Definition of done: no patient data in logs | Logs carry ids only | Pass |

Re-check after Phase 1 design: pass; no violations, Complexity Tracking not needed.

## Project Structure

### Documentation (this feature)

```text
specs/008-noshow-block/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── clarifications.md    # Assumed answers Q1-Q3
├── contracts/
│   └── noshow-block.openapi.yaml   # Phase 1 output (additions to api-clinic-api-v1)
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output
```

### Source Code

Paths below are the planned layout. Features 003, 004 and 005 are written in parallel; where a file belongs to them (marked "existing"), the task edits it in place and the exact path is to be confirmed against the merged code.

```text
brightsmile/clinic-api/
├── app/
│   ├── noshow_policy/                 # new: cmp-noshow-policy
│   │   ├── __init__.py                # public in-process interface
│   │   ├── models.py                  # ent-no-show-block
│   │   ├── repository.py              # count and block queries
│   │   ├── service.py                 # recalculate, is_blocked, lift
│   │   ├── schemas.py
│   │   └── router.py                  # reception and eligibility endpoints
│   ├── booking/online.py              # existing (003/004): replace always-allow hook
│   ├── reception/status.py            # existing (005): notify on no-show / undo
│   ├── reception/day_view.py          # existing (005): add blocked flag
│   ├── reception/patient_search.py    # existing (005): add blocked flag
│   └── config.py                      # existing: noshow_block_enabled switch
├── alembic/versions/                  # new migration for the block table
└── tests/noshow_policy/               # unit, integration, contract tests

brightsmile/clinic-web/
└── src/
    ├── features/noshow-block/         # new: blocked notice, blocked badge, lift dialog
    ├── pages/patient/                 # existing (003/004): slot picker and reschedule show notice
    └── pages/reception/               # existing (005): day view, appointment panel, patient search show badge and lift
```

**Structure Decision**: web application split across the two repositories named in the constitution. All rules live in the API; the web only shows what the API returns.

## Design decisions

- **Count**: a person's counted no-shows are appointments of that person (`ent-appointment.patient`, a person, not an account: PD-007) with status `no_show`, start time within the last 6 months, and whose latest no-show status change happened after the person's last reception lift.
- **Block record**: created when a recalculation finds count >= 2 and no open block; closed (lifted by a user, or system-closed with no user) when count < 2. A system close never resets the count; only a reception lift does.
- **Check on the booking path**: blocked = open block exists AND current count >= 2. This makes no-shows ageing out and undo take effect on the very next request with no job.
- **Hook**: `cmp-booking` calls `noshow_policy.is_blocked(person_id)` before creating or moving an online appointment, including the final confirm; reception paths do not call it.
- **Event**: `cmp-reception` calls `noshow_policy.recalculate(person_id)` inside the transaction that marks or undoes a no-show (in-process call, no queue).
- **Refusal**: HTTP 403 with code `ONLINE_BOOKING_BLOCKED` and the clinic phone; the web shows the notice.
- **Switch**: `noshow_block_enabled` false means `is_blocked` returns false, recalculate still records blocks silently so the data is ready (assumed; see research.md R4), and the web hides every R2 surface.

## Complexity Tracking

No constitution violations; nothing to justify.
