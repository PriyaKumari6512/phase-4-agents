# Data Model: WhatsApp to SMS fallback and reminders-failed list

Only `ent-message` (owner cmp-messaging, store ctr-db) changes. Everything else is read through the owning component's interface.

## ent-message (changes)

| Field | Type | Rule |
|---|---|---|
| `fallback_of_message_id` (new) | UUID, nullable, foreign key to `ent-message.id` | Set only on an SMS fallback row; points to the original WhatsApp message. **Unique index**: at most one fallback per original message (thr-018). |
| `status` (existing) | enum | New value `reminder_failed`. Existing values from feature 006 stay. |
| `channel` (existing) | enum `sms`, `whatsapp` | A fallback row has channel `sms`; its original has channel `whatsapp`. |
| `kind` (existing) | enum | Fallback applies to kind `reminder` only. A fallback row has kind `reminder`. |

New index to serve the list: `(kind, status, appointment_id)` where `status = 'reminder_failed'` (partial index).

Retention is unchanged: 90 days, then deleted (ASM-012). A fallback row is deleted with its original; the foreign key deletes in order (fallback first).

### State transitions of a WhatsApp reminder (extends 006)

```text
queued -> sent -> delivered                       (no fallback)
queued/sent -> failed (3 attempts or failed receipt)
   failed -> [guards pass, switch on]  -> fallback SMS row created (status queued)
   failed -> [opted out or appointment cancelled] -> stays failed, no SMS, no mark
   failed -> [switch off or no SMS number]        -> reminder_failed
fallback SMS: queued -> sent -> delivered         (done)
fallback SMS: queued/sent -> failed               -> reminder_failed on the fallback row
reminder_failed -> delivered                       (a later delivered receipt)
```

`delivered` is final: a failed receipt that arrives after a delivered one is ignored.

## Fallback setting

| Name | Type | Default | Notes |
|---|---|---|---|
| `REMINDER_SMS_FALLBACK_ENABLED` | boolean (environment setting) | `true` | Read at decision time and at send time of the fallback SMS. |

## Read model: reminders-failed list item

Built by a query, not stored. Fields: `appointment_id`, `start_time` (UTC in storage, IST in the response), `patient_name`, `patient_phone`, `dentist_name`, `treatment_name`, `failed_at`.

Rules: appointment status is `booked`; start falls on tomorrow in IST; appointment clinic equals the receptionist's clinic; one row per appointment; ordered by start time. Name and phone are PII: returned only to a receptionist of that clinic and never logged.
