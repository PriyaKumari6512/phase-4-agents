# Quickstart: validating the reception day feature

Run after the tasks are done, in staging or a local stack. Contracts: [contracts/reception-day.openapi.yaml](contracts/reception-day.openapi.yaml). Data and rules: [data-model.md](data-model.md).

## Prerequisites

- ctr-clinic-api and ctr-db running with migrations applied (features 001 to 003 included); ctr-web built against it.
- Seed data: clinic A and clinic B; dentists Rao (A and B on different days), Mehta (A), Iyer (B); a receptionist for A and one for B; treatment types check-up (30 min, online) and root canal (90 min, reception only); a few patients, one who has only booked at B.
- The test clock can be set (the IST clock helper is injectable in tests); in staging use appointments relative to the real time.

## Scenario 1: day view (US1)

1. Sign in as clinic A's receptionist. The day view of today opens with one column for each dentist working at A today.
2. Step to tomorrow and back. Columns change with the working days; the date is shown in IST.
3. Check that no appointment of clinic B appears, and that requesting a clinic B appointment id returns 404.

Expected: fields patient name, phone, treatment, status on every appointment; load under 2 s.

## Scenario 2: arrived, no-show, undo (US2)

1. Mark a booked appointment arrived; status shows arrived.
2. For an appointment that started 10 minutes ago, "no-show" is refused with the time from which it is allowed; at 15 minutes it succeeds.
3. Undo the no-show; status is booked. Open the history: three rows with the receptionist's name and times.
4. With the clock after midnight IST, no-show and undo for yesterday's appointment are refused.

## Scenario 3: find or create a patient (US3)

1. Search by "98450" (part of a phone number) and by "sharma"; results show name and phone.
2. Search for the patient who only booked at B: found, with no appointments shown.
3. Create a patient with a new name and phone; try again with the same phone: the existing patient is returned.

## Scenario 4: book, walk-in, move, cancel (US4)

1. Book a root canal (90 min) for a found patient 1 hour from now; it appears in the day view at once.
2. Book a walk-in in the current slot: the appointment is arrived straight away.
3. Move the first appointment to another dentist; the old slot is free.
4. Try to book an overlapping slot: 409 with next free slots.
5. Cancel one as "patient asked" and one as "clinic cancelled": statuses cancelled by the patient and cancelled by the clinic.
6. Check that the confirmation or change message was requested (feature 006 queue, or the no-op port log in staging).

## Scenario 5: dentist day (US5)

1. Sign in as Rao on a day with hours at A and B. "My day" shows both clinics with only Rao's appointments, and no action buttons.
2. A POST to an arrive endpoint as Rao returns 403.

## Scenario 6: dry run of the paper diary (SA-005)

Reception types one week of future paper-diary appointments for each clinic in the week before go-live using the book-for-patient screen and compares the day views with the paper diary (see docs/reception-dry-run.md in clinic-api).

## Automated checks

- clinic-api: unit, integration, contract, security and performance suites listed in tasks.md.
- clinic-web: component tests of the reception and dentist screens.
