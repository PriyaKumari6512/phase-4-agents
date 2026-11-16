# Clarifications: Tasks and board with live updates

No user was available; the most reasonable option was assumed for each question.

## Q1: Does a task carry story points?

- Context: PRD FR-8 (burndown, feature 008) needs remaining story points per day, but the PRD defines no story points on tasks.
- Options: A) optional whole-number story points on the task; B) no story points now, add with feature 008; C) required story points.
- Assumed: A. Optional integer 0 to 100. Why: the cheapest option that unblocks FR-8 without forcing input; a nullable column is easy to change later.

## Q2: Can tasks be ordered inside a column?

- Context: US-2 only requires moving between columns.
- Options: A) order by creation time, no manual reorder; B) manual drag reorder inside a column.
- Assumed: A. Why: the PRD does not ask for reordering (Simplicity principle).

## Q3: What happens to a task whose assignee leaves the board?

- Context: membership management is in feature 001.
- Options: A) task keeps the assignee, shown as "no longer a member"; B) assignee is cleared automatically; C) removal is blocked while tasks are assigned.
- Assumed: A. Why: no data is lost and no hidden event is produced.
