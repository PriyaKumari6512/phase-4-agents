# Feature Specification: Comments and @mentions

**Feature Branch**: `004-comments-mentions`

**Created**: 2026-01-01

**Status**: Draft

**Input**: User description: "Comments and @mentions. Users can comment on tasks and mention teammates with @name; a mention notifies the teammate. (FR-3, US-3)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Post and read comments on a task (Priority: P1)

As a team member, I want to post comments on a task and read the comments of my teammates, so that discussions stay with the work. (source: US-3, FR-3)

**Why this priority**: Comments are the base of the feature. Mentions cannot exist without them.

**Independent Test**: Post a comment on a task as a board member and see it listed on the task, in order, with its author and time. A non-member cannot see or post it.

**Acceptance Scenarios**:

1. **Given** a task on a board I belong to, **When** I post a comment with text, **Then** the comment appears in the task's comment list with my name and the time it was posted. (source: US-3, FR-3)
2. **Given** a task with several comments, **When** I open the task, **Then** I see all comments in the order they were posted, oldest first. (source: FR-3)
3. **Given** I am not a member of the task's board, **When** I try to read or post comments on that task, **Then** access is refused and no comment content is revealed. (source: NFR-3)
4. **Given** I submit an empty or whitespace-only comment, **When** I post it, **Then** it is rejected with a clear message and nothing is stored. (source: FR-3)

---

### User Story 2 - Mention teammates and notify them (Priority: P1)

As a team member, I want to mention a teammate with @name in a comment, so that the teammate is notified and the discussion reaches them. (source: US-3, FR-3)

**Why this priority**: This is the acceptance criterion of US-3 ("Alice receives a notification").

**Independent Test**: Post a comment containing `@alice` where Alice is a board member; Alice receives one email notification. Posting a comment mentioning a non-member sends nothing.

**Acceptance Scenarios**:

1. **Given** a task and a board member Alice, **When** I post a comment mentioning @alice, **Then** Alice receives a notification (email, the only channel in this release). (source: US-3, FR-3)
2. **Given** a comment that mentions @alice twice, **When** it is posted, **Then** Alice receives one notification for that comment. (source: FR-3)
3. **Given** a comment that mentions someone who is not a member of the board, **When** it is posted, **Then** the comment is stored, the text is kept as plain text, no notification is sent, and the author is not told whether that person exists. (source: NFR-3; assumption A2)
4. **Given** I mention myself, **When** I post the comment, **Then** I receive no notification. (source: FR-3; assumption A4)
5. **Given** the email service is temporarily unavailable, **When** I post a comment with a mention, **Then** the comment is still saved and the notification is delivered later. (source: FR-3)
6. **Given** the notification preferences feature is available and Alice has turned mention notifications off, **When** I mention her, **Then** she receives no email. (source: Assumption in prd.md section 7, US-7)

---

### User Story 3 - Use comments and mentions with the keyboard only (Priority: P2)

As a team member who cannot use a pointing device, I want to read, write and post comments and mentions with the keyboard only, so that the feature is accessible. (source: NFR-4)

**Why this priority**: Required by NFR-4, but it builds on the working comment flow.

**Independent Test**: Complete the "post a comment with a mention" flow using only the keyboard, with visible focus at each step.

**Acceptance Scenarios**:

1. **Given** the task view is open, **When** I navigate with Tab and Shift+Tab, **Then** I can reach the comment list, the comment input and the post button in a logical order with a visible focus indicator. (source: NFR-4)
2. **Given** the comment input has focus, **When** I type a comment with an @mention and press the post button with Enter or Space, **Then** the comment is posted without any mouse action. (source: NFR-4)
3. **Given** a new comment or an error message appears, **When** I use a screen reader, **Then** the change is announced. (source: NFR-4)

---

### Edge Cases

- A comment mentions a name that matches no board member: stored as plain text, no notification (see A2).
- A comment mentions a person who was removed from the board after an earlier comment: only current board members are notified for new comments.
- A very long comment: rejected above the maximum length with a clear message (see A5).
- A mention is written inside a word or an email address such as `bob@example.com`: it is not treated as a mention.
- Two people post comments at the same time: both are saved and the order is stable.
- The comments feature is switched off (feature flag off): the comment endpoints and UI are not available and no mention notifications are created.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Board members MUST be able to post a text comment on a task of a board they belong to. (source: FR-3, US-3)
- **FR-002**: The system MUST list the comments of a task in posting order with author and time. (source: FR-3, US-3)
- **FR-003**: The system MUST reject empty comments and comments over the maximum length. (source: FR-3)
- **FR-004**: The system MUST detect `@name` mentions in a comment and resolve them to board members using the matching rule in assumption A1. (source: FR-3, US-3)
- **FR-005**: The system MUST notify each mentioned board member once per comment, by email, through the shared notification outbox and email client of feature 005-assignment-email. (source: FR-3, US-3)
- **FR-006**: The system MUST NOT notify the comment author about their own mention, and MUST NOT notify non-members. (source: FR-3, NFR-3)
- **FR-007**: Only board members MUST be able to read comments, post comments, or be mentioned. (source: NFR-3)
- **FR-008**: Saving a comment MUST NOT fail or wait because a notification cannot be sent immediately. (source: FR-3)
- **FR-009**: Mention notifications MUST respect the recipient's notification preferences once feature 007-notification-prefs is available. (source: prd.md section 7 assumption, US-7)
- **FR-010**: The comment and mention capability MUST be controlled by the feature flag FEATURE_COMMENTS, off by default in production until released. (source: implementation contract)
- **FR-011**: The comment form, comment list and mention flow MUST be usable with the keyboard only and announce changes to assistive technology. (source: NFR-4)
- **FR-012**: The mention notification email MUST identify the author, the task and the comment text, and link to the task. (source: FR-3, US-3; wording of the email content is assumption A6)

### Key Entities *(include if feature involves data)*

- **Comment**: text posted by a board member on a task; has author, task, creation time. Stored in the system of record. Belongs to one task.
- **Mention**: link between a comment and a mentioned board member, created when a comment is posted. At most one per comment and member.
- **Mention notification**: a request to notify a mentioned member; handed to the shared notification outbox owned by feature 005-assignment-email.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A mentioned board member receives the notification email within 1 minute of the comment being posted (same target as assignment emails, assumption A7), in 95% of cases.
- **SC-002**: A new comment is visible to other members of the board when they open the task, and to the author immediately after posting.
- **SC-003**: Zero comments or mentions are visible to or notify people who are not board members (checked by automated tests).
- **SC-004**: A user can post a comment with a mention using only the keyboard, with no step that needs a mouse.
- **SC-005**: A mentioned person receives exactly one notification per comment, even when mentioned several times.

## Assumptions

- A1 (open question Q1): Matching rule is not defined in prd.md. Assumed: `@name` matches the user's unique username, case-insensitively, among the members of the task's board. Display names are not matched. A name ends at the first character that is not a letter, digit, dot, underscore or hyphen.
- A2 (open question Q2): Mentions of non-members are not notified and not blocked; the text stays plain.
- A3 (open question Q3): Editing and deleting comments are not in prd.md and are out of scope for this release.
- A4: Mentioning yourself does not send you a notification.
- A5: Maximum comment length is 5,000 characters (not defined in prd.md; to be confirmed).
- A6: The mention email content (author, task title, comment text, link) is assumed; the final wording belongs to feature 005-assignment-email's email templates.
- A7: The 1-minute target is borrowed from FR-5; prd.md does not give a time for mention notifications.
- Email is the only notification channel in this release (prd.md section 7).
- Dependencies: users, boards, board membership and authorisation (feature 001 platform-foundation), tasks (feature 002 tasks-board), notification outbox and email client (feature 005-assignment-email), preferences (feature 007, consulted when available).
- Autocomplete suggestions while typing @ are not part of this release (not in prd.md).
- Mobile apps, other channels and integrations are out of scope (prd.md non-goals).
