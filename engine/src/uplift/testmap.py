"""testmap.py — map affected files to the tests that cover them.

Public API
----------
tests_for(root, files) -> dict[str, list[str]]
    Maps each file path (relative to *root*) to the sorted list of test file
    paths (also relative to *root*) that cover it, directly or one module hop.

annotate_candidates(candidates, root) -> (candidates_with_tests, tests_to_run, untested)
    Adds "tests" to each candidate in-place, returns the union test set and
    the list of candidate ids whose "tests" is empty.
"""
from __future__ import annotations

import ast
from pathlib import Path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _module_of(path: Path, root: Path) -> str:
    """Dotted module name of *path* relative to *root*, without the .py suffix."""
    return ".".join(path.relative_to(root).with_suffix("").parts)


def _imports_of(path: Path) -> set[str]:
    """Collect all module strings imported by *path* (both `import` and `from … import`)."""
    out: set[str] = set()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
            # Also add the individual names as fully-qualified strings
            out.update(f"{node.module}.{alias.name}" for alias in node.names)
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def tests_for(root: Path, files: list[str]) -> dict[str, list[str]]:
    """For each file in *files*, find test files that import it directly or
    one module level through another source module.

    Args:
        root:  Repository root (e.g. the sample-app directory).
        files: List of source file paths relative to *root* (e.g. "shop/users/service.py").

    Returns:
        Dict mapping each input file to a sorted list of covering test paths
        (relative to *root*).
    """
    # Build module -> rel-path map for all shop source files
    src_mods: dict[str, str] = {
        _module_of(p, root): p.relative_to(root).as_posix()
        for p in (root / "shop").rglob("*.py")
    }
    # Pre-compute imports for each source file (used for one-hop detection)
    src_imports: dict[str, set[str]] = {
        rel: _imports_of(root / rel) for rel in src_mods.values()
    }

    # Collect all test files (skip uplift_proofs injected by the prover)
    test_files = [
        p
        for p in (root / "tests").rglob("test_*.py")
        if "uplift_proofs" not in p.parts
    ]
    # Pre-compute imports for each test file
    test_imports: dict[str, set[str]] = {
        p.relative_to(root).as_posix(): _imports_of(p)
        for p in test_files
    }

    result: dict[str, list[str]] = {}
    for f in files:
        mod = _module_of(root / f, root)
        # Source files that import this module (one-hop bridge)
        importers: set[str] = {
            rel for rel, imps in src_imports.items() if mod in imps
        }
        found: list[str] = []
        for t_rel, t_imps in test_imports.items():
            # Direct import of the module, OR import of a source file that imports it
            if mod in t_imps or any(
                _module_of(root / bridge, root) in t_imps for bridge in importers
            ):
                found.append(t_rel)
        result[f] = sorted(found)
    return result


def annotate_candidates(
    candidates: list[dict],
    root: Path,
) -> tuple[list[dict], list[str], list[str]]:
    """Add ``"tests"`` to each candidate dict; compute testsToRun and untested.

    Modifies *candidates* in-place.

    Returns:
        (candidates, tests_to_run, untested)
        - tests_to_run: sorted union of all covering test paths.
        - untested: sorted list of candidate ids whose tests list is empty.
    """
    files = [c["file"] for c in candidates]
    mapping = tests_for(root, files)
    all_tests: set[str] = set()
    untested: list[str] = []

    for candidate in candidates:
        covering = mapping.get(candidate["file"], [])
        candidate["tests"] = covering
        all_tests.update(covering)
        if not covering:
            untested.append(candidate["id"])

    return candidates, sorted(all_tests), sorted(untested)
