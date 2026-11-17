# Clarifications: Platform foundation, access control and availability

No user was available; the most reasonable option was assumed in each case.

## Q1: How do users authenticate?

- Context: architecture.md and prd.md do not state the authentication mechanism (NFR-3 only requires board-member-only access).
- Options:
  - A: Email and password issued as a bearer token by the API (self-contained).
  - B: Single sign-on / external identity provider (OIDC).
  - C: Magic-link email sign-in.
- **Assumed: A** (open question Q1). It needs no component that the architecture does not name. Authentication is isolated behind one dependency so it can be replaced.

## Q2: How are board members added and removed?

- Context: no PRD story covers membership management, but membership drives NFR-3.
- Options:
  - A: Board owner adds/removes existing users through the API; creator is the owner.
  - B: Email invitations with acceptance flow.
  - C: Membership managed by an administrator only.
- **Assumed: A** (open question Q2). It is the smallest design that makes membership usable; invitations can be added later.

## Q3: What counts as downtime for the 99.5% monthly target?

- Context: NFR-2 gives no measurement rules.
- Options:
  - A: All downtime counts, per calendar month, external probe on prod.
  - B: Planned maintenance windows excluded.
  - C: Measured from server-side request success rate instead of a probe.
- **Assumed: A** (open question Q3). Strictest and simplest reading; probe-based measurement also detects outages in front of the API.
