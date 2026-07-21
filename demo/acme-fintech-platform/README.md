# acme-fintech-platform

A sample fintech backend used as the flagship demo repository for **Atlas**.

It is intentionally small but carries *real engineering memory*: genuine git
history, an ADR, an incident post-mortem, a pull-request export and a Slack
thread — the kinds of artifacts Atlas reasons over to reconstruct **why** the
code exists.

## The story encoded in this repo

1. **2022** — basic email/password auth is introduced.
2. **2023** — OAuth (Google, Azure) is added for enterprise SSO (PR #767).
3. **Mar 2025** — the OAuth providers suffer a 17-minute outage (**INC-284**),
   force-logging-out enterprise users.
4. **Mar 2025** — the team adds Redis session caching, provider retry + fallback,
   and refresh-token rotation (**ADR-012**, **PR #842**).

Open `backend/src/modules/auth/auth.service.ts`, select `authenticateUser`, and
ask Atlas *"Why is this function implemented this way?"*.
