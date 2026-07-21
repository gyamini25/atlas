"""Text → vector embedding.

Two backends, selected by settings:

* **live**  — OpenAI embeddings (`ATLAS_EMBEDDING_MODEL`). Real semantic vectors.
* **mock**  — a deterministic local hashing embedder. No network, fully
              reproducible, and good enough to rank a repo's worth of artifacts.
              This is what keeps the offline demo's retrieval *real* rather than
              hard-coded.

Both return L2-normalised vectors so cosine similarity is a plain dot product.
"""

from __future__ import annotations

import hashlib
import math
import re

from atlas.config import get_settings

_LOCAL_DIM = 512
_TOKEN = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]+")


def _normalise(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return vec
    return [x / norm for x in vec]


def _local_embed(text: str) -> list[float]:
    """Deterministic bag-of-tokens hashing embedding.

    Each token is hashed to an index and a sign; we accumulate then L2-normalise.
    Simple, dependency-free, and stable across runs — ideal for a demo.
    """
    vec = [0.0] * _LOCAL_DIM
    tokens = _TOKEN.findall(text.lower())
    for tok in tokens:
        digest = hashlib.md5(tok.encode()).digest()
        idx = int.from_bytes(digest[:4], "little") % _LOCAL_DIM
        sign = 1.0 if digest[4] & 1 else -1.0
        vec[idx] += sign
    return _normalise(vec)


class Embedder:
    """Facade over the active embedding backend."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = None

    def _openai(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=self._settings.openai_api_key)
        return self._client

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts."""
        if not texts:
            return []
        if self._settings.can_call_openai:
            try:
                resp = self._openai().embeddings.create(
                    model=self._settings.embedding_model,
                    input=[t[:8000] for t in texts],
                )
                return [_normalise(list(d.embedding)) for d in resp.data]
            except Exception:
                # Fall through to local embedding rather than failing the index.
                pass
        return [_local_embed(t) for t in texts]

    def embed_one(self, text: str) -> list[float]:
        out = self.embed([text])
        return out[0] if out else []


_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder
