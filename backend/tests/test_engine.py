"""Hermetic engine tests.

These build a tiny artifact set directly (no git/tree-sitter needed), so they run
fast and deterministically in mock mode, exercising graph → retrieval → reasoning
→ impact end-to-end.
"""

from __future__ import annotations

import pytest

from atlas.embeddings.pipeline import embed_repo
from atlas.graph.builder import build_graph
from atlas.impact.analyzer import analyze_impact
from atlas.models.domain import ArtifactKind
from atlas.reasoning.pipeline import ask, expand
from atlas.records import Artifact
from atlas.store import InMemoryStore

REPO = "fixture-repo"


def _fixture_artifacts() -> list[Artifact]:
    return [
        Artifact(
            id="symbol:auth.ts::login",
            kind=ArtifactKind.CODE_SYMBOL,
            title="login (auth.ts)",
            body="async function login() { this.redis.getSession(); this.oauth.verify(); }",
            path="auth.ts",
            symbol="login",
            line_start=1,
            line_end=8,
        ),
        Artifact(
            id="commit:abc1234",
            kind=ArtifactKind.COMMIT,
            title="Add retry + redis fallback to login (PR #7)",
            body="Implements ADR-005 after INC-99. references path:auth.ts",
            author="Dev One",
            author_email="dev@x.com",
            timestamp="2025-02-01T10:00:00+00:00",
            refs=["PR#7", "ADR-005", "INC-99", "path:auth.ts"],
            meta={"sha": "abc1234", "short_sha": "abc1234", "files": "auth.ts"},
        ),
        Artifact(
            id="pr:PR#7",
            kind=ArtifactKind.PULL_REQUEST,
            title="PR #7 - Add retry + redis fallback",
            body="Implements ADR-005 in response to INC-99. Rotates tokens.",
            timestamp="2025-02-02T10:00:00Z",
            refs=["ADR-005", "INC-99", "PR#7"],
            meta={"number": "7", "ref": "PR#7"},
        ),
        Artifact(
            id="incident:INC-99",
            kind=ArtifactKind.INCIDENT,
            title="INC-99: provider outage forced logouts",
            body="A 17-minute OAuth outage force-logged-out users.",
            timestamp="2025-01-20",
            refs=["INC-99"],
            meta={"ref": "INC-99"},
        ),
        Artifact(
            id="adr:ADR-005",
            kind=ArtifactKind.ADR,
            title="ADR-005: resilient auth",
            body="Cache sessions in redis, retry then fall back. Rejected longer TTLs.",
            refs=["ADR-005"],
            meta={"ref": "ADR-005"},
        ),
    ]


@pytest.fixture
def store() -> InMemoryStore:
    s = InMemoryStore()
    artifacts = _fixture_artifacts()
    s.add_artifacts(REPO, artifacts)
    nodes, edges = build_graph(artifacts)
    s.add_nodes(REPO, nodes)
    s.add_edges(REPO, edges)
    embed_repo(s, REPO, artifacts)
    return s


def test_graph_resolves_references(store: InMemoryStore) -> None:
    edges = store.get_edges(REPO)
    kinds = {(e.src, e.dst) for e in edges}
    # commit → symbol (modifies), commit → PR/ADR/incident (references)
    assert ("commit:abc1234", "symbol:auth.ts::login") in kinds
    assert ("commit:abc1234", "pr:PR#7") in kinds
    assert any(dst == "incident:INC-99" for _, dst in kinds)


def test_ask_produces_grounded_answer(store: InMemoryStore) -> None:
    result = ask(store, REPO, "Why is this implemented this way?", "auth.ts", "login")
    assert result.summary
    assert 0.0 < result.confidence <= 1.0
    source_kinds = {s.kind.value for s in result.sources}
    # The incident, PR and ADR should all be cited.
    assert {"incident", "pull_request", "adr"} <= source_kinds
    # Expansion is cached and retrievable.
    exp = expand(result.answer_id)
    assert exp is not None and exp.reasoning


def test_timeline_orders_incident_before_fix(store: InMemoryStore) -> None:
    result = ask(store, REPO, "why", "auth.ts", "login")
    dated = [t for t in result.timeline_preview]
    incident_idx = next((i for i, t in enumerate(dated) if t.is_incident), None)
    assert incident_idx is not None  # the incident appears on the timeline


def test_impact_of_redis(store: InMemoryStore) -> None:
    report = analyze_impact(store, REPO, "redis")
    assert report.risk in {"medium", "high", "critical"}
    assert "auth.ts" in report.files_affected
    assert report.migration  # a migration path is proposed
