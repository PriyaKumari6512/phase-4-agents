# TaskFlow — Architecture

## Context

TaskFlow is a web application for small teams (target: 200 teams, peak 50 requests/second). It runs on AWS in
`us-east-1` on Kubernetes (EKS), with three environments: `dev`, `stg` and `prod`. Monthly infrastructure budget:
USD 2,500 across all environments.

## Components

| Id | Component | Kind | Runtime | Repository | Depends on | Notes |
|---|---|---|---|---|---|---|
| ARCH-001 | taskflow-api | service | Python 3.12, FastAPI | acme/taskflow-api | ARCH-003, ARCH-004 | REST API for tasks, boards, comments, search, reports and CSV export. Serves HTTP. Confidential data. |
| ARCH-002 | taskflow-web | frontend | Node 22, React | acme/taskflow-web | ARCH-001 | Single-page app; the only public entry point. Public data only (static assets). |
| ARCH-003 | taskflow-db | database | PostgreSQL 16 | — | — | System of record for tasks, boards, comments, users. Confidential. |
| ARCH-004 | taskflow-cache | cache | Redis 7 | — | — | Caches board reads and search results. |
| ARCH-005 | notify-worker | worker | Python 3.12 | acme/taskflow-api | ARCH-003 | Sends assignment emails and the daily digest through the email provider's API. Confidential. |

## Key decisions

- Board updates reach other viewers through server-sent events from taskflow-api, backed by Redis pub/sub.
- Search uses PostgreSQL full-text search (GIN index) before considering a separate search engine.
- The worker shares the taskflow-api repository and image, started with a different command.
- Secrets (database URL, Redis URL, email provider key) live in AWS Secrets Manager and reach pods through
  External Secrets; nothing secret is stored in Git.

## Service levels

- API latency p95: 300ms
- Error rate: 1%
- Availability: 99.5% monthly
