# Quickstart: validate the no-show report

Contracts: [contracts/no-show-report.openapi.yaml](./contracts/no-show-report.openapi.yaml). Data rules: [data-model.md](./data-model.md).

## Prerequisites

- repo brightsmile/clinic-api running locally against a PostgreSQL 16 test database with the existing migrations.
- repo brightsmile/clinic-web running locally against that API.
- Test data: two clinics; appointments across 13 months in all five statuses, including one walk-in no-show, one appointment at 23:30 IST on a month's last day, and one anonymised appointment. Staff accounts: one practice manager, one receptionist, one dentist.
- Setting `noshow_report_enabled=true` for the API and the web flag on (both default off).

## Scenario 1: figures (User Story 1)

1. Sign in as the practice manager and call `GET /api/reports/no-shows`.
2. Expect 2 clinics, each with 12 months, newest first, the first one with `partial: true`.
3. Compare a month with the hand count: for 40 appointments with 4 no-shows, 6 cancelled by the patient and 2 by the clinic, expect `no_shows: 4`, `non_cancelled: 32`, `rate: 12.5`.
4. Expect the 23:30 IST appointment in the IST month, the walk-in no-show counted, the anonymised appointment counted, and an empty month with `rate: null`.

## Scenario 2: screen (User Story 2)

1. Open the web app as the practice manager and choose "No-show report" in the menu.
2. Expect one table per clinic with 12 rows, a dash for an empty month, "month so far" on the first row, no export or download control.
3. Stop the API and reload: expect a plain error message and a retry button.
4. Turn the flag off: expect no menu entry; the direct address shows "not found"; the API answers 404.

## Scenario 3: access (User Story 3)

1. Call the endpoint as receptionist, dentist, patient and without signing in: expect 403, 403, 403 and 401, with no figures.
2. Sign in to the web app as receptionist and dentist: expect no menu entry.

## Run the tests

- clinic-api: `pytest tests/unit/reporting tests/integration/booking tests/integration/reporting tests/contract/test_noshow_report_contract.py`
- clinic-web: the repo's component test command for `src/pages/NoShowReport`.
