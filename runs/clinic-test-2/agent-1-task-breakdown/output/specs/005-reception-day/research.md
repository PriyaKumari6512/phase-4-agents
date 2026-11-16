# Research: Reception day view, check-in, no-shows and dentist day

All technology is fixed by architecture.md; this file records the design decisions inside it. No NEEDS CLARIFICATION is left; the two product questions are in clarifications.md.

## D1: Status rules in cmp-booking, called by cmp-reception

- **Decision**: One module `booking/status_rules.py` holds the statuses and the allowed transitions; `booking/status_service.py` is the only code that changes an appointment's status. `cmp-reception` calls it (architecture: "cmp-reception -> cmp-booking: changes status, in-process").
- **Rationale**: FR-024 needs the history write on every change, including the online cancel of feature 004. One entry point makes the "who and when" guarantee testable once.
- **Alternatives**: status updates directly in reception routes (rejected: history could be skipped); a status-event bus (rejected: architecture says no event sourcing, history is an audit log).

## D2: Concurrency by conditional update

- **Decision**: A change runs `UPDATE appointment SET status = :to WHERE id = :id AND status = :expected_from` and inserts the history row in the same transaction. Zero rows updated means someone else changed it: respond 409 with the current status.
- **Rationale**: Two receptionists on one clinic's day is realistic; the conditional update needs no new column or lock (Simplicity).
- **Alternatives**: a version column (rejected: a migration and a field for the same effect); `SELECT ... FOR UPDATE` (rejected: longer transaction for no gain).

## D3: No-show window and "end of that day" in IST

- **Decision**: Times are stored in UTC. The rule uses `Asia/Kolkata`: no-show allowed when `now >= start + 15 min` and `now < start of next IST day after the appointment's IST date`. Undo (no-show or arrived to booked) allowed while `now` is on the appointment's IST date. The clock is injected so tests can set it.
- **Rationale**: PD-003, NFR-008; India has no daylight saving, so fixed offset +05:30 is safe, but the named zone keeps intent clear.
- **Alternatives**: client-side check only (rejected: server must enforce, thr-004).

## D4: Day view as one read query

- **Decision**: One query joins working-hours dentists of the clinic for the date (from cmp-scheduling's interface), appointments of that clinic and date, patients and treatment types; the response groups by dentist. Cancelled appointments are included with their status so reception sees what changed.
- **Rationale**: Payload about 15 KB for 6 columns (architecture capacity estimate); live queries meet QA-001, no cache.
- **Alternatives**: one request per dentist (rejected: 6 round trips on the desk PC); cache (rejected: architecture says none).

## D5: Patient search across clinics (ASM-011)

- **Decision**: `cmp-identity` offers `search_patients(q)` and `create_patient(name, phone)`. A query of 4 or more digits matches the phone number after normalising to +91 form (suffix match); a query with at least 2 letters matches name by case-insensitive contains. Results hold id, name, phone only and are capped at 20. A reception-created patient is an account holder (account plus person, ADR-0008) with the phone number as account key, so the person can later sign in with the same number and see the appointment.
- **Rationale**: Patients are not tied to a clinic; the volume (a few thousand people) needs no special index. Returning only id, name and phone keeps cross-clinic exposure minimal (NFR-006).
- **Alternatives**: trigram index (rejected: not named in the architecture, not needed at this size); a reception-only patient table (rejected: duplicates ent-patient and breaks later sign-in).

## D6: Reception booking, move and cancel

- **Decision**: `booking/reception_service.py` creates appointments through the same insert as online booking (so the exclusion constraint, ADR-0003, decides races) but skips the 4-hour rule, the 30-day horizon and the no-show block check, and allows any active treatment type. A walk-in inserts with status arrived and a history row (from none to arrived, reason "walk-in"). Move updates dentist and time of the same appointment in one transaction (history row with reason "moved"). Cancel takes `asked_by: patient|clinic` and sets the matching cancelled status (ASM-014). On a slot conflict the API answers 409 with the next free slots (same shape as online booking). An idempotency key on create prevents a retried request booking twice (QA-003 tactic).
- **Rationale**: One insert path, one constraint. A move that changes the time keeps the appointment id so history stays whole.
- **Alternatives**: cancel-and-create for move (rejected: loses history, resets reminders needlessly); reception-specific constraint (rejected: ADR-0003 says one).

## D7: Free slots for reception

- **Decision**: Ask `cmp-scheduling` for slots with an audience flag "reception": all active treatment types, no 30-day limit, and today's slots that have already started stay selectable (walk-in). Past days are not selectable. This is a small change in feature 002's slots module, listed as a dependency task.
- **Rationale**: FR-020 and SA-004; reuse of the same free-slot calculation avoids a second definition of "free".
- **Alternatives**: a reception-only slot query (rejected: two definitions of free).

## D8: Messages after reception changes

- **Decision**: After the transaction commits, `reception_service` calls the messaging interface of feature 006 (`notify_confirmation`, `notify_change`). Failures are logged with ids and do not undo the booking. Until feature 006 merges, a no-op port with the same signature is used.
- **Rationale**: Architecture says confirmation is sent after commit, not in the request (QA-002 tactic).

## D9: Roles and scoping

- **Decision**: `reception/access.py` wraps the access context of cmp-identity: `require_receptionist()` returns the clinic id from the database (not from the request); `require_dentist()` returns the dentist id. Every appointment lookup is filtered by that clinic id; an appointment of another clinic answers 404 (no existence leak), a wrong role answers 403.
- **Rationale**: thr-004, thr-007, QA-007.

## D10: Screens

- **Decision**: ctr-web adds `DayViewPage` (landing for receptionists), `AppointmentPanel` (side panel with actions and history), `BookForPatient` (with `PatientSearch`), and `MyDayPage` (landing for dentists, mobile-first, no action buttons). Reception screens are desktop-first; MyDayPage works on a phone without sideways scrolling.
