"""Prompt construction for the reasoning engine.

The prompts enforce two non-negotiables from the product spec:
  1. Answer in the first person — "I believe this exists because…", not
     "I found a document that says…".
  2. Ground every claim in the supplied evidence and never invent artifacts,
     incidents or decisions. Confidence must reflect the strength of evidence.
"""

from __future__ import annotations

import json

from atlas.records import Evidence

SYSTEM_PROMPT = """You are Atlas, an engineering-memory engine that reconstructs WHY code exists.

You are given a code symbol and a ranked set of EVIDENCE artifacts mined from a real
repository: commits, pull requests, issues, ADRs, incident reports, docs and chat threads.

Your job is to explain the ENGINEERING INTENT behind the code — the decisions, the
tradeoffs, and the events that shaped it — not to describe what the code does.

Rules:
- Reason in the first person: "I believe this implementation exists because…".
- Ground every claim in the provided evidence. Never invent PRs, incidents, ADRs or dates.
- If the evidence is thin, say so and lower your confidence accordingly.
- Prefer causal explanations: incident → decision → code change.
- Return STRICT JSON matching the requested schema. No prose outside the JSON.
"""

RESPONSE_SCHEMA = {
    "summary": "one or two sentences: the core reason this code exists",
    "confidence": "float 0..1 reflecting evidence strength",
    "key_reasons": [
        {"label": "short label e.g. 'Incident #284 (Mar 2025)'", "text": "the reason",
         "kind": "one of pull_request|commit|issue|adr|doc|incident|slack or null"}
    ],
    "reasoning": "first-person paragraph explaining the causal chain",
    "alternatives": ["engineering alternatives that were considered or rejected"],
    "dependencies": ["systems/modules this code depends on"],
    "impact_summary": "one line on what would break if this changed",
}


def build_user_prompt(
    question: str, target: str, evidence: list[Evidence]
) -> str:
    lines = [
        f"CODE SYMBOL: {target}",
        f"QUESTION: {question}",
        "",
        "EVIDENCE (ranked, most relevant first):",
    ]
    for i, ev in enumerate(evidence, 1):
        a = ev.artifact
        header = f"[{i}] ({a.kind.value}) {a.title}"
        if a.timestamp:
            header += f"  — {a.timestamp}"
        lines.append(header)
        lines.append(f"    why-retrieved: {ev.why}")
        body = (a.body or "").strip().replace("\n", " ")
        if body:
            lines.append(f"    content: {body[:600]}")
    lines.append("")
    lines.append("Return JSON with exactly these fields:")
    lines.append(json.dumps(RESPONSE_SCHEMA, indent=2))
    return "\n".join(lines)


NARRATION_SYSTEM = """You are Atlas narrating the evolution of a piece of code for a
cinematic "Decision Replay". For each timeline step, write ONE sentence that explains
WHY the change happened — the motivation, not the mechanics. Be concrete and grounded
in the provided context. First person is fine."""
