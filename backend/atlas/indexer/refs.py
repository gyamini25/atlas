"""Reference extraction.

Engineering intent lives in the cross-references people scatter through commit
messages, PR bodies and docs: "fixes #284", "see ADR-012", "caused by INC-284".
These regexes lift those references so the graph builder can turn them into edges.
"""

from __future__ import annotations

import re

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # PR / issue numbers: "#842", "PR #842", "pull/842"
    ("pr", re.compile(r"\b(?:PR\s*#|pull/)(\d+)\b", re.IGNORECASE)),
    ("issue", re.compile(r"(?<![\w/])#(\d+)\b")),
    # ADR-012 / ADR 12
    ("adr", re.compile(r"\bADR[-\s]?(\d+)\b", re.IGNORECASE)),
    # INC-284 / Incident #284
    ("incident", re.compile(r"\b(?:INC|Incident)[-\s#]*(\d+)\b", re.IGNORECASE)),
    # 7-40 char hex commit shas
    ("commit", re.compile(r"\b([0-9a-f]{7,40})\b")),
]


def extract_refs(text: str) -> list[str]:
    """Return normalised references found in `text`.

    Normalised forms are stable ids the graph builder can match on:
    "PR#842", "ISSUE#12", "ADR-012", "INC-284", or a raw commit sha.
    """
    if not text:
        return []
    found: list[str] = []
    for kind, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(1)
            if kind == "pr":
                found.append(f"PR#{value}")
            elif kind == "issue":
                found.append(f"ISSUE#{value}")
            elif kind == "adr":
                found.append(f"ADR-{int(value):03d}")
            elif kind == "incident":
                found.append(f"INC-{value}")
            elif kind == "commit":
                found.append(value)
    # De-dup, preserve order.
    seen: set[str] = set()
    out: list[str] = []
    for ref in found:
        if ref not in seen:
            seen.add(ref)
            out.append(ref)
    return out
