# Clarifications: Platform foundation, delivery and non-functional baseline

No user was available during this run. Each question below has an assumed answer, recorded in spec.md as
`Assumed: ... (open question Qn)`.

## Q1: Hosting provider and domain (PRD Q-008)

**Context**: Environments are hosted in an India cloud region chosen by us; the clinic supplies the domain. The provider is not named (ASM-002, RSK-008).

| Option | Answer | Implications |
|--------|--------|--------------|
| A | We choose a provider with managed container service, managed PostgreSQL 16 (HA standby, PITR) and CDN in an India region; domain supplied by the clinic later | Fits ADR-0005; infrastructure code names are provider-specific and set before staging |
| B | The clinic mandates a provider | Service names and cost change; RSK-008 |
| C | The clinic hosts on its own domain registrar/DNS only | DNS and certificate steps depend on the clinic |

**Assumed**: A. The environments use a placeholder domain until the clinic supplies theirs; confirm before staging is set up.

## Q2: Do the clinic's managers agree to the proposed speed and availability targets (NFR-002, NFR-004, PD-008, ASM-006)?

**Context**: The client gave no targets; 99.5% a month for online booking, 99.5% for reception hours 08:00-20:00 Monday to Saturday, 2 s / 3 s for 95% of requests are our proposals.

| Option | Answer | Implications |
|--------|--------|--------------|
| A | Proposed targets accepted at Gate 2 | The probes and SLO report use these numbers |
| B | Different (stricter) targets | Replicas, HA and alert thresholds change; cost rises |
| C | Targets are advisory with no SLA | Same measurements, no contractual consequence |

**Assumed**: C with A's numbers: measured and reported, no SLA (A-004).

## Q3: Who receives alerts and is there an out-of-hours rota?

**Context**: Alerts on health failure, 5xx > 2% for 5 minutes, availability below target, and reminder lag > 10 minutes need a recipient. No rota is defined in project documents.

| Option | Answer | Implications |
|--------|--------|--------------|
| A | Shared delivery-team channel and email, business hours only | No cost; slow night response; reminders at 20:00 may lag unnoticed overnight |
| B | Named on-call rota including evenings and weekends | Needs team agreement and tooling |
| C | Alert also to the practice manager | Non-technical recipient; noisy |

**Assumed**: A until go-live; revisit the rota before 2027-02-22.
