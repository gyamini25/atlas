"""Storage abstraction for Atlas.

The rest of the engine depends only on the `Store` protocol, never on a concrete
backend. Two implementations exist:

* `InMemoryStore` — zero external dependencies; the default so the demo runs with
  nothing but `uvicorn`. Fast, deterministic, perfect for a hackathon walkthrough.
* `PostgresStore` (atlas.db.store) — the production path: Postgres + pgvector.

The backend is chosen at process start by `get_store()` based on settings and
whether Postgres is actually reachable, so a missing database degrades to the
in-memory path instead of crashing the demo.
"""

from __future__ import annotations

import math
from typing import Protocol, runtime_checkable

from atlas.config import get_settings
from atlas.models.domain import EdgeKind
from atlas.models.schemas import IndexJob
from atlas.records import Artifact, Edge, Evidence, Node


@runtime_checkable
class Store(Protocol):
    """Persistence contract shared by every backend."""

    # ── artifacts ────────────────────────────────────────────────────────────
    def add_artifacts(self, repo: str, artifacts: list[Artifact]) -> None: ...
    def get_artifacts(self, repo: str) -> list[Artifact]: ...
    def get_artifact(self, repo: str, artifact_id: str) -> Artifact | None: ...

    # ── graph ────────────────────────────────────────────────────────────────
    def add_nodes(self, repo: str, nodes: list[Node]) -> None: ...
    def add_edges(self, repo: str, edges: list[Edge]) -> None: ...
    def get_nodes(self, repo: str) -> list[Node]: ...
    def get_edges(self, repo: str) -> list[Edge]: ...

    # ── embeddings ───────────────────────────────────────────────────────────
    def add_embedding(self, repo: str, artifact_id: str, vector: list[float]) -> None: ...
    def vector_search(self, repo: str, query: list[float], top_k: int) -> list[Evidence]: ...
    def keyword_search(self, repo: str, terms: list[str], top_k: int) -> list[Evidence]: ...

    # ── jobs ─────────────────────────────────────────────────────────────────
    def put_job(self, job: IndexJob) -> None: ...
    def get_job(self, job_id: str) -> IndexJob | None: ...

    def repos(self) -> list[str]: ...


def _cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length vectors (pure Python)."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class InMemoryStore:
    """A simple, process-local store. Everything is kept in dicts keyed by repo."""

    def __init__(self) -> None:
        self._artifacts: dict[str, dict[str, Artifact]] = {}
        self._nodes: dict[str, dict[str, Node]] = {}
        self._edges: dict[str, list[Edge]] = {}
        self._vectors: dict[str, dict[str, list[float]]] = {}
        self._jobs: dict[str, IndexJob] = {}

    # ── artifacts ────────────────────────────────────────────────────────────
    def add_artifacts(self, repo: str, artifacts: list[Artifact]) -> None:
        bucket = self._artifacts.setdefault(repo, {})
        for a in artifacts:
            bucket[a.id] = a

    def get_artifacts(self, repo: str) -> list[Artifact]:
        return list(self._artifacts.get(repo, {}).values())

    def get_artifact(self, repo: str, artifact_id: str) -> Artifact | None:
        return self._artifacts.get(repo, {}).get(artifact_id)

    # ── graph ────────────────────────────────────────────────────────────────
    def add_nodes(self, repo: str, nodes: list[Node]) -> None:
        bucket = self._nodes.setdefault(repo, {})
        for n in nodes:
            bucket[n.id] = n

    def add_edges(self, repo: str, edges: list[Edge]) -> None:
        self._edges.setdefault(repo, []).extend(edges)

    def get_nodes(self, repo: str) -> list[Node]:
        return list(self._nodes.get(repo, {}).values())

    def get_edges(self, repo: str) -> list[Edge]:
        return list(self._edges.get(repo, []))

    # ── embeddings ───────────────────────────────────────────────────────────
    def add_embedding(self, repo: str, artifact_id: str, vector: list[float]) -> None:
        self._vectors.setdefault(repo, {})[artifact_id] = vector

    def vector_search(self, repo: str, query: list[float], top_k: int) -> list[Evidence]:
        scored: list[Evidence] = []
        vectors = self._vectors.get(repo, {})
        for artifact_id, vec in vectors.items():
            artifact = self.get_artifact(repo, artifact_id)
            if artifact is None:
                continue
            score = _cosine(query, vec)
            scored.append(Evidence(artifact=artifact, score=score, why="semantic match"))
        scored.sort(key=lambda e: e.score, reverse=True)
        return scored[:top_k]

    def keyword_search(self, repo: str, terms: list[str], top_k: int) -> list[Evidence]:
        """Lexical fallback used when embeddings are unavailable (mock mode)."""
        needles = [t.lower() for t in terms if t]
        scored: list[Evidence] = []
        for artifact in self.get_artifacts(repo):
            text = artifact.searchable_text().lower()
            hits = sum(text.count(n) for n in needles)
            if hits:
                scored.append(Evidence(artifact=artifact, score=float(hits), why="keyword match"))
        scored.sort(key=lambda e: e.score, reverse=True)
        return scored[:top_k]

    # ── jobs ─────────────────────────────────────────────────────────────────
    def put_job(self, job: IndexJob) -> None:
        self._jobs[job.job_id] = job

    def get_job(self, job_id: str) -> IndexJob | None:
        return self._jobs.get(job_id)

    def repos(self) -> list[str]:
        return list(self._artifacts.keys())

    # ── traversal helper (used by the graph module) ──────────────────────────
    def neighbors(self, repo: str, node_id: str) -> list[tuple[Edge, Node]]:
        """Return (edge, node) pairs adjacent to `node_id` in either direction."""
        out: list[tuple[Edge, Node]] = []
        nodes = self._nodes.get(repo, {})
        for edge in self._edges.get(repo, []):
            if edge.src == node_id and edge.dst in nodes:
                out.append((edge, nodes[edge.dst]))
            elif edge.dst == node_id and edge.src in nodes:
                out.append((edge, nodes[edge.src]))
        return out


_store: Store | None = None


def get_store() -> Store:
    """Return the process-wide store, constructing it on first use.

    Selection order:
      1. ATLAS_STORE=postgres (or graph/db configured) and Postgres reachable → PostgresStore
      2. otherwise → InMemoryStore (always works)
    """
    global _store
    if _store is not None:
        return _store

    settings = get_settings()
    # Postgres is opt-in and best-effort; any failure falls back to memory so the
    # demo never dies on infrastructure.
    if settings.database_url and settings.llm_mode == "live":
        try:
            from atlas.db.store import PostgresStore

            _store = PostgresStore(settings.database_url)
            return _store
        except Exception:  # pragma: no cover - infra optional
            pass

    _store = InMemoryStore()
    return _store


def reset_store() -> None:
    """Testing/demo helper to drop all in-memory state."""
    global _store
    _store = None
