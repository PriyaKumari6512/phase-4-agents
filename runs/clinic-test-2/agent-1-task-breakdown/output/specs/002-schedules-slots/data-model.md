# Data Model: Dentist schedules, treatments and free slots

Owner: `cmp-scheduling` (ctr-clinic-api). Database: PostgreSQL 16. `clinic` and `dentist` tables come from feature 001 and are referenced only.

## treatment_type (ent-treatment-type)

| Field | Type | Constraint |
|---|---|---|
| id | bigint | primary key |
| name | text | not null, 1 to 80 characters, unique on `lower(name)` |
| duration_minutes | smallint | not null, one of 30, 60, 90 |
| online_bookable | boolean | not null, default false |
| active | boolean | not null, default true |
| created_at, updated_at | timestamptz | not null, UTC |

Rules: never deleted; switching off sets `active = false`. Changing duration or flag does not touch appointments (they store their own start and end).

Seed: Check-up (30, online), Cleaning (30, online), Consultation (30, online), Root canal (90, reception only), Extraction (60, reception only).

## working_hours (ent-working-hours)

| Field | Type | Constraint |
|---|---|---|
| id | bigint | primary key |
| dentist_id | bigint | not null, references dentist |
| clinic_id | bigint | not null, references clinic |
| weekday | smallint | not null, 1 (Monday) to 7 (Sunday) |
| start_time | time | not null, IST wall clock |
| end_time | time | not null, IST, greater than `start_time` |

Unique `(dentist_id, clinic_id, weekday)`. Index `(clinic_id, weekday)` and `(dentist_id, weekday)`.
Validation in the service: no overlap with the same dentist's hours at another clinic on the same weekday (half-open `[start, end)`).

## working_hours_break

| Field | Type | Constraint |
|---|---|---|
| id | bigint | primary key |
| working_hours_id | bigint | not null, references working_hours, on delete cascade |
| start_time | time | not null, IST |
| end_time | time | not null, greater than `start_time` |

Validation: break inside `[start_time, end_time]` of its working day; breaks of one day do not overlap.

## leave (ent-leave)

| Field | Type | Constraint |
|---|---|---|
| id | bigint | primary key |
| dentist_id | bigint | not null, references dentist |
| start_at | timestamptz | not null, UTC |
| end_at | timestamptz | not null, greater than `start_at` |
| whole_day | boolean | not null; true when entered as whole IST days (start 00:00 IST of first day, end 00:00 IST after last day) |
| note | text | null, up to 200 characters, no patient data |
| created_by | bigint | not null, staff account |
| created_at | timestamptz | not null |

Exclusion constraint: no two rows of one dentist overlap on `tstzrange(start_at, end_at)` (`btree_gist`). Index `(dentist_id, start_at, end_at)`. Retention: rows deleted 24 months after `end_at`.

## Computed (not stored)

- **FreeSlot**: `clinic_id`, `dentist_id`, `dentist_name`, `start_at` (UTC), `end_at` (UTC), `treatment_type_id`.
- **AppointmentToMove**: from the `AppointmentReader` interface: `appointment_id`, `clinic_id`, `dentist_id`, `start_at`, `end_at`, `treatment_name`, `patient_name`, `patient_phone`.

## Read from booking (not owned)

`appointment` (cmp-booking, ent-appointment) is read through `AppointmentReader` only. Its GiST exclusion constraint (ADR-0003) and its index on dentist and time are owned by feature 003.
