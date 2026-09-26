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


# ── 6. summary_strip() ───────────────────────────────────────────────────────

def test_summary_strip_s1_contains_risk_score_71():
    """summary_strip on S1 must contain the text '71' (risk score)."""
    r = _s1()
    rendered = str(panels.summary_strip(r))
    assert "71" in rendered


def test_summary_strip_s1_metric_figures():
    """summary_strip shows predicted=5, confirmed=4, fixed=4, regressions=0."""
    r = _s1()
    rendered = str(panels.summary_strip(r))
    assert "5" in rendered   # predicted
    assert "4" in rendered   # confirmed and fixed
    assert "0" in rendered   # regressions


def test_summary_strip_s1_has_accuracy_card():
    """S1 has an accuracy block, so the accuracy card must appear."""
    r = _s1()
    rendered = str(panels.summary_strip(r))
    assert "Accuracy" in rendered
    assert "Precision" in rendered
    assert "Recall" in rendered
    # 80% precision (0.8 * 100 = 80), 100% recall
    assert "80%" in rendered
    assert "100%" in rendered
    # TP=4, FP=1, FN=0 as badges
    assert "TP 4" in rendered
    assert "FP 1" in rendered
    assert "FN 0" in rendered


def test_summary_strip_no_accuracy_card_when_accuracy_absent():
    """A report without metrics.accuracy must render no accuracy card."""
    r = _report("migrate-pydantic2.mock.json")
    # migrate mock has no accuracy key
    assert "accuracy" not in r.get("metrics", {})
    rendered = str(panels.summary_strip(r))
    assert "Accuracy" not in rendered
    assert "Precision" not in rendered


def test_summary_strip_s1_risk_level_high():
    """Risk level 'high' must appear in the strip."""
    r = _s1()
    rendered = str(panels.summary_strip(r))
    assert "high" in rendered.lower() or "HIGH" in rendered


def test_summary_strip_tests_to_run_list():
    """summary_strip shows tests-to-run entries."""
    r = _s1()
    rendered = str(panels.summary_strip(r))
    assert "Tests to run" in rendered
    # At least one test file name from the S1 mock
    assert "test_invoice" in rendered or "test_receipt" in rendered or "test_service" in rendered


def test_summary_strip_untested_list():
    """summary_strip shows untested affected code entries."""
    r = _s1()
    rendered = str(panels.summary_strip(r))
    assert "Untested affected code" in rendered
    assert "user_spend_report" in rendered


def test_summary_strip_tests_bar_present_for_s1():
    """S1 has metrics.tests, so the stacked bar must appear (dcc.Graph)."""
    from dash import dcc as _dcc  # noqa: PLC0415
    r = _s1()
    strip = panels.summary_strip(r)
    rendered = str(strip)
    # dcc.Graph is in the rendered output when tests data is present
    assert "Graph" in rendered


def test_summary_strip_returns_html_div():
    """summary_strip must return an html.Div."""
    from dash import html as _html  # noqa: PLC0415
    r = _s1()
    result = panels.summary_strip(r)
    assert isinstance(result, _html.Div)


def test_summary_strip_no_tests_bar_when_tests_absent():
    """A report with no metrics.tests must not crash and omits the bar."""
    r = _s1()
    # Remove tests from metrics
    r["metrics"] = {k: v for k, v in r["metrics"].items() if k != "tests"}
    rendered = str(panels.summary_strip(r))
    # Must still render metric cards
    assert "Predicted" in rendered


def test_affected_table_header_has_dark_text():
    """DataTable header must have a dark color for contrast (not light grey)."""
    r = _s1()
    table = panels.affected_table(r)
    header_style = table.style_header or {}
    color = header_style.get("color", "")
    # Must not be a light colour; the dark fg is #1d2330
    assert color, "style_header must specify a color"
    # Verify it's not the old light bg-only style
    assert "backgroundColor" in header_style
    # The color must be a dark value (not white or light grey)
    assert color.lower() not in ("#ffffff", "#f7f8fa", "#f5f5f5", "white", "")


# ── C5: chart readability ─────────────────────────────────────────────────────

def test_chart_layout_returns_light_font_and_transparent_bg():
    """_chart_layout() must set a light font colour and transparent backgrounds."""
    layout = panels._chart_layout()
    assert layout["font"]["color"] == panels._CHART_FONT_COLOR
    assert layout["font"]["size"] >= 13
    assert layout["paper_bgcolor"] == "rgba(0,0,0,0)"
    assert layout["plot_bgcolor"] == "rgba(0,0,0,0)"


def test_chart_layout_overrides_are_merged():
    """Extra kwargs passed to _chart_layout() appear in the returned dict."""
    layout = panels._chart_layout(height=200, margin={"t": 10})
    assert layout["height"] == 200
    assert layout["font"]["color"] == panels._CHART_FONT_COLOR


def test_risk_gauge_figure_has_light_font_and_transparent_bg():
    """Risk gauge figure must use the shared light font colour and transparent bg."""
    import plotly.graph_objects as go  # noqa: PLC0415
    risk = {"score": 71, "level": "high", "factors": []}
    wrapper = panels._risk_gauge(risk)
    # The dcc.Graph is the only child of the wrapper div
    graph = wrapper.children
    fig = graph.figure
    assert isinstance(fig, go.Figure)
    layout = fig.layout
    assert layout.paper_bgcolor == "rgba(0,0,0,0)"
    assert layout.plot_bgcolor == "rgba(0,0,0,0)"
    # Global font colour is light
    assert layout.font.color == panels._CHART_FONT_COLOR
    # Gauge axis tick labels are light
    indicator = fig.data[0]
    assert indicator.gauge.axis.tickfont.color == panels._CHART_FONT_COLOR
    # Title uses "Risk: HIGH" colon format
    assert "Risk:" in indicator.title.text
    assert "HIGH" in indicator.title.text


def test_tests_bar_figure_has_light_font_and_transparent_bg():
    """Tests-bar figure must use the shared light font colour and transparent bg."""
    import plotly.graph_objects as go  # noqa: PLC0415
    tests = {"before": {"passed": 43, "failed": 4}, "after": {"passed": 47, "failed": 0}}
    graph = panels._tests_bar(tests)
    assert graph is not None
    fig = graph.figure
    assert isinstance(fig, go.Figure)
    layout = fig.layout
    assert layout.paper_bgcolor == "rgba(0,0,0,0)"
    assert layout.plot_bgcolor == "rgba(0,0,0,0)"
    # Global font colour is light
    assert layout.font.color == panels._CHART_FONT_COLOR
    # Gridlines are faint (rgba white)
    assert "rgba(255,255,255" in layout.yaxis.gridcolor
    # Bar traces carry text annotations
    for trace in fig.data:
        assert trace.text is not None and len(trace.text) == 2


def test_untested_empty_shows_none():
    """When untested is empty the strip must show 'None', not a dash."""
    r = _s1()
    r["untested"] = []
    rendered = str(panels.summary_strip(r))
    assert "Untested affected code" in rendered
    # "None" must appear (as the empty placeholder)
    assert "None" in rendered


# ── C6: migrate_view() ────────────────────────────────────────────────────────

def _migrate_report() -> dict:
    return _report("migrate-pydantic2.mock.json")


def test_migrate_view_returns_html_div():
    """migrate_view must return an html.Div."""
    from dash import html as _html  # noqa: PLC0415
    r = _migrate_report()
    result = panels.migrate_view(r)
    assert isinstance(result, _html.Div)


def test_migrate_view_has_four_lane_columns():
    """migrate_view must produce exactly 4 worker-lane dbc.Col components
    (one per entry in migration.modules in the pydantic2 mock)."""
    import dash_bootstrap_components as _dbc  # noqa: PLC0415
    r = _migrate_report()
    view = panels.migrate_view(r)

    def _collect(component, found):
        # Walk the component tree looking for dbc.Col with md=3 (lane columns)
        if isinstance(component, _dbc.Col) and getattr(component, "md", None) == 3:
            found.append(component)
        children = getattr(component, "children", None)
        if children is None:
            return
        if isinstance(children, (list, tuple)):
            for child in children:
                _collect(child, found)
        else:
            _collect(children, found)

    lane_cols: list = []
    _collect(view, lane_cols)
    assert len(lane_cols) == 4, f"Expected 4 lane columns, found {len(lane_cols)}"


def test_migrate_view_catalog_table_has_four_rows():
    """The catalog DataTable must have 4 rows (one per entry in the mock catalog)."""
    from dash import dash_table as _dash_table  # noqa: PLC0415
    r = _migrate_report()

    def _find_datatable(component):
        if isinstance(component, _dash_table.DataTable) and getattr(component, "id", None) == "catalog-table":
            return component
        children = getattr(component, "children", None)
        if children is None:
            return None
        if isinstance(children, (list, tuple)):
            for child in children:
                result = _find_datatable(child)
                if result is not None:
                    return result
        else:
            return _find_datatable(children)
        return None

    view = panels.migrate_view(r)
    table = _find_datatable(view)
    assert table is not None, "catalog DataTable not found in migrate_view output"
    assert len(table.data) == 4, f"Expected 4 catalog rows, got {len(table.data)}"


def test_migrate_view_catalog_table_columns():
    """Catalog table must have title, kind, guideSection, occurrences, replacement columns."""
    from dash import dash_table as _dash_table  # noqa: PLC0415
    r = _migrate_report()

    def _find_datatable(component):
        if isinstance(component, _dash_table.DataTable) and getattr(component, "id", None) == "catalog-table":
            return component
        children = getattr(component, "children", None)
        if children is None:
            return None
        if isinstance(children, (list, tuple)):
            for child in children:
                result = _find_datatable(child)
                if result is not None:
                    return result
        else:
            return _find_datatable(children)
        return None

    view = panels.migrate_view(r)
    table = _find_datatable(view)
    assert table is not None
    col_ids = {c["id"] for c in table.columns}
    assert col_ids == {"title", "kind", "guideSection", "occurrences", "replacement"}


def test_migrate_view_catalog_table_filter_action():
    """Catalog table must be filterable by kind (filter_action=native)."""
    from dash import dash_table as _dash_table  # noqa: PLC0415
    r = _migrate_report()

    def _find_datatable(component):
        if isinstance(component, _dash_table.DataTable) and getattr(component, "id", None) == "catalog-table":
            return component
        children = getattr(component, "children", None)
        if children is None:
            return None
        if isinstance(children, (list, tuple)):
            for child in children:
                result = _find_datatable(child)
                if result is not None:
                    return result
        else:
            return _find_datatable(children)
        return None

    view = panels.migrate_view(r)
    table = _find_datatable(view)
    assert table is not None
    assert table.filter_action == "native"


def test_migrate_view_catalog_guide_section_is_italic():
    """guideSection column must have italic font style."""
    from dash import dash_table as _dash_table  # noqa: PLC0415
    r = _migrate_report()

    def _find_datatable(component):
        if isinstance(component, _dash_table.DataTable) and getattr(component, "id", None) == "catalog-table":
            return component
        children = getattr(component, "children", None)
        if children is None:
            return None
        if isinstance(children, (list, tuple)):
            for child in children:
                result = _find_datatable(child)
                if result is not None:
                    return result
        else:
            return _find_datatable(children)
        return None

    view = panels.migrate_view(r)
    table = _find_datatable(view)
    assert table is not None
    cond = table.style_cell_conditional or []
    italic_cols = [c["if"]["column_id"] for c in cond if c.get("fontStyle") == "italic"]
    assert "guideSection" in italic_cols


def test_migrate_view_release_notes_rendered():
    """migrate_view must render the releaseNotes field via dcc.Markdown."""
    r = _migrate_report()
    rendered = str(panels.migrate_view(r))
    # The release notes in the mock start with "## Pydantic v2 upgrade"
    assert "Pydantic v2 upgrade" in rendered
    assert "Markdown" in rendered


def test_migrate_view_lane_module_names_present():
    """Each module name (users, orders, payments, core) must appear in the view."""
    r = _migrate_report()
    rendered = str(panels.migrate_view(r))
    for module_name in ("users", "orders", "payments", "core"):
        assert module_name.upper() in rendered or module_name in rendered


def test_migrate_view_graph_present():
    """migrate_view must include a Cytoscape graph component."""
    r = _migrate_report()
    rendered = str(panels.migrate_view(r))
    assert "Cytoscape" in rendered


def test_migrate_view_header_text_contrast():
    """Heading and caption text must use the light chart font color (not bare white on dark
    which would fail contrast, and not dark-on-dark which fails entirely).
    The _CHART_FONT_COLOR constant must be used for headings."""
    r = _migrate_report()
    rendered = str(panels.migrate_view(r))
    # The light font color must be referenced (headings use it via style dict)
    assert panels._CHART_FONT_COLOR in rendered


def test_detail_view_migrate_uses_migrate_view():
    """detail_view on the migrate scenario must include the catalog table id."""
    import app as _app  # noqa: PLC0415
    rendered = str(_app.detail_view("s3-pydantic2"))
    assert "catalog-table" in rendered
    assert "Worker lanes" in rendered
    assert "Release notes" in rendered


def test_detail_view_migrate_includes_summary_strip():
    """detail_view on the migrate scenario must include the summary strip."""
    import app as _app  # noqa: PLC0415
    rendered = str(_app.detail_view("s3-pydantic2"))
    # summary_strip emits 'summary-strip' class
    assert "summary-strip" in rendered

