# Feature Specification: Dentist schedules, treatments and free slots

**Feature Branch**: `002-schedules-slots`

**Created**: 2026-11-13

**Status**: Draft

**Input**: User description: "MOD-02, Release 1 (DL-1 2027-02-22): the practice manager sets each dentist's weekly hours and breaks per clinic, records leave, edits the treatment types; the system calculates the free slots (hours minus breaks, leave and booked appointments) and a 'first available' list. Covers FR-007, FR-008, FR-009, FR-010, NFR-003 (supports NFR-002)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Manage treatment types (Priority: P1)

The practice manager opens the treatments screen and sees every treatment type with its duration in minutes and whether patients may book it online. The list starts with the three online types (check-up, cleaning, consultation, 30 minutes each) and reception-only types such as root canal and extraction (60 or 90 minutes). The manager adds a type, changes its name, duration or online flag, and switches a type off when the clinic stops offering it. Booking and slot calculation use this list to know how long a visit lasts and what a patient may book online. (source: FR-009)

**Why this priority**: A slot only has a length once the treatment is known. Free slots (User Story 3) and every booking need this list, so it comes first.

**Independent Test**: Sign in as the practice manager, add a 60-minute reception-only type, change a type's duration, switch a type off, then read the list as a patient and as reception. The manager sees all types; a patient sees only active online types.

**Acceptance Scenarios**:

1. **Given** a new system, **When** the practice manager opens the treatments screen, **Then** the list shows check-up, cleaning and consultation as online, 30 minutes each, and at least root canal and extraction as reception-only with 60 or 90 minutes.
2. **Given** the treatments screen, **When** the manager adds a type with a name, a duration of 30, 60 or 90 minutes and the online flag, **Then** the type is saved and appears in the list at once.
3. **Given** an existing type, **When** the manager changes its duration or online flag, **Then** the change applies to new slot searches and new bookings, and appointments already booked keep their own start and end times.
4. **Given** an active type, **When** the manager switches it off, **Then** it no longer appears for booking, and appointments already booked with it are unchanged.
5. **Given** a type name that already exists (ignoring capital letters), or a duration that is not 30, 60 or 90 minutes, **When** the manager saves, **Then** the save is refused with a message that names the problem.
6. **Given** a signed-in patient, **When** they read the treatment list, **Then** they see only active online types; a receptionist sees all active types.
7. **Given** a user who is not the practice manager, **When** they try to add or change a type, **Then** the request is refused.

---

### User Story 2 - Set weekly working hours and breaks (Priority: P1)

The practice manager opens "dentists and hours", picks a dentist and a clinic and sets, for each weekday, the start and end of the working day and any breaks (for example lunch 13:00–14:00). A dentist can work at more than one clinic on different days. Hours are entered and shown in India time. A dentist with no hours at a clinic offers no slots there. The manager can add a third clinic or dentist later and give them hours in the same screen, with no software release. (source: FR-007, NFR-003)

**Why this priority**: With no hours there are no slots; this is the base of availability.

**Independent Test**: As the practice manager, set Dr Rao's Monday hours at Indiranagar to 09:00–17:00 with a break 13:00–14:00, reload and read them back; set Tuesday at Whitefield; try to set Monday at Whitefield overlapping Indiranagar and see it refused.

**Acceptance Scenarios**:

1. **Given** a dentist and a clinic with no hours, **When** the manager saves Monday 09:00–17:00 with a break 13:00–14:00, **Then** the weekly hours show that day with the break and the same values are returned on reload.
2. **Given** hours for a dentist at one clinic, **When** the manager sets other weekdays at a second clinic, **Then** both sets are kept and shown per clinic.
3. **Given** hours for a weekday, **When** the manager changes the start, end or breaks, **Then** new slot searches use the new hours and appointments already booked are not moved or cancelled.
4. **Given** a weekday entry, **When** the end is not after the start, or a break lies outside the working day or overlaps another break, **Then** the save is refused with a message.
5. **Given** a dentist with hours at clinic A on Monday 09:00–13:00, **When** the manager sets Monday hours at clinic B that overlap 09:00–13:00, **Then** the save is refused because one dentist cannot be at two clinics at once.
6. **Given** a weekday with hours, **When** the manager removes that weekday, **Then** the dentist offers no slots at that clinic on that weekday.
7. **Given** a newly added third clinic and a new dentist (added as data by the staff screens of feature 001), **When** the manager sets their hours, **Then** their slots become available with no software release.
8. **Given** a user who is not the practice manager, **When** they try to change hours, **Then** the request is refused.

---

### User Story 3 - Find free slots and first available (Priority: P1)

Other parts of the system (patient booking, reception booking, rescheduling) ask for free slots of one clinic for one date range and one treatment type, for one dentist or for all that clinic's dentists. A slot is a start time on the hour or half hour at which the whole treatment fits inside the dentist's working hours at that clinic, outside breaks and leave, and not overlapping an appointment already booked. "First available" returns the 10 earliest free slots across the clinic's dentists. Patients see slots only from now to the booking horizon (today plus 30 days, a setting). Slot lists are calculated live so a freed slot is bookable at once. (source: FR-010, NFR-003, NFR-002)

**Why this priority**: This is the module's output; booking (feature 003) cannot start without it.

**Independent Test**: With hours 09:00–17:00 and a break 13:00–14:00 for one dentist, one booked appointment 10:00–10:30 and a 30-minute type, ask for one day: slots are 09:00, 09:30, 10:30 … 12:30, 14:00 … 16:30 and nothing at 10:00 or in the break. Ask for a 90-minute type: the last slot is 15:30.

**Acceptance Scenarios**:

1. **Given** a dentist working 09:00–17:00 with a break 13:00–14:00 at a clinic and no bookings, **When** free slots are requested for a 30-minute type on that day, **Then** slots start every half hour from 09:00 to 16:30 except those inside 13:00–14:00.
2. **Given** a 60-minute or 90-minute type, **When** free slots are requested, **Then** only starts where the full duration fits before the end of the day and before the next break, leave or booked appointment are returned (for example 12:30 is not offered for 60 minutes when the break starts at 13:00).
3. **Given** a booked appointment 10:00–10:30, **When** free slots are requested, **Then** the 10:00 slot is not offered, and a 60-minute type is not offered at 09:30 or 10:00.
4. **Given** leave covering part of the day, **When** free slots are requested, **Then** no slot overlaps the leave.
5. **Given** an appointment is cancelled, **When** free slots are requested again, **Then** its slot appears at once.
6. **Given** a patient asks for slots, **When** the range goes past today plus the booking horizon (30 days) or starts in the past, **Then** only slots from now to the horizon are returned (1 March shows up to 31 March).
7. **Given** a clinic with several dentists, **When** "first available" is requested for a treatment type, **Then** the 10 earliest free slots across those dentists are returned in time order, each with its dentist.
8. **Given** a treatment type that is not bookable online, **When** a patient asks for its slots, **Then** the request is refused; a receptionist or manager can ask for it.
9. **Given** a receptionist of clinic A, **When** they ask for slots of clinic B, **Then** the request is refused.
10. **Given** 3 clinics, 10 dentists and 1,000 appointments a week, **When** 100 users ask for free slots at the same time, **Then** 95% of the answers come back fast enough for the slot list to show within 2 seconds on a 4G phone.
11. **Given** a request with a date range longer than 31 days, **When** slots are asked, **Then** the request is refused with a message.

---

### User Story 4 - Record dentist leave and list appointments to move (Priority: P2)

The practice manager opens the leave screen, picks a dentist and records leave for whole days or for part of a day (for example Thursday 14:00–17:00). Free slots stop being offered in that time at every clinic where the dentist works. If appointments are already booked in that time, the system lists them (patient, phone, clinic, treatment, time) so reception can phone the patients and move them. The system never moves or cancels an appointment itself, including those that conflict with leave added after booking. The manager can change or delete leave. (source: FR-008)

**Why this priority**: Without leave, slots would be offered while the dentist is away; the "to move" list protects patients already booked. It needs hours (User Story 2) and the slot calculation (User Story 3) to be seen in action.

**Independent Test**: Book an appointment for Dr Rao on Thursday 15:00, record leave Thursday 14:00–17:00, check that the appointment is listed as "to move", that it is still booked and unchanged, and that no slot is offered 14:00–17:00. Delete the leave and see the slots return.

**Acceptance Scenarios**:

1. **Given** a dentist with hours, **When** the manager records whole-day leave for a date range, **Then** no free slots are offered for that dentist on those days at any clinic.
2. **Given** a dentist, **When** the manager records part-day leave from 14:00 to 17:00, **Then** slots in that time are not offered and slots before and after are.
3. **Given** appointments already booked in the leave time, **When** the leave is saved, **Then** those appointments are listed with patient name, phone number, clinic, treatment and start time, and each stays booked and unchanged.
4. **Given** a leave with a "to move" list, **When** reception moves or cancels one of those appointments and the list is opened again, **Then** that appointment is no longer on it.
5. **Given** a receptionist of clinic A, **When** they open the list, **Then** they see only appointments at clinic A; the manager sees all clinics.
6. **Given** leave, **When** the manager changes its dates or times, **Then** the list and the slots follow the new times; when the manager deletes it, the slots in that time are offered again.
7. **Given** a leave whose end is not after its start, or that overlaps another leave of the same dentist, **When** the manager saves, **Then** the save is refused with a message.
8. **Given** leave that ended more than 24 months ago, **When** the yearly clean-up runs, **Then** it is deleted; newer leave stays.
9. **Given** a user who is not the practice manager, **When** they try to record leave, **Then** the request is refused.

---

### Edge Cases

- Leave added after appointments were booked: those appointments are only listed, never moved or cancelled by the system.
- Hours or breaks changed after appointments were booked: existing appointments stay and are not listed as conflicts (only leave creates the list).
- A treatment type's duration changed or the type switched off: existing appointments keep their times.
- A dentist working at two clinics: slots at one clinic never show times when the dentist is booked or on leave at the other clinic.
- Working hours that do not fall on the hour or half hour (for example 09:15): the first slot is the next half hour (09:30); a slot never starts at 09:15.
- A day without hours, a clinic or dentist that is switched off, or a dentist with no hours at the clinic: no slots; no error.
- Daylight saving does not apply (India time, one zone); all times are India time on screen and stored as universal time.
- Two patients choose the same slot at once: this module only offers slots; the double-booking guard belongs to booking (feature 003).
- Appointments cannot be read from the booking feature yet (it is built in parallel): booked appointments are treated as none until that read interface exists; see Assumptions.
- A request asks for a past range or a range wholly beyond the horizon: an empty list for patients, not an error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST let the practice manager set, for each dentist and each clinic, the weekly working hours (start and end for each weekday) with zero or more breaks per weekday, in India time. (source: FR-007)
- **FR-002**: The system MUST reject hours where the end is not after the start, a break lies outside the working day or overlaps another break, or the same dentist has overlapping hours at two clinics on the same weekday. (source: FR-007)
- **FR-003**: The system MUST let the practice manager add, change, remove and read weekly hours for any dentist and clinic with no software release, including for a third clinic or a new dentist added as data. (source: FR-007, NFR-003)
- **FR-004**: The system MUST let the practice manager record a dentist's leave as one or more whole days or as a part of a day, and change or delete it. (source: FR-008)
- **FR-005**: The system MUST reject leave whose end is not after its start or that overlaps another leave of the same dentist. (source: FR-008)
- **FR-006**: The system MUST list the appointments already booked in a leave's time (patient name, phone number, clinic, treatment, start time) for reception to move, and MUST NOT move, cancel or change any appointment itself. (source: FR-008)
- **FR-007**: The "to move" list MUST be calculated when it is opened, so appointments moved or cancelled since the leave was recorded no longer appear; a receptionist sees only their own clinic's appointments and the manager sees all. (source: FR-008)
- **FR-008**: The system MUST keep leave for 24 months after it ends and delete it afterwards. (source: FR-008)
- **FR-009**: The system MUST hold treatment types, each with a name, a duration of 30, 60 or 90 minutes, an online-bookable flag and an active flag, starting with check-up, cleaning and consultation as online 30-minute types and root canal and extraction as reception-only types. (source: FR-009)
- **FR-010**: The system MUST let the practice manager add, edit and switch off treatment types, refuse a duplicate name (ignoring capital letters) and refuse other durations, and MUST NOT change appointments already booked. (source: FR-009)
- **FR-011**: The system MUST show patients only active online treatment types, and reception and the manager all active types. (source: FR-009)
- **FR-012**: The system MUST calculate free slots for one clinic, one date range of at most 31 days and one treatment type, for one dentist or for all the clinic's dentists, as the dentist's working hours at that clinic minus breaks, leave (at any clinic) and booked appointments (at any clinic). (source: FR-010)
- **FR-013**: A free slot MUST start on the hour or half hour and the whole treatment duration MUST fit in free time. (source: FR-010)
- **FR-014**: The system MUST return the 10 earliest free slots across a clinic's dentists for a treatment type ("first available"), in time order, each with its dentist. (source: FR-010)
- **FR-015**: For patients the system MUST offer only slots from now to the booking horizon (today plus a number of days that is a setting, 30 by default) and only active online treatment types. (source: FR-010)
- **FR-016**: The system MUST calculate slots from the current data on every request so that a freed slot is offered at once. (source: FR-010)
- **FR-017**: The system MUST give the booking feature a way to ask whether one slot is free and to get the next free slots, using the same calculation as the slot list. (source: FR-010)
- **FR-018**: The system MUST read booked appointments only through an interface owned by the booking feature, and MUST NOT write appointments. (source: FR-008, FR-010)
- **FR-019**: Only the practice manager MAY change hours, leave and treatment types; patients, receptionists and dentists are refused; a receptionist may read slots and the "to move" list for their own clinic only. (source: FR-007, FR-008, FR-009)
- **FR-020**: The system MUST show and accept all times in India time and store them in universal time. (source: FR-007, FR-008, FR-010)
- **FR-021**: The system MUST handle 3 clinics, 10 dentists and 1,000 appointments a week, with 100 users asking for slots at the same time, with no redesign, and MUST show free slots within 2 seconds for 95% of requests on 4G. (source: NFR-003, NFR-002)
- **FR-022**: The system MUST write no patient name, phone number or birth year to logs. (source: FR-008)

### Key Entities *(include if feature involves data)*

- **Treatment type**: a kind of visit; name, duration in minutes (30, 60 or 90), whether patients can book it online, active or not.
- **Working hours**: for one dentist at one clinic on one weekday, the start and end of the working day, with its breaks. Kept until changed.
- **Break**: a time range inside a working day when the dentist takes no appointments.
- **Leave**: a time range, whole days or part of a day, when a dentist is away at every clinic. Kept 24 months.
- **Free slot**: a computed (not stored) start time for a clinic, dentist and treatment type.
- **Appointment to move**: a booked appointment, owned by the booking feature, that falls inside a leave; read only.
- **Clinic and dentist**: owned by the identity and staff feature (001); used here by reference.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of tested days (working hours, breaks, leave, bookings, 30-, 60- and 90-minute types), the offered slots equal the expected list, with none overlapping a break, leave or booked appointment.
- **SC-002**: A practice manager can set one dentist's full week of hours with breaks at a clinic in under 5 minutes.
- **SC-003**: A third clinic and a new dentist can be given hours and offer slots with 0 software releases.
- **SC-004**: With 3 clinics, 10 dentists, 1,000 appointments a week and 100 users asking at once, 95% of free-slot requests are answered fast enough to show within 2 seconds on a 4G phone.
- **SC-005**: After leave is recorded, 100% of the appointments booked in it are listed for reception and 0 appointments are changed by the system.
- **SC-006**: A slot freed by a cancellation is offered in the next request in 100% of tests.

## Assumptions

- Clinics, dentists and staff accounts are created by feature 001 (identity and staff); this feature uses them by reference and adds a clinic's or dentist's hours. Sign-in and role checks (practice manager, receptionist with a clinic, patient) come from feature 001.
- Appointments are owned by the booking feature (003, with reception in 005). This feature depends on a read interface to list active (status booked) appointments of a dentist in a time range. Until it exists, a stand-in that returns no appointments is used in tests; slot results with real bookings and the "to move" list are verified when features 003 and 005 are in.
- Appointments' conflict with leave added after booking is only listed, never moved (PRD FR-008). Hours changed after booking do not produce a list.
- Hours are one working day window per dentist per clinic per weekday, with breaks inside it; a split day is modelled with a break.
- One dentist is never at two clinics at the same time, so hours at different clinics on the same weekday must not overlap.
- Leave applies to the dentist at every clinic.
- Duration of treatment types is 30, 60 or 90 minutes; online types are not restricted by this feature beyond the PRD's starting list (all online types start at 30 minutes).
- The booking horizon is a setting, 30 days by default (today plus 30 days); only patients are limited by it; staff may ask for any range of up to 31 days.
- Dentists (read-only role) do not use treatment, hours, leave or slot screens in this feature; their own-day view belongs to reception feature 005.
- "First available" returns slots (time and dentist), so two dentists free at the same time give two entries.
- No open questions were raised in the PRD for this module.
- Release 1; all times are India time; English only.
