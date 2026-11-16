# Quickstart: validating Reception day view, check-in, no-show and dentist day

A validation guide, not an implementation. Contracts: [contracts/reception-dentist-day.openapi.yaml](./contracts/reception-dentist-day.openapi.yaml). Data: [data-model.md](./data-model.md).

## Prerequisites

- Features 001 (platform), 002 (staff sign-in, access context), 003 (clinics, dentists, hours, treatment types, free slots) and 005 (appointment status history) available in the environment; messaging (007) may be a stub that only records requests.
- Test data: two clinics A and B; receptionist RA (clinic A) and RB (clinic B); dentist D1 working at A and B today; dentists D2, D3 at A; treatment types: check-up (30 min, online), root canal (90 min, reception only); patients with and without appointments at each clinic.
- Backend test run in brightsmile/clinic-api (pytest, with a real PostgreSQL 16 database with `btree_gist`); web tests in brightsmile/clinic-web.

## Scenarios

1. **Day view (US1)**: sign in as RA, open today's view. Expect one column each for D1, D2, D3; D1 shows only clinic A appointments; next/previous day and date picker work; a Sunday shows "no dentists working". Expected response size for 6 × 16 appointments about 15 KB, load within 2 s.
2. **Scoping (US1–US6, SC-005)**: as RA, call every `/reception/appointments/{id}...` endpoint with an appointment id of clinic B: each returns 404 and nothing changes. As a dentist and as a patient, call every reception endpoint: 403.
3. **Arrived (US2)**: mark a booked appointment of today arrived; status changes; event row has RA and time. A future-dated appointment: refused (422).
4. **No-show (US3)**: with an appointment that started 10 minutes ago: refused with `allowed_from`; at 15 minutes: allowed; undo the same day: back to booked; with a yesterday appointment: refused. Arrived and cancelled appointments: refused.
5. **Stale status (US2, US3)**: open the same appointment in two sessions, mark arrived in one, mark no-show in the other: the second gets 409 with `current_status = arrived`.
6. **Patient search and create (US4)**: search "98" (refused, under 3 characters); search by 4 digits of a phone and by part of a name: name and phone only; a patient with appointments only at clinic B is found, no appointments shown. Create with an existing phone: existing patient returned (200).
7. **Booking (US5)**: book root canal (90 min) for tomorrow with D2; book a slot starting in 2 hours (accepted); book a date 45 days ahead (accepted); walk-in: appointment status arrived with two event rows. Two parallel requests for one slot: one 201, one 409 with next free slots. A run of 1,000 concurrent attempts leaves 0 overlaps.
8. **Reschedule and cancel (US6)**: move to D3's free slot (old slot free at once); cancel with `cancelled_by = patient` and `clinic`: matching statuses; reschedule or cancel of an arrived appointment: refused; messaging stub records a request for each change.
9. **Dentist day (US7)**: sign in as D1: grouped by clinic A and B, own appointments only, no phone numbers, no write endpoint accessible.
10. **Logging**: run scenarios 6 and 7 with log capture; no name or phone in any log line.
11. **Paper-diary dry run (SC-007)**: in the week before go-live, reception types the next week's paper-diary appointments of both clinics; each day's view is compared with the paper diary.

## Expected outcomes

All acceptance scenarios in spec.md pass; contract tests pass against the OpenAPI fragment merged into `contracts/clinic-api-v1.openapi.yaml`.
