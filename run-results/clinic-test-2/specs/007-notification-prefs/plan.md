# Implementation Plan: Notification preferences

**Branch**: `007-notification-prefs` | **Date**: 2026-01-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/007-notification-prefs/spec.md`

## Summary

Per-user notification preferences (FR-7, US-7): a preferences model with configurable channels and frequencies, a REST API, a keyboard-usable settings page, a single delivery-decision operation that the assignment, digest and mention senders consult, and a notify-worker job that sends one summary email for notifications held by an hourly or daily frequency. Email is the only enabled channel; the channel and frequency lists are configuration data because the client has not decided them (open question Q1). Everything is behind `FEATURE_NOTIFICATION_PREFS`.

## Technical Context

**Language/Version**: Python 3.12 (taskflow-api and notify-worker, ARCH-001/ARCH-005); Node 22 with React (taskflow-web, ARCH-002)

**Primary Dependencies**: FastAPI, Alembic (migrations, assumption A in the implementation contract), the email client and notification outbox owned by 005-notifications-email, per-user time zone owned by 006-daily-digest

**Storage**: PostgreSQL 16 (ARCH-003); three new tables, see [data-model.md](data-model.md)

**Testing**: pytest in `tests/` (assumption A in the contract); component tests for the React page (test runner of taskflow-web, not named in architecture.md, so the existing one is reused)

**Target Platform**: AWS EKS, `us-east-1`; api, web and worker are deployed by 001-platform-foundation

**Project Type**: web application (API + SPA) plus a worker in the API repository

**Performance Goals**: API p95 300 ms (service level); preferences read/write is a single-row-set query per user

**Constraints**: keyboard-only operation, WCAG 2.1 AA (NFR-4); a user only reads and writes own preferences (NFR-3); no secrets in code; inputs validated at the boundary; flag `FEATURE_NOTIFICATION_PREFS` read from the environment in `app/core/config.py`

**Scale/Scope**: 200 teams (5-30 people each) so at most about 6,000 users; 3 notification types x 1 channel per user

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Note |
|---|---|---|
| I. Tests first | PASS | Every story starts with test tasks; each story has an independent test in spec.md |
| II. Observability | PASS | Structured logs, a metric for fallback decisions, a health check endpoint (polish phase) |
| III. Security baseline | PASS | No secrets; own-data-only access; enum validation against configuration; the preference endpoints use the authentication owned by 001 |
| IV. Traceability | PASS | Stories and requirements carry `(source: ...)` ids; tasks name file paths |
| V. Simplicity | PASS | Three tables, one decision function, one worker job; no new service or channel beyond email |

Post-design re-check: PASS. No violations, no complexity tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/007-notification-prefs/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── clarifications.md
├── contracts/
│   ├── notification-preferences-api.md
│   └── delivery-decision.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
acme/taskflow-api
├── app/
│   ├── api/notification_preferences.py              # router (new)
│   ├── models/notification_preference.py            # channel, frequency, preference models (new)
│   ├── schemas/notification_preferences.py          # request/response schemas (new)
│   ├── services/notification_types.py               # notification type constants (new)
│   ├── services/notification_preferences.py         # get/save, resolve_delivery (new)
│   ├── services/notification_windows.py             # window end calculation (new)
│   ├── services/notification_summary.py             # summary email content (new)
│   ├── worker/jobs/send_notification_summaries.py   # notify-worker job (new)
│   └── core/config.py                               # FEATURE_NOTIFICATION_PREFS (edit, shared file)
├── migrations/versions/                             # one new migration (new)
└── tests/

acme/taskflow-web
├── src/api/notificationPreferences.ts               # API client (new)
└── src/features/notification-prefs/                 # settings page (new)
```

**Structure Decision**: Reuse the module roots of the implementation contract. The worker job lives in the same repository as the API (ARCH-005). Senders owned by 004, 005 and 006 are edited only to add the call to `resolve_delivery`.

## Cross-feature dependencies

- 001-platform-foundation: users table, authentication, current-user dependency, migration setup.
- 005-notifications-email: email client, notification outbox, assignment email. This plan needs the outbox to hold a notification with a "deliver after" time and a "held" state; to be confirmed with 005 (assumption).
- 006-daily-digest: per-user time zone, digest sender.
- 004-comments-mentions: mention sender.

## Complexity Tracking

No violations.
