"""Impact analysis — the blast radius of removing or changing something.

Answers "What breaks if I remove Redis?" by scanning the indexed code symbols,
tests and docs for usages of the target, then estimating risk, likely failures
and a migration path. Grounded in what the repository actually contains.
"""
