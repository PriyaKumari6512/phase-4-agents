# Clarifications: 009 WhatsApp to SMS fallback and reminders-failed list

## Q1: Does the client agree to the WhatsApp-to-SMS fallback?

**Source**: prd.md "Questions to raise", item 2; ISS-001, ASM-005, RSK-005.

**Context**: FR-029 sends an SMS to a patient who chose WhatsApp when the WhatsApp message fails. This adds SMS charges, which the clinic pays (CON-007). The client has not agreed.

| Option | Answer | Implications |
|--------|--------|--------------|
| A | Build it behind a switch, default on | Reminders still reach patients; extra SMS charges; client can turn it off at any time without a release |
| B | Build it behind a switch, default off | No extra charges until agreed; more reminders end as "reminder failed" for reception to phone |
| C | Do not build the fallback; only the failed list | Smallest scope; loses FR-029's first sentence |

**Assumed**: A (matches PD-005 and SA-008). Built behind a switch, default on. A finally failed WhatsApp reminder with the switch off is marked "reminder failed".

**Why**: The PRD default is to fall back; the switch removes the risk if the client says no. Delivery is not hard dated (DL-2 2027-03-19), so the answer can still arrive before release.

**Status**: Open question Q1 (assumed answer A).
