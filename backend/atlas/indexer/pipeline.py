"""Indexing orchestration.

Runs the full pipeline for one repository and streams progress into the job
record so the extension can show a live status:

    clone? → parse (git + code + docs) → build graph → embed → done

Each stage is best-effort; a failure in one extractor never aborts the others,
because partial engineering memory is still useful.
"""

from __future__ import annotations

import os
import subprocess
import tempfile

from atlas.indexer import code_parser, docs_parser, git_history, github_sync
from atlas.models.schemas import IndexJob, IndexRequest
from atlas.records import Artifact
from atlas.store import Store


def repo_id_for(request: IndexRequest, resolved_path: str) -> str:
    """Stable, human-readable repo id used as the store partition key."""
    if request.repo_url:
        tail = request.repo_url.rstrip("/").split("/")[-1]
        return tail[:-4] if tail.endswith(".git") else tail
    return os.path.basename(os.path.normpath(resolved_path))


def _clone(repo_url: str) -> str:
    dest = tempfile.mkdtemp(prefix="atlas-repo-")
    subprocess.run(["git", "clone", "--depth", "200", repo_url, dest], check=True)
    return dest


def run_index(store: Store, request: IndexRequest, job: IndexJob) -> None:
    """Execute the pipeline, mutating `job` and persisting into `store`."""
    from atlas.embeddings.pipeline import embed_repo
    from atlas.graph.builder import build_graph

    def update(status: str, progress: float, detail: str = "") -> None:
        job.status = status
        job.progress = progress
        job.detail = detail
        store.put_job(job)

    try:
        # ── resolve the repository path ──────────────────────────────────────
        if request.repo_url:
            update("cloning", 0.05, f"Cloning {request.repo_url}")
            repo_path = _clone(request.repo_url)
        else:
            repo_path = request.repo_path or ""
            if not os.path.isdir(repo_path):
                raise FileNotFoundError(f"Repo path not found: {repo_path}")

        repo = repo_id_for(request, repo_path)
        job.repo = repo

        # ── parse ────────────────────────────────────────────────────────────
        update("parsing", 0.2, "Reading git history")
        artifacts: list[Artifact] = []
        artifacts.extend(git_history.extract_commits(repo_path))

        update("parsing", 0.4, "Extracting code symbols")
        artifacts.extend(code_parser.extract_symbols(repo_path))

        update("parsing", 0.55, "Reading ADRs, incidents & docs")
        artifacts.extend(docs_parser.extract_docs(repo_path))

        # Optional live GitHub enrichment.
        token = request.github_token
        remote = _remote_url(repo_path)
        owner_repo = github_sync.parse_owner_repo(remote) if remote else None
        if owner_repo:
            update("parsing", 0.6, "Fetching pull requests from GitHub")
            artifacts.extend(github_sync.fetch_pull_requests(*owner_repo, token=token))

        store.add_artifacts(repo, artifacts)
        job.counts = _count_by_kind(artifacts)

        # ── graph ────────────────────────────────────────────────────────────
        update("graphing", 0.75, "Building the engineering-memory graph")
        nodes, edges = build_graph(artifacts)
        store.add_nodes(repo, nodes)
        store.add_edges(repo, edges)
        job.counts["nodes"] = len(nodes)
        job.counts["edges"] = len(edges)

        # ── embeddings ───────────────────────────────────────────────────────
        update("embedding", 0.9, "Embedding evidence for retrieval")
        embed_repo(store, repo, artifacts)

        update("done", 1.0, f"Indexed {len(artifacts)} artifacts")
    except Exception as exc:  # surface a clean error to the UI
        job.status = "error"
        job.error = str(exc)
        job.detail = "Indexing failed"
        store.put_job(job)


def _remote_url(repo_path: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", repo_path, "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return out.stdout.strip() or None
    except Exception:
        return None


def _count_by_kind(artifacts: list[Artifact]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for a in artifacts:
        counts[a.kind.value] = counts.get(a.kind.value, 0) + 1
    return counts
