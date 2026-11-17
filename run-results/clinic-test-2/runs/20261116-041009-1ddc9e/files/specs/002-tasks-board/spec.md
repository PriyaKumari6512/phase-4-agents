# Feature Specification: Tasks and board with live updates

**Feature Branch**: `002-tasks-board` (no git branch is created in this environment)

**Created**: 2026-01-01

**Status**: Draft

**Input**: User description: "Tasks and board with live updates. Task model and CRUD, board columns (To do, Doing, Done), moving tasks, board updates reaching all viewers within 5 seconds, board UI, keyboard accessibility. Task assignment must emit an event for the assignment email feature. Optional story points on a task (assumption)." Covers prd.md: FR-1, FR-2, US-1, US-2, NFR-1 (board-update part), NFR-4.

**Scope boundary**: Users, boards, board membership, sign-in and the board-membership authorisation check belong to feature 001-platform-foundation and are reused here. Search belongs to 003, comments to 004, assignment email delivery to 005, burndown and CSV export to 008. This feature owns the task, the three board columns, moving tasks, live board updates and the keyboard-usable board and task forms.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create, view, edit and delete tasks (Priority: P1)

A team member working on a board creates a task with a title and optionally a description, a due date and an assignee, later views it, edits any of those fields, and deletes it when it is no longer needed. A new task always starts in the "To do" column. Only members of the board can do any of this. (source: FR-1, US-1, NFR-3)

**Why this priority**: Tasks are the core object of TaskFlow; every other feature depends on them, and FR-1 is a pilot-beta (2026-12-18) requirement.

**Independent Test**: With a signed-in board member, create a task with only a title, then edit it to add a due date and an assignee, read it back, delete it, and confirm a non-member cannot do any of these.

**Acceptance Scenarios**:

1. **Given** I am a member of a board, **When** I create a task with a title, **Then** the task is saved and appears in the "To do" column. (source: US-1)
2. **Given** a task, **When** I set a due date and an assignee who is a member of the board, **Then** both are stored and shown on the task. (source: US-1, FR-1)
3. **Given** a task, **When** I edit its title, description, due date or assignee, **Then** the changes are saved and visible to every board member. (source: FR-1)
4. **Given** a task, **When** I delete it and confirm, **Then** it no longer appears on the board. (source: FR-1)
5. **Given** I create a task with an empty title, **When** I submit, **Then** the task is rejected with a clear message and nothing is saved. (source: FR-1)
6. **Given** I am not a member of a board, **When** I try to read or change its tasks, **Then** access is refused. (source: NFR-3)

---

### User Story 2 - See the board with three columns and task cards (Priority: P1)

A team member opens a board and sees three columns, "To do", "Doing" and "Done", each listing its tasks as cards. Each card shows the title, the due date and the assignee when they are set. (source: FR-2, US-1)

**Why this priority**: The board is the main screen of the product and the place where tasks are seen (US-1 acceptance scenario 2).

**Independent Test**: Open a board containing tasks in each column and verify the three columns and the card contents.

**Acceptance Scenarios**:

1. **Given** I am on a board, **When** the board loads, **Then** I see exactly three columns in the order To do, Doing, Done, each with its tasks. (source: FR-2)
2. **Given** a task with a due date and an assignee, **When** I look at its card, **Then** both are shown on the card. (source: US-1)
3. **Given** a column has no tasks, **When** the board loads, **Then** the column is shown with an empty-state message. (source: FR-2)
4. **Given** a board with many tasks, **When** I open it, **Then** the board loads quickly enough that ordinary requests stay within the 300 ms p95 target. (source: NFR-1)

---

### User Story 3 - Create, edit and delete tasks from the board (Priority: P1)

A team member uses forms on the board to create a task, open a card to edit its title, description, due date, assignee and story points, and delete a task after confirming. New tasks show up in "To do". (source: FR-1, US-1)

**Why this priority**: This is how team members actually perform US-1 in the product; FR-1 is a pilot-beta requirement.

**Independent Test**: On a board in the browser, create a task with a title, edit it to add a due date and an assignee, see both on the card, then delete it.

**Acceptance Scenarios**:

1. **Given** I am on a board, **When** I create a task with a title, **Then** it appears in the "To do" column. (source: US-1)
2. **Given** a task, **When** I set a due date and an assignee in the edit form, **Then** both are shown on the task card. (source: US-1)
3. **Given** the form has an invalid value, **When** I submit, **Then** I see an error message next to the field and nothing is saved. (source: FR-1)
4. **Given** a task, **When** I choose delete and confirm, **Then** the card disappears; **When** I cancel, **Then** the task stays. (source: FR-1)

---

### User Story 4 - Move tasks between columns (Priority: P1)

A team member moves a task from one column to another (To do, Doing, Done) by dragging the card, or by choosing a column in a task menu, so that the board always reflects the current state of the work. The move is saved. (source: FR-2, US-2)

**Why this priority**: Moving work across columns is the core workflow of a board; FR-2 is a pilot-beta requirement.

**Independent Test**: Move a task from "To do" to "Doing" by dragging and by the menu; reload the board and confirm the task stays in "Doing".

**Acceptance Scenarios**:

1. **Given** a task in "To do", **When** I drag it to "Doing", **Then** it is shown in "Doing" and stays there after reload. (source: US-2)
2. **Given** a task, **When** I choose another column from the task's move menu, **Then** it moves exactly as with dragging. (source: FR-2, NFR-4)
3. **Given** a move that cannot be saved (for example the connection is lost), **When** the save fails, **Then** the card returns to its original column and I see an error message. (source: FR-2)
4. **Given** two members move the same task at nearly the same time, **When** both moves are saved, **Then** the last saved move wins and every viewer ends up seeing the same column. (source: FR-2)

---

### User Story 5 - Everyone sees board changes within 5 seconds (Priority: P1)

Everyone who has a board open sees task creations, edits, moves and deletions made by others within 5 seconds, without reloading the page. If the live connection drops, the board reconnects and catches up with the missed changes. (source: US-2, FR-2, NFR-1)

**Why this priority**: The "within 5 seconds" promise is part of FR-2 and NFR-1 and is the visible difference from spreadsheets.

**Independent Test**: Open the same board in two sessions as two members; move a task in one and confirm the other shows it in the new column within 5 seconds, with no reload.

**Acceptance Scenarios**:

1. **Given** a task in "To do" and several members viewing the board, **When** one member moves it to "Doing", **Then** all board viewers see it in "Doing" within 5 seconds. (source: US-2, NFR-1)
2. **Given** a member is viewing a board, **When** another member creates, edits or deletes a task, **Then** the viewer sees the change within 5 seconds. (source: FR-2, NFR-1)
3. **Given** a viewer's live connection was interrupted, **When** the connection is restored, **Then** the board shows the current state, including changes made during the interruption. (source: NFR-1)
4. **Given** a person who is not a member of the board, **When** they try to receive its live updates, **Then** access is refused and no task data is sent. (source: NFR-3)
5. **Given** several boards are in use, **When** a task changes on one board, **Then** viewers of other boards receive nothing about it. (source: NFR-3)

---

### User Story 6 - Use the board and task forms with the keyboard only (Priority: P2)

A person who cannot or does not want to use a mouse can read the board, create, edit and delete tasks, and move tasks between columns using only the keyboard, with visible focus, meaningful labels for assistive technology and announcements when a card moves, meeting WCAG 2.1 AA. (source: NFR-4)

**Why this priority**: Accessibility is a stated requirement for the beta but builds on the board and forms from earlier stories.

**Independent Test**: Without a pointing device, tab to the board, create a task, edit it, move it from "To do" to "Done" and delete it; run an automated WCAG 2.1 AA check on the board and form screens.

**Acceptance Scenarios**:

1. **Given** the board is open, **When** I press Tab and arrow keys, **Then** focus moves through columns and cards in a logical order with a visible focus indicator. (source: NFR-4)
2. **Given** a card has focus, **When** I use the keyboard to pick it up and drop it in another column, **Then** the task moves and the change is announced to screen readers. (source: NFR-4, US-2)
3. **Given** the task form is open, **When** I use only the keyboard, **Then** I can fill every field, submit, cancel, and Escape closes the form returning focus to where it was. (source: NFR-4, FR-1)
4. **Given** a form field has an error, **When** validation fails, **Then** the error is shown as text linked to the field and announced, not by colour alone. (source: NFR-4)
5. **Given** the board and task form screens, **When** an automated WCAG 2.1 AA check runs, **Then** it reports no serious or critical violations. (source: NFR-4)

---

### User Story 7 - Task assignment emits an event for notifications (Priority: P2)

When a task is assigned or reassigned to a person, the system records a task-assigned event that the assignment-email feature (005) consumes, so that the assignee can be told about it. This feature does not send email itself. (source: FR-1, FR-5, US-1)

**Why this priority**: The email requirement FR-5 depends on this hook, but the event can be added after core task handling.

**Independent Test**: Assign a task and confirm exactly one task-assigned event with the task, assignee and assigner is available; confirm no event when other fields change or when the assignee is unchanged.

**Acceptance Scenarios**:

1. **Given** an unassigned task, **When** I assign it to a board member, **Then** one task-assigned event naming the task, the new assignee and the person who assigned it is recorded. (source: FR-1)
2. **Given** an assigned task, **When** I change the assignee, **Then** one new event is recorded for the new assignee. (source: FR-1)
3. **Given** a task, **When** I edit other fields or save without changing the assignee, **Then** no assignment event is recorded. (source: FR-1)
4. **Given** a task is created already assigned, **When** it is saved, **Then** one assignment event is recorded. (source: US-1)
5. **Given** an assignment is saved, **When** something fails midway, **Then** either both the assignment and its event are stored or neither is, so the two never disagree. (source: FR-1, FR-5)

---

### Edge Cases

- A title is empty, only whitespace or longer than the allowed maximum: rejected with a clear message.
- A due date in the past is allowed (tasks may be recorded late); an invalid date is rejected.
- The assignee is not a member of the board: rejected.
- An assignee is later removed from the board: the task remains and shows the assignee as no longer a member (assumption A5).
- A task is deleted by one member while another is editing or moving it: the second member sees the task disappear and a message that it no longer exists.
- Two members edit the same task at once: the last saved change wins and all viewers converge on the same data.
- A member has the board open for a long time and the session expires: the board stops updating and asks the user to sign in again, without losing a form that is being edited.
- The live-update service is temporarily unavailable: the board still works and falls back to refreshing automatically (see FR-011).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Board members MUST be able to create a task with a required title and optional description, due date, assignee and story points. (source: FR-1, US-1)
- **FR-002**: Board members MUST be able to view, edit and delete tasks of their boards; deletion requires confirmation in the interface. (source: FR-1)
- **FR-003**: The system MUST validate task input at the boundary: title required and at most 200 characters, description at most 10,000 characters, due date a valid calendar date, assignee a member of the board, story points an optional whole number from 0 to 100 (assumptions A2, A3). (source: FR-1)
- **FR-004**: Every board MUST have exactly three columns, "To do", "Doing" and "Done", in that order; a new task MUST start in "To do". (source: FR-2, US-1)
- **FR-005**: Board members MUST be able to move a task between any two columns, and the new column MUST be saved. (source: FR-2, US-2)
- **FR-006**: The board MUST show each task as a card with title, due date and assignee when set, and story points when set. (source: US-1)
- **FR-007**: Every task read, change and board-update subscription MUST be limited to members of that board, using the board-membership check provided by feature 001. (source: NFR-3)
- **FR-008**: Every task creation, edit, move and deletion MUST be pushed to all viewers of the same board and appear on their screens within 5 seconds, without page reload. (source: FR-2, US-2, NFR-1)
- **FR-009**: Live updates MUST only reach members of the board concerned, and MUST work when several instances of the API are running. (source: NFR-3, NFR-1)
- **FR-010**: After a lost live connection the board MUST reconnect automatically and show the current state of the board. (source: NFR-1)
- **FR-011**: If live updates are unavailable, the board MUST remain usable and MUST refresh its data automatically at an interval of 5 seconds or less (assumption A6). (source: NFR-1)
- **FR-012**: Reads of a board MUST reflect changes immediately after a write, even when board reads are cached. (source: FR-2, NFR-1)
- **FR-013**: The board, task cards, task form and move action MUST be fully operable with the keyboard only, with visible focus, labelled controls, screen-reader announcements of moves and errors, and no WCAG 2.1 AA violations in automated checks. (source: NFR-4)
- **FR-014**: When a task is created with an assignee or its assignee changes, the system MUST record exactly one task-assigned event (task, assignee, assigner, time) for the assignment-email feature to consume; it MUST NOT record one when the assignee is unchanged. (source: FR-1, FR-5)
- **FR-015**: Task endpoints, the board view and the live-update endpoint MUST report health and emit logs, metrics and traces, and meet the 300 ms p95 API latency target for ordinary task and board requests. (source: NFR-1)
- **FR-016**: Each task MUST record who created it and when, and when it was last changed. (source: FR-1)

### Key Entities *(include if feature involves data)*

- **Task**: A unit of work on one board. Attributes: title, description, due date, assignee (a board member), optional story points, current column, creator, created and updated times. Belongs to exactly one board.
- **Board column**: One of the three fixed states To do, Doing, Done. The state of a task is exactly one of them. The set is fixed in this release.
- **Task-assigned event**: A record that a task was assigned to a person by someone at a time. Produced by this feature, consumed by feature 005.
- **Board update**: A message about a change to a task (created, edited, moved, deleted) delivered to everyone viewing that board.

Board, User and Board membership are owned by feature 001 and only referenced here.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a test with at least 10 simultaneous viewers of a board, 100% of task moves, creations, edits and deletions appear on every viewer's screen within 5 seconds. (NFR-1, US-2)
- **SC-002**: A new user can create a task and move it to "Done" on their first attempt in under 2 minutes without help.
- **SC-003**: Ordinary task and board requests are answered within 300 ms for 95% of requests under the expected peak load (50 requests per second). (NFR-1)
- **SC-004**: Every user journey of this feature (create, edit, delete, move, open board) can be completed with the keyboard alone, and automated WCAG 2.1 AA checks report no serious or critical violations. (NFR-4)
- **SC-005**: Zero cases in testing where a non-member can read, change or receive live updates of a board's tasks. (NFR-3)
- **SC-006**: Every assignment produces exactly one assignment event: 0 missing and 0 duplicate events in the acceptance tests. (FR-1, FR-5)

## Assumptions

- A1: Sign-in, users, boards, board membership and the membership check are delivered by feature 001 and reused here. Board creation and member management are out of scope.
- A2 (open question Q1): Tasks have an optional story points field because the burndown report (PRD FR-8) needs remaining story points. The PRD does not define story points on tasks. Assumed: optional whole number 0 to 100, set by any board member; confirm with the client.
- A3: Field limits (title 200, description 10,000 characters) are not in the PRD and are reasonable defaults.
- A4: Dragging within a column to reorder tasks is out of scope; the order inside a column is by creation time (oldest first) unless the client decides otherwise (open question Q2).
- A5 (open question Q3): A task keeps its assignee when the assignee leaves the board; the card shows them as "no longer a member".
- A6: If live updates cannot be used, a periodic refresh no slower than 5 seconds keeps the 5-second promise.
- A7: Which board members may edit or delete a task is not defined in the PRD; assumed that every board member may create, edit, move and delete any task on the board.
- A8: Task deletion is permanent (no trash or undo) in this release.
- A9: Only the web application is in scope; mobile apps are a non-goal in the PRD.
- A10: Email delivery of assignment notices is feature 005; this feature only records the event.
