# Clarifications: Patient appointments (004)

No user was available; each question has an assumed answer. Please confirm at the next clarification round.

## Q1: Is the 4-hour limit inclusive?
- Options: A) allowed up to and including exactly 4 hours before start; B) allowed only when strictly more than 4 hours remain.
- **Assumed: A.** The PRD says "until 4 hours before its start", which reads as "up to".
- Why: matches the wording; the boundary is tested in both directions.

## Q2: What if a message link is opened while signed in as a different patient?
- Options: A) show "appointment not found" and offer sign-out; B) show "this is not your appointment" with sign-out; C) sign out automatically and ask for sign-in.
- **Assumed: A.**
- Why: B confirms that the appointment exists (information leak, thr-007); C loses the session without consent.

## Q3: Is there a limit on how many times an appointment can be rescheduled?
- Options: A) no limit; B) maximum 2 per appointment.
- **Assumed: A.**
- Why: the PRD sets no limit; the 4-hour rule and the no-show block (R2) already control abuse. Each reschedule is recorded, so a limit can be added later.
