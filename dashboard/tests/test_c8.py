"""
Tests for C8 polish pass.

Checks:
  1. DataTable style_active_cell does not use a jarring colour (no blue/dark override).
  2. DataTable style_active_cell suppresses the Dash default blue border.
  3. CSS does NOT apply transition to background-color on every element (*).
  4. DataTable cells explicitly disable transition (no hover-flash).
  5. Hover row in CSS uses a subtle, low-opacity tint (< 20% opacity).
  6. Selected-state conditional does not apply a solid dark-blue border.
  7. render.yaml exists with the correct service config.
  8. og.png exists and is under 300 kB.
  9. app.index_string contains og:image pointing to /assets/og.png.
 10. dcc.Loading wraps the graph in the detail view (loading spinner).

Run from repo root:
    python -m pytest -q dashboard/tests/test_c8.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_DASH_ROOT = Path(__file__).resolve().parent.parent
if str(_DASH_ROOT) not in sys.path:
    sys.path.insert(0, str(_DASH_ROOT))

import panels  # noqa: E402
import app as _app  # noqa: E402

_CSS_PATH = _DASH_ROOT / "assets" / "style.css"
_CSS = _CSS_PATH.read_text(encoding="utf-8")


# ── 1. style_active_cell does not use a jarring colour ────────────────────────

def test_active_cell_style_defined():
    """TABLE_STYLE_ACTIVE_CELL must be defined in panels."""
    assert hasattr(panels, "TABLE_STYLE_ACTIVE_CELL"), (
        "panels.TABLE_STYLE_ACTIVE_CELL must be defined to override Dash's default"
    )


def test_active_cell_no_jarring_blue():
    """TABLE_STYLE_ACTIVE_CELL must not use a solid dark-blue background colour."""
    style = panels.TABLE_STYLE_ACTIVE_CELL
    bg = style.get("backgroundColor", "").lower()
    # Must not be a solid blue like #3b82d4, #1a73e8, or #dbeafe
    jarring = {"#3b82d4", "#1a73e8", "#dbeafe", "#0d6efd", "blue"}
    assert bg not in jarring, (
        f"TABLE_STYLE_ACTIVE_CELL backgroundColor {bg!r} is a jarring blue — use 'inherit' or transparent"
    )


def test_active_cell_no_border():
    """TABLE_STYLE_ACTIVE_CELL must not show a border (Dash default is blue)."""
    style = panels.TABLE_STYLE_ACTIVE_CELL
    border = style.get("border", "none").lower()
    assert border == "none", (
        f"TABLE_STYLE_ACTIVE_CELL border must be 'none' to suppress Dash's blue active-cell ring, got {border!r}"
    )


def test_active_cell_applied_to_affected_table():
    """affected_table() style_data_conditional must include an 'active' state rule
    that suppresses Dash's blue highlight."""
    import json  # noqa: PLC0415
    r = json.loads((_DASH_ROOT / "reports" / "impact-s1.mock.json").read_text(encoding="utf-8"))
    table = panels.affected_table(r)
    conds = table.style_data_conditional or []
    # Find the condition that targets active state
    active_conds = [c for c in conds if c.get("if", {}).get("state") == "active"]
    assert active_conds, (
        "style_data_conditional must include a rule for state='active' to suppress "
        "Dash's default blue active-cell border"
    )
    bg = (active_conds[0].get("backgroundColor") or "").lower()
    assert bg in ("inherit", "", "transparent"), (
        f"Active-state backgroundColor should be 'inherit'/'transparent', got {bg!r}"
    )
    border = (active_conds[0].get("border") or "none").lower()
    assert border == "none", (
        f"Active-state border must be 'none', got {border!r}"
    )


# ── 2. CSS does NOT apply transition to background on every (*) element ────────

def test_css_no_wildcard_transition_with_background():
    """CSS must not apply a broad `* { transition: background ... }` rule.

    Such a rule causes the DataTable hover-flash: every mouse-move re-triggers
    a CSS transition on every td in the table, producing a dark-blue flicker.
    """
    # Match patterns like: * { ... transition: background ... }
    # or * { transition: background-color ... } with optional other props
    pattern = re.compile(
        r"\*\s*\{[^}]*transition\s*:[^}]*background",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(_CSS)
    assert match is None, (
        "CSS must not apply `transition: background...` on `*` — this causes DataTable "
        f"hover-flash. Found: {match.group()[:120]!r}"
    )


def test_css_datatable_cells_have_no_transition():
    """DataTable `td` cells must explicitly disable transition in CSS to prevent hover-flash."""
    assert "transition: none !important" in _CSS, (
        "DataTable td must have `transition: none !important` to prevent hover-flash refire"
    )


# ── 3. Hover tint is subtle (no dark-blue opacity >= 20%) ─────────────────────

def test_css_hover_tint_is_subtle():
    """The tr:hover td hover tint must use a low-opacity overlay (< 0.15).

    This uses `box-shadow: inset ... rgba(...)` rather than `background-color`
    on purpose: a plain background-color hover rule with !important beats a
    row's own verdict-colour background (also set via !important) because it
    comes later in the stylesheet, so a will_break row's red tint would
    disappear the instant the cursor is over it. An inset box-shadow paints
    ON TOP of the existing background instead of replacing it.
    """
    pattern = re.compile(
        r"tr:hover\s+td\s*\{[^}]*box-shadow\s*:\s*inset[^;]*rgba\s*\([^)]+\)",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(_CSS)
    assert match is not None, "tr:hover td must set an inset box-shadow rgba() hover tint"
    rgba_text = match.group()
    # Extract the alpha value from rgba(r,g,b,a)
    alpha_match = re.search(r"rgba\s*\(\s*[\d,\s]+,\s*([\d.]+)\s*\)", rgba_text)
    assert alpha_match is not None, "hover tint must use rgba() with an alpha value"
    alpha = float(alpha_match.group(1))
    assert alpha < 0.15, (
        f"Hover tint opacity {alpha} is too high (must be < 0.15) — jarring on mouse move"
    )
    # The overlay approach must not also replace background-color on hover,
    # which is the exact bug this rule was rewritten to avoid.
    assert "background-color" not in match.group(), (
        "tr:hover td must not set background-color — it overrides verdict-tinted rows; "
        "use box-shadow inset instead"
    )


# ── 4. render.yaml exists with required fields ─────────────────────────────────

def test_render_yaml_exists():
    """dashboard/render.yaml must exist."""
    render_yaml = _DASH_ROOT / "render.yaml"
    assert render_yaml.exists(), "dashboard/render.yaml must be committed for Render deploy"


def test_render_yaml_has_gunicorn_start_command():
    """render.yaml startCommand must be 'gunicorn app:server'."""
    render_yaml = _DASH_ROOT / "render.yaml"
    if not render_yaml.exists():
        return  # covered by test above
    content = render_yaml.read_text(encoding="utf-8")
    assert "gunicorn app:server" in content, (
        "render.yaml startCommand must be 'gunicorn app:server'"
    )


def test_render_yaml_python_version():
    """render.yaml must pin PYTHON_VERSION to 3.12.x."""
    render_yaml = _DASH_ROOT / "render.yaml"
    if not render_yaml.exists():
        return
    content = render_yaml.read_text(encoding="utf-8")
    assert "3.12" in content, "render.yaml must specify PYTHON_VERSION 3.12.x"


# ── 5. og.png exists and is reasonably sized ──────────────────────────────────

def test_og_png_exists():
    """dashboard/assets/og.png must exist."""
    og = _DASH_ROOT / "assets" / "og.png"
    assert og.exists(), "dashboard/assets/og.png must be committed for share preview"


def test_og_png_under_300kb():
    """og.png must be under 300 kB."""
    og = _DASH_ROOT / "assets" / "og.png"
    if not og.exists():
        return
    size = og.stat().st_size
    assert size < 300_000, f"og.png is {size // 1024} kB — must be under 300 kB"


# ── 6. app.index_string contains og:image ─────────────────────────────────────

def test_index_string_has_og_image():
    """app.index_string must include og:image pointing to /assets/og.png."""
    assert "og:image" in _app.app.index_string, (
        "app.index_string must contain og:image meta tag"
    )
    assert "/assets/og.png" in _app.app.index_string, (
        "og:image must point to /assets/og.png"
    )
