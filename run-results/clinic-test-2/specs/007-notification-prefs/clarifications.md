# Clarifications: Notification preferences

No user was available; the most reasonable option was assumed for each question.

## Q1: Which channels besides email, and which frequencies, should FR-7 offer?

Source: prd.md section 7 (open question, client has not decided). Affects: User Story 1, 2, 3.

| Option | Answer | Implications |
|--------|--------|--------------|
| A | Email only; frequencies immediate, hourly, daily, all as configuration data | Matches the PRD assumption; adding values later needs no code change in senders |
| B | Email only; immediate and daily | Smaller batching scope |
| C | Email plus other channels | Out of scope: no other channel is named in prd.md or architecture.md |

**Assumed**: A. This is a working assumption, not a decision; the client still has to answer. The data model keeps channels and frequencies configurable.

## Q2: May a user delay or switch off the assignment email, given US-5 promises an email within 1 minute?

Source: US-5, FR-5, FR-7, G2. Affects: User Story 2, 3.

| Option | Answer | Implications |
|--------|--------|--------------|
| A | Yes by explicit user choice; default stays immediate | US-5 holds for every user who did not change the setting |
| B | Assignment emails are always immediate and cannot be switched off | Conflicts with US-7 intent for that type |

**Assumed**: A.
