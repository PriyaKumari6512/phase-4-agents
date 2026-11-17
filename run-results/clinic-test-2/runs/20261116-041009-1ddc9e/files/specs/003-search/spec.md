# Feature Specification: Full-text task search

**Feature Branch**: `003-search`

**Created**: 2026-01-01

**Status**: Draft

**Input**: User description: "Full-text task search. FR-4: Full-text search over task titles and descriptions of the user's boards (US-4). US-4 (Must): As a team member, I want to search tasks so that I can find any task quickly; given 10,000 tasks, when I search by a word in the title, results appear in under 300 ms (p95). NFR-1: search p95 under 300 ms for 10,000 tasks. NFR-3: only board members see tasks. NFR-4: keyboard-usable UI."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Search tasks by keyword (Priority: P1)

A team member types one or more words into a search box and gets a ranked list of tasks whose title or description contains those words, across all boards they belong to. Each result shows the task title, the board it belongs to, its column and a short excerpt with the matching words highlighted, and opens the task when chosen.

**Why this priority**: This is the core of US-4 and FR-4: without it nobody can find a task quickly.

**Independent Test**: Seed a board with tasks, search for a word that appears in one task title and another task description, and verify both are returned with the title match ranked first.

**Acceptance Scenarios**:

1. **Given** I am a member of a board with a task titled "Prepare invoice report", **When** I search for "invoice", **Then** that task appears in the results. (source: FR-4, US-4)
2. **Given** a task whose description (not title) contains "migration", **When** I search for "migration", **Then** the task appears in the results. (source: FR-4)
3. **Given** two tasks, one with the search word in the title and one only in the description, **When** I search for that word, **Then** the title match is listed first. (source: FR-4)
4. **Given** no task matches my words, **When** I search, **Then** I see an empty-state message and no error. (source: FR-4)
5. **Given** a task is edited or deleted, **When** I search again, **Then** results reflect the change and never show a deleted task. (source: FR-4)

---

### User Story 2 - Results limited to my boards (Priority: P1)

Search only ever returns tasks from boards where the user is a member. Tasks on other boards are never returned, counted, or revealed through excerpts, error messages or cached responses.

**Why this priority**: Task data is confidential (NFR-3); a leak would be a security incident.

**Independent Test**: Create two users on different boards with the same keyword in both boards' tasks; each user must only see their own board's tasks, including when the other user's identical query was cached.

**Acceptance Scenarios**:

1. **Given** user A is on board 1 and user B is on board 2, both with a task containing "budget", **When** A searches "budget", **Then** only the board 1 task is returned. (source: NFR-3, FR-4)
2. **Given** I search with a board filter for a board I am not a member of, **When** the request is made, **Then** the system refuses it without revealing whether the board or any matching task exists. (source: NFR-3)
3. **Given** I was removed from a board, **When** I search again, **Then** that board's tasks no longer appear, even if an earlier identical search was cached. (source: NFR-3)
4. **Given** I am not signed in, **When** I call search, **Then** the request is rejected. (source: NFR-3)

---

### User Story 3 - Search stays fast at 10,000 tasks (Priority: P1)

Search responds quickly with a realistic data volume. With 10,000 tasks in the system, searching by a word in the title returns results in under 300 ms for 95% of requests. Repeated identical searches are served faster from a short-lived cache, and the cache never shows stale or foreign data.

**Why this priority**: This is the measurable acceptance criterion of US-4 and NFR-1; it needs an explicit load/performance test, not just an assumption.

**Independent Test**: Run a load test against an environment loaded with 10,000 tasks and verify p95 latency below 300 ms with the error rate within the service-level limit.

**Acceptance Scenarios**:

1. **Given** 10,000 tasks exist, **When** a load test issues searches by a word in a task title, **Then** the p95 response time is under 300 ms. (source: US-4, NFR-1)
2. **Given** an identical search was made recently by the same user, **When** it is repeated, **Then** the result is served from the cache and is identical. (source: NFR-1)
3. **Given** a cached result exists, **When** a task on one of the user's boards is created, edited, moved or deleted, **Then** the next search does not return stale content beyond the documented freshness limit. (source: FR-4, NFR-1)
4. **Given** the cache is unavailable, **When** I search, **Then** I still get correct results directly from the database, only slower. (source: NFR-1)

---

### User Story 4 - Keyboard-usable search interface (Priority: P2)

The web app offers a search box and a results list (the visual counterpart of User Story 1). A team member can open the search, type a query, move through results and open a task using only the keyboard, with visible focus and screen-reader announcements for the result count.

**Why this priority**: Accessibility is required (NFR-4) but the feature is usable by mouse users without it, so it follows the core stories.

**Independent Test**: Using only the keyboard, focus the search box, enter a query, navigate to a result and open it; verify with an automated accessibility check.

**Acceptance Scenarios**:

1. **Given** I am on the board page, **When** I press the documented shortcut or tab to the search box, **Then** the box receives visible focus. (source: NFR-4, US-4)
2. **Given** results are displayed, **When** I use the arrow keys, **Then** focus moves between results and Enter opens the focused task. (source: NFR-4)
3. **Given** results change, **When** a screen reader is in use, **Then** the number of results is announced. (source: NFR-4)
4. **Given** the results are open, **When** I press Escape, **Then** the results close and focus returns to the search box. (source: NFR-4)

---

### Edge Cases

- Empty or whitespace-only query: rejected with a clear validation message; no search is run.
- Very long query or special characters (quotes, operators, SQL metacharacters): handled safely as plain text, never as an error or injection.
- Query made only of very common words: returns an empty or limited result without error.
- User with no boards: returns an empty list.
- More matches than one page: results are paged; the total number of matches is indicated.
- Task with empty description: still searchable by title.
- Search while a task is being edited: eventually consistent within the freshness limit stated in the assumptions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST let a signed-in user search tasks by one or more words and return tasks whose title or description match. (source: FR-4, US-4)
- **FR-002**: System MUST restrict results to boards where the requesting user is a member, and MUST allow narrowing to one of those boards. (source: FR-4, NFR-3)
- **FR-003**: System MUST rank title matches above description-only matches and return results in a stable order. (source: FR-4)
- **FR-004**: System MUST return for each result: task id, title, board id and name, column, and an excerpt with matches marked. (source: FR-4, US-4)
- **FR-005**: System MUST page results and enforce a maximum page size. (source: FR-4, NFR-1)
- **FR-006**: System MUST reject empty queries and treat all query text as plain text. (source: FR-4)
- **FR-007**: System MUST reflect created, edited and deleted tasks in search results within the documented freshness limit. (source: FR-4)
- **FR-008**: System MUST answer search for 10,000 tasks with p95 latency under 300 ms. (source: US-4, NFR-1)
- **FR-009**: System MUST cache search results per user and query, MUST never serve one user's cached results to a user with different board membership, and MUST fall back to the database if the cache is unavailable. (source: NFR-1, NFR-3)
- **FR-010**: System MUST log search requests with latency and cache hit/miss, without logging task content, and expose search latency as a metric. (source: NFR-1, constitution II)
- **FR-011**: The search interface MUST be fully operable with the keyboard only and announce result counts to assistive technology. (source: NFR-4)
- **FR-012**: A repeatable load test MUST verify the 10,000-task, p95 300 ms target. (source: US-4, NFR-1)

### Key Entities *(include if feature involves data)*

- **Task**: owned by the tasks-board feature; this feature reads its title, description, board and column and adds a searchable index over title and description.
- **Board membership**: owned by the platform-foundation feature; defines which boards a user may search.
- **Search result**: a task summary with board, column, excerpt and rank; not persisted.
- **Cached search result**: short-lived copy of a result page keyed by user, query, board filter and page.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With 10,000 tasks, 95% of searches by a title word return results in under 300 ms.
- **SC-002**: In security tests, 0 tasks from boards the user does not belong to appear in any search result.
- **SC-003**: A user can find and open a known task in under 15 seconds, using the keyboard alone.
- **SC-004**: Search stays within the service error-rate limit of 1% during the load test.
- **SC-005**: The search interface passes automated accessibility checks (WCAG 2.1 AA) with no serious violations.

## Assumptions

- Search language configuration is not specified: assume English text-search configuration for stemming and stop words (open question Q1 in clarifications.md).
- Cache lifetime is not specified: assume 60 seconds, with invalidation when tasks on the board change (open question Q2).
- Result page size default 20, maximum 50 (assumed).
- Task model and CRUD come from 002-tasks-board; users, boards, membership and authentication come from 001-platform-foundation and are reused, not rebuilt.
- Searching comments is out of scope; only task titles and descriptions are searched.
- The search endpoint is under the `/api/v1` prefix and bearer-token authentication is assumed, as in the implementation contract.
- A separate search engine is not considered; PostgreSQL full-text search is used first, per the architecture.
- Search is available to all board members; no feature flag is introduced for it.
