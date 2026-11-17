# Implementation Plan: Full-text task search

**Branch**: `003-search` | **Date**: 2026-01-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-search/spec.md`

## Summary

Add `GET /api/v1/search/tasks` to taskflow-api (ARCH-001). It runs PostgreSQL full-text search (ARCH-003) against a stored `tsvector` over task title (weight A) and description (weight B) backed by a GIN index, restricted to the boards the caller belongs to. Results are cached per user and query in Redis (ARCH-004) with a short TTL and per-board version counters for invalidation. taskflow-web (ARCH-002) gets a keyboard-operable search box and results list. A load test proves p95 < 300 ms at 10,000 tasks. This feature owns the search endpoint, the GIN/tsvector migration and the search cache (implementation contract); the Task model (002-tasks-board) and users/boards/membership/auth (001-platform-foundation) are reused.

## Technical Context

**Language/Version**: Python 3.12 (taskflow-api, FastAPI); Node 22 + React (taskflow-web)

**Primary Dependencies**: FastAPI, Alembic (migrations, per contract), Redis 7 client already in `app/core/` (foundation), React

**Storage**: PostgreSQL 16 (generated `tsvector` column + GIN index on `tasks`); Redis 7 (search cache)

**Testing**: pytest in `tests/` (unit, integration, performance); component and accessibility tests in taskflow-web (test runner is the one set up by the web foundation)

**Target Platform**: Linux containers on AWS EKS, us-east-1 (dev, stg, prod)

**Project Type**: web application (api + SPA)

**Performance Goals**: p95 < 300 ms for search with 10,000 tasks (NFR-1); API p95 300 ms, error rate 1%

**Constraints**: results limited to the caller's boards (NFR-3); keyboard-only operable UI, WCAG 2.1 AA (NFR-4); no separate search engine; no secrets in code

**Scale/Scope**: 200 teams, peak 50 requests/second, 10,000 tasks in the load test

## Constitution Check

- I. Tests first: each story has an independent test; test tasks precede implementation. PASS
- II. Observability: structured logs, latency metric, trace span for search; readiness check for the search index. PASS
- III. Security baseline: membership enforced in SQL and in the cache key; inputs validated; no secrets. Authorization-related code gets explicit review (polish task). PASS
- IV. Traceability: requirements carry prd.md ids; every task names file paths. PASS
- V. Simplicity: one endpoint, one generated column, one index, one cache module; no search engine. PASS

Post-design re-check: PASS, no violations.

## Project Structure

### Documentation (this feature)

```text
specs/003-search/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── clarifications.md
├── contracts/
│   └── search-api.md
└── tasks.md
```

### Source Code

```text
# acme/taskflow-api
app/
├── api/search.py                  # router: GET /api/v1/search/tasks
├── schemas/search.py              # request/response schemas
├── services/search.py             # SQL full-text query, paging, excerpts
├── services/search_query.py       # query normalisation / validation
├── services/search_cache.py       # Redis cache, TTL, board version counters
└── services/search_telemetry.py   # log fields, metric, span
migrations/versions/003_task_search_index.py   # tsvector column + GIN index
tests/
├── unit/
├── integration/
└── performance/                   # seed + load test

# acme/taskflow-web
src/
├── api/search.ts
└── features/search/               # SearchBox, SearchResults, useTaskSearch, tests
```

**Structure Decision**: Web application across the two existing repositories using the module roots in the implementation contract (assumed paths marked (A) there). Shared files owned by other features (`app/main.py`, `app/services/tasks.py`, `app/api/health.py`, board page) receive small, coordinated edits only.

## Complexity Tracking

No constitution violations.
