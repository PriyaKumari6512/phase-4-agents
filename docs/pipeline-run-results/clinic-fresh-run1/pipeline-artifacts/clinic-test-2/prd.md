# PRD: clinic-test-2   (version 1.0)

> **Sample data.** Written by hand for a Phase 3B demo, in the requirements contract's format. Not produced by
> the Phase 1–2 agents; the client is fictional.

## 1. Overview

**Who has the problem.** BrightSmile Dental runs 2 dental clinics in Bengaluru (Indiranagar and Whitefield) with 6 dentists and about 450 appointments a week; a third clinic may open within 18 months. Every booking is made by phone and written in a paper diary per dentist, so reception spends most of the day on the phone.

**The problem.** Patients forget their appointments and the chair stays empty: "no-shows are our biggest problem" (REQ-002). Patients can only book during clinic hours, by phone (REQ-001).

**What we build.** A mobile-friendly website. Patients sign in with a phone code and book, reschedule and cancel 30-minute check-ups, cleanings and consultations. Reception runs each dentist's day, books longer treatments, checks patients in and marks no-shows. Patients get a confirmation and a reminder 24 hours before by SMS or WhatsApp, as they choose. Repeat no-shows lose online booking. The practice manager sets dentists' hours and sees no-shows per clinic per month. Go-live is firm on 1 March 2027.

## 2. Goals and success metrics
| Goal | REQs | Metric | Target |
|---|---|---|---|
| Patients book online instead of phoning | REQ-001 | Share of appointments booked online (not by reception) | At least 50% within 3 months after go-live (PD-001) |
| Reduce no-shows | REQ-002 | No-shows ÷ booked appointments per month, per clinic | TBD: today's rate is not known (Questions to raise, item 1). Measured from go-live with the app's own data. |
| Reduce no-shows (same goal) | REQ-002 | Share of due reminders sent within 15 minutes of their due time | At least 99% (PD-001, NFR-005) |

## 3. Non-goals

From "Out of scope" in `scope.md`. The app does not do these:

- Insurance claims (REQ-020).
- A native mobile app (REQ-021).
- Online payment, deposits or refunds; patients pay at the clinic (REQ-022).
- Clinical notes, X-rays, treatment records or prescriptions (REQ-025).
- Import of the paper diary; reception types in future appointments (REQ-030).
- Waiting lists, recall messages, marketing messages, integration with the clinic's dental software, other languages, report export.

## 4. Personas
| P | Persona | Role | Main need |
|---|---|---|---|
| P-01 | Patient (and the family members they book for) | Books from a phone | Book, move or cancel a visit in a minute at any time, and be reminded in the channel they read. |
| P-02 | Receptionist | Works at the reception desk of one clinic | See every dentist's day at a glance, book phone and walk-in patients, check them in, mark no-shows. |
| P-03 | Dentist | Works at one or both clinics | See their own day, with each patient and treatment. |
| P-04 | Practice manager | Runs both clinics | Set dentists' hours and leave, manage staff accounts, see no-shows per clinic. |

## 5. Functional requirements
| FR | Requirement | REQs | MOD |
|---|---|---|---|
| FR-001 | The system holds the clinics (2 now; a third is added as data) and the dentists. A dentist can work at more than one clinic, on set days. Every appointment belongs to one clinic and one dentist. | REQ-018 | MOD-01 |
| FR-002 | A patient signs in with their phone number and a one-time code sent by SMS (SA-006). The code is valid for 10 minutes and allows 5 wrong tries, after which the patient waits 15 minutes (PD-006). A new phone number creates an account after the code is verified and the patient gives their name. | REQ-023 | MOD-01 |
| FR-003 | Receptionists, dentists and the practice manager sign in with a username and password. | REQ-026 | MOD-01 |
| FR-004 | Each role sees only what it needs. A patient sees only their own appointments and those of their family members. A receptionist sees and changes the appointments of their own clinic only. A dentist sees their own day, read only. The practice manager sees both clinics and the settings. | REQ-026, REQ-027 | MOD-01 |
| FR-005 | The practice manager creates and deactivates the accounts of receptionists and dentists and assigns receptionists to a clinic. A deactivated person cannot sign in. | REQ-026 | MOD-01 |
| FR-006 | A patient can add up to 5 family members to their account (name and birth year) and book for any of them (SA-001; Q-007 is open). Each booking names the person it is for. | REQ-003, REQ-023 | MOD-01 |
| FR-007 | The practice manager sets each dentist's weekly working hours at each clinic, with breaks. | REQ-013 | MOD-02 |
| FR-008 | The practice manager records a dentist's leave (whole days or part days). Appointments already booked in that time are listed for reception to move; the system never moves them by itself. | REQ-013 | MOD-02 |
| FR-009 | The system holds the treatment types with their duration and whether patients can book them online. Online types are check-up, cleaning and consultation, 30 minutes each. Other types (for example root canal, extraction) are 60 or 90 minutes and are booked by reception only. The practice manager can edit the list. | REQ-014 | MOD-02 |
| FR-010 | Free slots are the dentist's working hours at that clinic minus breaks, leave and booked appointments. Slots start on the hour or half hour. | REQ-013, REQ-014 | MOD-02 |
| FR-011 | A signed-in patient books online: clinic, an online treatment type, a dentist or "first available", then a free slot within the next 30 days (SA-007, PD-002). "First available" shows the earliest free slots across that clinic's dentists. | REQ-003 | MOD-03 |
| FR-012 | A slot is never booked twice. If another booking takes the slot while the patient is choosing, the patient is told and shown the next free slots. | REQ-003 | MOD-03 |
| FR-013 | When booking, the patient chooses SMS or WhatsApp for messages about this appointment. The choice is remembered for their next booking. The first default is SMS. | REQ-012 | MOD-07 |
| FR-014 | On booking, the patient gets a confirmation at once in the chosen channel: clinic, dentist, treatment, date, time and a link to the appointment. | REQ-016 | MOD-07 |
| FR-015 | A signed-in patient sees their upcoming and past appointments (and their family members'), with status. | REQ-004, REQ-005 | MOD-04 |
| FR-016 | A patient can reschedule an upcoming appointment to another free slot (same clinic and treatment; any dentist) until 4 hours before its start. | REQ-004, REQ-006 | MOD-04 |
| FR-017 | A patient can cancel an upcoming appointment until 4 hours before its start. Inside 4 hours the page shows the clinic's phone number instead of the buttons. | REQ-005, REQ-006 | MOD-04 |
| FR-018 | After a cancel or reschedule the freed slot is bookable at once, and the patient gets a message in their chosen channel. | REQ-004, REQ-005, REQ-016 | MOD-04 |
| FR-019 | A receptionist sees the day view of their clinic: one column per dentist working that day, each appointment with patient name, phone number, treatment and status. They can move to other days. | REQ-007 | MOD-05 |
| FR-020 | A receptionist books, reschedules and cancels appointments for patients of their clinic, including reception-only treatment types and walk-ins (SA-004), with no 4-hour cut-off. They find a patient by phone number or name, or create one with name and phone number. | REQ-010, REQ-014, REQ-030 | MOD-05 |
| FR-021 | A receptionist marks a patient as arrived. | REQ-009 | MOD-05 |
| FR-022 | A receptionist marks a patient as a no-show from 15 minutes after the start time until the end of that day, and can undo it the same day (PD-003). | REQ-008 | MOD-05 |
| FR-023 | A dentist sees their own day at each clinic they work at that day, read only: time, patient name, treatment, status. | REQ-027 | MOD-05 |
| FR-024 | An appointment's status is booked, arrived, no-show, cancelled by the patient or cancelled by the clinic. Every change records who made it and when. | REQ-007, REQ-008, REQ-009 | MOD-05 |
| FR-025 | A patient with 2 no-shows in the last 6 months cannot book or reschedule online; the page says to phone the clinic. Their existing bookings stay. Family members' no-shows count against the person who had them (PD-007). | REQ-015 | MOD-06 |
| FR-026 | Reception sees that a patient is blocked, and can lift the block; lifting starts the count again from zero. | REQ-015 | MOD-06 |
| FR-027 | The patient gets a reminder 24 hours before the appointment in the chosen channel. A reminder due between 21:00 and 08:00 India time is sent at 20:00 the evening before (SA-003; Q-009 is open). | REQ-011, REQ-012 | MOD-07 |
| FR-028 | A reminder is not sent for a cancelled appointment. A rescheduled appointment gets a reminder for its new time only. An appointment booked less than 24 hours ahead gets no reminder, only the confirmation. | REQ-011 | MOD-07 |
| FR-029 | If a WhatsApp message cannot be delivered, it is sent once by SMS instead (SA-008, PD-005). If the SMS also fails, the appointment is marked "reminder failed". | REQ-011, REQ-012 | MOD-07 |
| FR-030 | Every reminder says the clinic, dentist, date and time, and has a link to reschedule or cancel. | REQ-011 | MOD-07 |
| FR-031 | A patient can stop reminders by replying STOP, or by asking reception, who switches them off in the patient's record. Confirmations of a booking or a change are still sent. | REQ-011, REQ-012 | MOD-07 |
| FR-032 | The practice manager sees, for each clinic and each of the last 12 months, the number of no-shows and the no-show rate (no-shows ÷ appointments that were not cancelled). On screen only. | REQ-028 | MOD-08 |
| FR-033 | Reception sees the list of tomorrow's appointments whose reminder failed, so they can phone those patients. | REQ-011 | MOD-07 |

## 6. User flows and screens

### Flow: A patient books online   P-01 · FR-002, FR-006, FR-011, FR-012, FR-013, FR-014
1. The patient opens the BrightSmile website on their phone and chooses "Book".
2. They enter their phone number and the code sent by SMS. A new patient also gives their name.
   - *Wrong or expired code:* the system says so and offers a new code; after 5 wrong tries they wait 15 minutes (FR-002).
3. They choose who the visit is for (themselves or a family member), the clinic and the treatment (check-up, cleaning or consultation).
4. They choose a dentist or "first available", then a day in the next 30 days and a free slot.
   - *Blocked patient:* the system says online booking is not available and shows the clinic's phone number (FR-025).
5. They choose SMS or WhatsApp for messages and confirm.
   - *Slot just taken:* the system says so and shows the next free slots (FR-012).
6. The system shows the booking and sends the confirmation in the chosen channel.

Screens: sign-in, who and what, slot picker, confirm, booked.

### Flow: A patient reschedules or cancels   P-01 · FR-015, FR-016, FR-017, FR-018
1. The patient opens the link in the confirmation or reminder, or signs in and opens "My appointments".
2. They choose an upcoming appointment, then "Change time" or "Cancel".
   - *Less than 4 hours before:* the buttons are replaced by the clinic's phone number (FR-017).
3. For a change, they pick a new free slot (FR-016). For a cancel, they confirm.
4. The system shows the result and sends a message in the chosen channel (FR-018).

Screens: my appointments, appointment, slot picker, done.

### Flow: Reception runs the day   P-02 · FR-019, FR-020, FR-021, FR-022, FR-024, FR-026, FR-033
1. The receptionist signs in and sees today's day view for their clinic, one column per dentist.
2. A patient arrives: the receptionist marks them arrived (FR-021).
3. A patient has not come 15 minutes after the start: the receptionist marks a no-show (FR-022), and can undo it that day.
4. A patient phones or walks in: the receptionist finds or creates the patient and books any treatment into a free slot (FR-020).
5. In the afternoon the receptionist opens "Reminders failed" for tomorrow and phones those patients (FR-033).
6. A blocked patient phones: the receptionist lifts the block if the clinic agrees (FR-026).

Screens: day view, appointment panel, book for patient, patient search, reminders failed.

### Flow: A dentist checks their day   P-03 · FR-003, FR-023
1. The dentist signs in on a phone or the clinic PC and sees today's appointments at each clinic, read only.

Screens: my day.

### Flow: The practice manager sets up the week   P-04 · FR-005, FR-007, FR-008, FR-009, FR-032
1. The practice manager sets or changes a dentist's weekly hours and breaks at a clinic (FR-007).
2. They record leave; the system lists the booked appointments in that time for reception to move (FR-008).
3. They edit the treatment list (FR-009) and staff accounts (FR-005).
4. They open the no-show report per clinic and month (FR-032).

Screens: dentists and hours, leave, treatments, staff, no-show report.

## 7. Non-functional requirements
| NFR | Category | Requirement | Target | REQs |
|---|---|---|---|---|
| NFR-001 | compatibility | A mobile-friendly website; no install and no native app. Reception and the practice manager use a desktop browser. | Every patient screen works on a phone without sideways scrolling in current Chrome and Safari on Android and iPhone (A-001) | REQ-017, REQ-021 |
| NFR-002 | performance | Slot lists and the day view load quickly on a phone network. | Free slots shown within 2 s and a booking confirmed within 3 s, for 95% of requests on 4G (PD-008) | REQ-017 |
| NFR-003 | scalability | Handles today's load and a third clinic without redesign. | 2 clinics, 6 dentists, ~450 appointments a week now; 3 clinics, 10 dentists, 1,000 appointments a week later; 30 patients booking at the same time | REQ-018 |
| NFR-004 | availability | Online booking is available at any time; reception screens during clinic hours. | 99.5% per month for online booking; reception screens 08:00–20:00 Monday to Saturday (A-004, PD-008) | REQ-001 |
| NFR-005 | reliability | Reminders go out on time. | 99% of due reminders sent within 15 minutes of their due time; none sent for cancelled appointments (PD-001) | REQ-011 |
| NFR-006 | security | Role separation and safe sign-in. | Receptionists can reach only their own clinic's data; code limits as FR-002; staff passwords at least 10 characters; all traffic over HTTPS | REQ-023, REQ-026 |
| NFR-007 | privacy | Store only what is needed; follow the DPDP Act. | Only name, phone number, family members' names and birth years, appointments, treatment type and message choice are stored; no clinical data; a patient's data is deleted on request within 30 days (A-003) | REQ-025 |
| NFR-008 | localisation | English only; India time. | All screens and messages in English; times in IST | REQ-024 |
| NFR-009 | delivery | Go-live is firm. | Release 1 live on 1 March 2027 | REQ-019 |
| NFR-010 | usability | Plain screens for patients of all ages. | A new patient books in 5 screens or fewer after sign-in; tap targets at least 44 px; no formal WCAG certification | REQ-017 |
| NFR-011 | compliance | Messages follow Indian SMS and WhatsApp rules. | SMS only through DLT-registered sender ID and templates; WhatsApp only through approved templates; STOP honoured within 1 hour (A-005) | REQ-012, REQ-029 |

## 8. Assumptions, product decisions and open questions

### Product decisions
| PD | Decision | Why | Used by |
|---|---|---|---|
| PD-001 | Targets: 50% of appointments booked online within 3 months; 99% of reminders on time. | The client gave no targets. | Goals, NFR-005 |
| PD-002 | Patients can book up to 30 days ahead. | Keeps the diary manageable; default SA-007. | FR-011 |
| PD-003 | No-show can be marked from 15 minutes after the start until the end of the day, and undone the same day. | Avoids marking patients who are only late; allows fixing mistakes. | FR-022 |
| PD-004 | Quiet hours 21:00–08:00 for messages. | Default of Q-009 (SA-003). | FR-027 |
| PD-005 | A failed WhatsApp message falls back once to SMS. | A reminder that never arrives defeats the goal; default SA-008. | FR-029 |
| PD-006 | Sign-in code: 10 minutes, 5 tries, 15-minute wait. | Common practice for phone codes. | FR-002 |
| PD-007 | A family member's no-show counts against that family member, not the account holder. | The block is about the person who did not come. | FR-025 |
| PD-008 | Performance and availability targets in NFR-002 and NFR-004. | The client gave none; sized for a small clinic. | NFR-002, NFR-004 |

### Assumptions and open questions

Assumptions (proposed unless noted):
- A-001: current Chrome and Safari on phones; desktop browser at reception.
- A-002: each reception desk has a PC with internet.
- A-003: no health data; DPDP Act practice.
- A-004: availability at clinic hours, no SLA.
- A-005: SMS DLT registration and WhatsApp templates are completed by the clinic with our help.
- A-006: the practice manager signs off by trying each flow.
- SA-001: one account per phone number, up to 5 family members.
- SA-002: hosting in India chosen by us; client domain.
- SA-003: quiet hours 21:00–08:00.
- SA-004: walk-ins are booked as normal appointments and marked arrived.
- SA-005: future paper-diary appointments typed in by reception before go-live.
- SA-006: sign-in code by SMS only.
- SA-007: booking up to 30 days ahead.
- SA-008: WhatsApp fallback to SMS.

Open questions (no answer yet; the PRD uses the default):
- Q-007: can one phone number book for family members? FR-006, FR-025.
- Q-008: hosting and domain? Not in the product; affects set-up.
- Q-009: when is a night-time reminder sent? FR-027.
- Q-015: how are walk-ins recorded? FR-020, FR-032.

### Questions to raise

For the next clarification round (no Q- ID yet):

1. **No-shows today.** The client has not said how many no-shows there are now, so the no-show target in section 2 is `TBD`. We need a rough number, or agreement that the first 2 months of app data are the baseline.
2. **Fallback to SMS.** FR-029 sends an SMS to a patient who chose WhatsApp when WhatsApp fails. Does the clinic agree?

## 9. Version history

| Version | Date | Change | Request |
|---|---|---|---|
| 1.0 | 2026-11-10 | First PRD after Gate 1. | Request 1 |
