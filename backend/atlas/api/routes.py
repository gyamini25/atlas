"""HTTP routes for the Atlas engine."""

from __future__ import annotations

import threading
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from atlas.impact.analyzer import analyze_impact
from atlas.indexer.pipeline import repo_id_for, run_index
from atlas.models.schemas import (
    AskExpansion,
    AskResult,
    ImpactReport,
    IndexJob,
    IndexRequest,
    ReplayStep,
    SubgraphResponse,
)
from atlas.reasoning.pipeline import ask as run_ask
from atlas.reasoning.pipeline import expand as run_expand
from atlas.replay.builder import build_replay
from atlas.store import get_store

router = APIRouter(prefix="/api", tags=["atlas"])


# ─── request models ──────────────────────────────────────────────────────────
class AskRequest(BaseModel):
    repo: str
    symbol: str
    file: str | None = None
    line: int | None = None
    question: str = "Why does this code exist?"


class ReplayRequest(BaseModel):
    repo: str
    symbol: str
    file: str | None = None


class ImpactRequest(BaseModel):
    repo: str
    target: str  # a dependency, module or symbol name, e.g. "Redis"


# ─── indexing ────────────────────────────────────────────────────────────────
@router.post("/index", response_model=IndexJob)
def index_repo(request: IndexRequest) -> IndexJob:
    store = get_store()
    job = IndexJob(
        job_id=uuid.uuid4().hex[:12],
        repo=repo_id_for(request, request.repo_path or ""),
        status="queued",
    )
    store.put_job(job)
    # Index off the request thread so the call returns immediately.
    threading.Thread(target=run_index, args=(store, request, job), daemon=True).start()
    return job


@router.get("/index/{job_id}", response_model=IndexJob)
def index_status(job_id: str) -> IndexJob:
    job = get_store().get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job")
    return job


@router.get("/repos")
def list_repos() -> dict:
    return {"repos": get_store().repos()}


@router.get("/verify-llm")
def verify_llm() -> dict:
    """Confirm whether real GPT-5.6 reasoning is reachable with the current config."""
    from atlas.reasoning.llm import get_llm

    return get_llm().verify()


# ─── ask ─────────────────────────────────────────────────────────────────────
@router.post("/ask", response_model=AskResult)
def ask(request: AskRequest) -> AskResult:
    store = get_store()
    if request.repo not in store.repos():
        raise HTTPException(status_code=404, detail=f"Repo '{request.repo}' not indexed")
    return run_ask(store, request.repo, request.question, request.file, request.symbol, request.line)


@router.get("/ask/{answer_id}/expand", response_model=AskExpansion)
def expand(answer_id: str) -> AskExpansion:
    expansion = run_expand(answer_id)
    if expansion is None:
        raise HTTPException(status_code=404, detail="Unknown answer id (ask first)")
    return expansion


# ─── replay ──────────────────────────────────────────────────────────────────
@router.post("/replay", response_model=list[ReplayStep])
def replay(request: ReplayRequest) -> list[ReplayStep]:
    store = get_store()
    if request.repo not in store.repos():
        raise HTTPException(status_code=404, detail=f"Repo '{request.repo}' not indexed")
    return build_replay(store, request.repo, request.file, request.symbol)


# ─── impact ──────────────────────────────────────────────────────────────────
@router.post("/impact", response_model=ImpactReport)
def impact(request: ImpactRequest) -> ImpactReport:
    store = get_store()
    if request.repo not in store.repos():
        raise HTTPException(status_code=404, detail=f"Repo '{request.repo}' not indexed")
    return analyze_impact(store, request.repo, request.target)


# ─── graph ───────────────────────────────────────────────────────────────────
@router.get("/graph/subgraph", response_model=SubgraphResponse)
def subgraph(repo: str, symbol: str, file: str | None = None, hops: int = 2) -> SubgraphResponse:
    from atlas.graph import traverse as graph_traverse

    store = get_store()
    node = graph_traverse.find_symbol_node(store, repo, file, symbol)
    if node is None:
        raise HTTPException(status_code=404, detail="Symbol not found in graph")
    return graph_traverse.subgraph(store, repo, node.id, hops=hops)
