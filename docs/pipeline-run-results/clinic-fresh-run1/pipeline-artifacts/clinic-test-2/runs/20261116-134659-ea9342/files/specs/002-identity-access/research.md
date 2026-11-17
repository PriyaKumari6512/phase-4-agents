# Research: Sign-in, roles and staff accounts

All decisions follow architecture.md; there were no unresolved NEEDS CLARIFICATION items in the Technical Context. Open product questions are in clarifications.md.

## R-01 Sign-in code storage and limits
- **Decision**: 6-digit random code from a cryptographically secure source; store only a keyed hash (HMAC with a pepper from the secret store) in ent-otp-challenge with expiry (10 minutes), attempts (max 5) and locked-until (15 minutes). The newest challenge per phone is the only valid one. Per-IP throttle and the daily cap are counted from challenge rows created in the last hour/24 hours (rows are kept 24 hours, which matches the cap window). A hashed IP (keyed hash) is stored on the row, not the raw address.
- **Rationale**: architecture thr-001 and thr-008; reuses the one named entity, no counter table or cache (constitution V). A 6-digit space is small, so the 5-try limit and lock carry the security.
- **Alternatives**: separate throttle table (new entity); in-memory counters (lost on restart, two replicas); Redis (not in architecture).

## R-02 Session token and cookie
- **Decision**: JWT signed with a key from the secret store, in an `HttpOnly`, `Secure`, `SameSite=Strict` cookie. Claims: user id, role, kind (patient/staff), issued-at, last-activity, and for staff the sign-in time. The cookie is re-issued on each request to slide last-activity. Patient: valid while less than 7 days since last activity. Staff: invalid after 8 hours since sign-in or 30 minutes since last activity. Role, clinic and active flag are read from the database on each request; claims about role are only a hint and are never trusted.
- **Rationale**: ADR-0004, ASM-008, thr-009. Time claims are required for the idle rules and are not personal data.
- **Alternatives**: server-side session table (not in architecture; the JWT plus DB re-read already gives immediate deactivation).

## R-03 CSRF and Origin
- **Decision**: all write methods (POST, PUT, PATCH, DELETE) require a custom CSRF header whose value matches a non-HttpOnly companion cookie (double submit) and an `Origin` header equal to the configured site origin; sign-in endpoints also require the Origin check. HTTPS-only with HSTS header; TLS terminates at the edge (ADR-0005).
- **Rationale**: thr-005 and ADR-0004 name "CSRF header and Origin check"; double submit is the minimal way to implement the header without server session state.
- **Alternatives**: synchroniser token in session table (needs session store).

## R-04 Staff passwords
- **Decision**: argon2id hashing, minimum 10 characters enforced on create, change and reset; failed-attempt counter and `locked_until` on the staff account (5 failures, 15 minutes); failure message is the same for unknown user and wrong password; a dummy hash is verified for unknown usernames to even out timing. WAF rate limit is infrastructure outside this feature.
- **Rationale**: thr-002, NFR-006. **Alternatives**: bcrypt (architecture names argon2id).

## R-05 Access context and clinic scoping
- **Decision**: a FastAPI dependency builds an `AccessContext` (user id, role, clinic id for receptionists, dentist id for dentists, patient account id and its person ids for patients) from the token owner and a fresh DB read. Other modules never take clinic or patient ids from the request alone: they call `ctx.require_role(...)`, `ctx.scope_clinic(query)`, `ctx.can_access_patient(patient_id)` and `ctx.can_access_clinic(clinic_id)`. Refused cross-owner reads answer 404 for patients' resources and 403 for role failures.
- **Rationale**: thr-004, thr-007, QA-007. Per-role matrix test over a registry of protected operations makes every new operation add a row.

## R-06 Account/person split and new-patient registration
- **Decision**: ent-patient-account (phone, name, preferred channel, reminders opt-out, active, erasure timestamps) and ent-patient (person: name, birth year, account). Registration is a two-step flow: verify code (challenge becomes verified) and a short-lived signed registration cookie (10 minutes) that allows `POST /api/auth/patient/register` with the name. The account and the account holder's person record are created in one transaction and the challenge is consumed.
- **Rationale**: ADR-0008, FR-002. Phone number is normalised to E.164 (+91 default) before use.

## R-07 Erasure on request
- **Decision**: manager confirms erasure for a patient account; one transaction sets `erasure_requested_at`, blocks sign-in (active false), and anonymises the person rows and account (name, phone, birth year replaced by non-identifying placeholders), then calls ports to anonymise appointment links and delete messages (ports are implemented by the booking and messaging features; a no-op adapter is registered until they exist). If a port fails, the request stays pending (`erased_at` null) and a scheduled job retries daily; an alert is raised if pending for more than 20 days. This keeps the 30-day promise with margin.
- **Rationale**: ASM-013, RSK-007, QA-008. **Alternatives**: wait up to 30 days then run (no benefit for the patient).

## R-08 Retention jobs
- **Decision**: identity job deletes ent-otp-challenge rows older than 24 hours, anonymises patient accounts idle for 24 months and staff accounts 24 months after deactivation. Messages (90 days) and appointments (24 months) are purged by their owning features; identity exposes the ports and the erasure hook only.
- **Rationale**: ASM-012, architecture section 5.

## R-09 Test tooling
- **Decision**: pytest and the contract tests in CI for the backend, as the CI flow in architecture section 8 requires unit and contract tests; pytest is not named in architecture.md and is assumed as the standard Python test runner. Web component tests use the runner chosen with the SPA shell. Both are recorded as an assumption, not a new architectural technology.
- **Rationale**: constitution I and DoD require automated tests.

## R-10 Message-sending port
- **Decision**: `MessageSender.send_code(phone, code)` is a port defined in `ports.py`; the SMS adapter in cmp-channel-adapters implements it in another feature. The code is sent inside the request (rel-007); a failure is shown to the patient as "could not send, try again" and does not count as a wrong try. Tests use a fake sender. Code text is never logged.
- **Rationale**: architecture rel-007, ports and adapters (ADR-0006).
