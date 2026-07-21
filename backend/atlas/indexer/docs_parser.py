"""Documentation & structured-artifact extraction.

Mines the human record of *why*:
  * docs/adr/*.md            → Architecture Decision Records
  * incidents/*.md           → incident write-ups
  * README / docs/**/*.md    → prose documentation
  * .atlas/pulls.json        → pull-request bodies (offline export or GitHub sync)
  * .atlas/slack-export.json → curated discussion threads

The `.atlas/*` files let a repository ship its own PR/Slack context so Atlas can
reason over it offline — the same shape `github_sync.py` produces from the API.
"""

from __future__ import annotations

import glob
import json
import os
import re

from atlas.indexer.refs import extract_refs
from atlas.models.domain import ArtifactKind
from atlas.records import Artifact

_HEADING = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except Exception:
        return ""


def _title_of(text: str, fallback: str) -> str:
    match = _HEADING.search(text)
    return match.group(1).strip() if match else fallback


def extract_docs(repo_path: str) -> list[Artifact]:
    """Return artifacts for ADRs, incidents, docs, PR and Slack exports."""
    artifacts: list[Artifact] = []
    artifacts.extend(_adrs(repo_path))
    artifacts.extend(_incidents(repo_path))
    artifacts.extend(_markdown_docs(repo_path))
    artifacts.extend(_pulls(repo_path))
    artifacts.extend(_slack(repo_path))
    return artifacts


def _adrs(repo_path: str) -> list[Artifact]:
    out: list[Artifact] = []
    for path in sorted(glob.glob(os.path.join(repo_path, "docs", "adr", "*.md"))):
        text = _read(path)
        name = os.path.splitext(os.path.basename(path))[0]  # e.g. "ADR-012"
        ref_match = re.search(r"(\d+)", name)
        ref = f"ADR-{int(ref_match.group(1)):03d}" if ref_match else name
        out.append(
            Artifact(
                id=f"adr:{ref}",
                kind=ArtifactKind.ADR,
                title=_title_of(text, name),
                body=text,
                path=os.path.relpath(path, repo_path),
                url=os.path.relpath(path, repo_path),
                refs=extract_refs(text) + [ref],
                meta={"ref": ref},
            )
        )
    return out


def _incidents(repo_path: str) -> list[Artifact]:
    out: list[Artifact] = []
    patterns = [
        os.path.join(repo_path, "incidents", "*.md"),
        os.path.join(repo_path, "docs", "incidents", "*.md"),
    ]
    for pattern in patterns:
        for path in sorted(glob.glob(pattern)):
            text = _read(path)
            name = os.path.splitext(os.path.basename(path))[0]  # e.g. "INC-284"
            ref_match = re.search(r"(\d+)", name)
            ref = f"INC-{ref_match.group(1)}" if ref_match else name
            out.append(
                Artifact(
                    id=f"incident:{ref}",
                    kind=ArtifactKind.INCIDENT,
                    title=_title_of(text, name),
                    body=text,
                    path=os.path.relpath(path, repo_path),
                    url=os.path.relpath(path, repo_path),
                    timestamp=_first_date(text),
                    refs=extract_refs(text) + [ref],
                    meta={"ref": ref},
                )
            )
    return out


def _markdown_docs(repo_path: str) -> list[Artifact]:
    out: list[Artifact] = []
    candidates = [os.path.join(repo_path, "README.md")]
    candidates += glob.glob(os.path.join(repo_path, "docs", "*.md"))
    for path in candidates:
        if not os.path.isfile(path):
            continue
        # ADRs/incidents already handled above.
        if "/adr/" in path or "/incidents/" in path:
            continue
        text = _read(path)
        rel = os.path.relpath(path, repo_path)
        out.append(
            Artifact(
                id=f"doc:{rel}",
                kind=ArtifactKind.DOC,
                title=_title_of(text, rel),
                body=text,
                path=rel,
                url=rel,
                refs=extract_refs(text),
            )
        )
    return out


def _pulls(repo_path: str) -> list[Artifact]:
    path = os.path.join(repo_path, ".atlas", "pulls.json")
    if not os.path.isfile(path):
        return []
    try:
        data = json.loads(_read(path))
    except Exception:
        return []
    out: list[Artifact] = []
    for pr in data:
        number = pr.get("number")
        body = pr.get("body", "") or ""
        title = pr.get("title", f"PR #{number}")
        out.append(
            Artifact(
                id=f"pr:PR#{number}",
                kind=ArtifactKind.PULL_REQUEST,
                title=f"PR #{number} - {title}",
                body=body,
                author=pr.get("author", ""),
                timestamp=pr.get("merged_at") or pr.get("created_at", ""),
                url=pr.get("url"),
                refs=extract_refs(f"{title}\n{body}") + [f"PR#{number}"],
                meta={"number": str(number)},
            )
        )
    return out


def _slack(repo_path: str) -> list[Artifact]:
    path = os.path.join(repo_path, ".atlas", "slack-export.json")
    if not os.path.isfile(path):
        return []
    try:
        data = json.loads(_read(path))
    except Exception:
        return []
    out: list[Artifact] = []
    for i, thread in enumerate(data):
        channel = thread.get("channel", "discussion")
        messages = thread.get("messages", [])
        text = "\n".join(f"{m.get('user', '?')}: {m.get('text', '')}" for m in messages)
        title = thread.get("title") or f"#{channel} discussion"
        out.append(
            Artifact(
                id=f"slack:{channel}:{i}",
                kind=ArtifactKind.SLACK,
                title=title,
                body=text,
                timestamp=thread.get("date", ""),
                refs=extract_refs(text),
                meta={"channel": channel},
            )
        )
    return out


def _first_date(text: str) -> str:
    """Pull the first ISO-ish date out of a document, for timeline ordering."""
    match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if match:
        return match.group(1)
    match = re.search(r"\b([A-Z][a-z]{2,8}\s+\d{4})\b", text)  # "March 2025"
    return match.group(1) if match else ""
