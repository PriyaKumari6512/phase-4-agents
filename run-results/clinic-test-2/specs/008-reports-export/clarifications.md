# Clarifications: Burndown report and CSV export

No user was available. For each question the most reasonable option was assumed. Maximum of 3 questions.

## Q1: Does only the Done column count toward the burndown?

Source: prd.md section 7, open question. Recorded on User Story 2 (burndown). Not decided here.

| Option | Answer | Implication |
|--------|--------|-------------|
| A | Only Done counts as burned down | Remaining = total points minus points in Done |
| B | Done and Doing (partly) count | Needs a rule for partial credit |
| C | Configurable per board | More scope, extra settings screen |

**Assumed**: A (Done only), because the board has only three columns and Done is the only finished state. Open question Q1 stays open for the client.

## Q2: Is the report and export limited to managers?

| Option | Answer | Implication |
|--------|--------|-------------|
| A | Any board member can view the report and export; only managers edit sprints | Matches NFR-3 (members already see all board tasks) |
| B | Only managers can view and export | Needs a manager role in 001 membership |

**Assumed**: A. The manager role is not defined in architecture.md, so it is used only for sprint edits (assumption A4). Open question Q2.

## Q3: Which time zone defines a sprint "day"?

| Option | Answer | Implication |
|--------|--------|-------------|
| A | UTC dates | Simple, same for all viewers |
| B | Per-user time zone (owned by 006 daily digest) | Daily records differ per viewer, complex |
| C | Per-board time zone | Needs a new board setting |

**Assumed**: A (UTC). Open question Q3.
