# Feature Specification: Sign-in, roles and staff accounts

**Feature Branch**: `002-identity-access`

**Created**: 2026-11-10

**Status**: Draft

**Input**: User description: "Sign-in, roles and staff accounts. Patients sign in with a phone number and an SMS code; receptionists, dentists and the practice manager sign in with username and password; each role sees only what it needs; the practice manager creates and deactivates staff accounts and erases a patient's data on request. Covers FR-002, FR-003, FR-004, FR-005, NFR-006, NFR-007."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Patient signs in with a phone code (Priority: P1)

A returning patient opens the BrightSmile website on their phone, enters their phone number, receives a one-time code by SMS, enters it and is signed in. A wrong or expired code is reported clearly and the patient can ask for a new code. After 5 wrong tries the patient must wait 15 minutes before trying again. Once signed in, the patient stays signed in for 7 days from their last use so they do not need a new code for every visit.

**Why this priority**: Every patient flow (booking, changing, cancelling) starts with signing in; without it nothing else in the product is reachable by patients.

**Independent Test**: Can be fully tested with a test phone number and a stubbed message sender: request a code, enter it, and reach a signed-in state; then repeat with wrong, expired and repeated-wrong codes. Delivers a working patient sign-in.

**Acceptance Scenarios**:

1. **Given** a patient account exists for a phone number, **When** the patient enters the number and asks for a code, **Then** a 6-digit code is sent by SMS and the screen asks for the code. (source: FR-002)
2. **Given** a code was sent less than 10 minutes ago, **When** the patient enters it correctly, **Then** the patient is signed in and sees their own appointments area. (source: FR-002)
3. **Given** a code was sent, **When** the patient enters a wrong code, **Then** the screen says the code is wrong, shows how to get a new code, and the wrong try is counted. (source: FR-002)
4. **Given** a code was sent more than 10 minutes ago, **When** the patient enters it, **Then** the screen says the code has expired and offers a new code. (source: FR-002)
5. **Given** a patient has entered 5 wrong codes for a phone number, **When** they try again within 15 minutes (with the old or a new code), **Then** the system refuses and says to wait, and after 15 minutes a new code can be requested. (source: FR-002, NFR-006)
6. **Given** a patient has not used the site for less than 7 days, **When** they return, **Then** they are still signed in; **Given** 7 days without use, **Then** they must sign in again. (source: FR-002)
7. **Given** a single network address or a single day has produced too many code requests, **When** another code is requested, **Then** the request is refused without sending an SMS. (source: NFR-006)

---

### User Story 2 - New patient creates an account (Priority: P1)

A patient whose phone number is not yet known enters the number, verifies the code and is then asked for their name. Only after the code is verified and the name is given is the account created and the patient signed in.

**Why this priority**: Most patients are new at go-live; without account creation they cannot book online.

**Independent Test**: Use a phone number with no account: verify the code, give a name, and check that exactly one patient account and one person record exist and that no account exists if the code was never verified.

**Acceptance Scenarios**:

1. **Given** a phone number with no account, **When** the patient verifies a correct code, **Then** the screen asks for their name and no account exists yet. (source: FR-002)
2. **Given** the code is verified for a new number, **When** the patient gives a name, **Then** one account for that phone number and one person record with that name are created and the patient is signed in. (source: FR-002, NFR-007)
3. **Given** the code for a new number is wrong or expired, **When** the patient continues, **Then** no account is created. (source: FR-002)
4. **Given** the name is empty, **When** the patient submits, **Then** the screen asks for a name and creates nothing. (source: FR-002)
5. **Given** an account already exists for the phone number, **When** a patient signs in with it, **Then** no second account is created. (source: FR-002)

---

### User Story 3 - Staff sign in with username and password (Priority: P1)

A receptionist, dentist or the practice manager opens the staff sign-in screen, enters their username and password and reaches the screen for their role. After 5 failed attempts for the same username the account is locked for 15 minutes. Staff sessions end after 8 hours, or after 30 minutes without use. Passwords are at least 10 characters long.

**Why this priority**: Reception, dentists and the manager cannot run the clinic without signing in; it is also the first line of defence for patient data.

**Independent Test**: Create a staff account in test data, sign in with right and wrong passwords, check lockout, idle and maximum session ends.

**Acceptance Scenarios**:

1. **Given** an active staff account, **When** the person enters the correct username and password, **Then** they are signed in and land on the screen for their role. (source: FR-003)
2. **Given** an active staff account, **When** a wrong password is entered, **Then** the screen says the username or password is wrong without saying which one. (source: FR-003, NFR-006)
3. **Given** 5 failed sign-ins for a username, **When** a sixth is tried within 15 minutes (even with the right password), **Then** it is refused with a message to wait; after 15 minutes sign-in works again. (source: NFR-006)
4. **Given** a staff member is signed in, **When** 30 minutes pass without use or 8 hours pass since sign-in, **Then** the next request requires signing in again. (source: FR-003)
5. **Given** a password is set or changed, **When** it has fewer than 10 characters, **Then** it is rejected. (source: NFR-006)
6. **Given** any screen or call, **When** it is reached over plain HTTP, **Then** it is not served; all traffic is over HTTPS. (source: NFR-006)
7. **Given** a signed-in staff member, **When** they change their own password (giving the current one) or the manager sets a new password for them, **Then** the new password works at the next sign-in and the old one does not. (source: FR-003, FR-005)

---

### User Story 4 - Each role sees only what it needs (Priority: P1)

Whatever a person asks for, the system decides from who they are, not from ids they type or change. A patient sees only their own appointments and those of their family members. A receptionist sees and changes appointments of their own clinic only, but can search for any patient by phone number or name. A dentist sees only their own day and cannot change anything. The practice manager sees both clinics and the settings. Other features rely on this decision when they return data.

**Why this priority**: This is the security core (role separation); every other module depends on it and a leak of patient data is the main product risk.

**Independent Test**: Run an automated per-role test matrix: for each role and each protected operation, check allowed and refused results, including requests with another clinic's or patient's id.

**Acceptance Scenarios**:

1. **Given** a patient is signed in, **When** they ask for an appointment of a person who is not themselves or one of their family members, **Then** the system refuses it as if it did not exist. (source: FR-004, NFR-006)
2. **Given** a receptionist of clinic A, **When** they ask for or change an appointment of clinic B, **Then** the system refuses. (source: FR-004, NFR-006)
3. **Given** a receptionist of clinic A, **When** they search patients by phone number or name, **Then** they find patients regardless of clinic but see appointments of clinic A only. (source: FR-004)
4. **Given** a dentist is signed in, **When** they ask for another dentist's day or try to change anything, **Then** the system refuses. (source: FR-004)
5. **Given** the practice manager is signed in, **When** they open data of either clinic or the settings, **Then** it is allowed. (source: FR-004)
6. **Given** a person's role, clinic or active flag changed since they signed in, **When** they make their next request, **Then** the current values apply at once. (source: FR-004, FR-005)
7. **Given** a request without sign-in, or one that changes data without coming from the BrightSmile website, **When** it is made, **Then** it is refused. (source: NFR-006)

---

### User Story 5 - Practice manager manages staff accounts (Priority: P1)

The practice manager opens the staff screen to create receptionist and dentist accounts, to assign each receptionist to a clinic, and to deactivate an account when a person leaves. A deactivated person cannot sign in, and a person already signed in loses access on their next request.

**Why this priority**: Without staff accounts nobody can use reception or dentist screens; deactivation protects patient data when staff leave.

**Independent Test**: As the manager, create a receptionist for Indiranagar, sign in as them, deactivate them, and confirm they cannot sign in and an open session stops working.

**Acceptance Scenarios**:

1. **Given** the manager is on the staff screen, **When** they create a receptionist with name, username, initial password and clinic, **Then** the account exists, is active and is assigned to that clinic. (source: FR-005)
2. **Given** the manager creates a dentist account, **When** it is saved, **Then** the dentist can sign in and see their own day. (source: FR-005)
3. **Given** a receptionist is assigned to one clinic, **When** the manager assigns them to another clinic, **Then** the receptionist's access follows the new clinic at once. (source: FR-005, FR-004)
4. **Given** an active staff account, **When** the manager deactivates it, **Then** the person cannot sign in and an existing session is refused on its next request. (source: FR-005)
5. **Given** a username already exists, **When** the manager creates another with the same username, **Then** the system refuses. (source: FR-005)
6. **Given** a person who is not the practice manager, **When** they try to create, change or deactivate a staff account, **Then** the system refuses. (source: FR-005, FR-004)
7. **Given** the manager is the only active manager, **When** they try to deactivate their own account, **Then** the system refuses. (source: FR-005)

---

### User Story 6 - Practice manager erases a patient's data on request (Priority: P2)

When a patient asks for their data to be deleted, the practice manager opens an admin screen, finds the patient account and starts erasure. The patient's name, phone number, family members' names and birth years, and stored messages are removed or anonymised within 30 days of the request. Appointment rows stay, anonymised, so clinic counts stay correct.

**Why this priority**: Required by the DPDP Act and the privacy requirement, but not needed for the first sign-in flows; it must be ready by go-live.

**Independent Test**: Create a patient with family members and appointments, run erasure, and check that no name, phone or birth year remains while appointment counts are unchanged.

**Acceptance Scenarios**:

1. **Given** the manager is on the erasure screen, **When** they find a patient account by phone number and confirm erasure, **Then** the request is recorded with its date and the account can no longer sign in. (source: NFR-007)
2. **Given** an erasure was confirmed, **When** the process completes (within 30 days of the request), **Then** the account, the person records of the account holder and family members, and the stored messages hold no name, phone number or birth year. (source: NFR-007)
3. **Given** the erased patient had appointments, **When** erasure completes, **Then** the appointment rows remain without any personal link. (source: NFR-007)
4. **Given** the system stores personal data, **When** the stored fields are reviewed, **Then** only name, phone number, family members' names and birth years, appointments, treatment type and message choice are held; no clinical data. (source: NFR-007)
5. **Given** a signed-in user who is not the practice manager, **When** they try to use erasure, **Then** it is refused. (source: NFR-007, FR-004)
6. **Given** logs are inspected, **When** any sign-in or erasure activity is searched, **Then** no name, phone number or birth year appears. (source: NFR-007)
7. **Given** sign-in codes and old personal data exist, **When** retention periods pass (sign-in codes 24 hours, accounts idle for 24 months, staff 24 months after deactivation), **Then** they are deleted or anonymised; messages (90 days) and appointments (24 months) follow the same rule in the features that own them. (source: NFR-007)

---

### User Story 7 - Reception deactivates a patient account (Priority: P3)

If a phone number has been taken over or swapped, or a patient asks, reception can deactivate that patient's account so nobody can sign in with it.

**Why this priority**: It is the agreed mitigation for the accepted risk of a swapped SIM; it is a small, rarely used action.

**Independent Test**: As a receptionist, deactivate a test patient account and check the patient cannot sign in and an open session is refused.

**Acceptance Scenarios**:

1. **Given** a receptionist finds a patient account by phone number or name, **When** they deactivate it, **Then** the patient cannot sign in and an open session is refused on its next request. (source: NFR-006)
2. **Given** a deactivated patient account, **When** the practice manager reactivates it, **Then** the patient can sign in again. (source: NFR-006)
3. **Given** a dentist or a patient, **When** they try to deactivate a patient account, **Then** it is refused. (source: NFR-006, FR-004)

---

### Edge Cases

- A phone number is entered in a different format (with +91 or spaces): it is treated as the same number.
- The SMS provider is down: the patient is told the code could not be sent and can try again; no code counts as a wrong try.
- Two code requests in a row for one phone number: only the latest code is valid.
- A patient requests a code while the 15-minute wait is running: no SMS is sent.
- A deactivated staff member's session is open on a second device: both are refused on the next request.
- The manager creates a dentist who works at both clinics: a dentist has no single clinic restriction on their own day.
- A patient asks for erasure while a future appointment exists: the future appointment is kept for the clinic but anonymised, and the clinic is told on the erasure screen that it has future appointments.
- Erasure of an account that has family members: all person records of the account are anonymised together.
- Cookie missing, expired or tampered with: the request is treated as not signed in.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST let a patient sign in with a phone number and a one-time code sent by SMS, and MUST accept only the most recent code. (source: FR-002)
- **FR-002**: The sign-in code MUST be valid for 10 minutes and allow 5 wrong tries; after the 5th wrong try the phone number MUST be locked for 15 minutes. (source: FR-002, NFR-006)
- **FR-003**: The system MUST tell the patient when a code is wrong or expired and MUST offer a new code, except during the 15-minute wait. (source: FR-002)
- **FR-004**: The system MUST create a patient account and a person record for a new phone number only after the code is verified and a non-empty name is given, and MUST NOT create a second account for an existing phone number. (source: FR-002)
- **FR-005**: The system MUST limit code requests per network address and per day to protect against floods and SMS cost, refusing excess requests without sending an SMS; the limits are in Assumptions. (source: NFR-006)
- **FR-006**: The system MUST keep patient sessions for 7 days from last use. (source: FR-002)
- **FR-007**: The system MUST let receptionists, dentists and the practice manager sign in with a username and password. (source: FR-003)
- **FR-008**: Staff passwords MUST have at least 10 characters, and the system MUST lock a staff username for 15 minutes after 5 failed sign-ins. (source: NFR-006)
- **FR-009**: Staff sessions MUST end after 8 hours from sign-in or after 30 minutes without use. (source: FR-003)
- **FR-010**: Sign-in failure messages MUST NOT reveal whether the username or the password was wrong. (source: NFR-006)
- **FR-011**: The system MUST decide what a signed-in user may see or change from their role, clinic and active status held by the system at the time of each request, and not from ids or roles supplied in the request. (source: FR-004, NFR-006)
- **FR-012**: A patient MUST be limited to their own appointments and those of their family members. (source: FR-004)
- **FR-013**: A receptionist MUST be limited to the appointments of their own clinic and MAY search all patients by phone number or name. (source: FR-004, NFR-006)
- **FR-014**: A dentist MUST be limited to their own day, read only. (source: FR-004)
- **FR-015**: The practice manager MUST have access to both clinics and the settings. (source: FR-004)
- **FR-016**: The system MUST provide to all other features one shared way to ask "may this user do this on this clinic or patient", so every feature applies the same rules. (source: FR-004, NFR-006)
- **FR-017**: The system MUST refuse requests that change data when they do not come from the BrightSmile website, and MUST serve everything over HTTPS only. (source: NFR-006)
- **FR-018**: The practice manager MUST be able to create receptionist and dentist accounts, assign a receptionist to a clinic, change that assignment, and deactivate an account. (source: FR-005)
- **FR-019**: A deactivated person MUST be unable to sign in, and any open session MUST stop working at their next request. (source: FR-005)
- **FR-020**: Only the practice manager MUST be able to manage staff accounts; the last active practice manager account MUST NOT be deactivated. (source: FR-005, FR-004)
- **FR-021**: The system MUST store only name, phone number, family members' names and birth years, appointments, treatment type and message choice, and no clinical data. (source: NFR-007)
- **FR-022**: The practice manager MUST be able to start erasure of a patient's data on request in an admin screen, and the system MUST remove or anonymise the person records, the account and the stored messages within 30 days of the request while keeping appointment rows without a personal link. (source: NFR-007)
- **FR-023**: The system MUST delete sign-in codes after 24 hours and anonymise patient accounts idle for 24 months and staff accounts 24 months after deactivation. Deleting messages after 90 days and anonymising appointments after 24 months is done by the features that own them; this feature gives them the hooks to anonymise a person's link and to erase an account's messages. (source: NFR-007)
- **FR-024**: The system MUST NOT write names, phone numbers or birth years to logs. (source: NFR-007)
- **FR-025**: Receptionists MUST be able to deactivate a patient account, and the practice manager MUST be able to reactivate it; a deactivated patient cannot sign in. (source: NFR-006)
- **FR-026**: The system MUST hold, for each patient account, the preferred message channel (default SMS) and a reminders opt-out flag, so other features can read and set them; this feature does not change them itself. (source: FR-013, FR-031)
- **FR-028**: A signed-in staff member MUST be able to change their own password, and the practice manager MUST be able to set a new password for any staff account; both follow the 10-character minimum. Assumed: no self-service reset by email or SMS (open question Q3). (source: FR-003, FR-005, NFR-006)
- **FR-027**: Each requirement and screen of this feature MUST be covered by automated tests for every role and operation, including tests that prove no cross-clinic and no cross-patient read. (source: NFR-006)

### Key Entities *(include if feature involves data)*

- **Staff account**: A receptionist, dentist or practice manager who signs in with username and password; holds name, username, role, clinic (receptionists), link to the dentist (dentists) and active status. Personal data of former staff is anonymised 24 months after deactivation.
- **Patient account**: One per phone number; holds phone number, name, preferred message channel, reminders opt-out and active status. Kept until deletion on request.
- **Patient (person)**: A person the account books for: the account holder or a family member (up to 5); holds name and birth year and belongs to one patient account. Family-member management is done by another feature; this feature creates the account holder's person record.
- **Sign-in code challenge**: A code issued to a phone number with an expiry, a count of wrong tries and a lock time; kept for 24 hours.
- **Access context**: The decision, made for every request, of who the user is, their role, clinic and active status; shared by all features.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A returning patient can sign in with a code in under 1 minute from entering the phone number, on a phone.
- **SC-002**: A new patient can create an account in under 2 minutes after the code arrives.
- **SC-003**: In the automated role tests, 100% of cross-clinic and cross-patient requests are refused, and 0 cross-clinic or cross-patient reads occur.
- **SC-004**: After 5 wrong codes (or 5 wrong staff passwords) 100% of further attempts are refused for 15 minutes.
- **SC-005**: A deactivated person is refused at their next request in 100% of tests, with no waiting time.
- **SC-006**: 100% of erasure requests are completed within 30 days, and a check after erasure finds no name, phone number or birth year for that patient.
- **SC-007**: 0 occurrences of a name, phone number or birth year in sampled logs.
- **SC-008**: 100% of staff passwords stored are at least 10 characters when set, and 100% of traffic is over HTTPS.

## Assumptions

- Q-007 is open: one account per phone number with up to 5 family members (SA-001). If families need separate sign-ins on one phone, sign-in changes. (open question Q1)
- The messaging feature provides a "send message" capability with a stub in tests; the real SMS provider is built in another feature. If the provider is down, sign-in codes cannot be sent (accepted risk RSK-002).
- Code limits other than the PRD's: 6-digit code; sent by SMS only (SA-006). Per-network-address and daily code limits have no figures in the PRD; proposed values are in open question Q2.
- A SIM swap or recycled phone number lets a person sign in as that patient (RSK-009, accepted); reception can deactivate the account.
- Staff passwords are set by the practice manager at creation. Assumed: staff can change their own password when signed in and the manager can reset a forgotten one; no email or SMS reset link (open question Q3). The first manager account is created by a set-up command provided with this feature, using a secret from the environment.
- Assumed: up to 10 code requests per network address per hour, 5 per phone number per hour and 1,000 codes per day in total, all as settings (open question Q2).
- Receptionists may search all patients by phone number or name, but see appointments of their own clinic only (ASM-011).
- Erasure on request is done by the practice manager in an admin screen (ASM-013, added for NFR-007). Retention: appointments 24 months then anonymised, messages 90 days, sign-in codes 24 hours.
- Family members' add/edit screens and booking for them belong to another feature (FR-006); the stored message choice (FR-013) and reminders opt-out (FR-031) are covered by other features and only stored here.
- All screens and messages are in English and times in IST (NFR-008).
- Sessions: patient 7 days from last use; staff 8 hours or 30 minutes idle (ASM-008).
- Depends on: the message-sending capability (messaging feature), the clinics and dentists data (feature 001) for assigning a receptionist to a clinic and linking a dentist, and the web app shell.
