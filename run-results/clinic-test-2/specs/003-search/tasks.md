---

description: "Task list for Full-text task search"
---

# Tasks: Full-text task search

**Input**: Design documents from `/specs/003-search/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/search-api.md

**Tests**: Included. The constitution requires tests first for business logic and an independent test per user story, and the spec requires a load test (FR-012).

**Organization**: Tasks are grouped by user story. API paths are relative to acme/taskflow-api, web paths (`src/...`) to acme/taskflow-web.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story the task belongs to
- Cross-feature prerequisites: the `tasks` table (002-tasks-board) and board membership/auth (001-platform-foundation) must exist; they are reused, not recreated.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Configuration and shared test data

- [ ] T001 Add search settings `SEARCH_CACHE_TTL_SECONDS` (default 60), `SEARCH_TS_CONFIG` (default english), `SEARCH_DEFAULT_LIMIT` (20), `SEARCH_MAX_LIMIT` (50), `SEARCH_MAX_QUERY_LENGTH` (200) in app/core/config.py
- [ ] T002 [P] Create test data factory for boards, members and tasks with chosen titles and descriptions in tests/fixtures/search_data.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Index migration and response schemas that all stories need

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 Create Alembic migration adding generated stored column `search_vector` (title weight A, description weight B, english configuration) and GIN index `ix_tasks_search_vector` on `tasks`, with downgrade, in migrations/versions/003_task_search_index.py (depends on the tasks table migration of 002-tasks-board)
- [ ] T004 [P] Add migration test checking the column, the index, and that title/description edits update `search_vector` in tests/integration/test_search_migration.py (depends on T003)
- [ ] T005 [P] Create request and response schemas (`q` 1-200 chars, `limit` 1-50 default 20, `offset` >= 0 default 0, `board_id` optional, result item and page) in app/schemas/search.py

**Checkpoint**: Foundation ready

---

## Phase 3: User Story 1 - Search tasks by keyword (Priority: P1) 🎯 MVP

**Goal**: A signed-in user gets ranked tasks matching words in title or description.

**Independent Test**: Seed tasks, search a word present in one title and another description, and verify both are returned with the title match first, plus empty-state and deleted-task behavior.

### Tests for User Story 1

- [ ] T006 [P] [US1] Unit tests for query normalisation (trim, empty rejected, over 200 chars rejected, special characters and SQL metacharacters kept as plain text) in tests/unit/test_search_query.py
- [ ] T007 [P] [US1] Integration tests for title match, description match, title-ranked-first, no match, edited and deleted tasks, paging and total in tests/integration/test_search_endpoint.py

### Implementation for User Story 1

- [ ] T008 [US1] Implement query normalisation and validation in app/services/search_query.py
- [ ] T009 [US1] Implement search service with `websearch_to_tsquery`, `ts_rank`, `ts_headline` excerpt, stable ordering (rank desc, task id) and paging with total in app/services/search.py (depends on T003, T005, T008)
- [ ] T010 [US1] Implement router `GET /api/v1/search/tasks` with 422 validation errors and register it in app/api/search.py and app/main.py (depends on T009)

**Checkpoint**: User Story 1 is functional via the API

---

## Phase 4: User Story 2 - Results limited to my boards (Priority: P1)

**Goal**: Search never returns tasks from boards the user is not a member of.

**Independent Test**: Two users on separate boards with the same keyword each see only their own board's tasks; a foreign `board_id` returns 404; unauthenticated calls return 401.

### Tests for User Story 2

- [ ] T011 [P] [US2] Integration tests for per-user isolation, foreign `board_id` returning the same 404 as an unknown board, removed member, and unauthenticated 401 in tests/integration/test_search_authorization.py

### Implementation for User Story 2

- [ ] T012 [US2] Restrict the SQL to `board_id = ANY(member board ids)` using the membership service of 001-platform-foundation (reuse, no new membership code) in app/services/search.py (depends on T009)
- [ ] T013 [US2] Require authentication on the router and return 404 for a `board_id` outside the user's boards in app/api/search.py (depends on T010, T012)

**Checkpoint**: User Stories 1 and 2 work and are secure

---

## Phase 5: User Story 3 - Search stays fast at 10,000 tasks (Priority: P1)

**Goal**: p95 under 300 ms at 10,000 tasks, with a safe Redis cache and a repeatable load test.

**Independent Test**: Run the load test against 10,000 seeded tasks and verify p95 < 300 ms and errors < 1%; verify cache hit, invalidation and Redis-down fallback.

### Tests for User Story 3

- [ ] T014 [P] [US3] Integration tests for cache hit and miss, invalidation after task create/update/move/delete, no cross-user or removed-member leakage, and fallback when Redis is down in tests/integration/test_search_cache.py
- [ ] T015 [P] [US3] Integration test that EXPLAIN of the search query uses `ix_tasks_search_vector` in tests/integration/test_search_index_usage.py (depends on T003)

### Implementation for User Story 3

- [ ] T016 [P] [US3] Implement Redis cache: key `search:v1:{sha256(user, member board ids, board versions, query, filter, limit, offset)}`, TTL from `SEARCH_CACHE_TTL_SECONDS`, `bump_board(board_id)` counter `search:ver:{board_id}`, errors fall back silently in app/services/search_cache.py
- [ ] T017 [P] [US3] Implement search telemetry: structured log fields (latency, cache hit or miss, result count, no task content), latency metric and OpenTelemetry span in app/services/search_telemetry.py
- [ ] T018 [US3] Use the cache in the search service (read before query, write after) in app/services/search.py (depends on T012, T016)
- [ ] T019 [US3] Call `search_cache.bump_board(board_id)` on task create, update, move and delete, as a small coordinated edit to the task service owned by 002-tasks-board in app/services/tasks.py (depends on T016)
- [ ] T020 [US3] Wire telemetry and the `X-Search-Cache` response header in app/api/search.py (depends on T013, T017, T018)
- [ ] T021 [P] [US3] Create seed script that loads 10,000 tasks over several boards with realistic titles and descriptions in tests/performance/seed_tasks.py
- [ ] T022 [US3] Create load test issuing concurrent title-word searches against the seeded data and asserting p95 < 300 ms and error rate < 1% in tests/performance/test_search_load.py (depends on T020, T021)
- [ ] T023 [US3] Document how to run the seed and load test in dev and stg and how to read the result in docs/search-performance.md (depends on T022)

**Checkpoint**: Performance target is verified

---

## Phase 6: User Story 4 - Keyboard-usable search interface (Priority: P2)

**Goal**: Search box and results list that work with keyboard only and assistive technology.

**Independent Test**: With only the keyboard, focus the search, type, arrow to a result, press Enter to open the task, Escape to close; automated accessibility check passes.

### Tests for User Story 4

- [ ] T024 [P] [US4] Component tests for keyboard flow (`/` shortcut, typing, arrow keys, Enter, Escape returns focus) in src/features/search/__tests__/SearchBox.test.tsx

### Implementation for User Story 4

- [ ] T025 [P] [US4] Create search API client for `GET /api/v1/search/tasks` in src/api/search.ts
- [ ] T026 [P] [US4] Create `useTaskSearch` hook with 250 ms debounce, request cancellation, loading, empty and error states in src/features/search/useTaskSearch.ts (depends on T025)
- [ ] T027 [US4] Create SearchBox component with combobox semantics, visible focus and `/` shortcut in src/features/search/SearchBox.tsx (depends on T026)
- [ ] T028 [US4] Create SearchResults list (listbox, arrow-key navigation, Enter opens task, safe rendering of the highlighted excerpt, `aria-live` result count) in src/features/search/SearchResults.tsx (depends on T026)
- [ ] T029 [US4] Mount the search box in the board page, a small coordinated edit to the board UI owned by 002-tasks-board, in src/features/board/BoardPage.tsx (depends on T027, T028)
- [ ] T030 [US4] Add automated accessibility test (WCAG 2.1 AA rules) for the search UI in src/features/search/__tests__/search.a11y.test.tsx (depends on T029)

**Checkpoint**: All user stories functional

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T031 [P] Document the search endpoint, assumptions (language, TTL, page size) and cache invalidation in docs/search.md
- [ ] T032 Add a readiness check that the search index exists to the API health endpoint (small coordinated edit to the foundation) in app/api/health.py
- [ ] T033 Record the explicit security review of the membership filter and cache key (constitution III) in docs/security-review-search.md
- [ ] T034 Run the quickstart.md validation scenarios in dev and record results in specs/003-search/quickstart.md

---

## Dependencies & Execution Order

- Setup, then Foundational (blocks all stories), then stories, then Polish.
- US1 first (MVP). US2 builds on the US1 service and router. US3 builds on US2 (cache key uses member boards). US4 needs the US1 endpoint only and can start in parallel with US2/US3 using the contract.
- Tests in each story are written before implementation.

## Parallel Example

```text
After Phase 2: T006, T007 together; T011 with T014, T015, T021 (different files).
US4 (T024, T025) can run alongside US2 and US3 work.
```

## Implementation Strategy

1. MVP: Phases 1-3 (API search), then US2 so nothing ships without membership enforcement.
2. Add US3 (cache and load test) to confirm the 300 ms target.
3. Add US4 UI; finish with Polish.
