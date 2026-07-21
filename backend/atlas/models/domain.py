"""Core domain vocabulary: the node, edge, artifact, and source kinds that make
up the engineering-memory graph.

Keeping these as string enums means they serialise cleanly to JSON for the
webview and to labels for the graph store.
"""

from __future__ import annotations

from enum import Enum


class ArtifactKind(str, Enum):
    """A raw piece of engineering evidence pulled from the repository."""

    COMMIT = "commit"
    PULL_REQUEST = "pull_request"
    ISSUE = "issue"
    ADR = "adr"
    DOC = "doc"
    COMMENT = "comment"
    INCIDENT = "incident"
    SLACK = "slack"
    CODE_SYMBOL = "code_symbol"
    TEST = "test"


class NodeKind(str, Enum):
    """Node types in the knowledge graph."""

    DEVELOPER = "developer"
    COMMIT = "commit"
    PULL_REQUEST = "pull_request"
    ISSUE = "issue"
    CODE_SYMBOL = "code_symbol"
    TEST = "test"
    DOC = "doc"
    ADR = "adr"
    INCIDENT = "incident"
    DISCUSSION = "discussion"


class EdgeKind(str, Enum):
    """Relationship types connecting graph nodes.

    The graph is intentionally directional so traversals read like sentences:
    developer --authored--> commit --modifies--> code_symbol.
    """

    AUTHORED = "authored"
    MODIFIES = "modifies"
    REFERENCES = "references"
    DECIDES = "decides"
    TESTS = "tests"
    DEPENDS_ON = "depends_on"
    SUPERSEDES = "supersedes"
    RESOLVES = "resolves"
    DISCUSSES = "discusses"


class SourceKind(str, Enum):
    """Citation categories the webview renders as typed chips.

    These map to the icons in the Atlas panel (GitHub PR, ⚠ incident, 📄 ADR, Slack).
    """

    PULL_REQUEST = "pull_request"
    COMMIT = "commit"
    ISSUE = "issue"
    ADR = "adr"
    DOC = "doc"
    INCIDENT = "incident"
    SLACK = "slack"


# Which artifact kinds are eligible to become graph nodes of a given kind.
ARTIFACT_TO_NODE: dict[ArtifactKind, NodeKind] = {
    ArtifactKind.COMMIT: NodeKind.COMMIT,
    ArtifactKind.PULL_REQUEST: NodeKind.PULL_REQUEST,
    ArtifactKind.ISSUE: NodeKind.ISSUE,
    ArtifactKind.ADR: NodeKind.ADR,
    ArtifactKind.DOC: NodeKind.DOC,
    ArtifactKind.INCIDENT: NodeKind.INCIDENT,
    ArtifactKind.SLACK: NodeKind.DISCUSSION,
    ArtifactKind.CODE_SYMBOL: NodeKind.CODE_SYMBOL,
    ArtifactKind.TEST: NodeKind.TEST,
}
