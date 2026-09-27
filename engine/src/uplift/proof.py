"""proof.py — run proof tests and determine confirmed / unconfirmed status.

A proof test is *confirmed* only when it:
  - passes on base (the pre-patch tree)
  - fails  on head  (the post-patch tree)

Any other outcome is "unconfirmed".

Public API
----------
run_pytest(python, cwd, test_paths, junit_xml) -> dict
    Run pytest with the given interpreter inside *cwd*, writing a JUnit XML
    to *junit_xml* (a Path OUTSIDE *cwd*).  Returns:
      {"passed": int, "failed": int, "cases": {"module::test": "passed"|"failed"|"error"}}

parse_junit(xml_path) -> dict
    Parse a JUnit XML file produced by pytest --junit-xml.  Same shape.

proof_run(repo, patch, proofs_dir, app_python, applied) -> dict
    Main entry point:
      - Build head / base trees.
      - Copy proofs_dir into whichever tree is a temp copy.
      - Run pytest on the proofs folder in each tree.
      - Determine confirmed / unconfirmed per proof file.
      - Also run the full test suite (excluding proofs) on each tree.
    Returns:
      {"proofs": [...], "suite": {"base": {...}, "head": {...}}}
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from uplift.diff import head_and_base

# ---------------------------------------------------------------------------
# JUnit XML parsing
# ---------------------------------------------------------------------------

_COLLECTION_ERROR_CLASSNAME = ""   # pytest uses empty classname for collection errors


def parse_junit(xml_path: Path) -> dict:
    """Parse a pytest JUnit XML report into a flat cases dict.

    Returns:
        {
          "passed": int,
          "failed": int,
          "cases": {"module::testname": "passed" | "failed" | "error"},
        }

    Collection errors appear as <testcase classname="" name="dotted.module">.
    We key them as "dotted.module" (no "::" prefix) so callers can detect them.
    """
    passed = 0
    failed = 0
    cases: dict[str, str] = {}

    if not xml_path.exists():
        return {"passed": 0, "failed": 0, "cases": {}}

    try:
        tree = ET.parse(xml_path)
    except ET.ParseError:
        return {"passed": 0, "failed": 0, "cases": {}}

    root = tree.getroot()
    # JUnit XML can have <testsuites><testsuite>... or just <testsuite>...
    suites = root.iter("testsuite") if root.tag == "testsuites" else [root]
    for suite in suites:
        for tc in suite.iter("testcase"):
            classname = tc.get("classname", "")
            name = tc.get("name", "")

            # Collection error: classname is empty
            if classname == _COLLECTION_ERROR_CLASSNAME:
                key = name   # e.g. "tests.uplift_proofs.test_broken"
                status = "error"
                cases[key] = status
                failed += 1
                continue

            key = f"{classname}::{name}"
            if tc.find("skipped") is not None:
                cases[key] = "skipped"
                continue
            failure = tc.find("failure")
            error = tc.find("error")
            if failure is not None or error is not None:
                status = "failed"
                failed += 1
            else:
                status = "passed"
                passed += 1
            cases[key] = status

    return {"passed": passed, "failed": failed, "cases": cases}


# ---------------------------------------------------------------------------
# pytest runner
# ---------------------------------------------------------------------------

def run_pytest(
    python: str,
    cwd: Path,
    test_paths: list[str],
    junit_xml: Optional[Path] = None,
) -> dict:
    """Run pytest with *python* inside *cwd* on *test_paths*.

    The JUnit XML is written to *junit_xml* (a path OUTSIDE cwd so it never
    gets committed back into the repo tree).  If *junit_xml* is None a temp
    file is used and cleaned up automatically.

    Returns the same dict shape as parse_junit().
    """
    own_tmp = junit_xml is None
    if own_tmp:
        fd, tmp = tempfile.mkstemp(suffix=".xml", prefix="uplift_proof_")
        import os; os.close(fd)
        junit_xml = Path(tmp)

    try:
        cmd = [
            python, "-m", "pytest",
            "--continue-on-collection-errors",
            f"--junit-xml={junit_xml}",
            "-q",
            "--tb=no",
        ] + test_paths
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        if result.returncode not in (0, 1) or not junit_xml.exists() or not junit_xml.stat().st_size:
            raise RuntimeError("pytest did not complete a test run: " + result.stdout + result.stderr)
        return parse_junit(junit_xml)
    finally:
        if own_tmp and junit_xml.exists():
            junit_xml.unlink()


# ---------------------------------------------------------------------------
# Proof-file → item id mapping
# ---------------------------------------------------------------------------

_ITEM_RE = re.compile(r"^#\s*uplift:item\s+(\S+)", re.MULTILINE)


def _item_id_for(proof_file: Path) -> str:
    """Return the uplift:item id from the first-line comment, or the file stem."""
    try:
        text = proof_file.read_text(encoding="utf-8")
    except OSError:
        return proof_file.stem
    m = _ITEM_RE.search(text)
    return m.group(1) if m else proof_file.stem


# ---------------------------------------------------------------------------
# Determine default app-python path
# ---------------------------------------------------------------------------

def _default_app_python(repo: Path) -> str:
    """Return the sample-app venv python if available next to repo, else sys.executable."""
    # Try <repo-parent>/sample-app/.venv/bin/python (Unix) or Scripts/python.exe (Windows)
    for parent in [repo.parent, repo.parent.parent]:
        for rel in (
            "sample-app/.venv311/bin/python",
            "sample-app/.venv311/Scripts/python.exe",
            "sample-app/.venv/bin/python",
            "sample-app/.venv/Scripts/python.exe",
        ):
            candidate = parent / rel
            if candidate.exists():
                return str(candidate)
    return sys.executable


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def proof_run(
    repo: Path,
    patch: Path,
    proofs_dir: Path,
    app_python: str,
    applied: bool,
) -> dict:
    """Run all proof tests in *proofs_dir* and return a proofs.json-compatible dict.

    Parameters
    ----------
    repo:        Repository root (absolute or relative).
    patch:       Unified diff patch file.
    proofs_dir:  Directory containing proof test files (e.g. sample-app/tests/uplift_proofs).
                 Must be under *repo*.
    app_python:  Python interpreter to use when running tests.
    applied:     True if the patch is already applied to *repo*.

    Returns
    -------
    {
        "proofs": [
            {
                "item":         str,   # uplift:item id or stem
                "testFile":     str,   # relative path from repo root
                "passesOnBase": bool,
                "failsOnHead":  bool,
                "status":       "confirmed" | "unconfirmed",
            },
            ...
        ],
        "suite": {
            "base": {"passed": int, "failed": int},
            "head": {"passed": int, "failed": int},
        },
    }
    """
    repo = repo.resolve()
    proofs_dir = proofs_dir.resolve()
    rel_proofs = proofs_dir.relative_to(repo)   # e.g. tests/uplift_proofs

    head, base = head_and_base(repo, patch, applied)

    # Copy proofs into any temp tree that doesn't already have them
    for tree in (head, base):
        if tree.resolve() != repo.resolve():
            src = repo / rel_proofs
            dst = tree / rel_proofs
            if src.exists() and not dst.exists():
                shutil.copytree(src, dst, dirs_exist_ok=True)

    # JUnit XML files are created OUTSIDE the trees under test
    tmp_dir = Path(tempfile.mkdtemp(prefix="uplift_proof_xml_"))
    try:
        xml_base_proofs = tmp_dir / "base_proofs.xml"
        xml_head_proofs = tmp_dir / "head_proofs.xml"
        xml_base_suite  = tmp_dir / "base_suite.xml"
        xml_head_suite  = tmp_dir / "head_suite.xml"

        # --- Run proofs on both trees ---
        # pytest is run from each tree so relative imports work
        proofs_rel = rel_proofs.as_posix()
        on_base_proofs = run_pytest(app_python, base, [proofs_rel], junit_xml=xml_base_proofs)
        on_head_proofs = run_pytest(app_python, head, [proofs_rel], junit_xml=xml_head_proofs)

        # --- Determine confirmed status per proof file ---
        proofs_result: list[dict] = []
        for f in sorted(proofs_dir.glob("test_*.py")):
            # Derive the module dotted name used by pytest as the key prefix
            rel_file = rel_proofs / f.name   # e.g. tests/uplift_proofs/test_x.py
            stem = f.stem                    # e.g. test_x
            # pytest keys cases as "tests/uplift_proofs/test_x.py::test_something"
            # BUT for collection errors it uses the dotted module name as the key
            module_dotted = ".".join(rel_proofs.parts + (stem,))

            def _cases_for(result: dict) -> list[str]:
                """Return statuses for all cases in this file, including collection errors."""
                cases = result["cases"]
                # Normal cases: key = "rel/path/test_x.py::test_fn"
                file_prefix = rel_file.as_posix() + "::"
                statuses = [v for k, v in cases.items() if k.startswith(file_prefix)]
                # Also try classname-based keys (pytest formats: "module::testname")
                class_prefix = module_dotted + "::"
                statuses += [v for k, v in cases.items()
                              if k.startswith(class_prefix) and not k.startswith(file_prefix)]
                # Collection error for this file
                if module_dotted in cases:
                    statuses.append(cases[module_dotted])
                return statuses

            base_statuses = _cases_for(on_base_proofs)
            head_statuses = _cases_for(on_head_proofs)

            # passes_on_base: file ran AND all cases passed
            passes_on_base = bool(base_statuses) and all(s == "passed" for s in base_statuses)
            # fails_on_head:  file did not run OR at least one case failed/errored
            fails_on_head = bool(head_statuses) and any(s in ("failed", "error") for s in head_statuses)

            status = "confirmed" if passes_on_base and fails_on_head else "unconfirmed"

            proofs_result.append({
                "item": _item_id_for(f),
                "testFile": (rel_proofs / f.name).as_posix(),
                "passesOnBase": passes_on_base,
                "failsOnHead": fails_on_head,
                "status": status,
            })

        # --- Full suite run (tests/ excluding proofs subdir) ---
        # Find the tests root: parent of proofs_dir
        tests_root = rel_proofs.parent      # e.g. "tests"
        tests_root_posix = tests_root.as_posix() if str(tests_root) != "." else "tests"

        # Build an ignore list for the proofs subdirectory via --ignore
        base_suite_cmd_extra: list[str] = []
        head_suite_cmd_extra: list[str] = []

        def _full_suite(tree: Path, xml: Path) -> dict:
            """Run the full tests/ suite excluding the proofs subfolder."""
            proofs_in_tree = (tree / rel_proofs).as_posix()
            cmd = [
                app_python, "-m", "pytest",
                "--continue-on-collection-errors",
                f"--junit-xml={xml}",
                "-q", "--tb=no",
                f"--ignore={proofs_in_tree}",
                tests_root_posix,
            ]
            result = subprocess.run(cmd, cwd=tree, capture_output=True, text=True)
            if result.returncode not in (0, 1) or not xml.exists():
                raise RuntimeError("pytest did not complete a suite run: " + result.stdout + result.stderr)
            return parse_junit(xml)

        base_suite = _full_suite(base, xml_base_suite)
        head_suite = _full_suite(head, xml_head_suite)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return {
        "proofs": proofs_result,
        "suite": {
            "base": {"passed": base_suite["passed"], "failed": base_suite["failed"]},
            "head": {"passed": head_suite["passed"], "failed": head_suite["failed"]},
        },
    }
