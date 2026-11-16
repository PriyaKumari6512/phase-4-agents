# Contract: Assignment email content

Rendered by `app/worker/templates/assignment_email.py`.

- **To**: the assignee only (name and address from the users table owned by F01).
- **From**: `EMAIL_FROM_ADDRESS` (configuration, open question Q3).
- **Subject**: `<assigner name> assigned you a task: <task title>` (default wording, Q3).
- **Body (plain text, optional HTML)**: task title, board name, assigner name, due date when set, link `<WEB_BASE_URL>/boards/<board_id>/tasks/<task_id>` (route assumed, owned by the web app (A)).
- **Escaping**: all user-provided values are escaped in HTML and stripped of line breaks in the subject.
- **Confidentiality**: no other task data, no comments, no other users' data.
- **No unsubscribe/preferences link** in this release (preferences are a separate feature).
