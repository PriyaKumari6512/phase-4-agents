# Feature Specification: Notification preferences

**Feature Branch**: `007-notification-prefs`

**Created**: 2026-01-01

**Status**: Draft

**Input**: User description: "Per-user notification preferences: channel and frequency (FR-7, US-7). As a team member, I want to choose which notifications I get and how often, so that I am not overwhelmed. Email is the only channel in this release. This feature owns the preferences model, API and UI behind the flag FEATURE_NOTIFICATION_PREFS. The senders (assignment email, daily digest, mention notification) are owned by other features and must consult the preferences."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Choose which notifications I receive (Priority: P1)

A team member opens a notification settings page, sees every notification type TaskFlow can send them (task assigned to me, mention in a comment, daily digest of tasks due tomorrow), sees the channel for each (email only in this release) and switches each type on or off. The choice is saved per user and survives sign-out. The page is fully usable with the keyboard only. (source: FR-7, US-7, NFR-4)

**Why this priority**: Without a stored per-user choice there is nothing for senders to consult and nothing to tune; it is the core of FR-7.

**Independent Test**: Sign in, open the settings page, switch "Mention" off, reload the page and read the preferences through the API: "Mention" is off, the other types are unchanged. Repeat using only the keyboard.

**Open question (affects this story)**: Q1 - which channels besides email FR-7 should offer. Assumed: email is the only channel in this release; the list of channels is configurable data, not fixed in code (open question Q1).

**Acceptance Scenarios**:

1. **Given** a user who never saved preferences, **When** they open the notification settings, **Then** every notification type is shown as on with channel "email" and the default frequency, which equals today's behaviour. (source: FR-7, US-7)
2. **Given** the settings page, **When** the user switches "Mention" off and saves, **Then** the choice is persisted and shown again after a page reload and a new sign-in. (source: FR-7, US-7)
3. **Given** the settings page, **When** the user navigates and changes every control with the keyboard only, **Then** every control is reachable, shows a visible focus, has an accessible name and can be saved without a mouse. (source: NFR-4)
4. **Given** user A saved preferences, **When** user B requests or changes preferences, **Then** B only ever sees and changes B's own preferences. (source: NFR-3, FR-7)
5. **Given** the flag FEATURE_NOTIFICATION_PREFS is off, **When** a user requests the preferences endpoints or the settings page, **Then** they are not available (not found) and the settings link is not shown. (source: FR-7)

---

### User Story 2 - Choose how often I am notified (Priority: P2)

A team member chooses a frequency for each notification type that supports one, so that notifications are grouped instead of arriving one by one. The available frequencies are configurable; the starting list is "immediate", "hourly" and "daily". When a frequency other than immediate is chosen, the notifications that arrive during the window are combined into one summary email at the end of the window. (source: FR-7, US-7)

**Why this priority**: "How often" is the second half of US-7; it needs the stored preferences from Story 1 and a batching mechanism.

**Independent Test**: Set the frequency of "Mention" to hourly, trigger three mentions within the hour, and verify that one summary email listing the three mentions is sent at the end of the window and none immediately.

**Open question (affects this story)**: Q1 - which frequencies FR-7 should offer; the client has not decided. Assumed: the list is configurable data, seeded with immediate, hourly and daily as named in prd.md; "immediate" is the default (open question Q1).

**Open question (affects this story)**: Q2 - may a user delay or switch off the assignment email, given that US-5 promises an email within 1 minute? Assumed: yes, only by an explicit choice of the user; the default for assignment stays immediate, so US-5 holds for every user who has not changed it (open question Q2).

**Acceptance Scenarios**:

1. **Given** the settings page, **When** the user opens the frequency control of a notification type, **Then** only the frequencies currently enabled in the configuration are offered, with "immediate" preselected for a user without saved preferences. (source: FR-7, US-7)
2. **Given** a user with "Mention" set to hourly, **When** three mentions occur within the same hour, **Then** the user receives one summary email listing the three mentions at the end of the hour and no individual emails. (source: FR-7, US-7)
3. **Given** a user with "Mention" set to immediate, **When** a mention occurs, **Then** the mention email is sent without added delay. (source: FR-7, FR-3)
4. **Given** a frequency value that is not enabled in the configuration, **When** a client submits it, **Then** the request is rejected with a validation error and nothing is saved. (source: FR-7)
5. **Given** a notification type whose schedule is fixed (the daily digest, sent at 08:00 in the user's time zone), **When** the user opens its settings, **Then** only on/off is offered for it. (source: FR-6, FR-7)

---

### User Story 3 - Senders respect my preferences (Priority: P2)

Whenever TaskFlow is about to send an assignment email, a daily digest or a mention notification, the sender asks the preferences first and then sends now, sends later in a summary, or does not send. A user who switched a type off never receives it. (source: FR-7, US-7, FR-3, FR-5, FR-6)

**Why this priority**: Preferences that senders ignore have no value; but the senders are built by other features, so this story only defines and tests the decision contract and the integration points.

**Independent Test**: With "Assignment" off for user A and on for user B, assign a task to each; only B receives an email. Switch the flag off: both receive emails as before.

**Open question (affects this story)**: Q1 - channels and frequencies are undecided; the decision contract takes the channel as input so a new channel needs no change in the senders (open question Q1).

**Acceptance Scenarios**:

1. **Given** user A has "Assignment" switched off, **When** a task is assigned to A, **Then** no assignment email is sent to A. (source: FR-7, FR-5)
2. **Given** user B has "Daily digest" switched off, **When** the digest runs for B, **Then** B receives no digest. (source: FR-7, FR-6)
3. **Given** user C has no saved preferences, **When** any sender asks for the decision, **Then** the answer is "send now", i.e. the behaviour defined by the sender's own story is unchanged. (source: FR-7)
4. **Given** the flag FEATURE_NOTIFICATION_PREFS is off, **When** any sender asks for the decision, **Then** the answer is "send now" for every user. (source: FR-7)
5. **Given** the preferences cannot be read (for example a database error), **When** a sender asks for the decision, **Then** the sender falls back to "send now", the failure is logged and a metric is raised. (source: FR-7, G2)

---

### Edge Cases

- A user changes preferences while a summary window is open: the new setting applies to notifications created after the change; already held notifications are still delivered at the end of their window.
- A user switches a type from hourly to off while notifications are held: the held notifications for that type are dropped and not sent.
- A frequency or channel is disabled in the configuration after users selected it: those users are treated as having the default frequency, and the settings page shows the default.
- Two browser tabs save at the same time: the last save wins and each save is atomic.
- A user saves with an unknown notification type or channel: the request is rejected and nothing is saved.
- The user's time zone is unknown when a daily window ends: the window ends at 08:00 UTC (assumption A4).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST store notification preferences per user, per notification type, with a channel, an on/off flag and a frequency. (source: FR-7)
- **FR-002**: System MUST offer the notification types "assignment", "mention" and "daily digest" in the preferences. (source: FR-7, FR-3, FR-5, FR-6)
- **FR-003**: System MUST keep the list of channels and the list of frequencies as configuration data that can be extended without changing the senders; in this release the only enabled channel is "email" and the seeded frequencies are "immediate", "hourly" and "daily" (assumed, open question Q1). (source: FR-7)
- **FR-004**: Users MUST be able to read and change only their own preferences through the API and through a settings page in the web app. (source: FR-7, NFR-3)
- **FR-005**: System MUST validate every submitted channel, frequency and notification type against the configuration and reject unknown values without saving. (source: FR-7)
- **FR-006**: System MUST provide a single decision operation for senders: given a user, a notification type and a channel, it returns "send now", "send later at a given time" or "do not send". (source: FR-7)
- **FR-007**: System MUST treat a user without saved preferences as "all types on, channel email, frequency immediate". (source: FR-7)
- **FR-008**: System MUST combine notifications held for an hourly or daily frequency into one summary email per user, type and window, sent at the end of the window. (source: FR-7, US-7)
- **FR-009**: The assignment email sender, the daily digest sender and the mention sender MUST consult the decision operation before sending; this feature specifies and tests the contract and does not change the senders' own behaviour when the answer is "send now". (source: FR-7, FR-3, FR-5, FR-6)
- **FR-010**: System MUST make the whole feature (endpoints, settings page, sender checks) available only when the feature flag FEATURE_NOTIFICATION_PREFS is on; when it is off the decision operation answers "send now". (source: FR-7)
- **FR-011**: The settings page MUST be fully operable with the keyboard only and meet WCAG 2.1 AA for its controls, labels, focus and status messages. (source: NFR-4)
- **FR-012**: System MUST show the user a clear confirmation after a save and a clear message after a failed save. (source: FR-7, US-7)
- **FR-013**: System MUST log each change of preferences and each non-default decision in a structured way, and the new endpoints MUST have a health check. (source: FR-7)

### Key Entities *(include if feature involves data)*

- **Notification channel**: A way a notification can be delivered (for example "email"); configurable, enabled or disabled; only email is enabled in this release.
- **Notification frequency**: How often a type is delivered (for example "immediate", "hourly", "daily"); configurable, enabled or disabled, with the length of its window.
- **Notification preference**: One row per user and notification type: the chosen channel, the on/off flag and the chosen frequency.
- **Delivery decision**: The answer given to a sender: send now, send later at a time, or do not send.
- **Held notification**: A notification waiting for the end of its summary window; stored in the notification outbox owned by the notifications-email feature (005).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can find the settings page, change one notification type and save it in under 1 minute, with mouse or keyboard only.
- **SC-002**: 100% of notifications of a type a user switched off are not delivered to that user.
- **SC-003**: For users who never changed their preferences, delivery behaviour is identical to today (0 changed or delayed assignment, mention or digest emails).
- **SC-004**: Reading or saving preferences meets the API service level (p95 under 300 ms).
- **SC-005**: A user with an hourly frequency receives at most one summary email per hour per notification type.
- **SC-006**: All controls of the settings page pass an automated and a manual keyboard-only accessibility check against WCAG 2.1 AA.

## Assumptions

- A1: Email is the only notification channel in this release (prd.md, section 7). Other channels are not specified; the open question on additional channels and frequencies (Q1) is undecided by the client and is not decided here.
- A2: The seeded frequency list (immediate, hourly, daily) comes from the wording of the PRD open question and is a working assumption, kept as configuration data (Q1).
- A3: The default is "on" with frequency "immediate" so that G2 and US-5 (assignment email within 1 minute) keep holding for users who never change anything (Q2).
- A4: The end of a daily window is 08:00 in the user's time zone as provided by the daily-digest feature (006); if no time zone is known, 08:00 UTC is used. Hourly windows end at the top of the hour.
- A5: The daily digest has a fixed schedule (FR-6), so only on/off applies to it.
- A6: Dependencies: users and authentication (001 platform-foundation); the email client, notify-worker skeleton, assignment email and notification outbox (005 notifications-email); the daily digest and per-user time zone (006); mention notifications (004 comments-mentions). The senders in 004, 005 and 006 call this feature's decision operation.
- A7: No other channel (SMS, push, chat) and no notification types beyond the three above are in scope.
- A8: Existing board-membership rules (NFR-3) are unchanged; preferences contain no task data.
