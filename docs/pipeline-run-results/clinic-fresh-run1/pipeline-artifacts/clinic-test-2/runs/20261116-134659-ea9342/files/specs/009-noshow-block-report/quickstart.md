# Quickstart: validate the no-show block and report

Prerequisites: the API and web app run in dev with the database migrated (feature 001 set-up); features 004 to 006 are deployed; test data has 2 clinics, 2 dentists, a receptionist, the practice manager, and a patient account with one family member. Switch the flag `r2_noshow_block_report` on for each scenario unless stated.

Run the automated checks in each repo: `pytest` in `clinic-api`, the web test command in `clinic-web`. The scenarios below are the manual acceptance run; operation details are in [contracts/noshow-block-report.openapi.yaml](contracts/noshow-block-report.openapi.yaml) and the tables in [data-model.md](data-model.md).

## 1. Block on online booking and reschedule (User Story 1)

1. As reception, mark 2 different appointments of one test patient (not the account holder) as no-show.
2. Sign in as that account and choose the blocked person, a clinic, a treatment, then reach the slot step. Expect: "online booking is not available" and the clinic's phone number; no booking is created.
3. Open "My appointments": the existing booking is still there. Try "Change time": refused with the clinic phone. Cancel still works.
4. Book for the account holder: accepted.
5. Switch the flag off: the blocked person can book and reschedule as before.

## 2. Reception shows and lifts (User Story 2)

1. As a receptionist, open the blocked patient's panel: the banner shows "blocked online since <date>" and a Lift button.
2. Press Lift. Expect the banner to go; the patient can book online at once; the lift is recorded with the receptionist and time.
3. Mark 1 new no-show: not blocked. Mark a second: blocked again.
4. Mark a no-show that creates a block, then undo it the same day: the block is gone and no lift record exists.
5. Book for a blocked patient at the desk: accepted.

## 3. No-show report (User Story 3)

1. Seed appointments in 2 clinics over several months with no-shows, arrivals, a walk-in, and both kinds of cancellation.
2. As the practice manager, open the no-show report: 12 months for each clinic, each with a count and a rate; the current month is marked "month so far". Compare with hand-counted figures.
3. A month with only cancelled appointments shows count 0 and no rate.
4. Anonymise a patient with no-shows (deletion on request): the figures do not change.
5. As a receptionist, a dentist and a patient: opening the report is refused. There is no export button.

## Expected outcomes

Match the acceptance scenarios in [spec.md](spec.md) and success criteria SC-001 to SC-008.
