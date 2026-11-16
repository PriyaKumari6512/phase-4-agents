# Architecture decisions — BrightSmile Booking

Based on: architecture v1 · All ADRs below are Version v1 (first design).

## ADR-0001: Modular monolith with one PostgreSQL database

- Status: accepted
- Version: v1
- Drivers: QA-003, QA-004, QA-005, QA-011, CON-001, FR-012, NFR-003, NFR-009
- Affects: ctr-web, ctr-clinic-api, ctr-db, rel-005, rel-006

### Context
The system is one business domain (appointments at 2–3 clinics) with about 450 appointments a week now and 1,000 later (NFR-003). One small team has about 16 weeks to a firm go-live (CON-001, NFR-009). The two H/H drivers are: no slot is ever booked twice under concurrent booking (QA-003, FR-012) and reminders sent on time (QA-004, NFR-005). The scope is split into 8 modules (MOD-01 to MOD-08) delivered in two releases (MVP, R2), and a third clinic must arrive as data (QA-011).

### Considered options
1. Modular monolith (one deployable API, modules per capability, one database) — one transaction covers booking, history and reminder scheduling. Modules can be shipped in releases and extracted later.
2. Plain layered monolith with no module boundaries — fastest to start, but R2 modules (MOD-06, MOD-08) and later changes would reach into every table, and QA-011 becomes harder.
3. Microservices per module — independent release, but 8 modules for one team, and booking plus reminder scheduling would need a saga where one transaction is enough. It would also put a network hop between QA-003 and the slot check.
4. Serverless functions with an event bus — cheap at idle, but the load is steady during clinic hours, cold starts hurt NFR-002, and ordering of booking and reminder events adds work with no driver that needs it.

### Decision
Option 1. A single deployable API container (`ctr-clinic-api`), modules by business capability (`cmp-` ids), one PostgreSQL store. Each module owns its tables and other modules call its interface, never its tables. The simpler option (2) is ruled out by QA-011 and the staged MVP / R2 releases. The more distributed options (3, 4) are ruled out by QA-003 (strict consistency in one transaction) and by team size and date (CON-001).

### Consequences
- Positive: double-booking is solved in the database (ADR-0003); simple deployment and rollback; low run cost; one language.
- Negative / accepted trade-offs: the API scales as one unit, and a defect in one module can take the API down. At 1,000 appointments a week this is acceptable.
- Follow-ups: RSK-004.

## ADR-0002: Reminder dispatcher runs inside the API replicas, claiming work from the database

- Status: accepted
- Version: v1
- Drivers: QA-004, QA-005, NFR-005, NFR-011, FR-027, FR-028, FR-029
- Affects: ctr-clinic-api, ctr-db, rel-006, rel-007, rel-008

### Context
Reminders must go out within 15 minutes of their due time for 99% of cases, with none for cancelled appointments (NFR-005). The volume is about 1,000 reminders a week. The booking transaction must create or cancel the reminder with the appointment, so they cannot disagree.

### Considered options
1. Messages are rows in `ent-message` with `scheduled_for`. Each API replica runs a dispatcher loop that claims due rows with `SELECT ... FOR UPDATE SKIP LOCKED` — no new container, no broker, and the row is written in the booking transaction.
2. A separate worker container with the same database — isolates provider slowness from the API, but adds a container to build, deploy and monitor for about 1,000 messages a week.
3. A managed message queue plus a cloud scheduler — a standard approach, but a second place that must stay in step with the appointment: a cancel would have to find and remove a queued message.
4. Keep the current design — not applicable (first design).

### Decision
Option 1. Provider calls are asynchronous with a 5 s timeout, so slow providers do not block request threads. A nightly reconciliation job (JOB-005) repairs any appointment that lacks its reminder. Lag is alerted.

### Consequences
- Positive: cancelling an appointment and cancelling its reminder are one transaction (NFR-005, "none sent for cancelled"); fewer parts to run.
- Negative / accepted trade-offs: dispatcher load shares CPU with the API. If volume grows well beyond NFR-003, the same code can start as a separate worker (same image, different command) without a data change.
- Follow-ups: RSK-004.

## ADR-0003: Double-booking is prevented by a PostgreSQL exclusion constraint

- Status: accepted
- Version: v1
- Drivers: QA-003, FR-012, FR-009, FR-010, US-012.AC2
- Affects: ctr-db, ctr-clinic-api, rel-006

### Context
A slot must never be booked twice, even when two patients (or a patient and reception) confirm at the same moment. Treatments last 30, 60 or 90 minutes, so two appointments can overlap without sharing a start time.

### Considered options
1. `EXCLUDE USING gist (dentist_id WITH =, time_range WITH &&) WHERE (status in booked or arrived)` on `ent-appointment` — the database refuses an overlapping row; the application turns the error into "slot taken".
2. Application check before insert inside a serializable transaction — works, but depends on every code path doing it, and retries on serialization failures.
3. A distributed lock in Redis — adds a second store (needs its own ADR) and a failure mode, with no benefit at this size.

### Decision
Option 1, plus the application's own check for a friendly message. It is the only option that is correct even if a future code path forgets to check.

### Consequences
- Positive: QA-003 holds by construction; US-012.AC2 is directly testable.
- Negative / accepted trade-offs: needs the `btree_gist` extension, which the managed PostgreSQL services allow.
- Follow-ups: none.

## ADR-0004: React single-page app on a CDN, with the API on the same site and a cookie session

- Status: accepted
- Version: v1
- Drivers: NFR-001, NFR-002, NFR-010, QA-007, CON-002
- Affects: ctr-web, ctr-clinic-api, rel-005

### Context
Patients use a phone browser, reception and the practice manager use a desktop browser, and there is no native app (CON-002). Screens must be light on a 4G network (NFR-002) and work without sideways scrolling (NFR-001).

### Considered options
1. React SPA (static files on a CDN) calling a JSON API under the same domain (`/api`) — the technology default; fast static delivery; one set of screens for all roles.
2. Server-rendered pages from the API — fewer moving parts, but each interaction (slot picker) reloads a page, which is slower on 4G, and the API would not be reusable.
3. SPA with the token in browser storage — works across domains, but a script flaw could steal the token.

### Decision
Option 1. The session is a signed token in an `HttpOnly`, `Secure`, `SameSite=Strict` cookie, with a CSRF header check on writes. The web container is not built by the backend agent.

### Consequences
- Positive: the token cannot be read by scripts; static delivery is cheap and fast.
- Negative / accepted trade-offs: one domain for site and API is needed (the clinic provides it, DEP-004); a CSRF check must be kept in every write.
- Follow-ups: none.

## ADR-0005: Managed container platform and managed PostgreSQL in an Indian region, not Kubernetes

- Status: accepted
- Version: v1
- Drivers: QA-005, QA-006, CON-001, CON-008, ASM-002, ASM-007
- Affects: ctr-web, ctr-clinic-api, ctr-db

### Context
Q-008 (hosting and domain) is open. SA-002 says we host in a standard cloud region in India. The team is small and has no operations staff. Availability is 99.5% a month (NFR-004).

### Considered options
1. A managed container service (the provider's serverless container runtime) with managed PostgreSQL with a standby, and a CDN — least operations work.
2. Kubernetes (managed) — flexible, but there is no multi-cloud or platform-team constraint that needs it, and it adds work against a firm date.
3. Virtual machines with self-managed PostgreSQL — cheapest at idle, but patching, failover and backups fall on the team.

### Decision
Option 1. The provider is chosen at set-up (ASM-002) and the design uses nothing provider-specific beyond these three service kinds. If the client names a host (Q-008), the same shape moves with a different service name.

### Consequences
- Positive: health checks, restarts, standby and backups are provided by the platform.
- Negative / accepted trade-offs: provider not fixed yet; a client-mandated host may change the service names and cost.
- Follow-ups: RSK-008.

## ADR-0006: Message providers sit behind one channel-adapter component; WhatsApp falls back to SMS

- Status: accepted
- Version: v1
- Drivers: QA-004, QA-009, FR-013, FR-014, FR-029, FR-031, NFR-011, CON-003, CON-007, ASM-005, ASM-009
- Affects: ctr-clinic-api, rel-007, rel-008, rel-009, rel-010

### Context
SMS (DLT-registered sender ID and templates) and WhatsApp (approved templates) are external systems we do not control, chosen by us and paid by the clinic (REQ-029). Their APIs, templates and error codes differ. The client has not agreed to the WhatsApp-to-SMS fallback (ISS-001).

### Considered options
1. A `cmp-channel-adapters` component with one adapter per provider, with templates and error codes mapped to the system's own model — the rest of the code asks for "send reminder" and never sees a provider type.
2. Call each provider's SDK from the messaging logic — less code at first, but switching provider (likely, since none is chosen) touches business code.
3. One aggregator for both channels — possible, and the adapters still apply, but it ties the design to one vendor before the client has chosen.

### Decision
Option 1. Fallback (FR-029) is implemented, but is a configuration switch (`FALLBACK_WHATSAPP_TO_SMS`, default on, as SA-008 says), and can be turned off if the client declines it. Only templated text is sent (NFR-011).

### Consequences
- Positive: provider change is one component; compliance is checked in one place.
- Negative / accepted trade-offs: two adapters to build and test against sandbox accounts that depend on DEP-001 and DEP-002.
- Follow-ups: RSK-001, RSK-005.

## ADR-0007: Accept SIM-swap and recycled-number risk on phone-code sign-in

- Status: accepted
- Version: v1
- Drivers: QA-007, FR-002, NFR-006, NFR-007, ASM-001
- Affects: rel-005, rel-007

### Context
Patients sign in with a phone number and an SMS code, with no password (REQ-023). Anyone who controls the number, by SIM swap or after the number is reassigned, can sign in and see that number's appointments. The data is name, appointments and treatment type only, with no clinical data (CON-006).

### Considered options
1. Accept the risk, with code limits (FR-002), and show only minimal data in the patient's screens — consistent with the client's wish for no passwords.
2. Add a second factor (birth year of the account holder) — reduces the risk, but adds a step against NFR-010 (5 screens or fewer) and was not asked for.
3. Do not accept: add email sign-in — outside the client's request.

### Decision
Option 1. The exposure is low (no health data, no payment) and the rest of the design limits it: the patient screens never show other patients' data, and a 5-try / 15-minute lock is applied.

### Consequences
- Positive: simple sign-in that meets the client's wish.
- Negative / accepted trade-offs: a person who gets the number gets the appointments.
- Follow-ups: RSK-009.

## ADR-0008: Patient account and patient person are separate entities

- Status: accepted
- Version: v1
- Drivers: FR-006, FR-025, FR-020, PD-007, ASM-001, RSK-003
- Affects: ctr-clinic-api, ctr-db

### Context
Sign-in is per phone number (one account, SA-001). Each appointment names the person it is for (FR-006), and no-shows count against that person (PD-007). Reception creates patients with only a name and a phone number (FR-020). Family members (US-006) are in R2 and Q-007 is open.

### Considered options
1. `ent-patient-account` (phone, sign-in, channel choice, STOP) and `ent-patient` (a person, linked to one account) — an appointment, a block and a no-show always point to a person; the account holder is the first person.
2. One patient record per phone number, family members as free text — simple, but no-shows and blocks could not be counted per person (PD-007).
3. A separate account per person with a shared phone — needs sign-in to choose between accounts; this is the Q-007 risk case.

### Decision
Option 1 from the MVP, although the family screens ship in R2, so R2 needs no data migration. If Q-007 is answered the other way, only sign-in changes.

### Consequences
- Positive: PD-007 and the block count work; R2 adds no migration.
- Negative / accepted trade-offs: one extra table and join in the MVP.
- Follow-ups: RSK-003.

## ADR-0009: Reminders are created at booking time with their send time already worked out

- Status: accepted
- Version: v1
- Drivers: QA-004, FR-027, FR-028, PD-004, ASM-003
- Affects: ctr-clinic-api, ctr-db

### Context
A reminder is due 24 hours before the start, moved to 20:00 if that falls in quiet hours (21:00–08:00 IST). It must not exist for a cancelled appointment, and a rescheduled appointment gets one for its new time only.

### Considered options
1. On booking or reschedule, create an `ent-message` row of kind reminder with `due_at` and `scheduled_for` (the quiet-hours-adjusted time), and cancel it on cancel or reschedule, in the same transaction — the dispatcher only reads due rows.
2. A periodic scan of appointments starting in 24–25 hours — no extra rows, but quiet-hour rules, cancel races and "booked less than 24 hours ahead" are re-decided at every scan, and a missed scan loses reminders.

### Decision
Option 1. `due_at` (start minus 24 hours) is kept next to `scheduled_for`, so NFR-005 is measured against the adjusted time and the real due time is auditable.

### Consequences
- Positive: the 99% in 15 minutes measure is a query; cancellations are exact.
- Negative / accepted trade-offs: a change to quiet hours (Q-009) does not move rows already created; a one-off script moves them.
- Follow-ups: RSK-004.
