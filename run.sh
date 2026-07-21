#!/usr/bin/env bash
# Start the Atlas backend API. Run ./setup.sh first.
#
#   ./run.sh                 # mock mode (offline, deterministic)
#   ATLAS_LLM_MODE=live ./run.sh   # live GPT-5.6 (needs OPENAI_API_KEY)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/backend"
# Find a usable venv. `./setup.sh` creates backend/.venv, so that is the normal
# answer. The extra candidates exist because a repo checked out under an
# iCloud-synced folder gets its venv evicted to the cloud, which turns every
# import into a network fetch — keeping a venv outside the tree avoids that.
# A candidate only counts if uvicorn actually imports, so a half-built venv is
# skipped rather than failing at startup.
VENV=""
for candidate in ${ATLAS_VENV:+"$ATLAS_VENV"} "$ROOT/backend/.venv" "$HOME/.venvs/atlas"; do
  if [ -x "$candidate/bin/python" ] && "$candidate/bin/python" -c "import uvicorn" 2>/dev/null; then
    VENV="$candidate"
    break
  fi
done
if [ -z "$VENV" ]; then
  echo "No usable venv found — run ./setup.sh first (or set ATLAS_VENV)." >&2
  exit 1
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"

# Force .env back onto local disk before the settings loader reads it. iCloud
# evicts it between runs, and an evicted file reads as EMPTY rather than
# blocking — which silently drops the backend to mock mode with no error.
if [ -f .env ]; then
  cat .env > /dev/null
  if [ ! -s .env ]; then
    echo "WARNING: .env read as empty (iCloud eviction) — LLM mode may fall back to mock." >&2
  fi
fi

PORT="${ATLAS_PORT:-8787}"
# Report what the backend will actually use, not just the shell override. Note
# the `|| true`: with no .env (the default for a fresh clone) grep exits non-zero
# and `set -o pipefail` would otherwise kill the script before it starts.
MODE=""
if [ -f .env ]; then
  MODE="$(grep -E '^ATLAS_LLM_MODE=' .env | tail -1 | cut -d= -f2 || true)"
fi
echo "▸ Atlas API on http://127.0.0.1:${PORT}  (mode: ${ATLAS_LLM_MODE:-${MODE:-mock}})"
echo "  health:     curl localhost:${PORT}/health"
echo "  verify LLM: curl localhost:${PORT}/api/verify-llm"
exec uvicorn atlas.api.app:app --host 127.0.0.1 --port "${PORT}"
