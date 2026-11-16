# Clarifications: No-show report per clinic and month

No user was available; the most reasonable option was assumed for each question.

## Q1: How are walk-ins recorded? (PRD Q-015)

**Context**: FR-004 of this spec (source FR-032). Walk-ins must be in or out of the rate.

| Option | Answer | Implications |
|---|---|---|
| A | Walk-in is a normal appointment marked arrived (SA-004), counts in the rate | No extra data; rate denominator includes walk-ins, which lowers the rate slightly |
| B | Walk-ins are a separate kind and excluded | Needs a walk-in flag on appointments (not in the architecture) |

**Assumed**: A (SA-004, ASM-004). Why: it is the PRD and architecture default and needs no new data. If the client answers B, the denominator query in cmp-reporting changes and a flag is needed in cmp-booking.

## Q2: What is the no-show target / baseline? (PRD Questions to raise, item 1)

**Context**: Goals table: target TBD; baseline unknown.

| Option | Answer | Implications |
|---|---|---|
| A | Baseline is the first 2 months of app data (ASM-015); the report shows rates only, no target line | Nothing to build beyond the report |
| B | Client gives a rough current number to show as a reference line | Needs a setting and an extra UI element |

**Assumed**: A. Why: ASM-015; no target exists to compare with.

## Q3: Is the current (partial) month part of the 12 months?

**Context**: "each of the last 12 months" in FR-032.

| Option | Answer | Implications |
|---|---|---|
| A | The current month plus the 11 before it; the current month is marked "month so far" | The manager sees fresh figures; the latest rate is incomplete |
| B | The 12 complete months before the current one | Figures are always final, but the report is up to a month old |

**Assumed**: A. Why: the manager reads the report to see whether no-shows are falling now; the partial month is clearly marked.
