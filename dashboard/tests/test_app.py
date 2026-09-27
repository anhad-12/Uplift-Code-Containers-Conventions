"""
Tests for dashboard/app.py — C2 requirements.

Run from the dashboard/ directory (or repo root with PYTHONPATH set):
    python -m pytest -q dashboard/tests/test_app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the dashboard package root is importable when pytest is run from the
# repo root rather than from dashboard/.
_DASH_ROOT = Path(__file__).resolve().parent.parent
if str(_DASH_ROOT) not in sys.path:
    sys.path.insert(0, str(_DASH_ROOT))

import app as _app_module  # noqa: E402 — after path fixup


# ── Helpers ──────────────────────────────────────────────────────────────────

def _render(layout_node) -> str:
    """Convert a Dash component tree to its string representation for inspection."""
    return str(layout_node)


# ── 1. Flask test-client returns HTTP 200 ────────────────────────────────────

def test_server_returns_200():
    client = _app_module.app.server.test_client()
    response = client.get("/")
    assert response.status_code == 200


# ── 2. route("") returns the home layout ─────────────────────────────────────

def test_route_no_search_returns_home():
    layout = _app_module.route(None)
    rendered = _render(layout)
    # Home layout must contain the hero headline
    assert "Know what a change will " in rendered and "Fix it." in rendered


def test_route_empty_search_returns_home():
    layout = _app_module.route("")
    rendered = _render(layout)
    assert "Know what a change will " in rendered and "Fix it." in rendered


# ── 3. route("?scenario=s1-null-user") returns the detail layout ─────────────

def test_route_known_scenario_returns_detail():
    layout = _app_module.route("?scenario=s1-null-user")
    rendered = _render(layout)
    # Detail layout shows the scenario title
    assert "get_user returns None" in rendered
    # Detail layout should NOT contain the hero headline
    assert "Know what a change will break" not in rendered


# ── 4. Unknown scenario id falls back to home ────────────────────────────────

def test_route_unknown_scenario_falls_back_to_home():
    layout = _app_module.route("?scenario=does-not-exist")
    rendered = _render(layout)
    assert "Know what a change will " in rendered and "Fix it." in rendered


# ── 5. home() structure checks ───────────────────────────────────────────────

def test_home_contains_hero_subtitle():
    rendered = _render(_app_module.home())
    assert "Uplift predicts what a change breaks" in rendered


def test_home_contains_how_it_works_strip():
    rendered = _render(_app_module.home())
    assert "Predict" in rendered
    assert "Prove" in rendered
    assert "Repair" in rendered
    assert "Verify" in rendered


# ── Bolder pass: hero emphasis + real-stepper proof teaser ───────────────────

def test_hero_h1_uses_emphasis_span_not_gradient_class():
    """The hero H1 must colour 'break' via a real span (hero-emphasis), not
    the old gradient-clip-text technique (a common generic-AI-dashboard tell,
    flagged independently by the design hook and the Impeccable critique)."""
    rendered = _render(_app_module.home())
    assert "hero-emphasis" in rendered
    assert "break" in rendered


def test_hero_css_has_no_gradient_clip_text():
    css = (Path(_app_module.__file__).resolve().parent / "assets" / "style.css").read_text(encoding="utf-8")
    assert "background-clip: text" not in css
    assert "-webkit-text-fill-color: transparent" not in css


def test_home_hero_includes_real_stepper_proof_teaser():
    """The hero must reuse the actual stepper() component (proof-of-product),
    not a decorative promise — this is the bolder-pass amplification move."""
    rendered = _render(_app_module.home())
    assert "hero-proof-teaser" in rendered
    assert "stepper" in rendered
    # The teaser marks all four steps done, using the real step-done styling.
    assert "step-done" in rendered


def test_how_it_works_step_cards_use_system_owned_tokens():
    """Each how-it-works step must render as its own hiw-step card (the
    bolder-pass replacement for a bare numbered list)."""
    rendered = _render(_app_module.home())
    assert rendered.count("hiw-step") >= 4


def test_home_contains_scenario_cards():
    rendered = _render(_app_module.home())
    for report in _app_module.REPORTS.values():
        assert report["scenario"]["title"] in rendered


# ── 6. scenario_cards() headline figures and Open button ─────────────────────

def test_scenario_cards_contain_figures_and_open_button():
    rendered = _render(_app_module.scenario_cards())
    assert "predicted" in rendered
    assert "confirmed" in rendered
    assert "fixed" in rendered
    assert "regressions" in rendered
    assert "Open" in rendered


def test_scenario_cards_contain_risk_badge():
    rendered = _render(_app_module.scenario_cards())
    # Both reports have risk levels; badge text is uppercased in the component
    assert "HIGH" in rendered or "MEDIUM" in rendered or "LOW" in rendered


# ── 7. stepper() accessibility checks ────────────────────────────────────────

def test_stepper_has_text_labels_not_colour_only():
    pipeline = {"predict": "done", "prove": "done", "repair": "pending", "verify": "pending"}
    rendered = _render(_app_module.stepper(pipeline))
    # Every step name must appear as text
    for name in ("Predict", "Prove", "Repair", "Verify"):
        assert name in rendered
    # State labels must appear as text too
    assert "done" in rendered
    assert "pending" in rendered


def test_stepper_aria_labels_present():
    pipeline = {"predict": "done", "prove": "pending", "repair": "pending", "verify": "pending"}
    rendered = _render(_app_module.stepper(pipeline))
    # aria-label attributes are serialised in Dash's string repr
    assert "aria-label" in rendered


# ── 8. C3 filter chip options, values and hint text ──────────────────────────

def test_filter_chip_options_unchanged():
    """FILTER_OPTIONS must contain the five expected verdicts in the correct order."""
    values = [o["value"] for o in _app_module.FILTER_OPTIONS]
    assert values == ["will_break", "might_break", "safe", "unknown", "untested"]


def test_filter_chip_labels_unchanged():
    """Human-readable labels must match the original spec."""
    labels = [o["label"] for o in _app_module.FILTER_OPTIONS]
    assert labels == ["will break", "might break", "safe", "unknown", "untested only"]


def test_filter_chip_default_values():
    """Default selection must include the four verdict chips (not untested)."""
    assert set(_app_module.FILTER_DEFAULT) == {"will_break", "might_break", "safe", "unknown"}


def test_filter_chip_detail_contains_checklist():
    """detail_view must render a Checklist with id 'filter-chips'."""
    layout = _app_module.detail_view("s1-null-user")
    rendered = _render(layout)
    assert "filter-chips" in rendered
    # All five option values must be present
    for val in ["will_break", "might_break", "safe", "unknown", "untested"]:
        assert val in rendered


def test_filter_chip_hint_text_present():
    """The hint line under the chips must appear in the detail view."""
    layout = _app_module.detail_view("s1-null-user")
    rendered = _render(layout)
    assert "Toggle a verdict to show or hide those nodes" in rendered
    assert "Untested only" in rendered
