# Clarifications: Reception day view, check-in, no-shows and dentist day

## Q1: How is a walk-in recorded? (open question Q-015)

- **Context**: FR-020 mentions walk-ins (SA-004). The PRD and ASM-004 say a walk-in is a normal appointment marked arrived and counts in the no-show rate.
- **Options**:
  - A. A normal appointment created with status arrived (reason "walk-in" in its history); counts in the no-show rate denominator.
  - B. A separate "walk-in" appointment kind that is excluded from the no-show rate.
  - C. Walk-ins are not recorded unless the patient is later booked.
- **Assumed**: A, as in SA-004 and ASM-004. It needs no extra status or table, and the history entry reason distinguishes walk-ins if the client later wants them excluded.
- **Why**: It is the PRD default and the smallest design. The answer affects the no-show rate in feature 008 (FR-032), not the data collected here.
- **Status**: open (Q-015), assumed A.

## Q2: Can "arrived" be undone?

- **Context**: FR-022 allows undoing a no-show on the same day. FR-021 says nothing about correcting a mistaken "arrived".
- **Options**:
  - A. Reception can return arrived to booked on the same day; the change is recorded.
  - B. Arrived is final.
  - C. Arrived can only be corrected by the practice manager.
- **Assumed**: A. Mis-clicks happen at a busy desk and B would leave wrong data in a record that counts no-shows.
- **Why**: Costs one more allowed transition and is recorded in the history like every change (FR-024).
- **Status**: open, assumed A.
