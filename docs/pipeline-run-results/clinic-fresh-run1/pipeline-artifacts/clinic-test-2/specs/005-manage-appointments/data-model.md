# Data Model: Patient appointment list, reschedule, cancel and status history

Times are stored in UTC (`timestamptz`) and shown in IST. Owner of both tables: `cmp-booking`.

## appointment (ent-appointment) — existing, extended

Created by the online booking feature. This feature relies on these columns and adds the status check if missing.

| Column | Type | Notes |
|---|---|---|
| id | uuid, PK | |
| clinic_id | uuid | not changed by a reschedule (same clinic) |
| dentist_id | uuid | may change on reschedule |
| patient_id | uuid | person the visit is for; person belongs to a patient account |
| treatment_type_id | uuid | not changed by a reschedule |
| starts_at, ends_at | timestamptz | UTC; changed by reschedule |
| time_range | tstzrange | exclusion constraint with `dentist_id` for active statuses (ADR-0003) |
| status | text | CHECK in (`booked`, `arrived`, `no_show`, `cancelled_by_patient`, `cancelled_by_clinic`) |
| channel | text | `sms` or `whatsapp`; used for the change message |
| booked_by | text/uuid | who booked |

Validation: cancel and reschedule by a patient only when `status = 'booked'` and `starts_at - now >= 4 hours`. The no-overlap exclusion constraint (ADR-0003) is defined by the online booking feature and covers active appointments; this feature relies on a cancelled appointment no longer counting as active, so its slot is free at once. Which statuses count as active beyond `booked` is decided there (open question for that feature, not here).

## appointment_event (ent-appointment-event) — new

| Column | Type | Notes |
|---|---|---|
| id | uuid, PK | |
| appointment_id | uuid, FK -> appointment(id) | same retention as appointment (24 months) |
| from_status | text, NOT NULL | CHECK same five values |
| to_status | text, NOT NULL | CHECK same five values |
| actor_kind | text, NOT NULL | CHECK in (`patient`, `staff`, `system`) |
| actor_id | uuid, NOT NULL | patient account id or staff account id |
| occurred_at | timestamptz, NOT NULL | default `now()` UTC |
| reason | text, NOT NULL | for example `patient_request`, `patient_reschedule`, `reception_cancel_patient_asked`, `reception_cancel_clinic` |
| from_starts_at, to_starts_at | timestamptz, NULL | filled for a reschedule (old and new time) |
| from_dentist_id, to_dentist_id | uuid, NULL | filled for a reschedule |
| idempotency_key | text, NULL | unique with appointment_id when not null |

Indexes: `(appointment_id, occurred_at)`; unique `(appointment_id, idempotency_key)` where key is not null.

Rules:
- Rows are only inserted, never updated or deleted by the application; the application database user has no UPDATE or DELETE right on this table (thr-006, thr-011).
- The 24-month retention job removes event rows with its appointment's personal link, using a separate maintenance database role (the application role cannot delete).
- A reschedule writes one row with `from_status = to_status = 'booked'` and the old/new time and dentist.
- An event row and its appointment change are one transaction.

## State transitions (status)

```text
booked  -> cancelled_by_patient   (patient online until 4 h; reception any time when the patient asked)
booked  -> cancelled_by_clinic    (reception, clinic's own decision)
booked  -> arrived                (reception, feature 006)
booked  -> no_show                (reception, feature 006)
no_show -> booked / arrived       (undo the same day, feature 006)
booked  -> booked                 (reschedule; a history row with old/new time)
```

Cancelled statuses are final for the patient. This feature implements the first two, the reschedule, and the shared status function that feature 006 uses for the rest.

## Patient list view (read model, no table)

Selected by account: appointment -> person -> patient account = token owner. Fields returned: appointment id, person name and id, clinic name and phone, dentist name, treatment name, start and end (ISO, UTC with offset; the web app formats IST), status, `can_change` and `can_cancel` flags (server computed from the same rules as cancel), `change_blocked_reason` (`too_late`, `not_booked`, `blocked`, or null).
