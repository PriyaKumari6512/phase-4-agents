# Clarifications: clinic-test-2

> **Sample data.** Written by hand for a Phase 3B demo, in the requirements contract's format. Not produced by
> the Phase 1–2 agents; the client is fictional.

## Questions for the client: round 1

Thank you for the brief. The questions below are the points we need you to decide before we fix scope and plan. For each one we say what we will assume if we don't hear back.

### Must answer first
- Q-004: By which date must the app be live, and is the date firm?
- Q-002: Reminders by SMS, WhatsApp or both?

### Booking rules
- Q-001, Q-005, Q-006, Q-011, Q-015.

### Roles, sign-in and data
- Q-003, Q-010, Q-012, Q-013, Q-014.

## Questions for the client: round 2

Thank you for the answers. Four points are still open; we use the default shown until you tell us otherwise.

### Still open
- Q-007 (family members), Q-008 (hosting), Q-009 (night-time reminders), Q-015 (walk-ins).

## Questions
| Q | Question | Why we ask | REQs | Blocking | Suggested default | Status | Raised | Answer |
|---|---|---|---|---|---|---|---|---|
| Q-001 | Do patients choose a dentist, or does the clinic assign one? | Decides the booking screens and how free slots are found. | REQ-003 | no | Patients choose a dentist or "first available". | answered | R1 | A dentist or "first available" (SRC-002 msg 1, para 4). |
| Q-002 | Reminders by SMS, WhatsApp or both? | The two need different accounts and template approval. | REQ-011, REQ-012 | yes | SMS only. | answered | R1 | Both: the patient chooses when booking (SRC-002 msg 1, para 1). |
| Q-003 | Do patients pay anything online (fee or deposit)? | Online payment adds a payment provider and refunds. | REQ-022 | no | No online payment. | answered | R1 | No; patients pay at the clinic (SRC-002 msg 1, para 2). |
| Q-004 | By which date must the app be live, and is it firm? | Sets the timeline and the first release. | REQ-019 | yes | 1 March 2027, movable by 2 weeks. | answered | R1 | 1 March 2027, firm (SRC-002 msg 1, para 10). |
| Q-005 | Until when can a patient cancel or reschedule online? | Late changes leave empty chairs. | REQ-004, REQ-005, REQ-006 | no | Until 24 hours before. | answered | R1 | Until 4 hours before (SRC-002 msg 1, para 3). |
| Q-006 | Should repeat no-shows be stopped from booking online? | The brief names no-shows as the main problem. | REQ-002, REQ-015 | no | No block; reminders only. | answered | R1 | Yes: 2 no-shows in 6 months block online booking; reception can lift it (SRC-002 msg 1, para 5). |
| Q-007 | Can one phone number book for family members (children, a parent)? | Sign-in is by phone number, and families often share one phone. | REQ-003, REQ-023 | no | One account per phone number; the account holder can add up to 5 family members by name and book for them. | open | R2 | Not answered in round 2. |
| Q-008 | Do you have a domain or hosting we must use? | Affects set-up and hand-over. | REQ-001 | no | We host in a standard cloud region in India; the clinic provides the domain. | open | R1 | Not answered. |
| Q-009 | If "24 hours before" falls at night, when is the reminder sent? | Night messages annoy patients; WhatsApp has rules on timing. | REQ-011 | no | No reminders between 21:00 and 08:00; a reminder due then is sent at 20:00 the evening before. | open | R2 | Not answered. |
| Q-010 | Do dentists sign in? What do they see? | Decides the roles. | REQ-026, REQ-027 | no | No dentist sign-in. | answered | R1 | Yes, to see their own day; they don't book (SRC-002 msg 1, para 6). |
| Q-011 | How long is an appointment, and can every treatment be booked online? | Decides slot length and what patients may book. | REQ-014 | no | All treatments, 30 minutes. | answered | R1 | 30-minute check-ups, cleanings and consultations online; longer treatments by reception (SRC-002 msg 1, para 4). |
| Q-012 | Which languages? | Each language adds work on every screen and message. | REQ-024 | no | English only. | answered | R1 | English only (SRC-002 msg 1, para 8). |
| Q-013 | Should the app keep clinical notes or treatment records? | Health records bring stricter data rules. | REQ-025 | no | No clinical records. | answered | R1 | No (SRC-002 msg 1, para 9). |
| Q-014 | Do you already have SMS or WhatsApp business accounts? | Account set-up and template approval take time. | REQ-029 | no | We open them in the clinic's name. | answered | R1 | No accounts; we choose, in the clinic's name; the clinic pays message charges (SRC-002 msg 1, para 11). |
| Q-015 | How are walk-in patients recorded? | The no-show figures and the day view need them. | REQ-010 | no | Reception books a walk-in into a free slot as a normal appointment and marks it arrived. | open | R2 | Not answered. |

## Assumptions
| A | Assumption | From | REQs | Status |
|---|---|---|---|---|
| A-001 | The app is a website used in current Chrome and Safari on phones, and in a desktop browser at reception. | gap: no browser targets given | REQ-017 | proposed |
| A-002 | Each reception desk has a PC with a current browser and internet. | gap: reception hardware not stated | REQ-007 | proposed |
| A-003 | The app stores only name, phone number, appointments and treatment type (and family members' names and birth year if Q-007's default holds); no health data. Normal DPDP Act practice applies. | REQ-025 | REQ-025 | proposed |
| A-004 | Availability at clinic hours (08:00–20:00, Monday to Saturday) with no formal SLA; support after go-live is agreed separately. | gap: not stated | REQ-001 | proposed |
| A-005 | SMS in India needs DLT registration of the sender ID and templates; WhatsApp needs approved templates. The clinic completes the registrations we prepare. | gap: regulatory | REQ-012, REQ-029 | proposed |
| A-006 | The practice manager signs off by trying each flow in the brief. | gap: acceptance not stated | REQ-001 | proposed |
