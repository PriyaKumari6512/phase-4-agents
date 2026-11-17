# Implementation contract (derived from architecture.md)

Items marked (A) are assumptions: architecture.md does not state them.

## Repositories and module roots
- `acme/taskflow-api` (Python 3.12, FastAPI): API package root `app/` (A). Sub-packages `app/api/` (routers), `app/models/`, `app/services/`, `app/schemas/`, `app/core/` (config, auth, db, redis) (A). Tests in `tests/` (A).
- `notify-worker` (ARCH-005) lives in the SAME repo and image as taskflow-api: `app/worker/` (A), started with a different command (architecture.md). Jobs in `app/worker/jobs/` (A).
- `acme/taskflow-web` (Node 22, React SPA): source root `src/`, features in `src/features/<feature>/` (A), API client in `src/api/` (A).
- `acme/taskflow-infra` (infra repo from project.json): Terraform / Kubernetes manifests (A layout: `terraform/`, `k8s/`). Environments `dev`, `stg`, `prod`, AWS us-east-1, EKS.

## API
- Prefix: `/api/v1` (A). JSON REST. Board updates via server-sent events at `/api/v1/boards/{board_id}/events` (SSE per architecture.md; path is A), backed by Redis pub/sub.
- Auth: every board-scoped endpoint enforces board membership (NFR-3). Auth mechanism is not stated in architecture.md (A: bearer token session; to be confirmed).
- Service levels: API p95 300 ms, error rate 1%, availability 99.5% monthly.

## Database
- PostgreSQL 16 (ARCH-003). Migrations directory in taskflow-api: `migrations/` (Alembic) (A). One migration per feature, never edit a merged migration.
- Search: GIN index on a tsvector over task title and description (architecture.md); no separate search engine.
- Redis 7 (ARCH-004): caches board reads and search results, and carries pub/sub for SSE.

## Secrets and config
- Database URL, Redis URL, email provider key in AWS Secrets Manager via External Secrets; nothing secret in Git. Read via environment variables in `app/core/config.py` (A).

## Feature flags (A)
- Flags read from env `FEATURE_<NAME>` (A): `FEATURE_COMMENTS`, `FEATURE_DIGEST`, `FEATURE_NOTIFICATION_PREFS`, `FEATURE_BURNDOWN`, `FEATURE_CSV_EXPORT`. Each owned by its feature; default off in prod until released.

## Foundation ownership
| Foundation | Owning feature |
|---|---|
| Repos CI, EKS environments dev/stg/prod, External Secrets, Postgres, Redis, observability and availability monitoring, deployment of api/web/worker | F01 platform-foundation |
| Users, boards, board membership, auth, authorisation check (NFR-3), base DB schema and migration setup | F01 platform-foundation |
| Task model and CRUD, board columns, SSE/Redis pub/sub board updates, board UI, keyboard accessibility | F02 tasks-board |
| Search endpoint, GIN index, search cache | F03 search |
| Comments and mentions model, mention parsing | F04 comments-mentions |
| Email provider client, notify-worker skeleton, assignment email, outbox of notifications | F05 notifications-email |
| Daily digest scheduler, per-user time zone | F06 daily-digest |
| Notification preferences model and UI | F07 notification-prefs |
| Sprint model, burndown report, CSV export | F08 reports-export |

Features that depend on a foundation must reuse it, not recreate it. Mention notifications (F04) use the notification outbox and email client owned by F05; preferences (F07) are consulted by F05/F06 senders.
