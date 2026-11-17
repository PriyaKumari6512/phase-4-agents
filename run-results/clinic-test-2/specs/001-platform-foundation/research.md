# Research: Platform foundation, access control and availability

Items marked (A) are assumptions: architecture.md does not state them.

## R1 Authentication mechanism (open question Q1)
- Decision (A): email + password sign-in issuing a short-lived signed bearer token; `get_current_user` dependency in `app/core/auth.py`.
- The token signing key is an additional secret (`token-signing-key`, A) stored in Secrets Manager next to the three named in architecture.md.
- Rationale: no component outside the architecture is needed; the contract already assumes bearer-token sessions.
- Alternatives: OIDC/SSO (needs an identity provider not in the architecture); magic links (needs email client, which F05 owns).

## R2 Authorisation model
- Decision: one shared dependency `require_board_member(board_id)` in `app/core/authz.py`, returning 404 to non-members (existence not leaked). Roles: owner, member. A test enumerates all routes under `/api/v1/boards/{board_id}` and fails if one lacks the dependency.
- Rationale: NFR-3 must hold for endpoints written by other features; a single mechanism plus a route-coverage test is the simplest enforceable design.
- Alternatives: Postgres row-level security (stronger but heavier; revisit if the test proves insufficient); per-endpoint ad hoc checks (rejected, error-prone).
- Cache rule: later cache keys for board data include the board id and are only read after the membership check passes; membership is read from the database (not cached) so removal is immediate.

## R3 Environments and cost (budget USD 2,500/month)
- Decision (A): one EKS cluster per environment is likely too costly; assume one EKS cluster for non-prod (namespaces dev and stg) and one for prod, or a single cluster with three namespaces, decided by devops against the budget. Managed PostgreSQL 16 (Amazon RDS) and Redis 7 (Amazon ElastiCache) per environment, smallest sizes in dev/stg, multi-AZ in prod. The cost estimate is produced as task T012 before provisioning and must be <= USD 2,500.
- Rationale: architecture only fixes EKS, region, three environments and the budget; RDS/ElastiCache are assumed as the managed services for ARCH-003/004.
- Alternatives: self-hosted Postgres/Redis in-cluster (cheaper but heavier on a 50%-time devops engineer).

## R4 CI/CD
- Decision (A): GitHub Actions in each repository (acme organisation), Terraform in taskflow-infra, container images in Amazon ECR, deploy through manifests/kustomize overlays in taskflow-infra. Build once, promote the same image tag dev -> stg -> prod; prod needs manual approval (protected environment).
- Rationale: single build artifact, simple, reviewable.
- Alternatives: GitOps controller (extra component, not in architecture).

## R5 Secrets
- Decision: AWS Secrets Manager holds `database-url`, `redis-url`, `email-provider-key` per environment; External Secrets Operator syncs them into Kubernetes Secrets exposed as env vars read in `app/core/config.py`. IAM permissions per environment. A secret scanner (gitleaks) runs in CI (A).
- Alternatives: sealed secrets (secrets in Git; rejected by architecture).

## R6 Migrations
- Decision: Alembic in `migrations/` of taskflow-api; a Kubernetes Job (pre-deploy) runs `alembic upgrade head`; CI applies migrations to a clean PostgreSQL 16 and checks `alembic upgrade head` after the previous release revision. One migration per feature; merged migrations are never edited.

## R7 Observability and availability
- Decision: OpenTelemetry SDK in the API/worker (logs, metrics, traces) exported to an OpenTelemetry Collector in the cluster; metrics in a Prometheus-compatible store with alert rules; external probe (A: CloudWatch Synthetics or equivalent outside the cluster) every minute against the public web URL and the API health route through it; alert delivery to an on-call channel (A: tool to be chosen by devops, e.g. Slack/PagerDuty). Burn-rate alerts against the 0.5% monthly error budget.
- Alternatives: pure CloudWatch (acceptable if cheaper; decision with devops within budget).

## R8 Login protection
- Decision: failed-attempt counter in Redis per account and IP, temporary lockout after 5 failures in 15 minutes (A thresholds).

## R9 Availability accounting (Q3)
- Decision: all downtime counts, calendar month, prod probe; 99.5% = about 3.6 h per 30-day month.
