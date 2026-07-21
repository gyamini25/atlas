"""The reasoning pipeline (LangGraph).

    collect ──▶ traverse ──▶ reason ──▶ synthesize
   (evidence)  (timeline)   (GPT-5.6)   (AskResult + expansion)

Implemented as an explicit LangGraph `StateGraph` so the stages are inspectable
and composable — and it degrades to a plain sequential run if LangGraph isn't
installed, so the demo never hard-depends on it.

The expansion payload (the "Learn More" content) is computed alongside the first
answer and cached by `answer_id`, so `/ask/{id}/expand` is an instant lookup.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from atlas.embeddings.retriever import retrieve
from atlas.graph import traverse as graph_traverse
from atlas.models.domain import SourceKind
from atlas.models.schemas import (
    AskExpansion,
    AskResult,
    KeyReason,
    Source,
)
from atlas.reasoning.llm import ReasonPayload, get_llm
from atlas.records import Artifact, Evidence
from atlas.store import Store
from atlas.timeline import build_timeline

# answer_id → (AskResult, AskExpansion) so expansion is a cheap second call.
_ANSWER_CACHE: dict[str, tuple[AskResult, AskExpansion]] = {}

_CITEABLE = {"pull_request", "commit", "issue", "adr", "doc", "incident", "slack"}

# How many sources the answer card cites; the full ranked list is kept for expansion.
_MAX_CITED_SOURCES = 6


@dataclass
class _State:
    store: Store
    repo: str
    question: str
    target: str
    root_id: str | None = None
    root: Artifact | None = None
    evidence: list[Evidence] = field(default_factory=list)
    timeline: list = field(default_factory=list)
    payload: ReasonPayload | None = None
    result: AskResult | None = None
    expansion: AskExpansion | None = None


# ─── pipeline stages ─────────────────────────────────────────────────────────
def _collect(state: _State) -> _State:
    node = graph_traverse.find_symbol_node(
        state.store, state.repo, _file_of(state.target), _symbol_of(state.target)
    )
    if node is not None:
        state.root_id = node.id
        state.root = state.store.get_artifact(state.repo, node.id)
    # Retrieve well past what we cite: code symbols outrank narrative artifacts on
    # graph proximity but are not citeable, so a tight top_k starves Sources and
    # Timeline of the PRs/ADRs/incidents that actually explain the code.
    state.evidence = retrieve(state.store, state.repo, state.question, state.root_id, top_k=24)
    return state


def _traverse(state: _State) -> _State:
    state.timeline = build_timeline(state.evidence, state.root)
    return state


def _reason(state: _State) -> _State:
    state.payload = get_llm().reason(state.question, state.target, state.evidence)
    return state


def _synthesize(state: _State) -> _State:
    payload = state.payload
    assert payload is not None
    answer_id = _answer_id(state.repo, state.target, state.question)

    # Cite the top few, but keep the full list: Slack/issue threads routinely rank
    # below the citation cutoff, and "Learn More" should still surface them.
    all_sources = _sources_from(state.evidence, limit=None)
    sources = all_sources[:_MAX_CITED_SOURCES]
    key_reasons = _key_reasons(payload)

    result = AskResult(
        answer_id=answer_id,
        question=state.question,
        target=state.target,
        summary=payload.summary,
        confidence=payload.confidence,
        key_reasons=key_reasons,
        sources=sources,
        timeline_preview=state.timeline[:4],
    )
    expansion = AskExpansion(
        answer_id=answer_id,
        reasoning=payload.reasoning,
        alternatives=payload.alternatives,
        timeline=state.timeline,
        dependencies=payload.dependencies,
        impact_summary=payload.impact_summary,
        related_discussions=[
            s for s in all_sources if s.kind in {SourceKind.SLACK, SourceKind.ISSUE}
        ],
    )
    state.result = result
    state.expansion = expansion
    _ANSWER_CACHE[answer_id] = (result, expansion)
    return state


# ─── graph assembly ──────────────────────────────────────────────────────────
def _run_pipeline(state: _State) -> _State:
    try:
        from langgraph.graph import END, StateGraph

        graph = StateGraph(_State)
        graph.add_node("collect", _collect)
        graph.add_node("traverse", _traverse)
        graph.add_node("reason", _reason)
        graph.add_node("synthesize", _synthesize)
        graph.set_entry_point("collect")
        graph.add_edge("collect", "traverse")
        graph.add_edge("traverse", "reason")
        graph.add_edge("reason", "synthesize")
        graph.add_edge("synthesize", END)
        compiled = graph.compile()
        return compiled.invoke(state)  # type: ignore[return-value]
    except Exception:
        # Sequential fallback — identical semantics without LangGraph.
        return _synthesize(_reason(_traverse(_collect(state))))


# ─── public API ──────────────────────────────────────────────────────────────
def ask(
    store: Store,
    repo: str,
    question: str,
    file: str | None,
    symbol: str,
    line: int | None = None,
) -> AskResult:
    target = f"{file}::{symbol}" if file else symbol
    state = _State(store=store, repo=repo, question=question, target=target)
    state = _ensure_state(_run_pipeline(state))
    assert state.result is not None
    return state.result


def expand(answer_id: str) -> AskExpansion | None:
    cached = _ANSWER_CACHE.get(answer_id)
    return cached[1] if cached else None


# ─── helpers ─────────────────────────────────────────────────────────────────
def _ensure_state(state) -> _State:
    # LangGraph may return a dict-like; normalise back to _State.
    if isinstance(state, _State):
        return state
    if isinstance(state, dict):
        s = _State(
            store=state["store"], repo=state["repo"], question=state["question"], target=state["target"]
        )
        s.result = state.get("result")
        s.expansion = state.get("expansion")
        return s
    return state


def _sources_from(evidence: list[Evidence], limit: int | None = _MAX_CITED_SOURCES) -> list[Source]:
    sources: list[Source] = []
    seen: set[str] = set()
    for ev in evidence:
        a = ev.artifact
        if a.kind.value not in _CITEABLE:
            continue
        try:
            kind = SourceKind(a.kind.value)
        except ValueError:
            continue
        ref = a.meta.get("ref") or a.meta.get("short_sha") or a.id
        if ref in seen:
            continue
        seen.add(ref)
        sources.append(
            Source(
                kind=kind,
                label=a.title[:60],
                ref=ref,
                url=a.url,
                detail=(a.body or "").strip().splitlines()[0][:120] if a.body else None,
            )
        )
        if limit is not None and len(sources) >= limit:
            break
    return sources


def _key_reasons(payload: ReasonPayload) -> list[KeyReason]:
    out: list[KeyReason] = []
    for r in payload.key_reasons:
        kind = None
        raw = r.get("kind")
        if raw:
            try:
                kind = SourceKind(raw)
            except ValueError:
                kind = None
        out.append(KeyReason(label=r.get("label", ""), text=r.get("text", ""), kind=kind))
    return out


def _answer_id(repo: str, target: str, question: str) -> str:
    digest = hashlib.sha1(f"{repo}|{target}|{question}".encode()).hexdigest()
    return digest[:12]


def _file_of(target: str) -> str | None:
    return target.split("::")[0] if "::" in target else None


def _symbol_of(target: str) -> str:
    return target.split("::")[-1]
