# Environment runbook: gym-full

## Bootstrap and ownership

DevOps Lead and Solution Architect review generated IaC and all remaining gaps before merge. This change set does not provision resources itself. Create encrypted, versioned remote state and its restricted IAM role first; apply dev/core before the shared ECR registries are used. Apply each environment through Atlantis after reviewed plans. Register Argo CD clusters named gym-full-<environment>; install the external-secrets operator, Load Balancer Controller, DNS, telemetry collector and Prometheus CRDs before syncing platform applications.

## Access and secrets

CI authenticates to AWS with GitHub OIDC, never static AWS keys. Scope the trust subject to the repository and protected main branch; scope ECR write to the generated image repositories. Grant ECR authorization-token access only as required by AWS. Atlantis uses a separate state/apply role. Disable standing cluster creator admin after explicit operational access is configured. Human access uses SSO groups with environment-specific RBAC; production access is audited and time limited.

ExternalSecrets hold paths, never values. Create the references listed in infra/PR.md in AWS Secrets Manager. Scope the external-secrets service account IAM policy to /gym-full/<environment>/* and bind its OIDC identity. Rotate values in the secret store, wait for ExternalSecrets refresh, and roll deployments only when the application requires it. Never paste values in prompts, PRs or logs.

## Build and promotion

Configure the GitOps GitHub App with actions-read on application repos and contents/pull-request writes on the infra repo. Install only on the required repositories. Configure GITOPS_APP_ID and GITOPS_APP_PRIVATE_KEY by reference in GitHub. Allow Actions to open pull requests. Required workflow checks must run on app-authored PRs.

Configure QA_APPROVER_ID, CLIENT_APPROVER_ID and DEVOPS_APPROVER_ID with the expected GitHub user or team numeric IDs. Grant the App read access to environment protection metadata. Promotion refuses missing reviewer protection, self-review or administrator bypass. Production additionally requires a successful production/go-no-go status on the current infra revision, recorded by the designated go/no-go authority. Protect main with required reviews and checks. Configure GitHub Environments before enabling promotion: dev after successful CI; qa requires QA Lead; stg requires client UAT sign-off; prod requires a recorded go/no-go and DevOps Lead. GitHub required-reviewer lists generally require only one listed reviewer, so enforce the additional prod sign-off through a separate required check or deployment protection rule. Prevent self-review and prohibit bypasses.

CI builds once, records sha and digest in image.json, and notifies this repo only after the run succeeds. Dev verifies the source run and artifact. Manual promotion takes only component and target: it copies the predecessor digest with no rebuild. Workloads sharing an image move together. The all-zero initial digest is a bootstrap placeholder, not a deployable image. Configure real ECR registry addresses, public DNS/certificates and worker commands before apply.

Review and merge the promotion PR. Argo CD syncs the exact digest. Check deployment health and the matching revision before advancing to the next environment. Never rebuild between UAT and production.

## Rollback and operations

Revert the relevant promotion merge in Git, review it, and sync Argo CD to the previous digest. Do not mutate an image tag. Database rollback requires a separate reviewed migration and backup restore plan; test restores in QA before incidents. Backups and restore ownership remain deployment-specific bootstrap requirements.

Alert rules are generated for each workload and environment. Connect Prometheus/Alertmanager routes to the team's on-call receiver and publish dashboard, tracing and incident links in the deployment record. HTTP services use latency/error alerts; workers use availability alerts. Confirm OTEL_EXPORTER_OTLP_ENDPOINT and operator health.

## Readiness evidence

Run `agent-engine phase4 check-environments --project-name gym-full` after merge/apply, using configured read-only source endpoints. Missing evidence remains not ready. Review environment-readiness.json alongside infra/PR.md before final G4 sign-off. Refresh evidence after every infra change; approval alone never proves provisioning.
