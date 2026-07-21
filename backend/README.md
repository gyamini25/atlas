# Atlas backend

The FastAPI reasoning engine for Atlas. See the [project README](../README.md) for the
full picture.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
python -m scripts.smoke                       # end-to-end engine check (offline)
uvicorn atlas.api.app:app --port 8787          # the API the extension talks to
```

- `atlas/indexer` — git / tree-sitter / docs → artifacts
- `atlas/graph` — knowledge-graph builder + traversal
- `atlas/embeddings` — retrieval (semantic × graph × recency)
- `atlas/reasoning` — LangGraph pipeline on GPT-5.6 (+ grounded offline mock)
- `atlas/impact`, `atlas/replay` — impact analysis + Decision Replay

Set `ATLAS_LLM_MODE=live` with `OPENAI_API_KEY` for real GPT-5.6; confirm with
`GET /api/verify-llm`.
