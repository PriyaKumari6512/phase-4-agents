# Tasks: Comments and @mentions

**Input**: Design documents from `/specs/004-comments-mentions/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/comments-api.md

**Tests**: Included, because the constitution requires tests first for business logic.

**Organization**: Tasks are grouped by user story. Source ids: FR-3, US-3, NFR-3, NFR-4.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story the task belongs to

## Path Conventions

- taskflow-api: `app/`, `migrations/versions/`, `tests/`
- taskflow-web: `src/api/`, `src/features/comments/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Feature flag and module skeletons

- [ ] T001 Add the `FEATURE_COMMENTS` setting (read from env `FEATURE_COMMENTS`, default off) to `app/core/config.py` (source: FR-3)
- [ ] T002 [P] Create empty module skeletons `app/api/comments.py`, `app/services/comments.py`, `app/services/mentions.py`, `app/schemas/comment.py` in taskflow-api and register the router behind the flag in the existing router setup in `app/api/__init__.py` (depends on T001)
- [ ] T003 [P] Create the folder `src/features/comments/` and API client stub `src/api/comments.ts` in taskflow-web

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data model that all stories need

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Create the Comment and CommentMention models in `app/models/comment.py`: `comments(id UUID pk, task_id, author_id, body text required not empty after trimming max 5,000 characters, created_at timestamptz server-set)` and `comment_mentions(comment_id, mentioned_user_id, created_at, primary key (comment_id, mentioned_user_id))`
- [ ] T005 Create the Alembic migration for `comments` and `comment_mentions` with index (task_id, created_at, id) in `migrations/versions/` as a new file named `<revision>_add_comments_and_mentions.py` (depends on T004)

**Checkpoint**: Foundation ready

---

## Phase 3: User Story 1 - Post and read comments on a task (Priority: P1) MVP

**Goal**: Board members post and read comments on a task; non-members are refused.

**Independent Test**: POST then GET a comment as a board member; a non-member gets no content; empty body is rejected.

### Tests for User Story 1

- [ ] T006 [P] [US1] Integration tests for POST/GET comments (create, order oldest first, empty and over-5,000-character body rejected, non-member refused, flag off returns 404) in `tests/integration/test_comments_api.py` (source: FR-3, NFR-3)
- [ ] T007 [P] [US1] Component tests for listing and posting a comment in `src/features/comments/__tests__/comments.test.tsx`

### Implementation for User Story 1

- [ ] T008 [P] [US1] Create request and response schemas with body validation (not empty after trimming, maximum 5,000 characters) in `app/schemas/comment.py`
- [ ] T009 [US1] Implement `create_comment` and `list_comments` (order by created_at then id, limit/offset) in `app/services/comments.py` (depends on T004, T008)
- [ ] T010 [US1] Implement `GET` and `POST /api/v1/tasks/{task_id}/comments` with the board-membership check from feature 001, and 404 when `FEATURE_COMMENTS` is off, in `app/api/comments.py` (depends on T009)
- [ ] T011 [US1] Add structured logging and metrics for comment creation and rejected requests in `app/services/comments.py` (depends on T009)
- [ ] T012 [P] [US1] Implement the API client functions `listComments` and `postComment` in `src/api/comments.ts`
- [ ] T013 [P] [US1] Implement `CommentList` (author, time, text, oldest first) in `src/features/comments/CommentList.tsx` (depends on T012)
- [ ] T014 [US1] Implement `CommentForm` with empty-text and too-long error messages in `src/features/comments/CommentForm.tsx` (depends on T012)
- [ ] T015 [US1] Show the comment section on the task view of the board UI, hidden when the flag is off, by mounting `CommentList` and `CommentForm` in `src/features/comments/CommentsSection.tsx` (depends on T013, T014)

**Checkpoint**: User Story 1 works and is testable on its own

---

## Phase 4: User Story 2 - Mention teammates and notify them (Priority: P1)

**Goal**: `@username` mentions of board members create mention records and one email notification each, via the F05 outbox.

**Independent Test**: Post "Please review, @alice" and verify one notification request for Alice in the outbox and one email from the worker; mentions of non-members, the author or duplicates do not produce extra notifications.

### Tests for User Story 2

- [ ] T016 [P] [US2] Unit tests for the mention parser (case-insensitive, duplicates, trailing dot, `bob@example.com` is not a mention, non-member ignored, author excluded) in `tests/unit/test_mentions.py` (source: FR-3)
- [ ] T017 [P] [US2] Integration tests for mention notifications (one outbox row per distinct mentioned member, none for non-members or self, comment saved when the email client fails, preference opt-out respected when feature 007 is present) in `tests/integration/test_mention_notifications.py` (source: US-3, NFR-3)

### Implementation for User Story 2

- [ ] T018 [US2] Implement `parse_mentions` and `resolve_mentions` (username, case-insensitive, current board members only) in `app/services/mentions.py` (depends on T016)
- [ ] T019 [US2] Confirm the outbox enqueue interface owned by feature 005-assignment-email and record the function name and module in `specs/004-comments-mentions/research.md` (open point: not named in the implementation contract)
- [ ] T020 [US2] In `app/services/comments.py`, store `comment_mentions` and enqueue one `mention` notification per distinct mentioned member other than the author, in the same database transaction as the comment (depends on T009, T018, T019)
- [ ] T021 [P] [US2] Add the mention email template (author, task title, comment text, link to the task) to the email templates owned by feature 005 in `app/worker/templates/mention_email.py` (path assumed, align with F05; depends on T019)
- [ ] T022 [US2] Return `mentions` in the comment schema and API response in `app/schemas/comment.py` and `app/api/comments.py` (depends on T020)
- [ ] T023 [P] [US2] Render mentions highlighted in comment text in `src/features/comments/CommentList.tsx` (depends on T022)
- [ ] T024 [US2] Add structured logging and a metric for mention notifications enqueued in `app/services/comments.py` (depends on T020)

**Checkpoint**: User Stories 1 and 2 both work

---

## Phase 5: User Story 3 - Use comments and mentions with the keyboard only (Priority: P2)

**Goal**: The comment flow is keyboard-operable and announced to assistive technology (NFR-4).

**Independent Test**: Complete "post a comment with a mention" with the keyboard only; focus is visible and changes are announced.

### Tests for User Story 3

- [ ] T025 [P] [US3] Keyboard and accessibility tests (tab order, Enter/Space on the post button, live-region announcement of a new comment and of errors) in `src/features/comments/__tests__/keyboard.test.tsx`

### Implementation for User Story 3

- [ ] T026 [US3] Make `CommentForm` keyboard-operable with a labelled textarea, native button and visible focus style in `src/features/comments/CommentForm.tsx` (depends on T014)
- [ ] T027 [US3] Add an `aria-live` region that announces new comments and error messages in `src/features/comments/CommentsSection.tsx` (depends on T015)
- [ ] T028 [US3] Ensure a logical tab order between the comment list, input and post button and a focus return to the input after posting in `src/features/comments/CommentsSection.tsx` (depends on T027)

**Checkpoint**: All user stories are independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements across stories

- [ ] T029 [P] Update documentation for the comments API, the `FEATURE_COMMENTS` flag and the mention matching rule in `docs/comments-mentions.md`
- [ ] T030 Security review of membership checks and input validation across `app/api/comments.py` and `app/services/comments.py` (no existence leak for non-members)
- [ ] T031 Run the validation steps in `specs/004-comments-mentions/quickstart.md` in the dev environment

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1) has no dependencies.
- Foundational (Phase 2) depends on Setup and blocks all user stories.
- User Story 1 (P1) starts after Foundational.
- User Story 2 (P1) starts after Foundational and uses the service from User Story 1 (T009); it also needs the outbox interface from feature 005 (T019).
- User Story 3 (P2) depends on the web components from User Story 1 (T014, T015).
- Polish depends on all stories.

### Within Each Story

- Tests before implementation, models before services, services before endpoints.

### Parallel Opportunities

- T002 and T003; T006 and T007; T008 and T012; T016 and T017; T021 and T023; T025 alongside T026 once T014 is done.

## Parallel Example: User Story 1

```text
Task: "Integration tests for POST/GET comments in tests/integration/test_comments_api.py"
Task: "Component tests for listing and posting a comment in src/features/comments/__tests__/comments.test.tsx"
Task: "Create request and response schemas in app/schemas/comment.py"
Task: "Implement the API client in src/api/comments.ts"
```

## Implementation Strategy

### MVP First

1. Setup, then Foundational.
2. User Story 1: validate comment posting and reading.
3. User Story 2: mentions and notifications (completes US-3's acceptance criterion).
4. User Story 3: keyboard accessibility.
5. Polish and release behind `FEATURE_COMMENTS`.

## Notes

- Mention notifications use the outbox and email client of feature 005-assignment-email; do not create another.
- Open questions assumed: Q1 matching rule, Q2 non-members, Q3 no edit/delete (see clarifications.md).
