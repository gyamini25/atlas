# Testing Atlas (for judges)

Atlas is a VS Code extension + a local reasoning backend. You can test it in **~3
minutes**. It works fully offline (deterministic mock mode) and, with an OpenAI key,
on **live GPT-5.6**.

## Option A — one command (recommended)

```bash
git clone <repo-url> atlas && cd atlas
./setup.sh          # installs backend, builds the demo repo history + the extension
./run.sh            # starts the API on http://127.0.0.1:8787  (leave running)
```

Then in VS Code:

```bash
code --install-extension extension/*.vsix     # install the built extension
code demo/acme-fintech-platform               # open the sample repo
```

Open `backend/src/modules/auth/auth.service.ts`, select **`authenticateUser`**, and
click **✨ Ask Atlas** (or right-click → *Ask Atlas*, or ⌘K ⌘A).

## Option B — Docker backend (no Python)

```bash
cd backend && docker compose up      # API on :8787 (mock mode)
```
Then install the extension and open the demo repo as above.

## What to try

1. **Ask** — select `authenticateUser` → *Ask Atlas*. Expect a **96%-confidence**
   answer citing PR #842, Incident #284 and ADR-012. Click **Learn more** for the
   reasoning and rejected alternatives.
2. **Decision Replay** — the **Timeline** tab animates *why* the code evolved:
   2022 basic auth → 2023 OAuth → Mar 2025 outage (red) → the fix.
3. **Impact** — Command Palette → **Atlas: Impact Analysis** → type `Redis`. Expect
   **critical** risk across auth + payments, with a migration path.
4. **Graph** — the **Graph** tab shows the knowledge graph behind the answer.
5. **Ask your own** — try any function; use the follow-up box to go deeper.

## Turning on live GPT-5.6

```bash
cd backend && cp .env.example .env
# set OPENAI_API_KEY=...  and  ATLAS_LLM_MODE=live  in .env
# (optional) set ATLAS_MODEL to the exact model id your key can access
../run.sh
curl localhost:8787/api/verify-llm      # {"ok":true,"mode":"live","model":"gpt-5.6"}
```

`verify-llm` confirms real reasoning is reachable. If the `gpt-5.6` id isn't available
to your key, Atlas automatically falls back through `ATLAS_MODEL_FALLBACKS` (and, worst
case, to the grounded offline engine) so a demo never hard-fails.

## Verify the engine directly (no editor)

```bash
cd backend && source .venv/bin/activate
python -m scripts.smoke     # indexes the demo repo and prints ask / impact / replay
python -m pytest -q         # 4 passing engine tests
```

## Notes

- Default backend URL is `http://127.0.0.1:8787` (change via Settings →
  `atlas.backendUrl`). If the panel shows "backend not reachable", start `./run.sh`.
- First `Ask` after a cold start loads the reasoning libraries once; subsequent calls
  are fast.
- Atlas only reads a repo's real artifacts and cites them — it never fabricates history;
  confidence reflects how much evidence actually exists.
