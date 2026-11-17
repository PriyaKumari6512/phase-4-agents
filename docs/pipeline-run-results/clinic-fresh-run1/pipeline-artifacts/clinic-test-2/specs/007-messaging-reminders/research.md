# Research: Confirmations, reminders, STOP and SMS fallback

All decisions follow architecture.md (ADR-0002, ADR-0006, ADR-0009, ASM-003, ASM-009, ASM-012, section 6 resilience). Items marked "open" cannot be settled now and are carried as assumptions.

## R1. Where do messages live and who sends them?
- **Decision**: Rows in one `messages` table (ent-message) with a precomputed `send_at`; a dispatcher inside the API process claims due rows every ~30 s with `FOR UPDATE SKIP LOCKED`.
- **Rationale**: ADR-0002: about 1,000 reminders a week, no broker needed; claim with skip locked makes two replicas safe.
- **Alternatives**: a message broker or worker process (rejected by ADR-0002, can be revisited, RSK-004); sending in the request (only for the sign-in code).

## R2. Quiet-hours rule (Q-009 open)
- **Decision**: due = start - 24 h (IST). Due 08:00-20:59 → send at due. Due 21:00-23:59 → 20:00 the same day. Due 00:00-07:59 → 20:00 the previous day. If the result is before "now": send now when now is 08:00-20:59, otherwise at the next 08:00. No reminder when start - now < 24 h. NFR-005 lag is measured from the adjusted time.
- **Rationale**: ASM-003 and PD-004. One pure function makes a client change cheap.
- **Alternatives**: send at 08:00 for all night due times (contradicts FR-027).

## R3. Resilience
- **Decision**: per attempt timeout 5 s; 3 attempts with waits of 5 s and 30 s done inline in the claiming task (a 30 s poll cycle cannot honour a 5 s wait); permanent errors (invalid number, template rejected) are not retried; transient errors are. Circuit breaker per provider, in memory per replica, opens after 5 failures in 60 s, half-open probe after a short pause (30 s assumed); while open, claimed rows go back to `queued` with no attempt counted.
- **Rationale**: matches rel-007 and rel-008; a hand-written class of about 40 lines is simpler than a library.
- **Alternatives**: breaker state in the database (shared across replicas; more complexity, not needed at this volume).

## R4. Idempotency and duplicates
- **Decision**: `dedupe_key` unique per logical message; partial unique index gives one live reminder per appointment; unique `(channel, provider_message_id)`; status only moves forward (queued → sending → sent → delivered, or → failed); a failed receipt after delivered is ignored; fallback SMS created with `INSERT ... ON CONFLICT (original_message_id) DO NOTHING` (thr-018). A crash between provider acceptance and commit could cause a second send; mitigated by passing the message id as the provider's client reference (open: the chosen provider must support it; ASM-009 to be extended to cover this).
- **Alternatives**: exactly-once via provider query before resend (provider-dependent).

## R5. Webhooks
- **Decision**: two endpoints, HMAC-SHA256 over the raw body with a shared secret per provider from the secret store; header name and encoding are provider specific and live in the adapter (open until providers chosen). Unsigned or wrongly signed → 401; valid but unknown message id or phone number → 200 and ignored. Handler does only cheap database work.
- **Rationale**: rel-009, rel-010, thr-015, thr-016, thr-017.
- **Open**: payload formats until the providers and their sandboxes exist (ASM-009); adapters isolate this and a fixtures folder captures real sandbox payloads.

## R6. STOP
- **Decision**: a reply whose trimmed text equals STOP (case-insensitive) from a phone number with an account sets `reminders_opt_out` through a cmp-identity function; the dispatcher re-check makes it effective at once for queued rows. Only SMS replies are processed (rel-009 carries replies; rel-010 carries receipts only), see Q3.
- **Alternatives**: also keywords such as UNSUBSCRIBE (not in the PRD; DLT rules on opt-out keywords to be checked with the provider, open).

## R7. Confirmation inside the booking transaction
- **Decision**: facade writes rows with the caller's session. No separate outbox table is needed because `messages` is the outbox.
- **Rationale**: ADR-0002 and section 5 consistency note ("confirmation committed with the booking transaction and sent after commit").

## R8. Templates
- **Decision**: one English catalogue file (`catalogue_en.yaml`) with the text and the variables per template key; `config/message_templates.yaml` maps (template key, channel) to the provider template id and approval status. Template keys: `sign_in_code` (SMS only), `confirmation`, `change_cancelled`, `change_rescheduled`, `reminder` (each for SMS and WhatsApp), so at most 9 templates. The renderer refuses to send when a key has no id or is not approved.
- **Rationale**: NFR-011, QA-009. DLT templates are fixed text with variables, so the catalogue text must equal what is registered.
- **Open**: DLT variable length limits and WhatsApp template category; to be set with the providers.

## R9. Sign-in code
- **Decision**: `send_sign_in_code(phone, code)` in `sign_in_code.py` calls the SMS adapter directly, one attempt, 5 s timeout, same breaker; writes a row with status and provider id but no rendered text and no params; returns `SendResult`. Not suppressed by opt-out.

## R10. Nightly job (JOB-005) and retention
- **Decision**: runs at 03:00 IST (assumed time, low traffic) inside the API process, guarded by a database advisory lock so only one replica runs it. It (1) returns `sending` rows older than 10 minutes to `queued`, (2) cancels queued reminders for appointments that are not booked, (3) creates missing reminders for booked appointments that are at least 24 h away and not opted out, (4) deletes messages older than 90 days, and (5) logs and counts results. The same "ensure reminders" routine is used when reception switches reminders back on.

## R11. Observability and alerts
- **Decision**: metrics `messages_total{kind,channel,status}`, `reminder_lag_seconds` (age of the oldest due unsent row, computed each cycle), `provider_errors_total{provider}`, `breaker_open{provider}`, `dispatcher_last_cycle_timestamp`; alert at lag > 10 minutes (RSK-004); health shows the dispatcher heartbeat; logs carry message id, appointment id, kind, status and correlation id, never names, phones or text.

## R12. Release 2 pieces
- **Decision**: fallback (`fallback.py`) is called on final failure of a WhatsApp reminder (provider error after retries, or failed receipt) when `WHATSAPP_SMS_FALLBACK_ENABLED` is true; the new SMS row references `original_message_id`. Any final failure of a reminder with no further permitted channel sets `reminder_failed_at` on the original reminder row. The reception list queries reminder rows with `reminder_failed_at` set for appointments tomorrow (IST) that are still booked, scoped by the clinic from the access context.
- **Switch**: a configuration setting read at the time of failure; changing it needs a configuration change (no code change).

## R13. Testing approach
- pytest with a fake clock and a fake provider that can be slow, failing or replaying signed webhooks; timing table tests; concurrency test with two dispatchers on one database; log scrub test; contract tests against `contracts/messaging-api.openapi.yaml`; a staging smoke test with sandbox accounts. The test library choice (pytest) is the common default for the Python stack and conflicts with nothing in the architecture.

## Open questions carried forward
- Q1 (Q-009), Q2 (ISS-001), Q3 (STOP via WhatsApp): see clarifications.md.
- Provider choice, provider webhook formats and header names, provider support for a client reference, DLT variable limits: resolved when the providers are chosen and sandbox accounts exist (weeks 1-2, ASM-009).
- Breaker pause length (30 s) and nightly job time (03:00 IST) are our assumptions.
