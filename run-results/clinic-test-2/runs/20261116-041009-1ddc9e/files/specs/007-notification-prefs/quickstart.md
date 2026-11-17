# Quickstart: Notification preferences validation

Prerequisites: dev environment with taskflow-api, taskflow-web and notify-worker running, the migration applied, `FEATURE_NOTIFICATION_PREFS=true`, two users A and B on a shared board.

1. Defaults: sign in as A, `GET /api/v1/users/me/notification-preferences`; expect all three types enabled, channel email, frequency immediate. (Story 1)
2. Save: `PUT` with `mention` disabled; `GET` again and reload the settings page; expect `mention` off. (Story 1)
3. Isolation: sign in as B; B's preferences are unchanged. (Story 1)
4. Keyboard: on the settings page use only Tab, Space and Enter to change and save a type; focus is visible and the save status is announced. (Story 1)
5. Validation: `PUT` with channel `sms` or frequency `weekly`; expect 422 and no change. (Stories 1, 2)
6. Senders: with `assignment` off for A, assign a task to A and to B; only B receives an email. (Story 3)
7. Batching: set `mention` to hourly for A, mention A three times; at the end of the hour A receives one summary listing the three mentions. (Story 2)
8. Flag off: set `FEATURE_NOTIFICATION_PREFS=false`; endpoints answer 404, the settings link is hidden, all senders send immediately. (Stories 1, 3)

Run the automated checks with pytest (`tests/`) in taskflow-api and the component tests in taskflow-web.
