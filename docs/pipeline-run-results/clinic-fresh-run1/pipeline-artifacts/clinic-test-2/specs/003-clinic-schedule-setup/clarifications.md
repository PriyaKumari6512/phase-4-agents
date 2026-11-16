# Clarifications: Clinics, dentist hours, leave, treatments and free slots

No user was available during the run. Each question below was answered with the most reasonable option; confirm with the client.

## Q1: Hours changes and appointments left outside the new hours

- **Context**: FR-007 says the manager sets weekly hours. FR-008 only requires a to-move list for leave. If hours shrink, existing appointments may fall outside them.
- **Options**:
  - A. Hours changes do nothing to existing appointments and create no list (only leave creates a list).
  - B. Hours changes also produce a to-move list of appointments left outside the new hours.
  - C. Refuse an hours change while appointments would fall outside it.
- **Assumed**: A.
- **Why**: The PRD ties the to-move list to leave only; B and C add scope not in the PRD. Reception sees the appointments in the day view anyway. Recorded as assumption A-5; revisit if the client wants B.

## Q2: Making a clinic, dentist or treatment type inactive while appointments exist

- **Context**: FR-001 and FR-009 keep these as data; the PRD does not say how they are retired.
- **Options**:
  - A. Mark inactive; existing appointments stay and are not listed for moving; no new bookings.
  - B. Mark inactive and list their future appointments for reception to move.
  - C. Refuse while future appointments exist.
- **Assumed**: A.
- **Why**: Simplest, loses no data, and a retiring dentist's leave can be recorded with FR-008 to produce a list if the clinic wants one.

## Q3: Reason or note on leave

- **Context**: FR-008 gives whole or part days; entity attributes in architecture.md are dentist, start, end, whole or part day.
- **Options**:
  - A. No reason or note stored.
  - B. Free-text note.
  - C. Fixed list of reasons (holiday, sick, training).
- **Assumed**: A.
- **Why**: Not in the PRD or architecture, and a free-text note could hold health information the privacy rules (NFR-007) say not to store.
