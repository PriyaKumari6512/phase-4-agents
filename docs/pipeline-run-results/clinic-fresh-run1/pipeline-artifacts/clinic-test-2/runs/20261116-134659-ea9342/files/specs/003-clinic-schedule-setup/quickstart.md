# Quickstart: validating clinics, hours, leave, treatments and free slots

Use this to prove the feature works end to end. Details: [data-model.md](data-model.md), [contracts/scheduling-api.openapi.yaml](contracts/scheduling-api.openapi.yaml).

## Prerequisites

- clinic-api and clinic-web scaffolded by the platform feature (001), PostgreSQL 16 available (local or dev environment).
- Sign-in and access context from feature 002, or the test fixtures that create a manager, a receptionist for each clinic, a dentist and a patient session.
- cmp-booking not required: the empty appointments stand-in is used; tests plug in a fake that returns chosen appointments.

## Setup

1. Apply migrations in clinic-api (`alembic upgrade head`). The three online treatment types and the horizon setting (30) exist afterwards.
2. Start the API and the web app (dev environment).

## Scenarios

1. **Third clinic as data (SC-001)**: sign in as the practice manager, open Clinics, add "Clinic C" with address and phone, add a dentist, open Dentists and hours and give the dentist Monday 09:00–17:00 with a 13:00–14:00 break at Clinic C. Without restarting anything, `GET /api/clinics` as a patient lists Clinic C and `GET /api/clinics/{id}/slots` for the next Monday returns 30-minute slots from 09:00 to 16:30 except 13:00 and 13:30.
2. **Treatments (US2)**: open Treatments, add "Root canal" 90 minutes, online off. As a patient, `GET /api/treatment-types` does not list it; as reception it does. Saving 45 minutes is refused.
3. **Hours rules (US3)**: set the same dentist Monday 15:00–19:00 at another clinic: refused with a message. Set 17:00–19:00 there: accepted.
4. **Leave and to-move (US5, US6)**: with the fake appointments port holding 3 booked appointments for the dentist on a Monday (2 at Clinic C, 1 at the other clinic), record whole-day leave for that Monday. The response lists all 3, none is changed. As the Clinic C receptionist, `GET /api/clinics/{C}/to-move` returns the 2; asking for the other clinic returns 403. Mark one appointment cancelled in the fake and read again: 1 left.
5. **Slots (US4)**: with a booked 10:00–10:30 appointment and 15:00–16:00 leave on a Monday, slots for 30 minutes exclude 10:00 and 15:00–15:30 starts; for 90 minutes every slot fits fully in free time; `first-available` returns 10 slots and `page=2` the next 10.
6. **Roles (SC-005)**: as receptionist, dentist and patient, each write route returns 403.

## Commands

- Unit and integration tests: `pytest clinic-api/tests/scheduling`
- Contract tests: `pytest clinic-api/tests/scheduling/contract`
- Performance check (QA-001): `pytest clinic-api/tests/scheduling/perf -m perf` (seeds 3 clinics, 10 dentists, 1,000 appointments a week; 100 concurrent users; expects server p95 at or under 500 ms)
- Web tests: the front-end test command from the platform feature, in `clinic-web/src/features/scheduling/__tests__`

## Expected outcome

All scenarios behave as described, the test suites pass, the performance test meets the p95 target, and logs from these routes contain no patient names or phone numbers.
