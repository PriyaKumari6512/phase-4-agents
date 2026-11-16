# Research: Patient appointments (004)

No NEEDS CLARIFICATION remain in the technical context. Decisions below close the design questions.

## R1. Where the 4-hour rule is evaluated
- **Decision**: one pure function in `cmp-booking`, used by read models (to set `can_change`) and by cancel and reschedule (to refuse). Inclusive at exactly 4 hours (Q1).
- **Rationale**: architecture says the rule is online-only and reception has none; a single function prevents screen and server drifting apart, and the screen flag is only a hint.
- **Alternatives**: rule in the web app only (rejected, thr-004); database trigger (rejected, reception must bypass it and the rule is business logic with a changing time source).

## R2. Reschedule: update in place or cancel and rebook
- **Decision**: update the same appointment row (dentist, start, end) and write a history row with reason `rescheduled`.
- **Rationale**: keeps the id (deep links in old messages stay valid), keeps one history chain, one transaction, and the exclusion constraint on the update decides races. The old slot is free at commit.
- **Alternatives**: cancel the old row and insert a new one (rejected: two ids, "cancelled by the patient" noise in no-show and report counts, broken links).

## R3. Race handling for reschedule
- **Decision**: lock the appointment row (`FOR UPDATE`), rely on the exclusion constraint for the target slot, translate SQLSTATE 23P01 to 409 `slot_taken` with the next free slots (same answer shape as booking, FR-012 of prd.md).
- **Rationale**: ADR-0003; QA-003.
- **Alternatives**: advisory locks per dentist (rejected: extra mechanism, the constraint is enough).

## R4. Idempotence
- **Decision**: repeating a cancel on an appointment already cancelled by the patient, or a reschedule to the current slot, returns 200 with the current state and writes no history or message. Writes are not retried by the client automatically (rel-005), but a double tap is possible.
- **Alternatives**: an idempotency-key header (rejected for simplicity: the state itself is the key here).

## R5. Messages and reminders
- **Decision**: insert a message row (kind change, template cancelled or rescheduled) in the same transaction; the dispatcher sends it. Reminder rows are withdrawn (cancel) or replaced (reschedule) through a messaging port; timing rules stay in feature 006.
- **Rationale**: ADR-0002 and ADR-0009: committed first, delivered later; provider outage cannot undo the change.
- **Alternatives**: send in the request (rejected: slower, couples the change to the provider).

## R6. R2 hook for the no-show block
- **Decision**: `RescheduleRule` interface in `cmp-booking/ports.py`; R1 implementation always allows. A refusal is returned as 403 `reschedule_blocked` with the clinic phone number. Cancel is never blocked by it.
- **Rationale**: FR-025 of prd.md blocks booking and rescheduling only; keeping it a port lets feature 006/R2 add the rule without changing `cmp-booking`.

## R7. Deep link
- **Decision**: link is `<web base>/appointments/<appointment id>` (opaque UUID, no secret and no login bypass). The web guard stores `returnTo`, sends signed-out users to sign-in and returns them. A non-owner gets "not found" (Q2).
- **Rationale**: ADR-0004 cookie session, thr-004 and thr-007; a magic link would weaken sign-in (thr-003).

## R8. Time and language
- **Decision**: API returns UTC ISO-8601; the web formats with the `Asia/Kolkata` zone; English text in one catalogue (QA-012). The 4-hour comparison is done in UTC.

## R9. Lists
- **Decision**: `GET /api/me/appointments` returns groups per person; upcoming = status booked and start in the future; past = the rest, latest first, first page of 20 with a cursor.
- **Rationale**: Release 2 adds persons with no change to the shape; size stays small (about 1.4 KB per appointment).
