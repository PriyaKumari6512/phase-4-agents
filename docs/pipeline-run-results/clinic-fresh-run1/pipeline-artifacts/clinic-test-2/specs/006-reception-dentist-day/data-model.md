# Data Model: Reception day view, check-in, no-show and dentist day

Conceptual and for this feature only. The full tables are in the architecture's data model; entities are owned as in architecture.md section 5. This feature adds no table and no column; it adds one index if missing.

## Entities used

| Entity | Owner | Used for | Key fields used |
|---|---|---|---|
| ent-appointment | cmp-booking | Day view, dentist day, status changes, reception booking | id, clinic_id, dentist_id, patient_id, treatment_type_id, start_at (UTC), end_at (UTC), status, booked_by |
| ent-appointment-event | cmp-booking | History of every change | appointment_id, from_status, to_status, actor, at, reason |
| ent-patient | cmp-identity | Search, create, name shown in views | id, name (PII), account_id, active |
| ent-patient-account | cmp-identity | Phone lookup, create | id, phone (PII), name (PII) |
| ent-staff-account | cmp-identity | Clinic scoping and dentist link | id, role, clinic_id (receptionist), dentist_id (dentist), active |
| ent-clinic, ent-dentist, ent-treatment-type | cmp-scheduling | Columns, slot length, reception-only flag | id, name, duration minutes, online flag |
| ent-working-hours, ent-leave | cmp-scheduling | Which dentists have a column; free slots | dentist, clinic, weekday, start, end |

## Status values and transitions made by this feature

Status values (stored in ent-appointment, checked in the database): `booked`, `arrived`, `no-show`, `cancelled by the patient`, `cancelled by the clinic`.

```text
(new) --reception book--------------> booked
(new) --reception walk-in-----------> booked --(same transaction)--> arrived
booked --arrived (appointment day)--> arrived
booked --no-show (start+15 min .. end of that day)--> no-show
no-show --undo (same day)-----------> booked
booked --reception cancel, patient asked----> cancelled by the patient
booked --reception cancel, clinic's choice--> cancelled by the clinic
booked --reschedule (dentist and/or time change; status stays booked)
```

Not allowed here: any change from arrived, cancelled by the patient or cancelled by the clinic; no-show on a later day; undo of arrived (Q2).

## Validation rules

- Date for the day view: valid calendar date; the clinic comes from the staff account, not the request.
- Patient search `q`: trimmed, at least 3 characters, at most 64; matched on name and phone digits.
- New patient: name 1–100 characters after trimming (no digits-only), phone valid as in sign-in, unique per account.
- Booking: treatment type active; dentist works at the receptionist's clinic on that date; slot free for the whole duration (from cmp-scheduling); the database exclusion constraint is the final check.
- Cancel: `cancelled_by` is required and is `patient` or `clinic`.
- Every status endpoint requires `expected_status` and rejects when stored status differs.

## Event rows written

| Action | from → to | reason |
|---|---|---|
| Book | (none) → booked | booked by reception |
| Walk-in | (none) → booked, booked → arrived | walk-in |
| Arrived | booked → arrived | checked in |
| No-show | booked → no-show | no-show marked |
| Undo | no-show → booked | no-show undone |
| Cancel | booked → cancelled by the patient / the clinic | cancelled at reception |
| Reschedule | booked → booked | moved by reception (old and new dentist and time in the reason text, ids only, no patient data) |

Actor is the staff account id; time is the database time in UTC.

## Index

- `ix_appointment_clinic_start` on `ent-appointment (clinic_id, start_at)` if feature 004 has not already created an equivalent; supports the day view (QA-001-style tactic: index on dentist and time, plus clinic).

## Retention and privacy

No new data kept. Name and phone are shown on reception screens only; the dentist's response has no phone. Appointments and events follow the 24-month retention of ent-appointment (ASM-012). Logs carry ids only.
