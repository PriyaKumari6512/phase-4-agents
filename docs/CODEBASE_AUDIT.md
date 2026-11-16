# agent-engine / PDLC Phase 4: technical audit

**Date:** 2026-11-13
**Scope:** the whole repository at `phase4-agent-engine/`. That covers the tracked engine and the untracked Phase 4 work: `src/agent_engine/**`, `agents/**`, `services/**`, `tests/**`, `docs/`, `examples/`, `docker-compose.yml`, `gates.toml`, `pyproject.toml`, plus the run artifacts in `outputs/`, `runs/` and `logs/`.

**Method:**
- Read every Python module, agent pack, prompt, template, policy and config.
- Traced the installed `deepagents 0.7.14` and `langchain_anthropic` code where behaviour depended on it.
- Ran the test suite: 125 passed in 74 s, with no model calls.
- Ran two offline verification scripts against **temporary copies** of project data. Each is described where it is used.
- Mined the recorded run reports and timestamped job transcripts (`outputs/*/runs/*/report.json`, `outputs/clinic-test-2/logs/*.log`, `logs/app.log`) for measurements.
- Two parts of the review were delegated to sub-reviewers, and their key claims were spot-checked against code and logs:
  - the Java solver and services;
  - the per-turn log timing.
- Built nothing, called no model, tracker or registry, and modified no file other than this report.

**Evidence labels** used throughout:

| Label | Meaning |
|---|---|
| **[V]** Verified | Seen in code at the cited location, reproduced by an offline script, or measured in a recorded run artifact |
| **[P]** Potential risk | Plausible from the code; needs the validation named |
| **[R]** Recommendation | A justified change, with its trade-offs |
| **[U]** Unknown | Cannot be decided from the evidence available; what would resolve it is stated |

File references are relative to the repository root.

---

## 0. Executive summary

**What the system is.** It is a CLI (`agent-engine`) that runs one LLM agent per invocation. Four Phase 4 agents turn a PRD and an architecture document into a backlog, a sprint plan, task assignments and infrastructure-as-code:

| Agent | Turns into |
|---|---|
| Task Breakdown | backlog |
| Sprint Planning | sprint plan |
| Work Allocation | task assignments |
| Infra & Pipeline | infrastructure-as-code |

Each agent:
- is a `deepagents`/LangGraph agent on Claude Sonnet 5.5, using either an API key or Claude.ai subscription OAuth;
- has deterministic tools: spec-kit stand-in, CP-SAT, Monte Carlo, Timefold, a Jinja catalog and IaC linters;
- is judged by a second, read-only LLM agent (its "validator"), with up to 2 fix passes.

Human approval gates sit between agents, and a separate `phase4 publish` command pushes approved artifacts to trackers or GitHub.

**There is no pipeline orchestrator.** The ">1 hour" is the sum of separately launched CLI runs (`README.md:§7`, `docs/PHASE4.md`). Measured wall-clock per run:

| Project | Agent | Wall-clock | Input tokens | Output tokens | Result |
|---|---|---|---|---|---|
| clinic-test-2 | Task Breakdown | **1,328 s** | **20.5 M** | 0.70 M | success after 3 verify + 2 fix passes |
| clinic-test-2 | Sprint Planning (run 1) | 726 s | 4.3 M | 67 k | **partial** (2 fix loops exhausted) |
| clinic-test-2 | Sprint Planning (run 2) | 348 s | 2.1 M | 26 k | **fail**, subscription 429 |
| clinic-test-2 | Infra & Pipeline | **3,341 s** | 0.65 M | 12 k | **fail**, subscription 429 after 55 min, work lost |
| bookmarks-live | Infra & Pipeline (one run) | **373,662 s (~4.3 days)** | 1.66 M | 54 k | fail, "Connection error." |

All rows are **[V]**, from `outputs/*/runs/*/report.json`; section 3 has the full table.

**Where time and money go (ranked; section 3 has the evidence):**
1. **The agent loop re-sends its whole context on every tool call.** One Task Breakdown run used 20.5 M input tokens for 0.7 M output; 86% were cache reads. Cost and latency scale with the number of tool calls times the context size. The backlog the agents read is 1.7 MB of JSON (`outputs/clinic-test-2/backlog/backlog.json`).
2. **Every run pays for full LLM-agent validators and fix loops** (`src/agent_engine/cli.py:253-280`). Most of what the validators check is already computed by deterministic `*_check` tools.
3. **The subscription rate limit is exhausted and there is no resume.** Agents were launched concurrently, the quota ran out, and a 55-minute run was thrown away (`subscription_models.py:248-265`, `cli.py:221-239`).
4. **The LLM does iterative search the solver should do.** Clinic Sprint Planning took 3 human requests and about 2 hours and still saved an **empty, INFEASIBLE plan**. Re-solving offline shows a feasible plan, with every must-have before the hard deadline, existed once the agent's own 28 pins were removed (section 2.4).
5. **Infra validation dominates the Infra run.** It was **96.8% of the measured 55-minute run**, with the LLM only 2.6%. Two causes: about 13 sequential `docker run` invocations per `infra_validate`, and `tofu init` timeouts misclassified as network errors and retried (`phase4/sandbox.py:32-33, 58, 128-136`).
6. **Upstream grep defect.** A missing `rg` triggers deepagents' fallback, which turns `grep <file>` into `grep <parent dir>`. In Task Breakdown, 22 of 73 greps returned 644 K characters from unrelated files, including other agents' logs.

**Measured split of the largest run (Task Breakdown, clinic):**
- Write pass 69%, of which subagent fan-outs were 77%: 466 s for spec-kit, including about 157 s waiting on one straggler, and 239 s for enrichment.
- Verify and fix loop 31%.
- 347 LLM requests averaging about 59 k input tokens each.

**The most serious correctness and security defects (all [V]):**
- **The write guard can be bypassed.**
  - `/outputs/<p>/./gates/...` and, on Windows, `/outputs/<p>/Gates/...` pass the read-only check. The backend then resolves them into the real `gates/` folder, so an agent can forge a human gate approval.
  - `requests.md` and **every other project's** files are writable (`guardrails.py:35-40`, reproduced).
- **`phase4 publish infra` publishes whatever is on disk.** It never checks the per-file hashes recorded in the approved manifest (`publish.py:432-439`).
- **Infra "checks passed" can be true when no check ran.** If every check was skipped, `checks_passed` is still true (`infra.py:413`). The test suite asserts this behaviour (`tests/test_phase4_pipeline.py:231`).
- **Backlog edits are silently lost on rebuild:**
  - enrichments on split tasks (`backlog.py:198`);
  - partially applied updates (`backlog.py:254-319`).
  Both were reproduced.
- **The sprint solver reports "capacity" for everything when it times out.** On UNKNOWN or MODEL_INVALID status, every story is reported as "capacity"-deferred (`sprint.py:191-211`). The infeasibility "core" is not minimal: 80 of 80 switches in the clinic run.
- **No timeout or budget exists at run, request or tool level.** That allowed the 4.3-day run. The SDK request timeout is `None` (section 2.1).
- **Concurrent runs on one project corrupt each other's bookkeeping.** For example, one Sprint Planning run was charged with 673 "changed files" (section 2.1).

**The highest-value direction.** Keep the deterministic cores (solvers, parsers, catalog), which are the strongest part of the codebase. Change the execution model:
- replace open-ended agent loops with bounded, structured LLM calls where the task is a fixed workflow;
- make validators deterministic first and the LLM second;
- add run budgets, checkpoint/resume and a real orchestrator.

Fix the guard, gate-integrity and silent-data-loss defects **before** any performance work. They are small changes, and they protect the human-approval model that the whole design rests on.

---

## 1. Verified current architecture

### 1.1 Components

| Layer | Files | What it does (verified from code) |
|---|---|---|
| CLI and run loop | `src/agent_engine/cli.py`, `__init__.py` (loads `.env` at import) | `run`, `add-inputs`, `gate`, `list`, `phase4 …`. `_run()` records the request, runs the agent pass, runs the validator, then fix passes, then writes `report.json` and the run history. |
| Agent packs | `agents/<name>/agent.toml`, `system_prompt.md`, `validator/` | Declarative agents. `load_pack()` validates keys, tools, I/O files and subagents (`agent.py:131-225`). |
| Agent construction | `agent.py:228-274` | `create_deep_agent` with: the model; the composite backend; Phase 4 tools; summarization; the write guard and lock middleware; the general-purpose helper and named subagents; and `response_format=Verdict` for judges. **Rebuilt for every pass** (`cli.py:230`). |
| Backend (file access) | `backends.py` | `/outputs/` maps to the **whole** `OUTPUTS_DIR` (every project). `/knowledge/` and `/skills/` map to pack folders. Everything else is an in-memory `StateBackend`. No shell. |
| Safety middleware | `guardrails.py`, `locking.py` | Refuses writes outside `/outputs/` and into `inputs/`, `gates/`, `requests/` and `runs/`. Uses one global `asyncio.Lock` per process around `write_file`/`edit_file`. |
| Models | `model_setup.py`, `subscription_models.py`, `config.py` | Tier resolution (strong/fast) and retries (6). An OAuth subclass of `ChatAnthropic` injects a billing marker and fails fast on a 429 whose reset is more than 60 s away. Summarization triggers at 30% of the context window, argument truncation at 20%. |
| Gates | `gates.py`, `gates.toml` | Approval files pin the sha256 of the gated files. `stale_approvals()` is checked before a gated agent runs and before publishing. Maker-checker compares free-text names. |
| History and logs | `history.py`, `logging_setup.py`, `observability.py` | Hashes the whole project before and after a run and copies changed files to `runs/<job>/`. The global `logs/deepagent.log` holds the full transcript; per-job logs are relocated into the project. Langfuse tracing is optional. |
| Phase 4 tools | `src/agent_engine/phase4/tools.py` (21 tools, 9 factories) | Sync `@tool` functions. Errors are returned as text. Read-only `*_check` tools are given to validators. |
| Agent 1 core | `speckit.py`, `speckit_parse.py`, `backlog.py`, `textsim.py`, `skills_taxonomy.py` | Python stand-in for spec-kit's bash scripts. Parses `spec.md` and `tasks.md` into epics, stories and tasks. Keeps enrichments, TF-IDF analogies, DAG/coverage/size validation and the critical path. |
| Agent 2 core | `sprint.py`, `sprint_model.py`, `capacity.py`, `calendars.py` | Sprint windows and availability, Monte Carlo P50/P85 (cold start: person-hours × 0.7), WSJF, a CP-SAT packing model with assumption literals, "verified options" when infeasible. |
| Agent 3 core | `allocation.py`, `alloc_solver.py`, `profiles.py` | Hard AI-eligibility rules, skill levels (declared and mined), ownership affinity, Timefold REST client or local CP-SAT fallback, runner-up, post-checks. |
| Agent 4 core | `infra.py`, `sandbox.py`, `agents/infra-pipeline/knowledge/catalog/**` | Intent validation, Jinja rendering of OpenTofu/Argo/Helm/ExternalSecrets/alerts/Atlantis/CI, about 10 checks via `docker run` (or local tools), secret regexes, a risk score, `PR.md`. |
| Publishing | `publish.py`, `trackers/*`, `github_api.py`, `dispatch.py` | Gate-checked publishing to local files, Jira, Linear or GitHub. Exactly-once mapping file. Three-way merge of owned fields. AI dispatch to Copilot or Claude Code Action. PRs. |
| Services | `services/allocation-solver` (forked Timefold quickstart, Java/Quarkus), `services/iac-sandbox`, `services/atlantis`, `docker-compose.yml` | Optional. The solver listens on `:8080`. The sandbox is a tools image. The Atlantis image is not in compose. |

### 1.2 End-to-end execution (as implemented)

```
human: agent-engine phase4 init  (copies example inputs)          [no LLM]
human: agent-engine run "<req>" --agent task-breakdown  ─┐
         cli._run: load pack+validator → check inputs/gates → record request → fingerprint project
         pass "write": build_agent(strong) → astream → (LLM ⇄ tools)* → reply
              Task Breakdown: speckit_init → backlog_set_features → N× task(speckit-feature) [parallel]
                 each subagent: read 4 SKILL.md (51 KB) + templates → specify → plan → tasks → analyze → fix
              → backlog_build → M× task(backlog-enricher) [parallel] → backlog_update… → backlog_validate (loop)
         check declared outputs exist (any age)                    cli.py:246-248
         for attempt in 1..max_fix_loops+1:                        cli.py:253-280
             pass "verify": validator agent (strong) reads md/json + *_check tool → Verdict (structured)
             if !satisfied and attempt ≤ max_fix_loops: pass "fix" (full agent again, with gaps)
         save_run (fingerprint diff + copies) → report.json        cli.py:287-293
human: agent-engine gate P4-G1 --decision approved …               [no LLM]
human: agent-engine phase4 publish backlog                          [no LLM]
human: … sprint-planning → gate P4-G2 → publish sprint
human: … work-allocation (one sprint) → gate P4-G3 → publish assignments (AI dispatch)
human: … infra-pipeline (independent of 1-3) → gate P4-G4 → publish infra (PRs)
```

**Verified execution facts:**
- **[V]** Each pass constructs a new graph, model clients and middleware (`cli.py:230`, `agent.py:228-274`). `resolve_model_with_retries` is called 2–3 times per build. `_token_trigger` calls `init_chat_model` twice more only to read profiles (`model_setup.py:158-178`).
- **[V]** `astream(stream_mode="values")` emits the full state after every step. The CLI logs only *new* messages, by index (`cli.py:78-92`). Subagent transcripts are not streamed to the job log; only the main agent's messages are.
- **[V]** Parallel subagents depend on the model emitting several `task` calls in one message. Nothing enforces or bounds the fan-out. Phase 4 tools are sync, so LangChain runs them in a thread pool. Backlog read-modify-write is serialized with a process-wide `threading.RLock` (`backlog.py:54`). The sprint, allocation and infra tools have no lock.
- **[V]** The LangGraph recursion limit is 9,999 (`deepagents/graph.py:971`). The CLI sets no step, time or token limit.
- **[V]** Named subagents keep deepagents' default summarization, built on the *subagent's own* model. Only the main agent gets the engine's "fast-model summarizer" (`deepagents/graph.py:687-700`; `agent.py:246-262` passes no summarization for subagents). This contradicts the intent stated in `model_setup.py:184-188`.
- **[V]** Anthropic prompt caching is applied automatically by deepagents' `AnthropicPromptCachingMiddleware` (`deepagents/graph.py:905`, `middleware/_prompt_caching.py`). This matches the 85–90% cache-read ratios measured.

### 1.3 Data contracts and gates

- **[V]** All file formats are strict Pydantic models (`extra="forbid"`) in `phase4/contracts.py`. Tools re-validate on every read.
- **[V]** Gates: P4-G1 pins `backlog/backlog.json`. P4-G2 pins `sprint/sprint-plan.json`. P4-G3 pins `allocation/assignments.json`. P4-G4 pins `infra/intent.json` and `infra/manifest.json` (`gates.toml`).
- **[V]** Lineage between agents uses content hashes:
  - `SprintPlan.backlog_sha256` is checked by `sprint.check`.
  - `AssignmentPlan.sprint_plan_sha256` is checked by `allocation.check`.
  - `InfraManifest.intent_sha256` and the per-file `sha256` are checked by `infra.check`.
  - These checks run only inside validators, **not in publish** (see SEC-3).

---

## 2. Implementation assessment

Findings carry IDs used later by the plan. Severity: **Critical**, **High**, **Medium**, **Low**.

### 2.1 Engine, orchestration and run lifecycle

**ENG-1 (High) [V]: No run, request or tool budget.**
- `cli._run` has no wall-clock limit, token budget or max-steps.
- The LangGraph recursion limit is 9,999.
- `ChatAnthropic` is built without a timeout, and `langchain_anthropic` forwards `timeout=None` to the SDK client (`.venv/.../langchain_anthropic/chat_models.py:1117,1460-1461`).
- Measured: `outputs/bookmarks-live/runs/20261106-024932-9e7987/report.json` shows `elapsed_seconds: 373661.8` (4.3 days), ending in "Connection error."
- **[P]** A request with no timeout is the most plausible cause. Machine sleep is an alternative the logs cannot exclude.
- README §7 acknowledges "No per-run token budget or hard stop".

**ENG-2 (High) [V]: A failed run cannot be resumed; all work in it is lost.**
- Model errors propagate out of `run_pass`. With a single-model pack (every Phase 4 pack uses `model = "strong"`) the error is raised immediately (`cli.py:233-236`).
- There is no checkpointer (`create_deep_agent` gets none), and the conversation state lives only in memory.
- Measured: infra-pipeline `20261113-124253-8388c0` ran 3,341 s and then failed with `SUBSCRIPTION_RATE_LIMITED … resets in 12690s`.
- Files written so far remain on disk. The operator's fix was to re-issue "continue request 2 from scratch" (`outputs/clinic-test-2/requests/sprint-planning.md`, Request 3).

**ENG-3 (High) [V]: Concurrent runs on one project are unsafe, and the code does not detect them.**
- Nothing prevents two `agent-engine run` processes on the same project. The `asyncio` lock and the backlog `RLock` are per process.
- `history.fingerprint` attributes every file changed during the run window to the run. Measured: Sprint Planning `20261113-132439-115043` lists **673 changed files** while Infra (`124253`, running 12:42–13:38) was writing in parallel. Task Breakdown `124309` overlapped Infra too, and lists 176.
- Both concurrent runs then hit the shared subscription quota.
- **[P]** `requests.md` numbering (`cli.py:95-106`), `report.json` and `logs/` are also racy.

**ENG-4 (Medium) [V]: The declared-output check accepts stale files.**
- `_missing()` only tests existence (`cli.py:109-110, 246-248`).
- On a repeat run, an agent that writes nothing still "produces" its outputs from the previous run, and the validator is paid to judge stale work.

**ENG-5 (Medium) [V]: A validator failure ends the loop as "partial" with no retry.**
- This applies even when the cause is transient (`cli.py:261-269`).
- A missing structured response is treated the same way.

**ENG-6 (Medium) [V]: Model fallback is effectively off.**
- Escalation (`model = ["fast","strong"]`) exists, but no Phase 4 pack uses it.
- A 429 on the strong model therefore fails the run instead of waiting or switching provider.
- The subscription path raises `SubscriptionRateLimited` when the reset is more than 60 s away (`subscription_models.py:255-262`). That is good for not hanging, but nothing upstream schedules a retry.

**ENG-7 (Low) [V]: Each pass rebuilds the agent and up to 4 model objects, and calls `init_chat_model` twice only to read profiles.**
- See `agent.py:230-233`, `model_setup.py:166-178`.
- The cost is negligible next to LLM latency, so this is listed for cleanliness, not speed.

**ENG-8 (Medium) [V]: The transcript logger records full tool payloads at INFO level and is never rotated.**
- The global `logs/deepagent.log` is 9.2 MB after a few runs. Client PRD content is copied into a global, cross-project file.
- Per-job logs live in `outputs/<p>/logs/`, which **agents can read**. **[V, measured]** Task Breakdown ingested the concurrently running Infra agent's transcript through grep (ENG-10). An example is the `infra_set_intent` lines with grep line prefixes at `outputs/clinic-test-2/logs/20261113-124309-491381.log:9871`.
- `runs/` (repository root, 5.1 MB) and `clinic-test-2/` are untracked and **not git-ignored**. Only `outputs/` and `logs/` are ignored (`.gitignore`). Client data could be committed.

**ENG-10 (High) [V, code plus measured]: `grep` on a single file searches its whole parent directory.**
- ripgrep is not installed. J4a L1317 logs "ripgrep ('rg') not found on PATH; using Python grep fallback".
- deepagents' Python fallback sets `root = base_full if base_full.is_dir() else base_full.parent` (`.venv/Lib/site-packages/deepagents/backends/filesystem.py:1185`).
- As a result, `grep('FR-0', path='/outputs/clinic-test-2/prd.md')` returned `architecture.md` and `backlog.json` matches (J1 L2966-2967, about 80 KB).
- Across Task Breakdown, 22 of 73 greps escaped their path, 643,650 characters in all, some from **other agents' job logs** and `.terraform` folders.
- This is an upstream library defect triggered by an environment gap, so neither the prompts nor the tests catch it. It inflates context (section 3.2) and leaks cross-agent transcripts (ENG-8).

**ENG-11 (High) [V]: A failed or interrupted run leaves live artifacts broken.**
- Tools write artifacts in place on every call. When a run dies mid-way, the last intermediate version stays as the "current" artifact.
- Example: Sprint Planning `115043` was rate-limited and left `sprint/sprint-plan.json` at v22, INFEASIBLE and unannotated, replacing the usable FEASIBLE v16 plan from the previous run.
- The next run is told to "read your previous output and change only what is needed" (`cli.py:137-142`), so it starts from the broken state.
- Runs do not write to staging and promote atomically on success.

**ENG-12 (Low) [V]: Agents call tools that do not exist.**
- Sprint Planning called `bash` twice and the validator called `x` (J2a L1328, L2670, L2196). The errors come back as text and cost a turn each.
- This is a symptom of prompts written for shell-equipped agents: the spec-kit skills reference `.specify/scripts/bash/*.sh`.

**ENG-9 (Medium) [V]: Most of the codebase is not in version control.**
- All of Phase 4 (`src/agent_engine/phase4/`, four agent packs, services, tests, docs) is untracked.
- Engine changes are uncommitted (`git status`).
- CI (`.github/workflows/tests.yml`) therefore does not test any of it.

### 2.2 Guardrails, trust boundaries and security

**SEC-1 (Critical) [V, reproduced]: The read-only check can be bypassed, so an agent can forge a gate approval.**
- `_is_read_only` compares the second path segment literally (`guardrails.py:35-40`).
- Reproduced with `verify_defects.py` (Appendix A):
  - `/outputs/p/./gates/P4-G1.approved.json` gives `read_only=False`, `traversal=False`.
  - deepagents' `FilesystemBackend._resolve_path` then `.resolve()`s it to `<outputs>/p/gates/x.json` (`deepagents/backends/filesystem.py:203-212`).
  - On Windows (the development platform), `/outputs/p/Gates/...` also passes and resolves to the same folder, because NTFS is case-insensitive.
- `phase4/files._rel` has the same flaw: `./gates/x` is accepted for writes.
- Gate approvals are plain JSON with sha256 values the agent can compute (`gates.py:339-357`). A prompt-injected or confused agent could therefore approve its own output. That defeats the human-in-the-loop design.

**SEC-2 (High) [V]: There is no project isolation.**
- `/outputs/` maps to all projects (`backends.py:21`). The guard allows writes anywhere under `/outputs/` (`/outputs/other-project/prd.md` passes, reproduced).
- Validators can read every project.
- Tools take `project` as an argument chosen by the model (`phase4/tools.py`), so a tool call can write another project's backlog.
- `requests.md`, the history the validator trusts, is writable by the agent: it is a file, not a directory listed in `READ_ONLY_PROJECT_DIRS`.
- `report.json` is writable too.

**SEC-3 (High) [V]: Publishing does not verify the approved content.**
- `publish_infra` reads every file listed in the manifest from disk and pushes it (`publish.py:432-439`). It never compares them with `ManifestFile.sha256`.
- The gate only pins `intent.json` and `manifest.json`, so edits to `infra/repo/**` after approval are published as "Approved at P4-G4".
- `publish_assignments` uses the unpinned `backlog/backlog.json` for the dispatch brief.

**SEC-4 (High) [V]: Infra "checks passed" is true when nothing was checked.**
- `checks_passed = bool(checks) and all(c.passed or c.skipped …)` (`infra.py:413`). With every tool skipped (sandbox off, no tools), it is true.
- `infra.check` then reports `ok` (`infra.py:491`), and the validator prompt treats skipped checks as acceptable.
- The test suite asserts this: `assert v["checks_passed"] and len(v["skipped"]) == 10` (`tests/test_phase4_pipeline.py:231`).
- `docs/PHASE4.md` claims checks are "never reported as passed" when skipped. That is true per tool but false for the aggregate.

**SEC-5 (High) [P]: Generated IaC is executed on the host when Docker is missing.**
- `sandbox._run` falls back to `bash -c` on the host with the full environment (`sandbox.py:46-53`).
- `tofu init`/`validate` downloads and runs provider binaries, and module sources come from files the agent may `edit_file` (`agents/infra-pipeline/system_prompt.md` step 3).
- The input chain is LLM-generated: prd/architecture, then intent, then edits. A prompt-injected source could reach provider or module fetching.
- Docker mode has `--network bridge` with full egress, and no `--read-only`, `--cap-drop`, `--pids-limit` or memory limits (`sandbox.py:42-45`). This contradicts the Dockerfile comment "network limited to registries" (`services/iac-sandbox/Dockerfile:1`).

**SEC-6 (High) [P]: The AI-dispatch path carries LLM text into an agent with write permissions.**
- `phase4-claude.yml.j2` grants `contents: write`, `pull-requests: write`, `issues: write` and `id-token: write`. It passes `inputs.brief` straight into `claude-code-action` as the prompt.
- The brief comes from LLM-generated backlog text (`dispatch.brief_for`).
- The brief is passed as an action input, not into a shell, so there is no shell injection **[V]**. Prompt injection into an agent with repo write and OIDC is a real exposure **[P]**.
- `id-token: write` is unnecessary for this job.

**SEC-7 (High) [V, from the services review]: The allocation solver is unauthenticated on all interfaces.**
- `docker-compose.yml:8` maps `"8080:8080"`.
- `services/allocation-solver/src/main/resources/application.properties:57` forces Swagger on, and the quickstart UI is served at `/`.
- Anyone on the network can submit, read or cancel jobs.
- The runtime image runs as root.

**SEC-8 (Medium) [V]: Maker-checker is a free-text name comparison.**
- `_same_person` compares case-folded names (`gates.py:361-364`). Any other string passes, and there is no identity or authentication.
- This is acceptable for a CLI prototype and documented as interim, but it is not a control.

**SEC-9 (Medium) [V]: Supply chain.**
- Base images are tags, not digests.
- Tool binaries are downloaded without checksums (`services/iac-sandbox/Dockerfile:11-21`, `services/atlantis/Dockerfile`).
- The Atlantis image pipes an install script from an unpinned branch into `sh` as root.
- `pyproject.toml` uses `>=` ranges; `uv.lock` plus `uv sync --locked` in CI mitigates this.
- **[V]** The Atlantis image **cannot build**: `COPY policies/` refers to a folder that does not exist in `services/atlantis/`.

**SEC-10 (Medium) [P]: Atlantis config.**
- `services/atlantis/repos.yaml` matches every repository (`id: /.*/`) and autoplans PR code with server credentials.
- It POSTs the full plan JSON (which can contain sensitive values) with `curl --data "$body"`.
- No receiver for that webhook exists in `src/`.

**SEC-11 (Low) [V]: The subscription path depends on undocumented provider behaviour.**
- It injects a hard-coded "billing marker" system block and suppresses the `X-Api-Key` header (`subscription_models.py:236-238, 317-326`).
- This is fragile and may conflict with provider terms. **[U]** Whether this use is permitted for this deployment is a question for the account owner.

### 2.3 Agent 1: Task Breakdown

**TB-1 (High) [V, reproduced]: Enrichments on split tasks are discarded on every rebuild.**
- `build()` computes `stale` against items parsed from spec-kit *before* enrichments, and therefore before splits, are reapplied (`backlog.py:195-200`).
- Split parts (`001-T001a`) are never in `by`, so their acceptance criteria, skills and estimates are dropped.
- Reproduced: before the rebuild the part's ACs were `['WHEN x THE SYSTEM SHALL y']`; afterwards `[]`, with `enrichments_dropped_changed_items: ['001-T001a']`.

**TB-2 (High) [V, reproduced]: A partially applied update is saved to `backlog.json` but not to `enrichments.json`.**
- `_apply` mutates fields one by one and can fail later, for example on invalid story points (`backlog.py:265-319`).
- `update()` still saves the mutated backlog but records nothing in enrichments (`backlog.py:395-402`).
- The next `backlog_build` silently reverts the change. Reproduced: the description was changed in `backlog.json`, absent from `enrichments.json`, and reverted after the rebuild.

**TB-3 (Medium) [V]: Duplicate user-story numbers in a `spec.md` silently overwrite each other.**
- `stories[f"US{st.num}"]` (`backlog.py:129`).
- Tasks in a phase before the first `## Phase` heading are ignored silently (`speckit_parse.py:253-254`).

**TB-4 (Medium) [V]: Several rules exist only in the prompt, not in code.**
- "Never edit backlog.json with write_file". The guard does not protect tool-owned files.
- "Confidence < 0.6 → do not add the dependency". `backlog.update` accepts any confidence.
- The ai_eligible "≤ 4 h / ≤ 4 files" rule is enforced later by Agent 3's `hard_checks`, which is good, but not at the source.

**TB-5 (Medium) [V]: Parallel fan-out is model-dependent and unbounded.**
- Running N `speckit-feature` subagents in parallel depends on the model emitting N `task` calls in one message (`system_prompt.md` step 3).
- There is no concurrency cap, so 10 features means 10 simultaneous long-context agents against one rate limit.
- Each subagent reads about 51 KB of `SKILL.md` (`agents/task-breakdown/skills/*/SKILL.md`: 12,139 + 8,344 + 19,122 + 11,683 bytes) plus templates, which are returned *again* as JSON by `speckit_script resolve-template`/`setup-tasks`.

**TB-6 (Low) [V]: Validation has an O(n²) pure-Python duplicate scan.**
- It covers up to 1,500 tasks (`backlog.py:585-592`).
- `by_id()` is rebuilt for every update item (`backlog.py:255, 396`).
- At the measured scale of 484 tasks the cost is negligible. Listed only so nobody optimizes it first.

**TB-7 (Medium) [V]: The constitution and skill choices force a lot of output per feature.**
- spec-kit specify, plan, tasks and analyze, plus clarifications, produce spec, plan, research, data-model, contracts and tasks for every feature.
- Measured artifacts for clinic: 10 features, about 610 KB of `specs/**.md`, 484 tasks, a 1.7 MB `backlog.json` and a 576 KB `enrichments.json`.
- The downstream agents consume only `spec.md` and `tasks.md`, through the parser (`backlog.py:103-107`). Whether plan, research and contracts improve the task quality enough to justify their cost is **[U]**. See the verification strategy.

### 2.4 Agent 2: Sprint Planning

**SP-1 (High) [V, reproduced offline]: An infeasible plan is reported where a feasible one exists, and the options never surface it.**
- Clinic run: `outputs/clinic-test-2/sprint/sprint-plan.json` has `solver.status: INFEASIBLE`, `conflicting_constraints` listing **80** switches (every must, every pin and DL-1), 0 stories planned, and 79 deferred as `deadline_infeasible`.
- Re-solving the same model offline (`sprint_repro.py`, Appendix A, on a temporary copy):

  | Variant | Status | Stories planned |
  |---|---|---|
  | as saved | INFEASIBLE | 0 |
  | **only the 28 agent-created `pin:…->0` switches removed** (DL-1 hard and every must kept) | **FEASIBLE** | **78** |
  | DL-1 made soft | FEASIBLE | 51 |
  | every must dropped | INFEASIBLE | 0 |

- Must-have load is 201 SP against a P50 capacity of 236.1 SP in sprints 1–7.
- **Root causes:**
  1. `sufficient_assumptions_for_infeasibility()` returns a *sufficient*, not minimal, set (`sprint_model.py:173-179`), so the core is useless for guidance.
  2. `verified_options` only tries **single-switch** relaxations and stops after 4 successes (`sprint_model.py:193-223`). It never tried "drop all pins".
  3. The agent was instructed by Request 2 to pin, so it added pins that conflicted with DL-1 coverage.
- It took 3 human requests, about 2 h and 3 runs (one rate-limited), and the last saved plan is empty.

**SP-2 (High) [V]: Solver status UNKNOWN or MODEL_INVALID is not handled.**
- `placement = res.placement or {all: 0}` (`sprint.py:191`).
- Every story is then deferred with reason "capacity", which is false, and the plan is written as if valid.
- `SolverReport.status` allows `UNKNOWN` (`contracts.py:296`), but no consumer reacts to it.

**SP-3 (Medium) [V]: The hard-deadline semantics make "slip the fewest must-haves" impossible to express.**
- Musts and hard deadlines are all-or-nothing assumption literals (`sprint_model.py:111-114, 143-145`). The objective cannot trade one late must-have against another.
- This is why the operator had to iterate in natural language (Requests 2–3).

**SP-7 (Medium) [V, measured]: The solver is non-deterministic, and the LLM calls it repeatedly.**
- CP-SAT runs with 8 workers under a 10 s time limit (`sprint_model.py:167-168`). Identical arguments returned OPTIMAL in 1.4 s at one call and FEASIBLE in 10.9 s at another (J2a L3081 vs L3112).
- One run made 16 `sprint_solve` calls (154.8 s). Each call rewrote `sprint-plan.json` and bumped its version.
- Approvers can see different plans for the same inputs.
- **[R]** Fix the seed (`random_seed`), use `num_workers=1` or deterministic interleaving for the final solve, and make `solve` a pure function: the tool returns a candidate; only an explicit "accept" persists it.

**SP-4 (Low) [V]: Per-skill capacity is computed but never used.**
- `skill_hours` is computed per story (`sprint.py:170-173`), but `SprintIn.skill_caps` is never filled. The constraint at `sprint_model.py:123-125` is dead code.

**SP-5 (Low) [V]: Calendar APIs are called twice per plan.**
- `capacity_report` and `solve` both call `_windows` → `unavailable_days` (`sprint.py:48-53, 64-66, 131`).
- Failures are swallowed, so capacity silently ignores out-of-office days (`calendars.py:459-461`).
- The Graph organizer is `calendar_ids[0]` (`calendars.py:458`), which is questionable.

**SP-6 (Low) [V]: Stories in the same sprint as a dependency are allowed.**
- `sprint(A) <= sprint(B)` (`sprint_model.py:133`). This is a policy choice; confirm it with delivery managers.

### 2.5 Agent 3: Work Allocation

**WA-1 (High) [V]: Task dependencies are not enforced.**
- Timefold has no precedence constraint. Python approximates it with `minStartTimeInMinutes` from the DAG, using the unscaled estimate (`allocation.py:264-274`).
- On a cycle, `es` stays empty and every `min_start` becomes 0 silently.
- Local CP-SAT ignores `min_start` in assignment and only uses it for post-hoc sequencing (`alloc_solver.py:116-164`).

**WA-2 (High) [V]: The two engines give different results.**
- Timefold capacity is the last task's *end time*, including idle gaps (`services/allocation-solver/.../Employee.java:116-121`). CP-SAT capacity is the sum of durations.
- Timefold penalizes every unassigned task equally (`TaskAssigningConstraintProvider.java:65-74`). CP-SAT weights by priority (`alloc_solver.py:138-139`).
- So the same input can produce different assignments and different "unassigned" reasons, and `allocation.py:336` can report "No worker … has capacity left" for a precedence-induced gap.

**WA-3 (Medium) [V]: Fallback happens only when the probe fails.**
- `solve()` probes `/v1/demo-data` once (`alloc_solver.py:107-112, 167-174`).
- Any later HTTP error, `DATASET_INVALID` (for example zero tasks after pins), or the 600 s poll deadline fails the tool. It does not fall back to CP-SAT.
- Polling GETs are not status-checked (`alloc_solver.py:85`), so a 404 after a service restart becomes a silent 10-minute wait.

**WA-4 (Medium) [V]: Every Timefold solve takes the full 30 s.**
- `spentLimit` defaults to PT30S (`settings.py:52`), with no unimproved-time termination in the service (`application.properties:6,12-13`).
- The 600 s client deadline is unrelated to the configured limit.

**WA-5 (Medium) [V]: AI agents are permanently in shadow mode under default settings.**
- `ai_min_recorded_outcomes` defaults to 20 (`contracts.py:123`), but **nothing writes `phase4/agent-outcomes.json`**: `grep` finds only readers (`allocation.py:95-100`).
- Humans lose 10% of capacity to a review budget whenever any agent is enabled, even if no task can go to AI (`allocation.py:238-240`).

**WA-6 (Low) [V]: The sensitive-area check uses substrings.**
- `RISKY` matches substrings: "role" in "controller", "auth" in "author" (`allocation.py:46-47, 126`).
- This errs on the safe side, but reduces AI eligibility noisily.

**WA-7 (Low) [V]: The runner-up is computed against final loads.**
- That is not the load at decision time (`allocation.py:317, 371-382`), so explanations built on it can be wrong.

### 2.6 Agent 4: Infra & Pipeline

**IN-1 (High) [V]: Validation is slow and sequential.**
- Every `infra_validate` runs, one after another, each as its own `docker run`:
  - the registry probe;
  - `tofu fmt`;
  - `tofu init` + `validate` **per environment**, with one retry on network errors;
  - tflint, trivy (600 s timeout), checkov (600 s), actionlint, helm lint, kubeconform, gitleaks, conftest;
  - one extra actionlint `docker run` **per CI repository** (`sandbox.py:84-271`, `infra.py:388-404`).
- Modules are re-downloaded on every `init`; only providers are cached (`sandbox.py:38-45`).
- The prompt allows up to 3 repair rounds, and fix passes add more.

**IN-6 (High) [V, code plus measured]: Timeouts are treated as network errors, retried, then reported as "skipped".**
- `_run` returns `"timeout after Ns"` (`sandbox.py:58`), and `"timeout after"` is listed in `NETWORK_ERRORS` (`sandbox.py:32-33`).
- So `_validate_envs` retries each `tofu init`/`validate` that timed out (`sandbox.py:128-136`), and finally reports the check as *skipped* because of "registry/network errors" rather than failed.
- Measured: the first clinic `infra_validate` took 1,998 s and returned `checks_passed: true` with `tofu_validate` skipped (J4a L858→L867).
- A hung or extremely slow `tofu init` therefore costs up to 6 × 300 s **and** turns into a pass (with SEC-4).

**IN-2 (Medium) [V]: The conftest check tests nothing generated.**
- It runs `conftest verify` on the shipped policy library's own unit tests (`sandbox.py:254-270`).
- It costs a container per validate and adds a "check" that cannot fail because of generated content.

**IN-3 (Medium) [V]: The secret scan and manifest skip agent-added files.**
- They only iterate `manifest.files` (`infra.py:406-411`). Files the agent creates under `infra/repo/` are not hashed, scanned by the regex or published. gitleaks still sees them.

**IN-4 (Low) [V]: actionlint globs only `*.yml`** (`sandbox.py:224`).

**IN-5 (Low) [V]: The catalog is AWS-only.**
- Non-AWS intents produce only CI and a gap (`infra.py:139-140, 264-265`).
- Most module pins are unverified ranges (`catalog.yaml`).

### 2.7 Publishing and integrations

**PUB-1 (Medium) [V]: The exactly-once mapping file is rewritten after every external write.**
- `ExternalIds.put` → `save()` rewrites the whole JSON, including `last_payload` bodies, on every write (`publish.py:74-80`). The I/O is O(n²).
- **[P]** A crash between `adapter.start()` and `ids.put("dispatch", …)` re-dispatches the same AI task (`publish.py:408-409`). Only tracker items have marker-based adoption.
- **[P]** Jira search used for adoption is eventually consistent, so duplicates are possible right after a crash.

**PUB-2 (Low) [V]: Publishing is sequential and throttled to about 1 write per second** (`trackers/base.py:70-74`). That is appropriate for API limits, but a 573-item backlog needs at least about 10 minutes of creates plus links. It is outside the LLM path.

**PUB-3 (U): Jira, Linear, GitHub, Copilot and Claude dispatch have never been run.** `docs/PHASE4.md` "Not verified here". Treat them as untested code.

### 2.8 Tests

**TST-1 (High) [V]: The tests mostly encode current behaviour, not requirements.**
- They pass (125/125), but:
  - they assert the defect in SEC-4;
  - they never test the guard against `.`, case, cross-project or `requests.md` paths (`tests/test_guardrails.py`);
  - they do not exercise a rebuild after splits (TB-1) or partial updates (TB-2);
  - every allocator test forces `PHASE4_ALLOCATION_SOLVER_MODE=local`, so there is no Timefold contract test;
  - every infra test forces `PHASE4_IAC_SANDBOX_MODE=off`, so no real check output is ever parsed;
  - nothing exercises an INFEASIBLE or UNKNOWN sprint solve, a pin interaction, concurrency, budgets or resume;
  - there is no evaluation of LLM output quality at all: no golden backlogs, no rubric.
- Test runtime is 74 s, mostly solver time limits. **[P]**

**TST-2 (Medium) [V]: Java tests in the Docker build run only the constraint-provider test** (`services/allocation-solver/Dockerfile:8-9`).

---

## 3. Performance and cost analysis

### 3.1 Measurements available

All rows are from `outputs/*/runs/*/report.json`. "Cache read" is the `input_token_details.cache_read` sum. Cache writes are reported under `ephemeral_5m_input_tokens`; for example, 2.78 M for Task Breakdown `124309`. Passes: w = write, v = verify, f = fix, ! = failed.

| Project / job | Agent | Status | Elapsed (s) | Passes | Input tok | of which cache-read | Output tok |
|---|---|---|---|---|---|---|---|
| bookmarks-live 151354 | task-breakdown | success | 562.5 | w,v,f,v | 3,456,902 | 2,973,273 (86%) | 115,105 |
| bookmarks-live 152624 | sprint-planning | partial | 195.1 | w,v,f,v,f,v | 503,871 | 384,241 | 20,798 |
| bookmarks-live 153144 | sprint-planning | success | 75.4 | w,v | 268,829 | 221,888 | 8,231 |
| bookmarks-live 024932 | infra-pipeline | fail | **373,661.8** | w,v,f! | 1,656,514 | 1,497,413 | 54,138 |
| bookmarks-live 130034 | infra-pipeline | success | 817.7 | w,v | 310,776 | 241,224 | 7,670 |
| bookmarks-live 131514 | work-allocation | success | 242.1 | w,v,f,v | 1,050,733 | 903,912 | 25,906 |
| clinic-test-2 124253 | infra-pipeline | fail (429) | 3,341.2 | w! | 651,052 | 553,099 | 12,201 |
| clinic-test-2 124309 | task-breakdown | success | 1,328.0 | w,v,f,v,f,v | **20,488,495** | 17,711,615 (86%) | **701,978** |
| clinic-test-2 131045 | sprint-planning | partial | 725.7 | w,v,f,v,f,v | 4,302,385 | 3,675,038 | 66,891 |
| clinic-test-2 132439 | sprint-planning | fail (429) | 347.9 | w! | 2,099,247 | 1,317,993 | 26,373 |

Scale of the clinic inputs and outputs **[V]**:
- 10 features, 79 stories, 484 tasks;
- `backlog.json` 1.68 MB, `backlog.md` 186 KB, `enrichments.json` 576 KB, `sprint-plan.json` 133 KB;
- about 610 KB of specs;
- 65 MB project folder, mostly run copies and logs.

**Measured timeline (clinic-test-2).** Sources are the per-job transcripts in `outputs/clinic-test-2/logs/*.log` (abbreviated J1, J2a, J2b, J4a) and the pass boundaries in `logs/app.log`. The local timezone is +05:30.

**Task Breakdown `124309`: 1,328 s.**

| Segment | Time | Notes |
|---|---|---|
| Write pass | **916.9 s (69%)** | Breakdown below |
| Validators | 206.4 s | 3 passes (73.7 + 86.6 + 46.1) |
| Fix passes | 199.4 s | 2 passes (151.7 + 47.7) |

Inside the write pass:

| Segment | Time | Evidence |
|---|---|---|
| Setup reads | 31.5 s | |
| One LLM turn writing 10 `task(speckit-feature)` calls (31.8 KB of arguments) | **75.0 s** | J1 L1055→L1057 |
| 10 parallel spec-kit subagents, 136 HTTP calls | **466.3 s** | J1 L1057→L1189 |
| Two `backlog_build` format failures and repair | about 20 s | J1 L1557, L1567 |
| Turn composing 10 enricher calls | 27.3 s | |
| 10 parallel enrichers, 127 HTTP calls | **239.3 s** | |
| Wrap-up | 52.3 s | |

- **Straggler.** Feature 001 finished at 12:52:34; the other nine finished between 12:48 and 12:50. One single 001 request took 114.9 s (L1189–1190). The whole fan-out waits for the slowest subagent, about 157 s here.
- **Request totals.** 347 LLM requests (84 main-agent, 263 subagent), about 59 k input tokens per request on average. Cache reads were 86.4% of input; **ephemeral cache writes 2.78 M (13.5%)**; output 0.70 M, of which 0.16 M was reasoning.
- **Request rate.** It peaked at 43–55 requests/min during the fan-outs.
- **File churn.** 177 subagent file writes/edits (from lock lines in `app.log`). `specs/003-online-booking/tasks.md` was edited **32 times**.

**Sprint Planning `131045`: 725.7 s, partial.**

| Segment | Time |
|---|---|
| Write pass | 288.1 s |
| Fix passes | 178.1 s and 169.8 s |
| Verify passes | 31.7 s, 31.5 s and 24.5 s |

- LLM wait was 563 s (78%).
- `sprint_solve` was called **16 times (154.8 s)**. `sprint-plan.json` went through 16 versions.
- **The same blocking gap appeared in all 3 verdicts** (S-POLISH-006 after DL-1), so the loop never converged.
- The agent made 3 calls to tools that do not exist (`bash`, `x`).
- 4 solver results overflowed into `/large_tool_results/` and were then read back in 80 KB chunks.

**Sprint Planning `115043`: 347.9 s, then 429.**
- 6 solves took 125 s, with individual calls of 26–33 s even though the limit is 10 s. **[P]** Likely CPU contention with the infra containers running in parallel, plus the core solve.
- The run left the live `sprint/sprint-plan.json` at version 22: INFEASIBLE, empty and `annotated:false`. The operator had to save the earlier output separately (`runs/clinic-test-2/agent-2-sprint-planning/output-run-1-partial/`).

**Infra & Pipeline `124253`: 3,341 s, then 429.**
- Only 16 LLM turns, and **LLM wait totalled 87 s (2.6%)**.
- **Two `infra_validate` calls took 1,998.4 s and 1,236.1 s, together 96.8% of the run** (J4a L858→L863, L1471→L1472).
- First call: it returned `checks_passed: true` with `tofu_validate` skipped ("registry/network errors"). This is SEC-4 happening in a real run.
- Second call: tofu validate failed with provider plugin start-up errors.
- **The mechanism [V].** A 300 s `tofu init` timeout returns the string `"timeout after 300s"`. That string is in `NETWORK_ERRORS` (`sandbox.py:32-33, 58`), so a timeout is classified as a network error and **retried**. The worst case is 3 environments × 2 attempts × 300 s = 1,800 s, plus trivy and checkov at up to 600 s each. The 1,998 s first call matches that worst case. **[P]** Which individual commands timed out needs per-tool timing.

**Rate limiting.**
- All four 429 resets point to the same moment (about 17:10 local): one subscription window exhausted by about 28 M Sonnet tokens across the preserved runs, 75% of them from Task Breakdown.
- Two retries were launched at 14:44, about 2.4 h before the reset, and both failed within 2 s.
- The failure is fail-fast: no time is spent in backoff (`subscription_models.py:255-262`).

**Upstream comparison [V].** The phase-3b report that produced these inputs (`clinic-test-2/clinic-test-2/report.json`) logs `elapsed 1237 s` and `cost_usd_equivalent 4.77`. Phase 4 logs no cost at all. Converting tokens to money needs the tariff of the auth mode in use, which is **[U]**.

**Evidence that the pipeline was driven by another automated session [V].**
- The `runs/clinic-test-2/*/run.log.seen` files (0 bytes; no writer anywhere in this repo) were touched shortly after each run finished.
- The P4-G1 approval names "Claude Code … Test approver (on user's instruction)" (`runs/clinic-test-2/agent-2-sprint-planning/input/gates/P4-G1.approved.json`).
- Maker-checker accepted it (SEC-8).

### 3.2 Where the time and tokens go: verified mechanisms

1. **Context re-sending per agent step dominates tokens [V].**
   - In the deepagents/LangGraph loop, each model call carries the system prompt, tool schemas, and the full message history including every tool result.
   - The 20.5 M input tokens against 0.7 M output in one Task Breakdown run (a ratio of about 29:1) is the signature of many steps over a large, growing context.
   - Prompt caching is on, so most of it is billed as cache reads, but cache reads still count against subscription limits and still add latency.
   - Contributing code paths:
     - tool results return large JSON: `backlog_validate` returns up to 40 warnings plus all blocking issues; `sprint_solve` returns every sprint's stories with titles; `speckit_script` returns entire templates;
     - agents read `backlog.json` and `backlog.md`, which are hundreds of KB, through `read_file` and `grep` (36 `grep` and 19 `read_file` calls by the main agent alone in clinic `124309`);
     - summarization triggers only at 30% of the context window (`config.py:COMPACTION_TRIGGER_FRACTION=0.30`), so contexts may grow to a large absolute size before compaction. The exact window depends on the model profile **[U]**.
2. **Verify and fix loops multiply the cost [V].**
   - Task Breakdown and Sprint Planning on clinic each ran **3 verify + 2 fix** passes.
   - Each verify pass is a full agent with file tools and a structured-output tail.
   - Each fix pass re-reads inputs and outputs from scratch, because there is no conversation carry-over: `_stream` starts a new message list each pass (`cli.py:81-83`).
   - On Sprint Planning the loop still ended "partial", so all three verify passes were paid without producing an approvable plan.
3. **Rate-limit waste [V].** Two runs ended in `SUBSCRIPTION_RATE_LIMITED` after 3,341 s and 348 s, and all their in-flight context was lost (ENG-2). Concurrency across CLI runs and unbounded subagent fan-out (TB-5) both draw on the same quota.
4. **Solver wall-clock [V].**
   - Sprint `solve` uses 10 s per CP-SAT call with 8 workers. When infeasible it adds a core solve (up to 10 s) and up to about 2 × (#conflicts) option solves at 5 s each. Measured offline on the clinic model: 16.2 s per `sprint_solve` call.
   - Timefold uses a fixed 30 s per allocation solve (WA-4).
   - All of this is small next to LLM time, but each solve also sits inside an agent step that holds the context.
5. **Infra validation [V, measured].**
   - On clinic, 96.8% of the Infra run was two `infra_validate` calls, with only 2.6% spent waiting on the LLM.
   - Contributors: sequential containers (IN-1); timeouts retried as "network" errors (IN-6); modules re-downloaded on every init.
   - On bookmarks `130034`: 817.7 s for 310 k input tokens, consistent with the same pattern.
6. **Fan-out stragglers and spec churn [V, measured].** The 10-way spec-kit fan-out waited about 157 s for one feature. One subagent edited its `tasks.md` 32 times. Each `edit_file` is a full model turn over that subagent's growing context.
7. **Tool-result inflation through grep [V, measured].** See ENG-10. In Task Breakdown, 22 of 73 main-agent greps returned results from files *other than the one requested*, 643,650 characters in all. Some of it came from job logs and `.terraform` folders.
8. **Compaction thresholds are fixed, not model-aware [V].** `app.log` contains 128 warnings that `claude-sonnet-5-5` "has no max_input_tokens in its profile". Compaction therefore fires at a fixed 100 k tokens and argument truncation at 60 k (`config.py` fallbacks; `model_setup.py:166-178`).

### 3.3 Hypotheses and what remains to measure

- **H1 (measured on one run):** For Task Breakdown, most of the write pass is subagent fan-out: 705.6 of 916.9 s (77%), or 53% of the whole run. *Still to measure:* the split inside each subagent across specify, plan, tasks, analyze and the fix rounds. That needs per-subagent spans, because subagent messages are not in the job log today (section 1.2).
- **H2 (measured on one run):** For Infra, `infra_validate` was 96.8% of wall-clock. *Still to measure:* which tool and environment consumed it. Wrap `sandbox._run` with timing per tool and per environment.
- **H3:** Fix passes contribute less quality than they cost. *Measure* by diffing the artifacts before and after each fix pass (`runs/<job>/files/` already captures the final state only) and scoring them against a rubric.
- **H4:** The full spec-kit chain (plan, research, data-model, contracts, analyze) does not change the backlog materially compared with specify + tasks. *Measure* with an A/B test on 3 PRDs and a blind comparison of backlog quality.

---

## 4. Production readiness assessment

| Capability | State | Evidence |
|---|---|---|
| Orchestration of the 4-agent flow | **Missing**: manual CLI per step | README §7, no orchestrator code |
| Run budgets (time, tokens, steps) | **Missing** | ENG-1 |
| Checkpoint/resume after a failure | **Missing** | ENG-2 |
| Concurrency control per project | **Missing** | ENG-3 |
| Rate-limit-aware scheduling | **Missing** (fail-fast only) | ENG-6, `subscription_models.py:248-265` |
| Authentication and authorization (gates, approvers, services) | **Missing** | SEC-7, SEC-8 |
| Integrity of human approvals | **Broken** (bypassable guard, publish without hash checks) | SEC-1, SEC-3 |
| Multi-tenant isolation | **Missing** | SEC-2 |
| Sandbox isolation for generated IaC | **Partial** (Docker, no hardening; host fallback) | SEC-5 |
| Observability | **Partial**: Langfuse optional; giant unstructured logs; no metrics; no per-tool timings | ENG-8 |
| Data retention and PII handling | **Missing**: transcripts with client content kept indefinitely; untracked data folders not git-ignored | ENG-8 |
| Deterministic validation before LLM judgement | **Partial**: `*_check` tools exist but only the LLM validator calls them | `cli.py:253-280` |
| Correct failure semantics (UNKNOWN solver, skipped checks) | **Broken** | SP-2, SEC-4 |
| Output quality evaluation | **Missing** | TST-1 |
| Tested external integrations | **Missing** | PUB-3 |
| Reproducibility (as_of, seeds, versions) | **Partial**: seeds fixed (`capacity.py:316,352`); `as_of` defaults to today; model versions are env-driven | `sprint.py:44-45` |
| Version control and CI coverage | **Missing** for Phase 4 | ENG-9 |

**Failure propagation worth noting:**
- A guard bypass (SEC-1) or an aggregate "passed" with skipped checks (SEC-4) flows into a human approval. The human is told checks passed or the gate is satisfied, approves, and `publish` (SEC-3) pushes possibly different content.
- A solver UNKNOWN (SP-2) produces a plan that looks valid. The LLM validator may or may not notice, because `sprint_check` reports no problem for "capacity" deferrals.
- A rate limit mid-run (ENG-2) leaves partially rewritten artifacts on disk, which the next run treats as "previous output" to "change only what is needed" (`cli.py:137-142`).

---

## 5. Detailed recommendations

Each recommendation lists the findings it resolves, the affected code, its trade-offs and the expected benefit. Benefits are stated qualitatively wherever no measurement exists. No speedup numbers are invented.

### 5.1 Integrity and safety first (small, high leverage)

**R-1: Canonicalize paths before every guard decision [R] (fixes SEC-1, SEC-2 partly).**
- In `guardrails.py` and `phase4/files._rel`:
  - normalize with `posixpath.normpath`;
  - reject `.` and empty segments;
  - compare segments case-insensitively;
  - resolve the real target through the backend and check `relative_to(OUTPUTS_DIR / <bound project>)`.
- Add `requests.md` and `report.json` to the protected set.
- **Bind each run to its project.** Build the backend with `/outputs/` mapped to `OUTPUTS_DIR/<project>` only, or route `/outputs/<project>/` only, and reject a tool `project` argument that differs from the run's project. Inject the project in `tools.py` rather than letting the model choose it.
- **Trade-off:** prompts and paths stay the same if the virtual prefix is kept as `/outputs/<project>/`.

**R-2: Make gate approvals unforgeable and publishing verifiable [R] (SEC-1, SEC-3, SEC-8).**
- Store approvals outside the agent-reachable tree, or sign them with an HMAC key the agent process does not expose to tools.
- In `publish_*`, verify every file against the approved digests. For infra, check each `ManifestFile.sha256` against disk, and refuse unlisted files under `infra/repo`.
- Pin `backlog.json` as part of P4-G3, or snapshot the approved files into `gates/<gate>/` and publish from the snapshot.

**R-3: Fix the "skipped means passed" semantics [R] (SEC-4).**
- Make `checks_passed` three-valued (`passed` / `failed` / `incomplete`). Require a configured minimum set of non-skipped tools, for example `tofu_validate`, `trivy`, `gitleaks` and `checkov`, for `passed`.
- Update `infra.check`, the validator prompt, `PR.md` and the test at `tests/test_phase4_pipeline.py:231`.

**R-4: Harden the sandbox and remove host execution by default [R] (SEC-5).**
- Default `PHASE4_IAC_SANDBOX_MODE` to Docker-only. Make "local tools" an explicit opt-in that runs with a scrubbed `env=`.
- Add `--read-only` (with a tmpfs for the workdir copy), `--cap-drop ALL`, `--security-opt no-new-privileges`, `--pids-limit`, `--memory` and `--cpus`.
- Mount a *copy* of `infra/repo` rather than the live folder.
- Restrict egress to the registries with a proxy or a network policy, or run `tofu init` in a separate step with the network on and `validate` with `--network none`.
- Before init, reject module or provider sources outside the catalog allow-list.

**R-5: Lock down services and dispatch [R] (SEC-6, SEC-7, SEC-9, SEC-10).**
- Bind the solver to `127.0.0.1:8080` in compose, disable Swagger and the UI, run as non-root, and add a health endpoint. Stop using `/v1/demo-data` as the probe.
- Drop `id-token: write` and `issues: write` from `phase4-claude.yml.j2`, and constrain `claude_args` (allowed tools, path restrictions).
- Fix or remove `services/atlantis` (missing `policies/`). Pin images by digest and verify binary checksums.

### 5.2 Correctness fixes in the deterministic cores

**R-6: Backlog enrichment persistence [R] (TB-1, TB-2).**
- Compute `stale` *after* `_apply_all` (or include split-part ids derived from `split_into`).
- Make `_apply` transactional: apply to a deep copy and commit only when there were no errors. Alternatively, record the successfully applied subset in `enrichments.json`.
- Add regression tests that mirror Appendix A, checks 3 and 4.

**R-7: Sprint solver failure semantics and better infeasibility handling [R] (SP-1, SP-2, SP-3).**
- **Status handling.** Treat UNKNOWN and MODEL_INVALID as errors returned to the agent, with no plan written. Raise the time limit or report "no solution found in N s".
- **Minimal cores.** Use a deletion-based MUS (Minimal Unsatisfiable Subset) over the assumption literals. With 80 literals at about 0.02 s per infeasibility check (measured wall time 0.024 s), a linear deletion pass costs about 80 solves. **[P]** That is a few seconds, which needs measuring. Alternatively, solve a MaxSAT-style relaxation: minimize the weighted number of violated switches, with `must` weighted higher than `pin`, which in turn is higher than `deadline-soft`. That directly answers "what is the smallest change that works?"
- **Group options.** Add group relaxations ("drop all pins", "drop pins of release 2", "soften deadline X") alongside the single-switch ones. The clinic case shows a group option was the feasible one.
- **Better formulation.** Replace the all-or-nothing must and hard-deadline switches with a lexicographic objective: (1) minimize must-haves after their deadline, (2) minimize must-haves unplanned, (3) maximize WSJF value. CP-SAT supports this through weighted objectives or successive solves with bounds.
- **Trade-off:** objective weights need product sign-off. The plan stays explainable because the violated items are reported.

**R-8: Make the allocator engines agree and fall back properly [R] (WA-1 to WA-4).**
- Choose one capacity semantics, either *worked minutes* or *calendar end*, and implement it in both engines.
- Add precedence: either a Timefold constraint, or hard precedence in CP-SAT with interval variables plus `AddNoOverlap` per worker.
- Detect cycles and return an error.
- In `auto` mode, fall back to CP-SAT on *any* Timefold failure; `raise_for_status` on polls; derive the poll deadline from `spentLimit`; add `unimproved-spent-limit` (for example PT5S) so small problems return early.
- Since the problems are small (a sprint's tasks), consider dropping Timefold altogether in favour of the local CP-SAT model, which is already in-process. That removes a Java service, a network hop, a fixed 30 s wait and a contract surface. **Trade-off:** you lose Timefold's score analysis and UI, and you would need to port its soft constraints.

**R-9: AI-eligibility plumbing [R] (WA-5, WA-6).**
- Either implement outcome recording (dispatch status sync writing `agent-outcomes.json`), or default `ai_min_recorded_outcomes` to 0, with shadow mode as an explicit opt-in.
- Apply the review-budget deduction only when tasks are actually assigned to AI.
- Use token- and path-segment-aware matching for `RISKY`.

### 5.3 Execution-model and performance changes (the big wins)

**R-10: Run budgets, timeouts and failure policy [R] (ENG-1, ENG-5, ENG-6).**
- Set the SDK request timeout (for example `timeout=`, connect and read) on every model.
- Wrap each pass in `asyncio.wait_for` (wall-clock), and add a token budget enforced by a callback that cancels the pass when usage exceeds the pack limit.
- Add `max_steps` per pass by setting `recursion_limit` on the config.
- Retry validator failures once.
- Configure a fallback model or provider for 429s (the packs can use the existing escalation machinery), or queue the run until the reset time.

**R-11: Checkpointing and resume [R] (ENG-2).**
- Pass a durable LangGraph checkpointer (SQLite or Postgres) to `create_deep_agent`, keyed by job id. Add `agent-engine resume <job>`.
- Also make the deterministic steps idempotent and their state explicit (they mostly are already: the tools rewrite files from inputs), so that resume rarely needs the transcript.
- **Stage outputs, then promote (ENG-11).** Tools write into a per-job staging directory or versioned files. On success, `cli._run` promotes the declared outputs atomically, by rename. A failed run never replaces the last good artifact.
- This also fixes ENG-4: "declared output exists" becomes "declared output was produced by this job".
- **Trade-off:** checkpoint storage grows with context size. Prune it after success.

**R-12: Deterministic pre-validation, and LLM validators only for judgement [R] (biggest cost lever after context size).**
- Before paying for a validator, call the pack's `*_check` tool directly from `cli._run`:
  - if it reports blocking problems, skip the validator and send the problems straight back as fix gaps;
  - if it is clean, run the LLM validator with a **narrow, structured input** instead of an open-ended agent: the check result, the specific judgement questions from the validator prompt, and only the relevant excerpts. For example, sprint goals plus the stories per sprint, or the AI-eligible tasks plus their ACs.
- That turns a multi-step agent into a single structured call in most cases.
- Mechanically checkable rubric items currently left to the LLM, such as "goal is one sentence", "each gap names an item id" or "ACs contain no vague words", can move into code.
- **Trade-off:** less "holistic" review. Mitigate this with the evaluation set from section 8.

**R-13: Shrink what the agents see [R].**
- Tools should return summaries and ids, not full payloads. For example, `sprint_solve` returns counts per sprint and deferral codes; the agent reads details on demand.
- Add focused read tools such as `backlog_get_items(ids, fields)` and `backlog_list(level, epic, fields)`, so agents stop `grep`ping a 1.7 MB JSON.
- Hide `logs/` and `runs/` from agents entirely, through backend routing.
- **Fix the grep scope (ENG-10).** Either:
  - make ripgrep a hard prerequisite: check for it at start-up and fail otherwise, and add it to the setup docs; or
  - wrap or replace the `grep` file tool so a file path searches only that file.

  Also report the fallback behaviour upstream to deepagents. This is cheap and removes measured, pure-waste context: 644 K characters in one run.
- Have `speckit_script` stop returning `TEMPLATE_CONTENT` inline where the skill only needs a path. **[U]** Check what the spec-kit skills actually require.
- Consider an earlier absolute compaction trigger for subagents, and give subagents the fast-model summarizer, as `model_setup.py` intends (section 1.2).
- **Expected benefit:** a direct reduction in per-step context, which the measurements show is the main token driver. The magnitude must be measured (H1, H3).

**R-14: Replace open-ended loops with fixed workflows where the steps are known [R/alternative].**
- The Task Breakdown flow is a fixed sequence: init, split, per-feature spec-kit, build, enrich per epic, cross-dependencies, validate. Today the main LLM orchestrates it through tool calls, paying context on every step.
- A code-driven workflow would:
  - call `speckit_init` and `set_features` once, with one structured LLM call to split features;
  - run per-feature spec-kit generation with **bounded concurrency** (semaphore sized to the rate limit). Each run is a short subagent, or better, a few direct structured calls for spec, tasks and analysis that write files deterministically;
  - run `backlog_build` in code;
  - enrich each epic with structured calls that return the `backlog_update` payload directly, validated by Pydantic;
  - use the LLM only to resolve the issues `validate` reports.
- The same applies to Sprint Planning (one structured call to score business values, solver in code, one call for goals and explanations) and Work Allocation (one structured call for AI verdicts, solver in code, one call for explanations).
- **Trade-off:** less flexibility for unusual requests. Keep an "agent mode" for feedback or repeat requests. The deterministic tools and contracts are reused as-is.

**R-15: Parallelize the infra checks and cache modules [R] (IN-1, IN-2).**
- Run independent checks concurrently, or run all checks in **one** container invocation with a small script that emits JSON per tool. That saves container start-up and lets `tofu init` per environment run in parallel.
- Cache modules with a shared `TF_DATA_DIR`-style cache, or mirror the catalog modules locally. They come from a fixed catalog, so they can be pre-fetched into the sandbox image.
- Skip unchanged environments by hashing their inputs.
- Drop or re-label `conftest verify`; run it in the image build instead.
- **Fix IN-6 first; it is a one-line change with the largest measured effect.** Remove `"timeout after"` from `NETWORK_ERRORS`. Do not retry timeouts. Report a timeout as **failed/incomplete**, not skipped. Make the per-tool timeouts configurable and log their duration.
- **Trade-off:** the output-capture logic changes. Timeouts become per-tool inside one container.

**R-16: Orchestrator with per-project locking and rate-aware scheduling [R] (ENG-3, ENG-6).**
- Add a small orchestrator: a CLI command or service holding a job queue per project. It should:
  - hold a project lock (file lock or DB row);
  - schedule Infra in parallel with Task Breakdown only when the rate budget allows;
  - stop at gates, and resume when the gate is approved;
  - write a run ledger.
- Fingerprint only the files the run's tools and guard actually touched, recorded by the middleware, instead of diffing the whole tree.

### 5.4 Observability and hygiene

**R-17 [R]:**
- Structured JSON logs with job id, pass, tool, duration and token usage per call, through a callback.
- Turn full-payload transcripts down to DEBUG, or truncate them.
- Rotate logs.
- Set a retention policy for `outputs/*/logs` and `runs/`.
- Git-ignore `runs/` and `clinic-test-2/` at the repository root.
- Commit the Phase 4 work so CI covers it.

---

## 6. Alternative designs

**A-1: "Deterministic spine, LLM at the edges" (recommended target).**
- Each Phase 4 step becomes a typed workflow:
  `inputs → LLM structured judgement (small, schema-validated) → deterministic solver/renderer → deterministic checks → LLM narrative (goals, explanations) → artifacts`.
- Agents with file tools are used only where the work is open-ended: spec authoring, infra repair of failing files, and feedback requests.
- This matches what the code already is underneath (contracts, solvers, checks); it removes the costly part, which is context replay over many tool steps.
- **Risks:** the spec-kit skills are written for an interactive agent and would need porting into prompts with structured outputs. Quality must be checked against an evaluation set.

**A-2: Drop spec-kit's full chain for backlog generation.**
- The parser needs only `spec.md` user stories and `tasks.md` checklists (`speckit_parse.py`).
- Generating plan, research, data-model, contracts and an analyze pass per feature is the heaviest LLM work in the system (TB-7).
- An alternative is one structured call per feature that emits stories, scenarios and tasks directly as `WorkItem`-shaped JSON. Specs then become an optional, separately triggered artifact.
- **Trade-off:** you lose spec-kit's design artifacts, which reviewers or the coding agents may value. **[U]** Ask the users of P4-G1. Decide with H4 data.

**A-3: Batch API or async jobs for non-interactive calls.**
- If an API key is used (not the subscription), batch-eligible calls could use a provider batch API: per-epic enrichment, per-story business values, explanations. Latency per call grows, but cost falls and per-minute limits stop mattering.
- This applies only under the A-1 structure, because agent loops are not batchable.

**A-4: Single CP-SAT allocator (drop Timefold).** See R-8. It removes a service and a class of contract drift, at the price of reimplementing a few soft constraints. The problem size per sprint (tens to hundreds of tasks) is well within CP-SAT's range.

**A-5: Validator as a rubric scorer.** Replace free-form verdicts with a fixed rubric: a list of check ids with pass, fail and evidence. Deterministic checks are prefilled and the LLM fills only the subjective rows. This makes the verdict comparable between runs and testable.

---

## 7. Prioritized implementation plan

Each phase depends on the previous one. Within a phase, items are independent unless noted.

**Phase 0: safety net (days).**
- Commit the current code to a branch so CI covers it (ENG-9).
- Git-ignore `runs/` and `clinic-test-2/`.
- Add failing regression tests for SEC-1, SEC-3, SEC-4, TB-1, TB-2, SP-1 and SP-2. Use the scripts in Appendix A as the basis. These tests define "fixed".

**Phase 1: integrity and cheap measured wins (days).**
- R-1, R-2, R-3, R-6, plus the UNKNOWN-status part of R-7.
- The IN-6 timeout fix (part of R-15).
- The ENG-10 grep fix (part of R-13).
- A fixed solver seed (SP-7).

These are small, local changes. The IN-6 and ENG-10 fixes remove time and context that were measured as pure waste.

**Phase 2: operability (1–2 weeks).**
- R-10 (timeouts and budgets) before anything else, because it bounds every later experiment.
- Then R-11 (checkpoint/resume) and R-17 (structured timing logs). Phase 3 needs the per-tool and per-subagent timings these produce to settle H1–H4.

**Phase 3: measure, then cut cost (1–2 weeks).**
- Build the evaluation set (section 8.2) and capture baselines (tokens, wall-clock, quality) for each agent on bookmarks and clinic.
- Then apply R-12 (deterministic pre-validation), R-13 (smaller tool payloads and focused readers) and R-15 (infra checks).
- Re-measure after each change. Keep a change only if quality holds.

**Phase 4: structural (2–4 weeks).**
- R-7 (MUS, group options, lexicographic objective).
- R-8 (one allocator semantics; decide on dropping Timefold).
- R-14 / A-1 for Sprint Planning and Work Allocation first: their judgement parts are small and well-bounded. Task Breakdown comes last, informed by H1 and H4.
- R-16 (orchestrator) once the steps are bounded and resumable.

**Phase 5: hardening for production.**
- R-4 and R-5 (sandbox, services, dispatch).
- Real authentication for gates (SEC-8).
- Integration tests against tracker sandboxes (PUB-3).
- A retention and PII policy.

**Dependencies:**
- R-12 depends on the `*_check` tools being correct, so it needs Phase 1 first.
- R-14 depends on R-10 and R-11 to keep runs safe while restructuring.
- R-16 depends on R-11.
- Dropping Timefold (A-4) depends on R-8's semantic decision.

---

## 8. Verification strategy

### 8.1 Correctness (deterministic, CI)

- **Guard property tests:** generate paths with `.`, `//`, mixed case, backslashes and other projects' names. Assert that the *resolved* target is inside the bound project and outside the protected folders.
- **Gate integrity:**
  - mutate an approved file, then confirm publish refuses;
  - add an unlisted file under `infra/repo`, then confirm publish refuses;
  - write a forged approval through the agent's tools, then confirm it is refused.
- **Backlog round-trips:** run build, update (including splits and partial errors), then build again. Assert that every enrichment survives, using a property-based test over random update sequences.
- **Sprint model:**
  - a corpus of small synthetic instances with known optimum or infeasibility;
  - assert that the reported MUS is minimal: removing any element makes the model feasible;
  - assert that UNKNOWN never writes a plan;
  - the clinic instance (an anonymized copy) as a regression: expect FEASIBLE once pins are dropped.
- **Allocator:**
  - the same instance through Timefold and CP-SAT must agree on feasibility, capacity use and precedence;
  - a contract test against the real Timefold container in CI (docker compose).
- **Infra:** run the sandbox in CI with the real image on the example intent. Assert that every check *ran* (not skipped) and that parsed findings are non-empty for seeded bad files.

### 8.2 Quality of LLM output (evaluation set)

- Assemble 3–5 PRD/architecture pairs: bookmarks, taskflow, an anonymized clinic, and one adversarial input with prompt-injection text in architecture.md.
- For each agent, define rubric metrics that are mostly mechanical:

  | Agent | Metrics |
  |---|---|
  | Task Breakdown | PRD id coverage; AC testability (regex plus LLM judge); estimate spread; dependency sanity |
  | Sprint Planning | must-haves before deadline; value order respected; goal-to-story consistency |
  | Work Allocation | eligibility rule violations; explanation faithfulness to `score_breakdown` |
  | Infra & Pipeline | checks actually passed; no invented components |

- Record baseline scores and tokens, then compare every change in section 5.3 against them. Use several seeds or runs per item, because the outputs are stochastic.

### 8.3 Performance benchmarking

- Instrument these first (R-17):
  - per-model-call latency and tokens: input, cache read, cache write, output;
  - per-tool duration;
  - per-subagent span;
  - per-pass totals.
- Benchmark each agent on bookmarks (small) and clinic (large), with the same model and auth mode and no concurrent runs, 3 runs each. Report the median and spread.
- Track in particular:
  - share of wall-clock in LLM vs tools vs waits;
  - tokens per pass type (write, verify, fix);
  - number of fix passes;
  - 429 incidents.
- For the infra sandbox: time per tool and per environment, cold and warm cache.

### 8.4 Production readiness gates

- **Chaos tests:**
  - kill the process mid-pass, then resume;
  - inject a 429 with a long reset;
  - inject a solver service 404 or 500;
  - run with Docker missing;
  - start two runs on one project, and assert the second one is refused.
- **Security review** of the sandbox profile and dispatch workflow permissions. Run a prompt-injection red-team using the adversarial evaluation item.

---

## 9. Unresolved findings and unknowns

| ID | Unknown | Why it is uncertain | What would resolve it |
|---|---|---|---|
| U-1 | Cause of the 4.3-day run | The report has only "Connection error."; the request timeout is `None` (ENG-1), but machine sleep is also possible | The job log `outputs/bookmarks-live/logs/20261106-024932-9e7987.log` timestamps around the gap; reproduce with network loss under no timeout |
| U-2 | Split of wall-clock between LLM, subagents and tools per agent | Subagent messages are not logged; there are no tool timings | R-17 instrumentation; H1, H2 |
| U-3 | ~~Cache writes~~: **resolved** | They are reported as `ephemeral_5m_input_tokens` (2.78 M in Task Breakdown) | n/a |
| U-4 | ~~Compaction trigger~~: **resolved** | The profile has no `max_input_tokens` (128 warnings in `app.log`), so the fixed 100 k / 60 k fallbacks apply | Whether those values suit Sonnet 5.5 is a tuning question for Phase 3 |
| U-5 | Timefold Service-module behaviour (termination override, statuses, job retention) | Lives in the closed Service parent, not in the repo | Contract test against the container; vendor docs |
| U-6 | Value of spec-kit plan, research and contracts artifacts to downstream users | A product question | Interview P4-G1 reviewers; H4 A/B |
| U-7 | Whether the subscription "billing marker" use is permitted | A legal/terms question | Account owner and provider confirmation |
| U-8 | Tracker, GitHub and dispatch adapters | Never run (`docs/PHASE4.md`) | Sandbox-tenant integration tests |
| U-9 | ~~Whether agents read other agents' job logs~~: **resolved, yes** | 4 Task Breakdown grep results contained job-log content (ENG-10) | Block `logs/` and `runs/` from agent routes; install `rg` or replace the grep tool |
| U-11 | Which infra tool or environment consumed the 1,998 s and 1,236 s validate calls | No per-tool timing is logged | Timing around `sandbox._run` (R-17) |
| U-12 | Why 6 solves in `115043` exceeded the 10 s limit (26–33 s) | Core extraction and option solves add time; there was concurrent CPU load | Log the solve phases separately |
| U-10 | Atlantis/Checkov severity gating without a Prisma key | Depends on external tool behaviour | Run the Atlantis workflow on a test repo |

**Not examined in depth:**
- `src/agent_engine/inputs.py` conversions (docx/xlsx/pptx/eml/msg), beyond reading its entry points. It is pre-existing, tracked code outside Phase 4.
- The bodies of the Jira, Linear and GitHub adapters, beyond their HTTP client, search and marker logic.
- The individual Terraform and Helm templates, for cloud-security quality. The policies and trivy/checkov are meant to cover them; a platform engineer should review them.

---

## Appendix A: offline verification performed

Both scripts are in the session scratchpad. They copy data to a temporary folder, make no network or model calls, and delete the copy afterwards.

1. **`verify_defects.py`** reproduced the following:
   - The guard bypass: `./gates`, `Gates` and cross-project writes all accepted, and backend resolution lands in the real `gates/` folder.
   - `files._rel` accepts `./gates`.
   - Split-part enrichments dropped on rebuild.
   - A partial update reverted on rebuild.
   - `checks_passed` true with every check skipped.
   - `sprint.solve` lacks UNKNOWN handling.
2. **`sprint_repro.py`** re-ran `sprint.solve` on a copy of `outputs/clinic-test-2` with the saved business values and pins. Results:
   - INFEASIBLE with 80 conflicts and 1 option, in 16.15 s;
   - dropping only the pins gives FEASIBLE with 78 stories planned;
   - dropping DL-1 gives FEASIBLE with 51;
   - dropping every must stays INFEASIBLE.
3. **Test suite:** `.venv\Scripts\python.exe -m pytest -q` passed 125 in 73.98 s.
4. **Run-report mining:** every `outputs/*/runs/*/report.json` was summarized (section 3.1).
