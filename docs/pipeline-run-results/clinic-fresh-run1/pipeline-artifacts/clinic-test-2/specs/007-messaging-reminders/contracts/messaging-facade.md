# In-process contracts of cmp-messaging (for features 002, 004, 005, 006)

Module: `clinic-api/app/modules/messaging/`. All calls are in-process Python. Calls that create rows take the caller's database session and must be made inside the caller's transaction.

## 1. Facade for appointment changes (`service.py`, `MessagingFacade`)

| Function | Called by | Effect |
|----------|-----------|--------|
| `on_booking_created(session, appointment_id)` | booking (004), reception booking (006) | Writes the confirmation row; writes a reminder row when the appointment starts 24 h or more from now |
| `on_appointment_cancelled(session, appointment_id)` | cancel by patient (005), by reception (006) | Marks queued reminders `cancelled`; writes a change notice (`change_cancelled`) |
| `on_appointment_rescheduled(session, appointment_id, old_start_at)` | reschedule by patient (005), by reception (006) | Marks old queued reminder `cancelled`; writes a change notice (`change_rescheduled`) with the new details; writes a new reminder if the new start is 24 h or more away |
| `reinstate_reminders(session, patient_account_id)` | reminders switch (this feature) | Creates missing reminders for the account's future booked appointments that are 24 h or more away |
| `purge_account_messages(session, patient_account_id)` (in `retention.py`, re-exported by `service.py`) | erasure on request (002) | Deletes the account's messages |

Rules:
- The appointment must already be written (flushed) in the same session: the facade reads the appointment through the booking interface.
- Calls are idempotent (unique `dedupe_key`); repeating a call never creates a second message.
- The facade never sends. Sending is done by the dispatcher after commit.
- Cancelling for any reason (patient, reception, clinic) must call `on_appointment_cancelled`; the send-time re-check is a second guard but not a replacement.

## 2. Sign-in code port (`sign_in_code.py`)

```text
send_sign_in_code(phone_e164: str, code: str) -> SendResult
SendResult: status = "accepted" | "failed" ; reason = "provider_unavailable" | "rejected" | "no_template" | None
```

- Sent during the call through the SMS adapter; one attempt; timeout 5 s; shares the SMS circuit breaker; never queued.
- Returns at once; the caller (feature 002) shows "could not send, try again" on `failed`.
- Writes a message row (`kind = sign_in_code`) with status and provider id only; the code and text are not stored and not logged.
- Not affected by the reminders-off flag.

## 3. Identity functions used by messaging (`app/modules/identity/reminder_preferences.py`)

| Function | Used for |
|----------|----------|
| `find_account_by_phone(session, phone_e164) -> account or None` | STOP replies |
| `get_reminders_enabled(session, account_id) -> bool` | send-time re-check |
| `set_reminders_enabled(session, account_id, enabled, actor)` | STOP (actor = system) and reception switch |

## 4. Booking interface used by messaging (`app/modules/messaging/ports.py`)

| Function | Returns |
|----------|---------|
| `get_appointment_snapshot(session, appointment_id)` | id, clinic name, dentist name, treatment, start_at, status, channel, patient account id; or None |
| `list_upcoming_booked(session, patient_account_id)` | snapshots of future appointments with status booked |
| `list_booked_starting_between(session, from_at, to_at)` | used by the nightly job to find missing reminders |

## 5. Channel adapter port (`app/modules/channel_adapters/base.py`)

```text
ChannelPort.send(template_id: str, to_phone: str, params: dict, client_ref: str) -> ProviderResult
    ProviderResult: ok(provider_message_id) | transient_error(code) | permanent_error(code)
ChannelPort.verify_signature(headers, raw_body) -> bool
ChannelPort.parse_webhook(raw_body) -> list[ProviderEvent]
    ProviderEvent: kind = delivered | failed | inbound_text ; provider_message_id | from_phone ; text ; occurred_at
```

One implementation per provider (`sms.py`, `whatsapp.py`). Only `params` (clinic, dentist, treatment, date, time, link) and the phone number cross this port.
