"""Atlas FastAPI application.

Thin HTTP surface over the engine. All heavy lifting lives in the domain modules;
routes only marshal requests/responses. CORS is wide-open because the only client
is a local VS Code webview.
"""

from __future__ import annotations

import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from atlas import __version__
from atlas.api.routes import router
from atlas.config import get_settings


def _warmup() -> None:
    """Import the heavy reasoning dependencies off the request path.

    LangGraph/LangChain have a large import graph; doing it in a background
    thread at startup means the first user question is snappy instead of paying
    a cold-import tax mid-demo.
    """
    try:
        import langgraph.graph  # noqa: F401
    except Exception:
        pass


def _preindex() -> None:
    """Index any repos named in ATLAS_PREINDEX_PATH at startup.

    A hosted backend can't see a client's local files, so the deployment pre-indexes
    the demo repo here; the extension then reasons over it without re-indexing.
    """
    import uuid

    from atlas.indexer.pipeline import repo_id_for, run_index
    from atlas.models.schemas import IndexJob, IndexRequest
    from atlas.store import get_store

    paths = [p.strip() for p in get_settings().preindex_path.split(",") if p.strip()]
    if not paths:
        return
    store = get_store()
    for path in paths:
        req = IndexRequest(repo_path=path)
        job = IndexJob(job_id=uuid.uuid4().hex[:12], repo=repo_id_for(req, path), status="queued")
        store.put_job(job)
        run_index(store, req, job)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Atlas — Engineering Memory Engine",
        version=__version__,
        description="Reconstructs why code exists by reasoning over a repository's history.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.on_event("startup")
    def _on_startup() -> None:
        threading.Thread(target=_warmup, daemon=True).start()
        threading.Thread(target=_preindex, daemon=True).start()

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        return {
            "status": "ok",
            "version": __version__,
            "llm_mode": settings.llm_mode,
            "model": settings.model,
        }

    return app


app = create_app()
