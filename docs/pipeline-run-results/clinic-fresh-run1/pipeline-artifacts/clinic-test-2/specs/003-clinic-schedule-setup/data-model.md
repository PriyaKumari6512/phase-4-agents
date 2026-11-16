# Data Model: Clinics, dentist hours, leave, treatments and free slots

Owner: cmp-scheduling. Database: PostgreSQL 16 (ctr-db). Migration: one Alembic revision in clinic-api, forward-only (expand style).

## clinic (ent-clinic)

| Column | Type | Rules |
|---|---|---|
| id | uuid, primary key | |
| name | text, not null | unique among active clinics (case-insensitive) |
| address | text, not null | |
| phone | text, not null | |
| active | boolean, not null, default true | inactive clinics are not offered for new bookings |
| created_at, updated_at | timestamptz | |

## dentist (ent-dentist)

| Column | Type | Rules |
|---|---|---|
| id | uuid, primary key | |
| name | text, not null | PII: never logged |
| active | boolean, not null, default true | |
| created_at, updated_at | timestamptz | |

The link from a staff account to a dentist belongs to cmp-identity (feature 002).

## treatment_type (ent-treatment-type)

| Column | Type | Rules |
|---|---|---|
| id | uuid, primary key | |
| name | text, not null | unique among active types (case-insensitive) |
| duration_minutes | integer, not null | greater than 0 and a multiple of 30 (check constraint) |
| online | boolean, not null | patients may book it online |
| active | boolean, not null, default true | |
| created_at, updated_at | timestamptz | |

Initial rows (migration data): check-up, cleaning, consultation, each 30 minutes, online, active.

## working_hours (ent-working-hours)

| Column | Type | Rules |
|---|---|---|
| id | uuid, primary key | |
| dentist_id | uuid, foreign key to dentist, not null | |
| clinic_id | uuid, foreign key to clinic, not null | |
| weekday | smallint, not null | 0 = Monday to 6 = Sunday; check 0 to 6 |
| start_time | time, not null | IST wall clock |
| end_time | time, not null | greater than start_time (check constraint) |

- Unique `(dentist_id, clinic_id, weekday)`: one working window per weekday at a clinic.
- Index `(dentist_id, clinic_id, weekday)` (the unique index) and `(clinic_id, weekday)` for "who works here today".
- Cross-clinic rule (service level): for one dentist and weekday, windows at different clinics must not overlap.

## working_break (breaks of ent-working-hours)

| Column | Type | Rules |
|---|---|---|
| id | uuid, primary key | |
| working_hours_id | uuid, foreign key to working_hours, on delete cascade, not null | |
| start_time | time, not null | |
| end_time | time, not null | greater than start_time; inside the window; non-overlapping (service level) |

## leave (ent-leave)

| Column | Type | Rules |
|---|---|---|
| id | uuid, primary key | |
| dentist_id | uuid, foreign key to dentist, not null | applies to every clinic |
| start_at | timestamptz, not null | UTC |
| end_at | timestamptz, not null | greater than start_at (check constraint); not in the past when created |
| whole_day | boolean, not null | whole days are 00:00 IST of the first day to 00:00 IST of the day after the last day |
| created_by | uuid, not null | the manager's staff account id (from the access context) |
| created_at | timestamptz | |

- Index `(dentist_id, start_at, end_at)`.
- Retention: removed 24 months after `end_at` (daily job).
- No reason or note column (Q3).

## scheduling_setting

| Column | Type | Rules |
|---|---|---|
| key | text, primary key | `booking_horizon_days` |
| value | integer, not null | 30 by default; at least 1 |

## Text length limits (API validation)

Design limits, not PRD facts: clinic name at most 120 characters, address at most 300, phone at most 20; dentist name at most 120; treatment type name at most 120. All text trimmed and not empty.

## Calculated, not stored

- **Free slot**: `{clinic_id, dentist_id, start_at, end_at}` in UTC, for one treatment length.
- **To-move item**: `{appointment_id, clinic_id, dentist_id, dentist_name, start_at, end_at, treatment_name, patient_name, patient_phone, leave_id}` from the appointments port.

## Relationships

- dentist 1..n working_hours; clinic 1..n working_hours; working_hours 0..n working_break.
- dentist 1..n leave.
- A dentist "works at" a clinic when at least one working_hours row exists for the pair.
- Appointments (owned by cmp-booking) reference clinic, dentist and treatment type by id; this feature never writes them.

## State transitions

- clinic, dentist, treatment_type: active to inactive and back by the practice manager; never deleted.
- leave: created, then optionally deleted (mistake) or removed by retention.
