# Gym (FitZone) — full Phase 4 pipeline test run, 2026-11-17

A test run of the whole Phase 4 pipeline (Task Breakdown, Infra & Pipeline, Sprint Planning, Work Allocation,
final G4, publishing) on the real gym project files and all 55 approved stories from Jira project GT
(read-only import). **Every gate approval here is an automated test approval, not a human sign-off.**
Publishing went to the local tracker (`tracker/`) and local PR folders (`publish/prs/`); nothing was written to
Jira or GitHub.

## Where things are

| Folder / file | What it is |
|---|---|
| `prd.md`, `architecture.md`, `designs/`, `api/`, `phase4/` | Inputs: PRD, architecture (ECS Fargate), designs (PRD section 6), API contract, project settings, imported stories |
| `backlog/` | Task Breakdown output: 55 stories → 174 tasks, 188 SP, 1,396 h |
| `infra/` | Infra & Pipeline output: intent, rendered OpenTofu/CI files, scanner results, `PR.md` |
| `sprint/` | Sprint plan: 10 sprints (MVP planned to finish 28 Feb 2027, due 31 Dec 2026) |
| `allocation/` | Sprint 1 assignments: 4 of 18 tasks assigned (team lacks ux-design and auth-security skills) |
| `gates/` | Gate decisions, including the test reviewer's decisions on GT-20, GT-29, GT-30, GT-42, GT-58 |
| `tracker/`, `publish/` | What publishing produced locally: 239 items, 207 links, 10 sprints, 2 PRs |
| `runs/`, `logs/`, `report.json` | Per-stage run reports (passes, models, tokens, time) and job logs |
| `pipeline-logs/run1.log` … `run-6.log` | Console logs of the six pipeline attempts |
| `test-only/accepted-checkov-risks.TEST-ONLY.yaml` | The checkov findings accepted only for this test; the real catalog accepts none |

## Cost and time (API-equivalent prices; the run used a subscription)

| Stage | Time | Model calls | Cost |
|---|---|---|---|
| Task Breakdown (fresh, Sonnet 5.5) | 316 s | 88 | $4.09 |
| Infra & Pipeline (Sonnet 5.5) | 152 s | 2 | $0.15 |
| Sprint Planning (Haiku 4.5 + one Sonnet fix) | 35 s | 4 | $0.05 |
| Work Allocation | 0.1 s | 0 | $0 |

A clean run: about 6 minutes and $4.40. All six attempts together: 288 calls, 23.4M input tokens (20.5M cached),
0.5M output tokens, about $12.96. The attempts stopped on pipeline defects that were fixed in commit `08a6d86`.
