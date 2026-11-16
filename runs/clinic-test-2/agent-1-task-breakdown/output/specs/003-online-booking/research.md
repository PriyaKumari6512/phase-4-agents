# Research: Online booking by patients (003)

No NEEDS CLARIFICATION remain in the technical context. Decisions below follow architecture.md (ADR-0003, QA-001/002/003, rel-005).

## D1. Who decides a race

- **Decision**: a PostgreSQL exclusion constraint using `btree_gist` on (dentist, time range) for active appointments. The application does not lock or pre-check as the decider; it may read free slots first for speed, but the insert is the authority.
- **Rationale**: one statement decides the winner under any number of simultaneous attempts, also across two API replicas (ADR-0003, QA-003).
- **Alternatives**: row lock on a slot table (needs slot rows, more writes); advisory locks (code path can bypass); optimistic version check (no row to version).

## D2. What "active" means

- **Decision**: any status other than "cancelled by the patient" and "cancelled by the clinic". Booked, arrived and no-show keep the slot.
- **Rationale**: matches FR-024 statuses; a cancelled slot is bookable at once (FR-018, feature MOD-04).

## D3. Conflict answer

- **Decision**: the insert fails with an exclusion violation; the service rolls back, re-reads the next free slots for the same clinic, treatment and dentist choice (top 10 for "first available") and answers HTTP 409 `slot_taken` with them.
- **Rationale**: ADR-0003; patient continues without starting over (FR-012).
- **Alternatives**: 422 (wrong; it is a normal outcome, not a bad request).

## D4. Retry key

- **Decision**: header `Idempotency-Key` (UUID from the browser, new for each confirm attempt). Table `booking_request` with unique (patient account, key) stores the request fingerprint and the outcome (appointment id, or "conflict"). A repeat with the same key and same fingerprint returns the stored result; same key with a different body returns 422. The key row and the appointment are inserted in one transaction, so a crash leaves neither.
- **Rationale**: client timeouts and double taps are normal on 4G; writes are never retried automatically by the client (rel-005), but the patient may press again.
- **Alternatives**: unique key column on appointment only (cannot store conflict outcome, Q2); client-side disabling only (not safe).

## D5. Confirmation after commit

- **Decision**: in the same transaction the booking inserts the appointment, the "booked" history entry and, through the `BookingMessages` port, the confirmation and reminder rows (feature 006 owns the rows' content and timing). The dispatcher sends them after commit. The request never calls a provider.
- **Rationale**: ADR-0003 and QA-002; a provider outage cannot slow or undo a booking.

## D6. "First available"

- **Decision**: no dentist given means: ask `SlotSource` for free slots of every dentist of the clinic who offers the treatment, from now to the horizon, merge by start time then dentist name, return the first 10. Named dentist: free slots for one day.
- **Rationale**: QA-001 (top 10, indexes on dentist and time); payload about 2 KB.
- **Open point handled**: free slots start on the hour or half hour (MOD-02); a slot in the past or already started is never returned.

## D7. Horizon

- **Decision**: a setting `booking_horizon_days`, default 30; the last bookable day is today plus the setting, inclusive (ASM-010). Slots are checked against the horizon at lookup and again at booking (a request beyond it gets 422).
- **Rationale**: PD-002, ASM-010; the check at booking stops hand-made requests.

## D8. Authorisation

- **Decision**: the patient account comes from the session; the request names the person (`patient_id`) and the server accepts only the account holder's own person in Release 1; any other value gives 403. Release 2 widens the rule to the account's family members (Q-007).
- **Rationale**: thr-004 (altered ids); keeps the contract stable (Q1).

## D9. Three ports

- **Decision**: `SlotSource` (cmp-scheduling: free slots, treatment check, dentist-at-clinic check), `BookingMessages` (cmp-messaging: create rows in the caller's transaction), `BlockPolicy` (cmp-noshow-policy: `is_blocked(person)`; default always false). All in-process, defined in `app/modules/booking/ports.py`.
- **Rationale**: module boundaries of the modular monolith (ADR-0001) and parallel work with MOD-02, feature 006 and R2, without speculative frameworks.

## D10. Performance and concurrency testing

- **Decision**: Python scripts in `tests/booking/` (pytest). The concurrency test starts many threads or async tasks against a real PostgreSQL, over two app instances where possible; the load test sends requests with an added delay profile for 4G and reports p95 for the server and for the whole round trip. Run against staging before go-live.
- **Rationale**: no new tool needed; Python is in the architecture.

## D11. Mobile acceptance

- **Decision**: screen tests in the web repo check screen count, tap target size (>= 44 px) and layout width without horizontal overflow at 320, 360 and 390 px; a device checklist is run by hand on current Chrome and Safari on Android and iPhone before go-live. The browser-automation tool is not named in architecture.md, so none is added here.
- **Rationale**: NFR-001, NFR-010 need real browsers to be believable; the checklist is cheap and recorded in the repo.
