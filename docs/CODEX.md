# Building Atlas with GPT-5.6 + Codex

Atlas was designed and built with OpenAI's tools in two distinct roles — one at
**runtime**, one during **development**. This document is the honest record of
how each was used, for the Build Week submission.

## GPT-5.6 — the product's runtime intelligence

GPT-5.6 *is* the reasoning engine. It is not a wrapper around search; it sits at
the end of a deliberate pipeline that first assembles evidence and only then reasons:

```
collect evidence ─▶ rank (semantic × graph proximity × recency) ─▶ traverse graph
   ─▶ identify decisions & tradeoffs (GPT-5.6) ─▶ explain (GPT-5.6) ─▶ cite
```

- **Where GPT-5.6 does the work:** `backend/atlas/reasoning/` — it turns a ranked
  set of real artifacts (commits, PRs, ADRs, incidents, Slack) into a first-person,
  confidence-scored explanation of *why* code exists, and narrates Decision Replay.
- **Grounding:** the prompts (`reasoning/prompts.py`) forbid inventing artifacts and
  require the confidence to track evidence strength — so the model reasons, it doesn't
  hallucinate history.
- **Offline determinism:** a `mock` mode synthesises the same shape of answer from the
  *real* retrieved evidence, so the pipeline is demonstrable without a network. Set
  `ATLAS_LLM_MODE=live` + `OPENAI_API_KEY` to run on GPT-5.6.

## Codex — the development accelerator

Codex was used to explore the design space and move fast on the mechanical parts,
which let the human effort concentrate on architecture and product judgement.

Representative places Codex accelerated the build:

- **Scaffolding & boilerplate:** the FastAPI surface, pydantic schemas, and the
  TypeScript ⇄ Python type mirroring between `backend/atlas/models` and
  `extension/webview/src/types.ts`.
- **Parsers:** the tree-sitter symbol walker (`indexer/code_parser.py`) and the
  reference-extraction regexes (`indexer/refs.py`) that turn "fixes #284 / see ADR-012"
  into graph edges.
- **The webview design system:** translating the product mockup into the VS Code
  theme-aware CSS and React components (Ask / Timeline / Graph / Impact).
- **Exploration:** comparing storage options (in-memory vs Postgres+pgvector vs Neo4j)
  and the evidence-ranking formula before committing to the design recorded in
  `docs/adr/`.

Architectural decisions — the knowledge-graph schema, the collect→rank→traverse→reason
pipeline, and the honesty guardrails — were human-owned and are documented as ADRs, with
Codex used to prototype and pressure-test the options.

> **Codex Session ID:** _(add the session id from `/feedback` where core functionality
> was built, per the submission requirements)._
