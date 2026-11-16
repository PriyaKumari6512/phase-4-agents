# Research: Assignment email notification

## R1: Queue mechanism
- **Decision**: PostgreSQL outbox table polled by the worker.
- **Rationale**: Architecture has only PostgreSQL and Redis; the outbox gives atomicity with the assignment transaction (no lost notification), needs no new infrastructure (budget) and meets the 1-minute target with a 5 s poll.
- **Alternatives**: Redis pub/sub (not durable, would lose events while the worker is down); a message broker (not in the architecture, extra cost); sending the email inside the API request (slows the request, loses email on provider outage).

## R2: Exactly-once behaviour
- **Decision**: unique dedupe key + row claim with `FOR UPDATE SKIP LOCKED` + status machine; provider idempotency key when supported.
- **Rationale**: True exactly-once with an external API is impossible; this gives effectively-once with a documented crash window.
- **Alternatives**: Distributed locks in Redis (more moving parts); at-most-once send (can lose emails, violates G2).

## R3: Email provider
- **Decision**: provider-agnostic `EmailClient` interface; one HTTP implementation configured by `EMAIL_PROVIDER_BASE_URL` and `EMAIL_PROVIDER_API_KEY`.
- **Rationale**: architecture.md does not name the provider (open question Q2).
- **Alternatives**: Pick a vendor now (invented fact).

## R4: Retry policy
- **Decision**: backoff 5 s, 15 s, 60 s, 5 min, 15 min, max 6 attempts (all assumed, configurable); permanent errors not retried.
- **Rationale**: first retries stay inside the 1-minute budget; later ones cover short provider outages.

## R5: Worker health
- **Decision**: the worker updates a heartbeat file each loop; Kubernetes liveness exec probe checks its age (A).
- **Rationale**: no HTTP server in the worker; constitution requires health checks.

## R6: Self-assignment
- **Decision**: send (Q1), see clarifications.md.
