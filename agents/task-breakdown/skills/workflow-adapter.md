# Task Breakdown adapter for spec-kit 1.3.0

This is the applicable workflow for this engine. It preserves the bundled upstream skills and MIT license
under skills/ for reference and upgrades; do not read all four generic skills on each feature job.
No shell, git branch management, extension hooks, waiting clarification UI or unsourced external research
is available here. Read an upstream section only if a concrete requirement cannot be resolved here.

1. Call speckit_feature_status before work and retain input_sha256; reuse only a checkpoint with reusable=true.
   Use source_context indexes/settings and exact source pages, keeping source hashes consistent across pages.
   Read the assigned PRD requirement sections, applicable global PRD constraints, architecture constraints,
   project settings, approved .specify/memory/constitution.md, request changes and shared
   backlog/implementation-contract.md. Cite original requirement IDs. Follow source precedence in the
   task; surface conflicts rather than silently choosing one. Reuse foundation owners and existing paths.
2. Specify independently testable user journeys with P1/P2/P3 priorities, real roles/benefits, Given/When/Then
   acceptance scenarios, source-linked functional requirements, relevant error/boundary cases and measurable
   success criteria. Do not invent metrics or security/product choices to make the document look complete.
3. Plan within the approved architecture. Preserve applicable data models, interface contracts and validation
   guide. Consolidate source-backed decisions once. Label every additional choice source/proposal/unresolved;
   source status requires a source reference, while proposals remain review questions. Research.md records
   these decisions and their evidence, not a claim that external research occurred. Resolve constitution or
   source conflicts explicitly. .specify/engine-policy.json identifies engine defaults requiring review.
4. Define concrete implementation work by story, including testing required by approved policy. Setup,
   foundational and polish work is included only when newly owned by this feature; otherwise record shared
   prerequisites. Each task has a stable ID, explicit files when known, actual predecessors and a [P] marker
   only for independent work. Preserve IDs on updates. Do not create duplicate shared foundations.
5. Call speckit_write_feature(project, feature_directory, document) once with the complete structured
   decisions below. The tool validates schema, IDs, PRD references, dependency DAG and parser compatibility
   before publishing spec.md/tasks.md, plan.md, research.md, applicable data-model.md/contracts, quickstart.md,
   clarifications.md and a quality checklist. It also writes feature.json as the canonical decision record.
   It cannot certify semantic correctness. Missing/invalid fields return an error; correct those fields and
   retry once. Stop and return remaining errors after the second failed write instead of starting over.
6. Review the rendered artifacts for genuine requirement coverage, source fidelity, testability, ambiguity,
   duplicate work, missing tasks, policy conflicts and cross-document consistency. Repair identified HIGH or
   CRITICAL issues once, preserving unaffected records. Call speckit_check_feature and checkpoint only after
   successful structural checks, passing the starting digest as expected_input_sha256 to
   speckit_checkpoint_feature. Changed inputs invalidate completion. Keep unresolved semantic findings and assumptions visible in the receipt.

## Structured document fields

Required: title, summary, stories, requirements, phases, validation_steps, success_criteria.
- stories: [{number:1,title,priority:"P1",as_a,i_want,so_that,source_ids:["FR-1"],
  acceptance:[{given,when,then}]}]. Story text/scenarios are single-line strings. Source IDs are original PRD IDs.
- requirements: [{number:1,text,source_ids:["FR-1"]}]. Numbers are local FR numbers, source_ids retain PRD identity.
- phases: [{kind:"setup"|"foundational"|"user_story"|"polish",story_number:1,
  tasks:[{task_id:"T001",description,file_paths:["src/example.py"],parallel:false,depends_on:["T002"]}]}].
  Only user_story phases have story_number. Every story needs its own task phase. IDs are unique within
  the feature. Put dependencies in depends_on, not prose; do not invent paths if source/plan leaves them unknown.
- validation_steps and success_criteria: lists of source-backed or explicitly proposed, testable statements.
Optional: technical_context:{label:value}, decisions:[{topic,status:"source"|"proposal"|"unresolved",decision,
  rationale,source_refs:[],alternatives:[]}], entities:[{name,fields:{field:constraint},relationships:[]}],
  interfaces:[{name:"short-name",description,status:"source"|"proposal"|"unresolved",source_refs:[]}],
  edge_cases:[], open_questions:[], shared_prerequisites:[]. Interface descriptions must retain applicable
  request/response/error behavior and data constraints; do not collapse a needed contract to a vague summary.
Use decision records for all unspecified numeric/security/technology choices; retain them in open_questions.
An unanswered decision remains unanswered even when a provisional proposal lets planning continue.

Read legacy Markdown-only features as they are; they remain supported. On conversion, retain their substantive
requirements, IDs, criteria, contracts, scenarios and decisions in the structured record. If a customized template
or legacy artifact needs sections this renderer does not represent, use the legacy write/edit workflow for that
feature, then run the same format and semantic checks. Do not overwrite it with a lossy conversion.
