# Quickstart: validating task search

Prerequisites: taskflow-api running with PostgreSQL 16 and Redis 7 (dev environment), migrations applied (`alembic upgrade head`), two users on different boards.

1. Functional: create tasks with "invoice" in a title and "migration" in a description; call `GET /api/v1/search/tasks?q=invoice` as a member and check results, ranking and the excerpt (see [contracts/search-api.md](contracts/search-api.md)).
2. Authorization: repeat as a user on another board; expect no results and 404 for a foreign `board_id`.
3. Cache: repeat a query and check `X-Search-Cache: hit`; edit a task and check the next response is `miss` and fresh. Stop Redis and confirm results still return.
4. Performance: run the seed script then the load test in `tests/performance/` (10,000 tasks); expect p95 < 300 ms and errors below 1%.
5. UI: in taskflow-web, use only the keyboard (`/`, type, arrows, Enter, Escape) to find and open a task; run the accessibility test.

Entities: see [data-model.md](data-model.md).
