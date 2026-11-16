# Feature Specification: Reception day view, check-in, no-shows and dentist day (MOD-05)

**Feature Branch**: `005-reception-day`

**Created**: 2027-01 (Release 1, deadline DL-1 2027-02-22)

**Status**: Draft

**Input**: User description: "Reception day view, check-in, no-shows and dentist day (MOD-05, Release 1). A receptionist signs in and sees today's day view of their clinic, one column per dentist; marks patients arrived; marks a no-show from 15 minutes after the start until the end of that day and can undo it that day; finds or creates a patient by phone number or name and books, moves or cancels any treatment (including reception-only treatments and walk-ins) without the 4-hour cut-off. A dentist sees their own day at each clinic, read only. Every status change records who and when." Covers FR-019, FR-020, FR-021, FR-022, FR-023, FR-024.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reception sees the day of their clinic (Priority: P1)

A receptionist signs in at the desk PC and lands on today's day view of their own clinic: one column per dentist who works there that day, and in each column the appointments in time order with patient name, phone number, treatment and status. They can move to the previous or next day, or pick a date, and see that day the same way. They never see appointments of another clinic. (source: FR-019, FR-024)

**Why this priority**: Every other reception action (arrive, no-show, book, move, cancel) starts from this screen. Without it reception cannot run the day, and it replaces the paper diary per dentist.

**Independent Test**: Seed one clinic with three dentists working today (one also working at another clinic on another day) and appointments in several statuses. Sign in as that clinic's receptionist, open the day view, step to tomorrow and back, and check the columns, the fields and that the other clinic's appointments are absent.

**Acceptance Scenarios**:

1. **Given** a receptionist of clinic A is signed in and three dentists work at clinic A today, **When** they open the day view, **Then** today's date in India time is shown with exactly three columns, one per dentist, each listing that dentist's appointments in time order. (source: FR-019)
2. **Given** an appointment exists, **When** it appears in the day view, **Then** it shows patient name, phone number, treatment and status, and the status is one of booked, arrived, no-show, cancelled by the patient or cancelled by the clinic. (source: FR-019, FR-024)
3. **Given** a dentist has no working hours at clinic A on the chosen day, **When** the receptionist views that day, **Then** that dentist has no column. (source: FR-019)
4. **Given** the day view of today, **When** the receptionist moves to the next day, the previous day or a chosen date, **Then** the columns and appointments of that day are shown. (source: FR-019)
5. **Given** appointments exist at clinic B, **When** the receptionist of clinic A opens any day or asks for a clinic B appointment directly, **Then** none of clinic B's appointments are shown and a direct request is refused. (source: FR-019, FR-004)

---

### User Story 2 - Reception marks arrived and no-show, and can undo (Priority: P1)

When a patient reaches the desk the receptionist marks the appointment as arrived. When a patient has not come, the receptionist marks the appointment as a no-show, which is allowed from 15 minutes after the start time until the end of that day (India time). A no-show can be undone on the same day, which puts the appointment back to booked. Every status change records who made it and when, so a later question ("who marked this?") has an answer. (source: FR-021, FR-022, FR-024)

**Why this priority**: This is the core of the no-show goal (REQ-002): the no-show data that the block (R2) and the monthly report (R2) count is created here.

**Independent Test**: Create booked appointments starting 5, 20 and 120 minutes ago and one tomorrow. As receptionist mark the first arrived, try a no-show on the first (refused, it is arrived) and on the 5-minute one before and after the 15-minute mark, mark the 20-minute one as no-show then undo it, and read the history of each appointment.

**Acceptance Scenarios**:

1. **Given** a booked appointment of the receptionist's clinic, **When** the receptionist marks the patient as arrived, **Then** the status becomes arrived and the day view shows it. (source: FR-021)
2. **Given** a booked appointment that started 15 minutes ago or more today, **When** the receptionist marks a no-show, **Then** the status becomes no-show. (source: FR-022)
3. **Given** a booked appointment that started less than 15 minutes ago, or has not started yet, **When** the receptionist tries to mark a no-show, **Then** the request is refused with a message that says from which time it is allowed, and the status stays booked. (source: FR-022)
4. **Given** an appointment on an earlier day that is still booked, **When** the receptionist tries to mark a no-show, **Then** the request is refused because the day has ended. (source: FR-022)
5. **Given** an appointment marked no-show today, **When** the receptionist undoes it the same day, **Then** the status returns to booked; **and when** the day has ended, **Then** undo is refused. (source: FR-022)
6. **Given** any status change (arrived, no-show, undo, cancel), **When** it is made, **Then** the change is stored with the previous and new status, the staff member who made it and the time, and that history can be read for the appointment. (source: FR-024)
7. **Given** an appointment that is arrived, no-show or cancelled, **When** a change is attempted that the status rules do not allow (for example marking an arrived patient a no-show, or arriving a cancelled appointment), **Then** it is refused and nothing is changed. (source: FR-024, FR-021, FR-022)
8. **Given** two receptionists act on the same appointment at the same time, **When** both save, **Then** one change is kept, the other is told the appointment was changed and sees the current status. (source: FR-024)

---

### User Story 3 - Reception finds or creates a patient (Priority: P1)

When a patient phones or walks in, the receptionist searches for them by phone number or by name. If the patient is found the receptionist selects them; if not, the receptionist creates the patient with a name and a phone number. Patients are not tied to one clinic, so the search covers all patients, but selecting a patient never shows appointments of another clinic. (source: FR-020)

**Why this priority**: Booking for callers and walk-ins (User Story 4) needs a patient first, and this is the first step of the "patient phones or walks in" flow.

**Independent Test**: Seed patients, one with the same name as another and one booked mainly at the other clinic. As receptionist search by full phone number, by part of a phone number, and by name; create a new patient with name and phone; try to create one with an existing phone number.

**Acceptance Scenarios**:

1. **Given** patients exist, **When** the receptionist enters a phone number or part of one (at least 4 digits), **Then** the matching patients are listed with name and phone number. (source: FR-020)
2. **Given** patients exist, **When** the receptionist enters part of a name (at least 2 letters), **Then** the matching patients are listed with name and phone number, ordered by best match. (source: FR-020)
3. **Given** a patient who has only booked at the other clinic, **When** the receptionist searches for them, **Then** they are found, and no appointment of the other clinic is shown. (source: FR-020, FR-004)
4. **Given** no patient matches, **When** the receptionist enters a name and a phone number and saves, **Then** a patient is created and selected for booking. (source: FR-020)
5. **Given** a phone number that already belongs to a patient account, **When** the receptionist tries to create a patient with that phone number, **Then** the existing patient is offered instead of a duplicate. (source: FR-020)
6. **Given** a missing name, or a phone number that is not a valid Indian mobile number, **When** the receptionist saves, **Then** the form shows what must be corrected and nothing is created. (source: FR-020)

---

### User Story 4 - Reception books, moves and cancels for patients (Priority: P1)

For the selected patient the receptionist books any treatment type, including the reception-only 60 and 90 minute types, with a dentist of their clinic in a free slot. This also covers a walk-in: the patient is booked into a free slot and marked arrived straight away. The receptionist can move an appointment to another free slot (or another dentist) and cancel an appointment. None of this has the 4-hour cut-off that applies to patients online. When cancelling, the receptionist says whether the patient asked (status "cancelled by the patient") or the clinic cancelled (status "cancelled by the clinic"). Future appointments from the paper diary are typed in this way before go-live, with no import. (source: FR-020, FR-021, FR-024)

**Why this priority**: Phone and walk-in booking is how most appointments are made on go-live day, and reception-only treatments can be booked nowhere else.

**Independent Test**: As receptionist, book a patient for a 90-minute reception-only treatment in a free slot 1 hour from now, book a walk-in into the current slot and see it arrived, move the first appointment to another dentist, try to book an overlapping slot, cancel one as "patient asked" and one as "clinic cancelled", and check statuses, the day view and the history.

**Acceptance Scenarios**:

1. **Given** a selected patient, **When** the receptionist picks any active treatment type (online or reception-only), a dentist of their clinic and a free slot and confirms, **Then** the appointment is booked in the clinic for that dentist and appears at once in the day view. (source: FR-020)
2. **Given** a slot starts in less than 4 hours, **When** the receptionist books, moves or cancels an appointment in it, **Then** the action is allowed, because reception has no 4-hour cut-off. (source: FR-020)
3. **Given** a patient who walks in, **When** the receptionist books a free slot and chooses "walk-in", **Then** a normal appointment is created with status arrived and it counts like any other appointment. (source: FR-020, FR-021, FR-024)
4. **Given** the slot is taken by another booking while the receptionist is choosing, **When** they confirm, **Then** nothing is double booked, they are told the slot is taken and are shown the next free slots. (source: FR-020)
5. **Given** a booked appointment, **When** the receptionist moves it to another free slot of the same or another dentist at their clinic, **Then** the old slot is free at once, the appointment keeps its patient and treatment, and the move is recorded in the history. (source: FR-020, FR-024)
6. **Given** a booked appointment, **When** the receptionist cancels it and states that the patient asked, **Then** the status becomes cancelled by the patient; **and when** the clinic cancelled, **Then** the status becomes cancelled by the clinic. In both cases the slot is free at once. (source: FR-020, FR-024)
7. **Given** a booking, move or cancel by reception, **When** it is saved, **Then** the patient gets the confirmation or change message in their channel, as delivered by the messages feature (006); a failure to send does not undo the booking. (source: FR-020)
8. **Given** the appointment belongs to the other clinic, **When** the receptionist tries to move or cancel it, **Then** it is refused. (source: FR-020, FR-004)
9. **Given** a typed-in future appointment before go-live (paper diary), **When** the receptionist books it, **Then** it works the same as any booking, so the dry run in the week before go-live can use these screens. (source: FR-020)

---

### User Story 5 - Dentist sees their own day, read only (Priority: P2)

A dentist signs in on a phone or the clinic PC and sees today's appointments at each clinic where they work today: time, patient name, treatment and status. The screen is read only: no arrive, no-show, book, move or cancel. The dentist can move to other days. They never see other dentists' appointments. (source: FR-023)

**Why this priority**: Valuable and simple, but reception can run the day without it, so it follows the reception stories.

**Independent Test**: Seed a dentist working at both clinics on one day and another dentist at one clinic. Sign in as the first dentist and check that both clinics are shown with only their own appointments, that no action is offered, and that action requests are refused.

**Acceptance Scenarios**:

1. **Given** a dentist works at clinic A in the morning and clinic B in the afternoon today, **When** they open "my day", **Then** the appointments of both clinics are shown, grouped by clinic, in time order. (source: FR-023)
2. **Given** an appointment, **When** it is shown, **Then** it has time, patient name, treatment and status, and no change action is offered. (source: FR-023)
3. **Given** a dentist signed in, **When** they try to change an appointment or to read another dentist's day, **Then** the request is refused. (source: FR-023, FR-004)
4. **Given** a phone-sized screen, **When** the dentist opens "my day", **Then** it is readable without sideways scrolling. (source: FR-023)

---

### Edge Cases

- A receptionist of clinic A requests a day view or appointment of clinic B: refused; search by phone or name still finds the patient (ASM-011).
- The receptionist marks a no-show at 14 minutes after start: refused; at exactly 15 minutes: allowed. Time is India time; "end of that day" is 23:59:59 IST.
- Marking no-show or undo is attempted after midnight India time for an appointment of the previous day: refused.
- An appointment is cancelled: it can no longer be marked arrived or no-show and shows in the day view as cancelled.
- A dentist's leave starts after appointments were booked (feature 002 lists them): reception moves them here; the system never moves them by itself.
- A phone number typed with a country code or spaces matches the same patient as one typed plain.
- Two patients with the same name: both are listed with their phone numbers so reception can tell them apart.
- A day with no dentists working at the clinic: the day view says so and still lets reception move to other days.
- A reception booking that overlaps another active appointment of the same dentist is refused by the same no-overlap rule that protects online booking.
- Sunday (clinic closed) shows no columns unless a dentist has hours that day.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST show a signed-in receptionist the day view of their own clinic for a chosen date (default today, India time): one column per dentist who works at that clinic that day, each listing the dentist's appointments in time order with patient name, phone number, treatment and status. (source: FR-019)
- **FR-002**: The system MUST let the receptionist move to the previous day, the next day or a chosen date, and MUST show only appointments of the receptionist's own clinic. (source: FR-019, FR-004)
- **FR-003**: The system MUST let a receptionist find a patient by phone number (full or part, at least 4 digits) or by name (part, at least 2 letters) across all patients, showing name and phone number only, and MUST let them create a patient with a name and a phone number. A phone number that already exists MUST offer the existing patient instead of creating a duplicate. (source: FR-020; ASM-011)
- **FR-004**: The system MUST let a receptionist book an appointment for a patient with any active treatment type, including reception-only types of 60 or 90 minutes, with a dentist of their clinic in a free slot, with no 4-hour cut-off, and MUST never allow two active appointments of one dentist to overlap. (source: FR-020)
- **FR-005**: The system MUST let a receptionist book a walk-in as a normal appointment that is created with status arrived. (source: FR-020, FR-021; SA-004, ASM-004)
- **FR-006**: The system MUST let a receptionist move a booked appointment of their clinic to another free slot, with the same or another dentist of that clinic, and cancel it, with no 4-hour cut-off. A cancel MUST record "cancelled by the patient" when the receptionist says the patient asked and "cancelled by the clinic" otherwise. (source: FR-020; ASM-014)
- **FR-007**: The system MUST make a slot freed by a move or cancel bookable at once, and MUST request the confirmation or change message for the patient through the messages feature (006) after a reception booking, move or cancel; a failure to send MUST NOT undo the change. (source: FR-020)
- **FR-008**: The system MUST let a receptionist mark a booked appointment of their clinic as arrived, and MUST refuse it for cancelled and no-show appointments. (source: FR-021)
- **FR-009**: The system MUST let a receptionist mark a booked appointment of their clinic as a no-show only from 15 minutes after its start time until the end of that day (India time), and MUST refuse it before that time, after that day, and for any status other than booked. (source: FR-022)
- **FR-010**: The system MUST let a receptionist undo a no-show on the same day, returning the appointment to booked, and MUST refuse the undo after the day has ended. (source: FR-022)
- **FR-011**: The system MUST let a receptionist return an arrived appointment to booked on the same day, to correct a mistaken click. Assumed: this is allowed (open question Q2). (source: FR-021, FR-024)
- **FR-012**: The system MUST give every appointment exactly one status of booked, arrived, no-show, cancelled by the patient or cancelled by the clinic, and MUST allow only these changes: booked to arrived, booked to no-show, no-show to booked (same day), arrived to booked (same day), booked to either cancelled status; cancelled statuses are final. (source: FR-024)
- **FR-013**: The system MUST record for every status change (including booking, move and cancel by reception) the previous status, the new status, who made it and when, and MUST let authorised staff of the clinic read that history for an appointment. (source: FR-024)
- **FR-014**: The system MUST show a signed-in dentist their own appointments for a chosen date (default today) at each clinic where they work that day, read only, with time, patient name, treatment and status, and MUST refuse any change or any read of another dentist's day. (source: FR-023, FR-004)
- **FR-015**: The system MUST refuse any action on an appointment of another clinic by a receptionist and MUST handle two simultaneous changes to one appointment so that exactly one is kept and the other user is told. (source: FR-004, FR-024)
- **FR-016**: The system MUST make the reception screens usable in a desktop browser and the dentist's day usable on a phone and on a PC. (source: FR-019, FR-023; NFR-001)

### Key Entities *(include if feature involves data)*

- **Appointment**: a booking of one patient with one dentist at one clinic for a treatment, with start, end and status (booked, arrived, no-show, cancelled by the patient, cancelled by the clinic), and who booked it (reception or patient). Owned by the booking capability; created by feature 003.
- **Appointment history entry**: one record per status change with previous status, new status, the staff member or patient who made it, the time and an optional reason (for example "walk-in" or "patient asked"). Table created by feature 003; this feature writes every reception change to it.
- **Patient**: a person with name and phone number; searchable by receptionists across clinics; created by reception with name and phone.
- **Dentist day (view)**: the dentist's appointments for one date, grouped by clinic.
- **Day view (view)**: the appointments of one clinic for one date, grouped by dentist.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A receptionist sees a clinic's full day (up to 6 dentists, about 16 appointments each) in under 2 seconds for 95% of loads on a normal office connection.
- **SC-002**: A receptionist can find or create a patient and book a treatment for them in under 2 minutes, in a first-time trial with the practice's reception staff.
- **SC-003**: Marking arrived or a no-show takes at most 2 actions from the day view (open the appointment, choose the action).
- **SC-004**: 100% of status changes made in tests have a history entry that names who made the change and when.
- **SC-005**: In tests, 0 appointments of the other clinic are visible or changeable to a receptionist, and 0 appointments of another dentist are visible to a dentist.
- **SC-006**: In 1,000 simultaneous attempts to book the same slot from reception and online, exactly one succeeds and no two active appointments of one dentist overlap.
- **SC-007**: The reception screens are available 99.5% of the hours 08:00 to 20:00 Monday to Saturday in a month.
- **SC-008**: In the dry run the week before go-live, reception types the paper-diary appointments of a full week for both clinics and finds no booking that cannot be entered.

## Assumptions

- Dependencies: sign-in, roles and clinic scoping (feature 001), clinics, dentists, working hours, treatment types and free slots (feature 002), the appointment table, the no-overlap rule and the history table (feature 003), the confirmation and change messages (feature 006). This feature builds the reception-side operations and the status transitions on top of them.
- A walk-in is a normal appointment marked arrived and counts in the no-show rate (SA-004, ASM-004). Q-015 stays open; see clarifications.md Q1.
- A receptionist may search all patients by phone or name, because a patient is not tied to one clinic, but sees appointments of their own clinic only (ASM-011).
- A reception cancel records "cancelled by the patient" when the patient asked, otherwise "cancelled by the clinic"; the no-show rate excludes both (ASM-014).
- Reception may book any free slot of today, including one that has already started (a walk-in), but not a slot on a day that has passed.
- Reception may use any active dentist of their clinic who has a free slot; a dentist who works at two clinics shows only at the clinic where they work that day.
- Future paper-diary appointments are typed in by reception before go-live, with no import (SA-005, REQ-030); a dry run is done the week before go-live.
- All times are India time (IST); the day view is for desktop browsers and the dentist's day works on phone and PC.
- Reception screens are available 08:00 to 20:00 Monday to Saturday; the day view of 6 columns is about 15 KB.
- Blocked-patient display and lifting (FR-026) and the list of failed reminders (FR-033) belong to other features and are not built here.
- Open question Q2 (undo of "arrived") is assumed allowed on the same day, see clarifications.md.
