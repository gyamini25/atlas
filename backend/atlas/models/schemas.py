"""API request/response schemas.

The webview consumes these verbatim, so field names here are the UI contract.
Every user-facing answer is designed for progressive disclosure: `AskResult`
is the lightweight first response; `AskExpansion` is the "Learn More" payload.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from atlas.models.domain import SourceKind


# ─── Indexing ────────────────────────────────────────────────────────────────
class IndexRequest(BaseModel):
    """Ask Atlas to index a repository."""

    repo_path: str | None = Field(
        default=None, description="Absolute path to a local git repository."
    )
    repo_url: str | None = Field(
        default=None, description="Remote git URL to clone and index."
    )
    github_token: str | None = Field(
        default=None, description="Optional token to enrich with PRs/issues."
    )


class IndexJob(BaseModel):
    """Status of an indexing job."""

    job_id: str
    repo: str
    status: str  # queued | cloning | parsing | graphing | embedding | done | error
    progress: float = 0.0
    detail: str = ""
    counts: dict[str, int] = Field(default_factory=dict)
    error: str | None = None


# ─── Citations ───────────────────────────────────────────────────────────────
class Source(BaseModel):
    """A cited artifact, rendered as a typed chip in the Atlas panel."""

    kind: SourceKind
    label: str  # e.g. "PR #842 - Add retry logic"
    ref: str  # stable id, e.g. commit sha / "PR#842" / "ADR-012"
    url: str | None = None  # deep link when available
    detail: str | None = None  # short tooltip / one-liner


# ─── Ask ─────────────────────────────────────────────────────────────────────
class KeyReason(BaseModel):
    """One checkmark-bulleted reason in the answer card."""

    label: str  # e.g. "Incident #284 (Mar 2025)"
    text: str  # the reason itself
    kind: SourceKind | None = None  # drives the bullet icon/accent


class AskResult(BaseModel):
    """The first, lightweight answer: summary + confidence + sources.

    Deliberately small — the panel shows this immediately and defers everything
    heavy to `AskExpansion`.
    """

    answer_id: str
    question: str
    target: str  # "auth.service.ts::authenticateUser"
    summary: str
    confidence: float  # 0..1
    key_reasons: list[KeyReason] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    timeline_preview: list[TimelineEntry] = Field(default_factory=list)


class TimelineEntry(BaseModel):
    """A node on the decision timeline (preview + full replay share this shape)."""

    date: str  # "2022", "Mar 2025"
    title: str  # "Retry logic added"
    detail: str  # one-line WHY
    kind: SourceKind | None = None
    is_incident: bool = False  # renders as a red node
    sources: list[Source] = Field(default_factory=list)


class AskExpansion(BaseModel):
    """The "Learn More" payload — the full reasoning behind an `AskResult`."""

    answer_id: str
    reasoning: str  # first-person, "I believe this exists because…"
    alternatives: list[str] = Field(default_factory=list)
    timeline: list[TimelineEntry] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    impact_summary: str = ""
    related_discussions: list[Source] = Field(default_factory=list)


# ─── Replay ──────────────────────────────────────────────────────────────────
class ReplayStep(BaseModel):
    """One cinematic step in Decision Replay. Narration explains WHY, not WHAT."""

    order: int
    date: str
    title: str
    narration: str
    kind: SourceKind | None = None
    is_incident: bool = False
    sources: list[Source] = Field(default_factory=list)


# ─── Impact ──────────────────────────────────────────────────────────────────
class ImpactReport(BaseModel):
    """Blast-radius analysis for removing/changing a dependency or symbol."""

    target: str
    risk: str  # low | medium | high | critical
    confidence: float
    summary: str
    files_affected: list[str] = Field(default_factory=list)
    services_affected: list[str] = Field(default_factory=list)
    tests_affected: list[str] = Field(default_factory=list)
    likely_failures: list[str] = Field(default_factory=list)
    migration: list[str] = Field(default_factory=list)


# ─── Graph ───────────────────────────────────────────────────────────────────
class GraphNode(BaseModel):
    id: str
    kind: str
    label: str
    meta: dict[str, str] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    kind: str


class SubgraphResponse(BaseModel):
    root: str
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


# Resolve forward references (AskResult references TimelineEntry defined later).
AskResult.model_rebuild()
