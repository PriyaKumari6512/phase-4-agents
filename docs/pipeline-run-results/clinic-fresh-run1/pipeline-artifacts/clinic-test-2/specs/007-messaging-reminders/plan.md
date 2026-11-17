# Implementation Plan: Confirmations, reminders, STOP and SMS fallback

**Branch**: `007-messaging-reminders` (no git branch is created) | **Date**: 2026-11-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-messaging-reminders/spec.md`

## Summary

Build the messaging module (`cmp-messaging`) and the channel adapters (`cmp-channel-adapters`) inside the one FastAPI deployable (ctr-clinic-api), plus a small reception screen in ctr-web. Messages are rows in `ent-message` with a precomputed send time (ADR-0002, ADR-0009). Booking, reschedule and cancel (features 004, 005, 006) call a messaging facade inside their own database transaction; the facade writes the confirmation, change notice and reminder rows. A dispatcher started with the API process claims due rows every ~30 seconds with `FOR UPDATE SKIP LOCKED`, re-checks the appointment and the opt-out flag, renders the English template and sends through one adapter per provider (ADR-0006) with a 5 s timeout, 3 attempts (waits of 5 s and 30 s) and a circuit breaker. Signed webhooks (rel-009 SMS receipts and STOP, rel-010 WhatsApp receipts) update status idempotently. A nightly job (JOB-005) reconciles missing or stuck reminders and deletes messages older than 90 days. The sign-in code is sent in the request through a separate synchronous port. Release 2 adds the WhatsApp-to-SMS fallback (a configuration switch, default on, one fallback per reminder by a unique key), the "reminder failed" mark and the reception "Reminders failed" list, kept in separate migrations, files and a feature flag so the MVP ships without them.

## Technical Context

**Language/Version**: Python 3.12 (ctr-clinic-api); TypeScript with React (ctr-web)

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic (architecture); OpenTelemetry for logs, metrics and traces (constitution). An async HTTP client for provider calls and a hand-written retry and circuit breaker (no extra library, Simplicity). The concrete SMS and WhatsApp providers are not chosen (open); each sits behind its own adapter.

**Storage**: PostgreSQL 16 (ctr-db), table for `ent-message`; reads `ent-patient-account` (channel and reminders-off flag, owned by cmp-identity) and `ent-appointment` (owned by cmp-booking) through those modules' interfaces

**Testing**: pytest with a controllable clock and a fake provider (signed webhooks, latency, failures); contract tests against the OpenAPI fragment in `contracts/`; React component tests for ctr-web

**Target Platform**: Linux container on a managed container service in an India region, 2 replicas in prod (ADR-0005); static web app on CDN

**Project Type**: web application (two repos: brightsmile/clinic-api, brightsmile/clinic-web)

**Performance Goals**: 99% of due reminders sent within 15 minutes of their adjusted time (NFR-005); confirmations within about 30 s; reminders-failed list within 2 s for 95% of requests; about 4,000 messages a week at design load, so one dispatcher cycle of ≤ 50 rows is plenty

**Constraints**: provider timeout 5 s; 3 attempts, backoff 5 s then 30 s; breaker after 5 failures in 1 minute; message stays queued; alert when lag > 10 min; STOP honoured within 1 hour (target: at once); SMS only via registered DLT sender ID and templates; WhatsApp only via approved templates; only templated fields to providers; no PII in logs; messages deleted after 90 days; times stored UTC, shown IST; single English catalogue; staging uses sandbox provider accounts

**Scale/Scope**: about 450 appointments a week now, 1,000 later; about 4 messages per appointment; 9 user stories (7 MVP, 2 Release 2); 2 new API route groups (webhooks, reception list) and 1 reminders switch

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|-----------|-------|--------|
| I. Tests first for business logic | Every story starts with test tasks (timing function, suppression, STOP, dispatcher, fallback, list); each story has an independent test | Pass |
| II. Observability | Structured logs with ids only, metrics (sent, failed, lag, breaker state), traces, dispatcher heartbeat in `GET /health`, alert on lag over 10 min | Pass |
| III. Security baseline | Webhooks verify an HMAC signature and reject unsigned requests; provider keys and webhook secrets come from the secret store; inputs validated at the edge; STOP and reminders switch authorised by role | Pass (webhook and reception endpoints need explicit security review, planned in Polish) |
| IV. Traceability | Spec items carry prd.md ids; every task names exact file paths | Pass |
| V. Simplicity | No broker, no extra queue library, hand-written breaker, one table, dispatcher in the API process (ADR-0002); R2 pieces isolated | Pass |
| Definition of done | No patient data in logs; unit and contract tests in CI | Pass (log scrubbing test planned) |

No violations; Complexity Tracking is empty. Re-check after design: still pass (see data-model.md; the only added structure is one table and two nullable R2 columns).

## Design Decisions (short; details in research.md)

1. **Facade called inside the booking transaction.** `MessagingFacade.on_booking_created`, `on_appointment_cancelled`, `on_appointment_rescheduled` take the caller's database session and write rows in that transaction, so a booking never exists without its confirmation row, and a rolled-back booking leaves no message. Sending happens later in the dispatcher.
2. **Quiet-hours timing is one pure function** (`compute_schedule(start_at, now)`) returning due time and adjusted send time or "no reminder". All cases of FR-005, FR-006 and FR-010 are table-tested.
3. **One live reminder per appointment** by a partial unique index; cancel and reschedule set queued reminders to `cancelled`; the send-time re-check (appointment booked, start in the future, account not opted out) is the safety net that gives zero reminders for cancelled appointments.
4. **Dispatcher**: claim rows with `status='queued' AND send_at <= now()` using `FOR UPDATE SKIP LOCKED`, mark `sending`, send with inline retries (5 s, 30 s), commit the result. A breaker per provider releases rows back to `queued`. Stale `sending` rows are returned to `queued` by the nightly job.
5. **Idempotency**: `dedupe_key` is unique per message (for example `confirmation:<appointment>:<version>`); provider message id is unique per channel; the message id is passed to the provider as the client reference where the provider supports it; receipts only move status forward.
6. **Webhooks** `POST /api/webhooks/sms` (receipts and STOP, rel-009) and `POST /api/webhooks/whatsapp` (receipts, rel-010): verify HMAC over the raw body, answer 200 quickly, ignore unknown ids and unknown numbers. They are exempt from the cookie session and the CSRF header; rate limiting is at the edge (feature 001 infrastructure).
7. **STOP**: only SMS replies (assumption Q3); the opt-out flag is set on the patient account through a cmp-identity function; the dispatcher re-check skips reminders (not confirmations, change notices or codes). Reception switches the flag with `PUT /api/patient-accounts/{id}/reminders`. Switching back on re-creates reminders for future eligible appointments using the same routine as the nightly job.
8. **Sign-in code** is sent by `send_sign_in_code(phone, code)` directly through the SMS adapter (one attempt, 5 s timeout, breaker shared); the message row records status but never the code.
9. **Release 2 isolation**: migration `007_02`, `fallback.py`, `reminders_failed.py`, the web page and the flag `r2_reminders_failed`; the fallback switch is the setting `WHATSAPP_SMS_FALLBACK_ENABLED` (default true). Without R2 code, a failed reminder ends in status `failed` (operator metric only).

## Project Structure

### Documentation (this feature)

```text
specs/007-messaging-reminders/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── clarifications.md    # Assumed answers to open questions
├── contracts/
│   ├── messaging-api.openapi.yaml   # webhooks, reception list, reminders switch (fragment of clinic-api-v1)
│   └── messaging-facade.md          # in-process interfaces for features 002, 004, 005, 006
├── checklists/requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository roots)

The folder layout `app/modules/<module>/` and `tests/` is assumed from the modular monolith (ADR-0001); feature 001 fixes the exact layout and the tasks follow it.

```text
brightsmile/clinic-api/
├── alembic/versions/
│   ├── 007_01_messages.py                 # MVP: messages table
│   └── 007_02_reminder_fallback.py        # R2: original_message_id, reminder_failed_at
├── app/modules/messaging/                 # cmp-messaging
│   ├── config.py  models.py  repository.py  ports.py  params.py
│   ├── templates.py  catalogue_en.yaml
│   ├── timing.py  reminders.py  confirmations.py  service.py   # facade
│   ├── dispatcher.py  resilience.py  metrics.py
│   ├── webhooks.py  stop_handler.py  receipts.py
│   ├── sign_in_code.py  readiness.py  jobs.py  retention.py
│   └── fallback.py                        # R2
├── app/modules/channel_adapters/          # cmp-channel-adapters
│   ├── base.py  errors.py  signature.py  sms.py  whatsapp.py
├── app/modules/identity/reminder_preferences.py   # cmp-identity: flag read/write
├── app/modules/identity/routes_reminders.py       # cmp-identity: reminders switch route
├── app/modules/reception/reminders_failed.py      # cmp-reception, R2
├── config/message_templates.yaml          # template ids and approval status per kind and channel
├── docs/messaging/                        # catalogue, onboarding tracker, runbook
├── ops/alerts/messaging-alerts.yaml       # lag alert definition
└── tests/messaging/  tests/channel_adapters/  tests/reception/  tests/contract/  tests/fakes/

brightsmile/clinic-web/
├── src/pages/reception/RemindersFailedPage.tsx     # R2
├── src/components/reception/RemindersToggle.tsx    # MVP, placed in the patient panel of feature 006
├── src/api/messagingApi.ts
├── src/config/flags.ts
└── tests (next to the files, *.test.tsx)
```

**Structure Decision**: web application with two repositories. All business logic is in ctr-clinic-api modules; ctr-web only shows the reminders switch and the R2 list.

## Dependencies on other features

- 002 (identity): `reminders_opt_out` on the patient account, the access context (roles and clinic scoping), and the caller of `send_sign_in_code`.
- 004 (online booking): calls `on_booking_created`; stores the chosen channel on the appointment.
- 005 (manage appointments): calls `on_appointment_cancelled` and `on_appointment_rescheduled`.
- 006 (reception): reception cancel and book call the same facade; the patient panel hosts `RemindersToggle`.
- 001 (platform): edge rate limit for webhook paths, secret store, `GET /health`, CI with sandbox smoke test.
- Outside the team: DLT registration and WhatsApp template approval by the clinic (A-005, DEP-001, DEP-002, RSK-001).

## Complexity Tracking

No constitution violations to justify.
