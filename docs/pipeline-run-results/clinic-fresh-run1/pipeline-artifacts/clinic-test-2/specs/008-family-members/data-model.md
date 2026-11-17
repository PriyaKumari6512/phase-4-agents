# Data Model: Family members on a patient account (Release 2)

Conceptual entities are `ent-patient-account` and `ent-patient` (architecture.md section 5, ADR-0008). Column names below are assumed (the architecture's `data-model.md` is separate); align with the tables created in feature 002.

## ent-patient-account (existing, owner cmp-identity)

| Field | Notes |
|---|---|
| id | Key |
| phone | PII; one account per phone number (SA-001) |
| name | PII; the account holder's name |
| preferred_channel | SMS (default) or WhatsApp; used for every person on the account |
| reminders_opt_out | Applies to every person on the account |

No change to this table in this feature. Its row is locked while a family member is added (R-2 in research.md).

## ent-patient (a person; owner cmp-identity)

| Field | Type / rule |
|---|---|
| id | Key |
| account_id | Required, references ent-patient-account |
| name | PII; required, trimmed, not empty |
| birth_year | PII; integer, 1900 to the current year (database check: at least 1900; the upper limit is checked in the service) |
| is_account_holder | true for the person created with the account, false for family members |
| active | true; this feature never sets it to false (A-4) |
| created_at | Time created |

Rules:
- At most 5 rows with `is_account_holder = false` and `active = true` per account (FR-002, enforced in a transaction that locks the account row).
- Unique per account on (lower(trim(name)), birth_year) (A-6).
- A family member has no phone, no sign-in and no channel of its own (FR-004).
- Retention: until deletion on request; anonymised at 24 months idle (architecture section 5).

State transitions: none in this feature (created only).

## ent-appointment (existing, owner cmp-booking)

Already references `patient` (a person). This feature requires only that the booking sets it to the chosen person. No schema change.

## Migration

`alembic/versions/0008_family_members.py`, expand-only and compatible with the previous release: add `is_account_holder` if feature 002 did not create it (default true for existing rows), the birth-year check, and the unique index. Index on `account_id` if missing.
