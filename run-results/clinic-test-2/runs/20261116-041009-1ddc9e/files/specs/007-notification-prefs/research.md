# Research: Notification preferences

## R1: Channels and frequencies (open question Q1)

- Decision: store channels and frequencies as rows in two small configuration tables with an `enabled` flag; seed one channel (`email`) and three frequencies (`immediate`, `hourly`, `daily`).
- Rationale: the client has not decided (prd.md section 7); the PRD assumption is that email is the only channel. Rows can be enabled, disabled or added without changing senders or the API shape.
- Alternatives considered: hard-coded enums (needs a code change and deploy for every client decision); a JSON settings blob per user (no validation, no referential integrity).

## R2: Where the decision is made

- Decision: one function `resolve_delivery(user_id, notification_type, channel)` in `app/services/notification_preferences.py`, called in-process by the senders (all run in taskflow-api or notify-worker, the same codebase).
- Rationale: simplest design; no network hop; one place for the flag check and the fallback.
- Alternatives considered: an HTTP endpoint for senders (needless latency and failure mode); each sender reading the table itself (duplicated logic).

## R3: Fail-open on errors

- Decision: when preferences cannot be read the decision is "send now", logged and counted.
- Rationale: goal G2 (no assignment missed) outweighs a possible unwanted email.
- Alternatives considered: fail closed (risks a missed assignment).

## R4: Batching held notifications (Q1/Q2)

- Decision: for hourly/daily frequency the sender stores the notification in the 005 outbox as held with a deliver-after time; a notify-worker job `send_notification_summaries` runs periodically, groups due held notifications by user, type and window, and sends one summary email via the 005 email client.
- Rationale: reuses the outbox and email client owned by 005; no new queue.
- Alternatives considered: separate queue (violates simplicity); Redis timers (not a system of record).
- Open dependency: 005's outbox must support a held state and a deliver-after time (to be confirmed with 005).

## R5: Window ends

- Decision: hourly windows end at the top of the hour; daily windows end at 08:00 in the user's time zone (from 006), 08:00 UTC when unknown (assumption A4).
- Rationale: aligns with the digest time in FR-6; no further decision needed from the client.
- Alternatives considered: rolling windows from the first held notification (harder to explain and test).

## R6: Frontend flag handling

- Decision: the endpoints return 404 when the flag is off; the web app shows the settings link only if the preferences request succeeds.
- Rationale: one flag, read in one place (API environment); architecture.md names no frontend flag mechanism.
- Alternatives considered: a build-time web flag (second source of truth).

## R7: Accessibility

- Decision: native form controls (checkbox/switch semantics via checkbox, native select), labels bound to controls, a polite live region for save status, visible focus.
- Rationale: NFR-4 keyboard-only, WCAG 2.1 AA.
- Alternatives considered: custom dropdown widgets (more keyboard work and risk).
