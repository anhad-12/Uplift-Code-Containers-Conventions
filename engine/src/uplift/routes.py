"""routes.py — extract FastAPI route definitions from a project tree.

Public API
----------
route_map(root) -> list[dict]

Each entry: {"method": "GET", "path": "/users/{user_id}", "handler": "shop/users/routes.py#get_user_route", "file": "shop/users/routes.py"}

Detection rules (pure AST, no imports):
  1. Scan every routes.py under <root>/shop/.
  2. Collect APIRouter variable names and their prefix= keyword argument.
  3. For each function decorated with @<router_var>.<http_method>("...", ...) emit a route.
  4. For app.include_router(router_var, prefix="/extra") in any .py under root/shop/,
     add the extra prefix to all routes whose handler variable matches router_var.
     (The sample-app does not use this pattern, but we handle it for completeness.)
"""
from __future__ import annotations

import ast
from pathlib import Path

HTTP_METHODS: frozenset[str] = frozenset({"get", "post", "put", "delete", "patch"})


def _collect_router_prefixes(tree: ast.AST) -> dict[str, str]:
    """Return {variable_name: prefix} for every APIRouter(...) assignment in *tree*."""
    prefixes: dict[str, str] = {}
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Call)
            and getattr(node.value.func, "id", "") == "APIRouter"
        ):
            continue
        prefix = next(
            (
                kw.value.value  # type: ignore[attr-defined]
                for kw in node.value.keywords
                if kw.arg == "prefix"
                and isinstance(kw.value, ast.Constant)
            ),
            "",
        )
        for target in node.targets:
            if isinstance(target, ast.Name):
                prefixes[target.id] = prefix
    return prefixes


def _collect_include_extra_prefixes(root: Path) -> dict[str, str]:
    """Return {router_var_name: extra_prefix} from app.include_router(var, prefix=...) calls.

    Only captures calls where a ``prefix`` keyword is supplied; calls without
    an extra prefix are silently ignored (the router's own prefix is enough).
    """
    extras: dict[str, str] = {}
    for py_file in sorted(root.rglob("*.py")):
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            # Match: <anything>.include_router(<name>, prefix="...")
            if not (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr == "include_router"
            ):
                continue
            call: ast.Call = node.value
            if not call.args or not isinstance(call.args[0], ast.Name):
                continue
            router_var = call.args[0].id
            extra = next(
                (
                    kw.value.value  # type: ignore[attr-defined]
                    for kw in call.keywords
                    if kw.arg == "prefix" and isinstance(kw.value, ast.Constant)
                ),
                None,
            )
            if extra is not None:
                extras[router_var] = extra
    return extras


def route_map(root: Path) -> list[dict]:
    """Return all FastAPI routes found under *root*/shop/."""
    extra_prefixes = _collect_include_extra_prefixes(root)
    routes: list[dict] = []

    for routes_file in sorted((root / "shop").rglob("routes.py")):
        try:
            source = routes_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (OSError, SyntaxError):
            continue

        prefixes = _collect_router_prefixes(tree)
        rel = routes_file.relative_to(root).as_posix()

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for dec in node.decorator_list:
                if not (
                    isinstance(dec, ast.Call)
                    and isinstance(dec.func, ast.Attribute)
                    and dec.func.attr in HTTP_METHODS
                    and isinstance(dec.func.value, ast.Name)
                    and dec.func.value.id in prefixes
                ):
                    continue
                router_var = dec.func.value.id
                sub = (
                    dec.args[0].value  # type: ignore[attr-defined]
                    if dec.args and isinstance(dec.args[0], ast.Constant)
                    else ""
                )
                base_prefix = prefixes[router_var]
                extra = extra_prefixes.get(router_var, "")
                full_path = extra + base_prefix + sub
                routes.append(
                    {
                        "method": dec.func.attr.upper(),
                        "path": full_path,
                        "handler": f"{rel}#{node.name}",
                        "file": rel,
                    }
                )

    return routes


def contracts_for(candidates: list[dict], routes: list[dict]) -> list[dict]:
    """Return contract entries for every candidate that is a route handler.

    A contract is {"type": "route", "id": "METHOD /path", "handler": "<candidate_id>", "verdict": "unknown"}.
    """
    handler_to_route: dict[str, dict] = {r["handler"]: r for r in routes}
    contracts: list[dict] = []
    for candidate in candidates:
        cid = candidate["id"]
        if cid in handler_to_route:
            r = handler_to_route[cid]
            contracts.append(
                {
                    "type": "route",
                    "id": f"{r['method']} {r['path']}",
                    "handler": cid,
                    "verdict": "unknown",
                }
            )
    return contracts
