# Data Model: Confirmations, reminders, STOP and SMS fallback

One new table (`messages`, entity ent-message, owned by cmp-messaging). Reads, through the owning modules' interfaces: patient account (channel, phone, `reminders_opt_out`; cmp-identity) and appointment (clinic, dentist, treatment, start, status, channel; cmp-booking). Times are `timestamptz` stored in UTC and shown in IST.

## messages (MVP migration `007_01_messages`)

| Column | Type | Notes |
|--------|------|-------|
| id | uuid, PK | also sent to the provider as the client reference |
| kind | enum: `sign_in_code`, `confirmation`, `change_notice`, `reminder` | |
| template_key | text | `sign_in_code`, `confirmation`, `change_cancelled`, `change_rescheduled`, `reminder` |
| channel | enum: `sms`, `whatsapp` | sign-in code is always `sms` |
| patient_account_id | uuid, FK to patient account | |
| appointment_id | uuid, FK to appointment, nullable | null for `sign_in_code` |
| to_phone | text | PII; E.164; used only by the dispatcher; never logged |
| due_at | timestamptz | nominal time (start − 24 h for reminders; creation time otherwise) |
| send_at | timestamptz | adjusted send time (quiet hours); the time NFR-005 is measured against |
| status | enum: `queued`, `sending`, `sent`, `delivered`, `failed`, `skipped`, `cancelled` | see state machine |
| skip_reason | text, nullable | `appointment_not_booked`, `opted_out`, `start_passed`, `no_template` |
| attempts | int, default 0 | |
| claimed_at | timestamptz, nullable | set when `sending`; used by the nightly job to find stuck rows |
| provider_message_id | text, nullable | |
| params | jsonb, nullable | templated values only: clinic, dentist, treatment, date, time, link; null for `sign_in_code` |
| rendered_text | text, nullable | PII; null for `sign_in_code`; deleted with the row |
| dedupe_key | text, unique | e.g. `confirmation:<appointment_id>:<version>`, `reminder:<appointment_id>:<start_at>` |
| sent_at, delivered_at | timestamptz, nullable | |
| last_error | text, nullable | error class only, no personal data |
| created_at, updated_at | timestamptz | retention is counted from `created_at` |

Indexes and constraints:
- partial index on `(send_at)` where `status = 'queued'` (dispatcher claim);
- unique `(channel, provider_message_id)` where `provider_message_id` is not null (idempotent receipts);
- partial unique index on `(appointment_id)` where `kind = 'reminder'` and `status in ('queued','sending')` and the row is not a fallback (one live reminder per appointment);
- index on `(created_at)` for the 90-day purge;
- index on `(patient_account_id, status)` for opt-out lookups.

## Release 2 migration `007_02_reminder_fallback` (expand only)

| Column | Type | Notes |
|--------|------|-------|
| original_message_id | uuid, nullable, FK to messages.id, **unique** | set on the fallback SMS; the unique key is what makes the fallback once per reminder (thr-018) |
| reminder_failed_at | timestamptz, nullable | set on the original reminder row when no permitted channel delivered it |

Index: partial on `(reminder_failed_at)` where not null, used by the reception list.

The partial unique index for live reminders excludes rows with `original_message_id` set, so the fallback SMS can exist beside the failed WhatsApp row.

## Status state machine

```
queued ──claim──▶ sending ──provider accepts──▶ sent ──receipt──▶ delivered
   ▲                 │                            │
   │   breaker open  │ permanent error or         └─failed receipt──▶ failed
   └─────────────────┤ 3 attempts used
                     └──────────────▶ failed
queued ──re-check fails or appointment cancelled/rescheduled──▶ skipped | cancelled
```

- `delivered` and `failed` are final; a later receipt never moves a final status (replays do nothing). `sent` then `failed receipt` is allowed because the provider may report failure after acceptance; `delivered` then `failed` is ignored.
- `skipped`: the re-check before sending found the appointment not booked or already started, or the patient opted out (reminders only), or no approved template.
- `cancelled`: set by the facade when an appointment is cancelled or rescheduled.

## Reminder failed (Release 2)

A reminder "failed" for an appointment when its root reminder row (the one with no `original_message_id`) has `reminder_failed_at` set. This happens when:
1. a WhatsApp reminder failed finally and the fallback switch is off; or
2. a WhatsApp reminder failed, the fallback SMS was created and it failed finally; or
3. an SMS reminder (chosen channel) failed finally.

## Reads from other modules (interfaces in `app/modules/messaging/ports.py`)

| Need | Owner | Used for |
|------|-------|----------|
| appointment snapshot: id, clinic name, dentist name, treatment, start_at, status, channel, patient account id | cmp-booking | building params, send-time re-check, nightly job |
| list of upcoming booked appointments for a patient account | cmp-booking | re-creating reminders when reception switches reminders on |
| account: phone, `reminders_opt_out`; find account by phone; set/clear `reminders_opt_out` | cmp-identity | dispatcher re-check, STOP, reception switch |
| access context (role, clinic) | cmp-identity | reception list and reminders switch |

## Retention and privacy

- `messages` rows are deleted 90 days after `created_at` (ASM-012); `rendered_text`, `params` and `to_phone` are personal data.
- Erasure on request (feature 002) removes or anonymises the account's messages through a messaging function `purge_account_messages(account_id)`.
- Sign-in code rows hold no code and no text.
