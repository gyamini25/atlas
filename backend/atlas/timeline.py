"""Chronological timeline construction.

Both the Ask card's timeline preview and the cinematic Decision Replay are built
from the same source: the dated artifacts (commits, PRs, incidents, ADRs) in a
symbol's graph neighbourhood, ordered by time. Building it once here keeps the
"why" story consistent between the two surfaces.
"""

from __future__ import annotations

from datetime import datetime

from atlas.models.domain import SourceKind
from atlas.models.schemas import Source, TimelineEntry
from atlas.records import Artifact, Evidence

_MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Artifact kinds that make meaningful timeline events, and their source kind.
_TIMELINE_KINDS = {
    "commit": SourceKind.COMMIT,
    "pull_request": SourceKind.PULL_REQUEST,
    "incident": SourceKind.INCIDENT,
    "adr": SourceKind.ADR,
    "issue": SourceKind.ISSUE,
}


def _parse(ts: str) -> datetime | None:
    """Parse a timestamp to a *naive* datetime.

    Git commits are timezone-aware while parsed doc dates ("2025-03-18") are
    naive; we strip tzinfo so every event is comparable when the timeline sorts.
    """
    if not ts:
        return None
    parsed: datetime | None = None
    try:
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        for fmt in ("%B %Y", "%b %Y", "%Y-%m", "%Y"):
            try:
                parsed = datetime.strptime(ts, fmt)
                break
            except Exception:
                continue
    if parsed is not None and parsed.tzinfo is not None:
        parsed = parsed.replace(tzinfo=None)
    return parsed


def _format(dt: datetime | None, ts: str) -> str:
    if dt is None:
        # Fall back to a 4-digit year if we can find one in the raw string.
        import re

        m = re.search(r"20\d{2}", ts or "")
        return m.group(0) if m else (ts or "—")
    # Recent-ish events show the month for precision; older ones just the year.
    if dt.year >= 2024:
        return f"{_MONTHS[dt.month]} {dt.year}"
    return str(dt.year)


def _source_for(artifact: Artifact, kind: SourceKind) -> Source:
    return Source(
        kind=kind,
        label=artifact.title[:60],
        ref=artifact.meta.get("ref") or artifact.meta.get("sha", "")[:8] or artifact.id,
        url=artifact.url,
        detail=(artifact.body or "").strip().splitlines()[0][:120] if artifact.body else None,
    )


def _detail(artifact: Artifact) -> str:
    body = (artifact.body or "").strip()
    if not body:
        return artifact.title
    # First non-heading line.
    for line in body.splitlines():
        line = line.strip().lstrip("#").strip()
        if line and not line.startswith("|"):
            return line[:140]
    return artifact.title


def build_timeline(evidence: list[Evidence], root: Artifact | None = None) -> list[TimelineEntry]:
    """Return chronologically ordered timeline entries from ranked evidence."""
    seen: set[str] = set()
    dated: list[tuple[datetime, TimelineEntry]] = []

    candidates = list(evidence)
    for ev in candidates:
        a = ev.artifact
        source_kind = _TIMELINE_KINDS.get(a.kind.value)
        if source_kind is None:
            continue
        if a.id in seen:
            continue
        dt = _parse(a.timestamp)
        if dt is None and not a.timestamp:
            continue
        seen.add(a.id)
        entry = TimelineEntry(
            date=_format(dt, a.timestamp),
            title=a.title.split("(")[0].strip()[:70],
            detail=_detail(a),
            kind=source_kind,
            is_incident=(a.kind.value == "incident"),
            sources=[_source_for(a, source_kind)],
        )
        # Undated events sort to the end using a far-future sentinel.
        dated.append((dt or datetime.max, entry))

    dated.sort(key=lambda pair: pair[0])
    return [entry for _, entry in dated]
