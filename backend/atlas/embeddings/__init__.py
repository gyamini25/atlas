"""Embedding + retrieval pipeline.

`embedder.py`  produces vectors — OpenAI in live mode, a deterministic local
               hashing embedder in mock mode (so retrieval is real and offline).
`pipeline.py`  embeds a repository's artifacts into the store.
`retriever.py` implements collect+rank: fuse semantic similarity, graph proximity
               and recency into a ranked evidence set for the reasoning engine.
"""
