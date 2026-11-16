# Data Model: No-show report per clinic and month

No new table, column or migration. The report is derived at request time from `ent-appointment` (owner: `cmp-booking`, store: ctr-db) and the clinic list (owner: `cmp-scheduling`).

## Read inputs

| Entity | Fields used | Rule |
|---|---|---|
| ent-appointment | clinic id, start time (UTC), status | Status is one of booked, arrived, no_show, cancelled_by_patient, cancelled_by_clinic. Anonymised rows keep these three fields. |
| ent-clinic | id, name, active | Every clinic that is active, or had appointments in the window, is reported. |

## Derived: Monthly no-show figure (not stored)

| Field | Type | Rule |
|---|---|---|
| month | text `YYYY-MM` | IST month of the appointment start time |
| no_shows | integer ≥ 0 | count of status `no_show` |
| non_cancelled | integer ≥ 0 | count of status booked, arrived, no_show (cancelled by patient and by clinic excluded) |
| rate | number or null | `no_shows ÷ non_cancelled × 100`, one decimal, half up; null when `non_cancelled` is 0 |
| partial | boolean | true only for the current IST month |

## Derived: Clinic report

| Field | Type | Rule |
|---|---|---|
| clinic_id | identifier | from ent-clinic |
| clinic_name | text | from ent-clinic |
| months | list of 12 monthly figures | newest first; months without appointments are filled with 0, 0, null |

## Window

Current IST month and the 11 months before it. Start of window = first day of the month 11 months back at 00:00 IST; end = start of next month after the current month at 00:00 IST (exclusive).
