# Research: Clinics, dentist hours, leave, treatments and free slots

All Technical Context items are resolved from architecture.md and the constitution; no NEEDS CLARIFICATION remains. Open business questions are in `clarifications.md`.

## R1. Where weekly hours live and how times are stored

- **Decision**: Weekly hours and breaks are stored as time-of-day values meant in IST (the clinics' local time, a fixed offset of +05:30 with no daylight saving). Leave and appointments are stored as UTC `timestamptz`. When slots are computed, each requested date is expanded to concrete instants by combining the date with the IST time of day, then converted to UTC.
- **Rationale**: A weekly pattern is a wall-clock idea ("09:00 on Mondays"); storing it as UTC would shift weekday boundaries. Architecture says times are stored in UTC and shown in IST; this keeps instants (leave, appointments, slots) in UTC and applies IST only where the rule is itself local.
- **Alternatives considered**: Storing hours as UTC offsets from midnight (confusing, breaks around the day boundary); a timezone per clinic (not needed, all clinics are in Bengaluru, and not in the PRD).

## R2. Free-slot algorithm

- **Decision**: For one clinic and a date range of at most 31 days, for each date and each active dentist who has hours at that clinic on that weekday: (1) build the working window(s) from hours; (2) subtract breaks; (3) subtract leave overlapping the date; (4) subtract the dentist's non-cancelled appointments from the appointments port, at any clinic; (5) walk the free intervals and emit every start on the :00 or :30 grid where `[start, start + duration)` lies fully inside one free interval; (6) drop starts before now and, for patients, after the end of the horizon. Pure interval functions live in `slot_math.py` and are unit-tested without a database.
- **Rationale**: Simple, deterministic, easy to test, and fast at this size: at most 10 dentists times 31 days. Data is fetched with one query per source for the whole range (hours for the clinic's dentists, leave for those dentists in the range, appointments for those dentists in the range), not per day.
- **Alternatives considered**: Precomputed slot rows (stale data and cache invalidation problems on every booking, and architecture says no cache); computing in SQL only (harder to test, harder to read).

## R3. "First available" (top 10, paginated)

- **Decision**: Walk dates forward from today in small windows (for example 7 days at a time, within the 31-day range per call and the horizon for patients), merge the dentists' slots in time order (tie-break by dentist id), and stop as soon as `(page + 1) * 10` slots exist. Return `page`, `page_size = 10`, the slots of the page and `has_more`. Page numbers start at 1.
- **Rationale**: Stops early, so the common request touches a few days of data. Matches architecture ("first available (top 10, paginated)").
- **Alternatives considered**: Computing the whole horizon then slicing (wasteful); cursor tokens (more moving parts than the use needs).

## R4. Appointments port

- **Decision**: `AppointmentsPort` in `ports.py`, a Python protocol with two methods: `busy_intervals(dentist_ids, start, end)` returning non-cancelled appointments' dentist id, clinic id, start, end, and `booked_overlapping(dentist_id, start, end, clinic_id=None)` returning booked appointments with id, clinic, dentist, start, end, treatment name, patient name and phone for the to-move list. cmp-booking (feature 004 onward) registers its implementation at startup. Until then `EmptyAppointments` returns nothing.
- **Rationale**: Architecture says the free-slot calculation and to-move list read booked appointments from cmp-booking in-process; the appointments table is owned by cmp-booking, so cmp-scheduling must not query it directly. The port keeps module boundaries and lets this feature be built and tested first.
- **Alternatives considered**: Direct SQL on the appointments table (breaks ownership); duplicating appointment data into scheduling (consistency problems).
- **Dependency note**: cmp-booking must index appointments on dentist and time (architecture section 10) and expose these two methods; tracked as a dependency of this feature, and a contract test for the port is included here so cmp-booking can reuse it.

## R5. Access control

- **Decision**: Use cmp-identity's access context (feature 002) through a thin adapter `access.py` with two checks: `require_manager` and `require_manager_or_own_clinic_reception(clinic_id)`. Read routes for clinics, dentists and treatments need any signed-in role; patients get only active records and only online treatment types. Slot routes accept patient, receptionist (own clinic) and manager. Dentist role may read hours and clinics. Server-side only; ids in the request are never trusted for scope (thr-004, thr-007).
- **Rationale**: Architecture section 9 puts clinic scoping in each module through the access context. The adapter isolates this feature from the exact names in feature 002.
- **Alternatives considered**: Role checks in the web app only (rejected by architecture).

## R6. Weekly hours editing and validation

- **Decision**: One operation replaces a dentist's whole week at one clinic (`PUT`), validated as a unit: each weekday at most one working window, start before end, breaks inside the window and not overlapping, and no overlap with the same dentist's hours at another clinic on the same weekday. Replace is done in one transaction. Hours on the same weekday at two clinics must be disjoint windows (for example 09:00–13:00 and 14:00–18:00).
- **Rationale**: Matches the screen (edit a week, press save), avoids partial states, and enforces "a dentist can't be at two clinics at once" without a database constraint (simplicity).
- **Alternatives considered**: Row-by-row create/update routes (more calls, partial invalid states); an exclusion constraint across tables (not expressible simply).

## R7. Leave model and to-move selection

- **Decision**: Leave is stored as `[start_at, end_at)` in UTC with a `whole_day` flag. Whole days from first day D1 to last day D2 become 00:00 IST on D1 to 00:00 IST on D2 plus 1 day. Leave applies to the dentist at every clinic. The to-move list is computed live: booked appointments of the dentist that overlap any of that dentist's leave and start in the future, for the clinic asked about. On leave create, the response includes the list across all clinics (manager only).
- **Rationale**: Live computation means a moved or cancelled appointment leaves the list with no extra state (SC-007). Overlap uses the half-open rule `appt.start < leave.end and appt.end > leave.start`.
- **Alternatives considered**: A stored to-move table with states (needs sync when appointments change in another module).

## R8. Retention

- **Decision**: A scheduled job inside the API process deletes leave rows whose `end_at` is more than 24 months ago, daily. Test with a time-controlled unit test.
- **Rationale**: architecture ent-leave retention is 24 months; the dispatcher and jobs already run in the API process (ADR-0002, section 13).
- **Alternatives considered**: A database-level job (managed service specifics unknown); manual cleanup (error-prone).

## R9. Booking horizon setting

- **Decision**: One row in a `scheduling_setting` table (`key = 'booking_horizon_days'`, value 30). Slots for patients are limited to `[now, end of (today + horizon days) in IST]`. No screen to edit it in this feature (assumption A-9).
- **Rationale**: ASM-010 says "the horizon is a setting". A settings row is data, not code, with minimal surface.
- **Alternatives considered**: An environment variable (needs a deploy to change); a constant (violates the setting rule).

## R10. Performance approach

- **Decision**: Indexes on `working_hours (dentist_id, clinic_id, weekday)`, `leave (dentist_id, start_at, end_at)`; cmp-booking provides the dentist and time index on appointments. One query per source per request. A performance test seeds 3 clinics, 10 dentists and 1,000 appointments a week and runs 100 concurrent virtual users against the slots routes, asserting server p95 ≤ 500 ms. A duration histogram is emitted per slot request.
- **Rationale**: Matches architecture section 10 (QA-001), and the capacity estimate of 3 to 6 indexed queries per request.
- **Alternatives considered**: Caching (explicitly not used in the architecture).

## R11. Front-end screens

- **Decision**: Five pages in one feature folder: Clinics (clinic and dentist lists with add, edit, active toggle), Dentists and hours (pick dentist and clinic, weekly editor with break rows), Leave (list, add whole-day or part-day, delete, result shows the to-move list), Treatments (table with edit), To move (reception and manager, by clinic). Times are entered and shown in IST using helpers in `time.ts`. All text in English (NFR-008). Desktop browser is the target for these screens.
- **Rationale**: The PRD lists screens "dentists and hours, leave, treatments"; adding clinics is required for QA-011 (a third clinic as data), so a Clinics page is included; the to-move list is read by reception.
- **Alternatives considered**: Hiding clinics management behind a database script (violates QA-011: "done in the staff screens").
