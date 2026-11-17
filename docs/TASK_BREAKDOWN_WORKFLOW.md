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
this is a routing threshold, not a token estimate. Oversized evidence is routed to
lossless paged execution rather than truncated. Task obligations are formed in
groups of 12 records and then batched with related
review obligations; artifact pages retain exact source evidence.
`AGENT_ENGINE_BREAKDOWN_REVIEW_CONCURRENCY` defaults to 4. Feature concurrency uses
the existing helper setting (bounded at 32). Individual responses are capped at
16000 tokens or the lower provider limit; larger outputs are assembled incrementally.
`AGENT_ENGINE_BREAKDOWN_REVIEW_RESERVE`
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

## Completion and preservation update

Oversized operations now enter `paged_operation.py` automatically instead of
raising a size-exhaustion error. Inputs are serialized losslessly into exact pages;
output is assembled incrementally by JSON path and validated against the original
schema. Source-page coverage is checked in code. Both input access and partial
output survive transcript compaction. Resume receipts bind the complete payload,
schema, instructions and selected model. Response parsing/length failures also
enter this path, so large outputs do not require fitting one response. Transport
errors retain the existing model escalation behavior. Ordinary calls still use
the direct structured-response fast path.

The paged worker has only five local operations: read input, read schema, read
output, edit retained output, and complete. It cannot run shell commands, write
public artifacts or approve gates. Only the caller publishes a fully validated
result. Paged execution continues under normal pass/stage deadlines and accounting;
size is no longer a termination condition. A provider outage, exhausted execution
budget, invalid result or incomplete semantic review still cannot be reported as
successful completion. Retained receipts allow work to resume.

Evidence is frozen per generation/review/repair operation, and source changes
before completion invalidate the result. Project settings and estimation history
are read from that same frozen view. The parent publishes the shared contract
before feature jobs start. Existing public source and artifact formats are unchanged.

Generation now fills missing/invalid fields on partially enriched items without
overwriting retained valid fields or story effort allocations. Structural repairs
restore unaffected canonical stories, phases, requirements and decisions before
publication; unchanged records recover their valid enrichment after rebuild.
Multi-feature structural repairs and field-patch batches roll back public files
on ordinary failure or cancellation. Source/output hash checks prevent acceptance
of a checkpoint whose files were rolled back. Existing byte-level writer
transactions still protect each published feature. A machine crash can leave
partial artifacts, which must pass the existing recovery/integrity checks.

Semantic review obligations are packed into evidence-sized batches. Exact source
sections are shared once within each batch and each obligation retains explicit
source references and required IDs. The aggregate verdict still requires every
obligation; it does not approve a sample. Cross-feature review includes task scope,
criteria, paths and dependencies in addition to stories and contracts. Dependency
analysis is cached against its complete input and selected model/instructions,
including the post-application identity for unchanged reruns.

The configured pack's current model tier and escalation level now apply to each
operation. Review receives the configured validator prompt and original request,
including imports without a request-history file. No model downgrade is introduced.
`AGENT_ENGINE_BREAKDOWN_REVIEW_BATCH_CHARS` defaults to 64000; the existing job
ceiling remains the direct-call/paged-call routing threshold. Paged input reads are
12000 characters, with schema pages and output continuation available as needed.

New tests cover lossless multi-page input/output and resume, mandatory read/schema
completion, tool-driven paged execution, reduced duplicate serialized evidence,
field-level enrichment retention, structural repair rollback, unaffected-story
preservation, model selection, frozen-input invalidation, and dependency reuse.
The evidence-batching test measures serialized input reduction on a controlled
fixture, not billed tokens. Live-provider quality and cost comparisons remain
necessary before claiming a measured performance gain.
