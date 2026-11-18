# Sprint plan v2 — gym-full

Solver **OPTIMAL** (0.148s) · as of 2026-11-17

- Sprint 1 (23 Nov–6 Dec) delivers the data foundation (home branch and check-ins, roles, staff accounts, English text) and lets members see the plans and prices. It commits 15 points against 15.7 expected capacity, which is above the 85% level (12.5).
- MVP is late: it is due 31 Dec 2026 but is planned to finish 28 Feb 2027 (sprint 7), with a 50% forecast of 14 Mar and 85% of 28 Mar. The due date is not hard.
- R2 is incomplete: GT-57 and GT-58 are deferred, and the sprints run to sprint 10 (50% forecast 9 May, 85% forecast 23 May). R3 is incomplete: all 7 of its stories are deferred, with a forecast of 6 Jun 2027.
- Risks: capacity confidence is low because there is no velocity history (fewer than 3 closed sprints). Sprints 1 to 6, 8 and 9 are committed above their 85% capacity levels. 20% of capacity is reserved for maintenance.
- Needed from the approver: accept the late MVP date or move the 31 Dec due date, and confirm that deferring GT-57 and GT-58 from R2 and the R3 stories is acceptable. Sprint goals for sprints 7 and 8 are now each one outcome as requested.

Forecast for the whole backlog: sprint 14 (2027-06-06) at P50, sprint 14 (2027-06-06) at P85.

## gym-full Sprint 1 (2026-11-23 → 2026-12-06)

Goal: Members can see the gym's monthly, quarterly and yearly plans with their prices.

15 SP committed · capacity P85 12.5 / P50 15.7 · 3.9 SP reserved for maintenance · 28.0 person-days

- GT-11 Home branch and check-in records are stored — 3 SP · MVP · priority #1
- GT-12 Every screen and message is in English, kept in one place — 2 SP · MVP · priority #2
- GT-13 Each user has one role and only that role's functions — 3 SP · MVP · priority #3
- GT-14 Owner creates and deactivates staff and manager accounts — 5 SP · MVP · priority #4
- GT-18 Member sees the plans and prices — 2 SP · MVP · priority #8

## gym-full Sprint 2 (2026-12-07 → 2026-12-20)

Goal: Members can sign in with their phone number and a WhatsApp code and see their plan and membership status.

17 SP committed · capacity P85 14.1 / P50 17.6 · 4.4 SP reserved for maintenance · 31.5 person-days

- GT-15 Staff, managers and owner sign in with username and password — 3 SP · MVP · priority #5
- GT-16 Messages go by WhatsApp only, from the Kothrud number — 3 SP · MVP · priority #6
- GT-17 Member signs in with phone number and WhatsApp code — 8 SP · MVP · priority #7
- GT-26 Member sees plan and membership status — 3 SP · MVP · priority #16

## gym-full Sprint 3 (2026-12-21 → 2027-01-03)

Goal: New members can sign up on their phone with a confirmed phone number, and each member sees their own QR code.

15 SP committed · capacity P85 12.5 / P50 15.7 · 3.9 SP reserved for maintenance · 28.0 person-days

- GT-19 Sign-up phone number is confirmed with a WhatsApp code — 5 SP · MVP · priority #9
- GT-20 New member signs up with the required details — 5 SP · MVP · priority #10
- GT-21 Registered phone number does not create a second member — 2 SP · MVP · priority #11
- GT-28 Member sees their QR code — 3 SP · MVP · priority #18

## gym-full Sprint 4 (2027-01-04 → 2027-01-17)

Goal: Members can pay online with UPI or card and renew from their own page, with the membership starting only once payment is confirmed.

17 SP committed · capacity P85 14.1 / P50 17.6 · 4.4 SP reserved for maintenance · 31.5 person-days

- GT-22 Membership starts or extends only after payment is confirmed — 3 SP · MVP · priority #12
- GT-23 Member pays online with UPI or card through Razorpay — 3 SP · MVP · priority #13
- GT-25 Member is told a payment is being confirmed — 3 SP · MVP · priority #15
- GT-37 Member pays the renewal online — 3 SP · MVP · priority #27
- GT-38 Member renews from their own page — 5 SP · MVP · priority #28

## gym-full Sprint 5 (2027-01-18 → 2027-01-31)

Goal: Front-desk staff can check in an existing member by phone number, with the existing members loaded from the Excel sheet.

17 SP committed · capacity P85 14.1 / P50 17.6 · 4.4 SP reserved for maintenance · 31.5 person-days

- GT-24 Failed or abandoned payment creates no membership — 5 SP · MVP · priority #14
- GT-29 Load flags missing phone numbers and possible duplicates — 3 SP · MVP · priority #19
- GT-30 Existing members are loaded from the Excel sheet — 3 SP · MVP · priority #20
- GT-31 Loaded members keep their plan, expiry date and home branch — 3 SP · MVP · priority #21
- GT-32 Staff check a member in by phone number — 3 SP · MVP · priority #22

## gym-full Sprint 6 (2027-02-01 → 2027-02-14)

Goal: Front-desk staff can check members in by scanning their QR code and are warned when a membership has expired.

17 SP committed · capacity P85 14.1 / P50 17.6 · 4.4 SP reserved for maintenance · 31.5 person-days

- GT-33 Staff see an expiry warning and decide — 8 SP · MVP · priority #23
- GT-34 Staff check a member in by scanning the QR code — 3 SP · MVP · priority #24
- GT-35 Staff see "member not found" and can retry or sign up the person — 3 SP · MVP · priority #25
- GT-39 Staff and managers list the flagged members of their branch — 3 SP · MVP · priority #29

## gym-full Sprint 7 (2027-02-15 → 2027-02-28)

Goal: Front-desk staff can record a cash payment that extends a member's membership.

16 SP committed · capacity P85 14.1 / P50 17.6 · 4.4 SP reserved for maintenance · 31.5 person-days

- GT-27 Member sees expiry date and days left — 2 SP · MVP · priority #17
- GT-36 Staff record a cash payment — 8 SP · MVP · priority #26
- GT-40 Staff add a missing phone number — 3 SP · MVP · priority #30
- GT-41 Member sees payment history — 3 SP · R2 · priority #31

## gym-full Sprint 8 (2027-03-01 → 2027-03-14)

Goal: Members are asked for WhatsApp consent, including existing members at first sign-in, so that they can receive messages they have accepted.

17 SP committed · capacity P85 14.1 / P50 17.6 · 4.4 SP reserved for maintenance · 31.5 person-days

- GT-42 Member receives a simple receipt — 5 SP · R2 · priority #32
- GT-43 New and trial members are asked about WhatsApp messages — 3 SP · R2 · priority #33
- GT-44 Existing member answers the WhatsApp question at first sign-in — 5 SP · R2 · priority #34
- GT-47 Member gets a second reminder 1 day before expiry — 2 SP · R2 · priority #37
- GT-48 Owner sees all branches together and one by one — 2 SP · R2 · priority #38

## gym-full Sprint 9 (2027-03-15 → 2027-03-28)

Goal: Members get a WhatsApp reminder 7 days before their membership expires, sent only to eligible members.

17 SP committed · capacity P85 14.1 / P50 17.6 · 4.4 SP reserved for maintenance · 31.5 person-days

- GT-45 Reminders go only to eligible members — 5 SP · R2 · priority #35
- GT-46 Member gets a WhatsApp reminder 7 days before expiry — 3 SP · R2 · priority #36
- GT-49 Owner sees active members per branch — 3 SP · R2 · priority #39
- GT-50 Owner sees memberships due to expire this week — 3 SP · R2 · priority #40
- GT-51 Owner sees revenue per month — 3 SP · R2 · priority #41

## gym-full Sprint 10 (2027-03-29 → 2027-04-11)

Goal: New members can start a 7-day free trial and then pay online to become members when it ends.

15 SP committed · capacity P85 14.1 / P50 17.6 · 4.4 SP reserved for maintenance · 31.5 person-days

- GT-52 Branch manager sees only their own branch — 2 SP · R2 · priority #42
- GT-53 Branch manager works within their allowed functions — 3 SP · R2 · priority #43
- GT-54 New member starts a 7-day free trial — 5 SP · R2 · priority #44
- GT-55 Only one free trial per phone number — 2 SP · R2 · priority #45
- GT-56 Trial member sees the trial has ended and can pay — 3 SP · R2 · priority #46

## Release plan

| Release | Deadline | Stories | Points | Planned finish | P50 / P85 forecast | Status |
|---|---|---|---|---|---|---|
| MVP | 2026-12-31 (project) | 30 | 111 | 2027-02-28 (sprint 7) | 2027-03-14 / 2027-03-28 | late |
| R2 | - | 18 | 58 | - | 2027-05-09 / 2027-05-23 | incomplete |
| R3 | - | 7 | 19 | - | 2027-06-06 / 2027-06-06 | incomplete |

## Deferred

- GT-65 `capacity`: Not scheduled because the 10 sprints are full with higher-priority work. Recording whether each reminder was delivered is a later-release item and waits for a future plan.
- GT-57 `capacity`: There is no room left in the 10 sprints after higher-priority work, so changing a plan's price in the app is not included. It belongs to the second release, which is therefore incomplete.
- GT-60 `capacity`: Not scheduled because the sprints are full with higher-priority work. Adding and deactivating plans is a later-release item.
- GT-59 `capacity`: Not scheduled because the sprints are full with higher-priority work. The warning about a second check-in on the same day is a later-release item.
- GT-58 `capacity`: There is no room left in the 10 sprints after higher-priority work, so marking a duplicate record is not included. It belongs to the second release, which is therefore incomplete.
- GT-61 `capacity`: Not scheduled because the sprints are full with higher-priority work. The saved member list on the tablet is part of the offline check-in work in the third release.
- GT-62 `capacity`: Not scheduled because the sprints are full with higher-priority work. Check-in while the internet is down is a later-release item.
- GT-63 `capacity`: Not scheduled because the sprints are full with higher-priority work. Sending offline check-ins once the internet returns is a later-release item.
- GT-64 `capacity`: Not scheduled because the sprints are full with higher-priority work. The message shown when someone is not in the saved list while offline is a later-release item.

## Assumptions

- Cold start: fewer than 3 closed sprints with history; capacity = person-hours ÷ 6.0 h/SP × 0.7 (low confidence).
- 20% of capacity reserved for maintenance work.
- Priority follows the approved roadmap: release (MVP → R2 → R3), then MoSCoW, then the tracker's Rank.
