# Benchmark runbook: one real Phase 4 generation run with diagnostics

For the operator. PowerShell, Windows, this checkout. Nothing here publishes, dispatches coding agents or applies
infrastructure. Each `orchestrate` that runs a stage makes paid model calls with your existing models and
credentials; nothing else about models, prompts, validators, solvers or concurrency changes.

## 0. One-time preparation

```powershell
$WT  = "C:\Users\admin\Desktop\agent-sprint-planner\phase4-agent-engine-perf"     # instrumentation worktree
$ORG = "C:\Users\admin\Desktop\agent-sprint-planner\phase4-agent-engine"          # your original checkout
$PY  = "$WT\.venv\Scripts\python.exe"
```

* **Credentials.** The engine loads `.env` from its own folder, and the worktree has none. Link (not copy) your
  existing file so there is still one copy of the secrets; `.env` is git-ignored in the worktree too:

  ```powershell
  New-Item -ItemType HardLink -Path "$WT\.env" -Target "$ORG\.env"
  ```

  Remove it later with `Remove-Item "$WT\.env"` (that removes only the link; your original stays).
* **Python.** `uv` is not on this machine's PATH. `$WT\.venv` reuses the packages already installed in
  `$ORG\.venv` (read-only, via a `.pth` file) with the worktree's source first. Use `& $PY -m agent_engine ...`.
* **Infrastructure checks need Docker.** Start Docker Desktop, then check the sandbox image exists:

  ```powershell
  docker image inspect phase4/iac-sandbox:dev --format "{{.Id}}"
  ```

  Without the daemon or the image the infra stage falls back to locally installed tools; missing tools are
  reported as `tool_unavailable` and the manifest says `validation_complete: false`. That is a different code
  path from a Docker run: record which one you benchmarked.
* **Allocation solver.** `PHASE4_ALLOCATION_SOLVER_MODE` in `.env` decides Timefold vs local CP-SAT (`auto`
  uses Timefold only if `PHASE4_ALLOCATION_SOLVER_URL` answers). They are different solvers; the summary
  records which one ran and why.

## 1. A fresh workspace from the project's real inputs

The orchestrator treats existing outputs as up to date, so a run against `$ORG\outputs\clinic-test-2` would do
almost nothing. Start from the inputs only. For `clinic-test-2` they are `prd.md`, `architecture.md` and
`phase4/project.json` (it has no `history.json`, `skill-profiles.json` or `agent-outcomes.json`). Generated
state (`specs/`, `backlog/`, `sprint/`, `allocation/`, `infra/`, `gates/`, `requests/`, `runs/`, `logs/`,
`report.json`) and approvals are deliberately **not** copied: every gate is decided again by a human.

```powershell
$P     = "clinic-test-2"
$SRC   = "$ORG\outputs\$P"
$BENCH = "C:\Users\admin\Desktop\agent-sprint-planner\perf-bench\run-1"     # outside both repositories
New-Item -ItemType Directory -Force "$BENCH\outputs\$P\phase4" | Out-Null
Copy-Item "$SRC\prd.md", "$SRC\architecture.md" "$BENCH\outputs\$P\"
Copy-Item "$SRC\phase4\project.json" "$BENCH\outputs\$P\phase4\"
```

The project name stays `clinic-test-2`, so prompts and paths the agents see are the same as before; only the
host folder differs (recorded in the manifests).

## 2. Turn diagnostics on (this shell only)

```powershell
cd $WT
$env:AGENT_ENGINE_OUTPUTS_DIR   = "$BENCH\outputs"
$env:AGENT_ENGINE_LOGS_DIR      = "$BENCH\logs"
$env:AGENT_ENGINE_PERF          = "1"
$env:AGENT_ENGINE_PERF_SESSION  = "clinic-fresh-run1"
$env:AGENT_ENGINE_PERF_MODE     = "generation"     # publish commands are refused while this is set
$env:PHASE4_PR_MODE             = "local"          # belt and braces: no GitHub writes even if publish ran
```

Environment variables set here win over `.env` (dotenv does not override them). Diagnostics land in
`$BENCH\logs\perf\clinic-fresh-run1\`, outside the project folder the agents can read.

Dry check, no model calls (expect `RUN` for task-breakdown and infra-pipeline, exit code 2):

```powershell
& $PY -m agent_engine phase4 orchestrate --project-name $P --plan; "exit=$LASTEXITCODE"
```

## 3. The run, with its human approvals

```powershell
& $PY -m agent_engine phase4 orchestrate --project-name $P --sprint 1; "exit=$LASTEXITCODE"
```

Exit `2` = waiting for a human at a gate (expected after task-breakdown and infra-pipeline, then after
sprint-planning, then after work-allocation). `1` = a stage failed or was rate-limited: stop and go to
section 5. `0` = all four stages done and approved.

At each stop, review the files it names, then record your decision exactly as you normally would (approver and
submitter must be different people), e.g.:

```powershell
& $PY -m agent_engine gate P4-G1 --project-name $P --decision approved --approver "<your name>" --submitted-by "<submitter>"
& $PY -m agent_engine gate P4-G4 --project-name $P --decision approved --approver "<your name>" --submitted-by "<submitter>"
& $PY -m agent_engine phase4 orchestrate --project-name $P --sprint 1; "exit=$LASTEXITCODE"
```

Repeat for P4-G2 and P4-G3. Do **not** add `--publish`. Do **not** use `--test-approve` on this real project.

**Correlation across stops.** Every command above carries `AGENT_ENGINE_PERF_SESSION`, so all of them land in one
session. Each `orchestrate` gets its own pipeline id (one attempt), each stage child its own invocation id, and
the child's events hang under the orchestrator span that started it. Human waiting is measured from the
`approval_wait_start` the orchestrator records when it stops to the `gate_decision` the `gate` command records.
If you continue in a new PowerShell window, set the same six variables again first. A decision recorded any
other way (another tool, another session) is matched only through the approval record's `decided_at` (1 s
resolution); a wait with no decision evidence is reported as not measured.

## 4. Summary

```powershell
& $PY -m agent_engine perf summarize --session clinic-fresh-run1
```

Writes and prints `$BENCH\logs\perf\clinic-fresh-run1\summary.md` (and `summary.json`). It works on partial
sessions too, so run it after any stop.

Where everything is:

| What | Where |
|---|---|
| Events (one file per process) | `$BENCH\logs\perf\clinic-fresh-run1\events\*.jsonl` |
| Full sandbox command output (redacted) | `...\clinic-fresh-run1\raw\` (file names in the summary's infrastructure and failure tables) |
| Provenance manifests | `...\clinic-fresh-run1\manifests\pipeline-*.json`, `invocation-*.json` |
| Diagnostics problems | `...\clinic-fresh-run1\INCOMPLETE-*.txt` (absent when complete) |
| Generated artifacts | `$BENCH\outputs\clinic-test-2\` |
| Per-stage report and changed files | `$BENCH\outputs\clinic-test-2\runs\<job-id>\` and `report.json` |
| Transcript per stage | `$BENCH\outputs\clinic-test-2\logs\<job-id>.log`; global `$BENCH\logs\deepagent.log`, `app.log` |

## 5. If something fails

Keep everything: do not delete `$BENCH`, do not rerun straight away.

1. `perf summarize` and read "Failures and incomplete work": failed spans with category, sanitized error and raw
   output file; spans that never ended; diagnostics problems.
2. The stage row's outcome and `report_problem` (e.g. "report.json is not from this invocation") and its verdicts
   (gap counts, inconsistent verdicts).
3. `$BENCH\outputs\clinic-test-2\runs\<job-id>\report.json` for the validator's gaps and passes, the job log for
   the transcript, `phase4\orchestrator-state.json` for what the orchestrator recorded.
4. For infrastructure: `infra\checks.json` (each check's `outcome`), `infra\manifest.json`
   (`validation_complete`, `checks_incomplete`) and the matching `raw\` files.
5. Previous valid artifacts stay where they were: a sprint solve that ends UNKNOWN or MODEL_INVALID no longer
   overwrites `sprint-plan.json` (an INFEASIBLE result is still written, with its verified options, as before),
   and each run's changed files are copied to `runs\<job-id>\files\`.

Do not change models, constraints, checks or approval rules to get past a failure; investigate first. A rate-limit
stop (`SUBSCRIPTION_RATE_LIMITED`) resumes with the same `orchestrate` command later; its waiting time sits
between invocations and is reported as unexplained, not as active time.

## 6. Back to normal

```powershell
"AGENT_ENGINE_PERF","AGENT_ENGINE_PERF_SESSION","AGENT_ENGINE_PERF_MODE","AGENT_ENGINE_OUTPUTS_DIR","AGENT_ENGINE_LOGS_DIR","PHASE4_PR_MODE" |
  ForEach-Object { Remove-Item "Env:$_" -ErrorAction SilentlyContinue }
```

(or close the window). With `AGENT_ENGINE_PERF` unset, nothing is recorded.

## 7. Repeating the benchmark correctly

A second case is a **new** workspace from the **same** inputs and a **new** session id:

```powershell
$BENCH = "C:\Users\admin\Desktop\agent-sprint-planner\perf-bench\run-2"
New-Item -ItemType Directory -Force "$BENCH\outputs\$P\phase4" | Out-Null
Copy-Item "$SRC\prd.md", "$SRC\architecture.md" "$BENCH\outputs\$P\"
Copy-Item "$SRC\phase4\project.json" "$BENCH\outputs\$P\phase4\"
$env:AGENT_ENGINE_OUTPUTS_DIR = "$BENCH\outputs"; $env:AGENT_ENGINE_LOGS_DIR = "$BENCH\logs"
$env:AGENT_ENGINE_PERF_SESSION = "clinic-fresh-run2"
```

Then sections 2–4 again, with fresh human approvals (never copy `gates\`). Rerunning `orchestrate` on run-1's
completed folder is a no-op, not a faster run. Re-running one agent with feedback on an existing workspace is a
different case (incremental feedback); label it as such.

Things that differ between runs even with identical inputs, so record them next to each result:

* **Date.** Sprint windows and capacity are computed from the UTC date (`as_of`); `clinic-test-2`'s first
  sprint starts 2026-11-16, so a run on another day can plan different sprints.
* **Caches.** The Docker plugin-cache volume and its state, Python bytecode caches, the OS file cache, and the
  provider's prompt cache (visible as cache-read tokens per call) can all be warmer on a second run. The pipeline
  manifest records what it can observe (`caches`); neither run is automatically "cold" or "warm".
* **Solver ties.** Multi-worker CP-SAT can return different, equally scored placements; the local allocation
  solver does so even with diagnostics off. Compare objective, status and assigned sets, not exact assignees.
* **Models.** The same prompts can produce different specs, estimates and numbers of fix passes.
