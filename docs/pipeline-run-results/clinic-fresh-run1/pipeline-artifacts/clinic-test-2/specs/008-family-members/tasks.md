---

description: "Task list for Family members on a patient account (Release 2)"
---

# Tasks: Family members on a patient account (Release 2)

**Input**: Design documents from `/specs/008-family-members/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/family-members.openapi.yaml, quickstart.md

**Tests**: Included. The constitution requires business-logic tests written before or with the implementation (principle I); write each test first and see it fail.

**Organization**: Tasks are grouped by user story. Source requirement: FR-006 (US-006); related FR-004, FR-015, FR-014, FR-027, FR-031, NFR-007. All code is behind the `family_members` feature flag (Release 2).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1 to US4)
- Paths start with the repository folder: `clinic-api/` is brightsmile/clinic-api, `clinic-web/` is brightsmile/clinic-web. The layout is the one assumed in plan.md (research R-6).

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: The Release 2 flag on both sides

- [ ] T001 [P] Add the boolean setting `family_members` (default off, read per request from configuration, not a secret) in clinic-api/app/core/feature_flags.py; reuse the mechanism of feature 001 if it exists
- [ ] T002 [P] Add the `useFeatureFlag` hook that reads flags from the API in clinic-web/src/features/flags/useFeatureFlag.ts

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Person constraints, the ownership check and the contract, needed by every story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 [P] Write failing unit tests for `resolve_person`: returns a person of the caller's account; raises not-found for a person of another account, an unknown id and an inactive person, in clinic-api/tests/unit/identity/test_access.py
- [ ] T004 Create the expand-only Alembic migration clinic-api/alembic/versions/0008_family_members.py: add `is_account_holder` (boolean, default true for existing rows) if missing; check `birth_year >= 1900`; unique index on (account_id, lower(trim(name)), birth_year); index on `account_id`
- [ ] T005 Update the person (`ent-patient`) model in clinic-api/app/modules/identity/models.py with `is_account_holder`, `birth_year` integer with the check 1900 to the current year (upper limit in the service), `name` required and trimmed, `active` (depends on T004)
- [ ] T006 Implement `resolve_person(access_context, person_id)` in clinic-api/app/modules/identity/access.py so it takes the account from the token owner only and answers not-found for other accounts (depends on T003, T005)
- [ ] T007 Expose the flags to the web app with `GET /api/feature-flags` in clinic-api/app/core/feature_flags_router.py and register it in clinic-api/app/main.py (depends on T001)
- [ ] T008 [P] Merge the additions of specs/008-family-members/contracts/family-members.openapi.yaml into clinic-api/contracts/clinic-api-v1.openapi.yaml as an additive minor version change

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Add family members to my account (Priority: P1) 🎯 MVP

**Goal**: A signed-in patient adds up to 5 family members (name and birth year) and sees them listed. (source: FR-006, US-006)

**Independent Test**: Sign in as a patient, add a family member, see them listed; add 4 more; the sixth is refused; invalid input is refused with a message; two concurrent adds at 4 give exactly one success.

### Tests for User Story 1 ⚠️

> Write these tests first and make sure they FAIL before implementation

- [ ] T009 [P] [US1] Unit tests for the add rules (name not empty and trimmed, birth year 1900 to the current year, sixth refused with FAMILY_LIMIT_REACHED, duplicate refused with FAMILY_DUPLICATE ignoring case, only name and birth year stored, flag off refused) in clinic-api/tests/unit/identity/test_family_service.py
- [ ] T010 [P] [US1] Integration test that two simultaneous adds at 4 family members give exactly one success in clinic-api/tests/integration/test_family_limit_concurrency.py
- [ ] T011 [P] [US1] Contract test of `GET /api/me/people` and `POST /api/me/family-members` against clinic-api/contracts/clinic-api-v1.openapi.yaml in clinic-api/tests/contract/test_family_contract.py
- [ ] T012 [P] [US1] Component test of the Family page and form (valid add, limit message, field errors) in clinic-web/src/features/family/FamilyPage.test.tsx

### Implementation for User Story 1

- [ ] T013 [US1] Add the `FamilyMemberIn` schema (name: required, at least 1 character after trimming; birth_year: integer, 1900 to the current year) and `PersonOut` schema (id, name, birth_year, is_account_holder) in clinic-api/app/modules/identity/schemas.py
- [ ] T014 [US1] Implement add and list in clinic-api/app/modules/identity/family_service.py: one transaction that locks the account row, counts active family members (at most 5, the holder not counted), refuses a duplicate, inserts; log ids only, never name or birth year (depends on T005, T009, T013)
- [ ] T015 [US1] Implement `GET /api/me/people` and `POST /api/me/family-members` (201, 409 with code, 422, 404 when the flag is off) in clinic-api/app/modules/identity/family_router.py (depends on T007, T014)
- [ ] T016 [US1] Register the family router in clinic-api/app/main.py (depends on T015)
- [ ] T017 [P] [US1] Add the API client for the two operations in clinic-web/src/features/family/api.ts
- [ ] T018 [P] [US1] Add the English texts for the Family screen, limit and field errors in clinic-web/src/i18n/messages.en.ts
- [ ] T019 [US1] Build the add form (name, birth year, 44 px tap targets, no sideways scrolling) in clinic-web/src/features/family/AddFamilyMemberForm.tsx (depends on T017, T018)
- [ ] T020 [US1] Build the Family page listing the holder and family members, hidden when the flag is off, in clinic-web/src/features/family/FamilyPage.tsx (depends on T002, T012, T019)
- [ ] T021 [US1] Add the Family route and menu link, shown only while the flag is on, in clinic-web/src/routes.tsx (depends on T020)

**Checkpoint**: User Story 1 is fully functional and testable on its own

---

## Phase 4: User Story 2 - Choose who the visit is for when booking (Priority: P1)

**Goal**: A patient with family members chooses who the visit is for; the booking and confirmation name that person; other accounts' people are refused. (source: FR-006, FR-004, US-006)

**Independent Test**: With two family members, book for one and see the booked screen name them; book for self; send another account's person id and get a refusal; with no family members no extra question shows.

### Tests for User Story 2 ⚠️

- [ ] T022 [P] [US2] Unit tests: booking with `person_id` saves the appointment for that person, absent `person_id` books the account holder, response names the person, in clinic-api/tests/unit/booking/test_booking_for_person.py
- [ ] T023 [P] [US2] Integration test that a booking naming a person of another account, or a made-up id, is refused with 404 and creates nothing (thr-004), in clinic-api/tests/integration/test_family_authorisation.py
- [ ] T024 [P] [US2] Component test of the "who is it for" step (hidden without family members, lists holder and members, flag off) in clinic-web/src/features/booking/WhoIsItFor.test.tsx

### Implementation for User Story 2

- [ ] T025 [US2] Add optional `person_id` to the booking request and `person {id, name}` to the booking response in clinic-api/app/modules/booking/schemas.py
- [ ] T026 [US2] Book for the chosen person: call `resolve_person`, store the person on the appointment, keep the one-transaction and idempotency-key behaviour, in clinic-api/app/modules/booking/service.py (depends on T006, T022, T025)
- [ ] T027 [US2] Pass the access context to the service, answer 404 for a person outside the account, and refuse a non-holder `person_id` while the flag is off, in clinic-api/app/modules/booking/router.py (depends on T001, T023, T026)
- [ ] T028 [US2] Build the "who is it for" step in clinic-web/src/features/booking/WhoIsItFor.tsx (depends on T017, T024)
- [ ] T029 [US2] Put the step first in the booking flow, skipped for a patient with no family members or while the flag is off, in clinic-web/src/features/booking/BookingFlow.tsx (depends on T028)
- [ ] T030 [US2] Show the person's name on the booked screen in clinic-web/src/features/booking/BookedScreen.tsx (depends on T029)

**Checkpoint**: User Stories 1 and 2 both work independently

---

## Phase 5: User Story 3 - See family members' appointments in my list (Priority: P2)

**Goal**: "My appointments" shows the appointments of the patient and the family members, each with the person's name and status, and nothing from other accounts. (source: FR-004, FR-015, US-006)

**Independent Test**: Book one visit for the patient and one for a family member; both show with names; another account sees neither.

### Tests for User Story 3 ⚠️

- [ ] T031 [P] [US3] Integration test: list and single-appointment reads cover all persons of the account, upcoming and past, with person name and status, and never another account's; the account holder can reschedule and cancel a family member's appointment under the same rules as their own, another account cannot; in clinic-api/tests/integration/test_family_appointment_list.py
- [ ] T032 [P] [US3] Component test that the list shows each person's name and status in clinic-web/src/features/appointments/AppointmentList.test.tsx

### Implementation for User Story 3

- [ ] T033 [US3] List and read appointments, and authorise reschedule and cancel (feature 005 rules unchanged), by the caller's account (all its persons), including the person's name, in clinic-api/app/modules/booking/service.py (depends on T026, T031)
- [ ] T034 [US3] Return `person {id, name}` in the appointment list and detail responses in clinic-api/app/modules/booking/router.py (depends on T027, T033)
- [ ] T035 [US3] Show the person's name next to each appointment in clinic-web/src/features/appointments/AppointmentList.tsx (depends on T032, T034)

**Checkpoint**: User Stories 1 to 3 work independently

---

## Phase 6: User Story 4 - Messages for a family member's visit reach the account's phone (Priority: P2)

**Goal**: Confirmation, change notice and reminder for a family member go to the account's phone and channel and name the person; the account's reminders opt-out applies. (source: FR-006, FR-014, FR-027, FR-031)

**Independent Test**: Book for a family member; the sandbox provider log shows the confirmation sent to the account's phone in the chosen channel, naming the family member; with reminders off no reminder is created.

### Tests for User Story 4 ⚠️

- [ ] T036 [P] [US4] Unit tests: messages for a family member's appointment use the account's phone and channel, include the person name value, and no reminder is made when the account has reminders off, in clinic-api/tests/unit/messaging/test_person_name_values.py

### Implementation for User Story 4

- [ ] T037 [US4] Add the `person_name` value to confirmation, change-notice and reminder rendering and address every message to the account's phone and channel in clinic-api/app/modules/messaging/templates.py; if the registered template cannot carry the name, fall back to the link only (open question Q4) (depends on T026, T036)
- [ ] T038 [P] [US4] Add the `person_name` variable to the template definitions and note the DLT and WhatsApp template changes to submit in clinic-api/config/message_templates.yaml
- [ ] T039 [P] [US4] Record the added template value against thr-013 and in the change log in architecture.md

**Checkpoint**: All four user stories work independently

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Privacy, flag behaviour, security review and end-to-end validation

- [ ] T040 [P] Write a failing integration test that erasure on request and the 24-month idle anonymisation include family members' names and birth years in clinic-api/tests/integration/test_family_erasure.py
- [ ] T041 [P] Integration test that with the flag off the family endpoints answer 404, family bookings are refused and existing family appointments still list, in clinic-api/tests/integration/test_family_flag_off.py
- [ ] T042 [P] Test that family names and birth years never appear in log output during add, book and list in clinic-api/tests/unit/test_family_no_pii_in_logs.py
- [ ] T043 Make the erasure and idle-anonymisation job cover all persons of an account in clinic-api/app/modules/identity/erasure.py (depends on T040)
- [ ] T044 Review authorisation changes (resolve_person, booking and list scoping, flag-off paths) and record the findings in specs/008-family-members/security-review.md (depends on T027, T034, T041)
- [ ] T045 Run the validation scenarios in specs/008-family-members/quickstart.md in staging and record the result in specs/008-family-members/quickstart.md (depends on T021, T030, T035, T037, T043, T044)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup; blocks all user stories
- **User Stories (Phase 3+)**: Depend on Foundational
- **Polish (Phase 7)**: Depends on the stories it covers

### User Story Dependencies

- **US1 (P1)**: After Foundational; no other story needed. It creates the family members the other stories use in tests.
- **US2 (P1)**: After Foundational; tested with fixtures that create family members, so it does not need US1's code, but the web step reuses `api.ts` from US1 (T017).
- **US3 (P2)**: After Foundational; extends the booking service and router touched by US2 (T033 after T026, T034 after T027).
- **US4 (P2)**: After Foundational; needs the person on the appointment from US2 (T026) and the template work of feature 007.
- Features this one depends on: 002 (accounts and persons), 004 (booking endpoint), 005 (appointment list), 007 (messages and templates).

### Within Each User Story

- Tests first and failing, then schemas, services, endpoints, then web screens
- Story complete before moving to the next priority

### Parallel Opportunities

- T001, T002 together; T003 and T008 beside T004 to T006
- In US1: T009 to T012 together; T017 and T018 together
- In US2: T022 to T024 together
- US4 (T036, T038, T039) can run beside US3 once T026 is done
- Polish tests T040 to T042 together

---

## Parallel Example: User Story 1

```text
Task: "Unit tests for the add rules in clinic-api/tests/unit/identity/test_family_service.py"
Task: "Concurrency test in clinic-api/tests/integration/test_family_limit_concurrency.py"
Task: "Contract test in clinic-api/tests/contract/test_family_contract.py"
Task: "Component test in clinic-web/src/features/family/FamilyPage.test.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 and 2)

1. Complete Setup and Foundational
2. Complete US1 (add family members), then US2 (book for them): this is the smallest useful Release 2 slice for FR-006
3. Validate with quickstart scenarios 1, 2 and 5

### Incremental Delivery

1. Setup and Foundational
2. US1, then US2: deploy behind the flag
3. US3 (list), then US4 (messages, needs the template decision Q4)
4. Polish, security review, then switch the flag on for the Release 2 date (2027-03-19)

---

## Notes

- The P marker: tasks touch different files and have no dependencies
- Every task names its file path (constitution IV); `[USn]` labels link to spec.md stories
- Never log names or birth years (constitution, Definition of Done)
- Open questions assumed: Q1 separate sign-ins (Q-007), Q2 edit and remove, Q3 limit counts the holder or not, Q4 person name in message templates
