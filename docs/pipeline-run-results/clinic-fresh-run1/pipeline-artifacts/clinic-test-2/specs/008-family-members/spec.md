# Feature Specification: Family members on a patient account (Release 2)

**Feature Branch**: `008-family-members`

**Created**: 2026-11-16

**Status**: Draft

**Input**: User description: "Family members on a patient account (Release 2). A patient can add up to 5 family members to their account (name and birth year) and book for any of them; each booking names the person it is for. Release 2 (Should), due 2027-03-19, about 2-3 weeks after the 1 March 2027 go-live; hidden by a feature flag until ready." (source: FR-006, US-006)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Add family members to my account (Priority: P1)

A signed-in patient opens "Family" on their account and adds a family member by giving a name and a birth year. They can add up to 5 family members. The new person shows in the list of people on the account, next to the patient themselves. The family member has no phone number and no sign-in of their own: they are a person on the account holder's account.

**Why this priority**: Nothing else in this feature works until a family member exists. It is the core of FR-006.

**Independent Test**: Sign in as a patient with no family members, add one with a name and birth year, and see them in the list. Add four more; the sixth attempt is refused with a clear message. Delivers a usable list of people on the account.

**Acceptance Scenarios**:

1. **Given** a signed-in patient with fewer than 5 family members, **When** they enter a name and a valid birth year and confirm, **Then** the family member is saved on their account and appears in the list of people on the account. (source: FR-006)
2. **Given** a signed-in patient who already has 5 family members, **When** they try to add another, **Then** the system refuses, says that 5 family members is the limit, and the list is unchanged. (source: FR-006)
3. **Given** a signed-in patient on the add screen, **When** they leave the name empty or enter a birth year that is not a four-digit year in a plausible range, **Then** the system says what to correct and saves nothing. (source: FR-006)
4. **Given** a signed-in patient, **When** they add a family member, **Then** only a name and a birth year are stored for that person (no phone number, no other personal details). (source: FR-006, NFR-007)
5. **Given** the family-members feature flag is off, **When** a patient opens their account or sends a request to add a family member, **Then** the "Family" screen is not shown and the request is refused. (source: FR-006)

---

### User Story 2 - Choose who the visit is for when booking (Priority: P1)

When a signed-in patient books online, the first choice is who the visit is for: themselves or one of their family members. The booking is saved against that person. The rest of the booking flow (clinic, treatment, dentist, slot, channel) is unchanged. A patient with no family members is not asked an extra question, and books for themselves as before.

**Why this priority**: This is the reason the patient adds family members: booking for them. Each booking must name the person it is for (FR-006).

**Independent Test**: With a patient who has two family members, book a visit for a family member and check that the confirmation and the appointment name that person. Book one for the patient themselves and check that it names the patient.

**Acceptance Scenarios**:

1. **Given** a signed-in patient with at least one family member and the flag on, **When** they start a booking, **Then** they are asked who the visit is for and the choices are themselves and each of their family members. (source: FR-006, US-006)
2. **Given** the patient chose a family member, **When** they complete the booking, **Then** the appointment is saved for that family member, the booked screen and the confirmation name that person, and the booking takes no more screens than a booking for the patient themselves plus the one "who is it for" choice. (source: FR-006)
3. **Given** a signed-in patient with no family members, **When** they start a booking, **Then** the visit is for themselves and no "who is it for" question is shown. (source: FR-006)
4. **Given** a signed-in patient, **When** a request names a person who is not on that patient's account, **Then** the system refuses it and no appointment is created. (source: FR-004, FR-006)
5. **Given** the family-members flag is off, **When** a patient books, **Then** the booking is for the patient themselves and no family choice is offered. (source: FR-006)

---

### User Story 3 - See family members' appointments in my list (Priority: P2)

A signed-in patient sees, in "My appointments", the upcoming and past appointments of themselves and of their family members, each with the name of the person it is for and its status. A patient never sees appointments of people outside their own account.

**Why this priority**: It lets the account holder manage the family's visits. FR-004 and FR-015 already say the list includes family members; this story makes it true once family members exist.

**Independent Test**: Book one visit for the patient and one for a family member, open "My appointments" and see both, each naming its person. Sign in as a different patient and see neither.

**Acceptance Scenarios**:

1. **Given** a patient and a family member each have an upcoming appointment, **When** the patient opens "My appointments", **Then** both appear, each showing the person it is for and its status. (source: FR-004, FR-015, FR-006)
2. **Given** a family member has a past appointment, **When** the patient opens the past appointments, **Then** it is listed with the family member's name and its status. (source: FR-015)
3. **Given** two different accounts, **When** one patient opens their list or asks for an appointment of the other account, **Then** the other account's appointments are never shown and the request is refused. (source: FR-004, NFR-006)
4. **Given** a patient opens an appointment of a family member, **When** they reschedule or cancel it under the rules of the appointment features, **Then** the same rules apply as for their own appointments. (source: FR-004, FR-015)

---

### User Story 4 - Messages for a family member's visit reach the account's phone (Priority: P2)

When a visit is booked for a family member, the confirmation, the change notice and the reminder go to the account's phone number in the account's chosen channel (SMS or WhatsApp). The message names the person the visit is for. Family members have no phone number or channel of their own. If the account has switched reminders off, no reminder goes for any person on the account, as for the account holder.

**Why this priority**: Without it the account holder cannot tell which family visit a message is about. It reuses the existing messaging; the change is the person's name in the message and the account-level addressing.

**Independent Test**: Book a visit for a family member, check that the confirmation arrives at the account's phone in the chosen channel and names the family member.

**Acceptance Scenarios**:

1. **Given** a visit booked for a family member, **When** the confirmation is sent, **Then** it goes to the account's phone number in the channel chosen for that booking and names the family member. (source: FR-006, FR-014)
2. **Given** a reminder is due for a family member's appointment, **When** it is sent, **Then** it goes to the account's phone number in the account's channel and names the family member. (source: FR-006, FR-027)
3. **Given** the account has reminders switched off, **When** a reminder falls due for a family member's appointment, **Then** no reminder is sent but confirmations and change notices still are. (source: FR-031)

---

### Edge Cases

- A patient adds a sixth family member: refused with a clear message (US1 scenario 2). If two requests to add arrive at the same time when the account has 4, only one succeeds so that the limit of 5 is never exceeded.
- A family member with the same name and birth year as a person already on the account: refused as a duplicate, so one person cannot be split into two to avoid a count of no-shows (PD-007). See assumption A-6.
- A request names a person from another account (changed id in the request): refused by the server; no data about that person is revealed (thr-004).
- A family member's no-show counts against that family member, not the account holder (PD-007). The booking records the person; the count itself is built in the no-show feature (009).
- The patient deletes their data on request: the family members' names and birth years go with the account and the appointments stay anonymised (NFR-007, RSK-007). The erasure itself is built in the identity feature (002); this feature only has to make sure family members are included.
- The flag is turned off after family members were added: the data stays; existing appointments for family members stay and still show to the account holder; no new family members or family bookings can be made while it is off. See assumption A-7.
- A family member has no phone number: a reception booking for a family member is out of scope here (see A-8).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A signed-in patient MUST be able to add a family member to their account by giving a name and a birth year. (source: FR-006)
- **FR-002**: The system MUST allow at most 5 family members on one account (the account holder is not counted) and MUST refuse a further one with a clear message, also when two adds arrive at the same time. (source: FR-006, SA-001)
- **FR-003**: The system MUST validate a family member's name (not empty) and birth year (four digits, not in the future, not before 1900) and tell the patient what to correct. (source: FR-006)
- **FR-004**: The system MUST store only the name and the birth year for a family member; no phone number, sign-in or other personal data. (source: FR-006, NFR-007)
- **FR-005**: The system MUST show the patient the list of people on their account: themselves and their family members. (source: FR-006, US-006)
- **FR-006**: When booking online, a patient with family members MUST be able to choose who the visit is for (themselves or a family member) as the first choice of the booking; a patient without family members books for themselves with no extra question. (source: FR-006, US-006)
- **FR-007**: Every booking MUST name the person it is for, and the booked screen and the confirmation MUST show that person's name. (source: FR-006, FR-014)
- **FR-008**: The system MUST refuse, on the server, any action on a person who is not on the signed-in patient's own account, whatever ids the request carries. (source: FR-004, NFR-006)
- **FR-009**: The patient's appointment list MUST include the upcoming and past appointments of the patient and of their family members, each with the person's name and the status, and MUST never include appointments of other accounts. (source: FR-004, FR-015)
- **FR-010**: Confirmations, change notices and reminders for a family member's appointment MUST go to the account's phone number in the channel chosen for the booking, and MUST name the person; the account's reminders opt-out applies to every person on the account. (source: FR-006, FR-014, FR-027, FR-031)
- **FR-011**: The family-member screens, the "who is it for" choice and the family-member operations MUST be available only while the Release 2 feature flag for family members is on; while it is off, booking is for the patient themselves only. (source: FR-006)
- **FR-012**: A family member's data MUST be included when the patient's data is deleted or anonymised (on request or at 24 months idle). (source: NFR-007)
- **FR-013**: The system MUST NOT write family members' names or birth years to logs. (source: NFR-007)
- **FR-014**: The system MUST refuse to add a family member with the same name and birth year as a person already on the account (assumption A-6, not in the PRD). (source: FR-006, PD-007)

### Key Entities *(include if feature involves data)*

- **Patient account**: One per phone number. Holds the phone number, the account holder's name, the preferred channel and the reminders opt-out. Owns up to 5 family members and the account holder as a person. Signs in; family members do not.
- **Patient (person)**: A person an appointment can be for: the account holder or one of up to 5 family members. Holds name, birth year, the account it belongs to and an active flag. Name and birth year are personal data.
- **Appointment**: Each appointment references one person (the one it is for). Owned by the booking feature; this feature relies on it and on the person being recorded at booking.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A patient can add a family member in under 1 minute from the account screen.
- **SC-002**: A patient can book a visit for a family member in no more than one extra choice compared with booking for themselves, and within the booking limit of 5 screens after sign-in.
- **SC-003**: In 100% of automated tests, a patient cannot see, book for or change a person or appointment from another account.
- **SC-004**: In 100% of tests the sixth family member is refused, including when adds are sent at the same time.
- **SC-005**: 100% of bookings and confirmations for a family member name that person.
- **SC-006**: With the flag off, 0 family screens or family choices are shown to patients.
- **SC-007**: 0 family member names or birth years appear in logs in a test run.

## Assumptions

- A-1: Release 2 (Should), due 2027-03-19, about 2-3 weeks after the 1 March 2027 go-live; screens and operations are hidden behind a feature flag until ready.
- A-2: One account per phone number with up to 5 family members (SA-001, ASM-001). The account holder signs in; family members never sign in and have no phone number.
- A-3: Q-007 is open. Assumed: no separate sign-ins for family members (open question Q1). If the answer is that families need separate sign-ins on one phone, sign-in and the identity component change (RSK-003, about 2-4 person-days). The account and person split (ADR-0008) already makes this change possible; this feature does not build separate sign-ins.
- A-4: The PRD specifies adding family members only. Assumed: edit and remove (deactivate) are not part of this release; a mistake is corrected by phoning the clinic or by a data-deletion request. The person has an "active" flag in the data model (ADR-0008), but this feature does not expose it. Assumed: no edit or remove in Release 2 (open question Q2).
- A-5: The limit of 5 counts family members only, not the account holder. Assumed: 5 family members plus the account holder (open question Q3).
- A-6: A duplicate (same name and birth year, ignoring case and spaces at the ends) on one account is refused. This is our assumption, not in the PRD; it protects the per-person no-show count (PD-007).
- A-7: Turning the flag off hides the screens and refuses new family members and new family bookings; existing family data and appointments stay and still show in the list.
- A-8: Reception booking for a family member is not part of this feature; reception finds patients as in feature 006. Whether reception sees family members of an account is an open point for feature 006.
- A-9: The booking, appointment list and messaging features (004, 005, 007) are built for the account holder first and already record a person on every appointment and list by account; this feature adds the person choice, the family list and the person's name in messages.
- A-10: A birth year is a year only (no day or month) as in the PRD; the valid range of 1900 to the current year is our assumption.
- A-12: Naming the person in a message needs a registered SMS template and an approved WhatsApp template that carry a person-name value (NFR-011). Assumed: feature 007 adds that value before the R2 templates are submitted. If a template cannot carry it in time, the message keeps the appointment link, which opens the appointment naming the person (open question Q4).
- A-11: A patient can have the same family member on two accounts (for example two parents); each account counts it separately. We do not try to link them, because only a name and birth year are stored.
