# ADR-002: Storage behind an interface; in-memory default, Postgres+pgvector for production

- **Status:** Accepted
- **Context:** The brief calls for Postgres + pgvector (+ optional Neo4j), but a
  demo must also run with zero setup on a judge's machine.

## Decision

Depend only on a `Store` protocol (`store.py`). Ship two implementations:

- **`InMemoryStore`** — the default: zero external services, deterministic, ideal
  for the demo and tests.
- **`PostgresStore`** (`db/`) — the production path: Postgres + pgvector, selected
  when configured and reachable, with automatic fallback to in-memory so
  infrastructure never breaks the demo.

Neo4j lives behind the same graph-store seam and is opt-in via a compose profile.

## Consequences

- Every engine module (indexer, graph, embeddings, reasoning) is storage-agnostic.
- We can demonstrate the full pipeline offline, then flip to the production stack
  by changing configuration only.
