# Data Model: Repeat no-show block and no-show report

Conceptual to table level for the one new table. Other entities are owned by earlier features and only read here.

## ent-no-show-block (new, owned by cmp-noshow-policy)

Table `no_show_block`:

| Field | Type | Rules |
|---|---|---|
| id | uuid | primary key |
| patient_id | uuid | the person (`ent-patient`), not the account (PD-007); required |
| blocked_at | timestamp with time zone (UTC) | when the person reached 2 counted no-shows |
| lifted_by | uuid, nullable | staff account of the receptionist who lifted; set together with `lifted_at` |
| lifted_at | timestamp with time zone, nullable | when lifted; null while the block is open |

- Check: `lifted_by` and `lifted_at` are both null or both set.
- Unique partial index: at most one open row (where `lifted_at` is null) per `patient_id`.
- Index on `(patient_id, lifted_at)` for finding the last lift.
- Retention: 24 months, then removed by the existing retention job (ASM-012). Deletion on request removes the personal link; the row holds only ids.

### Lifecycle

```
(none) --second counted no-show marked--> open (lifted_at null)
open   --receptionist lifts------------> lifted (lifted_by, lifted_at set)   [count restarts from zero]
open   --no-show undone same day, count under 2--> (row removed)            [no lift record]
open   --no-shows age out of 6 months--> stays open but does not block (live count under 2); blocked_at is reset at the next transition into 2
```

## Read-only inputs

- **Appointment** (`ent-appointment`, cmp-booking): `patient_id`, `clinic_id`, `start_at`, `status` (booked, arrived, no-show, cancelled by the patient, cancelled by the clinic).
- **Appointment history** (`ent-appointment-event`, cmp-booking): `appointment_id`, `to_status`, `actor`, `at`. The time of the latest change to no-show is the "marked at" time used after a lift (Q2).
- **Clinic** (`ent-clinic`, cmp-scheduling): `id`, `name`, `phone`, `active`.

## Derived values (not stored)

- **Counted no-shows for a person**: appointments with current status no-show, `start_at` within the last 6 months, and marked-at after the person's latest `lifted_at`.
- **Blocked**: counted no-shows is 2 or more (and the release flag is on).
- **Report row**: for a clinic and an IST calendar month of `start_at`: `no_shows` = appointments with status no-show; `not_cancelled` = appointments whose status is not cancelled by the patient and not cancelled by the clinic (walk-ins included); `rate` = `no_shows` / `not_cancelled`, empty when `not_cancelled` is 0.

## Validation rules

- Only a receptionist may set `lifted_by` / `lifted_at`; the value comes from the signed-in staff account.
- A lift on a person with no open and effective block is refused (HTTP 409).
- The report reads no patient columns, so anonymising a patient does not change any report figure.
