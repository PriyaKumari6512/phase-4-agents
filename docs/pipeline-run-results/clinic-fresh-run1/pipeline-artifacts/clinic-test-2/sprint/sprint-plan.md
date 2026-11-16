# Sprint plan v1 — clinic-test-2

Solver **INFEASIBLE** (0.525s) · as of 2026-11-16

**No feasible plan.** The solver returned INFEASIBLE, so I have committed nothing and every sprint is empty. Release 1 must-haves (DL-1, hard, 2027-02-22) total about 302 SP. Sprints 1-7 offer about 236 SP at P50 and 189 SP at P85, and even all 8 sprints give only about 271 SP at P50. Those figures use the cold-start capacity estimate, which is low confidence.
**Recommended option: OPT-1, add about 30% capacity (`capacity:x1.3`).** It is the only verified-feasible option. About 307 SP at P50 would fit before the deadline, with 8 stories left unplanned (should-haves such as S-001-US9 and the Release 2 work). Trade-off: it needs roughly 30% more person-days per sprint, e.g. more engineers or hours. Even then sprints would likely run above P85 (about 246 SP across sprints 1-7), so delivery risk stays high. The other levers are to drop deadline scope or must-haves, but the solver offered no verified option for them.
**Need from you:** choose OPT-1 or another way to close the gap of roughly 66 SP at P50. Please also confirm the 1 March go-live date. I will then re-run with the matching `changes` string. I have not applied any relaxation because none was requested.
**For Agent 1:** the capacity gap is large; if the estimates are cautious, splitting or re-checking S-FOUND-007 (13 SP) and the 8 SP stories could help. No unestimated or too-large stories were found. The messaging provider registration (S-007-US6, S-SETUP-007) has long external lead times and should start in sprint 1 whatever is chosen.

Forecast for the whole backlog: sprint 14 (2027-05-30) at P50, sprint 14 (2027-05-30) at P85.

## BrightSmile Booking Sprint 1 (2026-11-16 → 2026-11-29)

Goal: _not written_

0 SP committed · capacity P85 28.4 / P50 35.4 · 3.9 SP reserved for maintenance · 56.25 person-days


## BrightSmile Booking Sprint 2 (2026-11-30 → 2026-12-13)

Goal: _not written_

0 SP committed · capacity P85 28.4 / P50 35.4 · 3.9 SP reserved for maintenance · 56.25 person-days


## BrightSmile Booking Sprint 3 (2026-12-14 → 2026-12-27)

Goal: _not written_

0 SP committed · capacity P85 25.2 / P50 31.5 · 3.5 SP reserved for maintenance · 50.0 person-days


## BrightSmile Booking Sprint 4 (2026-12-28 → 2027-01-10)

Goal: _not written_

0 SP committed · capacity P85 25.2 / P50 31.5 · 3.5 SP reserved for maintenance · 50.0 person-days


## BrightSmile Booking Sprint 5 (2027-01-11 → 2027-01-24)

Goal: _not written_

0 SP committed · capacity P85 28.4 / P50 35.4 · 3.9 SP reserved for maintenance · 56.25 person-days


## BrightSmile Booking Sprint 6 (2027-01-25 → 2027-02-07)

Goal: _not written_

0 SP committed · capacity P85 25.2 / P50 31.5 · 3.5 SP reserved for maintenance · 50.0 person-days


## BrightSmile Booking Sprint 7 (2027-02-08 → 2027-02-21)

Goal: _not written_

0 SP committed · capacity P85 28.4 / P50 35.4 · 3.9 SP reserved for maintenance · 56.25 person-days


## BrightSmile Booking Sprint 8 (2027-02-22 → 2027-03-07)

Goal: _not written_

0 SP committed · capacity P85 28.4 / P50 35.4 · 3.9 SP reserved for maintenance · 56.25 person-days


## Deferred

- S-001-US1 `deadline_infeasible`: Not placed: plan infeasible. Pipeline and rollback; depends on S-FOUND-001.
- S-001-US2 `deadline_infeasible`: Not placed: plan infeasible. Environments and secrets; depends on S-FOUND-001.
- S-001-US3 `deadline_infeasible`: Not placed: plan infeasible. Database baseline and restore; depends on S-FOUND-001.
- S-001-US4 `deadline_infeasible`: Not placed: plan infeasible. Mobile shell; depends on S-FOUND-001.
- S-001-US5 `deadline_infeasible`: Not placed: plan infeasible. English and IST; depends on S-FOUND-001.
- S-001-US6 `deadline_infeasible`: Not placed: plan infeasible. Desktop staff layout; depends on S-FOUND-001.
- S-001-US7 `deadline_infeasible`: Not placed: plan infeasible. Observability and alerts; depends on S-FOUND-001.
- S-001-US8 `deadline_infeasible`: Not placed: plan infeasible. Release 2 switches (must for the Release 1 go-live); depends on S-FOUND-001.
- S-001-US9 `deadline_infeasible`: Should-have (load and scale proof); would be dropped first if capacity stays short. Plan infeasible overall.
- S-001-US10 `deadline_infeasible`: Not placed: plan infeasible. Go-live readiness checklist; naturally belongs in the last sprint before 2027-02-22.
- S-SETUP-001 `deadline_infeasible`: Not placed: no feasible plan exists. Must-have work for Release 1 (about 302 SP) exceeds the capacity to the 2027-02-22 deadline (about 236 SP at P50 over sprints 1-7). This is the first story on the critical path and should start in sprint 1 once the approver picks an option.
- S-FOUND-001 `deadline_infeasible`: Not placed: plan infeasible (capacity vs the DL-1 deadline). Foundation for every other story; first in line once capacity is agreed.
- S-POLISH-001 `deadline_infeasible`: Should-have polish; deferred behind all must-haves because capacity is short.
- S-002-US1 `deadline_infeasible`: Not placed: plan infeasible. Patient phone-code sign-in.
- S-002-US2 `deadline_infeasible`: Not placed: plan infeasible. New patient account.
- S-002-US3 `deadline_infeasible`: Not placed: plan infeasible. Staff sign-in.
- S-002-US4 `deadline_infeasible`: Not placed: plan infeasible. Role-based visibility.
- S-002-US5 `deadline_infeasible`: Not placed: plan infeasible. Staff account management.
- S-002-US6 `deadline_infeasible`: Not placed: plan infeasible. Patient data erasure (privacy must-have).
- S-002-US7 `deadline_infeasible`: Should-have (reception deactivates a patient account); deferred behind all must-haves.
- S-SETUP-002 `deadline_infeasible`: Not placed: plan infeasible (capacity vs deadline). Sign-in setup.
- S-FOUND-002 `deadline_infeasible`: Not placed: plan infeasible. Sign-in foundation; depends on platform foundation.
- S-POLISH-002 `deadline_infeasible`: Not placed: plan infeasible. Must-have polish for sign-in.
- S-003-US1 `deadline_infeasible`: Not placed: plan infeasible. Clinics and dentists as data.
- S-003-US2 `deadline_infeasible`: Not placed: plan infeasible. Treatment types.
- S-003-US3 `deadline_infeasible`: Not placed: plan infeasible. Dentist hours and breaks.
- S-003-US4 `deadline_infeasible`: Not placed: plan infeasible. Free slots; on the critical path to online booking.
- S-003-US5 `deadline_infeasible`: Not placed: plan infeasible. Dentist leave.
- S-003-US6 `deadline_infeasible`: Not placed: plan infeasible. Appointments to move.
- S-SETUP-003 `deadline_infeasible`: Not placed: plan infeasible. Schedule setup.
- S-FOUND-003 `deadline_infeasible`: Not placed: plan infeasible. Schedule foundation; on the critical path to booking.
- S-POLISH-003 `deadline_infeasible`: Should-have polish; deferred behind all must-haves.
- S-004-US1 `deadline_infeasible`: Not placed: plan infeasible. Online booking; main business goal.
- S-004-US2 `deadline_infeasible`: Not placed: plan infeasible. No double booking.
- S-004-US3 `deadline_infeasible`: Not placed: plan infeasible. SMS or WhatsApp choice.
- S-004-US4 `deadline_infeasible`: Not placed: plan infeasible. Proof that concurrent bookings never overlap.
- S-004-US5 `deadline_infeasible`: Should-have (booking speed on phone networks); deferred behind must-haves.
- S-SETUP-004 `deadline_infeasible`: Not placed: plan infeasible. Booking setup.
- S-FOUND-004 `deadline_infeasible`: Not placed: plan infeasible. Booking foundation.
- S-POLISH-004 `deadline_infeasible`: Should-have polish; deferred behind must-haves.
- S-005-US1 `deadline_infeasible`: Not placed: plan infeasible. Appointment list.
- S-005-US2 `deadline_infeasible`: Not placed: plan infeasible. Status history.
- S-005-US3 `deadline_infeasible`: Not placed: plan infeasible. Patient cancel.
- S-005-US4 `deadline_infeasible`: Not placed: plan infeasible. Patient reschedule.
- S-005-US5 `deadline_infeasible`: Should-have (open appointment from message link); deferred behind must-haves.
- S-SETUP-005 `deadline_infeasible`: Not placed: plan infeasible. Manage-appointments setup.
- S-FOUND-005 `deadline_infeasible`: Not placed: plan infeasible. Status history foundation.
- S-POLISH-005 `deadline_infeasible`: Should-have polish; deferred behind must-haves.
- S-006-US1 `deadline_infeasible`: Not placed: plan infeasible. Reception day view.
- S-006-US2 `deadline_infeasible`: Not placed: plan infeasible. Mark arrived.
- S-006-US3 `deadline_infeasible`: Not placed: plan infeasible. No-show and undo.
- S-006-US4 `deadline_infeasible`: Not placed: plan infeasible. Find or create patient.
- S-006-US5 `deadline_infeasible`: Not placed: plan infeasible. Reception booking.
- S-006-US6 `deadline_infeasible`: Not placed: plan infeasible. Reception reschedule and cancel.
- S-006-US7 `deadline_infeasible`: Not placed: plan infeasible. Dentist day.
- S-SETUP-006 `deadline_infeasible`: Not placed: plan infeasible. Reception setup.
- S-FOUND-006 `deadline_infeasible`: Not placed: plan infeasible. Reception foundation.
- S-POLISH-006 `deadline_infeasible`: Not placed: plan infeasible. Must-have polish for reception.
- S-007-US1 `deadline_infeasible`: Not placed: plan infeasible. Confirmations.
- S-007-US2 `deadline_infeasible`: Not placed: plan infeasible. 24-hour reminders; core to the no-show goal.
- S-007-US3 `deadline_infeasible`: Not placed: plan infeasible. No wrong reminders.
- S-007-US4 `deadline_infeasible`: Not placed: plan infeasible. STOP handling.
- S-007-US5 `deadline_infeasible`: Not placed: plan infeasible. On-time, compliant reminders.
- S-007-US6 `deadline_infeasible`: Not placed: plan infeasible. Provider accounts and templates; long external lead time.
- S-007-US7 `deadline_infeasible`: Not placed: plan infeasible. SMS sign-in code.
- S-007-US8 `deadline_infeasible`: Release 2 should-have (WhatsApp to SMS fallback); due 2027-03-19, after the Release 1 backlog.
- S-007-US9 `deadline_infeasible`: Release 2 should-have (reminders-failed list); due 2027-03-19, after the Release 1 backlog.
- S-SETUP-007 `deadline_infeasible`: Not placed: plan infeasible. Messaging setup; provider registration has long external lead times and should start early.
- S-FOUND-007 `deadline_infeasible`: Not placed: plan infeasible. Messaging foundation (13 SP, the largest story).
- S-POLISH-007 `deadline_infeasible`: Not placed: plan infeasible. Must-have polish for messaging; last on the critical path.
- S-008-US1 `deadline_infeasible`: Release 2 should-have (family members); behind all Release 1 must-haves.
- S-008-US2 `deadline_infeasible`: Release 2 should-have (family members); behind all Release 1 must-haves.
- S-008-US3 `deadline_infeasible`: Release 2 should-have (family members); behind all Release 1 must-haves.
- S-008-US4 `deadline_infeasible`: Release 2 should-have (family members); behind all Release 1 must-haves.
- S-SETUP-008 `deadline_infeasible`: Release 2 should-have (family members); behind all Release 1 must-haves.
- S-FOUND-008 `deadline_infeasible`: Release 2 should-have (family members); behind all Release 1 must-haves.
- S-POLISH-008 `deadline_infeasible`: Release 2 should-have polish; behind all Release 1 must-haves.
- S-009-US1 `deadline_infeasible`: Release 2 should-have (no-show block); behind all Release 1 must-haves.
- S-009-US2 `deadline_infeasible`: Release 2 should-have (lift a block); behind all Release 1 must-haves.
- S-009-US3 `deadline_infeasible`: Release 2 should-have (no-show report); behind all Release 1 must-haves.
- S-SETUP-009 `deadline_infeasible`: Release 2 should-have (no-show block and report); behind all Release 1 must-haves.
- S-FOUND-009 `deadline_infeasible`: Release 2 should-have (no-show block and report); behind all Release 1 must-haves.
- S-POLISH-009 `deadline_infeasible`: Release 2 should-have polish; behind all Release 1 must-haves.

## Options (each verified feasible by the solver)

- **OPT-1** Add 30% capacity — needs about 30% more person-days per sprint; 8 stories left unplanned (`capacity:x1.3`)

## Assumptions

- Cold start: fewer than 3 closed sprints with history; capacity = person-hours ÷ 6.0 h/SP × 0.7 (low confidence).
- 10% of capacity reserved for maintenance work.
