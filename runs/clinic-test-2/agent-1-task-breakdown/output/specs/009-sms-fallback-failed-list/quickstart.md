# Quickstart: validating the SMS fallback and reminders-failed list

Prerequisites: feature 006 deployed in a test environment (dispatcher, WhatsApp and SMS sandbox adapters, signed webhooks); a clinic with a receptionist account; two patients with WhatsApp as their channel and appointments tomorrow (IST) at that clinic; the web app built with the Release 2 flag on.

## 1. Fallback sends once (US1)

1. Configure the WhatsApp sandbox to fail every send. Run the dispatcher for a due reminder.
2. Expect: after 3 attempts the original is `failed`, exactly one SMS message exists with `fallback_of_message_id` set, and the SMS sandbox received one message.
3. Replay a signed failed receipt for the same WhatsApp message id twice. Expect: still one SMS.

## 2. Guards and switch (US2)

1. Set the patient's reminders off (STOP). Fail the WhatsApp message. Expect: no SMS, no `reminder_failed`.
2. Cancel the appointment, then fail its WhatsApp message. Expect: no SMS.
3. Set `REMINDER_SMS_FALLBACK_ENABLED=false`, restart, fail a WhatsApp reminder. Expect: no SMS; status `reminder_failed`.
4. Remove the setting. Expect: fallback works again (default on).

## 3. Reminder failed (US3)

1. Fail WhatsApp and the SMS sandbox. Expect: status `reminder_failed` on the SMS fallback row, once.
2. Replay the SMS failed receipt. Expect: no change.
3. Send a delivered receipt for the SMS. Expect: the mark is removed.

## 4. The list (US4)

1. As the receptionist call `GET /api/reception/reminders-failed` (contract: `contracts/reminders-failed.openapi.yaml`).
2. Expect: only tomorrow's booked appointments of this clinic with the mark, ordered by time; 403 for patient, dentist and practice manager; no other clinic's rows.

## 5. The screen (US5)

1. Flag on, sign in as the receptionist, open "Reminders failed". Expect: the same rows, each with a phone number to call; the empty state when none.
2. Flag off. Expect: no entry and the not-found page at the route.

Run: `pytest tests/messaging tests/reception tests/contract` in clinic-api; the web test runner in clinic-web.
