# Feature Specification: Repeat no-show block

**Feature Branch**: `008-noshow-block`

**Created**: 2026-11-13

**Status**: Draft

**Input**: User description: "Repeat no-show block (MOD-06, Release 2, DL-2 2027-03-19, not hard). A patient with 2 no-shows in the last 6 months cannot book or reschedule online; the page says to phone the clinic. Existing bookings stay. Family members' no-shows count against the person who had them (PD-007). Reception sees that a patient is blocked and can lift the block; lifting starts the count again from zero." (source: FR-025, FR-026, PD-007)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A repeat no-show patient cannot book or reschedule online (Priority: P1)

A patient (or a family member the patient books for) who has had 2 no-shows in the last 6 months is blocked from booking a new appointment online and from rescheduling an appointment online. Where they would book or change a time, the page tells them online booking is not available and shows the phone number of the clinic they were using. Appointments they already hold stay as they are. The count is kept per person: a family member's no-show counts against that family member, not against the account holder. Reception booking is never blocked. (source: FR-025, PD-007)

**Why this priority**: This is the point of the feature: repeat no-shows lose online booking so the chair is not left empty again and again. Without it nothing else in the feature has value.

**Independent Test**: Mark two no-shows for one patient inside 6 months, then try to book and to reschedule online as that patient: both are refused with the clinic phone number; the patient's existing future appointment is unchanged; the same attempt for the account holder (who has no no-shows) succeeds; a receptionist can still book that patient.

**Acceptance Scenarios**:

1. **Given** a patient has 2 no-shows within the last 6 months, **When** they reach the slot-choosing step of online booking for a clinic, **Then** the page says online booking is not available and shows that clinic's phone number, and no slot can be confirmed.
2. **Given** a patient has 2 no-shows within the last 6 months and an upcoming appointment, **When** they try to reschedule it online, **Then** the change is refused, the page says to phone the clinic and shows the clinic's phone number, and the appointment keeps its original time and status.
3. **Given** a blocked patient has other upcoming appointments, **When** they open their appointment list, **Then** all those appointments are still listed as booked and can still be cancelled online within the normal cancel rule.
4. **Given** a family member has 2 no-shows and the account holder has none, **When** the account holder books for themselves, **Then** the booking succeeds; **and When** they book for the family member, **Then** it is refused with the phone-the-clinic message.
5. **Given** a patient has only 1 no-show in the last 6 months, or has 2 no-shows of which one is older than 6 months, **When** they book or reschedule online, **Then** it succeeds.
6. **Given** a patient is blocked, **When** a receptionist books or reschedules an appointment for them, **Then** it succeeds with no block check.
7. **Given** a patient whose 2 counted no-shows were the only reason for the block, **When** the older of the two passes 6 months of age, **Then** the next online booking attempt succeeds without any staff action.

---

### User Story 2 - Reception sees who is blocked (Priority: P2)

A receptionist sees at a glance that a patient is blocked from online booking: on the appointment in the day view and appointment panel, and in patient search results. The panel shows since when the patient is blocked and the dates of the no-shows that count. A patient who is not blocked shows nothing extra. (source: FR-026, PD-007)

**Why this priority**: Reception is the only place the block can be resolved; they must see it before they can decide to lift it. It depends on Story 1's block existing.

**Independent Test**: Block a patient (two no-shows), open the day view, appointment panel and patient search as a receptionist: a "Blocked" marker and the block details show for that patient only, including a family member shown by their own name.

**Acceptance Scenarios**:

1. **Given** a blocked patient has an appointment in the clinic's day view, **When** the receptionist opens the day view, **Then** that appointment shows a "Blocked from online booking" marker.
2. **Given** a blocked patient, **When** the receptionist opens the appointment panel or finds the patient by phone number or name in patient search, **Then** the blocked state, the date the block started and the counted no-show dates are shown.
3. **Given** a patient that is not blocked, **When** the receptionist views the same screens, **Then** no blocked marker is shown.
4. **Given** a family member is blocked but the account holder is not, **When** the receptionist searches by the shared phone number, **Then** only the family member's entry shows the blocked marker.
5. **Given** the feature is switched off for the release, **When** a receptionist opens any screen, **Then** no blocked marker or lift control appears.

---

### User Story 3 - Reception lifts a block and the count restarts (Priority: P2)

When a blocked patient phones and the clinic agrees, the receptionist lifts the block. The patient can book and reschedule online straight away. The count starts again from zero at the moment of the lift: only no-shows after that moment count towards a new block. The lift records who did it and when. (source: FR-026)

**Why this priority**: Gives the clinic a fair way out of the block (Reception flow step 6). Needs Stories 1 and 2.

**Independent Test**: Block a patient, lift the block as a receptionist, confirm the patient can book online at once, then mark one no-show (still not blocked) and a second (blocked again); the earlier two no-shows are never counted again.

**Acceptance Scenarios**:

1. **Given** a blocked patient, **When** the receptionist chooses "Lift block" and confirms, **Then** the blocked marker disappears and the lift is recorded with the receptionist's name and the time.
2. **Given** a block has just been lifted, **When** the patient books or reschedules online, **Then** it succeeds.
3. **Given** a block was lifted, **When** the patient then gets 1 new no-show, **Then** they are not blocked; **and When** they get a second new no-show, **Then** they are blocked again.
4. **Given** a patient is not blocked, **When** a receptionist looks at the patient, **Then** no lift control is offered, and a direct lift request is refused.
5. **Given** a user who is not a receptionist (a patient, a dentist), **When** they try to lift a block, **Then** it is refused.

---

### User Story 4 - The block follows no-show corrections (Priority: P2)

When a receptionist marks a no-show or undoes one (allowed the same day, PD-003), the patient's block state is recalculated at once. Marking the second no-show blocks the patient; undoing a no-show that caused a block removes the block. (source: FR-025, FR-026, PD-007)

**Why this priority**: Without it, a mistaken no-show (undone the same day) would leave a patient wrongly blocked, which would harm patients and trust. It builds on Story 1.

**Independent Test**: Mark a second no-show for a patient with one earlier no-show: the patient becomes blocked immediately. Undo that no-show the same day: the patient is unblocked and can book online.

**Acceptance Scenarios**:

1. **Given** a patient has 1 no-show in the last 6 months, **When** a receptionist marks a second no-show for them, **Then** the patient is blocked from online booking immediately.
2. **Given** a patient was blocked by their second no-show, **When** the receptionist undoes that no-show the same day, **Then** the patient is no longer blocked.
3. **Given** a patient was blocked, lifted, and then had one new no-show, **When** that no-show is undone, **Then** the count is zero and nothing else changes.
4. **Given** a patient has no-shows for appointments of different family members, **When** a no-show is marked or undone, **Then** only the person the appointment was for is recounted.

---

### Edge Cases

- Exactly 2 no-shows, one at exactly 6 months ago: the 6-month window is rolling from now; a no-show older than 6 months does not count.
- 3 or more no-shows in the window: the patient is blocked (once); lifting restarts the count from zero.
- A no-show is marked on an appointment while a block is already in place: the block stays; it does not stack or need a second lift.
- A patient is blocked while in the middle of the online booking: the final confirm is also refused, not only the slot-picker step.
- A block can only be lifted while it is current; there is no "re-block" action; a new block comes only from new no-shows.
- No-shows that happened before this feature was switched on count (the count is from appointment data, not from the time of switching on).
- A patient's data is anonymised or deleted on request: the block record goes with it; counts are by person.
- Two receptionists press "Lift block" at the same time: one lift is recorded; the second sees it is already lifted.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST count, for each person (account holder or family member separately), the no-shows on that person's appointments in the 6 months before now, and treat the person as blocked when the count is 2 or more. (source: FR-025, PD-007)
- **FR-002**: System MUST refuse online booking and online rescheduling for a blocked person, including at the final confirm step, and MUST tell the patient online booking is not available and show the phone number of the clinic concerned. (source: FR-025)
- **FR-003**: System MUST leave all existing appointments of a blocked person unchanged, still visible and still cancellable online under the normal cancel rule. (source: FR-025)
- **FR-004**: System MUST NOT apply the block to bookings, reschedules or cancels made by reception. (source: FR-025, FR-026)
- **FR-005**: System MUST recalculate a person's block state immediately when a no-show is marked or undone, so the second no-show blocks and undoing it unblocks. (source: FR-025)
- **FR-006**: System MUST show reception that a person is blocked (day view, appointment panel, patient search) with the block start date and the counted no-show dates. (source: FR-026)
- **FR-007**: Reception MUST be able to lift a current block; the lift records who lifted it and when, takes effect at once for online booking, and restarts the count from zero so that only no-shows after the lift time count. (source: FR-026)
- **FR-008**: System MUST refuse a lift request from anyone who is not a receptionist and when the person is not currently blocked. (source: FR-026)
- **FR-009**: System MUST keep block records (person, blocked at, lifted by, lifted at) for 24 months. (source: FR-025, FR-026)
- **FR-010**: System MUST hide all screens and controls of this feature, and treat nobody as blocked, while the Release 2 feature switch for the no-show block is off. (source: FR-025, FR-026)
- **FR-011**: System MUST NOT write patient names, phone numbers or birth years to logs when checking, creating or lifting blocks. (source: FR-025, FR-026)

### Key Entities *(include if feature involves data)*

- **Repeat no-show block**: the record that a person was blocked from online booking: the person, when they were blocked, who lifted it (if lifted) and when. Kept 24 months. (source: FR-025, FR-026)
- **Person**: an account holder or a family member; the block and the no-show count belong to the person, not to the account. (source: PD-007)
- **Appointment status history**: the existing record of every status change (including no-show and its undo, with who and when); the no-show count is read from it and from appointment statuses.
- **Clinic**: provides the phone number shown to a blocked patient.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of test cases, a person with 2 no-shows in the last 6 months is refused online booking and rescheduling and shown the clinic phone number, and a person with fewer is not.
- **SC-002**: In 100% of test cases, a family member's no-shows never block the account holder or another family member.
- **SC-003**: After a receptionist marks, undoes or lifts, the patient's online booking behaviour reflects it on the very next attempt (no waiting period).
- **SC-004**: A receptionist can find a blocked patient and lift the block in under 1 minute, in 3 clicks or fewer from the patient search.
- **SC-005**: Existing appointments of a blocked patient are unchanged in 100% of test cases.
- **SC-006**: With the feature switch off, no screen shows any block information and no patient is refused.

## Assumptions

- Assumed: the 6-month window is rolling and measured by the appointment's start time; a no-show ageing out ends the block with no staff action (open question Q2 in clarifications.md).
- "No-shows after the lift" means no-shows marked after the lift time; the 6-month window is measured on the appointment's start time.
- Assumed: undoing a no-show that caused a block removes the block at once (open question Q1 in clarifications.md).
- Assumed: the phone number shown is that of the clinic of the booking being made or changed (open question Q3 in clarifications.md).
- Reception does not need to give a reason to lift a block; the lift is recorded with who and when only (the block record holds no reason field).
- Only receptionists lift blocks (the practice manager is not listed for this; can be widened later).
- Reception booking is never blocked; reception books anything (source: FR-025).
- Depends on feature 005 (reception no-show marking and undo; it must notify this feature), feature 003 (online booking) and feature 004 (reschedule); both already carry a check that always allows booking in Release 1, which this feature switches on.
- Depends on feature 007 (family members) only for the family-member scenarios; the person-level counting works with the account holder alone.
- Release 2 screens are hidden by a feature switch until ready; Release 2 date DL-2 2027-03-19 is not a hard date.
- Q-007 (family members on one phone) is open in the PRD; this feature follows the default: one account per phone number, family members are separate persons (PD-007).
