# Implementation Plan: Platform foundation, access control and availability

**Branch**: `001-platform-foundation` | **Date**: 2026-01-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-platform-foundation/spec.md`

## Summary

Deliver the foundations every other TaskFlow feature builds on: three EKS environments (dev, stg, prod) in AWS us-east-1 with PostgreSQL 16 and Redis 7; CI/CD for taskflow-api (api + worker image) and taskflow-web; External Secrets delivering the database URL, Redis URL and email provider key from AWS Secrets Manager; the users / boards / board-membership schema with Alembic migrations; bearer-token authentication (assumed, Q1); one shared board-membership authorisation dependency that every board-scoped endpoint uses (NFR-3); and OpenTelemetry-based observability with external availability probing and SLO alerting (NFR-2: 99.5% monthly, p95 300 ms, error rate 1%). Covers NFR-2 and NFR-3.

## Technical Context

**Language/Version**: Python 3.12 (taskflow-api, notify-worker), Node 22 (taskflow-web); infrastructure as Terraform and Kubernetes manifests in acme/taskflow-infra (layout from the implementation contract, assumed).

**Primary Dependencies**: FastAPI (API), React SPA (web), Alembic (migrations, per contract), External Secrets (secrets), OpenTelemetry (constitution). Choices not named by architecture.md (assumed, to be confirmed by devops): SQLAlchemy as ORM used with Alembic, pytest for tests, GitHub Actions for CI (repositories are under the `acme` organisation), Terraform for AWS, Prometheus-compatible metrics scraping and Grafana-style dashboards, password hashing library such as argon2/bcrypt, a JWT-style signed bearer token. Each of these is an assumption recorded in research.md.

**Storage**: PostgreSQL 16 (ARCH-003) for users, boards, memberships; Redis 7 (ARCH-004) for board read cache (reused by later features) and login rate-limit counters.

**Testing**: pytest unit and integration tests against a real PostgreSQL 16 and Redis 7 in CI; route-coverage test for board-scoped authorisation; infrastructure validation (terraform validate/plan, kubernetes manifest lint) in the infra repo; secret scan in CI.

**Target Platform**: Linux containers on AWS EKS, us-east-1, environments dev/stg/prod.

**Project Type**: Web service plus SPA plus infrastructure repo (three repositories: acme/taskflow-api, acme/taskflow-web, acme/taskflow-infra).

**Performance Goals**: API p95 300 ms, error rate 1%, availability 99.5% monthly; peak 50 requests/second; 200 teams.

**Constraints**: Monthly infrastructure budget USD 2,500 across all environments; no secrets in Git; web app is the only public entry point; the worker uses the same image as the API with a different command; devops capacity is 50% of one person.

**Scale/Scope**: 200 teams of 5-30 people (roughly 1,000-6,000 users), 3 environments, 3 workloads (api, web, worker).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | How the plan satisfies it |
|---|---|---|
| I. Tests first for business logic | PASS | Each story phase in tasks.md starts with its tests (membership check, auth, migrations, route coverage). |
| II. Observability | PASS | US7 delivers OpenTelemetry logs/metrics/traces and a health check endpoint; shared helpers reused by new endpoints. |
| III. Security baseline | PASS | Secrets only via External Secrets; CI secret scan; auth and authorisation changes flagged for explicit review (CODEOWNERS); inputs validated by schemas at the boundary. |
| IV. Traceability | PASS | Stories and requirements cite NFR-2 / NFR-3; every task names file paths. |
| V. Simplicity | PASS | One authorisation dependency, one auth dependency, no separate auth service, no extra infrastructure beyond architecture.md components. |
| Technology constraints | PASS | Only ARCH-001..005 and the named tools; everything else is marked as an assumption in research.md. |

Post-design re-check: PASS (no violations; Complexity Tracking not needed).

## Project Structure

### Documentation (this feature)

```text
specs/001-platform-foundation/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── clarifications.md
├── contracts/
│   └── auth-and-membership-api.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (three repositories; paths from the implementation contract)

```text
acme/taskflow-api
├── app/
│   ├── main.py                      # FastAPI app, router registration, OTel setup
│   ├── api/
│   │   ├── auth.py                  # /api/v1/auth/*
│   │   ├── boards.py                # /api/v1/boards, members
│   │   └── health.py                # /healthz, /readyz
│   ├── core/
│   │   ├── config.py                # env vars (secrets, FEATURE_<NAME> flags)
│   │   ├── db.py                    # session factory
│   │   ├── redis.py                 # Redis client
│   │   ├── security.py              # password hashing, token issue/verify
│   │   ├── auth.py                  # get_current_user dependency
│   │   ├── authz.py                 # require_board_member dependency (shared, NFR-3)
│   │   └── telemetry.py             # logging, metrics, tracing
│   ├── models/                      # user.py, board.py, board_membership.py
│   ├── schemas/                     # auth.py, board.py
│   ├── services/                    # auth_service.py, board_service.py
│   └── worker/                      # worker entry point placeholder (F05 fills in)
├── migrations/                      # Alembic (env.py, versions/)
├── tests/
│   ├── unit/ integration/ contract/
├── Dockerfile
└── .github/workflows/               # ci.yml, deploy.yml

acme/taskflow-web
├── src/api/health.ts                # health/probe page support
├── Dockerfile or build output
└── .github/workflows/               # ci.yml, deploy.yml

acme/taskflow-infra
├── terraform/                       # modules: network, eks, rds-postgres, redis, secrets, monitoring; envs: dev, stg, prod
├── k8s/                             # base + overlays dev/stg/prod: api, web, worker, external-secrets, ingress
└── monitoring/                      # alert rules, dashboards, probes
```

**Structure Decision**: Three repositories as fixed by architecture.md and the implementation contract. Foundations are placed in `app/core/` (auth, authz, config, telemetry) so later features import them rather than recreate them.

## Complexity Tracking

No constitution violations; nothing to justify.
