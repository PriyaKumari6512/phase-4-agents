# Tasks: Bookmark Management

**Input**: Design documents from `/specs/001-bookmark-management/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/bookmarks-api.yaml, quickstart.md
**Tests**: Included (Constitution Principle I: tests written before or with implementation; every story has an independent test).
**Organization**: Grouped by user story. Backend paths are in repo `taskflow-api/` (ARCH-001), frontend in `taskflow-web/` (ARCH-002), database via Alembic migrations (ARCH-003).

## Format: `- [ ] [ID] [P?] [Story] Description with file path`

---

## Phase 1: Setup

- [ ] T001 Add backend dependencies (FastAPI, Pydantic, SQLAlchemy, Alembic, psycopg, pytest, testcontainers, OpenTelemetry SDK) in taskflow-api/pyproject.toml
- [ ] T002 [P] Add frontend dev dependencies (Vitest, @testing-library/react, @testing-library/user-event) in taskflow-web/package.json
- [ ] T003 [P] Create empty test package directories with `__init__.py` in taskflow-api/tests/unit/__init__.py and taskflow-api/tests/integration/__init__.py

---

## Phase 2: Foundational (blocks all stories)

- [ ] T004 Create Alembic migration creating table `bookmarks` (id uuid PK generated; user_id uuid not null; url text not null; title text not null; tags text[] not null default `{}`; created_at timestamptz not null default now()), index `(user_id, created_at DESC)`, and GIN index on `tags` in taskflow-api/migrations/versions/001_create_bookmarks.py
- [ ] T005 [P] Create SQLAlchemy `Bookmark` model matching data-model.md (url ≤ 2048 chars, title ≤ 200 chars, tags each 1–30 chars, ≤ 10, source FR-001) in taskflow-api/src/models/bookmark.py
- [ ] T006 [P] Add config values for limits (MAX_TAGS=10, MAX_TAG_LEN=30, MAX_TITLE_LEN=200, MAX_URL_LEN=2048, list default 50 / max 100; FR-004) read from environment in taskflow-api/src/config.py
- [ ] T007 [P] Create pytest fixtures (PostgreSQL 16 test container, Alembic upgrade head, two test users with bearer tokens, API client) in taskflow-api/tests/integration/conftest.py
- [ ] T008 Create Pydantic schemas `BookmarkCreate`, `Bookmark`, `BookmarkList`, `Error` per contracts/bookmarks-api.yaml, including tag normalization (trim, lowercase, deduplicate, 1–30 chars, ≤ 10; FR-004) and http/https-only url validation in taskflow-api/src/api/schemas/bookmarks.py
- [ ] T009 Create bookmarks router skeleton with current-user dependency that derives `user_id` from the authenticated session (never from request body) and register it in the app in taskflow-api/src/api/bookmarks.py
- [ ] T010 [P] Add OpenTelemetry structured logging, metrics and traces for the bookmarks routes (Principle II) in taskflow-api/src/observability/bookmarks.py
- [ ] T011 [P] Create typed API client skeleton (base fetch with bearer token, `Bookmark` and `BookmarkList` types) in taskflow-web/src/services/bookmarksApi.ts
- [ ] T012 [P] Create `BookmarksPage` shell and route registration in taskflow-web/src/pages/BookmarksPage.tsx

**Checkpoint**: Foundation ready.

---

## Phase 3: User Story 1 - Save a link with title and tags (P1) 🎯 MVP

**Goal**: A user saves a link with title and optional tags (FR-001, FR-005, FR-004).
**Independent Test**: POST /bookmarks with url, title, tags ["Reading"," tech"] → 201 with tags `reading`,`tech`; missing title → 422 naming `title`; no tags → 201 with empty tags.

### Tests for User Story 1

- [ ] T013 [P] [US1] Unit tests for tag normalization and limits (case, spaces, dedupe, >10 tags, >30 chars, title >200, non-http url) in taskflow-api/tests/unit/test_bookmark_schemas.py
- [ ] T014 [P] [US1] Integration tests for POST /bookmarks (201, 422 missing url/title naming the field, empty tags) in taskflow-api/tests/integration/test_create_bookmark.py
- [ ] T015 [P] [US1] Component tests for BookmarkForm (submit, required-field messages, tags input) in taskflow-web/tests/BookmarkForm.test.tsx

### Implementation for User Story 1

- [ ] T016 [US1] Implement `create_bookmark(user_id, data)` in taskflow-api/src/services/bookmark_service.py (duplicate links allowed as separate bookmarks per research.md)
- [ ] T017 [US1] Implement POST /bookmarks returning 201 / 422 with `message` and `field` in taskflow-api/src/api/bookmarks.py (depends on T016)
- [ ] T018 [P] [US1] Add `createBookmark` to taskflow-web/src/services/bookmarksApi.ts
- [ ] T019 [P] [US1] Create BookmarkForm component (url, title, tags; user-friendly messages naming missing field, FR-005) in taskflow-web/src/components/BookmarkForm.tsx
- [ ] T020 [US1] Wire BookmarkForm into taskflow-web/src/pages/BookmarksPage.tsx (depends on T018, T019)

**Checkpoint**: US1 independently functional.

---

## Phase 4: User Story 2 - List own bookmarks filtered by tag (P2)

**Goal**: A user lists only their own bookmarks, optionally filtered by one tag (FR-002, FR-004).
**Independent Test**: GET /bookmarks returns all own; `?tag=TECH` returns only tech; unknown tag → `items: []` with UI "no bookmarks found"; second user sees none of the first user's bookmarks.

### Tests for User Story 2

- [ ] T021 [P] [US2] Integration tests for GET /bookmarks (no filter, case-insensitive tag filter, unknown tag empty, owner isolation, pagination default 50 / max 100) in taskflow-api/tests/integration/test_list_bookmarks.py
- [ ] T022 [P] [US2] Component tests for BookmarkList empty-state and TagFilter in taskflow-web/tests/BookmarkList.test.tsx

### Implementation for User Story 2

- [ ] T023 [US2] Implement `list_bookmarks(user_id, tag, limit, offset)` filtered by `user_id`, normalized tag via array containment, ordered by created_at DESC, returning items and total in taskflow-api/src/services/bookmark_service.py
- [ ] T024 [US2] Implement GET /bookmarks with `tag` (maxLength 30), `limit`, `offset` query params in taskflow-api/src/api/bookmarks.py (depends on T023)
- [ ] T025 [P] [US2] Add `listBookmarks(tag?, limit?, offset?)` to taskflow-web/src/services/bookmarksApi.ts
- [ ] T026 [P] [US2] Create BookmarkList component with "no bookmarks found" empty state in taskflow-web/src/components/BookmarkList.tsx
- [ ] T027 [P] [US2] Create TagFilter component (single tag) in taskflow-web/src/components/TagFilter.tsx
- [ ] T028 [US2] Integrate BookmarkList and TagFilter into taskflow-web/src/pages/BookmarksPage.tsx and refresh list after create (depends on T025–T027)

**Checkpoint**: US1 and US2 work independently.

---

## Phase 5: User Story 3 - Delete a bookmark (P3)

**Goal**: A user deletes their own bookmark immediately, no confirmation (FR-003).
**Independent Test**: DELETE /bookmarks/{id} → 204 and absent from all lists; repeat → 404; another user's id → 404 with identical body.

### Tests for User Story 3

- [ ] T029 [P] [US3] Integration tests for DELETE /bookmarks/{id} (204, repeat 404, foreign id 404 with identical body, absent from filtered lists) in taskflow-api/tests/integration/test_delete_bookmark.py
- [ ] T030 [P] [US3] Component tests for delete action in BookmarkList in taskflow-web/tests/BookmarkListDelete.test.tsx

### Implementation for User Story 3

- [ ] T031 [US3] Implement `delete_bookmark(user_id, id)` as hard delete filtered by `user_id`, returning not-found for missing or foreign ids in taskflow-api/src/services/bookmark_service.py
- [ ] T032 [US3] Implement DELETE /bookmarks/{id} (uuid path, 204 / 404 `message`) in taskflow-api/src/api/bookmarks.py (depends on T031)
- [ ] T033 [P] [US3] Add `deleteBookmark(id)` to taskflow-web/src/services/bookmarksApi.ts
- [ ] T034 [US3] Add delete button (no confirmation) and list refresh in taskflow-web/src/components/BookmarkList.tsx (depends on T033)

**Checkpoint**: All stories functional.

---

## Phase 6: Polish & Cross-Cutting

- [ ] T035 [P] Verify health check covers the service hosting the bookmarks routes in taskflow-api/src/api/health.py
- [ ] T036 [P] Add alert rules for error rate > 1% and p95 > 300 ms on bookmarks endpoints in taskflow-api/deploy/alerts/bookmarks.yaml
- [ ] T037 [P] Add load test at 50 req/s asserting p95 ≤ 300 ms and error rate ≤ 1% in taskflow-api/tests/performance/test_bookmarks_load.py
- [ ] T038 [P] Security review notes for owner scoping and 404 non-disclosure (Principle III) in taskflow-api/docs/bookmarks-security.md
- [ ] T039 Run quickstart.md validation scenarios from specs/001-bookmark-management/quickstart.md and record results in specs/001-bookmark-management/checklists/validation.md

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 (blocks all stories) → Phases 3–5 → Phase 6.
- US1 (P1) has no story dependencies. US2 (P2) and US3 (P3) need only Phase 2, though manual testing uses US1 to create data. Within a story: tests → service → endpoint → frontend integration.
- T016, T023, T031 share taskflow-api/src/services/bookmark_service.py; T017, T024, T032 share taskflow-api/src/api/bookmarks.py; T020 and T028 share BookmarksPage.tsx, so run those sequentially across stories.

## Parallel Examples

- Phase 2: T005, T006, T007, T010, T011, T012 together.
- US1: T013, T014, T015 together; then T018 and T019.
- US2: T021 and T022; then T025, T026, T027.
- US3: T029 and T030.

## Implementation Strategy

- **MVP**: Phases 1–2, then US1 (T001–T020); validate independently.
- **Incremental**: add US2 (T021–T028), then US3 (T029–T034), then Polish (T035–T039).
