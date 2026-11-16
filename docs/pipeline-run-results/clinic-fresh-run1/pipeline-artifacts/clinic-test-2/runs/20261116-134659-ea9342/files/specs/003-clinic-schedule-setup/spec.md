# Feature Specification: Clinics, dentist hours, leave, treatments and free slots

**Feature Branch**: `003-clinic-schedule-setup`

**Created**: 2026-11-16

**Status**: Draft

**Input**: User description: "Clinics, dentist hours, leave, treatments and free slots. Covers prd.md ids FR-001, FR-007, FR-008, FR-009, FR-010. The practice manager (P-04) sets up clinics, dentists, weekly hours and breaks, leave and the treatment list; reception (P-02) reads the list of appointments to move; the system works out free slots. A third clinic must arrive as data, with no code change and no deploy."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Clinics and dentists held as data (Priority: P1)

The practice manager keeps the list of clinics (name, address, phone) and the list of dentists in the staff screens. Today there are 2 clinics (Indiranagar and Whitefield) and 6 dentists. When a third clinic opens, the manager adds it in the same screen; it is then offered to patients and reception with no code change and no deploy. A clinic or a dentist that is no longer in use is marked inactive, not deleted. Every appointment belongs to exactly one clinic and exactly one dentist, so the other features can only pick from active clinics and dentists that this list holds. (source: FR-001)

**Why this priority**: Every other part of the system (hours, slots, bookings, day view) hangs on clinics and dentists existing as data. Without it nothing can be set up.

**Independent Test**: As the practice manager, add a third clinic and a new dentist in the staff screens. Both appear in the lists returned to patient and reception screens straight away, with no restart or deploy. Mark the clinic inactive and see it disappear from the lists offered for new bookings.

**Acceptance Scenarios**:

1. **Given** the practice manager is signed in and 2 active clinics exist, **When** they add a clinic with a name, address and phone number, **Then** the clinic is saved as active and appears in the clinic list for all roles without any deploy. (source: FR-001)
2. **Given** a dentist exists, **When** the manager edits the dentist's name or marks the dentist inactive, **Then** the change is saved and an inactive dentist is no longer offered for new bookings. (source: FR-001)
3. **Given** a clinic or dentist that has appointments, **When** the manager marks it inactive, **Then** existing appointments are kept unchanged and the record is not deleted. (source: FR-001)
4. **Given** a signed-in receptionist, dentist or patient, **When** they try to add, edit or deactivate a clinic or a dentist, **Then** the system refuses and nothing changes. (source: FR-001)
5. **Given** a clinic name already in use by an active clinic, **When** the manager saves a second clinic with the same name, **Then** the system refuses it and says why. (source: FR-001)

---

### User Story 2 - Treatment types with duration and online flag (Priority: P1)

The system holds the list of treatment types, each with a name, a duration in minutes and a flag saying whether patients may book it online. The online types are check-up, cleaning and consultation, 30 minutes each. Other types (for example root canal and extraction) are 60 or 90 minutes and are booked by reception only. The practice manager adds, edits and deactivates types in a "Treatments" screen. Patients see only active online types; reception sees all active types. (source: FR-009)

**Why this priority**: The duration of a treatment decides how long a free slot must be, and the online flag decides what patients may book. Booking and slot search cannot work without it.

**Independent Test**: As the manager, add "Root canal" with 90 minutes and online off, and change "Check-up" to 30 minutes online on. Ask for the list as a patient (only active online types) and as reception (all active types) and check both.

**Acceptance Scenarios**:

1. **Given** the system is set up, **When** any signed-in user asks for the treatment list, **Then** check-up, cleaning and consultation are present as online types of 30 minutes each. (source: FR-009)
2. **Given** the manager is signed in, **When** they add a treatment type with a name, a duration and the online flag off, **Then** the type is saved and is visible to reception but not to patients. (source: FR-009)
3. **Given** a treatment type, **When** the manager changes its duration or online flag, **Then** the change applies to slots and bookings made from then on and does not change existing appointments. (source: FR-009)
4. **Given** a treatment type, **When** the manager marks it inactive, **Then** it is no longer offered for new bookings and existing appointments keep it. (source: FR-009)
5. **Given** a duration that is not a positive multiple of 30 minutes, **When** the manager saves a treatment type, **Then** the system refuses it and says why. (source: FR-009, FR-010)
6. **Given** a signed-in receptionist, dentist or patient, **When** they try to add or edit a treatment type, **Then** the system refuses it. (source: FR-009)

---

### User Story 3 - Weekly working hours and breaks per dentist per clinic (Priority: P1)

The practice manager sets, for each dentist and each clinic the dentist works at, the weekly working hours: for each weekday, a start and an end, plus any breaks (for example lunch). A dentist can work at more than one clinic on set days, for example Monday to Wednesday at Indiranagar and Thursday to Saturday at Whitefield. The manager opens the "Dentists and hours" screen, picks a dentist and a clinic, and edits the week. (source: FR-007, FR-001)

**Why this priority**: Working hours minus breaks are the raw material for free slots. No hours means no slots, so no online booking.

**Independent Test**: As the manager, give a dentist Monday 09:00–17:00 with a 13:00–14:00 break at Indiranagar and Thursday 10:00–18:00 at Whitefield. Reading the week back shows exactly this. Try to give the same dentist overlapping hours at the other clinic on Monday and see it refused.

**Acceptance Scenarios**:

1. **Given** a dentist and a clinic, **When** the manager sets Monday 09:00–17:00 with a break 13:00–14:00, **Then** the hours and the break are saved and shown again when the week is opened. (source: FR-007)
2. **Given** a dentist who works Monday at clinic A, **When** the manager adds Thursday hours at clinic B, **Then** both are kept and the dentist is shown as working at both clinics on those days. (source: FR-001, FR-007)
3. **Given** a dentist with hours at clinic A on Monday 09:00–17:00, **When** the manager saves Monday 15:00–19:00 for the same dentist at clinic B, **Then** the system refuses it because the dentist cannot be at two clinics at the same time. (source: FR-001, FR-007)
4. **Given** a weekday's hours, **When** the manager enters an end that is not after the start, a break outside the hours, or two overlapping breaks, **Then** the system refuses it and names the problem. (source: FR-007)
5. **Given** a dentist with weekly hours, **When** the manager removes a weekday's hours (a day off), **Then** that weekday no longer produces free slots for that dentist at that clinic. (source: FR-007)
6. **Given** a signed-in receptionist, dentist or patient, **When** they try to change weekly hours, **Then** the system refuses it. A receptionist or dentist may read hours. (source: FR-007)
7. **Given** appointments already booked outside newly changed hours, **When** the manager saves the change, **Then** the hours are saved and the system does not move or cancel those appointments. (source: FR-007, FR-008)

---

### User Story 4 - Free slots for a clinic, dentist and treatment (Priority: P1)

For one clinic and one date range, the system works out each dentist's free slots: the dentist's working hours at that clinic, minus breaks, minus leave, minus appointments that are already booked (at any clinic, because a dentist cannot be in two places). Slots start on the hour or half hour and are as long as the chosen treatment. The system can also give "first available": the earliest free slots across all of that clinic's dentists, 10 at a time, with further pages on request. A patient only sees online treatment types and slots inside the booking horizon (today and the 30 days after; the number of days is a setting); reception can search any active type. Slots are shown in India time. (source: FR-010, FR-001)

**Why this priority**: The booking features (online and reception) are built on this calculation. It also carries the speed target: free slots must show within 2 seconds for 95% of requests on a 4G phone.

**Independent Test**: With a dentist's Monday 09:00–17:00, break 13:00–14:00, leave 15:00–16:00 and a booked 10:00–10:30 appointment, ask for Monday's 30-minute slots and check that exactly the expected start times come back. Ask for a 90-minute treatment and check that every returned slot fits fully inside free time. Ask for "first available" and check the first page has 10 slots in time order and the next page continues.

**Acceptance Scenarios**:

1. **Given** a dentist working Monday 09:00–17:00 at a clinic with a break 13:00–14:00, **When** free 30-minute slots are requested for that Monday, **Then** slots start at 09:00, 09:30 and so on on the hour or half hour, none start in 13:00–13:59, and the last one starts at 16:30. (source: FR-010)
2. **Given** the same dentist with an appointment booked 10:00–10:30, **When** slots are requested, **Then** the 10:00 slot is not offered and 10:30 is. (source: FR-010)
3. **Given** the same dentist is booked at another clinic on that Monday at 11:00–11:30, **When** slots are requested for this clinic, **Then** the 11:00 slot is not offered. (source: FR-010, FR-001)
4. **Given** leave recorded for that dentist from 15:00 to 16:00 on that Monday, **When** slots are requested, **Then** no slot overlaps 15:00–16:00. (source: FR-010, FR-008)
5. **Given** a 90-minute treatment, **When** slots are requested, **Then** a slot is offered only if the whole 90 minutes fit in working time without touching a break, leave or booked appointment. (source: FR-010, FR-009)
6. **Given** a signed-in patient, **When** they ask for slots, **Then** only online treatment types are accepted, only slots from now up to the end of the booking horizon are returned, and only active clinics and dentists are included. (source: FR-010, FR-009)
7. **Given** a clinic with several dentists, **When** "first available" is requested, **Then** the 10 earliest free slots across the clinic's dentists are returned in time order, each with its dentist, and asking for the next page returns the following 10. (source: FR-010)
8. **Given** a date range with no free slot, **When** slots are requested, **Then** an empty list is returned (not an error). (source: FR-010)
9. **Given** a request for slots at a clinic or dentist that is inactive, or a treatment type that is inactive, **When** it is made, **Then** no slots are returned. (source: FR-010, FR-001)
10. **Given** a booking made by another part of the system just before the request, **When** slots are requested, **Then** that appointment is already excluded. (source: FR-010)

---

### User Story 5 - Record dentist leave (Priority: P2)

The practice manager records a dentist's leave, either for whole days (from a first day to a last day) or for part of a day (a day with a start time and an end time). Leave applies to the dentist at every clinic. As soon as leave is saved, the system shows the manager the appointments already booked in that time, so reception can move them. The system never moves or cancels them by itself. Leave removes free slots for that dentist at once. A leave entry entered by mistake can be deleted. (source: FR-008)

**Why this priority**: Needed before go-live so absences do not leave patients booked with a dentist who is away, but the first bookings can be made before any leave exists.

**Independent Test**: As the manager, record a whole-day leave on a day when the dentist has 3 booked appointments (using the in-process appointment stand-in until the booking feature exists). The answer lists those 3 appointments, none is changed, and free slots for that day are empty. Record a part-day leave and check only overlapping appointments are listed.

**Acceptance Scenarios**:

1. **Given** a dentist, **When** the manager records leave for whole days from a first day to a last day, **Then** the leave is saved from the start of the first day to the end of the last day in India time. (source: FR-008)
2. **Given** a dentist, **When** the manager records part-day leave with a date, a start time and an end time, **Then** the leave is saved for exactly that time. (source: FR-008)
3. **Given** booked appointments that overlap the new leave, **When** the leave is saved, **Then** the response and screen list each of those appointments (date, time, clinic, patient name, phone number, treatment) and the system does not change any of them. (source: FR-008)
4. **Given** an appointment that only partly overlaps the leave, **When** the leave is saved, **Then** that appointment is listed too. (source: FR-008)
5. **Given** cancelled appointments or appointments outside the leave time, **When** the leave is saved, **Then** they are not listed. (source: FR-008)
6. **Given** saved leave, **When** free slots are requested for those days, **Then** no slot overlaps the leave. (source: FR-008, FR-010)
7. **Given** a leave end that is not after its start, or a leave that has already ended, **When** the manager saves it, **Then** the system refuses it and says why. (source: FR-008)
8. **Given** leave entered by mistake, **When** the manager deletes it, **Then** slots in that time come back and the appointments are no longer on any to-move list because of it. (source: FR-008)
9. **Given** a signed-in receptionist, dentist or patient, **When** they try to record or delete leave, **Then** the system refuses it. (source: FR-008)

---

### User Story 6 - Reception sees the appointments to move (Priority: P2)

Reception opens a "To move" list for their own clinic. It shows the booked appointments that fall inside a dentist's leave at that clinic, earliest first, so the receptionist can phone the patient and move the visit. The list updates by itself: an appointment disappears from it once it has been moved or cancelled. A receptionist never sees another clinic's list; the practice manager can see the list of any clinic. This feature only lists; moving an appointment is done in the reception features. (source: FR-008)

**Why this priority**: It is how a leave becomes action. It depends on leave (User Story 5) and on appointments from the booking feature, so it follows them.

**Independent Test**: With leave covering two appointments at Indiranagar and one at Whitefield, sign in as an Indiranagar receptionist and check only the two Indiranagar appointments appear. Cancel one of them (through the booking stand-in) and check it drops off the list.

**Acceptance Scenarios**:

1. **Given** leave that covers booked appointments at the receptionist's clinic, **When** the receptionist opens the to-move list, **Then** those appointments are listed with date, time, dentist, patient name, phone number and treatment, earliest first. (source: FR-008)
2. **Given** leave that also covers appointments at another clinic, **When** the receptionist asks for the list, **Then** only their own clinic's appointments are returned, and asking for another clinic is refused. (source: FR-008)
3. **Given** an appointment on the list, **When** it is moved to a time outside the leave or cancelled, **Then** it no longer appears on the next read. (source: FR-008)
4. **Given** nothing to move, **When** the list is opened, **Then** it says there is nothing to move. (source: FR-008)
5. **Given** the practice manager is signed in, **When** they ask for the to-move list of any clinic, **Then** it is returned. (source: FR-008)
6. **Given** a patient or dentist role, **When** they ask for the to-move list, **Then** the system refuses it. (source: FR-008)

---

### Edge Cases

- A dentist works at two clinics on the same weekday on different hours (morning at one, afternoon at the other): allowed if the hours do not overlap; a booking at one clinic still removes the same time at the other.
- Leave spans several days and clinics: it applies to the dentist at every clinic and is shown on every affected clinic's to-move list.
- A treatment longer than the gap between a break and the next appointment: no slot is offered there.
- A working day whose start is not on the half hour (for example 09:15): the first slot starts at 09:30 (slots start on the hour or half hour only).
- The date range requested is empty, reversed or longer than the allowed maximum: refused with a clear message.
- Slots earlier than the current time today are never offered.
- Weekly hours changed after appointments were booked outside the new hours: appointments are kept and are not placed on the to-move list (see Assumption A-5 and Q1).
- Clinic, dentist or treatment type made inactive while appointments exist: appointments remain; no new bookings (see Q2).
- The appointment data from the booking feature is not available (for example before it is built): the feature runs against a stand-in that returns no appointments, so slots are computed from hours, breaks and leave only.
- Two managers edit the same dentist's week at the same time: the last save wins and the screen shows the saved week when reopened.
- Times are entered and shown in India time (IST) and stored in UTC; leave across a day boundary keeps the same wall-clock times.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST hold clinics (name, address, phone, active) and dentists (name, active) as data that the practice manager can add, edit and mark inactive without a code change or deploy, so that a third clinic can be added by data only. (source: FR-001)
- **FR-002**: The system MUST NOT delete a clinic, dentist or treatment type; it MUST mark it inactive, keep existing appointments unchanged and stop offering it for new bookings. (source: FR-001, FR-009)
- **FR-003**: The system MUST let a dentist work at more than one clinic on set weekdays, and MUST refuse hours that put the same dentist at two clinics at overlapping times on one weekday. (source: FR-001, FR-007)
- **FR-004**: The system MUST expose clinics, dentists and treatment types to every signed-in role for reading (patients see only active records and, for treatments, only active online types), and MUST allow only the practice manager to create or change them. (source: FR-001, FR-009)
- **FR-005**: The system MUST let the practice manager set, for each dentist at each clinic, weekly working hours (a start and an end per weekday) with zero or more breaks per weekday, and MUST reject an end not after the start, a break outside the working hours and breaks that overlap. (source: FR-007)
- **FR-006**: The system MUST let the practice manager remove a weekday's hours for a dentist at a clinic, and MUST show the saved week when it is reopened. (source: FR-007)
- **FR-007**: The system MUST keep appointments that fall outside changed hours untouched. (source: FR-007, FR-008)
- **FR-008**: The system MUST let the practice manager record leave for a dentist as whole days (first day to last day) or a part day (date, start time, end time), apply it to the dentist at every clinic, refuse leave that ends before it starts or has already ended, and delete a leave entry. (source: FR-008)
- **FR-009**: The system MUST, when leave is saved, return the list of appointments already booked that overlap the leave (fully or partly), excluding cancelled appointments, and MUST NOT move, cancel or change any appointment itself. (source: FR-008)
- **FR-010**: The system MUST give reception a "to move" list for their own clinic (and the practice manager the list for any clinic), showing date, time, dentist, patient name, phone number and treatment, earliest first, computed from current data so that moved or cancelled appointments leave the list. (source: FR-008)
- **FR-011**: The system MUST refuse the to-move list of a clinic other than the receptionist's own, and MUST refuse it to patients and dentists. (source: FR-008)
- **FR-012**: The system MUST hold treatment types with name, duration in minutes, online flag and active flag; durations MUST be a positive multiple of 30 minutes. The three online types check-up, cleaning and consultation, 30 minutes each, MUST exist at first use. (source: FR-009)
- **FR-013**: The system MUST let patients book only active online treatment types and let reception use every active type (for example root canal, extraction at 60 or 90 minutes, reception only). (source: FR-009)
- **FR-014**: The system MUST compute free slots for one clinic, one date range and one treatment type (optionally one dentist) as the dentist's working hours at that clinic minus breaks, minus leave, minus appointments that are not cancelled at any clinic, and every slot MUST be as long as the treatment and fit entirely in the free time. (source: FR-010, FR-001)
- **FR-015**: The system MUST start slots only on the hour or half hour. (source: FR-010)
- **FR-016**: The system MUST NOT offer a slot that starts before the current time, and for patients MUST NOT offer a slot after the end of the booking horizon (today and the following 30 days by default; the number of days is a setting held as data). (source: FR-010, FR-001)
- **FR-017**: The system MUST provide "first available" for a clinic: the earliest free slots across that clinic's active dentists in time order, 10 per page, with further pages on request. (source: FR-010)
- **FR-018**: The system MUST limit slot requests to one clinic and a date range of at most 31 days, and MUST refuse a request outside that. (source: FR-010)
- **FR-019**: The system MUST read appointments only through the interface that the booking feature provides (in-process), MUST work with a stand-in that returns no appointments until that feature exists, and MUST show a freshly booked appointment as taken in the next slot request. (source: FR-010, FR-001)
- **FR-020**: The system MUST store times in UTC and show and accept them in India time (IST). (source: FR-010, FR-007)
- **FR-021**: The system MUST keep leave records for 24 months after the leave ends and then remove them. (source: FR-008)
- **FR-022**: The system MUST offer staff screens for clinics and dentists, dentists and hours, leave (with the to-move list), and treatments, usable in a desktop browser by the practice manager, and a to-move screen for reception. (source: FR-001, FR-007, FR-008, FR-009)
- **FR-023**: The system MUST apply role checks on the server for every operation (only the practice manager edits settings; reception reads its own clinic's to-move list only), never trusting ids in the request alone. (source: FR-001, FR-007, FR-008, FR-009)
- **FR-024**: The system MUST write no patient names or phone numbers to logs and MUST record slot-calculation timing so the 2-second target can be watched. (source: FR-010, FR-008)

### Key Entities

- **Clinic**: a place patients visit. Name, address, phone, active. Many dentists work at it; every appointment belongs to one clinic. (source: FR-001)
- **Dentist**: a person who treats patients. Name, active. May work at several clinics on set weekdays; every appointment belongs to one dentist. (source: FR-001)
- **Treatment type**: what is done at a visit. Name, duration in minutes, online flag (patients may book it online), active. (source: FR-009)
- **Working hours**: a dentist's hours at one clinic on one weekday: start, end and the breaks inside it. A dentist works at a clinic on the weekdays that have hours. (source: FR-007, FR-001)
- **Break**: a pause inside working hours (for example lunch) with a start and an end. (source: FR-007)
- **Leave**: time when a dentist is away at every clinic: start, end, whole day or part day. Kept 24 months. (source: FR-008)
- **Free slot** (calculated, not stored): a start time, an end time, a dentist and a clinic that are free for a given treatment length. (source: FR-010)
- **To-move item** (calculated, not stored): a booked appointment, owned by the booking feature, that overlaps a leave. (source: FR-008)
- **Booking horizon setting**: the number of days ahead a patient can book (30 by default; today and that many days after). (source: FR-010)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A third clinic and a new dentist, with hours, can be added and offered to patients entirely in the staff screens, with 0 deploys and 0 code changes.
- **SC-002**: Free slots show within 2 seconds for at least 95% of requests on a 4G phone connection, with 100 people using the system at the same time and data sized for 3 clinics, 10 dentists and 1,000 appointments a week.
- **SC-003**: In 100% of tested cases the slots returned respect working hours, breaks, leave and booked appointments, start on the hour or half hour, and fit the treatment length (no returned slot overlaps any of them).
- **SC-004**: When leave is recorded, 100% of the booked appointments that overlap it are listed for reception and 0 appointments are changed by the system.
- **SC-005**: A receptionist sees 0 appointments from another clinic on the to-move list, and no role other than the practice manager can change clinics, dentists, hours, leave or treatments (0 successful attempts in the role tests).
- **SC-006**: The practice manager can set a dentist's full week of hours at one clinic, including breaks, in under 3 minutes.
- **SC-007**: After a cancellation or a move, the appointment is off the to-move list at the next time the list is opened (within 5 seconds).

## Assumptions

- A-1: Prerequisite features exist or are stubbed: sign-in, roles and the access context (feature 002, cmp-identity) and the appointments owned by cmp-booking (feature 004 onwards). Until cmp-booking exists, an in-process stand-in returns no appointments.
- A-2: The practice manager uses a desktop browser; reception uses a desktop browser (A-001, A-002).
- A-3: Initial data (the 2 clinics, 6 dentists, hours, reception-only treatment types) is entered by the practice manager in the staff screens before go-live; only the three online treatment types are present from the start. The names, addresses, phones and durations of the others are not given in the PRD and are not invented here.
- A-4: Working hours are the same every week (a weekly pattern); there are no date-specific exceptions other than leave.
- A-5: A change of weekly hours or making a clinic, dentist or treatment inactive does not create to-move items; only leave does (FR-008). See Q1 and Q2.
- A-6: Leave applies to the dentist at every clinic.
- A-7: Appointments with status booked are the ones to move; appointments with status arrived or no-show are not listed; cancelled appointments never block slots or appear on lists. Appointments that are not cancelled block slots.
- A-8: The booking horizon (30 days) applies to patient requests only; reception may look further ahead, within the 31-day range per request.
- A-9: The booking-horizon number is held as a stored setting with the default 30 (PD-002, ASM-010); a screen to change it is not part of this feature.
- A-10: Treatment durations are multiples of 30 minutes so they fit the half-hour slot grid; the PRD shows only 30, 60 and 90.
- A-11: Deleting a leave entry is allowed to correct mistakes; the PRD only says leave is recorded.
- A-12: Staff accounts and the dentist-to-account link belong to the sign-in feature, not this one. The no-show, reminders and booking rules belong to other features.

## Open Questions (assumed answers)

See `clarifications.md`.

- Q1: Should changing weekly hours also list appointments left outside the new hours for reception to move? Assumed: No (open question Q1).
- Q2: What happens to future appointments when a clinic, dentist or treatment type is made inactive? Assumed: they stay and are not listed for moving (open question Q2).
- Q3: Does a leave list entry need a reason or note? Assumed: No reason is stored (open question Q3).
