# Atlas — 3-minute demo script

Target: **under 3 minutes**, public YouTube, audio covering **Codex** + **GPT-5.6** usage.

## Setup (before recording)
```bash
# backend (warm it so the first ask is instant)
cd backend && source .venv/bin/activate
uvicorn atlas.api.app:app --port 8787
# demo repo history (once)
cd demo && ./build-demo-git-history.sh
# open the demo repo in the Extension Development Host (F5 from extension/)
```
Open `demo/acme-fintech-platform/backend/src/modules/auth/auth.service.ts`.

---

## 0:00–0:20 — The hook
> "Every engineer has asked: *why is this code like this?* Copilot tells you how to
> write code. GitHub tells you what changed. Neither tells you **why**. Atlas does."

Show the file. Cursor on `authenticateUser`.

## 0:20–1:05 — Ask Atlas (the core)
Click **✨ Ask Atlas**. The panel answers:
- **96% confidence**, one-sentence summary.
- **Key reasons**: Incident #284, Security (token rotation), UX (fallback).
- **Sources**: PR #842, Incident #284, ADR-012, Slack — *real artifacts, clickable.*

> "Atlas didn't grep for keywords. It ran a reasoning pipeline on **GPT-5.6** over a
> knowledge graph it built from this repo's history — and it cites the incident, the
> decision record, and the PR that caused this code."

Click **Learn more** → reasoning + alternatives considered.

## 1:05–1:50 — Decision Replay (the wow)
Open the **Timeline** tab.
> "This is Decision Replay. Watch *why* this code evolved."

The timeline animates:
- **2022** basic auth → **2023** OAuth → **Mar 2025** the OAuth outage (red) →
  the ADR → the retry-logic fix.

> "Not what changed — *why* it changed, narrated step by step."

## 1:50–2:30 — Impact Analysis
Command Palette → **Atlas: Impact Analysis** → type `Redis`.
> "What breaks if I remove Redis?"

Atlas returns **critical** risk: 5 services (auth *and* payments), likely failures, a
migration path.
> "It reasoned across the call graph — Redis is load-bearing for both sessions and
> payment idempotency."

## 2:30–3:00 — Codex + close
> "GPT-5.6 is the reasoning engine. **Codex** built it with us — the tree-sitter
> parsers, the FastAPI surface, the webview design system — so we could focus on the
> architecture: a knowledge graph and a real reasoning pipeline, not plain RAG."

End on the line:
> **"This repository no longer stores code. It remembers why the code exists."**
