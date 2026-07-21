"""Repository indexer.

Turns a real repository into a stream of `Artifact` records by mining:
  * git history (commits, authors, diffs)        → git_history.py
  * source code symbols via tree-sitter          → code_parser.py
  * ADRs / incidents / docs / PR & Slack exports  → docs_parser.py
  * GitHub pull requests & issues (optional)      → github_sync.py

`pipeline.py` orchestrates these into a single indexing job.
"""
