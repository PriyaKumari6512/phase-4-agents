# Research: 006-reminders-messages

All decisions follow architecture.md (ADR-0002, ADR-0006, ADR-0009); no technology outside it is introduced. No NEEDS CLARIFICATION remains (assumptions in clarifications.md).

## R1: Where reminders are created and cancelled
- **Decision**: `messaging.service.on_booked / on_cancelled / on_rescheduled` are called by cmp-booking inside the booking transaction. They insert the confirmation / change notice row and the reminder row, or flip pending reminder rows to `cancelled`, all committed with the appointment and its history.
- **Rationale**: ADR-0009: nothing can be lost between booking and message row; cancel and reminder-cancel are atomic, which gives "none sent for cancelled" (NFR-005).
- **Alternatives**: event bus or after-commit callback (lost messages on crash; broker not in architecture).

## R2: Quiet-hours and 24-hour rule as a pure function
- **Decision**: `schedule.plan_reminder(appointment_start_utc, booked_at_utc, config) -> ReminderPlan | None`, working in IST (UTC+05:30, no DST). `due = start - 24h`. If `start - booked_at < 24h` return None. If due local time is in [21:00, 24:00) the send time is 20:00 same local day; in [00:00, 08:00) it is 20:00 the previous local day; else due. If the send time is before `booked_at`: send at once when `booked_at` is outside quiet hours, otherwise at the next 08:00. `due_at` and `scheduled_at` are both stored; NFR-005 is measured on `scheduled_at`.
- **Rationale**: ASM-003; pure function is trivially testable with a table of cases. Quiet-hours bounds, evening time (20:00) and morning time (08:00) are settings (Q-009 open).
- **Alternatives**: scheduling at the dispatcher (loses transactional guarantee).

## R3: Dispatcher
- **Decision**: An asyncio task started in the FastAPI lifespan, every 30 s: select up to 50 rows with `status='queued' AND scheduled_at <= now()` ordered by `scheduled_at` using `FOR UPDATE SKIP LOCKED`, set `status='sending'` and `claimed_until = now()+2 min`, commit, then process each: re-check appointment status = booked and (for reminders) account not opted out and not cancelled; render from the catalogue; call the adapter with retry (attempts 1-3, waits 5 s and 30 s, timeout 5 s); write result. Rows whose lease expired are requeued by the next cycle. A per-provider circuit breaker (5 failures in 60 s opens it for 60 s, then one probe) leaves rows `queued` while open.
- **Rationale**: ADR-0002; works with 2 replicas; no broker at this volume.
- **Alternatives**: separate worker process (kept as an option if RSK-004 materialises; the code is a plain coroutine that can be moved).

## R4: Idempotency
- **Decision**: unique key `(kind, appointment_id, appointment_version)` for appointment messages, so a retried booking request cannot create a second confirmation or reminder; the send passes the message id as the provider's client reference when the provider supports it. Webhooks: receipts update by `provider_message_id`, only move status forward (`sent` -> `delivered`/`failed`), and repeat calls do nothing; unknown ids are ignored with 200.
- **Rationale**: thr-018, thr-015, thr-016; QA-004.

## R5: Webhook security
- **Decision**: HMAC-SHA256 over the raw body with the per-provider shared secret from the secret store, constant-time compare, header name set in the adapter (provider-specific); unsigned or bad signature gets 401 and nothing is parsed. A small in-process token bucket per source IP plus the edge rate limit (thr-017). Handlers do a single indexed update and always answer quickly.
- **Alternatives**: IP allow-list only (not chosen; not available from all providers).

## R6: STOP handling
- **Decision**: Parse inbound text with `text.strip().upper() == "STOP"` (plus the provider's own opt-out keyword flag if given). Find the patient account by sender phone, set `reminders_opt_out=true` (source `stop_reply`, time), and in the same transaction set pending reminder rows to `cancelled`. Effective at once on receipt (requirement: within 1 hour). Confirmations and change notices ignore the flag.
- **Rationale**: FR-031, NFR-011, QA-009.

## R7: Provider unknown (ASM-009)
- **Decision**: `ChannelPort` has `send(message) -> SendResult`, `parse_receipt(body)`, `parse_inbound(body)`, `verify(headers, body)`. A sandbox adapter (fixed latency, controllable failures) is used in dev/staging and in tests; the real adapters are written to the same port and mapped to a provider's contract once chosen. Error mapping: `transient` (timeout, 5xx, 429), `permanent` (invalid number, template rejected), `unknown`.
- **Rationale**: ports and adapters (ADR-0006); keeps work unblocked by DEP-001/DEP-002.
- **Release 2 room**: `SendResult.error_class` and `message.original_message_id` let feature 009 add "if WhatsApp permanently fails create one SMS row" without changing the port.

## R8: Templates and catalogue
- **Decision**: One English catalogue `catalogue.py` keyed by `MessageKind`, with the variable names `clinic`, `dentist`, `date`, `time`, `link`, `code` (treatment for confirmation). Template ids per `(kind, channel)` live in settings (environment-specific). A startup check fails if a kind/channel has no template id in production. Dates formatted `DD Mon YYYY`, times `hh:mm AM/PM` in IST.
- **Rationale**: NFR-008, NFR-011, QA-012. Only these variables are passed to a provider; the rendered text is stored only for support and deleted after 90 days.

## R9: Sign-in code
- **Decision**: `messaging.service.send_code(phone, code)` is called by cmp-identity in the request; it calls the SMS adapter directly (timeout 5 s, no retry in the request), records a `message` row of kind `code` with no rendered text and returns success/failure; cmp-identity decides the answer to the patient.
- **Rationale**: Architecture says the code is sent in the request, not by the dispatcher (rel-007).

## R10: Nightly reconciliation and retention (JOB-005)
- **Decision**: One nightly job (02:00 IST) guarded by a PostgreSQL advisory lock so it runs once across replicas: (a) booked appointments starting 24h-48h ahead eligible for a reminder but without a reminder row (and not opted out) get one; (b) `sending` rows past their lease go back to `queued`; (c) `queued` rows for cancelled appointments are set `cancelled`; (d) delete `message` rows older than 90 days. Each repair is logged and counted.
- **Rationale**: ADR-0002; ASM-012.

## R11: Lag alert
- **Decision**: Every dispatcher cycle records the metric `messaging.reminder_lag_seconds` = max(now - scheduled_at) over queued due reminders; an alert rule fires at 600 s. Rollback trigger at 15 minutes is the existing deployment rule.
- **Rationale**: architecture sections 8 and 10.

## R12: Front-end
- **Decision**: `ChannelChoice` radio group (SMS / WhatsApp) on the existing confirm screen, 44 px targets, default from `GET /api/me/preferences`; booking request carries `channel`. `ReminderToggle` on the reception patient record screen calls the reception endpoint. No other screens change.
