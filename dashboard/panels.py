"""Right-hand detail panel, summary strip, and affected-items DataTable. Pure Dash components."""
from __future__ import annotations

from pathlib import Path

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import dash_table, dcc, html

# ── Bob mode summaries ────────────────────────────────────────────────────────
_BOB_MODE_SUMMARIES: dict[str, str] = {
    "uplift-impact-analyst":    "judges impact, cannot edit code",
    "uplift-prover":            "writes proof tests only",
    "uplift-migration-planner": "reads the migration guide",
    "uplift-worker-users":      "can edit only its own module",
    "uplift-worker-orders":     "can edit only its own module",
    "uplift-worker-payments":   "can edit only its own module",
    "uplift-worker-core":       "can edit only its own module",
    "uplift-verifier":          "re-runs tests and writes reports",
    "uplift-convention-scanner": "learns the repo's style",
}

# Static fallback list (9 modes) when provenance.bobModes is empty
_STATIC_BOB_MODES: list[str] = list(_BOB_MODE_SUMMARIES.keys())

_BOB_FEATURES = (
    "Agent mode, parallel tasks, subagents, and document understanding "
    "are the four IBM Bob features used to predict, prove, repair and verify every change."
)

# Verdict -> hex. Bootstrap's semantic colour tokens (danger/warning/success)
# render a visibly different red/orange/green than the rest of the app (the
# graph, the risk gauge, the filter chips), which is exactly the colour-token
# fragmentation the design critique flagged as P2. These hexes match
# graph.VERDICT_COLORS and panels._RISK_GAUGE_COLOR exactly, so every verdict
# badge anywhere in the app reads as the same system. (graph.py stays
# Dash-free and is not imported here — the four values are small and mirrored
# deliberately, the same convention _RISK_GAUGE_COLOR already follows.)
VERDICT_HEX = {
    "will_break":  "#d64545",
    "might_break": "#e0a030",
    "safe":        "#3fa66a",
    "unknown":     "#8a8f98",
}

# Badge background + text colour, one entry per badge "kind", chosen so every
# badge clears 4.5:1 contrast — not just eyeballed as "white on a colour
# chip". White on the raw VERDICT_HEX might_break/safe/unknown values is only
# 2.3-3.3:1 (small badge text doesn't get the "large text" 3:1 exemption), so
# those three use dark text instead. will_break/infra/accent needed the
# background darkened one notch (same hue, same underlying node/graph colour
# untouched — only the badge's own background differs) to clear 4.5:1 with
# white text.
BADGE_STYLE = {
    "will_break":  {"backgroundColor": "#d43d3d", "color": "#ffffff"},
    "might_break": {"backgroundColor": VERDICT_HEX["might_break"], "color": "#1d2330"},
    "safe":        {"backgroundColor": VERDICT_HEX["safe"],        "color": "#1d2330"},
    "unknown":     {"backgroundColor": VERDICT_HEX["unknown"],     "color": "#1d2330"},
    "changed":     {"backgroundColor": "#3b5bdb", "color": "#ffffff"},
    "infra":       {"backgroundColor": "#0b8177", "color": "#ffffff"},
    "accent":      {"backgroundColor": "#4565f4", "color": "#ffffff"},
}

# Maps verdict -> short icon character
VERDICT_ICON = {
    "will_break":  "✗",
    "might_break": "⚠",
    "safe":        "✓",
    "unknown":     "?",
}

# Maps proof status -> display label
PROOF_STATUS_LABEL = {
    "confirmed":     "Confirmed",
    "unconfirmed":   "Unconfirmed",
    "not_attempted": "Not attempted",
    "not_applicable": "Not applicable",
}

# Humanized verdict text so a cold reader never sees a raw snake_case enum
# next to the filter chips/legend, which already show "will break" etc.
VERDICT_LABEL = {
    "will_break":  "will break",
    "might_break": "might break",
    "safe":        "safe",
    "unknown":     "unknown",
}


def _tick_cross(value: bool | None) -> str:
    """Return a tick + 'yes' or a cross + 'no' for a boolean."""
    if value is True:
        return "✓ yes"
    if value is False:
        return "✗ no"
    return "—"


def detail_panel(item: dict) -> dbc.Card:
    """Build the right-hand detail card for a single affected item or contract.

    Args:
        item: One entry from ``report["affected"]`` or ``report["contracts"]``.
              Contract items are identified by their ``id`` starting with
              ``"contract:"``.

    Returns:
        A ``dbc.Card`` Dash component.
    """
    item_id = item.get("id", "")
    # Contracts: either the id already has the "contract:" prefix (when coming
    # from a graph node id) OR the item has a "type" field set to "route" /
    # "contract" (raw contract dict from report["contracts"] which has no "file").
    is_contract = item_id.startswith("contract:") or item.get("type") in ("route", "contract") or "file" not in item

    verdict = item.get("verdict", "unknown")
    badge_style = BADGE_STYLE.get(verdict, BADGE_STYLE["unknown"])
    badge_icon  = VERDICT_ICON.get(verdict, "?")

    # ── header row: id + verdict badge ──────────────────────────────────────
    header = dbc.CardHeader([
        html.Span(item_id, className="fw-bold small font-monospace d-block"),
        dbc.Badge(
            [html.Span(badge_icon, className="me-1", **{"aria-hidden": "true"}),
             VERDICT_LABEL.get(verdict, verdict)],
            className="mt-1",
            style=badge_style,
            title=f"verdict: {verdict}",
        ),
    ])

    body_children: list = []

    # ── metadata row ────────────────────────────────────────────────────────
    if is_contract:
        # Contracts: route, handler
        body_children.append(html.Dl([
            html.Dt("Route"),    html.Dd(item.get("id", "").removeprefix("contract:") or "—"),
            html.Dt("Handler"),  html.Dd(item.get("handler", "—") or "—"),
        ], className="row-dl"))
    else:
        # Affected items: id, file:line, module, hop, layer
        file_line = f"{item.get('file', '?')}:{item.get('line', '?')}"
        body_children.append(html.Dl([
            html.Dt("File"),   html.Dd(file_line, className="font-monospace small"),
            html.Dt("Module"), html.Dd(item.get("module", "—")),
            html.Dt("Hop"),    html.Dd(str(item.get("hop", "—"))),
            html.Dt("Layer"),  html.Dd(item.get("layer", "—")),
        ], className="row-dl"))

    # ── code snippet ─────────────────────────────────────────────────────────
    snippet = item.get("snippet", "")
    if snippet:
        body_children.append(dcc.Markdown(
            f"```python\n{snippet}\n```",
            className="snippet-md",
        ))

    # ── verdict / reason / fix ───────────────────────────────────────────────
    body_children.append(html.P(item.get("reason", ""), className="small text-dim mb-1"))
    fix = item.get("fix", "")
    if fix:
        body_children.append(html.P(["Fix: ", html.Em(fix)], className="small mb-2"))

    # ── proof section ────────────────────────────────────────────────────────
    proof = item.get("proof") or {}
    p_status = PROOF_STATUS_LABEL.get(proof.get("status", ""), proof.get("status", "—"))
    proof_items: list = [
        html.Li(f"Status: {p_status}"),
    ]
    if proof.get("testFile"):
        proof_items.append(html.Li(["Test file: ", html.Code(proof["testFile"], className="small")]))
    if proof.get("status") not in (None, "not_applicable", "not_attempted"):
        proof_items.append(html.Li(f"Passes on base: {_tick_cross(proof.get('passesOnBase'))}"))
        proof_items.append(html.Li(f"Fails on head: {_tick_cross(proof.get('failsOnHead'))}"))
    body_children.append(html.Details([
        html.Summary("Proof"),
        html.Ul(proof_items, className="small mb-0"),
    ], open=True))

    # ── repair section (affected items only) ────────────────────────────────
    repair = item.get("repair") or {}
    if repair:
        files = repair.get("filesChanged") or []
        repair_items: list = [
            html.Li(f"Status: {repair.get('status', '—')}"),
            html.Li(f"Worker: {repair.get('worker', '—')}"),
        ]
        if files:
            repair_items.append(html.Li(["Files changed: ", html.Ul([html.Li(html.Code(f)) for f in files])]))
        body_children.append(html.Details([
            html.Summary("Repair"),
            html.Ul(repair_items, className="small mb-0"),
        ], open=True))

    return dbc.Card([header, dbc.CardBody(body_children)], className="detail-card")


def changed_symbol_panel(symbol: dict, change: dict | None = None) -> dbc.Card:
    """Detail card for the star "changed symbol" node — the root cause.

    Args:
        symbol: One entry from ``report["changedSymbols"]`` (id, kind,
                changeType, optional hints).
        change: The report's top-level ``change`` block (summary, kind),
                shown as context for what triggered this run.

    Returns:
        A ``dbc.Card`` Dash component, styled like ``detail_panel``'s output
        so tapping the root node feels like part of the same system rather
        than a dead end.
    """
    change = change or {}
    header = dbc.CardHeader([
        html.Span(symbol.get("id", ""), className="fw-bold small font-monospace d-block"),
        dbc.Badge(
            [html.Span("★", className="me-1", **{"aria-hidden": "true"}), "changed symbol"],
            className="mt-1",
            # Matches graph.py's .changed node colour and the legend's star swatch.
            style=BADGE_STYLE["changed"],
        ),
    ])
    body_children: list = [
        html.Dl([
            html.Dt("Kind"),       html.Dd(symbol.get("kind", "—")),
            html.Dt("Change type"), html.Dd(symbol.get("changeType", "—")),
        ], className="row-dl"),
    ]
    hints = symbol.get("hints") or []
    if hints:
        body_children.append(html.Div("What changed:", className="small fw-semibold mb-1"))
        body_children.append(html.Ul([html.Li(h, className="small") for h in hints]))
    if change.get("summary"):
        body_children.append(html.P(change["summary"], className="small text-dim mb-0"))
    return dbc.Card([header, dbc.CardBody(body_children)], className="detail-card")


def infra_panel(infra: dict) -> dbc.Card:
    """Detail card for a Docker/infra-impact node (F17).

    Args:
        infra: One entry from ``report["infraImpact"]`` (file, trigger,
               optional layer/totalLayers/layersRebuilt/suggestion/
               measuredRebuildSeconds).

    Returns:
        A ``dbc.Card`` Dash component. Only shows a rebuild time when one was
        actually measured — never a made-up number.
    """
    header = dbc.CardHeader([
        html.Span(infra.get("file", ""), className="fw-bold small font-monospace d-block"),
        dbc.Badge(
            [html.Span("🐳", className="me-1", **{"aria-hidden": "true"}), "Docker layer impact"],
            className="mt-1",
            # Matches graph.py's .infra node colour and the legend's Docker swatch.
            style=BADGE_STYLE["infra"],
        ),
    ])
    body_children: list = []
    layer, total = infra.get("layer"), infra.get("totalLayers")
    if layer is not None and total is not None:
        body_children.append(html.P(f"Layer {layer} of {total}", className="small fw-semibold mb-1"))
    body_children.append(html.P(infra.get("trigger", ""), className="small text-dim mb-1"))
    if infra.get("layersRebuilt"):
        body_children.append(html.P(["Layers rebuilt: ", html.Strong(infra["layersRebuilt"])], className="small mb-1"))
    if infra.get("suggestion"):
        body_children.append(html.P(["Fix: ", html.Em(infra["suggestion"])], className="small mb-1"))
    if infra.get("measuredRebuildSeconds") is not None:
        body_children.append(html.P(
            f"Measured rebuild time: {infra['measuredRebuildSeconds']}s",
            className="small mb-0",
        ))
    return dbc.Card([header, dbc.CardBody(body_children)], className="detail-card")


def conventions_card(conventions: dict) -> dbc.Card | None:
    """'Repo conventions' card (F16): naming/imports/error-handling/file-layout
    plus a compliance badge, from ``report["conventions"]``.

    Returns None when *conventions* is absent/empty so callers can render
    nothing rather than an empty card.
    """
    if not conventions:
        return None

    rows: list = []
    for label, key in (("Naming", "naming"), ("Imports", "imports"),
                        ("Error handling", "errorHandling"), ("File layout", "fileLayout")):
        value = conventions.get(key)
        if value:
            rows.append(html.Dt(label))
            rows.append(html.Dd(value))

    evidence = conventions.get("evidenceFiles") or []
    evidence_block = []
    if evidence:
        evidence_block = [
            html.Div("Evidence files:", className="small fw-semibold mt-2 mb-1"),
            html.Ul([html.Li(html.Code(f, className="small"), className="small") for f in evidence]),
        ]

    compliance = conventions.get("compliance") or {}
    badge_children = []
    if compliance:
        checked   = compliance.get("checkedLines")
        violated  = compliance.get("violations")
        retried   = compliance.get("retried")
        if checked is not None:
            badge_children.append(dbc.Badge(
                f"{checked} lines checked", className="me-1",
                style=BADGE_STYLE["unknown"],
            ))
        if violated is not None:
            badge_children.append(dbc.Badge(
                f"{violated} violation{'s' if violated != 1 else ''}",
                className="me-1",
                style=BADGE_STYLE["safe"] if violated == 0 else BADGE_STYLE["might_break"],
            ))
        if retried:
            badge_children.append(dbc.Badge(
                "retried after violation",
                style=BADGE_STYLE["accent"],
            ))

    return dbc.Card([
        dbc.CardHeader(html.Strong("Repo conventions", style={"color": "#1d2330"}),
                       style={"backgroundColor": "#f7f8fa", "borderBottom": "1px solid #e5e7eb"}),
        dbc.CardBody([
            html.Dl(rows, className="row-dl mb-2") if rows else html.Div(),
            html.Div(badge_children, className="mb-1") if badge_children else html.Div(),
            *evidence_block,
        ], style={"backgroundColor": "#ffffff", "color": "#1d2330"}),
    ], className="mb-3", style={"border": "1px solid #e5e7eb", "borderRadius": "6px"})


# ── DataTable columns definition ─────────────────────────────────────────────
TABLE_COLUMNS = [
    {"name": "ID",      "id": "id"},
    {"name": "Module",  "id": "module"},
    {"name": "Hop",     "id": "hop"},
    {"name": "Layer",   "id": "layer"},
    {"name": "Verdict", "id": "verdict"},
    {"name": "Proof",   "id": "proof"},
    {"name": "Repair",  "id": "repair"},
]

# Conditional styling by verdict
TABLE_STYLE_DATA_CONDITIONAL = [
    {"if": {"filter_query": '{verdict} = "will_break"'},  "backgroundColor": "#fdf0f0", "color": "#7b1d1d"},
    {"if": {"filter_query": '{verdict} = "might_break"'}, "backgroundColor": "#fefae8", "color": "#7b5900"},
    {"if": {"filter_query": '{verdict} = "safe"'},        "backgroundColor": "#f0faf3", "color": "#14532d"},
    {"if": {"filter_query": '{verdict} = "unknown"'},     "backgroundColor": "#f5f5f5", "color": "#444"},
    # Selected row: stable teal highlight (not Dash's default blue active-cell)
    {"if": {"state": "selected"},                         "backgroundColor": "#e8f0fe", "border": "none"},
]

# Active-cell style: added as a state condition in style_data_conditional
# (style_active_cell is not available in dash_table 4.x)
TABLE_STYLE_ACTIVE_CELL = {
    "backgroundColor": "inherit",
    "border": "none",
}

# Extra conditional for the "active" state — suppresses Dash's default blue active-cell highlight
_TABLE_ACTIVE_CELL_COND = {"if": {"state": "active"}, "backgroundColor": "inherit", "border": "none"}


def build_table_rows(report: dict) -> list[dict]:
    """Convert report["affected"] to a list of flat row dicts for DataTable."""
    rows = []
    for item in report.get("affected", []):
        proof  = item.get("proof") or {}
        repair = item.get("repair") or {}
        rows.append({
            "id":      item.get("id", ""),
            "module":  item.get("module", ""),
            "hop":     item.get("hop", ""),
            "layer":   item.get("layer", ""),
            "verdict": item.get("verdict", ""),
            "proof":   PROOF_STATUS_LABEL.get(proof.get("status", ""), proof.get("status", "")),
            "repair":  repair.get("status", ""),
        })
    return rows


def affected_table(report: dict) -> dash_table.DataTable:
    """Build a sortable DataTable for all affected items in the report."""
    rows = build_table_rows(report)
    return dash_table.DataTable(
        id="affected-table",
        columns=TABLE_COLUMNS,
        data=rows,
        sort_action="native",
        row_selectable="single",
        style_table={"overflowX": "auto"},
        style_cell={
            "textAlign": "left",
            "fontSize": "14px",
            "padding": "10px 14px",
            "minHeight": "44px",
            "lineHeight": "1.4",
        },
        style_header={
            "fontWeight": "bold",
            "backgroundColor": "#ffffff",
            "color": "#1d2330",      # dark text — ≥ 16:1 on white
            "borderBottom": "2px solid #d0d4de",
            "position": "sticky",
            "top": 0,
        },
        style_data_conditional=TABLE_STYLE_DATA_CONDITIONAL + [_TABLE_ACTIVE_CELL_COND],
    )


# ── Risk level colours ────────────────────────────────────────────────────────
_RISK_GAUGE_COLOR = {
    "high":    "#d64545",
    "medium":  "#e0a030",
    "low":     "#3fa66a",
    "unknown": "#8a8f98",
}

# Light font colour used on the dark page background (≥4.5:1 contrast on #0e1320)
_CHART_FONT_COLOR = "#e6ebf5"
# Dark font colour used on white/light card backgrounds (≥4.5:1 contrast on #ffffff)
_CHART_FONT_COLOR_LIGHT = "#1d2330"

# Formula tooltip text (matches schema definition)
_RISK_FORMULA = (
    "score = min(100, 10×willBreak + 4×mightBreak + 12×untested + 15×contractHits)"
)


def _chart_layout(on_light: bool = False, **overrides) -> dict:
    """Return a shared Plotly layout dict with appropriate font colour and transparent backgrounds.

    Args:
        on_light: When True, use dark font (#1d2330) suitable for white/light card
                  backgrounds. When False (default), use light font (#e6ebf5) for
                  the dark page background.
        **overrides: Keyword arguments merged on top of the defaults.

    Returns:
        Layout dict for ``fig.update_layout(**...)``.
    """
    font_color = _CHART_FONT_COLOR_LIGHT if on_light else _CHART_FONT_COLOR
    base = {
        "font": {"color": font_color, "size": 13},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
    }
    base.update(overrides)
    return base


def _risk_gauge(risk: dict) -> dcc.Graph:
    """Plotly Indicator gauge for risk score 0-100."""
    score = risk.get("score", 0)
    level = risk.get("level", "unknown")
    color = _RISK_GAUGE_COLOR.get(level, "#8a8f98")

    factors = risk.get("factors", [])
    tooltip_lines = [_RISK_FORMULA, ""] + (factors if factors else ["No factors listed"])
    tooltip = "\n".join(tooltip_lines)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"font": {"size": 32, "color": color}},
        gauge={
            "axis": {
                "range": [0, 100],
                "tickfont": {"size": 11, "color": _CHART_FONT_COLOR},
            },
            "bar": {"color": color, "thickness": 0.3},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 40],   "color": "rgba(63,166,106,0.20)"},
                {"range": [40, 70],  "color": "rgba(224,160,48,0.20)"},
                {"range": [70, 100], "color": "rgba(214,69,69,0.20)"},
            ],
            "threshold": {"line": {"color": color, "width": 3}, "thickness": 0.75, "value": score},
        },
        title={"text": f"Risk: {level.upper()}", "font": {"size": 13, "color": _CHART_FONT_COLOR}},
    ))
    fig.update_layout(**_chart_layout(
        margin={"t": 50, "b": 10, "l": 20, "r": 20},
        height=180,
    ))
    return html.Div(
        dcc.Graph(
            figure=fig,
            config={"displayModeBar": False, "responsive": True},
            style={"width": "100%"},
        ),
        title=tooltip,   # native <title> tooltip on the wrapper div
    )


def _tests_bar(tests: dict) -> dcc.Graph | None:
    """Stacked bar of passed/failed tests before/after. Returns None if data absent."""
    if not tests or "before" not in tests or "after" not in tests:
        return None
    before = tests["before"]
    after  = tests["after"]
    labels = ["Before", "After"]
    passed = [before.get("passed", 0), after.get("passed", 0)]
    failed = [before.get("failed", 0), after.get("failed", 0)]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Passed",
        x=labels,
        y=passed,
        marker_color="#3fa66a",
        text=[str(v) if v > 0 else "" for v in passed],
        textposition="inside",
        textangle=0,
        insidetextanchor="middle",
        textfont={"color": "#ffffff", "size": 13},
    ))
    fig.add_trace(go.Bar(
        name="Failed",
        x=labels,
        y=failed,
        marker_color="#d64545",
        text=[str(v) if v > 0 else "" for v in failed],
        textposition="inside",
        textangle=0,
        insidetextanchor="middle",
        textfont={"color": "#ffffff", "size": 13},
    ))
    fig.update_layout(**_chart_layout(
        barmode="stack",
        margin={"t": 40, "b": 30, "l": 30, "r": 10},
        height=160,
        legend={
            "orientation": "h",
            "y": -0.3,
            "font": {"size": 11, "color": _CHART_FONT_COLOR},
        },
        title={"text": "Tests before / after", "font": {"size": 13, "color": _CHART_FONT_COLOR}},
        xaxis={
            "tickfont": {"color": _CHART_FONT_COLOR},
            "gridcolor": "rgba(255,255,255,0.12)",
            "linecolor": "rgba(255,255,255,0.20)",
        },
        yaxis={
            "tickfont": {"color": _CHART_FONT_COLOR},
            "gridcolor": "rgba(255,255,255,0.12)",
            "linecolor": "rgba(255,255,255,0.20)",
        },
        hoverlabel={
            "bgcolor": "#1c2540",
            "bordercolor": "#2a3555",
            "font": {"color": "#e6ebf5", "size": 12},
        },
    ))
    return dcc.Graph(figure=fig, config={"displayModeBar": False, "responsive": True},
                     style={"width": "100%"})


def _accuracy_card(accuracy: dict, reports_dir: Path | None = None) -> dbc.Card | None:
    """Accuracy card with precision/recall, TP/FP/FN and 'See what we missed' modal.

    Returns None when accuracy is absent (migrate/mock reports without accuracy).
    """
    if not accuracy:
        return None

    precision_pct = f"{accuracy.get('precision', 0) * 100:.0f}%"
    recall_pct    = f"{accuracy.get('recall', 0) * 100:.0f}%"
    tp = accuracy.get("truePositives",  0)
    fp = accuracy.get("falsePositives", 0)
    fn = accuracy.get("falseNegatives", 0)

    # Locate eval.md relative to the reports directory
    if reports_dir is None:
        reports_dir = Path(__file__).parent / "reports"
    eval_path = reports_dir.parent / "reports" / "eval.md"
    # Also check directly in reports_dir
    if not eval_path.exists():
        eval_path = reports_dir / "eval.md"

    modal_children: list = []
    modal_button: list = []
    if eval_path.exists():
        eval_text = eval_path.read_text(encoding="utf-8")
        modal_children = [
            dbc.ModalHeader(dbc.ModalTitle("What we missed")),
            dbc.ModalBody(dcc.Markdown(eval_text)),
        ]
        modal_button = [
            dbc.Button(
                "See what we missed",
                id="open-eval-modal",
                color="link",
                size="sm",
                className="mt-1 p-0",
            ),
            dbc.Modal(
                modal_children,
                id="eval-modal",
                is_open=False,
                scrollable=True,
                size="lg",
            ),
        ]

    body = [
        dbc.Row([
            dbc.Col([
                html.Div(precision_pct, className="fig-value"),
                html.Div("Precision", className="fig-label"),
            ], xs=6),
            dbc.Col([
                html.Div(recall_pct, className="fig-value"),
                html.Div("Recall", className="fig-label"),
            ], xs=6),
        ], className="g-2 mb-2"),
        html.Div([
            dbc.Badge(f"TP {tp}", className="me-1", style=BADGE_STYLE["safe"]),
            dbc.Badge(f"FP {fp}", className="me-1", style=BADGE_STYLE["might_break"]),
            dbc.Badge(f"FN {fn}", style=BADGE_STYLE["will_break"]),
        ], className="mb-1"),
    ] + modal_button

    return dbc.Card([
        dbc.CardHeader(html.Strong("Accuracy")),
        dbc.CardBody(body),
    ], className="h-100")


def summary_strip(report: dict, reports_dir: Path | None = None) -> html.Div:
    """Summary strip shown at the top of the detail page.

    Contains:
    - Risk gauge (score 0-100, level, tooltip with factors + formula)
    - Metric cards: predicted, confirmed, fixed, regressions
    - Tests before/after stacked bar (omitted when absent)
    - Accuracy card with precision/recall, TP/FP/FN, 'See what we missed' button
    - Two lists: "Tests to run" and "Untested affected code"

    Args:
        report: Parsed report dict.
        reports_dir: Optional path to the reports directory (for locating eval.md).

    Returns:
        A ``html.Div`` Dash component.
    """
    m    = report.get("metrics", {})
    risk = report.get("risk", {})

    # ── 1. Risk gauge ─────────────────────────────────────────────────────────
    gauge = _risk_gauge(risk)

    # ── 2. Metric cards ───────────────────────────────────────────────────────
    def _metric(label: str, value, extra_class: str = "") -> dbc.Col:
        val_class = f"fig-value {extra_class}".strip()
        return dbc.Col(dbc.Card(dbc.CardBody([
            html.Div(str(value), className=val_class),
            html.Div(label, className="fig-label"),
        ])), xs=6, sm=3)

    regressions = m.get("regressions", 0)
    metric_row = dbc.Row([
        _metric("Predicted",   m.get("predicted",   0)),
        _metric("Confirmed",   m.get("confirmed",   0)),
        _metric("Fixed",       m.get("fixed",       0)),
        _metric("Regressions", regressions, "fig-regressions" if regressions else ""),
    ], className="g-2 my-2")

    # ── 3. Tests bar (optional) ───────────────────────────────────────────────
    tests_bar = _tests_bar(m.get("tests"))

    # ── 4. Accuracy card (optional) ───────────────────────────────────────────
    accuracy_card = _accuracy_card(m.get("accuracy"), reports_dir=reports_dir)

    # ── 5. Tests-to-run and untested lists ────────────────────────────────────
    tests_to_run = report.get("testsToRun") or []
    untested     = report.get("untested")   or []

    def _bullet_list(items: list[str], empty: str = "—") -> html.Ul | html.P:
        if not items:
            return html.P(
                empty,
                className="small mb-0",
                style={"color": "#c9d3e6", "fontStyle": "italic"},
            )
        return html.Ul([html.Li(html.Code(t, className="small"), className="small") for t in items],
                       style={"paddingLeft": "1.2rem", "marginBottom": 0})

    lists_row = dbc.Row([
        dbc.Col([
            html.Strong("Tests to run", className="small"),
            _bullet_list(tests_to_run),
        ], xs=12, md=6, className="mb-2"),
        dbc.Col([
            html.Strong("Untested affected code", className="small"),
            _bullet_list(untested, empty="None"),
        ], xs=12, md=6, className="mb-2"),
    ], className="g-2 mt-1")

    # ── Layout: gauge left, metrics + bar + accuracy right ───────────────────
    right_cols: list = [metric_row]
    if tests_bar is not None:
        right_cols.append(tests_bar)
    if accuracy_card is not None:
        right_cols.append(accuracy_card)

    top_row = dbc.Row([
        dbc.Col(gauge, xs=12, md=3, className="d-flex align-items-center justify-content-center"),
        dbc.Col(right_cols, xs=12, md=9),
    ], className="g-3 align-items-start")

    return html.Div([
        top_row,
        lists_row,
    ], className="summary-strip mb-3")


# ── Migrate view ──────────────────────────────────────────────────────────────

# Catalog table column definitions
_CATALOG_COLUMNS = [
    {"name": "Title",         "id": "title"},
    {"name": "Kind",          "id": "kind"},
    {"name": "Guide section", "id": "guideSection"},
    {"name": "Occurrences",   "id": "occurrences"},
    {"name": "Replacement",   "id": "replacement"},
]

_CATALOG_STYLE_DATA_CONDITIONAL = [
    {"if": {"filter_query": '{kind} contains "api_removed"'},
     "backgroundColor": "#fdf0f0", "color": "#7b1d1d"},
    {"if": {"filter_query": '{kind} contains "api_changed"'},
     "backgroundColor": "#fefae8", "color": "#7b5900"},
    {"if": {"filter_query": '{kind} contains "behavior_changed"'},
     "backgroundColor": "#f0f4ff", "color": "#1e3a5f"},
    {"if": {"state": "selected"},
     "backgroundColor": "#dbeafe", "border": "1px solid #3b82d4"},
]

# Kind label map: adds a text label so colour is not the only signal
_KIND_LABELS = {
    "api_removed":     "🔴 api_removed",
    "api_changed":     "🟡 api_changed",
    "behavior_changed": "🔵 behavior_changed",
}

# Options for the kind filter dropdown (above the catalog table)
CATALOG_KIND_OPTIONS = [
    {"label": "All kinds",        "value": "all"},
    {"label": "api_removed",      "value": "api_removed"},
    {"label": "api_changed",      "value": "api_changed"},
    {"label": "behavior_changed", "value": "behavior_changed"},
]


def _catalog_table(catalog: list[dict]) -> dash_table.DataTable:
    """Build a sortable DataTable for the migration catalog entries.

    Rows are filtered externally via the ``catalog-kind-filter`` Dropdown
    callback.  The built-in Dash filter row is disabled; kind values are
    prefixed with a coloured label so colour is not the only signal.
    """
    rows = [
        {
            "title":        entry.get("title", ""),
            "kind":         _KIND_LABELS.get(entry.get("kind", ""), entry.get("kind", "")),
            "guideSection": entry.get("guideSection", ""),
            "occurrences":  entry.get("occurrences", 0),
            "replacement":  entry.get("replacement", ""),
        }
        for entry in catalog
    ]
    return dash_table.DataTable(
        id="catalog-table",
        columns=_CATALOG_COLUMNS,
        data=rows,
        sort_action="native",
        filter_action="none",
        style_table={"overflowX": "auto"},
        style_cell={
            "textAlign": "left",
            "fontSize": "14px",
            "padding": "10px 14px",
            "minHeight": "44px",
            "whiteSpace": "normal",
            "maxWidth": "260px",
            "lineHeight": "1.4",
        },
        style_cell_conditional=[
            {"if": {"column_id": "guideSection"}, "fontStyle": "italic"},
        ],
        style_header={
            "fontWeight": "bold",
            "backgroundColor": "#ffffff",
            "color": "#1d2330",
            "borderBottom": "2px solid #d0d4de",
            "position": "sticky",
            "top": 0,
        },
        style_data_conditional=_CATALOG_STYLE_DATA_CONDITIONAL,
        tooltip_data=[
            {
                "guideSection": {"value": row["guideSection"], "type": "markdown"},
                "replacement":  {"value": f"`{row['replacement']}`", "type": "markdown"},
            }
            for row in rows
        ],
        tooltip_delay=0,
        tooltip_duration=None,
    )


def _module_lane(mod: dict) -> dbc.Col:
    """Build a single worker-lane card for one entry in migration.modules."""
    worker   = mod.get("worker", "—")
    module   = mod.get("module", "—")
    files    = mod.get("filesChanged") or []
    fixes    = mod.get("fixesApplied", 0)
    tb       = mod.get("testsBefore") or {}
    ta       = mod.get("testsAfter")  or {}

    before_pass = tb.get("passed", 0)
    before_fail = tb.get("failed", 0)
    after_pass  = ta.get("passed", 0)
    after_fail  = ta.get("failed", 0)

    # Fixed-size inline before/after bar — height 140px so it stays inside the card
    _LANE_CHART_HEIGHT = 140
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Passed",
        x=["Before", "After"],
        y=[before_pass, after_pass],
        marker_color="#3fa66a",
        text=[str(before_pass) if before_pass > 0 else "",
              str(after_pass)  if after_pass  > 0 else ""],
        textposition="inside",
        textangle=0,
        insidetextanchor="middle",
        textfont={"color": "#ffffff", "size": 11},
    ))
    fig.add_trace(go.Bar(
        name="Failed",
        x=["Before", "After"],
        y=[before_fail, after_fail],
        marker_color="#d64545",
        text=[str(before_fail) if before_fail > 0 else "",
              str(after_fail)  if after_fail  > 0 else ""],
        textposition="inside",
        textangle=0,
        insidetextanchor="middle",
        textfont={"color": "#ffffff", "size": 11},
    ))
    # Lane charts sit on white cards — use dark font for readability
    fig.update_layout(**_chart_layout(
        on_light=True,
        barmode="stack",
        margin={"t": 10, "b": 30, "l": 10, "r": 10},
        height=_LANE_CHART_HEIGHT,
        showlegend=False,
        xaxis={
            "tickfont": {"color": _CHART_FONT_COLOR_LIGHT, "size": 10},
            "gridcolor": "rgba(0,0,0,0.08)",
            "linecolor": "rgba(0,0,0,0.15)",
        },
        yaxis={
            "tickfont": {"color": _CHART_FONT_COLOR_LIGHT, "size": 10},
            "gridcolor": "rgba(0,0,0,0.08)",
            "linecolor": "rgba(0,0,0,0.15)",
            "visible": False,
        },
        hoverlabel={
            "bgcolor": "#1c2540",
            "bordercolor": "#2a3555",
            "font": {"color": "#e6ebf5", "size": 12},
        },
    ))
    # Wrap graph in a fixed-height div so it never overflows the card
    bar = html.Div(
        dcc.Graph(
            figure=fig,
            config={"displayModeBar": False, "responsive": True},
            style={"height": f"{_LANE_CHART_HEIGHT}px", "width": "100%"},
        ),
        style={"height": f"{_LANE_CHART_HEIGHT}px", "overflow": "hidden"},
    )

    file_items = [html.Li(html.Code(f, className="small"), className="small") for f in files] or [html.Li("—")]

    card_body = dbc.CardBody(
        [
            html.Div(module.upper(), className="fw-bold small mb-1",
                     style={"color": "#1d2330", "letterSpacing": "0.05em"}),
            html.Dl([
                html.Dt("Worker", className="small"),
                html.Dd(html.Code(worker, className="small"),
                        style={"wordBreak": "break-all"}),
                html.Dt("Fixes applied", className="small"),
                html.Dd(str(fixes), className="small"),
            ], className="row-dl mb-1"),
            html.Div("Files changed:", className="small fw-semibold mb-0"),
            html.Ul(file_items, style={"paddingLeft": "1.2rem", "marginBottom": "0.4rem"}),
            html.Div(f"Tests: {before_pass + before_fail} → {after_pass + after_fail}",
                     className="small mb-1",
                     style={"color": "#1d2330"}),
            bar,
        ],
        style={"display": "flex", "flexDirection": "column"},
    )

    return dbc.Col(
        dbc.Card(
            card_body,
            className="h-100",
            style={
                "backgroundColor": "#ffffff",
                "border": "1px solid #e5e7eb",
                "overflow": "hidden",
            },
        ),
        xs=12, sm=6, md=3,
        className="mb-3",
    )


def migrate_view(report: dict) -> html.Div:
    """Build the full migrate-mode detail view.

    Sections (top to bottom):
    1. Summary strip (risk, metrics, tests bar).
    2. Dependency-change graph (changed symbol in centre, occurrences on ring 1).
    3. Catalog table — title, kind, guide section (italic), occurrences, replacement.
    4. Worker lanes — one dbc.Col per migration.modules entry, 4 on desktop.
    5. Release notes — dcc.Markdown from migration.releaseNotes.

    Args:
        report: Parsed report dict with ``mode == "migrate"``.

    Returns:
        A ``html.Div`` Dash component.
    """
    import graph as _graph  # local import to avoid circular at module level
    import dash_cytoscape as _cyto  # noqa: PLC0415

    migration     = report.get("migration") or {}
    catalog       = migration.get("catalog") or []
    modules       = migration.get("modules") or []
    release_notes = migration.get("releaseNotes") or ""

    # ── Repo conventions (F16) — top-level report field, optional ────────────
    conv_card = conventions_card(report.get("conventions"))
    conv_section = conv_card if conv_card is not None else html.Div()

    # ── 1. Graph ──────────────────────────────────────────────────────────────
    elements  = _graph.build_elements(report)
    stylesheet = _graph.build_stylesheet()
    cyto_graph = _cyto.Cytoscape(
        id="migrate-graph",
        elements=elements,
        stylesheet=stylesheet,
        layout={"name": "preset", "fit": True, "padding": 30},
        style={"width": "100%", "height": "100%"},
        minZoom=0.15,
        maxZoom=3.0,
    )

    # ── 2. Catalog section ────────────────────────────────────────────────────
    if catalog:
        kind_filter = dcc.Dropdown(
            id="catalog-kind-filter",
            options=CATALOG_KIND_OPTIONS,
            value="all",
            clearable=False,
            style={
                "width": "220px",
                "fontSize": "13px",
                "marginBottom": "8px",
                "color": "#1d2330",
            },
        )
        catalog_section = html.Div([
            html.H4("Migration catalog", className="mt-4 mb-2 section-heading",
                    style={"color": _CHART_FONT_COLOR}),
            html.P(
                "Use the dropdown to filter by kind. "
                "Guide-section cells show the verbatim quote from the migration guide.",
                className="small mb-2",
                style={"color": _CHART_FONT_COLOR},
            ),
            kind_filter,
            _catalog_table(catalog),
        ])
    else:
        catalog_section = html.P("No catalog entries.", className="text-dim small mt-3")

    # ── 3. Worker lanes ───────────────────────────────────────────────────────
    lanes = [_module_lane(m) for m in modules]
    if lanes:
        lanes_section = html.Div([
            html.H4("Worker lanes", className="mt-4 mb-1 section-heading",
                    style={"color": _CHART_FONT_COLOR}),
            html.P(
                "Each lane is an independent sandboxed Bob worker. They run in parallel.",
                className="small mb-2",
                style={"color": _CHART_FONT_COLOR},
            ),
            dbc.Row(lanes, className="g-3", style={"alignItems": "stretch"}),
        ], style={"marginBottom": "24px"})
    else:
        lanes_section = html.P("No worker lanes.", className="text-dim small mt-3")

    # ── 4. Release notes ──────────────────────────────────────────────────────
    if release_notes:
        rn_section = html.Div([
            html.H4("Release notes", className="mt-2 mb-2 section-heading",
                    style={"color": _CHART_FONT_COLOR}),
            dbc.Card(
                dbc.CardBody(
                    dcc.Markdown(release_notes, className="release-notes-md"),
                    style={"backgroundColor": "#ffffff", "padding": "16px"},
                ),
                style={"border": "1px solid #e5e7eb"},
            ),
        ])
    else:
        rn_section = html.Div()

    # ── 5. Graph container ────────────────────────────────────────────────────
    graph_section = html.Div(
        cyto_graph,
        style={
            "height": "420px",
            "marginBottom": "8px",
            "overflow": "hidden",
        },
    )

    return html.Div([
        graph_section,
        conv_section,
        catalog_section,
        lanes_section,
        rn_section,
    ])


def bob_panel(report: dict) -> dbc.Card:
    """'Powered by IBM Bob' panel: lists the Bob modes used (or all 9 when empty).

    Falls back to the full static list of 9 modes when ``provenance.bobModes``
    is absent or empty.  Each mode is shown with a one-line permission summary.
    A closing sentence names the four Bob features used.

    Args:
        report: Parsed report dict.

    Returns:
        A ``dbc.Card`` Dash component with a white background (dark text).
    """
    provenance = report.get("provenance") or {}
    bob_modes: list[str] = provenance.get("bobModes") or _STATIC_BOB_MODES

    mode_rows = []
    for mode in bob_modes:
        summary = _BOB_MODE_SUMMARIES.get(mode, "custom mode")
        mode_rows.append(
            html.Li([
                html.Code(mode, className="small",
                          style={"color": "#3b5bdb", "fontWeight": "600"}),
                html.Span(f" — {summary}", className="small",
                          style={"color": "#1d2330"}),
            ], style={"marginBottom": "4px"})
        )

    return dbc.Card([
        dbc.CardHeader(
            html.Strong("Powered by IBM Bob",
                        style={"color": "#1d2330"}),
            style={"backgroundColor": "#f7f8fa", "borderBottom": "1px solid #e5e7eb"},
        ),
        dbc.CardBody([
            html.Ul(mode_rows,
                    style={"paddingLeft": "1.2rem", "marginBottom": "0.75rem",
                           "listStyle": "disc"}),
            html.P(_BOB_FEATURES, className="small mb-0",
                   style={"color": "#57606a", "fontStyle": "italic"}),
        ], style={"backgroundColor": "#ffffff"}),
    ], style={"border": "1px solid #e5e7eb", "borderRadius": "6px"})
