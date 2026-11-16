# Quickstart: validating family members

Prerequisites: features 001 (sign-in, account/person split), 003 (booking) and 004 (appointment list) deployed in the dev environment; API setting `FAMILY_MEMBERS_ENABLED=true`; a test patient signed in with the test SMS code; a second test patient on another phone number.

Contracts: [family-members.openapi.yaml](contracts/family-members.openapi.yaml). Data: [data-model.md](data-model.md).

## Scenarios

1. **Add and limit (US1)**: In "Family members" add 5 people with valid names and birth years. Expect 5 in the list. Add a sixth: expect the limit message and an unchanged list. Try an empty name, birth year 2999 and birth year 1800: expect a field error each.
2. **Edit and remove (US1)**: Edit a name; expect it in the list. Remove a person with no upcoming appointment: expect it gone and room for a new one. Book for another person, then try to remove them: expect a refusal naming the cancel step.
3. **Book for a family member (US2)**: Start "Book"; at "who and what" choose a family member, a check-up, a slot, confirm. Expect the booked screen to name that person. With a patient that has no family members, expect no "who" choice.
4. **Account scoping (US2, US3)**: As patient B, call booking with patient A's family member id, and open patient A's appointment link: expect 404 both times. Patient A's "My appointments" lists holder and family appointments with names; patient B's lists only theirs.
5. **Erasure and logs (US4)**: Run erasure for patient A's account in the admin screen; expect no name or birth year of any person in the database for that account, appointments kept without personal link. Search the API log of the test run for the test names: expect none.
6. **Flag off (US1)**: Set `FAMILY_MEMBERS_ENABLED=false`; expect no family link or "who" choice, and `POST /api/patient/family-members` answering 404.

## Commands

- API (repo `brightsmile/clinic-api`): `pytest tests/unit tests/contract tests/integration -k "family or scoping"`
- Web (repo `brightsmile/clinic-web`): the repo's test command for `src/tests/family` and `src/tests/booking`
