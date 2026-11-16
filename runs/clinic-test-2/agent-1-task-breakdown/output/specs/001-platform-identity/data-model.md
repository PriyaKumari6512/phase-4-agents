# Data Model: Platform, sign-in, roles and clinics (MOD-01)

Database: PostgreSQL 16 (`ctr-db`), owned by `ctr-clinic-api`. Ids are UUIDs. Times are `timestamptz` in UTC.
Migrations are forward-only (Alembic). PII columns are marked **PII**; they never go to logs (constitution).

## Scheduling (component `cmp-scheduling`, data only)

### clinic (`ent-clinic`)
| Column | Type | Rule |
|---|---|---|
| id | uuid PK | |
| name | text NOT NULL | unique (case-insensitive), 1 to 80 characters |
| address | text NOT NULL | 1 to 300 characters |
| phone | text NOT NULL | the clinic's public phone number, 5 to 20 characters |
| active | boolean NOT NULL | default true |
| created_at | timestamptz NOT NULL | default now |

Seed: Indiranagar, Whitefield (active).

### dentist (`ent-dentist`)
| Column | Type | Rule |
|---|---|---|
| id | uuid PK | |
| name | text NOT NULL **PII** | 1 to 120 characters; replaced by "Former dentist" on anonymisation |
| active | boolean NOT NULL | default true |
| deactivated_at | timestamptz NULL | set when active becomes false |
| anonymised_at | timestamptz NULL | |
| created_at | timestamptz NOT NULL | |

### dentist_clinic_day
Which weekday a dentist works at which clinic. Weekly hours and breaks (`ent-working-hours`) are added by MOD-02 on top of this.
| Column | Type | Rule |
|---|---|---|
| id | uuid PK | |
| dentist_id | uuid FK dentist NOT NULL | |
| clinic_id | uuid FK clinic NOT NULL | |
| weekday | smallint NOT NULL | CHECK 0 to 6 (0 = Monday) |
| | | UNIQUE (dentist_id, weekday): a dentist is at one clinic on one weekday |

## Identity (component `cmp-identity`)

### staff_account (`ent-staff-account`)
| Column | Type | Rule |
|---|---|---|
| id | uuid PK | |
| username | text NOT NULL | 3 to 40 characters, letters, digits, `.`, `_`, `-`; unique on `lower(username)` |
| name | text NOT NULL **PII** | 1 to 120 characters |
| role | text NOT NULL | one of `receptionist`, `dentist`, `manager` |
| clinic_id | uuid FK clinic NULL | CHECK: NOT NULL when role = receptionist, NULL otherwise |
| dentist_id | uuid FK dentist NULL | CHECK: NOT NULL when role = dentist, NULL otherwise; unique |
| password_hash | text NOT NULL (sensitive) | argon2id; plain passwords are never stored; minimum length 10 is checked before hashing |
| must_change_password | boolean NOT NULL | default false; true for the seeded manager and after a reset |
| active | boolean NOT NULL | default true |
| deactivated_at | timestamptz NULL | |
| failed_attempts | integer NOT NULL | default 0; reset on success |
| locked_until | timestamptz NULL | set to now + 15 minutes at 5 failures |
| anonymised_at | timestamptz NULL | |
| created_at | timestamptz NOT NULL | |

### patient_account (`ent-patient-account`)
| Column | Type | Rule |
|---|---|---|
| id | uuid PK | |
| phone | text NOT NULL UNIQUE **PII** | normalised `+91` followed by 10 digits, first digit 6 to 9; after erasure `erased-<id>` |
| preferred_channel | text NOT NULL | `sms` or `whatsapp`, default `sms` (stored here, used by messaging, FR-013 of the PRD) |
| reminders_opt_out | boolean NOT NULL | default false (STOP flag, used by messaging) |
| last_used_at | timestamptz NOT NULL | updated at sign-in and at most once a minute on use |
| anonymised_at | timestamptz NULL | |
| created_at | timestamptz NOT NULL | |

### patient (`ent-patient`)
A person that bookings are for (ADR-0008).
| Column | Type | Rule |
|---|---|---|
| id | uuid PK | |
| account_id | uuid FK patient_account NOT NULL | |
| name | text NOT NULL **PII** | 1 to 120 characters; "Erased patient" after erasure |
| birth_year | smallint NULL **PII** | CHECK between 1900 and the current year; null for the account holder in this feature (family members, release 2, give it) |
| is_account_holder | boolean NOT NULL | UNIQUE partial index: one holder per account |
| active | boolean NOT NULL | default true |
| anonymised_at | timestamptz NULL | |

### otp_challenge (`ent-otp-challenge`)
One row per phone number, replaced by a new request.
| Column | Type | Rule |
|---|---|---|
| id | uuid PK | |
| phone | text NOT NULL UNIQUE **PII** | normalised |
| code_hash | text NOT NULL (sensitive) | HMAC-SHA256 of the 6-digit code with a server secret |
| expires_at | timestamptz NOT NULL | issue time + 10 minutes |
| wrong_tries | smallint NOT NULL | 0 to 5; kept when a new code replaces the old one while a lock is active |
| locked_until | timestamptz NULL | set to now + 15 minutes at the 5th wrong try |
| verified_at | timestamptz NULL | set when the code is right and no account exists yet; the name step must follow within 10 minutes |
| created_at | timestamptz NOT NULL | |
| updated_at | timestamptz NOT NULL | retention: row deleted when `updated_at` is older than 24 hours |

State: `issued` → (`wrong` up to 5 → `locked` for 15 minutes) or `verified` → `consumed` (row removed or marked used).

### auth_session
| Column | Type | Rule |
|---|---|---|
| id | uuid PK | the JWT `jti` |
| staff_account_id | uuid FK NULL | exactly one of the two owner columns is set (CHECK) |
| patient_account_id | uuid FK NULL | |
| issued_at | timestamptz NOT NULL | |
| last_used_at | timestamptz NOT NULL | refreshed at most once a minute |
| absolute_expires_at | timestamptz NULL | staff: issued + 8 hours; patient: null |
| revoked_at | timestamptz NULL | set at sign-out, deactivation, password reset, erasure |

Valid when not revoked, owner active, and: staff: now < absolute_expires_at and now - last_used_at < 30 minutes; patient: now - last_used_at < 7 days.

### sign_in_throttle
| Column | Type | Rule |
|---|---|---|
| id | uuid PK | |
| kind | text NOT NULL | `ip_hour` or `phone_day` |
| key_hash | text NOT NULL | HMAC of the IP or phone with a server secret (no plain PII) |
| window_start | timestamptz NOT NULL | start of the hour or day |
| count | integer NOT NULL | number of codes requested in the window |
| | | UNIQUE (kind, key_hash, window_start); rows older than 24 hours are deleted by the retention job |

### erasure_request
| Column | Type | Rule |
|---|---|---|
| id | uuid PK | |
| patient_account_id | uuid FK NOT NULL | |
| requested_by | uuid FK staff_account NOT NULL | the manager |
| requested_at | timestamptz NOT NULL | |
| due_at | timestamptz NOT NULL | requested_at + 30 days |
| done_at | timestamptz NULL | |
| done_by | uuid FK staff_account NULL | |

State: `open` (done_at null) → `done`. Overdue = open and now > due_at.

## Relationships

- clinic 1—N dentist_clinic_day N—1 dentist
- clinic 1—N staff_account (receptionists); dentist 1—0..1 staff_account
- patient_account 1—N patient (exactly one holder; family members later)
- patient_account 1—N auth_session, staff_account 1—N auth_session
- patient_account 1—N erasure_request

## Interface for other modules (not tables)

- `AccessContext` in `app/identity/access.py`: `kind`, `account_id`, `role`, `clinic_ids`, `patient_ids`, `require_role()`, `require_clinic()`, `clinic_filter()`.
- `SmsSender` port in `app/identity/sms_port.py`: `send_code(phone, code) -> SendResult`.
- Erasure steps registry and retention rules registry in `app/jobs/registry.py`.
