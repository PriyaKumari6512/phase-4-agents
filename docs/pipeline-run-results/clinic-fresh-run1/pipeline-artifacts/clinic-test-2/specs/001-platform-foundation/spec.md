# Feature Specification: Platform foundation, delivery and non-functional baseline

**Feature Branch**: `001-platform-foundation`

**Created**: 2026-11-16

**Status**: Draft

**Input**: User description: "Technical foundation that every other BrightSmile Booking feature builds on: repositories and CI/CD, dev/staging/prod environments, database baseline with migrations and backups, a mobile-first web app shell with English-only IST formatting, observability with SLO probes and alerts, load and scale verification, and a go-live readiness checklist for Release 1 on 1 March 2027. Covers NFR-001, NFR-003, NFR-004, NFR-008, NFR-009, NFR-010."

**Covers prd.md ids**: NFR-001, NFR-003, NFR-004, NFR-008, NFR-009, NFR-010

**Components**: ctr-web, ctr-clinic-api, ctr-db. **Repositories**: brightsmile/clinic-api, brightsmile/clinic-web, brightsmile/clinic-infra.

## User Scenarios & Testing *(mandatory)*

<!--
  This feature is the first epic. Its "users" are the patient on a phone, the receptionist and practice manager
  on a desktop browser, and the delivery team that builds and runs the service. Each story below is independently
  testable and delivers a usable slice of the foundation.
-->

### User Story 1 - Every change is built, tested and shipped safely (Priority: P1)

As the delivery team, we want each commit to the API and web repositories to be built, tested, scanned and deployed through one repeatable pipeline, so that Release 1 can be shipped on 1 March 2027 without manual, error-prone steps and a bad release can be undone quickly.

**Why this priority**: Every other feature depends on a working pipeline, and the go-live date is firm (NFR-009). Without it nothing can reach staging or production.

**Independent Test**: Push a trivial commit to the API repository and to the web repository. Confirm each pipeline runs every stage in order, a deliberately failing test or a seeded HIGH vulnerability stops the pipeline before deployment, and a deliberately failing health check triggers a rollback to the previous release.

**Acceptance Scenarios**:

1. **Given** a commit to the API repository, **When** the pipeline runs, **Then** it builds, runs unit tests, runs contract tests against the published API contract, scans the image, deploys to staging, runs the smoke test (health, sign-in with a test code, book and cancel against sandbox providers) and only then replaces production one replica at a time behind the health check.
2. **Given** a failing unit test, a contract test that no longer matches the API contract, or a HIGH image-scan finding, **When** the pipeline runs, **Then** the pipeline stops and nothing is deployed to staging or production.
3. **Given** a commit to the web repository, **When** the pipeline runs, **Then** the web app is built and published separately from the API and the previous published build is kept.
4. **Given** a new release in production, **When** the health check fails, or server errors exceed 2% for 5 minutes, or reminder lag exceeds 15 minutes, **Then** the team can roll back by redeploying the previous API image and the previous web build, and the rollback steps are documented and rehearsed once in staging.
5. **Given** a database change in a release, **When** the pipeline deploys it, **Then** the change only adds or relaxes structures (expand) and stays compatible with the previous release; removals happen in a later release (contract).

(source: NFR-009, NFR-004)

---

### User Story 2 - Dev, staging and production environments with managed secrets (Priority: P1)

As the delivery team, we want separate dev, staging and production environments, each with the API, the web app and the database, and with secrets kept in a secret store, so that we can test safely and production stays available and protected.

**Why this priority**: Staging is where the smoke tests and UAT run; production must be ready well before 1 March 2027.

**Independent Test**: Create each environment from the infrastructure repository, deploy a build of the API and of the web app to it, call the health check through the public route, and confirm that no secret value appears in any repository, image or log.

**Acceptance Scenarios**:

1. **Given** the infrastructure repository, **When** an environment is created, **Then** dev, staging and production each host the web app (static, behind a CDN), the API and the database, with dev and staging on the smallest tiers and staging using sandbox accounts for the SMS and WhatsApp providers.
2. **Given** production, **When** a visitor opens the site, **Then** the web app is served from the CDN, requests under `/api` are routed through the load balancer and web application firewall to the API, and all traffic uses HTTPS.
3. **Given** production, **When** one API replica or one zone is lost, **Then** the other replica keeps serving online booking, and under sustained CPU above 60% the API scales between 2 and 4 replicas.
4. **Given** the secret store holds the database credentials, provider keys, webhook secrets and token signing key, **When** the API starts in any environment, **Then** it receives them as environment variables and no secret is present in code, images or configuration files.
5. **Given** the clinic has not yet confirmed a hosting provider or domain, **When** environments are created, **Then** they use an India cloud region chosen by the delivery team and a placeholder domain until the clinic supplies theirs (Assumed: see open question Q1).

(source: NFR-004, NFR-003, NFR-009)

---

### User Story 3 - Database baseline, migrations, backups and a tested restore (Priority: P1)

As the delivery team, we want a managed database with a first migration, a repeatable migration process, encrypted backups and a rehearsed restore, so that appointment data is never lost beyond 15 minutes and service can be restored within 1 hour.

**Why this priority**: Every feature stores data in the database, and a tested restore is a go-live condition.

**Independent Test**: Run the migrations on an empty database in dev, confirm the baseline schema and the no-overlap capability are present; then restore a production-like database from a snapshot plus archived logs to a chosen point in time and measure the time taken.

**Acceptance Scenarios**:

1. **Given** an empty database in any environment, **When** the migrations are applied, **Then** the baseline schema is created, including the extension needed to prevent overlapping appointments for one dentist, and the migration can be applied again without error.
2. **Given** the application's database user, **When** it connects, **Then** it can read and write data but cannot change the database structure; structure changes run under a separate migration user.
3. **Given** production, **When** one day passes, **Then** a snapshot is taken and kept 14 days, backups and archived logs are encrypted, and logs are archived continuously so any point in time can be restored.
4. **Given** a backup, **When** the delivery team restores it to a new database before go-live, **Then** the restored data is at most 15 minutes older than the chosen point (RPO) and the restore completes within 1 hour (RTO); the date, duration and result are recorded in the readiness checklist.
5. **Given** production, **When** the primary database node fails, **Then** the synchronous standby in the second zone takes over without losing committed data.

(source: NFR-004, NFR-003)

---

### User Story 4 - A patient uses every screen comfortably on a phone (Priority: P1)

As a patient on a phone, I want a plain, mobile-friendly website that needs no install and has big tap targets and no sideways scrolling, so that I can book at any age in Chrome or Safari on my Android phone or iPhone.

**Why this priority**: Online booking is the product's main value; the shell sets the layout and rules every patient screen reuses (NFR-001, NFR-010).

**Independent Test**: Open the shell's sample patient screens in current Chrome and Safari on an Android phone and an iPhone (real devices or the team's device lab); check for horizontal scrolling, measure tap targets, and count the screens in the booking journey after sign-in.

**Acceptance Scenarios**:

1. **Given** the web app shell, **When** I open any patient screen on a phone-width display in current Chrome or Safari on Android or iPhone, **Then** the page fits the width with no sideways scrolling and nothing needs to be installed.
2. **Given** any tappable control on a patient screen (buttons, links, form fields, list rows), **When** its size is measured, **Then** it is at least 44 px by 44 px.
3. **Given** the booking journey defined in the shell (who and what, slot picker, confirm, booked), **When** screens are counted after sign-in, **Then** a new patient reaches a booked appointment in 5 screens or fewer.
4. **Given** an automated responsive check, **When** the pipeline runs, **Then** it fails any patient screen that scrolls sideways or has a tap target smaller than 44 px.
5. **Given** a patient with slow 4G, **When** the shell loads, **Then** the sign-in screen is usable without waiting for unrelated screens (the app loads only what the screen needs).

(source: NFR-001, NFR-010)

---

### User Story 5 - All screens and messages are in English with times in India time (Priority: P2)

As a patient or receptionist, I want every screen and message in plain English and every time shown in India time (IST), so that I never have to convert times or guess what a message means.

**Why this priority**: Every later feature shows dates and times; the rule has to exist before screens multiply.

**Independent Test**: Store a known moment in time in the database, display it on a patient screen and a reception screen, and compare it to the expected IST clock time, including a moment near midnight and a moment in UTC that falls on a different calendar day in India.

**Acceptance Scenarios**:

1. **Given** a time stored in universal time (UTC), **When** it is shown on any screen or in any message, **Then** it appears as India time (IST, UTC+05:30) with the correct date, including when the UTC date and the IST date differ.
2. **Given** any screen text or message wording, **When** it is reviewed, **Then** it comes from one English message catalogue and no text is typed directly into a screen or message.
3. **Given** a person enters a date or time in a form, **When** it is saved, **Then** it is interpreted as IST and stored as UTC.
4. **Given** the automated checks, **When** a string is missing from the catalogue or a screen shows a time without a timezone conversion, **Then** the check fails.

(source: NFR-008)

---

### User Story 6 - Reception and the practice manager get a desktop layout that is available in clinic hours (Priority: P2)

As a receptionist or the practice manager on a desktop browser, I want a wide-screen layout with navigation for my role, available during clinic hours, so that I can run the day from the reception PC.

**Why this priority**: Reception screens must be available 08:00 to 20:00 Monday to Saturday; later features add the screens, this story provides the layout and the availability proof.

**Independent Test**: Open the staff area on a desktop browser at common desktop widths and confirm it uses the space; run the availability probe for the reception screens over a clinic day.

**Acceptance Scenarios**:

1. **Given** a desktop browser, **When** I open the staff area, **Then** I see a wide-screen layout with a navigation area for my role (receptionist, dentist, practice manager) that later features fill with their screens.
2. **Given** a phone, **When** a dentist opens "my day", **Then** the staff layout also fits without sideways scrolling (the dentist may use a phone).
3. **Given** a clinic day (08:00 to 20:00 IST, Monday to Saturday), **When** the reception screens are probed, **Then** availability over the month is reported against the 99.5% target.
4. **Given** a planned release during clinic hours, **When** it is deployed, **Then** the rolling replacement keeps reception screens available (no full outage).

(source: NFR-001, NFR-004)

---

### User Story 7 - The team sees problems before patients do (Priority: P2)

As the delivery team, we want structured logs without personal data, a health check, minute-by-minute availability probes, response-time measurement and alerts, so that we find and fix problems before the clinics notice and can prove the targets are met.

**Why this priority**: The availability and speed targets are only real if they are measured; it also feeds the rollback triggers.

**Independent Test**: Make a request and follow its correlation id through the logs; search all logs for a test patient's name, phone number and birth year and find none; stop the API in staging and confirm an alert arrives within the alert window.

**Acceptance Scenarios**:

1. **Given** the API is running, **When** `GET /health` is called, **Then** it reports whether the API and its database connection are working, and the interactive API documentation is reachable at `/docs`.
2. **Given** any request, **When** it is logged, **Then** the log carries ids and a correlation id and never contains a name, phone number or birth year; an automated test seeds personal data and fails if it appears in logs.
3. **Given** the production site, **When** a probe runs every minute reading the health check and the free-slot list, **Then** the result is recorded and monthly availability is calculated against 99.5%.
4. **Given** the free-slot list and booking confirmation, **When** requests are measured, **Then** 95% of free-slot requests finish within 2 s and 95% of booking confirmations within 3 s as seen by a phone on 4G, with server-side p95 at most 500 ms and 800 ms respectively.
5. **Given** a deploy, **When** health fails, 5xx exceeds 2% for 5 minutes, or reminder lag exceeds 15 minutes, **Then** the rollback alert fires; an alert also fires when reminder lag exceeds 10 minutes (Assumed: alerts go to the delivery team's shared channel, see open question Q3).
6. **Given** the monthly SLO report, **When** it is produced, **Then** it shows booking availability, reception-hours availability, slot and booking speed, reminders sent within 15 minutes (99%) and reminders sent for cancelled appointments (0).

(source: NFR-004, NFR-003)

---

### User Story 8 - Release 2 screens stay hidden until they are ready (Priority: P2)

As the practice manager, I want the Release 2 features (family members, no-show block, no-show report, reminders-failed list and SMS fallback) to be invisible to patients and staff until they are switched on, so that Release 1 goes live on 1 March 2027 without half-finished screens.

**Why this priority**: Release 2 is about 2 to 3 weeks after go-live (due 2027-03-19); the switch must exist before any R2 work merges.

**Independent Test**: Deploy a build with a sample R2 screen behind the switch. With the switch off it is not reachable or visible; with it on in staging it appears; switching it on in production needs no new deploy.

**Acceptance Scenarios**:

1. **Given** a Release 2 screen or action, **When** its switch is off, **Then** no menu entry, route or API action for it is visible or usable to patients or staff.
2. **Given** the switch for a feature is turned on in staging, **When** a user opens the app, **Then** the feature appears without a new deploy, and turning it off hides it again.
3. **Given** production at go-live, **When** the switch settings are reviewed, **Then** all Release 2 switches are off and the setting is recorded in the readiness checklist.
4. **Given** the switch is changed, **When** it is read, **Then** who changed it and when is recorded.

(source: NFR-009)

---

### User Story 9 - The service handles 100 concurrent users and a third clinic as data (Priority: P2)

As the practice manager, I want proof that the service copes with today's clinics, with 30 patients booking at once, and with a third clinic and 1,000 appointments a week, so that the business can grow without a rebuild.

**Why this priority**: It proves NFR-003 before go-live and gives early warning if a design choice would block growth.

**Independent Test**: Run the load test against staging sized like production with 100 concurrent simulated users (about 35 requests per second at peak) and the scale data set (3 clinics, 10 dentists, a year of appointments at 1,000 per week); read the results.

**Acceptance Scenarios**:

1. **Given** staging sized like production and today's data (2 clinics, 6 dentists, about 450 appointments a week), **When** 30 simulated patients book at once, **Then** the free-slot and booking targets (2 s and 3 s for 95%) are met.
2. **Given** the same environment, **When** 100 concurrent simulated users run for at least 10 minutes at about 35 requests per second, **Then** the free-slot and booking targets are still met and there are no errors other than "slot taken".
3. **Given** a data set of 3 clinics, 10 dentists and 1,000 appointments a week for a year, **When** the load test runs again, **Then** the targets are still met with no change to the application code or the data structures.
4. **Given** a third clinic and a tenth dentist are added through the setup screens or data load, **When** patients open the site, **Then** they are offered without a deploy.
5. **Given** the load test results, **When** they are reviewed, **Then** they are recorded in the readiness checklist with the date and the environment size.

(source: NFR-003)

---

### User Story 10 - Release 1 is checked off as ready for UAT and go-live (Priority: P1)

As the practice manager, I want a go-live readiness checklist that the delivery team completes before the user acceptance test (UAT) and go-live, so that I can sign off by trying each flow and be confident Release 1 can go live on 1 March 2027.

**Why this priority**: The date is firm (NFR-009); Release 1 must be UAT-ready by 2027-02-22. A clear checklist exposes late items early.

**Independent Test**: Walk the checklist in staging: every item has an owner, a status and evidence, and the checklist can be reviewed on 2027-02-22 for a go or no-go decision.

**Acceptance Scenarios**:

1. **Given** the checklist, **When** it is reviewed, **Then** each item shows an owner, a due date, a status (not started, in progress, done) and a link to evidence.
2. **Given** the readiness date 2027-02-22, **When** the checklist is reviewed, **Then** it covers: pipeline and rollback rehearsal, environments and secrets, restore test result, responsive check results on Chrome and Safari on Android and iPhone, English and IST checks, SLO probes and alerts running, load test result, Release 2 switches off, provider sandbox and production accounts and registrations status (owned by the messaging feature), domain and hosting confirmed, and the paper-diary dry run (owned by reception).
3. **Given** an item is not done by the readiness date, **When** the checklist is reviewed, **Then** it is marked as a risk with an owner and a plan so the date is not silently missed.
4. **Given** go-live day 2027-03-01, **When** the checklist is closed, **Then** the go or no-go decision, who made it and when are recorded.
5. **Given** the practice manager signs off by trying each flow, **When** they finish, **Then** their sign-off is recorded against the checklist (A-006).

(source: NFR-009)

---

### Edge Cases

- What happens when a phone is held in landscape or a very small phone (320 px wide) is used? The page still fits without sideways scrolling.
- What happens when the browser is older than the current Chrome or Safari? It is not covered by the target; the shell shows a plain "please update your browser" message instead of a broken page.
- What happens when the SPA is loaded but the API is down? The shell shows a plain English message and a phone number placeholder for the clinic instead of a blank screen.
- What happens when a time falls near midnight IST or on a daylight-saving date elsewhere? IST has no daylight saving; times are converted using a fixed UTC+05:30 offset.
- What happens when a migration fails halfway in production? The deployment stops, the previous release keeps running, and the migration is fixed forward (forward-only migrations; no destructive rollback).
- What happens when a database restore takes longer than 1 hour in the rehearsal? The readiness item is marked at risk and the restore process is improved and re-run before go-live.
- What happens when the load test finds the targets are missed? The release is not signed off until the cause is fixed and the test is repeated.
- What happens when personal data is accidentally added to a log message? The automated log check fails the pipeline.
- What happens when a secret is committed by mistake? The pipeline's secret scan fails the build and the secret is rotated.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The delivery team MUST have a repository for the API, a repository for the web app and an infrastructure repository, each with a README that explains how to build, test and run it locally. (source: NFR-009)
- **FR-002**: Each commit to the API repository MUST run, in order: build, unit tests, contract tests against the published API contract, image scan, deploy to staging, a smoke test (health check, sign-in with a test code, book and cancel against sandbox providers), then a production deploy by rolling replacement one replica at a time behind the health check; any failing stage MUST stop the pipeline. (source: NFR-009, NFR-004)
- **FR-003**: The web app MUST be built and published separately from the API, and the previous published build MUST be kept so it can be restored. (source: NFR-009)
- **FR-004**: The team MUST be able to roll back a release by redeploying the previous API image and the previous web build; the rollback triggers are a failing health check, server errors above 2% for 5 minutes, or reminder lag above 15 minutes. (source: NFR-009, NFR-004)
- **FR-005**: Database changes MUST be forward-only and compatible with the previous release (expand, then contract), and MUST be applied by the pipeline with a migration user that is separate from the application's database user. (source: NFR-004, NFR-009)
- **FR-006**: Dev, staging and production environments MUST each host the web app, the API and the database; staging MUST use sandbox accounts for the SMS and WhatsApp providers. (source: NFR-009, NFR-004)
- **FR-007**: Production MUST serve the web app from a CDN, route `/api` through a load balancer and web application firewall to at least 2 API replicas in 2 zones, scale between 2 and 4 replicas when CPU stays above 60%, and use a managed database with a synchronous standby in the second zone. (source: NFR-004, NFR-003)
- **FR-008**: Secrets (database credentials, provider keys, webhook secrets, token signing key) MUST be kept in a secret store and passed to the API as environment variables; no secret MAY be stored in code, images, configuration files or logs, and the pipeline MUST scan for committed secrets. (source: NFR-004, NFR-009)
- **FR-009**: Environments MUST be hosted in an India cloud region chosen by the delivery team, and the clinic's domain MUST be configurable without a code change. (source: NFR-009, NFR-004)
- **FR-010**: The database MUST be created from migrations that include the capability to prevent overlapping appointments for one dentist, and migrations MUST be repeatable on an empty database in every environment. (source: NFR-003, NFR-004)
- **FR-011**: The database MUST keep continuous log archiving with point-in-time restore and a daily snapshot kept 14 days, all encrypted, with RPO of 15 minutes and RTO of 1 hour; a restore MUST be rehearsed and recorded before go-live. (source: NFR-004)
- **FR-012**: The web app shell MUST provide a mobile-first layout so that every patient screen fits a phone without sideways scrolling in current Chrome and Safari on Android and iPhone, and needs no install. (source: NFR-001)
- **FR-013**: The shell MUST provide shared components whose tap targets are at least 44 px by 44 px, and an automated check MUST fail the build for any patient screen with a smaller target or sideways scrolling. (source: NFR-001, NFR-010)
- **FR-014**: The shell MUST define the patient booking journey so a new patient reaches a booked appointment in 5 screens or fewer after sign-in, and an automated check MUST count the screens. (source: NFR-010)
- **FR-015**: The shell MUST provide a desktop layout with role-based navigation for receptionist, dentist and practice manager that later features fill with screens; the dentist's day screen MUST also fit a phone. (source: NFR-001)
- **FR-016**: The system MUST show all screen text and messages from a single English message catalogue; no other language is supported and no text is typed directly into screens or messages. (source: NFR-008)
- **FR-017**: The system MUST store all times in UTC and show every time in IST (UTC+05:30), converting form input in IST to UTC on save. (source: NFR-008)
- **FR-018**: The API MUST expose `GET /health` (reporting API and database status) and interactive documentation at `/docs`. (source: NFR-004)
- **FR-019**: The API MUST write structured logs carrying ids and a correlation id for every request, and MUST NOT write names, phone numbers or birth years to logs; an automated test MUST fail if seeded personal data appears in logs. (source: NFR-004)
- **FR-020**: The system MUST probe online booking every minute (health check and free-slot read) in production, record the results, and report monthly availability against 99.5%; it MUST report reception-screen availability for 08:00 to 20:00 IST Monday to Saturday. (source: NFR-004)
- **FR-021**: The system MUST measure the free-slot list and booking confirmation response times and report them against 2 s and 3 s for 95% of requests (server-side p95 at most 500 ms and 800 ms). (source: NFR-003, NFR-004)
- **FR-022**: The system MUST alert the delivery team when the health check fails, when 5xx exceeds 2% for 5 minutes, when probe availability falls below target, and when reminder lag exceeds 10 minutes. (source: NFR-004)
- **FR-023**: The system MUST provide switches that hide Release 2 screens and actions from patients and staff until turned on; all Release 2 switches MUST be off at go-live; a switch change MUST be recorded with who and when and MUST not need a deploy. (source: NFR-009)
- **FR-024**: A repeatable load test MUST simulate 100 concurrent users (about 35 requests per second at peak) and 30 patients booking at once against staging, with today's data and with a data set of 3 clinics, 10 dentists and 1,000 appointments a week, and report whether the response-time targets are met. (source: NFR-003)
- **FR-025**: Adding a third clinic and further dentists MUST need no code change, schema change or deploy; this MUST be verified in the scale check. (source: NFR-003)
- **FR-026**: A go-live readiness checklist MUST list each item with owner, due date, status and evidence, and MUST be reviewed on 2027-02-22 (UAT-ready) and closed with a go/no-go record on 2027-03-01. (source: NFR-009)

### Key Entities *(include if feature involves data)*

- **Environment**: One of dev, staging, production; has a web app build, an API release, a database and a set of secrets.
- **Release**: A tested combination of an API image, a web build and database migrations, with a version and a deployment time; the previous release is kept for rollback.
- **Migration**: A forward-only, ordered database change that keeps the previous release working.
- **Backup**: A snapshot or archived log segment with a retention period and encryption; a restore record notes date, point in time, duration and result.
- **Message catalogue**: The single set of English texts for screens and messages.
- **Feature switch**: A named setting (for example, Release 2 family members) that is on or off per environment, with a change record.
- **SLO measurement**: A recorded probe result or timing used to report availability and speed against targets.
- **Readiness checklist item**: A go-live condition with owner, due date, status and evidence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every commit reaches staging through the full pipeline in one automated run, and a release can be rolled back in under 15 minutes in a rehearsal.
- **SC-002**: A new environment can be recreated from the infrastructure repository and shows a healthy site without manual steps beyond supplying secrets.
- **SC-003**: A database restore rehearsed before go-live finishes within 1 hour and loses at most 15 minutes of data.
- **SC-004**: 100% of patient screens work on a phone without sideways scrolling in current Chrome and Safari on Android and iPhone, and 100% of tap targets are at least 44 px.
- **SC-005**: A new patient can complete a booking in 5 screens or fewer after sign-in.
- **SC-006**: 100% of screens and messages are in English and every time shown matches the correct IST time in all checked cases, including a UTC/IST date boundary.
- **SC-007**: Online booking is available at least 99.5% of each month, and reception screens are available at least 99.5% of the hours 08:00 to 20:00 IST Monday to Saturday.
- **SC-008**: 95% of free-slot requests are answered within 2 s and 95% of booking confirmations within 3 s for patients on 4G, including during a 100-user load test.
- **SC-009**: The load test with 100 concurrent users and with the third-clinic data set (3 clinics, 10 dentists, 1,000 appointments a week) meets the same targets with no application or data-structure change.
- **SC-010**: No name, phone number or birth year appears in any log in any environment during automated and UAT testing.
- **SC-011**: The readiness checklist is complete (or each open item is a recorded, owned risk) on 2027-02-22, and Release 1 is live on 2027-03-01 with all Release 2 switches off.

## Assumptions

- Hosting is on a managed container service, a managed PostgreSQL 16 database and a CDN in an India cloud region chosen by the delivery team; the clinic supplies the domain. The provider and domain are not decided (PRD Q-008 is open); see open question Q1. (Assumed: ADR-0005 and ASM-002; open question Q1)
- Targets for speed and availability are the delivery team's proposals (PD-008, ASM-006); no formal SLA is promised (A-004). Open question Q2 asks the clinic to confirm.
- Current Chrome and Safari on phones and a desktop browser at reception are the supported browsers (A-001, A-002); older browsers are not tested.
- Real devices for the responsive check are an Android phone and an iPhone borrowed or from the team's device lab; the team has not stated which devices (Assumed: current mid-range Android phone and a current iPhone).
- No formal WCAG certification is required (NFR-010); plain, large, high-contrast screens are still the aim.
- Alerts go to a shared delivery-team channel and email; who is on call out of hours is not defined (Assumed: no out-of-hours rota before go-live; open question Q3).
- The sign-in code, booking, SMS and WhatsApp behaviour are built in other features; this feature supplies the pipeline, environments, shell and probes they run on. The smoke test uses stubs until those features exist.
- Release 1 UAT-readiness is 2027-02-22; Release 2 is due 2027-03-19 (not firm); the practice manager signs off by trying each flow (A-006).
- The paper-diary dry run (SA-005, RSK-010) is owned by reception; the checklist only tracks it.
- Reception and the practice manager use a desktop browser (A-001); the dentist may use a phone or the clinic PC.
