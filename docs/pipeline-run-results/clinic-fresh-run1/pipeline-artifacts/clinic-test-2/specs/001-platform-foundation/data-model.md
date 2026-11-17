# Data Model: Platform foundation

This feature creates only the baseline of the database. Business tables (appointments, patients, messages and so on) belong to the features that own them; this baseline gives them the extension and roles they need.

## Database baseline (migration 0001; feature flag tables follow in migration 0002)

| Item | Detail |
|---|---|
| Extension | `btree_gist` (needed by the no-overlap exclusion constraint for appointments, ADR-0003, built in feature 004) |
| Versioning | Alembic `alembic_version`; forward-only (no production downgrade), every change expand then contract |
| Users | `migrator` (DDL, used only by the pipeline) and `app` (read/write on tables, no DDL) |
| Time | All timestamps are `timestamptz` stored as UTC; display conversion to IST is in the web app and message builders |

## Entity: feature_flag (created by migration 0002; owned by ctr-clinic-api core)

| Field | Type | Rules |
|---|---|---|
| key | text, primary key | lowercase words with dots, for example `r2.family-members`, `r2.noshow-block`, `r2.noshow-report`, `r2.reminders-failed-list`, `r2.sms-fallback` |
| enabled | boolean | default false |
| description | text | plain English |
| updated_at | timestamptz | UTC |
| updated_by | text | tool operator id (not personal data) |

## Entity: feature_flag_change

| Field | Type | Rules |
|---|---|---|
| id | bigint, primary key | |
| key | text, foreign key to feature_flag | |
| old_value | boolean | |
| new_value | boolean | |
| changed_by | text | operator id |
| changed_at | timestamptz | UTC |

State transition: `enabled` false to true or true to false; every transition writes one `feature_flag_change` row in the same transaction.

## Non-database records

| Record | Where | Fields |
|---|---|---|
| Probe result | monitoring service (chosen provider) | time, probe kind (health, slot read), status, duration |
| SLO report | `clinic-infra/monitoring/slo-report/` output file | month, booking availability, reception-hours availability, free-slot p95, booking p95, reminder on-time share, reminders sent for cancelled |
| Restore record | `clinic-infra/docs/restore-runbook.md` | date, snapshot used, point in time, duration, result |
| Load test report | `clinic-api/tests/load/reports/` | date, environment size, data set, users, p95 per route, errors |
| Readiness item | `clinic-infra/docs/go-live-readiness.md` | id, item, owner, due date, status, evidence link, risk note |

## Data protection

No personal data is stored by this feature. Log, probe and test records hold ids only; the load-test seed data uses synthetic names and numbers that never appear in logs.
