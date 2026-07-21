"""Blast-radius analysis over the indexed repository.

Given a target (a dependency like "Redis", a module, or a symbol name), we:
  1. find every code symbol whose body references it (usage sites),
  2. group them into files, tests and inferred services,
  3. estimate risk from breadth × sensitivity (auth/payment paths weigh more),
  4. produce likely failures and a migration outline.

All grounded in real indexed code — no external calls required.
"""

from __future__ import annotations

import re

from atlas.models.schemas import ImpactReport
from atlas.records import Artifact
from atlas.store import Store

# Paths matching these are treated as tests.
_TEST_RE = re.compile(r"(^|/)(tests?|__tests__)/|\.(test|spec)\.", re.I)
# Sensitive domains raise the risk level when touched.
_SENSITIVE = re.compile(r"auth|payment|billing|session|token|security|login", re.I)


def _mentions(target: str, artifact: Artifact) -> bool:
    text = f"{artifact.body}\n{artifact.symbol or ''}\n{artifact.path or ''}"
    # Word-ish boundary so "redis" doesn't match "redistribute".
    return re.search(rf"\b{re.escape(target)}\w*", text, re.I) is not None


def analyze_impact(store: Store, repo: str, target: str) -> ImpactReport:
    artifacts = store.get_artifacts(repo)
    symbols = [a for a in artifacts if a.kind.value == "code_symbol"]

    usages = [a for a in symbols if _mentions(target, a)]

    files = sorted({a.path for a in usages if a.path})
    tests = sorted({a.path for a in usages if a.path and _TEST_RE.search(a.path)})
    prod_files = [f for f in files if f not in tests]

    services = _infer_services(artifacts, target)
    likely_failures = _likely_failures(target, usages)
    migration = _migration(target, usages, services)

    sensitive_hits = sum(1 for a in usages if a.path and _SENSITIVE.search(a.path))
    risk = _risk(len(prod_files), len(usages), sensitive_hits, services)
    confidence = _confidence(usages, files)

    summary = _summary(target, prod_files, usages, services, risk)

    return ImpactReport(
        target=target,
        risk=risk,
        confidence=confidence,
        summary=summary,
        files_affected=prod_files,
        services_affected=services,
        tests_affected=tests,
        likely_failures=likely_failures,
        migration=migration,
    )


def _infer_services(artifacts: list[Artifact], target: str) -> list[str]:
    services: set[str] = set()
    for a in artifacts:
        text = f"{a.title}\n{a.body}"
        if not re.search(rf"\b{re.escape(target)}", text, re.I):
            continue
        # Services usually show up as "<Name>Service" or in docker/compose docs.
        for match in re.finditer(r"\b([A-Z][a-zA-Z]+Service)\b", text):
            services.add(match.group(1))
    return sorted(services)[:8]


def _likely_failures(target: str, usages: list[Artifact]) -> list[str]:
    out: list[str] = []
    for a in usages[:6]:
        where = a.symbol or (a.path or "code")
        out.append(f"`{where}` can no longer reach {target}; calls that depend on it will fail.")
    if not out:
        out.append(f"No direct usages of {target} were found in indexed code — impact is likely low.")
    return out


def _migration(target: str, usages: list[Artifact], services: list[str]) -> list[str]:
    steps = [
        f"Introduce an abstraction over {target} so call sites depend on an interface, not the client.",
        f"Provide a drop-in replacement (or in-process fallback) behind that interface.",
    ]
    if services:
        steps.append(f"Update {', '.join(services)} to consume the new interface.")
    if usages:
        steps.append(f"Migrate {len(usages)} usage site(s), then remove the {target} dependency and its config.")
    steps.append("Run the affected tests and load-test any hot paths before removing infrastructure.")
    return steps


def _risk(prod_files: int, usages: int, sensitive: int, services: list[str]) -> str:
    if usages == 0:
        return "low"
    score = prod_files + usages + 2 * sensitive + len(services)
    if sensitive and score >= 6:
        return "critical"
    if score >= 8:
        return "high"
    if score >= 3:
        return "medium"
    return "low"


def _confidence(usages: list[Artifact], files: list[str]) -> float:
    if not usages:
        return 0.5
    return round(min(0.95, 0.6 + 0.05 * len(files)), 2)


def _summary(target: str, prod_files: list[str], usages: list[Artifact], services: list[str], risk: str) -> str:
    if not usages:
        return f"I found no indexed code that depends on {target}; removing it looks low-risk."
    svc = f" across {len(services)} service(s)" if services else ""
    return (
        f"Removing {target} is **{risk}** risk: it's used in {len(usages)} place(s) "
        f"spanning {len(prod_files)} file(s){svc}. See the likely failures and migration path below."
    )
