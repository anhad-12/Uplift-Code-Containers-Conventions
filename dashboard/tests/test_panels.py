"""
Tests for dashboard/panels.py — C4 requirements.

Run from the dashboard/ directory (or repo root with PYTHONPATH set):
    python -m pytest -q dashboard/tests/test_panels.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure the dashboard package root is importable when pytest is run from the
# repo root rather than from dashboard/.
_DASH_ROOT = Path(__file__).resolve().parent.parent
if str(_DASH_ROOT) not in sys.path:
    sys.path.insert(0, str(_DASH_ROOT))

import panels  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────────────

_REPORTS = _DASH_ROOT / "reports"


def _report(name: str) -> dict:
    return json.loads((_REPORTS / name).read_text(encoding="utf-8"))


def _s1() -> dict:
    return _report("impact-s1.mock.json")


# ── 1. detail_panel for a normal affected item ────────────────────────────────

def test_detail_panel_returns_component_for_affected_item():
    r = _s1()
    item = r["affected"][0]  # build_invoice — will_break, has proof + repair
    component = panels.detail_panel(item)
    rendered = str(component)

    # id must appear
    assert "shop/orders/invoice.py#build_invoice" in rendered
    # file:line
    assert "shop/orders/invoice.py" in rendered
    assert "18" in rendered
    # module, hop, layer
    assert "orders" in rendered
    assert "1" in rendered
    assert "direct" in rendered
    # snippet in a code block (dcc.Markdown)
    assert "Markdown" in rendered
    assert "get_user" in rendered
    # verdict badge
    assert "will_break" in rendered
    # reason
    assert "None check" in rendered
    # fix
    assert "Fix" in rendered
    # proof section
    assert "Proof" in rendered
    assert "confirmed" in rendered.lower() or "Confirmed" in rendered
    assert "yes" in rendered  # tick + yes for passesOnBase and failsOnHead
    # repair section
    assert "Repair" in rendered
    assert "fixed" in rendered


def test_detail_panel_shows_passes_on_base_and_fails_on_head():
    r = _s1()
    # item at index 0 has passesOnBase=True, failsOnHead=True
    item = r["affected"][0]
    rendered = str(panels.detail_panel(item))
    assert "Passes on base" in rendered
    assert "Fails on head" in rendered
    assert "✓ yes" in rendered


def test_detail_panel_shows_test_file():
    r = _s1()
    item = r["affected"][0]
    rendered = str(panels.detail_panel(item))
    assert "test_invoice_missing_user" in rendered


# ── 2. detail_panel for a contract ───────────────────────────────────────────

def test_detail_panel_returns_component_for_contract():
    r = _s1()
    # Contracts use raw dict from report["contracts"], id does NOT start with "contract:"
    # in the raw data — the "contract:" prefix is added by graph.py as a node id.
    # panels.detail_panel must accept the raw contract dict directly when called
    # from the show_detail callback (which passes find_item's result).
    # find_item strips the prefix back to the contract dict, so we call with the
    # raw dict here; the id in the raw dict does NOT start with "contract:".
    contract = r["contracts"][0]
    # The callback passes the raw contract dict; we verify detail_panel handles it
    rendered = str(panels.detail_panel(contract))
    # route id appears
    assert "GET /users/{user_id}" in rendered
    # handler
    assert "shop/users/routes.py#get_user_route" in rendered
    # verdict
    assert "will_break" in rendered
    # reason
    assert "null" in rendered.lower() or "404" in rendered or "None" in rendered
    # proof section
    assert "Proof" in rendered


def test_detail_panel_for_contract_with_contract_prefix_in_id():
    """detail_panel must also work when the id already has the 'contract:' prefix."""
    contract = {
        "id": "contract:GET /orders/{order_id}",
        "handler": "shop/orders/routes.py#get_order",
        "verdict": "might_break",
        "reason": "Returns a different shape.",
        "proof": {"status": "not_attempted"},
    }
    rendered = str(panels.detail_panel(contract))
    assert "GET /orders/{order_id}" in rendered
    assert "might_break" in rendered
    # Route and Handler headings appear (not file/module/hop/layer)
    assert "Route" in rendered
    assert "Handler" in rendered
    assert "shop/orders/routes.py#get_order" in rendered


# ── 3. detail_panel for an item without a proof ───────────────────────────────

def test_detail_panel_no_proof():
    item = {
        "id": "shop/admin/reports.py#user_spend_report",
        "file": "shop/admin/reports.py",
        "line": 33,
        "module": "admin",
        "hop": 2,
        "layer": "indirect",
        "via": "shop/orders/service.py#create_order",
        "snippet": "rows = [{\"user\": get_user(o.user_id).name} for o in orders]",
        "tests": [],
        "verdict": "might_break",
        "reason": "Reads .name on get_user's result.",
        "fix": "Skip orders whose user is None.",
        # no "proof" key at all
    }
    component = panels.detail_panel(item)
    rendered = str(component)
    assert "might_break" in rendered
    assert "Proof" in rendered
    # no crash, component renders
    assert "admin" in rendered


def test_detail_panel_proof_not_attempted():
    r = _s1()
    # user_spend_report has proof.status = "not_attempted"
    item = next(a for a in r["affected"] if "user_spend_report" in a["id"])
    rendered = str(panels.detail_panel(item))
    # should not show passes-on-base / fails-on-head rows for not_attempted
    assert "Passes on base" not in rendered
    assert "Fails on head" not in rendered


# ── 4. affected_table row count equals len(report["affected"]) ────────────────

def test_table_rows_count_equals_affected():
    r = _s1()
    rows = panels.build_table_rows(r)
    assert len(rows) == len(r["affected"])


def test_table_rows_have_correct_columns():
    r = _s1()
    rows = panels.build_table_rows(r)
    expected_keys = {"id", "module", "hop", "layer", "verdict", "proof", "repair"}
    for row in rows:
        assert set(row.keys()) == expected_keys


def test_affected_table_returns_datatable():
    from dash import dash_table as _dash_table  # noqa: PLC0415
    r = _s1()
    table = panels.affected_table(r)
    assert isinstance(table, _dash_table.DataTable)
    assert len(table.data) == len(r["affected"])


def test_affected_table_native_sorting():
    r = _s1()
    table = panels.affected_table(r)
    assert table.sort_action == "native"


def test_affected_table_conditional_styling_present():
    r = _s1()
    table = panels.affected_table(r)
    # At least one conditional rule for will_break — rules are nested: rule["if"]["filter_query"]
    conditions = [c.get("if", {}).get("filter_query", "") for c in (table.style_data_conditional or [])]
    assert any("will_break" in c for c in conditions)
    assert any("might_break" in c for c in conditions)
    assert any("safe" in c for c in conditions)


# ── 5. Migrate mock: detail_panel works on a different report ─────────────────

def test_detail_panel_on_migrate_report():
    r = _report("migrate-pydantic2.mock.json")
    affected = r.get("affected", [])
    if not affected:
        return  # skip if migrate mock has no affected items
    item = affected[0]
    rendered = str(panels.detail_panel(item))
    assert item["id"] in rendered
    assert item["verdict"] in rendered
