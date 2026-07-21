# ADR-003: Dual-mode reasoning — live GPT-5.6 and a grounded offline mock

- **Status:** Accepted
- **Context:** The reasoning engine should run on GPT-5.6, but the demo must not
  depend on a network or an API key at the moment it matters most.

## Decision

The LLM facade (`reasoning/llm.py`) supports two modes:

- **`live`** — calls GPT-5.6 with a strict-JSON, citation-grounded contract.
- **`mock`** — synthesises an answer from the *real* retrieved evidence
  (themes, causal chain, confidence derived from evidence agreement), with an
  optional curated override (`seed/traces.json`) for the flagship demo target.

Both modes return the same `ReasonPayload`, so nothing downstream changes.

## Why

- Determinism and resilience for demos and CI.
- Honesty: even the mock is grounded in indexed artifacts and never fabricates the
  citations — confidence tracks the strength of what was actually found.

## Consequences

- The pipeline is testable offline (`scripts/smoke.py`, `tests/`).
- Going live is a one-line config change (`ATLAS_LLM_MODE=live`).
