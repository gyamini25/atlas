"""Source-code symbol extraction via tree-sitter.

We walk each source file's AST and emit an `Artifact` per function / method /
class, capturing its name, line range and the leading comment block (which often
holds the human "why"). The captured code body feeds both retrieval and the
impact analyser's call-graph.

tree-sitter and the language pack are imported lazily so a machine without them
still indexes git history and docs.
"""

from __future__ import annotations

import os

from atlas.models.domain import ArtifactKind
from atlas.records import Artifact

# File extension → tree-sitter language name (as exposed by tree-sitter-language-pack).
_EXT_LANG: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
    ".java": "java",
    ".rb": "ruby",
    ".rs": "rust",
}

# AST node types that represent a nameable symbol, per language family.
_SYMBOL_NODES = {
    "function_definition",
    "function_declaration",
    "method_definition",
    "method_declaration",
    "class_definition",
    "class_declaration",
    "arrow_function",
}

# Directories we never descend into.
_SKIP_DIRS = {
    ".git", "node_modules", "dist", "build", ".venv", "venv",
    "__pycache__", ".next", "coverage", ".atlas",
}


def _iter_source_files(repo_path: str) -> list[str]:
    out: list[str] = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for name in files:
            ext = os.path.splitext(name)[1].lower()
            if ext in _EXT_LANG:
                out.append(os.path.join(root, name))
    return out


def _node_name(node, source: bytes) -> str | None:
    """Best-effort name of a declaration node via its `name`/`identifier` child."""
    for child in node.children:
        if child.type in {"identifier", "type_identifier", "property_identifier"}:
            return source[child.start_byte : child.end_byte].decode("utf-8", "ignore")
    # Some grammars expose a named field.
    try:
        field = node.child_by_field_name("name")
        if field is not None:
            return source[field.start_byte : field.end_byte].decode("utf-8", "ignore")
    except Exception:
        pass
    return None


def extract_symbols(repo_path: str, max_files: int = 800) -> list[Artifact]:
    """Return code-symbol artifacts for every parseable source file."""
    try:
        from tree_sitter_language_pack import get_parser
    except Exception:
        return []

    artifacts: list[Artifact] = []
    parsers: dict[str, object] = {}

    for file_path in _iter_source_files(repo_path)[:max_files]:
        ext = os.path.splitext(file_path)[1].lower()
        lang = _EXT_LANG[ext]
        try:
            if lang not in parsers:
                parsers[lang] = get_parser(lang)
            parser = parsers[lang]
        except Exception:
            continue

        try:
            with open(file_path, "rb") as fh:
                source = fh.read()
            tree = parser.parse(source)  # type: ignore[attr-defined]
        except Exception:
            continue

        rel = os.path.relpath(file_path, repo_path)
        artifacts.extend(_walk(tree.root_node, source, rel, lang))

    return artifacts


def _walk(root, source: bytes, rel_path: str, lang: str) -> list[Artifact]:
    out: list[Artifact] = []
    stack = [root]
    while stack:
        node = stack.pop()
        if node.type in _SYMBOL_NODES:
            name = _node_name(node, source)
            if name:
                start = node.start_point[0] + 1
                end = node.end_point[0] + 1
                body = source[node.start_byte : node.end_byte].decode("utf-8", "ignore")
                out.append(
                    Artifact(
                        id=f"symbol:{rel_path}::{name}",
                        kind=ArtifactKind.CODE_SYMBOL,
                        title=f"{name} ({rel_path})",
                        body=body[:4000],
                        path=rel_path,
                        symbol=name,
                        line_start=start,
                        line_end=end,
                        meta={"lang": lang, "kind": node.type},
                    )
                )
        stack.extend(node.children)
    return out
