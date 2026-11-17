# Clarifications: Comments and @mentions

No user was available; the most reasonable option was assumed for each question.

## Q1: How is `@name` matched?
- Options: (A) unique username; (B) display name; (C) either, with a disambiguation step.
- Assumed: A. Case-insensitive match on the username among the board's members.
- Why: usernames are unique and have no spaces, so parsing is unambiguous; display names can collide. prd.md does not define it.

## Q2: What happens when the mentioned person is not a board member?
- Options: (A) comment saved, plain text, no notification; (B) comment rejected; (C) mention triggers an invitation to the board.
- Assumed: A.
- Why: NFR-3 forbids notifying or exposing non-members; rejecting would reveal who is a user; invitations are out of scope.

## Q3: Can comments be edited or deleted?
- Options: (A) not in this release; (B) author can edit and delete.
- Assumed: A.
- Why: prd.md names only posting and mentioning. Editing would raise the question of re-notifying mentions.
