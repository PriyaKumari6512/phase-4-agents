# Research: Comments and @mentions

## R1: Mention matching rule
- Decision: `@username`, case-insensitive, resolved only among current members of the task's board. Token = `@` followed by letters, digits, `.`, `_`, `-`; a trailing `.` is not part of the name. `@` must be at the start of the text or after whitespace or an opening bracket, so `bob@example.com` is not a mention.
- Rationale: usernames are unique and space-free; display names can collide and contain spaces. NFR-3 requires that non-members are never notified.
- Alternatives: display-name matching (ambiguous); autocomplete picker with stored user ids (more UI, not in prd.md).
- Status: assumption, open question Q1 (clarifications.md). The username field is assumed to exist on the user model from feature 001 (A).

## R2: Notification hand-off
- Decision: insert the notification request into the outbox owned by F05 in the same database transaction as the comment (transactional outbox). notify-worker sends it.
- Rationale: the comment is never lost or delayed by email problems (FR-008), and mentions are not lost if the app crashes after commit.
- Alternatives: call the email client inside the request (blocks, fails the request); fire-and-forget task (can lose notifications).
- Dependency: the outbox interface belongs to F05 and is not in the contract; confirm it before implementation.

## R3: Duplicate and self mentions
- Decision: distinct resolved user ids per comment, excluding the author; a unique constraint on (comment_id, mentioned_user_id) guarantees one mention per member.

## R4: Non-member mentions
- Decision: stored as plain text, no notification, no error or hint about whether the user exists (NFR-3). Open question Q2.

## R5: Feature flag
- Decision: `FEATURE_COMMENTS` env variable read in `app/core/config.py`; default off in prod. When off the router returns 404 and the web feature hides the comment section (flag exposed to web through the API's existing config mechanism, A: to be defined by feature 001/002; fallback: comments endpoint returns 404 and the UI hides the section).

## R6: Ordering and pagination
- Decision: order by creation time then id, oldest first. Simple list endpoint with `limit`/`offset` (default 100) to bound the response. Pagination style is not in prd.md (A).

## R7: Accessibility
- Decision: native form controls (textarea, button), labelled input, a live region for new comment and error announcements, logical tab order. WCAG 2.1 AA per NFR-4.
