# Feature Specification: No-show report per clinic and month

**Feature Branch**: `010-noshow-report`

**Created**: 2027-03-01

**Status**: Draft

**Input**: User description: "No-show report per clinic and month (MOD-08, Release 2, DL-2 2027-03-19, not hard). The practice manager sees, for each clinic and each of the last 12 months, the number of no-shows and the no-show rate (no-shows ÷ appointments that were not cancelled). On screen only." (source: FR-032, REQ-028)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Monthly no-show figures per clinic (Priority: P1)

The practice manager asks the system for the no-show figures of every clinic for each of the last 12 months. For each clinic and month the system returns the number of no-shows, the number of appointments that were not cancelled, and the no-show rate (no-shows ÷ appointments that were not cancelled). Walk-ins count like any other appointment. Appointments cancelled by the patient and appointments cancelled by the clinic are both left out of the denominator. Months follow India time (IST). Appointments whose personal details were anonymised after 24 months still count. (source: FR-032)

**Why this priority**: This is the whole business value of the feature: the practice manager can see where no-shows happen and whether they fall. Without the figures there is nothing to show.

**Independent Test**: Load appointments in different statuses for two clinics across several months, ask for the report, and compare each number and rate with a hand count. Can be tested without any screen.

**Acceptance Scenarios**:

1. **Given** a clinic had 40 appointments in a month, of which 4 were no-shows, 6 were cancelled by the patient and 2 were cancelled by the clinic, **When** the practice manager requests the report, **Then** that clinic and month show 4 no-shows and a rate of 4 ÷ 32 = 12.5%. (source: FR-032)
2. **Given** a walk-in that was booked at reception and marked arrived, and another walk-in marked as a no-show, **When** the report is requested, **Then** both are counted in the denominator and the no-show is counted as a no-show. (source: FR-032)
3. **Given** two clinics, **When** the report is requested, **Then** each clinic has its own row of 12 months and the figures of one clinic never include appointments of the other. (source: FR-032)
4. **Given** an appointment starting at 23:30 IST on the last day of a month (which is already the next day in UTC), **When** the report is requested, **Then** it is counted in the IST month it started in. (source: FR-032)
5. **Given** an appointment in the 12-month window whose patient details have been anonymised (after 24 months, or after a deletion request), **When** the report is requested, **Then** it still counts in its month and status. (source: FR-032)
6. **Given** a clinic with no appointments, or only cancelled appointments, in a month, **When** the report is requested, **Then** that month shows 0 no-shows and no rate (not a division error). (source: FR-032)

---

### User Story 2 - No-show report screen for the practice manager (Priority: P1)

The practice manager opens the "no-show report" screen from the staff menu and sees a table per clinic: one row per month for the last 12 months, newest first, with the number of no-shows, the number of appointments that were not cancelled, and the rate as a percentage. The screen is read only and has no export. While the feature is not switched on, the screen is not offered at all. (source: FR-032)

**Why this priority**: The figures are of no use to the manager until they can read them on screen; this is the only way the report is delivered (export is a non-goal).

**Independent Test**: Sign in as the practice manager with the feature switched on, open the report screen and check that each clinic shows 12 monthly rows that match the report figures; switch the feature off and check that the screen is not offered.

**Acceptance Scenarios**:

1. **Given** the practice manager is signed in and the report is switched on, **When** they open the no-show report from the menu, **Then** they see every clinic with 12 monthly rows showing no-shows, non-cancelled appointments and rate. (source: FR-032)
2. **Given** a month with no rate (no non-cancelled appointments), **When** the table is shown, **Then** the rate cell shows a dash and not 0% or an error. (source: FR-032)
3. **Given** a third clinic has been added as data, **When** the screen is opened, **Then** the third clinic appears without any change to the screen. (source: FR-032)
4. **Given** the report is switched off, **When** the practice manager looks at the menu or opens the screen address directly, **Then** the screen is not offered and the address shows "not found". (source: FR-032)
5. **Given** the figures cannot be loaded, **When** the screen is opened, **Then** the manager sees a plain error message with a retry button, and no partial figures. (source: FR-032)
6. **Given** the report screen, **When** the manager looks for a download or print-to-file option, **Then** there is none: the report is on screen only. (source: FR-032)

---

### User Story 3 - Only the practice manager can read the report (Priority: P2)

Receptionists, dentists and patients cannot see the report or its figures, neither through the screen nor by asking the system directly. Only the practice manager sees all clinics. (source: FR-032)

**Why this priority**: The report is management information, and the roles rule (FR-004) is a security baseline. It is P2 because the figures are only harmful if the role check is missing, and the check is cheap to build together with story 1.

**Independent Test**: Request the report as each of the four roles, and without signing in; only the practice manager gets figures.

**Acceptance Scenarios**:

1. **Given** a receptionist is signed in, **When** they request the report directly, **Then** the request is refused and no figures are returned. (source: FR-032)
2. **Given** a dentist or a patient is signed in, **When** they request the report directly, **Then** the request is refused. (source: FR-032)
3. **Given** nobody is signed in, **When** the report is requested, **Then** the request is refused as not signed in. (source: FR-032)
4. **Given** a receptionist or a dentist is signed in, **When** they look at the menu, **Then** there is no no-show report entry. (source: FR-032)

---

### Edge Cases

- A clinic with no appointments in a month: 0 no-shows, no rate (dash).
- A month where every appointment was cancelled: denominator is 0, no rate.
- The current month is not finished: it is shown as the latest of the 12 months, with figures so far, marked "month so far". The 12 months are the current month and the 11 before it. Assumed: Q3.
- A clinic opened part-way through the window: months before its first appointment show 0 and a dash.
- An appointment marked no-show and then undone the same day (FR-022) is a booked/arrived appointment again and is counted by its current status.
- A deactivated clinic: still reported for the months in which it had appointments.
- A patient erased on request: the appointment stays as an anonymised row and still counts (RSK-007).
- Appointments in the future (status booked) are counted in the denominator for the month they fall in, since they are not cancelled. Only the current month can contain them.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST give the practice manager, for each clinic and each of the last 12 months (IST), the number of no-shows. (source: FR-032, REQ-028)
- **FR-002**: The system MUST give, for each clinic and month, the no-show rate as no-shows ÷ appointments that were not cancelled, shown as a percentage. (source: FR-032, REQ-028)
- **FR-003**: The system MUST count appointments cancelled by the patient and appointments cancelled by the clinic as cancelled, and leave both out of the denominator; all other statuses (booked, arrived, no-show) are in the denominator. (source: FR-032; ASM-014)
- **FR-004**: The system MUST count walk-ins like any other appointment, in the denominator and, if marked no-show, in the no-shows. Assumed: Q-015 default SA-004 (open question Q1). (source: FR-032; ASM-004)
- **FR-005**: The system MUST assign each appointment to a month by its start time in IST. (source: FR-032, NFR-008)
- **FR-006**: The system MUST still count appointments whose personal details were anonymised after 24 months. (source: FR-032; RSK-007)
- **FR-007**: The system MUST show no rate, and no error, for a clinic and month with zero non-cancelled appointments. (source: FR-032)
- **FR-008**: The system MUST include every active clinic in the report, with no change needed when a clinic is added. (source: FR-032)
- **FR-009**: The system MUST offer the report only to the practice manager, refuse every other role and unsigned requests, and not show the menu entry to other roles. (source: FR-032)
- **FR-010**: The system MUST present the report on screen only, with no export, download or print-to-file function. (source: FR-032, REQ-028)
- **FR-011**: The system MUST hide the report screen and refuse the report request while the Release 2 feature switch for it is off. (source: FR-032)
- **FR-012**: The system MUST NOT write patient names, phone numbers or birth years into logs when producing the report; the report itself holds only counts. (source: FR-032, NFR-007)

### Key Entities *(include if feature involves data)*

- **Monthly no-show figure**: for one clinic and one IST month: the number of no-shows, the number of appointments that were not cancelled, and the rate. Derived, not stored.
- **Appointment**: owned by the booking capability; has a clinic, a start time and a status (booked, arrived, no-show, cancelled by the patient, cancelled by the clinic). The report only reads counts of appointments by clinic, month and status.
- **Clinic**: one of the clinics (2 now, a third later), identified by name.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a prepared set of appointments covering all five statuses, two clinics and 12 months, 100% of monthly counts and rates match a hand count.
- **SC-002**: The practice manager can open the report and read all clinics and all 12 months on one screen within 3 seconds for 95% of requests on an office desktop connection.
- **SC-003**: In role tests, 0 requests by receptionists, dentists, patients or unsigned users return figures.
- **SC-004**: With the feature switch off, 0 menu entries and 0 successful report requests are possible.
- **SC-005**: The practice manager can read a clinic's no-show rate for any of the last 12 months in at most 2 actions after signing in (open menu, open report).
- **SC-006**: After 2 months of app data the practice manager can read the baseline no-show rate per clinic (ASM-015), so that a target can be set.

## Assumptions

- Release 2 feature: ships about 2–3 weeks after go-live (target 2027-03-19, not hard). The screen is hidden by a feature switch until the data is ready.
- The report covers the 12 months ending with the current month, in IST; the current month is partial. (open question Q3)
- Walk-ins are normal appointments marked arrived or no-show (SA-004), so they are counted. Q-015 is still open (open question Q1).
- The no-show target is TBD and no baseline is known; the first 2 months of app data are the baseline (ASM-015, open question Q2). The report shows rates only; it does not compare them with a target.
- The report is on screen only; export is a non-goal.
- Depends on the appointment statuses of FR-024 (no-show marking, FR-022) and the clinics of FR-001, and on staff sign-in and roles (FR-003, FR-004).
- Targets the practice manager on a desktop browser (NFR-001); English text, times in IST (NFR-008).
- Appointments and history are kept 24 months and then anonymised, not deleted, so counts survive (ASM-012, RSK-007).
