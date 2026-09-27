"""test_proof.py — unit tests for uplift.proof.

Tests:
  - confirmed proof: passes on base, fails on head
  - unconfirmed control: passes on both (does not detect the regression)
  - unconfirmed broken: does not compile on head (collection error)
  - both --applied and not-applied flavours produce the same result
  - no *.xml file is left inside the repo tree after proof_run
"""
from __future__ import annotations

import json
import subprocess
import textwrap
from pathlib import Path

import pytest

from uplift.proof import parse_junit, proof_run, run_pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


def _git_init(repo: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test"],
                   cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"],
                   cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"],
                   cwd=repo, check=True, capture_output=True)


# ---------------------------------------------------------------------------
# Fixture: a tiny package whose function behaviour is changed by a patch
# ---------------------------------------------------------------------------

def _build_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    """
    Build a minimal project:
      shop/__init__.py
      shop/calc.py:  def add(a, b): return a + b      (base: correct addition)
    Patch changes it to:
      def add(a, b): return a - b                    (head: broken — subtracts)

    Three proof files:
      tests/uplift_proofs/__init__.py
      tests/uplift_proofs/test_add_confirmed.py    # checks old behaviour -> confirmed
      tests/uplift_proofs/test_control.py          # passes on both        -> unconfirmed
      tests/uplift_proofs/test_broken_import.py    # syntax error         -> unconfirmed

    Returns: (repo_path, patch_path, proofs_dir_path)
    """
    repo = tmp_path / "repo"

    # Source
    _write(repo / "shop" / "__init__.py", "")
    _write(repo / "shop" / "calc.py", """\
        def add(a, b):
            return a + b
        """)

    # Tests (regular suite — not the proofs)
    _write(repo / "tests" / "__init__.py", "")
    _write(repo / "tests" / "test_calc_suite.py", """\
        from shop.calc import add
        def test_basic():
            assert add(1, 2) == 3
        """)

    # Proof files
    _write(repo / "tests" / "uplift_proofs" / "__init__.py", "")
    # Confirmed: asserts old behaviour (a + b == 3); will FAIL on head (a - b = -1)
    _write(repo / "tests" / "uplift_proofs" / "test_add_confirmed.py", """\
        # uplift:item shop/calc.py#add
        from shop.calc import add
        def test_add_old_behaviour():
            assert add(1, 2) == 3
        """)
    # Control: passes on both trees (generic assertion)
    _write(repo / "tests" / "uplift_proofs" / "test_control.py", """\
        # uplift:item shop/calc.py#add_control
        def test_always_passes():
            assert 1 + 1 == 2
        """)
    # Broken: syntax error; will fail to collect on head (and on base too)
    _write(repo / "tests" / "uplift_proofs" / "test_broken_import.py", """\
        # uplift:item shop/calc.py#add_broken
        this is not valid python!!!
        """)

    _git_init(repo)

    # Patch: change add() to subtract
    patch_text = (
        "--- a/shop/calc.py\n"
        "+++ b/shop/calc.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def add(a, b):\n"
        "-    return a + b\n"
        "+    return a - b\n"
    )
    patch = tmp_path / "change.patch"
    patch.write_text(patch_text, encoding="utf-8")

    proofs_dir = repo / "tests" / "uplift_proofs"
    return repo, patch, proofs_dir


# ---------------------------------------------------------------------------
# parse_junit unit tests
# ---------------------------------------------------------------------------

class TestParseJunit:
    def test_missing_file_returns_zeros(self, tmp_path: Path):
        result = parse_junit(tmp_path / "nonexistent.xml")
        assert result == {"passed": 0, "failed": 0, "cases": {}}

    def test_parses_passed_and_failed(self, tmp_path: Path):
        xml = tmp_path / "report.xml"
        xml.write_text("""\
<?xml version="1.0" ?>
<testsuites>
  <testsuite>
    <testcase classname="tests.test_foo" name="test_ok"/>
    <testcase classname="tests.test_foo" name="test_bad">
      <failure>assert 1==2</failure>
    </testcase>
  </testsuite>
</testsuites>
""", encoding="utf-8")
        result = parse_junit(xml)
        assert result["passed"] == 1
        assert result["failed"] == 1
        assert result["cases"]["tests.test_foo::test_ok"] == "passed"
        assert result["cases"]["tests.test_foo::test_bad"] == "failed"

    def test_collection_error_empty_classname(self, tmp_path: Path):
        xml = tmp_path / "report.xml"
        xml.write_text("""\
<?xml version="1.0" ?>
<testsuite>
  <testcase classname="" name="tests.uplift_proofs.test_broken">
    <error>SyntaxError</error>
  </testcase>
</testsuite>
""", encoding="utf-8")
        result = parse_junit(xml)
        assert result["failed"] == 1
        assert result["cases"]["tests.uplift_proofs.test_broken"] == "error"


# ---------------------------------------------------------------------------
# Integration: proof_run with --applied=False (not applied)
# ---------------------------------------------------------------------------

class TestProofRunNotApplied:
    def test_confirmed_proof(self, tmp_path: Path):
        """A proof that checks old behaviour is confirmed (passes base, fails head)."""
        repo, patch, proofs_dir = _build_fixture(tmp_path)
        result = proof_run(repo, patch, proofs_dir, sys_python(), applied=False)
        by_item = {p["item"]: p for p in result["proofs"]}
        confirmed = by_item["shop/calc.py#add"]
        assert confirmed["passesOnBase"] is True
        assert confirmed["failsOnHead"] is True
        assert confirmed["status"] == "confirmed"

    def test_control_is_unconfirmed(self, tmp_path: Path):
        """A test that passes on both trees must be unconfirmed."""
        repo, patch, proofs_dir = _build_fixture(tmp_path)
        result = proof_run(repo, patch, proofs_dir, sys_python(), applied=False)
        by_item = {p["item"]: p for p in result["proofs"]}
        ctrl = by_item["shop/calc.py#add_control"]
        assert ctrl["passesOnBase"] is True
        assert ctrl["failsOnHead"] is False   # still passes on head
        assert ctrl["status"] == "unconfirmed"

    def test_broken_import_is_unconfirmed(self, tmp_path: Path):
        """A proof file with a syntax error does not compile; status must be unconfirmed."""
        repo, patch, proofs_dir = _build_fixture(tmp_path)
        result = proof_run(repo, patch, proofs_dir, sys_python(), applied=False)
        by_item = {p["item"]: p for p in result["proofs"]}
        broken = by_item["shop/calc.py#add_broken"]
        assert broken["status"] == "unconfirmed"

    def test_suite_counts_present(self, tmp_path: Path):
        """Suite counts for base and head are present and non-negative integers."""
        repo, patch, proofs_dir = _build_fixture(tmp_path)
        result = proof_run(repo, patch, proofs_dir, sys_python(), applied=False)
        for tree in ("base", "head"):
            assert isinstance(result["suite"][tree]["passed"], int)
            assert isinstance(result["suite"][tree]["failed"], int)
            assert result["suite"][tree]["passed"] >= 0

    def test_no_xml_left_in_repo(self, tmp_path: Path):
        """No *.xml file should remain inside the repo tree after proof_run."""
        repo, patch, proofs_dir = _build_fixture(tmp_path)
        proof_run(repo, patch, proofs_dir, sys_python(), applied=False)
        leftover = list(repo.rglob("*.xml"))
        assert not leftover, f"XML files left in repo: {leftover}"


# ---------------------------------------------------------------------------
# Integration: proof_run with --applied=True (patch already applied)
# ---------------------------------------------------------------------------

class TestProofRunApplied:
    """Run the same fixture in --applied mode.

    We apply the patch to the repo first, then call proof_run with applied=True.
    The same confirmed/unconfirmed outcomes must hold.
    """

    def _apply_patch(self, repo: Path, patch: Path) -> None:
        subprocess.run(
            ["git", "apply", "--whitespace=nowarn", str(patch.resolve())],
            cwd=repo, check=True, capture_output=True,
        )

    def test_confirmed_applied(self, tmp_path: Path):
        repo, patch, proofs_dir = _build_fixture(tmp_path)
        self._apply_patch(repo, patch)
        result = proof_run(repo, patch, proofs_dir, sys_python(), applied=True)
        by_item = {p["item"]: p for p in result["proofs"]}
        confirmed = by_item["shop/calc.py#add"]
        assert confirmed["status"] == "confirmed"

    def test_control_unconfirmed_applied(self, tmp_path: Path):
        repo, patch, proofs_dir = _build_fixture(tmp_path)
        self._apply_patch(repo, patch)
        result = proof_run(repo, patch, proofs_dir, sys_python(), applied=True)
        by_item = {p["item"]: p for p in result["proofs"]}
        assert by_item["shop/calc.py#add_control"]["status"] == "unconfirmed"

    def test_no_xml_left_in_repo_applied(self, tmp_path: Path):
        repo, patch, proofs_dir = _build_fixture(tmp_path)
        self._apply_patch(repo, patch)
        proof_run(repo, patch, proofs_dir, sys_python(), applied=True)
        leftover = list(repo.rglob("*.xml"))
        assert not leftover, f"XML files left in repo: {leftover}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

import sys as _sys

def sys_python() -> str:
    return _sys.executable
