# Feature Specification: Online booking by patients (MOD-03)

**Feature Branch**: `003-online-booking` (no git branch is created in this run)

**Created**: 2027-01 (Release 1, delivery line DL-1 2027-02-22)

**Status**: Draft

**Input**: User description: "Online booking by patients (MOD-03, Release 1). A signed-in patient books a visit: clinic, an online treatment type, a dentist or 'first available', then a free slot within the next 30 days. A slot is never booked twice. Mobile-friendly, fast, usable by a new patient in 5 screens or fewer after sign-in." Requirement ids covered: FR-011, FR-012, NFR-001, NFR-002, NFR-010 (prd.md).

## Scope and neighbours

- **In this feature**: the patient booking flow (screens "who and what", "slot picker", "confirm", "booked"), the slot lookup for patients, the booking itself, the no-double-booking guarantee, the appointment and appointment-history records with the first "booked" history entry, and the tests for concurrency, performance and mobile usability.
- **Not in this feature (neighbours)**: patient sign-in (feature 001, FR-002); clinics, hours, treatment types and the free-slot calculation (scheduling, MOD-02, FR-010); the SMS/WhatsApp choice being remembered and the confirmation text and delivery (messaging, feature 006, FR-013 and FR-014); status changes and the history screen (feature 005, FR-024); "My appointments", reschedule and cancel (MOD-04); family members (Release 2, FR-006, Q-007); the repeat no-show block (Release 2, FR-025).
- **Coordination**: this feature creates the appointment and appointment-history tables and writes the first "booked" history entry. Feature 005 adds later status changes to the same tables.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Find a free slot (Priority: P1)

A signed-in patient opens "Book", chooses the clinic and one of the online treatment types (check-up, cleaning, consultation), then chooses a dentist at that clinic or "first available", and sees the free slots for a day within the next 30 days. With "first available" the patient sees the earliest free slots across all of that clinic's dentists.

**Why this priority**: Without seeing real free slots, no booking is possible. It is the first half of the core flow.

**Independent Test**: Sign in as a patient, pick a clinic, a treatment and "first available", and check that the 10 earliest free slots are shown in time order, each with its dentist. Pick a named dentist and a day and check that only that dentist's free slots are shown. Check that day 31 and later are not offered.

**Acceptance Scenarios**:

1. **Given** a signed-in patient on the "who and what" screen, **When** they open the treatment list for a clinic, **Then** only online-bookable treatment types (check-up, cleaning, consultation) are offered, and reception-only types are not.
2. **Given** a clinic with several dentists who have free slots, **When** the patient chooses "first available", **Then** the system shows the earliest free slots across that clinic's dentists (at most 10, earliest first), each with dentist name, date and time.
3. **Given** a patient who chose a named dentist, **When** they pick a day, **Then** the free slots of that dentist for that day are shown, on the hour or half hour.
4. **Given** today is 1 March, **When** the patient looks at days, **Then** days from 1 March up to and including 31 March can be chosen and later days cannot (the window is today plus 30 days, a setting).
5. **Given** a day with no free slots, **When** the patient picks it, **Then** the screen says no slots are free that day and suggests the next day that has free slots.
6. **Given** a patient who is not signed in, **When** they ask for slots, **Then** they are sent to sign in first (feature 001) and return to the same choice afterwards.

(source: FR-011, NFR-002)

---

### User Story 2 - Confirm and see the booking (Priority: P1)

After picking a slot, the patient chooses SMS or WhatsApp for messages about this visit, reviews a summary (who, clinic, dentist, treatment, date, time, channel) and confirms. The system books the appointment for the patient's own account and shows the "booked" screen with the details. A confirmation message is requested and delivered shortly after (feature 006), not while the patient waits.

**Why this priority**: It completes the core flow and creates the appointment record that every later feature uses.

**Independent Test**: As a signed-in patient pick a free slot, choose a channel, confirm; check that the appointment exists with status "booked" for that patient, that exactly one "booked" history entry exists with who and when, that the "booked" screen shows clinic, dentist, treatment, date and time, and that a confirmation message was queued.

**Acceptance Scenarios**:

1. **Given** a patient who picked a free slot, **When** they choose SMS or WhatsApp and confirm, **Then** the appointment is saved with status "booked" for their own account and the "booked" screen shows clinic, dentist, treatment, date, time and the chosen channel.
2. **Given** a first-time booker, **When** the confirm screen opens, **Then** SMS is pre-selected as the default channel.
3. **Given** a successful booking, **When** it is saved, **Then** one history entry "booked" with the patient as actor and the time is saved together with it, and a confirmation message request and the reminder record are saved in the same step.
4. **Given** a successful booking, **When** the messaging provider is slow or down, **Then** the patient still sees the "booked" screen and the booking stays.
5. **Given** the patient taps "Confirm" twice or their phone retries the request (same booking attempt), **When** the system receives both, **Then** only one appointment exists and both answers show that same appointment.
6. **Given** a request that names another patient's account, **When** a patient submits it, **Then** it is refused and nothing is booked (a patient books only for their own account).
7. **Given** the "is this patient blocked" check, **When** a booking is made in Release 1, **Then** the check always allows booking (the real block arrives in Release 2).
8. **Given** a slow network, **When** no answer arrives within 10 seconds, **Then** the patient is told the result is unknown and is offered to check their appointments before trying again; the booking is never retried automatically.

(source: FR-011, NFR-002, NFR-010)

---

### User Story 3 - A slot is never booked twice (Priority: P1)

If another booking takes the slot while the patient is choosing, the patient is told "this slot was just taken" and is shown the next free slots (same clinic, treatment and dentist choice) to pick again, without starting over.

**Why this priority**: Double-booking is the one failure reception cannot accept; it is an architecture driver.

**Independent Test**: Two patients confirm the same slot at the same moment; exactly one booking succeeds, the other gets the "slot taken" message with next free slots, and only one active appointment exists for that dentist and time.

**Acceptance Scenarios**:

1. **Given** two patients who confirm the same free slot at the same time, **When** both requests are processed, **Then** exactly one appointment is created and the other patient is told the slot was just taken.
2. **Given** a patient told the slot was taken, **When** the message appears, **Then** the next free slots for the same clinic, treatment and dentist choice are shown on the same screen and the patient can pick one and confirm.
3. **Given** a slot taken after "first available", **When** the patient is shown next free slots, **Then** they come from across the clinic's dentists again (at most 10).
4. **Given** a slot that overlaps part of another active appointment of the same dentist, **When** a booking is attempted, **Then** it is refused in the same way, not only when start times are equal.
5. **Given** a cancelled appointment, **When** another patient books its slot, **Then** the booking succeeds (only active appointments block a slot).
6. **Given** a slot that is no longer free for a reason other than a booking (for example, leave was added), **When** the patient confirms, **Then** the patient gets the same "slot no longer available" message with next free slots.

(source: FR-012)

---

### User Story 4 - Prove no double booking under load (Priority: P2)

A test story: an automated concurrency test attacks the same slots with many simultaneous booking attempts and proves that no two active appointments ever overlap for one dentist.

**Why this priority**: The 0-overlap guarantee is a headline quality target; it has to be shown, not assumed.

**Independent Test**: Run the concurrency suite: 1,000 runs, each with simultaneous attempts on the same dentist and slot (and on overlapping slots); after each run count active overlapping appointments.

**Acceptance Scenarios**:

1. **Given** a free slot and at least 30 simultaneous booking attempts for it, **When** a run finishes, **Then** exactly one attempt succeeded, all others got "slot taken", and 0 overlapping active appointments exist.
2. **Given** 1,000 such runs, **When** all finish, **Then** 0 overlapping active appointments were found in 100% of runs.
3. **Given** the same booking attempt sent several times at once with the same retry key, **When** the run finishes, **Then** exactly one appointment exists.
4. **Given** the test report, **When** reviewed, **Then** it lists the number of runs, attempts, successes, conflicts and overlaps found.

(source: FR-012, NFR-002)

---

### User Story 5 - Prove booking speed on a phone network (Priority: P2)

A test story: a load test with realistic phone-network conditions measures how fast free slots appear and how fast a booking is confirmed.

**Why this priority**: The speed targets are customer-visible and must be verified before go-live.

**Independent Test**: Run the load test with 100 concurrent simulated patients on a 4G network profile; read the 95th-percentile timings for slot lists and for booking confirmation.

**Acceptance Scenarios**:

1. **Given** 100 concurrent simulated patients on a 4G profile, **When** they open the slot picker, **Then** free slots are shown within 2 seconds for 95% of requests (server share at most 500 ms at the 95th percentile).
2. **Given** the same load, **When** patients confirm bookings, **Then** the confirmation is shown within 3 seconds for 95% of requests (server share at most 800 ms at the 95th percentile).
3. **Given** the "first available" view for a clinic with all dentists, **When** it is requested under load, **Then** it returns at most 10 slots and meets scenario 1.
4. **Given** the test report, **When** reviewed, **Then** it states pass or fail against these limits and the data volume used (at least a year of appointments for 3 clinics and 10 dentists).

(source: NFR-002)

---

### User Story 6 - Booking works on a phone for a new patient (Priority: P2)

A mobile usability acceptance story: a new patient completes a booking on an Android or iPhone in no more than 5 screens after sign-in, with large tap targets and no sideways scrolling.

**Why this priority**: Patients of all ages use phones; the screens must work without help.

**Independent Test**: Run the booking flow on current Chrome and Safari on an Android phone and an iPhone (or their emulators): count screens after sign-in, measure tap target size, check for sideways scrolling at 320, 360 and 390 px widths.

**Acceptance Scenarios**:

1. **Given** a new patient who has just signed in, **When** they book a visit, **Then** they reach the "booked" screen after 5 screens or fewer (who and what, slot picker, confirm, booked).
2. **Given** every patient screen in this flow, **When** viewed on current Chrome and Safari on Android and iPhone at widths from 320 px, **Then** there is no sideways scrolling.
3. **Given** every button, link, slot and field in this flow, **When** measured, **Then** each tap target is at least 44 px high and wide.
4. **Given** "Back" is used on the phone, **When** the patient returns from a later screen, **Then** their earlier choices are still filled in.
5. **Given** all texts and times in the flow, **When** viewed, **Then** they are in English and times are in India time (IST).

(source: NFR-001, NFR-010)

---

### Edge Cases

- No dentist at the chosen clinic has any free slot in the next 30 days: the screen says so and shows the clinic's phone number.
- The patient waits on the confirm screen so long that the slot is taken or the day has passed: the system treats it as a "slot taken" case.
- A slot that starts in the past or less than the clinic's minimum notice (none is set in Release 1) is never offered.
- The patient's session ends during booking: they sign in again and return to the confirm screen with their choices kept.
- Two different patients book two adjacent slots of one dentist at once: both succeed (adjacent, not overlapping).
- The same patient books two slots at the same time with different dentists: allowed in Release 1 (no rule forbids it).
- The booking request arrives twice because of a flaky network: one appointment only (retry key).
- Daylight saving does not apply in India; all times are IST.
- The patient is blocked (Release 2): the hook exists and always allows in Release 1.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A signed-in patient MUST be able to choose a clinic, an online treatment type and then either a named dentist of that clinic or "first available". (source: FR-011)
- **FR-002**: The system MUST offer only treatment types that are marked bookable online (check-up, cleaning, consultation, 30 minutes each). (source: FR-011)
- **FR-003**: The system MUST offer days from today up to today plus 30 days; the number of days MUST be a setting, with 30 as the default. (source: FR-011)
- **FR-004**: For a named dentist the system MUST show that dentist's free slots for the chosen day; for "first available" it MUST show the earliest free slots across all of that clinic's dentists, earliest first, at most 10. (source: FR-011)
- **FR-005**: The patient MUST choose SMS or WhatsApp for messages about the appointment before confirming; SMS is the default. Remembering the choice for the next booking belongs to feature 006. (source: FR-011)
- **FR-006**: On confirm the system MUST create an appointment with status "booked" for the signed-in patient, recording clinic, dentist, patient, treatment, start, end, channel and who booked it. (source: FR-011)
- **FR-007**: The system MUST allow a patient to book only for their own account; a request for any other account MUST be refused by the server. Booking for family members is Release 2. (source: FR-011)
- **FR-008**: In the same step as the appointment, the system MUST save one "booked" history entry (who, when) and the records that let the confirmation and the reminder be sent. (source: FR-011)
- **FR-009**: The confirmation message MUST be requested as part of the booking and sent after the booking is saved; a messaging problem MUST NOT undo or delay the booking. (source: FR-011, NFR-002)
- **FR-010**: Each booking attempt MUST carry a retry key; repeating an attempt with the same key MUST return the original result and never create a second appointment. (source: FR-012)
- **FR-011**: The system MUST never keep two active appointments for the same dentist whose times overlap, whatever the number of simultaneous attempts. (source: FR-012)
- **FR-012**: When a slot is no longer available at confirm time, the system MUST tell the patient and show the next free slots for the same clinic, treatment and dentist choice, so the patient can pick again. (source: FR-012)
- **FR-013**: The system MUST call a "is this patient blocked from online booking" check before booking; in Release 1 it MUST always answer "not blocked". (source: FR-011)
- **FR-014**: The "booked" screen MUST show clinic, dentist, treatment, date, time (IST) and the chosen channel. (source: FR-011, NFR-010)
- **FR-015**: A booking request that gets no answer in 10 seconds MUST be shown as "result unknown, check your appointments"; booking writes MUST NOT be retried automatically. (source: FR-012, NFR-002)
- **FR-016**: Free slots MUST be shown within 2 seconds and a booking confirmed within 3 seconds for 95% of requests on a 4G phone network. (source: NFR-002)
- **FR-017**: Every patient screen in the booking flow MUST work on current Chrome and Safari on Android and iPhone without sideways scrolling and without installing anything. (source: NFR-001)
- **FR-018**: A new patient MUST be able to book in 5 screens or fewer after sign-in, with every tap target at least 44 px. (source: NFR-010)
- **FR-019**: All booking texts MUST be in English and times in IST; per the project constitution, patient name and phone number MUST NOT appear in logs. (source: NFR-010)

### Key Entities *(include if feature involves data)*

- **Appointment**: one visit of one patient with one dentist at one clinic for one treatment type, with start, end, status (starts as "booked"), message channel and who booked it. Owned by the booking capability; later features change its status.
- **Appointment history entry**: one record per status change with the previous and new status, who made the change, when and an optional reason. This feature writes the first one ("booked").
- **Free slot**: a start time on the hour or half hour for a dentist at a clinic that is inside working hours and not taken, not on leave and not in a break. Calculated by the scheduling capability (MOD-02); read here, never stored.
- **Booking attempt (retry key)**: the identifier a booking request carries so a repeat returns the same result.
- **Booking setting**: the number of days ahead a patient may book (default 30).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of 1,000 simultaneous-booking test runs end with 0 overlapping active appointments for any dentist.
- **SC-002**: Free slots are shown within 2 seconds for 95% of requests and a booking is confirmed within 3 seconds for 95% of requests, on a 4G phone network with 100 patients at once.
- **SC-003**: A new patient completes a booking in 5 screens or fewer after sign-in in 100% of mobile test runs.
- **SC-004**: 100% of patient screens in the flow show no sideways scrolling and have tap targets of at least 44 px on current Chrome and Safari on Android and iPhone.
- **SC-005**: When a slot is lost to another booking, 100% of affected patients see the "just taken" message and at least one alternative slot (if any is free) in the same screen, with no loss of their other choices.
- **SC-006**: A repeated booking request never produces more than one appointment (0 duplicates in the test runs).
- **SC-007**: 0 bookings made by one patient for another patient's account in the role-separation tests.

## Assumptions

- Assumed: in Release 1 a patient books for themselves only; the "who is the visit for" choice shows only the patient themselves and may be pre-selected, without counting as an extra screen (open question Q1, Q-007 family members, Release 2).
- Assumed: the day-31 boundary follows ASM-010, today plus 30 days inclusive, and is a setting.
- Assumed: a repeated request with the same retry key after a "slot taken" answer returns that same "slot taken" answer (open question Q2).
- Assumed: the channel choice is sent with the booking request and stored on the appointment; saving it as the patient's default for next time is handled by the messaging and identity features (open question Q3).
- Patient sign-in, clinics, dentists, hours, leave, treatment types and the free-slot calculation come from features 001 and MOD-02 and are available.
- Reception booking (FR-020), reschedule, cancel and the patient's appointment list are separate features.
- Target users have a phone with current Chrome or Safari and a 4G connection.
