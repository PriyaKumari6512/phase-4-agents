# Phase 4 alignment verification

Local verification on 2026-11-17, branch feat/task-breakdown-from-approved-stories. Work Allocation and Infra were completed and pushed separately before integration. Existing contracts, solvers, catalog rendering and dispatch adapters remain the architecture.

## Decisions applied

Keep missing paths/questions as AI blockers. Route structured security, payment and architecture signals to humans; allow configured human-only components. Record AI owners in tracker comments. Move dispatch behind an explicit Phase 5 command. Add qa and retain stg. Use trunk-based development, digest GitOps promotion and AWS-only catalog support. Retain checkpoint approvals and require final G4 before every publication path.

## Offline end-to-end run

Reproduce with `uv run python -m pytest -q -s tests/test_phase4_integration.py`. Eight file-source stories, two epics and two releases generated 24 tasks through the four real CLI stages, using fake models, fake scanner results and the local tracker. Approval identities are synthetic test fixtures, not human sign-offs. HTTP is blocked by tests/conftest.py.

| Stage | Local elapsed seconds |
|---|---:|
| task-breakdown | 0.163 |
| sprint-planning | 0.133 |
| work-allocation | 0.071 |
| infra-pipeline | 0.543 |

Observed fake-model calls: Task Breakdown 8 story calls + 1 cross-story call + 1 light review; Sprint Planning 1 annotation call; Infra 1 intent call; Work Allocation 0 calls because AI readiness was absent. These timings measure local orchestration and deterministic code only. Tokens, cache-read tokens and live cost are not measured by these fakes.

Assertions cover upstream preservation, release outputs, owner plans, four environments, local PR bundles and tracker writes, no Phase 4 dispatch, publication blocked before final G4, stale approval refusal and Phase 5 blocked without readiness. Separate tests cover degraded Argo evidence, promotion digest mismatch, shared-image updates, cache reuse, checked retries, independent capacity, risk signals and no deep agent construction for Work Allocation.

Final validation: **393 tests passed**. Targeted lint passes for the new and changed stage/publishing modules; repository-wide lint still reports older unrelated findings.

## Remaining deployment verification

No Jira writes, paid model requests, GitHub PR creation, provider dispatch or infrastructure apply were performed. The live GT run still requires explicit authorization and deployment credentials/configuration. GR remains untouched. Real scanner execution, GitHub App permissions/protection rules, Atlantis apply and Argo operational state remain unverified here. CI and GitOps placeholders must be configured before deployment.

Provisional budgets now bound every structured stage. Production token limits and concurrency are intentionally not calibrated from fake usage; tune after the authorized live run using measured calls, tokens, cache reads and latency. The live portion of handoff 03 remains outstanding for that reason.
