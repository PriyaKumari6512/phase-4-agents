# Research: Repeat no-show block and no-show report

All unknowns from the Technical Context are resolved below. Technology is fixed by `architecture.md`; these entries are design decisions inside it.

## R-001: Where the block rule lives and how booking asks it

- **Decision**: `cmp-noshow-policy` implements the "is blocked?" interface that `cmp-booking` already holds (added by features 004 and 005, returning "not blocked"). `main.py` wires the real policy in place of the stub. The interface name and signature are those already in `booking/block_port.py`; this feature does not change the signature, only adds the clinic phone through the existing refusal path.
- **Rationale**: The architecture draws `cmp-booking` asking `cmp-noshow-policy` in-process. Keeping the interface in `cmp-booking` stops a circular import.
- **Alternatives considered**: Booking calling the policy module directly (circular imports); a database trigger (hides rules from tests, against thr-011 style of explicit rules).

## R-002: How a no-show is counted

- **Decision**: A no-show is counted for a person when the appointment's current status is no-show, its start time is within the last 6 months, and the time the status became no-show (from `ent-appointment-event`) is after the person's most recent `lifted_at` (if any). An undone no-show is no longer in status no-show, so it stops counting. The count is a live query, never stored.
- **Rationale**: FR-025 and FR-026; Q2 assumed answer (counted by marked time). A live count needs no job for the 6-month window ageing out.
- **Alternatives considered**: A stored counter (drifts on undo and anonymisation); counting by appointment date after lift (Q2 option B).

## R-003: What `ent-no-show-block` is for

- **Decision**: The blocked state is the live count (2 or more). The table `ent-no-show-block` records the block episode: patient, blocked at, lifted by, lifted at, kept 24 months. A row is opened when a no-show mark takes a person from under 2 to 2 or more (updating the `blocked_at` of an open row left stale by ageing). A lift sets `lifted_by` and `lifted_at` on the open row under a row lock. An undo that leaves the person under 2 deletes the open row (Q1 assumed answer) and writes no lift record.
- **Rationale**: Gives reception a "blocked since" date and an audit trail of who lifted, while the live count keeps the rule exact when no-shows age out.
- **Alternatives considered**: A row per no-show (more data, not in the architecture entity); blocking purely by the row (breaks when no-shows age out or are undone).

## R-004: Concurrent lifts

- **Decision**: Lift reads the open row with `SELECT ... FOR UPDATE`; the first lifter sets the fields; the second finds no open row and gets a "not blocked" answer (HTTP 409) so there is one lift record.
- **Rationale**: Edge case "two receptionists lift at once"; one transaction per action as the architecture states.
- **Alternatives considered**: Optimistic version column (more code, same result).

## R-005: Where the block is enforced

- **Decision**: In `cmp-booking`, the block check runs inside the confirm of an online booking and of an online reschedule, in the same transaction as the insert, and is also available as a read-only eligibility call for the slot-picking step. A blocked person gets HTTP 403 with code `ONLINE_BOOKING_BLOCKED` and the clinic's phone number. Reception-side booking operations and online cancel do not call it.
- **Rationale**: FR-005 in the spec (check on confirm, not only on view); keeps strong consistency (a block check commits with the booking per architecture section 5).
- **Alternatives considered**: Checking only when the screen loads (a block arriving mid-session would slip through).

## R-006: Which clinic's phone number is shown

- **Decision**: The booking flow shows the phone of the clinic chosen in the booking; reschedule shows the phone of the appointment's clinic. Both come from `ent-clinic` through `cmp-scheduling`.
- **Rationale**: Edge case in the spec; matches how FR-017 shows a clinic phone inside 4 hours.
- **Alternatives considered**: A single practice number (none is defined in the PRD).

## R-007: Report query

- **Decision**: `cmp-reporting` asks `cmp-booking` for monthly counts. `cmp-booking` runs one grouped query over `ent-appointment` by clinic and IST calendar month of the start time for the last 12 months including the current one (Q3 assumed answer), returning no-show count and not-cancelled count (statuses other than cancelled by the patient and cancelled by the clinic; walk-ins included). `cmp-reporting` adds clinics with no rows as zeros (clinic list from `cmp-scheduling`, so a third clinic appears as data) and computes the rate, which is empty when the denominator is zero.
- **Rationale**: FR-032, ASM-004, ASM-014; the architecture says reporting reads through `cmp-booking`. The query does not use patient fields, so anonymised rows still count (RSK-007).
- **Alternatives considered**: A summary table refreshed by a job (not needed at 36 rows and about 52,000 appointments a year); reporting reading tables directly (breaks module ownership).

## R-008: Access and flag

- **Decision**: The report endpoint is allowed for the practice manager role only. Lift and block state are allowed for receptionists (any patient they can find, ASM-011). A patient may only ask about persons in their own account. One flag, `r2_noshow_block_report`, gates the block's effect, the block endpoints, the report endpoint and the three web pieces. With the flag off the policy returns not blocked, endpoints answer 404 and the screens are hidden. Block rows are still maintained while the flag is off so the data is ready when it is switched on. The flag name is an assumption to align with feature 001's flag mechanism.
- **Rationale**: FR-014, FR-016; architecture says R2 screens are hidden by a feature flag until their data is ready.
- **Alternatives considered**: Two flags (the PRD ties both to Release 2 and the spec has one requirement).

## R-009: Code layout assumption

- **Decision**: Use `app/modules/<component>` in clinic-api and `src/pages`, `src/components` in clinic-web. Implementers align paths with the scaffold from feature 001 and the files created by features 004 to 006 before starting.
- **Rationale**: Those features were planned in parallel, so their final paths are not visible here.
- **Alternatives considered**: None; recorded as an open dependency.

## R-010: Logging and metrics

- **Decision**: Structured logs for refusals and lifts with person id, clinic id, receptionist id and correlation id only; counters for blocked attempts and lifts; a log line when the report is read (user id). No names or phone numbers.
- **Rationale**: Constitution II and the Definition of Done.
- **Alternatives considered**: None.
