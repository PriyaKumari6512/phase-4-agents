# Clarifications: Reception day view, check-in, no-show and dentist day

No user was available during the run. Each question below has the option that was assumed; the spec carries `Assumed: ... (open question Qn)` where it matters.

## Q1: How are walk-ins recorded? (PRD Q-015, FR-020)

Options:
- A. A walk-in is a normal appointment in a free slot, booked and marked arrived at once; it counts in the no-show rate (SA-004, ASM-004).
- B. A walk-in is a separate kind of record, not an appointment, and does not count.
- C. A walk-in is an appointment with a "walk-in" flag.

Assumed: A. It is the PRD default and the architecture's ASM-004. A flag (C) can be added later without changing the flow.
Why: no new status or entity, the no-overlap constraint covers it, and the chair time is really used.
Used in: spec User Story 5, FR-015.

## Q2: Can "arrived" be undone if marked by mistake? (FR-021)

Options:
- A. No. Only no-show has an undo (PD-003); a wrong "arrived" is left as it is.
- B. Yes, on the same day, back to booked.
- C. Yes, but only by the practice manager.

Assumed: A. The PRD gives an undo for no-show only; we do not invent more. If the client wants B, it is a small addition to the same status-change path.
Why: smallest design that meets FR-021.
Used in: spec User Story 2 and Assumptions.

## Q3: Do appointments typed in before go-live (paper diary, SA-005) send confirmations and reminders to patients?

Options:
- A. No messages are sent for appointments typed in before go-live; messaging is switched on at go-live (the exact switch is feature 007's).
- B. Messages are sent as normal when the appointment is booked.
- C. Confirmations are sent but reminders follow the normal rule.

Assumed: A. Real patients would receive "confirmations" for appointments they already booked by phone, before the service is announced, and provider accounts may not be live (RSK-001).
Why: avoids surprise messages and message cost during the dry run (RSK-010).
Used in: spec Edge Cases and Assumptions; to be agreed with feature 007.
