# Research: Patient appointment list, reschedule, cancel and status history

All Technical Context items were resolved from architecture.md and the constitution; no NEEDS CLARIFICATION remains. Open product questions Q1-Q3 are in clarifications.md.

## R1: Where is the 4-hour cut-off checked?
- Decision: on the server, inside the cancel/reschedule transaction, comparing the appointment's stored UTC start with the server's UTC now (`start - now >= 4 h` allows). The screen also hides the buttons, but only as convenience.
- Rationale: the UI can be stale; the architecture puts authorisation and rules on the server (thr-004).
- Alternatives: client-only check (rejected, bypassable); database trigger (rejected, the rule differs for reception, which has no cut-off).

## R2: How does a reschedule stay safe against double booking?
- Decision: update the same appointment row to the new dentist and time-range inside one transaction; the exclusion constraint (ADR-0003) refuses an overlap, which is mapped to a "slot taken" 409 with the next free slots (same answer as booking, FR-012). Lock the appointment row first (`SELECT ... FOR UPDATE`) so a simultaneous cancel and reschedule serialise.
- Rationale: one mechanism for booking and reschedule; no second check path.
- Alternatives: insert new row and cancel old (rejected: breaks link identity, two events, more reminder churn); advisory locks (rejected, constraint is enough).

## R3: How are history, reminder and messages made atomic?
- Decision: `manage_service` opens one session transaction: lock row, check state and cut-off, check policy (reschedule only), change row, `history.record(...)`, call `messaging.replace_reminder(...)` (reschedule) or `messaging.cancel_reminder(...)` (cancel), call `messaging.create_change_notice(...)`, commit. The dispatcher of feature 007 sends the message after commit.
- Rationale: architecture section 5 (all cross-component writes in one transaction) and ent-message work-list design (ADR-0002).
- Alternatives: send in the request (rejected, provider outage would fail a cancel).

## R4: Idempotency of repeated requests
- Decision: cancel is naturally idempotent (a second call on an already patient-cancelled appointment returns the same result with no new rows). Reschedule takes an `Idempotency-Key` header, as architecture QA-003 requires for booking; a repeat with the same key and same target returns the first result. Without a key, a repeat to the same slot is answered "same time".
- Rationale: writes are never retried by the client automatically, but patients double-tap.
- Alternatives: separate idempotency table (rejected as not needed for cancel; for reschedule the key is stored on the event row, unique per appointment).

## R5: Status values enforced in the database
- Decision: a `CHECK` constraint on `appointment.status` with the five values (`booked`, `arrived`, `no_show`, `cancelled_by_patient`, `cancelled_by_clinic`) and the same on `appointment_event.from_status/to_status`; the migration adds the constraint to the appointment table only if it is not already there (thr-011).
- Rationale: architecture requires the status check in DB. The appointment table is created by the online booking feature; this feature must not assume it already has the check.

## R6: List by account
- Decision: the list query selects appointments whose person belongs to the token owner's account (join person -> account), so family members appear automatically once feature 008 adds them; until then only the account holder's person exists.
- Rationale: spec requires the list to work by account.
- Alternatives: by patient id only (rejected, would need rework in feature 008).

## R7: Link from messages
- Decision: the web route `/appointments/:id` is the link target; if there is no session the SPA sends the patient through sign-in and returns to the route. The API answers 404 for appointments outside the owner's account.
- Rationale: link carries only the appointment id, no authority (thr-004); 404 rather than 403 avoids leaking existence.

## R8: Reception cancel actor and status (ASM-014)
- Decision: `status_service.change_status(appointment_id, to_status, actor, reason)` is the single function; reception passes `cancelled_by_patient` when "patient asked" is set, else `cancelled_by_clinic`. Feature 006 calls it; this feature tests it.
- Rationale: one write path for history (thr-006).

## R9: Retention
- Decision: no new job here; the 24-month retention job of the appointment (feature owning ASM-012) must treat `appointment_event` rows by cascade of the appointment's anonymisation. This feature adds the foreign key and notes it in data-model.md.
