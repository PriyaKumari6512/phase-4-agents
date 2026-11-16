# Research: WhatsApp to SMS fallback and reminders-failed list

## R1. How to guarantee exactly one SMS fallback per original message (thr-018)

- **Decision**: Add a nullable `fallback_of_message_id` column to `ent-message` with a unique index. The fallback is created by an insert that does nothing when the key exists (`INSERT ... ON CONFLICT DO NOTHING`), in the same transaction that marks the original message `failed`. Only the call that really inserted the row goes on to send.
- **Rationale**: The database decides the winner, so the dispatcher's own failure and a replayed or concurrent receipt can never both create an SMS. It is the same idea as the exclusion constraint used for bookings (ADR-0003).
- **Alternatives**: An in-memory or cache lock (no cache exists; fails across 2 replicas). A "fallback sent" flag with read-then-write (race between replicas).

## R2. Where "reminder failed" lives

- **Decision**: A new status value `reminder_failed` on `ent-message` (the architecture says "ent-message status"). The list is a query: reminder messages in status `reminder_failed`, joined to booked appointments starting tomorrow (IST) at the receptionist's clinic. No new column on the appointment.
- **Rationale**: Keeps the state with the work list owned by cmp-messaging; cmp-reception depends on cmp-messaging as in the component view; no change to cmp-booking's status set (FR-024).
- **Alternatives**: A flag on `ent-appointment` (touches cmp-booking's owned table, breaks FR-024's status list). A separate table (speculative).

## R3. Which message gets the mark

- **Decision**: The last message in the chain: the SMS fallback when it fails; the WhatsApp message itself when the switch is off or the patient has no valid SMS number. A later delivered receipt for any message of the chain clears it (status becomes `delivered`).
- **Rationale**: One row per appointment's reminder chain carries the final state; the query returns distinct appointments.
- **Alternatives**: Mark both messages (double counting, extra clean-up).

## R4. The switch

- **Decision**: An environment-backed setting `REMINDER_SMS_FALLBACK_ENABLED`, default `true`, read at decision time and again at send time of the fallback SMS. Changing it needs a restart or config reload of the service, not a code release.
- **Rationale**: The client has not agreed (ASM-005, RSK-005); secrets/config come from the cloud secret store or environment as in architecture section 9. No admin screen is in the PRD.
- **Alternatives**: A database setting with an admin screen (scope not in the PRD). A build-time constant (needs a release).

## R5. Opt-out, cancelled and delivered guards

- **Decision**: At decision time and again at send time: (1) reminders opt-out flag read through cmp-identity; (2) appointment status read through cmp-booking (must be booked, not started); (3) original message not delivered. A guard hit skips the SMS without marking `reminder_failed` for opt-out and cancelled (nothing to phone about), and marks it for switch-off or missing number.
- **Rationale**: Honours STOP (FR-031, NFR-011) and "no reminder for cancelled" (FR-028, QA-004).
- **Alternatives**: Check only at decision time (a STOP arriving between creation and sending would be missed).

## R6. Release 2 flag

- **Decision**: A web configuration flag read by the router and the navigation in ctr-web; the screen route and menu entry exist only when the flag is on. The API endpoint is always available to receptionists (it exposes nothing new beyond the role's own clinic data).
- **Rationale**: Architecture section 8: "R2 screens are hidden by a feature flag until their data is ready". Reuse the flag if another R2 feature already added it.
- **Alternatives**: A server-side flag that also hides the endpoint (more moving parts with no extra security value).

## R7. "Tomorrow" in IST

- **Decision**: Compute the day bounds in IST (UTC+5:30) from the current time and compare against UTC-stored appointment start times.
- **Rationale**: Times are stored in UTC and shown in IST (QA-012).

## R8. Contract

- **Decision**: One additive path, `GET /api/reception/reminders-failed`, merged into `contracts/clinic-api-v1.openapi.yaml` (minor version bump). Fragment in `contracts/reminders-failed.openapi.yaml`. Webhook operations do not change.
- **Rationale**: Additive and backward compatible; contract tests in CI cover it (architecture section 8).
