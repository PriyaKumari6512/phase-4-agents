# Backlog: clinic-test-2

> **Sample data.** Written by hand for a Phase 3B demo, in the requirements contract's format. Not produced by
> the Phase 1–2 agents; the client is fictional.

## Method

Sources used: `user-stories.md` (29 stories, none withdrawn), `prd.md` v1.0, `estimate.md`, `scope.md`, `register.md`, `clarifications.md`.

**MoSCoW definitions**
- `Must`: the product cannot go live without it, or another Must depends on it.
- `Should`: important, but go-live is possible without it for a short time.
- `Could`: nice to have; the first to move if time runs short. No story is `Could`.
- `Won't`: agreed not in this plan. No story is `Won't`; what the client does not want is in the PRD non-goals.

**"Proposed" marking.** A row is marked `proposed` in Rationale when its priority or release rests on no client statement.

**How the MVP line was drawn**
1. Go-live on 1 March 2027 is firm (REQ-019). The client's purpose is online booking and fewer no-shows (REQ-001, REQ-002), so booking, changes, the reception day, no-show marking and reminders are in the MVP.
2. The repeat no-show block (MOD-06) and the no-show report (MOD-08) need a few weeks of no-show data before they matter, so they follow in R2, as the estimate's Release 2 has them.
3. Two stories move to R2 beyond the estimate's split: family members (US-006, MOD-01; Q-007 is open) and the WhatsApp-to-SMS fallback with the failed-reminder list (US-027, MOD-07). Both are proposed (see Decisions needed, item 1).
4. Ranking: dependencies first, then priority, then value.

## Backlog
| Rank | US | EPIC | MoSCoW | Release | MOD | Rationale |
|---|---|---|---|---|---|---|
| 1 | US-001 | EPIC-01 | Must | MVP | MOD-01 | REQ-018; every appointment needs a clinic and a dentist. |
| 2 | US-003 | EPIC-01 | Must | MVP | MOD-01 | REQ-026; staff must sign in before anything else is set up. |
| 3 | US-005 | EPIC-01 | Must | MVP | MOD-01 | REQ-026; staff accounts. Proposed: no client priority given. |
| 4 | US-004 | EPIC-01 | Must | MVP | MOD-01 | REQ-026, NFR-006; role separation. |
| 5 | US-009 | EPIC-02 | Must | MVP | MOD-02 | REQ-014 client; needed by US-010 and US-011. DEP-003 (treatment list). |
| 6 | US-007 | EPIC-02 | Must | MVP | MOD-02 | REQ-013 client; needed by US-010. DEP-003 (hours). |
| 7 | US-008 | EPIC-02 | Must | MVP | MOD-02 | REQ-013 client (leave). |
| 8 | US-010 | EPIC-02 | Must | MVP | MOD-02 | Needed by every booking story. |
| 9 | US-002 | EPIC-01 | Must | MVP | MOD-01 | REQ-023 client; needed by US-011. DEP-001 (SMS for the code). |
| 10 | US-013 | EPIC-03 | Must | MVP | MOD-07 | REQ-012 client (channel choice at booking). |
| 11 | US-011 | EPIC-03 | Must | MVP | MOD-03 | REQ-003 client; the main goal REQ-001. |
| 12 | US-012 | EPIC-03 | Must | MVP | MOD-03 | Part of REQ-003: a booking must be kept. |
| 13 | US-014 | EPIC-03 | Must | MVP | MOD-07 | REQ-016 inferred. Proposed: the client did not ask for confirmations. DEP-001, DEP-002. |
| 14 | US-015 | EPIC-04 | Must | MVP | MOD-04 | Needed by US-016 and US-017. |
| 15 | US-016 | EPIC-04 | Must | MVP | MOD-04 | REQ-004, REQ-006 client. |
| 16 | US-017 | EPIC-04 | Must | MVP | MOD-04 | REQ-005, REQ-006 client; frees slots (goal REQ-002). |
| 17 | US-018 | EPIC-05 | Must | MVP | MOD-05 | REQ-007 client. |
| 18 | US-019 | EPIC-05 | Must | MVP | MOD-05 | REQ-010 inferred, REQ-030 client: reception types in the paper diary before go-live (SA-005, DEP-006). |
| 19 | US-020 | EPIC-05 | Must | MVP | MOD-05 | REQ-009 client. |
| 20 | US-021 | EPIC-05 | Must | MVP | MOD-05 | REQ-008 client; goal REQ-002. |
| 21 | US-023 | EPIC-05 | Must | MVP | MOD-05 | FR-024; the history behind no-show disputes. Proposed: no client priority given. |
| 22 | US-022 | EPIC-05 | Must | MVP | MOD-05 | REQ-027 client. |
| 23 | US-026 | EPIC-07 | Must | MVP | MOD-07 | REQ-011, REQ-012 client; the main lever on no-shows (REQ-002). DEP-001, DEP-002. |
| 24 | US-028 | EPIC-07 | Must | MVP | MOD-07 | NFR-011: messaging rules require an opt-out before reminders are sent. |
| 25 | US-024 | EPIC-06 | Should | R2 | MOD-06 | REQ-015 client; needs no-show history (US-021). |
| 26 | US-025 | EPIC-06 | Should | R2 | MOD-06 | REQ-015 client; ships with US-024. |
| 27 | US-027 | EPIC-07 | Should | R2 | MOD-07 | SA-008, FR-033. Proposed: reminders work without the fallback; PRD Questions to raise, item 2. |
| 28 | US-006 | EPIC-01 | Should | R2 | MOD-01 | SA-001; Q-007 open. Proposed: until then a parent books under their own name and tells reception. |
| 29 | US-029 | EPIC-08 | Should | R2 | MOD-08 | REQ-028 client; needs a month of data. |

## Releases

### MVP

**Goal:** patients book, move and cancel online and get reminders; reception runs the day and marks no-shows. Live on 1 March 2027.

| MOD | Stories in MVP | Estimate range | Share | MVP effort (person-days) |
|---|---|---|---|---|
| MOD-01 | 5 of 6 | 10–15 | 83% | 9–13 (8.3–12.5) |
| MOD-02 | 4 of 4 | 8–12 | 100% | 8–12 |
| MOD-03 | 2 of 2 | 9–14 | 100% | 9–14 |
| MOD-04 | 3 of 3 | 4–7 | 100% | 4–7 |
| MOD-05 | 6 of 6 | 9–14 | 100% | 9–14 |
| MOD-07 | 4 of 5 | 15–24 | 80% | 12–20 (12–19.2) |
| **Module total** | | | | **51–80** |

With cross-cutting and contingency: low 51 × 1.885 = 96.1, so **97**; high 80 × 2.145 = 171.6, so **172**. **MVP: 97–172 person-days, about 7–12 weeks** (97 ÷ 17 = 5.7, + 1; 172 ÷ 17 = 10.1, + 2), against about 16 weeks to 1 March 2027.

### R2

**Goal:** stop repeat no-shows, measure them, and close the reminder and family gaps. About 2–3 weeks after go-live.

**Stories (5), in rank order:** US-024, US-025, US-027, US-006, US-029.

| MOD | Stories in R2 | Estimate range | R2 effort (person-days) |
|---|---|---|---|
| MOD-01 | 1 of 6 | 10–15 | 2–3 (1.7–2.5) |
| MOD-06 | 2 of 2 | 3–5 | 3–5 |
| MOD-07 | 1 of 5 | 15–24 | 3–5 (3–4.8) |
| MOD-08 | 1 of 1 | 3–5 | 3–5 |
| **Module total** | | | **11–18** |

With cross-cutting and contingency: low 11 × 1.885 = 20.7, so **21**; high 18 × 2.145 = 38.6, so **39**. **R2: 21–39 person-days, about 2–3 weeks** after the MVP.

### Check against the full scope

Module totals: MVP 51–80 and R2 11–18 add up to 62–98, against 61–96 in the estimate; rounding each share up adds 1–2 days. All 29 stories are in exactly one release.

## Decisions needed

1. **Two stories move to R2 beyond the estimate's split** (US-006 family members, US-027 fallback and failed-reminder list). The client should confirm, or they return to the MVP (about 5–8 person-days, still inside the 16 weeks).
2. **Q-007 (family members)** decides US-006; if families need separate sign-ins on one phone, MOD-01 grows by 2–4 person-days.
3. **Confirmations (US-014)** rest on an inferred requirement (REQ-016); the client should confirm they want them, since each message has a charge.
