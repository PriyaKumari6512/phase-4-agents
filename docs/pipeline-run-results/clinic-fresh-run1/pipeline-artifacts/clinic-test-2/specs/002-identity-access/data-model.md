# Data Model: Sign-in, roles and staff accounts

Owner of all entities: cmp-identity in ctr-clinic-api; stored in ctr-db (PostgreSQL 16). Column lists are logical; migration is a forward-only Alembic revision. PII fields are marked.

## ent-staff-account (table `staff_account`)
| Field | Type | Notes |
|---|---|---|
| id | uuid, PK | |
| username | text, unique | case-insensitive unique |
| name | text | PII |
| role | enum `receptionist`, `dentist`, `manager` | |
| clinic_id | uuid, nullable | required for receptionist; FK to ent-clinic (feature 001); null for dentist and manager |
| dentist_id | uuid, nullable | required for dentist; FK to ent-dentist (feature 001) |
| password_hash | text | argon2id, sensitive |
| failed_attempts | int | reset on success |
| locked_until | timestamptz, nullable | |
| active | bool | deactivated accounts cannot sign in |
| deactivated_at | timestamptz, nullable | anonymise 24 months after |
| created_at, updated_at | timestamptz | |

Validation: role-specific columns as above; password at least 10 characters before hashing. State: active <-> deactivated (manager only); the last active manager cannot be deactivated.

## ent-patient-account (table `patient_account`)
| Field | Type | Notes |
|---|---|---|
| id | uuid, PK | |
| phone | text, unique | PII, E.164; replaced by a placeholder on erasure |
| name | text | PII |
| preferred_channel | enum `sms`, `whatsapp`, default `sms` | read/written by messaging and booking features (FR-013) |
| reminders_opt_out | bool, default false | written by messaging features (FR-031) |
| active | bool | false after deactivation or erasure |
| deactivated_by, deactivated_at | uuid / timestamptz, nullable | who and when |
| erasure_requested_at | timestamptz, nullable | |
| erased_at | timestamptz, nullable | set when person rows, account and ports are done |
| last_seen_at | timestamptz | for the 7-day session and 24-month idle anonymisation |
| created_at | timestamptz | |

## ent-patient (table `patient`)
| Field | Type | Notes |
|---|---|---|
| id | uuid, PK | |
| account_id | uuid, FK patient_account | |
| name | text | PII |
| birth_year | smallint, nullable | PII; set for family members by feature 003-family |
| is_account_holder | bool | exactly one per account |
| active | bool | |
| created_at | timestamptz | |

Validation: at most 5 family members (non-holder) per account (enforced by the family feature; the constraint helper lives here). Anonymised rows keep their id so appointments stay linked to a non-identifying row.

## ent-otp-challenge (table `otp_challenge`)
| Field | Type | Notes |
|---|---|---|
| id | uuid, PK | |
| phone | text | PII; retained 24 hours |
| code_hash | text | keyed hash, sensitive |
| ip_hash | text | keyed hash of the network address |
| created_at | timestamptz | used by the throttles and the daily cap |
| expires_at | timestamptz | created_at + 10 minutes |
| attempts | int | max 5 |
| locked_until | timestamptz, nullable | set on the 5th wrong try (+15 minutes) |
| verified_at | timestamptz, nullable | set on a correct code |
| consumed_at | timestamptz, nullable | set when sign-in or registration completes |

State: issued -> verified -> consumed; issued -> expired; issued -> locked. Only the newest challenge for a phone can be verified. The lock applies per phone (the latest locked_until over the phone's rows). Rows are deleted after 24 hours.

## Access context (not stored)
Built per request from the token owner and a database read: user id, kind, role, clinic id, dentist id, patient account id and person ids, active flag.

## Ports (interfaces owned by cmp-identity, implemented elsewhere)
- `MessageSender.send_code(phone, code)` — cmp-messaging / cmp-channel-adapters.
- `AppointmentAnonymiser.anonymise_for_patients(patient_ids)` and `FutureAppointments.count_for_patients(patient_ids)` — cmp-booking.
- `MessageEraser.erase_for_account(account_id)` — cmp-messaging.
