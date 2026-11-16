# Requirements register: clinic-test-2

> **Sample data.** Written by hand for a Phase 3B demo, in the requirements contract's format. Not produced by
> the Phase 1–2 agents; the client is fictional.

## Summary
Client: BrightSmile Dental, 2 dental clinics in Bengaluru (Indiranagar and Whitefield) with 6 dentists and about 450 appointments a week; a third clinic may open within 18 months. Every booking is made by phone into a paper diary per dentist, and no-shows are the clinic's biggest problem. The client wants a mobile-friendly website where patients book, reschedule and cancel; receptionists run each dentist's day, check patients in and mark no-shows; and patients get a reminder 24 hours before the visit by SMS or WhatsApp, as they choose. No online payment, no clinical records, no insurance claims, no mobile app. Go-live is firm on 1 March 2027. Round 2 answered most questions; four are still open (Q-007, Q-008, Q-009, Q-015), none blocking.

## Requirements
| REQ | Type | Statement | Sources | Status | Confidence | Round |
|---|---|---|---|---|---|---|
| REQ-001 | goal | Let patients book online instead of phoning, so reception spends less time on the phone. | SRC-001 para 2; SRC-001 para 3, bullet 1 | stated | high | R1 |
| REQ-002 | goal | Reduce no-shows, the clinic's biggest problem. | SRC-001 para 2 | stated | high | R1 |
| REQ-003 | feature | A patient books an appointment online: clinic, treatment, dentist or "first available", date and time. | SRC-001 para 3, bullet 1; SRC-002 msg 1, para 4 | confirmed | high | R1, changed R2 |
| REQ-004 | feature | A patient reschedules their appointment online. | SRC-001 para 3, bullet 2 | stated | high | R1 |
| REQ-005 | feature | A patient cancels their appointment online. | SRC-001 para 3, bullet 2 | stated | high | R1 |
| REQ-006 | constraint | Online cancel and reschedule are allowed until 4 hours before the appointment; after that the patient phones the clinic. | SRC-002 msg 1, para 3 | stated | high | R2 |
| REQ-007 | feature | Receptionists see each dentist's day at their clinic. | SRC-001 para 3, bullet 3 | stated | high | R1 |
| REQ-008 | feature | Receptionists mark a patient as a no-show. | SRC-001 para 3, bullet 3 | stated | high | R1 |
| REQ-009 | feature | Receptionists check patients in when they arrive. | SRC-001 para 3, bullet 3 | stated | high | R1 |
| REQ-010 | feature | Receptionists book, move and cancel appointments for patients who phone or walk in. Inferred: phone booking continues for longer treatments (SRC-002 msg 1, para 4) and for patients who don't book online. | SRC-002 msg 1, para 4 | inferred | medium | R2 |
| REQ-011 | feature | Patients get a reminder 24 hours before the visit. | SRC-001 para 3, bullet 4 | stated | high | R1 |
| REQ-012 | feature | Reminders go by SMS or WhatsApp; the patient chooses the channel when booking. | SRC-001 para 3, bullet 4; SRC-002 msg 1, para 1 | confirmed | high | R1, changed R2 |
| REQ-013 | feature | The practice manager sets each dentist's working hours and leave at each clinic. | SRC-002 msg 1, para 6 | stated | high | R2 |
| REQ-014 | constraint | Online booking offers only check-ups, cleanings and consultations of 30 minutes. Longer treatments (60 or 90 minutes) are booked by reception only. | SRC-002 msg 1, para 4 | stated | high | R2 |
| REQ-015 | feature | A patient with 2 no-shows in 6 months can no longer book online until reception lifts the block. | SRC-002 msg 1, para 5 | stated | high | R2 |
| REQ-016 | feature | The patient gets a message confirming a booking, a change or a cancellation, by the channel they chose. Inferred from the reminder channel choice; the client did not ask for it. | SRC-002 msg 1, para 1 | inferred | medium | R2 |
| REQ-017 | nfr | It works well on a phone, as a website; most patients book from their phone. | SRC-001 para 4 | stated | high | R1 |
| REQ-018 | nfr | 2 clinics, 6 dentists, about 450 appointments a week; a third clinic may open within 18 months. | SRC-001 para 1; SRC-001 para 4; SRC-002 msg 1, para 10 | confirmed | high | R1, changed R2 |
| REQ-019 | constraint | Go-live on 1 March 2027 is firm (2 new chairs open at Whitefield that day). | SRC-002 msg 1, para 10 | stated | high | R2 |
| REQ-020 | not-wanted | Insurance claims are not handled. | SRC-001 para 5 | stated | high | R1 |
| REQ-021 | not-wanted | No native mobile app. | SRC-001 para 5 | stated | high | R1 |
| REQ-022 | not-wanted | No online payment or deposit; patients pay at the clinic. | SRC-002 msg 1, para 2 | stated | high | R2 |
| REQ-023 | feature | Patients sign in with their phone number and a one-time code; no passwords for patients. | SRC-002 msg 1, para 7 | stated | high | R2 |
| REQ-024 | nfr | English only. | SRC-002 msg 1, para 8 | stated | high | R2 |
| REQ-025 | data | No clinical notes, X-rays or treatment records in the app; they stay in the clinic's own software. | SRC-002 msg 1, para 9 | stated | high | R2 |
| REQ-026 | feature | Four roles: patient, receptionist (own clinic), dentist (own day, read only) and practice manager (both clinics). | SRC-001 para 3; SRC-002 msg 1, para 6 | confirmed | medium | R1, changed R2 |
| REQ-027 | feature | A dentist sees their own day; dentists do not book. | SRC-002 msg 1, para 6 | stated | high | R2 |
| REQ-028 | feature | The practice manager sees the number of no-shows each month at each clinic. | SRC-002 msg 1, para 12 | stated | high | R2 |
| REQ-029 | integration | SMS and WhatsApp accounts are opened in the clinic's name with a provider we choose; the clinic pays the message charges. | SRC-002 msg 1, para 11 | stated | high | R2 |
| REQ-030 | data | Future appointments in the paper diary on go-live day are typed in by reception; no import. | SRC-002 msg 1, para 13 | stated | high | R2 |

## Conflicts
None open. Round 1 said "SMS reminder"; round 2 added WhatsApp alongside SMS with the patient's choice (REQ-012 changed).

## Change log
### Round 1
- REQ-001 to REQ-012, REQ-017, REQ-018, REQ-020, REQ-021, REQ-026 raised from SRC-001.
### Round 2
- REQ-003 changed: dentist or "first available"; only 30-minute treatments online.
- REQ-012 changed: WhatsApp added alongside SMS, patient chooses.
- REQ-018 changed: third clinic within 18 months.
- REQ-026 changed: dentist role confirmed, read only.
- REQ-006, REQ-010, REQ-013 to REQ-016, REQ-019, REQ-022 to REQ-025, REQ-027 to REQ-030 added from SRC-002.
