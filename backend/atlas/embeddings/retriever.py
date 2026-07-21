"""Evidence retrieval — the collect + rank stages of the reasoning pipeline.

A single similarity search is not enough to explain *why* code exists; the answer
usually lives one or two hops away in the graph (the PR that changed it, the
incident that motivated the PR). So we fuse three orthogonal signals:

    score = w_sem · semantic_similarity
          + w_graph · graph_proximity        (closer in the memory graph = better)
          + w_recency · recency              (recent decisions explain current code)

This deliberately is *not* plain RAG: the graph proximity term is what pulls in
the causal chain the LLM then reasons over.
"""

from __future__ import annotations

import re

from atlas.embeddings.embedder import get_embedder
from atlas.graph import traverse
from atlas.records import Evidence
from atlas.store import Store

_W_SEM = 0.5
_W_GRAPH = 0.35
_W_RECENCY = 0.15

_YEAR = re.compile(r"(20\d{2})")


def _recency(timestamp: str, min_year: int, max_year: int) -> float:
    match = _YEAR.search(timestamp or "")
    if not match or max_year == min_year:
        return 0.3
    year = int(match.group(1))
    return max(0.0, min(1.0, (year - min_year) / (max_year - min_year)))


def retrieve(
    store: Store,
    repo: str,
    query: str,
    root_id: str | None,
    top_k: int = 8,
) -> list[Evidence]:
    """Return the top-k ranked evidence artifacts for a question."""
    embedder = get_embedder()

    # ── semantic ─────────────────────────────────────────────────────────────
    query_vec = embedder.embed_one(query)
    semantic = store.vector_search(repo, query_vec, top_k=top_k * 3)
    sem_scores = {e.artifact.id: e.score for e in semantic}

    # Keyword fallback ensures explicit refs in the question (e.g. "Redis") match.
    terms = re.findall(r"[A-Za-z_]{3,}", query)
    for e in store.keyword_search(repo, terms, top_k=top_k * 2):
        sem_scores.setdefault(e.artifact.id, min(1.0, 0.4 + 0.1 * e.score))

    # ── graph proximity ──────────────────────────────────────────────────────
    distances: dict[str, int] = {}
    if root_id:
        distances = traverse.neighborhood(store, repo, root_id, hops=2)

    # ── assemble candidate set ───────────────────────────────────────────────
    candidate_ids = set(sem_scores) | set(distances)
    candidate_ids.discard(root_id or "")

    artifacts = {a.id: a for a in store.get_artifacts(repo)}
    years = [int(m.group(1)) for a in artifacts.values() if (m := _YEAR.search(a.timestamp or ""))]
    min_year, max_year = (min(years), max(years)) if years else (2000, 2000)

    scored: list[Evidence] = []
    for artifact_id in candidate_ids:
        artifact = artifacts.get(artifact_id)
        if artifact is None:
            continue
        sem = sem_scores.get(artifact_id, 0.0)
        dist = distances.get(artifact_id)
        graph_score = 1.0 / (1 + dist) if dist is not None else 0.0
        recency = _recency(artifact.timestamp, min_year, max_year)

        score = _W_SEM * sem + _W_GRAPH * graph_score + _W_RECENCY * recency
        why = _describe(sem, dist, recency)
        scored.append(Evidence(artifact=artifact, score=score, why=why))

    scored.sort(key=lambda e: e.score, reverse=True)
    return scored[:top_k]


def _describe(sem: float, dist: int | None, recency: float) -> str:
    parts: list[str] = []
    if sem > 0.15:
        parts.append("semantically relevant")
    if dist is not None:
        parts.append(f"{dist} hop(s) from the code in the memory graph")
    if recency > 0.66:
        parts.append("recent")
    return ", ".join(parts) or "related"
