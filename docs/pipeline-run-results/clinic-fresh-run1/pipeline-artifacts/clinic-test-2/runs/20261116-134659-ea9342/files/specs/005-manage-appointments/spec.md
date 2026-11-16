# Feature Specification: Patient appointment list, reschedule, cancel and status history

**Feature Branch**: `005-manage-appointments`

**Created**: 2026-11-10

**Status**: Draft

**Input**: User description: "Patient appointment list, reschedule, cancel and status history. Covers prd.md FR-015, FR-016, FR-017, FR-018, FR-024. Persona P-01 Patient. Flow 'A patient reschedules or cancels'. Go-live firm 1 March 2027 (MVP)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See my upcoming and past appointments (Priority: P1)

A signed-in patient opens "My appointments" and sees every upcoming appointment and every past appointment, each with clinic, dentist, treatment, date, time (IST) and its status (booked, arrived, no-show, cancelled by the patient, cancelled by the clinic). The list is built per account, so when family members exist (feature 008, Release 2) their appointments appear for the account holder, each naming the person it is for. Opening one appointment shows its detail screen with the buttons or the phone number described in the cancel and reschedule stories. (source: FR-015, FR-024)

**Why this priority**: Every other action starts from this list; patients cannot manage a visit they cannot find. Must for the 1 March 2027 MVP.

**Independent Test**: Seed an account with upcoming, past, cancelled and no-show appointments (and a second person on the same account); sign in and open "My appointments". Delivers value alone: a patient can check their visits and statuses without phoning.

**Acceptance Scenarios**:

1. **Given** a signed-in patient with two upcoming and three past appointments, **When** they open "My appointments", **Then** the upcoming ones are listed soonest first and the past ones most recent first, each with clinic, dentist, treatment, date, time in IST and status.
2. **Given** an account that also holds appointments for another person on the same account, **When** the account holder opens the list, **Then** those appointments appear too and each shows the name of the person it is for.
3. **Given** another patient's appointment exists, **When** the signed-in patient requests the list or opens that appointment by its identifier, **Then** it is not shown and the request is refused as not found.
4. **Given** a patient with no appointments, **When** they open the list, **Then** a plain message says there are none and offers "Book".
5. **Given** an appointment cancelled by the clinic, **When** the patient views the list, **Then** it appears in the past/cancelled part with the status "cancelled by the clinic".

---

### User Story 2 - Every status change records who and when (Priority: P1)

Each appointment has a status: booked, arrived, no-show, cancelled by the patient or cancelled by the clinic. Every change of status, and every reschedule, writes a history entry with the old and new status, who made it (the patient, or a named staff member), when, and a reason. Cancels or moves made at reception (feature 006) use the same recording: a reception cancel is recorded as "cancelled by the patient" when the patient asked, otherwise "cancelled by the clinic". Only the five statuses are accepted. (source: FR-024)

**Why this priority**: Without it a patient can deny "I never cancelled" and the cancel and reschedule stories cannot be trusted; it is built first so they can use it.

**Independent Test**: Through the shared status operation, cancel as the patient, cancel by reception (patient asked and not asked) and mark arrived and no-show; read the history of each appointment and check actor, time, from and to status, reason; try an invalid status and see it refused.

**Acceptance Scenarios**:

1. **Given** a booked appointment, **When** the patient cancels it, **Then** a history entry exists with from status "booked", to status "cancelled by the patient", the patient as actor, the time of the change and the reason "patient request".
2. **Given** a booked appointment, **When** a patient reschedules it, **Then** a history entry records the old and new time and dentist, with status booked before and after, the patient as actor and the time.
3. **Given** a receptionist cancels at a patient's request, **When** the change is saved through the shared status operation, **Then** the new status is "cancelled by the patient" and the actor is the receptionist; when the clinic itself cancels it is "cancelled by the clinic".
4. **Given** any code path tries to write a status outside the five allowed values, **When** it is saved, **Then** the data store refuses it.
5. **Given** a status change fails, **When** the transaction ends, **Then** neither the new status nor a history entry is stored (both or neither).
6. **Given** history older than 24 months, **When** the retention job runs, **Then** history is removed on the same schedule as its appointment's personal link.

---

### User Story 3 - Cancel an upcoming appointment (Priority: P1)

From the appointment screen a patient taps "Cancel", confirms, and sees a "done" screen. The slot is free for other patients at once and the patient gets a message in their chosen channel. Less than 4 hours before the start, the Cancel and Change time buttons are replaced by the clinic's phone number. (source: FR-017, FR-018, FR-024)

**Why this priority**: Frees chairs for other patients, which supports the goal of fewer empty slots; firm MVP.

**Independent Test**: Cancel one booked appointment more than 4 hours ahead and one less than 4 hours ahead (clock controlled in test). The first becomes cancelled by the patient, its slot is bookable, a message is queued; the second shows the phone number and the cancel request is refused.

**Acceptance Scenarios**:

1. **Given** a booked appointment starting in more than 4 hours, **When** the patient taps "Cancel" and confirms, **Then** the status becomes "cancelled by the patient", the done screen is shown, and the slot appears again in the free slots straight away.
2. **Given** a successful cancel, **When** it is saved, **Then** the patient receives a cancellation message in the channel chosen for that appointment, and no reminder is sent for it.
3. **Given** a booked appointment starting in less than 4 hours, **When** the patient opens it, **Then** no Cancel or Change time button is shown and the clinic's phone number is shown instead.
4. **Given** the patient kept the screen open past the cut-off, **When** they confirm a cancel less than 4 hours before the start, **Then** the request is refused, nothing changes, and the clinic's phone number is shown.
5. **Given** an appointment that is already cancelled, arrived or no-show, **When** the patient opens it, **Then** no Cancel or Change time button is shown.
6. **Given** the patient taps Cancel twice, or sends the request again after a slow network, **When** the second request arrives, **Then** the appointment is cancelled once, one message is created and the patient sees the same result.

---

### User Story 4 - Reschedule an upcoming appointment (Priority: P1)

A patient taps "Change time" on an upcoming appointment, sees free slots at the same clinic for the same treatment with any dentist, picks one and confirms. The appointment moves to the new slot, the old slot is free at once, and the patient gets a message in their chosen channel. Not allowed less than 4 hours before the original start. A patient who is blocked by the repeat no-show rule (feature 009, Release 2) cannot reschedule online; until that feature exists the block check always answers "not blocked". (source: FR-016, FR-018, FR-024, FR-025)

**Why this priority**: Rescheduling keeps the visit rather than losing it; firm MVP.

**Independent Test**: Reschedule a booked appointment to another dentist's free slot at the same clinic; verify one appointment holds the new slot, the old slot is free, a history row exists and a message is queued. Repeat with the slot taken meanwhile and with the policy answering "blocked".

**Acceptance Scenarios**:

1. **Given** a booked appointment starting in more than 4 hours, **When** the patient taps "Change time", **Then** the slot picker shows free slots at the same clinic for the same treatment, for any dentist working there, and no other clinic or treatment.
2. **Given** the patient picks a free slot and confirms, **When** the change is saved, **Then** the same appointment now has the new time and dentist, its status stays "booked", the done screen shows the new details, and the old slot is bookable at once.
3. **Given** a successful reschedule, **When** it is saved, **Then** the patient receives a message in the chosen channel with the new details, the reminder for the old time is withdrawn and a reminder exists for the new time only (by feature 007).
4. **Given** two people confirm the same slot at once, **When** the second confirm arrives, **Then** it is refused with a "slot just taken" answer, the patient's original appointment is untouched, and the next free slots are shown.
5. **Given** an appointment starting in less than 4 hours, **When** the patient asks to reschedule, **Then** the request is refused and the clinic's phone number is shown.
6. **Given** the no-show policy answers "blocked" for this patient, **When** they try to reschedule, **Then** the request is refused with a message to phone the clinic, and their existing booking stays booked.
7. **Given** the reschedule cannot be completed (for example the message cannot be created), **When** the error occurs, **Then** the appointment stays at its old time and nothing is half-saved.
8. **Given** the patient picks the slot they already hold, **When** they confirm, **Then** nothing changes and the patient is told it is the same time.

---

### User Story 5 - Open my appointment from the message link (Priority: P2)

A patient taps the link in a confirmation or reminder message. If not signed in they sign in with the phone code, then land on that appointment's screen. They can only open it if it belongs to their account; the link carries no authority by itself. (source: FR-015, FR-016, FR-017)

**Why this priority**: Most patients will arrive from a message, but "My appointments" already covers the same actions, so this follows the P1 stories.

**Independent Test**: Open the link signed out, sign in as the owner and land on the appointment; repeat as a different patient and get "not found".

**Acceptance Scenarios**:

1. **Given** a signed-out patient opens an appointment link, **When** they finish sign-in, **Then** they are taken to that appointment and not to the home page.
2. **Given** a signed-in patient opens a link to an appointment on their account, **When** the page loads, **Then** the appointment screen shows with the buttons or phone number that apply.
3. **Given** a signed-in patient opens a link to an appointment on another account, **When** the page loads, **Then** nothing about it is shown and the answer is "not found".
4. **Given** a link for an appointment that is cancelled or in the past, **When** the owner opens it, **Then** the appointment is shown read only with its status.

---

### Edge Cases

- A patient opens the appointment at 3 h 59 min before the start and taps a button at 3 h 58 min: the cut-off is checked on the server at the moment of the request; the request is refused and the phone number shown.
- Exactly 4 hours before the start: allowed ("until 4 hours before its start" includes that moment).
- Reschedule to a slot that was taken while choosing: refused, original kept, next free slots shown.
- Cancel and reschedule requested at the same time for one appointment: one wins, the other is refused because the appointment is no longer in the state it needed.
- Reception cancels while the patient is on the cancel screen: the patient's request is refused as already cancelled.
- Patient has stopped reminders (STOP): change and cancel messages are still sent, because they are confirmations of a change (feature 007 rule, prd FR-031).
- Messaging provider is down: the cancel or reschedule still succeeds; the message waits and is sent after commit by the dispatcher.
- Times are stored in UTC and always shown in IST, also across a day boundary.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST show a signed-in patient the upcoming and past appointments on their account, including those for family members when feature 008 exists, each with clinic, dentist, treatment, date, time in IST, the person it is for and its status. (source: FR-015)
- **FR-002**: The system MUST show only appointments that belong to the signed-in patient's account; the owner is taken from the sign-in session, never from an identifier in the request. (source: FR-015, FR-004)
- **FR-003**: The system MUST let a patient reschedule an upcoming appointment with status booked to another free slot at the same clinic and for the same treatment, with any dentist, until 4 hours before its start. (source: FR-016)
- **FR-004**: The system MUST let a patient cancel an upcoming appointment with status booked until 4 hours before its start. (source: FR-017)
- **FR-005**: The system MUST check the 4-hour cut-off on the server at the time of each cancel or reschedule request, using the original start time, and refuse the request after the cut-off. (source: FR-016, FR-017)
- **FR-006**: Inside 4 hours of the start, the appointment screen MUST show the clinic's phone number instead of the Cancel and Change time buttons. (source: FR-017)
- **FR-007**: The system MUST make the slot freed by a cancel or reschedule bookable at once, in the same step in which the change is saved. (source: FR-018)
- **FR-008**: The system MUST create a message to the patient in the channel chosen for the appointment for every successful cancel or reschedule, in the same transaction as the change, and send it only after the change is committed. (source: FR-018)
- **FR-009**: A reschedule MUST never produce two active appointments for one dentist at overlapping times; if the chosen slot is taken, the system MUST refuse, keep the original appointment and show the next free slots. (source: FR-016, FR-018)
- **FR-010**: A reschedule MUST change the appointment, add its history entry and change its reminder (withdraw the old, create one for the new time only, per feature 007) as one atomic step. (source: FR-016, FR-018)
- **FR-011**: Before accepting a reschedule the system MUST ask the no-show policy whether the patient is blocked, and refuse with a message to phone the clinic if so; until feature 009 exists the policy answers "not blocked". Cancel and existing bookings are never blocked. (source: FR-016, FR-025)
- **FR-012**: An appointment's status MUST be one of booked, arrived, no-show, cancelled by the patient, cancelled by the clinic, and the data store MUST refuse any other value. (source: FR-024)
- **FR-013**: Every status change and every reschedule MUST record a history entry with the appointment, from and to status, who made it, when, and a reason; the entry and the change succeed or fail together. (source: FR-024)
- **FR-014**: The shared status-change operation MUST also serve reception and the reception-only flows of feature 006: a reception cancel is recorded as "cancelled by the patient" when the patient asked and otherwise as "cancelled by the clinic"; the 4-hour rule applies to online patients only. (source: FR-024, FR-020)
- **FR-015**: History MUST be kept for the same period as its appointment (24 months). (source: FR-024)
- **FR-016**: The system MUST open an appointment from the link in a confirmation or reminder message after the patient signs in, and return "not found" to anyone but the owner. (source: FR-015, FR-004)
- **FR-017**: Repeating a cancel or reschedule request MUST NOT cancel or move twice nor create a second message. (source: FR-017, FR-018)
- **FR-018**: All screens and messages MUST be in English with times in IST, and patient screens MUST work on a phone without sideways scrolling and with tap targets of at least 44 px. (source: FR-015, FR-016, FR-017)
- **FR-019**: Logs and metrics for these operations MUST NOT contain patient name, phone number or birth year; they carry identifiers only. (source: FR-024)

### Key Entities *(include if feature involves data)*

- **Appointment**: one visit of one person at one clinic with one dentist for one treatment, with start, end, status, message channel and who booked it. Owned by the appointments component; kept 24 months, then the personal link is removed.
- **Appointment history entry**: one change to an appointment: from and to status, actor (patient or named staff member), time, reason. Kept as long as its appointment.
- **Patient account and person**: the account holder and, from Release 2, family members. The list is built by account.
- **Message**: the cancel or reschedule notice, created by the messaging component in the same step as the change.
- **Clinic**: supplies the phone number shown inside the 4-hour window.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A patient can cancel an appointment in 3 taps or fewer from the appointment screen, and reschedule in 5 screens or fewer after sign-in.
- **SC-002**: 100% of cancel and reschedule requests made less than 4 hours before the start are refused, and 100% of those made at 4 hours or more before are accepted, in automated boundary tests.
- **SC-003**: After a cancel or reschedule, the freed slot is offered to the next patient in the very next slot request (0 seconds of delay) in 100% of test runs.
- **SC-004**: 0 overlapping active appointments for one dentist after 1,000 concurrent reschedule and booking attempts.
- **SC-005**: 100% of status changes have a history entry with actor and time; 0 appointments hold a status outside the five allowed.
- **SC-006**: 0 cross-patient reads of the list or of one appointment in role tests.
- **SC-007**: The appointment list and the slot picker for a change load within 2 seconds for 95% of requests on a 4G phone; a cancel or reschedule completes within 3 seconds for 95% of requests.
- **SC-008**: 100% of successful cancels and reschedules lead to one message in the chosen channel within the normal confirmation time (about 30 seconds).

## Assumptions

- Assumed: the slot picker for a change offers only slots inside the same booking horizon as online booking (today and the next 30 days) and starting in the future (open question Q1).
- Assumed: the cancel or reschedule message goes in the channel chosen for that appointment (SMS by default, from booking); the patient cannot change channel on these screens (open question Q2).
- Assumed: a reschedule to a new slot that starts less than 4 hours from now is allowed, because the 4-hour rule is stated only against the original start (open question Q3).
- The same appointment record is moved on a reschedule (it keeps its identifier and link); its history shows the old and new time.
- The 4-hour cut-off is evaluated against the actual start time in UTC; the clinic phone number comes from the clinic record held by the clinics and schedules component.
- Reception-side booking, moving and cancelling (feature 006), the arrived and no-show screens (feature 006), the reminder rules (feature 007), family members (feature 008) and the no-show block (feature 009) are other features; this feature supplies or calls the operations they share and must work without them.
- Patients sign in with the phone code (prd FR-002, owned by the identity component) and use the confirmation and reminder links created by feature 007; this feature owns only the page that links open. Assumed: the sign-in screen can send the patient on to a given same-site path after sign-in.
- Session, role and ownership checks come from the identity component; the token owner is the only authority for access.
- Appointments and history are kept 24 months (ASM-012), then personal data is anonymised.
- Only English and IST; no payment, refunds or deposits on cancel; no waiting list.
