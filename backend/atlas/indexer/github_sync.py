"""Optional GitHub enrichment.

When a repo has a GitHub remote (and optionally a token), we pull merged pull
requests and issues via the REST API and turn them into artifacts — the live
equivalent of the `.atlas/pulls.json` offline export. Entirely best-effort:
network or rate-limit failures degrade to "no PR/issue artifacts".
"""

from __future__ import annotations

import re

from atlas.indexer.refs import extract_refs
from atlas.models.domain import ArtifactKind
from atlas.records import Artifact

_REMOTE = re.compile(r"github\.com[:/]([^/]+)/([^/.]+)")


def parse_owner_repo(remote_url: str) -> tuple[str, str] | None:
    match = _REMOTE.search(remote_url or "")
    return (match.group(1), match.group(2)) if match else None


def fetch_pull_requests(
    owner: str, repo: str, token: str | None = None, limit: int = 50
) -> list[Artifact]:
    """Fetch recent PRs. Returns [] on any failure."""
    try:
        import httpx
    except Exception:
        return []

    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    params = {"state": "closed", "per_page": str(limit), "sort": "updated"}
    try:
        resp = httpx.get(url, headers=headers, params=params, timeout=15.0)
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        return []

    out: list[Artifact] = []
    for pr in payload:
        if not pr.get("merged_at"):
            continue
        number = pr.get("number")
        title = pr.get("title", "")
        body = pr.get("body") or ""
        out.append(
            Artifact(
                id=f"pr:PR#{number}",
                kind=ArtifactKind.PULL_REQUEST,
                title=f"PR #{number} - {title}",
                body=body,
                author=(pr.get("user") or {}).get("login", ""),
                timestamp=pr.get("merged_at", ""),
                url=pr.get("html_url"),
                refs=extract_refs(f"{title}\n{body}") + [f"PR#{number}"],
                meta={"number": str(number)},
            )
        )
    return out
