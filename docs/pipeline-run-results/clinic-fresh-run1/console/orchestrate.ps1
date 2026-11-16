param([switch]$Plan, [switch]$TestApprove)
# -TestApprove: the operator chose automated TEST approvals for this disposable benchmark copy (recorded as
# "NOT a human sign-off"); publishing stays refused (AGENT_ENGINE_PERF_MODE=generation).
# Benchmark run-1 of clinic-test-2 with diagnostics on (docs/PERF_BENCHMARK_RUNBOOK.md).
$WT    = "C:\Users\admin\Desktop\agent-sprint-planner\phase4-agent-engine-perf"
$BENCH = "C:\Users\admin\Desktop\agent-sprint-planner\perf-bench\run-1"
$P     = "clinic-test-2"
$env:AGENT_ENGINE_OUTPUTS_DIR  = "$BENCH\outputs"
$env:AGENT_ENGINE_LOGS_DIR     = "$BENCH\logs"
$env:AGENT_ENGINE_PERF         = "1"
$env:AGENT_ENGINE_PERF_SESSION = "clinic-fresh-run1"
$env:AGENT_ENGINE_PERF_MODE    = "generation"
$env:PHASE4_PR_MODE            = "local"
Set-Location $WT
$args2 = @("-m", "agent_engine", "phase4", "orchestrate", "--project-name", $P, "--sprint", "1")
if ($Plan) { $args2 += "--plan" }
if ($TestApprove) { $args2 += "--test-approve" }
& "$WT\.venv\Scripts\python.exe" @args2
"ORCHESTRATE_EXIT=$LASTEXITCODE"
