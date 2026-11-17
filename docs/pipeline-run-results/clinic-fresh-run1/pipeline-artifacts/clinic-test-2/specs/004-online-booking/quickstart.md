# Quickstart: validate Patient online booking

A validation guide, not an implementation. Links: [spec.md](spec.md), [data-model.md](data-model.md), [contracts/booking-api.openapi.yaml](contracts/booking-api.openapi.yaml).

## Prerequisites

- Features 001, 002 and 003 available in the environment: database with `btree_gist`, a signed-in test patient (test sign-in code in dev or staging), 2 clinics, at least 2 dentists with working hours in the next 30 days, treatment types check-up, cleaning, consultation (online) and one reception-only type.
- Migrations `004a` and `004b` applied (`alembic upgrade head` in `brightsmile/clinic-api`).
- Messaging may be the no-op adapter (feature 007 not ready) and the policy adapter "not blocked" (feature 009 not ready).

## Scenario 1: book with a named dentist (User Story 1)

1. Sign in as test patient A; open `/book`.
2. Who and what: choose "myself", a clinic, "check-up"; continue.
3. Slot picker: choose dentist Dr X, a day, a slot; continue.
4. Confirm: SMS is selected; confirm.
5. Expected: booked screen shows clinic, dentist, treatment, date and time in IST; one `appointment` row with status `booked` and one `appointment_event` row; 4 screens used.

## Scenario 2: first available (User Story 1)

1. Repeat with "cleaning" and "first available".
2. Expected: up to 10 slots across the clinic's dentists, soonest first, each with its dentist; the booked appointment is for the dentist of the chosen slot.

## Scenario 3: slot taken (User Story 2)

1. Open the confirm screen as patient A for slot S. As patient B (second browser), book S and finish.
2. Confirm as patient A.
3. Expected: A sees "this slot has just been taken" with the next free slots on the slot picker; clinic, treatment and channel are kept; exactly one appointment exists for S.

## Scenario 4: retry (User Story 2)

1. Send `POST /api/booking/appointments` twice with the same `Idempotency-Key` and body.
2. Expected: first 201, second 200 with `Idempotent-Replay: true`; one appointment. With a different body and the same key: 422 `idempotency_key_reused`.

## Scenario 5: remembered channel (User Story 3)

1. As a new patient confirm a booking with WhatsApp.
2. Start another booking.
3. Expected: WhatsApp preselected. After a "slot taken" failure with SMS selected, the remembered channel is still WhatsApp.

## Scenario 6: refusals

- Treatment not online (root canal): 422 `not_bookable_online` with the clinic phone number.
- Not signed in: 401, no booking.
- Slot more than 30 days ahead or in the past: 422 `outside_booking_window`.
- Policy adapter returning blocked (test double): 403 `online_booking_blocked` with the clinic phone number.

## Scenario 7: concurrency test (User Story 4, QA-003)

- Run in `brightsmile/clinic-api`: `pytest tests/concurrency/booking -m concurrency` against the test database.
- Expected: 1,000 runs, each with up to 100 simultaneous attempts; every run has one winner per contested slot and 0 overlapping active appointments per dentist. Output is a summary line with runs, failures and the maximum attempts.

## Scenario 8: performance check (User Story 5, NFR-002)

- Server side: `python tests/performance/booking/run_load.py --patients 100 --duration 300` against staging. Expected report: slot list p95 at most 500 ms, booking p95 at most 800 ms.
- Client side: on a phone or the browser with the "Fast 4G" profile, open the slot picker and confirm 20 bookings. Expected: slots shown within 2 s and booked screen within 3 s for at least 95% of requests.

## Screen checks (NFR-010)

- On Chrome and Safari on Android and iPhone: four screens, tap targets at least 44 px, no sideways scrolling.
