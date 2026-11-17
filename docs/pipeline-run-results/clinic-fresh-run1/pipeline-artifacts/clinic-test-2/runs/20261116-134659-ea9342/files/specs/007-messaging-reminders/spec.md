# Feature Specification: Confirmations, reminders, STOP and SMS fallback

**Feature Branch**: `007-messaging-reminders` (no git branch is created; the feature lives in `specs/007-messaging-reminders`)

**Created**: 2026-11-16

**Status**: Draft

**Input**: User description: "Confirmations, reminders, STOP and SMS fallback. Covers prd.md ids FR-014, FR-027, FR-028, FR-029, FR-030, FR-031, FR-033, NFR-005, NFR-011. MVP (Must, 1 March 2027): FR-014, FR-027, FR-028, FR-030, FR-031, NFR-005, NFR-011. Release 2 (Should, about 2-3 weeks later): FR-029 and FR-033, with the SMS fallback built behind a switch that defaults to on. Also provides the message-sending capability the sign-in feature (002) needs for the SMS sign-in code."

## Context

BrightSmile Dental runs 2 clinics in Bengaluru with about 450 appointments a week. No-shows are the clinic's biggest problem, and reminders are the main tool against them. The goal is that 99% of due reminders go out within 15 minutes of their due time. Patients choose SMS or WhatsApp when they book (that choice is stored by the booking feature, FR-013). This feature sends everything the patient receives about an appointment: the confirmation, notices of changes, the reminder 24 hours before, and the one-time sign-in code. It also handles STOP, and in Release 2 the fallback from WhatsApp to SMS and the reception list of failed reminders.

MVP stories (User Stories 1-7, Must, go-live 1 March 2027) and Release 2 stories (User Stories 8-9, Should, about 2-3 weeks after go-live) are kept separate so that the MVP can ship without Release 2.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Patient gets a confirmation when booking or changing (Priority: P1)

A patient books an appointment online (or reception books it for them). At once, in the channel chosen for the appointment, they receive a confirmation that names the clinic, dentist, treatment, date and time, and gives a link to the appointment. When the patient cancels or reschedules, they receive a change notice in the same channel that says what changed.

**Why this priority**: The confirmation is the patient's proof of the booking and the first message in the no-show chain. Without it the booking flow is not complete at go-live.

**Independent Test**: Book an appointment against a sandbox provider account for each channel; check that one confirmation per booking arrives in the chosen channel with the six items. Cancel and reschedule it and check that one change notice arrives for each.

**Acceptance Scenarios**:

1. **Given** a patient who chose SMS, **When** the booking is saved, **Then** one SMS confirmation is sent within about 30 seconds with the clinic, dentist, treatment, date, time (in IST) and a link to the appointment. (source: FR-014)
2. **Given** a patient who chose WhatsApp, **When** the booking is saved, **Then** the confirmation is sent through WhatsApp with the same content. (source: FR-014)
3. **Given** a booking that fails (for example the slot was taken), **When** the patient is told the slot is gone, **Then** no confirmation is sent. (source: FR-014)
4. **Given** the message provider is down when a booking is made, **When** the booking is saved, **Then** the booking still succeeds and the confirmation is sent as soon as the provider recovers. (source: FR-014)
5. **Given** a patient who has switched reminders off, **When** they book, **Then** they still receive the confirmation. (source: FR-031)
6. **Given** an appointment that is cancelled or rescheduled, **When** the change is saved, **Then** one change notice is sent in the chosen channel (for a reschedule it shows the new clinic, dentist, date and time). (source: FR-018, FR-031)

---

### User Story 2 - Patient gets a reminder 24 hours before, never at night (Priority: P1)

A patient with an appointment booked at least 24 hours ahead receives a reminder 24 hours before the start, in the channel they chose. It says the clinic, dentist, date and time and has a link to reschedule or cancel. A reminder that would fall between 21:00 and 08:00 India time is sent at 20:00 instead, so no patient is messaged at night.

**Why this priority**: This is the core feature that reduces no-shows.

**Independent Test**: Create appointments whose reminders fall due in daytime, in the 21:00-24:00 window and in the 00:00-08:00 window, and book some close to the due time; with a controllable clock check that each reminder is sent at the expected time in the chosen channel with the required content.

**Acceptance Scenarios**:

1. **Given** an appointment on Tuesday 11:00, **When** Monday 11:00 IST arrives, **Then** one reminder is sent in the chosen channel stating clinic, dentist, date, time and a link to reschedule or cancel. (source: FR-027, FR-030)
2. **Given** an appointment on Tuesday 22:30 (reminder due Monday 22:30), **When** Monday 20:00 IST arrives, **Then** the reminder is sent at 20:00 on Monday. (source: FR-027)
3. **Given** an appointment on Tuesday 03:00 (reminder due Monday 03:00), **When** Sunday 20:00 IST arrives, **Then** the reminder is sent at Sunday 20:00, the evening before the due day. (source: FR-027)
4. **Given** an appointment on Tuesday 08:00 (reminder due Monday 08:00, the end of quiet hours), **When** Monday 08:00 IST arrives, **Then** the reminder is sent at 08:00. (source: FR-027)
5. **Given** a booking made on Monday 20:30 for Tuesday 22:00 (due Monday 22:00, adjusted time 20:00 already passed, now outside quiet hours), **When** the booking is saved, **Then** the reminder is sent at once. (source: FR-027)
6. **Given** a booking made on Monday 21:15 for Tuesday 22:00 (adjusted time passed, now inside quiet hours), **When** the booking is saved, **Then** the reminder is sent at 08:00 on Tuesday. (source: FR-027)
7. **Given** a reminder, **When** it is built, **Then** the time shown is in IST and the text comes from the single English catalogue. (source: FR-030)

---

### User Story 3 - No wrong reminders: cancelled, rescheduled and short-notice appointments (Priority: P1)

A patient is never reminded of an appointment that no longer exists. A cancelled appointment gets no reminder, even if the reminder was already queued. A rescheduled appointment gets one reminder, for its new time only. An appointment booked less than 24 hours ahead gets only the confirmation.

**Why this priority**: A reminder for a cancelled visit would confuse patients and damage trust; NFR-005 requires zero of them.

**Independent Test**: With a controllable clock, cancel, reschedule and short-notice-book appointments around the time their reminders are due and verify what is sent.

**Acceptance Scenarios**:

1. **Given** an appointment with a queued reminder, **When** the appointment is cancelled by the patient, by reception or by the clinic, **Then** the reminder is never sent. (source: FR-028)
2. **Given** a reminder that is due now but not yet sent, **When** the appointment is cancelled one second before the send attempt, **Then** the send is skipped because the appointment is checked again immediately before sending. (source: FR-028, NFR-005)
3. **Given** an appointment with a queued reminder, **When** it is rescheduled to a new time at least 24 hours away, **Then** the old reminder is dropped and exactly one reminder exists, for the new time. (source: FR-028)
4. **Given** an appointment rescheduled to a time less than 24 hours away, **When** the change is saved, **Then** the old reminder is dropped, no new reminder is created and only the change notice is sent. (source: FR-028)
5. **Given** an appointment booked less than 24 hours before its start, **When** the booking is saved, **Then** only the confirmation is sent and no reminder is ever created. (source: FR-028)
6. **Given** a reminder that has already been sent, **When** the appointment is later rescheduled, **Then** a new reminder is created for the new time (if 24 hours or more away). (source: FR-028)

---

### User Story 4 - Patient or reception can stop reminders (Priority: P1)

A patient replies STOP to a message and from then on gets no more reminders. Or the patient asks reception, who switches reminders off in the patient's record. Confirmations, change notices and sign-in codes are still sent.

**Why this priority**: Required by Indian messaging rules (NFR-011) and by the patient's right to stop being messaged. It must work at go-live.

**Independent Test**: Send a signed STOP reply from a sandbox number, then check that queued reminders for that account are skipped while a new booking still produces a confirmation. Repeat by switching the setting off as reception.

**Acceptance Scenarios**:

1. **Given** a patient with a queued reminder, **When** a genuine STOP reply from their phone number is received, **Then** their reminders are switched off and the queued reminder is not sent. (source: FR-031)
2. **Given** reception is on the patient's record, **When** the receptionist switches reminders off, **Then** no further reminders are sent for that patient account. (source: FR-031)
3. **Given** reminders are off for a patient, **When** the patient books, reschedules or cancels, **Then** the confirmation or change notice is still sent. (source: FR-031)
4. **Given** a STOP reply, **When** it is received, **Then** it takes effect within 1 hour at the latest (the design target is at once). (source: NFR-011)
5. **Given** a STOP notification that is not properly signed or comes from a number with no account, **When** it arrives, **Then** it is rejected or ignored and no setting changes. (source: FR-031, NFR-011)
6. **Given** reminders are off, **When** reception switches them back on at the patient's request, **Then** reminders are sent again for appointments that are still 24 hours or more away. (source: FR-031; see Assumptions)

---

### User Story 5 - Reminders are on time and compliant, even when a provider has problems (Priority: P1)

The clinic's operator can rely on 99% of due reminders being sent within 15 minutes of their (adjusted) due time, on none being sent for cancelled appointments, and on every message going out only through registered templates. When a provider is slow or down, messages wait and are retried rather than being lost or duplicated, and the team is alerted when messages are late.

**Why this priority**: This is the measurable goal of the whole feature (NFR-005) and a legal condition for sending (NFR-011).

**Independent Test**: Run a simulated day of reminders against a provider stub that is slow, failing or repeating notifications; verify timeliness, no duplicates, no sends for cancelled appointments, alert on lag, and that nothing is sent without a registered template.

**Acceptance Scenarios**:

1. **Given** normal load, **When** reminders fall due, **Then** at least 99% in a month are sent within 15 minutes of their adjusted due time. (source: NFR-005)
2. **Given** the provider times out or errors, **When** a message is sent, **Then** it is retried (3 attempts, waiting 5 s then 30 s between them) and stays queued if the provider is still unavailable, rather than being dropped. (source: NFR-005)
3. **Given** many consecutive provider failures (5 within 1 minute), **When** further messages are due, **Then** sending to that provider pauses briefly and messages stay queued, and sending resumes when the provider recovers. (source: NFR-005)
4. **Given** the same message is processed twice (restart, two API instances, repeated provider notification), **When** it is sent, **Then** the patient receives it only once, and a repeated delivery receipt changes nothing. (source: NFR-005)
5. **Given** the oldest due, unsent message is more than 10 minutes late, **When** the lag is measured, **Then** an alert is raised. (source: NFR-005)
6. **Given** the nightly check, **When** it finds an appointment that should have a reminder but has none, or a message stuck in progress, **Then** it repairs it and reports the count. (source: NFR-005)
7. **Given** any message to be sent, **When** its kind and channel have no approved template configured, **Then** it is not sent and the problem is reported; SMS goes only through the registered sender ID and DLT templates, and WhatsApp only through approved templates. (source: NFR-011)
8. **Given** a provider call, **When** it is made, **Then** only the templated values (clinic, dentist, date, time, link) and the phone number are sent, and no patient name, phone number or message text appears in logs. (source: NFR-011)
9. **Given** a delivery receipt that is unsigned or refers to an unknown message, **When** it arrives, **Then** it is rejected or ignored. (source: NFR-011)
10. **Given** messages older than 90 days, **When** the retention job runs, **Then** they are deleted. (source: NFR-011)

---

### User Story 6 - Provider accounts and templates are registered and ready before go-live (Priority: P1)

The delivery team and the clinic get the SMS provider and WhatsApp provider accounts, the DLT registration (sender ID and templates) and the WhatsApp template approvals started early, so that confirmations, reminders and sign-in codes can go live on 1 March 2027. Staging works against provider sandbox accounts.

**Why this priority**: If registration or approval is late, confirmations, reminders and sign-in codes cannot go live (RSK-001). Lead times are outside our control, so this work starts first.

**Independent Test**: Check that the template catalogue is written and submitted, that sandbox accounts work in staging, and that a go-live readiness check in production configuration reports every template as approved and configured.

**Acceptance Scenarios**:

1. **Given** the message kinds and channels, **When** the template catalogue is reviewed, **Then** there is one English template for each kind and channel in use, each using only the allowed fields, ready for submission. (source: NFR-011)
2. **Given** the catalogue, **When** the clinic (with our help) submits DLT registration and the WhatsApp templates, **Then** each submission, date, owner and status is tracked. (source: NFR-011)
3. **Given** staging, **When** a booking is made, **Then** messages go to provider sandbox accounts and never to real patients. (source: NFR-011)
4. **Given** the production configuration, **When** the readiness check runs, **Then** it lists any template that is not approved or has no identifier configured, and the go-live decision uses that list. (source: NFR-011)
5. **Given** the chosen providers are not yet decided, **When** the work starts, **Then** the provider-specific parts are isolated in one adapter per provider so a provider can be replaced without changing the rest. (source: NFR-011; see Assumptions)

---

### User Story 7 - Sign-in code is sent by SMS straight away (Priority: P1)

The sign-in feature asks this feature to send a one-time code by SMS to a phone number. The code is sent during the request (not queued), so the patient sees at once whether it was sent. It goes through the registered SMS sender ID and template.

**Why this priority**: Patients cannot sign in, and so cannot book, without the code (feature 002 depends on this).

**Independent Test**: Call the sending capability with a sandbox number; check that the SMS arrives from the registered template and that a provider failure is reported back to the caller immediately.

**Acceptance Scenarios**:

1. **Given** the sign-in feature requests a code for a phone number, **When** the request is made, **Then** the SMS is sent during that request and the caller learns at once whether the provider accepted it. (source: NFR-011)
2. **Given** the SMS provider is down or times out, **When** a code is requested, **Then** the caller gets a clear "could not send" result within the timeout and the code is not queued for later delivery. (source: NFR-011)
3. **Given** a sign-in code message, **When** it is recorded, **Then** the code itself is not kept in readable form in the message record or any log. (source: NFR-011)
4. **Given** a patient who has switched reminders off, **When** they request a code, **Then** the code is still sent. (source: FR-031)

---

### User Story 8 - Undelivered WhatsApp reminder is sent once by SMS (Release 2) (Priority: P2)

When a WhatsApp reminder cannot be delivered, the patient gets it once by SMS instead. If the SMS also fails, the appointment is marked "reminder failed". The fallback is built behind a switch that is on by default, because the client has not yet agreed to it.

**Why this priority**: Release 2 (Should). A reminder that never arrives defeats the goal, but the MVP can go live without it. The client has not agreed to the fallback (ISS-001, ASM-005), so it must be switchable.

**Independent Test**: With the switch on, make the WhatsApp sandbox fail a reminder and check that exactly one SMS follows; make SMS fail too and check the appointment is marked "reminder failed". Turn the switch off and repeat.

**Acceptance Scenarios**:

1. **Given** a WhatsApp reminder that cannot be delivered (provider error after retries, or a failed delivery receipt) and the fallback switch on, **When** the failure is known, **Then** one SMS reminder with the same content is sent to the same patient. (source: FR-029)
2. **Given** a failed-receipt notification is repeated or replayed, **When** it arrives again, **Then** no second SMS is created. (source: FR-029)
3. **Given** the SMS fallback also fails, **When** the failure is known, **Then** the appointment is marked "reminder failed". (source: FR-029)
4. **Given** the fallback switch is off, **When** a WhatsApp reminder cannot be delivered, **Then** no SMS is sent and the appointment is marked "reminder failed". (source: FR-029; see Assumptions)
5. **Given** a patient who chose SMS and the SMS reminder fails, **When** the failure is known, **Then** the appointment is marked "reminder failed" and no other message is sent. (source: FR-029)
6. **Given** the fallback SMS is sent, **When** the patient has replied STOP in the meantime or the appointment has been cancelled, **Then** the SMS is not sent. (source: FR-029, FR-028, FR-031)
7. **Given** a WhatsApp reminder that is delivered, **When** the receipt arrives, **Then** no SMS is sent. (source: FR-029)

---

### User Story 9 - Reception sees tomorrow's failed reminders (Release 2) (Priority: P2)

In the afternoon, a receptionist opens the "Reminders failed" screen and sees tomorrow's appointments, at their own clinic, whose reminder could not be delivered by any channel. They phone those patients.

**Why this priority**: Release 2 (Should). It gives reception a safety net for the patients the system could not reach.

**Independent Test**: Create tomorrow's appointments with failed, delivered, cancelled and not-reminded states at two clinics, sign in as a receptionist of one clinic and check the list.

**Acceptance Scenarios**:

1. **Given** tomorrow has appointments marked "reminder failed", **When** a receptionist opens "Reminders failed", **Then** they see exactly those appointments at their own clinic with time, patient name, phone number, dentist, treatment and chosen channel. (source: FR-033)
2. **Given** a failed-reminder appointment is cancelled, **When** the list is refreshed, **Then** it no longer appears. (source: FR-033)
3. **Given** a receptionist of one clinic, **When** they open the list, **Then** they never see another clinic's appointments; the practice manager sees both clinics. (source: FR-033)
4. **Given** appointments whose reminders were delivered, are still queued, or were never created (booked less than 24 hours ahead), **When** the list is shown, **Then** they do not appear. (source: FR-033, FR-028)
5. **Given** no reminder failed for tomorrow, **When** the list is opened, **Then** an empty state says so. (source: FR-033)
6. **Given** the Release 2 feature flag is off, **When** a user looks for the screen, **Then** it is not shown. (source: FR-033)

---

### Edge Cases

- Appointment booked exactly 24 hours ahead: it is "24 hours or more", so it gets a reminder (see Assumptions).
- A reminder due exactly at 21:00 is in quiet hours and goes at 20:00; one due exactly at 08:00 is outside quiet hours and goes at 08:00.
- Daylight saving does not apply in India; all times are IST.
- Provider accepts a message but never reports delivery: the message is treated as sent; only an explicit failure receipt triggers the fallback or the failed mark.
- Two API instances claim messages at the same time: each message is sent once.
- A patient changes their chosen channel between booking and reminder: the reminder uses the channel on the appointment (chosen for it at booking).
- The phone number of the account is deleted on a deletion request: queued messages for it are removed and not sent.
- The appointment is rescheduled several times: only one live reminder exists at any time.
- A STOP arrives for a phone number with no account: ignored, no data created.
- The reception list is opened late in the evening, after the reminder due time for tomorrow's early appointments has passed: failed ones are still shown.
- Provider outage lasts longer than the 15-minute window: messages stay queued and are sent on recovery; late ones count against the 99% target and raise the lag alert.
- A reminder becomes due after its appointment started (system down all day): it is not sent.

## Requirements *(mandatory)*

### Functional Requirements

**MVP (User Stories 1-7)**

- **FR-001**: System MUST record a confirmation for every successful booking as part of saving the booking, so that a saved booking always has its confirmation queued, and MUST send it within about 30 seconds in normal operation. (source: FR-014)
- **FR-002**: Confirmation MUST be sent in the channel chosen for that appointment and MUST state clinic, dentist, treatment, date, time (IST) and a link to the appointment. (source: FR-014)
- **FR-003**: System MUST send a change notice in the chosen channel when an appointment is cancelled or rescheduled, with the new details for a reschedule. (source: FR-018, FR-031)
- **FR-004**: System MUST create one reminder for each appointment booked at least 24 hours ahead, due 24 hours before the start, in the channel chosen for the appointment. (source: FR-027)
- **FR-005**: A reminder due between 21:00 and 08:00 IST MUST be sent at 20:00: due 21:00-24:00 at 20:00 the same evening, due 00:00-08:00 at 20:00 the evening before. (source: FR-027)
- **FR-006**: If the adjusted send time has already passed when the booking is made, the reminder MUST be sent at once when the current time is outside quiet hours, otherwise at 08:00. (source: FR-027)
- **FR-007**: Every reminder MUST state clinic, dentist, date and time (IST) and include a link to reschedule or cancel. (source: FR-030)
- **FR-008**: System MUST NOT send a reminder for a cancelled appointment, including one already due and queued. (source: FR-028, NFR-005)
- **FR-009**: When an appointment is rescheduled, System MUST drop its old reminder and create one for the new time only (none if the new time is less than 24 hours away). (source: FR-028)
- **FR-010**: System MUST NOT create a reminder for an appointment booked less than 24 hours ahead; only the confirmation is sent. (source: FR-028)
- **FR-011**: Immediately before sending a reminder, System MUST re-check that the appointment is still booked and the patient account has not opted out, and skip the send otherwise. (source: FR-028, FR-031, NFR-005)
- **FR-012**: A STOP reply from a patient's phone number MUST switch reminders off for that patient account. (source: FR-031)
- **FR-013**: Reception MUST be able to switch reminders off (and back on at the patient's request) in the patient's record. (source: FR-031)
- **FR-014**: Confirmations, change notices and sign-in codes MUST still be sent when reminders are switched off. (source: FR-031)
- **FR-015**: STOP MUST be honoured within 1 hour of receipt; the design target is that it applies before the next message is sent. (source: NFR-011, FR-031)
- **FR-016**: At least 99% of due reminders in a month MUST be sent within 15 minutes of their adjusted due time. (source: NFR-005)
- **FR-017**: When a provider fails or times out, System MUST retry (3 attempts, waiting 5 s then 30 s), pause a failing provider after 5 failures in 1 minute, and keep the message queued rather than lose it. (source: NFR-005)
- **FR-018**: A message MUST reach a provider at most once even if processing is repeated, and repeated provider notifications MUST NOT change the outcome. (source: NFR-005)
- **FR-019**: System MUST raise an alert when the oldest due unsent message is more than 10 minutes late. (source: NFR-005)
- **FR-020**: A nightly check MUST find appointments missing a due reminder and messages stuck in progress, repair them and report the counts. (source: NFR-005)
- **FR-021**: SMS MUST go only through the registered sender ID and registered templates, and WhatsApp only through approved templates; a message with no approved template configured MUST NOT be sent. (source: NFR-011)
- **FR-022**: Only the phone number and the templated values (clinic, dentist, date, time, link) MUST be sent to providers. (source: NFR-011)
- **FR-023**: System MUST accept provider notifications (delivery receipts, STOP replies) only when properly signed, and MUST ignore those for unknown messages. (source: NFR-011, FR-031)
- **FR-024**: System MUST NOT write patient names, phone numbers or message text to logs, and MUST delete messages 90 days after creation. (source: NFR-011)
- **FR-025**: System MUST keep a single English template catalogue, with template identifiers held in configuration and times shown in IST. (source: FR-014, FR-030, NFR-011)
- **FR-026**: System MUST provide the sign-in feature with a way to send the SMS sign-in code during the request and return the result at once, without queueing. (source: NFR-011)
- **FR-027**: System MUST NOT keep the sign-in code in readable form in message records or logs. (source: NFR-011)
- **FR-028**: The delivery team MUST have a written template catalogue, a tracked submission status for DLT registration and WhatsApp template approval, sandbox provider accounts for staging, and a go-live readiness check listing any unapproved template. (source: NFR-011)

**Release 2 (User Stories 8-9)**

- **FR-029**: When a WhatsApp reminder cannot be delivered and the fallback switch is on, System MUST send it once by SMS, and MUST create at most one fallback per reminder. (source: FR-029)
- **FR-030**: The fallback switch MUST be configurable without a code change and MUST default to on. (source: FR-029)
- **FR-031**: When a reminder cannot be delivered by any permitted channel, System MUST mark the appointment "reminder failed". (source: FR-029)
- **FR-032**: Reception MUST see a "Reminders failed" list of tomorrow's appointments whose reminder failed, limited to the receptionist's own clinic (the practice manager sees both clinics), showing time, patient name, phone number, dentist, treatment and channel. (source: FR-033)

### Key Entities *(include if feature involves data)*

- **Message**: One outgoing message. Kind (sign-in code, confirmation, change notice, reminder), channel (SMS or WhatsApp), the patient account and appointment it belongs to, the time it is due and the adjusted time it is to be sent, status (queued, sent, delivered, failed, skipped), the provider's message id, number of attempts, and the rendered text (personal data, kept 90 days; never kept for sign-in codes). A fallback SMS refers to the WhatsApp message it replaces.
- **Reminder state on an appointment**: Whether the appointment has a live reminder, and whether it is marked "reminder failed" (Release 2).
- **Patient account**: Owned by the sign-in feature; this feature reads the preferred/chosen channel and reads and sets the "reminders off" flag.
- **Appointment**: Owned by the booking feature; this feature reads clinic, dentist, treatment, start time, status and channel.
- **Message template**: A registered or approved text for one kind and channel, with an identifier held in configuration and a registration status.
- **Provider notification**: A signed delivery receipt or STOP reply from the SMS or WhatsApp provider, matched to a message by the provider's message id.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In normal operation, 95% of confirmations and change notices are sent within about 30 seconds of the booking or change being saved (checked in tests and measured in operation). (source: FR-014)
- **SC-002**: At least 99% of due reminders in a month are sent within 15 minutes of their adjusted due time. (source: NFR-005)
- **SC-003**: Zero reminders are sent for cancelled appointments, in tests and in monthly operation. (source: NFR-005, FR-028)
- **SC-004**: 100% of STOP replies take effect within 1 hour; in tests, no reminder is sent after a STOP is processed, while 100% of confirmations and change notices after STOP are still sent. (source: FR-031, NFR-011)
- **SC-005**: 100% of SMS go through registered templates and the registered sender ID, and 100% of WhatsApp messages through approved templates. (source: NFR-011)
- **SC-006**: Every template for every message kind and channel in use is submitted for registration or approval and approved before the Release 1 UAT-ready date (22 February 2027), so that go-live on 1 March 2027 is not blocked. (source: NFR-011)
- **SC-007**: A patient never receives more than one reminder per appointment, and never more than one fallback SMS per reminder, even when providers repeat notifications. (source: FR-027, FR-029)
- **SC-008**: In tests of Release 2, 100% of undelivered WhatsApp reminders produce exactly one SMS when the switch is on and none when it is off, and 100% of reminders that fail on every permitted channel appear in the reception list on the day before the appointment. (source: FR-029, FR-033)
- **SC-009**: The "Reminders failed" list loads within 2 seconds for 95% of requests and shows all of tomorrow's failed-reminder appointments for the receptionist's clinic. (source: FR-033)

## Assumptions

- Chosen providers: the SMS provider and the WhatsApp provider are not yet named. The design isolates each provider behind its own adapter. ASM-009 is assumed to hold: providers offer delivery-receipt webhooks, forwarding of inbound replies (STOP) and a test account in weeks 1-2.
- Quiet hours are 21:00-08:00 IST (SA-003, PD-004); the exact rule for night-time reminders (Q-009) is still open; Assumed: the rule in FR-005 and FR-006 (open question Q1).
- "Booked at least 24 hours ahead" includes exactly 24 hours; "less than 24 hours" gets no reminder.
- The reminder time is always 24 hours before the appointment start, adjusted for quiet hours; no second reminder is sent.
- A reminder is for an appointment, but the opt-out is per patient account (phone number), so STOP stops reminders for all appointments of that account, including family members' appointments (family members are Release 2 in another feature).
- STOP stops reminders only. Confirmations, change notices and sign-in codes are always sent.
- STOP by reply is recognised from SMS replies. Whether a STOP sent in a WhatsApp conversation is also honoured depends on what the WhatsApp provider forwards. Assumed: only SMS replies are processed in the MVP and WhatsApp patients ask reception (open question Q3).
- Reception can switch reminders back on at the patient's request; the PRD only says they can switch them off, so a patient cannot switch them back on by messaging.
- The fallback to SMS (FR-029) applies to reminders. Confirmations and change notices that fail are retried and reported but not re-sent by another channel.
- In the MVP (before Release 2), a reminder that fails after all retries is recorded as failed for operators and in logs without personal data, but not shown to reception; the "reminder failed" mark and the reception list are Release 2.
- When the fallback switch is off (Release 2), a failed WhatsApp reminder is marked "reminder failed" directly.
- The client has not agreed to the fallback (ISS-001, ASM-005); it is built behind a switch that defaults to on. Assumed: the fallback stays on until the client decides (open question Q2).
- Booking, rescheduling and cancelling (features 004, 005 and 006) call this feature when an appointment is created or changed; the patient's chosen channel is stored by feature 004; the reception patient record screen is built by feature 006 and this feature adds the "reminders" switch to it; the sign-in feature (002) calls this feature to send the code.
- The link in messages leads to the appointment page, where the patient signs in if needed (feature 005); no personal data is placed in the link.
- Reminders cover appointments in the next 30 days at most (the booking horizon), so no long-range scheduling is needed.
- Message charges are paid by the clinic and the provider accounts are in the clinic's name (CON-007); DLT registration and WhatsApp templates are completed by the clinic with our help (A-005, DEP-001, DEP-002). If they are late, confirmations, reminders and sign-in codes cannot go live (RSK-001).
- Message text, language: English only, times in IST.
- Out of scope: marketing messages, recall messages, waiting-list messages, other languages, marking on the reception list that a patient has been phoned, and messages other than the four kinds above.

## Open Questions (assumed answers; see clarifications.md)

- Q1 (Q-009): When is a night-time reminder sent? Assumed: at 20:00 as in FR-005 and FR-006.
- Q2 (ISS-001): Does the clinic agree to the WhatsApp-to-SMS fallback? Assumed: yes for now; built behind a switch that defaults to on.
- Q3: Can a patient who chose WhatsApp stop reminders by replying STOP in WhatsApp? Assumed: only SMS replies are processed in the MVP; WhatsApp patients ask reception.
