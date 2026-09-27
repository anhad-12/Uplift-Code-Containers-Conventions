"""test_migrate.py — unit tests for uplift.migrate.

All tests use tmp_path fixtures and skip gracefully when the real
sample-app is not present so they always pass in CI.
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from uplift.migrate import _parse_junit_by_module, module_of, scan


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


def _make_shop(root: Path) -> None:
    """Create a minimal shop/ package for scanning."""
    _write(root / "shop" / "__init__.py", "")
    _write(root / "shop" / "config.py", """\
        from pydantic import BaseSettings

        class Settings(BaseSettings):
            sender: str = "no-reply@example.com"
        """)
    _write(root / "shop" / "users" / "__init__.py", "")
    _write(root / "shop" / "users" / "schemas.py", """\
        from pydantic import BaseModel, validator

        class UserOut(BaseModel):
            name: str

            class Config:
                orm_mode = True

            @validator("name")
            def not_empty(cls, v):
                return v
        """)
    _write(root / "shop" / "orders" / "__init__.py", "")
    _write(root / "shop" / "orders" / "schemas.py", """\
        from pydantic import BaseModel
        from typing import Optional

        class OrderOut(BaseModel):
            total: float

            class Config:
                orm_mode = True

            price: Optional[float]
        """)
    _write(root / "shop" / "payments" / "__init__.py", "")
    _write(root / "shop" / "payments" / "schemas.py", """\
        from pydantic import BaseModel

        class PaymentIn(BaseModel):
            amount: float = 0.0
            regex = "^[0-9]+$"
        """)


CATALOG = [
    {"id": "p2-basesettings", "detect": {"type": "import", "pattern": "from pydantic import BaseSettings"}},
    {"id": "p2-orm-mode", "detect": {"type": "regex", "pattern": r"orm_mode\s*=\s*True"}},
    {"id": "p2-field-regex", "detect": {"type": "regex", "pattern": r"\bregex\s*="}},
    {"id": "p2-validator", "detect": {"type": "call", "pattern": "validator"}},
    {"id": "p2-optional", "detect": {"type": "regex", "pattern": r":\s*Optional\[[^\]]+\]\s*$"}},
]


# ---------------------------------------------------------------------------
# module_of
# ---------------------------------------------------------------------------

def test_module_of_nested() -> None:
    assert module_of("shop/users/service.py") == "users"


def test_module_of_top_level() -> None:
    assert module_of("shop/config.py") == "core"


def test_module_of_non_shop() -> None:
    assert module_of("tests/test_foo.py") == "core"


# ---------------------------------------------------------------------------
# scan — each detect type
# ---------------------------------------------------------------------------

def test_scan_import(tmp_path: Path) -> None:
    _make_shop(tmp_path)
    results = scan(tmp_path, [{"id": "p2-basesettings", "detect": {"type": "import", "pattern": "from pydantic import BaseSettings"}}])
    assert len(results) == 1
    assert results[0]["entry"] == "p2-basesettings"
    assert results[0]["module"] == "core"


def test_scan_regex(tmp_path: Path) -> None:
    _make_shop(tmp_path)
    results = scan(tmp_path, [{"id": "p2-orm-mode", "detect": {"type": "regex", "pattern": r"orm_mode\s*=\s*True"}}])
    modules = {r["module"] for r in results}
    # users and orders both have orm_mode = True
    assert "users" in modules
    assert "orders" in modules
    assert len(results) == 2


def test_scan_call(tmp_path: Path) -> None:
    _make_shop(tmp_path)
    results = scan(tmp_path, [{"id": "p2-validator", "detect": {"type": "call", "pattern": "validator"}}])
    assert len(results) >= 1
    assert any(r["module"] == "users" for r in results)


def test_scan_optional_regex(tmp_path: Path) -> None:
    _make_shop(tmp_path)
    results = scan(tmp_path, [{"id": "p2-optional", "detect": {"type": "regex", "pattern": r":\s*Optional\[[^\]]+\]\s*$"}}])
    assert len(results) >= 1
    assert any(r["module"] == "orders" for r in results)


def test_scan_field_regex(tmp_path: Path) -> None:
    _make_shop(tmp_path)
    results = scan(tmp_path, [{"id": "p2-field-regex", "detect": {"type": "regex", "pattern": r"\bregex\s*="}}])
    assert len(results) >= 1
    assert any(r["module"] == "payments" for r in results)


def test_scan_no_shop(tmp_path: Path) -> None:
    """scan returns empty list when shop/ doesn't exist."""
    results = scan(tmp_path, CATALOG)
    assert results == []


# ---------------------------------------------------------------------------
# _parse_junit_by_module — per-module grouping including collection errors
# ---------------------------------------------------------------------------

_JUNIT_NORMAL = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="3" errors="0" failures="1">
    <testcase classname="tests.orders.test_service" name="test_create_ok" />
    <testcase classname="tests.orders.test_service" name="test_create_bad">
      <failure>AssertionError</failure>
    </testcase>
    <testcase classname="tests.users.test_routes" name="test_get_user" />
  </testsuite>
</testsuites>
"""

_JUNIT_COLLECTION_ERROR = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="1" errors="1" failures="0">
    <testcase classname="" name="tests.orders.test_service" >
      <error>ImportError: cannot import</error>
    </testcase>
  </testsuite>
</testsuites>
"""


def test_parse_junit_normal(tmp_path: Path) -> None:
    xml = tmp_path / "junit.xml"
    xml.write_text(_JUNIT_NORMAL, encoding="utf-8")
    result = _parse_junit_by_module(xml)
    assert result["passed"] == 2
    assert result["failed"] == 1
    by = result["byModule"]
    assert by["orders"]["passed"] == 1
    assert by["orders"]["failed"] == 1
    assert by["users"]["passed"] == 1


def test_parse_junit_collection_error(tmp_path: Path) -> None:
    xml = tmp_path / "junit.xml"
    xml.write_text(_JUNIT_COLLECTION_ERROR, encoding="utf-8")
    result = _parse_junit_by_module(xml)
    assert result["failed"] == 1
    assert result["passed"] == 0
    # collection error for tests.orders.test_service -> "orders"
    assert result["byModule"].get("orders", {}).get("failed", 0) == 1


def test_parse_junit_missing(tmp_path: Path) -> None:
    result = _parse_junit_by_module(tmp_path / "nonexistent.xml")
    assert result["passed"] == 0
    assert result["failed"] == 0


# ---------------------------------------------------------------------------
# Integration: scan against real sample-app (skip if absent)
# ---------------------------------------------------------------------------

SAMPLE_APP = Path(__file__).parent.parent.parent / "sample-app"


@pytest.mark.skipif(not SAMPLE_APP.exists(), reason="sample-app not present")
def test_scan_real_app_counts() -> None:
    """Sample app is fully migrated to pydantic v2 — scan finds zero occurrences."""
    results = scan(SAMPLE_APP, CATALOG)
    counts: dict[str, int] = {}
    for r in results:
        counts[r["entry"]] = counts.get(r["entry"], 0) + 1

    assert counts.get("p2-basesettings", 0) == 0, f"basesettings count: {counts}"
    assert counts.get("p2-orm-mode", 0) == 0, f"orm-mode count: {counts}"
    assert counts.get("p2-validator", 0) == 0, f"validator count: {counts}"
    assert counts.get("p2-optional", 0) == 0, f"optional count: {counts}"
    assert counts.get("p2-field-regex", 0) == 0, f"field-regex count: {counts}"


@pytest.mark.skipif(not SAMPLE_APP.exists(), reason="sample-app not present")
def test_scan_real_app_modules() -> None:
    """Sample app is fully migrated to pydantic v2 — no pattern entries by module."""
    results = scan(SAMPLE_APP, CATALOG)
    assert results == [], f"unexpected occurrences after migration: {results}"
