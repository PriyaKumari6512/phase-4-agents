# Clarifications: Family members on a patient account

No user was available; each question was answered with the most reasonable option and the assumption is in spec.md.

## Q1: Do family members need their own sign-in on the same phone? (PRD Q-007, RSK-003)

| Option | Answer | Implications |
|---|---|---|
| A | No: one account per phone number, only the account holder signs in; family members are people on that account (SA-001, ASM-001) | Matches ADR-0008 and the PRD text of FR-006. Nothing to build for sign-in. |
| B | Yes: each family member signs in separately on the same phone | Sign-in and cmp-identity change, about 2-4 person-days (RSK-003). Phone-code sign-in cannot tell them apart today. |

**Assumed**: A (spec.md A-3). Owner: client, PRD Q-007. If B, this feature is reworked in cmp-identity sign-in.

## Q2: Can a patient edit or remove a family member after adding them?

| Option | Answer | Implications |
|---|---|---|
| A | No: only add is specified in FR-006; a mistake is fixed by phoning the clinic or by a deletion request | Smallest scope. The `active` flag of ADR-0008 stays unused by the screens. |
| B | Edit name and birth year, and deactivate | More screens and rules (what happens to future appointments, no-show history, the 5-limit). Not in the PRD. |
| C | Deactivate only | Frees a place under the 5-limit but may let a no-show history be dropped (PD-007). |

**Assumed**: A (spec.md A-4). Raise with the client.

## Q3: Does the limit of 5 include the account holder?

| Option | Answer | Implications |
|---|---|---|
| A | No: the account holder plus up to 5 family members (6 people) | Follows the PRD wording "up to 5 family members" and ADR-0008 (the holder is a person too). |
| B | Yes: 5 people in total including the holder | Only 4 family members. |

**Assumed**: A (spec.md A-5).

## Q4 (found while planning): May a family member's name be sent in an SMS or WhatsApp message?

| Option | Answer | Implications |
|---|---|---|
| A | Yes: add a person-name value to the registered/approved templates | Needs template changes by feature 007 and by the clinic's DLT and WhatsApp registration (NFR-011, RSK-001); thr-013's list of template values (clinic, dentist, date, time, link) grows by one. |
| B | No: messages keep only the link, which opens the appointment naming the person | No template change; the account holder cannot tell from the message text who the visit is for. |

**Assumed**: A, with B as the fallback if templates cannot carry the name in time (spec.md A-12, research.md R-7).
