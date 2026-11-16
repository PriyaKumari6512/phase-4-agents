# Data Model: 006-reminders-messages

Owner components: cmp-messaging (`message`), cmp-identity (account preferences), cmp-booking (`appointment.channel`). Alembic migrations are forward-only and compatible with the previous release (expand, then contract).

## Table `message` (ent-message, owner cmp-messaging)

| Column | Type | Rules |
|---|---|---|
| id | uuid | primary key |
| kind | text | NOT NULL; one of `confirmation`, `change_notice`, `reminder`, `code` |
| channel | text | NOT NULL; one of `sms`, `whatsapp` (`code` is always `sms`) |
| patient_account_id | uuid | NOT NULL; FK patient account |
| appointment_id | uuid | NULL for `code`; FK appointment otherwise |
| appointment_version | int | NULL for `code`; the appointment's change counter when the row was created, part of the idempotency key |
| due_at | timestamptz (UTC) | When the message is due by the plain rule (reminder: start minus 24 h; others: creation time) |
| scheduled_at | timestamptz (UTC) | NOT NULL; the send time after the quiet-hours adjustment; NFR-005 is measured on it |
| status | text | NOT NULL; `queued`, `sending`, `sent`, `delivered`, `failed`, `cancelled`, `skipped`; default `queued`. R2 adds no value here (fallback reuses `failed` plus a new row) |
| status_reason | text | NULL; e.g. `appointment_cancelled`, `opted_out`, `provider_permanent_error`, `retries_exhausted` |
| provider | text | NULL until sent; configured provider name |
| provider_message_id | text | NULL until accepted; unique where not null (webhook idempotency) |
| template_id | text | template id used (from configuration) |
| attempts | smallint | NOT NULL default 0; 0 to 3 |
| claimed_until | timestamptz | NULL; lease while `sending` |
| rendered_text | text | NULL; holds PII (names, dates); NULL for `code`; deleted with the row after 90 days |
| original_message_id | uuid | NULL; reserved for the Release 2 fallback (unique where not null); not written in this feature |
| error_class | text | NULL; `transient`, `permanent`, `unknown` |
| created_at / sent_at / delivered_at | timestamptz | audit |

Constraints and indexes:
- UNIQUE `(kind, appointment_id, appointment_version)` WHERE `appointment_id IS NOT NULL` (idempotent creation).
- Partial index on `(scheduled_at)` WHERE `status = 'queued'` for the claim query.
- Index on `(appointment_id, kind, status)` for cancelling pending reminders.
- Index on `(patient_account_id, kind, status)` for STOP.
- CHECK `attempts BETWEEN 0 AND 3`.

State transitions: `queued -> sending -> sent -> delivered`; `sending -> queued` (retry/lease expiry, attempts < 3); `sending -> failed` (permanent error or retries exhausted); `queued -> cancelled` (appointment cancelled/rescheduled, STOP for reminders); `queued -> skipped` (re-check finds appointment no longer booked or opted out at send time); `sent -> failed` (failed receipt). Receipts never move status backwards.

## Patient account additions (ent-patient-account, owner cmp-identity)

| Column | Type | Rules |
|---|---|---|
| preferred_channel | text | NOT NULL default `sms`; `sms` or `whatsapp`; updated when a booking is saved |
| reminders_opt_out | boolean | NOT NULL default false |
| reminders_opt_out_at | timestamptz | NULL |
| reminders_opt_out_source | text | NULL; `stop_reply` or `reception` |
| reminders_opt_out_by | uuid | NULL; staff account id when source is `reception` |

Reception changes also write a row to the existing audit/history mechanism of cmp-identity (who, what, when).

## Appointment addition (ent-appointment, owner cmp-booking)

| Column | Type | Rules |
|---|---|---|
| channel | text | NOT NULL; `sms` or `whatsapp`; chosen on the confirm screen; used for every message about the appointment |

Reschedule keeps the same channel; the appointment's change counter (`version`) increments on reschedule.

## Configuration (not tables)

| Setting | Meaning |
|---|---|
| `MSG_TEMPLATE_IDS` | map `(kind, channel)` to the registered or approved template id |
| `QUIET_START` / `QUIET_END` / `EVENING_SEND` | 21:00 / 08:00 / 20:00 IST (Q-009 open) |
| `REMINDER_LEAD_HOURS` | 24 |
| `SMS_PROVIDER`, `WHATSAPP_PROVIDER` | `sandbox` or the chosen provider name (switch) |
| provider keys and webhook secrets | from the secret store, never in files |
