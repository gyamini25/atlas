"""The reasoning engine.

This is where Atlas stops being a search index and starts *reasoning*. A
LangGraph pipeline collects evidence, ranks it, traverses the memory graph,
identifies the engineering decisions and tradeoffs, then synthesises a
first-person explanation with a calibrated confidence score and real citations.

`llm.py`      — GPT-5.6 in live mode; a grounded, deterministic synthesiser in
                mock mode so the demo reasons offline over real retrieved evidence.
`prompts.py`  — the structured prompts that make the model cite, not hallucinate.
`pipeline.py` — the LangGraph state machine tying the stages together.
"""
