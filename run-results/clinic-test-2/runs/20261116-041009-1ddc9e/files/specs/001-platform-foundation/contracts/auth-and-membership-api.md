# Contract: Auth, boards and membership API (`/api/v1`, JSON)

Paths and token scheme are assumptions from the implementation contract (A).

| Method | Path | Auth | Purpose | Success | Errors |
|---|---|---|---|---|---|
| POST | /api/v1/auth/register | none | Create a user (email, display_name, password) | 201 user | 409 email taken, 422 invalid |
| POST | /api/v1/auth/login | none | Sign in, returns bearer token | 200 {access_token, token_type, expires_in} | 401 generic failure, 429 locked out |
| GET | /api/v1/auth/me | bearer | Own profile | 200 user | 401 |
| POST | /api/v1/boards | bearer | Create board, caller becomes owner | 201 board | 401, 422 |
| GET | /api/v1/boards | bearer | List boards where caller is a member | 200 [board] | 401 |
| GET | /api/v1/boards/{board_id} | bearer + member | Read board | 200 board | 401, 404 (non-member or unknown) |
| GET | /api/v1/boards/{board_id}/members | bearer + member | List members | 200 [member] | 401, 404 |
| POST | /api/v1/boards/{board_id}/members | bearer + owner | Add existing user (user_id or email, role) | 201 member | 401, 404, 403 not owner, 409 already member |
| DELETE | /api/v1/boards/{board_id}/members/{user_id} | bearer + owner | Remove member | 204 | 401, 404, 403, 409 last owner |
| GET | /healthz | none | Liveness | 200 | |
| GET | /readyz | none | Readiness (database and Redis reachable) | 200 | 503 |

Rules:
- Every route under `/api/v1/boards/{board_id}` depends on `require_board_member`; non-members get 404 with the same body as an unknown board.
- Error bodies never contain task content, password hashes or secrets.
- Tokens are sent as `Authorization: Bearer <token>`.
