# Atlas — Judge's Guide

**No API key. No database. No local backend.** The extension talks to a hosted
backend that already has the demo repository indexed and runs GPT-5.6.

Total time: about 3 minutes, most of it the one-time build.

---

## Install

Prefer no build? Download `atlas-vscode-0.1.0.vsix` from the
[latest release](https://github.com/gyamini25/atlas/releases/latest), then
`code --install-extension atlas-vscode-0.1.0.vsix` and skip to step 2 below.
You still need the repository cloned for the sample code to open.

```bash
git clone https://github.com/gyamini25/atlas.git
cd atlas
./setup.sh     # builds VSIX in ~1 minute

code --install-extension extension/*.vsix
code demo/acme-fintech-platform

# VS Code:
# 1. Developer: Reload Window
# 2. Select authenticateUser in auth.service.ts
# 3. ✨ Ask Atlas
# 4. Open Timeline → Replay Evolution
# 5. Open Impact → Impact Analysis
```

You should see the ✨ **Atlas** icon in the activity bar (left edge) after the reload.

> **First analysis may take 10–15 seconds while the hosted backend wakes from idle.**
> Everything after that is fast.

> **Open `demo/acme-fintech-platform`, not the repository root.** Atlas indexes the
> folder you open, and the sample repository's ADRs, incidents and PR exports live
> at *its* root.

---

## The 90-second walkthrough

### 1. Ask — why does this code exist?

Open `backend/src/modules/auth/auth.service.ts`, select the function name
**`authenticateUser`** (line 25), and click **✨ Ask Atlas** above it.

Atlas answers with **96% confidence**:

> This function implements email/password authentication with OAuth fallback and
> refresh-token rotation to handle provider outages and improve security.

with three key reasons and **6 cited sources** — the commit, **PR #842**,
**INC-284**, **ADR-012**, and the **#backend-discussion** Slack thread.

The point: the `NOTE:` comment on line 22 says *"see ADR-012 and incident INC-284"*.
The citations, timeline and graph are all derived from the repository's own
history by the retrieval and graph traversal — nothing about them is hardcoded.

> **Disclosed:** the summary text for this one function is a curated trace in
> `backend/seed/traces.json`, so the flagship demo reads identically every run.
> Ask about any other symbol to see the pipeline reason from scratch — and note
> that the confidence is genuinely calibrated, not decorative:
>
> - `rotateRefresh` → **0.97**, ties it to the post-INC-284 session model
> - `charge` → **0.46**, and says so: *"The evidence does not contain a clear…"*
>
> Select the symbol in the editor and press `Cmd/Ctrl+K Cmd/Ctrl+A`.

Click **Learn more →** for the reasoning, alternatives considered, and dependencies.

### 2. Timeline — how did it get this way?

Open the **Timeline** tab → click **🎬 Replay Evolution**.

A narrated replay of 7 steps, 2022 → 2025:

```
2022      Introduce basic email/password authentication
2023      Add OAuth (Google, Azure) for enterprise SSO
Mar 2025  INC-284: OAuth provider outage forces enterprise logouts
Mar 2025  Post-mortem
Mar 2025  ADR-012: resilient auth with OAuth fallback
Mar 2025  Retry logic + Redis session fallback
Mar 2025  PR #842
```

### 3. Impact — what breaks if I change it?

Open the **Impact** tab → click **💥 Impact Analysis**.

Risk **critical**: 5 services affected, 6 likely failures, and a 5-step migration
path. Or run `Cmd/Ctrl+Shift+P` → **Atlas: Impact Analysis** and type `Redis` to
ask a different question.

### 4. Graph — the memory behind the answer

Open the **Graph** tab: the developer → decision → commit → code → incident
subgraph (20 nodes, 25 edges) that the reasoning ran over.

---

## Troubleshooting

**No Atlas icon in the activity bar.**
The window was open before the extension was installed. Reload it:
`Cmd/Ctrl+Shift+P` → **Developer: Reload Window**.

**The first analysis takes 10–15 seconds.**
Expected — the hosted backend sleeps when idle and is waking up. Every request
after that is fast. Check it directly:

```bash
curl https://atlas-backend-ryj4.onrender.com/health
# {"status":"ok","llm_mode":"live","model":"gpt-5.6-sol"}
```

**Timeline / Impact tabs look empty.**
They are on-demand — click the button in the middle of the tab, or use
**Atlas: Replay Evolution** / **Atlas: Impact Analysis** from the command palette.

**A fetch error, or you'd rather not depend on our backend.**
Run it yourself — this works fully offline, no API key:

```bash
./run.sh          # starts on http://127.0.0.1:8787
```

Then set **Settings → Extensions → Atlas → `atlas.backendUrl`** to
`http://127.0.0.1:8787`. In this mode Atlas runs in **mock** reasoning — still
grounded in real retrieved evidence from the repository, just synthesised without
calling GPT-5.6. All four tabs populate identically.

For live GPT-5.6 locally, put `OPENAI_API_KEY` in `backend/.env` with
`ATLAS_LLM_MODE=live`, then verify with `curl localhost:8787/api/verify-llm`.

---

## What to look at in the code

| Question | Where |
|---|---|
| How is the memory graph built? | `backend/atlas/indexer/`, `backend/atlas/graph/` |
| Why is this not plain RAG? | `backend/atlas/embeddings/retriever.py` — semantic + graph proximity + recency |
| The reasoning pipeline | `backend/atlas/reasoning/pipeline.py` — LangGraph: collect → traverse → reason → synthesize |
| The GPT-5.6 contract | `backend/atlas/reasoning/llm.py`, `prompts.py` |
| Architecture decisions | `docs/adr/` |

Requirements if building locally: **Python 3.11+**, **Node 18+**, **VS Code 1.85+**.
