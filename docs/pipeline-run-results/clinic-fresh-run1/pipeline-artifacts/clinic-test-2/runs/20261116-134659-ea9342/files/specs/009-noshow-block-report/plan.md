# Implementation Plan: Repeat no-show block and no-show report (Release 2)

**Branch**: `009-noshow-block-report` | **Date**: 2026-11-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/009-noshow-block-report/spec.md`

## Summary

Put the real repeat no-show rule behind the "is this person blocked?" check that online booking (feature 004) and rescheduling (feature 005) already call, let reception see and lift a block, and give the practice manager a 12-month no-show report per clinic. Backend: a new `cmp-noshow-policy` module (counts a person's no-shows in the last 6 months since their last lift, keeps `ent-no-show-block` rows, lifts) and a new `cmp-reporting` module (one grouped read through `cmp-booking`), plus small additions to `cmp-booking` (a no-show counting reader, the block check wired in on confirm) and `cmp-reception` (show and lift). Web: block notice on the booking and reschedule screens, a block banner and Lift action in the reception patient panel, and a no-show report screen for the practice manager. Everything sits behind one Release 2 feature flag. Counts are live queries over appointments and their history (no cache, no new table beyond `ent-no-show-block`), per the architecture.

## Technical Context

**Language/Version**: Python 3.12 (ctr-clinic-api); TypeScript with React (ctr-web)

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic (ctr-clinic-api); React SPA on CDN (ctr-web). No new dependencies.

**Storage**: PostgreSQL 16 (ctr-db): one new table for `ent-no-show-block`; report and counts are read from `ent-appointment` and `ent-appointment-event`

**Testing**: pytest for the API (unit, contract tests against `contracts/clinic-api-v1.openapi.yaml`, integration tests on PostgreSQL); the web app's test runner set up by feature 001 for component tests. Tests are written before or with the code (constitution I).

**Target Platform**: ctr-clinic-api on the managed container service (2 replicas); ctr-web static files on the CDN. Reception and the practice manager use a desktop browser; patients use a phone browser.

**Project Type**: web application: backend (brightsmile/clinic-api) and frontend (brightsmile/clinic-web)

**Performance Goals**: The block check adds one indexed count query to a booking or reschedule and must stay inside the existing booking budget (server p95 at most 800 ms, QA-002). The report is one grouped query per request; the architecture sets no separate report target, so none is invented here.

**Constraints**: Count per person, not per account (PD-007, ADR-0008). Existing bookings never change. Report on screen only, no export. No patient name, phone or birth year in logs; logs carry ids and the correlation id (constitution DoD). Role and clinic scoping through `cmp-identity` on every endpoint, from the token owner, never from request ids alone (thr-004, thr-007). Times stored UTC, shown IST. Release 2 flag off means no behaviour change.

**Scale/Scope**: about 450 appointments a week now, 1,000 later (NFR-003); 3 screens or panels in ctr-web, 4 new endpoints, 1 new table. Report: at most 3 clinics by 12 months = 36 rows.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Tests first for business logic | Each user story has an independent test; count, window, lift and rate rules get unit tests written first (tasks list tests before code) | Pass |
| II. Observability | New endpoints emit structured logs and metrics (blocked attempts, lifts, report reads) with ids only; the existing `GET /health` is unchanged | Pass |
| III. Security baseline | No secrets; role checks through `cmp-identity` on each endpoint; request bodies validated at the boundary; this feature changes authorisation rules, so the tasks include an explicit review step | Pass |
| IV. Traceability | Spec stories and requirements cite FR-025, FR-026, FR-032 (and PD-007, ASM ids); each task names exact file paths | Pass |
| V. Simplicity | One table, live queries, no cache, no scheduled job, no new library; the existing booking interface is reused | Pass |
| Technology constraints | Follows `architecture.md` (modular monolith, in-process calls, ctr-db, ctr-web); repos brightsmile/clinic-api and brightsmile/clinic-web | Pass |

**Post-design re-check**: Pass. The design adds no component beyond the two the architecture names and does not move data ownership: `cmp-noshow-policy` owns `ent-no-show-block`; `cmp-booking` still owns appointments.

## Project Structure

### Documentation (this feature)

```text
specs/009-noshow-block-report/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── clarifications.md    # Assumed answers to open questions Q1 to Q3
├── contracts/
│   └── noshow-block-report.openapi.yaml   # Operations added to api-clinic-api-v1
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

The layout below assumes the module-per-component folders set up by feature 001; where a folder or file already exists from features 004 to 006, the tasks add to it.

```text
clinic-api/                                  # repo brightsmile/clinic-api
├── app/
│   ├── modules/
│   │   ├── noshow_policy/                   # cmp-noshow-policy (new)
│   │   │   ├── __init__.py
│   │   │   ├── models.py                    # ent-no-show-block table
│   │   │   ├── service.py                   # count, is_blocked, on_marked, on_undone, lift
│   │   │   └── schemas.py
│   │   ├── reporting/                       # cmp-reporting (new)
│   │   │   ├── __init__.py
│   │   │   ├── service.py                   # 12-month report from cmp-booking
│   │   │   ├── router.py                    # GET /api/reports/no-shows
│   │   │   └── schemas.py
│   │   ├── booking/                         # cmp-booking (existing, extended)
│   │   │   ├── no_show_stats.py             # no-show counting and monthly counts reader
│   │   │   ├── block_port.py                # existing "is blocked?" interface (from 004/005)
│   │   │   └── router.py                    # block refusal on confirm and reschedule
│   │   └── reception/                       # cmp-reception (existing, extended)
│   │       └── router.py                    # block state and lift endpoints
│   ├── flags.py                             # release flag (from feature 001)
│   └── main.py                              # wires the real policy into the booking port
├── migrations/versions/                     # Alembic: no_show_block table
└── tests/
    ├── unit/
    ├── integration/
    └── contract/

clinic-web/                                  # repo brightsmile/clinic-web
├── src/
│   ├── pages/
│   │   ├── booking/                         # slot picker and reschedule screens (existing)
│   │   ├── reception/                       # patient panel (existing)
│   │   └── manager/NoShowReport.tsx         # no-show report screen (new)
│   ├── components/
│   │   ├── BlockedNotice.tsx                # "online booking is not available" with clinic phone
│   │   └── BlockBanner.tsx                  # reception banner and Lift action
│   └── services/                            # API calls
└── tests/
```

**Structure Decision**: Web application with two repositories. New code goes in two new backend modules named after their components and in existing modules where the architecture says they call each other; ctr-web gets one new page and two components. Folder names are an assumption that must match feature 001's scaffold (see research.md, R-009).

## Complexity Tracking

No constitution violations.
