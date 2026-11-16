# Requirements review: clinic-test-2

> **Sample data.** Written by hand for a Phase 3B demo, in the requirements contract's format. Not produced by
> the Phase 1–2 agents; the client is fictional.

## Result

**Ready for Gate 2, with 1 major and 3 minor issues.**

The chain is complete: all 25 in-scope REQs reach an FR or NFR, all 33 FRs reach a story, all 29 stories have acceptance criteria and exactly one backlog row. IDs agree across the files and the 8 modules match everywhere. The MVP (97–172 person-days, 7–12 weeks) fits the 16 weeks to the firm go-live on 1 March 2027. The main schedule risk is outside the build: SMS DLT registration and WhatsApp template approval (DEP-001, DEP-002).

## Coverage
| Link | Count | Missing |
|---|---|---|
| In-scope REQs in `scope.md` | 25 (REQ-003 to REQ-019, REQ-023 to REQ-030) | none |
| Out-of-scope REQs | 3 (REQ-020, REQ-021, REQ-022), only in the PRD non-goals | none cited as live |
| Goal REQs → PRD goals | 2 of 2 (REQ-001, REQ-002) | none |
| In-scope REQs → FR or NFR | 25 of 25 (21 through FRs; REQ-017, REQ-019, REQ-024, REQ-029 through NFRs only) | none |
| Each in-scope REQ → exactly one MOD | 25 of 25 | none |
| FR / NFR → REQ | 33 FRs and 11 NFRs, all trace to at least one REQ | none |
| FR → US | 33 of 33 (Coverage table in `user-stories.md` agrees with each story's Traces line) | none |
| US → AC | 29 of 29, 71 ACs | none |
| US → backlog row | 29 of 29, one row each (MVP 24, R2 5) | none |
| MOD in PRD FRs, backlog and estimate | 8 of 8 agree | none |

## Issues
| ISS | Severity | File | IDs | Problem | Suggested fix | Fix by |
|---|---|---|---|---|---|---|
| ISS-001 | major | prd.md; user-stories.md | FR-029, US-027, SA-008, PD-005 | FR-029 sends an SMS to a patient who chose WhatsApp when WhatsApp fails. The client has not agreed to this, and it adds message charges. | Ask the client (PRD Questions to raise, item 2); until then keep US-027 in R2, as the backlog does. | clarification |
| ISS-002 | minor | backlog.md | US-006, US-027, Method point 3 | Two stories move to R2 beyond the estimate's Release 1 split. The effect is small but not agreed. | Client confirms (backlog Decisions needed, item 1). | prioritization |
| ISS-003 | minor | prd.md | Section 2, REQ-002 | The no-show target is `TBD` because today's rate is unknown. | Agree that the first 2 months of app data are the baseline. | prd |
| ISS-004 | minor | prd.md | NFR-002, NFR-004, PD-008 | Performance and availability targets are our proposals, not the client's. | Confirm at Gate 2. | prd |

## Checks run
- Every ID cited in one file exists in the file that defines it.
- Every story has an EPIC, a persona, a Traces line and at least one AC in Given / When / Then.
- Backlog ranks are unique and 1 to 29; every MVP story's dependencies rank before it.
- Release effort in the backlog adds up to the estimate within rounding.
