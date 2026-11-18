# Environment runbook: gym-full

## Bootstrap and ownership

DevOps Lead and Solution Architect review generated IaC and all remaining gaps before merge. This change set does not provision resources itself. Create encrypted, versioned remote state and its restricted IAM role first; apply dev/core before the shared ECR registries are used. Apply each environment through Atlantis after reviewed plans. Services run on ECS Fargate in each environment's cluster; set the ACM certificate and DNS for the load balancer before the first apply.

## Access and secrets

CI authenticates to AWS with GitHub OIDC, never static AWS keys. Scope the trust subject to the repository and protected main branch; scope ECR write to the generated image repositories. Grant ECR authorization-token access only as required by AWS. Atlantis uses a separate state/apply role. Human access uses SSO groups with environment-specific IAM roles; ECS Exec stays disabled; production access is audited and time limited.

Task definitions reference Secrets Manager entries by name, never values. Create the references listed in infra/PR.md before the first apply; only each service's execution role may read its own entries. After rotating a value, force a new deployment of the service so tasks read it. Never paste values in prompts, PRs or logs.

## Build and promotion

Configure the GitOps GitHub App with actions-read on application repos and contents/pull-request writes on the infra repo. Install only on the required repositories. Configure GITOPS_APP_ID and GITOPS_APP_PRIVATE_KEY by reference in GitHub. Allow Actions to open pull requests. Required workflow checks must run on app-authored PRs.

Configure QA_APPROVER_ID, CLIENT_APPROVER_ID and DEVOPS_APPROVER_ID with the expected GitHub user or team numeric IDs. Grant the App read access to environment protection metadata. Promotion refuses missing reviewer protection, self-review or administrator bypass. Production additionally requires a successful production/go-no-go status on the current infra revision, recorded by the designated go/no-go authority. Protect main with required reviews and checks. Configure GitHub Environments before enabling promotion: dev after successful CI; qa requires QA Lead; stg requires client UAT sign-off; prod requires a recorded go/no-go and DevOps Lead. GitHub required-reviewer lists generally require only one listed reviewer, so enforce the additional prod sign-off through a separate required check or deployment protection rule. Prevent self-review and prohibit bypasses.

CI builds once, records sha and digest in image.json, and notifies this repo only after the run succeeds. Dev verifies the source run and artifact. Manual promotion takes only component and target: it copies the predecessor digest with no rebuild. Workloads sharing an image move together. The all-zero initial digest is a bootstrap placeholder, not a deployable image. Configure real ECR registry addresses, public DNS/certificates and worker commands before apply.

Review and merge the promotion PR. The promotion PR changes only envs/<environment>/core/images.auto.tfvars.json; Atlantis plans it and applies the new task definition with the exact digest after approval. Check deployment health and the matching revision before advancing to the next environment. Never rebuild between UAT and production.

## Rollback and operations

Revert the relevant promotion merge in Git, review it, and apply it through Atlantis to return to the previous digest. Do not mutate an image tag. Database rollback requires a separate reviewed migration and backup restore plan; test restores in QA before incidents. Backups and restore ownership remain deployment-specific bootstrap requirements.

Alert rules are generated for each workload and environment. Connect the CloudWatch alarms (CPU; 5xx rate and p95 latency at the load balancer) to the team's on-call receiver and publish dashboard, tracing and incident links in the deployment record. HTTP services use latency/error alerts; workers use availability alerts. Logs go to CloudWatch Logs per service.

## Readiness evidence

Run `agent-engine phase4 check-environments --project-name gym-full` after merge/apply, using configured read-only source endpoints. Missing evidence remains not ready. Review environment-readiness.json alongside infra/PR.md before final G4 sign-off. Refresh evidence after every infra change; approval alone never proves provisioning.
