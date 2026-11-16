# Feature Specification: WhatsApp to SMS fallback and reminders-failed list

**Feature Branch**: `009-sms-fallback-failed-list`

**Created**: 2026-11-12

**Status**: Draft

**Input**: User description: "WhatsApp to SMS fallback and reminders-failed list (MOD-07 Release 2 part, DL-2 2027-03-19, not hard). If a WhatsApp reminder cannot be delivered it is sent once by SMS instead; if the SMS also fails the appointment is marked 'reminder failed'; reception sees tomorrow's appointments whose reminder failed so they can phone those patients. Built behind a switch, default on. Source: FR-029, FR-033 (PD-005, SA-008, ASM-005, RSK-005)."

## Context

This is a Release 2 part of the messages and reminders module (MOD-07). Release 1 already sends confirmations and reminders in the channel the patient chose, with the sending, retry, delivery-receipt and STOP handling (feature 006). This feature adds what happens when a WhatsApp reminder finally fails, and gives reception a list of tomorrow's patients who could not be reached, so they can phone them (reception's afternoon routine, "Reminders failed"). The delivery date (2027-03-19) is a target, not a hard date. The client has **not** agreed to the SMS fallback (open question Q1): it is built behind a switch that is on by default, and it adds message charges.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A failed WhatsApp reminder is sent once by SMS (Priority: P1)

A patient chose WhatsApp for messages. Their reminder cannot be delivered on WhatsApp (the provider reports an error after all attempts, or reports a failed delivery receipt). The system then sends the same reminder once by SMS so the patient is still reminded.

**Why this priority**: A reminder that never arrives defeats the goal of fewer no-shows; this is the core of the feature.

**Independent Test**: Make a WhatsApp reminder fail (provider error after 3 attempts, or a failed receipt) and check that exactly one SMS reminder is created and sent for it, even when the failed receipt is delivered several times.

**Acceptance Scenarios**:

1. **Given** a due WhatsApp reminder for a booked appointment and the fallback switch on, **When** the WhatsApp provider returns an error on all 3 attempts, **Then** one SMS reminder with the same content is created and sent to the patient's phone number.
2. **Given** a WhatsApp reminder that was accepted by the provider, **When** a failed delivery receipt arrives later, **Then** one SMS reminder is created and sent.
3. **Given** a WhatsApp reminder that already has its SMS fallback, **When** the same failed receipt is received again (replayed), **Then** no second SMS is created or sent.
4. **Given** a WhatsApp reminder that was delivered, **When** a delivery receipt arrives, **Then** no SMS is sent.
5. **Given** an SMS fallback has been sent, **When** it is delivered, **Then** the appointment is not marked "reminder failed".

(source: FR-029, PD-005, SA-008)

---

### User Story 2 - The fallback respects STOP, cancellations and the switch (Priority: P2)

The fallback never sends an SMS the patient has asked not to receive, never for an appointment that has since been cancelled, and can be switched off without a new release because the client has not agreed to it.

**Why this priority**: These are compliance, cost and trust guards around Story 1; a fallback SMS to an opted-out patient breaks the STOP promise.

**Independent Test**: Fail a WhatsApp reminder in each situation (patient opted out, appointment cancelled, switch off) and check that no SMS is created and nothing wrong is shown to reception.

**Acceptance Scenarios**:

1. **Given** a failed WhatsApp reminder for a patient who has switched reminders off (STOP or by reception), **When** the fallback would run, **Then** no SMS is created.
2. **Given** a failed WhatsApp reminder whose appointment has been cancelled, **When** the fallback would run, **Then** no SMS is created.
3. **Given** the fallback switch is off, **When** a WhatsApp reminder finally fails, **Then** no SMS is created and the appointment is marked "reminder failed" so reception can phone the patient.
4. **Given** the system is installed without any setting for the switch, **When** a WhatsApp reminder finally fails, **Then** the fallback behaves as on.
5. **Given** the switch was turned off while an SMS fallback was waiting to be sent, **When** the sending is due, **Then** the SMS is not sent and the appointment is marked "reminder failed".

(source: FR-029, FR-031, FR-028, PD-005, ASM-005, RSK-005)

---

### User Story 3 - An appointment is marked "reminder failed" when the SMS also fails (Priority: P1)

When the SMS fallback also cannot be delivered, the appointment is marked "reminder failed", so that nobody assumes the patient was reminded.

**Why this priority**: Without this mark, reception cannot know whom to phone (Story 4 depends on it).

**Independent Test**: Fail a WhatsApp reminder and then its SMS fallback (provider error or failed receipt) and check that the appointment shows "reminder failed" once, and that replayed receipts change nothing.

**Acceptance Scenarios**:

1. **Given** an SMS fallback for a failed WhatsApp reminder, **When** the SMS provider returns an error on all attempts, **Then** the appointment is marked "reminder failed".
2. **Given** an SMS fallback accepted by the provider, **When** a failed delivery receipt arrives, **Then** the appointment is marked "reminder failed".
3. **Given** an appointment already marked "reminder failed", **When** the same failed receipt is received again, **Then** the mark is unchanged and no further message is sent.
4. **Given** the appointment was cancelled before the SMS failed, **When** the SMS failure is recorded, **Then** the appointment is not shown as "reminder failed" to reception.
5. **Given** a "reminder failed" mark, **When** a later delivery receipt says the earlier message was in fact delivered, **Then** the mark is removed.

(source: FR-029, REQ-011)

---

### User Story 4 - Reception gets tomorrow's reminders-failed list (Priority: P2)

A receptionist asks for the list of tomorrow's appointments, at their own clinic, whose reminder failed, with what is needed to phone the patient (patient name, phone number, time, dentist, treatment).

**Why this priority**: This is the human fallback that makes the failure visible and actionable; it relies on Story 3.

**Independent Test**: Create appointments for tomorrow and the day after at two clinics, some marked "reminder failed", and check that a receptionist of clinic A sees only clinic A's tomorrow appointments that are marked, ordered by time.

**Acceptance Scenarios**:

1. **Given** tomorrow has 3 booked appointments at the receptionist's clinic marked "reminder failed", **When** the receptionist requests the list, **Then** all 3 are listed in time order with patient name, phone number, time, dentist and treatment.
2. **Given** an appointment marked "reminder failed" at another clinic, **When** a receptionist of this clinic requests the list, **Then** it is not shown.
3. **Given** an appointment marked "reminder failed" for a day other than tomorrow, **When** the list is requested, **Then** it is not shown.
4. **Given** a "reminder failed" appointment that has since been cancelled, **When** the list is requested, **Then** it is not shown.
5. **Given** no reminders failed, **When** the list is requested, **Then** an empty list is returned, not an error.
6. **Given** a patient, dentist or practice manager signs in, **When** they request the list, **Then** the request is refused.

(source: FR-033, FR-004, NFR-006)

---

### User Story 5 - "Reminders failed" screen for reception (Priority: P3)

In the afternoon the receptionist opens the "Reminders failed" screen for tomorrow, sees the patients to phone, and works down the list. The screen is hidden until Release 2 is switched on.

**Why this priority**: Presents Story 4; the list is useful as soon as the screen exists, but the screen can follow the data.

**Independent Test**: Sign in as a receptionist with the Release 2 flag on and off; check that the entry and the screen appear only when on, and that the list matches the data.

**Acceptance Scenarios**:

1. **Given** the Release 2 flag is on and a receptionist is signed in, **When** they open "Reminders failed", **Then** tomorrow's failed reminders of their clinic are shown with a phone number per patient.
2. **Given** the Release 2 flag is off, **When** a receptionist uses the application, **Then** no "Reminders failed" entry is shown and its address shows the standard not-found page.
3. **Given** there are none, **When** the screen opens, **Then** a plain message says no reminders failed for tomorrow.
4. **Given** the list cannot be loaded, **When** the screen opens, **Then** an error message with a retry action is shown.
5. **Given** a dentist, patient or practice manager is signed in, **When** they browse the application, **Then** they see no "Reminders failed" entry.

(source: FR-033, REQ-011)

---

### Edge Cases

- The WhatsApp provider reports "failed" for a message that was already reported "delivered": the delivered status wins; no SMS is sent (receipts may arrive out of order).
- The same failed receipt arrives twice, or at the same moment as the dispatcher's own failure: still exactly one SMS.
- The patient has no valid phone number for SMS: the appointment is marked "reminder failed" without an SMS attempt.
- The SMS provider is down for a long time: the SMS is retried as for any SMS; after the final attempt the appointment is marked "reminder failed".
- WhatsApp fails close to the appointment start (after the reminder time window): the SMS is still sent only if the appointment has not started.
- A WhatsApp failure for a confirmation or change notice (not a reminder): the fallback applies to reminders only; other messages keep their Release 1 behaviour.
- Reminder is rescheduled after failure: the new reminder is a new message with its own fallback; the old failed mark no longer applies to the new time.
- Midnight: "tomorrow" is by India time (IST), not server time.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When a WhatsApp reminder finally fails (the provider returns an error after 3 attempts, or a failed delivery receipt arrives), the system MUST send the reminder once by SMS to the same patient. (source: FR-029, PD-005)
- **FR-002**: The system MUST create at most one SMS fallback for any one original WhatsApp message, even when failed receipts are replayed or arrive at the same time as the dispatcher's own failure. (source: FR-029)
- **FR-003**: The system MUST NOT create an SMS fallback when the patient has switched reminders off, when the appointment is cancelled, or when the original WhatsApp message was delivered. (source: FR-029, FR-031, FR-028)
- **FR-004**: The system MUST provide a setting that turns the SMS fallback off; it MUST be on when no value is set. When off, a finally failed WhatsApp reminder is marked "reminder failed" without sending an SMS. (source: FR-029, ASM-005, RSK-005)
- **FR-005**: The SMS fallback MUST use the same registered SMS template content rules as any SMS reminder (clinic, dentist, date, time, link to reschedule or cancel). (source: FR-029, FR-030, NFR-011)
- **FR-006**: When the SMS fallback finally fails (provider error after its attempts, or a failed delivery receipt), the system MUST mark the appointment "reminder failed". Repeated receipts MUST NOT change the mark again. (source: FR-029)
- **FR-007**: The system MUST keep the "reminder failed" mark only while the appointment is booked, and MUST remove it when a later receipt shows delivery. (source: FR-029, FR-028)
- **FR-008**: The system MUST give a receptionist the list of tomorrow's (IST) booked appointments at their own clinic whose reminder is marked "reminder failed", in time order, each with patient name, phone number, time, dentist and treatment. (source: FR-033, FR-004)
- **FR-009**: The list MUST be refused to every role other than receptionist, and MUST never include another clinic's appointments. (source: FR-033, FR-004, NFR-006)
- **FR-010**: Reception MUST have a "Reminders failed" screen showing that list, with an empty-state message and an error state with retry. (source: FR-033)
- **FR-011**: The "Reminders failed" screen MUST be hidden behind the Release 2 flag until the data is ready. (source: FR-033)
- **FR-012**: The system MUST NOT write patient names or phone numbers to logs when running the fallback or the list; logs carry identifiers only. (source: NFR-007, FR-029)
- **FR-013**: Each fallback decision (sent, skipped for opt-out, skipped for cancelled, skipped for switch off, marked failed) MUST be recorded so it can be counted and audited. (source: FR-029, NFR-005)

### Key Entities *(include if feature involves data)*

- **Message (reminder)**: One message to a patient about an appointment, in one channel (WhatsApp or SMS), with a status and attempts. A fallback SMS is a message linked to the original WhatsApp message; at most one per original.
- **Reminder-failed mark**: The state "reminder failed" on the reminder of an appointment, set when no channel could deliver it; read by reception.
- **Fallback setting**: The on/off setting for the SMS fallback, on by default.
- **Appointment / Patient**: Existing entities; used for clinic, time, dentist, treatment, cancelled state, patient name, phone number and reminders opt-out.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of tested cases where a WhatsApp reminder finally fails and the fallback applies, exactly one SMS reminder is sent, including when the failure is reported several times.
- **SC-002**: 0 SMS fallbacks are sent to patients who have switched reminders off or for cancelled appointments, in all tests.
- **SC-003**: 100% of appointments whose WhatsApp reminder and SMS fallback both failed appear on the reception list for the day before the appointment, and 0 appear on any other clinic's list.
- **SC-004**: A receptionist can open the list and see the first patient to phone within 3 seconds on a desktop browser for a list of up to 50 appointments.
- **SC-005**: With the switch turned off, 0 fallback SMS messages are sent from the next failure onwards, with no new release needed.
- **SC-006**: Before the Release 2 flag is on, 0 receptionists see the "Reminders failed" entry.

## Assumptions

- The sending, 3 attempts with backoff, delivery receipts, STOP handling and the reminder dispatcher already exist from feature 006; this feature adds the fallback decision and the "reminder failed" state to them.
- Open question Q1 (recorded in `clarifications.md`): the client has not agreed to the fallback. Assumed: build it behind a switch that is on by default (PD-005, SA-008) and tell the client that it adds message charges.
- Only reminders fall back; confirmations and change notices do not.
- The "reminder failed" state also applies when a reminder chosen as SMS finally fails, so reception gets one complete list; this reuses the same state and needs no extra rule.
- "Tomorrow" means the next calendar day in India time (IST); the list is read live and has no history view.
- Reception phones patients outside the system; the list has no "called" tick in this release.
- The Release 2 flag is the same flag that hides the other Release 2 screens.
- Message rows, including the failed mark, are kept 90 days like all messages.
- Depends on feature 006 (messaging, adapters and webhooks) and on the reception module's clinic scoping for receptionists.
