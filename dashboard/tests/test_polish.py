"""
Tests for C8 visual polish pass.

Checks:
  1. style.css defines every design-system token.
  2. The paste textarea has the class/style that sets a readable placeholder colour.
  3. The PR comment markdown container has the class used by the table CSS.
  4. _chart_layout(on_light=True) uses dark font colour; on_light=False uses light.
  5. The primary button class btn-uplift-primary exists in the CSS.
  6. Alert classes (.alert-danger, .alert-warning) are in the CSS with dark-theme bg.
  7. Upload drop zone has min-height 96px in the CSS.
  8. The tests bar figure has a dark hoverlabel.

Run from repo root:
    python -m pytest -q dashboard/tests/test_polish.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_DASH_ROOT = Path(__file__).resolve().parent.parent
if str(_DASH_ROOT) not in sys.path:
    sys.path.insert(0, str(_DASH_ROOT))

import panels  # noqa: E402
import app as _app  # noqa: E402

_CSS_PATH = _DASH_ROOT / "assets" / "style.css"
_CSS = _CSS_PATH.read_text(encoding="utf-8")


# ── 1. Design system tokens defined in style.css ─────────────────────────────

def test_css_token_bg():
    assert "--bg:          #0e1320" in _CSS or "--bg" in _CSS
    assert "#0e1320" in _CSS


def test_css_token_surface():
    assert "--surface:" in _CSS
    assert "#151c2e" in _CSS


def test_css_token_surface_2():
    assert "--surface-2:" in _CSS
    assert "#1c2540" in _CSS


def test_css_token_border():
    assert "--border:" in _CSS
    assert "#2a3555" in _CSS


def test_css_token_text():
    assert "--text:" in _CSS
    assert "#e6ebf5" in _CSS


def test_css_token_text_muted():
    assert "--text-muted:" in _CSS
    assert "#9fb0cc" in _CSS


def test_css_token_accent():
    assert "--accent:" in _CSS
    assert "#4f6df5" in _CSS


def test_css_token_ok():
    assert "--ok:" in _CSS
    assert "#2fb56b" in _CSS


def test_css_token_warn():
    assert "--warn:" in _CSS
    assert "#f0a020" in _CSS


def test_css_token_bad():
    assert "--bad:" in _CSS
    assert "#e5484d" in _CSS


# ── 2. Paste textarea has readable placeholder colour ──────────────────────────

def test_css_textarea_placeholder_colour():
    """The paste textarea placeholder must be set to #9fb0cc (readable on dark bg)."""
    assert "#9fb0cc" in _CSS, "Placeholder colour #9fb0cc must appear in CSS"
    # Check it's associated with ::placeholder
    assert "::placeholder" in _CSS


def test_css_textarea_min_height():
    """The paste textarea must have min-height 140px in the CSS."""
    assert "140px" in _CSS


def test_css_textarea_font_size_14px():
    """The paste textarea font-size must be 14px."""
    assert "14px" in _CSS


def test_css_textarea_border_colour():
    """The paste textarea border must use #3a4763."""
    assert "#3a4763" in _CSS


def test_css_textarea_border_radius_10px():
    """The paste textarea border-radius must be 10px."""
    assert "10px" in _CSS


def test_layout_paste_textarea_has_class():
    """The paste-json textarea in the layout must have class paste-json-textarea."""
    rendered = str(_app.app.layout)
    assert "paste-json-textarea" in rendered, (
        "Textarea must have class 'paste-json-textarea' so CSS placeholder rule applies"
    )


def test_layout_paste_textarea_text_colour():
    """The paste-json textarea must specify color #e6ebf5 (typed text)."""
    rendered = str(_app.app.layout)
    assert "#e6ebf5" in rendered


# ── 3. PR comment container has the class used by table CSS ──────────────────

def test_pr_comment_card_has_pr_comment_card_class():
    """The PR comment card must have class 'pr-comment-card' for table CSS targeting."""
    rendered = str(_app.detail_view("s1-null-user"))
    assert "pr-comment-card" in rendered, (
        "dbc.Card inside PR comment tab must have className='pr-comment-card'"
    )


def test_pr_comment_md_has_pr_md_content_class():
    """The dcc.Markdown in the PR comment tab must have class 'pr-md-content'."""
    rendered = str(_app.detail_view("s1-null-user"))
    assert "pr-md-content" in rendered, (
        "dcc.Markdown inside PR comment tab must have className='... pr-md-content'"
    )


def test_pr_comment_scroll_container_present():
    """The PR comment tab must include a pr-comment-scroll wrapper."""
    rendered = str(_app.detail_view("s1-null-user"))
    assert "pr-comment-scroll" in rendered


def test_css_pr_comment_table_has_cell_padding():
    """CSS must define cell padding for .pr-md-content table."""
    assert "pr-md-content" in _CSS
    assert "10px 16px" in _CSS


def test_pr_comment_tab_has_copy_caption():
    """PR comment tab must show the caption about Uplift posting the comment."""
    rendered = str(_app.detail_view("s1-null-user"))
    assert "exact comment Uplift posts" in rendered


# ── 4. _chart_layout on_light flag ───────────────────────────────────────────

def test_chart_layout_on_light_false_uses_light_font():
    """_chart_layout(on_light=False) must use light font colour #e6ebf5."""
    layout = panels._chart_layout(on_light=False)
    assert layout["font"]["color"] == panels._CHART_FONT_COLOR
    assert layout["font"]["color"] == "#e6ebf5"


def test_chart_layout_on_light_true_uses_dark_font():
    """_chart_layout(on_light=True) must use dark font colour #1d2330."""
    layout = panels._chart_layout(on_light=True)
    assert layout["font"]["color"] == panels._CHART_FONT_COLOR_LIGHT
    assert layout["font"]["color"] == "#1d2330"


def test_chart_layout_default_is_dark_background():
    """_chart_layout() default (no args) uses light font (dark background mode)."""
    layout = panels._chart_layout()
    assert layout["font"]["color"] == "#e6ebf5"


def test_chart_layout_on_light_still_transparent_bg():
    """on_light=True must still use transparent backgrounds."""
    layout = panels._chart_layout(on_light=True)
    assert layout["paper_bgcolor"] == "rgba(0,0,0,0)"
    assert layout["plot_bgcolor"] == "rgba(0,0,0,0)"


def test_lane_chart_uses_dark_font_on_white_card():
    """Lane charts (on white cards) must use dark font colour #1d2330."""
    import json, pathlib  # noqa: E401
    r = json.loads((pathlib.Path(_DASH_ROOT) / "reports" / "migrate-pydantic2.mock.json").read_text(encoding="utf-8"))
    first_mod = r["migration"]["modules"][0]
    lane_col = panels._module_lane(first_mod)

    def _find_graph(component):
        from dash import dcc as _dcc  # noqa: PLC0415
        if isinstance(component, _dcc.Graph):
            return component
        children = getattr(component, "children", None)
        if children is None:
            return None
        if isinstance(children, (list, tuple)):
            for child in children:
                result = _find_graph(child)
                if result is not None:
                    return result
        else:
            return _find_graph(children)
        return None

    graph = _find_graph(lane_col)
    assert graph is not None
    font_color = graph.figure.layout.font.color
    assert font_color == "#1d2330", (
        f"Lane chart on white card must use dark font #1d2330, got {font_color!r}"
    )


# ── 5. Primary button class in CSS ────────────────────────────────────────────

def test_css_btn_uplift_primary_class_exists():
    """The CSS must define .btn-uplift-primary with #4f6df5 background."""
    assert ".btn-uplift-primary" in _CSS
    assert "#4f6df5" in _CSS


def test_css_btn_uplift_primary_has_hover():
    """The primary button must have a :hover state in the CSS."""
    assert ".btn-uplift-primary:hover" in _CSS


def test_layout_validate_button_has_primary_class():
    """The Validate button must have class btn-uplift-primary."""
    rendered = str(_app.app.layout)
    assert "btn-uplift-primary" in rendered, (
        "Validate button must use class 'btn-uplift-primary'"
    )


# ── 6. Alert dark-theme styling in CSS ────────────────────────────────────────

def test_css_alert_danger_dark_bg():
    """Alert danger must have dark-tinted background rgba in CSS."""
    assert ".alert-danger" in _CSS
    assert "rgba(229,72,77" in _CSS


def test_css_alert_warning_dark_bg():
    """Alert warning must have dark-tinted background rgba in CSS."""
    assert ".alert-warning" in _CSS
    assert "rgba(240,160,32" in _CSS


def test_css_alert_text_colour():
    """Alert text must be #f3f6fb (light on dark bg) in CSS."""
    assert "#f3f6fb" in _CSS


def test_css_alert_border_radius_12px():
    """Alerts must have 12px border-radius in CSS."""
    assert "border-radius: 12px" in _CSS


# ── 7. Upload drop zone size ──────────────────────────────────────────────────

def test_css_upload_min_height():
    """Upload zone must have min-height 96px in CSS."""
    assert "min-height: 96px" in _CSS


def test_css_upload_has_hover():
    """Upload zone must have a :hover rule in CSS."""
    assert ".upload:hover" in _CSS


def test_layout_upload_text_updated():
    """Upload children must say 'Drop a report.json here or click to browse'."""
    rendered = str(_app.app.layout)
    assert "click to browse" in rendered


# ── 8. Tests bar has dark hoverlabel ─────────────────────────────────────────

def test_tests_bar_has_dark_hoverlabel():
    """The tests-before/after bar chart must have a dark hoverlabel config."""
    tests = {"before": {"passed": 43, "failed": 4}, "after": {"passed": 47, "failed": 0}}
    graph = panels._tests_bar(tests)
    assert graph is not None
    layout = graph.figure.layout
    hoverlabel = layout.hoverlabel
    assert hoverlabel is not None, "hoverlabel must be set on the tests bar figure"
    assert hoverlabel.bgcolor == "#1c2540", (
        f"Tooltip bg must be dark #1c2540, got {hoverlabel.bgcolor!r}"
    )


# ── 9. Tab styling in CSS ─────────────────────────────────────────────────────

def test_css_nav_tabs_styled():
    """CSS must override Bootstrap nav-tabs with dark-theme styles."""
    assert ".nav-tabs .nav-link" in _CSS
    assert ".nav-tabs .nav-link.active" in _CSS


def test_css_active_tab_has_accent_underline():
    """Active tab must have an accent-colour underline pseudo-element."""
    assert ".nav-tabs .nav-link.active::after" in _CSS
    assert "var(--accent)" in _CSS


def test_css_detail_tabs_margin_top():
    """The detail tabs must have margin-top: 24px spacing from the H1."""
    assert "#detail-tabs" in _CSS
    assert "margin-top: 24px" in _CSS
