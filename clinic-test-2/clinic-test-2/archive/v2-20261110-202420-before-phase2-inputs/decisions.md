# Clinic Booking System — Architecture decisions

## ADR-0001: Modular monolith as the architecture style

- Status: accepted
- Version: v1
- Drivers: QA-002, QA-003, QA-004, QA-007, ASM-012, ASM-002
- Affects: ctr-web-app, ctr-clinic-api, ctr-clinic-db, rel-003, rel-004, rel-005
- Supersedes: none

### Context
The only H/H driver is QA-002: two users booking the same slot must never both succeed. The load is small (peak 10 requests/s, ASM-002), one clinic, one team, one release cadence. FR-1 to FR-3 touch the same data: appointments, dentists' hours, patients and reminders. QA-004 needs the SMS gateway kept behind an adapter so its failures never block booking.

### Considered options
1. Plain monolith, no enforced module boundaries — simplest, but SMS and identity code would mix with booking code, so the SMS isolation in QA-004 and the ownership rules (one owner per entity) are not enforced and extraction later is costly.
2. Modular monolith — one deployable, capability modules that each own their entities and talk through interfaces. QA-002 is one database transaction.
3. Serverless functions — low idle cost, but no cost or managed-cloud constraint exists (ASM-001), and cold starts and many functions sharing one database add complexity for no driver.
4. Event-driven services — no workflow needs eventual consistency or event history, and QA-002 would turn into a saga.
5. Microservices — no multiple teams or independent release needs, and splitting booking from scheduling would break the strict consistency QA-002 needs.

### Decision
Option 2. It is the simplest style that meets QA-002, and it adds module ownership over a plain monolith (option 1), which QA-004 and the SMS anti-corruption adapter need. Option 3 has no driver in the requirements. Options 4 and 5 are ruled out by QA-002, which wants strict ACID across booking and scheduling data, and by the single small team.

### Consequences
- Positive: double booking solved in the database (ADR-0002), one deployable and one pipeline, low operating cost, modules can be extracted later if one capability outgrows the others.
- Negative / accepted trade-offs: the API scales as one unit, a defect in one module can affect the whole process, module boundaries rely on discipline and tests, not the network.
- Follow-ups: RSK-007

## ADR-0002: PostgreSQL as the only data store, with a unique constraint against double booking

- Status: accepted
- Version: v1
- Drivers: QA-002, QA-008, FR-1
- Affects: ctr-clinic-db, rel-004
- Supersedes: none

### Context
QA-002 requires 0 double bookings under concurrent requests. All entities are relational and small (about 0.35 GB at 3 years, capacity estimate). Backup targets are RPO 15 min and RTO 1 h (QA-008).

### Considered options
1. PostgreSQL only, with a unique partial index on (dentist, start time) where status is booked — the database refuses the second insert, whatever the application does.
2. PostgreSQL plus Redis for slot locks — faster locking, but a second store, a second failure mode and lock expiry races, with no performance need at 10 requests/s.
3. Application-level locking (check then insert) — simple, but unsafe across 2 or more instances and fails QA-002.
4. Document store — no relational integrity guarantees for the uniqueness rule.

### Decision
Option 1. The unique index is the final guard, and the booking is one transaction (check slot validity, insert appointment, insert reminder). No Redis, search or document store is introduced.

### Consequences
- Positive: correctness does not depend on instance count or on application code paths, one store to back up and restore.
- Negative / accepted trade-offs: a conflicting insert fails and the user must pick another slot, the database is a single write point (scaling path: larger instance, then read replica).
- Follow-ups: none

## ADR-0003: Reminders as database rows polled by a scheduled job, not a message broker

- Status: accepted
- Version: v1
- Drivers: QA-004, FR-3, QA-003, ASM-006, ASM-009
- Affects: ctr-clinic-api, ctr-clinic-db, rel-005
- Supersedes: none

### Context
FR-3 needs one SMS about 24 hours before each appointment. QA-004 requires retries during gateway outages, no duplicates across replicas and no impact on booking. Volume is about 200 reminders per day.

### Considered options
1. Reminder row written in the booking transaction, and an in-process job in ctr-clinic-api that claims due rows with row locks (skip locked) and calls the SMS adapter.
2. RabbitMQ or Kafka with delayed messages — a new container, a dual write between database and queue (needing an outbox), for 200 messages a day.
3. A cloud scheduler or separate worker container — another deployable and another place to configure, for no load reason.
4. Send the SMS synchronously at booking time — cannot meet the 24-hour timing and ties booking to the gateway.

### Decision
Option 1. The reminder exists if and only if the booking commits, replicas never double-claim a row, retries and cutoffs are plain data (attempts, due time), and the job catches up after downtime.

### Consequences
- Positive: no extra infrastructure, no outbox needed, easy to inspect and replay.
- Negative / accepted trade-offs: polling every 60 s adds up to a minute of lateness, the job stops when all API instances are down, a crash after the gateway accepts a message can duplicate it (mitigated by a provider idempotency key).
- Follow-ups: RSK-001, RSK-002, RSK-007

## ADR-0004: Cloud-agnostic hosting on Kubernetes

- Status: accepted
- Version: v1
- Drivers: ASM-001, QA-003, QA-007
- Affects: ctr-clinic-api, ctr-web-app, ctr-clinic-db
- Supersedes: none

### Context
The client has not named a cloud (ASM-001). The standard cloud-agnostic target for a long-running service is Kubernetes. QA-003 needs at least 2 instances across zones with health checks and auto-restart.

### Considered options
1. Kubernetes with an ingress, a deployment of 2 to 4 replicas and a PostgreSQL operator or managed database — portable across clouds and on-premises.
2. A single managed container service on a chosen cloud (for example ECS Fargate) — less operations work, but picks a cloud the client has not chosen.
3. A single virtual machine with Docker Compose — cheapest, but one node cannot meet the 99.9% availability or zone failover of QA-003.

### Decision
Option 1 until the client confirms a cloud. Once ASM-001 is answered, the same containers move to that cloud's managed container service or managed Kubernetes with no design change.

### Consequences
- Positive: portable, meets the availability tactics, same topology in dev, staging and prod.
- Negative / accepted trade-offs: more operations effort than a managed container service for a small load.
- Follow-ups: RSK-003

## ADR-0005: Built-in authentication with JWT, no external identity provider

- Status: accepted
- Version: v1
- Drivers: QA-006, FR-1, FR-2, ASM-004
- Affects: ctr-clinic-api, rel-003
- Supersedes: none

### Context
Two roles exist: patient and receptionist. Patients self-register and the requirements name no identity provider, single sign-on or directory (ASM-004). QA-006 needs OWASP ASVS L1 and no unauthenticated data access.

### Considered options
1. Built-in accounts in cmp-identity: argon2id passwords, 60-minute signed JWT, RBAC, login rate limiting.
2. External OIDC provider (managed identity service) — less credential handling, but a new dependency, cost and integration the client did not ask for.
3. Sessions with server-side state — needs shared session storage across instances, a second store.

### Decision
Option 1, inside the monolith, behind the interface `authenticate(token)` so an OIDC provider can replace it later without changing other components.

### Consequences
- Positive: no extra dependency or container, stateless instances, simple for patients.
- Negative / accepted trade-offs: the clinic owns password storage, lockout and reset risk, no multi-factor authentication and no password reset by email in this version unless the client asks for it.
- Follow-ups: RSK-006

## ADR-0006: One adapter per reminder channel behind a common channel interface, inside ctr-clinic-api

- Status: accepted
- Version: v2
- Drivers: FR-4, QA-009, QA-004, CON-003, ASM-013, ASM-014
- Affects: ctr-clinic-api, ctr-web-app, cmp-reminders, cmp-whatsapp-adapter, cmp-sms-adapter, rel-006, api-clinic-api-v1
- Supersedes: none

### Context
Request 2 adds WhatsApp as a reminder channel chosen by the patient at booking (FR-4). WhatsApp differs from SMS: approved templates (CON-003), its own provider, API key and failure modes. QA-009 needs a WhatsApp outage to leave SMS and booking unaffected. Volume is unchanged, about 200 reminders per day. ADR-0001 and ADR-0003 already keep reminders as rows polled by an in-process job.

### Considered options
1. Keep the current design (SMS only) — no cost, but does not meet FR-4.
2. Add cmp-whatsapp-adapter beside cmp-sms-adapter in ctr-clinic-api, both implementing one `send` interface, with cmp-reminders choosing by the reminder's channel — minimal change, separate breakers, no new deployable.
3. Replace both with one generic adapter that switches on channel — fewer files, but one breaker and one error mapping for two providers, so a WhatsApp outage would trip SMS (fails QA-009).
4. A separate notification service container — no driver: one team, 200 messages a day, and it would add a deployable and a network call to a flow ADR-0003 chose to keep in process.

### Decision
Option 2. The channel is stored per appointment (chosen at booking, optional `reminder_channel`, default `sms`) and copied to the reminder row. It extends the existing job and tables and changes the contract additively. Option 3 is ruled out by QA-009, option 4 by the absence of any driver for a new container.

### Consequences
- Positive: no new infrastructure, per-channel breaker and credentials, a future channel is one more adapter, the contract change is backward compatible (1.1.0).
- Negative / accepted trade-offs: two external dependencies to operate and rotate keys for, template approval becomes a go-live dependency.
- Follow-ups: RSK-008

## ADR-0007: One-time fallback from WhatsApp to SMS

- Status: accepted
- Version: v2
- Drivers: QA-009, FR-3, FR-4, ASM-014, ASM-015
- Affects: cmp-reminders, cmp-whatsapp-adapter, cmp-sms-adapter, ent-reminder, rel-005, rel-006
- Supersedes: none

### Context
A patient who chose WhatsApp may have a number that is not on WhatsApp, or the provider may be down while the reminder window (due time to 2 h before the visit) closes. FR-3 is only met if the reminder arrives. SMS consent is assumed from registration (ASM-008), WhatsApp opt-in from the choice at booking (ASM-014).

### Considered options
1. No fallback: a failed WhatsApp reminder is marked Failed and alerts fire — simplest and strictly respects the chosen channel, but the patient gets no reminder.
2. Fallback to SMS once, on a permanent WhatsApp error or an open breaker; the reminder row changes channel, sets the fallback flag and goes back to Pending — the reminder still arrives, never on two channels.
3. Send on both channels always — maximum reach, but contradicts the patient's choice and doubles cost and duplicates.

### Decision
Option 2. The switch is one update on the reminder row (channel to `sms`, fallback-used set, attempts reset), so the row-lock claim keeps it single-channel. Transient errors still retry on WhatsApp until the breaker opens. The client must confirm ASM-015; if SMS consent does not cover it, the fallback is switched off by configuration and the design becomes option 1.

### Consequences
- Positive: reminders survive WhatsApp failures, QA-009 measurable, no duplicate across channels.
- Negative / accepted trade-offs: a patient may get an SMS they did not choose, consent risk until confirmed, a crash between a WhatsApp accept and the status update can still duplicate (provider idempotency key = reminder id per channel).
- Follow-ups: RSK-009
