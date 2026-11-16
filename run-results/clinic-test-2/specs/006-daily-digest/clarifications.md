# Clarifications: Daily due-tomorrow digest

No user was available; the most reasonable option was assumed for each question.

## Q1: How is the digest scheduled?

architecture.md and prd.md do not say.

| Option | Answer | Implications |
|--------|--------|--------------|
| A | Kubernetes CronJob starting the notify-worker image every 5 minutes | Simple, restart-safe, manifest in acme/taskflow-infra `k8s/`; delivery time precision is 5 minutes |
| B | Internal scheduler loop in a long-running worker | One more long-lived process; needs leader election with several replicas |
| C | One CronJob per time zone | Many manifests; hard to maintain |

**Assumed**: A. Why: smallest design (constitution V). Correctness comes from the per-user, per-date delivery record, so the scheduler choice can be changed later.

## Q2: How is the user's time zone captured?

| Option | Answer | Implications |
|--------|--------|--------------|
| A | Field in user settings, pre-filled from the browser, UTC fallback if never set | One column, one endpoint, one control |
| B | Detected silently from the browser at every login | Can change without user knowledge |
| C | One organisation-wide time zone | Wrong for distributed teams |

**Assumed**: A.

## Q3: Do users with no tasks due tomorrow get an email?

| Option | Answer | Implications |
|--------|--------|--------------|
| A | No | Less noise; matches the PRD wording "listing them" |
| B | Yes, an "Nothing due" email | More email, no clear value |

**Assumed**: A (stated in the request).
