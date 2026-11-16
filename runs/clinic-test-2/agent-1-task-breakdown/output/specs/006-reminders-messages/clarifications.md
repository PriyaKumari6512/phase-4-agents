# Clarifications: 006-reminders-messages

No user was available; the most reasonable option was assumed for each question.

## Q1: Q-009 - When is a night-time reminder sent?

- Options: (A) 20:00 the evening before the quiet period (SA-003, PD-004, ASM-003); (B) 08:00 on the due day; (C) send exactly on time regardless of quiet hours.
- Assumed: **A**. Due 21:00-23:59 goes at 20:00 the same evening; due 00:00-07:59 goes at 20:00 the evening before; if that time has passed at booking, send at once outside quiet hours, otherwise at 08:00.
- Why: It is the PRD default and ASM-003; NFR-005 is measured against the adjusted time. Quiet-hours start, end and send times are configuration values so the answer can change without code changes.

## Q2: Which SMS and WhatsApp providers?

- Options: (A) pick one provider per channel now; (B) build against our own port with a sandbox/fake provider and bind the real provider by configuration when chosen; (C) wait for the choice.
- Assumed: **B** (ASM-009, ADR-0006). Adapters are written to a generic contract (send, template mapping, error mapping, HMAC-signed webhooks); the real provider's field names are filled in when chosen (provider test accounts in weeks 1-2).
- Why: Provider choice and DLT/template approval (DEP-001, DEP-002, RSK-001) must not block development.

## Q3: Does the client accept the WhatsApp-to-SMS fallback?

- Options: (A) yes, built in Release 2 (feature 009) behind a switch; (B) no fallback.
- Assumed: **A**, but it is not part of this feature (ISS-001, ASM-005). Here a failed WhatsApp message is retried (3 attempts) and then marked failed; message status values and the adapter leave room for the fallback.
- Why: Keeps this feature within the Release 1 scope of the request.
