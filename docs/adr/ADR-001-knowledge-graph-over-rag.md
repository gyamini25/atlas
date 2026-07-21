# ADR-001: An engineering-memory knowledge graph, not plain RAG

- **Status:** Accepted
- **Context:** Atlas must answer *why* code exists, which is fundamentally a
  question about causal chains (incident → decision → commit → code), not about
  document similarity.

## Decision

Build a typed **knowledge graph** (developer → decision → commit → code → test →
incident → doc) and make **graph proximity** a first-class retrieval signal
alongside semantic similarity and recency. The reasoning engine traverses this
graph to assemble the causal chain before the LLM explains it.

## Why not plain RAG

Nearest-neighbour retrieval surfaces documents that *look* similar to the question,
but the artifact that explains *why* a function exists is often not textually
similar to it — it's the incident two hops away. A pure-vector approach misses
that chain. The graph makes the chain explicit.

## Consequences

- We maintain a graph builder (`graph/builder.py`) that resolves references
  (`PR#842`, `ADR-012`, `INC-284`, commit shas, file paths) into edges.
- Retrieval fuses three signals (`embeddings/retriever.py`).
- The graph is also directly useful as a product surface (the Graph tab).
