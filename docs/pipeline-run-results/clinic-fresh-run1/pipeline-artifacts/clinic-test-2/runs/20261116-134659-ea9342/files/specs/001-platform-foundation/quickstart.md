# Quickstart: validating the platform foundation

Use this to prove the foundation works end to end. Details are in [plan.md](./plan.md), [data-model.md](./data-model.md) and [contracts/platform-api.openapi.yaml](./contracts/platform-api.openapi.yaml).

## Prerequisites

- Access to the three repositories (`brightsmile/clinic-api`, `brightsmile/clinic-web`, `brightsmile/clinic-infra`) and to dev and staging environments.
- Python 3.12, Node (current LTS), a local PostgreSQL 16 with `btree_gist` available (or the dev database).
- Secrets for dev from the secret store, set as environment variables (never committed).

## Scenarios

1. **Local run (US1, US7)**: start the API against a local database, apply migrations, call `GET /health` and open `/docs`. Expected: `status: ok`, `database: ok`; the Swagger page lists `/health` and `/api/v1/feature-flags`.
2. **Pipeline (US1)**: push a trivial commit; expect all stages green in order and staging showing the new version. Then push a commit with a failing test and one with a seeded HIGH finding; expect both stop before deploy.
3. **Rollback (US1)**: in staging deploy a version whose health check fails; expect the rollback to the previous image and web build within 15 minutes, following `clinic-infra/docs/rollback.md`.
4. **Environments and secrets (US2)**: for each of dev, staging, prod open the site, call `/api/health` through the edge, and search the repos, images and logs for secret values. Expected: health ok; no secret found.
5. **Database and restore (US3)**: apply migrations to an empty database twice (second run is a no-op); confirm `btree_gist` and the flag tables; try a DDL statement as the application user (refused). Then run the restore rehearsal and record time and data age.
6. **Responsive (US4)**: run the responsive checks locally and in CI; open the sample patient screens on one real Android phone (Chrome) and one iPhone (Safari). Expected: no sideways scrolling, tap targets at least 44 px, booking journey of at most 5 screens.
7. **English and IST (US5)**: run the time and catalogue tests, including 2027-02-28T19:00:00Z (shown 2027-03-01 00:30 IST).
8. **Staff layout (US6)**: open the staff area at 1280 px and the dentist day page at 390 px.
9. **Logs and probes (US7)**: make a request with a seeded test patient name, phone and birth year; follow its correlation id in logs; confirm none of the seeded values appear. Stop the staging API and confirm an alert arrives and the probe records a failure.
10. **Feature flags (US8)**: with `r2.family-members` off the sample R2 route and API action are unavailable; turn it on in staging with the admin tool; it appears without a deploy and a change row is recorded.
11. **Load and scale (US9)**: run the load test at 100 virtual users, then seed the 3-clinic data set and run again. Expected: 95% of free-slot responses within 2 s and of booking confirmations within 3 s; report stored.
12. **Readiness (US10)**: review `clinic-infra/docs/go-live-readiness.md` on 2027-02-22; every item has owner, status and evidence or a recorded risk.
