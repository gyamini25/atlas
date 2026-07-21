# Atlas backend — containerised so it runs anywhere with zero Python setup.
#
# IMPORTANT: build from the REPO ROOT (so the demo repo can be baked in and
# pre-indexed for the hosted demo):
#
#   docker build -f backend/Dockerfile -t atlas-backend .
#   docker run --rm -p 8787:8787 -e ATLAS_LLM_MODE=mock atlas-backend
#
# On Render this is driven by render.yaml. The container pre-indexes the demo
# repo at startup, because a remote backend cannot read a client's local files.
FROM python:3.11-slim

# git is needed by the indexer (GitPython) and to build the demo history.
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install the backend.
COPY backend/pyproject.toml backend/README.md ./
COPY backend/atlas ./atlas
COPY backend/seed ./seed
RUN pip install --no-cache-dir -e .

# Bake in the demo repo and build its real git history so it can be pre-indexed.
COPY demo ./demo
RUN chmod +x ./demo/build-demo-git-history.sh && ./demo/build-demo-git-history.sh

# Configure git identity for any runtime clone operations.
RUN git config --global user.email "atlas@example.com" && git config --global user.name "atlas"

ENV ATLAS_HOST=0.0.0.0 \
    ATLAS_LLM_MODE=mock \
    ATLAS_MODEL=gpt-5.6 \
    ATLAS_PREINDEX_PATH=/app/demo/acme-fintech-platform

EXPOSE 8787
# Render (and most PaaS) inject $PORT; default to 8787 locally.
CMD ["sh", "-c", "uvicorn atlas.api.app:app --host 0.0.0.0 --port ${PORT:-8787}"]
