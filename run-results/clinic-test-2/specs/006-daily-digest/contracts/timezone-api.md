# Contract: Time zone API

Prefix `/api/v1` (A, from the implementation contract). Authentication per feature 001: the caller is the authenticated user and can only read or change their own time zone. Both endpoints are available whether or not `FEATURE_DIGEST` is on (the stored value is harmless); the settings control is hidden when the flag is off.

## GET /api/v1/users/me/timezone

Response 200:

```json
{ "timezone": "Europe/Berlin" }
```

`timezone` is `null` when never set (digest uses UTC).

## PUT /api/v1/users/me/timezone

Request:

```json
{ "timezone": "Europe/Berlin" }
```

- `timezone`: string, required, at most 64 characters, must be an IANA zone name known to the zone database.

Responses:
- 200 with the stored value.
- 401 not authenticated.
- 422 invalid or unknown zone; stored value unchanged.

## Worker command (internal, not HTTP)

`python -m app.worker.jobs.daily_digest` (A, follows the worker skeleton of 005): one tick, exits 0 on a normal run including partial send failures (recorded), non-zero only when the run itself cannot start (database unavailable). Does nothing and exits 0 when `FEATURE_DIGEST` is off.
