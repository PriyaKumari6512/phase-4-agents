# Contract: Delivery decision (for senders of 004, 005 and 006)

Module: `app/services/notification_preferences.py`

```text
resolve_delivery(user_id, notification_type, channel="email", now=None) -> DeliveryDecision
DeliveryDecision.action: "send_now" | "send_later" | "skip"
DeliveryDecision.deliver_after: datetime | None   # set only for "send_later"
```

`notification_type` is one of `assignment`, `mention`, `digest`.

Rules, in order:

1. Flag `FEATURE_NOTIFICATION_PREFS` off -> `send_now`.
2. No saved preference (or stored channel/frequency now disabled) -> default: `send_now`.
3. Preference `enabled = false` -> `skip`.
4. Frequency `immediate` -> `send_now`.
5. Frequency `hourly` or `daily` -> `send_later` with `deliver_after` = end of the current window (hourly: next top of the hour; daily: next 08:00 in the user's time zone, 08:00 UTC if unknown).
6. Any error while reading -> `send_now`, a structured log entry and a counter metric `notification_prefs_fallback_total`.

Sender obligations:

- `send_now`: send as the sender's own story defines.
- `skip`: do not send; do not create an outbox row.
- `send_later`: store the notification in the 005 outbox as held with `deliver_after`; the notify-worker job `send_notification_summaries` sends one summary per user, type and window.
- Senders never read the preference tables directly.
