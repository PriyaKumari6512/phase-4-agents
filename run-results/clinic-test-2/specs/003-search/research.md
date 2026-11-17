# Research: Full-text task search

## Decision 1: PostgreSQL full-text search with stored tsvector and GIN index
- Rationale: architecture.md says to use PostgreSQL FTS (GIN) before considering a separate engine; 10,000 tasks is small for GIN.
- Alternatives: separate search engine (rejected by architecture for now); `ILIKE '%x%'` scans (cannot meet p95 as data grows, no ranking).
- Form: generated stored column `search_vector` = setweight(title, 'A') || setweight(description, 'B'), so it never drifts from the data and needs no trigger.

## Decision 2: Text-search configuration `english` (assumption, Q1)
- Rationale: language not specified. Configuration is held in one setting (`SEARCH_TS_CONFIG`) but a generated column bakes it in, so changing it needs a new migration.
- Alternatives: `simple` (no stemming), per-board language (needs a board language attribute that does not exist).

## Decision 3: Query parsing with `websearch_to_tsquery`
- Rationale: accepts free text safely (quotes, `-`, `or`), never raises syntax errors on user input, and values are bound as parameters.
- Alternatives: `plainto_tsquery` (no phrase/OR), `to_tsquery` (syntax errors on user input).

## Decision 4: Membership filter in SQL
- Rationale: `board_id = ANY(:member_board_ids)` using membership from the foundation service; the filter is part of the query so a result can never include foreign tasks. A requested board filter that is not in the member set returns 404.

## Decision 5: Redis cache with TTL 60 s and board version counters (assumption, Q2)
- Key: `search:v1:{sha256(user_id, sorted member board ids, their version counters, normalised query, board filter, limit, offset)}`.
- Invalidation: task create/update/move/delete calls `search_cache.bump_board(board_id)` which increments `search:ver:{board_id}`; old keys expire by TTL. Membership change alters the member board ids in the key, so removed users never get old entries.
- Fallback: any Redis error is logged and the database result is returned.
- Alternatives: delete keys by pattern (needs SCAN, slow); TTL only (stale up to TTL, rejected as less fresh).

## Decision 6: Load test tooling
- Architecture names no load tool. Use a pytest-driven async HTTP load script (`tests/performance/test_search_load.py`) with a seed script for 10,000 tasks; asserts p95 < 300 ms. Tool choice is an assumption and can be swapped.

## Decision 7: Frontend interaction
- Debounced (250 ms, assumed) input; combobox/listbox pattern with arrow keys, Enter, Escape; `aria-live` result count; shortcut `/` focuses the search box (assumed).
