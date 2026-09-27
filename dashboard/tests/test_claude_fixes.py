"""
Regression tests for the bug-fix pass (post C1-C8, pre bolder/polish).

Covers, per the Impeccable critique dated 2026-09-27 (dashboard/.impeccable/critique/):
  P0 - infraImpact (Docker node) and conventions (compliance badge) never rendered
  P0 - dropped/pasted report crashes on first interaction (filter/tap/row-click)
  P1 - landing "0 REGRESSIONS" hard-coded red even at zero
  P1 - star "changed symbol" node returns no detail
  P2 - table-row hover overrides verdict-colour background (see test_c8.py's updated test)
  P2 - colour-token fragmentation (Bootstrap badge vs custom tokens) + legend/node mismatch
  P3 - raw snake_case verdict text inconsistent with humanized chips/legend

Run from the dashboard/ directory (or repo root with PYTHONPATH set):
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_DASH_ROOT = Path(__file__).resolve().parent.parent
if str(_DASH_ROOT) not in sys.path:
    sys.path.insert(0, str(_DASH_ROOT))

import graph  # noqa: E402
import panels  # noqa: E402

_REPORTS = _DASH_ROOT / "reports"
_APP_SRC = (_DASH_ROOT / "app.py").read_text(encoding="utf-8")


def _report(name: str) -> dict:
    return json.loads((_REPORTS / name).read_text(encoding="utf-8"))


def _s1() -> dict:
    return _report("impact-s1.mock.json")


def _migrate() -> dict:
    return _report("migrate-pydantic2.mock.json")


# ── Bootstrap .text-muted vs dark-theme contrast (found via live screenshot) ─
#
# Bootstrap's `.text-muted` utility is `color: var(--bs-secondary-color)
# !important`, which resolves to a dark charcoal grey meant for a white
# background. Paired with any dark card in this app, its !important beats our
# own (plain) --text-muted colour and renders as near-invisible dark-on-dark
# text — this is exactly what made the scenario-card description and the
# detail panel's "reason" text unreadable. `.text-dim` is the safe
# replacement (same intent, `!important` so it always wins).

def test_no_python_source_uses_bootstrap_text_muted_class():
    """Nothing in app.py/panels.py may pair with Bootstrap's `.text-muted` —
    it silently overrides our dark-theme muted colour. Use `.text-dim`."""
    for path in ("app.py", "panels.py"):
        src = (_DASH_ROOT / path).read_text(encoding="utf-8")
        assert not re.search(r'className="[^"]*\btext-muted\b[^"]*"', src), (
            f"{path} pairs a className with Bootstrap's text-muted utility, which is "
            "!important and overrides our dark-theme --text-muted colour — use text-dim"
        )


def test_css_text_dim_class_forces_muted_colour():
    css = (_DASH_ROOT / "assets" / "style.css").read_text(encoding="utf-8")
    assert re.search(r"\.text-dim\s*\{[^}]*color:\s*var\(--text-muted\)\s*!important", css)


def test_scenario_card_description_uses_text_dim_not_bootstrap_muted():
    import app as _app  # noqa: PLC0415
    rendered = str(_app.scenario_cards())
    assert "text-dim" in rendered
    assert "text-muted" not in rendered


def test_detail_panel_reason_uses_text_dim_not_bootstrap_muted():
    r = _s1()
    rendered = str(panels.detail_panel(r["affected"][0]))
    assert "text-dim" in rendered
    assert "text-muted" not in rendered


# ── P0: uploaded-report resolver ────────────────────────────────────────────

def test_resolve_report_returns_uploaded_data_for_uploaded_sid():
    import app  # noqa: PLC0415
    data = {"scenarioId": "uploaded"}
    assert app._resolve_report("uploaded", data) is data


def test_resolve_report_returns_none_for_uploaded_sid_with_no_data():
    import app  # noqa: PLC0415
    assert app._resolve_report("uploaded", None) is None


def test_resolve_report_falls_back_to_reports_dict_for_builtin_sid():
    import app  # noqa: PLC0415
    assert app._resolve_report("s1-null-user", None) is app.REPORTS["s1-null-user"]


def test_uploaded_is_never_a_key_in_reports():
    """REPORTS must never contain "uploaded" as a key — it lives in the
    uploaded-report Store and is only reachable through _resolve_report()."""
    import app  # noqa: PLC0415
    assert "uploaded" not in app.REPORTS


def test_callbacks_use_resolve_report_not_bare_reports_lookup():
    """Every interaction callback must resolve the report through
    _resolve_report so it also works for an uploaded/pasted report, not just
    REPORTS[sid] / sid in REPORTS / sid not in REPORTS, which silently break
    for sid == "uploaded" (REPORTS never has that key)."""
    for func_name in ("show_detail", "update_graph", "table_row_selects_node", "filter_catalog"):
        m = re.search(rf"def {func_name}\(.*?\n(?:.*\n)*?(?=\n@app\.callback|\nif __name__)", _APP_SRC)
        assert m, f"could not locate function body for {func_name}"
        body = m.group()
        assert "_resolve_report(" in body, f"{func_name} must call _resolve_report(...)"
        assert "REPORTS[sid]" not in body, f"{func_name} must not index REPORTS[sid] directly"
        assert "REPORTS.get(sid)" not in body, f"{func_name} must not call REPORTS.get(sid) directly"
        assert re.search(r"\bsid (not )?in REPORTS\b", body) is None, (
            f"{func_name} must not gate on `sid in REPORTS` — that is always False for 'uploaded'"
        )


# ── P0: infra (Docker) node rendering ───────────────────────────────────────

def test_build_elements_includes_infra_node_and_edge():
    r = _s1()
    assert r.get("infraImpact"), "fixture must have infraImpact for this test to mean anything"
    els = graph.build_elements(r)
    infra_nodes = [e for e in els if e["data"].get("kind") == "infra"]
    assert len(infra_nodes) == 1
    infra_id = infra_nodes[0]["data"]["id"]
    assert infra_id == "infra:sample-app/Dockerfile"
    assert "infra" in infra_nodes[0]["classes"]
    edges_to_infra = [e for e in els if "source" in e["data"] and e["data"]["target"] == infra_id]
    assert len(edges_to_infra) == 1
    assert edges_to_infra[0]["data"]["source"] == r["changedSymbols"][0]["id"]


def test_build_stylesheet_has_distinct_infra_style():
    sheet = graph.build_stylesheet()
    infra_rule = next((s for s in sheet if s["selector"] == ".infra"), None)
    assert infra_rule is not None
    assert infra_rule["style"]["shape"] == "round-rectangle"
    # Must not collide with a verdict colour or the contract's own colour.
    assert infra_rule["style"]["background-color"] not in graph.VERDICT_COLORS.values()


def test_find_infra_impact_returns_matching_entry():
    r = _s1()
    entry = graph.find_infra_impact(r, "infra:sample-app/Dockerfile")
    assert entry is not None
    assert entry["file"] == "sample-app/Dockerfile"
    assert graph.find_infra_impact(r, "infra:nope") is None
    assert graph.find_infra_impact(r, "shop/users/service.py#get_user") is None


def test_infra_panel_renders_key_fields_without_fabricating_time():
    r = _s1()
    entry = r["infraImpact"][0]
    rendered = str(panels.infra_panel(entry))
    assert "Dockerfile" in rendered
    assert "Layer 4 of 7" in rendered
    assert "4-7" in rendered
    assert "Split the COPY" in rendered
    # measuredRebuildSeconds is absent in the fixture — must not appear/be invented
    assert "Measured rebuild time" not in rendered


def test_infra_panel_shows_measured_time_only_when_present():
    entry = {"file": "x/Dockerfile", "trigger": "t", "measuredRebuildSeconds": 42.5}
    rendered = str(panels.infra_panel(entry))
    assert "42.5" in rendered
    assert "Measured rebuild time" in rendered


# ── P0: conventions (compliance badge) rendering ────────────────────────────

def test_conventions_card_none_when_absent():
    assert panels.conventions_card(None) is None
    assert panels.conventions_card({}) is None


def test_conventions_card_renders_fields_and_compliance():
    r = _migrate()
    conv = r["conventions"]
    rendered = str(panels.conventions_card(conv))
    assert conv["naming"] in rendered
    assert conv["imports"] in rendered
    assert "22 lines checked" in rendered
    assert "1 violation" in rendered
    assert "retried after violation" in rendered
    for f in conv["evidenceFiles"]:
        assert f in rendered


def test_migrate_view_includes_conventions_card():
    r = _migrate()
    rendered = str(panels.migrate_view(r))
    assert "Repo conventions" in rendered
    assert r["conventions"]["naming"] in rendered


def test_detail_view_impact_includes_conventions_card_when_present():
    """conventions is a general top-level schema field, not migrate-only — the
    impact detail view must also render it when a report happens to carry it."""
    import app as _app  # noqa: PLC0415
    r = dict(_s1())
    r["conventions"] = {"naming": "snake_case everywhere", "compliance": {"checkedLines": 5, "violations": 0}}
    _app.REPORTS["__tmp_conv_test__"] = r
    try:
        rendered = str(_app.detail_view("__tmp_conv_test__"))
        assert "Repo conventions" in rendered
        assert "snake_case everywhere" in rendered
    finally:
        del _app.REPORTS["__tmp_conv_test__"]


# ── P1: star "changed symbol" node detail ───────────────────────────────────

def test_find_changed_symbol_returns_matching_entry():
    r = _s1()
    sym = graph.find_changed_symbol(r, "shop/users/service.py#get_user")
    assert sym is not None
    assert sym["kind"] == "function"
    assert graph.find_changed_symbol(r, "nope") is None


def test_changed_symbol_panel_renders_kind_changetype_hints_and_summary():
    r = _s1()
    sym = r["changedSymbols"][0]
    rendered = str(panels.changed_symbol_panel(sym, r["change"]))
    assert sym["id"] in rendered
    assert sym["kind"] in rendered
    assert sym["changeType"] in rendered
    for hint in sym["hints"]:
        assert hint in rendered
    assert r["change"]["summary"] in rendered


def test_changed_symbol_panel_handles_missing_hints_and_change():
    sym = {"id": "a.py#b", "kind": "function", "changeType": "signature"}
    rendered = str(panels.changed_symbol_panel(sym, None))
    assert "a.py#b" in rendered  # no crash with no hints/change


# ── P1: landing-page regressions colour ─────────────────────────────────────

def test_scenario_cards_regressions_not_alarm_red_when_zero():
    import app as _app  # noqa: PLC0415
    rendered = str(_app.scenario_cards())
    # Both live scenarios report regressions: 0 — the red class must not be applied.
    for r in _app.REPORTS.values():
        assert r["metrics"].get("regressions", 0) == 0
    assert "fig-regressions" not in rendered


def test_scenario_cards_regressions_alarm_red_when_nonzero():
    import app as _app  # noqa: PLC0415
    saved = _app.REPORTS["s1-null-user"]["metrics"].get("regressions")
    _app.REPORTS["s1-null-user"]["metrics"]["regressions"] = 2
    try:
        rendered = str(_app.scenario_cards())
        assert "fig-regressions" in rendered
    finally:
        _app.REPORTS["s1-null-user"]["metrics"]["regressions"] = saved


# ── Polish pass: badge colour consistency (verdict/risk badges only) ───────

def test_no_verdict_badges_use_bootstrap_semantic_color_prop():
    """Every verdict/risk-related dbc.Badge in panels.py must use VERDICT_HEX
    (or an equivalent literal hex matching it) via `style=`, not Bootstrap's
    color="danger"/"warning"/"success"/"secondary"/"info"/"primary" tokens,
    which render a visibly different red/orange/green than the rest of the
    app (the graph, the risk gauge, the filter chips)."""
    src = (_DASH_ROOT / "panels.py").read_text(encoding="utf-8")
    for token in ('color="danger"', 'color="warning"', 'color="success"',
                  'color="secondary"', 'color="info"', 'color="primary"'):
        assert token not in src, f"found Bootstrap semantic colour {token} on a badge in panels.py"


def test_detail_panel_badge_uses_badge_style_hex():
    r = _s1()
    item = r["affected"][0]  # verdict: will_break
    rendered = str(panels.detail_panel(item))
    assert panels.BADGE_STYLE["will_break"]["backgroundColor"] in rendered


def test_changed_symbol_and_infra_badges_use_badge_style():
    r = _s1()
    sym = r["changedSymbols"][0]
    changed_rendered = str(panels.changed_symbol_panel(sym, r["change"]))
    assert panels.BADGE_STYLE["changed"]["backgroundColor"] in changed_rendered

    infra_rendered = str(panels.infra_panel(r["infraImpact"][0]))
    assert panels.BADGE_STYLE["infra"]["backgroundColor"] in infra_rendered


def test_accuracy_card_tp_fp_fn_use_badge_style():
    accuracy = {"precision": 0.8, "recall": 1.0, "truePositives": 4, "falsePositives": 1, "falseNegatives": 0}
    rendered = str(panels._accuracy_card(accuracy))
    assert panels.BADGE_STYLE["safe"]["backgroundColor"] in rendered         # TP
    assert panels.BADGE_STYLE["might_break"]["backgroundColor"] in rendered  # FP
    assert panels.BADGE_STYLE["will_break"]["backgroundColor"] in rendered   # FN


def test_conventions_card_compliance_badges_use_badge_style():
    conv = {"compliance": {"checkedLines": 10, "violations": 0, "retried": True}}
    rendered = str(panels.conventions_card(conv))
    assert panels.BADGE_STYLE["safe"]["backgroundColor"] in rendered    # 0 violations -> ok green
    assert panels.BADGE_STYLE["accent"]["backgroundColor"] in rendered  # retried badge -> accent


def test_all_badge_style_entries_clear_4_5_contrast():
    """Every BADGE_STYLE entry must have a text/background pair that clears
    WCAG AA for normal-size text (4.5:1) — small badge text does not qualify
    for the 3:1 large-text exemption."""
    def _luminance(hexv: str) -> float:
        hexv = hexv.lstrip("#")
        r, g, b = (int(hexv[i:i + 2], 16) / 255 for i in (0, 2, 4))
        def f(c): return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        r, g, b = f(r), f(g), f(b)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    def _ratio(h1: str, h2: str) -> float:
        l1, l2 = _luminance(h1), _luminance(h2)
        l1, l2 = max(l1, l2), min(l1, l2)
        return (l1 + 0.05) / (l2 + 0.05)

    for name, style in panels.BADGE_STYLE.items():
        ratio = _ratio(style["color"], style["backgroundColor"])
        assert ratio >= 4.5, f"BADGE_STYLE[{name!r}] contrast is {ratio:.2f}:1, must be >= 4.5:1"


# ── P2: colour-token fragmentation / legend accuracy ────────────────────────

def test_scenario_cards_risk_badge_uses_custom_hex_not_bootstrap_token():
    import app as _app  # noqa: PLC0415
    rendered = str(_app.scenario_cards())
    # Must use the same hex as the risk gauge / graph verdict palette, not a
    # bare Bootstrap semantic colour name.
    assert any(hexv in rendered for hexv in _app.RISK_COLOUR_HEX.values())


def test_legend_untested_colour_matches_actual_node_style():
    import app as _app  # noqa: PLC0415
    untested_entry = next(item for item in _app.LEGEND_ITEMS if "Untested" in item[2])
    sheet = graph.build_stylesheet()
    untested_rule = next(s for s in sheet if s["selector"] == ".untested")
    assert untested_entry[1] == untested_rule["style"]["border-color"], (
        "legend swatch colour for 'Untested' must match the actual node border colour"
    )


def test_legend_has_infra_entry():
    import app as _app  # noqa: PLC0415
    assert any("Docker" in item[2] for item in _app.LEGEND_ITEMS)


# ── P2: contract hide + dangling-edge fix ───────────────────────────────────

def test_hidden_contract_verdict_is_not_rendered():
    r = _s1()
    contract_verdict = r["contracts"][0]["verdict"]
    els = graph.build_elements(r, hide={contract_verdict})
    contract_nodes = [e for e in els if e["data"].get("kind") == "contract"]
    assert contract_nodes == [], "a contract whose own verdict is hidden must not render"


def test_no_dangling_edge_to_a_hidden_handler():
    r = _s1()
    # Hide every affected verdict so no handler node is rendered at all.
    els = graph.build_elements(r, hide={"will_break", "might_break", "safe", "unknown"})
    node_ids = {e["data"]["id"] for e in els if "source" not in e["data"]}
    edges = [e for e in els if "source" in e["data"]]
    for edge in edges:
        assert edge["data"]["source"] in node_ids, "edge source must be a node that is actually rendered"
        assert edge["data"]["target"] in node_ids, "edge target must be a node that is actually rendered"


# ── "untested only" filter (previously a silent no-op) ──────────────────────

def test_untested_only_keeps_only_items_without_tests():
    r = _s1()
    els = graph.build_elements(r, untested_only=True)
    affected_nodes = [e for e in els if e["data"].get("kind") == "affected"]
    assert affected_nodes, "fixture must have at least one untested affected item"
    for n in affected_nodes:
        item = graph.find_item(r, n["data"]["id"])
        assert not item.get("tests"), f"{n['data']['id']} has tests and must be hidden by untested_only"


def test_untested_only_false_keeps_everything_hide_alone_would():
    r = _s1()
    without = graph.build_elements(r)
    with_flag_off = graph.build_elements(r, untested_only=False)
    assert len(without) == len(with_flag_off)


def test_accessible_node_list_respects_untested_only():
    import app as _app  # noqa: PLC0415
    r = _s1()
    full = str(_app.accessible_node_list(r))
    only_untested = str(_app.accessible_node_list(r, untested_only=True))
    assert len(only_untested) < len(full)
    assert "user_spend_report" in only_untested  # the known untested item stays


# ── P3: humanized verdict text (source-level, complements test_panels.py) ──

def test_verdict_label_map_covers_all_verdicts():
    for v in ("will_break", "might_break", "safe", "unknown"):
        assert "_" not in panels.VERDICT_LABEL[v] or panels.VERDICT_LABEL[v] == v == "unknown"


# ── Full-page sanity: an uploaded report survives every interaction path ───

def test_uploaded_report_end_to_end_via_resolver():
    """Simulates what the callbacks now do for an uploaded report: resolve,
    then run the same pure logic a real interaction would trigger. This is
    the direct regression test for the P0 upload-crash bug (Dash callback
    context can't be constructed outside a running app, so this exercises
    the exact same code path each callback delegates to)."""
    import app as _app  # noqa: PLC0415

    uploaded = _s1()
    r = _app._resolve_report("uploaded", uploaded)
    assert r is uploaded

    # Filter-chip toggle path (used to return [] / wipe the graph to nothing)
    hide = graph.filter_hide(["will_break"])
    elements = graph.build_elements(r, hide=hide)
    assert elements, "filtering an uploaded report must not wipe the graph"

    # Graph-node-tap path (used to KeyError on r["affected"] against {})
    node_id = r["affected"][0]["id"]
    item = graph.find_item(r, node_id)
    assert item is not None
    panels.detail_panel(item)  # must not raise

    # Table-row-click path (used to IndexError on r["affected"][row_index])
    affected = r.get("affected", [])
    assert affected[0] is not None
    panels.detail_panel(affected[0])  # must not raise
