# Sprint plan v61 — clinic-test-2

Solver **OPTIMAL** (0.217s) · as of 2026-11-13

**Result:** The plan is saved and solver-verified (OPTIMAL), but it is not fully clean. One Release 1 must-have, S-POLISH-006 (3 SP, polish for reminders), lands in sprint 8, after DL-1 (2027-02-22). It can only start after S-006-US7, which sits in sprint 7, and no valid plan found places it earlier. With DL-1 held as a hard date the solver said INFEASIBLE, so I used its only verified option, "soften DL-1". All other must-haves finish in sprints 1-7.
**Capacity basis:** P50 is the hard cap. Capacity is a cold-start estimate (low confidence). Over P85: sprint 1 (35 vs 28.4), sprint 8 (32 vs 28.4), and sprints 2, 3, 5 and 7 by 1-3 SP. Sprints 4 and 6 are at 99% of P85. If velocity comes in at P85, the sprint 8 Release 2 work slips first: the no-show report (S-010 stories) and then the repeat no-show block (S-008 stories). S-POLISH-006 slips as well.
**Release 2:** No-show block and report are in sprint 8 (they have no Release 1 dependents). Family members (S-007) and the SMS fallback (S-009), 15 stories, are outside the horizon. Forecast to finish everything: P50 2027-04-04, P85 2027-04-18. DL-2 (2027-03-19) is at risk and is missed even in the P50 case.
**Decision needed:** Approve accepting S-POLISH-006 after DL-1, or give a way to free capacity before sprint 7, for example a smaller scope for S-006-US7. Also decide whether DL-2 moves or Release 2 scope is cut.

Forecast for the whole backlog: sprint 10 (2027-04-04) at P50, sprint 11 (2027-04-18) at P85.

## BrightSmile Booking Sprint 1 (2026-11-16 → 2026-11-29)

Goal: Clinic staff can sign in with a username and password and see only what their role allows.

35 SP committed · capacity P85 28.4 / P50 35.4 · 3.9 SP reserved for maintenance · 56.25 person-days

- S-SETUP-003 Online booking by patients (MOD-03): Setup — 1 SP · WSJF 100.0
- S-SETUP-004 Patient appointments: view, reschedule, cancel: Setup — 1 SP · WSJF 91.3
- S-SETUP-005 Reception day view, check-in, no-shows and dentist day (MOD-05): Setup — 1 SP · WSJF 91.3
- S-SETUP-002 Dentist schedules, treatments and free slots: Setup — 1 SP · WSJF 86.96
- S-SETUP-001 Platform, sign-in, roles and clinics (MOD-01): Setup — 2 SP · WSJF 52.17
- S-SETUP-006 Confirmations, reminders and opt-out via SMS and WhatsApp: Setup — 2 SP · WSJF 43.48
- S-FOUND-004 Patient appointments: view, reschedule, cancel: Foundational prerequisites — 3 SP · WSJF 30.43
- S-FOUND-003 Online booking by patients (MOD-03): Foundational prerequisites — 5 SP · WSJF 22.61
- S-001-US3 Each role sees only what it needs — 3 SP · WSJF 21.74
- S-001-US2 Staff sign in with a username and password — 3 SP · WSJF 20.29
- S-001-US7 Old identity data is cleaned up automatically — 2 SP · WSJF 19.57
- S-001-US6 A patient's data is erased on request — 3 SP · WSJF 14.49
- S-FOUND-001 Platform, sign-in, roles and clinics (MOD-01): Foundational prerequisites — 8 SP · WSJF 13.04

## BrightSmile Booking Sprint 2 (2026-11-30 → 2026-12-13)

Goal: A patient can sign in with a phone number and a code.

29 SP committed · capacity P85 28.4 / P50 35.4 · 3.9 SP reserved for maintenance · 56.25 person-days

- S-002-US1 Manage treatment types — 3 SP · WSJF 30.43
- S-001-US1 A patient signs in with a phone number and a code — 5 SP · WSJF 19.13
- S-FOUND-006 Confirmations, reminders and opt-out via SMS and WhatsApp: Foundational prerequisites — 5 SP · WSJF 19.13
- S-FOUND-005 Reception day view, check-in, no-shows and dentist day (MOD-05): Foundational prerequisites — 5 SP · WSJF 18.26
- S-001-US5 The system holds the clinics and the dentists — 3 SP · WSJF 17.39
- S-FOUND-002 Dentist schedules, treatments and free slots: Foundational prerequisites — 5 SP · WSJF 17.39
- S-001-US4 The practice manager manages staff accounts — 3 SP · WSJF 15.94

## BrightSmile Booking Sprint 3 (2026-12-14 → 2026-12-27)

Goal: Patients can choose SMS or WhatsApp for their messages and get an immediate booking confirmation.

26 SP committed · capacity P85 25.2 / P50 31.5 · 3.5 SP reserved for maintenance · 50.0 person-days

- S-006-US1 Choose SMS or WhatsApp when booking — 3 SP · WSJF 34.78
- S-006-US3 Reminder 24 hours before, with quiet hours — 3 SP · WSJF 33.33
- S-006-US6 Sign-in codes sent by SMS — 2 SP · WSJF 28.26
- S-POLISH-001 Platform, sign-in, roles and clinics (MOD-01): Polish & cross-cutting concerns — 2 SP · WSJF 17.39
- S-003-US2 Confirm and see the booking — 8 SP · WSJF 14.13
- S-006-US2 Immediate booking confirmation — 8 SP · WSJF 13.59

## BrightSmile Booking Sprint 4 (2026-12-28 → 2027-01-10)

Goal: Patients can see their upcoming appointments and cancel them.

25 SP committed · capacity P85 25.2 / P50 31.5 · 3.5 SP reserved for maintenance · 50.0 person-days

- S-004-US4 Open an appointment from a message link — 2 SP · WSJF 23.91
- S-002-US2 Set weekly working hours and breaks — 5 SP · WSJF 19.13
- S-004-US1 See my appointments — 5 SP · WSJF 18.26
- S-005-US1 Reception sees the day of their clinic — 5 SP · WSJF 18.26
- S-005-US5 Dentist sees their own day, read only — 3 SP · WSJF 15.94
- S-004-US2 Cancel an upcoming appointment — 5 SP · WSJF 15.65

## BrightSmile Booking Sprint 5 (2027-01-11 → 2027-01-24)

Goal: A patient can find a free slot on a phone and book it, and the slot is never booked twice.

29 SP committed · capacity P85 28.4 / P50 35.4 · 3.9 SP reserved for maintenance · 56.25 person-days

- S-POLISH-003 Online booking by patients (MOD-03): Polish & cross-cutting concerns — 2 SP · WSJF 23.91
- S-003-US4 Prove no double booking under load — 3 SP · WSJF 17.39
- S-003-US6 Booking works on a phone for a new patient — 3 SP · WSJF 15.94
- S-003-US1 Find a free slot — 5 SP · WSJF 15.65
- S-003-US5 Prove booking speed on a phone network — 3 SP · WSJF 14.49
- S-003-US3 A slot is never booked twice — 5 SP · WSJF 13.91
- S-002-US3 Find free slots and first available — 8 SP · WSJF 12.5

## BrightSmile Booking Sprint 6 (2027-01-25 → 2027-02-07)

Goal: Patients can reschedule an upcoming appointment themselves.

25 SP committed · capacity P85 25.2 / P50 31.5 · 3.5 SP reserved for maintenance · 50.0 person-days

- S-006-US4 Reminders follow changes; change notices — 3 SP · WSJF 24.64
- S-POLISH-004 Patient appointments: view, reschedule, cancel: Polish & cross-cutting concerns — 2 SP · WSJF 21.74
- S-005-US2 Reception marks arrived and no-show, and can undo — 5 SP · WSJF 18.26
- S-POLISH-002 Dentist schedules, treatments and free slots: Polish & cross-cutting concerns — 2 SP · WSJF 17.39
- S-002-US4 Record dentist leave and list appointments to move — 5 SP · WSJF 9.57
- S-004-US3 Reschedule an upcoming appointment — 8 SP · WSJF 8.7

## BrightSmile Booking Sprint 7 (2027-02-08 → 2027-02-21)

Goal: Reception can find or create a patient and book, move or cancel appointments for them.

29 SP committed · capacity P85 28.4 / P50 35.4 · 3.9 SP reserved for maintenance · 56.25 person-days

- S-POLISH-005 Reception day view, check-in, no-shows and dentist day (MOD-05): Polish & cross-cutting concerns — 3 SP · WSJF 14.49
- S-006-US5 Stop reminders by replying STOP or through reception — 5 SP · WSJF 13.91
- S-005-US3 Reception finds or creates a patient — 5 SP · WSJF 10.43
- S-006-US7 Reliable and compliant delivery operations — 8 SP · WSJF 8.15
- S-005-US4 Reception books, moves and cancels for patients — 8 SP · WSJF 6.52

## BrightSmile Booking Sprint 8 (2027-02-22 → 2027-03-07)

Goal: Reception can see which patients are blocked for repeat no-shows and lift a block.

32 SP committed · capacity P85 28.4 / P50 35.4 · 3.9 SP reserved for maintenance · 56.25 person-days

- S-SETUP-008 Repeat no-show block: Setup — 1 SP · WSJF 52.17
- S-SETUP-010 No-show report per clinic and month: Setup — 1 SP · WSJF 43.48
- S-FOUND-010 No-show report per clinic and month: Foundational prerequisites — 1 SP · WSJF 39.13
- S-POLISH-010 No-show report per clinic and month: Polish & cross-cutting concerns — 1 SP · WSJF 21.74
- S-POLISH-006 Confirmations, reminders and opt-out via SMS and WhatsApp: Polish & cross-cutting concerns — 3 SP · WSJF 17.39
- S-FOUND-008 Repeat no-show block: Foundational prerequisites — 3 SP · WSJF 15.94
- S-008-US3 Reception lifts a block and the count restarts — 2 SP · WSJF 15.22
- S-008-US4 The block follows no-show corrections — 2 SP · WSJF 15.22
- S-010-US2 No-show report screen for the practice manager — 2 SP · WSJF 15.22
- S-008-US2 Reception sees who is blocked — 3 SP · WSJF 13.04
- S-010-US3 Only the practice manager can read the report — 2 SP · WSJF 13.04
- S-010-US1 Monthly no-show figures per clinic — 3 SP · WSJF 11.59
- S-008-US1 A repeat no-show patient cannot book or reschedule online — 5 SP · WSJF 8.7
- S-POLISH-008 Repeat no-show block: Polish & cross-cutting concerns — 3 SP · WSJF 7.25

## Deferred

- S-007-US1 `dependency`: Waits for family members setup (S-SETUP-007, S-FOUND-007), which is outside the horizon.
- S-007-US2 `dependency`: Waits for family members setup and S-007-US1, which are outside the horizon.
- S-007-US3 `dependency`: Waits for family members setup and S-007-US2, which are outside the horizon.
- S-007-US4 `dependency`: Waits for family members setup and S-007-US1, which are outside the horizon.
- S-SETUP-007 `human_override`: Release 2 (family members). Placed outside the 8-sprint horizon because Release 1 must-haves fill sprints 1-7 and sprint 8 is already over P85 with the no-show block and report.
- S-FOUND-007 `dependency`: Waits for S-SETUP-007, which is outside the horizon.
- S-POLISH-007 `dependency`: Waits for all family-member stories (S-007-US1 to US4), which are outside the horizon.
- S-009-US1 `dependency`: Waits for SMS fallback setup (S-SETUP-009, S-FOUND-009), which is outside the horizon.
- S-009-US2 `dependency`: Waits for SMS fallback setup and S-009-US1, which are outside the horizon.
- S-009-US3 `dependency`: Waits for SMS fallback setup and S-009-US1 and US2, which are outside the horizon.
- S-009-US4 `dependency`: Waits for SMS fallback setup and S-009-US3, which are outside the horizon.
- S-009-US5 `dependency`: Waits for SMS fallback setup (S-SETUP-009, S-FOUND-009), which is outside the horizon.
- S-SETUP-009 `human_override`: Release 2 (SMS fallback). Placed outside the 8-sprint horizon because Release 1 must-haves fill sprints 1-7 and sprint 8 is already over P85 with the no-show block and report.
- S-FOUND-009 `dependency`: Waits for S-SETUP-009, which is outside the horizon.
- S-POLISH-009 `dependency`: Waits for all SMS fallback stories (S-009-US1 to US5), which are outside the horizon.

## Assumptions

- Cold start: fewer than 3 closed sprints with history; capacity = person-hours ÷ 6.0 h/SP × 0.7 (low confidence).
- 10% of capacity reserved for maintenance work.
