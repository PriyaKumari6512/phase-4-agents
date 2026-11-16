# Quickstart: validate online booking (003)

Prerequisites: PostgreSQL 16 with `btree_gist`; the clinic-api migration `0003_online_booking` applied; seed data with 1 clinic, 2 dentists with working hours, the three online treatment types and one test patient signed in (fixture from feature 001). Contract: [contracts/online-booking.openapi.yaml](contracts/online-booking.openapi.yaml). Tables: [data-model.md](data-model.md).

## 1. Happy path (User Stories 1 and 2)

1. In clinic-api run the booking integration tests: `pytest tests/booking/unit tests/booking/contract tests/booking/integration`.
2. Start the api and the web app locally; sign in as the test patient; choose Book, a clinic, "Check-up", "first available".
3. Expected: up to 10 slots, earliest first, each with a dentist; pick one, keep SMS, confirm.
4. Expected: the "booked" screen shows clinic, dentist, treatment, date, time (IST) and channel; the database holds one `appointment` (status `booked`), one `appointment_event` (to_status `booked`) and the message rows.

## 2. Slot taken (User Story 3)

1. Open the slot picker in two browser sessions (two patients), pick the same slot, confirm in both.
2. Expected: one "booked" screen; the other shows "this slot was just taken" with the next free slots on the same screen.

## 3. Retry safety

1. Send `POST /api/appointments` twice with the same `Idempotency-Key` and body.
2. Expected: first answer 201, second 200 with the same appointment id; one row in `appointment`.

## 4. Concurrency (User Story 4)

Run `pytest tests/booking/concurrency -m concurrency` (1,000 runs). Expected: report shows 0 overlapping active appointments in every run.

## 5. Performance (User Story 5)

Run `python tests/booking/performance/run_load.py --users 100 --profile 4g` against staging. Expected: report with p95 for slot lists (<= 2 s round trip, <= 500 ms server) and for bookings (<= 3 s round trip, <= 800 ms server).

## 6. Mobile (User Story 6)

Follow `src/features/booking/__tests__/mobile-acceptance.md` on current Chrome and Safari on an Android phone and an iPhone. Expected: 4 screens after sign-in, no sideways scrolling from 320 px, tap targets at least 44 px, Back keeps choices.
