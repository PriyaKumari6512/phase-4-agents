# Feature Specification: Bookmark Management

**Feature Branch**: `001-bookmark-management`

**Created**: 2026-11-04

**Status**: Draft

**Input**: User description: "Bookmark management: users save a link with a title and tags, list their own bookmarks filtered by tag, and delete a bookmark. Source: inputs/features/F01.md (FR-001, FR-002, FR-003)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Save a link with title and tags (Priority: P1)

A user saves a link they want to return to, giving it a title and one or more tags to organise it. (source: FR-001)

**Why this priority**: Without saved bookmarks nothing else has value; this alone is a viable MVP. (source: FR-001)

**Independent Test**: Save a link with a title and tags and confirm it appears in the user's collection with that title and those tags.

**Acceptance Scenarios**:

1. **Given** a user with no bookmarks, **When** they save a link with a title and tags "reading" and "tech", **Then** the bookmark is stored and shown with its link, title and both tags. (source: FR-001)
2. **Given** a user saving a link, **When** they omit the link or the title, **Then** the bookmark is not saved and the user is told which field is required. (source: FR-001)
3. **Given** a user saving a link, **When** they provide no tags, **Then** the bookmark is saved without tags. (source: FR-001)

---

### User Story 2 - List own bookmarks filtered by tag (Priority: P2)

A user views their own bookmarks and narrows the list to those carrying a chosen tag, so they can find links again. (source: FR-002)

**Why this priority**: Retrieval is the purpose of saving; it depends on Story 1. (source: FR-002)

**Independent Test**: With bookmarks carrying different tags, list all, then filter by one tag, and confirm only matching bookmarks of that user appear.

**Acceptance Scenarios**:

1. **Given** a user with bookmarks tagged "tech" and "recipes", **When** they filter by "tech", **Then** only bookmarks tagged "tech" are shown. (source: FR-002)
2. **Given** a user with bookmarks, **When** they list without a tag filter, **Then** all their bookmarks are shown. (source: FR-002)
3. **Given** a tag no bookmark has, **When** the user filters by it, **Then** an empty list with a clear "no bookmarks found" message is shown. (source: FR-002)
4. **Given** two users with bookmarks, **When** one lists bookmarks, **Then** they see only their own. (source: FR-002)

---

### User Story 3 - Delete a bookmark (Priority: P3)

A user removes a bookmark they no longer need. (source: FR-003)

**Why this priority**: Keeps the collection tidy; useful but not needed to get value from saving and finding. (source: FR-003)

**Independent Test**: Delete a saved bookmark and confirm it no longer appears in any list.

**Acceptance Scenarios**:

1. **Given** a user with a bookmark, **When** they delete it, **Then** it no longer appears in their list, with or without tag filters. (source: FR-003)
2. **Given** a bookmark belonging to another user, **When** a user tries to delete it, **Then** it is not deleted and no information about it is revealed. (source: FR-003)
3. **Given** a bookmark that was already deleted, **When** the user tries to delete it again, **Then** they are told it no longer exists and nothing else changes. (source: FR-003)

---

### Edge Cases

- Tags differing only by letter case or surrounding spaces (e.g. "Tech" and " tech") are treated as the same tag. (source: FR-001, FR-002)
- The same link saved twice by one user: [NEEDS CLARIFICATION: should a duplicate link be rejected, merged, or allowed as a separate bookmark?]
- Deleting the last bookmark carrying a tag: that tag no longer yields results; the filter returns the empty-list message. (source: FR-002, FR-003)
- Very long titles or tags are rejected with a clear message once limits are set. (source: FR-001)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to save a link together with a title and zero or more tags; link and title are required. (source: FR-001)
- **FR-002**: Users MUST be able to list their own bookmarks, optionally filtered by a single tag; the list MUST never include other users' bookmarks, and an empty result MUST show a clear empty-state message. (source: FR-002)
- **FR-003**: Users MUST be able to delete one of their own bookmarks, after which it no longer appears in any list. Deletion is immediate with no confirmation step in this scope. (source: FR-003)
- **FR-004**: Tags MUST be matched case-insensitively and ignoring surrounding spaces; the system MUST limit tag count and length: [NEEDS CLARIFICATION: maximum number of tags per bookmark and maximum tag/title length are not defined in the PRD]. (source: FR-001, FR-002)
- **FR-005**: System MUST reject a bookmark with a missing link or title with a user-friendly message. (source: FR-001)

### Key Entities

- **Bookmark**: A saved link owned by one user, with a link, a title and zero or more tags. (source: FR-001)
- **Tag**: A short label attached to bookmarks, used to organise and filter them. (source: FR-001, FR-002)
- **User**: The owner of a personal collection of bookmarks. (source: FR-002)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can save a bookmark with title and tags in under 30 seconds. (source: FR-001)
- **SC-002**: Filtering by a tag shows 100% of the user's bookmarks with that tag and none without it. (source: FR-002)
- **SC-003**: 0 bookmarks of one user are ever visible or deletable by another user. (source: FR-002, FR-003)
- **SC-004**: 100% of deleted bookmarks are absent from all subsequent lists. (source: FR-003)

## Assumptions

- Users are already identified by the product; bookmarks are private to their owner.
- Filtering uses one tag at a time; multi-tag filtering is out of scope.
- Out of scope: editing, sharing, folders, full-text search, import/export, link validation, and non-functional targets (none defined in the PRD).
- No design frames apply: DS-001 and DS-002 describe a task-management product, not bookmarks.
- No components are mapped: ARCH-001 to ARCH-005 describe TaskFlow and do not mention bookmarks; mapping awaits resolution of the document mismatch.
