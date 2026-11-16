# Scope: clinic-test-2

> **Sample data.** Written by hand for a Phase 3B demo, in the requirements contract's format. Not produced by
> the Phase 1–2 agents; the client is fictional.

## Summary
Ready for Gate 1: no blocking question is open (Q-007, Q-008, Q-009 and Q-015 are open with defaults).

BrightSmile Dental (2 clinics in Bengaluru, 6 dentists, about 450 appointments a week) gets a mobile-friendly website, not a native app. Patients sign in with a phone code and book, reschedule and cancel 30-minute check-ups, cleanings and consultations with a dentist or "first available". Reception runs each dentist's day, books longer treatments and walk-ins, checks patients in and marks no-shows. Patients get a confirmation and a reminder 24 hours before by SMS or WhatsApp, as they choose. Two no-shows in 6 months block online booking. The practice manager sets dentists' hours and leave and sees no-shows per clinic per month. Go-live is firm on 1 March 2027. No online payment, clinical records, insurance claims or mobile app.

## Modules
| MOD | Module | REQs |
|---|---|---|
| MOD-01 | Platform, sign-in, roles and clinics | REQ-017, REQ-018, REQ-019, REQ-023, REQ-024, REQ-025, REQ-026 |
| MOD-02 | Dentist schedules, treatments and slots | REQ-013, REQ-014 |
| MOD-03 | Online booking | REQ-003 |
| MOD-04 | Patient appointments: view, reschedule, cancel | REQ-004, REQ-005, REQ-006 |
| MOD-05 | Reception day view, check-in and no-shows | REQ-007, REQ-008, REQ-009, REQ-010, REQ-027, REQ-030 |
| MOD-06 | Repeat no-show block | REQ-015 |
| MOD-07 | Reminders and messages (SMS and WhatsApp) | REQ-011, REQ-012, REQ-016, REQ-029 |
| MOD-08 | No-show report | REQ-028 |

## In scope
| REQ | Item | MOD | Notes |
|---|---|---|---|
| REQ-003 | Online booking: clinic, treatment, dentist or first available, slot | MOD-03 | Next 30 days only (SA-007). |
| REQ-004 | Online reschedule | MOD-04 | |
| REQ-005 | Online cancel | MOD-04 | |
| REQ-006 | 4-hour cut-off for online changes | MOD-04 | Reception has no cut-off. |
| REQ-007 | Day view per dentist at each clinic | MOD-05 | |
| REQ-008 | Mark no-show | MOD-05 | |
| REQ-009 | Check a patient in on arrival | MOD-05 | |
| REQ-010 | Reception books, moves and cancels for phone and walk-in patients | MOD-05 | Walk-ins per SA-004. |
| REQ-011 | Reminder 24 hours before | MOD-07 | Quiet hours per SA-003. |
| REQ-012 | SMS or WhatsApp, patient chooses | MOD-07 | DLT and template approval (DEP-001, DEP-002). |
| REQ-013 | Dentists' hours and leave | MOD-02 | Set by the practice manager. |
| REQ-014 | 30-minute online treatments; longer ones by reception | MOD-02 | Treatment list from the clinic (DEP-003). |
| REQ-015 | Block online booking after 2 no-shows in 6 months | MOD-06 | Reception lifts the block. |
| REQ-016 | Booking, change and cancellation messages | MOD-07 | |
| REQ-017 | Mobile-friendly website | MOD-01 | A-001. |
| REQ-018 | 2 clinics, 6 dentists, ~450 appointments a week; third clinic later | MOD-01 | A third clinic is added as data, no rebuild. |
| REQ-019 | Go-live 1 March 2027 (firm) | MOD-01 | Drives the release plan. |
| REQ-023 | Patient sign-in by phone code | MOD-01 | Code by SMS (SA-006). |
| REQ-024 | English only | MOD-01 | |
| REQ-025 | No clinical records | MOD-01 | A-003. |
| REQ-026 | Four roles | MOD-01 | |
| REQ-027 | Dentist sees own day | MOD-05 | Read only. |
| REQ-028 | No-shows per clinic per month | MOD-08 | On screen, no export. |
| REQ-029 | SMS and WhatsApp accounts in the clinic's name | MOD-07 | Client pays message charges. |
| REQ-030 | Future paper-diary appointments typed in by reception | MOD-05 | No import (SA-005). |

## Out of scope
| Item | REQs | Reason |
|---|---|---|
| Insurance claims | REQ-020 | client-said |
| Native mobile app | REQ-021 | client-said |
| Online payment, deposits, refunds | REQ-022 | client-said |
| Clinical notes, X-rays, treatment records, prescriptions | REQ-025 | client-said |
| Import of past or future appointments from the paper diary | REQ-030 | client-said |
| Waiting lists, recalls ("your 6-month check-up is due"), marketing messages | | not-requested |
| Integration with the clinic's own dental software | | not-requested |
| Kannada or Hindi screens | | not-requested |
| Export of reports to Excel or PDF | | not-requested |

## Assumptions
| SA | Assumption | Affects |
|---|---|---|
| SA-001 | One account per phone number; the account holder can add up to 5 family members by name and birth year and book for them. Default of Q-007 (open). | MOD-01, MOD-03, MOD-06 |
| SA-002 | We host in a standard cloud region in India; the clinic provides the domain and owns the accounts at hand-over. Default of Q-008 (open). | Cross-cutting DevOps |
| SA-003 | No messages between 21:00 and 08:00 India time; a reminder due then is sent at 20:00 the evening before. Default of Q-009 (open). | MOD-07 |
| SA-004 | Reception books a walk-in into a free slot as a normal appointment and marks it arrived. Default of Q-015 (open). | MOD-05, MOD-08 |
| SA-005 | Reception types in the future appointments from the paper diary in the 2 weeks before go-live, using the normal reception booking screens. | MOD-05 |
| SA-006 | The patient's sign-in code goes by SMS (the SMS account is needed anyway); a WhatsApp code is not offered. | MOD-01, MOD-07 |
| SA-007 | Patients can book up to 30 days ahead. | MOD-03 |
| SA-008 | If a WhatsApp reminder cannot be delivered, it is sent once by SMS instead. | MOD-07 |
| SA-009 | The scope otherwise relies on A-001 to A-006 as written in the clarifications file. | All |

## Dependencies
| DEP | Dependency | Owner | Needed by |
|---|---|---|---|
| DEP-001 | SMS account in the clinic's name with DLT-registered sender ID and templates (sign-in code, confirmation, reminder) | Clinic | Test account in week 1; registration done before UAT |
| DEP-002 | WhatsApp Business number in the clinic's name and approved message templates | Clinic | Number in week 2; templates approved before UAT |
| DEP-003 | Treatment list (which are online, durations) and each dentist's weekly hours at each clinic | Practice manager | Week 2 |
| DEP-004 | Domain or subdomain for the website | Clinic | Before UAT |
| DEP-005 | Reception PCs with a current browser at both clinics | Clinic | Before UAT |
| DEP-006 | Reception time to type in the future appointments from the paper diary | Clinic | 2 weeks before go-live |

## Risks from open questions
| Q | Risk if unanswered | Effect on scope / estimate |
|---|---|---|
| Q-007 | Families may need separate accounts with the same phone number, which the sign-in cannot do. | MOD-01 and MOD-03 grow by 2–4 person-days if family members need their own sign-in. |
| Q-009 | The client may want a different reminder time. | Small: a setting, under 1 person-day. |
| Q-015 | Walk-ins recorded differently would change the no-show rate. | MOD-08 definition only. |
| Q-008 | A client-mandated host may differ from our choice. | DevOps share only. |
