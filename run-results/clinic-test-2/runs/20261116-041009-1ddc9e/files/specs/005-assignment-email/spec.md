# Feature Specification: Assignment email notification

**Feature Branch**: `005-assignment-email` (no git branch is used; directory `specs/005-assignment-email`)

**Created**: Phase 4 backlog generation

**Status**: Draft

**Input**: User description: "Assignment email notification: an assignee receives exactly one email within 1 minute when a task is assigned to them. This feature owns the email provider client, the notify-worker skeleton and entrypoint, the notification outbox and the assignment email. (source: FR-5, US-5, goal G2)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Assignee is emailed when a task is assigned (Priority: P1)

As an assignee, I want an email when a task is assigned to me so that I never miss new work. When a team member or manager assigns a task to me (when creating the task or by changing its assignee), I receive an email that names the task, the board, who assigned it, the due date if any, and a link to the task. (source: US-5, FR-5)

**Why this priority**: This is the Must story US-5 and serves goal G2 (no assigned task is missed). Nothing else in this feature has value without it.

**Independent Test**: Assign a task to a user in the dev environment (or in an automated test with a fake email provider) and verify that exactly one email addressed to that user is handed to the email provider less than 60 seconds after the assignment is saved.

**Acceptance Scenarios**:

1. **Given** a task on a board, **When** it is assigned to me, **Then** I receive one email within 1 minute. (source: US-5, FR-5)
2. **Given** a task created with an assignee, **When** the task is saved, **Then** the assignee receives the assignment email in the same way as for a later assignment. (source: FR-1, FR-5)
3. **Given** a task assigned to Alice, **When** it is reassigned to Bob, **Then** Bob receives one assignment email and Alice receives no assignment email for this change. (source: FR-5)
4. **Given** an assignment email, **When** I open it, **Then** it contains the task title, board name, the name of the person who assigned it, the due date (if set) and a link to the task, and no data from tasks I cannot see. (source: FR-5, NFR-3)
5. **Given** a manager assigns a task to themselves, **When** the assignment is saved, **Then** an assignment email is sent to them as for any other assignee. Assumed: yes (open question Q1). (source: FR-5)

---

### User Story 2 - One email per assignment, none lost (Priority: P1)

As an assignee, I want to receive exactly one email per assignment, even when the system retries, restarts or the email provider has a problem, so that I am neither spammed with duplicates nor left without a notification. (source: US-5, FR-5)

**Why this priority**: "One email" is part of the US-5 acceptance criterion and "no assigned task is missed" is goal G2. Duplicates and silent losses break both.

**Independent Test**: With a fake email provider, enqueue the same assignment twice, run two workers concurrently, kill a worker mid-send, and make the provider fail temporarily; in every case exactly one email per assignment is eventually sent and no assignment ends without a recorded outcome.

**Acceptance Scenarios**:

1. **Given** the same assignment is reported twice, **When** the notification is recorded, **Then** only one notification exists and one email is sent. (source: US-5)
2. **Given** two notify-worker instances are running, **When** one notification is due, **Then** only one instance sends it. (source: US-5)
3. **Given** the notify-worker is stopped or the email provider is unavailable when a task is assigned, **When** the service recovers, **Then** the email is still sent, once. (source: FR-5, G2)
4. **Given** the email provider returns a temporary error, **When** the worker retries, **Then** the email is sent once on the first successful attempt and no further attempts are made. (source: FR-5)
5. **Given** the email provider rejects an email permanently (for example an invalid address), **When** the worker handles the error, **Then** the notification is marked failed with the reason, is not retried and is visible to operators. (source: FR-5)
6. **Given** the task was deleted or the assignee has no usable email address when the worker processes the notification, **When** the worker handles it, **Then** no email is sent and the notification is marked skipped with the reason. (source: FR-5, NFR-3)

---

### User Story 3 - Operators can see delivery health and failures (Priority: P2)

As the operator of TaskFlow, I want logs, metrics and an alert for assignment email delivery so that I notice delayed or failing emails before assignees miss work. (source: US-5, FR-5, G2)

**Why this priority**: Supports the 1-minute promise and goal G2 in production; required by the project's observability principle, but the emails themselves work without it.

**Independent Test**: In an automated test, fail provider calls and delay processing; verify that the failure counter, the oldest-pending-age metric and the structured logs show it, and that an alert rule fires on the oldest pending notification being older than the threshold.

**Acceptance Scenarios**:

1. **Given** the worker sends an email, **When** the send finishes, **Then** a structured log entry and metrics record the outcome (sent, retry, failed, skipped) and the time from assignment to send. (source: FR-5)
2. **Given** a pending notification is older than 45 seconds, **When** the alert rules are evaluated, **Then** an alert warns the operators before the 1-minute limit is exceeded. (source: FR-5)
3. **Given** the worker process stops making progress, **When** the health check runs, **Then** the pod is reported unhealthy and restarted. (source: NFR-2)
4. **Given** any log line or metric, **When** it is inspected, **Then** it contains no email provider key and no email body. (source: NFR-3)

---

### Edge Cases

- A task is assigned, then reassigned within seconds: each assignment is its own event and its assignee receives one email (stale-assignment suppression is out of scope; see Assumptions).
- A task is saved again with the same assignee: no new assignment event, no email.
- The assignee is removed from the board before the email is sent: the email is still sent only if the task still exists; email content never exceeds what the assignee could see at assignment time. Assumed (see Assumptions).
- The worker crashes after the provider accepted the email but before the outcome is recorded: the notification is reclaimed after a visibility timeout; duplicate prevention at the provider relies on the idempotency key if the provider supports it (open question Q2).
- The provider is down for longer than the retry window: the notification ends as failed and is visible to operators; it can be requeued manually.
- Burst of assignments (for example a manager assigning many tasks): emails are sent at the rate the provider accepts without losing any.
- Task title or user names contain characters that need escaping in the email: they are rendered safely.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST send one email to the assignee when a task is assigned to them, including on task creation with an assignee and on reassignment. (source: FR-5, US-5)
- **FR-002**: The system MUST hand the email to the email provider within 1 minute of the assignment being saved under normal operation. (source: FR-5, US-5, G2)
- **FR-003**: The system MUST record each assignment notification durably in the notification outbox in the same transaction as the assignment, so a stopped worker or provider outage cannot lose it. (source: FR-5, G2)
- **FR-004**: The system MUST send exactly one email per assignment event: repeated reports of the same assignment, concurrent workers, retries and worker restarts MUST NOT cause duplicate emails. (source: US-5)
- **FR-005**: The system MUST retry temporary send failures with increasing delays up to a maximum number of attempts, and mark a notification failed (with a reason) when a failure is permanent or attempts are exhausted. (source: FR-5)
- **FR-006**: The system MUST NOT send an email, and MUST mark the notification skipped with a reason, when the task no longer exists or the assignee has no usable email address. (source: FR-5, NFR-3)
- **FR-007**: The email MUST contain the task title, board name, the name of the person who assigned the task, the due date when set and a link to the task, and MUST be sent only to the assignee. (source: FR-5, NFR-3)
- **FR-008**: The system MUST NOT send an email when a task is saved without a change of assignee. (source: FR-5)
- **FR-009**: The system MUST provide an email provider client, a notify-worker entrypoint (a different start command of the taskflow-api image) and a notification outbox that other notification features (mentions, daily digest, notification preferences) can reuse for their own notification kinds. (source: FR-5, ARCH-005)
- **FR-010**: The system MUST read the email provider key only from the environment, supplied to the worker through External Secrets from AWS Secrets Manager, and MUST NOT store it in code, configuration files or Git. (source: NFR-3, ARCH-005)
- **FR-011**: The system MUST emit structured logs, metrics and traces for every notification outcome, expose a worker health check, and alert operators when the oldest pending notification exceeds 45 seconds or notifications fail. (source: FR-5, NFR-2)
- **FR-012**: The system MUST send assignment notifications by email only; no other channel is provided in this release. (source: PRD assumption, FR-5)
- **FR-013**: The system MUST NOT write the provider key or the email body to logs, metrics or traces. (source: NFR-3)

### Key Entities *(include if feature involves data)*

- **Notification (outbox entry)**: A durable record of one notification to send. Holds its kind (here: assignment email), a unique deduplication key per assignment event, the recipient user, the task and assigning user it refers to, its status (pending, sending, sent, failed, skipped), attempt count, next attempt time, last error reason, the provider message id once sent, and timestamps (created, sent).
- **Assignment event**: The moment a task's assignee is set or changed, produced by the task feature (002-tasks-board); identified by a unique id so the same event can never create two notifications.
- **Assignment email**: The message sent to the assignee, built from the task, board, assigner and assignee data.
- **Email provider client**: The component that submits an email to the external email provider and classifies the result as accepted, temporary failure or permanent failure.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 99% of assignments result in an email handed to the provider within 60 seconds of the assignment when the provider is available.
- **SC-002**: 0 duplicate assignment emails are sent in the duplicate, concurrency and restart test scenarios.
- **SC-003**: 100% of assignments end with a recorded outcome (sent, failed or skipped); none stay pending without being retried.
- **SC-004**: Operators are alerted when the oldest pending notification is older than 45 seconds, before the 1-minute limit is exceeded.
- **SC-005**: No secret and no email body appears in any log, metric or trace sample inspected.

## Assumptions

- Email is the only notification channel in this release (PRD assumption). Notification preferences (US-7) are delivered by another feature and are not consulted here; this feature sends assignment emails always.
- "Within 1 minute" is measured from the assignment being saved to the email being accepted by the email provider; time from provider to inbox is outside our control.
- The task feature (002-tasks-board) reports an assignment event (with a unique id) whenever a task's assignee is set or changed, and calls the outbox enqueue function inside the assignment transaction. The assignee must be a board member (enforced by 001/002).
- Every assignment event produces an email, including reassignments made within seconds; suppressing stale assignments is out of scope.
- Retry policy (assumed, adjustable): first retry after 5 seconds, then growing delays, at most 6 attempts, then failed. Polling interval of the worker is 5 seconds.
- A notification stuck in "sending" is reclaimed after a visibility timeout (assumed 120 seconds).
- Email content language is the product's default language; sender address and wording are not specified in the PRD and are configurable (open question Q3).
- The email provider is not named in architecture.md; the client is built behind a provider-agnostic interface and a concrete provider is chosen later (open question Q2).
- Outbox, client and worker skeleton are shared foundations owned here; features F04, F06 and F07 reuse them.

## Open Questions (assumed answers, see clarifications.md)

- Q1: Is an email sent when the assigner assigns a task to themselves? Assumed: yes (PRD US-5 has no exception).
- Q2: Which email provider is used, and does it support idempotency keys? Assumed: provider-agnostic client; idempotency key passed when supported.
- Q3: What are the sender address/domain and the email wording? Assumed: configuration values, simple default text.
