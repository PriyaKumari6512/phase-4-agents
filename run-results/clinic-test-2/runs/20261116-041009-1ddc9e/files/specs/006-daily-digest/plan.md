# Implementation Plan: Daily due-tomorrow digest

**Branch**: `006-daily-digest` | **Date**: 2026-01-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/006-daily-digest/spec.md`

## Summary

Once per user per local day, at or after 08:00 in the user's time zone, the notify-worker (ARCH-005) emails the user the open tasks assigned to them that are due on the next local calendar date. The feature owns the per-user time zone field (column, API, settings control), the digest scheduler job and the delivery record that guarantees exactly-once. The worker is started by a Kubernetes CronJob every 5 minutes (assumption A1, Q1). Each tick selects users whose local time has reached 08:00 and who have no delivery record for their local date, claims the record with a unique key, builds the email and sends it through the email client owned by feature 005. Everything is behind `FEATURE_DIGEST` (default off in prod).

## Technical Context

**Language/Version**: Python 3.12 (taskflow-api and notify-worker, same repo and image); Node 22 / React for the one settings control in taskflow-web

**Primary Dependencies**: FastAPI (existing), Python standard `zoneinfo` for IANA zones (standard library, no new dependency), email client and worker skeleton from feature 005 (reused, not created here), OpenTelemetry per constitution

**Storage**: PostgreSQL 16 (ARCH-003): one new column `users.timezone`, one new table `digest_deliveries`; migration in `migrations/` (Alembic, A). No Redis use.

**Testing**: pytest in `tests/` (A) with a controllable clock; frontend component test in taskflow-web (framework per F01 setup)

**Target Platform**: EKS (dev, stg, prod); worker runs as a CronJob from the taskflow-api image

**Project Type**: web application with a worker (acme/taskflow-api, acme/taskflow-web, acme/taskflow-infra)

**Performance Goals**: digest within 15 minutes after local 08:00 for 99% of digests (SC-002); the API setting endpoint stays within the service-level p95 of 300 ms

**Constraints**: exactly-once per user and local date; DST-correct; no secrets in code (email key comes from External Secrets via F05); board membership enforced (NFR-3); keyboard-accessible control (NFR-4)

**Scale/Scope**: target 200 teams of 5-30 people, so about 6,000 users at most; one tick evaluates all users in a single indexed query

## Constitution Check

| Principle | Status |
|---|---|
| I. Tests first | Pass: test tasks precede implementation in each story |
| II. Observability | Pass: structured logs, metrics and traces per run; a health signal for the CronJob (FR-013) |
| III. Security baseline | Pass: time zone validated at the boundary; no secrets; endpoint touches only the caller's own profile; membership filter in the query |
| IV. Traceability | Pass: source ids in spec; every task names file paths |
| V. Simplicity | Pass: one table, one column, one job; CronJob rather than a custom scheduler |

Re-check after design: no violations, Complexity Tracking not needed.

## Project Structure

### Documentation (this feature)

```text
specs/006-daily-digest/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── clarifications.md
├── contracts/
│   └── timezone-api.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

Paths follow `backlog/implementation-contract.md` (module roots marked (A) there are assumptions).

```text
acme/taskflow-api
├── migrations/versions/006_user_timezone_digest_deliveries.py   # new migration
├── app/core/config.py                      # edit: FEATURE_DIGEST flag (owned here)
├── app/models/user.py                      # edit (F01 file): add timezone column
├── app/models/digest_delivery.py           # new
├── app/schemas/timezone.py                 # new
├── app/api/timezone.py                     # new: GET/PUT /api/v1/users/me/timezone
├── app/services/digest_schedule.py         # new: local time, due test, tomorrow
├── app/services/digest_query.py            # new: users due now, tasks per user
├── app/services/digest_delivery.py         # new: claim / mark sent / mark failed
├── app/services/digest_email.py            # new: subject and body composition
├── app/services/digest_preferences.py      # new: consults 007 when present
├── app/worker/jobs/daily_digest.py         # new: job run by the CronJob
└── tests/{unit,integration,contract}/      # new test files

acme/taskflow-web
├── src/api/timezone.ts                     # new
└── src/features/digest/TimeZoneSetting.tsx # new (+ test)

acme/taskflow-infra
└── k8s/notify-worker/digest-cronjob.yaml   # new
```

Reused and not created here: the email client module and the worker skeleton/entry point from feature 005 (`app/worker/`), the `users`, `boards`, membership and `tasks` tables and the auth dependency from features 001 and 002.

**Structure Decision**: web application with worker, as in the contract; the digest job sits in `app/worker/jobs/`, business logic in `app/services/` so it is unit-testable without the worker.

## Complexity Tracking

No violations.
