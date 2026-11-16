# Data Model: Patient appointments (004)

No new table and no new column; at most one index on the appointment list query, added only if missing (task T051). This feature reads and updates entities owned elsewhere. Field names below follow architecture.md section 5; exact column names are those created by feature 003 (appointment) and feature 006 (message); tasks use the names found in those migrations.

## ent-appointment (owner cmp-booking, feature 003)

| Field | Use here |
|---|---|
| id (UUID) | identifies the appointment in the API and in the deep link |
| patient_id | person the visit is for; joined to the account for ownership |
| clinic_id | fixed on reschedule |
| dentist_id | may change on reschedule |
| treatment_type_id | fixed on reschedule |
| start_at, end_at (UTC) | change on reschedule; end_at = start_at + treatment duration |
| status | booked, arrived, no_show, cancelled_by_patient, cancelled_by_clinic (FR-024 of prd.md) |
| channel | SMS or WhatsApp, chosen at booking; used for the change message |
| booked_by | unchanged |

Constraints used: the exclusion constraint on (dentist, time range) for active statuses (booked, arrived) only; cancelled and no-show rows do not block the slot, so the freed slot is bookable on commit. Validation rules: `status` must be `booked` for cancel and reschedule; `start_at` must be at least 4 hours ahead (inclusive); new `start_at` must be a free slot of the same clinic and treatment, within the booking horizon.

State transitions by this feature:

- `booked` -> `cancelled_by_patient` (cancel)
- `booked` -> `booked` with new dentist and times (reschedule)

## ent-appointment-event (owner cmp-booking)

One row per change, in the same transaction.

| Field | Value |
|---|---|
| appointment_id | the appointment |
| from_status, to_status | `booked` -> `cancelled_by_patient`; `booked` -> `booked` for a reschedule |
| actor | the patient (person id and role `patient`) |
| at | time of change (UTC) |
| reason | `cancelled_by_patient`, or `rescheduled from <old start UTC> to <new start UTC>`; dentist ids are not written as names, so no personal data enters the history |

## ent-message (owner cmp-messaging)

| Field | Value |
|---|---|
| kind | `change` |
| template | `appointment_cancelled` or `appointment_rescheduled` (registered DLT / WhatsApp templates; ids in configuration) |
| channel | appointment channel |
| patient account, appointment | links |
| scheduled time | now (send at once) |
| status | `pending`, claimed by the dispatcher |

Reminder rows (kind `reminder`) of the appointment: cancelled on cancel; cancelled and recreated for the new time on reschedule (timing rules in feature 006).

## Read-only entities

- ent-clinic: name, phone (shown when changes are not allowed).
- ent-dentist: name. ent-treatment-type: name, duration, online flag.
- ent-patient: person name; ent-patient-account: ownership.

## Retention

Unchanged: appointments and history 24 months; messages 90 days.
