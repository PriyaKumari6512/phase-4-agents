# Quickstart: validating assignment emails

## Prerequisites
- Migration `005_notification_outbox` applied (`alembic upgrade head` in acme/taskflow-api).
- Local: PostgreSQL 16 and the API running; `EMAIL_PROVIDER_BASE_URL` pointing to a fake provider (or the fake client in tests), `EMAIL_PROVIDER_API_KEY` set to any dummy value, `EMAIL_FROM_ADDRESS` and `WEB_BASE_URL` set.
- dev/stg: the `notify-worker` deployment running with the key from External Secrets.

## Run
1. Start the worker: `python -m app.worker.main`.
2. Run tests: `pytest tests/services tests/worker tests/integration -k "notification or assignment or outbox"`.
3. Manually: create a task on a board and assign it to a second user.

## Expected outcomes
- One `notification_outbox` row with status `sent` and `sent_at - created_at < 60 s`; one email at the provider for the assignee.
- Each change of assignee (including A to B and back to A) creates its own row and email; saving a task without changing the assignee creates none.
- Stopping the worker, assigning, then starting the worker: one email is sent.
- Provider returning 503 twice then 200: one email, `attempts = 3`.
- Metrics show outcome counters and the pending-age gauge; logs contain no key and no email body.
