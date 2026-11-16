# Quickstart: validate Patient appointments (004)

Prerequisites: clinic-api running against PostgreSQL 16 with migrations of features 001 to 003 applied; the web app pointed at it; a test patient account with a session; test clinic with phone number, two dentists with working hours (feature 002); sandbox message providers (staging). Contracts: [patient-appointments.openapi.yaml](contracts/patient-appointments.openapi.yaml). Data: [data-model.md](data-model.md).

## Scenario 1 - list and detail (US1)
1. Create for the test patient: 2 booked appointments (one in 2 days, one in 3 hours), one past, one cancelled.
2. `GET /api/me/appointments` returns one group; `upcoming` has 2 (earliest first), `past` has 2.
3. Open "My appointments" in the web app on a 360 px wide phone viewport: no sideways scroll; times in IST.
4. Open the 3-hour appointment: clinic phone number shown, no buttons. Open the 2-day appointment: both buttons.
5. As a second patient, `GET /api/appointments/{id}` of the first patient's appointment returns 404.

## Scenario 2 - cancel (US2)
1. On the 2-day appointment choose Cancel, then Confirm: Done screen; status `cancelled_by_patient`.
2. Slot query for that dentist and time now lists the slot; booking it as another patient succeeds.
3. One history row (who, when, from `booked` to `cancelled_by_patient`), one change message row (channel of the appointment), reminder rows cancelled.
4. Send the cancel again: 200, still one history row and one message.
5. `POST .../cancel` on the 3-hour appointment returns 409 `within_cutoff` with the clinic phone.

## Scenario 3 - reschedule (US3)
1. On a 2-day appointment choose Change time: slot picker lists free slots of the same clinic for any dentist.
2. Pick one and confirm: Done screen shows the new dentist and time; the old slot is free; history reason `rescheduled from ... to ...`; reminder replaced; message row created.
3. Race: two sessions confirm the same slot; one gets 200, the other 409 `slot_taken` with `next_slots`, and keeps its original appointment.
4. Boundary: appointment at now + 4h exactly allowed; at now + 3h59m refused.

## Scenario 4 - deep link (US4)
1. In a clean browser open `/appointments/{id}` of the test patient: redirected to sign-in; after the phone code the appointment screen opens.
2. Open the same link signed in as another patient: "appointment not found".

## Automated checks
`pytest tests/booking` in clinic-api (unit tests for the change window, integration tests for list, cancel, reschedule, RBAC and the slot race, contract tests against the OpenAPI fragment); the web repo's test run for the four screens and the route guard. Expected: all pass in CI.
