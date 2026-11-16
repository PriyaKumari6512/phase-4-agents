# Quickstart: validating family members

Prerequisites: features 002 (patient sign-in, account and person), 004 (online booking), 005 (appointment list) and 007 (messages) running in staging with sandbox providers; flag `family_members` on; two test accounts A (two or more family members possible) and B.

Contracts: [contracts/family-members.openapi.yaml](./contracts/family-members.openapi.yaml). Data: [data-model.md](./data-model.md).

## Scenario 1: add family members (US1)
1. Sign in as A, open Family, add "Asha", birth year 2015. Expected: Asha appears under the holder.
2. Add four more. Expected: 5 family members listed.
3. Add a sixth. Expected: refused with the limit message; list unchanged.
4. Add one with an empty name, then birth year 1850 and a future year. Expected: field messages; nothing saved.
5. Send two adds at once when A has 4. Expected: exactly one succeeds.

## Scenario 2: book for a family member (US2)
1. As A, choose Book. Expected: "who is the visit for" lists A and each family member.
2. Choose Asha, finish the booking. Expected: the booked screen and the confirmation name Asha; the appointment is for Asha.
3. As B, send a booking with Asha's person id. Expected: refused (404), nothing created.
4. Sign in as a patient with no family members. Expected: no extra question.

## Scenario 3: appointment list (US3)
1. As A, open My appointments. Expected: A's and Asha's upcoming and past appointments, each with the person's name and status.
2. As B, open the list. Expected: none of A's appointments.

## Scenario 4: messages (US4)
1. After booking for Asha, check the sandbox SMS or WhatsApp provider log. Expected: the confirmation went to A's phone in the chosen channel and names Asha.
2. Set reminders off for A. Expected: no reminder for Asha's appointment; confirmation and change notices still sent.

## Scenario 5: flag off (FR-011)
1. Switch the flag off. Expected: no Family screen, no "who is it for" step; the family endpoints answer 404; the earlier appointments still show.

## Scenario 6: logs and erasure
1. Search the test run logs for the names and birth years used. Expected: none found.
2. Run the erasure for account A. Expected: Asha's name and birth year are removed or anonymised with the account.

## Automated checks
- API unit and integration tests (limit, duplicate, validation, ownership, flag, concurrency) and the contract test against the OpenAPI file run in CI.
- Web component tests for the Family page, the "who is it for" step and the list.
