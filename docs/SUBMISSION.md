# Build Week submission checklist

**Category:** Developer Tools
**Deadline:** 2026-07-21, 5:00 PM PT

## Required deliverables

- [x] **Working project** — Atlas backend engine + VS Code extension (this repo).
- [x] **README** with setup instructions, sample data, and execution guidance — see [`README.md`](../README.md).
- [x] **Sample data** — `demo/acme-fintech-platform` (real git history + ADR/incident/PR/Slack).
- [x] **Uses GPT-5.6** — the reasoning engine (`backend/atlas/reasoning/`).
- [x] **Uses Codex** — see [`CODEX.md`](CODEX.md).
- [ ] **Demo video** (< 3 min, public YouTube, audio covers Codex + GPT-5.6) — script in [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md).
- [ ] **Public code repo** (or shared with testing@devpost.com + build-week-event@openai.com).
- [ ] **Codex Session ID** from `/feedback` where core functionality was built — add to `CODEX.md`.
- [x] **Install/testing instructions** for the extension — see README "VS Code extension".

## Judging criteria → where we deliver

| Criterion | Atlas |
| --- | --- |
| Technological implementation & Codex use | Knowledge graph + LangGraph reasoning pipeline on GPT-5.6; Codex documented in `CODEX.md`. |
| Design & complete product experience | Native VS Code webview matching the product mockup: Ask · Timeline · Graph · Impact. |
| Potential impact | Cuts onboarding time; preserves institutional knowledge for large engineering orgs. |
| Creativity & novelty | Answers *why*, not *how* — differentiated from Copilot, Cursor, and plain RAG. |

## Attribution note

The deliverable credits **GPT-5.6** and **Codex** only. Commit authorship and all
in-repo text are free of any other AI-assistant references.
