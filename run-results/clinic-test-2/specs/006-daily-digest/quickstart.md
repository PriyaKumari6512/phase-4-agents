# Quickstart: validate the daily digest

Prerequisites: taskflow-api checked out with migrations applied, a test PostgreSQL 16, features 001, 002 and 005 in place, `FEATURE_DIGEST=true`, the email client replaced by a recording fake.

1. Apply migrations (`migrations/versions/006_...`): `users.timezone` and `digest_deliveries` exist.
2. Create user Ana (time zone `Europe/Berlin`) with two open tasks due tomorrow on a board she belongs to, one Done task due tomorrow, one task due tomorrow assigned to someone else.
3. Run the digest job with the clock at 07:59 Berlin time: no email. Run at 08:00: exactly one email to Ana listing the two open tasks only.
4. Run the job again, and two jobs in parallel: still one email (one `sent` delivery record).
5. User with no tasks due tomorrow: no email, no failure.
6. Set the clock around 2026-03-29 (Berlin spring forward) and 2026-10-25 (fall back): one digest per day, "tomorrow" is the next calendar date.
7. Make the fake client fail once: the next tick the same day retries and sends; after 3 failures the record stays `failed`.
8. `PUT /api/v1/users/me/timezone` with `Nowhere/City` returns 422; with `Asia/Kolkata` returns 200.
9. Set `FEATURE_DIGEST=false`: the job sends nothing.

Expected results map to spec.md acceptance scenarios for User Stories 1-3 and to [contracts/timezone-api.md](contracts/timezone-api.md).
