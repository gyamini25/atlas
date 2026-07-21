#!/usr/bin/env bash
# Reconstructs a realistic, dated git history for the acme-fintech-platform demo
# repo so Atlas has genuine commits to mine. Idempotent: wipes any existing .git.
#
# Usage:  ./build-demo-git-history.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/acme-fintech-platform" && pwd)"
cd "$REPO_DIR"

rm -rf .git
git init -q
git config user.name "acme-platform-team"
git config user.email "platform@acme.example"

commit() {
  # $1 = ISO date, $2 = author name, $3 = author email, $4 = message
  GIT_AUTHOR_DATE="$1" GIT_COMMITTER_DATE="$1" \
  GIT_AUTHOR_NAME="$2" GIT_AUTHOR_EMAIL="$3" \
  GIT_COMMITTER_NAME="$2" GIT_COMMITTER_EMAIL="$3" \
  git commit -q -m "$4"
}

# 2022 — basic email/password auth introduced.
git add README.md backend/src/shared/config.service.ts
commit "2022-04-11T10:00:00" "Sam Osei" "sam@acme.example" \
  "Introduce basic email/password authentication

Initial AuthService with email/password login. No external providers yet."

# 2023 — OAuth integration (PR #767).
git add backend/src/modules/auth/strategies/oauth.provider.ts backend/src/modules/auth/jwt.service.ts
commit "2023-06-09T13:20:00" "Marcus Lee" "marcus@acme.example" \
  "Add OAuth (Google, Azure) integration for enterprise SSO (PR #767)

Enterprise SSO requirement from sales. Adds OAuth login via Google and Azure."

# Mar 2025 — incident write-up committed.
git add incidents/INC-284.md
commit "2025-03-18T15:30:00" "Dana Whitfield" "dana@acme.example" \
  "Add INC-284 post-mortem: OAuth outage forced enterprise logouts

SEV-1, 17 min. Hard dependency on the provider for authenticated requests."

# Mar 2025 — ADR recording the decision.
git add docs/adr/ADR-012.md .atlas/slack-export.json
commit "2025-03-22T09:00:00" "Priya Nair" "priya@acme.example" \
  "Record ADR-012: resilient auth with OAuth fallback + refresh rotation

Implements the INC-284 follow-ups. Rejects hard-dependency and longer-TTL options."

# Mar 2025 — the actual code change (PR #842).
git add backend/src/modules/auth/auth.service.ts backend/src/shared/redis.service.ts \
        backend/src/modules/payments/payment.service.ts tests/auth.service.spec.ts .atlas/pulls.json
commit "2025-03-24T16:40:00" "Priya Nair" "priya@acme.example" \
  "Add retry logic + Redis session fallback to authenticateUser (PR #842)

Implements ADR-012 in response to INC-284. Caches sessions in Redis, retries the
OAuth provider with backoff then falls back to the cached session, and rotates
refresh tokens to prevent replay. Redis is now load-bearing for auth."

echo "Demo git history created at $REPO_DIR ($(git rev-list --count HEAD) commits)."
