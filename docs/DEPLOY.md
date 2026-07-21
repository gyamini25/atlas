# Deploying Atlas on Render

The Atlas backend runs as a single Docker web service. The demo repo is **baked into
the image and pre-indexed at startup**, so judges can test the hosted backend without
it ever touching their local filesystem.

> Note on scope: a *hosted* backend serves the **pre-indexed demo repo** (and any repo
> you index by public git URL). To let Atlas reason over your **own local** repository,
> run the backend locally (`./run.sh`) — a remote server can't read local files. Both
> paths use the identical engine.

## Step 1 — Fix the blockers first

### 1a. Confirm the GPT-5.6 model id (only you can do this)
```bash
cd backend && cp .env.example .env
# edit .env: set OPENAI_API_KEY=...  and  ATLAS_LLM_MODE=live
source .venv/bin/activate && uvicorn atlas.api.app:app --port 8787 &
curl localhost:8787/api/verify-llm
```
- `{"ok":true,"model":"gpt-5.6"}` → good.
- If `model` comes back different, the fallback caught a bad id — set `ATLAS_MODEL` to
  the exact id your key can access and re-check.

### 1b. Build the extension on a clean machine
```bash
./setup.sh            # installs backend, builds demo history, builds + packages the .vsix
```
Produces `extension/atlas-vscode-0.1.0.vsix`.

## Step 2 — Push to GitHub
```bash
git init && git add -A && git commit -m "Atlas: engineering memory engine"
git branch -M main
git remote add origin https://github.com/<you>/atlas.git
git push -u origin main
```
(Public, or private + share with `testing@devpost.com` and `build-week-event@openai.com`.)

## Step 3 — Deploy the Blueprint on Render
1. Go to **Render → New + → Blueprint**.
2. Select your `atlas` repo. Render reads [`render.yaml`](../render.yaml) and provisions
   the **atlas-backend** Docker web service. Click **Apply**.
3. Wait for the build (installs deps, bakes the demo repo, builds its git history).
   When live you get a URL like `https://atlas-backend.onrender.com`.

## Step 4 — Turn on live GPT-5.6
1. Render → **atlas-backend → Environment**.
2. Set `OPENAI_API_KEY` = your key, and change `ATLAS_LLM_MODE` = `live`.
3. Save → Render redeploys.
4. Verify:
   ```bash
   curl https://atlas-backend.onrender.com/health
   curl https://atlas-backend.onrender.com/api/verify-llm     # {"ok":true,"mode":"live",...}
   ```

## Step 5 — Point the extension at the hosted backend
Install the `.vsix`, then in VS Code:
**Settings → Extensions → Atlas → `atlas.backendUrl`** = `https://atlas-backend.onrender.com`.

Open `demo/acme-fintech-platform`, select `authenticateUser`, click **✨ Ask Atlas**.
Because the backend pre-indexed the demo repo, the extension skips indexing and answers
immediately.

## Notes
- On Render's starter plan the service sleeps when idle; the **first request after idle**
  takes a few seconds to wake — hit `/health` once to warm it before a demo.
- CORS is open, so the extension host can call the hosted API directly.
- To index a public repo on the hosted backend, POST `/api/index {"repo_url": "..."}`.
