# Quickstart: validating patient appointment management

Prerequisites: clinic-api running locally against a PostgreSQL 16 database with `btree_gist` and migrations applied (including `0005_appointment_event`); test data with one clinic with a phone number, two dentists with hours, one online treatment type, one patient account with a person; the messaging and scheduling interfaces available (real from features 007 and 002, or test doubles); the clock controllable in tests. Contracts: [contracts/appointments.openapi.yaml](contracts/appointments.openapi.yaml). Data: [data-model.md](data-model.md).

## Scenarios

1. **List (US1)** - sign in as the patient; `GET /api/appointments`. Expect upcoming (soonest first) and past (latest first) with status; another account's appointment is absent; its id on `GET /api/appointments/{id}` gives 404.
2. **Cancel more than 4 hours ahead (US3)** - `POST /api/appointments/{id}/cancel`. Expect 200 with status `cancelled_by_patient`, the slot in the free-slot list at once, one `appointment_event` row, one change message row created, and the reminder withdrawn.
3. **Cancel inside 4 hours (US3)** - set the clock to 3 h 59 min before the start. Expect 409 `too_late` with the clinic phone; no rows change. At exactly 4 h 00 min, expect 200.
4. **Reschedule (US4)** - `GET /api/appointments/{id}/slots`, pick a slot of the other dentist, `POST .../reschedule`. Expect 200 with new time and dentist, status `booked`, old slot free, one event row with old/new time, reminder replaced, one message row.
5. **Slot taken (US4)** - take the slot first by another booking, then reschedule to it. Expect 409 `slot_taken` with `nextSlots`; the appointment is unchanged.
6. **Blocked (US4)** - make the policy double answer blocked. Expect 409 `blocked`; cancel still works.
7. **History (US2)** - a reception-style call to `change_status` with the patient-asked flag gives `cancelled_by_patient`; without it `cancelled_by_clinic`; a raw insert of status `x` is refused by the database; the app user cannot UPDATE or DELETE an event row.
8. **Message link (US5)** - open `/appointments/{id}` in the web app signed out, sign in, land on the appointment; as another patient, see "not found".
9. **Atomicity** - make the messaging double raise; expect the appointment and history unchanged after the error.

## Commands

- API tests: run pytest in `clinic-api` (`tests/unit/booking`, `tests/api/booking`, `tests/contract`).
- Web tests: run the web repo's test command in `clinic-web` (`tests/appointments`).
- Manual check on a phone-sized viewport: no sideways scroll, tap targets at least 44 px, times in IST.
