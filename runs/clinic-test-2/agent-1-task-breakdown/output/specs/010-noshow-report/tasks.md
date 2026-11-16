---

description: "Task list for the no-show report per clinic and month (MOD-08, Release 2)"
---

# Tasks: No-show report per clinic and month

**Input**: Design documents from `/specs/010-noshow-report/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/no-show-report.openapi.yaml, quickstart.md

**Tests**: Included. The constitution requires tests first for business logic; each user story has an independent test.

**Organization**: Tasks are grouped by user story. Every task states its repository: `clinic-api` = brightsmile/clinic-api (ctr-clinic-api), `clinic-web` = brightsmile/clinic-web (ctr-web). Paths are relative to that repository root.

**Source requirement**: FR-032 (REQ-028). Estimate: 3–5 person-days (scope/estimate.md, MOD-08).

## Format: `- [ ] T001 [P] [US1] Description with file path`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[USn]**: The user story the task belongs to

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: The two feature flags (Release 2 screen hidden until ready).

- [ ] T001 [P] Check the real layout of `app/modules/` and the appointment status values in `app/modules/booking/` (expected: booked, arrived, no_show, cancelled_by_patient, cancelled_by_clinic), then add the setting `noshow_report_enabled` (bool, default `false`, read from the environment, no secret) in `app/core/config.py` (repo: clinic-api)
- [ ] T002 [P] Add the flag `noShowReportEnabled` (build-time, default `false`) in `src/config/featureFlags.ts` (repo: clinic-web)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The reporting module shell, response models and contract that every story uses.

**CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T003 Create the `cmp-reporting` module shell: `app/modules/reporting/__init__.py` and `app/modules/reporting/router.py` with an empty router under prefix `/api/reports`, and register it in `app/main.py` (repo: clinic-api) (depends on T001)
- [ ] T004 [P] Define the response models `NoShowReport`, `ClinicNoShowReport` and `MonthlyNoShow` (fields `month` as `YYYY-MM`, `no_shows` ≥ 0, `non_cancelled` ≥ 0, `rate` number or null, `partial` bool; 12 months per clinic) in `app/modules/reporting/schemas.py` per data-model.md (repo: clinic-api)
- [ ] T005 [P] Merge the path `/api/reports/no-shows` and its schemas from `specs/010-noshow-report/contracts/no-show-report.openapi.yaml` into `contracts/clinic-api-v1.openapi.yaml` (repo: clinic-api)

**Checkpoint**: Foundation ready; user stories can start.

---

## Phase 3: User Story 1 - Monthly no-show figures per clinic (Priority: P1) 🎯 MVP

**Goal**: The API returns, per clinic and each of the last 12 IST months, no-shows, non-cancelled appointments and the rate.

**Independent Test**: Load appointments in all five statuses for two clinics over several months, call `GET /api/reports/no-shows` (flag on, as practice manager) and compare each figure with a hand count (quickstart scenario 1).

### Tests for User Story 1

> Write these tests first and see them fail before the implementation.

- [ ] T006 [P] [US1] Unit tests for the window (current IST month plus 11 before, newest first, only the current month `partial`) and the rate (4 ÷ 32 = 12.5; half-up rounding to one decimal; `null` when the denominator is 0) in `tests/unit/reporting/test_calc.py` (repo: clinic-api)
- [ ] T007 [P] [US1] Integration test of the count query against PostgreSQL in `tests/integration/booking/test_appointment_counts_by_month.py`: both cancel kinds excluded, walk-in counted, a 23:30 IST month-end appointment in its IST month, an anonymised appointment counted, two clinics kept apart (repo: clinic-api)
- [ ] T008 [P] [US1] Contract test that the response of `GET /api/reports/no-shows` matches `contracts/clinic-api-v1.openapi.yaml` in `tests/contract/test_noshow_report_contract.py` (repo: clinic-api) (depends on T005)

### Implementation for User Story 1

- [ ] T009 [US1] Implement the read-only function `count_appointments_by_clinic_month(window_start, window_end)` in `app/modules/booking/reporting_interface.py`: one grouped query by clinic id, `date_trunc('month', start_at AT TIME ZONE 'Asia/Kolkata')` and status, returning counts only, no patient fields (repo: clinic-api)
- [ ] T010 [P] [US1] Implement the pure functions `report_window(now)` and `no_show_rate(no_shows, non_cancelled)` in `app/modules/reporting/calc.py` (repo: clinic-api)
- [ ] T011 [US1] Implement `ReportService.build_report()` in `app/modules/reporting/service.py`: take the clinic list from the `cmp-scheduling` in-process interface, take counts from `cmp-booking` (T009), treat `no_show` as no-shows and booked, arrived and no_show as non-cancelled, fill months without appointments with 0, 0, null, set `partial` on the current month (repo: clinic-api) (depends on T004, T009, T010)
- [ ] T012 [US1] Implement `GET /api/reports/no-shows` returning `NoShowReport` in `app/modules/reporting/router.py` (repo: clinic-api) (depends on T003, T011)
- [ ] T013 [US1] Add structured logging (`report_generated` with correlation id, clinic count and duration only; no patient data), an OpenTelemetry span and a duration metric to `app/modules/reporting/service.py` (repo: clinic-api)

**Checkpoint**: User Story 1 works and is testable through the API alone.

---

## Phase 4: User Story 2 - No-show report screen for the practice manager (Priority: P1)

**Goal**: The practice manager opens the "no-show report" screen and reads one 12-month table per clinic; the screen and the endpoint are hidden while the flag is off.

**Independent Test**: Sign in as practice manager with the flags on, open the screen and check each clinic shows 12 rows matching the API; switch the flags off and check the menu entry is gone, the address shows "not found" and the API answers 404 (quickstart scenario 2).

### Tests for User Story 2

- [ ] T014 [P] [US2] Integration test that the endpoint answers 404 when `noshow_report_enabled` is false and 200 when true, in `tests/integration/reporting/test_noshow_report_flag.py` (repo: clinic-api)
- [ ] T015 [P] [US2] Component tests with a mocked API in `src/pages/NoShowReport/NoShowReportPage.test.tsx`: 12 rows per clinic, a dash for a `null` rate, "month so far" on the partial month, a plain error message with a retry button on failure, no export or download control (repo: clinic-web)

### Implementation for User Story 2

- [ ] T016 [US2] Add the flag dependency (404 when `noshow_report_enabled` is false) in `app/modules/reporting/dependencies.py` and apply it to the router in `app/modules/reporting/router.py` (repo: clinic-api) (depends on T012)
- [ ] T017 [P] [US2] Add the API client `getNoShowReport()` and its types, matching `contracts/no-show-report.openapi.yaml`, in `src/api/noShowReport.ts` (repo: clinic-web)
- [ ] T018 [US2] Build the page in `src/pages/NoShowReport/NoShowReportPage.tsx`: one table per clinic, newest month first, columns month, no-shows, appointments not cancelled, rate in percent; dash when the rate is null; "month so far" label; error message with retry; English text, desktop layout; no export (repo: clinic-web) (depends on T017)
- [ ] T019 [US2] Add the route and the "No-show report" menu entry, both shown only when `noShowReportEnabled` is true, in `src/routes/staffRoutes.tsx` and `src/components/StaffMenu.tsx`; a direct address shows "not found" when the flag is off (repo: clinic-web) (depends on T002, T018)

**Checkpoint**: User Stories 1 and 2 work together behind the flags.

---

## Phase 5: User Story 3 - Only the practice manager can read the report (Priority: P2)

**Goal**: Receptionists, dentists, patients and unsigned callers get no figures, neither from the screen nor from the API.

**Independent Test**: Call the endpoint as each of the four roles and unsigned: only the practice manager gets figures; receptionist and dentist see no menu entry (quickstart scenario 3).

### Tests for User Story 3

- [ ] T020 [P] [US3] Role matrix integration test in `tests/integration/reporting/test_noshow_report_rbac.py`: practice manager 200, receptionist 403, dentist 403, patient 403, unsigned 401, and no figures in any refused response (repo: clinic-api)
- [ ] T021 [P] [US3] Component test that the menu entry is shown only to the practice manager when the flag is on, in `src/components/StaffMenu.test.tsx` (repo: clinic-web)

### Implementation for User Story 3

- [ ] T022 [US3] Add the practice-manager-only dependency (role and active flag re-read through the `cmp-identity` access context) in `app/modules/reporting/dependencies.py` and apply it to the endpoint in `app/modules/reporting/router.py` (repo: clinic-api) (depends on T016)
- [ ] T023 [US3] Show the menu entry and allow the route only for the practice manager role in `src/components/StaffMenu.tsx` and `src/routes/staffRoutes.tsx` (repo: clinic-web) (depends on T019)

**Checkpoint**: All user stories work independently and together.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Performance, rollout notes and final validation.

- [ ] T024 [P] Performance test in `tests/integration/reporting/test_noshow_report_perf.py`: 3 clinics and 52,000 appointments, report returned within 3 s for 95% of 50 calls (spec SC-002); add an index only if this fails (repo: clinic-api) (depends on T012)
- [ ] T025 [P] Write `docs/noshow-report.md`: the flag settings in both repos, how to switch the report on, the counting rules (ASM-004, ASM-014, IST months), and the note that the baseline is the first 2 months of app data (ASM-015) (repo: clinic-api)
- [ ] T026 Run the quickstart.md scenarios 1 to 3 against local clinic-api and clinic-web and record the result in `specs/010-noshow-report/quickstart.md` (repo: clinic-api) (depends on T013, T022, T023)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none; T001 and T002 run in parallel.
- **Foundational (Phase 2)**: after Setup; blocks all stories.
- **User Story 1 (P1)**: after Foundational; no dependency on other stories.
- **User Story 2 (P1)**: web tasks (T015, T017, T018, T019) need only Foundational and T002 and can run in parallel with US1; T016 needs T012 from US1.
- **User Story 3 (P2)**: T022 follows T016; T023 follows T019.
- **Polish**: after the stories it checks.

### Within Each Story

- Tests are written first and must fail before implementation.
- Counts (T009) and pure functions (T010) before the service (T011); service before the endpoint (T012).

### Parallel Opportunities

- T001 and T002; T004 and T005; T006, T007, T008; T009 and T010; T014 and T015; T017 alongside backend tasks; T020 and T021; T024 and T025.

---

## Parallel Example: User Story 1

```text
Task: "Unit tests in tests/unit/reporting/test_calc.py"            (clinic-api)
Task: "Integration test in tests/integration/booking/test_appointment_counts_by_month.py"   (clinic-api)
Task: "Pure functions in app/modules/reporting/calc.py"            (clinic-api)
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 and 2.
2. Phase 3: the API figures. Stop and validate with quickstart scenario 1.

### Incremental Delivery

1. Add User Story 2: the screen behind the flags. Validate scenario 2.
2. Add User Story 3: manager-only access. Validate scenario 3. Do not switch the flags on in production before US3 is done, because until then the endpoint is open to any signed-in role.
3. Polish, then switch the report on when ready (Release 2, target 2027-03-19, not hard).

---

## Notes

- Open questions assumed: Q-015 walk-ins counted (SA-004), no-show baseline from the first 2 months, current month shown as partial (see clarifications.md).
- No new table or migration; no export (non-goal).
- Ship order: US3 must be complete before the flags are turned on.
