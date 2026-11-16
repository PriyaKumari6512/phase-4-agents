# Research: Platform foundation, delivery and non-functional baseline

All items that were open in Technical Context are resolved here. Where the architecture does not name a technology,
the choice is limited to tests, pipelines or infrastructure code and is marked **tooling decision**; none of them
change the runtime architecture.

## R1. Hosting provider and domain (Q-008, open question Q1)

- **Decision**: Provider-neutral design: managed container service, managed PostgreSQL 16 with HA standby and PITR, CDN with load balancer and WAF, in an India cloud region. Provider chosen before staging is created; placeholder domain until the clinic supplies theirs.
- **Rationale**: ADR-0005 and ASM-002 define three managed service kinds and leave the provider to us; RSK-008 says to confirm before staging set-up.
- **Alternatives considered**: A client-mandated provider (changes service names and cost, kept as a possibility); self-managed Kubernetes (rejected by ADR-0005).

## R2. Infrastructure as code (tooling decision)

- **Decision**: Terraform-style modules per kind (web-hosting, container-service, database, secrets, edge, monitoring) with one folder per environment.
- **Rationale**: The infra owner (project settings) declares Terraform and observability skills; modules keep the provider swappable (R1).
- **Alternatives considered**: Click-ops in a console (not repeatable, fails SC-002); provider-specific templates (lock-in before Q1 is answered).

## R3. CI/CD (tooling decision)

- **Decision**: Hosted CI workflows in each repo (`.github/workflows/ci.yml`; repos are on GitHub per project settings). API: build, unit tests, contract tests, image scan, secret scan, deploy staging, smoke test, rolling prod deploy gated by the health check. Web: build, unit tests, responsive checks, publish with the previous build kept.
- **Rationale**: Order of stages is fixed by architecture.md section 8. Secret scanning added for FR-008.
- **Alternatives considered**: A separate CD tool (extra moving part, constitution V).

## R4. Contract tests

- **Decision**: Run schema-based tests (generated from `contracts/clinic-api-v1.openapi.yaml`) against the running API in CI; the feature adds `GET /health` and `GET /api/v1/feature-flags` to that file.
- **Rationale**: Architecture names this contract file and the CI stage.
- **Alternatives considered**: Hand-written endpoint tests only (drift risk).

## R5. Database baseline and roles

- **Decision**: Alembic migration 0001 enables `btree_gist` and sets default privileges; migration 0002 creates `feature_flag` and `feature_flag_change` (US8). Two database users: a migration user (DDL) and an application user (DML only, thr-011). Migrations are forward-only (no downgrade scripts in production); every change is expand then contract.
- **Rationale**: ADR-0003 needs `btree_gist` before the appointment table exists in feature 004; architecture says the application user has no DDL rights and migrations are forward-only.
- **Alternatives considered**: Creating the extension in feature 004 (risks a late dependency on managed-service permissions; doing it now surfaces provider limits early).

## R6. Backups and restore rehearsal

- **Decision**: Use the managed database's continuous log archiving, PITR and daily snapshots (14 days, encrypted); the restore is rehearsed into a new instance from a snapshot plus logs, timed, and the result recorded in `clinic-infra/docs/restore-runbook.md` and the readiness checklist.
- **Rationale**: Architecture section 5 and ASM-007 fix RPO 15 minutes, RTO 1 hour and a restore test before go-live.
- **Alternatives considered**: Own `pg_dump` jobs (do not give PITR).

## R7. Web shell tooling (tooling decision)

- **Decision**: React + TypeScript SPA with a Vite-style build, Vitest-style unit tests and a Playwright-style runner for responsive checks. No i18n library: one typed `en.ts` catalogue and a tiny `t()` helper. Times shown with the browser `Intl` APIs fixed to the `Asia/Kolkata` zone.
- **Rationale**: One language only (NFR-008) means a library adds no value (constitution V). IST has no daylight saving, so a fixed zone is safe.
- **Alternatives considered**: i18next or similar (speculative for a single language); local-time display (wrong when the device is outside India, violates NFR-008).

## R8. Responsive and tap-target verification

- **Decision**: Automated checks at 320, 360, 390 and 412 px widths in Chromium and WebKit: assert no horizontal overflow and that every interactive element is at least 44 x 44 px. A manual pass on one real Android phone (Chrome) and one iPhone (Safari) before UAT, recorded in the readiness checklist.
- **Rationale**: NFR-001 names Chrome and Safari on Android and iPhone; WebKit emulation approximates Safari but cannot prove it.
- **Alternatives considered**: Cloud device farm (extra cost, unnamed); emulation only (does not meet "works on iPhone Safari" evidence).

## R9. Screen budget for NFR-010

- **Decision**: `journeys/booking-journey.ts` lists the booking screens after sign-in (who and what, slot picker, confirm, booked = 4) and a unit test asserts the count is at most 5; later features must register their screens in it.
- **Rationale**: Gives a cheap, automated guard that stops screens being added silently.
- **Alternatives considered**: Manual review only.

## R10. Logging without PII, and observability

- **Decision**: Structured JSON logs with a correlation-id middleware; a logging filter drops or masks known PII field names and the API never logs request bodies; a test seeds a name, phone and birth year and scans captured logs. OpenTelemetry for traces and metrics (constitution II). Request timing recorded per route group (free slots, booking) for the p95 SLIs.
- **Rationale**: Architecture: logs carry ids and a correlation id, never PII.
- **Alternatives considered**: Regex scrubbing alone (misses unknown shapes); filter plus "never log bodies" rule plus test is stronger.

## R11. SLO probes, alerts and report

- **Decision**: A synthetic probe every minute calls `GET /health` and the free-slot read through the public route and records the result; reception probe runs 08:00-20:00 IST Monday to Saturday. Alerts: health fails, 5xx above 2% for 5 minutes, availability below target, reminder lag above 10 minutes (a metric exposed by the messaging feature; the alert is configured here), and the rollback trigger at lag above 15 minutes. A monthly SLO report script reads the recorded results. The probe uses the monitoring service of the chosen provider (R1); the free-slot read needs the scheduling feature, so until then the probe uses a stub endpoint behind a flag.
- **Rationale**: SLO table in architecture.md section 10.
- **Alternatives considered**: Third-party uptime service (adds a data processor; not named).

## R12. Alert recipients (open question Q3)

- **Decision**: Shared delivery-team channel and email, business hours only until go-live; revisit before 2027-02-22.
- **Rationale**: No rota defined; avoids inventing on-call.

## R13. Feature flags for Release 2

- **Decision**: A small database table `feature_flag` (key, enabled, description) read by `GET /api/v1/feature-flags`; the web app hides R2 routes and menu entries when off, and the API refuses R2 actions when off. Changes are made by an admin tool that records who and when in `feature_flag_change`; no deploy needed. Default off in production at go-live.
- **Rationale**: Architecture says R2 screens are hidden by a feature flag until data is ready; a table is the smallest design (constitution V).
- **Alternatives considered**: Build-time flags (need a deploy); a flag service (extra component).

## R14. Load test and scale data (tooling decision)

- **Decision**: A Python load-test tool (in the API repo, same language as the team's backend skills) driving 100 concurrent virtual users on the slot and booking paths against staging sized like production, with a seeder that creates a 3-clinic, 10-dentist, one-year/1,000-per-week data set. The test is a repeatable script; results are stored as a report file. Booking paths use stubs until features 003-004 exist; the test is then re-run before UAT.
- **Rationale**: NFR-003 and capacity estimate (about 35 requests/s).
- **Alternatives considered**: Manual testing (not repeatable); a separate load-test platform (extra cost).

## R15. Go-live readiness checklist

- **Decision**: A markdown checklist in `clinic-infra/docs/go-live-readiness.md` with owner, due date, status and evidence per item; reviewed on 2027-02-22 and closed with go/no-go on 2027-03-01. The practice manager's sign-off (A-006) is recorded in it.
- **Rationale**: Simplest tracked artifact; the backlog tracker carries tasks, the checklist carries evidence.
- **Alternatives considered**: A tracker-only checklist (evidence links scattered).
