# Feature Specification: Family members on a patient account

**Feature Branch**: `007-family-members` (no git branch; spec directory `specs/007-family-members`)

**Created**: 2027-03-01

**Status**: Draft

**Input**: User description: "Family members on a patient account (MOD-01, Release 2 part, DL-2 2027-03-19, not a hard date). A patient can add up to 5 family members (name and birth year) to their account and book for any of them. Each booking names the person it is for. A patient sees only their own appointments and those of their family members. Q-007 is open. Release 2 screens are hidden by a feature flag until ready."

**Source requirements**: FR-006 (REQ-003, REQ-023); related: FR-004, FR-015, NFR-007, SA-001, ASM-001, RSK-003, Q-007.

**Depends on (other features)**: 001 (sign-in and the account/person split, already built), 003 (online booking flow), 004 (patient appointment list).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Add and manage family members (Priority: P1)

A signed-in patient opens "Family members" from their account and adds a person with a name and a birth year. They can see the list of people on the account (themselves first, then family members), correct a name or birth year, and remove a family member they no longer book for. An account holds at most 5 family members.

**Why this priority**: Without family members on the account nothing else in this feature can be used.

**Independent Test**: Sign in as a patient with no family members, add 5 people, try a sixth, edit one, remove one, and add a new one again. Delivers a working family list with no booking changes.

**Acceptance Scenarios**:

1. **Given** a signed-in patient with fewer than 5 family members, **When** they add a family member with a valid name and a valid birth year, **Then** the person appears in the family list and can be chosen in later screens. (source: FR-006)
2. **Given** a patient who already has 5 family members, **When** they try to add another, **Then** the system refuses, explains that 5 is the limit, and the list is unchanged. (source: FR-006, SA-001)
3. **Given** a patient adding a family member, **When** the name is empty, or the birth year is not a four-digit year, is in the future, or is more than 120 years ago, **Then** the system shows what is wrong next to the field and saves nothing. (source: FR-006)
4. **Given** a patient with a family member, **When** they correct the name or birth year, **Then** the change is saved and shown in the list and on that person's appointments. (source: FR-006)
5. **Given** a family member with no upcoming booked appointment, **When** the patient removes them, **Then** they leave the list, can no longer be chosen for new bookings, and the patient can add another family member in their place. (source: FR-006)
6. **Given** a family member with an upcoming booked appointment, **When** the patient tries to remove them, **Then** the system refuses and says to cancel those appointments first. (source: FR-006; Assumed, open question Q2)
7. **Given** the family feature is switched off, **When** any patient opens their account, **Then** no family screens or links are visible and the family operations are refused. (source: FR-006)

---

### User Story 2 - Choose who the visit is for when booking (Priority: P1)

In the booking flow, at the step "who and what", the patient chooses whether the visit is for themselves or for one of their family members, then continues with clinic and treatment as before. The booking records the person it is for. If the patient has no family members, the booking flow behaves as before (visit for themselves) without an extra choice.

**Why this priority**: Booking for another person is the whole value of the feature for P-01.

**Independent Test**: With one family member on the account, book a check-up choosing that family member; the booked screen and the saved appointment name that person. Book another choosing "myself".

**Acceptance Scenarios**:

1. **Given** a signed-in patient with at least one family member, **When** they reach the "who and what" step, **Then** they see themselves and each family member as choices, with "myself" pre-selected. (source: FR-006)
2. **Given** a patient who chose a family member, **When** they confirm the booking, **Then** the appointment is saved for that person and the booked screen and the appointment page name that person. (source: FR-006, REQ-003)
3. **Given** a patient who has no family members, **When** they book, **Then** the visit is for themselves and no "who" choice is asked. (source: FR-006)
4. **Given** a request to book for a person who is not on the patient's own account (for example a changed id), **When** the booking is submitted, **Then** the system refuses it and no appointment is created. (source: FR-006, FR-004)
5. **Given** a family member who was removed, **When** the patient books, **Then** that person is not offered and a booking for them is refused. (source: FR-006)
6. **Given** a family member who is blocked online after repeat no-shows, **When** the patient chooses them, **Then** the block message from the no-show rules applies to that person only, not to the account holder or other members. (source: FR-006; PD-007 handled by feature 006)

---

### User Story 3 - See family members' appointments, and only those (Priority: P2)

On "My appointments" the patient sees upcoming and past appointments for themselves and for every family member on the account, each showing the name of the person it is for. A patient never sees appointments of anyone who is not a person on their own account.

**Why this priority**: Booking for family is hard to trust if the patient cannot see the result, and the privacy rule is mandatory; but the list can ship just after booking.

**Independent Test**: Create appointments for the holder and two family members on one account and one appointment on another account. The first patient's list shows exactly three, with names; the second patient's list shows only theirs.

**Acceptance Scenarios**:

1. **Given** an account with appointments for the holder and for two family members, **When** the patient opens "My appointments", **Then** all of them are listed with status and the name of the person each is for. (source: FR-015, FR-006)
2. **Given** two different accounts, **When** one patient opens an appointment of the other account, by list or by direct link, **Then** the system refuses and reveals nothing about it. (source: FR-004, FR-006)
3. **Given** a family member who was removed but had past appointments, **When** the patient opens the list, **Then** the past appointments are still shown with that person's name. (source: FR-006; Assumed, open question Q2)
4. **Given** an account with family appointments, **When** the patient reschedules or cancels one of them within the usual 4-hour rule, **Then** it works exactly as for their own appointments. (source: FR-006, FR-016, FR-017)

---

### User Story 4 - Erase family member data and keep it out of logs (Priority: P3)

When a patient asks for their data to be deleted, the family members' names and birth years go with it. A deleted family member's appointments stay as anonymous rows so counts remain right. Names and birth years never appear in logs or error reports.

**Why this priority**: Required by the privacy rule (NFR-007) but it builds on the existing erasure of the account and is used rarely.

**Independent Test**: Erase an account with 3 family members; none of their names or birth years remain stored or findable, their appointments remain without personal link, and a search of the logs from the test run finds none of those values.

**Acceptance Scenarios**:

1. **Given** an account with family members, **When** the practice manager runs erasure for that account on request, **Then** every family member's name and birth year are removed or anonymised, and their appointments remain without a personal link. (source: NFR-007, FR-006)
2. **Given** a family member added, edited, removed or booked for, **When** the logs of that action are inspected, **Then** they contain ids and a correlation id but no name or birth year. (source: NFR-007, FR-006)
3. **Given** an account erased on request, **When** the patient signs in again with the same phone number, **Then** it is treated as a new account with no family members. (source: NFR-007)

---

### Edge Cases

- Two family members with the same name and birth year on one account: refused as a duplicate; the same name with a different birth year is allowed.
- A name with leading or trailing spaces, or only spaces: trimmed; empty after trimming is refused.
- Name longer than 100 characters: refused.
- Two browser tabs adding the 5th and 6th member at the same moment: only 5 are saved.
- The patient removes a family member while another tab is in the middle of booking for them: the booking is refused with a clear message.
- The family feature flag is switched off after members exist: existing members and their appointments are kept, but the family screens and the "who" choice are hidden; the booking flow is for the account holder only and the appointment list still shows all of the account's appointments.
- If Q-007 is answered differently (families need separate sign-ins on one phone), sign-in and the account/person model change; this feature would need rework (see Assumptions).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A signed-in patient MUST be able to add a family member to their account with a name and a birth year. (source: FR-006)
- **FR-002**: The system MUST allow at most 5 family members per account and refuse a sixth, including when two requests arrive at the same time. (source: FR-006, SA-001)
- **FR-003**: The system MUST validate a family member: name 1 to 100 characters after trimming; birth year a four-digit year not in the future and not more than 120 years ago; no second active member with the same name and birth year on the account. (source: FR-006)
- **FR-004**: A patient MUST be able to list, edit and remove family members of their own account only. (source: FR-006, FR-004)
- **FR-005**: Removing a family member MUST be refused while that person has an upcoming booked appointment. After removal the person cannot be chosen for new bookings, does not count towards the limit of 5, and their past appointments remain visible to the account. (source: FR-006; Assumed, open question Q2)
- **FR-006**: The booking flow MUST ask who the visit is for (the account holder or one of the active family members) when the account has at least one family member, and MUST record that person on the appointment. (source: FR-006, REQ-003)
- **FR-007**: The system MUST refuse a booking, reschedule, cancel or view for any person who is not on the signed-in patient's account. (source: FR-006, FR-004)
- **FR-008**: The patient's appointment list MUST include appointments of the account holder and of all family members of the account (including removed ones), and show the name of the person each appointment is for. (source: FR-015, FR-004)
- **FR-009**: The booked screen and the appointment page (the link in the confirmation message) MUST name the person the visit is for. The text of confirmation and reminder messages is unchanged. (source: FR-006, REQ-003)
- **FR-010**: Erasure of an account on request MUST remove or anonymise the name and birth year of every person on it, and keep the appointments without a personal link. (source: NFR-007)
- **FR-011**: The system MUST NOT write a family member's name or birth year to logs, metrics, traces or error reports. (source: NFR-007)
- **FR-012**: All family screens, the "who is this for" step, and the family operations MUST be hidden or refused while the Release 2 feature flag for family members is off; with the flag off the booking flow behaves as for the account holder only. (source: FR-006)
- **FR-013**: The family list and the "who" choice MUST work on a phone without sideways scrolling, with tap targets of at least 44 px and in English only. (source: FR-006, NFR-001, NFR-010)

### Key Entities *(include if feature involves data)*

- **Patient account**: One phone number. Owns one account holder and up to 5 active family members. Already exists (feature 001).
- **Person (patient)**: Someone a visit can be for: the account holder or a family member. Has a name and a birth year (both personal data), belongs to one account, and is active or removed. Already exists (feature 001); this feature adds the family-member lifecycle.
- **Appointment**: Names exactly one person it is for. A patient reaches an appointment only through the persons on their own account. Owned by feature 003.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A patient can add a family member in under 1 minute from the account screen on a phone.
- **SC-002**: A patient who has a family member can book a visit for that person within the booking limit of 5 screens after sign-in, with the "who" choice included.
- **SC-003**: In tests, 0 appointments of one account are visible, changeable or bookable from another account, across every operation that takes a person or appointment.
- **SC-004**: 100% of attempts to save a sixth family member, or an invalid name or birth year, are refused with a message that says what to fix.
- **SC-005**: After an erasure request is processed, 0 names or birth years of that account's people remain in stored data, and 0 appear in logs from any family-member action.
- **SC-006**: With the feature flag off, 0 family screens or choices are visible to patients.

## Assumptions

- Q-007 is open. This spec assumes the PRD default (SA-001, ASM-001): one account per phone number, the account holder signs in once and books for up to 5 family members. If Q-007 is answered differently (separate sign-ins on one phone), sign-in and the identity module change and MOD-01 grows 2 to 4 person-days (RSK-003); the work here would be revised. (open question Q1)
- The limit of 5 counts family members only; the account holder is an extra person, so an account has up to 6 people (open question Q3).
- "Remove" keeps the person's record, marked removed, so past appointments and no-show counts stay correct (PD-007); the personal data is removed only by erasure on request. (open question Q2)
- Family members do not have their own phone numbers or sign-ins; messages about their visits go to the account's phone number and the account's channel choice.
- The account/person split already exists from feature 001; sign-in, the booking flow and the appointment list are built by features 001, 003 and 004, and this feature extends them.
- Receptionist screens show the name of the person on an appointment through the existing patient fields; no new receptionist screen is part of this feature.
- This feature belongs to Release 2 (target 2027-03-19, not a hard date) and is hidden behind a feature flag until ready. Work is in two repositories: `brightsmile/clinic-api` and `brightsmile/clinic-web`.
- Only name and birth year are stored for a family member; no clinical data (NFR-007).
