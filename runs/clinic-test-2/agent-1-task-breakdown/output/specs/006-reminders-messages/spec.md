# Feature Specification: Confirmations, reminders and opt-out via SMS and WhatsApp

**Feature Branch**: `006-reminders-messages` (no git branch is used; directory only)

**Created**: 2027-01 (planning; delivery deadline DL-1 2027-02-22)

**Status**: Draft

**Input**: User description: "MOD-07 Release 1 part: the patient chooses SMS or WhatsApp when booking and the choice is remembered; confirmation at once after booking; reminder 24 hours before with quiet hours; no reminder for cancelled, rescheduled (new time only) or last-minute bookings; reminder content with link; STOP and reception opt-out of reminders; DLT/approved-template compliance; English, IST. Also the shared sending of sign-in codes (FR-002) and of confirmation/change notices after cancel or reschedule (FR-018). The WhatsApp-to-SMS fallback (FR-029) and the reception list of failed reminders (FR-033) are Release 2, feature 009, and are out of scope here."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Choose SMS or WhatsApp when booking (Priority: P1)

On the confirm screen of the booking flow the patient picks SMS or WhatsApp for messages about this appointment. SMS is pre-selected the first time. Whatever they pick is pre-selected next time they book.

**Why this priority**: Every message in this feature goes to the channel the patient chose; without the choice nothing can be sent. It is also the only patient-visible screen change of the feature.

**Independent Test**: Book once choosing WhatsApp, start a second booking and see WhatsApp pre-selected; a brand-new patient sees SMS pre-selected.

**Acceptance Scenarios**:

1. **Given** a patient who has never booked, **When** they reach the confirm screen, **Then** SMS is pre-selected and WhatsApp can be chosen instead.
2. **Given** a patient who chose WhatsApp on their last booking, **When** they reach the confirm screen of a new booking, **Then** WhatsApp is pre-selected.
3. **Given** a patient who confirms a booking with a channel, **When** the booking is saved, **Then** the appointment records that channel and it becomes the patient's remembered choice.
4. **Given** a patient who chose WhatsApp for an appointment, **When** messages about it are sent, **Then** they go only to WhatsApp, never to both channels.

(source: FR-013)

---

### User Story 2 - Immediate booking confirmation (Priority: P1)

Right after a booking is saved the patient receives a confirmation in the chosen channel: clinic, dentist, treatment, date, time (India time) and a link to the appointment. The booking screen does not wait for the message to be delivered.

**Why this priority**: The confirmation is the first proof to the patient that the booking exists; it also exercises the whole sending path (templates, providers, status) that the reminder story reuses.

**Independent Test**: Book an appointment against the sandbox providers; within 1 minute a confirmation with the five details and a working link is recorded as sent in the chosen channel.

**Acceptance Scenarios**:

1. **Given** a patient confirms a booking with SMS, **When** the booking is saved, **Then** a confirmation SMS is sent within 1 minute giving clinic, dentist, treatment, date, time in IST and a link to the appointment.
2. **Given** a patient confirms a booking with WhatsApp, **When** the booking is saved, **Then** the confirmation is sent as an approved WhatsApp template message with the same details.
3. **Given** the booking fails (for example the slot was just taken), **When** the patient sees the "slot taken" answer, **Then** no confirmation is sent.
4. **Given** the provider is down when the booking is saved, **When** the patient confirms, **Then** the booking still succeeds and the confirmation stays queued and is retried.
5. **Given** a patient who has switched reminders off, **When** they book, **Then** the confirmation is still sent.

(source: FR-014, NFR-008, NFR-011)

---

### User Story 3 - Reminder 24 hours before, with quiet hours (Priority: P1)

Twenty-four hours before the appointment the patient receives a reminder in the chosen channel stating clinic, dentist, date and time (IST) and a link to reschedule or cancel. A reminder that would fall due between 21:00 and 08:00 India time is sent at 20:00 the evening before the quiet period; if that time has already passed when the booking is made, it is sent at once when outside quiet hours, otherwise at 08:00.

**Why this priority**: Reducing no-shows is the main goal of the product (goal REQ-002); this is the feature that delivers it.

**Independent Test**: Create bookings at fixed times in a test clock (due at 14:00, due at 22:30, due at 03:00, booked 30 hours ahead for a night-time due, booked 10 hours ahead) and check the scheduled send time of each reminder and that it is sent within 15 minutes of that time.

**Acceptance Scenarios**:

1. **Given** an appointment tomorrow at 14:00 booked a week ago, **When** the due time (today 14:00) arrives, **Then** the reminder is sent within 15 minutes in the chosen channel with clinic, dentist, date, time (IST) and a link to reschedule or cancel.
2. **Given** an appointment whose reminder is due at 22:30 IST, **When** the booking is saved, **Then** the reminder is scheduled for 20:00 IST the same evening.
3. **Given** an appointment whose reminder is due at 03:00 IST, **When** the booking is saved, **Then** the reminder is scheduled for 20:00 IST the evening before the due time.
4. **Given** a reminder whose adjusted 20:00 time has already passed when the booking is made, **When** the booking is saved, **Then** the reminder goes at once if it is outside 21:00-08:00 IST, otherwise at 08:00 IST.
5. **Given** an appointment booked less than 24 hours before it starts, **When** the booking is saved, **Then** no reminder is created and only the confirmation is sent.
6. **Given** the reminder link, **When** the patient opens it, **Then** it opens that appointment where they can reschedule or cancel.

(source: FR-027, FR-030, NFR-005, NFR-008)

---

### User Story 4 - Reminders follow changes; change notices (Priority: P1)

When a patient cancels, no reminder is sent for that appointment and the patient gets a cancellation notice. When a patient reschedules, the old reminder is dropped, one reminder is set for the new time only, and the patient gets a change notice with the new details. These notices are the messages required by the cancel/reschedule flows.

**Why this priority**: A reminder for a cancelled appointment is a hard failure of NFR-005 ("none sent for cancelled appointments") and would confuse patients; change notices complete the patient flow of feature 004.

**Independent Test**: Book, then cancel before the reminder is due and verify no reminder is sent and a cancellation notice is; book, then reschedule and verify only one reminder exists, for the new time, and a change notice is sent.

**Acceptance Scenarios**:

1. **Given** a booked appointment with a pending reminder, **When** the patient or reception cancels it, **Then** the pending reminder is cancelled in the same change and never sent.
2. **Given** a reminder already claimed for sending, **When** the appointment is found cancelled at the last re-check, **Then** the reminder is not sent.
3. **Given** a booked appointment with a pending reminder, **When** it is rescheduled, **Then** the old reminder is cancelled and exactly one new reminder is scheduled for the new time (quiet-hours rule and less-than-24-hours rule apply).
4. **Given** a cancel or reschedule, **When** it is saved, **Then** the patient receives a notice in the chosen channel with the clinic, dentist, date and time (new date and time for a reschedule), even if reminders are switched off.
5. **Given** a reschedule to a time less than 24 hours ahead, **When** it is saved, **Then** no reminder is created and only the change notice is sent.

(source: FR-028, FR-018, NFR-005)

---

### User Story 5 - Stop reminders by replying STOP or through reception (Priority: P2)

A patient can stop reminders by replying STOP to a message, or by asking reception, who switch reminders off in the patient's record. From then on no reminders are sent, but confirmations of a booking or a change are still sent. Reception can switch reminders back on if the patient asks.

**Why this priority**: Required by the messaging rules (NFR-011) and by the patient's rights; it must be live at go-live but depends on the sending path from stories 1-4.

**Independent Test**: Post a signed STOP webhook for a test patient and check that their pending reminders are not sent and a following booking still gets a confirmation; switch the flag on from the reception record screen and check the same.

**Acceptance Scenarios**:

1. **Given** a patient with pending reminders, **When** the provider forwards their STOP reply, **Then** the patient's reminders are switched off at once and their pending reminders are cancelled (honoured well within 1 hour).
2. **Given** reminders switched off, **When** the patient books or changes an appointment, **Then** the confirmation or change notice is still sent and no reminder is created.
3. **Given** a receptionist on the patient's record screen, **When** they switch reminders off, **Then** the same effect applies as for STOP and the change is recorded with who did it and when.
4. **Given** a receptionist, **When** they switch reminders back on at the patient's request, **Then** future bookings get reminders again.
5. **Given** an incoming STOP webhook without a valid signature or from an unknown sender, **When** it is received, **Then** it is rejected and nothing changes.
6. **Given** the same STOP webhook delivered twice, **When** it is processed, **Then** the result is the same as once.

(source: FR-031, NFR-011)

---

### User Story 6 - Sign-in codes sent by SMS (Priority: P2)

When a patient asks for a sign-in code, the system sends it by SMS through the registered sender and template, as part of the request, and reports a clear error if it cannot be sent. This feature supplies only the sending; code rules (10 minutes, 5 tries, 15-minute wait) belong to the sign-in feature.

**Why this priority**: Patients cannot sign in, and so cannot book, without it; it is a shared use of the same provider setup.

**Independent Test**: Request a code for a test number against the sandbox SMS provider and check that exactly one SMS with the code is sent through the code template, and that a provider failure gives the patient a "try again" answer.

**Acceptance Scenarios**:

1. **Given** a valid phone number and sign-in allowed, **When** the patient asks for a code, **Then** one SMS with the code is sent through the registered code template before the request returns.
2. **Given** the provider is slow or failing, **When** the patient asks for a code, **Then** the request ends within the provider timeout with a clear "could not send, try again" answer and the failure is recorded without the code or the phone number in logs.
3. **Given** a sign-in code message, **When** it is stored, **Then** the code itself is not kept in readable form after sending.

(source: FR-002, NFR-011, NFR-008)

---

### User Story 7 - Reliable and compliant delivery operations (Priority: P2)

The operations team can trust that due messages go out on time and only through approved templates: delivery receipts update message status, a nightly check finds due messages that were never sent, an alert fires when reminders lag by 10 minutes, templates are chosen from configuration, and only the allowed fields reach the providers. The design leaves room for the Release 2 fallback and failed-reminder list.

**Why this priority**: Needed to prove NFR-005 and NFR-011 in production, and to catch a stuck dispatcher before patients notice.

**Independent Test**: Run the dispatcher with a failing provider and verify retries, circuit breaker and that the message stays queued; post receipts and check status; skip a due row and check the nightly check reports it; check the lag alert fires at 10 minutes.

**Acceptance Scenarios**:

1. **Given** due messages, **When** the dispatcher runs every 30 seconds, **Then** each due message is claimed by exactly one worker, sent once, and marked sent with the provider message id.
2. **Given** a provider error, **When** a send fails, **Then** it is retried up to 3 attempts in all, with waits of 5 s and 30 s, and a provider call never lasts more than 5 s.
3. **Given** 5 provider failures within 1 minute, **When** the next message is due, **Then** sending to that provider pauses (message stays queued) and resumes after a probe succeeds.
4. **Given** a delivery receipt (SMS or WhatsApp) with a valid signature, **When** it arrives, **Then** the message status is updated; the same receipt twice, or one for an unknown message id, changes nothing.
5. **Given** a due message still unsent 10 minutes after its scheduled time, **When** the monitor runs, **Then** an alert is raised.
6. **Given** the nightly check, **When** it finds a due reminder without a message row, or a stuck row for a booked appointment, **Then** it creates or requeues it and logs the repair; it never sends for a cancelled appointment.
7. **Given** any outgoing message, **When** it is built, **Then** it uses the template id from configuration for that kind and channel and sends only clinic, dentist, date, time and link as template values.
8. **Given** message rows older than 90 days, **When** the retention job runs, **Then** they are deleted.

(source: NFR-005, NFR-011, NFR-008, FR-027)

---

### Edge Cases

- Patient chooses WhatsApp but the WhatsApp send fails: in this release the message is retried per the retry rule and then marked failed; the fallback to SMS and the "reminder failed" list are Release 2 (feature 009). Status values and the adapter are designed to take them later.
- Appointment moved by reception (not the patient): treated as a reschedule; the patient gets a change notice and a new reminder.
- Cancelled by the clinic because of dentist leave: same as cancel.
- Reminder due time falls exactly at 21:00 or 08:00: 21:00 counts as quiet; 08:00 is not quiet.
- The booking is made in the last minutes before a quiet-hours boundary, or the adjusted time has just passed: the "at once / 08:00" rule applies.
- STOP arrives while a reminder is already sent to the provider: the reminder cannot be recalled; no further reminders go.
- STOP replies are read from the SMS channel only (the architecture's WhatsApp webhook carries delivery receipts, not inbound text). A patient who chose WhatsApp stops reminders through reception or by replying STOP to an SMS (for example the sign-in code SMS); a WhatsApp STOP keyword is a later addition once the provider forwards it (ASM-009).
- A booking made by reception for a patient without a chosen channel uses the account's preferred channel (SMS by default).
- STOP reply in lower case, with spaces or in another form ("stop ", "Stop"): treated as STOP.
- A patient with several appointments sends STOP: all their pending reminders are cancelled.
- The same phone number is the account for family members: opt-out and channel apply to the account (one phone number).
- Duplicate booking request retried by the browser: only one confirmation and one reminder.
- Daylight saving does not apply in India; all times are fixed UTC+05:30.
- Reminder link opened after the appointment is cancelled or has passed: the appointment page shows the current state (owned by feature 004).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST let the patient choose SMS or WhatsApp for messages about an appointment on the confirm screen of a booking, pre-select SMS for a patient with no earlier choice, and pre-select the last chosen channel on later bookings. (source: FR-013)
- **FR-002**: The system MUST record the chosen channel on the appointment and as the patient's remembered preference when the booking is saved. (source: FR-013)
- **FR-003**: The system MUST send a booking confirmation after the booking is saved, in the chosen channel, containing clinic, dentist, treatment, date, time in IST and a link to the appointment, without making the booking response wait for delivery. (source: FR-014, NFR-008)
- **FR-004**: The system MUST NOT send a confirmation for a booking that was not saved. (source: FR-014)
- **FR-005**: The system MUST create, in the same transaction as the booking, one reminder due 24 hours before the appointment start, unless the appointment starts less than 24 hours after the booking, in which case no reminder is created. (source: FR-027, FR-028)
- **FR-006**: The system MUST adjust a reminder due between 21:00 and 08:00 IST: due 21:00-23:59 goes at 20:00 the same evening; due 00:00-07:59 goes at 20:00 the evening before. If that time has already passed at booking, the reminder goes at once when outside 21:00-08:00, otherwise at 08:00. The default quiet hours and the 20:00 / 08:00 times are configuration values because Q-009 is open. (source: FR-027)
- **FR-007**: The system MUST send each reminder in the chosen channel with the clinic, dentist, date, time in IST and a link that opens the appointment to reschedule or cancel. (source: FR-030, NFR-008)
- **FR-008**: The system MUST cancel the pending reminder when the appointment is cancelled by anyone, and MUST re-check before every send that the appointment is still booked and reminders are not switched off. (source: FR-028, NFR-005)
- **FR-009**: The system MUST, when an appointment is rescheduled, cancel its pending reminder and create one reminder for the new time only, applying the same rules as at booking. (source: FR-028)
- **FR-010**: The system MUST send a notice in the chosen channel after every cancel or reschedule with the clinic, dentist, date and time, regardless of the reminders opt-out. (source: FR-018, FR-031)
- **FR-011**: The system MUST switch a patient's reminders off when a valid STOP reply is received from the provider (case and spacing insensitive), cancel their pending reminders, and still send confirmations and change notices. (source: FR-031, NFR-011)
- **FR-012**: The system MUST let reception switch a patient's reminders off, and back on, in the patient's record, with the change recorded (who, when). (source: FR-031)
- **FR-013**: The system MUST send sign-in codes by SMS through the registered code template as part of the sign-in request and return a clear error if sending fails. (source: FR-002, NFR-011)
- **FR-014**: The system MUST send SMS only with a DLT-registered sender ID and registered templates, and WhatsApp only with approved templates; the template id for each message kind and channel comes from configuration, and only the templated values (clinic, dentist, date, time, link, code) are sent to a provider. (source: NFR-011)
- **FR-015**: The system MUST write every message as a stored row (kind, channel, patient account, appointment, due time, scheduled time, status, provider message id, attempts) and send due rows from a dispatcher that handles each row once, retries a failed send up to 3 attempts in all (waits of 5 s and 30 s), limits a provider call to 5 s and pauses a provider after 5 failures in 1 minute. (source: NFR-005, NFR-011)
- **FR-016**: The system MUST accept signed delivery receipts and STOP replies from the SMS provider and signed delivery receipts from the WhatsApp provider, reject unsigned or badly signed calls, rate-limit them, and handle repeated calls and unknown message ids without effect. (source: NFR-011, FR-031)
- **FR-017**: The system MUST send 99% of due reminders within 15 minutes of their (quiet-hours-adjusted) scheduled time and none for cancelled appointments; it MUST raise an alert when a due message is still unsent after 10 minutes and run a nightly reconciliation that repairs missed or stuck reminders. (source: NFR-005)
- **FR-018**: The system MUST write all message text in English with times in IST (stored in UTC) from a single message catalogue. (source: NFR-008)
- **FR-019**: The system MUST keep rendered message text for 90 days and then delete it, and MUST NOT write patient names or phone numbers to logs. (source: NFR-011, NFR-008)
- **FR-020**: The system MUST select the SMS and WhatsApp providers by configuration, with sandbox providers in staging, behind one interface per channel so that a second provider or the Release 2 fallback can be added without changing message building. (source: NFR-011)

### Key Entities *(include if feature involves data)*

- **Message**: A confirmation, change notice, reminder or sign-in code to one patient account in one channel. Holds kind, channel, appointment, due time, scheduled (send) time, status (queued, sending, sent, delivered, failed, cancelled, skipped), provider message id, attempt count and rendered text (personal data, kept 90 days).
- **Patient account preferences**: The preferred channel (SMS by default) and the reminders opt-out flag (with who/when), held on the patient account (a phone number).
- **Appointment channel**: The channel chosen for this appointment, copied from the confirm screen.
- **Message template mapping**: Configuration linking each message kind and channel to a registered template id.
- **Provider receipt / inbound reply**: A signed call from a provider with a provider message id, a delivery state or a STOP text.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 99% of due reminders are sent within 15 minutes of their adjusted due time, measured monthly; zero reminders are sent for cancelled appointments.
- **SC-002**: 95% of booking confirmations are sent within 1 minute of the booking being saved; the booking screen is never slowed by delivery.
- **SC-003**: 100% of SMS messages use a registered template and sender and 100% of WhatsApp messages use an approved template.
- **SC-004**: After a patient replies STOP, no further reminder is sent to them from the moment the reply is processed, and in every case within 1 hour of the reply.
- **SC-005**: 100% of messages are in English with times in IST.
- **SC-006**: A patient can choose a channel with no extra screen (the choice is on the existing confirm screen) and finds their last choice pre-selected in 100% of later bookings.
- **SC-007**: A provider outage delays messages but loses none; when it ends, queued messages that are still valid are sent.

## Assumptions

- Quiet hours are 21:00-08:00 IST with the adjustment rule of ASM-003 / SA-003 (Q-009 is open; the default is PD-004).
- The SMS provider and the WhatsApp provider are not yet chosen (ASM-009); both are assumed to offer delivery-receipt webhooks, inbound STOP forwarding and a test account in weeks 1-2.
- DLT registration (DEP-001) and WhatsApp template approval (DEP-002) are done by the clinic with our help (A-005); late registration (RSK-001) is the main schedule risk. Until then sandbox providers are used in staging.
- Release 2 (feature 009) adds the WhatsApp-to-SMS fallback (FR-029) and the reception list of failed reminders (FR-033). They are out of scope here; the message status and channel adapter are designed to take them.
- The appointment page that the links open (feature 004), the booking transaction (feature 003), cancel and reschedule (feature 004) and sign-in (feature 001) exist or are built in parallel; this feature supplies hooks they call.
- One phone number is one patient account; channel and opt-out are per account (SA-001).
- The Release 1 delivery date for this feature is DL-1 2027-02-22.
- Estimate guide: all of MOD-07 is 15-24 person-days, of which the Release 2 part belongs to feature 009.
