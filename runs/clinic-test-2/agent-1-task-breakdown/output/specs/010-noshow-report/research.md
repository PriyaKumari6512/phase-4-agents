# Research: No-show report per clinic and month

No NEEDS CLARIFICATION remain in the Technical Context. The decisions below close the design questions.

## D1: Where the numbers are computed

- **Decision**: `cmp-booking` gets one read-only function returning counts of appointments grouped by clinic, IST month and status. `cmp-reporting` turns counts into no-shows, non-cancelled appointments and rate.
- **Rationale**: architecture.md: "cmp-reporting ... read through cmp-booking (in-process)"; `cmp-booking` owns `ent-appointment`. One grouped SQL query, no data copied.
- **Alternatives considered**: reporting queries the appointment table itself (breaks ownership); a stored summary table refreshed by a job (more moving parts, stale figures; volume of ~52,000 rows a year does not need it); a cache (architecture says no cache).

## D2: Month boundaries in IST

- **Decision**: group by `date_trunc('month', start_at AT TIME ZONE 'Asia/Kolkata')`; start times are stored in UTC (QA-012).
- **Rationale**: NFR-008, spec FR-005. An appointment at 23:30 IST on the last day of a month is in the next UTC month.
- **Alternatives considered**: group in UTC (wrong near month ends); group in Python (loads all rows).

## D3: Status mapping

- **Decision**: no-show = status `no_show`. Denominator = all statuses except `cancelled_by_patient` and `cancelled_by_clinic` (booked, arrived, no_show). Walk-ins need no special case.
- **Rationale**: FR-032, ASM-014 (both cancel kinds excluded), ASM-004 / SA-004 (walk-in is a normal appointment). Exact status string values are taken from the existing `ent-appointment` status check in clinic-api; a task confirms them.
- **Alternatives considered**: a separate walk-in flag (Q-015 option B; not in the architecture).

## D4: 12-month window and partial month

- **Decision**: current month plus the 11 before it, in IST, newest first on screen; the current month is flagged `partial: true` and labelled "month so far".
- **Rationale**: clarifications Q3; the manager wants to see the latest trend.
- **Alternatives considered**: 12 complete months only.

## D5: Rate representation

- **Decision**: the API returns `rate` as a number with one decimal in percent (for example 12.5) or `null` when the denominator is 0; the screen shows `null` as a dash. Rounding is done once, in `calc.py` (half up).
- **Rationale**: avoids a division error (spec FR-007) and keeps the UI free of business logic.
- **Alternatives considered**: fraction 0–1 (the UI would have to round); 0 for an empty month (misleading).

## D6: Clinic list

- **Decision**: clinic ids and names come from the existing clinic list of `cmp-scheduling` (in-process read), so a clinic with no appointments still shows 12 empty rows and a third clinic appears as data.
- **Rationale**: spec FR-008. The architecture diagram shows only reporting → booking; this extra in-process read of a clinic list is minor and should be added to the component view at the next architecture revision (noted, no change made here).
- **Alternatives considered**: take clinics only from the booking counts (a clinic without appointments in 12 months would be missing; names would still be needed).

## D7: Access and feature flag

- **Decision**: a FastAPI dependency allows only the practice manager role through the `cmp-identity` access context (role re-read from the database per request, as architecture §9). A second dependency returns 404 when the setting `noshow_report_enabled` is false (default false). The web app hides the menu entry and the route behind a build-time flag in `featureFlags.ts`.
- **Rationale**: architecture §8 "R2 screens are hidden by a feature flag until their data is ready"; QA-007 role checks in the API, not the web app.
- **Alternatives considered**: a flag service (not in the architecture); a runtime flag endpoint (extra API surface for one flag).

## D8: Anonymised appointments

- **Decision**: no special handling. Anonymisation removes the personal link from `ent-appointment` but keeps clinic, start and status, so counts stay (ASM-012, RSK-007). The 12-month window is shorter than the 24-month retention, so the rule matters only for the date range of the data.
- **Alternatives considered**: none.

## D9: Observability

- **Decision**: the service logs `report_generated` with the correlation id, clinic count and duration only; it emits an OpenTelemetry span and a duration metric. No patient fields exist in the report path.
- **Rationale**: constitution II and Definition of Done.
