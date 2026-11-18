# FitZone gym app — Designs (TEST STAND-IN from PRD section 6)

> Test input: user flows and screens copied from prd.md section 6; no separate UX design exists.

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

