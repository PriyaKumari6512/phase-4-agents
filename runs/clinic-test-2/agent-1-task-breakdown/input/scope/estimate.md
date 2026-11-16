# Estimate: clinic-test-2

> **Sample data.** Written by hand for a Phase 3B demo, in the requirements contract's format. Not produced by
> the Phase 1–2 agents; the client is fictional. The numbers follow the draft estimation guide's method; they
> are not company figures.

## Basis
Sizes and percentages come from `/knowledge/estimation-guide.md`, a **draft (version 0.1)**. Each module was sized by the guide's bands (`XS` 1-3, `S` 3-8, `M` 8-15, `L` 15-30, `XL` 30-60 person-days), at the low end for well-understood work and at the high end when a driver applies (outside system, roles, open question). Effort covers design, build, unit tests and review of the module; cross-cutting work is added below.

No blocking question is open. Two modules depend on open questions (MOD-01 on Q-007, MOD-07 on Q-009), so they are `medium` confidence; the overall confidence is **medium**.

## Breakdown
| MOD | Module | Size | Effort (person-days) | Confidence | Drivers |
|---|---|---|---|---|---|
| MOD-01 | Platform, sign-in, roles and clinics | M | 10–15 | medium | 4 roles; clinic separation for reception; phone-code sign-in; family members (Q-007 default). |
| MOD-02 | Dentist schedules, treatments and slots | M | 8–12 | high | Weekly hours per dentist per clinic, breaks, leave; slot calculation; treatment list with durations. |
| MOD-03 | Online booking | M | 9–14 | high | Clinic, treatment, dentist or first available, slot; no double booking under concurrent bookings. |
| MOD-04 | Patient appointments: view, reschedule, cancel | S | 4–7 | high | 4-hour cut-off; frees the slot at once. |
| MOD-05 | Reception day view, check-in and no-shows | M | 9–14 | high | Day view per dentist; reception booking without cut-off and for long treatments; arrivals, no-shows, undo; dentist's own day. |
| MOD-06 | Repeat no-show block | S | 3–5 | high | Rolling 6-month count; lift by reception. |
| MOD-07 | Reminders and messages (SMS and WhatsApp) | L | 15–24 | medium | Two providers; DLT and template approval; scheduling with quiet hours (Q-009); fallback to SMS; delivery failures; opt-out. |
| MOD-08 | No-show report | S | 3–5 | high | One figure and rate per clinic per month, 12 months. |

## Cross-cutting work
| Work | Share | Low (person-days) | High (person-days) |
|---|---|---|---|
| UI / UX design | 10–15% | 6 (10% of 61) | 15 (15% of 96 = 14.4) |
| QA and test automation | 20–25% | 12 (20% of 61 = 12.2) | 24 (25% of 96) |
| Project management and BA | 10–15% | 6 (10% of 61) | 15 (15% of 96 = 14.4) |
| DevOps, environments, release | 5–10% | 3 (5% of 61 = 3.05) | 10 (10% of 96 = 9.6) |
| Total cross-cutting | 45–65% | 27 | 64 |

## Totals
Module effort: 61–96 person-days. With cross-cutting (×1.45 to ×1.65) and 30% contingency (×1.3): 61 × 1.885 = 115; 96 × 2.145 = 205.9, so 206.

| Release | Modules | Module effort (low–high) | With cross-cutting and contingency |
|---|---|---|---|
| Release 1 (go-live, 1 March 2027) | MOD-01, MOD-02, MOD-03, MOD-04, MOD-05, MOD-07 | 10 + 8 + 9 + 4 + 9 + 15 = 55 to 15 + 12 + 14 + 7 + 14 + 24 = 86 | 55 × 1.885 = 103.7, so 104; 86 × 2.145 = 184.5, so 185. **104–185** |
| Release 2 (after go-live) | MOD-06, MOD-08 | 3 + 3 = 6 to 5 + 5 = 10 | 6 × 1.885 = 11.3, so 12; 10 × 2.145 = 21.5, so 22. **12–22** |

## Team
- 2 full-stack developers
- 1 QA engineer (test automation)
- 0.5 UI / UX designer
- 0.5 project manager / business analyst
- 0.25 DevOps engineer

Team size for the timeline: 4.25 people.

## Timeline
Method from the guide: weeks = person-days ÷ (team size × 4), plus 1-2 weeks for UAT and launch. Team size × 4 = 4.25 × 4 = 17 person-days per week.

| Scope | Low | High | Weeks |
|---|---|---|---|
| Full scope in one release | 115 ÷ 17 = 6.8, + 1 = about 8 | 206 ÷ 17 = 12.1, + 2 = about 14 | **8–14 weeks** |
| Release 1 (go-live) | 104 ÷ 17 = 6.1, + 1 = about 7 | 185 ÷ 17 = 10.9, + 2 = about 13 | **7–13 weeks** |
| Release 2 (after go-live) | 12 ÷ 17 = 0.7 | 22 ÷ 17 = 1.3 | **1–2 weeks** after Release 1 |

**Go-live date.** The request date is 10 November 2026; 1 March 2027 is about 16 weeks away. Release 1 fits even at the high end (13 weeks), with about 3 weeks to spare for Gate 1, Gate 2 and the SMS and WhatsApp registrations (DEP-001, DEP-002), which are the main schedule risk.

## Assumptions
SA- IDs that change the numbers:
- SA-001: family members on one account (MOD-01, MOD-03, MOD-06).
- SA-002: hosting in India chosen by us (DevOps share).
- SA-003: reminder quiet hours (MOD-07).
- SA-004: walk-ins as normal appointments (MOD-05, MOD-08).
- SA-005: future appointments typed in by reception, no import (MOD-05).
- SA-006: sign-in code by SMS only (MOD-01, MOD-07).
- SA-008: WhatsApp fallback to SMS (MOD-07).

## For the Delivery Manager
Rates, price and commercial terms are set by the Delivery Manager.
