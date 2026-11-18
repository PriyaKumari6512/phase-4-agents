# PRD: gym-demo   (version 1.0)

## 1. Overview

**Who has the problem.** FitZone is a chain of 3 gyms in Pune (Kothrud and Baner are named) with about 1,200 members today and about 3,000 expected within a year. Members sign up on paper and pay each month in cash or UPI. Staff track expiry dates in an Excel sheet.

**The problem.** Expired members often keep coming in without anyone noticing, and renewals get missed (REQ-002 is inferred from this; the client did not state it as a goal).

**The vision.** One simple website, usable on a phone, that replaces the paper form and the Excel sheet (REQ-001):
- New people sign up and pay online, or start a 7-day free trial without paying.
- Members see their plan, expiry date and payment history, and renew online.
- Front-desk staff check a member in by phone number or QR code and see a clear warning if the membership has expired.
- WhatsApp reminders go out 7 days and 1 day before expiry.
- The owner and the branch managers see active members, renewals due and revenue on a dashboard.

It is a website, not a native app. It is in English only. Online payments go through the client's existing Razorpay account. The existing members are loaded from the client's Excel file.

**Launch.** The client says 1 January is firm. The year is assumed to be 2027 (SA-001; Q-004 is open). Sign-up, online payment and check-in must be live on day one. The dashboard may follow a few weeks later. The scope estimate says full scope does not fit before launch, so the first release is planned as the minimum set (SA-013). Release priorities are set in the backlog, not here.

## 2. Goals and success metrics

| Goal | REQs | Metric | Target |
|---|---|---|---|
| Replace paper sign-up and the Excel expiry sheet with the web app | REQ-001 | Number of branches where staff no longer use the Excel sheet or paper sign-up forms | 3 of 3 branches within 4 weeks after launch (PD-001) |
| Replace paper sign-up and the Excel expiry sheet (same goal) | REQ-001 | Share of check-ins recorded in the app (not on paper or in Excel) | 100% of check-ins from the first day at each branch (PD-001) |
| Stop expired members from entering unnoticed | REQ-002 | Share of check-ins of expired members that show the expiry warning | 100% (PD-002) |
| Reduce missed renewals | REQ-002 | Share of memberships renewed on or before the expiry date | TBD: the current rate is not known. See Questions to raise, item 2. Measured from launch with the app's own data. |
| Reduce missed renewals (same goal) | REQ-002 | Share of due WhatsApp reminders (7 days and 1 day) sent on the due day | At least 95% (PD-002) |

The two `goal` REQs are REQ-001 and REQ-002. They are goals, not scoped features. REQ-002 is inferred.

## 3. Non-goals

From "Out of scope" in `scope.md`. The app does not do these:

- Refunds of online payments (the client does them at the front desk) (REQ-027).
- A native mobile app on Play Store or App Store (REQ-038).
- GST tax invoices. A simple receipt is planned (Q-013 is open).
- Pausing ("freezing") a membership, or switching plan part-way.
- A trainer role, class or personal-trainer booking, diet or workout plans.
- Shop or point-of-sale, and links to accounting software.
- Control of doors or turnstiles. The expiry warning is only a warning.
- Marathi or Hindi screens.
- Marketing messages, messages after expiry, and sign-up or payment confirmation messages on WhatsApp.
- Export of dashboard figures to Excel or PDF.
- Typing in paper records, and automatic merging of duplicate members.
- Automatic recurring (auto-debit) payments.
- An uptime guarantee (SLA), post-launch support, formal accessibility certification, and load testing.

## 4. Personas

| P | Persona | Role | Main need |
|---|---|---|---|
| P-01 | Member (including a new member and a free-trial member) | Signs up, pays, renews, checks in with a phone | Join or try the gym without paper, see when the membership ends, renew in a few taps, and get reminded before it ends. Some members have low digital skills and older phones (A-027). |
| P-02 | Front-desk staff | Works at the front desk of one branch on the Android tablet | Check members in quickly and know at once if a membership has expired. Fix member details such as a missing phone number. |
| P-03 | Branch manager | Runs one branch | See the figures of their own branch only (active members, renewals due, revenue). |
| P-04 | Owner | Owns FitZone and sees all 3 branches | See all branches, manage plans, prices and staff accounts, and be sure that renewals are not missed. |

No trainer role is planned (A-026).

## 5. Functional requirements

| FR | Requirement | REQs | MOD |
|---|---|---|---|
| FR-001 | The system holds the 3 FitZone branches. Every member has a home branch. Every sign-up, payment and check-in records the branch it happened at. A membership is valid at all 3 branches (SA-003; Q-006 is open). | REQ-022 | MOD-01 |
| FR-002 | A member signs in with their phone number and a one-time code sent by WhatsApp (SA-006; Q-011 is open). The code is valid for 10 minutes and allows 5 wrong tries, after which the member waits 15 minutes before trying again (PD-008). If the phone number is not registered, the system says so and offers sign-up or free trial. | REQ-024 | MOD-01 |
| FR-003 | Front-desk staff, branch managers and the owner sign in with a username and password (SA-006). | REQ-024 | MOD-01 |
| FR-004 | After sign-in each person sees only what their role needs. A member sees only their own membership. Front-desk staff see check-in, member look-up and member data fixes. A branch manager sees the dashboard and the member list of their own branch. The owner sees everything. | REQ-024 | MOD-01 |
| FR-005 | A branch manager sees only the data of their own branch (members, check-ins, payments, dashboard figures). The system does not show them any other branch's data. | REQ-035 | MOD-01 |
| FR-006 | Only the owner can see the data of all branches together, and the figures of each branch separately. | REQ-036 | MOD-01 |
| FR-007 | The owner creates, deactivates and assigns to a branch the accounts of front-desk staff and branch managers (A-013, A-026). A deactivated person cannot sign in. | REQ-024 | MOD-01 |
| FR-008 | A new member signs up online by giving their name and phone number and choosing a home branch (PD-007). The system checks the phone number with a one-time code before the account is created. | REQ-003 | MOD-02 |
| FR-009 | If the phone number given at sign-up or free trial already has an account, the system does not create a second account. It says the number is already registered and offers sign-in instead (PD-003, PD-015). | REQ-003 | MOD-02 |
| FR-010 | The system shows the monthly, quarterly and yearly plans with duration and price, and the new member must choose one before paying. A monthly plan lasts 1 calendar month, a quarterly plan 3 and a yearly plan 12. The expiry date is the last day the membership is valid (PD-006). | REQ-004 | MOD-02 |
| FR-011 | The owner can edit plan names, durations and prices on an admin screen (SA-004; Q-008 is open). A price change applies to future purchases only and does not change past payments. | REQ-004 | MOD-02 |
| FR-012 | A new member pays for the chosen plan online with UPI or a card through the client's Razorpay account. The membership starts only when Razorpay confirms the payment. The start date is the payment date. | REQ-005, REQ-026 | MOD-03 |
| FR-013 | If the payment is declined, abandoned, or not confirmed, no membership starts and no payment is shown as paid. The member sees what happened in plain words, keeps the plan they chose, and can try again or pick another method. If Razorpay has not yet confirmed, the screen says "We are checking your payment" and updates when confirmation arrives (PD-004). | REQ-005, REQ-026 | MOD-03 |
| FR-014 | Each successful online payment is stored with date, amount, plan, method (UPI or card), branch and the Razorpay reference. | REQ-005, REQ-026 | MOD-03 |
| FR-015 | Front-desk staff can record a cash or UPI payment taken at the desk for a member and a plan. It updates the expiry date by the same rules as an online renewal, and shows in the payment history marked "at the desk" (SA-002; Q-005 is open). A wrongly entered desk payment is cancelled by the branch manager or the owner with a reason, and the expiry date goes back to what it was (PD-016). No REQ covers this yet; see Questions to raise. | REQ-005, REQ-008 | MOD-03 |
| FR-016 | A signed-in member sees their current plan (name and duration) and whether it is active, expired or a free trial. | REQ-006 | MOD-04 |
| FR-017 | A signed-in member sees their membership expiry date and the number of days left, or that it has expired. | REQ-007 | MOD-04 |
| FR-018 | A signed-in member sees their payment history, newest first: date, amount, plan, method (online or at the desk) and a simple receipt for each payment, with no GST invoice (SA-007; Q-013 is open). The receipt shows member name, plan, amount, date and payment reference (PD-012). | REQ-008 | MOD-04 |
| FR-019 | A signed-in member with an active membership can renew online, paying through Razorpay (FR-012 and FR-013 apply). The new period is added after the current expiry date (SA-005; Q-009 is open). | REQ-009 | MOD-05 |
| FR-020 | A signed-in member whose membership has expired can also renew online. The new period starts on the payment date (A-015). | REQ-009 | MOD-05 |
| FR-021 | A new person can start a 7-day free trial without paying. They give name, phone number and home branch, and verify the number with a one-time code. The trial starts at once and lasts 7 days counting the start day (PD-007, PD-006). | REQ-028, REQ-030 | MOD-06 |
| FR-022 | The system allows one free trial per phone number. A phone number that already had a trial, or that is in the loaded member list, cannot start one. The person is told why and is offered sign-up with a plan (A-022). | REQ-029 | MOD-06 |
| FR-023 | A free-trial member gets an account and a QR code, and can check in at any branch during the 7 days. After the 7 days the system shows them as expired and they can buy a plan online (SA-010; Q-017 is open). | REQ-028 | MOD-06 |
| FR-024 | A signed-in member sees a personal QR code on their phone for check-in. | REQ-011 | MOD-07 |
| FR-025 | Front-desk staff check a member in by typing the member's phone number. The system shows the member's name, plan, status and expiry date. | REQ-010 | MOD-07 |
| FR-026 | Front-desk staff check a member in by scanning the QR code on the member's own phone with the front-desk tablet camera (A-004). | REQ-011, REQ-031 | MOD-07 |
| FR-027 | Front-desk staff can also find a member by name, which is the way to check in a member who has no phone number on record (SA-009; Q-016 is open). | REQ-010, REQ-033 | MOD-07 |
| FR-028 | When the member's membership has expired, the system shows a clear warning with the expiry date. The warning is not a door lock: staff decide whether to let the member in, and the check-in is recorded as "entered while expired" if they do (A-003, PD-005). | REQ-012 | MOD-07 |
| FR-029 | If no member matches the phone number or QR code, the system says "member not found", suggests checking the number or searching by name, and offers to send the person to the free-trial or sign-up page. | REQ-010, REQ-011 | MOD-07 |
| FR-030 | Every check-in is stored with the member, the branch, the date and time, the staff user, and the result (valid, trial, expired, entered while expired). A member whose home branch is another branch can check in at this branch (SA-003, A-026). | REQ-010, REQ-011, REQ-022 | MOD-07 |
| FR-031 | If the gym's internet is down, the check-in screen on the tablet keeps working for up to 15 minutes using a saved copy of the member list and expiry dates. It shows a banner saying it is offline and when the list was last updated. Check-ins made offline are stored on the tablet and sent when the internet is back. A member who joined or renewed just before or during the outage may show as expired or not found (SA-011, PD-013; Q-018 is open). Sign-up and payment need internet. | REQ-032 | MOD-08 |
| FR-032 | Before launch, the project team loads the existing members from the client's Excel file as it is: name, phone number, branch, plan and expiry date for each row. Rows with no phone number and duplicate rows are loaded, not rejected or merged (A-019, SA-016). Paper records are not typed in. | REQ-023 | MOD-09 |
| FR-033 | After the load, the system gives a report with the number of rows loaded, rows with no phone number, and rows sharing a phone number. Staff see a "needs attention" list of those members, per branch (PD-009). | REQ-033 | MOD-09 |
| FR-034 | Front-desk staff and branch managers can edit a member's name, phone number and home branch for the members of their own branch, and the owner for all. A phone number already used by another member is refused with a message naming that member (PD-009, PD-015). A member who changes number gets the change made by staff. | REQ-034 | MOD-09 |
| FR-035 | Staff can remove a duplicate member. The duplicate is archived, not erased: it disappears from search, check-in and the counts, and its payments and check-ins stay in the records (PD-009). The system never merges members by itself. | REQ-034 | MOD-09 |
| FR-036 | The system sends each member a WhatsApp reminder 7 days before their expiry date. It says the name, the expiry date and how to renew (PD-010). | REQ-016 | MOD-10 |
| FR-037 | The system sends each member a WhatsApp reminder 1 day before their expiry date. | REQ-017 | MOD-10 |
| FR-038 | A reminder is sent at 09:00 India time on its due day. It is not sent if the member has already renewed (the expiry date has moved), has no phone number, has stopped reminders (FR-041), or is archived. A failed send is tried again up to 3 times during that day and then marked failed on the member's record (PD-010). | REQ-016, REQ-017 | MOD-10 |
| FR-039 | Reminders go by WhatsApp only, never by SMS. They are sent from the client's WhatsApp Business number, the same number for all 3 branches (SA-012; Q-019 is open). | REQ-018, REQ-025 | MOD-10 |
| FR-040 | A free-trial member gets one WhatsApp reminder 1 day before the trial ends, inviting them to buy a plan (SA-010; Q-017 is open). | REQ-028, REQ-018 | MOD-06, MOD-10 |
| FR-041 | A member can stop WhatsApp reminders by asking staff, who switch them off in the member's record, or by replying to the message as WhatsApp's rules require. Staff can see which members have stopped reminders and can switch them on again (A-028). | REQ-018 | MOD-10 |
| FR-042 | The dashboard shows the number of active members per branch (PD-011). | REQ-013 | MOD-11 |
| FR-043 | The dashboard shows the renewals due this week, with the number per branch and the list of members with their expiry date (PD-011). | REQ-014 | MOD-11 |
| FR-044 | The dashboard shows revenue per month, per branch, from successful online payments and desk payments (PD-011, SA-002). The figures are on screen only, with no export. The owner sees all branches; a branch manager sees their own. | REQ-015 | MOD-11 |

## 6. User flows and screens

### Flow: A new member signs up and pays   P-01 · FR-008, FR-009, FR-010, FR-012, FR-013, FR-014, FR-024

1. The person opens the FitZone website on their phone and chooses "Join".
2. They enter name and phone number, and choose a home branch.
3. The system sends a one-time code by WhatsApp. The person enters it.
   - *Wrong or expired code:* the system says so and lets them retry or ask for a new code. After 5 wrong tries they wait 15 minutes (FR-002).
   - *Number already registered:* the system says the number already has an account and offers sign-in. No second account is made (FR-009).
4. The system shows the monthly, quarterly and yearly plans with price. The person picks one.
5. The system shows a summary (plan, price, expiry date it would give) and the person chooses to pay.
6. The person pays by UPI or card on the Razorpay payment step.
   - *Payment declined or abandoned:* no membership starts. The system says what happened, keeps the chosen plan, and offers "try again" or another method (FR-013).
   - *Payment not yet confirmed:* the system says it is checking and updates the page when Razorpay confirms.
7. On success the system shows the plan, the expiry date and the personal QR code, and the membership is active.

Screens: Join (name, phone, branch); Enter one-time code; Plan choice; Order summary; Razorpay payment step; Payment result (success, failed, checking); Membership home with QR code.

### Flow: A new person starts the free trial   P-01 · FR-021, FR-022, FR-023, FR-009, FR-040

1. The person opens the website and chooses "Try 7 days free".
2. They enter name, phone number and home branch, and verify the number with a one-time code.
3. The system checks the number.
   - *Number already had a trial, or is in the loaded member list:* the system says a trial is not available and offers sign-up with a plan (FR-022).
   - *Number already has an account:* offers sign-in (FR-009).
4. The trial starts at once without payment. The system shows the trial end date and the personal QR code.
5. One day before the trial ends the person gets a WhatsApp reminder to buy a plan. After the trial the person shows as expired at check-in and can buy a plan online (FR-023).

Screens: Free trial start (name, phone, branch); Enter one-time code; Trial not available; Trial started (end date and QR code); Membership home (trial status, "buy a plan").

### Flow: A member signs in and sees their membership   P-01 · FR-002, FR-016, FR-017, FR-018, FR-024

1. The member opens the website and chooses "Sign in".
2. They enter their phone number. The system sends a one-time code by WhatsApp. They enter it.
   - *Wrong or expired code:* retry or new code (limits in FR-002).
   - *Number not registered:* the system offers Join or Free trial. A loaded member whose number is missing or wrong at FitZone is told to ask at the front desk, where staff fix it (FR-034).
   - *WhatsApp code does not arrive:* the member can ask for a new code, or ask at the front desk.
3. The member sees the home page: current plan, status, expiry date with days left, the QR code, and a "Renew" button.
4. The member opens payment history and sees each payment with its receipt.

Screens: Sign in (phone); Enter one-time code; Membership home (plan, expiry, QR code, renew); Payment history with receipt view.

### Flow: A member renews online   P-01 · FR-019, FR-020, FR-012, FR-013, FR-014

1. The member signs in (flow above) and chooses "Renew", either before or after the expiry date.
2. The system shows the plans and the new expiry date for each one: after the current expiry date if the membership is still active, from today if it has expired.
3. The member picks a plan and pays by UPI or card on the Razorpay payment step.
   - *Payment declined, abandoned or not confirmed:* the existing expiry date does not change; the member sees what happened and can try again (FR-013).
4. On success the system shows the new expiry date and adds the payment to the history.

Screens: Membership home; Renew plan choice (with new expiry date); Razorpay payment step; Payment result.

### Flow: A member gets a reminder and renews   P-01 · FR-036, FR-037, FR-038, FR-039, FR-041, FR-019

1. Seven days before expiry the system sends a WhatsApp reminder at 09:00 with the expiry date and how to renew. One day before expiry it sends a second reminder.
2. The member follows the link and renews (renewal flow above).
   - *Member already renewed:* no reminder is sent (FR-038).
   - *Member has no phone number or has stopped reminders:* no reminder is sent. Staff can add a number or switch reminders on at the desk.
   - *WhatsApp send fails:* the system tries again up to 3 times that day, then marks it failed on the member's record.
3. A member who wants no more reminders replies to the message or asks staff to switch them off (FR-041).

Screens: The WhatsApp message (text only, no screen of ours); Sign in; Renew (as in the renewal flow); Member record, reminder status (staff).

### Flow: Front-desk staff check a member in   P-02 · FR-003, FR-025, FR-026, FR-027, FR-028, FR-029, FR-030, FR-031

1. Staff sign in on the front-desk tablet with username and password.
2. The member arrives. Staff either scan the QR code on the member's phone, type the member's phone number, or search by name.
3. The system shows the member's name, plan, status and expiry date, and records the check-in with the branch and time.
   - *Membership active or trial:* a clear "valid" result.
   - *Membership expired:* a warning with the expiry date. Staff choose to record entry anyway (marked "entered while expired") or not. Staff may take the member to renew or pay at the desk (FR-028).
   - *Member not found:* the system says "member not found", suggests checking the number or searching by name, and offers free trial or sign-up (FR-029).
   - *Member from another branch:* the check-in is accepted and records this branch (FR-030).
   - *Internet is down:* the screen shows an "offline" banner with the time the saved list was last updated. The check goes against the saved list and is sent later. A very recent joiner or renewal may show as expired or not found; staff handle that in person (FR-031).
4. The next member is checked in.

Screens: Staff sign in; Check-in (QR scan, phone number, name search, offline banner); Member result (valid, trial, expired warning, not found); Member search results.

### Flow: Front-desk staff record a payment taken at the desk   P-02 · FR-015, FR-018   (depends on Q-005; SA-002)

1. Staff find the member (as in check-in) and choose "Record payment".
2. Staff pick the plan and whether it was cash or UPI. The system shows the amount from the plan price and the resulting expiry date.
3. Staff confirm. The system saves the payment, updates the expiry date and shows it in the member's payment history as "at the desk".
   - *Member not found:* as in check-in; staff add the member first (flow below) or send the person to online sign-up.
   - *Wrong entry:* staff ask the branch manager or the owner, who cancel the payment with a reason. The expiry date goes back to what it was (PD-016).
4. Refunds are not done here: they stay at the front desk, outside the app.

Screens: Member result (with "Record payment"); Record payment (plan, cash or UPI, resulting expiry); Payment saved; Cancel payment (manager or owner).

### Flow: Staff fix imported member records   P-02, P-03 · FR-032, FR-033, FR-034, FR-035, FR-027

1. Before launch the project team loads the Excel file. The system shows the load report: rows loaded, rows without a phone number, rows sharing a phone number.
2. After launch, staff or the branch manager open the "needs attention" list for their branch.
3. For a member with no phone number, staff ask the member at the desk and add the number.
   - *The number is already used by another member:* the system refuses and names that member; staff decide whether it is a duplicate (FR-034).
4. For a duplicate, staff open the two entries and remove the duplicate. It is archived and its history stays (FR-035).
5. Until a number is added the member is found by name at check-in and gets no reminders.

Screens: Load report; Needs attention list (per branch); Member record (edit name, phone, branch; reminders on or off); Remove duplicate confirmation.

### Flow: The owner and branch managers view the dashboard   P-03, P-04 · FR-005, FR-006, FR-042, FR-043, FR-044   (second release)

1. The person signs in with username and password.
2. The owner sees active members, renewals due this week and revenue per month for each branch and can pick a single branch. A branch manager sees the same figures for their own branch only; other branches are not offered.
3. The person opens "renewals due this week" to see the list of members with expiry dates.
   - *No data yet for a month or a branch:* the system shows zero, not an error.
4. The figures are on screen only. There is no export.

Screens: Sign in; Dashboard (active members, renewals due, revenue per month; branch selector for the owner); Renewals due list.

### Flow: The owner manages plans, prices and staff accounts   P-04 · FR-007, FR-011

1. The owner signs in and opens "Plans".
2. The owner edits a plan's name, duration or price. A price change applies to future purchases only.
3. The owner opens "Staff". The owner adds a front-desk staff member or a branch manager, picks the branch and sets a username and a first password.
4. To remove access, the owner deactivates the account. That person can no longer sign in.
   - *Username already taken:* the system asks for another one.

Screens: Sign in; Plans (list and edit); Staff accounts (list, add, deactivate).

## 7. Non-functional requirements

| NFR | Category | Requirement | Target | REQs |
|---|---|---|---|---|
| NFR-001 | compatibility | The app is a mobile-friendly website for members. It needs no install and no native app. | Every member screen can be used on a phone without sideways scrolling, in current Chrome and Safari on Android phones and iPhones (A-018). The client gave no device or browser targets, so these are assumed. | REQ-019 |
| NFR-002 | compatibility | Check-in runs in the browser on one Android tablet at each front desk. The client provides the tablet with a working camera. Staff and managers can also use a desktop browser. | 1 tablet per front desk, 3 in total (DEP-005, SA-014). | REQ-031 |
| NFR-003 | usability | Inferred from the members' low digital skills (A-027): sign-up, payment and renewal each need only a few screens, with plain English and large buttons. | Sign-up to payment in no more than 5 screens; renewal in no more than 3 screens after sign-in (PD-014). | REQ-019, REQ-003, REQ-009 |
| NFR-004 | accessibility | Inferred (A-027): readable text size and contrast, and a label on every field. No formal accessibility standard is required and none is certified. | Good practice only; no WCAG level and no screen-reader testing (A-027). | REQ-019, REQ-037 |
| NFR-005 | scalability | The app supports about 1,200 members now and 3,000 within a year without slowing down. | 3,000 members and their check-ins, payments and reminders; no special load testing (A-008). | REQ-020 |
| NFR-006 | performance | Inferred (A-008): check-in must be fast during the early-morning and evening rush, and pages must load on a mobile connection. | Check-in result shown within 2 seconds for 95% of check-ins while online. Member pages load within 3 seconds on a normal 4G connection (PD-012). | REQ-020, REQ-010 |
| NFR-007 | localisation | The app is in English only for now. | All screens and WhatsApp messages in English; no Marathi or Hindi. | REQ-037 |
| NFR-008 | operations | Launch is on 1 January and the date is firm because New Year is when most people join. | Live on 1 January 2027 (SA-001; Q-004 is open). | REQ-021 |
| NFR-009 | operations | Online sign-up must be live on launch day. | Live on launch day; this is part of the first release. | REQ-039 |
| NFR-010 | operations | Online payment must be live on launch day. | Live on launch day, with the client's live Razorpay account (DEP-001). | REQ-040 |
| NFR-011 | operations | Front-desk check-in must be live on launch day. | Live on launch day at all 3 branches, with the existing members loaded (MOD-09). | REQ-041 |
| NFR-012 | operations | The owner dashboard (FR-042 to FR-044) may be delivered a few weeks after launch. | A few weeks after launch; the date is set in the backlog (SA-013; Q-020 is open). | REQ-042 |
| NFR-013 | availability | Check-in keeps working when the gym's internet is down, "if possible" (client's words). The client asked for 10-15 minutes. | Check-in works for up to 15 minutes without internet (FR-031, PD-013). Longer outages are not covered. Q-018 is open. | REQ-032 |
| NFR-014 | security | A free trial is given only once per phone number, so the phone number is verified with a one-time code. | 0 trials started on an unverified number or on a number that already had a trial. | REQ-029 |
| NFR-015 | security | A branch manager sees only their own branch's data; only the owner sees all branches. | 0 screens or lists that show a manager data from another branch. Tested with a manager account of each branch. | REQ-035, REQ-036 |
| NFR-016 | security | Inferred from the use of Razorpay (REQ-026) and from A-023: the app never sees or stores card or UPI details. Payment details are entered on Razorpay's payment step. Sign-in codes and staff passwords are protected (code limits in PD-008). | Card details stored in the app: none. | REQ-026, REQ-024 |
| NFR-017 | privacy | Inferred (A-007): the app stores member name, phone number, plan, payments and check-in history, and no health data. It follows normal Indian data-protection practice (DPDP Act). | No health data stored. A member's data can be deleted when the owner asks (A-007). The legal check of the DPDP Act is not done by this PRD. | REQ-003, REQ-008, REQ-024 |
| NFR-018 | availability | Inferred (A-009): the app is available during normal business and gym hours. No formal uptime guarantee. | No SLA (A-009). Support after launch is agreed separately. | REQ-001 |

## 8. Assumptions, product decisions and open questions

### Product decisions

| PD | Decision | Why | Used by |
|---|---|---|---|
| PD-001 | Targets for the goal "replace paper and Excel": all 3 branches have stopped using the Excel sheet and paper forms within 4 weeks after launch, and 100% of check-ins are in the app from the first day. | The client gave no target; the goal is "replace paper and Excel", so the measure is that they are no longer used. | Goals (section 2) |
| PD-002 | Targets for the goal "stop expired members and reduce missed renewals": the expiry warning shows on 100% of check-ins of expired members, and at least 95% of due reminders are sent on their due day. | The client gave no target. The warning is a core function, so anything below 100% is a defect. 95% leaves room for WhatsApp delivery problems. | Goals (section 2), FR-028, FR-038 |
| PD-003 | If a phone number already has an account at sign-up or free trial, no new account is made. The system says the number is already registered and offers sign-in. | Phone number is the member's identity (sign-in, check-in, one trial per phone). Two accounts on one number would break all three. | FR-009, FR-022 |
| PD-004 | A declined, abandoned or unconfirmed payment starts no membership and changes no expiry date. The member sees a plain message and keeps the chosen plan. If Razorpay has not confirmed, the screen says it is checking and updates when confirmed. | Follows A-023. The client did not say what the member sees on failure. | FR-013, flows: sign-up, renewal |
| PD-005 | At check-in, an expired member gets a warning with the expiry date. Staff may still record entry; it is stored as "entered while expired". Not found, valid, trial and expired are the four results. | A-003 says the warning only warns. Recording the override lets the owner see how often expired members get in (goal REQ-002). | FR-028, FR-030 |
| PD-006 | A monthly plan lasts 1 calendar month, a quarterly plan 3 and a yearly plan 12. The expiry date is the last day the membership is valid, so a member is valid on the expiry date and shows as expired the day after. A free trial of 7 days counts the start day as day 1. | The client gave no rule for how durations and expiry days are counted. | FR-010, FR-021, FR-028 |
| PD-007 | Sign-up and free trial ask for name, phone number and home branch only. | The branch is needed for the dashboard (REQ-022). No other fields were requested, and fewer fields suit members with low digital skills (A-027). | FR-008, FR-021 |
| PD-008 | A one-time sign-in code is valid for 10 minutes. After 5 wrong tries the member waits 15 minutes. | The client did not say. These limits protect accounts without annoying members. | FR-002, NFR-016 |
| PD-009 | Front-desk staff and branch managers can edit the name, phone number and home branch of members of their own branch; the owner for all. A phone number already used by another member is refused. A duplicate is archived, not erased. The system lists members needing attention (no phone number, shared phone number) per branch. | REQ-034 says staff fix these by hand but not who, or how. Archiving keeps payment history. | FR-033, FR-034, FR-035 |
| PD-010 | A reminder goes out at 09:00 India time on its due day. It says name, expiry date and how to renew. It is skipped for a member who already renewed, has no phone number, has stopped reminders, or is archived. A failed send is retried up to 3 times that day, then marked failed. | The client gave the days, not the time or the content. Skipping renewed members avoids reminding someone who has already paid. | FR-036, FR-038 |
| PD-011 | Dashboard definitions. "Active members": members with a paid membership that has not expired, counted by home branch; free-trial members are not counted. "Renewals due this week": paid memberships whose expiry date is from today to 6 days ahead and that have not renewed. "Revenue per month": the sum of successful online payments and desk payments in the calendar month, by the member's home branch. | The brief names three figures but does not define them. | FR-042, FR-043, FR-044 |
| PD-012 | Performance targets: check-in result within 2 seconds for 95% of check-ins while online; member pages within 3 seconds on 4G. A receipt shows member name, plan, amount, date and payment reference. | The client gave no response times or receipt content. | NFR-006, FR-018 |
| PD-013 | Offline check-in: the tablet refreshes its saved member list every 5 minutes while online, shows an "offline" banner with the time of the last refresh, keeps check-ins on the tablet, and sends them as soon as the internet is back. | The client said "if possible" for 10-15 minutes. Q-018 is open, so these details can change with the answer. | FR-031, NFR-013 |
| PD-014 | Usability targets: sign-up to payment in no more than 5 screens; renewal in no more than 3 screens after sign-in. | A-027 asks for "a few screens". This turns it into a testable number. | NFR-003 |
| PD-015 | One phone number belongs to one member. The same number cannot be used for two accounts, two trials, or two members after a staff edit. | Sign-in, check-in by phone and the once-per-phone trial all key on the phone number. A shared family phone would not be allowed; see Questions to raise. | FR-009, FR-034, FR-022 |
| PD-016 | A wrongly entered desk payment is cancelled by the branch manager or the owner, with a reason. The expiry date goes back to what it was. Front-desk staff cannot cancel. | Without it, a typing mistake would give a member free time. Refunds themselves stay out of the app (REQ-027). | FR-015 |

### Assumptions and open questions

Assumptions (proposed unless noted):
- A-003: the expiry warning is only a warning; the app does not control doors.
- A-004: the member shows the QR code on their own phone; staff scan it with the tablet camera. No scanner hardware.
- A-005: the only WhatsApp messages are the two expiry reminders, the sign-in code and the trial reminder.
- A-007: the app stores name, phone, plan, payments and check-ins, no health data; normal DPDP Act practice.
- A-008: peak load is the gym rush, up to 3,000 members; no load testing.
- A-009: availability at normal gym hours; no SLA.
- A-013, A-026: the owner creates staff and manager accounts; no trainer role; front desk can look up any member valid at their gym.
- A-014: plan prices are the same at all 3 gyms; the client supplies the price list.
- A-015: an expired member can renew; the new period starts on the payment date.
- A-016: pausing a membership and switching plans are not in the app.
- A-018: mobile-friendly website in current Chrome and Safari; check-in on the client's Android tablet.
- A-019: existing members are loaded from the Excel as it is; incomplete and duplicate rows are not rejected or merged by us.
- A-020: dashboard figures per branch, on screen only, no export.
- A-022: trial members can check in for 7 days; loaded numbers cannot start a trial; the number is verified by a code.
- A-023: failed or abandoned payments start no membership; refunds are not in the app.
- A-024: the client pays WhatsApp message charges directly to the provider.
- A-025: the Razorpay account and WhatsApp number belong to FitZone, which gives us access.
- A-027: members include people with low digital skills; plain screens; no formal accessibility standard.
- A-028: a member can stop reminders by asking staff or replying to the message.
- SA-001: launch is 1 January 2027.
- SA-002: staff can record desk payments (default of Q-005; no REQ yet).
- SA-003: a membership is valid at all 3 gyms.
- SA-004: the owner edits plans and prices on an admin screen.
- SA-005: a renewal before expiry is added after the current expiry date.
- SA-006: members sign in by phone plus a WhatsApp code; staff by username and password.
- SA-007: simple receipt, no GST invoice.
- SA-009: members with no phone number are loaded, found by name, and get no reminders.
- SA-010: trial members can check in; one reminder before the trial ends.
- SA-011: offline check-in uses a saved copy on the tablet.
- SA-012: the existing Kothrud WhatsApp number is used for all branches if it can send automated messages.
- SA-013: if time gets short, items move to after launch in this order: dashboard, member pages, renewal, reminders last; offline check-in also moves.
- SA-014: the tablet is provided by the client with a working camera.
- SA-016: the existing members are loaded once, before launch.

Open questions (no answer yet; the PRD uses the default):
- Q-004 (blocking): is the launch 1 January 2027?
- Q-005 (blocking): can staff record cash or UPI payments taken at the desk? FR-015 relies on it.
- Q-006: is a membership valid at all 3 gyms? FR-001, FR-030.
- Q-008: who changes plans and prices? FR-011.
- Q-009: does a renewal start from the old expiry date? FR-019.
- Q-011: how do members sign in (WhatsApp code, SMS code, email and password)? FR-002.
- Q-013: simple receipt or GST invoice? FR-018.
- Q-014: does the client already have a domain or hosting? Not in the product; affects set-up.
- Q-016: how are members with no phone number handled? FR-027.
- Q-017: what happens when a free trial ends? FR-023, FR-040.
- Q-018: is offline check-in with a saved copy acceptable? FR-031.
- Q-019: can the Kothrud WhatsApp number send automated messages? FR-039, FR-002.
- Q-020: in what order do items move if time is short? NFR-012.

### Questions to raise

For the next clarification round (no Q- ID yet):

1. **Desk payments have no REQ.** FR-015 is in the approved estimate through SA-002, but no REQ in the register covers it. Intake should add one if Q-005 is answered yes. If the answer is no, FR-015, the "Record payment" flow and the desk part of FR-044 are withdrawn.
2. **Missed renewals today.** The client has not said how many renewals are missed now, so the renewal target in section 2 is `TBD`. We need a rough number or a decision that the first months of app data are the baseline.
3. **Shared phone numbers.** The app treats one phone number as one member (PD-015). Do any members share a phone (for example a couple or a parent and child)? If yes, the sign-in, trial and check-in rules need to change. The duplicate rows in the Excel (REQ-033) may include such cases.
4. **Name of the third branch.** The sources name Kothrud and Baner only. The branch list is needed for sign-up and the dashboard (FR-001).
5. **Letting expired members in.** The PRD lets staff record entry of an expired member (PD-005). Does the owner want that, or should it need a branch manager?
6. **Day-one fit.** The scope says full scope does not fit before 1 January. The client has not placed the member pages, renewal and reminders on day one (Q-020 is open); renewal and reminders are the main way to reach the goal of fewer missed renewals (REQ-002), so the reviewer should look at that choice.

## 9. Version history

| Version | Date | Change | Request |
|---|---|---|---|
| 1.0 | 2026-11-04 | First PRD after Gate 1 (G1 approved 2026-11-04). | Request 1 |
