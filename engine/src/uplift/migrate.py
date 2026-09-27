"""migrate.py — scan for migration catalog occurrences and run upgrade tests.

Public API
----------
module_of(rel) -> str
    Return the shop module name for a repo-relative POSIX path.

scan(root, catalog) -> list[dict]
    Find every catalog entry occurrence in root/shop/**/*.py.
    Returns list of {entry, file, line, module, snippet}.

run_pytest_in_tree(python, cwd, junit_xml) -> dict
    Run pytest --continue-on-collection-errors in cwd, write JUnit XML to
    junit_xml (OUTSIDE cwd), return {passed, failed, byModule, cases}.

upgrade_test(repo, requirements, app_python, current, out) -> dict
    Copy repo to a temp dir, create a temp venv (or use current interpreter),
    pip install -r the upgraded requirements, run pytest.
    Returns {passed, failed, byModule}.
"""
from __future__ import annotations

import ast
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def module_of(rel: str) -> str:
    """Return the module name for a repo-relative POSIX path.

    shop/users/service.py -> "users"
    shop/config.py        -> "core"
    """
    parts = rel.split("/")
    if len(parts) > 2 and parts[0] == "shop":
        return parts[1]
    return "core"


def _enclosing_function(tree: ast.AST, lineno: int) -> Optional[str]:
    """Return the name of the function/method that contains *lineno*, or None."""
    best: Optional[str] = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, "end_lineno", None)
            if end is None:
                continue
            if node.lineno <= lineno <= end:
                best = node.name
    return best


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

def scan(root: Path, catalog: list[dict]) -> list[dict]:
    """Find every catalog entry occurrence in root/shop/**/*.py.

    Each detect type:
      - "regex":      re.search on each line
      - "import":     line.strip() starts with / equals the pattern
      - "call":       ast.Call whose func name matches
      - "identifier": ast.Name whose id matches

    Returns list of {entry, file, line, module, snippet}.
    """
    out: list[dict] = []
    shop_root = root / "shop"
    if not shop_root.exists():
        return out

    for path in sorted(shop_root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        lines = text.splitlines()
        try:
            tree: Optional[ast.AST] = ast.parse(text)
        except SyntaxError:
            tree = None

        for entry in catalog:
            d = entry["detect"]
            hits: list[int] = []

            if d["type"] == "regex":
                hits = [i + 1 for i, ln in enumerate(lines) if re.search(d["pattern"], ln)]

            elif d["type"] == "import":
                pat = d["pattern"]
                hits = [
                    i + 1 for i, ln in enumerate(lines)
                    if ln.strip() == pat or pat in ln
                ]

            elif d["type"] in ("call", "identifier") and tree is not None:
                for node in ast.walk(tree):
                    name: Optional[str] = None
                    if d["type"] == "call" and isinstance(node, ast.Call):
                        f = node.func
                        if isinstance(f, ast.Name):
                            name = f.id
                        elif isinstance(f, ast.Attribute):
                            name = f.attr
                    elif d["type"] == "identifier" and isinstance(node, ast.Name):
                        name = node.id
                    if name == d["pattern"]:
                        hits.append(node.lineno)

            for h in sorted(set(hits)):
                snippet = "\n".join(lines[max(0, h - 2): h + 1])
                out.append({
                    "entry": entry["id"],
                    "file": rel,
                    "line": h,
                    "module": module_of(rel),
                    "snippet": snippet,
                })

    return out


# ---------------------------------------------------------------------------
# JUnit XML parsing (per-module grouping)
# ---------------------------------------------------------------------------

def _parse_junit_by_module(xml_path: Path) -> dict:
    """Parse a pytest JUnit XML file and group results by module.

    Module is derived from the test path:
      tests/orders/test_service.py -> "orders"
      tests/test_foo.py            -> "core"
      Collection error key (classname="") uses the dotted name:
        tests.orders.test_service -> "orders"

    Returns:
        {
          "passed":   int,
          "failed":   int,
          "byModule": {"orders": {"passed": int, "failed": int}, ...},
          "cases":    {"key": "passed"|"failed"|"error"},
        }
    """
    passed = 0
    failed = 0
    by_module: dict[str, dict] = defaultdict(lambda: {"passed": 0, "failed": 0})
    cases: dict[str, str] = {}

    if not xml_path.exists():
        return {"passed": 0, "failed": 0, "byModule": {}, "cases": {}}

    try:
        tree = ET.parse(xml_path)
    except ET.ParseError:
        return {"passed": 0, "failed": 0, "byModule": {}, "cases": {}}

    root = tree.getroot()
    suites = list(root.iter("testsuite")) if root.tag == "testsuites" else [root]

    for suite in suites:
        for tc in suite.iter("testcase"):
            classname = tc.get("classname", "")
            name = tc.get("name", "")

            # Determine module
            if classname == "":
                # Collection error — derive module from dotted name
                # e.g. "tests.orders.test_service" -> "orders"
                parts = name.split(".")
                module = parts[1] if len(parts) > 2 and parts[0] == "tests" else "core"
                key = name
                status = "error"
                cases[key] = status
                failed += 1
                by_module[module]["failed"] += 1
                continue

            # Normal case — classname is like "tests/orders/test_service" or
            # "tests.orders.test_service" depending on pytest version
            # Normalise to parts
            normalized = classname.replace("\\", "/").replace(".", "/")
            parts = normalized.split("/")
            # Find "tests" segment
            try:
                idx = next(i for i, p in enumerate(parts) if p == "tests")
                module = parts[idx + 1] if idx + 1 < len(parts) - 1 else "core"
            except StopIteration:
                module = "core"

            key = f"{classname}::{name}"
            if tc.find("skipped") is not None:
                cases[key] = "skipped"
                continue
            failure = tc.find("failure")
            error = tc.find("error")
            if failure is not None or error is not None:
                status = "failed"
                failed += 1
                by_module[module]["failed"] += 1
            else:
                status = "passed"
                passed += 1
                by_module[module]["passed"] += 1
            cases[key] = status

    return {
        "passed": passed,
        "failed": failed,
        "byModule": dict(by_module),
        "cases": cases,
    }


# ---------------------------------------------------------------------------
# upgrade-test
# ---------------------------------------------------------------------------

def _find_python_in_venv(venv_dir: Path) -> str:
    """Return the python executable path inside a venv."""
    for rel in ("bin/python", "Scripts/python.exe", "Scripts/python"):
        p = venv_dir / rel
        if p.exists():
            return str(p)
    # Fallback: return the Scripts/python path (Windows) even if not present yet
    return str(venv_dir / "Scripts" / "python.exe")


def upgrade_test(
    repo: Path,
    requirements: Path,
    app_python: Optional[str] = None,
    current: bool = False,
    out: Optional[Path] = None,
) -> dict:
    """Run the test suite against upgraded requirements.

    Parameters
    ----------
    repo:         Path to the repository root (sample-app/).
    requirements: Path to the upgraded requirements.txt.
    app_python:   Explicit interpreter to use (required when current=True, or
                  used as the base interpreter to create the temp venv).
    current:      If True, run with the existing *app_python* instead of
                  creating a temp venv.
    out:          If given, write the result JSON there.

    Returns
    -------
    {"passed": int, "failed": int, "byModule": {...}}
    """
    repo = repo.resolve()
    requirements = requirements.resolve()

    base_python = app_python or sys.executable

    tmp_root = Path(tempfile.mkdtemp(prefix="uplift_upgrade_"))
    xml_path = tmp_root / "junit.xml"

    try:
        if current:
            # Run tests with the provided interpreter directly (no temp venv/copy)
            python_exe = base_python
            test_cwd = repo
        else:
            # Copy repo to a temp directory
            repo_copy = tmp_root / "repo"
            shutil.copytree(repo, repo_copy, symlinks=False,
                            ignore=shutil.ignore_patterns(".venv*", "__pycache__", "*.pyc"))

            # Create a temp venv
            venv_dir = tmp_root / "venv"
            subprocess.run(
                [base_python, "-m", "venv", str(venv_dir)],
                check=True, capture_output=True, text=True,
            )
            python_exe = _find_python_in_venv(venv_dir)

            # Install upgraded requirements
            subprocess.run(
                [python_exe, "-m", "pip", "install", "--quiet", "-r", str(requirements)],
                check=True, capture_output=True, text=True,
            )

            # Also install the shop package itself (editable not available in copy;
            # just add to PYTHONPATH via -m pytest which handles sys.path)
            test_cwd = repo_copy

        # Run pytest
        cmd = [
            python_exe, "-m", "pytest",
            "--continue-on-collection-errors",
            f"--junit-xml={xml_path}",
            "-q", "--tb=no",
            "tests",
        ]
        completed = subprocess.run(cmd, cwd=test_cwd, capture_output=True, text=True)
        if completed.returncode not in (0, 1) or not xml_path.exists():
            raise RuntimeError("Upgrade test did not complete: " + completed.stdout + completed.stderr)
        result = _parse_junit_by_module(xml_path)
        if not result["cases"]:
            raise RuntimeError("Upgrade test produced no test cases")

    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)

    output = {
        "passed": result["passed"],
        "failed": result["failed"],
        "byModule": result["byModule"],
    }

    if out is not None:
        import json
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(output, indent=2), encoding="utf-8")

    return output
