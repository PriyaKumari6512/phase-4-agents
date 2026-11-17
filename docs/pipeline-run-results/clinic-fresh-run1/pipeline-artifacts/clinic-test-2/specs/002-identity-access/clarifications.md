# Clarifications: Sign-in, roles and staff accounts

No user was available; each question has an assumed answer, used in spec.md, plan.md and tasks.md.

## Q1: One account per phone number with family members (Q-007, SA-001)
- Options: (A) one account per phone number, up to 5 family members booked from it; (B) every family member signs in separately with their own phone; (C) one phone can hold several separate accounts.
- Assumed: A (the PRD default).
- Why: the PRD and architecture (ASM-001, ADR-0008) use A. If the client answers B or C, sign-in and the account/person model change (RSK-003, 2-4 person-days).

## Q2: Per-network-address throttle and daily cap on sign-in codes (thr-001, thr-008)
- Options: (A) 10 code requests per network address per hour and 5 per phone per hour, daily cap of 1,000 codes system-wide; (B) stricter 5 per address per hour, 500 per day; (C) no figures until the SMS cost is known.
- Assumed: A, all as settings that can be changed without a code change.
- Why: PRD gives no figures; about 4,000 messages a week are expected (architecture capacity estimate), so a daily cap of 1,000 codes leaves room for peaks. To be confirmed.

## Q3: How do staff change or reset a forgotten password?
- Options: (A) the practice manager sets a new password for a staff account in the staff screen (no self-service); (B) staff change their own password when signed in, manager resets forgotten ones; (C) email/SMS reset link.
- Assumed: B (own password change when signed in, and manager reset); no email or SMS reset link, because staff have no email in the stored data (NFR-007).
- Why: the PRD says nothing about password recovery; B is the smallest design that works without storing more personal data. The manager's own forgotten password is solved by a break-glass operations procedure outside this feature.
