"""Git history extraction via GitPython.

Every commit becomes an `Artifact` carrying its author, timestamp, message and the
files it touched. Commit messages are mined for references (PRs, issues, ADRs,
incidents) so the graph builder can wire commits to the decisions behind them.

GitPython is imported lazily: repositories without a `.git` directory (or hosts
without git) simply yield no commit artifacts instead of failing the whole index.
"""

from __future__ import annotations

import os

from atlas.indexer.refs import extract_refs
from atlas.models.domain import ArtifactKind
from atlas.records import Artifact


def extract_commits(repo_path: str, max_commits: int = 500) -> list[Artifact]:
    """Return commit artifacts for the repository at `repo_path`.

    Returns an empty list (never raises) if the path is not a git repository.
    """
    if not os.path.isdir(os.path.join(repo_path, ".git")):
        return []

    try:
        from git import Repo  # imported lazily; optional dependency at runtime
    except Exception:
        return []

    try:
        repo = Repo(repo_path)
    except Exception:
        return []

    artifacts: list[Artifact] = []
    for commit in repo.iter_commits(max_count=max_commits):
        message = str(commit.message).strip()
        title = message.splitlines()[0] if message else "(no message)"
        # Files touched by this commit (best-effort; merge commits may be empty).
        try:
            files = list(commit.stats.files.keys())
        except Exception:
            files = []

        sha = commit.hexsha
        refs = extract_refs(message)
        # A commit implicitly references the paths it modifies.
        refs.extend(f"path:{f}" for f in files)

        artifacts.append(
            Artifact(
                id=f"commit:{sha}",
                kind=ArtifactKind.COMMIT,
                title=title,
                body=message,
                author=str(commit.author.name or ""),
                author_email=str(commit.author.email or ""),
                timestamp=commit.committed_datetime.isoformat(),
                refs=refs,
                meta={
                    "sha": sha,
                    "short_sha": sha[:8],
                    "files": ",".join(files[:50]),
                },
            )
        )
    return artifacts
