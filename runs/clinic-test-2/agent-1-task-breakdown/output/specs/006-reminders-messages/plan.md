# Implementation Plan: Confirmations, reminders and opt-out via SMS and WhatsApp

**Branch**: `006-reminders-messages` (no git branch used) | **Date**: 2027-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/006-reminders-messages/spec.md`

## Summary

Build the Release 1 part of MOD-07: the patient's channel choice (SMS or WhatsApp, remembered), the booking confirmation, change notices after cancel or reschedule, the 24-hour reminder with quiet-hours timing, reminder suppression for cancelled / rescheduled / last-minute bookings, STOP and reception opt-out, and the SMS sign-in code sending. Approach (architecture.md ADR-0002, ADR-0006, ADR-0009): every message is a row in `message` committed in the same transaction as the booking with a precomputed send time; a dispatcher inside the API process claims due rows with `FOR UPDATE SKIP LOCKED` every 30 s, re-checks the appointment and the opt-out, and sends through a channel adapter (one port, one adapter per provider) with timeout 5 s, 3 attempts (5 s, 30 s) and a circuit breaker. Signed webhooks (rel-009, rel-010) bring delivery receipts and STOP replies. The Release 2 fallback (FR-029) and failed-reminder list (FR-033) are feature 009; the message status set, a nullable `original_message_id` and the adapter port are designed for them but nothing of them is built here.

## Technical Context

**Language/Version**: Python 3.12 (ctr-clinic-api, repo brightsmile/clinic-api); TypeScript with React (ctr-web, repo brightsmile/clinic-web)

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic (architecture.md); an HTTP client for provider calls (httpx, async); OpenTelemetry for logs/metrics/traces (constitution II). No message broker, no cache (architecture "Not used").

**Storage**: PostgreSQL 16 (ctr-db). New table `message`; new columns on the patient account (preferred channel, reminders opt-out) and on the appointment (channel, owned by cmp-booking).

**Testing**: pytest (unit for the quiet-hours rule, template mapping, STOP parser, HMAC check, breaker; integration against PostgreSQL for claim/SKIP LOCKED and transactional creation; contract tests against `contracts/clinic-api-v1.openapi.yaml`); fake/sandbox provider servers for adapter tests; Vitest and React Testing Library for the two UI pieces.

**Target Platform**: Linux container (managed container service, 2 replicas in prod); static SPA on CDN.

**Project Type**: web application (backend modular monolith + SPA).

**Performance Goals**: 99% of due reminders sent within 15 minutes of the adjusted due time (NFR-005); 95% of confirmations within 1 minute (dispatcher cycle 30 s); booking response unaffected by delivery (QA-002: 95% within 3 s).

**Constraints**: SMS only via DLT-registered sender and templates, WhatsApp only via approved templates (NFR-011); English and IST (NFR-008); only templated fields to providers; no PII in logs; rendered text deleted after 90 days; provider call timeout 5 s; breaker after 5 failures in 1 minute; lag alert at 10 minutes.

**Scale/Scope**: about 1,000 appointments a week at most, about 4,000 messages a week, dispatcher every 30 s (architecture section 10).

## Constitution Check

*GATE: passed before Phase 0; re-checked after Phase 1.*

| Principle | Check | Result |
|---|---|---|
| I. Tests first for business logic | Quiet-hours rule, suppression rules, STOP handling, retry/breaker and webhook idempotency each get tests written with or before the code; each story has an independent test | Pass |
| II. Observability | Structured logs with correlation id and message id (no PII), OpenTelemetry metrics `messaging.reminder_lag_seconds`, `messaging.send_total{result}`, `messaging.breaker_state`; webhook endpoints covered by `GET /health` of the service | Pass |
| III. Security baseline | Provider keys and webhook secrets from the secret store via environment, none in code; HMAC check on webhooks; inputs validated; reception opt-out endpoint behind RBAC (needs explicit review) | Pass |
| IV. Traceability | Spec stories carry prd.md ids; every task names exact paths and the repo | Pass |
| V. Simplicity | No broker, no new service; dispatcher in the API process; one port with two adapters only; fallback not built (Release 2) | Pass |

Post-design re-check: still passes; the only added structure is the adapter port required by ADR-0006.

## Project Structure

### Documentation (this feature)

```text
specs/006-reminders-messages/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── clarifications.md
├── contracts/
│   └── messaging-api.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code

```text
# repo: brightsmile/clinic-api  (ctr-clinic-api)
src/clinic_api/
├── messaging/                      # cmp-messaging
│   ├── models.py                   # Message ORM model, status/kind enums
│   ├── schedule.py                 # pure quiet-hours and 24-hour rule
│   ├── catalogue.py                # single English message catalogue + template ids lookup
│   ├── service.py                  # on_booked / on_cancelled / on_rescheduled / send_code / opt-out
│   ├── dispatcher.py               # claim, re-check, send, retry, status
│   ├── jobs.py                     # nightly reconciliation (JOB-005) and 90-day retention
│   ├── webhooks.py                 # rel-009 / rel-010 routes, rate limit
│   └── settings.py                 # templates, quiet hours, providers, switches
├── channel_adapters/               # cmp-channel-adapters
│   ├── port.py                     # ChannelPort protocol, SendResult, error classes
│   ├── breaker.py                  # circuit breaker
│   ├── signature.py                # HMAC verification
│   ├── sms.py                      # SMS provider adapter
│   ├── whatsapp.py                 # WhatsApp provider adapter
│   └── sandbox.py                  # sandbox/fake adapters for dev and staging
├── identity/                       # cmp-identity (existing module, small additions)
│   ├── preferences.py              # preferred channel and reminders opt-out on the account
│   └── api.py                      # GET/PUT preferences, reception opt-out endpoint
└── booking/                        # cmp-booking (existing; add channel field, call messaging hooks)
alembic/versions/
tests/{unit,integration,contract}/messaging/ , tests/{unit,integration}/channel_adapters/

# repo: brightsmile/clinic-web  (ctr-web)
src/features/booking/ChannelChoice.tsx        # confirm-screen choice
src/features/reception/ReminderToggle.tsx     # reception record screen toggle
src/api/preferences.ts
```

**Structure Decision**: Web application with two repos as in the constitution. All new backend code sits in the two modules named by the architecture (cmp-messaging, cmp-channel-adapters) with thin additions to cmp-identity and cmp-booking; the front end gets two small components.

## Complexity Tracking

No constitution violations. The adapter port (ports and adapters) is mandated by ADR-0006 and is the smallest way to support two providers plus the Release 2 fallback.
