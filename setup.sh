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
Setup complete. To run Atlas:

  1. Start the backend:        ./run.sh
  2. Install the extension:    code --install-extension extension/*.vsix
     (or open ./extension in VS Code and press F5)
  3. Open the demo repo:       code demo/acme-fintech-platform
  4. Select `authenticateUser` in auth.service.ts → ✨ Ask Atlas

For LIVE GPT-5.6 reasoning: put OPENAI_API_KEY in backend/.env and set
ATLAS_LLM_MODE=live, then check:  curl localhost:8787/api/verify-llm
────────────────────────────────────────────────────────────
EOF
