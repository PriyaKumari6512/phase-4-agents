# Quickstart: validating feature 002

Prerequisites: `clinic-api` running against a PostgreSQL 16 test database with migrations applied (including the scheduling migration and seed), feature 001 data (2 clinics, a dentist, a practice manager account, a receptionist for clinic 1), `clinic-web` dev server pointing at the API.

Run the checks:

```text
# clinic-api
pytest tests/scheduling/unit tests/scheduling/api tests/scheduling/contract
python -m tests.scheduling.load.slots_load   # 100 concurrent users, 3 clinics, 10 dentists

# clinic-web
npm test -- scheduling
```

Scenarios (each maps to a user story; contracts in `contracts/scheduling-api.openapi.yaml`):

1. **Treatments (US1)**: as manager, `GET /api/treatment-types` shows the five seeded types; `POST` a 60-minute reception-only type; `PATCH` it to `active=false`; as a patient the list has only the active online types.
2. **Hours (US2)**: as manager, `PUT /api/dentists/{id}/clinics/{clinic}/working-hours` with Monday 09:00-17:00 and a break 13:00-14:00; read back the same values; a second clinic overlapping Monday is refused with 409.
3. **Slots (US3)**: with a booking at 10:00-10:30 (fake reader), `GET /api/clinics/{clinic}/slots?treatment_type_id=<30 min>&from=<Monday>&to=<Monday>` returns 09:00, 09:30, 10:30 ... and no slot in 13:00-14:00; the 90-minute type's last slot is 15:30; `first-available` returns 10 slots in time order.
4. **Leave (US4)**: `POST /api/dentists/{id}/leave` for Thursday 14:00-17:00 IST returns `appointments_to_move` with the 15:00 appointment, which stays booked; slots in that time disappear; `DELETE /api/leave/{id}` brings them back.
5. **Scale**: the load script reports p95 under 500 ms server time at 100 concurrent users with 3 clinics, 10 dentists and 1,000 appointments a week of fake bookings.
6. **Privacy**: grep the captured logs of the run for the test patient's name and phone: no match.
