"""Knowledge-graph construction.

Given the flat list of artifacts from the indexer, we produce a directed graph
whose edges encode engineering relationships. The core trick is a *reference
index*: every artifact exposes stable ids for what it points at (PR#842,
ADR-012, INC-284, a commit sha, a file path), and we resolve those into edges.

The result reads like institutional memory:

    developer --authored--> commit --modifies--> symbol
                              |--references--> PR --decides--> ADR
                                               |--resolves--> incident
"""

from __future__ import annotations

from atlas.models.domain import ARTIFACT_TO_NODE, ArtifactKind, EdgeKind, NodeKind
from atlas.records import Artifact, Edge, Node


def _developer_id(name: str, email: str) -> str:
    return f"dev:{(email or name).strip().lower()}"


def _edge_kind(src_kind: ArtifactKind, dst_node: NodeKind) -> EdgeKind:
    """Infer the relationship between an artifact and a referenced node."""
    if dst_node == NodeKind.CODE_SYMBOL:
        return EdgeKind.MODIFIES
    if src_kind == ArtifactKind.PULL_REQUEST:
        if dst_node in {NodeKind.ADR}:
            return EdgeKind.DECIDES
        if dst_node in {NodeKind.ISSUE, NodeKind.INCIDENT}:
            return EdgeKind.RESOLVES
    if src_kind == ArtifactKind.ADR and dst_node == NodeKind.ADR:
        return EdgeKind.SUPERSEDES
    if dst_node in {NodeKind.DISCUSSION}:
        return EdgeKind.DISCUSSES
    return EdgeKind.REFERENCES


def build_graph(artifacts: list[Artifact]) -> tuple[list[Node], list[Edge]]:
    """Return (nodes, edges) for the given artifacts."""
    nodes: dict[str, Node] = {}
    edges: list[Edge] = []

    # ── 1. a node per artifact ───────────────────────────────────────────────
    for a in artifacts:
        node_kind = ARTIFACT_TO_NODE.get(a.kind, NodeKind.DOC)
        nodes[a.id] = Node(
            id=a.id,
            kind=node_kind,
            label=a.title,
            meta={
                "kind": a.kind.value,
                "path": a.path or "",
                "symbol": a.symbol or "",
                "timestamp": a.timestamp,
                "ref": a.meta.get("ref", ""),
                "url": a.url or "",
            },
        )

    # ── 2. reference index: normalised ref → artifact id ─────────────────────
    ref_index: dict[str, str] = {}
    path_index: dict[str, list[str]] = {}
    for a in artifacts:
        # By explicit ref label (ADR-012, INC-284, PR#842, ISSUE#12).
        if a.meta.get("ref"):
            ref_index[a.meta["ref"]] = a.id
        number = a.meta.get("number")
        if a.kind == ArtifactKind.PULL_REQUEST and number:
            ref_index[f"PR#{number}"] = a.id
        # By commit sha (full + short).
        if a.kind == ArtifactKind.COMMIT:
            sha = a.meta.get("sha", "")
            if sha:
                ref_index[sha] = a.id
                ref_index[sha[:8]] = a.id
                ref_index[sha[:7]] = a.id
        # By file path (for commit --modifies--> symbol resolution).
        if a.kind == ArtifactKind.CODE_SYMBOL and a.path:
            path_index.setdefault(a.path, []).append(a.id)

    # ── 3. developers + authorship edges ─────────────────────────────────────
    for a in artifacts:
        if a.kind in {ArtifactKind.COMMIT, ArtifactKind.PULL_REQUEST} and (a.author or a.author_email):
            dev_id = _developer_id(a.author, a.author_email)
            if dev_id not in nodes:
                nodes[dev_id] = Node(
                    id=dev_id,
                    kind=NodeKind.DEVELOPER,
                    label=a.author or a.author_email,
                    meta={"email": a.author_email},
                )
            edges.append(Edge(src=dev_id, dst=a.id, kind=EdgeKind.AUTHORED))

    # ── 4. reference edges ───────────────────────────────────────────────────
    for a in artifacts:
        for ref in a.refs:
            targets: list[str] = []
            if ref.startswith("path:"):
                targets = path_index.get(ref[len("path:") :], [])
            elif ref in ref_index:
                targets = [ref_index[ref]]
            for target_id in targets:
                if target_id == a.id or target_id not in nodes:
                    continue
                dst_kind = nodes[target_id].kind
                edges.append(
                    Edge(src=a.id, dst=target_id, kind=_edge_kind(a.kind, dst_kind))
                )

    # De-duplicate edges (same src/dst/kind can be produced twice).
    seen: set[tuple[str, str, str]] = set()
    unique_edges: list[Edge] = []
    for e in edges:
        key = (e.src, e.dst, e.kind.value)
        if key not in seen:
            seen.add(key)
            unique_edges.append(e)

    return list(nodes.values()), unique_edges
