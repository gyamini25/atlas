"""Build the Decision Replay for a symbol.

Reuses the same retrieval + timeline machinery as the Ask flow, then turns each
timeline event into a narrated step. Narration is produced by GPT-5.6 in live
mode, or synthesised from the event's kind and content in mock mode — always a
"why", never a "what".
"""

from __future__ import annotations

from atlas.embeddings.retriever import retrieve
from atlas.graph import traverse as graph_traverse
from atlas.models.domain import SourceKind
from atlas.models.schemas import ReplayStep, TimelineEntry
from atlas.reasoning.llm import get_llm
from atlas.store import Store
from atlas.timeline import build_timeline

# Kind → verb used when synthesising narration in mock mode.
_NARRATION = {
    SourceKind.INCIDENT: "A production incident forced a rethink here — {detail}",
    SourceKind.PULL_REQUEST: "This change was deliberately introduced — {detail}",
    SourceKind.ADR: "An architecture decision was recorded — {detail}",
    SourceKind.COMMIT: "The implementation evolved — {detail}",
    SourceKind.ISSUE: "A reported issue drove this — {detail}",
}


def build_replay(store: Store, repo: str, file: str | None, symbol: str) -> list[ReplayStep]:
    node = graph_traverse.find_symbol_node(store, repo, file, symbol)
    root_id = node.id if node else None
    root = store.get_artifact(repo, root_id) if root_id else None

    question = f"How and why did {symbol} evolve over time?"
    evidence = retrieve(store, repo, question, root_id, top_k=12)

    # The evolution story is a history, not just a neighbourhood: enrich with the
    # commits that shaped this symbol's module over time so early milestones
    # (initial implementation, OAuth integration) appear alongside recent ones.
    evidence = _enrich_with_module_history(store, repo, node, symbol, evidence)

    timeline = build_timeline(evidence, root)

    llm = get_llm()
    steps: list[ReplayStep] = []
    for i, entry in enumerate(timeline):
        steps.append(
            ReplayStep(
                order=i,
                date=entry.date,
                title=entry.title,
                narration=_narrate(llm, symbol, entry),
                kind=entry.kind,
                is_incident=entry.is_incident,
                sources=entry.sources,
            )
        )
    return steps


def _enrich_with_module_history(store, repo, node, symbol, evidence):
    """Merge in commits that touched this symbol's module or mention it.

    Uses two grounded signals: commits whose changed files live under the same
    module directory, and commits whose message mentions the symbol or its domain
    keyword (e.g. "auth"). Both come straight from the indexed git history.
    """
    from atlas.records import Evidence

    module_dir = ""
    if node and node.meta.get("path"):
        parts = node.meta["path"].split("/")
        module_dir = "/".join(parts[:-1])  # directory containing the file

    domain = symbol.lower()
    keyword = "auth" if "auth" in domain else domain[:5]

    have = {e.artifact.id for e in evidence}
    extra: list[Evidence] = []
    for a in store.get_artifacts(repo):
        if a.kind.value != "commit" or a.id in have:
            continue
        files = a.meta.get("files", "")
        text = f"{a.title}\n{a.body}".lower()
        in_module = module_dir and any(f.strip().startswith(module_dir) for f in files.split(","))
        mentions = keyword in text or domain in text
        if in_module or mentions:
            extra.append(Evidence(artifact=a, score=0.4, why="module history"))

    return list(evidence) + extra


def _narrate(llm, symbol: str, entry: TimelineEntry) -> str:
    # Prefer a real model narration; fall back to a grounded template.
    context = (
        f"Symbol: {symbol}\nWhen: {entry.date}\nEvent: {entry.title}\nDetail: {entry.detail}\n"
        f"Explain in one sentence WHY this happened."
    )
    live = llm.narrate(context)
    if live:
        return live
    template = _NARRATION.get(entry.kind or SourceKind.COMMIT, "{detail}")
    return template.format(detail=entry.detail)
