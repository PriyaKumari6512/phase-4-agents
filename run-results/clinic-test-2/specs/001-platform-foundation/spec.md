# Feature Specification: Platform foundation, access control and availability

**Feature Branch**: `001-platform-foundation` (no git branch is used; directory `specs/001-platform-foundation`)

**Created**: 2026-01-01

**Status**: Draft

**Input**: User description: "Platform foundation, access control and availability. Covers NFR-2 (availability 99.5% monthly for web app and API) and NFR-3 (only board members can see a board's tasks; task data is confidential). Owns CI/CD, EKS dev/stg/prod environments, External Secrets, Postgres/Redis provisioning, observability and availability monitoring, deployment of api/web/worker, users/boards/board-membership schema, authentication, board-member authorisation and migration setup."

## User Scenarios & Testing *(mandatory)*

The "users" of the platform stories (US1-US3, US7) are the TaskFlow engineers and operators (backend, frontend, fullstack, devops); the users of US4-US6 are TaskFlow team members and managers whose task data must stay confidential. Every story is sized to at most 13 story points; larger concerns were split (environments vs. CI/CD, schema vs. authentication vs. authorisation).

### User Story 1 - Three environments with managed data stores (Priority: P1)

As a TaskFlow engineer, I want separate dev, stg and prod environments, each with its own database and cache, so that features can be built, verified and released safely and the whole platform stays inside the monthly infrastructure budget.

**Why this priority**: Every other feature in the backlog needs a place to run and a database and cache to use; nothing can be released without it.

**Independent Test**: Can be fully tested by bringing up each environment, checking that the API, web app and worker workloads start, that the database and cache accept connections from the workloads only, and that the cost report for all three environments is under the budget.

**Acceptance Scenarios**:

1. **Given** the infrastructure definitions for dev, stg and prod, **When** an environment is created, **Then** it is isolated from the other two (own cluster namespace or cluster, own database, own cache) and runs in the AWS us-east-1 region. (source: NFR-2)
2. **Given** an environment, **When** the API, web and worker workloads are scheduled, **Then** the database and cache are reachable from those workloads and are not reachable from the public internet. (source: NFR-3)
3. **Given** all three environments are running, **When** the monthly cost is reviewed, **Then** the forecast total is at most USD 2,500 across all environments. (source: NFR-2)
4. **Given** the production environment, **When** one workload instance fails, **Then** at least one other instance of the API and web app keeps serving traffic. (source: NFR-2)

---

### User Story 2 - CI/CD for api, web and worker (Priority: P1)

As a TaskFlow engineer, I want every change to be built, tested and deployed automatically through the environments so that releases are repeatable and a broken change never reaches production unnoticed.

**Why this priority**: Without a pipeline no feature can reach pilot customers by the mid-December 2026 beta, and uncontrolled releases threaten the availability target.

**Independent Test**: Can be fully tested by merging a trivial change in each repository and watching it build, pass tests, deploy to dev, promote to stg, and (after approval) to prod, then rolling back to the previous version.

**Acceptance Scenarios**:

1. **Given** a pull request in the api or web repository, **When** it is opened or updated, **Then** unit and integration tests run and the pull request cannot be merged while they fail.
2. **Given** a change merged to the main branch, **When** the pipeline runs, **Then** one image is built for the api and the worker (same repository and image, different start command) and a build of the web app is produced, and both are deployed to dev automatically.
3. **Given** a version running in stg that passed its checks, **When** an engineer approves promotion, **Then** the same build artifact is deployed to prod without being rebuilt. (source: NFR-2)
4. **Given** a deployment to prod whose health check fails, **When** the rollout does not become healthy, **Then** the previous version keeps serving traffic and the failed deployment is reported. (source: NFR-2)
5. **Given** the pipeline definitions, **When** they are reviewed, **Then** they contain no secret values. (source: NFR-3)

---

### User Story 3 - Secrets delivered without being stored in Git (Priority: P1)

As a TaskFlow engineer, I want the database URL, Redis URL and email provider key to be stored in AWS Secrets Manager and delivered to the workloads automatically so that no secret ever appears in Git and confidential task data stays protected.

**Why this priority**: Workloads cannot start without their connection settings, and the constitution forbids secrets in code or configuration files.

**Independent Test**: Can be fully tested by creating a secret in an environment's Secrets Manager, observing it appear as an environment variable in the workload, rotating it, and scanning all repositories for secret values.

**Acceptance Scenarios**:

1. **Given** the three secrets (database URL, Redis URL, email provider key) in an environment's Secrets Manager, **When** a workload starts, **Then** each secret is available to it as an environment variable. (source: NFR-3)
2. **Given** a secret value changes in Secrets Manager, **When** the synchronisation interval passes and workloads are restarted, **Then** they use the new value without any change in Git. (source: NFR-3)
3. **Given** any of the repositories, **When** a secret scan runs in CI, **Then** it finds no secret values and fails the build if it finds one. (source: NFR-3)
4. **Given** the dev, stg and prod environments, **When** their secrets are compared, **Then** each environment only has access to its own secrets. (source: NFR-3)

---

### User Story 4 - Users, boards and board membership data foundation (Priority: P1)

As a TaskFlow developer, I want the users, boards and board membership data structures and a versioned migration process in place so that every later feature stores its data on the same, reviewed foundation.

**Why this priority**: Membership is what the confidentiality rule (NFR-3) is based on, and all feature teams add their own migrations on top of this base.

**Independent Test**: Can be fully tested by applying all migrations to an empty database, creating users, a board and memberships, and verifying uniqueness and referential rules, then rolling the migration back and forward again.

**Acceptance Scenarios**:

1. **Given** an empty database, **When** migrations are applied, **Then** users, boards and board memberships exist and the migration history records the version. (source: NFR-3)
2. **Given** a user who is already a member of a board, **When** the same membership is created again, **Then** it is rejected and no duplicate exists. (source: NFR-3)
3. **Given** a board with members, **When** a user is added as a member, **Then** the membership is stored with the user, the board and the member's role (owner or member). (source: NFR-3)
4. **Given** a new feature needs a table, **When** a developer adds a migration, **Then** the migration runs in CI against a clean database and after the previous release's schema. (source: NFR-2)

---

### User Story 5 - Authentication (Priority: P1)

As a team member, I want to sign in so that the platform knows who I am and every request I make is tied to my identity.

**Why this priority**: Authorisation (US6) is impossible without a known caller identity.

**Independent Test**: Can be fully tested by signing in with valid and invalid credentials and calling an authenticated endpoint with a valid, an expired and a missing credential.

**Acceptance Scenarios**:

1. **Given** a registered user, **When** they sign in with correct credentials, **Then** they receive a credential (bearer token) that identifies them on later requests. (source: NFR-3)
2. **Given** a user with wrong credentials, **When** they try to sign in, **Then** access is refused with a generic message that does not reveal whether the account exists. (source: NFR-3)
3. **Given** a request to a protected endpoint with no, malformed or expired credential, **When** it is processed, **Then** it is refused as unauthenticated and no data is returned. (source: NFR-3)
4. **Given** repeated failed sign-in attempts for one account, **When** the limit is exceeded, **Then** further attempts are temporarily refused. (source: NFR-3)
5. **Given** a signed-in user, **When** they ask who they are, **Then** the system returns their own profile only. (source: NFR-3)

---

### User Story 6 - Board-member authorisation on every board-scoped endpoint (Priority: P1)

As a team member, I want only the members of a board to be able to see or change anything on it so that my team's task data stays confidential.

**Why this priority**: This is the core of the security and privacy requirement (NFR-3); all later task, search, comment, report and export endpoints must reuse it.

**Independent Test**: Can be fully tested with two boards and two users, each a member of only one: every board-scoped endpoint must answer the non-member with a refusal and reveal nothing, while the member is served.

**Acceptance Scenarios**:

1. **Given** a board and a user who is not a member, **When** the user requests the board or anything under it, **Then** the system refuses and returns no board or task data; the response is indistinguishable from a board that does not exist. (source: NFR-3)
2. **Given** a board member, **When** they request the board, **Then** they are served. (source: NFR-3)
3. **Given** a user removed from a board, **When** they make the next request, **Then** they no longer have access, including to cached data. (source: NFR-3)
4. **Given** a new board-scoped endpoint added by any feature, **When** it is built, **Then** it uses the shared membership check, and an automated test fails if a registered board-scoped route does not enforce it. (source: NFR-3)
5. **Given** a list or search spanning several boards, **When** a user requests it, **Then** only data from boards where they are a member is included. (source: NFR-3)
6. **Given** any refused access, **When** it happens, **Then** an audit-style log entry records the user, the board and the time, without task content. (source: NFR-3)

---

### User Story 7 - Availability monitoring and service-level alerting (Priority: P2)

As a TaskFlow operator, I want to see and be alerted on availability, latency and error rate of the web app and API so that we can keep the 99.5% monthly availability promise and react before customers notice.

**Why this priority**: Required to prove NFR-2, but it needs running environments (US1, US2) first.

**Independent Test**: Can be fully tested by stopping the API in dev, checking that the availability probe fails and an alert reaches the on-call channel, and that the monthly availability and error-budget figures update.

**Acceptance Scenarios**:

1. **Given** the web app and the API are running, **When** an external probe checks them every minute, **Then** availability per month is calculated for each. (source: NFR-2)
2. **Given** the API error rate exceeds 1% over a measurement window, **When** the alert rule evaluates, **Then** an alert is sent to the on-call channel. (source: NFR-2)
3. **Given** the API p95 latency exceeds 300 ms over a measurement window, **When** the alert rule evaluates, **Then** an alert is sent. (source: NFR-2)
4. **Given** the remaining error budget for the month (0.5% of the month) is being consumed too fast, **When** the burn-rate rule evaluates, **Then** a warning is sent before the budget is exhausted. (source: NFR-2)
5. **Given** any service, **When** it runs, **Then** it emits structured logs, metrics and traces and exposes a health check endpoint. (source: NFR-2)
6. **Given** an engineer opens the operations dashboard, **When** they choose an environment, **Then** they see availability, p95 latency, error rate and worker health for it. (source: NFR-2)

---

### Edge Cases

- A user is removed from a board while their sign-in credential is still valid or while they have the board open.
- A user belongs to no board: board lists are empty, not an error.
- The last owner of a board tries to leave or is removed (assumed: refused).
- The database or cache is unavailable: the API reports itself unhealthy and returns a clear error; board reads must not fall back to unauthorised cached data.
- A deployment includes a migration that fails halfway.
- Secrets Manager is unreachable when a pod starts.
- A maintenance window or an upstream AWS outage counts against availability (assumed, see Assumptions).
- Probe or alerting service is itself down (a missing-data alert must fire).
- Board identifiers guessed by a user who is not a member (enumeration attempts).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The platform MUST provide three isolated environments (dev, stg, prod) in AWS us-east-1 on Kubernetes (EKS), each with its own PostgreSQL 16 database and Redis 7 cache. (source: NFR-2)
- **FR-002**: The total forecast monthly infrastructure cost of all environments MUST stay within USD 2,500, and the environments MUST be sized for 200 teams and a peak of 50 requests per second in prod. (source: NFR-2)
- **FR-003**: Production MUST run more than one instance of the API and of the web app so that a single instance failure does not interrupt service. (source: NFR-2)
- **FR-004**: The web app MUST be the only publicly reachable entry point; the API, database, cache and worker MUST NOT be directly reachable from the public internet other than through the web app's public route. (source: NFR-3)
- **FR-005**: Every pull request MUST run automated tests and block merging on failure; a merge to the main branch MUST build and deploy to dev automatically. (source: NFR-2)
- **FR-006**: Promotion to stg and prod MUST deploy the already-built artifact, prod promotion MUST need explicit approval, and a failed rollout MUST leave the previous version serving. (source: NFR-2)
- **FR-007**: The API and the notification worker MUST be built from the same repository and image and deployed as separate workloads with different start commands; the web app is built and deployed from its own repository. (source: NFR-2)
- **FR-008**: The database URL, Redis URL and email provider key MUST be stored in AWS Secrets Manager and delivered to workloads through External Secrets; no secret value may be stored in Git, and CI MUST scan for secrets. (source: NFR-3)
- **FR-009**: Each environment MUST have access only to its own secrets. (source: NFR-3)
- **FR-010**: The system MUST store users, boards and board memberships (user, board, role) with a unique membership per user and board. (source: NFR-3)
- **FR-011**: Database schema changes MUST be made only through versioned migrations that run in CI and as a step of deployment; a merged migration MUST NOT be edited. (source: NFR-2)
- **FR-012**: The system MUST authenticate users and identify the caller on every protected request; unauthenticated requests MUST be refused. (source: NFR-3)
- **FR-013**: Passwords, if used for sign-in, MUST be stored only as salted one-way hashes, and repeated failed sign-ins MUST be rate limited. (source: NFR-3)
- **FR-014**: Every board-scoped endpoint MUST allow access only to members of that board, using one shared membership check, and MUST return a response that does not reveal whether a board exists to non-members. (source: NFR-3)
- **FR-015**: An automated test MUST fail the build when a registered board-scoped route does not enforce the membership check. (source: NFR-3)
- **FR-016**: Cached board data MUST NOT be served to a user who is not a member of the board, and removal of a member MUST take effect on their next request. (source: NFR-3)
- **FR-017**: Refused access to a board MUST be logged with user, board and time but without task content, and task content MUST NOT be written to logs. (source: NFR-3)
- **FR-018**: All services MUST emit structured logs, metrics and traces (OpenTelemetry) and expose a health check endpoint. (source: NFR-2)
- **FR-019**: The system MUST probe the web app and the API externally at least once per minute and compute monthly availability per service against the 99.5% target. (source: NFR-2)
- **FR-020**: Alerts MUST fire to an on-call channel when the API error rate exceeds 1%, API p95 latency exceeds 300 ms, a probe fails, or the monthly error budget burn rate is too high; an alert MUST also fire when monitoring data is missing. (source: NFR-2)
- **FR-021**: An operations dashboard per environment MUST show availability, p95 latency, error rate and worker health. (source: NFR-2)
- **FR-022**: Foundation capabilities (membership check, authentication dependency, migration setup, feature flag configuration read from `FEATURE_<NAME>` environment variables) MUST be provided as shared modules so later features reuse rather than recreate them. (source: NFR-3)

### Key Entities *(include if feature involves data)*

- **User**: a person who signs in; identity, display name (used for mentions later), email, credential hash, time zone (reserved for later features).
- **Board**: a shared workspace owned by a team; name, creation time, creator. Task data of later features hangs off a board.
- **Board Membership**: link between a user and a board with a role (owner or member); unique per user and board; the basis of every access decision.
- **Environment**: one of dev, stg, prod with its own cluster resources, data stores and secrets.
- **Secret**: a named confidential setting (database URL, Redis URL, email provider key) held in AWS Secrets Manager.
- **Service level objective**: availability 99.5% monthly, API p95 latency 300 ms, error rate 1%.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Web app and API are each available at least 99.5% of every calendar month, measured by an external probe. (source: NFR-2)
- **SC-002**: At least 95% of requests to the API are answered within 300 ms and fewer than 1% of requests fail, measured over each monitoring window at up to 50 requests per second. (source: NFR-2)
- **SC-003**: A change merged to the main branch is running in dev within 30 minutes, and a prod rollback to the previous version completes within 15 minutes. (Assumed targets, see Assumptions.)
- **SC-004**: In an automated test with two boards, 100% of board-scoped endpoints refuse a non-member and serve a member; zero task data is returned to non-members. (source: NFR-3)
- **SC-005**: A scan of all repositories and pipeline definitions finds zero secret values. (source: NFR-3)
- **SC-006**: A simulated outage of the API is detected and alerted to the on-call channel within 5 minutes. (Assumed target, see Assumptions.)
- **SC-007**: The forecast monthly infrastructure cost of all three environments is at most USD 2,500. (source: NFR-2)

## Assumptions

- **Auth mechanism (assumption, open question Q1)**: architecture.md and prd.md do not state how users authenticate. Assumed: email and password sign-in that issues a bearer token (session) accepted on every `/api/v1` request. The choice of single sign-on or an external identity provider is open.
- **Membership management (assumption, open question Q2)**: no PRD story describes inviting or removing members. Assumed: a board owner can add existing users to a board and remove members through the API; a board creator becomes its owner; no email invitation flow and no self-service sign-up UI beyond what authentication requires.
- **Availability accounting (assumption, open question Q3)**: the PRD says 99.5% monthly without exclusions. Assumed: all downtime counts, including planned maintenance, measured per calendar month by an external probe on the production environment. 99.5% of a 30-day month allows about 3.6 hours of downtime.
- **Token signing key (assumption)**: the bearer-token scheme needs a signing key. Assumed: it is stored as a fourth secret (`token-signing-key`) in AWS Secrets Manager with the three named in architecture.md, and never in Git.
- Non-members receive a "not found" style response for board resources so board existence is not leaked.
- Roles are limited to owner and member; there is no global administrator role in this release.
- The API prefix is `/api/v1`, the API lives in `app/` in acme/taskflow-api, migrations in `migrations/` (Alembic), infra code in acme/taskflow-infra under `terraform/` and `k8s/` (all from the implementation contract, assumed).
- Dev and stg may be smaller than prod and may run a single instance; only prod has redundancy and availability monitoring with paging. Dev and stg are probed but alert in a non-paging channel.
- The on-call channel and alert delivery tool are not named in the architecture; the choice is made in the plan within the stack named by the architecture and constitution (OpenTelemetry), and is subject to Dave's (devops) confirmation.
- Time to beta: pilot customers need a beta by mid-December 2026. Dave (devops) is available 50% of the time, so devops stories are the likely bottleneck.
- Task CRUD, board columns, search, comments, notifications and reports are out of scope; they belong to features F02-F08 and reuse the foundations defined here.
