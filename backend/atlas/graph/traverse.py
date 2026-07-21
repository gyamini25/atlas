"""Graph traversal.

Builds a NetworkX view over whatever the store holds (backend-agnostic) and
provides the two traversals the engine needs:

  * `neighborhood`  — BFS from a symbol to gather the surrounding evidence
                      (commits, PRs, ADRs, incidents) with hop distance, which
                      the reasoning ranker uses as a proximity signal.
  * `subgraph`      — a bounded projection for the React Flow "Graph" tab.
"""

from __future__ import annotations

from atlas.models.schemas import GraphEdge, GraphNode, SubgraphResponse
from atlas.records import Node
from atlas.store import Store


def _nx_graph(store: Store, repo: str):
    import networkx as nx

    graph = nx.MultiDiGraph()
    for node in store.get_nodes(repo):
        graph.add_node(node.id, **{"kind": node.kind.value, "label": node.label, "meta": node.meta})
    for edge in store.get_edges(repo):
        if graph.has_node(edge.src) and graph.has_node(edge.dst):
            graph.add_edge(edge.src, edge.dst, kind=edge.kind.value)
    return graph


def find_symbol_node(store: Store, repo: str, file: str | None, symbol: str) -> Node | None:
    """Locate the code-symbol node best matching (file, symbol).

    Matching is forgiving: exact id first, then symbol-name + path-suffix, then
    symbol-name alone — because the editor sends a path relative to its own root.
    """
    nodes = store.get_nodes(repo)
    symbol_nodes = [n for n in nodes if n.meta.get("kind") == "code_symbol"]

    if file:
        exact = f"symbol:{file}::{symbol}"
        for n in symbol_nodes:
            if n.id == exact:
                return n
        for n in symbol_nodes:
            if n.meta.get("symbol") == symbol and n.meta.get("path", "").endswith(file):
                return n
        for n in symbol_nodes:
            if n.meta.get("symbol") == symbol and file.endswith(n.meta.get("path", "")):
                return n

    matches = [n for n in symbol_nodes if n.meta.get("symbol") == symbol]
    return matches[0] if matches else None


def neighborhood(store: Store, repo: str, root_id: str, hops: int = 2) -> dict[str, int]:
    """Return {artifact_id: hop_distance} within `hops` of `root_id`.

    Traverses edges in both directions — engineering intent flows both ways
    (a commit points at an ADR; we also want the ADR when starting from the code).
    """
    graph = _nx_graph(store, repo)
    if not graph.has_node(root_id):
        return {}

    undirected = graph.to_undirected(as_view=True)
    import networkx as nx

    lengths = nx.single_source_shortest_path_length(undirected, root_id, cutoff=hops)
    return dict(lengths)


def subgraph(store: Store, repo: str, root_id: str, hops: int = 2) -> SubgraphResponse:
    """Bounded projection around `root_id` for visualisation."""
    graph = _nx_graph(store, repo)
    if not graph.has_node(root_id):
        return SubgraphResponse(root=root_id)

    reachable = set(neighborhood(store, repo, root_id, hops).keys())
    nodes = [
        GraphNode(
            id=n,
            kind=graph.nodes[n]["kind"],
            label=graph.nodes[n]["label"],
            meta=graph.nodes[n].get("meta", {}),
        )
        for n in reachable
    ]
    edges = [
        GraphEdge(source=u, target=v, kind=data["kind"])
        for u, v, data in graph.edges(data=True)
        if u in reachable and v in reachable
    ]
    return SubgraphResponse(root=root_id, nodes=nodes, edges=edges)
