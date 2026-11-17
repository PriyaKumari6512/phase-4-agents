# Quickstart: validating the platform foundation

Prerequisites: access to the three repositories, an AWS account in us-east-1, Docker, Python 3.12, Node 22.

## 1. Local API checks (taskflow-api)
1. Start PostgreSQL 16 and Redis 7 locally and export `DATABASE_URL` and `REDIS_URL`.
2. Run the Alembic upgrade to head; expect tables users, boards, board_memberships (see [data-model.md](data-model.md)).
3. Run the test suite; expect the membership route-coverage test, auth tests and migration tests to pass.
4. Register two users, sign in, create a board as user A, call `GET /api/v1/boards/{id}` as user B; expect 404 (see [contracts](contracts/auth-and-membership-api.md)).

## 2. Environments (taskflow-infra)
1. Run the Terraform plan for dev, stg and prod; expect no errors and a cost estimate at or below USD 2,500 per month for all environments.
2. After apply, check that api, web and worker pods are running in dev and that `GET /readyz` returns 200.

## 3. Secrets
1. Create the three secrets in the dev Secrets Manager; expect them as environment variables in the pods.
2. Run the secret scan across the repositories; expect zero findings.

## 4. CI/CD
1. Open a pull request in each repository; expect tests to run and block merging on failure.
2. Merge; expect automatic deployment to dev, then promote the same image to stg and (with approval) prod. Break the health check on purpose in dev and expect the rollout to roll back.

## 5. Availability monitoring
1. Open the dashboard for dev; expect availability, p95 latency, error rate, worker health.
2. Stop the API in dev; expect a failed probe and an alert within 5 minutes.
