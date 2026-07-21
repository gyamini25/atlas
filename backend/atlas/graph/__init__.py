"""The engineering-memory knowledge graph.

`builder.py`  turns artifacts into typed nodes + edges by resolving the
              cross-references people leave in commits, PRs, ADRs and incidents.
`traverse.py` walks that graph to gather the evidence neighbourhood around a
              code symbol, and to project subgraphs for the React Flow view.
"""
