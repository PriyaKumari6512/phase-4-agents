# Task Breakdown quality and context changes

The existing project inputs, backlog schema, output locations, gate workflow and pipeline commands remain
the interface. Task Breakdown now generates feature documents from validated structured decisions, uses a
compact environment-specific workflow, restricts helper ownership, and retains completed work with hashes.
Independent semantic review is still mandatory; structural validity and checkpoints do not approve a gate.

## Changes that apply automatically

- A feature helper supplies one canonical decision record through `speckit_write_feature`. Deterministic
  rendering creates compatible spec/tasks Markdown and applicable plans, research/decision records, data
  models, contracts, clarification records, validation guides and checklists. `feature.json` retains the
  decisions. Required detail must be preserved; custom templates and incompatible legacy sections use the
  existing Markdown workflow instead of a lossy conversion.
- `skills/workflow-adapter.md` replaces reading four generic upstream workflows on each feature. Upstream
  skills/license remain versioned references. Source facts, proposals and unresolved choices remain distinct.
  Shared foundations have one owner; enrichment fills affected/missing fields instead of restarting decisions.
- `source_context` returns compact settings/indexes and paged exact source text. Helpers still read all
  applicable requirements/global constraints. `backlog_view` retains full records and explicit pagination.
- Feature helpers have feature-owned filesystem writes and specification tools. Enrichers have assigned-epic
  views/updates, with no raw file writes or global build tools. JSON handoffs bind each helper to a registered
  feature/epic. Shared-input changes and global builds wait until active helpers finish.
- Helpers explicitly use the fast model for summarization. Effective default strong-model effort/temperature
  settings are honored. The writer/reviewer model choices themselves are retained.
- `speckit_feature_status` and `speckit_checkpoint_feature` retain completed feature generation across a failed
  parent run. Checkpoints include exact source/output hashes; helper checkpoints require the input digest
  read before generation. Full PRD/architecture changes conservatively invalidate reuse. Unrelated schedule
  fields and adjacent identical request retries do not invalidate generation/enrichment on their own.
- Review retry snapshots are scoped to Task Breakdown dependencies rather than unrelated stage outputs.
  `--resume-verification` reuses the business request rather than appending a new request.
- Duplicate story IDs are rejected; uncited stories cannot automatically claim every feature requirement;
  stale source manifests block review; task and story graphs are checked after bounded cycle repair.
- Automatic task-hour rollups conserve the story budget or reject impossible task/minimum combinations.
  Independent task estimates remain explicit overrides, with reconciliation warnings where totals differ.
- Existing constitution/template overrides are preserved. Engine-default policy provenance is identified
  separately. Edited generated files conflict instead of being overwritten; only unchanged obsolete files
  recorded in the renderer's ownership manifest are removed.
- Ordinary errors/cancellation during multi-file writes restore prior artifacts, including after a work-budget
  stop. This is error recovery, not a power-loss-atomic multi-file transaction.

## Run and recovery

Use the existing command with your configured environment:

```bash
uv sync --locked
uv run agent-engine phase4 orchestrate --project-name YOUR_PROJECT
```

No new ENV settings are required. Existing diagnostics settings still record the next run. Reports include
`stage_budget`; exact feature completion records live under `.engine-feature-jobs/`. Keep that engine-owned
directory with the project when resuming; it records completed generation, never human approval.

Older artifacts lack the new completion/provenance evidence and need a conservative refresh once. Subsequent
unchanged work is eligible for reuse. A scheduling-only change may require a cheap backlog rebuild to refresh
raw provenance while preserving feature work and valid enrichments.

Use the existing `--resume-verification` command with the exact original request after a verifier failure.
Changed relevant artifacts/settings reject that retry. Human gates still require their normal decisions.

## Optional shared work budgets

| Environment setting | Default | Meaning |
| --- | ---: | --- |
| `AGENT_ENGINE_BREAKDOWN_MAX_CALLS` | 1000 | Model calls, including helper and internal summarizer calls. |
| `AGENT_ENGINE_BREAKDOWN_MAX_INPUT_TOKENS` | 30000000 | Cumulative provider-reported input usage across calls. |
| `AGENT_ENGINE_BREAKDOWN_MAX_OUTPUT_TOKENS` | 2000000 | Cumulative provider-reported output usage. |
| `AGENT_ENGINE_BREAKDOWN_TIMEOUT_SECONDS` | 7200 | Shared invocation deadline; the existing per-pass timeout also applies. |
| `AGENT_ENGINE_BREAKDOWN_MAX_HELPERS` | 128 | Total helper launches across writer/repair work. |
| `AGENT_ENGINE_BREAKDOWN_MAX_SAME_HANDOFF` | 3 | Repeated identical normalized JSON helper handoffs. |

These generous safeguards are defaults, not recommended cost targets or measured optimal values. Token limits
are soft because concurrent requests may already be in flight and some providers omit usage. They are not a
currency spending cap. A stopped budget produces a partial result and retains completed work; it cannot approve
an incomplete backlog. The budget spans fresh writer, repair and verifier graphs within one CLI invocation.

## Validation and scope

Regression coverage targets Task Breakdown: rendering/parser round trips, source fidelity, completeness,
rollback/drift, helper ownership, scoped reuse, effort settings and work-budget failure paths. A controlled local
integration covers structured feature generation through backlog enrichment and deterministic review readiness.
It does not assert that generated prose is semantically correct; the independent reviewer remains responsible.

No solver/scanner redesign, new framework, embedding service, or broad numerical optimization is included.
Actual token savings, latency and model quality must be compared in the next real run using identical inputs
and effective model settings. Fewer tokens alone is not success if requirement coverage or task quality declines.
