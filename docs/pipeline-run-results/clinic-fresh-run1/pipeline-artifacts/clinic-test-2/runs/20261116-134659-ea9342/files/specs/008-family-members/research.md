# Research: Family members on a patient account (Release 2)

No NEEDS CLARIFICATION remain in the technical context. Unknown product questions are in clarifications.md.

## R-1: Where family members live
- **Decision**: A family member is an `ent-patient` row (person) with `account_id` set to the holder's `ent-patient-account`. No separate table. The holder is the person with `is_account_holder = true`.
- **Rationale**: ADR-0008 already splits account and person; every appointment references an `ent-patient`; the no-show count is per person (PD-007).
- **Alternatives**: a separate family_member table (rejected: appointments would need two kinds of reference); family members with their own phone (rejected: NFR-007 stores only name and birth year, and it is Q-007's open scenario).

## R-2: Enforcing the limit of 5 under concurrency
- **Decision**: Add runs in one transaction: lock the account row (`SELECT ... FOR UPDATE`), count active family members, refuse at 5, insert.
- **Rationale**: Two concurrent adds at 4 serialise on the lock, so the limit is never exceeded (SC-004). Same style as the one-transaction rule used for bookings (QA-002).
- **Alternatives**: a database trigger (rejected: logic hidden from tests, Simplicity); unique slot numbers 1..5 per account (workable, but harder to explain); application check only (rejected: race).

## R-3: Duplicate persons
- **Decision**: Unique index on (account_id, lower(trim(name)), birth_year); the service returns a clear 409 duplicate error.
- **Rationale**: Assumption A-6; protects the per-person no-show count (PD-007).
- **Alternatives**: no check (rejected: lets one person be split into two).

## R-4: Authorisation of the chosen person
- **Decision**: `cmp-identity` exposes `resolve_person(access_context, person_id)`. It returns the person only if the person's account is the caller's account and the person is active; otherwise it raises "not found" (404, so another account's person is not revealed). `cmp-booking` calls it for every booking, and the appointment list is filtered by the caller's account.
- **Rationale**: thr-004 and thr-007; the architecture says every module enforces scoping through `cmp-identity`'s access context.
- **Alternatives**: check inside cmp-booking SQL only (rejected: duplicates identity rules).

## R-5: Feature flag
- **Decision**: One boolean flag `family_members`, read on the server per request from configuration (not a secret). When off: family endpoints answer 404, a booking that carries a `person_id` other than the holder is refused, and the web app hides the screens. The web app reads the flag from the API so the SPA build does not depend on release timing.
- **Rationale**: Architecture section 8: R2 screens are hidden by a feature flag until their data is ready. Reuse the mechanism of feature 001 (go-live readiness) if it exists; otherwise add the minimal one in `app/core/feature_flags.py`.
- **Alternatives**: separate builds (rejected: extra pipeline work).

## R-6: Folder layout and test tooling
- **Decision**: Use the layout in plan.md. It is an assumption because architecture.md names modules, not folders, and features 001 and 002 are being specified in parallel.
- **Follow-up**: Tasks use these paths; if feature 001 sets a different layout, rename paths only.

## R-7: Person name in messages (open question Q4)
- **Decision**: Add a `person_name` value to confirmation, change and reminder messages. Messages go to the account's phone and channel (`ent-patient-account`), unchanged.
- **Rationale**: FR-010 and the spec say messages name the person. SMS templates are DLT-registered and WhatsApp templates are approved (NFR-011, RSK-001), so a new variable needs a template change owned by feature 007 and thr-013's list of template values must be updated.
- **Fallback**: If a template cannot carry the name in time, the message keeps the link, and the link opens the appointment that names the person.

## R-8: Erasure and anonymisation
- **Decision**: The erasure operation (feature 002, ASM-013) already anonymises person, account and messages. This feature adds a test that family members are included, and a check that the idle-24-months job treats all persons of an account together.
- **Rationale**: NFR-007, RSK-007.

## R-9: Booking requests and idempotency
- **Decision**: `person_id` is an optional field on the booking request defined in feature 004; when absent, the booking is for the account holder, so MVP clients and tests keep working. The idempotency key of the booking request is unchanged.
- **Rationale**: Backward compatible contract change (expand, then contract; architecture section 8).
