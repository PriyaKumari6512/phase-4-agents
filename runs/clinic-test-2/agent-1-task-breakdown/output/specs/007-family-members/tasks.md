---

description: "Task list for Family members on a patient account"
---

# Tasks: Family members on a patient account

**Input**: Design documents from `/specs/007-family-members/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/family-members.openapi.yaml, quickstart.md

**Tests**: Included. The constitution requires tests first for business logic; write each test before its implementation and see it fail.

**Organization**: Tasks are grouped by user story. Every task names its repo: `brightsmile/clinic-api` (written `[repo: clinic-api]`) or `brightsmile/clinic-web` (`[repo: clinic-web]`). Paths are relative to that repo's root.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1 to US4)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm what features 001, 003 and 004 already built

- [ ] T001 [repo: clinic-api, clinic-web] Confirm the real file names of the patient models, booking service and router, appointment list and booking "who and what" screen built by features 001, 003 and 004, and correct the paths in `specs/007-family-members/plan.md` (Source Code section) if they differ

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Flag, schema, account check and contract that every story needs

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T002 [P] [repo: clinic-api] Add the setting `FAMILY_MEMBERS_ENABLED` (boolean, default false, read from the environment, never from a file with secrets) in `app/core/settings.py`
- [ ] T003 [repo: clinic-api] Write the forward-only Alembic migration `migrations/versions/0007_family_members.py` for `ent-patient` per data-model.md: add `is_account_holder` (boolean, not null, default false, only if feature 001 has no equivalent; backfill the holder), `removed_at` (timestamptz, nullable); add partial unique index on (account_id, lower(name), birth_year) where active is true, partial unique index on (account_id) where is_account_holder is true, and index on (account_id, active); name stays "not null, 1 to 100 characters after trimming" and birth_year "four digits, not in the future, not more than 120 years ago" (the range check is done in the service, not the database)
- [ ] T004 [P] [repo: clinic-api] Implement `person_belongs_to_account(account_id, patient_id, include_removed=False)` in `app/modules/identity/access.py`; it reads the account from the session token's owner and never from request ids (thr-004)
- [ ] T005 [repo: clinic-api] Return `features.family_members` (from T002) in the signed-in session response in `app/modules/identity/session_router.py` (depends on T002)
- [ ] T006 [P] [repo: clinic-web] Read `features.family_members` from the session response and expose it as `isFamilyEnabled()` in `src/config/featureFlags.ts` (depends on T005)
- [ ] T007 [P] [repo: clinic-api] Merge the additions of `specs/007-family-members/contracts/family-members.openapi.yaml` into `contracts/clinic-api-v1.openapi.yaml` (family endpoints, `patient_id` on booking, `person` on appointment list items) and raise the contract version to 1.1.0

**Checkpoint**: Foundation ready; user stories can start

---

## Phase 3: User Story 1 - Add and manage family members (Priority: P1) 🎯 MVP

**Goal**: A patient adds, edits, lists and removes up to 5 family members on their account.

**Independent Test**: Sign in, add 5 people, fail on a sixth and on invalid input, edit one, remove one with no upcoming appointment, add another (quickstart scenarios 1, 2).

### Tests for User Story 1 ⚠️ write first, they must fail

- [ ] T008 [P] [US1] [repo: clinic-api] Unit tests for limit of 5 (including two simultaneous adds), name 1 to 100 characters after trimming, birth year four digits not in the future and not more than 120 years ago, duplicate name and birth year, removal refused with an upcoming booked appointment, holder cannot be removed, and operations on a person of another account, in `tests/unit/identity/test_family_service.py`
- [ ] T009 [P] [US1] [repo: clinic-api] Contract tests for `GET /api/patient/people`, `POST /api/patient/family-members`, `PATCH` and `DELETE /api/patient/family-members/{personId}` (status codes 201, 204, 404, 409, 422; 404 when flag off) in `tests/contract/test_family_members_contract.py` (depends on T007)
- [ ] T010 [P] [US1] [repo: clinic-web] Component tests for the family list, the add form with field errors, the limit message and the remove refusal message in `src/tests/family/FamilyMembersPage.test.tsx`

### Implementation for User Story 1

- [ ] T011 [US1] [repo: clinic-api] Implement add, edit, remove and list in `app/modules/identity/family_service.py`: lock the account row (`SELECT ... FOR UPDATE`) before counting active non-holder persons, refuse at 5, trim and validate name and birth year, soft-remove with `active = false` and `removed_at`, refuse removal with an upcoming booked appointment (depends on T003, T004, T008)
- [ ] T012 [US1] [repo: clinic-api] Implement the endpoints of the contract in `app/modules/identity/family_router.py` and register the router; answer 404 `family_disabled` when `FAMILY_MEMBERS_ENABLED` is false; error bodies name the field and never echo the value (depends on T005, T011)
- [ ] T013 [P] [US1] [repo: clinic-web] Add the API client for the family endpoints in `src/features/family/familyApi.ts`
- [ ] T014 [P] [US1] [repo: clinic-web] Build the add/edit form with name and birth year and inline field errors, tap targets at least 44 px, in `src/features/family/FamilyMemberForm.tsx`
- [ ] T015 [US1] [repo: clinic-web] Build the family page (list with holder first, add, edit, remove with confirm, limit message when 5 are present) in `src/features/family/FamilyMembersPage.tsx` (depends on T013, T014)
- [ ] T016 [US1] [repo: clinic-web] Add the "Family members" link on the account screen in `src/features/account/AccountPage.tsx` and the route in `src/app/routes.tsx`, both shown only when `isFamilyEnabled()` is true (depends on T006, T015)

**Checkpoint**: User Story 1 works and can be tested alone

---

## Phase 4: User Story 2 - Choose who the visit is for when booking (Priority: P1)

**Goal**: The booking flow asks who the visit is for and records that person.

**Independent Test**: With one family member, book for them and for "myself"; the booked screen names the person; a foreign person id is refused (quickstart scenarios 3, 4).

### Tests for User Story 2 ⚠️ write first, they must fail

- [ ] T017 [P] [US2] [repo: clinic-api] Unit tests: booking with `patient_id` of a family member, default to the holder, refusal for a person of another account, refusal for a removed person, refusal of non-holder when flag off, block of one person does not block another, in `tests/unit/booking/test_booking_for_person.py`
- [ ] T018 [P] [US2] [repo: clinic-web] Component tests: choices "myself" plus each active family member with "myself" preselected, no choice shown when no family members or flag off, in `src/tests/booking/WhoAndWhatStep.test.tsx`

### Implementation for User Story 2

- [ ] T019 [US2] [repo: clinic-api] Accept an optional person id in the booking flow in `app/modules/booking/booking_service.py`: default the holder, check `person_belongs_to_account` for an active person, refuse otherwise with `person_not_found`, refuse non-holder when the flag is off, store the person on the appointment (depends on T004, T017)
- [ ] T020 [US2] [repo: clinic-api] Add `patient_id` to the booking request schema and map `person_not_found` and `family_disabled` to 404 in `app/modules/booking/booking_router.py` (depends on T007, T019)
- [ ] T021 [US2] [repo: clinic-web] Add the "who is this for" choice to the "who and what" step in `src/features/booking/WhoAndWhatStep.tsx`, using the people list from `src/features/family/familyApi.ts`, hidden when `isFamilyEnabled()` is false or the account has no family members, and send `patient_id` with the booking (depends on T013, T018, T020)
- [ ] T022 [US2] [repo: clinic-web] Show the name of the person the visit is for on the booked screen in `src/features/booking/BookedScreen.tsx` (depends on T021)

**Checkpoint**: Users can book for family members

---

## Phase 5: User Story 3 - See family members' appointments, and only those (Priority: P2)

**Goal**: The appointment list shows every person of the account with names; nobody sees another account's appointments.

**Independent Test**: Holder plus two family members with appointments, and a second account; the first sees exactly their three with names, the second cannot open them by list or link (quickstart scenario 4).

### Tests for User Story 3 ⚠️ write first, they must fail

- [ ] T023 [P] [US3] [repo: clinic-api] Integration tests per operation (list, view, reschedule, cancel, book) with two accounts: 0 cross-account reads or changes, past appointments of a removed person still listed, in `tests/integration/test_account_scoping.py`
- [ ] T024 [P] [US3] [repo: clinic-web] Component tests that each list row shows the person's name, including a removed person, in `src/tests/appointments/AppointmentList.test.tsx`

### Implementation for User Story 3

- [ ] T025 [US3] [repo: clinic-api] List appointments of all persons of the signed-in account (holder, active and removed family members) with `person` id and name in `app/modules/booking/appointment_list.py` (depends on T004, T023)
- [ ] T026 [US3] [repo: clinic-api] Add `app/modules/booking/appointment_access.py` that applies `person_belongs_to_account(..., include_removed=True)` to view, reschedule and cancel, answering 404 for others, and call it from the booking router `app/modules/booking/booking_router.py` (depends on T004, T020, T023)
- [ ] T027 [US3] [repo: clinic-web] Show the person's name on each row of the list in `src/features/appointments/AppointmentList.tsx` (depends on T024, T025)
- [ ] T028 [US3] [repo: clinic-web] Show the person's name on the appointment page in `src/features/appointments/AppointmentDetail.tsx` (depends on T027)

**Checkpoint**: Stories 1 to 3 work together

---

## Phase 6: User Story 4 - Erase family member data and keep it out of logs (Priority: P3)

**Goal**: Erasure removes every person's name and birth year; nothing personal reaches logs.

**Independent Test**: Erase an account with 3 family members; no name or birth year remains, appointments stay without personal link, logs from the run hold none of the values (quickstart scenario 5).

### Tests for User Story 4 ⚠️ write first, they must fail

- [ ] T029 [P] [US4] [repo: clinic-api] Unit tests: erasure clears name and birth year of the holder and all family members (active and removed), keeps appointment rows without personal link, and a later sign-in with the same phone creates a new account without family members, in `tests/unit/identity/test_erasure_family.py`
- [ ] T030 [P] [US4] [repo: clinic-api] Add a log-capture fixture in `tests/conftest.py` and a test in `tests/integration/test_no_pii_in_logs.py` that runs add, edit, remove, book-for-person and erase, then asserts the test names and birth years appear in no log line, metric label or error report

### Implementation for User Story 4

- [ ] T031 [US4] [repo: clinic-api] Extend the erasure operation in `app/modules/identity/erasure.py` to clear name and birth year of every person of the account and remove the personal link on their appointments (depends on T029)
- [ ] T032 [US4] [repo: clinic-api] Make the log lines in `app/modules/identity/family_service.py` and `app/modules/identity/family_router.py` carry person id, account id and correlation id only, and keep validation errors from echoing values (depends on T012, T030)
- [ ] T033 [P] [US4] [repo: clinic-web] Make sure the family form and client do not write names or birth years to the console or error reports in `src/features/family/familyApi.ts` and `src/features/family/FamilyMemberForm.tsx` (depends on T013, T014)

**Checkpoint**: All stories done

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Review, documentation, flag-off check, validation

- [ ] T034 [P] [repo: clinic-api] Document the endpoints, the flag, the limit of 5, the soft-remove rule and the Q-007 contingency (separate sign-ins would change sign-in and identity, 2 to 4 person-days, RSK-003) in `docs/family-members.md`
- [ ] T035 [repo: clinic-api] Add an end-to-end test with `FAMILY_MEMBERS_ENABLED=false`: no family operation works, booking is for the holder, existing family appointments still show in the list, in `tests/integration/test_family_flag_off.py`
- [ ] T036 [repo: clinic-api] Record the explicit security review of the access-control change (constitution III) in `specs/007-family-members/checklists/security-review.md` (depends on T026, T035)
- [ ] T037 Run the six scenarios of `specs/007-family-members/quickstart.md` in dev with both repos deployed and note the result in `specs/007-family-members/checklists/security-review.md` (depends on T036)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none
- **Foundational (Phase 2)**: after Setup; blocks all stories
- **US1 (P1)** after Foundational. **US2 (P1)** after Foundational and needs the family API client (T013) from US1 for the web step. **US3 (P2)** after Foundational; T026 needs T020 from US2. **US4 (P3)** after US1 (T012, T013, T014).
- **Polish**: after all stories

### Parallel Opportunities

- Foundational: T002, T004, T007 in parallel; T006 after T005.
- US1: T008, T009, T010 together; T013 and T014 together.
- US2: T017 and T018 together. US3: T023 and T024 together. US4: T029, T030 and T033 together.
- clinic-api and clinic-web tasks of one story can run in parallel by two people once the contract (T007) is merged.

## Implementation Strategy

1. Setup and Foundational, then US1 and stop to validate (MVP: family list).
2. Add US2 (booking for a person), validate, then US3 (list and scoping), then US4 (erasure and logs).
3. Keep the flag off in production until all four stories pass and Polish is done; Release 2 target is 2027-03-19, not a hard date.

## Notes

- If Q-007 is answered with separate sign-ins, stop and re-plan: identity and sign-in change (clarifications.md Q1).
- Never log or echo a family member's name or birth year.
