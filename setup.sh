#!/usr/bin/env bash
# One-command setup for Atlas. Safe to re-run.
#
#   ./setup.sh
#
# Prepares: backend venv + deps, the demo repo's git history, and the built
# VS Code extension (+ a .vsix judges can install directly).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "▸ 1/3  Backend (Python)"
cd "$ROOT/backend"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -e .
echo "  ✓ backend installed"

echo "▸ 2/3  Demo repository (sample data)"
cd "$ROOT/demo"
./build-demo-git-history.sh
echo "  ✓ demo git history ready"

echo "▸ 3/3  VS Code extension"
cd "$ROOT/extension"
npm install --silent
npm run build
# Package a .vsix if vsce is available (judges can install without building).
if npx --yes @vscode/vsce package --allow-missing-repository >/dev/null 2>&1; then
  echo "  ✓ extension built + packaged: extension/$(ls *.vsix 2>/dev/null | head -1)"
else
  echo "  ✓ extension built (vsce packaging skipped)"
fi

cat <<'EOF'

────────────────────────────────────────────────────────────
Setup complete. To see Atlas — no API key or local backend needed:

  1. Install the extension:  code --install-extension extension/*.vsix
  2. Open the demo repo:     code demo/acme-fintech-platform
  3. Reload VS Code:         Cmd/Ctrl+Shift+P → "Developer: Reload Window"
  4. In auth.service.ts, select `authenticateUser` → ✨ Ask Atlas
  5. Timeline tab → 🎬 Replay Evolution
     Impact tab   → 💥 Impact Analysis

The extension talks to the hosted backend by default, which already has the
demo repository indexed and runs GPT-5.6.

To run the backend yourself instead:  ./run.sh
then set the "atlas.backendUrl" VS Code setting to http://127.0.0.1:8787.
That works offline in mock mode; for live GPT-5.6 put OPENAI_API_KEY in
backend/.env with ATLAS_LLM_MODE=live and check /api/verify-llm.
────────────────────────────────────────────────────────────
EOF
