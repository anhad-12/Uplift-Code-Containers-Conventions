"""
Tests for C7 features:
  - comment.py pr_comment output
  - panels.bob_panel (9 modes fallback)
  - detail_view tabs (PR comment tab, Bob tab)
  - on_upload extended behaviour (store + redirect, 5 schema errors)
  - paste JSON textarea present in layout

Run from repo root:
    python -m pytest -q dashboard/tests/test_c7.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_DASH_ROOT = Path(__file__).resolve().parent.parent
if str(_DASH_ROOT) not in sys.path:
    sys.path.insert(0, str(_DASH_ROOT))

import comment as _comment  # noqa: E402
import panels               # noqa: E402
import app as _app          # noqa: E402

_REPORTS = _DASH_ROOT / "reports"


def _s1() -> dict:
    return json.loads((_REPORTS / "impact-s1.mock.json").read_text(encoding="utf-8"))


# ── 1. comment.pr_comment ────────────────────────────────────────────────────

def test_pr_comment_contains_risk_score():
    """pr_comment on S1 must contain 'Risk 71/100 (high)'."""
    r = _s1()
    text = _comment.pr_comment(r)
    assert "Risk 71/100 (high)" in text


def test_pr_comment_contains_scenario_title():
    r = _s1()
    text = _comment.pr_comment(r)
    assert "get_user returns None instead of raising" in text


def test_pr_comment_contains_table_header():
    r = _s1()
    text = _comment.pr_comment(r)
    assert "| Item | Verdict | Proof | Reason |" in text


def test_pr_comment_will_break_items_before_safe():
    """will_break items must appear before safe items in the sorted table."""
    r = _s1()
    text = _comment.pr_comment(r)
    will_idx = text.index("will_break")
    safe_idx  = text.index("safe")
    assert will_idx < safe_idx


def test_pr_comment_contains_api_contracts():
    r = _s1()
    text = _comment.pr_comment(r)
    assert "API contracts" in text
    assert "GET /users/{user_id}" in text


def test_pr_comment_contains_untested():
    r = _s1()
    text = _comment.pr_comment(r)
    assert "Untested affected code" in text
    assert "user_spend_report" in text


def test_pr_comment_contains_tests_to_run():
    r = _s1()
    text = _comment.pr_comment(r)
    assert "Tests to run" in text


def test_pr_comment_contains_metrics_line():
    r = _s1()
    text = _comment.pr_comment(r)
    assert "predicted 5" in text
    assert "confirmed 4" in text
    assert "fixed 4" in text
    assert "regressions 0" in text


# ── 2. panels.bob_panel ────────────────────────────────────────────────────────

def test_bob_panel_returns_card():
    import dash_bootstrap_components as _dbc  # noqa: PLC0415
    r = _s1()
    card = panels.bob_panel(r)
    assert isinstance(card, _dbc.Card)


def test_bob_panel_nine_modes_when_bob_modes_empty():
    """When provenance.bobModes is empty, bob_panel must list all 9 static modes."""
    r = _s1()
    # S1 has bobModes: [] — should fall back to 9 static modes
    rendered = str(panels.bob_panel(r))
    for mode in panels._STATIC_BOB_MODES:
        assert mode in rendered, f"Mode {mode!r} missing from bob_panel output"
    assert len(panels._STATIC_BOB_MODES) == 9


def test_bob_panel_nine_modes_when_bob_modes_absent():
    """When provenance key is absent entirely, bob_panel must still list 9 modes."""
    r = dict(_s1())
    r.pop("provenance", None)
    rendered = str(panels.bob_panel(r))
    assert len(panels._STATIC_BOB_MODES) == 9
    for mode in panels._STATIC_BOB_MODES:
        assert mode in rendered


def test_bob_panel_uses_provided_modes():
    """When provenance.bobModes is non-empty, only those modes are listed."""
    r = dict(_s1())
    r["provenance"] = {"generatedBy": "bob", "bobModes": ["uplift-verifier"]}
    rendered = str(panels.bob_panel(r))
    assert "uplift-verifier" in rendered
    # Other modes should NOT appear (only the provided one)
    assert "uplift-prover" not in rendered


def test_bob_panel_mode_summaries_present():
    """Each mode in the fallback list must have a summary in _BOB_MODE_SUMMARIES."""
    for mode in panels._STATIC_BOB_MODES:
        assert mode in panels._BOB_MODE_SUMMARIES, f"No summary for {mode!r}"


def test_bob_panel_contains_four_features_sentence():
    r = _s1()
    rendered = str(panels.bob_panel(r))
    # The sentence must mention all four features
    assert "Agent mode" in rendered
    assert "parallel tasks" in rendered
    assert "subagents" in rendered
    assert "document understanding" in rendered


def test_bob_panel_text_contrast_white_background():
    """bob_panel text must use dark colour (#1d2330) on white card background."""
    r = _s1()
    rendered = str(panels.bob_panel(r))
    assert "#1d2330" in rendered  # dark text on white card


# ── 3. detail_view tabs ────────────────────────────────────────────────────────

def test_detail_view_has_pr_comment_tab():
    """detail_view on S1 must include a PR comment tab."""
    rendered = str(_app.detail_view("s1-null-user"))
    assert "PR comment" in rendered


def test_detail_view_has_bob_tab():
    """detail_view on S1 must include a 'Powered by IBM Bob' tab."""
    rendered = str(_app.detail_view("s1-null-user"))
    assert "Powered by IBM Bob" in rendered


def test_detail_view_pr_comment_contains_risk():
    """The PR comment content must be in the detail view."""
    rendered = str(_app.detail_view("s1-null-user"))
    assert "Risk 71/100" in rendered


def test_detail_view_has_clipboard():
    """detail_view must include a dcc.Clipboard component."""
    rendered = str(_app.detail_view("s1-null-user"))
    assert "Clipboard" in rendered


def test_detail_view_migrate_has_pr_tab():
    """detail_view on the migrate scenario must also have the PR comment tab."""
    rendered = str(_app.detail_view("s3-pydantic2"))
    assert "PR comment" in rendered
    assert "Powered by IBM Bob" in rendered


# ── 4. Layout: paste JSON area ────────────────────────────────────────────────

def test_layout_contains_paste_textarea():
    """App layout must include the paste-json textarea."""
    rendered = str(_app.app.layout)
    assert "paste-json" in rendered


def test_layout_contains_validate_button():
    """App layout must include the paste-validate-btn button."""
    rendered = str(_app.app.layout)
    assert "paste-validate-btn" in rendered


def test_layout_contains_uploaded_store():
    """App layout must contain the uploaded-report dcc.Store."""
    rendered = str(_app.app.layout)
    assert "uploaded-report" in rendered


# ── 5. on_upload / _process_report_dict ──────────────────────────────────────

def test_process_valid_report_returns_store_and_redirect():
    """A valid report dict must return the report as store data and a redirect href."""
    r = _s1()
    store, _msg, href = _app._process_report_dict(r)
    assert store is not None
    assert href == "/?scenario=uploaded"


def test_process_invalid_report_returns_up_to_five_errors():
    """An invalid report must return None store and an error message with <= 5 items."""
    bad = {"schemaVersion": 1}  # missing required fields
    store, msg, href = _app._process_report_dict(bad)
    assert store is None
    assert href == _app.dash.no_update
    rendered = str(msg)
    assert "schema errors" in rendered.lower() or "error" in rendered.lower()


def test_process_invalid_report_shows_no_more_than_five_errors():
    """Error list must be capped at 5 items."""
    bad = {"schemaVersion": 1}
    _store, msg, _href = _app._process_report_dict(bad)
    rendered = str(msg)
    # Count Li items: the rendered string contains 'Li(' for each list item
    # A simpler check: the number of <li> elements won't exceed 5
    # We verify by counting list items in the component tree
    from dash import html as _html  # noqa: PLC0415

    def _count_li(component, count=0):
        if isinstance(component, _html.Li):
            count += 1
        children = getattr(component, "children", None)
        if children is None:
            return count
        if isinstance(children, (list, tuple)):
            for child in children:
                count = _count_li(child, count)
        else:
            count = _count_li(children, count)
        return count

    li_count = _count_li(msg)
    assert li_count <= 5, f"Expected at most 5 error items, got {li_count}"


# ── 6. route() with uploaded scenario ─────────────────────────────────────────

def test_route_uploaded_with_store_renders_detail():
    """route('?scenario=uploaded', report_data) must render the scenario title."""
    r = _s1()
    # Simulate store holding the uploaded report
    rendered = str(_app.route("?scenario=uploaded", r))
    assert "get_user returns None" in rendered


def test_route_uploaded_without_store_falls_back_to_home():
    """route('?scenario=uploaded', None) must fall back to home."""
    rendered = str(_app.route("?scenario=uploaded", None))
    assert "Know what a change will " in rendered and "Fix it." in rendered
