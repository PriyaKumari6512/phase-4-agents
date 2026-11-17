# Tasks: Platform foundation, access control and availability

**Input**: Design documents from `/specs/001-platform-foundation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/auth-and-membership-api.md

**Tests**: Included (constitution principle I: tests first for business logic; every user story has an independent test).

**Organization**: Tasks are grouped by user story. Repositories: acme/taskflow-api (`app/`, `migrations/`, `tests/`), acme/taskflow-web (`src/`), acme/taskflow-infra (`terraform/`, `k8s/`, `monitoring/`). Paths below are relative to the repository named in the task. Paths come from the implementation contract and are assumptions where architecture.md is silent.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Repository skeletons

- [ ] T001 Create the taskflow-api package skeleton in acme/taskflow-api: app/__init__.py, app/api/__init__.py, app/core/__init__.py, app/models/__init__.py, app/schemas/__init__.py, app/services/__init__.py, app/worker/__init__.py, tests/__init__.py
- [ ] T002 [P] Create pyproject.toml in acme/taskflow-api with Python 3.12, FastAPI, SQLAlchemy, Alembic, pytest, OpenTelemetry and lint configuration
- [ ] T003 [P] Create the taskflow-infra layout in acme/taskflow-infra: terraform/README.md, k8s/README.md, monitoring/README.md
- [ ] T004 [P] Scaffold the taskflow-web baseline on Node 22 in acme/taskflow-web: package.json, src/main.tsx, src/App.tsx (placeholder public page only; feature UI belongs to F02)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared API modules that every user story and later feature reuses

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Implement settings in app/core/config.py reading DATABASE_URL, REDIS_URL, EMAIL_PROVIDER_KEY, TOKEN_SIGNING_KEY and FEATURE_<NAME> flags from environment variables, with no default secret values (depends on T001)
- [ ] T006 [P] Implement the PostgreSQL session factory in app/core/db.py (depends on T005)
- [ ] T007 [P] Implement the Redis client in app/core/redis.py (depends on T005)
- [ ] T008 [P] Implement uniform error responses in app/core/errors.py that never include task content, password hashes or secrets (depends on T001)
- [ ] T009 Create the FastAPI app in app/main.py and the `/api/v1` router in app/api/router.py (depends on T006, T007, T008)
- [ ] T010 [P] Create the worker entry point placeholder in app/worker/main.py and the single Dockerfile for api and worker (different start commands) in Dockerfile (depends on T001)

**Checkpoint**: Foundation ready - user story implementation can begin

---

## Phase 3: User Story 1 - Three environments with managed data stores (Priority: P1)

**Goal**: dev, stg and prod on EKS in us-east-1, each with its own PostgreSQL 16 and Redis 7, within USD 2,500 per month.

**Independent Test**: Bring up each environment; workloads start, data stores are reachable only from workloads, cost forecast is at most USD 2,500.

- [ ] T011 [P] [US1] Write the environment verification script tests/verify_environment.sh in acme/taskflow-infra (region is us-east-1, workloads healthy, database and cache not reachable from the public internet, prod has at least 2 api and web instances)
- [ ] T012 [US1] Produce the cost estimate and sizing per environment in docs/cost-estimate.md in acme/taskflow-infra (total at most USD 2,500 per month, 200 teams, 50 requests per second at peak in prod)
- [ ] T013 [P] [US1] Create the network and EKS Terraform modules in terraform/modules/network/main.tf and terraform/modules/eks/main.tf (depends on T012)
- [ ] T014 [P] [US1] Create the PostgreSQL 16 Terraform module in terraform/modules/postgres/main.tf with private subnets, access only from workloads, redundancy in prod only (depends on T012)
- [ ] T015 [P] [US1] Create the Redis 7 Terraform module in terraform/modules/redis/main.tf with private subnets and access only from workloads (depends on T012)
- [ ] T016 [US1] Create the environment roots terraform/envs/dev/main.tf, terraform/envs/stg/main.tf and terraform/envs/prod/main.tf (depends on T013, T014, T015)
- [ ] T017 [US1] Create the Kubernetes base manifests k8s/base/api.yaml, k8s/base/web.yaml and k8s/base/worker.yaml with health probes and resource requests (depends on T010)
- [ ] T018 [US1] Create the overlays k8s/overlays/dev/kustomization.yaml, k8s/overlays/stg/kustomization.yaml and k8s/overlays/prod/kustomization.yaml, with prod running at least 2 api and web replicas and a pod disruption budget (depends on T017)
- [ ] T019 [US1] Create the public ingress for the web app only in k8s/base/ingress.yaml and network policies in k8s/base/networkpolicy.yaml so api, worker, database and cache are not publicly reachable (depends on T017)

**Checkpoint**: Environments run and verify

---

## Phase 4: User Story 2 - CI/CD for api, web and worker (Priority: P1)

**Goal**: Every change is built, tested and promoted dev to stg to prod with approval and automatic rollback.

**Independent Test**: Merge a trivial change in each repository, watch it deploy to dev, promote to stg and prod, then roll back.

- [ ] T020 [P] [US2] Write tests/integration/test_worker_entrypoint.py in acme/taskflow-api proving the same image starts the worker command without serving HTTP (depends on T010)
- [ ] T021 [P] [US2] Create the API CI workflow .github/workflows/ci.yml in acme/taskflow-api running lint and pytest against PostgreSQL 16 and Redis 7 services, required before merge (depends on T002)
- [ ] T022 [P] [US2] Create the web CI workflow .github/workflows/ci.yml in acme/taskflow-web running lint, tests and build on Node 22 (depends on T004)
- [ ] T023 [US2] Create the image build workflow .github/workflows/build.yml in acme/taskflow-api that builds one image used by api and worker and pushes it tagged by commit SHA (depends on T021)
- [ ] T024 [P] [US2] Create the web build workflow .github/workflows/build.yml in acme/taskflow-web that builds the static assets image tagged by commit SHA (depends on T022)
- [ ] T025 [US2] Create the deployment workflow .github/workflows/deploy.yml in acme/taskflow-infra: automatic deploy to dev, promotion of the same tag to stg, and prod only after manual approval (depends on T016, T018, T023, T024)
- [ ] T026 [US2] Add rollout safety to .github/workflows/deploy.yml and the rolling update strategy to k8s/base/api.yaml so a failed health check rolls back to the previous version (depends on T025)
- [ ] T027 [US2] Document required status checks, review requirements and the rollback procedure in docs/ci-cd.md in acme/taskflow-infra (depends on T025)

**Checkpoint**: A change flows from pull request to prod with rollback

---

## Phase 5: User Story 3 - Secrets delivered without being stored in Git (Priority: P1)

**Goal**: Database URL, Redis URL, email provider key (and the assumed token signing key) come from AWS Secrets Manager through External Secrets; nothing secret in Git.

**Independent Test**: Create a secret in dev, see it as an environment variable in the pod, rotate it, and scan all repositories for secrets.

- [ ] T028 [P] [US3] Write tests/unit/test_config.py in acme/taskflow-api: settings load from environment, startup fails when a required secret is missing, no default secret values exist (depends on T005)
- [ ] T029 [US3] Create the secrets Terraform module terraform/modules/secrets/main.tf in acme/taskflow-infra defining database-url, redis-url, email-provider-key and token-signing-key entries (values set outside Git) and a per-environment access role (depends on T016)
- [ ] T030 [P] [US3] Install the External Secrets operator with k8s/external-secrets/operator.yaml in acme/taskflow-infra
- [ ] T031 [US3] Create k8s/base/external-secret.yaml and per-environment secret stores k8s/overlays/dev/secret-store.yaml, k8s/overlays/stg/secret-store.yaml and k8s/overlays/prod/secret-store.yaml so each environment reads only its own secrets (depends on T018, T029, T030)
- [ ] T032 [US3] Expose the synchronised secrets as environment variables in k8s/base/api.yaml and k8s/base/worker.yaml (depends on T031)
- [ ] T033 [P] [US3] Add the secret scan workflow .github/workflows/secret-scan.yml in acme/taskflow-api that fails the build on a finding
- [ ] T034 [P] [US3] Add the secret scan workflow .github/workflows/secret-scan.yml in acme/taskflow-web
- [ ] T035 [P] [US3] Add the secret scan workflow .github/workflows/secret-scan.yml in acme/taskflow-infra
- [ ] T036 [US3] Write the rotation and per-environment access runbook docs/secrets.md in acme/taskflow-infra (depends on T032)

**Checkpoint**: Pods start with secrets delivered; scans clean

---

## Phase 6: User Story 4 - Users, boards and board membership data foundation (Priority: P1)

**Goal**: Users, boards and memberships exist with a versioned migration process.

**Independent Test**: Apply all migrations to an empty database, create users, a board and memberships, verify constraints, roll back and forward.

- [ ] T037 [P] [US4] Write tests/integration/test_migrations.py in acme/taskflow-api: upgrade a clean PostgreSQL 16 to head, downgrade and upgrade again, upgrade from the previous release revision (depends on T006)
- [ ] T038 [P] [US4] Write tests/integration/test_membership_constraints.py in acme/taskflow-api: unique membership per user and board, role limited to owner or member, creator becomes owner, last owner cannot be removed (depends on T006)
- [ ] T039 [US4] Set up Alembic with alembic.ini, migrations/env.py (reads the database URL from app/core/config.py) and migrations/script.py.mako (depends on T005, T006)
- [ ] T040 [P] [US4] Create the User model in app/models/user.py: email required, unique case-insensitive, max 254 chars; display_name required, max 100 chars; password_hash required; time_zone nullable; created_at default now (depends on T006)
- [ ] T041 [P] [US4] Create the Board model in app/models/board.py: name required, 1-100 chars; created_by required FK to users; created_at default now (depends on T040)
- [ ] T042 [P] [US4] Create the BoardMembership model in app/models/board_membership.py: board_id and user_id required with cascade delete, role required one of owner or member, unique (board_id, user_id), indexes on user_id and board_id (depends on T041)
- [ ] T043 [US4] Create migrations/versions/0001_users_boards_memberships.py for the three tables (depends on T039, T040, T041, T042)
- [ ] T044 [US4] Implement app/services/board_service.py: create a board with the owner membership in one transaction, add and remove members, refuse removing or demoting the last owner (depends on T042)
- [ ] T045 [US4] Create the pre-deploy migration job k8s/base/migrate-job.yaml in acme/taskflow-infra running the Alembic upgrade to head before each rollout (depends on T017, T043)
- [ ] T046 [US4] Add a migration check step to .github/workflows/ci.yml in acme/taskflow-api that applies migrations to a clean database and after the previous release revision (depends on T021, T043)

**Checkpoint**: Schema and migration pipeline in place

---

## Phase 7: User Story 5 - Authentication (Priority: P1)

**Goal**: Users register and sign in with email and password and receive a bearer token (assumed mechanism, open question Q1).

**Independent Test**: Sign in with valid and invalid credentials; call an authenticated endpoint with valid, expired and missing tokens.

- [ ] T047 [P] [US5] Write tests/unit/test_security.py in acme/taskflow-api: password hash and verify, token expiry, tampered token rejected (depends on T005)
- [ ] T048 [P] [US5] Write tests/integration/test_auth_api.py in acme/taskflow-api: register, login, generic failure message for wrong credentials, /auth/me returns own profile only, missing or expired token gives 401, lockout gives 429 (depends on T009)
- [ ] T049 [US5] Implement password hashing and token issue and verify in app/core/security.py using the token signing key from app/core/config.py (depends on T005)
- [ ] T050 [P] [US5] Create request and response schemas in app/schemas/auth.py: email max 254 chars, display_name max 100 chars, password minimum length 12 (assumed), password never in responses (depends on T001)
- [ ] T051 [US5] Implement registration and login in app/services/auth_service.py with the Redis failed-attempt counter, 5 failures in 15 minutes gives temporary lockout (assumed thresholds) (depends on T007, T040, T049, T050)
- [ ] T052 [US5] Implement the get_current_user dependency in app/core/auth.py (depends on T040, T049)
- [ ] T053 [US5] Implement POST /api/v1/auth/register, POST /api/v1/auth/login and GET /api/v1/auth/me in app/api/auth.py and register the router in app/api/router.py (depends on T009, T051, T052)
- [ ] T054 [US5] Add .github/CODEOWNERS in acme/taskflow-api requiring explicit review for app/core/auth.py, app/core/authz.py, app/core/security.py and migrations/ (constitution principle III)

**Checkpoint**: Users can sign in; protected endpoints know the caller

---

## Phase 8: User Story 6 - Board-member authorisation on every board-scoped endpoint (Priority: P1)

**Goal**: Only members of a board can see or change anything under it; non-members learn nothing.

**Independent Test**: Two boards and two users each in one board: every board-scoped endpoint refuses the non-member and serves the member.

- [ ] T055 [P] [US6] Write tests/integration/test_board_authz.py in acme/taskflow-api: member served, non-member gets the same 404 as an unknown board, removed member loses access on the next request, board list contains only the caller's boards (depends on T009)
- [ ] T056 [P] [US6] Write tests/contract/test_board_routes_enforce_membership.py in acme/taskflow-api that enumerates every route under /api/v1/boards/{board_id} and fails if one lacks the membership dependency (depends on T009)
- [ ] T057 [P] [US6] Implement refusal logging in app/core/audit.py recording user, board and time and never task content (depends on T008)
- [ ] T058 [US6] Implement require_board_member and require_board_owner in app/core/authz.py using the membership table, with no caching of membership, returning 404 to non-members (depends on T042, T052, T057)
- [ ] T059 [P] [US6] Create board and member schemas in app/schemas/board.py: board name 1-100 chars, role one of owner or member (depends on T001)
- [ ] T060 [US6] Implement the board and membership endpoints from contracts/auth-and-membership-api.md in app/api/boards.py (depends on T044, T058, T059)
- [ ] T061 [US6] Register the boards router in app/api/router.py (depends on T060)
- [ ] T062 [US6] Add the visible_board_ids(user) helper for multi-board queries to app/services/board_service.py so search, lists and reports only include the caller's boards (depends on T044)
- [ ] T063 [US6] Write the developer guide docs/authorisation.md in acme/taskflow-api: how new board-scoped endpoints use require_board_member, cache keys include the board id and are read only after the membership check, how to add routes to the coverage test (depends on T058)

**Checkpoint**: NFR-3 enforced and testable for all current and future board routes

---

## Phase 9: User Story 7 - Availability monitoring and service-level alerting (Priority: P2)

**Goal**: Availability, p95 latency and error rate are measured and alerted against 99.5% monthly, 300 ms and 1%.

**Independent Test**: Stop the API in dev; the probe fails, an alert reaches the on-call channel within 5 minutes, and availability figures update.

- [ ] T064 [P] [US7] Write tests/integration/test_health.py in acme/taskflow-api: /healthz returns 200, /readyz returns 503 when the database or Redis is unreachable (depends on T009)
- [ ] T065 [P] [US7] Write alert rule tests monitoring/tests/alert-rules-test.yaml in acme/taskflow-infra covering error rate above 1%, p95 above 300 ms, probe failure, burn rate and missing data
- [ ] T066 [US7] Implement structured JSON logging (no task content), metrics and tracing with OpenTelemetry in app/core/telemetry.py (depends on T005)
- [ ] T067 [US7] Implement the /healthz and /readyz endpoints in app/api/health.py (depends on T006, T007)
- [ ] T068 [US7] Wire telemetry, request metrics and the health router into app/main.py and add a worker heartbeat metric in app/worker/main.py (depends on T009, T010, T066, T067)
- [ ] T069 [US7] Deploy the OpenTelemetry collector and the metrics store with k8s/monitoring/otel-collector.yaml and k8s/monitoring/metrics-store.yaml in acme/taskflow-infra (depends on T018)
- [ ] T070 [US7] Create external availability probes every minute for the web app and the API health route in terraform/modules/monitoring/probes.tf, paging for prod only (depends on T016)
- [ ] T071 [US7] Write alert rules in monitoring/alert-rules.yaml: error rate above 1%, p95 above 300 ms, probe failure, monthly error budget burn rate, missing monitoring data (depends on T065, T069, T070)
- [ ] T072 [US7] Configure routing to the on-call channel in monitoring/alert-routing.yaml (delivery tool to be confirmed by devops) (depends on T071)
- [ ] T073 [US7] Create the per-environment dashboard monitoring/dashboards/slo.json and monthly availability rules monitoring/availability-rules.yaml showing availability, p95 latency, error rate and worker health (depends on T069)

**Checkpoint**: Availability and SLOs visible and alerting

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Verification and documentation across stories

- [ ] T074 [P] Write the API README README.md in acme/taskflow-api covering local setup, migrations, env vars and the shared modules later features must reuse (depends on T063)
- [ ] T075 [P] Write the migration conventions docs/migrations.md in acme/taskflow-api: one migration per feature, never edit a merged migration (depends on T043)
- [ ] T076 [P] Write the peak-load test tests/load/test_peak_load.py in acme/taskflow-api checking 50 requests per second against stg with p95 below 300 ms and error rate below 1% (depends on T025, T061)
- [ ] T077 Perform the security review and record results in docs/security-review.md in acme/taskflow-api: no secrets in repositories, authorisation coverage test passing, authentication reviewed (depends on T035, T056, T058)
- [ ] T078 Run the quickstart.md validation in specs/001-platform-foundation/quickstart.md against dev and record the outcome in docs/quickstart-results.md in acme/taskflow-infra (depends on T073, T077)

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1) then Foundational (Phase 2) block everything.
- US1 (environments) is needed by US2, US3 and US7 for deployment tasks; API-code tasks of US4, US5 and US6 can proceed in parallel with US1 and US2.
- US4 (schema) precedes US5 (users table) and US6 (membership table); US5 precedes US6 (get_current_user).
- US7 depends on US1 for monitoring deployment; its API instrumentation depends only on Foundational.
- Polish depends on all stories.

### Within Each Story

- Tests first and failing, then models, services, endpoints, integration.

### Parallel Opportunities

- Terraform modules T013-T015; CI workflows T021/T022; secret scans T033-T035; models after T040; alert tests T065 with health tests T064.
- Devops stories (US1-US3, US7) and backend stories (US4-US6) run in parallel by different engineers.

## Implementation Strategy

### MVP First

1. Setup, Foundational, then US4 -> US5 -> US6 for the confidentiality core.
2. In parallel, US1 -> US2 -> US3 to get environments, pipeline and secrets.
3. US7 last, once dev and stg run; monitoring must be live before the mid-December 2026 beta.

## Notes

- Auth mechanism, membership management and availability accounting rules are assumed (clarifications.md Q1-Q3).
- Tools not named in architecture.md (GitHub Actions, Terraform, Amazon ECR, RDS/ElastiCache, secret scanner, metrics store, alert delivery) are assumptions listed in research.md.
