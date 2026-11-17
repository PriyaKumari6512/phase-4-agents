# Resume completed work without restarting generation

The existing orchestration command now selects recovery automatically:

```bash
uv run agent-engine phase4 orchestrate --project-name YOUR_PROJECT --parallel-independent
```

For an unchanged stage it resumes the saved review or targeted repair, or waits at the gate when review is
already complete. A failed stage does not prevent independent runnable stages from retaining their results.
Dependent stages still wait for their required gates; unresolved findings and human decisions are not approvals.

## What is saved

- `.engine-recovery/<agent>.json`: generated, checked, review-pending, repair-pending/running,
  awaiting-decision or verified boundary, with input/artifact identity, original request and gaps.
- `.engine-recovery/artifacts/`: byte-checked output snapshots. Unchanged revisions reuse a snapshot.
- `.engine-recovery/interrupted/`: edits retained from an interrupted repair before restoration/retry.
- Existing `.engine-feature-jobs/` records: completed Task Breakdown feature work. Parallel merge validates
  registered checkpoint filenames/output hashes and permits them only from Task Breakdown.
- `.engine-pending-merge.json`: points to a retained parallel session until orchestration records its outcomes.
- `logs/parallel/<session>/merge-plan.json`: child requests, original file hashes, merge intent and commit state.
  Each child has its own durable result/inventory. Child roots and a before-merge copy remain available.

Keep the project and its corresponding logs/session directories when resuming on another machine. These contain
project data; retain them as recovery evidence. They are not published domain artifacts or human approvals.
Do not edit their hashes to force reuse. Automatic retention/deletion of these backups is intentionally absent.

## Recovery behavior

| Interruption | Next operation |
| --- | --- |
| Writer completed, reviewer failed or process stopped | Current deterministic checks and reviewer; no initial writer. |
| Empty, JSON-invalid or schema-invalid verdict | One bounded fresh review attempt; then retain review-pending state. |
| Reviewer model/instructions or runtime parsing code changed | Re-review retained generation, provided generation inputs/artifacts still match. |
| Real gaps remain after bounded repairs | Await a decision; preserve artifacts/gaps. A different evaluator may recheck non-human blocks, but cannot clear a recorded human decision automatically. |
| Process stopped during repair | Validate the prior snapshot and unchanged inputs, retain interrupted edits, restore saved artifacts and retry only repair. |
| One parallel child finished, another interrupted | Reuse the finished child's recorded result; resume only the unfinished child. |
| Merge failed or process stopped partway through file replacements | Validate retained outputs and replay the merge, without model calls for completed children. |
| Merge committed but orchestration state was not saved | Record the retained outcomes and continue to the next required boundary. |
| Inputs changed | Regenerate/rebuild affected work using existing feature reuse where valid. |
| Unexpected output edits or corrupt recovery metadata | Stop with artifacts retained; require explicit review/conflict resolution instead of silently regenerating or overwriting. |

Current deterministic checks always precede a new semantic review. A completed review is reused only when
source/artifact bytes and its evaluation identity remain unchanged. Provider/runtime failures do not approve
anything. Changing a reviewer does not make previously generated artifacts conform automatically.

## Explicit commands

Resume one stage using the exact original request recorded in its report:

```bash
uv run agent-engine run 'EXACT ORIGINAL REQUEST' --agent task-breakdown --project-name YOUR_PROJECT --resume
```

The existing `--resume-verification` option remains available to force a fresh review of unchanged saved work.
These Phase 4 checkpoints permit reviewer/runtime fixes while retaining generation. Relevant source/output or
generation-instruction changes still invalidate strict reuse. Older generic packs retain conservative checks.

After inspecting manual output corrections, explicitly review the current artifacts without initial generation:

```bash
uv run agent-engine run 'EXACT ORIGINAL REQUEST' --agent task-breakdown --project-name YOUR_PROJECT --review-existing
```

This performs deterministic checks and independent review. Remaining gaps can still cause targeted fixes within
the existing repair limit. It does not waive checks or approve a gate. Use `--agent infra-pipeline` for retained
infrastructure output; unresolved security/budget choices still need their normal decisions.

Recover a named retained parallel session, including an older run without a merge journal:

```bash
uv run agent-engine phase4 recover-parallel --project-name YOUR_PROJECT --session logs/parallel/SESSION_ID
```

Use the actual configured logs directory if different. This command makes no model calls. Older sessions require
completed child reports, unchanged shared inputs, and absent/identical current owned outputs. Conflicting newer
edits are not overwritten. Partial results stay partial. Then run the usual orchestration command.

## Limits and validation

Recovery depends on retained files and working storage. This is replayable filesystem recovery, not a distributed
or power-loss-atomic transaction. External publishing behavior is unchanged; this does not promise exactly-once
GitHub/tracker side effects. In-flight failed model responses can still incur cost; completed checkpoints avoid
repeating their preceding work. Source changes legitimately require new work.

Targeted failure-injection tests exercise malformed/empty verdicts, changed reviewer configuration, review/repair
interruptions, backup corruption, finished-child retention, merge errors, process-crash replay, source conflicts,
legacy imports, checkpoint ownership and unchanged gate behavior. The full pipeline suite is not required to
exercise these paths; no real API run is claimed by those tests.

Validation for this update: **154 affected tests passed** (139 recovery/stage/harness/history regressions and
15 report-integrity/diagnostics cases). Full pipeline, Java, policy and image-build suites were not run.
