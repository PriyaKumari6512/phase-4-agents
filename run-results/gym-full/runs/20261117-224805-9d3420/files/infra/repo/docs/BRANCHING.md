# Branching and promotion

Use protected main, short-lived feature branches, required reviewed pull requests and required CI/policy checks. Tag approved releases with immutable release tags. CODEOWNERS routes infrastructure changes to DevOps; configure branch protection to require those reviews.

Build once on main. Promote the same image digest through dev → qa → stg → prod using promotion pull requests. QA Lead approves QA, the client approves Staging/UAT, and a recorded go/no-go plus DevOps Lead approval authorizes production. No environment-specific long-lived application branches and no rebuild during promotion.
