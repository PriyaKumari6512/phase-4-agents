# Backlog v1 — clinic-test-2

8 epics · 57 stories · 355 tasks · 214 story points · 0 blocking issues

## Issues

- **warning** `open_questions`: 20 items have open questions for the reviewer

## Coverage of prd.md

- US-1: S-002-US1, S-002-US2, S-002-US3, S-002-US7
- US-2: S-002-US4, S-002-US5, S-002-US6
- US-3: S-004-US1, S-004-US2, S-004-US3
- US-4: S-003-US1, S-003-US3, S-003-US4
- US-5: S-005-US1, S-005-US2
- US-6: S-006-US1, S-006-US2, S-006-US3
- US-7: S-007-US1, S-007-US2, S-007-US3
- US-8: S-008-US1, S-008-US2
- US-9: S-008-US3
- FR-1: S-002-US1, S-002-US3, S-002-US6, S-002-US7
- FR-2: S-002-US2, S-002-US4, S-002-US5
- FR-3: S-004-US1, S-004-US2, S-004-US3
- FR-4: S-003-US1, S-003-US2, S-003-US3
- FR-5: S-005-US1, S-005-US2, S-005-US3
- FR-6: S-006-US1, S-006-US2, S-006-US3
- FR-7: S-007-US1, S-007-US2, S-007-US3
- FR-8: S-008-US1, S-008-US2
- FR-9: S-008-US3
- NFR-1: S-002-US2, S-002-US5
- NFR-2: S-001-US1, S-001-US2, S-001-US4, S-001-US7
- NFR-3: S-001-US1, S-001-US2, S-001-US3, S-001-US4, S-001-US5, S-001-US6
- NFR-4: S-002-US4, S-002-US6

Critical path: S-SETUP-001 → S-FOUND-001 → S-001-US1 → S-001-US2 → S-001-US4 → S-001-US5 → S-001-US6 → S-002-US1 → S-002-US2 → S-002-US3 → S-002-US4 → S-002-US7 → S-005-US1 → S-005-US2 → S-005-US3 → S-POLISH-005

## E-001 Platform foundation, access control and availability

Environments, CI/CD, secrets, users/boards/membership, board-member authorisation, monitoring for 99.5% availability.

### S-001-US1 Three environments with managed data stores — P1/must · 8 SP (low, llm)

As a TaskFlow engineer, I want separate dev, stg and prod environments, each with its own database and cache so that features can be built, verified and released safely and the whole platform stays inside the monthly infrastructure budget.
Depends on: S-FOUND-001 · Sources: NFR-2, NFR-3

- [AC-S-001-US1-1] Given the infrastructure definitions for dev, stg and prod, When an environment is created, Then it is isolated from the other two (own cluster namespace or cluster, own database, own cache) and runs in the AWS us-east-1 region. (source: NFR-2)
- [AC-S-001-US1-2] Given an environment, When the API, web and worker workloads are scheduled, Then the database and cache are reachable from those workloads and are not reachable from the public internet. (source: NFR-3)
- [AC-S-001-US1-3] Given all three environments are running, When the monthly cost is reviewed, Then the forecast total is at most USD 2,500 across all environments. (source: NFR-2)
- [AC-S-001-US1-4] Given the production environment, When one workload instance fails, Then at least one other instance of the API and web app keeps serving traffic. (source: NFR-2)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T011 | Write the environment verification script tests/verify_environment.sh in acme/ta | 4.0 | devops-ci, kubernetes | no | - |
| 001-T012 | Produce the cost estimate and sizing per environment in docs/cost-estimate.md in | 4.0 | terraform, docs | no | - |
| 001-T013 | Create the network and EKS Terraform modules in terraform/modules/network/main.t | 10.0 | terraform, kubernetes | no | 001-T012 |
| 001-T014 | Create the PostgreSQL 16 Terraform module in terraform/modules/postgres/main.tf  | 6.0 | terraform, postgres | no | 001-T012 |
| 001-T015 | Create the Redis 7 Terraform module in terraform/modules/redis/main.tf with priv | 4.0 | terraform | no | 001-T012 |
| 001-T016 | Create the environment roots terraform/envs/dev/main.tf, terraform/envs/stg/main | 6.0 | terraform | no | 001-T013, 001-T014, 001-T015 |
| 001-T017 | Create the Kubernetes base manifests k8s/base/api.yaml, k8s/base/web.yaml and k8 | 5.0 | kubernetes | no | 001-T010 |
| 001-T018 | Create the overlays k8s/overlays/dev/kustomization.yaml, k8s/overlays/stg/kustom | 4.0 | kubernetes | no | 001-T017 |
| 001-T019 | Create the public ingress for the web app only in k8s/base/ingress.yaml and netw | 5.0 | kubernetes | no | 001-T017 |

### S-001-US2 CI/CD for api, web and worker — P1/must · 8 SP (low, llm)

As a TaskFlow engineer, I want every change to be built, tested and deployed automatically through the environments so that releases are repeatable and a broken change never reaches production unnoticed.
Depends on: S-001-US1 · Sources: NFR-2, NFR-3

- [AC-S-001-US2-1] Given a pull request in the api or web repository, When it is opened or updated, Then unit and integration tests run and the pull request cannot be merged while they fail
- [AC-S-001-US2-2] Given a change merged to the main branch, When the pipeline runs, Then one image is built for the api and the worker (same repository and image, different start command) and a build of the web app is produced, and both are deployed to dev automatically
- [AC-S-001-US2-3] Given a version running in stg that passed its checks, When an engineer approves promotion, Then the same build artifact is deployed to prod without being rebuilt. (source: NFR-2)
- [AC-S-001-US2-4] Given a deployment to prod whose health check fails, When the rollout does not become healthy, Then the previous version keeps serving traffic and the failed deployment is reported. (source: NFR-2)
- [AC-S-001-US2-5] Given the pipeline definitions, When they are reviewed, Then they contain no secret values. (source: NFR-3)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T020 | Write tests/integration/test_worker_entrypoint.py in acme/taskflow-api proving t | 3.0 | qa-automation, backend-python | yes | 001-T010 |
| 001-T021 | Create the API CI workflow .github/workflows/ci.yml in acme/taskflow-api running | 5.0 | devops-ci | no | 001-T002 |
| 001-T022 | Create the web CI workflow .github/workflows/ci.yml in acme/taskflow-web running | 4.0 | devops-ci, frontend-react | no | 001-T004 |
| 001-T023 | Create the image build workflow .github/workflows/build.yml in acme/taskflow-api | 5.0 | devops-ci | no | 001-T021 |
| 001-T024 | Create the web build workflow .github/workflows/build.yml in acme/taskflow-web t | 4.0 | devops-ci, frontend-react | no | 001-T022 |
| 001-T025 | Create the deployment workflow .github/workflows/deploy.yml in acme/taskflow-inf | 12.0 | devops-ci, kubernetes | no | 001-T016, 001-T018, 001-T023, 001-T024 |
| 001-T026 | Add rollout safety to .github/workflows/deploy.yml and the rolling update strate | 8.0 | devops-ci, kubernetes | no | 001-T025 |
| 001-T027 | Document required status checks, review requirements and the rollback procedure  | 4.0 | docs, devops-ci | yes | 001-T025 |

### S-001-US3 Secrets delivered without being stored in Git — P1/must · 5 SP (low, llm)

As a TaskFlow engineer, I want the database URL, Redis URL and email provider key stored in AWS Secrets Manager and delivered to the workloads automatically so that no secret ever appears in Git and confidential task data stays protected.
Depends on: S-001-US1 · Sources: NFR-3

- [AC-S-001-US3-1] Given the three secrets (database URL, Redis URL, email provider key) in an environment's Secrets Manager, When a workload starts, Then each secret is available to it as an environment variable. (source: NFR-3)
- [AC-S-001-US3-2] Given a secret value changes in Secrets Manager, When the synchronisation interval passes and workloads are restarted, Then they use the new value without any change in Git. (source: NFR-3)
- [AC-S-001-US3-3] Given any of the repositories, When a secret scan runs in CI, Then it finds no secret values and fails the build if it finds one. (source: NFR-3)
- [AC-S-001-US3-4] Given the dev, stg and prod environments, When their secrets are compared, Then each environment only has access to its own secrets. (source: NFR-3)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T028 | Write tests/unit/test_config.py in acme/taskflow-api: settings load from environ | 3.0 | qa-automation, backend-python | yes | 001-T005 |
| 001-T029 | Create the secrets Terraform module terraform/modules/secrets/main.tf in acme/ta | 4.0 | terraform | no | 001-T016 |
| 001-T030 | Install the External Secrets operator with k8s/external-secrets/operator.yaml in | 4.0 | kubernetes | no | - |
| 001-T031 | Create k8s/base/external-secret.yaml and per-environment secret stores k8s/overl | 6.0 | kubernetes, terraform | no | 001-T018, 001-T029, 001-T030 |
| 001-T032 | Expose the synchronised secrets as environment variables in k8s/base/api.yaml an | 2.0 | kubernetes | no | 001-T031 |
| 001-T033 | Add the secret scan workflow .github/workflows/secret-scan.yml in acme/taskflow- | 2.0 | devops-ci | no | - |
| 001-T034 | Add the secret scan workflow .github/workflows/secret-scan.yml in acme/taskflow- | 1.5 | devops-ci | no | - |
| 001-T035 | Add the secret scan workflow .github/workflows/secret-scan.yml in acme/taskflow- | 1.5 | devops-ci | no | - |
| 001-T036 | Write the rotation and per-environment access runbook docs/secrets.md in acme/ta | 3.0 | docs, devops-ci | no | 001-T032 |

### S-001-US4 Users, boards and board membership data foundation — P1/must · 5 SP (low, llm)

As a TaskFlow developer, I want the users, boards and board membership data structures and a versioned migration process in place so that every later feature stores its data on the same, reviewed foundation.
Depends on: S-001-US2 · Sources: NFR-3, NFR-2

- [AC-S-001-US4-1] Given an empty database, When migrations are applied, Then users, boards and board memberships exist and the migration history records the version. (source: NFR-3)
- [AC-S-001-US4-2] Given a user who is already a member of a board, When the same membership is created again, Then it is rejected and no duplicate exists. (source: NFR-3)
- [AC-S-001-US4-3] Given a board with members, When a user is added as a member, Then the membership is stored with the user, the board and the member's role (owner or member). (source: NFR-3)
- [AC-S-001-US4-4] Given a new feature needs a table, When a developer adds a migration, Then the migration runs in CI against a clean database and after the previous release's schema. (source: NFR-2)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T037 | Write tests/integration/test_migrations.py in acme/taskflow-api: upgrade a clean | 4.0 | qa-automation, postgres | no | 001-T006 |
| 001-T038 | Write tests/integration/test_membership_constraints.py in acme/taskflow-api: uni | 4.0 | qa-automation, postgres | yes | 001-T006 |
| 001-T039 | Set up Alembic with alembic.ini, migrations/env.py (reads the database URL from  | 3.0 | postgres, backend-python | no | 001-T005, 001-T006 |
| 001-T040 | Create the User model in app/models/user.py: email required, unique case-insensi | 3.0 | data-modeling, backend-python | yes | 001-T006 |
| 001-T041 | Create the Board model in app/models/board.py: name required, 1-100 chars; creat | 2.0 | data-modeling, backend-python | yes | 001-T040 |
| 001-T042 | Create the BoardMembership model in app/models/board_membership.py: board_id and | 3.0 | data-modeling, postgres | yes | 001-T041 |
| 001-T043 | Create migrations/versions/0001_users_boards_memberships.py for the three tables | 3.0 | postgres, data-modeling | no | 001-T039, 001-T040, 001-T041, 001-T042 |
| 001-T044 | Implement app/services/board_service.py: create a board with the owner membershi | 5.0 | backend-python, postgres | no | 001-T042 |
| 001-T045 | Create the pre-deploy migration job k8s/base/migrate-job.yaml in acme/taskflow-i | 2.0 | kubernetes, postgres | no | 001-T017, 001-T043 |
| 001-T046 | Add a migration check step to .github/workflows/ci.yml in acme/taskflow-api that | 2.0 | devops-ci, postgres | no | 001-T021, 001-T043 |

### S-001-US5 Authentication — P1/must · 5 SP (low, llm)

As a team member, I want to sign in so that the platform knows who I am and every request I make is tied to my identity.
Depends on: S-001-US4 · Sources: NFR-3

- [AC-S-001-US5-1] Given a registered user, When they sign in with correct credentials, Then they receive a credential (bearer token) that identifies them on later requests. (source: NFR-3)
- [AC-S-001-US5-2] Given a user with wrong credentials, When they try to sign in, Then access is refused with a generic message that does not reveal whether the account exists. (source: NFR-3)
- [AC-S-001-US5-3] Given a request to a protected endpoint with no, malformed or expired credential, When it is processed, Then it is refused as unauthenticated and no data is returned. (source: NFR-3)
- [AC-S-001-US5-4] Given repeated failed sign-in attempts for one account, When the limit is exceeded, Then further attempts are temporarily refused. (source: NFR-3)
- [AC-S-001-US5-5] Given a signed-in user, When they ask who they are, Then the system returns their own profile only. (source: NFR-3)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T047 | Write tests/unit/test_security.py in acme/taskflow-api: password hash and verify | 3.0 | qa-automation, backend-python | no | 001-T005 |
| 001-T048 | Write tests/integration/test_auth_api.py in acme/taskflow-api: register, login,  | 4.0 | qa-automation, api-design | no | 001-T009 |
| 001-T049 | Implement password hashing and token issue and verify in app/core/security.py us | 4.0 | backend-python | no | 001-T005 |
| 001-T050 | Create request and response schemas in app/schemas/auth.py: email max 254 chars, | 2.0 | backend-python, api-design | no | 001-T001 |
| 001-T051 | Implement registration and login in app/services/auth_service.py with the Redis  | 6.0 | backend-python | no | 001-T007, 001-T040, 001-T049, 001-T050 |
| 001-T052 | Implement the get_current_user dependency in app/core/auth.py | 3.0 | backend-python, api-design | no | 001-T040, 001-T049 |
| 001-T053 | Implement POST /api/v1/auth/register, POST /api/v1/auth/login and GET /api/v1/au | 4.0 | backend-python, api-design | no | 001-T009, 001-T051, 001-T052 |
| 001-T054 | Add .github/CODEOWNERS in acme/taskflow-api requiring explicit review for app/co | 1.0 | backend-python | no | 001-T053 |

### S-001-US6 Board-member authorisation on every board-scoped endpoint — P1/must · 5 SP (low, llm)

As a team member, I want only the members of a board to be able to see or change anything on it so that my team's task data stays confidential.
Depends on: S-001-US5 · Sources: NFR-3

- [AC-S-001-US6-1] Given a board and a user who is not a member, When the user requests the board or anything under it, Then the system refuses and returns no board or task data; the response is indistinguishable from a board that does not exist. (source: NFR-3)
- [AC-S-001-US6-2] Given a board member, When they request the board, Then they are served. (source: NFR-3)
- [AC-S-001-US6-3] Given a user removed from a board, When they make the next request, Then they no longer have access, including to cached data. (source: NFR-3)
- [AC-S-001-US6-4] Given a new board-scoped endpoint added by any feature, When it is built, Then it uses the shared membership check, and an automated test fails if a registered board-scoped route does not enforce it. (source: NFR-3)
- [AC-S-001-US6-5] Given a list or search spanning several boards, When a user requests it, Then only data from boards where they are a member is included. (source: NFR-3)
- [AC-S-001-US6-6] Given any refused access, When it happens, Then an audit-style log entry records the user, the board and the time, without task content. (source: NFR-3)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T055 | Write tests/integration/test_board_authz.py in acme/taskflow-api: member served, | 5.0 | qa-automation, api-design | no | 001-T009 |
| 001-T056 | Write tests/contract/test_board_routes_enforce_membership.py in acme/taskflow-ap | 4.0 | qa-automation, backend-python | no | 001-T009 |
| 001-T057 | Implement refusal logging in app/core/audit.py recording user, board and time an | 3.0 | backend-python, observability | no | 001-T008 |
| 001-T058 | Implement require_board_member and require_board_owner in app/core/authz.py usin | 5.0 | backend-python, api-design | no | 001-T042, 001-T052, 001-T057 |
| 001-T059 | Create board and member schemas in app/schemas/board.py: board name 1-100 chars, | 2.0 | backend-python, api-design | yes | 001-T001 |
| 001-T060 | Implement the board and membership endpoints from contracts/auth-and-membership- | 6.0 | backend-python, api-design | no | 001-T044, 001-T058, 001-T059 |
| 001-T061 | Register the boards router in app/api/router.py | 1.0 | backend-python | yes | 001-T060 |
| 001-T062 | Add the visible_board_ids(user) helper for multi-board queries to app/services/b | 3.0 | backend-python, postgres | no | 001-T044 |
| 001-T063 | Write the developer guide docs/authorisation.md in acme/taskflow-api: how new bo | 3.0 | docs, backend-python | yes | 001-T058 |

### S-001-US7 Availability monitoring and service-level alerting — P2/should · 8 SP (low, llm)

As a TaskFlow operator, I want to see and be alerted on availability, latency and error rate of the web app and API so that we can keep the 99.5% monthly availability promise and react before customers notice.
Depends on: S-001-US2 · Sources: NFR-2

- [AC-S-001-US7-1] Given the web app and the API are running, When an external probe checks them every minute, Then availability per month is calculated for each. (source: NFR-2)
- [AC-S-001-US7-2] Given the API error rate exceeds 1% over a measurement window, When the alert rule evaluates, Then an alert is sent to the on-call channel. (source: NFR-2)
- [AC-S-001-US7-3] Given the API p95 latency exceeds 300 ms over a measurement window, When the alert rule evaluates, Then an alert is sent. (source: NFR-2)
- [AC-S-001-US7-4] Given the remaining error budget for the month (0.5% of the month) is being consumed too fast, When the burn-rate rule evaluates, Then a warning is sent before the budget is exhausted. (source: NFR-2)
- [AC-S-001-US7-5] Given any service, When it runs, Then it emits structured logs, metrics and traces and exposes a health check endpoint. (source: NFR-2)
- [AC-S-001-US7-6] Given an engineer opens the operations dashboard, When they choose an environment, Then they see availability, p95 latency, error rate and worker health for it. (source: NFR-2)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T064 | Write tests/integration/test_health.py in acme/taskflow-api: /healthz returns 20 | 2.0 | qa-automation, backend-python | yes | 001-T009 |
| 001-T065 | Write alert rule tests monitoring/tests/alert-rules-test.yaml in acme/taskflow-i | 4.0 | observability | yes | - |
| 001-T066 | Implement structured JSON logging (no task content), metrics and tracing with Op | 5.0 | observability, backend-python | no | 001-T005 |
| 001-T067 | Implement the /healthz and /readyz endpoints in app/api/health.py | 2.0 | backend-python, api-design | yes | 001-T006, 001-T007 |
| 001-T068 | Wire telemetry, request metrics and the health router into app/main.py and add a | 4.0 | backend-python, observability | yes | 001-T009, 001-T010, 001-T066, 001-T067 |
| 001-T069 | Deploy the OpenTelemetry collector and the metrics store with k8s/monitoring/ote | 8.0 | kubernetes, observability | no | 001-T018 |
| 001-T070 | Create external availability probes every minute for the web app and the API hea | 4.0 | terraform, observability | no | 001-T016 |
| 001-T071 | Write alert rules in monitoring/alert-rules.yaml: error rate above 1%, p95 above | 5.0 | observability | no | 001-T065, 001-T069, 001-T070 |
| 001-T072 | Configure routing to the on-call channel in monitoring/alert-routing.yaml (deliv | 3.0 | observability, devops-ci | no | 001-T071 |
| 001-T073 | Create the per-environment dashboard monitoring/dashboards/slo.json and monthly  | 6.0 | observability | no | 001-T069 |

### S-SETUP-001 Platform foundation, access control and availability: Setup — P1/must · 2 SP (low, llm)

Depends on: - · Sources: E-001

- [AC-S-SETUP-001-1] Given the setup tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T001 | Create the taskflow-api package skeleton in acme/taskflow-api: app/__init__.py,  | 2.0 | backend-python | no | - |
| 001-T002 | Create pyproject.toml in acme/taskflow-api with Python 3.12, FastAPI, SQLAlchemy | 3.0 | backend-python | yes | - |
| 001-T003 | Create the taskflow-infra layout in acme/taskflow-infra: terraform/README.md, k8 | 1.5 | terraform, docs | no | - |
| 001-T004 | Scaffold the taskflow-web baseline on Node 22 in acme/taskflow-web: package.json | 3.0 | frontend-react | yes | - |

### S-FOUND-001 Platform foundation, access control and availability: Foundational prerequisites — P1/must · 3 SP (low, llm)

Depends on: S-SETUP-001 · Sources: E-001

- [AC-S-FOUND-001-1] Given the foundational prerequisites tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T005 | Implement settings in app/core/config.py reading DATABASE_URL, REDIS_URL, EMAIL_ | 3.0 | backend-python | no | 001-T001 |
| 001-T006 | Implement the PostgreSQL session factory in app/core/db.py | 3.0 | backend-python, postgres | yes | 001-T005 |
| 001-T007 | Implement the Redis client in app/core/redis.py | 2.0 | backend-python | yes | 001-T005 |
| 001-T008 | Implement uniform error responses in app/core/errors.py that never include task  | 3.0 | backend-python, api-design | yes | 001-T001 |
| 001-T009 | Create the FastAPI app in app/main.py and the `/api/v1` router in app/api/router | 4.0 | backend-python, api-design | yes | 001-T006, 001-T007, 001-T008 |
| 001-T010 | Create the worker entry point placeholder in app/worker/main.py and the single D | 3.0 | devops-ci, backend-python | no | 001-T001 |

### S-POLISH-001 Platform foundation, access control and availability: Polish & cross-cutting concerns — P3/could · 3 SP (low, llm)

Depends on: S-001-US3, S-001-US6, S-001-US7 · Sources: E-001

- [AC-S-POLISH-001-1] Given the polish & cross-cutting concerns tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 001-T074 | Write the API README README.md in acme/taskflow-api covering local setup, migrat | 3.0 | docs, backend-python | yes | 001-T063 |
| 001-T075 | Write the migration conventions docs/migrations.md in acme/taskflow-api: one mig | 2.0 | docs, postgres | yes | 001-T043 |
| 001-T076 | Write the peak-load test tests/load/test_peak_load.py in acme/taskflow-api check | 6.0 | qa-automation, backend-python | no | 001-T025, 001-T061 |
| 001-T077 | Perform the security review and record results in docs/security-review.md in acm | 4.0 | qa-automation, docs | no | 001-T035, 001-T056, 001-T058 |
| 001-T078 | Run the quickstart.md validation in specs/001-platform-foundation/quickstart.md  | 3.0 | qa-automation, devops-ci | no | 001-T073, 001-T077 |

## E-002 Tasks and board with live updates

Task CRUD, three-column board, drag to move, SSE live updates within 5 s, keyboard accessibility.

### S-002-US1 Create, view, edit and delete tasks — P1/must · 5 SP (low, llm)

As a team member, I want to create, view, edit and delete tasks with a title, description, due date and assignee so that all of my team's work is in one place and only board members can see it.
Depends on: S-FOUND-002, S-001-US6 · Sources: FR-1, US-1

- [AC-S-002-US1-1] Given I am a member of a board, When I create a task with a title, Then the task is saved and appears in the "To do" column. (source: US-1)
- [AC-S-002-US1-2] Given a task, When I set a due date and an assignee who is a member of the board, Then both are stored and shown on the task. (source: US-1, FR-1)
- [AC-S-002-US1-3] Given a task, When I edit its title, description, due date or assignee, Then the changes are saved and visible to every board member. (source: FR-1)
- [AC-S-002-US1-4] Given a task, When I delete it and confirm, Then it no longer appears on the board. (source: FR-1)
- [AC-S-002-US1-5] Given I create a task with an empty title, When I submit, Then the task is rejected with a clear message and nothing is saved. (source: FR-1)
- [AC-S-002-US1-6] Given I am not a member of a board, When I try to read or change its tasks, Then access is refused. (source: NFR-3)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 002-T010 | Unit tests for task schema validation (empty and whitespace title, title over 20 | 2.0 | qa-automation, backend-python | yes | - |
| 002-T011 | Integration tests for create, get, patch, delete, new task status 'todo', assign | 5.0 | qa-automation, backend-python | no | - |
| 002-T012 | Implement create, get, update and delete in taskflow-api/app/services/task_servi | 6.0 | backend-python | no | 002-T003, 002-T006, 002-T007 |
| 002-T013 | Implement routes POST /boards/{board_id}/tasks, GET, PATCH and DELETE /boards/{b | 4.0 | backend-python, api-design | no | 002-T012 |
| 002-T014 | Register the tasks router under the /api/v1 prefix in taskflow-api/app/main.py | 1.0 | backend-python | yes | 002-T013 |
| 002-T015 | Add structured log lines and trace attributes (board_id, task_id, actor_id; no t | 2.0 | backend-python, observability | yes | 002-T013 |

### S-002-US2 See the board with three columns and task cards — P1/must · 5 SP (low, llm)

As a team member, I want to see my board as three columns (To do, Doing, Done) with task cards so that I can see the current state of all work at a glance.
Depends on: S-FOUND-002 · Sources: FR-2, US-1, NFR-1

- [AC-S-002-US2-1] Given I am on a board, When the board loads, Then I see exactly three columns in the order To do, Doing, Done, each with its tasks. (source: FR-2)
- [AC-S-002-US2-2] Given a task with a due date and an assignee, When I look at its card, Then both are shown on the card. (source: US-1)
- [AC-S-002-US2-3] Given a column has no tasks, When the board loads, Then the column is shown with an empty-state message. (source: FR-2)
- [AC-S-002-US2-4] Given a board with many tasks, When I open it, Then the board loads quickly enough that ordinary requests stay within the 300 ms p95 target. (source: NFR-1)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 002-T016 | Integration tests for GET /boards/{board_id}/board (three columns in order, task | 4.0 | qa-automation, redis | yes | - |
| 002-T017 | Component tests for BoardPage, Column and TaskCard (three columns in order, empt | 3.0 | qa-automation, frontend-react | yes | - |
| 002-T018 | Implement the board view read with Redis cache (key `board:{board_id}:view`, TTL | 5.0 | backend-python, redis | no | 002-T003, 002-T006, 002-T007 |
| 002-T019 | Implement route GET /boards/{board_id}/board in taskflow-api/app/api/board_view. | 2.0 | backend-python, api-design | yes | 002-T018, 002-T014 |
| 002-T020 | Create the Column component with heading and empty-state message in taskflow-web | 2.0 | frontend-react | yes | - |
| 002-T021 | Create the TaskCard component showing title, due date, assignee name (or "no lon | 3.0 | frontend-react | yes | - |
| 002-T022 | Create the useBoard hook that loads the board snapshot and exposes columns, load | 3.0 | frontend-react | yes | 002-T008 |
| 002-T023 | Create BoardPage that renders three Column components from useBoard in taskflow- | 3.0 | frontend-react | yes | 002-T020, 002-T021, 002-T022 |
| 002-T024 | Register the board route `/boards/:boardId` in taskflow-web/src/routes.tsx (A: r | 1.0 | frontend-react | yes | 002-T023 |

### S-002-US3 Create, edit and delete tasks from the board — P1/must · 5 SP (low, llm)

As a team member, I want to create, edit and delete tasks with forms on the board so that I can maintain my team's tasks without leaving the board.
Depends on: S-FOUND-002 · Sources: FR-1, US-1

- [AC-S-002-US3-1] Given I am on a board, When I create a task with a title, Then it appears in the "To do" column. (source: US-1)
- [AC-S-002-US3-2] Given a task, When I set a due date and an assignee in the edit form, Then both are shown on the task card. (source: US-1)
- [AC-S-002-US3-3] Given the form has an invalid value, When I submit, Then I see an error message next to the field and nothing is saved. (source: FR-1)
- [AC-S-002-US3-4] Given a task, When I choose delete and confirm, Then the card disappears; **When** I cancel, **Then** the task stays. (source: FR-1)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 002-T025 | Component tests for TaskForm and delete confirmation (create puts card in "To do | 4.0 | qa-automation, frontend-react | yes | - |
| 002-T026 | Create the TaskForm component (title, description, due date, assignee select fil | 8.0 | frontend-react | no | - |
| 002-T027 | Create the ConfirmDeleteDialog component in taskflow-web/src/features/board/Conf | 2.0 | frontend-react | yes | - |
| 002-T028 | Add createTask, updateTask and deleteTask actions to taskflow-web/src/features/b | 4.0 | frontend-react | yes | 002-T022 |
| 002-T029 | Add the "New task" button, open-card-to-edit and delete actions that use TaskFor | 5.0 | frontend-react | no | 002-T023, 002-T026, 002-T027, 002-T028 |

### S-002-US4 Move tasks between columns — P1/must · 5 SP (low, llm)

As a team member, I want to move tasks between To do, Doing and Done by dragging or by a menu so that everyone sees the current state of the work.
Depends on: S-FOUND-002 · Sources: FR-2, US-2, NFR-4

- [AC-S-002-US4-1] Given a task in "To do", When I drag it to "Doing", Then it is shown in "Doing" and stays there after reload. (source: US-2)
- [AC-S-002-US4-2] Given a task, When I choose another column from the task's move menu, Then it moves exactly as with dragging. (source: FR-2, NFR-4)
- [AC-S-002-US4-3] Given a move that cannot be saved (for example the connection is lost), When the save fails, Then the card returns to its original column and I see an error message. (source: FR-2)
- [AC-S-002-US4-4] Given two members move the same task at nearly the same time, When both moves are saved, Then the last saved move wins and every viewer ends up seeing the same column. (source: FR-2)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 002-T030 | Integration tests for POST /boards/{board_id}/tasks/{task_id}/move (every column | 4.0 | qa-automation, backend-python | yes | - |
| 002-T031 | Component tests for drag move, menu move and rollback with error message on fail | 4.0 | qa-automation, frontend-react | yes | - |
| 002-T032 | Add `move_task` to taskflow-api/app/services/task_service.py (update status and  | 2.0 | backend-python | yes | 002-T012 |
| 002-T033 | Implement route POST /boards/{board_id}/tasks/{task_id}/move in taskflow-api/app | 2.0 | backend-python, api-design | no | 002-T015, 002-T032 |
| 002-T034 | Create the MoveMenu component ("Move to" with the other two columns) in taskflow | 2.0 | frontend-react | yes | - |
| 002-T035 | Add drag source to TaskCard and drop target to Column using native HTML5 drag an | 4.0 | frontend-react | yes | 002-T020, 002-T021 |
| 002-T036 | Add `moveTask` with optimistic update and rollback on error to taskflow-web/src/ | 3.0 | frontend-react | yes | 002-T028 |
| 002-T037 | Wire MoveMenu and drop handlers to `moveTask` and show the error message on fail | 3.0 | frontend-react | yes | 002-T029, 002-T034, 002-T035, 002-T036 |

### S-002-US5 Everyone sees board changes within 5 seconds — P1/must · 8 SP (low, llm)

As a team member, I want to see changes made by other members on the board within 5 seconds without reloading so that everyone works from the current state of the board.
Depends on: S-FOUND-002 · Sources: US-2, FR-2, NFR-1

- [AC-S-002-US5-1] Given a task in "To do" and several members viewing the board, When one member moves it to "Doing", Then all board viewers see it in "Doing" within 5 seconds. (source: US-2, NFR-1)
- [AC-S-002-US5-2] Given a member is viewing a board, When another member creates, edits or deletes a task, Then the viewer sees the change within 5 seconds. (source: FR-2, NFR-1)
- [AC-S-002-US5-3] Given a viewer's live connection was interrupted, When the connection is restored, Then the board shows the current state, including changes made during the interruption. (source: NFR-1)
- [AC-S-002-US5-4] Given a person who is not a member of the board, When they try to receive its live updates, Then access is refused and no task data is sent. (source: NFR-3)
- [AC-S-002-US5-5] Given several boards are in use, When a task changes on one board, Then viewers of other boards receive nothing about it. (source: NFR-3)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 002-T038 | Integration tests for GET /boards/{board_id}/events (ready event, update events  | 6.0 | qa-automation, backend-python | no | - |
| 002-T039 | Latency test with 10 simultaneous subscribers asserting every update arrives in  | 3.0 | qa-automation, backend-python | yes | - |
| 002-T040 | Unit tests for the web stream client (parsing events, reconnect with backoff 1 s | 4.0 | qa-automation, frontend-react | yes | - |
| 002-T041 | Add `subscribe_board_updates(board_id)` async generator over Redis pub/sub, with | 5.0 | backend-python, redis | no | 002-T007 |
| 002-T042 | Implement route GET /boards/{board_id}/events returning `text/event-stream` with | 4.0 | backend-python, messaging | no | 002-T019, 002-T041 |
| 002-T043 | Add metrics (open SSE connections gauge, publish failure counter) and structured | 3.0 | backend-python, observability | yes | 002-T041 |
| 002-T044 | Create the fetch-stream SSE client with Authorization header, reconnect backoff  | 6.0 | frontend-react, messaging | no | 002-T008 |
| 002-T045 | Apply task.created, task.updated, task.moved and task.deleted messages to board  | 4.0 | frontend-react | yes | 002-T036, 002-T044 |
| 002-T046 | Start the board subscription when BoardPage mounts and show a "reconnecting" ind | 2.0 | frontend-react | yes | 002-T037, 002-T045 |

### S-002-US6 Use the board and task forms with the keyboard only — P2/should · 5 SP (low, llm)

As a team member who uses only the keyboard or assistive technology, I want to read the board, edit tasks and move tasks between columns using only the keyboard so that I can do my work with TaskFlow regardless of how I use my computer (WCAG 2.1 AA).
Depends on: S-FOUND-002 · Sources: NFR-4, US-2, FR-1

- [AC-S-002-US6-1] Given the board is open, When I press Tab and arrow keys, Then focus moves through columns and cards in a logical order with a visible focus indicator. (source: NFR-4)
- [AC-S-002-US6-2] Given a card has focus, When I use the keyboard to pick it up and drop it in another column, Then the task moves and the change is announced to screen readers. (source: NFR-4, US-2)
- [AC-S-002-US6-3] Given the task form is open, When I use only the keyboard, Then I can fill every field, submit, cancel, and Escape closes the form returning focus to where it was. (source: NFR-4, FR-1)
- [AC-S-002-US6-4] Given a form field has an error, When validation fails, Then the error is shown as text linked to the field and announced, not by colour alone. (source: NFR-4)
- [AC-S-002-US6-5] Given the board and task form screens, When an automated WCAG 2.1 AA check runs, Then it reports no serious or critical violations. (source: NFR-4)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 002-T047 | Accessibility tests running axe-core on BoardPage, TaskForm and ConfirmDeleteDia | 3.0 | qa-automation, frontend-react | yes | - |
| 002-T048 | Keyboard interaction tests (Tab order, Space or Enter to pick up, Left and Right | 5.0 | qa-automation, frontend-react | no | - |
| 002-T049 | Create the LiveAnnouncer component with an `aria-live="polite"` region in taskfl | 1.0 | frontend-react | yes | - |
| 002-T050 | Add keyboard pick-up, arrow-key column choice, drop and cancel to the card and c | 6.0 | frontend-react | no | 002-T035, 002-T049 |
| 002-T051 | Add focus trap, Escape to close, focus return to the opener, labelled inputs and | 4.0 | frontend-react | yes | 002-T026, 002-T027 |
| 002-T052 | Add landmarks, heading structure, the LiveAnnouncer for moves, remote updates an | 3.0 | frontend-react | yes | 002-T046, 002-T049 |
| 002-T053 | Add visible focus styles and sufficient colour contrast (text 4.5:1) for cards,  | 3.0 | frontend-css | yes | - |

### S-002-US7 Task assignment emits an event for notifications — P2/must · 3 SP (low, llm)

As a assignee, I want the system to record a task-assigned event whenever a task is assigned or reassigned to me so that the assignment email feature can notify me within a minute and I never miss new work.
Depends on: S-FOUND-002 · Sources: FR-1, US-1

- [AC-S-002-US7-1] Given an unassigned task, When I assign it to a board member, Then one task-assigned event naming the task, the new assignee and the person who assigned it is recorded. (source: FR-1)
- [AC-S-002-US7-2] Given an assigned task, When I change the assignee, Then one new event is recorded for the new assignee. (source: FR-1)
- [AC-S-002-US7-3] Given a task, When I edit other fields or save without changing the assignee, Then no assignment event is recorded. (source: FR-1)
- [AC-S-002-US7-4] Given a task is created already assigned, When it is saved, Then one assignment event is recorded. (source: US-1)
- [AC-S-002-US7-5] Given an assignment is saved, When something fails midway, Then either both the assignment and its event are stored or neither is, so the two never disagree. (source: FR-1, FR-5)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 002-T054 | Integration tests (event on create with assignee, on first assignment, on reassi | 5.0 | qa-automation, backend-python | no | - |
| 002-T055 | Write a TaskAssignmentEvent row (task, assignee, assigned_by) in the same transa | 4.0 | backend-python | yes | 002-T004, 002-T032 |
| 002-T056 | Document the event table and how feature 005 reads it (increasing id cursor, no  | 2.0 | docs, messaging | yes | - |

### S-SETUP-002 Tasks and board with live updates: Setup — P1/must · 1 SP (low, llm)

Depends on: - · Sources: E-002

- [AC-S-SETUP-002-1] Given the setup tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 002-T001 | Add board settings `BOARD_VIEW_CACHE_TTL_SECONDS` (default 60) and `SSE_HEARTBEA | 1.0 | backend-python | yes | - |
| 002-T002 | Create the feature folder taskflow-web/src/features/board/ with taskflow-web/src | 2.0 | qa-automation, frontend-react | yes | - |

### S-FOUND-002 Tasks and board with live updates: Foundational prerequisites — P1/must · 5 SP (low, llm)

Depends on: S-SETUP-002, S-001-US4 · Sources: E-002

- [AC-S-FOUND-002-1] Given the foundational prerequisites tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 002-T003 | Create the Task model in taskflow-api/app/models/task.py with columns and constr | 3.0 | backend-python, data-modeling | yes | - |
| 002-T004 | Create the TaskAssignmentEvent model in taskflow-api/app/models/task_assignment_ | 2.0 | backend-python, data-modeling | yes | - |
| 002-T005 | Add the Alembic migration creating `tasks` (index on board_id, status, created_a | 3.0 | postgres, backend-python | no | 002-T003, 002-T004 |
| 002-T006 | Create request and response schemas TaskCreate, TaskUpdate, TaskMove, TaskRead a | 3.0 | backend-python, api-design | yes | - |
| 002-T007 | Create taskflow-api/app/services/board_events.py with `publish_board_update(boar | 4.0 | backend-python, redis | yes | 002-T001 |
| 002-T008 | Create the REST client and TypeScript types for tasks and the board (create, get | 4.0 | frontend-react, api-design | yes | - |
| 002-T009 | Create integration test fixtures in taskflow-api/tests/integration/conftest.py:  | 4.0 | qa-automation, backend-python | no | - |

### S-POLISH-002 Tasks and board with live updates: Polish & cross-cutting concerns — P3/could · 3 SP (low, llm)

Depends on: S-002-US1, S-002-US2, S-002-US3, S-002-US4, S-002-US5, S-002-US6, S-002-US7 · Sources: E-002

- [AC-S-POLISH-002-1] Given the polish & cross-cutting concerns tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 002-T057 | Add OpenTelemetry spans around database, Redis and publish calls in taskflow-api | 3.0 | backend-python, observability | yes | 002-T055, 002-T018 |
| 002-T058 | Confirm the feature 001 health check covers database and Redis, and add the boar | 2.0 | backend-python, observability | yes | 002-T042 |
| 002-T059 | Set the ingress idle timeout for the path /api/v1/boards/*/events above 15 secon | 2.0 | kubernetes | no | - |
| 002-T060 | Add a load script for board and task endpoints at 50 requests per second asserti | 4.0 | qa-automation, backend-python | yes | 002-T042 |
| 002-T061 | Update docs for the task, board and SSE endpoints and the story points assumptio | 3.0 | docs, api-design | yes | - |
| 002-T062 | Run the quickstart.md validation in dev and record the result in specs/002-tasks | 2.0 | qa-automation, docs | no | 002-T046, 002-T052, 002-T055, 002-T059, 002-T060 |

## E-003 Full-text task search

PostgreSQL full-text search over titles and descriptions of the user's boards, p95 under 300 ms at 10,000 tasks.

### S-003-US1 Search tasks by keyword — P1/must · 3 SP (low, llm)

As a team member, I want to search tasks by keyword across my boards and get ranked results with highlighted excerpts so that I can find any task quickly.
Depends on: S-FOUND-003 · Sources: FR-4, US-4

- [AC-S-003-US1-1] Given I am a member of a board with a task titled "Prepare invoice report", When I search for "invoice", Then that task appears in the results. (source: FR-4, US-4)
- [AC-S-003-US1-2] Given a task whose description (not title) contains "migration", When I search for "migration", Then the task appears in the results. (source: FR-4)
- [AC-S-003-US1-3] Given two tasks, one with the search word in the title and one only in the description, When I search for that word, Then the title match is listed first. (source: FR-4)
- [AC-S-003-US1-4] Given no task matches my words, When I search, Then I see an empty-state message and no error. (source: FR-4)
- [AC-S-003-US1-5] Given a task is edited or deleted, When I search again, Then results reflect the change and never show a deleted task. (source: FR-4)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 003-T006 | Unit tests for query normalisation (trim, empty rejected, over 200 chars rejecte | 2.0 | qa-automation, backend-python | yes | - |
| 003-T007 | Integration tests for title match, description match, title-ranked-first, no mat | 4.0 | qa-automation, backend-python | yes | - |
| 003-T008 | Implement query normalisation and validation in app/services/search_query.py | 2.0 | backend-python | yes | - |
| 003-T009 | Implement search service with `websearch_to_tsquery`, `ts_rank`, `ts_headline` e | 6.0 | backend-python, postgres | no | 003-T003, 003-T005, 003-T008 |
| 003-T010 | Implement router `GET /api/v1/search/tasks` with 422 validation errors and regis | 3.0 | backend-python, api-design | yes | 003-T009 |

### S-003-US2 Results limited to my boards — P1/must · 3 SP (low, llm)

As a team member, I want search results limited to tasks on boards I belong to so that confidential task data from other boards is never exposed to me.
Depends on: S-FOUND-003, S-001-US6 · Sources: FR-4

- [AC-S-003-US2-1] Given user A is on board 1 and user B is on board 2, both with a task containing "budget", When A searches "budget", Then only the board 1 task is returned. (source: NFR-3, FR-4)
- [AC-S-003-US2-2] Given I search with a board filter for a board I am not a member of, When the request is made, Then the system refuses it without revealing whether the board or any matching task exists. (source: NFR-3)
- [AC-S-003-US2-3] Given I was removed from a board, When I search again, Then that board's tasks no longer appear, even if an earlier identical search was cached. (source: NFR-3)
- [AC-S-003-US2-4] Given I am not signed in, When I call search, Then the request is rejected. (source: NFR-3)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 003-T011 | Integration tests for per-user isolation, foreign `board_id` returning the same  | 4.0 | qa-automation, auth-security | no | - |
| 003-T012 | Restrict the SQL to `board_id = ANY(member board ids)` using the membership serv | 3.0 | backend-python, auth-security | no | 003-T009 |
| 003-T013 | Require authentication on the router and return 404 for a `board_id` outside the | 2.0 | auth-security, backend-python | no | 003-T010, 003-T012 |

### S-003-US3 Search stays fast at 10,000 tasks — P1/must · 5 SP (low, llm)

As a team member, I want search to respond in under 300 ms at 10,000 tasks without showing stale or foreign data so that I can find tasks quickly even in a large workspace.
Depends on: S-FOUND-003 · Sources: US-4, FR-4

- [AC-S-003-US3-1] Given 10,000 tasks exist, When a load test issues searches by a word in a task title, Then the p95 response time is under 300 ms. (source: US-4, NFR-1)
- [AC-S-003-US3-2] Given an identical search was made recently by the same user, When it is repeated, Then the result is served from the cache and is identical. (source: NFR-1)
- [AC-S-003-US3-3] Given a cached result exists, When a task on one of the user's boards is created, edited, moved or deleted, Then the next search does not return stale content beyond the documented freshness limit. (source: FR-4, NFR-1)
- [AC-S-003-US3-4] Given the cache is unavailable, When I search, Then I still get correct results directly from the database, only slower. (source: NFR-1)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 003-T014 | Integration tests for cache hit and miss, invalidation after task create/update/ | 5.0 | qa-automation, redis | no | - |
| 003-T015 | Integration test that EXPLAIN of the search query uses `ix_tasks_search_vector`  | 2.0 | qa-automation, postgres | yes | 003-T003 |
| 003-T016 | Implement Redis cache: key `search:v1:{sha256(user, member board ids, board vers | 6.0 | backend-python, redis | no | - |
| 003-T017 | Implement search telemetry: structured log fields (latency, cache hit or miss, r | 3.0 | backend-python, observability | yes | - |
| 003-T018 | Use the cache in the search service (read before query, write after) in app/serv | 3.0 | backend-python, redis | yes | 003-T012, 003-T016 |
| 003-T019 | Call `search_cache.bump_board(board_id)` on task create, update, move and delete | 2.0 | backend-python | no | 003-T016 |
| 003-T020 | Wire telemetry and the `X-Search-Cache` response header in app/api/search.py | 2.0 | backend-python, observability | yes | 003-T013, 003-T017, 003-T018 |
| 003-T021 | Create seed script that loads 10,000 tasks over several boards with realistic ti | 3.0 | qa-automation, postgres | yes | - |
| 003-T022 | Create load test issuing concurrent title-word searches against the seeded data  | 4.0 | qa-automation, backend-python | yes | 003-T020, 003-T021 |
| 003-T023 | Document how to run the seed and load test in dev and stg and how to read the re | 2.0 | docs, qa-automation | yes | 003-T022 |

### S-003-US4 Keyboard-usable search interface — P1/must · 5 SP (low, llm)

As a team member, I want to open the search, type a query, move through results and open a task using only the keyboard so that I can find tasks quickly without a mouse and with a screen reader.
Depends on: S-FOUND-003 · Sources: US-4

- [AC-S-003-US4-1] Given I am on the board page, When I press the documented shortcut or tab to the search box, Then the box receives visible focus. (source: NFR-4, US-4)
- [AC-S-003-US4-2] Given results are displayed, When I use the arrow keys, Then focus moves between results and Enter opens the focused task. (source: NFR-4)
- [AC-S-003-US4-3] Given results change, When a screen reader is in use, Then the number of results is announced. (source: NFR-4)
- [AC-S-003-US4-4] Given the results are open, When I press Escape, Then the results close and focus returns to the search box. (source: NFR-4)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 003-T024 | Component tests for keyboard flow (`/` shortcut, typing, arrow keys, Enter, Esca | 3.0 | qa-automation, frontend-react | yes | - |
| 003-T025 | Create search API client for `GET /api/v1/search/tasks` in src/api/search.ts | 1.5 | frontend-react, api-design | yes | - |
| 003-T026 | Create `useTaskSearch` hook with 250 ms debounce, request cancellation, loading, | 3.0 | frontend-react | yes | 003-T025 |
| 003-T027 | Create SearchBox component with combobox semantics, visible focus and `/` shortc | 4.0 | frontend-react | yes | 003-T026 |
| 003-T028 | Create SearchResults list (listbox, arrow-key navigation, Enter opens task, safe | 5.0 | frontend-react | no | 003-T026 |
| 003-T029 | Mount the search box in the board page, a small coordinated edit to the board UI | 2.0 | frontend-react | no | 003-T027, 003-T028 |
| 003-T030 | Add automated accessibility test (WCAG 2.1 AA rules) for the search UI in src/fe | 3.0 | qa-automation, frontend-react | yes | 003-T029 |

### S-SETUP-003 Full-text task search: Setup — P1/must · 1 SP (low, llm)

Depends on: - · Sources: E-003

- [AC-S-SETUP-003-1] Given the setup tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 003-T001 | Add search settings `SEARCH_CACHE_TTL_SECONDS` (default 60), `SEARCH_TS_CONFIG`  | 1.0 | backend-python | yes | - |
| 003-T002 | Create test data factory for boards, members and tasks with chosen titles and de | 3.0 | qa-automation, backend-python | yes | - |

### S-FOUND-003 Full-text task search: Foundational prerequisites — P1/must · 2 SP (low, llm)

Depends on: S-SETUP-003, S-FOUND-002 · Sources: E-003

- [AC-S-FOUND-003-1] Given the foundational prerequisites tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 003-T003 | Create Alembic migration adding generated stored column `search_vector` (title w | 4.0 | postgres, backend-python | no | - |
| 003-T004 | Add migration test checking the column, the index, and that title/description ed | 3.0 | qa-automation, backend-python | no | 003-T003 |
| 003-T005 | Create request and response schemas (`q` 1-200 chars, `limit` 1-50 default 20, ` | 2.0 | backend-python, api-design | yes | - |

### S-POLISH-003 Full-text task search: Polish & cross-cutting concerns — P3/could · 2 SP (low, llm)

Depends on: S-003-US1, S-003-US2, S-003-US3, S-003-US4 · Sources: E-003

- [AC-S-POLISH-003-1] Given the polish & cross-cutting concerns tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 003-T031 | Document the search endpoint, assumptions (language, TTL, page size) and cache i | 2.0 | docs, api-design | yes | - |
| 003-T032 | Add a readiness check that the search index exists to the API health endpoint (s | 2.0 | backend-python, api-design | yes | - |
| 003-T033 | Record the explicit security review of the membership filter and cache key (cons | 3.0 | auth-security, docs | no | 003-T032 |
| 003-T034 | Run the quickstart.md validation scenarios in dev and record results in specs/00 | 2.0 | qa-automation, docs | no | 003-T033 |

## E-004 Comments and @mentions

Comment on tasks, mention teammates with @name, mention triggers notification.

### S-004-US1 Post and read comments on a task — P2/should · 5 SP (low, llm)

As a team member, I want post comments on a task and read the comments of my teammates so that discussions stay with the work.
Depends on: S-FOUND-004 · Sources: US-3, FR-3

- [AC-S-004-US1-1] Given a task on a board I belong to, When I post a comment with text, Then the comment appears in the task's comment list with my name and the time it was posted. (source: US-3, FR-3)
- [AC-S-004-US1-2] Given a task with several comments, When I open the task, Then I see all comments in the order they were posted, oldest first. (source: FR-3)
- [AC-S-004-US1-3] Given I am not a member of the task's board, When I try to read or post comments on that task, Then access is refused and no comment content is revealed. (source: NFR-3)
- [AC-S-004-US1-4] Given I submit an empty or whitespace-only comment, When I post it, Then it is rejected with a clear message and nothing is stored. (source: FR-3)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 004-T006 | Integration tests for POST/GET comments (create, order oldest first, empty and o | 5.0 | qa-automation, backend-python | no | - |
| 004-T007 | Component tests for listing and posting a comment in `src/features/comments/__te | 3.0 | qa-automation, frontend-react | yes | - |
| 004-T008 | Create request and response schemas with body validation (not empty after trimmi | 2.0 | backend-python, api-design | yes | - |
| 004-T009 | Implement `create_comment` and `list_comments` (order by created_at then id, lim | 4.0 | backend-python | yes | 004-T004, 004-T008 |
| 004-T010 | Implement `GET` and `POST /api/v1/tasks/{task_id}/comments` with the board-membe | 4.0 | backend-python, api-design | no | 004-T009 |
| 004-T011 | Add structured logging and metrics for comment creation and rejected requests in | 2.0 | backend-python, observability | yes | 004-T009 |
| 004-T012 | Implement the API client functions `listComments` and `postComment` in `src/api/ | 2.0 | frontend-react, api-design | yes | - |
| 004-T013 | Implement `CommentList` (author, time, text, oldest first) in `src/features/comm | 3.0 | frontend-react | yes | 004-T012 |
| 004-T014 | Implement `CommentForm` with empty-text and too-long error messages in `src/feat | 3.0 | frontend-react | yes | 004-T012 |
| 004-T015 | Show the comment section on the task view of the board UI, hidden when the flag  | 2.0 | frontend-react | yes | 004-T013, 004-T014 |

### S-004-US2 Mention teammates and notify them — P2/should · 5 SP (low, llm)

As a team member, I want mention a teammate with @name in a comment so that the teammate is notified and the discussion reaches them.
Depends on: S-FOUND-004, S-FOUND-005 · Sources: US-3, FR-3

- [AC-S-004-US2-1] Given a task and a board member Alice, When I post a comment mentioning @alice, Then Alice receives a notification (email, the only channel in this release). (source: US-3, FR-3)
- [AC-S-004-US2-2] Given a comment that mentions @alice twice, When it is posted, Then Alice receives one notification for that comment. (source: FR-3)
- [AC-S-004-US2-3] Given a comment that mentions someone who is not a member of the board, When it is posted, Then the comment is stored, the text is kept as plain text, no notification is sent, and the author is not told whether that person exists. (source: NFR-3; assumption A2)
- [AC-S-004-US2-4] Given I mention myself, When I post the comment, Then I receive no notification. (source: FR-3; assumption A4)
- [AC-S-004-US2-5] Given the email service is temporarily unavailable, When I post a comment with a mention, Then the comment is still saved and the notification is delivered later. (source: FR-3)
- [AC-S-004-US2-6] Given the notification preferences feature is available and Alice has turned mention notifications off, When I mention her, Then she receives no email. (source: Assumption in prd.md section 7, US-7)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 004-T016 | Unit tests for the mention parser (case-insensitive, duplicates, trailing dot, ` | 3.0 | qa-automation, backend-python | yes | - |
| 004-T017 | Integration tests for mention notifications (one outbox row per distinct mention | 6.0 | qa-automation, backend-python | no | - |
| 004-T018 | Implement `parse_mentions` and `resolve_mentions` (username, case-insensitive, c | 4.0 | backend-python | yes | 004-T016 |
| 004-T019 | Confirm the outbox enqueue interface owned by feature 005-assignment-email and r | 2.0 | docs, api-design | no | 004-T018 |
| 004-T020 | In `app/services/comments.py`, store `comment_mentions` and enqueue one `mention | 6.0 | backend-python, auth-security | no | 004-T009, 004-T018, 004-T019 |
| 004-T021 | Add the mention email template (author, task title, comment text, link to the ta | 3.0 | backend-python | no | 004-T019 |
| 004-T022 | Return `mentions` in the comment schema and API response in `app/schemas/comment | 2.0 | backend-python, api-design | yes | 004-T020 |
| 004-T023 | Render mentions highlighted in comment text in `src/features/comments/CommentLis | 2.0 | frontend-react | yes | 004-T022 |
| 004-T024 | Add structured logging and a metric for mention notifications enqueued in `app/s | 2.0 | backend-python, observability | yes | 004-T020 |

### S-004-US3 Use comments and mentions with the keyboard only — P2/should · 3 SP (low, llm)

As a team member who cannot use a pointing device, I want read, write and post comments and mentions with the keyboard only so that the feature is accessible.
Depends on: S-FOUND-004 · Sources: FR-3, US-3

- [AC-S-004-US3-1] Given the task view is open, When I navigate with Tab and Shift+Tab, Then I can reach the comment list, the comment input and the post button in a logical order with a visible focus indicator. (source: NFR-4)
- [AC-S-004-US3-2] Given the comment input has focus, When I type a comment with an @mention and press the post button with Enter or Space, Then the comment is posted without any mouse action. (source: NFR-4)
- [AC-S-004-US3-3] Given a new comment or an error message appears, When I use a screen reader, Then the change is announced. (source: NFR-4)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 004-T025 | Keyboard and accessibility tests (tab order, Enter/Space on the post button, liv | 6.0 | qa-automation, frontend-react | no | - |
| 004-T026 | Make `CommentForm` keyboard-operable with a labelled textarea, native button and | 4.0 | frontend-react | yes | 004-T014 |
| 004-T027 | Add an `aria-live` region that announces new comments and error messages in `src | 4.0 | frontend-react | yes | 004-T015 |
| 004-T028 | Ensure a logical tab order between the comment list, input and post button and a | 4.0 | frontend-react | yes | 004-T027 |

### S-SETUP-004 Comments and @mentions: Setup — P2/should · 1 SP (low, llm)

Depends on: - · Sources: E-004

- [AC-S-SETUP-004-1] Given the setup tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 004-T001 | Add the `FEATURE_COMMENTS` setting (read from env `FEATURE_COMMENTS`, default of | 1.0 | backend-python | yes | - |
| 004-T002 | Create empty module skeletons `app/api/comments.py`, `app/services/comments.py`, | 3.0 | backend-python | no | 004-T001 |
| 004-T003 | Create the folder `src/features/comments/` and API client stub `src/api/comments | 2.0 | frontend-react | yes | - |

### S-FOUND-004 Comments and @mentions: Foundational prerequisites — P2/should · 2 SP (low, llm)

Depends on: S-SETUP-004, S-FOUND-002 · Sources: E-004

- [AC-S-FOUND-004-1] Given the foundational prerequisites tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 004-T004 | Create the Comment and CommentMention models in `app/models/comment.py`: `commen | 5.0 | backend-python, data-modeling | no | - |
| 004-T005 | Create the Alembic migration for `comments` and `comment_mentions` with index (t | 7.0 | postgres, backend-python | no | 004-T004 |

### S-POLISH-004 Comments and @mentions: Polish & cross-cutting concerns — P3/could · 2 SP (low, llm)

Depends on: S-004-US1, S-004-US2, S-004-US3 · Sources: E-004

- [AC-S-POLISH-004-1] Given the polish & cross-cutting concerns tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 004-T029 | Update documentation for the comments API, the `FEATURE_COMMENTS` flag and the m | 3.0 | docs, api-design | yes | - |
| 004-T030 | Security review of membership checks and input validation across `app/api/commen | 6.0 | auth-security, backend-python | no | - |
| 004-T031 | Run the validation steps in `specs/004-comments-mentions/quickstart.md` in the d | 3.0 | docs, qa-automation | no | 004-T030 |

## E-005 Assignment email notification

Email to assignee within 1 minute of assignment via notify-worker and email provider API.

### S-005-US1 Assignee is emailed when a task is assigned — P1/must · 5 SP (low, llm)

As a assignee (team member or manager), I want an email when a task is assigned to me, naming the task, board, assigner, due date and a link so that I never miss new work.
Depends on: S-FOUND-005, S-002-US7 · Sources: US-5, FR-5

- [AC-S-005-US1-1] Given a task on a board, When it is assigned to me, Then I receive one email within 1 minute. (source: US-5, FR-5)
- [AC-S-005-US1-2] Given a task created with an assignee, When the task is saved, Then the assignee receives the assignment email in the same way as for a later assignment. (source: FR-1, FR-5)
- [AC-S-005-US1-3] Given a task assigned to Alice, When it is reassigned to Bob, Then Bob receives one assignment email and Alice receives no assignment email for this change. (source: FR-5)
- [AC-S-005-US1-4] Given an assignment email, When I open it, Then it contains the task title, board name, the name of the person who assigned it, the due date (if set) and a link to the task, and no data from tasks I cannot see. (source: FR-5, NFR-3)
- [AC-S-005-US1-5] Given a manager assigns a task to themselves, When the assignment is saved, Then an assignment email is sent to them as for any other assignee. Assumed: yes (open question Q1). (source: FR-5)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 005-T010 | Integration test that assigning a task (on create and on reassignment) writes on | 4.0 | qa-automation, backend-python | yes | - |
| 005-T011 | Unit test of the email content (title, board, assigner, due date, link, HTML esc | 2.0 | qa-automation, backend-python | yes | - |
| 005-T012 | Unit test of the send job with `FakeEmailClient` (one message to the assignee on | 3.0 | qa-automation, backend-python | yes | - |
| 005-T013 | Implement subject and body rendering per contracts/assignment-email.md in `app/w | 3.0 | backend-python, api-design | yes | 005-T011 |
| 005-T014 | Implement the job that loads task, board, assignee and assigner, renders the ema | 5.0 | backend-python | no | 005-T013 |
| 005-T015 | Implement the dispatcher that claims due outbox rows and calls the job by `kind` | 5.0 | backend-python | no | 005-T014 |
| 005-T016 | Run the dispatcher from the poll loop in `app/worker/main.py` | 2.0 | backend-python | yes | 005-T015 |
| 005-T017 | Call `enqueue_assignment_notification` with a new `assignment_event_id` inside t | 3.0 | backend-python | no | 005-T007 |
| 005-T018 | Latency test: assignment saved to email handed to the client takes under 60 s wi | 3.0 | qa-automation, backend-python | yes | 005-T016 |

### S-005-US2 One email per assignment, none lost — P1/must · 5 SP (low, llm)

As a assignee, I want receive exactly one email per assignment, even when the system retries, restarts or the email provider has a problem so that I am neither spammed with duplicates nor left without a notification.
Depends on: S-FOUND-005 · Sources: US-5, FR-5

- [AC-S-005-US2-1] Given the same assignment is reported twice, When the notification is recorded, Then only one notification exists and one email is sent. (source: US-5)
- [AC-S-005-US2-2] Given two notify-worker instances are running, When one notification is due, Then only one instance sends it. (source: US-5)
- [AC-S-005-US2-3] Given the notify-worker is stopped or the email provider is unavailable when a task is assigned, When the service recovers, Then the email is still sent, once. (source: FR-5, G2)
- [AC-S-005-US2-4] Given the email provider returns a temporary error, When the worker retries, Then the email is sent once on the first successful attempt and no further attempts are made. (source: FR-5)
- [AC-S-005-US2-5] Given the email provider rejects an email permanently (for example an invalid address), When the worker handles the error, Then the notification is marked failed with the reason, is not retried and is visible to operators. (source: FR-5)
- [AC-S-005-US2-6] Given the task was deleted or the assignee has no usable email address when the worker processes the notification, When the worker handles it, Then no email is sent and the notification is marked skipped with the reason. (source: FR-5, NFR-3)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 005-T019 | Test that enqueueing the same assignment event twice yields one row and returns  | 2.0 | qa-automation, backend-python | yes | - |
| 005-T020 | Test that two dispatchers running concurrently on PostgreSQL send each notificat | 3.0 | qa-automation, postgres | yes | - |
| 005-T021 | Test retry with backoff (5 s, 15 s, 60 s, 5 min, 15 min), maximum 6 attempts, an | 3.0 | qa-automation, backend-python | yes | - |
| 005-T022 | Test that a row left in `sending` longer than `NOTIFY_CLAIM_TIMEOUT_SECONDS` is  | 3.0 | qa-automation, backend-python | yes | - |
| 005-T023 | Test that a deleted task or an assignee without a usable email address ends as ` | 2.0 | qa-automation, backend-python | yes | - |
| 005-T024 | Make enqueue insert-on-conflict-do-nothing on `dedupe_key` and return whether a  | 2.0 | backend-python, postgres | yes | 005-T019 |
| 005-T025 | Make `claim_due` use `FOR UPDATE SKIP LOCKED`, set `sending` and `claimed_at`, a | 5.0 | backend-python, postgres | no | 005-T024 |
| 005-T026 | Implement transient-error rescheduling with the backoff list, maximum attempts a | 5.0 | backend-python | no | 005-T015, 005-T021 |
| 005-T027 | Classify provider responses (timeout, connection error, 429, 5xx as transient; o | 3.0 | backend-python, api-design | yes | 005-T005 |
| 005-T028 | Implement skip rules (task deleted, no usable assignee address) in `app/worker/j | 2.0 | backend-python | yes | 005-T014, 005-T023 |

### S-005-US3 Operators can see delivery health and failures — P2/should · 3 SP (low, llm)

As a operator of TaskFlow, I want logs, metrics and an alert for assignment email delivery so that I notice delayed or failing emails before assignees miss work.
Depends on: S-FOUND-005 · Sources: FR-5

- [AC-S-005-US3-1] Given the worker sends an email, When the send finishes, Then a structured log entry and metrics record the outcome (sent, retry, failed, skipped) and the time from assignment to send. (source: FR-5)
- [AC-S-005-US3-2] Given a pending notification is older than 45 seconds, When the alert rules are evaluated, Then an alert warns the operators before the 1-minute limit is exceeded. (source: FR-5)
- [AC-S-005-US3-3] Given the worker process stops making progress, When the health check runs, Then the pod is reported unhealthy and restarted. (source: NFR-2)
- [AC-S-005-US3-4] Given any log line or metric, When it is inspected, Then it contains no email provider key and no email body. (source: NFR-3)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 005-T029 | Test that outcomes (sent, retry, failed, skipped), the assignment-to-send durati | 2.0 | qa-automation, observability | yes | - |
| 005-T030 | Implement structured logging, OpenTelemetry metrics (`notify_outcome_total`, `no | 4.0 | observability, backend-python | no | 005-T029 |
| 005-T031 | Instrument the dispatcher with the telemetry module in `app/worker/outbox_dispat | 2.0 | backend-python, observability | yes | 005-T026, 005-T030 |
| 005-T032 | Implement the heartbeat file updated on each poll loop in `app/worker/health.py` | 2.0 | backend-python | yes | 005-T008 |
| 005-T033 | Add a liveness exec probe on the heartbeat age to `k8s/notify-worker/deployment. | 2.0 | kubernetes | no | 005-T032 |
| 005-T034 | Add alert rules (oldest pending notification older than 45 s, any `failed` notif | 3.0 | terraform, observability | no | 005-T030 |
| 005-T035 | Write the operator runbook (reading `notification_outbox` states, requeueing a ` | 3.0 | docs, observability | yes | - |

### S-SETUP-005 Assignment email notification: Setup — P1/must · 1 SP (low, llm)

Depends on: - · Sources: E-005

- [AC-S-SETUP-005-1] Given the setup tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 005-T001 | Add settings `EMAIL_PROVIDER_API_KEY`, `EMAIL_PROVIDER_BASE_URL`, `EMAIL_FROM_AD | 2.0 | backend-python | no | - |
| 005-T002 | Create the package skeleton `app/worker/__init__.py`, `app/worker/jobs/__init__. | 1.0 | backend-python, qa-automation | no | - |

### S-FOUND-005 Assignment email notification: Foundational prerequisites — P1/must · 5 SP (low, llm)

Depends on: S-SETUP-005, S-001-US4, S-001-US3 · Sources: E-005

- [AC-S-FOUND-005-1] Given the foundational prerequisites tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 005-T003 | Create Alembic migration `migrations/versions/005_notification_outbox.py` for ta | 3.0 | postgres, backend-python | no | - |
| 005-T004 | Create the `NotificationOutbox` model in `app/models/notification_outbox.py` and | 2.0 | backend-python, data-modeling | yes | 005-T003 |
| 005-T005 | Implement the provider-agnostic `EmailClient`, `EmailMessage`, `SendResult`, `Tr | 6.0 | api-design, backend-python | no | 005-T001 |
| 005-T006 | Create `FakeEmailClient` (records messages, can fail transiently or permanently  | 3.0 | qa-automation, backend-python | yes | 005-T005 |
| 005-T007 | Implement `enqueue_assignment_notification`, `claim_due`, `mark_sent`, `mark_ret | 7.0 | backend-python, api-design | no | 005-T004 |
| 005-T008 | Create the notify-worker entrypoint `app/worker/main.py` (`python -m app.worker. | 4.0 | backend-python | yes | 005-T001 |
| 005-T009 | Wire the email provider key into the worker pod in acme/taskflow-infra: create ` | 5.0 | kubernetes | no | - |

### S-POLISH-005 Assignment email notification: Polish & cross-cutting concerns — P3/could · 1 SP (low, llm)

Depends on: S-005-US1, S-005-US2, S-005-US3 · Sources: E-005

- [AC-S-POLISH-005-1] Given the polish & cross-cutting concerns tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 005-T036 | Test that the provider key and email bodies never appear in worker logs or error | 2.0 | qa-automation, backend-python | yes | - |
| 005-T037 | Document the outbox, client and worker for reuse by F04, F06 and F07, the retry  | 2.0 | docs | yes | - |
| 005-T038 | Run the quickstart validation on dev and record the result in `specs/005-assignm | 2.0 | docs, qa-automation | no | - |

## E-006 Daily due-tomorrow digest

Daily digest email of tasks due tomorrow at 08:00 in the user's time zone.

### S-006-US1 Receive a daily digest of tasks due tomorrow — P2/should · 5 SP (low, llm)

As a team member, I want one email each morning at 08:00 in my time zone that lists the tasks assigned to me that are due tomorrow so that I can plan my day.
Depends on: S-FOUND-006, S-FOUND-002 · Sources: US-6, FR-6

- [AC-S-006-US1-1] Given tasks due tomorrow assigned to me, When the daily digest runs at 08:00 in my time zone, Then I receive one email listing them. (source: US-6, FR-6)
- [AC-S-006-US1-2] Given tasks due tomorrow assigned to me on several boards I belong to, When the digest runs, Then one single email lists all of them, grouped by board, and each task shows its title, board and due date. (source: FR-6)
- [AC-S-006-US1-3] Given I have no open tasks due tomorrow, When the digest runs, Then I receive no email (assumed, open question Q3). (source: FR-6)
- [AC-S-006-US1-4] Given a task due tomorrow is already in the "Done" column, When the digest runs, Then it is not listed (assumption A3). (source: FR-6)
- [AC-S-006-US1-5] Given a task due tomorrow is assigned to a colleague, When the digest runs for me, Then it is not listed in my email. (source: FR-6, NFR-3)
- [AC-S-006-US1-6] Given I am no longer a member of a board, When the digest runs, Then tasks from that board are not listed. (source: FR-6, NFR-3)
- [AC-S-006-US1-7] Given the digest feature flag is off, When the scheduled run starts, Then no digest is sent. (source: FR-6)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 006-T006 | Integration test for the due-tomorrow query (open only, assignee only, member bo | 3.0 | qa-automation, backend-python | yes | - |
| 006-T007 | Unit test for email composition (grouped by board, title, board, due date, "+N m | 2.0 | qa-automation, backend-python | yes | - |
| 006-T008 | Integration test for the job: one email at 08:00 local, none before, none withou | 4.0 | qa-automation, backend-python | yes | - |
| 006-T009 | Implement local-time helpers in app/services/digest_schedule.py: local now from  | 3.0 | backend-python, qa-automation | yes | - |
| 006-T010 | Implement the users-and-tasks query in app/services/digest_query.py joining task | 3.0 | backend-python, postgres | yes | 006-T004 |
| 006-T011 | Implement digest subject and text body rendering in app/services/digest_email.py | 2.0 | backend-python | yes | - |
| 006-T012 | Implement `digest_allowed(user_id)` in app/services/digest_preferences.py: True  | 2.0 | backend-python | yes | - |
| 006-T013 | Implement the digest job in app/worker/jobs/daily_digest.py: exit when `FEATURE_ | 5.0 | backend-python | no | 006-T009, 006-T010, 006-T011, 006-T012 |
| 006-T014 | Add structured logs, metrics (evaluated, sent, skipped, failed) and a trace span | 2.0 | backend-python, observability | yes | 006-T013 |
| 006-T015 | Add the CronJob manifest running the notify-worker image with the digest command | 2.0 | kubernetes | no | - |

### S-006-US2 Capture and change my time zone — P2/should · 3 SP (low, llm)

As a team member, I want my time zone stored on my profile so that the digest arrives at 08:00 where I am.
Depends on: S-FOUND-006 · Sources: US-6, FR-6

- [AC-S-006-US2-1] Given I open my settings, When I choose a time zone from the list of valid zones and save, Then it is stored and shown the next time I open settings. (source: FR-6)
- [AC-S-006-US2-2] Given I have not chosen a time zone, When I open settings for the first time, Then the zone detected by my browser is pre-selected and I can confirm or change it (assumed, open question Q2). (source: FR-6)
- [AC-S-006-US2-3] Given a value that is not a valid time zone name, When it is submitted, Then it is rejected with a clear error and my stored value is unchanged. (source: FR-6)
- [AC-S-006-US2-4] Given I have never saved a time zone, When the digest runs, Then my 08:00 is computed in UTC (assumption A2). (source: FR-6)
- [AC-S-006-US2-5] Given I change my time zone, When the next digest runs, Then it uses the new zone, and I do not get a second digest for a day that already had one. (source: FR-6)
- [AC-S-006-US2-6] Given I use the keyboard only, When I choose and save a time zone, Then I can complete every step. (source: NFR-4)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 006-T016 | Contract test for GET and PUT `/api/v1/users/me/timezone` (200, 401, 422, own pr | 3.0 | qa-automation, backend-python | no | - |
| 006-T021 | Component test for the time zone control (browser zone pre-selected, save, error | 3.0 | qa-automation, frontend-react | yes | - |
| 006-T017 | Create request and response schemas in app/schemas/timezone.py validating "requi | 2.0 | backend-python, api-design | yes | - |
| 006-T018 | Implement the GET and PUT endpoints in app/api/timezone.py updating only the aut | 3.0 | backend-python, api-design | no | 006-T004, 006-T017 |
| 006-T019 | Register the timezone router under the `/api/v1` prefix in app/main.py (A) | 1.0 | backend-python | yes | 006-T018 |
| 006-T020 | Add the API client functions getTimeZone and setTimeZone in src/api/timezone.ts | 1.0 | frontend-react, api-design | yes | - |
| 006-T022 | Implement the time zone control with a labelled, keyboard-operable select pre-fi | 3.0 | frontend-react | yes | 006-T020, 006-T021 |
| 006-T023 | Mount the control in the user settings screen at src/features/settings/SettingsP | 2.0 | frontend-react | yes | 006-T022 |

### S-006-US3 Exactly one digest per user per day, correct across DST — P2/should · 5 SP (low, llm)

As a team member, I want receive the digest once per day, never twice and never skipped, including on days when my clocks change so that I can trust it.
Depends on: S-FOUND-006 · Sources: US-6, FR-6

- [AC-S-006-US3-1] Given the digest already went out to me for today's local date, When the scheduler runs again, even concurrently or after a restart, Then I get no second email. (source: US-6, FR-6)
- [AC-S-006-US3-2] Given a send failed before the provider accepted it, When a later scheduler run happens on the same local date, Then sending is retried, up to 3 attempts in total (assumption A6). (source: FR-6)
- [AC-S-006-US3-3] Given my time zone changes clocks forward on a given day, When the digest runs, Then I receive it at 08:00 local time once, and "tomorrow" is the next calendar date, not 24 hours later. (source: FR-6)
- [AC-S-006-US3-4] Given my time zone changes clocks back on a given day, When the digest runs, Then I receive it once. (source: FR-6)
- [AC-S-006-US3-5] Given the scheduler was down at 08:00, When it comes back later the same local day, Then the digest is still sent once that day and never for a past day. (source: FR-6)
- [AC-S-006-US3-6] Given many users across several time zones, When each reaches 08:00 local, Then each receives their own digest at their own local time. (source: FR-6)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 006-T024 | Unit tests for DST: spring forward and fall back in `Europe/Berlin` and `America | 5.0 | qa-automation, backend-python | no | - |
| 006-T025 | Integration test that repeated and parallel job runs and a restart yield one ema | 4.0 | qa-automation, backend-python | yes | - |
| 006-T026 | Integration test for retry: provider failure retried on later ticks up to 3 atte | 4.0 | qa-automation, backend-python | yes | - |
| 006-T027 | Implement claim, mark sent, mark failed and re-claim (`attempts < 3`) with `INSE | 5.0 | backend-python, postgres | no | 006-T005 |
| 006-T028 | Make app/services/digest_schedule.py DST-safe and catch-up aware so that the uni | 5.0 | backend-python, qa-automation | no | 006-T009, 006-T024 |
| 006-T029 | Wrap each send in the claim and status updates in app/worker/jobs/daily_digest.p | 4.0 | backend-python | no | 006-T013, 006-T027, 006-T028 |
| 006-T030 | Add retry handling and a log line and metric for stuck `claimed` rows in app/wor | 3.0 | backend-python, observability | yes | 006-T029 |

### S-SETUP-006 Daily due-tomorrow digest: Setup — P2/should · 1 SP (low, llm)

Depends on: - · Sources: E-006

- [AC-S-SETUP-006-1] Given the setup tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 006-T001 | Add the `FEATURE_DIGEST` flag (read from env `FEATURE_DIGEST`, default off) to t | 2.0 | backend-python | yes | - |
| 006-T002 | Add a recording fake of the feature-005 email client and a controllable clock fi | 4.0 | qa-automation, backend-python | yes | - |

### S-FOUND-006 Daily due-tomorrow digest: Foundational prerequisites — P2/should · 2 SP (low, llm)

Depends on: S-SETUP-006, S-FOUND-005 · Sources: E-006

- [AC-S-FOUND-006-1] Given the foundational prerequisites tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 006-T003 | Create the Alembic migration migrations/versions/006_user_timezone_digest_delive | 6.0 | postgres, backend-python | no | - |
| 006-T004 | Add the nullable `timezone` column to the User model in app/models/user.py | 2.0 | backend-python, data-modeling | yes | 006-T003 |
| 006-T005 | Create the DigestDelivery model in app/models/digest_delivery.py with fields id, | 4.0 | backend-python, data-modeling | yes | 006-T003 |

### S-POLISH-006 Daily due-tomorrow digest: Polish & cross-cutting concerns — P3/could · 2 SP (low, llm)

Depends on: S-006-US1, S-006-US2, S-006-US3 · Sources: E-006

- [AC-S-POLISH-006-1] Given the polish & cross-cutting concerns tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 006-T031 | Document the scheduler, flag, time zone behaviour, assumptions Q1-Q3 and stuck-c | 4.0 | docs | yes | - |
| 006-T032 | Run the quickstart.md validation scenarios against dev with `FEATURE_DIGEST` ena | 4.0 | docs, qa-automation | no | 006-T015, 006-T023, 006-T030 |
| 006-T033 | Security review of the time zone endpoint, the membership filter in app/services | 4.0 | kubernetes, backend-python | no | 006-T032 |

## E-007 Notification preferences

Per-user notification preferences: channel and frequency (channels/frequencies undecided).

### S-007-US1 Choose which notifications I receive — P1/must · 5 SP (low, llm)

As a team member, I want to see every notification type TaskFlow can send me and switch each on or off so that I only receive the notifications I want and am not overwhelmed.
Depends on: S-FOUND-007 · Sources: FR-7, US-7

- [AC-S-007-US1-1] Given a user who never saved preferences, When they open the notification settings, Then every notification type is shown as on with channel "email" and the default frequency, which equals today's behaviour. (source: FR-7, US-7)
- [AC-S-007-US1-2] Given the settings page, When the user switches "Mention" off and saves, Then the choice is persisted and shown again after a page reload and a new sign-in. (source: FR-7, US-7)
- [AC-S-007-US1-3] Given the settings page, When the user navigates and changes every control with the keyboard only, Then every control is reachable, shows a visible focus, has an accessible name and can be saved without a mouse. (source: NFR-4)
- [AC-S-007-US1-4] Given user A saved preferences, When user B requests or changes preferences, Then B only ever sees and changes B's own preferences. (source: NFR-3, FR-7)
- [AC-S-007-US1-5] Given the flag FEATURE_NOTIFICATION_PREFS is off, When a user requests the preferences endpoints or the settings page, Then they are not available (not found) and the settings link is not shown. (source: FR-7)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 007-T010 | Write API contract tests (GET defaults with all types on; PUT persists; another  | 3.0 | qa-automation, api-design | no | - |
| 007-T011 | Write service unit tests for `get_preferences` (defaults filled in) and `save_pr | 3.0 | qa-automation, backend-python | yes | - |
| 007-T012 | Write component tests (renders every type, toggles and saves, shows confirmation | 4.0 | qa-automation, frontend-react | yes | - |
| 007-T013 | Implement `get_preferences(user_id)` and `save_preferences(user_id, payload)` in | 4.0 | backend-python | no | 007-T004, 007-T005, 007-T006 |
| 007-T014 | Implement the router with `GET` and `PUT /api/v1/users/me/notification-preferenc | 3.0 | backend-python, api-design | no | 007-T013 |
| 007-T015 | Register the router in the application entry point `app/main.py` | 0.5 | backend-python | yes | 007-T014 |
| 007-T016 | Create the API client `getPreferences` and `savePreferences` in `src/api/notific | 1.5 | frontend-react, api-design | yes | - |
| 007-T017 | Build the settings page with one labelled checkbox per type, a save button, a po | 5.0 | frontend-react, frontend-css | no | 007-T016 |
| 007-T018 | Add the settings route and a settings link shown only when the preferences reque | 2.0 | frontend-react | yes | 007-T017 |

### S-007-US2 Choose how often I am notified — P2/should · 5 SP (low, llm)

As a team member, I want to choose how often I am notified for each type that supports a frequency so that notifications are grouped into one summary email instead of arriving one by one.
Depends on: S-FOUND-007 · Sources: FR-7, US-7

- [AC-S-007-US2-1] Given the settings page, When the user opens the frequency control of a notification type, Then only the frequencies currently enabled in the configuration are offered, with "immediate" preselected for a user without saved preferences. (source: FR-7, US-7)
- [AC-S-007-US2-2] Given a user with "Mention" set to hourly, When three mentions occur within the same hour, Then the user receives one summary email listing the three mentions at the end of the hour and no individual emails. (source: FR-7, US-7)
- [AC-S-007-US2-3] Given a user with "Mention" set to immediate, When a mention occurs, Then the mention email is sent without added delay. (source: FR-7, FR-3)
- [AC-S-007-US2-4] Given a frequency value that is not enabled in the configuration, When a client submits it, Then the request is rejected with a validation error and nothing is saved. (source: FR-7)
- [AC-S-007-US2-5] Given a notification type whose schedule is fixed (the daily digest, sent at 08:00 in the user's time zone), When the user opens its settings, Then only on/off is offered for it. (source: FR-6, FR-7)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 007-T019 | Write service tests for frequency validation (disabled or unknown frequency reje | 2.0 | qa-automation, backend-python | yes | - |
| 007-T020 | Write worker tests (three held mentions in one window produce one summary email; | 4.0 | qa-automation, backend-python | yes | - |
| 007-T021 | Write component tests for the frequency control (only enabled frequencies offere | 2.0 | qa-automation, frontend-react | yes | - |
| 007-T022 | Extend `save_preferences` and `get_preferences` with frequency validation and th | 3.0 | backend-python | yes | 007-T013, 007-T019 |
| 007-T023 | Build the summary email content (grouped list per user, type and window) in `app | 3.0 | backend-python | yes | - |
| 007-T024 | Implement the notify-worker job that finds due held notifications in the 005 out | 6.0 | backend-python | no | 007-T008, 007-T020, 007-T023 |
| 007-T025 | Drop the held outbox notifications of a type when the user switches that type of | 3.0 | backend-python | yes | 007-T022, 007-T024 |
| 007-T026 | Add the native frequency select per type (labelled, keyboard operable, hidden fo | 3.0 | frontend-react | yes | 007-T017, 007-T021 |

### S-007-US3 Senders respect my preferences — P2/should · 3 SP (low, llm)

As a team member, I want the assignment, daily digest and mention senders to consult my preferences before sending so that a notification I switched off or delayed is never sent immediately.
Depends on: S-FOUND-007, S-005-US1, S-006-US1, S-004-US2 · Sources: FR-7, US-7

- [AC-S-007-US3-1] Given user A has "Assignment" switched off, When a task is assigned to A, Then no assignment email is sent to A. (source: FR-7, FR-5)
- [AC-S-007-US3-2] Given user B has "Daily digest" switched off, When the digest runs for B, Then B receives no digest. (source: FR-7, FR-6)
- [AC-S-007-US3-3] Given user C has no saved preferences, When any sender asks for the decision, Then the answer is "send now", i.e. the behaviour defined by the sender's own story is unchanged. (source: FR-7)
- [AC-S-007-US3-4] Given the flag FEATURE_NOTIFICATION_PREFS is off, When any sender asks for the decision, Then the answer is "send now" for every user. (source: FR-7)
- [AC-S-007-US3-5] Given the preferences cannot be read (for example a database error), When a sender asks for the decision, Then the sender falls back to "send now", the failure is logged and a metric is raised. (source: FR-7, G2)

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 007-T027 | Write unit tests for `resolve_delivery` (off gives skip; no row gives send_now;  | 3.0 | qa-automation, backend-python | yes | - |
| 007-T028 | Write integration tests for the three senders (assignment off for A and on for B | 4.0 | qa-automation, backend-python | yes | - |
| 007-T029 | Implement `resolve_delivery(user_id, notification_type, channel, now)` as in `co | 4.0 | api-design, backend-python | yes | 007-T008, 007-T013, 007-T027 |
| 007-T030 | Call `resolve_delivery` in the assignment email sender owned by 005 (module unde | 2.0 | backend-python | no | 007-T029 |
| 007-T031 | Call `resolve_delivery` in the daily digest sender owned by 006 (module under `a | 2.0 | backend-python | no | 007-T029 |
| 007-T032 | Call `resolve_delivery` in the mention sender owned by 004 (module under `app/se | 2.0 | backend-python | no | 007-T029 |

### S-SETUP-007 Notification preferences: Setup — P1/must · 1 SP (low, llm)

Depends on: - · Sources: E-007

- [AC-S-SETUP-007-1] Given the setup tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 007-T001 | Add the `FEATURE_NOTIFICATION_PREFS` flag (read from the environment, default of | 1.0 | backend-python | yes | - |
| 007-T002 | Create the web feature folder with an empty `src/features/notification-prefs/ind | 0.5 | frontend-react | yes | - |

### S-FOUND-007 Notification preferences: Foundational prerequisites — P1/must · 3 SP (low, llm)

Depends on: S-SETUP-007, S-FOUND-005 · Sources: E-007

- [AC-S-FOUND-007-1] Given the foundational prerequisites tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 007-T003 | Create the Alembic migration `migrations/versions/007_notification_prefs.py` cre | 4.0 | postgres, backend-python | no | - |
| 007-T004 | Create the SQLAlchemy models `NotificationChannel`, `NotificationFrequency` and  | 3.0 | data-modeling, backend-python | yes | - |
| 007-T005 | Create the request and response schemas matching `contracts/notification-prefere | 3.0 | api-design, backend-python | yes | - |
| 007-T006 | Define the notification type constants (`assignment`, `mention`, `digest`, with  | 1.5 | backend-python | yes | - |
| 007-T007 | Write unit tests for window ends (hourly ends at the next top of the hour; daily | 2.5 | qa-automation, backend-python | yes | - |
| 007-T008 | Implement `window_end(frequency, now, user_time_zone)` in `app/services/notifica | 3.0 | backend-python | yes | 007-T007 |
| 007-T009 | Write a migration and model test (seed rows exist, unique constraint, check cons | 3.0 | qa-automation, backend-python | no | 007-T003, 007-T004 |

### S-POLISH-007 Notification preferences: Polish & cross-cutting concerns — P3/could · 2 SP (low, llm)

Depends on: S-007-US1, S-007-US2, S-007-US3 · Sources: E-007

- [AC-S-POLISH-007-1] Given the polish & cross-cutting concerns tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 007-T033 | Add structured logs for each preference change and each non-default decision in  | 1.5 | backend-python, observability | yes | 007-T029 |
| 007-T034 | Add the health check `GET /api/v1/notification-preferences/health` to `app/api/n | 2.0 | backend-python, qa-automation | yes | 007-T014 |
| 007-T035 | Add a latency test for GET and PUT preferences against the p95 300 ms service le | 3.0 | qa-automation, backend-python | yes | 007-T014 |
| 007-T036 | Record a manual keyboard-only and WCAG 2.1 AA check of the settings page in `doc | 2.0 | docs, frontend-react | no | - |
| 007-T037 | Run the validation scenarios in `specs/007-notification-prefs/quickstart.md` and | 2.0 | docs, qa-automation | no | 007-T018, 007-T026, 007-T032 |

## E-008 Burndown report and CSV export

Per-board burndown chart of remaining story points per sprint day; CSV export of a board.

### S-008-US1 Manager sets a sprint on a board — P2/should · 5 SP (low, llm)

As a team manager, I want to set a sprint (name, start date, end date) on a board so that the burndown report has a time window to cover and I can see whether we will finish on time.
Depends on: S-FOUND-008, S-001-US6 · Sources: FR-8, US-8

- [AC-S-008-US1-1] Given a board and a manager who is a member of it, When the manager creates a sprint with a name, a start date and an end date on or after the start date, Then the sprint is saved and shown as the board's current sprint while today falls between the two dates
- [AC-S-008-US1-2] Given a board that already has a sprint overlapping the requested dates, When a manager creates another sprint with overlapping dates, Then the request is rejected with a clear message and nothing is saved
- [AC-S-008-US1-3] Given a sprint end date earlier than its start date, When the manager submits it, Then the request is rejected with a validation message
- [AC-S-008-US1-4] Given a board member who is not a manager, When they try to create or edit a sprint, Then the request is refused and no data changes
- [AC-S-008-US1-5] Given a user who is not a member of the board, When they request that board's sprints, Then the request is refused and nothing about the board is revealed

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 008-T007 | Unit tests for sprint validation, overlap detection and current-sprint selection | 3.5 | qa-automation, backend-python | yes | - |
| 008-T008 | Integration and contract tests for POST/PATCH/GET sprint endpoints (201, 403 mem | 4.5 | qa-automation, api-design | no | - |
| 008-T009 | Implement SprintService (create, update, list, current sprint by UTC date, overl | 6.0 | backend-python | no | 008-T003, 008-T006, 008-T007 |
| 008-T010 | Implement the sprint router with `/api/v1/boards/{board_id}/sprints` endpoints,  | 4.5 | backend-python, api-design | no | 008-T009 |
| 008-T011 | Register the sprint router in `app/main.py` | 0.5 | backend-python | yes | 008-T010 |
| 008-T012 | Add sprint API client functions (list, create, update) in `src/api/reports.ts` i | 2.5 | frontend-react, api-design | yes | - |
| 008-T013 | Build the keyboard-accessible SprintForm with labelled fields and inline validat | 5.0 | frontend-react | no | 008-T012 |
| 008-T014 | Component test for SprintForm validation and keyboard submit in `src/features/re | 3.5 | qa-automation, frontend-react | yes | - |

### S-008-US2 Manager reads the burndown report — P2/should · 8 SP (low, llm)

As a team manager, I want to open a burndown report for a board showing remaining story points per day of the current sprint so that I can tell whether the team will finish on time without a status meeting.
Depends on: S-FOUND-008 · Sources: FR-8, US-8

- [AC-S-008-US2-1] Given a board with a current sprint, When a board member opens the report, Then they see the remaining story points for each day of the sprint, from the start date to the end date, with future days left empty
- [AC-S-008-US2-2] Given a sprint with tasks totalling 20 story points and tasks worth 5 points moved to Done today, When the report is opened, Then today's remaining points are 15
- [AC-S-008-US2-3] Given a day in the sprint for which no daily record exists, When the report is shown, Then the last known value is carried forward for that day and the day is not shown as zero
- [AC-S-008-US2-4] Given a board without a current sprint, When a member opens the report, Then they see an empty state that says no sprint is set, instead of an error or an empty chart
- [AC-S-008-US2-5] Given a task without story points, When the report is computed, Then that task counts as 0 points
- [AC-S-008-US2-6] Given the report page, When a user navigates it with the keyboard only, Then they can reach the chart and read the same values as a table
- [AC-S-008-US2-7] Given a user who is not a member of the board, When they request that board's report, Then the request is refused
- [AC-S-008-US2-8] Given the flag `FEATURE_BURNDOWN` is off, When anyone requests the sprint or burndown endpoints, Then the feature is not available and the report entry point is not shown

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 008-T015 | Unit tests for remaining-points calculation (null points count 0, Done only), ca | 3.5 | qa-automation, backend-python | yes | - |
| 008-T016 | Integration and contract tests for `GET /api/v1/boards/{board_id}/reports/burndo | 4.5 | qa-automation, backend-python | no | - |
| 008-T017 | Integration test for the daily snapshot job (writes the record for the day, upse | 3.0 | qa-automation, backend-python | yes | - |
| 008-T018 | Create the BurndownResponse schema (days with day, remaining_points, total_point | 1.5 | backend-python, api-design | yes | - |
| 008-T019 | Implement BurndownService (live remaining points for today, upsert of today's re | 7.0 | backend-python | no | 008-T004, 008-T009, 008-T015, 008-T018 |
| 008-T020 | Implement the burndown router `GET /api/v1/boards/{board_id}/reports/burndown` w | 3.0 | backend-python, api-design | no | 008-T019 |
| 008-T021 | Register the reports router in `app/main.py` | 0.5 | backend-python | yes | 008-T011, 008-T020 |
| 008-T022 | Implement the daily snapshot job entry point that records the day's remaining po | 3.5 | backend-python | yes | 008-T017, 008-T019 |
| 008-T023 | Add the daily CronJob that runs the worker image with the snapshot job command i | 2.0 | kubernetes | no | 008-T022 |
| 008-T024 | Add the burndown API client function in `src/api/reports.ts` in taskflow-web | 1.5 | frontend-react, api-design | yes | 008-T012 |
| 008-T025 | Build BurndownChart as an SVG line chart with an accessible name and focusable d | 5.0 | frontend-react, frontend-css | no | - |
| 008-T026 | Build BurndownTable with the same per-day values as the chart in `src/features/r | 2.5 | frontend-react | yes | - |
| 008-T027 | Build BurndownPage with chart, table, empty state when no sprint is set, the Spr | 4.5 | frontend-react | no | 008-T013, 008-T024, 008-T025, 008-T026 |
| 008-T028 | Add the report route and a "Burndown" link in the board header, shown only when  | 2.5 | frontend-react, api-design | yes | 008-T027 |
| 008-T029 | Component tests for BurndownPage, chart/table parity, empty state and keyboard-o | 3.5 | qa-automation, frontend-react | yes | - |

### S-008-US3 Manager exports board data as CSV — P3/could · 3 SP (low, llm)

As a team manager, I want to export a board's tasks as a CSV file with one row per task and every task field so that I can analyse the data in a spreadsheet or other tool.
Depends on: S-FOUND-008 · Sources: FR-9, US-9

- [AC-S-008-US3-1] Given a board with N tasks, When a board member clicks Export, Then a CSV file is downloaded with a header row and exactly N task rows
- [AC-S-008-US3-2] Given the task model, When the file is produced, Then it has one column for every task field, including story points and the column the task is in
- [AC-S-008-US3-3] Given a task title or description containing commas, double quotes or line breaks, When it is exported, Then the cell is quoted so the file parses back to the original text
- [AC-S-008-US3-4] Given a task text field that begins with `=`, `+`, `-`, `@`, a tab or a carriage return, When it is exported, Then the cell is neutralised so a spreadsheet does not run it as a formula, and the visible text is still readable
- [AC-S-008-US3-5] Given two boards with tasks, When a member exports one board, Then the file contains no task from the other board
- [AC-S-008-US3-6] Given a board with no tasks, When a member exports it, Then the file contains the header row only
- [AC-S-008-US3-7] Given a user who is not a member of the board, When they request the export, Then the request is refused and no file is produced
- [AC-S-008-US3-8] Given the flag `FEATURE_CSV_EXPORT` is off, When anyone requests the export, Then the feature is not available and the Export button is not shown

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 008-T030 | Unit tests for CSV quoting, UTF-8 output and formula neutralising of `=`, `+`, ` | 2.5 | qa-automation, backend-python | yes | - |
| 008-T031 | Integration and contract tests for `GET /api/v1/boards/{board_id}/export/csv` (r | 3.5 | qa-automation, backend-python | no | - |
| 008-T032 | Implement CsvExportService that streams rows filtered by board_id, takes columns | 3.5 | backend-python | yes | 008-T030 |
| 008-T033 | Implement the export router with `FEATURE_CSV_EXPORT` guard, board-membership ch | 2.0 | backend-python, api-design | no | 008-T032 |
| 008-T034 | Register the export router in `app/main.py` | 0.5 | backend-python | yes | 008-T021, 008-T033 |
| 008-T035 | Add the CSV download client function in `src/api/reports.ts` in taskflow-web | 1.0 | frontend-react, api-design | yes | 008-T024 |
| 008-T036 | Build the keyboard-accessible ExportButton that downloads the file and shows an  | 2.0 | frontend-react | yes | 008-T035 |
| 008-T037 | Add the ExportButton to the board header, hidden when the feature answers 404, i | 1.0 | frontend-react | yes | 008-T028, 008-T036 |
| 008-T038 | Component test for ExportButton (download, error, keyboard activation) in `src/f | 2.0 | qa-automation, frontend-react | yes | - |

### S-SETUP-008 Burndown report and CSV export: Setup — P2/should · 1 SP (low, llm)

Depends on: - · Sources: E-008

- [AC-S-SETUP-008-1] Given the setup tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 008-T001 | Add settings `FEATURE_BURNDOWN` and `FEATURE_CSV_EXPORT` (read from env `FEATURE | 1.0 | backend-python | yes | - |
| 008-T002 | Create test packages `tests/unit/reports/__init__.py`, `tests/integration/report | 0.5 | qa-automation, backend-python | yes | - |

### S-FOUND-008 Burndown report and CSV export: Foundational prerequisites — P2/should · 2 SP (low, llm)

Depends on: S-SETUP-008, S-FOUND-002 · Sources: E-008

- [AC-S-FOUND-008-1] Given the foundational prerequisites tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 008-T003 | Create the Sprint model in `app/models/sprint.py` with fields name (text, "1 to  | 3.0 | backend-python, data-modeling | yes | - |
| 008-T004 | Create the SprintBurndownRecord model in `app/models/sprint_burndown_record.py`  | 2.0 | backend-python, data-modeling | yes | - |
| 008-T005 | Create the Alembic migration for `sprints` and `sprint_burndown_records` (and th | 4.5 | postgres, backend-python | no | 008-T003, 008-T004 |
| 008-T006 | Create pydantic schemas SprintCreate, SprintUpdate and SprintRead in `app/schema | 2.5 | backend-python, api-design | yes | - |

### S-POLISH-008 Burndown report and CSV export: Polish & cross-cutting concerns — P3/could · 2 SP (low, llm)

Depends on: S-008-US1, S-008-US2, S-008-US3 · Sources: E-008

- [AC-S-POLISH-008-1] Given the polish & cross-cutting concerns tasks, When they are done, Then all of them meet the Definition of Done

| Task | Title | Hours | Skills | AI | Depends on |
|---|---|---|---|---|---|
| 008-T039 | Add structured logs (board id, user id, result, duration; no task content) and r | 5.0 | backend-python, observability | no | 008-T010, 008-T020, 008-T022, 008-T033 |
| 008-T040 | Write the security review notes (membership and manager checks, cross-board isol | 2.0 | auth-security, docs | no | - |
| 008-T041 | Document the endpoints, flags, daily job and the assumptions Q1, Q2, Q3 in `docs | 2.5 | docs, api-design | yes | - |
| 008-T042 | Run the scenarios in `specs/008-reports-export/quickstart.md` and record the res | 2.5 | qa-automation, docs | no | 008-T028, 008-T037, 008-T039 |

## Open questions

- S-001-US1: Is a total of at most USD 2,500 per month across dev, stg and prod achievable with HA prod? Task 001-T012 must confirm before the Terraform modules are built.
- S-001-US3: The synchronisation interval for External Secrets and whether workloads restart automatically on rotation are not fixed; confirm with devops.
- S-001-US5: Assumed values need product/security confirmation: password minimum length 12, lockout after 5 failures in 15 minutes.
- S-001-US7: Alert delivery tool for the on-call channel is still to be confirmed by devops (task 001-T072).
- 001-T072: Which tool delivers alerts to the on-call channel? To be confirmed by devops.
- S-002-US7: MoSCoW raised from should to must: FR-5 / US-5 (Must) depends on this event hook; priority stays P2 because FR-5 is not in DL-1 (beta, 2026-12-18 covers FR-1 and FR-2). Confirm with the product owner.
- S-003-US4: Spec marks this story P2/should, but it contains the only search UI in the web app and US-4 is Must in prd.md; raised to must. Confirm with product owner whether the keyboard/a11y part (NFR-4) alone may slip to a later release.
- S-003-US4: Search UI tasks name src/ paths while the epic repo is acme/taskflow-api; frontend code belongs in acme/taskflow-web. Confirm the repo.
- S-004-US2: Name and module of the outbox enqueue function owned by feature 005-assignment-email is not confirmed (task 004-T019).
- S-004-US2: Path of the mention email template (app/worker/templates/mention_email.py) is assumed and must be aligned with feature 005.
- S-004-US2: AC 6 (opt-out of mention notifications) depends on feature 007 (US-7); confirm whether it is in scope for the same release.
- S-005-US1: Q1 (assumed yes in spec): confirm that a manager who assigns a task to themselves also gets an assignment email
- S-006-US1: Q3 (spec): no email when there are no tasks due tomorrow is an assumption and needs product confirmation.
- S-006-US2: Q2 (spec): pre-selecting the browser-detected zone is an assumption and needs product confirmation.
- S-006-US2: The settings screen is owned by feature 001 (T023); confirm that SettingsPage.tsx exists before this story starts.
- S-007-US1: Q1 (client undecided): which channels besides email FR-7 should offer; assumed email only, channel list kept as configurable data.
- S-007-US2: Q1 (client undecided): which frequencies FR-7 should offer; assumed configurable data seeded with immediate, hourly, daily.
- S-007-US2: Q2: may a user delay or switch off the assignment email given US-5 promises an email within 1 minute? Assumed yes only by explicit choice; default stays immediate.
- S-007-US3: Q1 (client undecided): channels and frequencies; decision contract takes the channel as input so new channels need no sender change.
- S-007-US3: Exact sender modules owned by features 004, 005 and 006 must be taken from their tasks (T030-T032 have no file paths).
- 007-T030: Exact sender module is defined in feature 005's tasks; file path unknown.
- 007-T031: Exact digest sender module is defined in feature 006's tasks; file path unknown.
- 007-T032: Exact sender module is defined in feature 004's tasks; file path unknown.
- S-008-US1: PRD does not say how sprints are created or managed; this story assumes a minimal sprint (name, start, end). Confirm scope with the product owner.
- S-008-US2: PRD open question Q1: is Done the only column that counts toward the burndown? Currently assumed yes (see clarifications.md).
- S-008-US2: Who runs the daily snapshot and at what UTC time is not decided in the PRD; assumed a daily Kubernetes CronJob.
- S-FOUND-008: Is the btree_gist extension allowed in the target Postgres? If not, the overlap backstop constraint is dropped and the service-level check is the only guard.
