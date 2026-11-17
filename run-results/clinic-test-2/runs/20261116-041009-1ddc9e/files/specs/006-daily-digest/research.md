# Research: Daily due-tomorrow digest

## R1: Scheduling mechanism (Q1)
- **Decision**: Kubernetes CronJob in acme/taskflow-infra, every 5 minutes, `concurrencyPolicy: Forbid`, running the notify-worker image with the digest job command.
- **Rationale**: Smallest design. Correctness relies on the delivery record, not on the scheduler, so overlapping or repeated runs are safe. A 5-minute tick covers 30- and 45-minute offsets and gives 08:00 plus at most 5 minutes (target: 15).
- **Alternatives**: internal scheduler loop in a long-running worker (needs leader election, more moving parts); one CronJob per time zone (too many manifests).

## R2: Time zone capture (Q2)
- **Decision**: `users.timezone` stores an IANA name (nullable). The settings control pre-selects the browser-detected zone; NULL means UTC at digest time.
- **Rationale**: Offsets alone do not follow DST; IANA names do. Validation uses the zone database in the Python standard library (`zoneinfo.available_timezones()`).
- **Alternatives**: UTC offset (breaks DST); silent detection at each login (changes user data without consent).

## R3: Who is due at a tick
- **Decision**: For each user, `local_now = now_utc in user zone`; the user is due when `local_now.time() >= 08:00` and no `digest_deliveries` row exists for `(user_id, local_now.date())`. Because the check is `>=` and not `==`, a missed tick or a nonexistent 08:00 still sends later the same local date. Past dates are never back-filled.
- **DST**: "tomorrow" is `local_date + 1 day` (calendar arithmetic), never `now + 24h`. Spring-forward and fall-back transitions normally happen outside 08:00; the `>=` rule plus the unique key cover odd zones. Tests use a fake clock with `Europe/Berlin`, `America/New_York`, `Australia/Lord_Howe` (30-minute DST) and `Asia/Kolkata` (no DST, +5:30).

## R4: Exactly-once
- **Decision**: Insert `digest_deliveries(user_id, local_date, status='claimed', attempts=1)` with `ON CONFLICT DO NOTHING`; only the run that inserted the row sends. On success status becomes `sent`. On a definite provider error status becomes `failed` and a later tick the same date may re-claim it with `attempts < 3` using a conditional update. A row stuck in `claimed` (crash during send) is not re-sent automatically: the outcome is unknown and duplicates are worse than one missed digest; it is counted and logged for operators.
- **Rationale**: A database unique key gives exactly-once claim without a distributed lock. Strict end-to-end exactly-once cannot be guaranteed without provider-side idempotency; whether the email provider supports an idempotency key is not stated in the architecture (open point for feature 005, not assumed here).
- **Alternatives**: advisory locks (do not survive crashes across ticks); Redis lock (extra dependency not needed).

## R5: Digest content query
- **Decision**: A single query joining tasks, boards and board membership: `assignee_id = user`, `due_date = tomorrow_local`, status not Done, the user is a member of the board. Ordered by board name then title, capped at 50 with a "+N more" line.
- **Rationale**: Enforces NFR-3 in the query itself.

## R6: Preferences from 007
- **Decision**: `app/services/digest_preferences.py` exposes `digest_allowed(user_id)`. When `FEATURE_NOTIFICATION_PREFS` is off or the preferences module is not importable it returns True; otherwise it asks the preferences service. The call site is stable, so 007 only fills in one function.

## R7: Use of F05 email client
- **Decision**: Call the F05 email client with a rendered subject and text body; no new provider code. The digest does not use the assignment outbox unless 005 defines a generic send path; if it does, use it (reuse over duplication). The exact module name is confirmed with 005 during implementation.
