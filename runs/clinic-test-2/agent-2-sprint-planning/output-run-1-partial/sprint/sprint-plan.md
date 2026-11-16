# Sprint plan v16 — clinic-test-2

Solver **FEASIBLE** (10.003s) · as of 2026-11-13

- Sprint 1 delivers staff sign-in with username and password and role-based visibility. It also holds setup for most epics and foundations for MOD-01, 03 and 04. Patient sign-in, appointments and booking follow in sprints 2 to 4.
- DL-1 risk: the must-have S-POLISH-006 (reminder contract and load tests) is in sprint 8. Sprint 8 starts on the DL-1 date (2027-02-22) and ends 2027-03-07, so it finishes after DL-1. All other must-haves finish by sprint 7.
- Capacity risk: Release 1 holds about 201 SP, but sprints 1 to 7 only hold about 190 SP at P85. All 8 sprints are planned at their P50 ceiling, which is 123% of P85 (35 against 28.4, or 31 against 25.2). Capacity is a cold-start estimate with low confidence, so expect slippage.
- The request wants Release 2 after DL-1, but the solver still places some Release 2 work early. That is setup 007 to 010, foundation 007 and 010, and the fallback stories 009-US1 to US4. It takes capacity the must-haves need. I tried pinning these, but I should not have: the request has no pins. That attempt gave an infeasible result, and I re-solved with no pins. The saved plan has none.
- Forecast for the whole backlog: P50 sprint 10 (about 2027-04-04), P85 sprint 11 (about 2027-04-18). S-POLISH-008 is deferred. No story is unestimated or too large.
- Decision for you: (a) pin S-POLISH-006 to sprint 7 and Release 2 stories to sprint 8 or later, then I re-solve; (b) cut or re-baseline Release 1 scope; (c) accept the DL-1 risk. Agent 1 should also check Release 1 against the Phase 2 estimate, because it looks to be at the top of that range.

Forecast for the whole backlog: sprint 10 (2027-04-04) at P50, sprint 11 (2027-04-18) at P85.

## BrightSmile Booking Sprint 1 (2026-11-16 → 2026-11-29)

Goal: Staff can sign in with a username and password and each role sees only the screens and data it needs.

35 SP committed · capacity P85 28.4 / P50 35.4 · 3.9 SP reserved for maintenance · 56.25 person-days

- S-SETUP-003 Online booking by patients (MOD-03): Setup — 1 SP · WSJF 100.0
- S-SETUP-004 Patient appointments: view, reschedule, cancel: Setup — 1 SP · WSJF 95.65
- S-SETUP-005 Reception day view, check-in, no-shows and dentist day (MOD-05): Setup — 1 SP · WSJF 95.65
- S-SETUP-002 Dentist schedules, treatments and free slots: Setup — 1 SP · WSJF 91.3
- S-SETUP-001 Platform, sign-in, roles and clinics (MOD-01): Setup — 2 SP · WSJF 52.17
- S-SETUP-009 WhatsApp to SMS fallback and reminders-failed list: Setup — 1 SP · WSJF 43.48
- S-SETUP-008 Repeat no-show block: Setup — 1 SP · WSJF 39.13
- S-SETUP-010 No-show report per clinic and month: Setup — 1 SP · WSJF 39.13
- S-FOUND-010 No-show report per clinic and month: Foundational prerequisites — 1 SP · WSJF 34.78
- S-FOUND-004 Patient appointments: view, reschedule, cancel: Foundational prerequisites — 3 SP · WSJF 31.88
- S-001-US3 Each role sees only what it needs — 3 SP · WSJF 23.19
- S-FOUND-003 Online booking by patients (MOD-03): Foundational prerequisites — 5 SP · WSJF 22.61
- S-001-US2 Staff sign in with a username and password — 3 SP · WSJF 21.74
- S-001-US6 A patient's data is erased on request — 3 SP · WSJF 15.94
- S-FOUND-001 Platform, sign-in, roles and clinics (MOD-01): Foundational prerequisites — 8 SP · WSJF 13.04

## BrightSmile Booking Sprint 2 (2026-11-30 → 2026-12-13)

Goal: Patients can sign in with their phone number and a code, see their appointments and cancel one.

35 SP committed · capacity P85 28.4 / P50 35.4 · 3.9 SP reserved for maintenance · 56.25 person-days

- S-SETUP-006 Confirmations, reminders and opt-out via SMS and WhatsApp: Setup — 2 SP · WSJF 45.65
- S-002-US1 Manage treatment types — 3 SP · WSJF 31.88
- S-004-US4 Open an appointment from a message link — 2 SP · WSJF 28.26
- S-001-US7 Old identity data is cleaned up automatically — 2 SP · WSJF 21.74
- S-001-US1 A patient signs in with a phone number and a code — 5 SP · WSJF 20.0
- S-004-US1 See my appointments — 5 SP · WSJF 19.13
- S-FOUND-002 Dentist schedules, treatments and free slots: Foundational prerequisites — 5 SP · WSJF 18.26
- S-001-US4 The practice manager manages staff accounts — 3 SP · WSJF 17.39
- S-001-US5 The system holds the clinics and the dentists — 3 SP · WSJF 17.39
- S-004-US2 Cancel an upcoming appointment — 5 SP · WSJF 16.52

## BrightSmile Booking Sprint 3 (2026-12-14 → 2026-12-27)

Goal: A patient who books gets an immediate confirmation and can see the booking.

31 SP committed · capacity P85 25.2 / P50 31.5 · 3.5 SP reserved for maintenance · 50.0 person-days

- S-006-US1 Choose SMS or WhatsApp when booking — 3 SP · WSJF 37.68
- S-POLISH-001 Platform, sign-in, roles and clinics (MOD-01): Polish & cross-cutting concerns — 2 SP · WSJF 21.74
- S-FOUND-006 Confirmations, reminders and opt-out via SMS and WhatsApp: Foundational prerequisites — 5 SP · WSJF 20.0
- S-002-US2 Set weekly working hours and breaks — 5 SP · WSJF 19.13
- S-003-US2 Confirm and see the booking — 8 SP · WSJF 14.13
- S-006-US2 Immediate booking confirmation — 8 SP · WSJF 14.13

## BrightSmile Booking Sprint 4 (2026-12-28 → 2027-01-10)

Goal: A patient can find a free slot on a phone and book it, and a slot is never booked twice.

31 SP committed · capacity P85 25.2 / P50 31.5 · 3.5 SP reserved for maintenance · 50.0 person-days

- S-006-US6 Sign-in codes sent by SMS — 2 SP · WSJF 28.26
- S-POLISH-003 Online booking by patients (MOD-03): Polish & cross-cutting concerns — 2 SP · WSJF 26.09
- S-003-US4 Prove no double booking under load — 3 SP · WSJF 18.84
- S-003-US5 Prove booking speed on a phone network — 3 SP · WSJF 15.94
- S-003-US6 Booking works on a phone for a new patient — 3 SP · WSJF 15.94
- S-003-US1 Find a free slot — 5 SP · WSJF 15.65
- S-003-US3 A slot is never booked twice — 5 SP · WSJF 13.91
- S-002-US3 Find free slots and first available — 8 SP · WSJF 12.5

## BrightSmile Booking Sprint 5 (2027-01-11 → 2027-01-24)

Goal: Patients get a reminder 24 hours before the visit, outside quiet hours, and can reschedule their appointment.

35 SP committed · capacity P85 28.4 / P50 35.4 · 3.9 SP reserved for maintenance · 56.25 person-days

- S-SETUP-007 Family members on a patient account: Setup — 1 SP · WSJF 39.13
- S-006-US3 Reminder 24 hours before, with quiet hours — 3 SP · WSJF 36.23
- S-006-US4 Reminders follow changes; change notices — 3 SP · WSJF 26.09
- S-POLISH-002 Dentist schedules, treatments and free slots: Polish & cross-cutting concerns — 2 SP · WSJF 21.74
- S-FOUND-005 Reception day view, check-in, no-shows and dentist day (MOD-05): Foundational prerequisites — 5 SP · WSJF 19.13
- S-006-US5 Stop reminders by replying STOP or through reception — 5 SP · WSJF 14.78
- S-FOUND-009 WhatsApp to SMS fallback and reminders-failed list: Foundational prerequisites — 3 SP · WSJF 13.04
- S-002-US4 Record dentist leave and list appointments to move — 5 SP · WSJF 10.43
- S-004-US3 Reschedule an upcoming appointment — 8 SP · WSJF 9.24

## BrightSmile Booking Sprint 6 (2027-01-25 → 2027-02-07)

Goal: Reception sees the day of their clinic and can mark patients as arrived or no-show.

31 SP committed · capacity P85 25.2 / P50 31.5 · 3.5 SP reserved for maintenance · 50.0 person-days

- S-POLISH-004 Patient appointments: view, reschedule, cancel: Polish & cross-cutting concerns — 2 SP · WSJF 26.09
- S-005-US1 Reception sees the day of their clinic — 5 SP · WSJF 19.13
- S-005-US2 Reception marks arrived and no-show, and can undo — 5 SP · WSJF 19.13
- S-005-US5 Dentist sees their own day, read only — 3 SP · WSJF 17.39
- S-FOUND-007 Family members on a patient account: Foundational prerequisites — 2 SP · WSJF 17.39
- S-009-US2 The fallback respects STOP, cancellations and the switch — 3 SP · WSJF 8.7
- S-009-US3 An appointment is marked "reminder failed" when the SMS also fails — 3 SP · WSJF 7.25
- S-009-US4 Reception gets tomorrow's reminders-failed list — 3 SP · WSJF 7.25
- S-009-US1 A failed WhatsApp reminder is sent once by SMS — 5 SP · WSJF 6.09

## BrightSmile Booking Sprint 7 (2027-02-08 → 2027-02-21)

Goal: Reception can find or create a patient and book, move or cancel appointments for them.

35 SP committed · capacity P85 28.4 / P50 35.4 · 3.9 SP reserved for maintenance · 56.25 person-days

- S-POLISH-005 Reception day view, check-in, no-shows and dentist day (MOD-05): Polish & cross-cutting concerns — 3 SP · WSJF 17.39
- S-005-US3 Reception finds or creates a patient — 5 SP · WSJF 12.17
- S-006-US7 Reliable and compliant delivery operations — 8 SP · WSJF 9.24
- S-007-US2 Choose who the visit is for when booking — 3 SP · WSJF 8.7
- S-007-US3 See family members' appointments, and only those — 3 SP · WSJF 7.25
- S-005-US4 Reception books, moves and cancels for patients — 8 SP · WSJF 7.07
- S-007-US1 Add and manage family members — 5 SP · WSJF 6.09

## BrightSmile Booking Sprint 8 (2027-02-22 → 2027-03-07)

Goal: The practice manager can open a monthly no-show report per clinic.

35 SP committed · capacity P85 28.4 / P50 35.4 · 3.9 SP reserved for maintenance · 56.25 person-days

- S-POLISH-006 Confirmations, reminders and opt-out via SMS and WhatsApp: Polish & cross-cutting concerns — 3 SP · WSJF 20.29
- S-POLISH-010 No-show report per clinic and month: Polish & cross-cutting concerns — 1 SP · WSJF 17.39
- S-010-US2 No-show report screen for the practice manager — 2 SP · WSJF 13.04
- S-FOUND-008 Repeat no-show block: Foundational prerequisites — 3 SP · WSJF 11.59
- S-008-US3 Reception lifts a block and the count restarts — 2 SP · WSJF 10.87
- S-008-US4 The block follows no-show corrections — 2 SP · WSJF 10.87
- S-010-US3 Only the practice manager can read the report — 2 SP · WSJF 10.87
- S-010-US1 Monthly no-show figures per clinic — 3 SP · WSJF 10.14
- S-007-US4 Erase family member data and keep it out of logs — 2 SP · WSJF 8.7
- S-008-US2 Reception sees who is blocked — 3 SP · WSJF 8.7
- S-POLISH-007 Family members on a patient account: Polish & cross-cutting concerns — 2 SP · WSJF 6.52
- S-POLISH-009 WhatsApp to SMS fallback and reminders-failed list: Polish & cross-cutting concerns — 2 SP · WSJF 6.52
- S-008-US1 A repeat no-show patient cannot book or reschedule online — 5 SP · WSJF 6.09
- S-009-US5 "Reminders failed" screen for reception — 3 SP · WSJF 5.8

## Deferred

- S-POLISH-008 `capacity`: Not planned in the 8 sprints: capacity is used by Release 1 must-haves and higher-value stories. It is a Release 2 hardening story and is forecast for sprint 9.

## Assumptions

- Cold start: fewer than 3 closed sprints with history; capacity = person-hours ÷ 6.0 h/SP × 0.7 (low confidence).
- 10% of capacity reserved for maintenance work.
