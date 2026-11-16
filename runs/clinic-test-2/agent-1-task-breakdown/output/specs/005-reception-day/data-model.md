# Data Model: Reception day view, check-in, no-shows and dentist day

No new tables. This feature reads and writes tables owned by other components and adds one Alembic migration only if the existing check on status values lacks a value (see Status values). Entities use the architecture's ids.

## ent-appointment (owner cmp-booking, created by feature 003)

Fields used: `id`, `clinic_id`, `dentist_id`, `patient_id`, `treatment_type_id`, `start_at` (UTC), `end_at` (UTC), `status`, `channel`, `booked_by` (patient account or staff account id).

### Status values

`booked`, `arrived`, `no_show`, `cancelled_by_patient`, `cancelled_by_clinic`. The database holds a check on these values (thr-011). If feature 003 created fewer values, this feature's migration extends the check.

### State transitions (enforced in `booking/status_rules.py`)

| From | To | Who | Condition |
|---|---|---|---|
| (new) | booked | receptionist | free slot, no overlap |
| (new) | arrived | receptionist | walk-in booking, free slot, no overlap |
| booked | arrived | receptionist of the clinic | appointment of own clinic |
| booked | no_show | receptionist of the clinic | now >= start + 15 min and now before the end of the appointment's IST day |
| no_show | booked | receptionist of the clinic | same IST day as the appointment (undo) |
| arrived | booked | receptionist of the clinic | same IST day as the appointment (Q2 assumed) |
| booked | cancelled_by_patient | receptionist | patient asked |
| booked | cancelled_by_clinic | receptionist | clinic cancelled |
| cancelled_* | any | nobody | final |

Every other change is refused with 409 (rule) or 403 (role).

### Overlap rule

The exclusion constraint of ADR-0003 on (`dentist_id`, time range) stays the single arbiter. A move that changes dentist or time is an UPDATE that the same constraint checks. Statuses covered by the constraint are those of feature 003 (active ones: booked, arrived, no_show); cancelled rows do not block a slot.

## ent-appointment-event (owner cmp-booking, created by feature 003)

Fields: `id`, `appointment_id`, `from_status` (null for a new appointment), `to_status`, `actor_type` (staff or patient), `actor_id`, `occurred_at` (UTC), `reason` (text, at most 200 characters, no patient name or phone).

Written by this feature for: reception booking (reason `booked by reception`), walk-in (`walk-in`), move (`moved`; from and to status equal), arrived, no-show, undo (`undo no-show`, `undo arrived`), cancel (`patient asked` or `clinic cancelled`). A row and its status change commit in one transaction (FR-024). Rows are never updated or deleted by this feature.

## ent-patient-account and ent-patient (owner cmp-identity)

Used for search and create only. Created by reception: one account (phone number in +91 form, name) and one person (the account holder). `phone` is unique per account (feature 001), so a duplicate create returns the existing patient. Search returns `id`, `name`, `phone` only.

Validation: name 2 to 100 characters, not blank; phone a valid Indian mobile number (10 digits starting 6 to 9, with or without +91 or spaces), stored normalised.

## Read models (no storage)

- **DayView**: `date`, `clinic_id`, `columns[]` (`dentist_id`, `dentist_name`, `working_from`, `working_to`, `appointments[]`), each appointment: `id`, `start_at`, `end_at`, `patient_id`, `patient_name`, `patient_phone`, `treatment_name`, `status`.
- **DentistDay**: `date`, `clinics[]` (`clinic_id`, `clinic_name`, `appointments[]` with `id`, `start_at`, `end_at`, `patient_name`, `treatment_name`, `status`). No phone number.

## Indexes

Uses the dentist-and-time index of feature 003 for day queries and the clinic and start index for the day view. No new index is planned; if the query plan for the day view needs `(clinic_id, start_at)`, the migration in task T007 adds it.
