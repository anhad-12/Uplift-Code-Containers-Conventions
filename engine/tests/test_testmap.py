"""test_testmap.py — tests for uplift.testmap.tests_for and annotate_candidates.

Integration tests are skipped if sample-app/ is not found.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from uplift.testmap import annotate_candidates
from uplift.testmap import tests_for as _tests_for


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


# ---------------------------------------------------------------------------
# Fixture unit tests
# ---------------------------------------------------------------------------

def _build_project(tmp_path: Path) -> Path:
    """Build a tiny project:

      shop/service.py          - defines get_item()
      shop/middle.py           - imports and re-exports service
      tests/test_direct.py     - imports shop.service directly
      tests/test_via_middle.py - imports shop.middle (one hop to service)
      tests/test_unrelated.py  - imports nothing relevant
    """
    root = tmp_path / "project"

    _write(root / "shop" / "__init__.py", "")
    _write(
        root / "shop" / "service.py",
        """\
        def get_item(item_id: int):
            return {"id": item_id}
        """,
    )
    _write(
        root / "shop" / "middle.py",
        """\
        from shop.service import get_item

        def wrapped(item_id: int):
            return get_item(item_id)
        """,
    )
    _write(root / "tests" / "__init__.py", "")
    _write(
        root / "tests" / "test_direct.py",
        """\
        from shop.service import get_item

        def test_direct():
            assert get_item(1)
        """,
    )
    _write(
        root / "tests" / "test_via_middle.py",
        """\
        from shop.middle import wrapped

        def test_via():
            assert wrapped(1)
        """,
    )
    _write(
        root / "tests" / "test_unrelated.py",
        """\
        def test_nothing():
            pass
        """,
    )
    return root


def test_tests_for_direct(tmp_path: Path) -> None:
    """tests_for returns tests that directly import the file."""
    root = _build_project(tmp_path)
    result = _tests_for(root, ["shop/service.py"])
    covering = result["shop/service.py"]
    assert "tests/test_direct.py" in covering, (
        f"Expected test_direct.py, got: {covering}"
    )


def test_tests_for_one_hop(tmp_path: Path) -> None:
    """tests_for returns tests that import via one intermediate module."""
    root = _build_project(tmp_path)
    result = _tests_for(root, ["shop/service.py"])
    covering = result["shop/service.py"]
    # test_via_middle.py imports shop.middle which imports shop.service
    assert "tests/test_via_middle.py" in covering, (
        f"Expected test_via_middle.py, got: {covering}"
    )


def test_tests_for_unrelated_excluded(tmp_path: Path) -> None:
    """tests_for does not include unrelated test files."""
    root = _build_project(tmp_path)
    result = _tests_for(root, ["shop/service.py"])
    covering = result["shop/service.py"]
    assert "tests/test_unrelated.py" not in covering, (
        f"test_unrelated.py should not be included, got: {covering}"
    )


def test_tests_for_returns_sorted(tmp_path: Path) -> None:
    """tests_for returns sorted test paths."""
    root = _build_project(tmp_path)
    result = _tests_for(root, ["shop/service.py"])
    covering = result["shop/service.py"]
    assert covering == sorted(covering)


def test_annotate_candidates(tmp_path: Path) -> None:
    """annotate_candidates fills tests, testsToRun, and untested correctly."""
    root = _build_project(tmp_path)
    # Add a second source file with no tests
    _write(
        root / "shop" / "orphan.py",
        """\
        def orphaned():
            pass
        """,
    )
    candidates = [
        {"id": "shop/service.py#get_item", "file": "shop/service.py", "hop": 1},
        {"id": "shop/orphan.py#orphaned", "file": "shop/orphan.py", "hop": 1},
    ]
    _, tests_to_run, untested = annotate_candidates(candidates, root)

    # service.py candidate should have tests
    svc = next(c for c in candidates if c["id"] == "shop/service.py#get_item")
    assert svc["tests"], f"Expected tests for service.py, got empty"

    # orphan.py candidate should have no tests
    orp = next(c for c in candidates if c["id"] == "shop/orphan.py#orphaned")
    assert orp["tests"] == []
    assert "shop/orphan.py#orphaned" in untested

    # tests_to_run is the union
    for t in svc["tests"]:
        assert t in tests_to_run


# ---------------------------------------------------------------------------
# Locate sample-app
# ---------------------------------------------------------------------------

def _find_sample_app() -> Path | None:
    here = Path(__file__).resolve()
    for parent in [here.parent, here.parent.parent, here.parent.parent.parent]:
        candidate = parent / "sample-app"
        if candidate.is_dir():
            return candidate
    return None


SAMPLE_APP = _find_sample_app()
_SKIP_MSG = (
    "sample-app/ not found — integration tests require the demo app "
    "to be present alongside the engine/ folder."
)


# ---------------------------------------------------------------------------
# Integration: s1-null-user untested check
# ---------------------------------------------------------------------------

@pytest.mark.skipif(SAMPLE_APP is None, reason=_SKIP_MSG)
def test_s1_untested_includes_admin_report() -> None:
    """shop/admin/reports.py#user_spend_report must be in untested (no admin tests)."""
    assert SAMPLE_APP is not None
    from uplift.diff import changed_symbols, head_and_base
    from uplift.graph import find_candidates

    patch = SAMPLE_APP / "scenarios" / "s1-null-user.patch"
    if not patch.exists():
        pytest.skip(f"Patch not found: {patch}")

    head, base = head_and_base(SAMPLE_APP, patch, applied=False)
    changed = changed_symbols(head, base, patch)
    candidates = find_candidates(head, changed)

    _, tests_to_run, untested = annotate_candidates(candidates, head)

    assert "shop/admin/reports.py#user_spend_report" in untested, (
        f"Expected user_spend_report in untested, got: {untested}"
    )
    # Sanity: tests_to_run is sorted and non-empty
    assert tests_to_run
    assert tests_to_run == sorted(tests_to_run)
