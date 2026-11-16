# Implementation Plan: Burndown report and CSV export

**Branch**: `008-reports-export` | **Date**: 2026-01-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/008-reports-export/spec.md`

## Summary

Add a minimal sprint entity, a per-board burndown report (remaining story points per day of the current sprint) and a per-board CSV export. The API (taskflow-api, ARCH-001) stores sprints and one daily record per sprint day in PostgreSQL (ARCH-003). The remaining points for a past day come from a stored daily record; today's value is computed live from the task table when the report is opened. A scheduled daily job in the worker image writes the records. The web app (taskflow-web, ARCH-002) shows a keyboard-accessible chart with an equivalent table, a sprint form and an Export button. The CSV is streamed by the API with formula-injection protection. Sprints and burndown sit behind `FEATURE_BURNDOWN`; the export sits behind `FEATURE_CSV_EXPORT`.

## Technical Context

**Language/Version**: Python 3.12 (taskflow-api); Node 22 with React (taskflow-web), from architecture.md

**Primary Dependencies**: FastAPI (architecture.md); React (architecture.md). Chart rendering approach: plain SVG drawn by a React component, so no new charting library is chosen (architecture.md names none). Alembic for migrations, pytest for tests, and the web test runner are contract assumptions (A) or follow the repo's existing tooling.

**Storage**: PostgreSQL 16 (ARCH-003): new tables `sprints` and `sprint_burndown_records`. Redis (ARCH-004) is not used by this feature (reports are computed on request; no caching, to keep today's value live).

**Testing**: pytest in `tests/` (A, contract); web component tests with the repo's existing test runner. Business logic tests are written first (constitution principle I).

**Target Platform**: EKS (Kubernetes) on AWS us-east-1; environments dev, stg, prod.

**Project Type**: Web application (REST API + React SPA) plus a scheduled worker job in the same repo/image as the API.

**Performance Goals**: API p95 300 ms, error rate 1%, availability 99.5% monthly (architecture.md service levels). Burndown read is one query per sprint (at most a few dozen rows plus one aggregate), well within the 300 ms budget. CSV export is streamed, not part of the interactive p95 target (assumption).

**Constraints**: Only board members see board data (NFR-3). Keyboard-only use (NFR-4). No secrets in code; flags read from env `FEATURE_BURNDOWN` and `FEATURE_CSV_EXPORT` in `app/core/config.py`. Inputs validated at the boundary. New endpoints emit structured logs and metrics (constitution II).

**Scale/Scope**: 200 teams, peak 50 requests/second (architecture.md). Boards up to about 10,000 tasks (the PRD's search scale, used as an upper bound for the export).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | How |
|-----------|--------|-----|
| I. Tests first for business logic | Pass | Test tasks come before implementation tasks in each story (burndown computation, CSV sanitising, sprint validation, authorisation). |
| II. Observability | Pass | Structured logs and metrics for the new endpoints and the snapshot job; the job reports success or failure per run. Health checks come from the platform foundation (F01); no new service is introduced. |
| III. Security baseline | Pass | No secrets added. Membership check on every endpoint (reuse F01). Inputs validated by pydantic schemas. CSV formula injection neutralised. |
| IV. Traceability | Pass | Stories and requirements cite prd.md ids; every task names file paths. |
| V. Simplicity | Pass | Two tables, no cache, no charting library, no ideal line, no per-task sprint assignment. |

Post-design re-check: still pass. No violations; Complexity Tracking not needed.

## Project Structure

### Documentation (this feature)

```text
specs/008-reports-export/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── clarifications.md
├── contracts/
│   └── reports-api.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

Paths follow `backlog/implementation-contract.md` (module roots are assumptions there). Shared modules (auth, membership check, DB session, task model, board UI) are owned by 001 and 002 and are reused, not recreated.

```text
acme/taskflow-api
├── app/
│   ├── api/
│   │   ├── sprints.py            # sprint endpoints (FEATURE_BURNDOWN)
│   │   ├── reports.py            # burndown endpoint (FEATURE_BURNDOWN)
│   │   └── export.py             # CSV export endpoint (FEATURE_CSV_EXPORT)
│   ├── core/
│   │   └── config.py             # add the two flags (file owned by F01, extended here)
│   ├── models/
│   │   ├── sprint.py
│   │   └── sprint_burndown_record.py
│   ├── schemas/
│   │   ├── sprint.py
│   │   └── burndown.py
│   ├── services/
│   │   ├── sprint_service.py
│   │   ├── burndown_service.py
│   │   └── csv_export_service.py
│   └── worker/jobs/
│       └── burndown_snapshot.py  # daily job
├── migrations/versions/          # one migration for this feature
└── tests/
    ├── unit/
    ├── integration/
    └── contract/

acme/taskflow-web
└── src/
    ├── api/reports.ts
    └── features/reports/
        ├── BurndownPage.tsx
        ├── BurndownChart.tsx
        ├── BurndownTable.tsx
        ├── SprintForm.tsx
        └── ExportButton.tsx

acme/taskflow-infra
└── k8s/burndown-snapshot-cronjob.yaml   # daily job, same image as the API (A layout)
```

**Structure Decision**: Web application layout from the implementation contract: API code in `app/` of taskflow-api, UI code in `src/features/reports/` of taskflow-web, the job under `app/worker/jobs/` (same repo and image as the API, as architecture.md requires for the worker), one Alembic migration in `migrations/`.

## Design Decisions

1. **Daily snapshot for remaining points (design choice requested in the brief).** The task model keeps no history of column moves, so past days cannot be rebuilt from tasks alone. A table `sprint_burndown_records (sprint_id, day, remaining_points)` stores one row per sprint day. A daily job writes the row for the day that just ended. When the report is opened, today's value is computed live and upserted, so the report is correct even if the job is late. Days without a row get the last known value carried forward. Alternatives are in research.md.
2. **Remaining points** = sum of `story_points` of all tasks on the board minus the sum of `story_points` of tasks in the Done column; null counts as 0 (assumption A1/A2, open question Q1 kept open).
3. **Current sprint** = sprint whose `start_date <= today(UTC) <= end_date`; overlapping sprints on one board are rejected at write time (assumption A3, A6).
4. **Roles**: sprint writes need the manager role from the F01 membership (assumption A4); reads and export need membership only.
5. **CSV**: streamed response, UTF-8, RFC 4180 quoting, columns read from the task model's field list in one place so they follow 002 (assumption A8); cells starting with `=`, `+`, `-`, `@`, tab or CR get a leading single quote.
6. **Flags**: when a flag is off, its endpoints return 404 and the web hides the entry point (the web learns this from a 404 on first use; there is no new config endpoint).
7. **Scheduling**: a Kubernetes CronJob running the worker image with a different command (A); F06 owns a daily digest scheduler, but this job does not depend on it. If F06's scheduler is available when implementing, switching to it is a deployment change only.

## Complexity Tracking

No violations to justify.
