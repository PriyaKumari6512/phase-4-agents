# Research: Family members on a patient account

All Technical Context items are resolved from architecture.md and the constitution; no NEEDS CLARIFICATION remains. Open product questions are in clarifications.md.

## Decision 1: Reuse the account/person split; add no table

- **Decision**: Family members are rows of `ent-patient` with the same `account` as the account holder. The holder is marked with `is_account_holder`; a removed person has `active = false` and `removed_at` set.
- **Rationale**: ADR-0008 and feature 001 already separate account (phone) from person, and `ent-appointment.patient` already points at the person. Simplicity (principle V).
- **Alternatives considered**: a separate `family_member` table (duplicates the person concept and breaks the per-person no-show rule PD-007); separate sign-ins per person (that is the Q-007 alternative, rejected as default, see RSK-003).

## Decision 2: Enforce the limit of 5 inside one transaction with an account row lock

- **Decision**: Add and "reactivate" operations lock the `ent-patient-account` row (`SELECT ... FOR UPDATE`), count active non-holder persons, and insert if fewer than 5.
- **Rationale**: Two simultaneous adds must not both pass the count (spec edge case). Volume is tiny, so a row lock is cheap; the whole system already relies on one database and strong consistency (architecture section 5).
- **Alternatives considered**: a database trigger or counter column (more moving parts); an application-level check only (race).

## Decision 3: Account scoping from the token, never from request ids

- **Decision**: One function `person_belongs_to_account(account_id, patient_id)` in `cmp-identity` is used by booking, list, reschedule and cancel. The account id comes from the session token's owner.
- **Rationale**: thr-004 and QA-007; a changed id in a request must be refused. One shared check avoids per-module copies.
- **Alternatives considered**: filtering only in queries (easy to forget on one operation); trusting the web app to send only valid ids (not acceptable).

## Decision 4: "Remove" is a soft removal; erasure is the real deletion

- **Decision**: Remove sets `active = false`, keeps name and birth year until erasure on request or the 24-month idle anonymisation (ASM-012). Refused while an upcoming booked appointment exists (Q2).
- **Rationale**: Keeps history and per-person no-show counts correct (PD-007); NFR-007 is met by the erasure operation (ASM-013, QA-008) which anonymises all persons of the account.
- **Alternatives considered**: hard delete on remove (breaks appointment history and the no-show report, RSK-007); auto-cancel upcoming appointments (surprising for the patient).

## Decision 5: Feature flag as an API setting exposed to the web app

- **Decision**: `FAMILY_MEMBERS_ENABLED` (environment setting, default off) in the API; the signed-in session response includes `features.family_members`; the web app hides the family screens and the "who" step when false; the API refuses family operations and defaults a booking's person to the account holder when false.
- **Rationale**: Architecture section 8: R2 screens are hidden by a feature flag until their data is ready. Server-side refusal prevents use through direct calls.
- **Alternatives considered**: a web-only build-time flag (API still reachable); a flag table with an admin screen (speculative, principle V).

## Decision 6: Logging without personal data

- **Decision**: Log lines for family operations carry person id, account id and correlation id only. A test captures logs during every family operation and asserts the name and birth year strings are absent. Validation error responses name the field, never echo the value.
- **Rationale**: Constitution Definition of Done and architecture section 9.
- **Alternatives considered**: a generic log scrubber (would hide mistakes rather than prevent them).

## Decision 7: Messages for a family member's visit go to the account

- **Decision**: Confirmation and reminder messages use the account's phone and channel choice (FR-013 is stored on the account); the existing confirmation and reminder templates are not changed, so message text does not name the person; this feature adds no new template.
- **Rationale**: Family members have no phone or sign-in (SA-001). Adding a template needs DLT approval (NFR-011) and is out of scope; the person is named on the booked screen and in the appointment link page.
- **Alternatives considered**: a new template naming the person (DLT lead time, RSK-001).
