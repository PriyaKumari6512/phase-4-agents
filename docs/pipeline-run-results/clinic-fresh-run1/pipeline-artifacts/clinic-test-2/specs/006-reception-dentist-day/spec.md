# Feature Specification: Reception day view, check-in, no-show and dentist day

**Feature Branch**: `006-reception-dentist-day`

**Created**: 2026-11-16

**Status**: Draft

**Input**: User description: "Reception day view, check-in, no-show and dentist day. Covers prd.md FR-019, FR-020, FR-021, FR-022, FR-023. Personas P-02 Receptionist, P-03 Dentist. Flows 'Reception runs the day' and 'A dentist checks their day'. Screens: day view, appointment panel, book for patient, patient search, my day."

## User Scenarios & Testing *(mandatory)*

Context: BrightSmile Dental runs 2 clinics in Bengaluru with a paper diary per dentist today. This feature gives reception one screen per clinic to run the day, and gives each dentist a read-only view of their own day. Go-live is firm on 1 March 2027 (MVP). Future paper-diary appointments are typed in by reception before go-live through the same booking screens (SA-005; no import; risk RSK-010, dry run in the week before go-live).

Out of scope here (other features): sign-in and accounts (feature 002), hours, leave and free-slot calculation (003), online booking (004), patient self-service and the status history table itself (005), confirmations, reminders, STOP and the "Reminders failed" list (007), the repeat no-show block and lifting it (009).

### User Story 1 - See the day of my clinic (Priority: P1)

A receptionist signs in and sees today's day view for their own clinic: one column per dentist working that day, each appointment showing patient name, phone number, treatment and status. They can move to other days. Opening an appointment shows the appointment panel with the actions that apply.

**Why this priority**: It replaces the paper diary and is the screen every other reception action starts from.

**Independent Test**: Sign in as a receptionist of clinic A with seeded dentists and appointments at clinics A and B. The day view shows only clinic A, one column per dentist working that day, and the day can be changed forward and back.

**Acceptance Scenarios**:

1. **Given** a receptionist of clinic A and three dentists with working hours at clinic A today, **When** they sign in, **Then** they see today's date (IST) with three columns, one per dentist, each listing that dentist's appointments in time order with patient name, phone number, treatment and status. (source: FR-019)
2. **Given** a dentist who works at both clinics today, **When** the receptionist of clinic A opens the day view, **Then** the column shows only that dentist's appointments at clinic A. (source: FR-019)
3. **Given** the day view for today, **When** the receptionist chooses next day, previous day or picks a date, **Then** the view shows that date's columns and appointments for their clinic. (source: FR-019)
4. **Given** a date on which no dentist works at the clinic and no appointment exists (for example a Sunday), **When** the receptionist opens it, **Then** the view says no dentists are working that day. (source: FR-019)
5. **Given** the day view is open, **When** another receptionist books or changes an appointment, **Then** the change appears within about 30 seconds without the receptionist reloading. (source: FR-019)
6. **Given** an appointment in the view, **When** the receptionist selects it, **Then** an appointment panel opens with the details and only the actions that apply to its current status and time. (source: FR-019)

---

### User Story 2 - Mark a patient as arrived (Priority: P1)

When a patient arrives, the receptionist marks the appointment as arrived and the column shows the new status.

**Why this priority**: Check-in is the most frequent action during the day and feeds the no-show numbers.

**Independent Test**: Open a booked appointment of today, mark it arrived, and see the status change and the recorded actor and time.

**Acceptance Scenarios**:

1. **Given** a booked appointment today at the receptionist's clinic, **When** the receptionist marks it arrived, **Then** its status becomes arrived in the day view and the change records the receptionist and the time. (source: FR-021)
2. **Given** an appointment on a future date, **When** the receptionist opens its panel, **Then** "Arrived" is not offered. (source: FR-021)
3. **Given** an appointment already changed by another receptionist (for example cancelled), **When** the receptionist tries to mark it arrived, **Then** the system refuses, says the appointment's current status and refreshes the view. (source: FR-021)
4. **Given** an appointment of the other clinic, **When** the receptionist tries to mark it arrived by any means, **Then** the system refuses and nothing changes. (source: FR-021)

---

### User Story 3 - Mark a no-show and undo it the same day (Priority: P1)

When a patient has not come 15 minutes after the start time, the receptionist marks a no-show. The mark can be set from 15 minutes after the start until the end of that day, and undone the same day.

**Why this priority**: No-shows are the clinic's biggest problem; the status must be recorded reliably and fixable.

**Independent Test**: With an appointment that started 20 minutes ago, mark no-show, then undo; also try at 10 minutes after the start and on the next day.

**Acceptance Scenarios**:

1. **Given** a booked appointment that started 15 minutes ago or more today, **When** the receptionist marks it a no-show, **Then** the status becomes no-show and the change records who and when. (source: FR-022)
2. **Given** a booked appointment that started less than 15 minutes ago, **When** the receptionist opens its panel, **Then** "No-show" is not offered and an attempt through the system is refused with the time from which it is allowed. (source: FR-022)
3. **Given** an appointment marked no-show today, **When** the receptionist chooses undo on the same day, **Then** the status returns to booked and the undo records who and when. (source: FR-022)
4. **Given** an appointment of a day that has ended (after midnight IST), **When** the receptionist tries to mark a no-show or undo one, **Then** the system refuses. (source: FR-022)
5. **Given** an appointment with status arrived, cancelled by the patient or cancelled by the clinic, **When** the receptionist tries to mark it a no-show, **Then** the system refuses. (source: FR-022)

---

### User Story 4 - Find or create a patient (Priority: P1)

A patient phones or walks in. The receptionist finds the patient by phone number or name, or creates one with name and phone number.

**Why this priority**: Every reception-side booking starts from a patient.

**Independent Test**: Search by a phone number and by a name; create a patient with a new phone number; try to create with an existing phone number.

**Acceptance Scenarios**:

1. **Given** existing patients, **When** the receptionist searches by part of a phone number or name, **Then** matching patients are listed with name and phone number only. (source: FR-020)
2. **Given** a patient who has appointments only at the other clinic, **When** the receptionist searches for them, **Then** the patient is found, but no appointment of the other clinic is shown. (source: FR-020)
3. **Given** no match, **When** the receptionist enters a name and a phone number, **Then** a new patient is created and selected for booking. (source: FR-020)
4. **Given** a phone number that already has an account, **When** the receptionist tries to create a patient with it, **Then** the system offers the existing patient instead of creating a duplicate. (source: FR-020)
5. **Given** a missing name or a phone number that is not valid, **When** the receptionist saves, **Then** the system says what to correct and creates nothing. (source: FR-020)

---

### User Story 5 - Book a patient, including long treatments and walk-ins (Priority: P1)

For a selected patient the receptionist books any treatment type, including reception-only types of 60 or 90 minutes, into a free slot of their clinic, with no 4-hour cut-off. A walk-in is booked as a normal appointment and marked arrived.

**Why this priority**: Phone and walk-in booking is how reception works today, and longer treatments can only be booked here. It is also how the paper diary is typed in before go-live.

**Independent Test**: Book a 90-minute treatment for tomorrow and a 30-minute walk-in for the next free slot today; verify both appear in the day view, and that two receptionists booking the same slot cannot both succeed.

**Acceptance Scenarios**:

1. **Given** a selected patient, **When** the receptionist chooses a reception-only treatment type (60 or 90 minutes), a dentist and a free slot long enough, **Then** the appointment is booked at the receptionist's clinic and appears in the dentist's column. (source: FR-020)
2. **Given** a free slot that starts in 2 hours, **When** the receptionist books it, **Then** it is booked, because there is no 4-hour cut-off for reception. (source: FR-020)
3. **Given** a patient who is present and not booked, **When** the receptionist books a free slot as a walk-in, **Then** the appointment is created as a normal appointment and its status is arrived. (source: FR-020)
4. **Given** two receptionists confirm the same slot at once, **When** both submit, **Then** one booking succeeds and the other is told the slot is taken and sees the next free slots. (source: FR-020)
5. **Given** a free slot on a date more than 30 days ahead, **When** the receptionist books it, **Then** the booking is accepted (the 30-day limit applies to online booking only), which also allows typing in the paper diary before go-live. (source: FR-020)
6. **Given** a slot that is not free (break, leave, existing appointment, or too short for the treatment), **When** the receptionist looks for slots, **Then** it is not offered. (source: FR-020)

---

### User Story 6 - Reschedule or cancel for a patient (Priority: P2)

The receptionist moves an appointment of their clinic to another free slot, or cancels it, at any time before it starts or later the same day, with no 4-hour cut-off. A cancel records whether the patient asked or the clinic did.

**Why this priority**: Callers change plans by phone; reception must be able to do it, but it builds on the booking and day view.

**Independent Test**: Move a booked appointment to another dentist's free slot; cancel one as "patient asked" and one as "clinic"; check statuses and that the slots become free.

**Acceptance Scenarios**:

1. **Given** a booked appointment at the receptionist's clinic, **When** they pick another free slot (same clinic, any dentist) and confirm, **Then** the appointment moves, the old slot is free at once, and the change records who and when. (source: FR-020)
2. **Given** an appointment starting in 1 hour, **When** the receptionist reschedules or cancels it, **Then** it is allowed. (source: FR-020)
3. **Given** a cancel, **When** the receptionist states that the patient asked, **Then** the status becomes cancelled by the patient. (source: FR-020)
4. **Given** a cancel, **When** the receptionist states that the clinic cancelled, **Then** the status becomes cancelled by the clinic. (source: FR-020)
5. **Given** a rescheduled or cancelled appointment, **When** the change is saved, **Then** the patient notice and reminder change are requested from messaging (feature 007). (source: FR-020)
6. **Given** an appointment that is arrived or no-show, **When** the receptionist opens its panel, **Then** reschedule and cancel are not offered. (source: FR-020)

---

### User Story 7 - Dentist sees their own day (Priority: P2)

A dentist signs in on a phone or the clinic PC and sees their own appointments for today at each clinic they work at that day, read only: time, patient name, treatment, status.

**Why this priority**: Replaces looking at the paper diary; no other action depends on it.

**Independent Test**: Sign in as a dentist who works at both clinics today and check both clinics' appointments appear, only their own, with no actions.

**Acceptance Scenarios**:

1. **Given** a dentist who works at clinic A in the morning and clinic B in the afternoon today, **When** they sign in, **Then** they see today's appointments grouped by clinic, each with time, patient name, treatment and status. (source: FR-023)
2. **Given** other dentists have appointments today, **When** the dentist opens their day, **Then** none of the other dentists' appointments are shown. (source: FR-023)
3. **Given** the dentist's day, **When** they look for any way to change an appointment, **Then** none exists, and a change request from a dentist account is refused. (source: FR-023)
4. **Given** a dentist with no appointments today, **When** they sign in, **Then** the screen says there are no appointments today. (source: FR-023)
5. **Given** a phone-size screen, **When** the dentist opens their day, **Then** it is readable without sideways scrolling. (source: FR-023)

---

### Edge Cases

- Dentist on leave all day but with already-booked appointments: the dentist still has a column so the appointments can be seen and moved (the system never moves them by itself, FR-008).
- Appointment's end passes while the receptionist has the panel open: allowed actions are checked again when the action is submitted, not only when the panel was drawn.
- Two receptionists change the same appointment at once: the second gets the current status instead of overwriting.
- Day boundary: "same day" and "end of that day" are the calendar date in IST; the 15-minute rule uses the appointment start in IST.
- A patient has two appointments the same day: each is marked independently.
- A newly created patient who later signs in with the same phone number finds the account created at reception, not a second one.
- Receptionist session ends (8 hours or 30 minutes idle): the next action asks them to sign in again and keeps nothing half-saved.
- Appointments typed in before go-live must not send unexpected messages to real patients (see assumption and Q3).
- A deactivated receptionist or dentist account cannot see or change anything from the next request.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: After sign-in a receptionist MUST see today's (IST) day view for their own clinic, and only that clinic. (source: FR-019)
- **FR-002**: The day view MUST show one column per dentist working at that clinic on that date, and also any dentist who has an appointment at that clinic that date. (source: FR-019)
- **FR-003**: Each appointment in a column MUST show start and end time, patient name, phone number, treatment and status, in time order. (source: FR-019)
- **FR-004**: The receptionist MUST be able to move to the previous day, the next day and to a chosen date. (source: FR-019)
- **FR-005**: The day view MUST refresh itself about every 30 seconds and offer a manual refresh, without closing an open appointment panel. (source: FR-019)
- **FR-006**: Selecting an appointment MUST open an appointment panel showing its details and only the actions allowed for its status and time (arrived, no-show, undo no-show, reschedule, cancel). (source: FR-019)
- **FR-007**: A receptionist MUST be able to mark a booked appointment of their clinic, on the day of the appointment, as arrived. (source: FR-021)
- **FR-008**: A receptionist MUST be able to mark a booked appointment as a no-show only from 15 minutes after its start time until the end of that day (IST); at any other time the system MUST refuse and say when it is allowed. (source: FR-022)
- **FR-009**: A receptionist MUST be able to undo a no-show on the same day, which returns the appointment to booked; after that day the system MUST refuse. (source: FR-022)
- **FR-010**: Every status change made on this feature's screens MUST go through the appointments component, record the actor and the time, and be refused when the stored status is no longer the one the receptionist saw. (source: FR-021, FR-022)
- **FR-011**: A receptionist MUST be able to find a patient by phone number or name, searching all patients (not only those of their clinic), with results showing name and phone number only, at least 3 characters required, at most 20 results. (source: FR-020)
- **FR-012**: A receptionist MUST be able to create a patient with a name and a phone number; if the phone number already has an account the system MUST offer the existing patient and not create a duplicate. (source: FR-020)
- **FR-013**: A receptionist MUST be able to book any active treatment type, including reception-only types of 60 or 90 minutes, for a selected patient with a chosen dentist into a free slot of their own clinic that fits the treatment duration. (source: FR-020)
- **FR-014**: Reception-side booking, rescheduling and cancelling MUST NOT apply the 4-hour cut-off or the 30-day booking horizon, and MUST give the same no-overlap guarantee as online booking: a slot is never booked twice, and a conflict tells the receptionist and shows the next free slots. (source: FR-020)
- **FR-015**: A receptionist MUST be able to book a walk-in, which creates a normal appointment with status arrived, recorded as booked and then arrived. (source: FR-020)
- **FR-016**: A receptionist MUST be able to reschedule an appointment of their clinic to another free slot of the same clinic with any dentist, keeping the treatment type. (source: FR-020)
- **FR-017**: A receptionist MUST be able to cancel an appointment of their clinic and MUST state whether the patient asked (status cancelled by the patient) or the clinic cancelled (status cancelled by the clinic); no default is preselected. (source: FR-020)
- **FR-018**: A receptionist MUST NOT be able to see, change, book into or cancel appointments of another clinic; such requests MUST be refused on the server, whatever ids are sent. (source: FR-019, FR-020, FR-021, FR-022)
- **FR-019**: Reception-side booking, reschedule and cancel MUST request the patient confirmation, change notice and reminder updates from messaging (feature 007) in the same way as online changes, and MUST NOT build messaging here. (source: FR-020)
- **FR-020**: A signed-in dentist MUST see their own appointments for today at each clinic they work at that day, grouped by clinic, each with time, patient name, treatment and status, and nothing else about the patient (no phone number). (source: FR-023)
- **FR-021**: The dentist's day MUST be read only: no status change, booking or cancel is possible from a dentist account, and a dentist MUST NOT see other dentists' appointments. (source: FR-023)
- **FR-022**: The dentist's day MUST be usable on a phone and on a desktop browser; the reception screens are designed for a desktop browser. (source: FR-023, FR-019)
- **FR-023**: Patient names, phone numbers and birth years MUST NOT be written to logs; logs carry ids and a correlation id. (source: FR-019, FR-020)

### Key Entities *(include if feature involves data)*

- **Appointment**: one clinic, one dentist, one patient, one treatment type, start and end, status (booked, arrived, no-show, cancelled by the patient, cancelled by the clinic), who booked it. Owned by the appointments component. (source: FR-019, FR-020)
- **Appointment event**: one row per status change or move: from and to status, who, when, reason. Written for every change in this feature. (source: FR-021, FR-022)
- **Patient**: a person with name and, through the account, a phone number; searchable by receptionists across clinics, shown with name and phone only. (source: FR-020)
- **Patient account**: one per phone number; created at reception when a new patient is created. (source: FR-020)
- **Dentist, Clinic, Treatment type**: set up in feature 003; read here for columns, slot length and the reception-only flag. (source: FR-019, FR-020)
- **Staff account**: receptionist (one clinic) or dentist (own appointments); used for scoping. (source: FR-019, FR-023)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After sign-in, a receptionist sees the day view for a full day (6 dentist columns, about 16 appointments each) within 2 seconds on 95% of loads at a reception desktop.
- **SC-002**: A receptionist marks a patient as arrived in 3 clicks or fewer from the day view.
- **SC-003**: A receptionist books a returning patient by phone number into a free slot in under 2 minutes in a usability check with reception staff.
- **SC-004**: 100% of status changes, bookings, moves and cancels made at reception record who and when.
- **SC-005**: In role tests, 0 appointments of another clinic are readable or changeable by a receptionist, and 0 changes are possible from a dentist account, across every operation of this feature.
- **SC-006**: In concurrent booking tests that include reception requests, 0 overlapping active appointments exist for one dentist.
- **SC-007**: In the dry run in the week before go-live, reception types in the paper-diary appointments of both clinics for the following week using these screens, and each day's day view matches the paper diary (risk RSK-010).
- **SC-008**: A dentist sees today's appointments for every clinic they work at in one screen after sign-in, with 100% of their own appointments and none of other dentists'.

## Assumptions

- Q-015 is open: a walk-in is a normal appointment marked arrived and counts in the no-show rate (SA-004, ASM-004; open question Q1).
- Reception screens are used on a desktop browser at the reception desk; they are available 08:00–20:00 Monday to Saturday (NFR-004, delivered by feature 001).
- Sign-in, sessions (8 hours or 30 minutes idle), roles and clinic scoping come from feature 002; here they are only used. The receptionist's clinic comes from their staff account.
- Hours, breaks, leave, treatment types and free-slot calculation come from feature 003; the status values and the history table come from feature 005 (FR-024); messages from feature 007; the repeat no-show block from feature 009 (reception booking is not blocked by it).
- "Arrived" can be set only on the day of the appointment and, once set, cannot be undone in this feature (only no-show has an undo in the PRD; open question Q2).
- "End of that day" is midnight IST at the end of the appointment's calendar date; the PRD does not tie it to the clinic's closing time.
- Cancelled appointments are not drawn in the dentist columns, so their slots look free; their history stays in the appointment history.
- Reception can book any future date (no 30-day horizon), and can book a free slot that started earlier today, which is needed for walk-ins.
- Reschedule at reception keeps the clinic and treatment type and lets the receptionist choose another dentist and time. Changing the treatment type is done by cancelling and booking again.
- A booking made at reception uses the patient's remembered message channel (default SMS); reception does not choose the channel here.
- Creating a patient at reception creates an account for that phone number with the name; the patient finds it when they first sign in with that number (feature 002). Phone numbers are validated as in patient sign-in.
- Search needs at least 3 characters and returns at most 20 patients, to limit bulk reading of patient data; this is our proposal under NFR-006 and ASM-011.
- Appointments typed in before go-live must not send patients unexpected messages; how this is switched is decided with feature 007 (open question Q3 in clarifications).
- The day view load target in SC-001 is our proposal, taken from the NFR-002 slot list target; to confirm with the client.
- The practice manager's own view of a day is not a screen of this feature; the manager's access to both clinics is part of feature 002.
- Dentists see today only; viewing other days is not in the PRD flow and is not built here.
- Only the listed personal data is stored (name, phone number, appointments, treatment type); no clinical data (NFR-007).
