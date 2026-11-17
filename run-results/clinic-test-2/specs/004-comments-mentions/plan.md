# Implementation Plan: Comments and @mentions

**Branch**: `004-comments-mentions` | **Date**: 2026-01-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-comments-mentions/spec.md`

## Summary

Board members comment on tasks; `@username` mentions of current board members create a mention record and hand one
email notification per mentioned member to the notification outbox owned by feature 005-assignment-email. The
comment and its notification request are saved in one database transaction, so a slow or failing email provider
never blocks or loses a comment. The notify-worker (ARCH-005, same repo) sends the emails. Everything sits behind
the feature flag `FEATURE_COMMENTS`. Covers FR-3, US-3, NFR-3, NFR-4.

## Technical Context

**Language/Version**: Python 3.12 (taskflow-api, notify-worker); Node 22 with React (taskflow-web)

**Primary Dependencies**: FastAPI (architecture.md); SQLAlchemy and Alembic are assumed from the implementation contract (A: `migrations/` is Alembic); React for the UI. No new libraries.

**Storage**: PostgreSQL 16 (ARCH-003), system of record for comments. Redis (ARCH-004) is not used by this feature.

**Testing**: pytest in `tests/` (A) for api and worker; a React test runner for web is not named in architecture.md (A: to be fixed by feature 001/002 setup; tasks use `src/features/comments/__tests__/`).

**Target Platform**: AWS EKS us-east-1, environments dev/stg/prod (architecture.md)

**Project Type**: web application (taskflow-api + taskflow-web + shared worker)

**Performance Goals**: API p95 300 ms (service levels); mention email within 1 minute (spec SC-001, assumption A7)

**Constraints**: only board members read/post/get mentioned (NFR-3); keyboard usable (NFR-4); no secrets in code; flag `FEATURE_COMMENTS` read from env in `app/core/config.py`

**Scale/Scope**: 200 teams, 50 requests/second peak (architecture.md); comments are low volume. Maximum comment length 5,000 characters (assumption A5).

## Constitution Check

| Principle | Status |
|---|---|
| I. Tests first | Pass: unit tests for the parser and integration tests for each story are tasks that precede the implementation tasks |
| II. Observability | Pass: structured logs and metrics for comment create and mention notification enqueue; endpoints covered by the existing health checks (feature 001) |
| III. Security baseline | Pass: membership check on every endpoint, input validated at the boundary (length, non-empty), no secrets; auth changes: none |
| IV. Traceability | Pass: source ids kept in spec and tasks name exact paths |
| V. Simplicity | Pass: two tables, one parser function, no autocomplete, no edit/delete |

Post-design re-check: pass. No complexity violations.

## Shared foundations reused (implementation contract)

- Users, boards, membership and the authorisation check: feature 001 (`app/core/`). Not recreated here.
- Task model: feature 002 (`app/models/`). Comments reference tasks by foreign key.
- Notification outbox, email client and notify-worker skeleton: feature 005-assignment-email. This feature only enqueues a "mention" notification and adds a mention email template to F05's template mechanism. The exact enqueue function name and module are not in the contract (A: reuse whatever F05 exposes in `app/services/`; the task for it is marked to confirm against F05).
- Preferences: feature 007 is consulted by the F05/F06 senders (contract); this feature does nothing extra.

## Project Structure

### Documentation (this feature)

```text
specs/004-comments-mentions/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── clarifications.md
├── contracts/comments-api.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code

```text
# taskflow-api (acme/taskflow-api)
app/
├── api/comments.py              # router: GET/POST task comments
├── models/comment.py            # Comment, CommentMention
├── schemas/comment.py           # request/response schemas, validation
├── services/mentions.py         # mention parsing and resolution against board members
├── services/comments.py         # create/list comments, enqueue mention notifications
├── core/config.py               # shared file: add FEATURE_COMMENTS setting
└── worker/jobs/                 # F05 owns; only the mention email template is added by this feature
migrations/versions/             # one migration for this feature
tests/
├── unit/test_mentions.py
└── integration/test_comments_api.py, test_mention_notifications.py

# taskflow-web (acme/taskflow-web)
src/
├── api/comments.ts
└── features/comments/ (CommentList.tsx, CommentForm.tsx, __tests__/)
```

**Structure Decision**: Web application layout from the implementation contract. Module roots are `app/` in taskflow-api and `src/features/comments/` in taskflow-web.

## Complexity Tracking

No violations.
