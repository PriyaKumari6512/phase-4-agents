# Clarifications: Full-text task search

## Q1: Text-search language configuration
- Options: A) English configuration; B) "simple" configuration (no stemming); C) per-board language.
- Assumed: A (English). Why: PRD does not state a language; English is the most common default. Revisit if pilot teams use other languages.

## Q2: Search cache TTL and invalidation
- Options: A) 60 s TTL plus invalidation on board task changes; B) TTL only (30-300 s); C) no cache.
- Assumed: A. Why: architecture says Redis caches search results; PRD gives no TTL; short TTL bounds staleness and invalidation keeps results fresh.

## Q3: Search scope across boards
- Options: A) all of the user's boards by default with optional board filter; B) current board only.
- Assumed: A. Why: FR-4 says "the user's boards".
