# Implementation Plan: Assignment email notification

**Branch**: `005-assignment-email` | **Date**: Phase 4 backlog generation | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-assignment-email/spec.md`

## Summary

When a task is assigned, the task feature (002-tasks-board) calls an enqueue function in the same database transaction. It writes one row into a notification outbox table (PostgreSQL, ARCH-003) with a unique deduplication key per assignment event. The notify-worker (ARCH-005; same repository `acme/taskflow-api` and image as the API, started with a different command) polls the outbox every few seconds, claims due rows safely for concurrent workers, renders the assignment email and sends it through the email provider client. Outcomes (sent, retry, failed, skipped) are stored on the row and emitted as logs, metrics and traces. The provider key reaches the worker pod through External Secrets from AWS Secrets Manager. Outbox, provider client and worker skeleton are shared foundations reused by F04, F06 and F07. (source: FR-5, US-5)

## Technical Context

**Language/Version**: Python 3.12 (architecture.md, ARCH-005)

**Primary Dependencies**: Project stack from the API (FastAPI app package `app/`, SQLAlchemy-style models and Alembic migrations as in the contract (A)); a standard HTTP client for the provider API; OpenTelemetry (constitution). No new framework and no message broker: the outbox table in PostgreSQL is the queue (Simplicity). The email provider is not named in architecture.md: provider-agnostic client (open question Q2).

**Storage**: PostgreSQL 16 (ARCH-003): new table `notification_outbox`. Redis is not used by this feature.

**Testing**: pytest in `tests/` (A); unit tests with a fake email client, integration tests against PostgreSQL (needed for row locking and transactional enqueue).

**Target Platform**: Linux containers on EKS (`dev`, `stg`, `prod`, us-east-1); worker deployed by F01's deployment foundation with the command `python -m app.worker.main` (A).

**Project Type**: Background worker plus shared service module in the existing API repository, and small manifest changes in `acme/taskflow-infra`.

**Performance Goals**: Email handed to the provider within 60 s of the assignment (FR-5); worker poll interval 5 s (A) leaves margin for retries.

**Constraints**: Exactly one email per assignment; no secrets or email bodies in logs; the budget (USD 2,500/month for all environments) rules out extra infrastructure, so the worker runs as one small deployment (2 replicas for availability (A)).

**Scale/Scope**: 200 teams, 5-30 people each; assignment volume is low (at most a few per second at peak (A)); polling a single indexed table is sufficient.

## Constitution Check

| Principle | Status | How |
|---|---|---|
| I. Tests first | Pass | Each story phase starts with test tasks (fake email client, concurrency, retry, crash recovery). |
| II. Observability | Pass | Story 3: structured logs, OTel metrics/traces, worker health check, alert rules. The worker has no HTTP endpoint; health is a heartbeat check (A). |
| III. Security baseline | Pass | Provider key only via environment from External Secrets; inputs (task title, names) escaped in the email; no secrets/bodies in logs (FR-013). No auth change. |
| IV. Traceability | Pass | Stories and requirements cite prd.md ids; every task names file paths. |
| V. Simplicity | Pass | Outbox table + polling instead of a broker; one provider interface with one implementation. |

Post-design re-check: pass; no complexity violations.

## Project Structure

### Documentation (this feature)

```text
specs/005-assignment-email/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── clarifications.md
├── contracts/
│   ├── outbox-enqueue.md
│   ├── email-provider-client.md
│   └── assignment-email.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code

Paths follow `backlog/implementation-contract.md`; items marked (A) are assumptions there.

```text
acme/taskflow-api
├── app/
│   ├── core/config.py                      # EMAIL_* / NOTIFY_* settings (env)
│   ├── models/notification_outbox.py       # outbox model
│   ├── services/
│   │   ├── notification_outbox.py          # enqueue, claim, mark_* (shared by F04/F06)
│   │   ├── email_client.py                 # email provider client (shared by F04/F06)
│   │   └── tasks.py                        # (owned by F02) calls enqueue on assignment
│   └── worker/
│       ├── main.py                         # notify-worker entrypoint: python -m app.worker.main
│       ├── outbox_dispatcher.py            # poll, claim, dispatch by kind, retry/backoff
│       ├── health.py                       # heartbeat for liveness
│       ├── telemetry.py                    # logs, metrics, traces
│       ├── templates/assignment_email.py   # subject/text rendering
│       └── jobs/send_assignment_email.py   # one assignment email
├── migrations/versions/005_notification_outbox.py
├── docs/notifications.md
├── docs/runbooks/notify-worker.md
└── tests/{services,worker,integration,fakes}/

acme/taskflow-infra
├── k8s/notify-worker/external-secret.yaml  # provider key from Secrets Manager (store owned by F01)
├── k8s/notify-worker/deployment.yaml       # command, env, liveness probe (deployment owned by F01)
└── terraform/observability/notify-worker-alerts.tf   # alert rules (A)
```

**Structure Decision**: Reuse the API repository and image for the worker (architecture.md). `app/worker/` and `app/worker/jobs/` follow the contract. Infra paths follow the `terraform/` and `k8s/` layout assumed in the contract.

## Key Design Decisions

- **Transactional outbox**: the enqueue runs inside the assignment transaction of F02, so a committed assignment always has a notification row and a rolled-back one has none.
- **Deduplication**: `dedupe_key = assignment:<task_id>:<assignee_id>:<assignment_event_id>` with a UNIQUE constraint; enqueue uses insert-on-conflict-do-nothing.
- **Claiming**: workers claim due rows with `FOR UPDATE SKIP LOCKED`, set status `sending` and a claim time; rows stuck in `sending` longer than the visibility timeout (120 s (A)) are reclaimed.
- **Retry**: transient errors reschedule with backoff 5 s, 15 s, 60 s, 5 min, 15 min (A), max 6 attempts, then `failed`; permanent errors go straight to `failed`.
- **Residual duplicate window**: a crash after the provider accepted the message but before the row is marked sent could cause one duplicate. The dedupe key is sent to the provider as idempotency key when the provider supports it (Q2); otherwise this is documented as a known limitation.
- **Worker secrets**: `EMAIL_PROVIDER_API_KEY` is an environment variable populated from an External Secrets `ExternalSecret`; the store and Secrets Manager entry are owned by 001-platform-foundation, this feature adds the worker wiring.

## Dependencies on other features

- 001-platform-foundation: users table (recipient email, name), boards, External Secrets store, worker deployment, observability stack, Alembic setup.
- 002-tasks-board: task model and the assignment path in `app/services/tasks.py` that must call `enqueue_assignment_notification` and supply `assignment_event_id`.
- Provided to: 004-comments-mentions, 006-daily-digest (outbox, client, worker), 007-notification-prefs (consults preferences in the sender).

## Complexity Tracking

No constitution violations.
