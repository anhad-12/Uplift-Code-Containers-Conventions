"""diff.py — parse a unified patch and classify the symbols it changed.

Public API
----------
head_and_base(repo, patch, applied) -> (head_path, base_path)
changed_symbols(head, base, patch) -> list[dict]
"""
from __future__ import annotations

import ast
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from unidiff import PatchSet

# Files / directories to exclude when copying the repo tree
IGNORE = shutil.ignore_patterns(
    ".git", ".venv*", "__pycache__", ".pytest_cache", "node_modules"
)


# ---------------------------------------------------------------------------
# Tree helpers
# ---------------------------------------------------------------------------

def copy_tree(src: Path) -> Path:
    """Copy *src* into a fresh temp directory and return the copy's path."""
    dst = Path(tempfile.mkdtemp(prefix="uplift_")) / src.name
    shutil.copytree(src, dst, ignore=IGNORE)
    return dst


def git_apply(tree: Path, patch: Path, reverse: bool = False) -> None:
    """Apply (or reverse-apply) *patch* inside *tree* via git apply."""
    cmd = (
        ["git", "apply", "--whitespace=nowarn"]
        + (["-R"] if reverse else [])
        + [str(patch.resolve())]
    )
    # Copies must not inherit an unrelated repository from an ancestor directory:
    # Git otherwise silently skips diff --git paths outside its cwd prefix.
    env = os.environ.copy()
    env["GIT_CEILING_DIRECTORIES"] = str(tree.resolve().parent)
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        env.pop(key, None)
    r = subprocess.run(cmd, cwd=tree, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        raise RuntimeError(f"git apply failed: {r.stderr.strip()}")


def head_and_base(repo: Path, patch: Path, applied: bool) -> tuple[Path, Path]:
    """Return (head_tree, base_tree).

    applied=True  -> repo already contains the patch; base is a temp copy
                     with the patch reverse-applied.
    applied=False -> head is a temp copy with the patch applied; base is repo.
    """
    if applied:
        base = copy_tree(repo)
        git_apply(base, patch, reverse=True)
        return repo, base
    head = copy_tree(repo)
    git_apply(head, patch)
    return head, repo


# ---------------------------------------------------------------------------
# Symbol extraction
# ---------------------------------------------------------------------------

@dataclass
class Symbol:
    qualname: str
    kind: str          # "function" | "method" | "class"
    start: int
    end: int
    node: ast.AST = field(repr=False, default=None)


def symbols_in(path: Path) -> list[Symbol]:
    """Return all functions / methods / classes in *path*."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return []
    out: list[Symbol] = []

    def visit(node: ast.AST, prefix: str, in_class: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                q = f"{prefix}{child.name}"
                out.append(
                    Symbol(q, "method" if in_class else "function",
                           child.lineno, child.end_lineno, child)
                )
                visit(child, q + ".", False)
            elif isinstance(child, ast.ClassDef):
                q = f"{prefix}{child.name}"
                out.append(Symbol(q, "class", child.lineno, child.end_lineno, child))
                visit(child, q + ".", True)
            else:
                visit(child, prefix, in_class)

    visit(tree, "", False)
    return out


def enclosing(symbols: list[Symbol], line: int) -> Optional[Symbol]:
    """Return the narrowest symbol that contains *line*, or None."""
    best: Optional[Symbol] = None
    for s in symbols:
        if s.start <= line <= s.end:
            if best is None or (s.end - s.start) < (best.end - best.start):
                best = s
    return best


# ---------------------------------------------------------------------------
# Change classification helpers
# ---------------------------------------------------------------------------

def _signature_of(node: ast.AST) -> str:
    if isinstance(node, ast.ClassDef):
        return ast.dump(ast.Tuple(elts=node.bases, ctx=ast.Load()))
    return ast.dump(node.args) if hasattr(node, "args") else ""


def _returns_of(node: ast.AST) -> str:
    return ast.dump(node.returns) if getattr(node, "returns", None) is not None else ""


def _body_of(node: ast.AST) -> str:
    return "|".join(ast.dump(n) for n in getattr(node, "body", []))


# ---------------------------------------------------------------------------
# Hint rules
# ---------------------------------------------------------------------------

# Each rule: (regex_pattern, which_side, hint_label)
HINT_RULES: list[tuple[str, str, str]] = [
    (r"^\s*raise\b",              "removed", "raise removed"),
    (r"^\s*return\s+None\b",      "added",   "return None added"),
    (r"^\s*if\b.*\bis\s+None\b",  "removed", "None check removed"),
    (r"^\s*if\b.*\bis\s+None\b",  "added",   "None check added"),
    (r"\*\s*100\b|\b100\s*\*",    "added",   "unit scaling added"),
    (r"/\s*100\b",                "added",   "unit scaling added"),
]

_NUM_RE = re.compile(r"\b\d+(\.\d+)?\b")


def hints_for(added: list[str], removed: list[str]) -> list[str]:
    """Derive deterministic behavioural hints from the added/removed line lists."""
    hints: list[str] = []
    for pattern, side, label in HINT_RULES:
        lines = added if side == "added" else removed
        if any(re.search(pattern, line) for line in lines) and label not in hints:
            hints.append(label)
    # Numeric literal change
    nums_added = {m.group() for line in added for m in _NUM_RE.finditer(line)}
    nums_removed = {m.group() for line in removed for m in _NUM_RE.finditer(line)}
    if nums_added != nums_removed and (added or removed):
        if any(_NUM_RE.search(line) for line in added + removed):
            hints.append("numeric literal changed")
    return hints


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def changed_symbols(head: Path, base: Path, patch: Path) -> list[dict]:
    """Map every hunk in *patch* to its enclosing symbol and classify the change.

    changeType values match the schema enum:
      signature | returnShape | behavior | removed | renamed | added
    """
    ps = PatchSet(patch.read_text(encoding="utf-8"))
    # Use a dict keyed by (rel_path, qualname) to merge hunks for the same symbol
    result: dict[tuple[str, str], dict] = {}

    for pf in ps:
        rel: str = pf.path  # unidiff already strips the a/ b/ prefixes
        if not rel.endswith(".py"):
            continue
        # Skip test-only files
        parts = rel.replace("\\", "/").split("/")
        if any(p in ("tests", "test") or p.startswith("test_") for p in parts):
            continue

        head_syms = symbols_in(head / rel)
        base_syms = symbols_in(base / rel)

        touched: dict[str, dict] = {}
        for hunk in pf:
            for line in hunk:
                if line.is_added and line.target_line_no:
                    sym = enclosing(head_syms, line.target_line_no)
                    if sym:
                        touched.setdefault(
                            sym.qualname, {"added": [], "removed": []}
                        )["added"].append(line.value)
                elif line.is_removed and line.source_line_no:
                    sym = enclosing(base_syms, line.source_line_no)
                    if sym:
                        touched.setdefault(
                            sym.qualname, {"added": [], "removed": []}
                        )["removed"].append(line.value)

        head_by = {s.qualname: s for s in head_syms}
        base_by = {s.qualname: s for s in base_syms}

        for q, d in touched.items():
            h = head_by.get(q)
            b = base_by.get(q)
            if b and not h:
                change = "removed"
            elif h and not b:
                change = "added"
            elif h and b and _signature_of(h.node) != _signature_of(b.node):
                change = "signature"
            elif h and b and _returns_of(h.node) != _returns_of(b.node):
                change = "returnShape"
            else:
                change = "behavior"
            kind = (h or b).kind  # type: ignore[union-attr]
            result[(rel, q)] = {
                "id": f"{rel}#{q}",
                "kind": kind,
                "changeType": change,
                "hints": hints_for(d["added"], d["removed"]),
            }

    return list(result.values())
