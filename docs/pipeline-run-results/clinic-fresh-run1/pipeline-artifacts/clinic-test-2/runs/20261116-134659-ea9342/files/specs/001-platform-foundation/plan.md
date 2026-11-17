# Implementation Plan: Platform foundation, delivery and non-functional baseline

**Branch**: `001-platform-foundation` | **Date**: 2026-11-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-platform-foundation/spec.md`

## Summary

Build the technical foundation every other BrightSmile Booking feature runs on: three repositories (`brightsmile/clinic-api`, `brightsmile/clinic-web`, `brightsmile/clinic-infra`), a per-commit CI/CD pipeline with staging smoke test and rolling production deploy, dev/staging/prod environments with a secret store, a baseline PostgreSQL 16 schema (with `btree_gist`) with forward-only Alembic migrations, backups and a rehearsed restore, a mobile-first React + TypeScript shell with a single English catalogue and IST formatting, structured PII-free logging with a correlation id, `GET /health`, SLO probes and alerts, a feature-flag mechanism for Release 2, a load/scale verification, and a go-live readiness checklist for Release 1 (UAT-ready 2027-02-22, live 2027-03-01). The approach follows architecture.md: one FastAPI deployable (modular monolith, ADR-0001) with 8 module packages scaffolded empty, one managed PostgreSQL database, and a static SPA on a CDN.

## Technical Context

**Language/Version**: Python 3.12 (ctr-clinic-api); TypeScript with React (ctr-web); SQL for PostgreSQL 16 migrations

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic (ctr-clinic-api, architecture.md); React SPA (ctr-web); OpenTelemetry for logs, metrics and traces (constitution principle II). Supporting tools chosen in [research.md](./research.md) and confined to tests or infrastructure code: pytest, a contract-test tool against the OpenAPI file, an image scanner and secret scanner, a Playwright-style browser test runner, a Python load-test tool, and infrastructure as code (Terraform, the infra owner's declared skill; provider-neutral modules)

**Storage**: Managed PostgreSQL 16 with `btree_gist` (ctr-db); production with a synchronous HA standby in a second zone; encrypted snapshots (14 days) and continuous log archiving (PITR). The web app holds no data.

**Testing**: pytest (unit, integration against a real PostgreSQL 16, contract tests against `contracts/clinic-api-v1.openapi.yaml`); web unit tests plus automated responsive checks (no sideways scroll, 44 px tap targets, screen count) in Chromium and WebKit emulation, with a manual real-device pass on Android Chrome and iPhone Safari; load test against staging; log-PII test; restore rehearsal

**Target Platform**: Managed container service in an India cloud region (provider not yet fixed, Q1), CDN + load balancer + WAF at the edge; browsers: current Chrome and Safari on Android and iPhone, desktop browser at reception

**Project Type**: Web application: React SPA (`clinic-web`) + FastAPI API (`clinic-api`) + infrastructure repo (`clinic-infra`)

**Performance Goals**: Free slots shown within 2 s and booking confirmed within 3 s for 95% of requests on 4G (server p95 at most 500 ms and 800 ms); 100 concurrent users, design peak about 35 requests/s; 30 patients booking at once

**Constraints**: Online booking available 99.5% per month; reception screens available 08:00-20:00 IST Monday to Saturday; RPO 15 min, RTO 1 h; forward-only expand/contract migrations; no secrets in code, images or config; no names, phone numbers or birth years in logs; English only; times stored UTC and shown IST; tap targets at least 44 px; booking in 5 screens or fewer after sign-in; Release 1 live 2027-03-01 (firm)

**Scale/Scope**: Now 2 clinics, 6 dentists, about 450 appointments/week; later 3 clinics, 10 dentists, 1,000 appointments/week (about 0.5 GB of data at 3 years)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / rule | Status | How this plan satisfies it |
|---|---|---|
| I. Tests first for business logic; every story has an independent test | Pass | Every user story has an Independent Test; tasks list tests before implementation for the pipeline checks, IST conversion, PII-log guard, feature flags and responsive checks |
| II. Observability (structured logs, metrics, traces via OpenTelemetry; health check on new endpoints) | Pass | US7 delivers structured logging with correlation id, OpenTelemetry instrumentation, `GET /health`, probes and alerts |
| III. Security baseline (no secrets in code/config; inputs validated; auth changes reviewed) | Pass | Secret store + env vars, secret scan in CI, separate migration and application DB users; no auth changes in this feature; feature-flag changes are admin-tool only |
| IV. Traceability (source ids; exact file paths in tasks) | Pass | Stories and requirements cite NFR ids; tasks name repo-relative paths with the repo name as first segment |
| V. Simplicity | Pass | No broker, cache or gateway; no i18n library for one language; flags are a small table and tool, not a flag service |
| Technology constraint: follow architecture.md | Pass | Only architecture-named runtime technologies; supporting test/IaC tools listed in research.md as tooling decisions |
| DoD: no patient data in logs; unit and contract tests in CI; no new HIGH findings | Pass | FR-019 log guard test; CI contract test and image scan stages |

Post-design re-check (after Phase 1): Pass. No violations; Complexity Tracking not needed.

## Project Structure

### Documentation (this feature)

```text
specs/001-platform-foundation/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── clarifications.md    # Assumed answers to open questions Q1-Q3
├── contracts/           # Phase 1 output (health, feature flags, probe and checklist formats)
├── checklists/requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (three repositories; task paths start with the repository folder name)

```text
clinic-api/                                  # brightsmile/clinic-api (ctr-clinic-api)
├── pyproject.toml
├── Dockerfile
├── alembic.ini
├── migrations/
│   ├── env.py
│   └── versions/                            # 0001_baseline.py (btree_gist, privileges), 0002_feature_flags.py
├── src/clinic_api/
│   ├── main.py                              # app factory, /docs, router wiring
│   ├── config.py                            # env-var settings (secrets from environment only)
│   ├── observability/
│   │   ├── logging.py                       # structured JSON logs, PII scrubber
│   │   ├── correlation.py                   # correlation-id middleware
│   │   ├── telemetry.py                     # OpenTelemetry setup
│   │   └── metrics.py                       # request timing, SLI counters
│   ├── core/
│   │   ├── clock.py                         # UTC storage, IST conversion helpers
│   │   └── messages.py                      # English message catalogue for API messages
│   ├── db/
│   │   ├── session.py                       # SQLAlchemy engine/session, pool, statement timeout
│   │   └── models/feature_flag.py
│   ├── api/
│   │   ├── health.py                        # GET /health
│   │   └── feature_flags.py                 # GET /api/v1/feature-flags
│   ├── tools/set_flag.py                    # admin tool, records who/when
│   └── modules/                             # 8 empty module packages (ADR-0001)
│       ├── identity/ scheduling/ booking/ reception/
│       └── noshow_policy/ messaging/ channel_adapters/ reporting/
├── tests/
│   ├── unit/ integration/ contract/
│   └── load/                                # load test and scale data seeder
├── scripts/ run_migrations.sh  post_deploy_gate.py
└── .github/workflows/ ci.yml  deploy.yml

clinic-web/                                  # brightsmile/clinic-web (ctr-web)
├── package.json
├── src/
│   ├── main.tsx  App.tsx
│   ├── layout/ PatientLayout.tsx  StaffLayout.tsx
│   ├── components/ Button.tsx  TextField.tsx  ListRow.tsx   # >= 44 px targets
│   ├── i18n/ en.ts  t.ts                    # single English catalogue
│   ├── time/ ist.ts                         # IST formatting from UTC
│   ├── flags/ useFlags.ts                   # feature flags from API
│   ├── journeys/ booking-journey.ts         # screen budget (<= 5 after sign-in)
│   └── routes/                              # placeholder patient and staff routes
├── tests/ unit/ responsive/
└── .github/workflows/ci.yml

clinic-infra/                                # brightsmile/clinic-infra
├── modules/ (web-hosting, container-service, database, secrets, edge, monitoring)
├── envs/ dev/ staging/ prod/
├── monitoring/ probes/ alerts/ slo-report/
└── docs/ rollback.md  restore-runbook.md  go-live-readiness.md
```

**Structure Decision**: Web application with three repositories as set in the constitution and project settings. All runtime code follows architecture.md (one FastAPI deployable with 8 module packages, one database, one static SPA). The infrastructure repo holds environments, monitoring and runbooks.

## Complexity Tracking

No constitution violations to justify.
