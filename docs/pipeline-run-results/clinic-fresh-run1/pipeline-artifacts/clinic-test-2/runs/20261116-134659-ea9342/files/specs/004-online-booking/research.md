# Research: Patient online booking

All decisions follow architecture.md (ADR-0003, QA-001, QA-002, QA-003, QA-010). Items the architecture does not decide are marked **Assumed** and carried as open points.

## R1. How the winner of a contested slot is decided

- **Decision**: A PostgreSQL exclusion constraint on (dentist, time range) over active appointments, using `btree_gist` (ADR-0003). The application's own "is free" check is only a fast path.
- **Rationale**: Application checks cannot be race-free across two API replicas; the database serialises concurrent inserts and the loser gets SQLSTATE 23P01. This is the design for the driver QA-003.
- **Alternatives considered**: advisory locks per dentist (extra moving part, not enforced for other writers such as reception); serializable transactions with retry (more retries under load, still no guarantee for other code paths); a slot table with unique key (does not cover overlapping times for different durations).

## R2. Which statuses count as "active"

- **Decision (Assumed)**: `booked`, `arrived` and `no_show` occupy the time; `cancelled_by_patient` and `cancelled_by_clinic` free it. The free-slot calculation in feature 003 must use the same list.
- **Rationale**: Architecture says "active appointments" without listing them. Keeping `no_show` in means that undoing a no-show on the same day (feature 006) can never collide with a new booking.
- **Alternatives considered**: only `booked` and `arrived` (a past no-show would not matter for future slots, but undo could fail). Open point for features 005 and 006 to confirm.

## R3. Idempotency

- **Decision**: Required `Idempotency-Key` header (1 to 64 characters, letters, digits and hyphen), unique per patient account in table `booking_request`; key claimed first inside the booking transaction (`INSERT ... ON CONFLICT DO NOTHING`). A concurrent duplicate waits on the unique index and then returns the stored result. Failed bookings roll the key back, so a retry after "slot taken" with the same key is a new attempt. The web app creates a new key per confirm tap sequence and reuses it only for retries of the same confirm.
- **Rationale**: ADR-0003 and QA-003 require that a retry never books twice; the unique index is simple and needs no cache (architecture: no cache).
- **Alternatives considered**: HTTP middleware with a cache (architecture rules out a cache); relying on the exclusion constraint alone (a retry would get "slot taken" for the patient's own booking, which is confusing).
- **Retention**: Assumed kept with the appointment (no personal data stored in the row); no cleanup job in this feature.

## R4. Messaging hook

- **Decision**: A `MessagingPort` with `enqueue_booking_messages(session, appointment)` called inside the booking transaction, so the confirmation row and the reminder row commit with the appointment (ADR-0003). Sending is done after commit by the dispatcher (ADR-0002) in feature 007. The default adapter is a no-op until feature 007 lands.
- **Rationale**: Matches "insert of appointment, history row and reminder row is one transaction" and "confirmation is sent after commit, not in the request".
- **Alternatives considered**: calling the provider in the request (breaks the 3 s target and QA-002); an after-commit callback only (a crash between commit and callback loses the confirmation).

## R5. "Is blocked?" interface

- **Decision**: `PolicyPort.is_blocked(patient_id) -> bool`; default `NotBlockedPolicy` returns `False`. The slot read and the booking step both call it. A blocked answer returns HTTP 403 with code `online_booking_blocked` and the clinic's phone number.
- **Rationale**: Architecture: cmp-booking asks cmp-noshow-policy through an interface that returns not-blocked until feature 009 exists.
- **Alternatives considered**: no call until feature 009 (would force a change to the booking step later).

## R6. Where slot calculation lives

- **Decision**: Feature 003 (cmp-scheduling) owns `list_free_slots(clinic, treatment, dentist|None, from, to, limit)` including "first available" (top 10, paginated) and `is_slot_free` / online treatment checks. Feature 004 adds the patient-facing HTTP read in the booking router that calls it and adds the blocked check.
- **Rationale**: The component diagram gives slot calculation to cmp-scheduling and booking calls it in-process. One calculation avoids two answers to "is this slot free".
- **Assumed**: the function names and signatures above; feature 003's plan confirms or this feature adapts through `SchedulingPort`.

## R7. Next free slots after a conflict

- **Decision**: Return up to 10 slots for the same clinic, treatment and dentist choice (named dentist, or all dentists for "first available"), starting at the time of the slot that was taken, soonest first, read after the failed transaction is rolled back.
- **Rationale**: PRD: "shown the next free slots". Starting at the taken time is the least surprising for the patient. The exact count (10) matches the "first available" size in the architecture.
- **Alternatives considered**: restarting from today (the patient loses their place in the day).

## R8. Remembered channel

- **Decision**: Column `preferred_channel` (`sms` or `whatsapp`, default `sms`) on the patient account table owned by cmp-identity, updated in the booking transaction when a booking is confirmed. The appointment's own `channel` holds the choice for that appointment.
- **Rationale**: Architecture: "Channel choice stored on ent-patient-account (preferred channel, default SMS)". Updating inside the transaction keeps the two consistent and a failed booking leaves it unchanged.
- **Assumed**: feature 002 may already create the column; migration `004b` is written to add it only if missing.

## R9. Web flow and screen count

- **Decision**: Four screens after sign-in: who and what (who, clinic, treatment), slot picker (dentist or first available, day strip, slots), confirm (summary, channel), booked. Page state in one React context; browser back keeps choices.
- **Rationale**: NFR-010 and QA-010: 5 screens or fewer, 44 px tap targets, no sideways scrolling.
- **Assumed**: the web shell (feature 001) provides routing, English catalogue, IST formatting and the tap-target base styles.

## R10. Test and measurement tooling

- **Decision (Assumed)**: pytest, pytest-asyncio and httpx for API, contract and concurrency tests against a real PostgreSQL 16 with `btree_gist` (not SQLite); a small asyncio load script in `tests/performance/booking/` for server percentiles; client-side 4G timing recorded with the browser's built-in "Fast 4G" throttling profile.
- **Rationale**: No test or load tool is named in architecture.md; this uses nothing beyond Python and the browser. The 4G profile is not defined in the PRD (PD-008): to confirm with the client at the gate (ASM-006).
- **Alternatives considered**: a dedicated load-testing product (a new tool for one check; revisit if feature 001 chooses one).

## R11. Concurrency test design

- **Decision**: For each of 1,000 runs, start N barrier-synchronised attempts (N from 2 up to 100) against one dentist and slot, each on its own database connection. Some runs also mix in attempts for a different start time whose time range overlaps (for example a 60-minute reception-style booking that starts 30 minutes earlier, inserted through the booking service's lower-level insert used by feature 006). After each run assert: exactly one winner per contested slot, and a SQL query over the whole table finds 0 overlapping active pairs per dentist.
- **Rationale**: QA-003 measure: 0 overlapping active appointments in 100% of 1,000 runs; design load 100.
- **Note**: Online slots are 30 minutes on the half hour, so partial overlaps only arise from longer reception treatments (feature 006); the test uses a longer duration in test data to prove the constraint covers them.

## Open points carried forward

- R2: statuses counted as active (features 005, 006).
- R6: function names owned by feature 003.
- R10: 4G profile and test tooling (features 001 and client gate).
- Clarifications Q1 to Q3 in `clarifications.md`.
