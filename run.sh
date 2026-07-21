#!/usr/bin/env bash
# Start the Atlas backend API. Run ./setup.sh first.
#
#   ./run.sh                 # mock mode (offline, deterministic)
#   ATLAS_LLM_MODE=live ./run.sh   # live GPT-5.6 (needs OPENAI_API_KEY)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/backend"
# shellcheck disable=SC1091
source .venv/bin/activate

PORT="${ATLAS_PORT:-8787}"
echo "▸ Atlas API on http://127.0.0.1:${PORT}  (mode: ${ATLAS_LLM_MODE:-mock})"
echo "  health:     curl localhost:${PORT}/health"
echo "  verify LLM: curl localhost:${PORT}/api/verify-llm"
exec uvicorn atlas.api.app:app --host 127.0.0.1 --port "${PORT}"
