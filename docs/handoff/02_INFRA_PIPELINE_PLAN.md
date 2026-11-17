# Infrastructure & Pipeline Setup (PDLC Phase 4, step 4.4) — review and fix plan

Self-contained plan for aligning the **Infra & Pipeline** agent of `https://github.com/PriyaKumari6512/phase-4-agents`
(branch `feat/task-breakdown-from-approved-stories`) with the product specification. Background, the full Phase 4
spec and the working method are in `docs/handoff/00_START_HERE.md`. Do this after `01_WORK_ALLOCATION_PLAN.md`.

## 1. What the specification asks for

| | |
|---|---|
| Step | 4.4 — "Provision Dev/QA/Staging/Prod & CI/CD pipelines" (after 4.3, then gate G4) |
| Model tier | **M** (mid-tier); escalate only when output fails checks |
| Responsibilities | • Write Infrastructure-as-Code (Terraform or similar) for **Dev, QA, Staging, Prod** • Create **CI/CD pipelines and branching strategy** • Set up **secrets management, access controls, monitoring hooks** |
| Inputs | HLD/LLD, NFRs, client hosting / cloud constraints |
| Outputs | IaC scripts, **provisioned environments**, pipeline definitions, **environment runbook** |
| Output reviewed by | DevOps Lead; Solution Architect |
| Related rules | Environment promotion **Dev (auto after CI) → QA (QA Lead approves) → Staging/UAT (client signs off) → Prod (go/no-go + DevOps Lead)**; **the same build artifact all the way** (never rebuilt between Staging and Prod); secrets never in prompts, logs or code |

## 2. Where the code is

- Pack: `agents/infra-pipeline/agent.toml` (`model = "strong"`, tools `phase4-infra`, write-capable filesystem,
  knowledge = the golden-path catalog), `system_prompt.md`, `validator/` (`strong`, tool `phase4-infra-check`).
- Golden-path catalog: `agents/infra-pipeline/knowledge/catalog/` (`catalog.yaml`, OpenTofu templates for **AWS
  only** — network, EKS, RDS Postgres, ElastiCache Redis, SQS, S3, ECR; GitOps templates — Argo CD ApplicationSet,
  Helm chart and values, ExternalSecrets, ClusterSecretStore, PrometheusRule; repo templates — CI workflow, Atlantis,
  drift check, CODEOWNERS, a Claude Code workflow; OPA/Rego policies with tests).
- Deterministic code: `src/agent_engine/phase4/infra.py` (`set_intent`, `render`, `validate`, `check`, `render_pr`,
  risk score, `ENV_CIDR`, `REPLICAS`), `sandbox.py` (10 checks: tofu fmt/validate, tflint, trivy, checkov, actionlint,
  and others, run in the `phase4/iac-sandbox` image or local tools; missing tools are reported as skipped).
- Contracts: `InfraIntent`, `InfraManifest`, `CheckResult`, `Env = Literal["dev", "stg", "prod"]` in
  `src/agent_engine/phase4/contracts.py`.
- Orchestrator: stage `infra-pipeline`, gate `P4-G4`, runs **in parallel with Task Breakdown** (inputs:
  `architecture.md` + parts of `project.json`). Work Allocation only gives tasks to AI agents for repositories whose
  CI was approved at P4-G4 and is operational (`readiness.py`).
- Publishing: `publish_infra` in `publish.py` opens one infra PR and one CI PR per code repository
  (`PHASE4_PR_MODE=github`) or writes local PR bundles (default `local`). Atlantis applies after merge.
- Recorded run (old docs): 13.6 min, 0.3M input tokens, 44 files, all 10 checks passed, risk 50, 1 infra PR + 2 CI PRs.

## 3. Review findings

### Wrong (does not match the spec)
1. **No QA environment.** `Env` is only `dev | stg | prod` and the defaults, CIDRs and replica tables have no `qa`.
   The spec requires Dev, **QA**, Staging, Prod and a promotion path through QA (QA Lead approval).
2. **No branching strategy.** CI triggers on `main` and pull requests; there is no documented branching and
   environment-promotion strategy.
3. **No promotion pipeline / same-artifact rule.** `render` reports "image promotion is not generated" as a gap: CI
   builds and pushes images but nothing promotes **the same image digest** Dev → QA → Staging → Prod with the
   required approvals (QA Lead, client, go/no-go + DevOps Lead).
4. **No environment runbook.** `infra/PR.md` lists checks, risk and gaps, but there is no runbook (bootstrap order,
   access, secrets rotation, promotion, rollback, on-call/monitoring links).
5. **"Provisioned environments" are not verified.** The stage produces a reviewed PR; provisioning happens later via
   Atlantis. G4 needs "ready environments", so readiness evidence (applied, Argo CD apps healthy, CI green) should be
   collected and shown before G4 is approved.
6. **Labels:** P4-G4 says "platform engineer"; the spec says **DevOps Lead + Solution Architect**.

### Extra / questionable
- A full Sonnet validator after the deterministic `infra.check`, with up to 2 fix rounds.
- The validator and agent get write tools beyond what they need (the agent legitimately edits generated files to fix
  failing checks; the validator should be read-only and deterministic-first).
- A generated `phase4-claude.yml` workflow (AI coding agent in CI) belongs to Phase 5 dispatch; keep it only if the
  product owner wants AI agents enabled per repository.

### Correct and worth keeping
- Golden-path catalog rendering (deterministic, reviewed templates) instead of free-form IaC; secrets only as
  references (ExternalSecrets); CODEOWNERS; PrometheusRule alerts from SLOs; Atlantis plan/apply after human
  approval; drift detection; 10 sandbox checks with "skipped is never passed"; risk score; Rego policy tests.
- Intent extracted from `architecture.md` and validated (`set_intent` rejects invalid combinations, e.g. restricted
  data on a public endpoint).
- Tier M (`strong`) is right for this agent.

### Gaps to raise (not necessarily to build now)
- **Cloud coverage:** only AWS templates exist. "Client hosting / cloud constraints" may require Azure or GCP;
  `set_intent` should reject an unsupported cloud with a clear message (verify) and the plan should list what a
  second cloud would need.

### Optimizations
- Intent extraction can be **one structured call** (schema = `InfraIntent`) with a cached prefix of
  `architecture.md` + `catalog.yaml`, checked by `set_intent` and retried once. The repair loop (editing generated
  files until checks pass) is genuine agent work; keep a bounded tool loop **only when checks fail**, on the M tier,
  escalating to `frontier` on repeated failure.
- Validation: deterministic `infra.check` + sandbox results first; a light model review only of flagged items
  (e.g. public ingress on a non-public component, probes on non-HTTP workers, missing secret references).

## 4. Decisions to ask the product owner first

1. **Environment names:** `dev, qa, stg, prod` (add `qa`) — or rename `stg` to `staging`? *(Recommended: add `qa`,
   keep `stg` to avoid churn.)*
2. **Promotion mechanism:** GitOps promotion by pull request that changes the image digest per environment (Argo CD),
   with GitHub Environments protection rules for the approvals? *(Recommended.)*
3. **Branching strategy:** trunk-based (`main` + short-lived feature branches, PRs required, release tags) or
   GitFlow? *(Recommended: trunk-based with release tags.)*
4. **Provisioning evidence before G4:** is a merged-and-applied infra PR plus healthy Argo CD apps required for G4,
   or is an approved PR enough for Phase 4? *(Recommended: approved PR is the agent's output; readiness evidence is
   collected by a read-only check and shown at G4.)*
5. **Clouds:** AWS only for now? *(Recommended: yes, reject others clearly.)*

## 5. Fix plan (one step at a time; each step: code → tests → full suite green)

**Step 1 — Add the QA environment**
- `Env` gains `qa`; defaults `["dev", "qa", "stg", "prod"]`; `ENV_CIDR`, `REPLICAS`, templates, Argo CD
  ApplicationSet, alerts and Rego policies handle `qa`; `ci_ready_repos` and the risk score unchanged in meaning.
- Done when: rendering the example intent produces `envs/qa/...` and all sandbox checks (or their mocks in tests) pass.

**Step 2 — Promotion pipeline with the same artifact**
- Generate a promotion workflow per application: CI builds once and records the image digest; promotion PRs set that
  digest in the next environment's values (`dev` automatic after CI; `qa`, `stg`, `prod` through GitHub Environments
  with required reviewers matching QA Lead, client approver, DevOps Lead). Remove the "image promotion is not
  generated" gap. Add a check that every environment pins a digest (no `latest`).

**Step 3 — Branching strategy and runbook**
- Render `docs/BRANCHING.md` and `docs/RUNBOOK.md` into the infra repo from templates: branch model, PR rules,
  release tags; bootstrap order (state backend, core, Argo CD clusters), access model (IAM roles, CODEOWNERS),
  secrets (store paths, rotation), promotion and rollback steps, monitoring and alert routing, DR notes. List them in
  `infra/manifest.json` and in `infra/PR.md`.

**Step 4 — Access controls and monitoring hooks review**
- Confirm least-privilege IAM for CI (OIDC, no long-lived keys), Kubernetes namespaces/RBAC per environment, alert
  routes for every SLO; add Rego policies for any gap found. Keep secrets as references only.

**Step 5 — Code-driven intent + bounded repair**
- New `src/agent_engine/phase4/infra_pipeline.py` (`generate`, `review`, `repair`, `operation_model`) registered in
  `STRUCTURED_STAGES`: one structured call for `InfraIntent` (checked by `set_intent`, one retry) → `render` →
  `validate`; only if checks fail, a bounded repair (structured edits per failing file, or the existing tool loop) on
  `strong`, escalating to `frontier`. Pack: `model = ["strong", "frontier"]`; validator read-only, deterministic first.

**Step 6 — Readiness evidence for G4 and labels**
- A read-only `phase4 check-environments` (extend `readiness.py`): infra PR merged, Atlantis applied, Argo CD apps
  healthy per environment, CI green per repository → `phase4/environment-readiness.json`, shown in `infra/PR.md` and at
  G4. P4-G4 description → "DevOps Lead + Solution Architect".

**Step 7 — Clean-up, docs, tests**
- Remove unused agent tools/tool sets once the stage is code-driven; write `docs/INFRA_PIPELINE.md`; update
  `docs/PHASE4.md`; tests for QA env rendering, digest promotion, runbook/branching files, intent call checks,
  repair escalation, readiness evidence (all with fake tools; no network).

## 6. Acceptance criteria for "Infra & Pipeline complete"
- Dev, QA, Staging and Prod are generated with CI/CD, a documented branching strategy, digest-based promotion with
  the spec's approvals, secrets as references, least-privilege access and SLO alerts.
- An environment runbook is generated and listed in the PR.
- Intent comes from one checked structured call; repairs run only when checks fail; tier M with escalation.
- Readiness evidence exists for G4; labels match the spec.
- All tests pass; the component is committed and pushed as one commit.
