# Feature Specification: Patient online booking

**Feature Branch**: `004-online-booking`

**Created**: 2026-11-16

**Status**: Draft

**Input**: User description: "Patient online booking. A signed-in patient books online: clinic, an online treatment type, a dentist or 'first available', then a free slot within the next 30 days. A slot is never booked twice. The patient chooses SMS or WhatsApp for messages about the appointment; the choice is remembered. Free slots shown within 2 s and a booking confirmed within 3 s for 95% of requests on 4G. Covers prd.md FR-011, FR-012, FR-013, NFR-002. Persona P-01 Patient. Go-live firm 1 March 2027 (MVP)."

## Context

BrightSmile Dental has 2 clinics in Bengaluru (about 450 appointments a week). Today patients can book only by phone in clinic hours. This feature lets a signed-in patient book a visit on the website from a phone at any hour. Sign-in (feature 002), clinic schedules and free-slot rules (feature 003), the confirmation message itself (feature 007), family members (feature 008, Release 2) and the repeat no-show block (feature 009, Release 2) are separate features. This feature leaves the places where they connect (a signed-in patient, a confirmation call, a "who is the visit for" step with one choice, a "blocked?" check that always answers "not blocked") and works without them.

Screens for the patient: who and what, slot picker, confirm, booked. A new patient reaches the booked screen in 5 screens or fewer after sign-in (NFR-010, owned by feature 001; this feature must meet it for its screens).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Book a free slot online (Priority: P1)

A signed-in patient opens the booking flow on a phone, chooses who the visit is for (themselves; family members arrive with feature 008), the clinic and one of the online treatment types (check-up, cleaning or consultation, 30 minutes each). They then choose a dentist at that clinic or "first available", pick a day within the next 30 days and a free slot, confirm, and see the booked appointment. "First available" shows the earliest free slots across all of that clinic's dentists. The system records the booking and asks for the confirmation message to be sent.

**Why this priority**: This is the reason for the project: patients book without phoning in clinic hours. Without it nothing else in the feature has value.

**Independent Test**: Sign in as a test patient, book a check-up at a clinic with a named dentist, then book a cleaning with "first available". Both appear as booked appointments in the right clinic, with the right dentist, start and end time, and a confirmation request is recorded for each. Delivering this story alone (with SMS as the only channel) is a viable MVP slice.

**Acceptance Scenarios**:

1. **Given** a signed-in patient on the first booking screen, **When** they choose themselves, a clinic and "check-up", **Then** they can continue to the dentist and slot step, and only the online treatment types (check-up, cleaning, consultation) are offered.
2. **Given** a clinic with several dentists working in the next 30 days, **When** the patient chooses "first available", **Then** the earliest free slots across all that clinic's dentists are shown, each with its dentist and time, soonest first.
3. **Given** a patient who chose a named dentist, **When** they open the day picker, **Then** only days from today to 30 days after today are offered (1 March shows up to 31 March), and the free slots of that dentist for the chosen day are listed, each on the hour or half hour.
4. **Given** a patient on the confirm screen with a free slot, **When** they confirm, **Then** one appointment is created with status "booked" for that patient, clinic, dentist, treatment, start and end, and the booked screen shows clinic, dentist, treatment, date and time in India time.
5. **Given** a confirmed booking, **When** it is saved, **Then** a request to send the booking confirmation in the patient's chosen channel is recorded together with the booking (so it cannot be lost) for the confirmation feature, and the patient's screen does not wait for the message to be delivered.
6. **Given** a patient who is not signed in, **When** they try to open or submit any booking step, **Then** they are sent to sign-in and nothing is booked.
7. **Given** a patient who asks to book a treatment that patients cannot book online (for example a root canal), **When** the request reaches the system, **Then** it is refused with a clear message to phone the clinic, and nothing is booked.
8. **Given** a patient for whom the repeat no-show check (feature 009) says "blocked", **When** they start to book, **Then** the page says online booking is not available and shows the clinic's phone number. Until feature 009 exists the check always says "not blocked".
9. **Given** a new patient who has just signed in, **When** they book, **Then** they reach the booked screen in 5 screens or fewer, every tap target is at least 44 px, and no screen needs sideways scrolling on a phone.

(source: FR-011, NFR-002)

---

### User Story 2 - A slot is never booked twice (Priority: P1)

If another booking takes the slot while the patient is choosing, the patient is told the slot has just been taken and is shown the next free slots, so they can pick another without starting again. If the patient's confirm request is repeated (a double tap or a network retry), only one appointment is made.

**Why this priority**: A double-booked dentist is the worst failure for a clinic; the clinic must be able to trust the online diary.

**Independent Test**: Start two bookings for the same dentist and slot, confirm both. Exactly one succeeds; the other is told "slot taken" and is shown the next free slots. Repeat the same confirm request twice and see one appointment.

**Acceptance Scenarios**:

1. **Given** two patients who both chose the same dentist and slot, **When** both confirm at nearly the same time, **Then** exactly one booking is made and the other patient is told the slot was just taken.
2. **Given** a patient told the slot is taken, **When** the message is shown, **Then** it comes with the next free slots (same clinic, treatment and dentist choice as before) and the patient can choose one and confirm without re-entering clinic or treatment.
3. **Given** a patient who confirms and the screen does not respond, **When** the same confirm request is sent again with the same request key, **Then** the system returns the original booking and does not create a second appointment.
4. **Given** a slot that is already booked, **When** a booking for it arrives by any route, **Then** it is never saved as a second active appointment for that dentist.
5. **Given** a dentist who already has an active appointment (including a longer one made by reception), **When** a booking is requested whose time overlaps it even in part, **Then** it is refused as "slot taken".
6. **Given** a patient who is told "slot taken" and there are no further free slots in the next 30 days for their choice, **When** the answer is shown, **Then** the patient is told no slots are free and offered the clinic's phone number.

(source: FR-012)

---

### User Story 3 - Choose SMS or WhatsApp, remembered for next time (Priority: P1)

On the confirm screen the patient chooses SMS or WhatsApp for messages about this appointment. The first time the choice is SMS. When they confirm, the choice is saved with the appointment and remembered as their choice for their next booking.

**Why this priority**: The confirmation and reminder messages depend on the channel; it is part of the booking and costs the patient one tap.

**Independent Test**: A new patient sees SMS selected on the confirm screen. They choose WhatsApp and confirm; the appointment holds WhatsApp. On the next booking, WhatsApp is already selected. They switch to SMS for that booking; the next booking after that starts on SMS.

**Acceptance Scenarios**:

1. **Given** a patient who has never booked online, **When** the confirm screen opens, **Then** SMS is selected.
2. **Given** a patient who selects WhatsApp and confirms, **When** the booking is saved, **Then** the appointment holds channel WhatsApp and the patient's remembered choice becomes WhatsApp.
3. **Given** a patient whose remembered choice is WhatsApp, **When** they start another booking, **Then** the confirm screen starts with WhatsApp selected and they can change it.
4. **Given** a booking that fails because the slot was taken, **When** the patient is shown other slots, **Then** their channel choice on screen is kept, and the remembered choice changes only when a booking is confirmed.
5. **Given** a channel value other than SMS or WhatsApp in a request, **When** it is submitted, **Then** it is refused and nothing is booked.

(source: FR-013)

---

### User Story 4 - Prove that concurrent bookings never overlap (Priority: P2)

The delivery team can run a repeatable test that makes many patients try to book the same dentist and slot at once and checks the diary afterwards. It shows that no dentist ever has two overlapping active appointments.

**Why this priority**: This is a main design risk of the system (quality scenario QA-003). It must be proven before go-live, but patients do not see it, so it follows the booking stories.

**Independent Test**: Run the concurrency test suite against a staging-like database: 1,000 runs, each with many simultaneous attempts on one dentist and slot, with some attempts overlapping a neighbouring slot. Every run ends with 0 overlapping active appointments and exactly one winner per contested slot.

**Acceptance Scenarios**:

1. **Given** a free slot and 30 simultaneous booking attempts for it, **When** all complete, **Then** exactly one is booked, 29 are told "slot taken", and 0 overlapping active appointments exist for that dentist.
2. **Given** 1,000 concurrent-attempt runs, **When** the suite finishes, **Then** 0 overlapping active appointments for one dentist are found in 100% of the runs.
3. **Given** a run that includes up to 100 simultaneous attempts (the design load), **When** it finishes, **Then** the same result holds.
4. **Given** repeated attempts that carry the same request key, **When** the run finishes, **Then** they produce one appointment each, not more.
5. **Given** the test is part of the delivery pipeline, **When** it fails, **Then** the release is stopped.

(source: FR-012, NFR-002)

---

### User Story 5 - Booking is quick on a phone network (Priority: P2)

On a 4G phone, free slots appear within 2 seconds and a confirmed booking within 3 seconds, for 95% of requests. The delivery team can run a performance check that shows this at the expected load.

**Why this priority**: Patients give up on slow screens; the targets are our proposals (open for confirmation at the client gate), so they must be measured rather than assumed.

**Independent Test**: Run the performance check with 100 simulated concurrent patients (about 35 requests a second) browsing slots and booking. Report the 95th percentile of slot list and booking times, on the server and as measured from a 4G-like client.

**Acceptance Scenarios**:

1. **Given** 100 concurrent simulated patients, **When** they open the slot picker, **Then** 95% of slot lists are shown within 2 seconds on a 4G-like connection, and the server answers 95% within 500 ms.
2. **Given** the same load, **When** patients confirm bookings, **Then** 95% of confirmations are shown within 3 seconds on a 4G-like connection, and the server answers 95% within 800 ms.
3. **Given** a booking is confirmed, **When** the request is timed, **Then** the time to send the confirmation message is not part of it (the message is sent after the booking is saved).
4. **Given** the check runs on a pull request or before release, **When** a target is missed, **Then** the report names which target and the release owner sees it.
5. **Given** a "first available" request across all dentists of a clinic, **When** it is timed, **Then** it also meets the 2 second target.

(source: NFR-002)

---

### Edge Cases

- Slot taken while the patient is choosing: the patient is told and shown the next free slots (User Story 2).
- A slot that just ran out of time: a slot whose start has already passed is never offered or booked.
- The patient's phone loses signal after tapping confirm: a retry with the same request key returns the original booking, never a second one.
- A dentist's leave, break or schedule change makes a shown slot unavailable before confirm: the booking is refused with the same "slot taken" style answer and fresh slots are shown.
- A treatment type or clinic made inactive while the patient is choosing: the request is refused with a clear message and the patient restarts at the first screen.
- A request that names a patient, clinic or dentist the signed-in person is not allowed to use: refused; the patient is always taken from the sign-in, never from the request.
- A patient with no WhatsApp: they can still choose SMS; the system does not check that a phone has WhatsApp (assumption below).
- No free slot at all in 30 days for the chosen clinic and treatment: the patient is told and shown the clinic's phone number.
- The next-slots list after "slot taken" is built from live data and may itself be taken by the time the patient taps; the same handling applies again.
- The patient's remembered channel is changed by a booking made in another browser at the same time: the later confirmed booking wins.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A signed-in patient MUST be able to book an appointment online by choosing a clinic, an online treatment type, a dentist or "first available", and a free slot, in that order. (source: FR-011)
- **FR-002**: The system MUST offer only treatment types that are marked bookable online (check-up, cleaning, consultation, 30 minutes each) and MUST refuse an online booking for any other type. (source: FR-011)
- **FR-003**: The system MUST offer only slots from today up to 30 days after today (a setting owned by clinic scheduling), starting on the hour or half hour, that are free according to clinic scheduling, and never a slot that has already started. (source: FR-011)
- **FR-004**: For "first available" the system MUST show the earliest free slots across all that clinic's dentists, soonest first, each with its dentist. The list shows the next 10 slots; to see other days the patient chooses a named dentist and a day. (source: FR-011)
- **FR-005**: On confirm the system MUST create one appointment with patient, clinic, dentist, treatment, start, end, status "booked", channel and "booked by" (the patient), together with its history record, in one all-or-nothing step. (source: FR-011)
- **FR-006**: The system MUST take the patient from the sign-in, never from the request, and MUST refuse booking steps from anyone who is not a signed-in patient. (source: FR-011)
- **FR-007**: The system MUST ask the repeat no-show check whether the patient is blocked before offering slots and again before saving; when it says "blocked" the patient sees that online booking is not available and the clinic's phone number. Until the repeat no-show feature exists, the check MUST answer "not blocked". (source: FR-011)
- **FR-008**: The system MUST record, together with the booking and in the same all-or-nothing step, a request to send the booking confirmation in the chosen channel; the message is delivered after the booking is saved and never inside the patient's request. The message content and delivery belong to the messaging feature. (source: FR-011)
- **FR-009**: The system MUST never save two active appointments for one dentist whose times overlap, whatever the order or timing of requests. (source: FR-012)
- **FR-010**: When a booking cannot be saved because the slot is taken, the system MUST tell the patient the slot was just taken and return the next free slots for the same clinic, treatment and dentist choice, so the patient can pick one without starting again. (source: FR-012)
- **FR-011**: Every confirm request MUST carry a request key; a repeated request with the same key and the same patient MUST return the original result and MUST NOT create another appointment. (source: FR-012)
- **FR-012**: The system MUST let the patient choose SMS or WhatsApp for messages about the appointment on the confirm screen, SMS selected the first time. (source: FR-013)
- **FR-013**: The system MUST save the chosen channel on the appointment and, when the booking is confirmed, remember it as the patient's choice for their next booking. A failed booking MUST NOT change the remembered choice. (source: FR-013)
- **FR-014**: The system MUST accept only SMS or WhatsApp as the channel. (source: FR-013)
- **FR-015**: The system MUST show free slots within 2 seconds and confirm a booking within 3 seconds for 95% of requests on a 4G phone, with server answers for 95% of slot lists within 500 ms and of bookings within 800 ms at the design load of 100 concurrent patients (about 35 requests a second). (source: NFR-002)
- **FR-016**: The system MUST provide a repeatable concurrency test showing 0 overlapping active appointments for one dentist in 100% of 1,000 concurrent-attempt runs, and a repeatable performance check for the targets in FR-015. (source: FR-012, NFR-002)
- **FR-017**: The patient screens of this feature (who and what, slot picker, confirm, booked) MUST let a new patient finish in 5 screens or fewer after sign-in, with tap targets of at least 44 px and no sideways scrolling on a phone, in English with times in India time. (source: FR-011)
- **FR-018**: The system MUST NOT write the patient's name, phone number or birth year to logs for any booking step. (source: FR-011)

### Key Entities

- **Appointment**: a booked visit. Holds clinic, dentist, patient (the person the visit is for), treatment type, start, end, status (booked, arrived, no-show, cancelled by the patient, cancelled by the clinic), channel (SMS or WhatsApp) and who booked it. Owned by the booking capability. This feature creates appointments with status "booked" only.
- **Appointment history record**: one entry per status change (here: the first entry, "booked") with who and when. Shared with feature 005.
- **Booking request key**: a value the patient's screen sends with each confirm so a repeat is recognised and answered with the original result.
- **Patient account**: the signed-in person's account; holds the remembered message channel (SMS or WhatsApp, SMS at first).
- **Slot**: a free 30 minute time with one dentist at one clinic for one treatment; calculated by clinic scheduling, not stored as a record.
- **Confirmation request**: the call that asks the messaging feature to send the confirmation after the booking is committed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new patient books an appointment in 5 screens or fewer after sign-in.
- **SC-002**: In 100% of 1,000 concurrent-attempt test runs, no dentist has two overlapping active appointments.
- **SC-003**: 95% of free-slot views appear within 2 seconds and 95% of booking confirmations within 3 seconds on a 4G phone, with 100 patients using the site at once.
- **SC-004**: When two patients choose the same slot, exactly one is booked and the other sees "slot taken" with other free slots in the same screen, 100% of the time in testing.
- **SC-005**: A repeated confirm (double tap or retry) never creates a second appointment, in 100% of tests.
- **SC-006**: A returning patient's last chosen channel is pre-selected on their next booking, 100% of the time in testing.
- **SC-007**: Every booking screen has tap targets of at least 44 px and needs no sideways scrolling on current Chrome and Safari on Android and iPhone.

## Assumptions

- A signed-in patient and their patient record already exist (feature 002); this feature takes who they are from the sign-in. In the MVP the visit is always for the account holder; the "who is the visit for" step shows one choice until family members (feature 008, Release 2) exist.
- Clinics, dentists, hours, breaks, leave, treatment types and the free-slot calculation exist (feature 003). The 30-day window is "today and the 30 days after" (1 March shows up to 31 March), kept as a setting (ASM-010, PD-002, SA-007).
- The confirmation message, its template and its delivery belong to feature 007. Here we only raise the request after commit and keep the chosen channel; if feature 007 is not ready, the request is recorded and not sent.
- The repeat no-show check belongs to feature 009 (Release 2). Until then an interface answers "not blocked" and a blocked answer shows the clinic's phone number.
- Targets in NFR-002 are our proposals (PD-008, ASM-006) and are to be confirmed with the client at the gate; the performance check reports against them.
- Times are stored in UTC and shown in India time (IST); screens are in English only.
- NFR-002 also mentions the reception day view; that screen belongs to feature 006 and is not covered here.
- The design load is 30 patients booking at once, designed for 100 (about 35 requests a second).
- The system does not check that a phone number has WhatsApp. If a WhatsApp message cannot be delivered, feature 007 handles it.
- Open question Q1 (see `clarifications.md`): no limit on how many upcoming online appointments one patient may hold is assumed.
- Open question Q2: a slot may be booked online up to its start time; no minimum notice is assumed.
- Open question Q3: the patient may hold two appointments at the same time with different dentists; no check for the same patient overlapping is assumed.
- Receptionists book by phone through reception screens in feature 006; those bookings use the same rule that no slot is booked twice.
