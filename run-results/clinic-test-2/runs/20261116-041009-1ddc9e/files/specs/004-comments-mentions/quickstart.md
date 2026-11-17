# Quickstart: validating Comments and @mentions

Prerequisites: dev environment with features 001, 002 and 005 deployed; `FEATURE_COMMENTS=true`; a board with members `bob` and `alice` and one task; a mailbox or email sandbox for the test (A: how the email provider is faked in dev is defined by F05).

1. Run the migration for this feature (`alembic upgrade head`, A) and the tests: `pytest tests/unit/test_mentions.py tests/integration/test_comments_api.py tests/integration/test_mention_notifications.py`.
2. As `bob`, POST a comment `"Please review, @alice"` to the task (see contracts/comments-api.md). Expect 201 and `alice` in `mentions`.
3. Run the notify-worker (same image, worker command). Expect exactly one mention email to Alice within 1 minute, with author, task and comment text.
4. Post `"cc @nobody and bob@example.com"`: expect 201, empty `mentions`, no email.
5. As a user who is not a board member, GET and POST the comments: expect refusal and no content.
6. Set `FEATURE_COMMENTS=false`: expect 404 and no comment section in the web app.
7. In the web app, with keyboard only, Tab to the comment box, type a comment with a mention, press Enter on the post button; confirm the new comment is announced and focus stays logical.
