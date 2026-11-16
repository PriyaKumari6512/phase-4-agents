# Clarifications: Repeat no-show block

No user was available. Each question below was answered with the most reasonable option, and the assumed answer is used in spec.md, plan.md and tasks.md.

## Q1: What happens to a block when the no-show that caused it is undone?

Options:
- A: The block is removed at once (the count falls below 2).
- B: The block stays until reception lifts it.
- C: The block stays, but reception is asked to review.

Assumed: **A**. Why: PD-003 lets reception undo a mistaken no-show the same day; keeping a block caused by a mistake would be unfair, and option A needs no extra screens. (FR-025, FR-022)

## Q2: Does a block end by itself when no-shows age past 6 months?

Options:
- A: Yes, the 6 months are rolling; when the count in the window is below 2 the person is no longer blocked.
- B: No, a block lasts until reception lifts it.

Assumed: **A**. Why: FR-025 says "2 no-shows in the last 6 months", which is a rolling window. (FR-025)

## Q3: Which clinic phone number is shown to a blocked patient?

Options:
- A: The clinic of the booking being made or the appointment being rescheduled.
- B: A single main number for the practice.
- C: All clinic numbers.

Assumed: **A**. Why: the patient has already chosen a clinic (booking step 3) and the existing 4-hour rule (FR-017) also shows that clinic's number. (FR-025)
