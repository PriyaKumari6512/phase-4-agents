# Feature Specification: Daily due-tomorrow digest

**Feature Branch**: `006-daily-digest`

**Created**: 2026-01-01

**Status**: Draft

**Input**: User description: "Daily due-tomorrow digest. US-6 (Should): As a team member, I want a daily digest of tasks due tomorrow so that I can plan my day. Given tasks due tomorrow assigned to me, When the daily digest runs at 08:00 in my time zone, Then I receive one email listing them. FR-6: A daily digest email of tasks due tomorrow, sent at 08:00 in the user's time zone."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Receive a daily digest of tasks due tomorrow (Priority: P1)

As a team member, I want one email each morning at 08:00 in my time zone that lists the tasks assigned to me that are due tomorrow, so that I can plan my day. (source: US-6, FR-6)

**Why this priority**: This is the whole value of US-6 and FR-6. It is the only story that delivers the digest itself.

**Independent Test**: With a user who has a time zone and two open tasks due tomorrow, run the digest at 08:00 local time and check that exactly one email listing both tasks is sent to that user. Needs the time zone from User Story 2 to exist as data, but can be tested by setting the value directly.

**Acceptance Scenarios**:

1. **Given** tasks due tomorrow assigned to me, **When** the daily digest runs at 08:00 in my time zone, **Then** I receive one email listing them. (source: US-6, FR-6)
2. **Given** tasks due tomorrow assigned to me on several boards I belong to, **When** the digest runs, **Then** one single email lists all of them, grouped by board, and each task shows its title, board and due date. (source: FR-6)
3. **Given** I have no open tasks due tomorrow, **When** the digest runs, **Then** I receive no email (assumed, open question Q3). (source: FR-6)
4. **Given** a task due tomorrow is already in the "Done" column, **When** the digest runs, **Then** it is not listed (assumption A3). (source: FR-6)
5. **Given** a task due tomorrow is assigned to a colleague, **When** the digest runs for me, **Then** it is not listed in my email. (source: FR-6, NFR-3)
6. **Given** I am no longer a member of a board, **When** the digest runs, **Then** tasks from that board are not listed. (source: FR-6, NFR-3)
7. **Given** the digest feature flag is off, **When** the scheduled run starts, **Then** no digest is sent. (source: FR-6)

---

### User Story 2 - Capture and change my time zone (Priority: P1)

As a team member, I want my time zone stored on my profile, so that the digest arrives at 08:00 where I am. (source: US-6, FR-6)

**Why this priority**: The digest is defined as "08:00 in the user's time zone", so every user needs a time zone value. The PRD does not say how the time zone is captured; see Q2.

**Independent Test**: Set a time zone through the settings screen, reload, and confirm the same value is shown and returned; submit an invalid value and confirm it is rejected.

**Acceptance Scenarios**:

1. **Given** I open my settings, **When** I choose a time zone from the list of valid zones and save, **Then** it is stored and shown the next time I open settings. (source: FR-6)
2. **Given** I have not chosen a time zone, **When** I open settings for the first time, **Then** the zone detected by my browser is pre-selected and I can confirm or change it (assumed, open question Q2). (source: FR-6)
3. **Given** a value that is not a valid time zone name, **When** it is submitted, **Then** it is rejected with a clear error and my stored value is unchanged. (source: FR-6)
4. **Given** I have never saved a time zone, **When** the digest runs, **Then** my 08:00 is computed in UTC (assumption A2). (source: FR-6)
5. **Given** I change my time zone, **When** the next digest runs, **Then** it uses the new zone, and I do not get a second digest for a day that already had one. (source: FR-6)
6. **Given** I use the keyboard only, **When** I choose and save a time zone, **Then** I can complete every step. (source: NFR-4)

---

### User Story 3 - Exactly one digest per user per day, correct across DST (Priority: P2)

As a team member, I want to receive the digest once per day, never twice and never skipped, including on days when my clocks change, so that I can trust it. (source: US-6, FR-6)

**Why this priority**: Without this the digest is noisy or unreliable, but it builds on User Story 1.

**Independent Test**: Run the scheduler repeatedly and in parallel for the same day and check one digest per user. Run it with a simulated clock across a spring-forward and a fall-back date for several zones.

**Acceptance Scenarios**:

1. **Given** the digest already went out to me for today's local date, **When** the scheduler runs again, even concurrently or after a restart, **Then** I get no second email. (source: US-6, FR-6)
2. **Given** a send failed before the provider accepted it, **When** a later scheduler run happens on the same local date, **Then** sending is retried, up to 3 attempts in total (assumption A6). (source: FR-6)
3. **Given** my time zone changes clocks forward on a given day, **When** the digest runs, **Then** I receive it at 08:00 local time once, and "tomorrow" is the next calendar date, not 24 hours later. (source: FR-6)
4. **Given** my time zone changes clocks back on a given day, **When** the digest runs, **Then** I receive it once. (source: FR-6)
5. **Given** the scheduler was down at 08:00, **When** it comes back later the same local day, **Then** the digest is still sent once that day and never for a past day. (source: FR-6)
6. **Given** many users across several time zones, **When** each reaches 08:00 local, **Then** each receives their own digest at their own local time. (source: FR-6)

---

### Edge Cases

- A user has more tasks due tomorrow than fit comfortably in one email: the email lists all of them up to a cap of 50 and states how many more are not shown (assumption A7).
- A user's time zone has a 30- or 45-minute offset: 08:00 local still maps to an exact scheduler tick.
- A time zone rule change removes 08:00 on a given day: the send happens at the first run after the local time passes 08:00.
- The email provider is unavailable: the digest is retried per User Story 3 and the failure is logged and counted.
- A task has no due date or no assignee: it is never listed.
- A user is deleted or deactivated between run start and send: no email.
- Notification preferences (feature 007) exist and the user turned the digest off: no digest is sent. When 007 is not deployed, all users receive it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST send each user at most one digest email per local calendar date, at or after 08:00 in that user's time zone. (source: FR-6, US-6)
- **FR-002**: The digest MUST list the open tasks assigned to the user whose due date is the next calendar date in the user's time zone, limited to boards where the user is a member. (source: FR-6, US-6, NFR-3)
- **FR-003**: The system MUST NOT send a digest to a user with no matching tasks. (source: FR-6; assumed, open question Q3)
- **FR-004**: The system MUST store an IANA time zone name per user, validate it at the boundary, and let the user read and change it. (source: FR-6)
- **FR-005**: The system MUST fall back to UTC for users with no stored time zone. (source: FR-6; assumption A2)
- **FR-006**: The system MUST record each digest attempt per user and local date so that parallel runs, restarts and retries cannot produce a second email for the same user and date. (source: FR-6, US-6)
- **FR-007**: The system MUST compute 08:00 and "tomorrow" with calendar-aware time zone rules so that DST changes do not skip, duplicate or shift the digest. (source: FR-6)
- **FR-008**: The system MUST send a missed digest later on the same local date and MUST NOT send digests for past dates. (source: FR-6)
- **FR-009**: The system MUST retry a failed send on later runs of the same local date, up to 3 attempts in total, then record the failure. (source: FR-6; assumption A6)
- **FR-010**: The digest MUST be sent only when the digest feature flag `FEATURE_DIGEST` is enabled. (source: FR-6)
- **FR-011**: The system MUST check the notification preferences of feature 007 before sending when that feature is enabled, and skip users who turned the digest off. When 007 is absent it sends to everyone. (source: FR-6, FR-7)
- **FR-012**: The system MUST reuse the email client and worker skeleton of feature 005 (assignment email) and MUST NOT introduce a second email integration. (source: FR-6, FR-5)
- **FR-013**: The system MUST emit structured logs, metrics and traces for each digest run (users evaluated, sent, skipped, failed) and expose a health signal for the scheduled run. (source: constitution II)
- **FR-014**: The digest email MUST be addressed only to the task's assignee and MUST NOT expose tasks from boards the user cannot access. (source: NFR-3)

### Key Entities *(include if feature involves data)*

- **User time zone**: An IANA zone name attached to a user (for example `Europe/Berlin`). Optional; UTC is used when empty.
- **Digest delivery record**: One record per user and local date with status (claimed, sent, failed), attempt count, timestamps and the number of tasks listed. Its uniqueness on user and date enforces exactly-once.
- **Digest content**: The user's open tasks due on the next local date, grouped by board, with title, board and due date. Read from the existing task data; not stored.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of users with at least one matching task receive exactly one digest per local day; the duplicate-digest count is 0 over a 14-day test period.
- **SC-002**: At least 99% of digests arrive within 15 minutes after 08:00 in the user's time zone.
- **SC-003**: On the days clocks change in the tested zones, there are 0 skipped and 0 duplicated digests.
- **SC-004**: A user can set their time zone in under 30 seconds.
- **SC-005**: 0 digest emails contain a task from a board the recipient is not a member of.

## Assumptions

- A1 (scheduling): The worker is scheduled by a Kubernetes CronJob that starts the notify-worker image every 5 minutes (open question Q1). Exactly-once does not depend on the scheduler, only on the delivery record.
- A2 (time zone capture): Users set a time zone in settings, pre-filled from the browser; users who never set one are treated as UTC (open question Q2).
- A3: "Open" means not in the "Done" column. Due dates are calendar dates without a time of day.
- A4: Email is the only notification channel (PRD assumption); the digest is not shown in-app.
- A5: Task, user, board and membership data come from features 001 and 002 (platform foundation and tasks board); the email client, worker skeleton and outbox come from feature 005.
- A6: Up to 3 send attempts per user and date; a send whose outcome is unknown after a crash is not retried automatically, to prefer no duplicates (see research.md).
- A7: The email lists at most 50 tasks.
- A8: Notification preferences (feature 007) are optional; the digest runs without them.
- Out of scope: other channels, per-user digest time or frequency (feature 007), digests for tasks due beyond tomorrow, overdue tasks, mobile push.

## Open Questions (assumed answers, see clarifications.md)

- Q1: How is the worker scheduled (Kubernetes CronJob or an internal scheduler)? Assumed: CronJob every 5 minutes.
- Q2: How is the user's time zone captured? Assumed: settings field, pre-filled from the browser, UTC fallback.
- Q3: Do users with no due tasks get an email? Assumed: no.
