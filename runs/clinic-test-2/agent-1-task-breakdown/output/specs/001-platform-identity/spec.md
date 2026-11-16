# Feature Specification: Platform, sign-in, roles and clinics (MOD-01)

**Feature Branch**: `001-platform-identity` (no git branch is used; the spec folder is `specs/001-platform-identity`)

**Created**: 2026-11-10

**Status**: Draft

**Release**: Release 1 (go-live 1 March 2027, firm; module deadline DL-1 2027-02-22)

**Input**: User description: "Platform, sign-in, roles and clinics (MOD-01). Patients sign in with phone number and SMS code; receptionists, dentists and the practice manager sign in with username and password; each role sees only what it needs; the practice manager manages staff accounts; the system holds the clinics and dentists; patient data is deleted on request. Includes the project foundation that every other feature builds on."

**Requirement ids covered**: FR-001, FR-002, FR-003, FR-004, FR-005, NFR-006, NFR-007, NFR-009 (ids refer to `prd.md`).

> **Numbering note.** The `FR-00x` ids in the *Functional Requirements* section below are local to this spec.
> Each one names the `prd.md` requirement it comes from at its end, as `(source: ...)`. The PRD's family-member
> requirement (PRD FR-006) is **not** part of this feature; it is a Release 2 feature (see Assumptions, Q-007).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A patient signs in with a phone number and a code (Priority: P1)

A patient opens the BrightSmile website on their phone, enters their mobile number and receives a 6-digit code by
SMS. Entering the code signs them in. A phone number the system has not seen before becomes a new account once the
code is verified and the patient has typed their name. Wrong or expired codes are explained plainly and a new code
can be asked for. After 5 wrong tries the patient must wait 15 minutes. The patient stays signed in for 7 days from
their last use so they do not need a new SMS every visit. (source: FR-002, NFR-006)

**Why this priority**: Without patient sign-in no patient can book, which is the main goal of the product
(booking online instead of by phone). It is also the only part of the system that costs money per use (SMS), so its
limits matter from day one.

**Independent Test**: With a fake SMS sender, request a code for a phone number, read it from the fake sender,
verify it, and see a signed-in session; repeat with a wrong code 5 times and see the 15-minute wait. Fully testable
without any booking feature.

**Acceptance Scenarios**:

1. **Given** a phone number that already has an account, **When** the patient asks for a code and enters the correct code within 10 minutes, **Then** the patient is signed in and sees their name.
2. **Given** a phone number with no account, **When** the patient enters the correct code, **Then** the system asks for their name, and after the name is given an account is created and the patient is signed in.
3. **Given** a code was sent, **When** the patient enters a wrong code, **Then** the system says the code is wrong, says how many tries are left, and offers to send a new code.
4. **Given** a code was sent more than 10 minutes ago, **When** the patient enters it, **Then** the system says the code has expired and offers a new code.
5. **Given** a patient has entered 5 wrong codes for a phone number, **When** they try again or ask for a new code within 15 minutes, **Then** the system refuses and says when they can try again; after 15 minutes they can ask for a new code.
6. **Given** a signed-in patient who last used the site 6 days ago, **When** they open the site, **Then** they are still signed in.
7. **Given** a signed-in patient who last used the site more than 7 days ago, **When** they open the site, **Then** they must sign in again.
8. **Given** too many codes were requested from one network address in a short time, or the daily limit of codes for one phone number is used up, **When** another code is requested, **Then** the system refuses without sending an SMS and says to try later or phone the clinic.

---

### User Story 2 - Staff sign in with a username and password (Priority: P1)

A receptionist, dentist or practice manager opens the staff sign-in page, enters a username and password and lands
on the screen for their role. Passwords have at least 10 characters. After 5 wrong passwords in a row the account is
locked for 15 minutes. Staff sessions end after 8 hours, or after 30 minutes without use. (source: FR-003, NFR-006)

**Why this priority**: Reception, dentists and the manager cannot work without it, and the other staff stories
(roles, account management) depend on it.

**Independent Test**: Create a staff account in the database (seed or admin tool), sign in with the right password,
fail 5 times with a wrong one and see the lock, and check that a session idle for 30 minutes is refused.

**Acceptance Scenarios**:

1. **Given** an active staff account, **When** the person enters the correct username and password, **Then** they are signed in and the system tells the web app their role and (for receptionists) their clinic.
2. **Given** an active staff account, **When** the person enters a wrong password, **Then** the system says the username or password is wrong, without saying which one.
3. **Given** 5 wrong passwords in a row for one username, **When** the person tries again within 15 minutes (even with the right password), **Then** the sign-in is refused with a message that the account is locked and for how long.
4. **Given** a password shorter than 10 characters, **When** it is set for a staff account, **Then** the system rejects it and says the minimum length.
5. **Given** a signed-in staff member idle for 30 minutes, or signed in for 8 hours, **When** they make a request, **Then** the session is refused and they must sign in again.
6. **Given** a signed-in user, **When** they sign out, **Then** the session ends at once and cannot be reused.

---

### User Story 3 - Each role sees only what it needs (Priority: P1)

Every request the system answers is checked against who is asking. A patient reaches only their own data (the
patient's family members are added by a later feature, but the rule is built here to cover them). A receptionist
reaches only the data of their own clinic. A dentist sees only their own day, read only. The practice manager sees
both clinics and the settings. The check uses the signed-in person's role, clinic and active flag read from the
database on every request, never ids or roles sent by the browser. Other features use the same check. Searching
patients by phone number or name is allowed for receptionists and the manager across all clinics, while
appointments stay limited to the receptionist's own clinic. (source: FR-004, NFR-006)

**Why this priority**: This is the security backbone (QA-007). Every later module relies on it, and the PRD makes
"a receptionist reaches only their own clinic" a hard requirement.

**Independent Test**: With one account of each role, call the same set of protected operations and check each role
gets exactly the allowed answers and a refusal otherwise; change a request's clinic id to the other clinic as a
receptionist and see it refused; deactivate an account and see its next request refused.

**Acceptance Scenarios**:

1. **Given** a receptionist of Indiranagar, **When** they ask for the clinic list or for data of Whitefield, **Then** they see Indiranagar only and Whitefield is refused.
2. **Given** a practice manager, **When** they ask for the clinic list, **Then** they see both clinics and the settings screens.
3. **Given** a dentist, **When** they ask for their own day or clinics, **Then** it is allowed read only, and any change request is refused.
4. **Given** a patient, **When** they ask for another patient's data, or send a patient id that is not theirs, **Then** the request is refused; only data owned by the signed-in person is returned.
5. **Given** a signed-in person whose account was just deactivated or whose role changed, **When** they make their next request, **Then** it is refused or handled with the new role at once, without waiting for the session to expire.
6. **Given** any write request from a browser, **When** it lacks the anti-forgery header or comes from another origin, **Then** it is refused.
7. **Given** an unsigned visitor, **When** they call any protected operation, **Then** they get a "sign in" answer and no data.
8. **Given** a receptionist, **When** they search for a patient by phone number or name, **Then** patients of any clinic can be found, but appointments shown with the patient are limited to their own clinic.

---

### User Story 4 - The practice manager manages staff accounts (Priority: P1)

The practice manager opens the "Staff" screen, creates accounts for receptionists and dentists (name, username,
temporary password, role), assigns each receptionist to one clinic, links a dentist account to a dentist record,
and deactivates a person who leaves. A deactivated person cannot sign in and any session they hold stops working at
once. The manager can also reactivate an account and reset a password. (source: FR-005, NFR-006)

**Why this priority**: Staff accounts are how reception and dentists get in; without this screen only developers
could create them. The first manager account is seeded.

**Independent Test**: Sign in as the manager, create a receptionist for Whitefield, sign in as that receptionist and
see Whitefield only, deactivate them, and see sign-in and the old session refused.

**Acceptance Scenarios**:

1. **Given** a signed-in manager, **When** they create a receptionist with a username, name, a password of at least 10 characters and a clinic, **Then** the account exists, is active and can sign in.
2. **Given** a signed-in manager, **When** they create a receptionist without a clinic, **Then** the system refuses and says a clinic is required.
3. **Given** a username already in use, **When** the manager creates another account with it, **Then** the system refuses and says the username is taken.
4. **Given** an active staff account that is signed in, **When** the manager deactivates it, **Then** the next request from that person is refused and they cannot sign in again until reactivated.
5. **Given** a receptionist or dentist, **When** they try to create, change or deactivate an account, **Then** the request is refused.
6. **Given** the manager is the only active manager, **When** they try to deactivate themselves, **Then** the system refuses so the practice cannot lock itself out.
7. **Given** a staff member forgot their password, **When** the manager resets it to a new temporary password of at least 10 characters, **Then** the old password stops working and the person's failed-attempt lock is cleared.

---

### User Story 5 - The system holds the clinics and the dentists (Priority: P1)

The system keeps the clinics (Indiranagar and Whitefield from day one) and the dentists as data. A dentist can work
at more than one clinic, on set weekdays. The practice manager adds a third clinic, adds a dentist, and sets which
weekdays a dentist works at which clinic, in the staff screens, with no change to the software. Later features give
every appointment exactly one clinic and one dentist from these records. (source: FR-001)

**Why this priority**: Every booking, schedule and day view refers to a clinic and a dentist; the third clinic must
arrive as data (QA-011).

**Independent Test**: On a fresh database both clinics exist; as manager add a third clinic and a dentist who works
Monday at Indiranagar and Thursday at Whitefield; the clinic list and dentist list show them, and a deactivated
clinic is no longer offered.

**Acceptance Scenarios**:

1. **Given** a new installation, **When** the clinic list is read, **Then** Indiranagar and Whitefield are present and active.
2. **Given** a signed-in manager, **When** they add a clinic with a name, address and phone number, **Then** it appears in the clinic list at once for all roles that may see it, without a deployment.
3. **Given** a signed-in manager, **When** they add a dentist and set Monday at Indiranagar and Thursday at Whitefield, **Then** the dentist is listed at both clinics, only on those days.
4. **Given** a dentist already has a day at one clinic, **When** the manager assigns the same weekday at a second clinic, **Then** the system refuses, because a dentist is in one place on one day.
5. **Given** a manager deactivates a clinic or a dentist, **When** the lists are read for booking, **Then** the inactive one is not offered, while existing records that point to it stay readable.
6. **Given** a receptionist, **When** they ask to add a clinic or a dentist, **Then** the request is refused.

---

### User Story 6 - A patient's data is erased on request (Priority: P2)

When a patient asks (by phone or at reception) to have their data deleted, the practice manager opens an admin
screen, finds the patient by phone number, records the request and carries out the erasure. The patient's name,
phone number and birth year are anonymised in the person and account records, any open sessions end, and messages
held for that person are anonymised too. Appointment rows stay as anonymous counts so that reports are not broken.
The screen shows the due date (30 days after the request) and flags overdue requests. (source: NFR-007)

**Why this priority**: The privacy requirement (DPDP Act) is mandatory, but it is only needed after real patients
exist, so it comes after sign-in and roles; it still ships in Release 1.

**Independent Test**: Create a patient account, record an erasure request, run it, and check the name, phone and
birth year no longer appear anywhere in the person and account records and the patient cannot sign in with that
phone number as the old account.

**Acceptance Scenarios**:

1. **Given** a signed-in manager and a patient account, **When** the manager records an erasure request, **Then** the request is stored with its date and a due date 30 days later and is listed as open.
2. **Given** an open erasure request, **When** the manager runs the erasure, **Then** the patient's name, phone number and birth year are replaced by anonymous values, their sessions end, and the request is marked done with the date.
3. **Given** an erased patient's former phone number, **When** that number signs in again, **Then** a brand-new account is created after the code is verified; nothing of the old data returns.
4. **Given** an open request that is more than 30 days old, **When** the manager opens the list, **Then** it is flagged as overdue.
5. **Given** a receptionist, dentist or patient, **When** they try to record or run an erasure, **Then** it is refused.
6. **Given** an erasure ran, **When** logs and audit records are read, **Then** they contain the erased person's id only, never name or phone number.

---

### User Story 7 - Old identity data is cleaned up automatically (Priority: P3)

A daily job removes what is no longer needed: sign-in codes after 24 hours, personal data of staff and dentists
24 months after deactivation, and personal data of patient accounts that have not been used for 24 months. The job
also provides a place where later features register their own retention rules (appointments 24 months, messages 90
days). (source: NFR-007)

**Why this priority**: It keeps the "store only what is needed" promise over time. It is not needed on go-live day,
so it can be last, but it is small and built on the same foundation as erasure.

**Independent Test**: Insert old records with back-dated times and run the job; old codes disappear, old
deactivated staff are anonymised, and recent records are untouched.

**Acceptance Scenarios**:

1. **Given** a sign-in code created more than 24 hours ago, **When** the daily job runs, **Then** it is deleted.
2. **Given** a staff account deactivated more than 24 months ago, **When** the daily job runs, **Then** its name is anonymised and the account stays deactivated.
3. **Given** a patient account not used for 24 months, **When** the daily job runs, **Then** its personal data is anonymised in the same way as an erasure.
4. **Given** a record inside its retention period, **When** the daily job runs, **Then** it is not changed.
5. **Given** the daily job fails half-way, **When** it is run again, **Then** it finishes the work without double effects.

---

### Foundation (not a user story: project skeleton and shared framework)

Besides the stories above, this feature delivers what every other feature builds on: the two code bases with
build and test set-up, configuration from the environment, database migrations, a health check, structured logging
without personal data, the session/token framework and the access-check framework used by all modules. These items
are planned as the Setup and Foundational phases in `tasks.md` and are described in requirements FR-012, FR-014,
FR-018 and FR-019 below. (source: NFR-006, NFR-009)

### Edge Cases

- Phone numbers are accepted in common Indian forms (`9876543210`, `+91 98765 43210`) and stored in one normalised form; anything that is not a valid Indian mobile number is refused before any SMS is sent.
- The SMS provider is down or refuses: the patient is told the code could not be sent and the attempt does not count as a wrong try; the daily cap still counts requests that were sent.
- A patient asks for a new code while a valid code exists: the old code stops working, only the newest is valid.
- Two sign-in attempts for a new phone number at the same moment create exactly one account.
- A staff member and a patient use the same browser: the two sessions do not mix; the cookie that is presented decides the role.
- A staff username differs only by upper/lower case: usernames are compared case-insensitively.
- A dentist is deactivated while they have a signed-in session: the next request is refused.
- The practice manager changes a receptionist's clinic: the receptionist's next request already uses the new clinic.
- A clinic is deactivated while receptionists are assigned to it: it stays readable to them, and the manager is warned to reassign them.
- Erasure is requested for a phone number that has no account: the system says no account exists, nothing is created.
- A person's browser clock is wrong: all expiry decisions use server time.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST hold clinics as data, with Indiranagar and Whitefield present from the first start, and allow the practice manager to add, edit and deactivate clinics (name, address, phone number) without a software change. (source: FR-001)
- **FR-002**: The system MUST hold dentists as data, allow a dentist to work at more than one clinic on set weekdays, refuse two clinics for the same dentist on the same weekday, and expose stable clinic and dentist references so that each appointment can later belong to exactly one clinic and one dentist. (source: FR-001)
- **FR-003**: The system MUST let a patient sign in with a mobile phone number and a 6-digit one-time code sent by SMS. The code MUST be valid for 10 minutes, MUST be stored only in hashed form, and a newer code MUST replace the older one. (source: FR-002, NFR-006)
- **FR-004**: The system MUST allow 5 wrong code tries per phone number, after which further tries and new codes for that number are refused for 15 minutes, and MUST say plainly when the code is wrong, expired or locked and offer a new code where allowed. (source: FR-002, NFR-006)
- **FR-005**: The system MUST create a patient account for a new phone number only after the code is verified and the patient has given their name, and MUST NOT create duplicates for the same phone number. (source: FR-002)
- **FR-006**: The system MUST limit code requests per network address and per phone number per day, refusing without sending an SMS when a limit is reached. (source: FR-002, NFR-006)
- **FR-007**: The system MUST keep a patient signed in for 7 days from their last use. (source: FR-002)
- **FR-008**: The system MUST let receptionists, dentists and the practice manager sign in with a username and a password of at least 10 characters, store passwords only as strong salted hashes, lock the account for 15 minutes after 5 wrong passwords in a row, and give the same message for wrong username and wrong password. (source: FR-003, NFR-006)
- **FR-009**: The system MUST end a staff session after 8 hours or 30 minutes without use, and MUST let any user sign out so that the session cannot be reused. (source: FR-003)
- **FR-010**: The system MUST decide what each request may see or change from the signed-in person's role, clinic and active flag read from the data store on every request, and never from ids or roles sent by the browser: a patient reaches only their own records, a receptionist only their own clinic's data, a dentist only their own day read only, the practice manager both clinics and the settings. (source: FR-004, NFR-006)
- **FR-011**: The system MUST let receptionists and the practice manager search patients by phone number or name across clinics while limiting appointments shown to a receptionist to their own clinic. (source: FR-004, NFR-006)
- **FR-012**: The system MUST refuse any write that lacks the anti-forgery header or comes from an origin other than the site's own, and MUST accept traffic over HTTPS only in deployed environments. (source: NFR-006)
- **FR-013**: The system MUST let the practice manager create receptionist and dentist accounts, assign each receptionist to one clinic, link a dentist account to a dentist record, deactivate and reactivate accounts, and reset passwords; usernames MUST be unique; a deactivated person MUST NOT be able to sign in and their sessions MUST stop working at once; the last active manager MUST NOT be deactivatable. (source: FR-005, NFR-006)
- **FR-014**: The system MUST store only name, phone number, birth year (person record), preferred message channel and reminder opt-out flag, and the clinic and dentist records; it MUST NOT store clinical data, and MUST NOT write names, phone numbers or birth years to logs. (source: NFR-007)
- **FR-015**: The system MUST let the practice manager record a patient erasure request, show its due date 30 days after the request and flag overdue ones, and carry out the erasure by anonymising the person and account records, ending sessions and anonymising any message records through a step later features can add; appointment rows stay as anonymous counts. (source: NFR-007)
- **FR-016**: The system MUST run a daily retention job that deletes sign-in codes after 24 hours, anonymises staff and dentist personal data 24 months after deactivation and patient accounts unused for 24 months, and lets later features register their own retention rules. (source: NFR-007)
- **FR-017**: The system MUST send the sign-in code through a replaceable SMS sending interface so that this feature can be tested with a fake sender and the real provider is connected by the messaging features. (source: FR-002)
- **FR-018**: The system MUST provide the shared foundation for later features: a runnable service and a web app, configuration from the environment with no secrets in code, versioned database migrations, a health check, structured logs with a correlation id, and a reusable access-check framework. (source: NFR-006, NFR-009)
- **FR-019**: The work of this feature MUST be complete and releasable so that Release 1 can go live on 1 March 2027, with the module finished by deadline DL-1 (2027-02-22). (source: NFR-009)

### Key Entities *(include if feature involves data)*

- **Clinic**: a BrightSmile location (name, address, phone number, active). Two exist at the start; more are added as data.
- **Dentist**: a person who treats patients (name, active), who can work at several clinics on set weekdays; may be linked to one staff account.
- **Dentist clinic day**: which weekday a dentist works at which clinic (one clinic per weekday per dentist).
- **Staff account**: a receptionist, dentist or practice manager sign-in (username, name, role, clinic for receptionists, dentist link for dentists, password hash, active, failed-attempt lock).
- **Patient account**: a phone number that signs in (phone number, preferred message channel, reminder opt-out flag, last used time). One account per phone number.
- **Patient (person)**: the person bookings are for (name, birth year, account). The account holder is the first person; family members are added in a Release 2 feature. Kept separate from the account so that family members can be added later without changing sign-in.
- **Sign-in code challenge**: a pending phone sign-in (phone, hashed code, expiry, wrong tries, locked-until). Short lived.
- **Erasure request**: a manager-recorded request to delete a patient's data (patient, requested at, due at, done at, done by).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A returning patient can sign in with phone and code in under 1 minute; a new patient in under 2 minutes, including giving their name.
- **SC-002**: In tests, 100% of attempts by a receptionist, dentist or patient to reach another clinic's or another person's data are refused (0 cross-clinic or cross-patient reads).
- **SC-003**: After 5 wrong codes or 5 wrong passwords, 100% of further attempts within 15 minutes are refused, including attempts with the right code or password.
- **SC-004**: A deactivated staff member is locked out on their very next request (0 requests accepted after deactivation).
- **SC-005**: The practice manager can add a third clinic and a dentist in the staff screens in under 5 minutes with no deployment.
- **SC-006**: A patient's erasure is carried out within 30 days of the request in 100% of cases, and after erasure the name, phone number and birth year are found in 0 records or log lines.
- **SC-007**: The foundation can be started from an empty environment with one documented procedure, and its health check answers within 1 second.
- **SC-008**: All of the module's stories pass their independent tests and the module is ready by the deadline DL-1 (2027-02-22), seven days before go-live on 1 March 2027.

## Assumptions

- **Q-007 (open question, assumed)**: One account per phone number; family members are handled in the Release 2 feature for PRD FR-006. Only the split between account and person (ADR-0008) is built here, so adding family later needs no change to sign-in. (Assumed: SA-001 default, open question Q-007)
- **Q-008 (open question, assumed)**: Hosting and domain are not yet decided. This feature builds container-ready services configured from the environment and does not depend on a provider; the HTTPS requirement is enforced by configuration. (Assumed: managed container service and PostgreSQL in an India region, domain from the clinic, open question Q-008)
- **Q-015 (open question, assumed)**: A walk-in is a normal appointment marked arrived (SA-004). For this feature that means a walk-in patient is a normal patient record; reception search and creation of patients belongs to the reception feature (PRD FR-020) and uses the access rules built here. (Assumed: SA-004, open question Q-015)
- SMS sign-in codes only (SA-006); no WhatsApp or email sign-in.
- The sign-in code is sent in the request through an SMS sender interface; the real provider adapter, DLT-registered template and delivery tracking belong to the messaging features (DEP-001, RSK-001). Until then a fake sender is used in development and tests.
- Patient sessions last 7 days from last use; staff sessions 8 hours or 30 minutes idle (ASM-008).
- Receptionists may search all patients by phone number or name but see appointments of their own clinic only (ASM-011).
- Erasure on request is done by the practice manager in an admin screen (ASM-013); it was added for NFR-007 and is not a PRD functional requirement. Appointments are anonymised, not deleted (RSK-007).
- Retention periods follow ASM-012: appointments 24 months and messages 90 days are implemented by their owning features through the retention job built here; this feature handles sign-in codes, staff, dentists and patient accounts.
- The practice manager account is created by a seed step at installation; its first password is set from the environment and must be changed at first sign-in.
- A dentist's weekday-at-clinic assignment is stored here as a simple data record; weekly hours, breaks and leave belong to the schedule feature (MOD-02).
- A receptionist belongs to exactly one clinic; the practice manager and dentists are not tied to one clinic account field (a dentist's clinics come from the dentist records).
- Time is stored in UTC and shown in IST; all text is English (NFR-008).
- Team estimate for this module is 10 to 15 person-days (`scope/estimate.md`); family members are no longer counted in it.
