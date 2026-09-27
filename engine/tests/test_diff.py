"""test_diff.py — unit tests for uplift.diff.

All tests use a tiny fixture project created inside tmp_path, so they run
anywhere without requiring the real sample-app.
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from uplift.diff import changed_symbols, head_and_base


# ---------------------------------------------------------------------------
# Helpers: build a minimal Python project inside tmp_path
# ---------------------------------------------------------------------------

def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


def _make_repo(tmp_path: Path) -> Path:
    """Create a minimal repo with shop/service.py containing two functions."""
    repo = tmp_path / "repo"
    _write(
        repo / "shop" / "service.py",
        """\
        def get_item(item_id: int):
            if item_id is None:
                raise ValueError("item_id required")
            return {"id": item_id}


        def list_items() -> list:
            return []
        """,
    )
    return repo


def _git_init(repo: Path) -> None:
    """Initialise a bare git repo so git apply works."""
    import subprocess
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test"],
        cwd=repo, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo, check=True, capture_output=True,
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo, check=True, capture_output=True,
    )


# ---------------------------------------------------------------------------
# Case 1: body-only change (raise removed) -> changeType "behavior"
# ---------------------------------------------------------------------------

def test_behavior_raise_removed(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _git_init(repo)

    patch_text = textwrap.dedent("""\
        --- a/shop/service.py
        +++ b/shop/service.py
        @@ -1,4 +1,3 @@
         def get_item(item_id: int):
        -    if item_id is None:
        -        raise ValueError("item_id required")
        +    pass
             return {"id": item_id}
        """)
    patch = tmp_path / "case1.patch"
    patch.write_text(patch_text, encoding="utf-8")

    head, base = head_and_base(repo, patch, applied=False)
    symbols = changed_symbols(head, base, patch)

    assert len(symbols) == 1
    s = symbols[0]
    assert s["changeType"] == "behavior"
    assert "raise removed" in s["hints"]


# ---------------------------------------------------------------------------
# Case 2: argument list change -> changeType "signature"
# ---------------------------------------------------------------------------

def test_signature_change(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _git_init(repo)

    patch_text = textwrap.dedent("""\
        --- a/shop/service.py
        +++ b/shop/service.py
        @@ -1,4 +1,4 @@
        -def get_item(item_id: int):
        +def get_item(item_id: int, include_meta: bool = False):
             if item_id is None:
                 raise ValueError("item_id required")
             return {"id": item_id}
        """)
    patch = tmp_path / "case2.patch"
    patch.write_text(patch_text, encoding="utf-8")

    head, base = head_and_base(repo, patch, applied=False)
    symbols = changed_symbols(head, base, patch)

    assert len(symbols) == 1
    assert symbols[0]["changeType"] == "signature"


# ---------------------------------------------------------------------------
# Case 3: delete a function -> "removed"; add a function -> "added"
# ---------------------------------------------------------------------------

def test_removed_and_added(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _git_init(repo)

    patch_text = textwrap.dedent("""\
        --- a/shop/service.py
        +++ b/shop/service.py
        @@ -5,4 +5,6 @@
         
         
        -def list_items() -> list:
        -    return []
        +def list_items() -> list:
        +    return []
        +
        +def delete_item(item_id: int) -> None:
        +    pass
        """)
    # We'll use a simpler approach: write a patch that removes list_items entirely
    # and adds a new function new_function
    # Generate valid unified context lines (blank context lines require a space).
    import difflib
    original = (repo / "shop/service.py").read_text(encoding="utf-8")
    replacement = original.replace("def list_items() -> list:\n    return []", "def new_function() -> dict:\n    return {}")
    patch_text2 = "".join(difflib.unified_diff(original.splitlines(True), replacement.splitlines(True), fromfile="a/shop/service.py", tofile="b/shop/service.py"))
    patch = tmp_path / "case3.patch"
    patch.write_text(patch_text2, encoding="utf-8")

    head, base = head_and_base(repo, patch, applied=False)
    symbols = changed_symbols(head, base, patch)

    change_types = {s["changeType"] for s in symbols}
    ids = {s["id"].split("#")[1] for s in symbols}
    assert "removed" in change_types
    assert "added" in change_types
    assert "list_items" in ids
    assert "new_function" in ids


# ---------------------------------------------------------------------------
# Case 4: --applied and not-applied give the same changedSymbols
# ---------------------------------------------------------------------------

def _make_patch(repo: Path, new_content: str) -> str:
    """Modify a file, capture git diff, then restore. Returns the diff text."""
    import subprocess
    svc = repo / "shop" / "service.py"
    original = svc.read_text(encoding="utf-8")
    svc.write_text(new_content, encoding="utf-8")
    r = subprocess.run(["git", "diff"], cwd=repo, capture_output=True, text=True, check=True)
    svc.write_text(original, encoding="utf-8")
    return r.stdout


def test_applied_and_unapplied_equivalent(tmp_path: Path) -> None:
    import subprocess
    import shutil

    repo = _make_repo(tmp_path)
    _git_init(repo)

    new_content = (
        "def get_item(item_id: int):\n"
        "    return {\"id\": item_id}\n"
        "\n"
        "\n"
        "def list_items() -> list:\n"
        "    return []\n"
    )
    patch_text = _make_patch(repo, new_content)
    assert patch_text, "git diff produced no output"
    patch = tmp_path / "case4.patch"
    patch.write_text(patch_text, encoding="utf-8")

    # unapplied
    head_u, base_u = head_and_base(repo, patch, applied=False)
    symbols_unapplied = changed_symbols(head_u, base_u, patch)

    # applied: make a copy of repo with the patch already applied
    applied_repo = tmp_path / "applied_repo"
    shutil.copytree(repo, applied_repo)
    subprocess.run(
        ["git", "apply", "--whitespace=nowarn", str(patch.resolve())],
        cwd=applied_repo, check=True, capture_output=True,
    )

    head_a, base_a = head_and_base(applied_repo, patch, applied=True)
    symbols_applied = changed_symbols(head_a, base_a, patch)

    # Both must report the same set of (id, changeType)
    key = lambda s: (s["id"], s["changeType"])
    assert sorted(symbols_unapplied, key=key) == sorted(symbols_applied, key=key)


# ---------------------------------------------------------------------------
# Case 5: test-only changes produce no changed symbols
# ---------------------------------------------------------------------------

def test_test_files_excluded(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    # Add a tests/ file
    _write(
        repo / "tests" / "test_service.py",
        """\
        def test_something():
            pass
        """,
    )
    _git_init(repo)

    # Patch only touches the test file
    patch_text = textwrap.dedent("""\
        --- a/tests/test_service.py
        +++ b/tests/test_service.py
        @@ -1,2 +1,3 @@
         def test_something():
             pass
        +
        +def test_another():
        +    assert True
        """)
    patch = tmp_path / "case5.patch"
    patch.write_text(patch_text, encoding="utf-8")

    head, base = head_and_base(repo, patch, applied=False)
    symbols = changed_symbols(head, base, patch)

    assert symbols == [], f"Expected no symbols, got: {symbols}"
