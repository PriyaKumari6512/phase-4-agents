# Research: Reception day view, check-in, no-show and dentist day

All technology is fixed by architecture.md; this file records the design decisions for this feature. No NEEDS CLARIFICATION remains in the Technical Context. Business unknowns are in clarifications.md (Q1–Q3).

## R1: Where the status-change rules live

- **Decision**: Pure functions in `cmp-reception` (`status_rules.py`) decide what is allowed (15 minutes, same day, status); `cmp-booking` performs the change and writes the event. The rules are re-checked on submit.
- **Rationale**: Architecture says cmp-reception calls cmp-booking to change status; cmp-booking owns appointments and history. The panel and the endpoint must agree, so one function serves both.
- **Alternatives**: rules only in the web app (rejected: authorisation and rules must be server-side, thr-004); rules in a database trigger (rejected: harder to test, no need, simplicity).

## R2: Preventing a stale screen from overwriting a newer status

- **Decision**: Conditional update on the expected status, 409 with the current status on zero rows, event row in the same transaction.
- **Rationale**: Two receptionists share one clinic; no extra column or lock needed.
- **Alternatives**: a version column (rejected: a new column for a problem the status already solves); row lock (rejected: needless, held across a request).

## R3: Reception booking and the no-overlap guarantee

- **Decision**: Reuse the online insert path with two flags off: 4-hour cut-off and 30-day horizon. The exclusion constraint on active appointments decides concurrent attempts (ADR-0003); conflict returns 409 with next free slots; an idempotency key guards retries.
- **Rationale**: Same guarantee for both channels (QA-003 counts reception in the test).
- **Alternatives**: a separate reception insert (rejected: two code paths for one invariant).

## R4: "End of that day" and the 15-minute rule

- **Decision**: IST calendar date of the appointment start; times are stored in UTC and converted for comparison. No-show window is `[start + 15 min, midnight IST after start)`.
- **Rationale**: PD-003 says "until the end of that day"; NFR-008 says times in IST.
- **Alternatives**: clinic closing time as the end (rejected: not in the PRD).

## R5: Patient search

- **Decision**: Case-insensitive contains match on name and on the digits of the phone number, at least 3 characters, 20 results, ordered by name; response has id, name, phone only. No new database extension.
- **Rationale**: ASM-011 allows search across clinics; limiting length and results reduces bulk reading. Volume (a few thousand people) is small; the architecture names no trigram extension, so none is added (simplicity).
- **Alternatives**: trigram index (rejected for now; revisit if search is slow); exact phone only (rejected: PRD says by phone number or name).
- **Open point**: if the client wants a different minimum length, it is a setting in one place.

## R6: Creating a patient at reception

- **Decision**: Find the account by normalised phone number; if found, return it; if not, create the account (phone, name) and its first person (name) in one transaction through `cmp-identity`. Phone format is validated as in sign-in (feature 002).
- **Rationale**: Account is one per phone number (ASM-001, ADR-0008); the patient meets the same account at their first sign-in.
- **Alternatives**: allow duplicate phones (rejected: breaks sign-in and the no-show count per person).

## R7: Day view refresh

- **Decision**: The web app polls the day view every 30 s and on demand.
- **Rationale**: Architecture capacity assumes about 10 sessions refreshing every 30 s (≈0.3 requests/s); no push channel is named, none added.
- **Alternatives**: WebSocket or server-sent events (rejected: new infrastructure, not needed).

## R8: Cancelled appointments in the day view

- **Decision**: Not drawn in the columns; the slot shows as free.
- **Rationale**: The slot can be booked again at once (FR-018 of the PRD, feature 005), so overlapping cards would confuse the day view. History stays in `ent-appointment-event`.
- **Alternatives**: a "show cancelled" toggle (deferred; add if reception asks).

## R9: Messages for reception changes before go-live

- **Decision**: This feature calls the messaging interface for every reception booking, move and cancel; whether it sends is decided in feature 007 (Q3 assumes none before go-live).
- **Rationale**: Keeps messaging in one component and avoids duplicate logic.
