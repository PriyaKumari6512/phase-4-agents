# Implementation Plan: No-show report per clinic and month

**Branch**: `010-noshow-report` | **Date**: 2027-03-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/010-noshow-report/spec.md`

## Summary

The practice manager sees, per clinic and for each of the last 12 months (IST), the number of no-shows and the no-show rate (no-shows ÷ appointments not cancelled), on screen only (source: FR-032). MOD-08, Release 2, DL-2 2027-03-19 (not hard); estimate 3–5 person-days (scope/estimate.md).

Approach (from architecture.md): a new `cmp-reporting` module in `ctr-clinic-api` (repo `brightsmile/clinic-api`) exposes one read-only endpoint. It asks `cmp-booking` in-process for appointment counts grouped by clinic, IST month and status, and turns them into counts and rates. A new screen in `ctr-web` (repo `brightsmile/clinic-web`) shows one table per clinic. Access is practice manager only (RBAC through `cmp-identity`). The screen and the endpoint are hidden by a Release 2 feature flag until ready. No new table, no new migration, no message, no export.

## Technical Context

**Language/Version**: Python 3.12 (ctr-clinic-api); TypeScript with React (ctr-web)

**Primary Dependencies**: FastAPI, SQLAlchemy (Alembic present but not needed here) in ctr-clinic-api; React SPA in ctr-web (as named in architecture.md)

**Storage**: PostgreSQL 16 (ctr-db), read only; reads `ent-appointment` through `cmp-booking`. No new storage.

**Testing**: pytest (unit, integration against PostgreSQL, contract tests against the OpenAPI file) in clinic-api; the web app's existing component test setup in clinic-web. Tests are written before or with the code (constitution I).

**Target Platform**: Managed container service (API) and CDN static hosting (web); practice manager on a desktop browser.

**Project Type**: web application: two repositories (brightsmile/clinic-api, brightsmile/clinic-web)

**Performance Goals**: Report within 3 s for 95% of requests (spec SC-002). Data size is small: about 52,000 appointments a year, three clinics, so one grouped query is enough; no cache (architecture "not used").

**Constraints**: Months in IST (NFR-008); no patient data in logs (constitution DoD); role and clinic scoping enforced in the API, not only in the web app (QA-007); feature flag hides the R2 screen until ready; report on screen only (export is a non-goal).

**Scale/Scope**: 2 clinics now, 3 later; 12 months; 1 endpoint, 1 screen, 3 user stories, about 25 tasks.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Tests first for business logic | Rate, month window, status mapping and IST boundary have unit and integration tests, listed before the implementation tasks of each story | Pass |
| II. Observability | The report service writes structured logs with a correlation id and emits an OpenTelemetry metric and trace span; the service already has `GET /health` and no new service is added | Pass |
| III. Security baseline | RBAC to practice manager enforced server side; no secrets; the flag is a plain setting; inputs: the endpoint takes no free-text input | Pass |
| IV. Traceability | Spec stories and requirements cite FR-032; every task names a file path and repo | Pass |
| V. Simplicity | One query, no new table, no cache, no export, no generic reporting framework | Pass |
| Technology constraints | Only technologies in architecture.md; repos brightsmile/clinic-api and brightsmile/clinic-web | Pass |

Post-design re-check: still passes; there are no violations to justify (Complexity Tracking empty).

## Project Structure

### Documentation (this feature)

```text
specs/010-noshow-report/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── clarifications.md    # Assumed answers (Q1-Q3)
├── contracts/
│   └── no-show-report.openapi.yaml   # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code

```text
# repo brightsmile/clinic-api (ctr-clinic-api)
app/
├── core/config.py                              # feature flag setting
├── main.py                                     # registers the reporting router
└── modules/
    ├── booking/reporting_interface.py          # cmp-booking: counts by clinic, IST month, status (in-process)
    └── reporting/                              # cmp-reporting (new)
        ├── __init__.py
        ├── calc.py                             # 12-month window and rate (pure functions)
        ├── dependencies.py                     # flag check, manager-only access
        ├── router.py                           # GET /api/reports/no-shows
        ├── schemas.py                          # response models
        └── service.py                          # builds the report
contracts/clinic-api-v1.openapi.yaml            # new path added
tests/
├── contract/test_noshow_report_contract.py
├── integration/booking/test_appointment_counts_by_month.py
├── integration/reporting/test_noshow_report_rbac.py
├── integration/reporting/test_noshow_report_flag.py
├── integration/reporting/test_noshow_report_perf.py
└── unit/reporting/test_calc.py

# repo brightsmile/clinic-web (ctr-web)
src/
├── config/featureFlags.ts                      # flag for the R2 screen
├── api/noShowReport.ts                         # API client and types
├── pages/NoShowReport/
│   ├── NoShowReportPage.tsx
│   └── NoShowReportPage.test.tsx
├── routes/staffRoutes.tsx                      # route behind flag and role
└── components/StaffMenu.tsx                    # menu entry, manager only, behind flag
```

**Structure Decision**: Web application split over the two repositories named in the constitution. The new backend code is the `reporting` module beside the existing modules in ctr-clinic-api; the only change inside `cmp-booking` is one read-only counting function. File names follow the layout the architecture implies (one module per component); a task confirms the real layout of each repo before the first edit.

## Complexity Tracking

No violations.
