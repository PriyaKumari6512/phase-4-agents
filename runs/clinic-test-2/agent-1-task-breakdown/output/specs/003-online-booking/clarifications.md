# Clarifications: Online booking by patients (003)

No user was available. For each question the most reasonable option was assumed.

## Q1: Family members at booking time (PRD open question Q-007)

- **Question**: The flow has a "who is the visit for" step. Family members are Release 2 (FR-006). What does Release 1 show?
- **Options**: (A) only the patient themselves, pre-selected, no extra screen; (B) a full who-for screen with a disabled family list; (C) hide the step completely.
- **Assumed**: A. The "who and what" screen shows the patient's own name as the pre-selected person. The booking request still names the person, so Release 2 can add family members without changing the contract; the server accepts only the signed-in patient's own person.
- **Why**: Keeps the 5-screen limit (NFR-010) and avoids rework when Q-007 is answered.

## Q2: Repeated request after a "slot taken" answer

- **Question**: If a request with a retry key got a 409 "slot taken" and is repeated with the same key, what is returned?
- **Options**: (A) the same 409 with fresh next free slots; (B) try again to book; (C) an error.
- **Assumed**: A. The key is stored with the final outcome of an attempt, success or conflict; a repeat returns the stored outcome (for a conflict, with next free slots re-read). A patient who picks another slot sends a new key.
- **Why**: A retry must never book twice and must not silently book a different outcome.

## Q3: Where the SMS/WhatsApp choice is saved

- **Question**: Feature 006 (FR-013) remembers the channel for the next booking. Does this feature save it too?
- **Options**: (A) this feature sends the channel with the request and stores it on the appointment only; the default for next time is kept by identity/messaging; (B) this feature also updates the patient's saved choice.
- **Assumed**: A.
- **Why**: Account preference belongs to the identity component; avoids two owners of one value.
