# Implementation Plan: WhatsApp to SMS fallback and reminders-failed list

**Branch**: `009-sms-fallback-failed-list` | **Date**: 2026-11-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-sms-fallback-failed-list/spec.md`

## Summary

On the final failure of a WhatsApp reminder (provider error after 3 attempts, or a failed receipt on webhook rel-010), `cmp-messaging` creates exactly one SMS message linked to the original (unique key on the original message, thr-018) and sends it through the SMS adapter in `cmp-channel-adapters`. If the SMS also fails (provider error or failed receipt on rel-009), the `ent-message` status becomes `reminder_failed`. A configuration switch (default on) turns the fallback off; with it off a finally failed WhatsApp reminder is marked `reminder_failed` directly. The fallback skips opted-out patients (STOP) and cancelled appointments. `cmp-reception` exposes `GET /api/reception/reminders-failed` (tomorrow in IST, own clinic, receptionist only), reading through the `cmp-messaging` interface. `ctr-web` gets a "Reminders failed" screen for reception, hidden by the Release 2 feature flag.

This builds on feature 006 (dispatcher, `ent-message`, adapters, webhooks). No new component, container or technology is added. Open question Q1 (client agreement on the fallback) is assumed answered "build behind a switch, default on" (see `clarifications.md`).

## Technical Context

**Language/Version**: Python 3.12 (ctr-clinic-api, repo `brightsmile/clinic-api`); TypeScript with React (ctr-web, repo `brightsmile/clinic-web`)

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic (clinic-api); React SPA (clinic-web), as in architecture.md. No new libraries.

**Storage**: PostgreSQL 16 (ctr-db), table of `ent-message` (one forward-only, expand-only migration)

**Testing**: pytest for clinic-api (unit, integration, contract tests against `contracts/clinic-api-v1.openapi.yaml`); the web app's existing test runner for clinic-web. Provider sandboxes in staging for the quickstart.

**Target Platform**: Managed container service (ctr-clinic-api, 2 replicas); static CDN (ctr-web)

**Project Type**: web application (API + SPA), two repositories

**Performance Goals**: Fallback SMS created in the same dispatcher cycle (30 s) as the final failure, within the 15-minute reminder window (QA-004); list returned within 500 ms server-side for up to 50 rows (reception screens, SC-004)

**Constraints**: Fallback created at most once per original message (thr-018); replayed receipts idempotent; SMS only through DLT-registered templates (NFR-011, CON-003); no name or phone in logs (constitution, NFR-007); receptionist scoped to own clinic (NFR-006, thr-007); R2 screen behind a feature flag; times in IST (NFR-008)

**Scale/Scope**: About 1,000 reminders a week at 3 clinics; a failed list of at most a few dozen rows a day; 1 endpoint, 1 screen, 1 migration

## Constitution Check

| Principle | Status | How |
|---|---|---|
| I. Tests first for business logic | Pass | Each story starts with test tasks (fallback once, guards, marking, scoping, screen) |
| II. Observability | Pass | Structured logs and OpenTelemetry counters for every fallback decision (FR-013); the new endpoint sits behind the existing `GET /health`-covered service |
| III. Security baseline | Pass | No secrets added; the switch is an environment setting; webhook HMAC already checked in 006; list endpoint authorised by role and clinic from the access context, never from request parameters |
| IV. Traceability | Pass | Spec items cite prd.md ids; every task names a repo and file path |
| V. Simplicity | Pass | No new component or table; one nullable column with a unique index, one status value, one query, one endpoint, one screen |

No violations; Complexity Tracking is empty. Re-checked after design: still passing.

## Project Structure

### Documentation (this feature)

```text
specs/009-sms-fallback-failed-list/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── clarifications.md
├── contracts/
│   └── reminders-failed.openapi.yaml
├── checklists/requirements.md
└── tasks.md
```

### Source Code

The folder layout follows what feature 006 creates in each repository; the paths below are the intended ones and are adjusted to 006's real layout when implementing.

```text
# repo brightsmile/clinic-api (ctr-clinic-api)
app/
├── core/config.py                      # fallback switch setting (default on)
├── messaging/                          # cmp-messaging
│   ├── models.py                       # ent-message: fallback_of_message_id, status reminder_failed
│   ├── repository.py                   # create-fallback-once, failed lookups
│   ├── fallback.py                     # fallback decision and creation
│   ├── reminder_state.py               # mark and clear "reminder failed"
│   ├── fallback_metrics.py             # decision log and counters
│   ├── api.py                          # interface used by cmp-reception
│   ├── dispatcher.py                   # final-failure hooks, send-time re-checks (from 006)
│   └── webhooks.py                     # rel-009 and rel-010 handlers (from 006)
├── channel_adapters/sms_templates.py   # reminder template reused for the fallback
└── reception/                          # cmp-reception
    ├── router.py                       # GET /api/reception/reminders-failed
    └── schemas.py
alembic/versions/                       # forward-only migration
contracts/clinic-api-v1.openapi.yaml    # new path added
tests/{messaging,reception,contract}/

# repo brightsmile/clinic-web (ctr-web)
src/
├── api/remindersFailed.ts
├── config/featureFlags.ts              # Release 2 flag
├── pages/reception/RemindersFailedPage.tsx
└── routes/receptionRoutes.tsx
```

**Structure Decision**: Web application with two repositories as set out in architecture.md (ctr-clinic-api and ctr-web). All backend work is inside the existing `cmp-messaging`, `cmp-channel-adapters` and `cmp-reception` modules; cmp-reception reads reminder state only through the cmp-messaging interface, as in the component view.

## Complexity Tracking

No violations to justify.
