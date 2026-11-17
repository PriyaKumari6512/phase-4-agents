# Contract: Notification preferences API

Prefix `/api/v1` (assumption in the implementation contract). JSON. Authentication is the mechanism owned by 001; every call acts on the current user only. When `FEATURE_NOTIFICATION_PREFS` is off every endpoint below answers 404.

## GET /api/v1/users/me/notification-preferences

200:

```json
{
  "types": [
    {"type": "assignment", "label": "Task assigned to me", "supports_frequency": true},
    {"type": "mention", "label": "Mentioned in a comment", "supports_frequency": true},
    {"type": "digest", "label": "Daily digest", "supports_frequency": false}
  ],
  "channels": [{"code": "email", "label": "Email"}],
  "frequencies": [
    {"code": "immediate", "label": "Immediately"},
    {"code": "hourly", "label": "Hourly summary"},
    {"code": "daily", "label": "Daily summary"}
  ],
  "preferences": [
    {"notification_type": "assignment", "channel": "email", "enabled": true, "frequency": "immediate"}
  ]
}
```

`channels` and `frequencies` list only enabled configuration rows. `preferences` always has one entry per type (defaults filled in for types without a saved row).

Errors: 401 not authenticated; 404 flag off.

## PUT /api/v1/users/me/notification-preferences

Body: `{"preferences": [{"notification_type": "...", "channel": "...", "enabled": true, "frequency": "..."}]}`.

Replaces the current user's preferences atomically. Returns 200 with the same body as GET.

Errors: 401; 404 flag off; 422 for unknown/disabled channel or frequency, unknown type, duplicate type/channel pair, or a frequency other than `immediate` for `digest`. Nothing is saved on error.

## GET /api/v1/notification-preferences/health

Health check required by the constitution. 200 `{"status": "ok"}` when the database answers; 503 otherwise; 404 when the flag is off. No authentication, no user data.
