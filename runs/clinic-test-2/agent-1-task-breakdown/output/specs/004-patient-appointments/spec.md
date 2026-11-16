# Feature Specification: Patient appointments: view, reschedule, cancel

**Feature Branch**: `004-patient-appointments`

**Created**: 2026-11-10

**Status**: Draft

**Input**: User description: "Patient appointments: view, reschedule, cancel (MOD-04, Release 1, DL-1 2027-02-22). A signed-in patient sees upcoming and past appointments with status, reschedules to another free slot or cancels until 4 hours before the start; inside 4 hours the page shows the clinic phone number; the freed slot is bookable at once and the patient gets a message in the chosen channel; the link in messages opens the appointment."

**Source requirements** (prd.md): FR-015, FR-016, FR-017, FR-018. The `FR-nnn` ids below are this feature's own numbering; each item ends with `(source: ...)` naming the prd.md ids it comes from. Flow: prd.md section 6, "A patient reschedules or cancels" (screens: my appointments, appointment, slot picker, done).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See my appointments (Priority: P1)

A signed-in patient opens "My appointments" and sees their upcoming appointments and their past appointments, each with clinic, dentist, treatment, date, time (India time) and status. Choosing one opens the appointment screen with the full details. The list is built per person of the account, so when family members arrive in Release 2 their appointments appear in their own group with no change to the screen; in Release 1 only the account holder's own appointments are listed. On the appointment screen the patient sees "Change time" and "Cancel" buttons when the change is still allowed, or the clinic's phone number when it is not. (source: FR-015)

**Why this priority**: Every other story starts here, and it is useful by itself: patients can check a booking without phoning reception.

**Independent Test**: Sign in as a patient with two upcoming, one past and one cancelled appointment, open "My appointments", and check grouping, status text, IST times and that another patient's appointments never appear.

**Acceptance Scenarios**:

1. **Given** a signed-in patient with upcoming and past appointments, **When** they open "My appointments", **Then** they see the upcoming ones first (earliest first) and the past ones below (latest first), each with clinic, dentist, treatment, date, time in IST and status. (source: FR-015)
2. **Given** a patient with a cancelled appointment and an appointment marked arrived or no-show, **When** they open "My appointments", **Then** those appear in the past group with the status shown in plain words (for example "Cancelled by you", "Cancelled by the clinic", "Attended", "Missed"). (source: FR-015)
3. **Given** a patient with no appointments, **When** they open "My appointments", **Then** they see a short message and a "Book" button. (source: FR-015)
4. **Given** a signed-in patient, **When** they ask for the appointment of another patient (by changing the id in the address), **Then** the system answers as if it does not exist and shows no data of that other patient. (source: FR-015)
5. **Given** an upcoming appointment that starts in more than 4 hours, **When** the patient opens it, **Then** the buttons "Change time" and "Cancel" are shown. **Given** one that starts in 4 hours or less, **When** the patient opens it, **Then** the buttons are replaced by the clinic's phone number. (source: FR-015, FR-017)
6. **Given** a phone with a narrow screen, **When** the patient uses these screens, **Then** nothing needs sideways scrolling and every button is easy to tap. (source: FR-015)

---

### User Story 2 - Cancel an upcoming appointment (Priority: P1)

A patient opens an upcoming appointment, chooses "Cancel", confirms, and sees a "Done" screen saying the appointment is cancelled. The slot is free at once for other patients, the appointment's reminder is withdrawn, and the patient gets a message in the channel they chose for that appointment. Cancelling is possible until 4 hours before the start; after that the page shows the clinic's phone number instead of the buttons and the system refuses a cancel sent by other means. (source: FR-017, FR-018)

**Why this priority**: It frees chairs for other patients, which is the point of the product, and it is the simplest of the two changes.

**Independent Test**: Cancel an appointment 5 hours ahead and check status, free slot, history row and message; then try an appointment 3 hours ahead and check that no cancel is possible.

**Acceptance Scenarios**:

1. **Given** an upcoming appointment more than 4 hours away, **When** the patient chooses "Cancel" and confirms, **Then** the appointment status becomes "cancelled by the patient", the "Done" screen shows the result, and a record of who cancelled and when is kept. (source: FR-017)
2. **Given** a cancelled appointment, **When** another patient looks for slots of that dentist at that time, **Then** the slot is offered at once and can be booked. (source: FR-018)
3. **Given** a cancelled appointment, **When** the cancel is done, **Then** the patient gets a message in the channel chosen for that appointment stating clinic, dentist, date and time of the cancelled visit, and no reminder is sent for it. (source: FR-018)
4. **Given** an appointment 4 hours or less away, **When** the patient opens it, **Then** no "Cancel" button is shown, the clinic phone number is shown, and a cancel request made some other way is refused with the same phone number in the answer. (source: FR-017)
5. **Given** the patient chooses "Cancel", **When** they do not confirm (they go back), **Then** nothing changes. (source: FR-017)
6. **Given** the patient taps "Confirm" twice, **When** the second request arrives, **Then** the appointment is cancelled once, one message is sent, and the patient sees the same "Done" screen. (source: FR-017, FR-018)
7. **Given** the message provider is unavailable, **When** the patient cancels, **Then** the cancel still succeeds and the message is sent later. (source: FR-018)

---

### User Story 3 - Reschedule an upcoming appointment (Priority: P2)

A patient opens an upcoming appointment, chooses "Change time", and sees free slots for the same clinic and the same treatment with any dentist. They pick one, confirm, and see a "Done" screen with the new time. The old slot becomes free at once, the reminder moves to the new time, and the patient gets a message in their chosen channel. Rescheduling is possible until 4 hours before the current start. If someone else takes the chosen slot first, the patient is told and shown the next free slots. A later rule (feature 006, FR-025) may block rescheduling; this feature calls a policy check that always allows it in Release 1. (source: FR-016, FR-018)

**Why this priority**: Important to keep patients instead of losing them to a cancel, but it builds on the screens and rules of the first two stories.

**Independent Test**: Reschedule an appointment 2 days ahead to a free slot with another dentist; check new time, freed old slot, history row, message; then race two patients for one slot and check one wins.

**Acceptance Scenarios**:

1. **Given** an upcoming appointment more than 4 hours away, **When** the patient chooses "Change time", **Then** they see free slots for the same clinic and treatment from any dentist, within the same booking horizon as new bookings, never the slot they already hold. (source: FR-016)
2. **Given** the patient picks a free slot and confirms, **When** the change is saved, **Then** the appointment has the new date, time and dentist, keeps its clinic, treatment and channel, and the "Done" screen shows the new details. (source: FR-016)
3. **Given** the change is saved, **When** another patient looks for slots, **Then** the old slot is offered at once. (source: FR-018)
4. **Given** the change is saved, **When** messages are created, **Then** the patient gets a message in the channel chosen for that appointment with the new clinic, dentist, date and time, and the old reminder is withdrawn so that only a reminder for the new time can exist. (source: FR-016, FR-018)
5. **Given** another patient takes the chosen slot while this patient is choosing, **When** the patient confirms, **Then** nothing changes, the patient is told the slot was just taken and is shown the next free slots, and keeps their original appointment. (source: FR-016)
6. **Given** an appointment 4 hours or less away, **When** the patient opens it, **Then** no "Change time" button is shown, the clinic phone number is shown, and a change request made some other way is refused. (source: FR-016, FR-017)
7. **Given** the no-show policy says a patient may not reschedule, **When** the patient chooses "Change time", **Then** the page shows the clinic phone number instead. In Release 1 the policy always allows. (source: FR-016)
8. **Given** a reschedule, **When** the history is read, **Then** it shows who changed the appointment, when, and the old and new time. (source: FR-016, FR-018)

---

### User Story 4 - Open an appointment from a message link (Priority: P2)

A patient taps the link in a confirmation, change message or reminder. If they are signed in, the appointment screen opens at once. If not, they sign in with their phone code and then land on that same appointment. A link only opens an appointment of the signed-in patient; for anyone else it behaves as an unknown appointment. This lets the patient reach "Change time" or "Cancel" in one tap from the reminder. (source: FR-015, FR-016, FR-017)

**Why this priority**: It turns the reminder into a one-tap way to free a slot, but the stories above work without it through "My appointments".

**Independent Test**: Open the link of an appointment in a fresh browser, sign in, and check that the appointment screen opens; repeat with another patient's account and check that it does not.

**Acceptance Scenarios**:

1. **Given** a patient who is not signed in, **When** they open the appointment link, **Then** they are asked to sign in and, after signing in, the appointment screen opens. (source: FR-015)
2. **Given** a signed-in patient, **When** they open the link of their own appointment, **Then** the appointment screen opens at once with the buttons or the phone number according to the 4-hour rule. (source: FR-015, FR-017)
3. **Given** a patient signed in as someone else, **When** they open the link, **Then** they see "appointment not found" and no data of the appointment. (source: FR-015)
4. **Given** a link to a cancelled or past appointment, **When** the patient opens it, **Then** the appointment screen shows its status without buttons. (source: FR-015)

---

### Edge Cases

- Exactly 4 hours before the start: the change is still allowed; one minute later it is not (Assumed, open question Q1).
- The patient has the page open and the 4-hour time passes: the buttons are still visible, but the system refuses the action and shows the clinic phone number.
- Reception cancels or moves the appointment while the patient is looking at it: the patient's next action is refused with a clear message and the screen refreshes to the current state.
- The appointment already started or is past: no change is possible; only the status is shown.
- The patient has chosen STOP for reminders: change and cancel messages are still sent, because FR-031 of prd.md keeps confirmations of a change (source: FR-018).
- The patient has no new slot to choose (no free slot in the horizon): the slot picker says so and offers the clinic phone number; the original appointment stays.
- Rescheduling to the very same dentist and time is not offered.
- Many reschedules of the same appointment are allowed; each one is recorded (Assumed, open question Q3).
- A patient asks to see an appointment whose personal link was removed after 24 months: it is not found.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST show a signed-in patient their upcoming and past appointments with status, grouped per person of the account; in Release 1 the only person is the account holder. (source: FR-015)
- **FR-002**: The system MUST show, for each appointment, clinic, dentist, treatment, date, start time (IST) and status in plain words. (source: FR-015)
- **FR-003**: The system MUST let a patient see only appointments of persons on their own account, and MUST answer "not found" for any other appointment. (source: FR-015)
- **FR-004**: The system MUST offer "Change time" and "Cancel" on an upcoming appointment only while the current time is at least 4 hours before its start, and MUST show the clinic's phone number instead otherwise. (source: FR-016, FR-017)
- **FR-005**: The system MUST enforce the 4-hour rule on the server for every change and cancel request, whatever the screen showed, and MUST return the clinic phone number when it refuses. (source: FR-016, FR-017)
- **FR-006**: The system MUST let a patient cancel an upcoming appointment after an explicit confirmation, setting its status to "cancelled by the patient". (source: FR-017)
- **FR-007**: The system MUST offer, for a reschedule, the free slots of the same clinic and the same treatment with any dentist, within the same booking horizon as a new booking. (source: FR-016)
- **FR-008**: The system MUST let a patient move an upcoming appointment to one of those free slots, keeping clinic, treatment and message channel, and MUST never create an overlap with another active appointment of the dentist. (source: FR-016)
- **FR-009**: When the chosen slot was taken meanwhile, the system MUST leave the original appointment unchanged, tell the patient, and show the next free slots. (source: FR-016)
- **FR-010**: The system MUST make the freed slot bookable by others at once after a cancel or reschedule, with no waiting time. (source: FR-018)
- **FR-011**: The system MUST send the patient a message in the channel chosen for that appointment after a cancel or reschedule, stating clinic, dentist, date and time, and the message MUST NOT delay or undo the change if the provider is down. (source: FR-018)
- **FR-012**: The system MUST withdraw the reminder of a cancelled appointment and, on reschedule, replace it so only a reminder for the new time can exist (reminder timing rules belong to feature 006). (source: FR-018)
- **FR-013**: The system MUST record, in the same step as the change, who made it, when, the old and new status, and for a reschedule the old and new time. (source: FR-017, FR-018)
- **FR-014**: The system MUST ask a repeat no-show policy whether this patient may reschedule, and MUST allow it in Release 1; a refusal shows the clinic phone number. (source: FR-016)
- **FR-015**: A link in a message MUST open the appointment screen after sign-in, and only for the owner. (source: FR-015, FR-016, FR-017)
- **FR-016**: Repeating a cancel or a confirm (double tap, retry) MUST NOT cancel twice, send two messages or write two history rows. (source: FR-017, FR-018)
- **FR-017**: All times MUST be shown in India time and all text MUST be in English; patient screens MUST work on a phone without sideways scrolling and have tap targets of at least 44 px. (source: FR-015)

### Key Entities

- **Appointment**: a visit of one person with one dentist at one clinic for one treatment, with start, end, status (booked, arrived, no-show, cancelled by the patient, cancelled by the clinic) and message channel. Owned by the booking capability (feature 003).
- **Appointment history entry**: one row per change: who, when, old and new status, reason (for example "rescheduled" with old and new time).
- **Person / patient account**: the account holder (and, in Release 2, family members) whose appointments are listed.
- **Change message**: a message to the patient after a cancel or reschedule, in the chosen channel.
- **Free slot**: a bookable time of a dentist at a clinic, offered by the scheduling capability.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A patient can open "My appointments" and reach the appointment screen in 2 taps, and can cancel in 3 taps after opening the appointment (Cancel, Confirm, Done).
- **SC-002**: A patient can reschedule in 5 screens or fewer from "My appointments" (list, appointment, slot picker, confirm, done).
- **SC-003**: After a cancel or reschedule the freed slot appears in other patients' slot lists in under 2 seconds, and in 100% of 100 test runs it can be booked straight away.
- **SC-004**: 100% of cancel and reschedule requests made less than 4 hours before the start are refused, and 100% made earlier succeed (tested at the boundary).
- **SC-005**: In 100% of tests a patient sees no appointment of any person outside their own account.
- **SC-006**: 95% of the list and appointment screens load in under 2 seconds on a 4G phone, and a cancel or reschedule is confirmed in under 3 seconds for 95% of requests.
- **SC-007**: Every cancel or reschedule has exactly one history entry and exactly one message to the patient, including when the request is repeated.

## Assumptions

- Depends on feature 003 (online booking, which creates the appointment table and the booking horizon) and feature 002 (slots, clinics, treatments, clinic phone number). Sign-in and roles come from feature 001; reminder timing from feature 006.
- Q1 (open question): is the 4-hour limit inclusive? Assumed: yes, a change is allowed up to and including exactly 4 hours before the start (open question Q1).
- Q2 (open question): what if the patient opens a message link while signed in as a different patient? Assumed: show "appointment not found" and offer to sign out, never reveal the appointment (open question Q2).
- Q3 (open question): is there a limit on how many times one appointment can be rescheduled? Assumed: no limit in Release 1 (open question Q3).
- The message channel is the one chosen for that appointment at booking (prd.md FR-013); the message text uses an approved template for cancel and for reschedule.
- The reschedule keeps the same treatment and duration; a different treatment or clinic means cancel and book again.
- Family members arrive in Release 2 (prd.md FR-006); this feature only makes the list and access checks per person so that nothing changes then.
- Reception-side change and cancel without the 4-hour rule belong to feature 005 and use the same appointment rules, not these screens.
- Appointment history is kept 24 months, as in the architecture; no clinical data is shown.
