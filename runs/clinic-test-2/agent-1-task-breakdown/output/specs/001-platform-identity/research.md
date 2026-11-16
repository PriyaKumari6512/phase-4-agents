# Research: Platform, sign-in, roles and clinics (MOD-01)

All unknowns of the Technical Context were resolved from `architecture.md`, the constitution and `prd.md`. The three
open product questions are recorded in `clarifications.md`.

## R1. How to hold a session that has idle expiry, sign-out and immediate deactivation

- **Decision**: JWT in an `HttpOnly`, `Secure`, `SameSite=Strict` cookie, carrying only the session id (`jti`) and the owner id. A row in `auth_session` stores `last_used_at`, `absolute_expires_at` and `revoked_at`. On every request the API loads the session and the owner (staff or patient account) and re-reads role, clinic and active flag.
- **Rationale**: The architecture requires a JWT cookie and a re-read of role, clinic and active flag on each request (section 9, thr-009). A 30-minute idle limit and "sign-out ends the session at once" need server state; one small table is the simplest way and needs no cache (architecture: no cache).
- **Alternatives considered**: Pure stateless JWT with short expiry (cannot do idle timeout or revocation without refresh tokens, more moving parts); server session in a cache (architecture names no cache).

## R2. Session lengths

- **Decision**: Staff: expire at the earlier of 8 hours after sign-in and 30 minutes after last use. Patient: expire 7 days after last use. Cookie and row are refreshed at most once a minute to avoid a write on every request.
- **Rationale**: ASM-008. Updating `last_used_at` once a minute keeps database writes low and the idle limit exact to a minute.
- **Alternatives considered**: Write on every request (needless load); fixed 7-day patient token (would not be "from last use").

## R3. Storing and checking the one-time code

- **Decision**: 6 digits from `secrets`, stored as HMAC-SHA256 with a server secret from the environment, compared in constant time. One `otp_challenge` row per phone number, replaced on a new request, with `wrong_tries` and `locked_until` kept until the lock has passed.
- **Rationale**: The architecture says "6-digit code stored hashed" (thr-001). A plain hash of a 6-digit number can be reversed in a second, so a keyed hash is used. Keeping the try counter on the row stops "ask for a new code" from resetting the 5-try limit.
- **Alternatives considered**: bcrypt/argon2 for codes (slow for no gain at 10-minute life); a row per code (counter reset problem, more cleanup).

## R4. Per-IP throttle and daily cap

- **Decision**: Table `sign_in_throttle` with counters per (kind, hashed key, window). Defaults, all settings: 10 code requests per IP per hour, 10 codes per phone per day. A request over a limit is refused before any SMS is sent.
- **Rationale**: Architecture thr-001 and thr-008 require a per-IP throttle and a daily cap; two API replicas run, so counters must be shared; the database is the only shared store in the design. The numbers are not in the PRD; they are our defaults and are settings (see Assumptions in the spec and open point below).
- **Alternatives considered**: In-memory counters (not shared between replicas); WAF only (architecture adds WAF rate limits on top, not instead).
- **Open point (not a blocker)**: The exact numbers (10/hour/IP, 10/day/phone) should be confirmed at Gate 2; changing them is a configuration change.

## R5. Staff password hashing and lockout

- **Decision**: argon2id; minimum length 10 enforced at creation, reset and change; `failed_attempts` and `locked_until` on `staff_account`; 5 failures lock for 15 minutes; a successful sign-in resets the count; the same message for unknown user and wrong password; a dummy hash check for unknown users to equalise timing.
- **Rationale**: Architecture section 9 and thr-002; PRD NFR-006.
- **Alternatives considered**: Lockout per IP (would lock a whole clinic behind one address).

## R6. CSRF, Origin check and HTTPS

- **Decision**: Middleware requires a custom header (`X-Requested-With: brightsmile`) on all `POST`, `PUT`, `PATCH`, `DELETE` and checks that the `Origin` header equals one of the allowed origins from settings. The cookie is `Secure` unless `COOKIE_SECURE=false` is set for local development only. HTTPS itself is terminated at the edge (architecture, section 8); the API refuses plain HTTP when `REQUIRE_HTTPS=true` (checks `X-Forwarded-Proto`).
- **Rationale**: ADR-0004 and thr-005: `SameSite=Strict`, CSRF header and Origin check on writes.
- **Alternatives considered**: Double-submit CSRF token (more state; the custom header plus Origin plus SameSite meets the architecture).

## R7. Access framework

- **Decision**: One `AccessContext` created by a FastAPI dependency from the cookie. It contains kind (`staff` / `patient`), id, role, `clinic_ids` (receptionist: its clinic; dentist: clinics of its dentist record; manager: all active and inactive clinics), `patient_ids` (patient: persons of its account) and helpers `require_role`, `require_clinic`, `clinic_filter`. Routers take it as a dependency; services never read ids from the request body for scope.
- **Rationale**: Architecture thr-004 and thr-007: authorisation from the token owner, never request ids alone; `cmp-identity` offers the access context to all modules.
- **Alternatives considered**: Row-level security in PostgreSQL (strong, but extra set-up and the architecture keeps checks in the modules); decorators per route without a shared context (duplicated scope logic).

## R8. Account/person split

- **Decision**: `patient_account` (phone, channel, opt-out, last used) and `patient` (name, birth year, `is_account_holder`). Creating an account creates the holder. Family members are added later by the Release 2 feature; nothing in this feature needs more.
- **Rationale**: ADR-0008, assumption ASM-001 (Q-007 open). Keeps the cost of the other answer low (RSK-003).
- **Alternatives considered**: One table (would force a migration and sign-in change when family members arrive).

## R9. Erasure and retention

- **Decision**: Anonymise in place: name becomes "Erased patient", birth year null, phone replaced by `erased-<id>` (so the number can be used again for a new account), channel reset, all sessions revoked, `anonymised_at` set. Appointment rows are kept anonymous (RSK-007). `erasure_service` runs an ordered list of registered steps so messaging can add "anonymise messages". The retention job (`app/jobs/retention.py`) runs a registry of rules; this feature registers: sign-in codes after 24 hours, staff and dentists 24 months after deactivation, patient accounts unused for 24 months.
- **Rationale**: ASM-012, ASM-013, QA-008, NFR-007; spec FR-015, FR-016.
- **Alternatives considered**: Hard delete (breaks appointment counts, the no-show report and the block, RSK-007).

## R10. Scheduling of the daily job

- **Decision**: The job is a function with a command-line entry point (`python -m app.jobs.retention`) and an in-process daily trigger started with the app, in line with the architecture ("dispatcher and scheduled jobs are modules of ctr-clinic-api, started with the app"). It takes a database advisory lock so two replicas do not run it together, and every rule is idempotent.
- **Rationale**: Architecture section 13. Idempotent rules satisfy spec User Story 7 scenario 5.
- **Alternatives considered**: An external scheduler (extra infrastructure, Q-008 unknown).

## R11. Logging without personal data

- **Decision**: Structured JSON logs with `correlation_id`, `account_id`, `session_id`; a logging filter masks values that look like phone numbers and refuses known PII field names; a test asserts no name, phone or birth year in captured logs for every flow. OpenTelemetry traces and metrics are set up in the Foundation (constitution principle II).
- **Rationale**: Constitution Definition of Done; architecture section 9.
- **Alternatives considered**: Rely on developer care only (not testable).

## R12. Seed data

- **Decision**: An idempotent Alembic data migration inserts Indiranagar and Whitefield (address and phone are placeholders to be replaced by the manager in the clinic screen). The first manager is created by `python -m app.identity.seed` from `SEED_MANAGER_USERNAME` / `SEED_MANAGER_PASSWORD` environment variables with `must_change_password=true`.
- **Rationale**: Spec Assumptions; constitution: no secrets in code.
- **Alternatives considered**: Hard-coded default manager password (security finding).
