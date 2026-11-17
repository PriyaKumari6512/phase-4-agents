# Task Breakdown execution and compatibility

Task Breakdown now uses an application-controlled workflow for compatible structured
features. Existing commands, source files, backlog schemas, specification paths,
Verdict shape and human gate remain the public contract. No downstream stage is
replaced. Engine-owned state is under `.engine-breakdown/` and is excluded from
public run artifact inventories. Parallel orchestration retains this state only
for Task Breakdown, with explicit path ownership checks.

## Execution

Python registers a typed feature partition, freezes the shared implementation
contract, schedules bounded feature jobs, builds the backlog, merges enrichment
patches, computes checks and dispatches independent review jobs. Models receive
schemas and prepared evidence rather than navigating files and scheduling helpers.
Feature jobs write the existing canonical record and existing rendered documents.
The backlog adapter reads a canonical record directly only when rendered artifacts
still match. Divergent/manual Markdown and customized project templates retain the
legacy writer/importer. They still use the bounded independent reviewer.

Evidence keeps exact source text. PRD sections whose IDs are explicitly unrelated
can be excluded; unclassified text and global constraints are always retained.
Architecture, requests and shared policies remain conservative global dependencies.
This intentionally avoids claiming complete semantic dependency inference. Changed
local PRD sections invalidate dependent features; changes to global dependencies
invalidate all affected features. Existing whole-stage integrity checks still apply.

Generation supplies typed enrichment patches. Task hours roll up using existing
Python rules. Valid retained enrichments take precedence over replayed generation
patches. Workers never concurrently mutate the backlog: patches merge after the
feature generation barrier. Scoped backlog pagination hashes selected records;
unscoped reads preserve raw-file snapshot semantics.

Review covers every requirement, every story/task partition, supporting Markdown
artifacts, and cross-feature contracts/ownership/dependencies. A job must explicitly
account for every assigned ID. Missing/failed partitions cannot approve the stage.
Review receipts bind exact evidence, records, rubric/schema and reviewer identity.
The public Verdict is assembled deterministically from retained findings. There is
no separate model call for verdict formatting. Review caches are never human approvals.

Repair receives complete structured findings. Field repairs are restricted to
identified records; structural coverage/story-size repairs regenerate affected
canonical features and preserve the remaining project. Unidentifiable owners,
legacy structural ambiguity, failed schemas and exhausted limits retain artifacts
without asserting successful completion. Normal recovery commands remain available.

## Limits

Existing stage call/token/deadline limits and callback usage accounting apply.
`AGENT_ENGINE_BREAKDOWN_JOB_MAX_CHARS` defaults to 160000 characters per operation;
this is an admission ceiling, not a token estimate. Oversized evidence returns
partial status rather than silently truncating requirements. Task reviews batch
12 task records; artifact reviews page 24000 characters with full source evidence.
`AGENT_ENGINE_BREAKDOWN_REVIEW_CONCURRENCY` defaults to 4. Feature concurrency uses
the existing helper setting (bounded at 32). Individual responses are capped at
16000 tokens or the lower provider limit. `AGENT_ENGINE_BREAKDOWN_REVIEW_RESERVE`
defaults to 0.2 of stage admission budgets. Concurrent in-flight calls can overshoot
reported-token limits; missing provider usage cannot be charged. All remaining
work is cancelled and awaited if a sibling job fails.

These defaults are bounded starting policies, not measured optima. This change
uses no historical result artifacts and makes no measured speed/cost claim.
Smaller model cascades, reasoning tuning, additional judges, vector retrieval,
fine-tuning and a framework migration are not enabled without quality evidence.

## Verification

Run `uv run python -m pytest -q`. Tests exercise direct/legacy record equivalence,
manual-edit preservation, unchanged generation/review reuse, incomplete review
rejection, internal-state exclusion, scoped pagination and failure recovery without
paid model calls. Fresh provider evaluations are still needed for semantic quality,
provider-specific response limits, latency and billed cost. Compare identical input
bytes across fresh generation, unchanged resume and a local requirement edit.
