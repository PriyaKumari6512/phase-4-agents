# Quickstart: validating messaging and reminders

Prerequisites: local or staging environment with the API, a PostgreSQL database, and the fake provider (`clinic-api/tests/fakes/fake_provider.py`) or the providers' sandbox accounts (staging). Test patients and a test clinic exist (from features 002-004).

## 1. MVP scenarios (User Stories 1-7)

1. **Confirmation (US1)**: book an appointment with channel SMS, then another with WhatsApp. Expect one message each within about 30 s with clinic, dentist, treatment, date, time (IST) and an appointment link. Cancel and reschedule one; expect one change notice each.
2. **Reminder and quiet hours (US2)**: with the test clock, create appointments for Tuesday 11:00, 22:30, 03:00 and 08:00 and check the send times (Mon 11:00, Mon 20:00, Sun 20:00, Mon 08:00). Book Tuesday 22:00 at Mon 20:30 (sent at once) and at Mon 21:15 (sent Tue 08:00).
3. **No wrong reminders (US3)**: cancel an appointment whose reminder is queued, and one whose reminder is due this second; reschedule one; book one less than 24 h ahead. Expect no reminder, one reminder for the new time, and only a confirmation.
4. **STOP (US4)**: post a signed STOP reply from a test number to `/api/webhooks/sms`; expect queued reminders skipped, a later booking still confirmed. Switch reminders off and on as reception through `PUT /api/patient-accounts/{id}/reminders`.
5. **Reliability and compliance (US5)**: make the fake provider slow, then failing; expect retries (5 s, 30 s), breaker after 5 failures in 1 minute, messages staying queued and sent on recovery, the lag alert at 10 minutes, and no duplicates when the same webhook is posted twice. Run the nightly job and check the counts. Try an unsigned webhook (expect 401) and a message with an unapproved template (expect no send).
6. **Provider onboarding (US6)**: run the readiness check (`python -m app.modules.messaging.readiness`); expect it to list every template that is not approved or has no id configured. In staging, confirm messages reach the sandbox accounts only.
7. **Sign-in code (US7)**: call `send_sign_in_code` with a sandbox number; expect an SMS from the sign-in template and an immediate `failed` result when the fake provider is down. Check that the message row and the logs hold no code.

## 2. Release 2 scenarios (User Stories 8-9)

1. **Fallback (US8)**: fail a WhatsApp reminder in the fake provider; expect exactly one SMS. Replay the failed receipt; expect no second SMS. Make the SMS fail; expect the appointment marked "reminder failed". Set `WHATSAPP_SMS_FALLBACK_ENABLED=false`; expect no SMS and the appointment marked at once.
2. **Reminders failed list (US9)**: with the flag `r2_reminders_failed` on, sign in as a receptionist of clinic A; open "Reminders failed"; expect only clinic A's tomorrow appointments with a failed reminder, not cancelled ones. Sign in as the manager; expect both clinics.

## 3. Commands (from the repo roots)

- API tests: `pytest tests/messaging tests/channel_adapters tests/reception tests/contract` in `brightsmile/clinic-api`.
- Web tests: the test script of `brightsmile/clinic-web` for `RemindersFailedPage` and `RemindersToggle`.
- Contract: `tests/contract/test_messaging_contract.py` checks `contracts/messaging-api.openapi.yaml`.

## 4. Expected outcomes (from spec success criteria)

- SC-002: in the simulated day test at least 99% of reminders are sent within 15 minutes of the adjusted time.
- SC-003: zero reminders for cancelled appointments.
- SC-005: every send used an approved template (test asserts on the adapter call).
- SC-007: never two reminders per appointment; never two fallbacks per reminder.
