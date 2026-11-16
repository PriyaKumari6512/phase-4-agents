# Data Model: Family members on a patient account

No new table. This feature adds the family-member lifecycle on `ent-patient` (owner: cmp-identity) and an account check for `ent-appointment.patient` (owner: cmp-booking).

## ent-patient-account (existing, feature 001)

| Field | Notes |
|---|---|
| id | primary key |
| phone number | PII, unique (one account per phone, SA-001) |
| name | PII |
| preferred channel, reminders opt-out | unchanged |

Relationship: one account has many persons (`ent-patient`), exactly one of them the account holder, at most 5 active family members.

## ent-patient (existing, feature 001; changed here)

| Field | Type | Constraint | Notes |
|---|---|---|---|
| id | uuid | primary key | |
| account_id | uuid | not null, foreign key to account | |
| name | text | not null, 1 to 100 characters after trimming | PII |
| birth_year | smallint | not null for family members; four digits, between (current year - 120) and current year | PII |
| is_account_holder | boolean | not null, default false; exactly one true per account | added by migration if feature 001 has no equivalent |
| active | boolean | not null, default true | false after removal |
| removed_at | timestamptz | nullable | set on removal |
| created_at | timestamptz | not null | |

Indexes and constraints (migration `0007_family_members.py`):
- Partial unique index on (account_id, lower(name), birth_year) where `active` is true: no duplicate active person on one account.
- Partial unique index on (account_id) where `is_account_holder` is true: one holder per account.
- Index on (account_id, active) for the family list and the limit count.

## Validation rules

- Limit: count of rows with `account_id` = X, `is_account_holder` = false, `active` = true must be below 5 before an insert; checked under a row lock on the account.
- Name is trimmed; empty after trimming is refused; longer than 100 characters is refused.
- Birth year is an integer; not in the future; not before (current year - 120).
- A person with `is_account_holder` = true cannot be removed through the family operations.
- A person with an upcoming appointment in status booked cannot be removed.

## State transitions

```text
(new) --add--> active --edit--> active
active --remove (no upcoming booked appointment)--> removed (active=false, removed_at set)
active or removed --erasure on request--> anonymised (name and birth_year cleared, appointments keep the row without personal link)
```

A removed person is never reactivated; adding the same name and birth year again creates a new person.

## ent-appointment (existing, feature 003; read here)

`patient` references the person (`ent-patient.id`). Access rule: a patient reaches an appointment only if its person's `account_id` equals the signed-in account. Appointments of removed persons stay readable by that account.

## PII and retention

Name and birth year are PII. They are never logged (NFR-007). Retention is as ent-patient: until deletion on request, anonymised at 24 months idle (ASM-012).
