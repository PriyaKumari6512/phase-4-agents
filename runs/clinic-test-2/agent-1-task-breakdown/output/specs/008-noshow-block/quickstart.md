# Quickstart: validate the repeat no-show block

Prerequisites: features 001 to 005 running in a dev or staging environment; test data with two clinics (with phone numbers), one patient account with a family member, one receptionist account; `noshow_block_enabled` set to true in the API configuration (false first, to check the switch).

Contract: [contracts/noshow-block.openapi.yaml](contracts/noshow-block.openapi.yaml). Data: [data-model.md](data-model.md).

## Scenarios

1. **Block after two no-shows (US1, US4)**: create two past appointments for the family member; as a receptionist mark both as no-show (the second 15 minutes or more after start). Expect: the family member is blocked; the account holder is not.
2. **Refused online (US1)**: as the patient, open booking for the family member and choose the clinic. Expect: the page says online booking is not available and shows the clinic's phone number; no slot confirmable. Try to reschedule the family member's upcoming appointment: refused with the phone number; the appointment is unchanged. Book for the account holder: succeeds.
3. **Reception sees it (US2)**: as a receptionist open the day view, the appointment panel and patient search by the shared phone number. Expect: a "Blocked" marker on the family member only, with block date and the two no-show dates.
4. **Undo (US4)**: undo the second no-show the same day. Expect: marker gone, the patient can book.
5. **Lift (US3)**: mark the second no-show again, then lift the block. Expect: patient books at once; lift shows who and when; mark one more no-show (not blocked), then another (blocked again).
6. **Switch off**: set `noshow_block_enabled` to false. Expect: no marker, no lift control, nobody refused.
7. **Reception unaffected**: as a receptionist book and reschedule for a blocked patient: succeeds.

## Commands

- API tests: `pytest tests/noshow_policy` in brightsmile/clinic-api (unit, integration, contract).
- Web tests: the project's test runner in brightsmile/clinic-web for `src/features/noshow-block`.

Expected outcome: all scenarios behave as listed and the test suites pass in CI.
