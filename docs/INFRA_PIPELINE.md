# Infrastructure & Pipeline Setup (PDLC Phase 4, step 4.4)

DevOps Lead and Solution Architect review generated AWS OpenTofu, GitOps, CI, promotion, access and operational documentation at P4-G4. The catalog and existing renderer remain the architecture; unsupported clouds and deployment targets fail clearly rather than receiving a substitute topology.

## Execution

`infra_pipeline.py` extracts `InfraIntent` through one checked structured call with a cached instruction prefix. Intent and exact input/model identities are retained. Code renders and runs scanners. Invalid intent is retried once. Default strong tier escalates to frontier on failed checks. Repairs return structured edits only for specific failing generated files; incomplete/unavailable scanners pause for a human. Nothing applies infrastructure or opens PRs during generation.

Environments are dev, qa, stg and prod. The generated manifest tracks every file and marks repairs. Secrets remain references. Existing Terraform policies, private cluster endpoints, GitHub OIDC CI and ExternalSecrets remain; restricted namespace labels, observer RBAC, no workload API token mounting and alert routing labels are generated.

## Build and promotion

CI records immutable image metadata as an Actions artifact. A workflow_run notification sends a dev promotion event only after CI completes successfully. The infra workflow verifies the source repository, successful main push run, workflow path and digest artifact before opening a promotion PR. Higher environments copy the predecessor digest, including shared-image workers; no rebuild occurs. Local checks reject mutable tags.

The initial all-zero digest is an explicit bootstrap placeholder. Real ECR registry addresses, DNS/certificates and worker commands require deployment configuration. Configure the GitOps App, protected main and GitHub Environment protections before use. Promotion preflight verifies the configured reviewer ID, self-review prevention and no administrator bypass; production also checks the separate production/go-no-go status. Configure QA_APPROVER_ID, CLIENT_APPROVER_ID and DEVOPS_APPROVER_ID. The generated runbook explains QA Lead, client UAT, go/no-go and DevOps approvals; a reviewer list alone does not enforce multiple required approvals.

## Runbook and readiness

Generated `docs/BRANCHING.md` and `docs/RUNBOOK.md` cover trunk-based development, release tags, bootstrap/apply order, scoped IAM/SSO access, secret creation/rotation, promotion, rollback, monitoring and backup ownership. They are included in the manifest and PR description.

`phase4 check-environments` performs GET-only checks using `phase4/environment-sources.json`: `environments.<env>.pull_request` identifies the merged infrastructure PR and `apply_context` identifies that environment's Atlantis status. Configure ARGOCD_SERVER and ARGOCD_TOKEN by name. It verifies generated files against the merged Git tree, ancestry of current main, apply success, current CI and healthy Argo applications synced to that head. Missing evidence fails closed. Results are saved to `phase4/environment-readiness.json` and summarized in PR.md; refreshing PR.md requires renewed gate approval.

## Verification limits

Tests use fake models, scanners and API clients with network blocked. Real OpenTofu/scanner execution, GitHub App permissions, environment protection settings, Atlantis apply and Argo provisioning must be verified in the deployment environment. A generated or approved PR is never described as a provisioned environment. Azure/GCP require reviewed network, compute, data, secrets, IAM, CI and policy catalog entries before support can be enabled.

Publication also requires every Phase 4 checkpoint and final G4 approval; see [PHASE4.md](PHASE4.md). Phase 5 dispatch additionally requires current environment readiness.
