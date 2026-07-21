<div align="center">

# ✨ Atlas: the Engineering Memory Engine

**Atlas answers the one question no developer tool answers well: _Why?_**

Not "what does this code do" or "how do I write this" but *why does this code exist,
why was this architecture chosen, what incident caused it, and what breaks if I change it.*

Atlas lives inside VS Code / Cursor and reconstructs engineering intent from your
repository's real history.

</div>

---

## Why Atlas

| Tool | Answers |
| --- | --- |
| Copilot / Cursor | *How* do I write this code? |
| GitHub | *What* changed, and when? |
| **Atlas** | ***Why*** does this code exist? |

Cursor helps you write code. GitHub stores history. **Atlas understands engineering history** it is institutional memory for software teams.

## What it does

Highlight a function and ask **"Why is this implemented this way?"**. Atlas replies with:

- a **one-sentence answer** and a **calibrated confidence score**,
- **key reasons** grounded in real artifacts,
- **typed source citations** — the PR, the incident, the ADR, the Slack thread,

and, on demand:

- **🎬 Decision Replay** — a cinematic, narrated timeline of *why* the code evolved,
- **💥 Impact Analysis** — "What breaks if I remove Redis?" with risk, blast radius and a migration path,
- **🕸️ Knowledge Graph** — the developer → decision → commit → code → incident graph behind the answer.

## How it works — not plain RAG

Atlas builds an **engineering-memory knowledge graph** from your repository, then runs a
**LangGraph reasoning pipeline** over it powered by **GPT-5.6**:

```
Repository ─▶ Indexer ─▶ Knowledge Graph ─▶ Embeddings ─▶ Reasoning Engine ─▶ Atlas API ─▶ VS Code
            git · AST     NetworkX +          pgvector      collect · rank ·                (React
            PR · ADR ·    Postgres            (semantic)    traverse · reason ·             webview)
            incident ·                                      cite  (GPT-5.6)
            docs · Slack
```

The reasoning pipeline fuses three signals **semantic similarity**, **graph proximity**
(the causal chain of commits → PRs → incidents), and **recency**, so it explains the *why*,
citing real artifacts, instead of returning the nearest document.

## Repository layout

```
atlas/
├── backend/      FastAPI engine: indexer, graph, embeddings, reasoning, impact, replay
├── extension/    VS Code extension + React webview (Ask · Timeline · Graph · Impact)
├── demo/         acme-fintech-platform — the flagship demo repo (real git history + ADR/incident/PR/Slack)
├── docs/adr/     Atlas's own architecture decision records
├── setup.sh      one-command setup: backend deps, demo history, built .vsix
├── run.sh        start the backend locally
├── render.yaml   Render blueprint for the hosted backend
└── JUDGES.md     the 3-minute walkthrough
```

## Quick start

> **Judging or just want to see it work?** Read **[JUDGES.md](JUDGES.md)** instead —
> no API key, no database, no local backend, about 3 minutes:
>
> ```bash
> git clone https://github.com/gyamini25/atlas.git
> cd atlas
> ./setup.sh     # builds VSIX in ~1 minute
>
> code --install-extension extension/*.vsix
> code demo/acme-fintech-platform
>
> # VS Code:
> # 1. Developer: Reload Window
> # 2. Select authenticateUser in auth.service.ts
> # 3. ✨ Ask Atlas
> # 4. Open Timeline → Replay Evolution
> # 5. Open Impact → Impact Analysis
> ```
>
> The extension defaults to the hosted backend, which has the demo repository
> pre-indexed. First analysis may take 10–15 seconds while it wakes from idle.
> A prebuilt `.vsix` is attached to the [latest release](https://github.com/gyamini25/atlas/releases/latest)
> if you'd rather not build.

The sections below are for running everything yourself.

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e .

# (optional) real GPT-5.6 reasoning + Postgres; the demo runs fully offline without these
cp .env.example .env          # set OPENAI_API_KEY and ATLAS_LLM_MODE=live to go live
# docker compose up -d        # Postgres + pgvector for the production storage path

# prove the whole engine end-to-end on the demo repo (no server, no network):
python -m scripts.smoke
```

Then start the API the extension talks to — from the repository root:

```bash
./run.sh                        # http://127.0.0.1:8787
curl localhost:8787/health      # {"status":"ok","llm_mode":"mock",...}
```

The engine defaults to **mock mode**: deterministic, offline, and grounded in *real* retrieved
evidence. Set `ATLAS_LLM_MODE=live` with an `OPENAI_API_KEY` to reason with GPT-5.6, then confirm
with `curl localhost:8787/api/verify-llm`.

### 2. Demo repo (sample data)

```bash
cd demo && ./build-demo-git-history.sh   # reconstructs real, dated git history
```

### 3. VS Code extension

```bash
cd extension
npm install
npm run build                                       # React webview + extension bundle
npx @vscode/vsce package --allow-missing-repository # produces atlas-vscode-0.1.0.vsix
code --install-extension atlas-vscode-0.1.0.vsix
```

Reload VS Code (`Cmd/Ctrl+Shift+P` → **Developer: Reload Window**), then open the
`demo/acme-fintech-platform` folder — **not** the repository root, since Atlas indexes the
folder you open and the sample repo's ADRs, incidents and PR exports live at *its* root.
Open `backend/src/modules/auth/auth.service.ts`, select **`authenticateUser`**, and click
**✨ Ask Atlas**.

> **Point the extension at your local backend.** `atlas.backendUrl` defaults to the hosted
> deployment, so a backend you started with `./run.sh` is ignored until you change it:
> **Settings → Extensions → Atlas → `atlas.backendUrl`** = `http://127.0.0.1:8787`.

For extension development, `npm run watch` plus **F5** launches an Extension Development
Host instead — no packaging step.

## The 30-second demo

1. Open the demo repo, select `authenticateUser`, click **✨ Ask Atlas**.
2. Atlas answers with **96% confidence**: OAuth outage (INC-284) → ADR-012 → retry + Redis fallback (PR #842),
   citing the commit, PR, incident, ADR and Slack thread it reasoned over.
3. Open the **Timeline** tab → click **🎬 Replay Evolution** → the decision replay animates
   *why* the code evolved, 2022 → today.
4. Open the **Impact** tab → click **💥 Impact Analysis** → Atlas reasons it's **critical**:
   5 services, auth + payments.

Steps 3 and 4 are also available from the command palette as
**Atlas: Replay Evolution** and **Atlas: Impact Analysis**.

The summary text for `authenticateUser` is a curated trace in `backend/seed/traces.json`, so the
flagship demo reads identically every run; its citations, timeline and graph are all derived from
the repository. Ask about `rotateRefresh` (**0.97**) or `charge` (**0.46**, and it says the evidence
is thin) to watch the pipeline reason from scratch, see [JUDGES.md](JUDGES.md).

> *"This repository no longer stores code. It remembers why the code exists."*

## Built with GPT-5.6 + Codex

Atlas's runtime intelligence is **GPT-5.6** (the reasoning pipeline). It was built with the help of
**Codex** — see [`docs/CODEX.md`](docs/CODEX.md) for where Codex accelerated the work and how the two
were used to explore ideas, make architectural decisions, and ship a polished product.

## License

MIT.
