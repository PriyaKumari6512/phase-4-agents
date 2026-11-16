# Quickstart: validating 006-reminders-messages

Prerequisites: clinic-api running with PostgreSQL 16 and migrations applied; `SMS_PROVIDER=sandbox`, `WHATSAPP_PROVIDER=sandbox`; template ids set for every (kind, channel); webhook secrets set for the sandbox providers; clinic-web running against it. Contracts: [contracts/messaging-api.md](contracts/messaging-api.md). Tables: [data-model.md](data-model.md).

## Scenario 1: channel choice and confirmation (US1, US2)
1. Sign in as a new patient, book a check-up; the confirm screen shows SMS selected. Choose WhatsApp and confirm.
2. Expected: booking succeeds at once; within 1 minute the sandbox WhatsApp provider has one confirmation (clinic, dentist, treatment, date, time IST, link); `message` row has `kind=confirmation`, `status=sent`.
3. Start another booking: WhatsApp is pre-selected.

## Scenario 2: reminder timing (US3)
1. Book an appointment 3 days ahead at 14:00: one `reminder` row with `scheduled_at` = due time 14:00 IST two days later.
2. Book one at 22:30 and one at 03:00: `scheduled_at` is 20:00 IST same evening / 20:00 IST the evening before the due time.
3. Book one starting in 10 hours: no reminder row, only the confirmation.
4. Move the clock (or set `scheduled_at` to the past) and run a dispatcher cycle: the reminder is sent within 15 minutes of `scheduled_at` with a link that opens the appointment.

## Scenario 3: cancel and reschedule (US4)
1. Cancel a booked appointment with a pending reminder: reminder row `cancelled`, a cancellation notice is sent; dispatcher never sends the reminder.
2. Reschedule another: old reminder `cancelled`, exactly one new reminder for the new time, change notice sent.

## Scenario 4: STOP and reception opt-out (US5)
1. POST a correctly signed inbound `STOP` to `/api/webhooks/sms` for the patient's number: account flag set, pending reminders `cancelled`; a new booking still gets a confirmation but no reminder. An unsigned call returns 401.
2. As a receptionist switch reminders off and on from the patient record; changes show who and when.

## Scenario 5: sign-in code (US6)
Request a code for a test number: one SMS through the code template; sandbox set to fail returns the "try again" answer within about 5 s.

## Scenario 6: reliability (US7)
1. Make the sandbox fail: attempts 1-3 at 0 s, 5 s, 30 s; after 5 failures in a minute the breaker opens and rows stay `queued`; they send when it recovers.
2. Replay the same delivery receipt twice and one with an unknown id: no change after the first.
3. Hold a due reminder unsent for 10 minutes: lag metric passes 600 s and the alert fires.
4. Run the nightly job: it creates a missing reminder, requeues an expired lease and deletes rows older than 90 days.

Automated: `pytest tests/unit/messaging tests/unit/channel_adapters tests/integration/messaging tests/contract` in clinic-api; `npm test` in clinic-web.
