"""test_routes.py — tests for uplift.routes.route_map and contracts_for.

Integration tests are skipped if sample-app/ is not found.
"""
from __future__ import annotations

import ast
import textwrap
from pathlib import Path

import pytest

from uplift.routes import contracts_for, route_map


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


# ---------------------------------------------------------------------------
# Fixture unit tests
# ---------------------------------------------------------------------------

def test_route_map_basic(tmp_path: Path) -> None:
    """route_map returns all decorated routes from a routes.py."""
    _write(
        tmp_path / "shop" / "users" / "routes.py",
        """\
        from fastapi import APIRouter

        router = APIRouter(prefix="/users")


        @router.get("/{user_id}")
        def get_user_route(user_id: int):
            pass


        @router.get("")
        def list_users_route():
            pass
        """,
    )

    routes = route_map(tmp_path)
    methods_paths = {(r["method"], r["path"]) for r in routes}
    assert ("GET", "/users/{user_id}") in methods_paths
    assert ("GET", "/users") in methods_paths
    for r in routes:
        assert r["handler"].startswith("shop/users/routes.py#")


def test_route_map_post(tmp_path: Path) -> None:
    """route_map handles POST routes correctly."""
    _write(
        tmp_path / "shop" / "orders" / "routes.py",
        """\
        from fastapi import APIRouter

        router = APIRouter(prefix="/orders")


        @router.post("")
        def post_order(payload):
            pass
        """,
    )
    routes = route_map(tmp_path)
    assert any(r["method"] == "POST" and r["path"] == "/orders" for r in routes)


def test_route_map_extra_prefix(tmp_path: Path) -> None:
    """Extra prefix from app.include_router(..., prefix='/api') is prepended."""
    _write(
        tmp_path / "shop" / "users" / "routes.py",
        """\
        from fastapi import APIRouter

        router = APIRouter(prefix="/users")


        @router.get("")
        def list_users():
            pass
        """,
    )
    _write(
        tmp_path / "shop" / "app.py",
        """\
        from fastapi import FastAPI
        from shop.users.routes import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        """,
    )
    routes = route_map(tmp_path)
    assert any(r["path"] == "/api/users" for r in routes), (
        f"Expected /api/users, got: {[r['path'] for r in routes]}"
    )


def test_contracts_for(tmp_path: Path) -> None:
    """contracts_for returns a contract entry for candidate ids that match a handler."""
    routes = [
        {"method": "GET", "path": "/users/{user_id}", "handler": "shop/users/routes.py#get_user_route", "file": "shop/users/routes.py"},
        {"method": "POST", "path": "/orders", "handler": "shop/orders/routes.py#post_order", "file": "shop/orders/routes.py"},
    ]
    candidates = [
        {"id": "shop/users/routes.py#get_user_route", "hop": 1},
        {"id": "shop/users/service.py#get_user", "hop": 1},  # not a route handler
    ]
    contracts = contracts_for(candidates, routes)
    assert len(contracts) == 1
    ct = contracts[0]
    assert ct["type"] == "route"
    assert ct["id"] == "GET /users/{user_id}"
    assert ct["handler"] == "shop/users/routes.py#get_user_route"
    assert ct["verdict"] == "unknown"


def test_contracts_for_empty(tmp_path: Path) -> None:
    """No contracts when no candidates match a route handler."""
    routes = [{"method": "GET", "path": "/x", "handler": "shop/x/routes.py#fn", "file": "shop/x/routes.py"}]
    candidates = [{"id": "shop/y/service.py#fn", "hop": 1}]
    assert contracts_for(candidates, routes) == []


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
# Integration: s1-null-user route_map
# ---------------------------------------------------------------------------

@pytest.mark.skipif(SAMPLE_APP is None, reason=_SKIP_MSG)
def test_s1_route_map() -> None:
    """route_map on the demo app must return the 5 expected routes."""
    assert SAMPLE_APP is not None
    routes = route_map(SAMPLE_APP)
    method_paths = {(r["method"], r["path"]) for r in routes}

    expected = {
        ("POST", "/orders"),
        ("GET", "/orders/{order_id}"),
        ("POST", "/payments"),
        ("GET", "/users/{user_id}"),
        ("GET", "/users"),
    }
    missing = expected - method_paths
    assert not missing, (
        f"Missing routes: {missing}\nActual: {method_paths}"
    )


@pytest.mark.skipif(SAMPLE_APP is None, reason=_SKIP_MSG)
def test_s1_contracts_include_expected() -> None:
    """contracts_for on the s1 graph must include GET /users/{user_id}, POST /orders, POST /payments."""
    assert SAMPLE_APP is not None
    from uplift.diff import changed_symbols, head_and_base
    from uplift.graph import find_candidates

    patch = SAMPLE_APP / "scenarios" / "s1-null-user.patch"
    if not patch.exists():
        pytest.skip(f"Patch not found: {patch}")

    head, base = head_and_base(SAMPLE_APP, patch, applied=False)
    changed = changed_symbols(head, base, patch)
    candidates = find_candidates(head, changed)
    routes = route_map(head)
    contracts = contracts_for(candidates, routes)

    contract_ids = {ct["id"] for ct in contracts}
    expected = {"GET /users/{user_id}", "POST /orders", "POST /payments"}
    missing = expected - contract_ids
    assert not missing, (
        f"Missing contracts: {missing}\nActual: {contract_ids}"
    )

    # Each contract must have the correct handler
    handler_map = {ct["id"]: ct["handler"] for ct in contracts}
    assert handler_map.get("GET /users/{user_id}") == "shop/users/routes.py#get_user_route"
