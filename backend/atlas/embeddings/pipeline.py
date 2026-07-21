"""Embed a repository's artifacts into the store.

We embed the retrieval-relevant artifacts (the "why" evidence: commits, PRs,
ADRs, incidents, docs, discussions, and code symbols). Batched to keep OpenAI
calls efficient in live mode.
"""

from __future__ import annotations

from atlas.embeddings.embedder import get_embedder
from atlas.records import Artifact
from atlas.store import Store

_BATCH = 64


def embed_repo(store: Store, repo: str, artifacts: list[Artifact]) -> None:
    embedder = get_embedder()
    batch: list[Artifact] = []

    def flush() -> None:
        if not batch:
            return
        vectors = embedder.embed([a.searchable_text() for a in batch])
        for artifact, vector in zip(batch, vectors):
            store.add_embedding(repo, artifact.id, vector)
        batch.clear()

    for artifact in artifacts:
        if not artifact.searchable_text():
            continue
        batch.append(artifact)
        if len(batch) >= _BATCH:
            flush()
    flush()
