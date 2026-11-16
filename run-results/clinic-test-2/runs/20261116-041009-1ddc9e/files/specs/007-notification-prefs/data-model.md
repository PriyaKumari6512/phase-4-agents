# Data Model: Notification preferences

Migration: one new Alembic migration in `migrations/versions/` (never edit a merged migration).

## notification_channels (configuration)

| Field | Type | Constraint |
|---|---|---|
| code | varchar(32) | primary key, lowercase `[a-z_]+` |
| label | varchar(64) | not null |
| enabled | boolean | not null, default true |

Seed: `email` (enabled). No other channel (assumption A1, open question Q1).

## notification_frequencies (configuration)

| Field | Type | Constraint |
|---|---|---|
| code | varchar(32) | primary key, lowercase `[a-z_]+` |
| label | varchar(64) | not null |
| window_minutes | integer | not null, >= 0; 0 means immediate |
| enabled | boolean | not null, default true |

Seed (assumption A2, open question Q1): `immediate` (0), `hourly` (60), `daily` (1440). A window of 1440 ends at 08:00 in the user's time zone (assumption A4).

## notification_preferences

| Field | Type | Constraint |
|---|---|---|
| id | uuid | primary key |
| user_id | uuid | not null, foreign key to users (owned by 001), on delete cascade |
| notification_type | varchar(32) | not null, one of `assignment`, `mention`, `digest` (check constraint) |
| channel_code | varchar(32) | not null, foreign key to notification_channels.code |
| enabled | boolean | not null, default true |
| frequency_code | varchar(32) | not null, default `immediate`, foreign key to notification_frequencies.code |
| updated_at | timestamptz | not null |

Unique: (`user_id`, `notification_type`, `channel_code`). Index on `user_id`.

Rules:
- No row for a user and type means defaults: enabled true, channel `email`, frequency `immediate` (FR-007).
- Type `digest` accepts only frequency `immediate` (its schedule is fixed, FR-6); only the on/off flag is meaningful.
- Submitted channel and frequency must exist and be enabled; otherwise the request is rejected (FR-005).
- If a stored frequency or channel is later disabled, reads and decisions treat it as the default.

## Held notification (not owned here)

Held notifications are rows of the notification outbox owned by 005 with a held state and a deliver-after time (to be confirmed with 005). This feature only creates held rows (through the decision result and the sender) and consumes them in the summary job.

## State transitions

- Preference: absent (default) -> saved; saved -> changed; a save replaces all of the user's rows atomically.
- Held notification: held -> summarised and sent (at window end) or dropped (type switched off).
