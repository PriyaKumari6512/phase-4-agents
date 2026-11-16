# Feature Specification: Repeat no-show block and no-show report (Release 2)

**Feature Branch**: `009-noshow-block-report`

**Created**: 2026-11-16

**Status**: Draft

**Input**: User description: "Repeat no-show block and no-show report (Release 2). Covers prd.md ids FR-025, FR-026, FR-032. A patient with 2 no-shows in the last 6 months cannot book or reschedule online; reception sees and lifts the block; the practice manager sees no-shows and the no-show rate per clinic and month for the last 12 months, on screen only. Release 2 (Should, due 2027-03-19, after the 1 March 2027 go-live), hidden by a feature flag until ready."

## Context

No-shows are BrightSmile Dental's biggest problem. Today's no-show rate is not known (PRD "Questions to raise", item 1), so the no-show target is TBD and the first 2 months of app data are the baseline (ASM-015). This feature has two parts: a repeat no-show block on online booking (P-01 Patient, P-02 Receptionist) and a monthly no-show report (P-04 Practice manager). Both belong to Release 2 and stay hidden behind a feature flag until their data is ready. Two earlier features already call a "is this person blocked?" check on online booking and rescheduling and get "not blocked" until this feature exists; this feature puts the real rule behind that check without changing how existing bookings behave.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A patient with 2 recent no-shows cannot book or reschedule online (Priority: P1)

A patient (or a family member the patient books for) who has had 2 no-shows in the last 6 months is told, when they try to book or reschedule online, that online booking is not available and is shown the clinic's phone number. Appointments they already have stay as they are. Each person is counted on their own: a family member's no-shows count against that family member, not against the account holder. (source: FR-025, PD-007)

**Why this priority**: This is the rule that discourages repeat no-shows, the clinic's biggest problem. Without it the other two stories have nothing to show or lift.

**Independent Test**: Record 2 no-shows within 6 months for one test patient, then sign in as that patient and try to book and to reschedule; both are refused with the clinic phone number, while an existing booking is still listed and can be cancelled. Repeat for a family member on the same account and confirm the account holder is not blocked.

**Acceptance Scenarios**:

1. **Given** a patient with 2 no-shows in the last 6 months, **When** they reach the step where they choose a dentist and slot, **Then** the system says online booking is not available and shows the phone number of the clinic they chose, and no booking is created.
2. **Given** a patient with 2 no-shows in the last 6 months and an upcoming booking, **When** they try to reschedule it online, **Then** the system says online rescheduling is not available and shows the phone number of that appointment's clinic, and the booking stays unchanged.
3. **Given** a patient with 2 no-shows in the last 6 months and upcoming bookings, **When** they view their appointments, **Then** all existing bookings are still listed and none is cancelled or changed by the block.
4. **Given** an account holder with a family member who has 2 no-shows in the last 6 months, **When** the account holder books online for themselves, **Then** the booking is accepted; **When** they try to book for that family member, **Then** it is refused as in scenario 1.
5. **Given** a patient with 1 no-show in the last 6 months, **When** they book or reschedule online, **Then** the booking proceeds as normal.
6. **Given** a patient whose older no-show falls out of the 6-month window so that fewer than 2 remain in the window, **When** they try to book online, **Then** the booking proceeds as normal without anyone lifting anything.
7. **Given** the Release 2 feature flag is off, **When** a patient with 2 no-shows in the last 6 months books or reschedules, **Then** the booking behaves as before this feature (not blocked).

---

### User Story 2 - Reception sees a block and lifts it (Priority: P1)

A receptionist opening a patient's record sees that the patient is blocked from online booking. When a blocked patient phones and the clinic agrees, the receptionist lifts the block. Lifting starts the patient's no-show count again from zero, and the lift records who did it and when. (source: FR-026)

**Why this priority**: A block with no way out would turn away patients for good and flood reception with complaints. Lifting must ship with the block.

**Independent Test**: Block a test patient, open their record as a receptionist and confirm the block is shown, lift it, then confirm the patient can book online again, that the lift is recorded with the receptionist and time, and that one new no-show does not block them but a second new one does.

**Acceptance Scenarios**:

1. **Given** a blocked patient, **When** a receptionist opens that patient's record or an appointment panel for that patient, **Then** the screen clearly shows the patient is blocked from online booking and since when.
2. **Given** a blocked patient, **When** the receptionist lifts the block, **Then** the patient can book and reschedule online straight away, and the system records the receptionist and the time of the lift.
3. **Given** a patient whose block was just lifted, **When** one new no-show is recorded, **Then** the patient is not blocked; **When** a second new no-show is recorded after the lift, **Then** the patient is blocked again.
4. **Given** a patient who had 2 no-shows before a lift and none after, **When** the system counts their no-shows, **Then** the count is zero.
5. **Given** a patient who is not blocked, **When** a receptionist opens their record, **Then** no lift action is offered.
6. **Given** a blocked patient, **When** a receptionist books an appointment for them at the desk or by phone, **Then** the booking is accepted, because the block applies to online booking and rescheduling only.
7. **Given** a patient is blocked because of a no-show marked today, **When** the receptionist undoes that no-show the same day and the patient then has fewer than 2 no-shows in the window, **Then** the block no longer applies and no lift record is created.

---

### User Story 3 - The practice manager reads the no-show report per clinic and month (Priority: P2)

The practice manager opens a no-show report that shows, for each clinic and for each of the last 12 months, the number of no-shows and the no-show rate (no-shows divided by appointments that were not cancelled). The report is on screen only, with no export. (source: FR-032, ASM-004, ASM-014)

**Why this priority**: It gives the manager the figure the clinic lacks today and the baseline for the TBD no-show target (ASM-015). It does not depend on the block, so it can ship and be tested on its own, but patients and reception feel the block first.

**Independent Test**: Seed appointments across 2 clinics and several months with a known mix of statuses, open the report as the practice manager, and compare each clinic-month cell with hand-counted figures; confirm a receptionist and a patient cannot open it and that no export action exists.

**Acceptance Scenarios**:

1. **Given** the practice manager is signed in, **When** they open the no-show report, **Then** they see one row per clinic and month for the last 12 months, each with the number of no-shows and the no-show rate.
2. **Given** a clinic-month with 40 appointments of which 4 were cancelled by the patient, 2 cancelled by the clinic and 3 are no-shows, **When** the report is shown, **Then** the rate is 3 divided by 34 (appointments not cancelled), shown as a percentage, and the no-show count is 3.
3. **Given** a walk-in booked as a normal appointment and marked arrived, **When** the report counts that month, **Then** the walk-in is counted among the appointments that were not cancelled.
4. **Given** a clinic-month with no appointments that were not cancelled, **When** the report is shown, **Then** the count is 0 and the rate is shown as "no appointments" rather than as a number or an error.
5. **Given** a patient whose personal data was deleted on request and whose appointment rows were anonymised, **When** the report is shown, **Then** the counts and rates are the same as before the deletion.
6. **Given** a receptionist or a patient or a dentist is signed in, **When** they try to open the report, **Then** access is refused.
7. **Given** the report is open, **When** the manager looks for a way to download or export it, **Then** none is offered.
8. **Given** the Release 2 feature flag is off, **When** the practice manager looks at the menu, **Then** the report screen is not shown.

---

### Edge Cases

- A patient reaches exactly 2 no-shows on the day of a booking they are making: the block applies from the moment the second no-show is recorded, so the next online booking or reschedule attempt is refused.
- A no-show is undone on the same day (FR-022) after it created a block: the block is removed if the patient is back under 2 (see Story 2, scenario 7).
- A blocked patient cancels an existing booking online: cancelling is still allowed, because only booking and rescheduling are blocked.
- A patient is blocked while a booking is in progress: the final confirm step is refused with the same message, so no booking is created.
- A blocked patient has appointments at both clinics: the phone number shown is that of the clinic the patient is trying to book at or reschedule in.
- Two receptionists lift the same block at once: the block is lifted once, with one lift record.
- A patient with no-shows before a lift and later no-shows after: only no-shows after the lift count.
- A patient's data is deleted on request: the personal link is removed and the person no longer exists to be blocked, while the anonymised appointment rows still count in the report (RSK-007).
- A clinic-month with zero non-cancelled appointments: shows a count of 0 and no rate, never a divide-by-zero error.
- A third clinic is added as data: it appears in the report without a code change.
- The current month is not finished: the report shows it as "month so far" (see open question Q3).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST count no-shows per person (the patient the appointment is for, whether the account holder or a family member), never per account. (source: FR-025, PD-007)
- **FR-002**: System MUST treat a person as blocked from online booking when they have 2 or more no-shows in the last 6 months, counting only no-shows recorded after the person's most recent block lift. (source: FR-025, FR-026)
- **FR-003**: System MUST refuse an online booking and an online reschedule for a blocked person, tell them online booking is not available, and show the phone number of the clinic concerned; no appointment is created or changed. (source: FR-025)
- **FR-004**: System MUST leave every existing appointment of a blocked person as it is (not cancelled, moved or hidden) and MUST still allow the person to cancel online. (source: FR-025)
- **FR-005**: System MUST apply the block check whenever an online booking or reschedule is confirmed, not only when the slot step is shown, so a block that arrives during a session still stops the booking. (source: FR-025)
- **FR-006**: System MUST NOT apply the block to bookings, reschedules or cancellations made by reception. (source: FR-025, FR-026)
- **FR-007**: System MUST show reception that a patient is blocked, with the date the block began, on the patient's record and appointment panel. (source: FR-026)
- **FR-008**: System MUST let a receptionist lift a block, MUST start that person's count again from zero so only no-shows recorded after the lift count, and MUST record who lifted the block (the signed-in receptionist) and when, as an auditable action. (source: FR-026)
- **FR-009**: System MUST record when a block began (blocked at) and, once lifted, who lifted it and when, and MUST keep these records for 24 months. (source: FR-025, FR-026)
- **FR-010**: System MUST remove a block that came only from a no-show that is then undone the same day, when the person is back under 2 no-shows, without creating a lift record. (source: FR-022, FR-025, FR-026)
- **FR-011**: System MUST show the practice manager, for each clinic and each of the last 12 months, the number of no-shows and the no-show rate, where the rate is the number of no-shows divided by the number of appointments that were not cancelled. (source: FR-032)
- **FR-012**: System MUST exclude appointments cancelled by the patient and appointments cancelled by the clinic from the rate's denominator, and MUST include walk-ins in the count of appointments that were not cancelled. (source: FR-032, ASM-004, ASM-014)
- **FR-013**: System MUST show the report on screen only and MUST NOT offer export or download. (source: FR-032)
- **FR-014**: System MUST make the report available to the practice manager role only, showing both clinics. (source: FR-032)
- **FR-015**: System MUST keep report counts unchanged when a patient's personal data is deleted on request, by anonymising the appointment rows instead of removing them. (source: FR-032, RSK-007)
- **FR-016**: System MUST hide the block (its effect on booking and its reception actions) and the report screen behind a Release 2 feature flag until they are ready; with the flag off, booking and rescheduling behave as before this feature. (source: FR-025, FR-026, FR-032)
- **FR-017**: System MUST include a third clinic in the report as soon as it exists as data, with no code change. (source: FR-032)

### Key Entities *(include if feature involves data)*

- **No-show block**: A record that a person was blocked from online booking: the person (patient), when blocked, who lifted it and when it was lifted. Kept 24 months. One person can have several over time; at most one is unlifted at a time. (source: FR-025, FR-026)
- **Patient (person)**: The person an appointment is for, either the account holder or a family member. No-shows are counted against this person. Owned by an earlier feature. (source: PD-007)
- **Appointment**: Has a clinic, a person, a start time and a status (booked, arrived, no-show, cancelled by the patient, cancelled by the clinic). Its status history records who changed it and when. Owned by an earlier feature; this feature reads statuses and counts. (source: FR-025, FR-032)
- **No-show report row**: One clinic and one month: the number of no-shows, the number of appointments not cancelled, and the rate. Derived from appointments, not stored. (source: FR-032)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In acceptance testing, 100% of online booking and reschedule attempts by a person with 2 no-shows in the last 6 months (after any lift) are refused with the clinic's phone number, and 0 of their existing appointments are changed.
- **SC-002**: In acceptance testing, 100% of attempts by a person with fewer than 2 counted no-shows are not refused because of the block.
- **SC-003**: A receptionist can see a patient's blocked state and lift the block in 3 steps or fewer from the patient's record, and the patient can book online straight afterwards.
- **SC-004**: Every block lift shows the receptionist and the time in 100% of tested cases.
- **SC-005**: For a seeded test set, every clinic-month number of no-shows and every rate in the report matches the hand-counted figure (100% of cells).
- **SC-006**: The practice manager can read all 12 months for both clinics on one screen without using an export, and no export option exists.
- **SC-007**: With the feature flag off, 100% of existing booking and reschedule tests from earlier features still pass unchanged.
- **SC-008**: From go-live of this feature the clinic has the monthly no-show figure it lacks today, so the no-show baseline from the first 2 months of app data (ASM-015) can be read directly from the report.

## Assumptions

- The 6-month window is a rolling window counted back from today, using the appointment's start time; no-shows older than 6 months stop counting automatically, so a block ends by itself when fewer than 2 remain in the window (source: FR-025).
- After a lift, a no-show counts only if it was marked after the lift time (Open question Q2).
- Only a receptionist lifts a block; the practice manager's lift rights are not specified in FR-026 and are out of scope. Any receptionist can see and lift a block for any patient they can find, because patients are not tied to one clinic (ASM-011).
- The block affects online booking and online rescheduling only; online cancelling and everything done by reception are unaffected.
- A walk-in is a normal appointment marked arrived, and it counts among appointments that were not cancelled (ASM-004; Q-015 is still open in the PRD).
- Both kinds of cancellation (by the patient and by the clinic) are left out of the rate (ASM-014).
- The report's no-show rate is shown as a percentage and months are IST calendar months, attributed by the appointment's start date.
- There is no no-show target yet (TBD); the report shows facts and does not compare with a target. The first 2 months of app data are the baseline (ASM-015).
- Patient personal data is deleted on request by anonymising rows, so report counts stay (RSK-007, ASM-012).
- The patient is told about the block only when they try to book or reschedule; no message is sent when a block begins (none is specified in the PRD).
- Depends on earlier features: online booking (004), manage appointments (005), reception day and no-show marking (006), identity and person records (002, 008), and the release flag from the platform foundation (001).

## Open Questions (assumed answers)

- **Q1**: If a no-show that created a block is undone the same day, is the block removed? Assumed: yes, if the person is back under 2 no-shows, with no lift record (open question Q1).
- **Q2**: After a lift, does a no-show count by when it was marked or by the appointment date? Assumed: by when it was marked, so an earlier appointment marked as a no-show after the lift counts (open question Q2).
- **Q3**: Should the report's current, unfinished month be included and how is it rated? Assumed: the 12 months end with the current month, shown as "month so far", with the rate computed by the PRD formula over all appointments in that month that were not cancelled (open question Q3).
