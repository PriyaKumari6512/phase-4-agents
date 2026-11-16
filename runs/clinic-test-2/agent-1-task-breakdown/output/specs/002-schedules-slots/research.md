# Research: Dentist schedules, treatments and free slots

## R1 Storing weekly hours and leave

- **Decision**: Weekly hours are recurring wall-clock IST values: `weekday` (1 = Monday … 7 = Sunday), `start_time`, `end_time` as `time`, breaks as `time` pairs. Leave is stored as `timestamptz` start and end in UTC (architecture: times stored UTC, shown IST). The engine converts each requested IST date to UTC instants when it builds the day's windows.
- **Rationale**: A recurring "Monday 09:00" has no date, so UTC makes no sense for it. India has one zone and no daylight saving, so IST wall time maps to a fixed UTC offset (+05:30). Leave and appointments are instants and stay UTC.
- **Alternatives**: all values in UTC (breaks readable only after conversion, every edit needs conversion: rejected); `timestamptz` with a template week (rejected, over-complex).

## R2 Slot calculation

- **Decision**: Per request: load the clinic's dentists' hours for the weekdays in the range (one query), leave overlapping the range for those dentists (one query), booked appointments of those dentists at any clinic in the range through the `AppointmentReader` (one call). The engine builds, per dentist and IST date, the working window at this clinic, subtracts break, leave and appointment intervals (as half-open `[start, end)`), and for each remaining free interval emits every start on the hour or half hour (rounded up to the next :00/:30) where `start + duration` fits inside the free interval. Slots in the past are dropped; for patients slots after `now + horizon` are dropped.
- **Rationale**: Interval subtraction on a day's few intervals is cheap in Python (about 20 ms for 10 dentists x 31 days), keeps SQL simple and avoids per-dentist queries (QA-001). Half-open intervals mean an appointment ending 10:30 does not block a slot starting 10:30.
- **Alternatives**: generate slot rows in advance (stale data, no immediate freeing: rejected, architecture says live); SQL-only with generate_series (harder to test: rejected).

## R3 Booked appointments from another module

- **Decision**: `ports.AppointmentReader` protocol in `app/scheduling/ports.py`:
  `list_active(dentist_ids, start_utc, end_utc, clinic_id=None) -> list[AppointmentBrief]` where `AppointmentBrief` has `id, clinic_id, dentist_id, start_utc, end_utc, treatment_name, patient_name, patient_phone`. "Active" means status booked. `cmp-booking` (features 003/005) implements it; this feature ships a `FakeAppointmentReader` for tests and a default reader that returns nothing until the booking module registers its own. The slot calculation uses only ids and times; patient fields are used by the "to move" list only.
- **Rationale**: Appointments are owned by `cmp-booking`; ADR-0003's exclusion constraint on appointments remains the final guard against double booking. A narrow protocol avoids a dependency on booking's tables.
- **Alternatives**: query the `appointment` table directly (breaks ownership: rejected).

## R4 Booking horizon and range limits

- **Decision**: `booking_horizon_days` (default 30) in `app/scheduling/settings.py`, read from application configuration; patient requests are clipped to `[now, end of (today + horizon)]` IST (1 March → up to 31 March). `max_range_days` is 31 per request.
- **Rationale**: ASM-010 says a setting; a configuration value is the simplest setting (Principle V) and needs no admin screen. Staff are not limited by the horizon because reception books with no cut-off (FR-020 in the PRD).
- **Alternatives**: a settings table with a manager screen (not asked for: rejected).

## R5 Treatment types seed and rules

- **Decision**: Alembic data migration seeds check-up, cleaning, consultation (30, online) and root canal (90), extraction (60) (reception only). Duration is validated to `{30, 60, 90}` (all slot grids are half hours). Names unique ignoring case (unique index on `lower(name)`). Types are switched off with `active = false`, never deleted, so history keeps the name.
- **Rationale**: PRD FR-009 lists these; 30-minute multiples keep durations aligned with the half-hour grid (FR-010).

## R6 Authorisation

- **Decision**: FastAPI dependencies from `cmp-identity` (feature 001): `require_role("manager")` on every write and on hours/leave reads; `require_authenticated` on treatment and slot reads with the clinic scope check for receptionists; patients get the online-only and horizon rules.
- **Rationale**: Constitution III and architecture section 9: authorisation is enforced server side in each module, not in the web app.

## R7 Leave retention

- **Decision**: A daily job `jobs/leave_retention.py` deletes leave whose `end_at` is older than 24 months, registered with the scheduled jobs of `ctr-clinic-api`.
- **Rationale**: Architecture ent-leave: kept 24 months.

## R8 Overlap rules

- **Decision**: Leave overlap of the same dentist is refused by a PostgreSQL exclusion constraint on `(dentist_id, tstzrange(start_at, end_at))` using `btree_gist` (already enabled for ADR-0003). Overlapping hours of one dentist across clinics on the same weekday are refused in the service in the same transaction (a constraint cannot compare across clinic rows with `time` ranges and different clinics unless using a generated range; the service check plus a unique key `(dentist_id, clinic_id, weekday)` is enough for a manager-only write path).
- **Rationale**: Simplicity; the manager screen is a low-concurrency write path.

## R9 Observability and privacy

- **Decision**: Structured logs with ids only; a histogram metric `scheduling_slots_seconds` per endpoint (OpenTelemetry); no patient fields in log records, including those of the "to move" list.
