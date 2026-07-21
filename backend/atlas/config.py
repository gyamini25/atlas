"""Central, env-driven configuration.

Everything Atlas needs to run is declared here once and injected everywhere else.
Defaults are chosen so `uvicorn atlas.api.app:app` works out of the box in mock
mode with no external services beyond Postgres.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LLMMode = Literal["live", "mock"]
GraphBackend = Literal["networkx", "neo4j"]


class Settings(BaseSettings):
    """Runtime configuration, populated from environment / `.env`."""

    model_config = SettingsConfigDict(
        env_prefix="ATLAS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── LLM / reasoning ──────────────────────────────────────────────────────
    # OpenAI key is read WITHOUT the ATLAS_ prefix so it matches the ecosystem
    # standard `OPENAI_API_KEY`.
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    model: str = "gpt-5.6"
    # Comma-separated fallbacks tried if `model` is unavailable at runtime, so a
    # mis-typed / unreleased model id degrades gracefully instead of 404-ing the
    # whole demo. Set to the ids your key can actually access.
    model_fallbacks: str = "gpt-5,gpt-4.1,gpt-4o"
    embedding_model: str = "text-embedding-3-large"
    llm_mode: LLMMode = "mock"

    @property
    def model_candidates(self) -> list[str]:
        """The primary model followed by configured fallbacks (de-duplicated)."""
        out: list[str] = []
        for m in [self.model, *self.model_fallbacks.split(",")]:
            m = m.strip()
            if m and m not in out:
                out.append(m)
        return out

    # ── Data stores ──────────────────────────────────────────────────────────
    database_url: str = "postgresql+psycopg://atlas:atlas@localhost:5432/atlas"
    graph_backend: GraphBackend = "networkx"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "atlaspassword"

    # ── Integrations ─────────────────────────────────────────────────────────
    github_token: str = ""

    # A repo path (or comma-separated paths) to index automatically at startup.
    # Used by the hosted deployment to pre-index the demo repo, since a remote
    # backend cannot read a client's local filesystem.
    preindex_path: str = ""

    # ── Server ───────────────────────────────────────────────────────────────
    host: str = "127.0.0.1"
    port: int = 8787
    log_level: str = "info"

    @property
    def can_call_openai(self) -> bool:
        """True when we are configured to make real OpenAI calls."""
        return self.llm_mode == "live" and bool(self.openai_api_key)

    @property
    def embedding_dim(self) -> int:
        """Vector width for the configured embedding model.

        Kept in one place because the pgvector column and the local fallback
        embedder must agree on dimensionality.
        """
        # text-embedding-3-large → 3072, -small → 1536. Local fallback → 1536.
        return 3072 if self.embedding_model.endswith("large") else 1536


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (single source of truth per process)."""
    return Settings()
