# Clarifications: Family members on a patient account

No user was available; each answer below is an assumption and can be changed.

## Q1 (prd Q-007): Can one phone number book for family members?

- **Options**: A. Yes, one account per phone number, the holder books for up to 5 family members (SA-001). B. No, each family member needs their own sign-in on the same phone.
- **Assumed**: A.
- **Why**: It is the PRD default (SA-001, ASM-001) and the account/person split (ADR-0008) already exists. If the client answers B, sign-in and cmp-identity change and MOD-01 grows 2 to 4 person-days (RSK-003); this feature would be reworked. Status in prd.md: open.

## Q2: What does "remove a family member" do when the person has appointments?

- **Options**: A. Refuse while an upcoming booked appointment exists; otherwise mark the person removed and keep the record and past appointments. B. Delete the person and their appointments at once. C. Always allow, and cancel the upcoming appointments.
- **Assumed**: A.
- **Why**: Safest for the patient (no silent cancellations), and keeps appointment history and per-person no-show counts (PD-007). Personal data is removed through erasure on request (NFR-007).

## Q3: Does the limit of 5 include the account holder?

- **Options**: A. No, 5 family members plus the holder. B. Yes, 5 people in total.
- **Assumed**: A.
- **Why**: FR-006 says "add up to 5 family members" and SA-001 says "up to 5 family members".
