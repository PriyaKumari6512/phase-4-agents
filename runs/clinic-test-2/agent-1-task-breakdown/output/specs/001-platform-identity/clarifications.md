# Clarifications: Platform, sign-in, roles and clinics (MOD-01)

No user was available during this run. The three open questions of the PRD are recorded with the option assumed.
None of them blocks this feature. Ids are the PRD's (`prd.md`, section 8).

## Q-007: Can one phone number book for family members?

- **Options**: (A) One account per phone number with up to 5 family members who share the sign-in (SA-001, PRD default); (B) each family member has their own sign-in on the same phone.
- **Assumed**: A.
- **Why**: It is the PRD default and the architecture assumption ASM-001. Phone-code sign-in cannot tell two people on one phone apart, so B would change sign-in.
- **Effect on this feature**: Only the account/person split (ADR-0008) is built: `patient_account` holds the phone, `patient` holds the person (name, birth year). Adding family members is a Release 2 feature (PRD FR-006). If the answer turns out to be B, sign-in changes (RSK-003, 2-4 person-days).

## Q-008: Hosting and domain?

- **Options**: (A) Managed container service and managed PostgreSQL in an India cloud region, domain supplied by the clinic (ASM-002); (B) a host or domain mandated by the client.
- **Assumed**: A, undecided.
- **Why**: Not part of the product; it affects only set-up, cost and service names (RSK-008).
- **Effect on this feature**: Everything is configured from environment variables; the services run in containers; HTTPS and secure-cookie flags are enforced by configuration, so no code depends on the host. No task here sets up hosting.

## Q-015: How are walk-ins recorded?

- **Options**: (A) A walk-in is a normal appointment marked arrived (SA-004, ASM-004); (B) a separate walk-in record type.
- **Assumed**: A.
- **Why**: PRD default; the no-show rate counts them as normal appointments.
- **Effect on this feature**: No separate record type. A walk-in patient is an ordinary patient (person) record; reception search and creation of patients is built with the reception feature (PRD FR-020) on top of the access rules built here (ASM-011).
