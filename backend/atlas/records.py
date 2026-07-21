"""Internal persistence records.

These are the shapes that flow between the indexer, the graph builder, the
embedder, and the reasoning engine. They are deliberately separate from the
API schemas in `atlas.models` — internal records can change freely without
touching the webview contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from atlas.models.domain import ArtifactKind, EdgeKind, NodeKind


@dataclass
class Artifact:
    """A single piece of engineering evidence extracted from a repository.

    One `Artifact` covers commits, PRs, issues, ADRs, docs, comments, incidents,
    Slack messages, code symbols and tests — the `kind` field disambiguates and
    `meta` carries kind-specific extras.
    """

    id: str
    kind: ArtifactKind
    title: str
    body: str = ""
    author: str = ""
    author_email: str = ""
    # ISO-8601 string; kept as text so it round-trips through JSON untouched.
    timestamp: str = ""
    path: str | None = None
    symbol: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    url: str | None = None
    # Free-form references this artifact makes to others, e.g. ["PR#842",
    # "INC-284", "ADR-012", "<commit sha>"]. Resolved into edges by the graph builder.
    refs: list[str] = field(default_factory=list)
    meta: dict[str, str] = field(default_factory=dict)

    def searchable_text(self) -> str:
        """Concatenated text used for embedding + keyword retrieval."""
        parts = [self.title, self.body]
        if self.symbol:
            parts.append(self.symbol)
        if self.path:
            parts.append(self.path)
        return "\n".join(p for p in parts if p).strip()


@dataclass
class Node:
    """A knowledge-graph node."""

    id: str
    kind: NodeKind
    label: str
    meta: dict[str, str] = field(default_factory=dict)


@dataclass
class Edge:
    """A directed knowledge-graph edge."""

    src: str
    dst: str
    kind: EdgeKind
    meta: dict[str, str] = field(default_factory=dict)


@dataclass
class Evidence:
    """An artifact retrieved for a query, with a relevance score and rationale."""

    artifact: Artifact
    score: float
    why: str = ""  # why this evidence was retrieved (semantic / graph / recency)
