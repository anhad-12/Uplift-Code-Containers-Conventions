"""graph.py — build a 3-hop reference graph from changed symbols.

Public API
----------
find_candidates(head, changed, max_hops=3) -> list[dict]

Each candidate dict:
  id, file, line, hop, via, module, layer, snippet, resolution
  resolution: "jedi" (resolved via jedi.get_references) or "name" (AST name match fallback)
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Optional

import jedi

from uplift.diff import Symbol, enclosing, symbols_in

MAX_CANDIDATES = 200


def _module_of(rel: str) -> str:
    """Return the first folder under shop/ as the module name.

    Files directly in shop/ (e.g. shop/app.py) return "core".
    Examples:
      shop/users/service.py  -> "users"
      shop/admin/reports.py  -> "admin"
      shop/app.py            -> "core"
    """
    parts = rel.replace("\\", "/").split("/")
    # parts: ["shop", "module", ...] or ["shop", "file.py"]
    if len(parts) > 2:
        return parts[1]
    return "core"


def _iter_python_files(root: Path):
    """Yield all .py files under root except tests/ directories."""
    for path in sorted(root.rglob("*.py")):
        try:
            rel = path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            continue
        # Skip anything under a tests/ directory
        rel_parts = rel.split("/")
        if any(p in ("tests", "test") or p.startswith("test_") for p in rel_parts):
            continue
        yield path, rel


def _name_based_candidates(
    head: Path,
    sym_name: str,
    seen: set[str],
    sym_id: str,
    hop: int,
) -> list[dict]:
    """AST name-based fallback: find all files that reference sym_name by name."""
    results: list[dict] = []
    for path, rel in _iter_python_files(head):
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (OSError, SyntaxError):
            continue
        lines = source.splitlines()
        file_syms = symbols_in(path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Name) or node.id != sym_name:
                continue
            line_no: int = node.lineno
            enc = enclosing(file_syms, line_no)
            if not enc:
                continue
            cid = f"{rel}#{enc.qualname}"
            if cid in seen or cid == sym_id:
                continue
            seen.add(cid)
            snippet = "\n".join(lines[max(0, line_no - 4): line_no + 4])
            results.append({
                "id": cid,
                "file": rel,
                "line": line_no,
                "hop": hop,
                "via": sym_id,
                "module": _module_of(rel),
                "layer": "direct" if hop == 1 else "indirect",
                "snippet": snippet,
                "resolution": "name",
            })
    return results


def find_candidates(
    head: Path,
    changed: list[dict],
    max_hops: int = 3,
) -> list[dict]:
    """Walk up to *max_hops* of callers for each changed symbol.

    Strategy per symbol at each hop:
    1. Try jedi.Script.get_references() — resolution="jedi".
    2. If jedi finds zero external references, fall back to AST name search —
       resolution="name".

    Rules:
    - Skip any reference whose file is under tests/.
    - Deduplicate by candidate id; no cycles.
    - Return at most MAX_CANDIDATES (200) candidates total.
    """
    project = jedi.Project(path=str(head))
    seen: set[str] = {c["id"] for c in changed}
    frontier: list[str] = [c["id"] for c in changed]
    candidates: list[dict] = []

    for hop in range(1, max_hops + 1):
        if len(candidates) >= MAX_CANDIDATES:
            break
        nxt: list[str] = []
        for sym_id in frontier:
            if len(candidates) >= MAX_CANDIDATES:
                break
            try:
                rel, qual = sym_id.split("#", 1)
            except ValueError:
                continue
            path = head / rel
            if not path.exists():
                continue

            sym: Optional[Symbol] = next(
                (s for s in symbols_in(path) if s.qualname == qual), None
            )
            if sym is None:
                continue

            # Find the column of the symbol's short name on its definition line
            try:
                def_line = path.read_text(encoding="utf-8").splitlines()[sym.start - 1]
                short_name = qual.split(".")[-1]
                col = def_line.index(short_name)
            except (ValueError, IndexError):
                col = 0

            # --- Jedi pass ---
            jedi_candidates: list[dict] = []
            try:
                script = jedi.Script(path=str(path), project=project)
                refs = script.get_references(sym.start, col, include_builtins=False)
                for ref in refs:
                    if ref.is_definition() or not ref.module_path:
                        continue
                    ref_path = Path(ref.module_path)
                    try:
                        ref_rel = ref_path.resolve().relative_to(head.resolve()).as_posix()
                    except ValueError:
                        continue
                    ref_parts = ref_rel.replace("\\", "/").split("/")
                    if any(p in ("tests", "test") or p.startswith("test_") for p in ref_parts):
                        continue
                    if not ref_rel.endswith(".py"):
                        continue
                    enc = enclosing(symbols_in(ref_path), ref.line)
                    if not enc:
                        continue
                    cid = f"{ref_rel}#{enc.qualname}"
                    if cid in seen:
                        continue
                    seen.add(cid)
                    lines = ref_path.read_text(encoding="utf-8").splitlines()
                    snippet = "\n".join(lines[max(0, ref.line - 4): ref.line + 4])
                    jedi_candidates.append({
                        "id": cid,
                        "file": ref_rel,
                        "line": ref.line,
                        "hop": hop,
                        "via": sym_id,
                        "module": _module_of(ref_rel),
                        "layer": "direct" if hop == 1 else "indirect",
                        "snippet": snippet,
                        "resolution": "jedi",
                    })
            except Exception:
                pass

            if jedi_candidates:
                for c in jedi_candidates:
                    if len(candidates) >= MAX_CANDIDATES:
                        break
                    candidates.append(c)
                    nxt.append(c["id"])
            else:
                # --- AST name fallback ---
                name_cands = _name_based_candidates(head, short_name, seen, sym_id, hop)
                for c in name_cands:
                    if len(candidates) >= MAX_CANDIDATES:
                        break
                    candidates.append(c)
                    nxt.append(c["id"])

        frontier = nxt

    return candidates
