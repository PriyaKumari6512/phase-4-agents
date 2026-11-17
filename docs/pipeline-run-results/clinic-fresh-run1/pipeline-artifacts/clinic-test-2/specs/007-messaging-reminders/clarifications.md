# Clarifications: Confirmations, reminders, STOP and SMS fallback

No user was available during specification. Each question below has an assumed answer; the spec uses it.

## Q1: When is a night-time reminder sent? (prd.md Q-009, FR-027)

| Option | Answer | Implications |
|--------|--------|--------------|
| A | Due 21:00-24:00 goes at 20:00 the same evening; due 00:00-08:00 goes at 20:00 the evening before; if that time has already passed at booking, send at once outside quiet hours, otherwise at 08:00 (ASM-003) | Matches architecture; NFR-005 is measured against the adjusted time |
| B | All night-time reminders go at 08:00 | Reminder can arrive less than a few hours before an early appointment; contradicts FR-027 text |
| C | Send at the due time regardless of quiet hours | Breaks PD-004 |

**Assumed**: A. Why: it is the PRD default (SA-003, PD-004) and ASM-003. The rule is a small isolated function, so a change by the client is cheap.

## Q2: Does the clinic agree to the WhatsApp-to-SMS fallback? (ISS-001, ASM-005, FR-029)

| Option | Answer | Implications |
|--------|--------|--------------|
| A | Yes, fallback on | More reliable reminders; extra SMS charges paid by the clinic |
| B | No, fallback off | A failed WhatsApp reminder is marked "reminder failed" at once and reception phones the patient |
| C | Yes but only for reminders, not confirmations | Same as A for this spec |

**Assumed**: A (switch default on, per SA-008 and PD-005), limited to reminders. Why: the PRD default; built behind a switch so the answer can change without a code change. It is Release 2.

## Q3: Can a patient who chose WhatsApp stop reminders by replying STOP in WhatsApp? (FR-031)

| Option | Answer | Implications |
|--------|--------|--------------|
| A | Only SMS STOP replies are processed; WhatsApp patients ask reception | Matches the webhooks in the architecture (rel-009 carries STOP replies, rel-010 carries receipts only) |
| B | Also process inbound WhatsApp STOP messages | Needs the WhatsApp provider to forward replies and a change to rel-010 |
| C | Reminders in WhatsApp include a button or text to opt out | Needs template approval changes |

**Assumed**: A. Why: it is what the architecture supports and keeps the MVP small. Confirm with the client and the chosen WhatsApp provider; the adapter design allows B later.
