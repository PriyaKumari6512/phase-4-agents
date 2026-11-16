# Clarifications: Patient online booking

No user was available during the run. The most reasonable option was assumed for each question. The assumption is also written in spec.md (Assumptions).

## Q1: Limit on upcoming online appointments per patient

- **Context**: FR-011 does not limit how many appointments a patient may hold.
- **Options**: A) no limit; B) a fixed limit (for example 3 upcoming online bookings); C) one per treatment type.
- **Assumed**: A, no limit. The PRD states none and the repeat no-show block (feature 009) is the only abuse control in scope.
- **Why**: adding a limit would invent a rule. If the client wants one, it is a small check in the booking step.

## Q2: Minimum notice for an online booking

- **Context**: "A free slot within the next 30 days" says nothing about same-day slots that start soon.
- **Options**: A) any slot not yet started can be booked; B) a fixed minimum notice (for example 2 hours); C) no same-day online booking.
- **Assumed**: A. A reminder is not sent for a booking made less than 24 hours ahead (FR-028 in feature 007), and the PRD sets no notice rule.
- **Why**: the smallest rule that matches the PRD wording. Reception may want a notice period so the dentist is not surprised; to confirm with the client.

## Q3: Same patient booking overlapping times

- **Context**: nothing in the PRD stops one patient booking two different dentists at the same time.
- **Options**: A) allow; B) refuse an overlap for the same patient; C) warn but allow.
- **Assumed**: A, allow. The only no-overlap rule required is per dentist (QA-003).
- **Why**: avoids inventing a patient-level rule; to confirm with the client.
