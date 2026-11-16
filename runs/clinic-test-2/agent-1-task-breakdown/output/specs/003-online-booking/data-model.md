# Data Model: Online booking by patients (003)

Owner: cmp-booking in ctr-clinic-api. Database: ctr-db (PostgreSQL 16, extension `btree_gist`). Times are `timestamptz` stored in UTC, shown in IST. Migration: `alembic/versions/0003_online_booking.py` (forward-only, expand style).

## appointment (ent-appointment)

| Column | Type | Rules |
|---|---|---|
| id | uuid | primary key |
| clinic_id | uuid | not null, foreign key to clinic |
| dentist_id | uuid | not null, foreign key to dentist; the dentist must work at the clinic |
| patient_id | uuid | not null, foreign key to patient (the person); personal link removed after 24 months (ASM-012) |
| treatment_type_id | uuid | not null, foreign key to treatment type |
| start_at | timestamptz | not null; on the hour or half hour; in the future when booked online |
| end_at | timestamptz | not null; `end_at > start_at`; start plus the treatment duration (30 minutes for online types) |
| status | text | not null; one of `booked`, `arrived`, `no_show`, `cancelled_by_patient`, `cancelled_by_clinic`; check constraint; starts as `booked` |
| channel | text | not null; one of `sms`, `whatsapp` |
| booked_by_user_id | uuid | not null; the signed-in user who made the booking |
| booked_by_role | text | not null; `patient` here (later `receptionist`) |
| created_at | timestamptz | not null, default now |
| updated_at | timestamptz | not null, default now |

Constraints and indexes:

- Exclusion constraint `appointment_no_overlap`: `EXCLUDE USING gist (dentist_id WITH =, tstzrange(start_at, end_at, '[)') WITH &&) WHERE (status NOT IN ('cancelled_by_patient', 'cancelled_by_clinic'))` (ADR-0003). It also serves as the index on dentist and time (QA-001).
- Index `appointment_patient_start_idx` on (patient_id, start_at) for later patient lists.
- Index `appointment_clinic_start_idx` on (clinic_id, start_at) for later day views.

## appointment_event (ent-appointment-event)

| Column | Type | Rules |
|---|---|---|
| id | uuid | primary key |
| appointment_id | uuid | not null, foreign key to appointment |
| from_status | text | null for the first entry |
| to_status | text | not null; same value list as appointment.status |
| actor_user_id | uuid | not null; who made the change |
| actor_role | text | not null |
| at | timestamptz | not null, default now |
| reason | text | null; at most 200 characters |

This feature writes the first entry (`from_status` null, `to_status` `booked`) in the booking transaction. Feature 005 writes later entries. Index on (appointment_id, at).

## booking_request (supporting table of cmp-booking, retry keys)

| Column | Type | Rules |
|---|---|---|
| patient_account_id | uuid | not null |
| idempotency_key | uuid | not null; primary key together with patient_account_id |
| request_fingerprint | text | not null; hash of clinic, dentist, treatment, start, channel, person |
| outcome | text | not null; `booked` or `slot_taken` |
| appointment_id | uuid | null; set when outcome is `booked`; foreign key to appointment |
| created_at | timestamptz | not null, default now |

Rows older than 24 hours are removed by the existing retention job (no personal data stored). The table is internal to cmp-booking; no other component reads it.

## Booking setting

`booking_horizon_days`: integer, default 30, minimum 1, maximum 90; application configuration read at start (ASM-010). Not a table.

## State transitions in this feature

`(none)` to `booked`. All other transitions belong to features MOD-04 (patient cancel and reschedule) and 005 (reception).

## Records written by one booking (one transaction)

1. `booking_request` row (key, fingerprint, outcome `booked`, appointment id).
2. `appointment` row, status `booked`.
3. `appointment_event` row, to_status `booked`.
4. Message rows (confirmation, reminder) through the `BookingMessages` port.
