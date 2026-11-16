# User stories: clinic-test-2

> **Sample data.** Written by hand for a Phase 3B demo, in the requirements contract's format. Not produced by
> the Phase 1–2 agents; the client is fictional.

## Epics

| EPIC | Epic | FRs |
|---|---|---|
| EPIC-01 | Clinics, sign-in, roles and family members | FR-001, FR-002, FR-003, FR-004, FR-005, FR-006 |
| EPIC-02 | Dentist schedules, treatments and slots | FR-007, FR-008, FR-009, FR-010 |
| EPIC-03 | Online booking | FR-011, FR-012, FR-013, FR-014 |
| EPIC-04 | My appointments | FR-015, FR-016, FR-017, FR-018 |
| EPIC-05 | Reception and the dentist's day | FR-019, FR-020, FR-021, FR-022, FR-023, FR-024 |
| EPIC-06 | Repeat no-show block | FR-025, FR-026 |
| EPIC-07 | Reminders | FR-027, FR-028, FR-029, FR-030, FR-031, FR-033 |
| EPIC-08 | No-show report | FR-032 |

## Stories

### US-001: Clinics and dentists
EPIC-01 · P-04 · Traces: FR-001
As the practice manager, I want both clinics and all dentists in the system so that every appointment belongs to a clinic and a dentist.
- US-001.AC1: Given the clinics Indiranagar and Whitefield, When a patient books, Then they choose one of them.
- US-001.AC2: Given a dentist who works at Indiranagar on Monday and Whitefield on Tuesday, When their hours are set, Then free slots appear at the right clinic on each day.
- US-001.AC3: Given a third clinic is added by the practice manager, When patients book, Then it is offered with no change to the app.
Notes: REQ-018.

### US-002: Patient signs in with a phone code
EPIC-01 · P-01 · Traces: FR-002
As a patient, I want to sign in with my phone number and a code so that I don't need a password.
- US-002.AC1: Given a patient enters their phone number, When they ask for a code, Then a code arrives by SMS.
- US-002.AC2: Given a correct code entered within 10 minutes, When they confirm, Then they are signed in.
- US-002.AC3: Given 5 wrong codes, When they try a sixth time, Then they are told to wait 15 minutes.
- US-002.AC4: Given a phone number with no account, When the code is verified, Then the patient gives their name and an account is created.
Notes: SA-006, PD-006, NFR-006.

### US-003: Staff sign in with username and password
EPIC-01 · P-02, P-03, P-04 · Traces: FR-003
As a member of staff, I want to sign in with a username and password so that I reach my screens.
- US-003.AC1: Given an active staff account, When the right username and password are entered, Then the person is signed in.
- US-003.AC2: Given a deactivated account, When its password is entered, Then sign-in is refused.

### US-004: Each role sees only its own screens
EPIC-01 · P-01 to P-04 · Traces: FR-004
As the practice manager, I want each person to see only what their role needs so that patient data stays private.
- US-004.AC1: Given a signed-in patient, When they open their appointments, Then they see only their own and their family members'.
- US-004.AC2: Given a receptionist at Indiranagar, When they open the day view, Then they see only Indiranagar.
- US-004.AC3: Given a dentist, When they sign in, Then they see only their own day and cannot change it.
- US-004.AC4: Given the practice manager, When they sign in, Then they see both clinics and the settings.
Notes: NFR-006.

### US-005: Practice manager manages staff accounts
EPIC-01 · P-04 · Traces: FR-005
As the practice manager, I want to create and deactivate staff accounts so that only current staff can sign in.
- US-005.AC1: Given the practice manager creates a receptionist for Whitefield, When that person signs in, Then they see the Whitefield day view.
- US-005.AC2: Given the practice manager deactivates an account, When that person tries to sign in, Then they are refused.

### US-006: Patient books for family members
EPIC-01 · P-01 · Traces: FR-006
As a parent, I want to add my children to my account so that I can book for them with my phone.
- US-006.AC1: Given a patient with 2 family members added, When they book, Then they choose who the visit is for.
- US-006.AC2: Given a patient with 5 family members, When they try to add a sixth, Then they are told the limit is 5.
- US-006.AC3: Given a booking for a family member, When reception opens it, Then it shows the family member's name and the account holder's phone number.
Notes: SA-001; Q-007 is open.

### US-007: Practice manager sets dentists' weekly hours
EPIC-02 · P-04 · Traces: FR-007
As the practice manager, I want to set each dentist's weekly hours and breaks at each clinic so that patients see the right free slots.
- US-007.AC1: Given a dentist set to 09:00–13:00 at Indiranagar on Mondays, When a patient looks at a Monday there, Then slots run from 09:00 to 12:30.
- US-007.AC2: Given a break from 11:00 to 11:30, When slots are shown, Then 11:00 is not offered.

### US-008: Practice manager records leave
EPIC-02 · P-04 · Traces: FR-008
As the practice manager, I want to record a dentist's leave so that nobody can book them on those days.
- US-008.AC1: Given leave recorded for a whole day, When patients look at that day, Then that dentist has no free slots.
- US-008.AC2: Given 3 appointments already booked in the leave, When the leave is saved, Then reception sees those 3 in a "to move" list and they are not moved by the system.

### US-009: Treatment types and durations
EPIC-02 · P-04 · Traces: FR-009
As the practice manager, I want a treatment list with durations so that only short treatments are booked online.
- US-009.AC1: Given the treatment list, When a patient books online, Then they can choose only check-up, cleaning or consultation.
- US-009.AC2: Given a root canal of 90 minutes, When reception books it at 10:00, Then the dentist is busy until 11:30.

### US-010: Free slots are worked out
EPIC-02 · P-01, P-02 · Traces: FR-010
As a patient, I want to see only slots that are really free so that my booking is kept.
- US-010.AC1: Given a dentist with hours, a break, leave and bookings, When free slots are shown, Then none overlaps any of them.
- US-010.AC2: Given any free slot, When it is shown, Then it starts on the hour or half hour.

### US-011: Patient books online
EPIC-03 · P-01 · Traces: FR-011
As a patient, I want to book a slot online so that I don't have to call.
- US-011.AC1: Given a signed-in patient, When they choose clinic, treatment, dentist and a free slot and confirm, Then the appointment is booked.
- US-011.AC2: Given "first available", When the patient looks for slots, Then the earliest free slots across that clinic's dentists are shown with the dentist's name.
- US-011.AC3: Given today is 1 March, When the patient looks for slots, Then they see days up to 31 March only.
Notes: PD-002, NFR-002, NFR-010.

### US-012: Slot taken while choosing
EPIC-03 · P-01 · Traces: FR-012
As a patient, I want to know at once if my slot was taken so that I can pick another.
- US-012.AC1: Given two patients confirm the same slot, When the second confirms, Then they are told it was just taken and shown the next free slots.
- US-012.AC2: Given any slot, When bookings are saved, Then it has at most one appointment.

### US-013: Patient chooses SMS or WhatsApp
EPIC-03 · P-01 · Traces: FR-013
As a patient, I want to choose SMS or WhatsApp so that I get messages where I read them.
- US-013.AC1: Given a first booking, When the patient reaches confirm, Then SMS is selected and WhatsApp can be chosen.
- US-013.AC2: Given the patient chose WhatsApp last time, When they book again, Then WhatsApp is selected.

### US-014: Booking confirmation
EPIC-03 · P-01 · Traces: FR-014
As a patient, I want a confirmation message so that I have the details.
- US-014.AC1: Given a booking with WhatsApp chosen, When it is confirmed, Then a WhatsApp message with clinic, dentist, treatment, date, time and a link arrives.
- US-014.AC2: Given a booking with SMS chosen, When it is confirmed, Then the same details arrive by SMS.

### US-015: Patient sees their appointments
EPIC-04 · P-01 · Traces: FR-015
As a patient, I want to see my upcoming and past appointments so that I know when to come.
- US-015.AC1: Given a patient with 2 upcoming and 3 past appointments, When they open "My appointments", Then upcoming are listed first, soonest at the top.
- US-015.AC2: Given a past appointment marked no-show, When it is listed, Then its status says no-show.

### US-016: Patient reschedules online
EPIC-04 · P-01 · Traces: FR-016, FR-018
As a patient, I want to move my appointment online so that I don't have to phone.
- US-016.AC1: Given an appointment tomorrow at 10:00, When the patient picks a new free slot, Then the appointment moves and the old slot is free at once.
- US-016.AC2: Given an appointment in 3 hours, When the patient opens it, Then there is no "Change time" button and the clinic's phone number is shown.
- US-016.AC3: Given a move, When it is saved, Then a message with the new time is sent in the chosen channel.

### US-017: Patient cancels online
EPIC-04 · P-01 · Traces: FR-017, FR-018
As a patient, I want to cancel online so that the clinic can give the slot to someone else.
- US-017.AC1: Given an appointment in 2 days, When the patient cancels, Then it is cancelled by the patient and the slot is free at once.
- US-017.AC2: Given an appointment in 3 hours, When the patient opens it, Then there is no "Cancel" button and the clinic's phone number is shown.
- US-017.AC3: Given a cancel, When it is saved, Then a cancellation message is sent in the chosen channel.

### US-018: Reception day view
EPIC-05 · P-02 · Traces: FR-019
As a receptionist, I want to see every dentist's day at my clinic so that I know who is coming.
- US-018.AC1: Given 3 dentists working today, When the receptionist opens the day view, Then there is one column per dentist with each appointment's time, patient, phone, treatment and status.
- US-018.AC2: Given the receptionist picks another date, When the view loads, Then it shows that day.

### US-019: Reception books for a patient
EPIC-05 · P-02 · Traces: FR-020
As a receptionist, I want to book, move and cancel for patients who phone or walk in so that they don't need the website.
- US-019.AC1: Given a phone caller, When the receptionist finds them by phone number and books a root canal, Then it is booked for 90 minutes.
- US-019.AC2: Given an appointment in 1 hour, When the receptionist moves it, Then the move is allowed.
- US-019.AC3: Given a walk-in patient, When the receptionist books a free slot now, Then it is booked and can be marked arrived.
- US-019.AC4: Given a caller with no account, When the receptionist enters name and phone number, Then a patient is created and the booking saved.
Notes: SA-004, SA-005 (future paper-diary appointments are typed in this way before go-live).

### US-020: Mark a patient arrived
EPIC-05 · P-02 · Traces: FR-021
As a receptionist, I want to mark a patient arrived so that the dentist knows they are here.
- US-020.AC1: Given a booked appointment, When the receptionist marks arrived, Then its status is arrived in the day view and the dentist's day.

### US-021: Mark a no-show
EPIC-05 · P-02 · Traces: FR-022, FR-024
As a receptionist, I want to mark patients who did not come so that no-shows are counted.
- US-021.AC1: Given an appointment that started 20 minutes ago, When the receptionist marks no-show, Then its status is no-show.
- US-021.AC2: Given an appointment that started 5 minutes ago, When the receptionist opens it, Then "No-show" cannot be chosen yet.
- US-021.AC3: Given a no-show marked by mistake today, When the receptionist undoes it, Then the status is booked again and the no-show is not counted.

### US-022: Dentist sees their day
EPIC-05 · P-03 · Traces: FR-023
As a dentist, I want to see my own day so that I can prepare for each patient.
- US-022.AC1: Given a dentist at Whitefield today, When they sign in, Then they see today's appointments there with time, patient, treatment and status.
- US-022.AC2: Given the dentist's day, When they open an appointment, Then they cannot change it.

### US-023: Every change is recorded
EPIC-05 · P-02, P-04 · Traces: FR-024
As the practice manager, I want every status change recorded with who and when so that disputes can be checked.
- US-023.AC1: Given a booking moved by reception and later cancelled by the patient, When the practice manager opens its history, Then both changes show with who and when.

### US-024: Repeat no-shows cannot book online
EPIC-06 · P-01 · Traces: FR-025
As the practice manager, I want patients with 2 no-shows in 6 months stopped from booking online so that chairs are not wasted.
- US-024.AC1: Given a patient with no-shows on 1 January and 1 April, When they try to book on 1 May, Then they are told to phone the clinic.
- US-024.AC2: Given that patient has an appointment already booked, When they are blocked, Then the appointment stays.
- US-024.AC3: Given a patient whose second no-show was over 6 months ago, When they book, Then booking is allowed.
Notes: PD-007.

### US-025: Reception lifts a block
EPIC-06 · P-02 · Traces: FR-026
As a receptionist, I want to see and lift a block so that a patient with a good reason can book online again.
- US-025.AC1: Given a blocked patient, When the receptionist finds them, Then the block is shown.
- US-025.AC2: Given the receptionist lifts the block, When the patient books online, Then it is allowed and their count starts from zero.

### US-026: Reminder 24 hours before
EPIC-07 · P-01 · Traces: FR-027, FR-028, FR-030
As a patient, I want a reminder the day before so that I don't forget.
- US-026.AC1: Given an appointment on Thursday at 11:00 with SMS chosen, When it is Wednesday 11:00, Then an SMS reminder with clinic, dentist, date, time and a change link is sent.
- US-026.AC2: Given an appointment on Thursday at 07:30, When the reminder is due (Wednesday 07:30, inside quiet hours), Then it is sent on Tuesday at 20:00.
- US-026.AC3: Given an appointment cancelled before its reminder, When the due time comes, Then no reminder is sent.
- US-026.AC4: Given an appointment booked 6 hours ahead, When it is booked, Then only the confirmation is sent.
Notes: SA-003; Q-009 is open; NFR-005, NFR-011.

### US-027: Failed reminders fall back and are listed
EPIC-07 · P-01, P-02 · Traces: FR-029, FR-033
As a receptionist, I want undelivered reminders resent by SMS and listed so that I can phone the patients.
- US-027.AC1: Given a WhatsApp reminder that cannot be delivered, When the failure is reported, Then the reminder is sent once by SMS.
- US-027.AC2: Given the SMS also fails, When reception opens "Reminders failed" for tomorrow, Then that appointment is listed with the patient's phone number.
Notes: SA-008; PRD Questions to raise, item 2.

### US-028: Patient stops reminders
EPIC-07 · P-01, P-02 · Traces: FR-031
As a patient, I want to stop reminders so that I am not messaged against my wish.
- US-028.AC1: Given a patient replies STOP, When their next reminder is due, Then it is not sent.
- US-028.AC2: Given a patient asks reception, When the receptionist switches reminders off, Then no further reminders are sent but booking confirmations still are.
Notes: NFR-011.

### US-029: No-show report per clinic
EPIC-08 · P-04 · Traces: FR-032
As the practice manager, I want no-shows per clinic per month so that I can see whether they fall.
- US-029.AC1: Given January had 400 non-cancelled appointments and 40 no-shows at Indiranagar, When the practice manager opens the report, Then it shows 40 and 10% for Indiranagar in January.
- US-029.AC2: Given the report, When it opens, Then it covers the last 12 months for each clinic, on screen only.
Notes: SA-004 (walk-ins count as appointments).

## Coverage
| FR | Stories |
|---|---|
| FR-001 | US-001 |
| FR-002 | US-002 |
| FR-003 | US-003 |
| FR-004 | US-004 |
| FR-005 | US-005 |
| FR-006 | US-006 |
| FR-007 | US-007 |
| FR-008 | US-008 |
| FR-009 | US-009 |
| FR-010 | US-010 |
| FR-011 | US-011 |
| FR-012 | US-012 |
| FR-013 | US-013 |
| FR-014 | US-014 |
| FR-015 | US-015 |
| FR-016 | US-016 |
| FR-017 | US-017 |
| FR-018 | US-016, US-017 |
| FR-019 | US-018 |
| FR-020 | US-019 |
| FR-021 | US-020 |
| FR-022 | US-021 |
| FR-023 | US-022 |
| FR-024 | US-021, US-023 |
| FR-025 | US-024 |
| FR-026 | US-025 |
| FR-027 | US-026 |
| FR-028 | US-026 |
| FR-029 | US-027 |
| FR-030 | US-026 |
| FR-031 | US-028 |
| FR-032 | US-029 |
| FR-033 | US-027 |
