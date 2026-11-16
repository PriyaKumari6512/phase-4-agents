# Research: Repeat no-show block

No NEEDS CLARIFICATION items remain; the three assumed questions are in clarifications.md.

## R1: How to compute "2 no-shows in the last 6 months"

- **Decision**: Query appointments of the person with status `no_show` and start time within the last 6 months (rolling, in UTC), keeping only those whose latest no-show status change is after the person's last reception lift.
- **Rationale**: PD-007 needs per-person counting; `ent-appointment.patient` is already the person. The appointment history (`ent-appointment-event`, FR-024) holds the time of each status change, so "after the lift" is exact and an undo followed by a re-mark counts as new.
- **Alternatives considered**: a stored counter per person (drifts on undo and on ageing out); counting by appointment start after the lift (a no-show marked after the lift for an earlier appointment would be lost).

## R2: Where the block state lives

- **Decision**: Keep `ent-no-show-block` rows (patient, blocked at, lifted by, lifted at), and decide "blocked" at read time as open row AND count >= 2.
- **Rationale**: The record is needed for reception to see since when and who lifted (FR-026) and for the 24-month retention. The count check at read time removes the need for an expiry job (Simplicity). Stale open rows are closed by the next recalculation.
- **Alternatives considered**: nightly job to close expired blocks (extra moving part, up to a day of wrong state); pure computed state with no table (no place for lift who/when).

## R3: Undo of a no-show

- **Decision**: Recalculate inside the same transaction as the undo; if count falls below 2 the open block is closed by the system (no user, no count reset).
- **Rationale**: Strong consistency in one database (architecture section 5); Q1 assumed answer A.
- **Alternatives considered**: eventual recalculation by a job (a wrongly blocked patient could try to book in the gap).

## R4: Feature switch behaviour

- **Decision**: One API setting `noshow_block_enabled`. Off: `is_blocked` is false and web hides block surfaces. Blocks are still recorded when no-shows are marked, so turning the switch on later is correct from day one.
- **Rationale**: Architecture says R2 screens are hidden by a feature flag until ready; Release 1 hook always allows; no-shows from Release 1 already exist in data (spec edge case).
- **Alternatives considered**: not recording while off (would need a back-fill at switch-on).

## R5: Error shape for a refused booking

- **Decision**: HTTP 403 with body `{code: "ONLINE_BOOKING_BLOCKED", clinic_phone}`; also a read-only eligibility call for the slot-picker step so the patient is told before choosing a slot.
- **Rationale**: 409 is already "slot taken" with next free slots (FR-012); a distinct code keeps the web logic simple. The eligibility call matches the booking flow (step 4, blocked patient).
- **Alternatives considered**: reuse 409 (mixes two meanings); only refuse at the final confirm (patient wastes a flow).

## R6: Who may lift

- **Decision**: Receptionists (any patient, ASM-011: patient search is not clinic-scoped); refused for other roles and when not blocked.
- **Rationale**: Architecture actor list says receptionist lifts blocks. Concurrency: lift is a conditional update on the open row, so a second lift gets "not blocked".
- **Alternatives considered**: also the practice manager (not in PRD; can be added later).
