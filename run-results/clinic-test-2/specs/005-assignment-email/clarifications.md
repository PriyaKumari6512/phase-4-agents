# Clarifications: Assignment email notification

No user was available; the most reasonable option was assumed for each question.

## Q1: Self-assignment
- **Question**: Should an email be sent when a user assigns a task to themselves?
- **Options**: A) Send as for any assignment. B) Do not send when assigner = assignee.
- **Assumed**: A. 
- **Why**: US-5 says "When it is assigned to me, I receive one email" with no exception; skipping would be an invented rule. Switching to B is a one-line condition in `app/services/notification_outbox.py`.

## Q2: Email provider
- **Question**: Which email provider is used and does it support idempotency keys?
- **Options**: A) Provider-agnostic client, idempotency key sent if the provider supports it. B) Fix a specific provider now.
- **Assumed**: A.
- **Why**: architecture.md names no provider, only "the email provider's API" and a key in AWS Secrets Manager. Duplicate prevention does not depend on the provider (outbox state machine); the provider idempotency key only narrows the crash window.

## Q3: Sender address and wording
- **Question**: What sender address/domain and email text should be used?
- **Options**: A) Configuration values with plain default text. B) Wait for client-defined branding.
- **Assumed**: A (`EMAIL_FROM_ADDRESS`, `WEB_BASE_URL` configuration).
- **Why**: Not in the PRD; does not change scope. Sender domain verification with the provider is an operational step.
