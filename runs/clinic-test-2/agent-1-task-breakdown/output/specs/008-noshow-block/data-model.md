# Data Model: Repeat no-show block

Owner: `cmp-noshow-policy` (ctr-clinic-api), stored in `ctr-db` (PostgreSQL 16). Source: FR-025, FR-026, PD-007.

## ent-no-show-block (table `no_show_block`)

| Field | Type | Notes |
|---|---|---|
| id | uuid, primary key | |
| patient_id | reference to `ent-patient` (a person) | Not the account: the block is per person (PD-007) |
| blocked_at | timestamp with time zone (UTC) | When the count reached 2 |
| lifted_at | timestamp with time zone, null | Null means the block is open |
| lifted_by_staff_id | reference to `ent-staff-account`, null | Set when a receptionist lifts; null on a system close (count fell below 2) |

Rules:
- At most one open block (`lifted_at` is null) per patient: partial unique index on `patient_id` where `lifted_at` is null.
- A reception lift sets `lifted_at` and `lifted_by_staff_id` in one conditional update (`where lifted_at is null`); only this resets the count.
- A system close sets `lifted_at` with `lifted_by_staff_id` null; it does not reset the count.
- Index on (`patient_id`, `lifted_at`).
- Retention 24 months from `blocked_at`, then deleted (retention job of `cmp-identity` / ASM-012 covers the table); erasure on request removes the person's rows (NFR-007).
- No PII stored in this table; only ids and times.

## Derived: counted no-shows for a person

Not stored. Appointments (owned by `cmp-booking`) where:
- `patient_id` = the person,
- `status` = no-show,
- `start` >= now minus 6 months,
- the time of the latest change to no-show in `ent-appointment-event` > `lifted_at` of the person's latest reception lift (if any).

Blocked = an open block exists AND counted no-shows >= 2.

## State transitions

```text
(no row) --count reaches 2--> open
open --reception lift--> lifted (count restarts at zero)
open --count falls below 2 (undo, or ageing out)--> closed by system (count not reset)
lifted / closed --count reaches 2 again--> new open row
```

## Relationships

- `no_show_block.patient_id` -> `ent-patient` (many blocks over time, one open at most).
- `no_show_block.lifted_by_staff_id` -> `ent-staff-account`.
- Reads `ent-appointment` and `ent-appointment-event` through the `cmp-booking` read interface (no write).
