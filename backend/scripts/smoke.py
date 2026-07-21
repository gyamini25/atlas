"""End-to-end smoke test for the Atlas engine (no server, no network).

Indexes the flagship demo repo synchronously, then exercises ask / impact /
replay and prints the results. Run:

    python -m scripts.smoke  [path-to-repo]
"""

from __future__ import annotations

import json
import os
import sys

from atlas.impact.analyzer import analyze_impact
from atlas.indexer.pipeline import run_index
from atlas.models.schemas import IndexRequest, IndexJob
from atlas.reasoning.pipeline import ask, expand
from atlas.replay.builder import build_replay
from atlas.store import get_store, reset_store


def main() -> None:
    default_repo = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "demo", "acme-fintech-platform")
    )
    repo_path = sys.argv[1] if len(sys.argv) > 1 else default_repo

    reset_store()
    store = get_store()

    print(f"→ Indexing {repo_path}")
    job = IndexJob(job_id="smoke", repo="", status="queued")
    run_index(store, IndexRequest(repo_path=repo_path), job)
    print(f"  status={job.status} counts={job.counts}")
    if job.error:
        print(f"  ERROR: {job.error}")
        sys.exit(1)

    repo = job.repo
    print(f"\n→ Ask: Why is authenticateUser implemented this way?")
    result = ask(
        store,
        repo,
        "Why is this function implemented this way?",
        file="backend/src/modules/auth/auth.service.ts",
        symbol="authenticateUser",
    )
    print(f"  confidence: {result.confidence:.0%}")
    print(f"  summary:    {result.summary}")
    print("  key reasons:")
    for r in result.key_reasons:
        print(f"    ✓ [{r.label}] {r.text}")
    print("  sources:")
    for s in result.sources:
        print(f"    • ({s.kind.value}) {s.label}")
    print("  timeline preview:")
    for t in result.timeline_preview:
        flag = " [INCIDENT]" if t.is_incident else ""
        print(f"    {t.date}: {t.title}{flag}")

    exp = expand(result.answer_id)
    print(f"\n  learn-more reasoning: {exp.reasoning[:180] if exp else ''}...")

    print(f"\n→ Impact: What breaks if I remove Redis?")
    report = analyze_impact(store, repo, "Redis")
    print(f"  risk={report.risk} confidence={report.confidence:.0%}")
    print(f"  {report.summary}")
    print(f"  files_affected: {report.files_affected}")
    print(f"  services_affected: {report.services_affected}")

    print(f"\n→ Replay: evolution of authenticateUser")
    steps = build_replay(store, repo, "backend/src/modules/auth/auth.service.ts", "authenticateUser")
    for step in steps:
        flag = " [INCIDENT]" if step.is_incident else ""
        print(f"  {step.date}: {step.title}{flag}")
        print(f"      → {step.narration}")

    print("\n✓ smoke test complete")


if __name__ == "__main__":
    main()
