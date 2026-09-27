"""Uplift dashboard prototype. `server` is what gunicorn serves: gunicorn app:server"""
from __future__ import annotations

import json
import base64

import dash
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
from dash import Input, Output, State, dcc, html

import graph
import loader
import panels
import comment as _comment_mod

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], title="Uplift",
                suppress_callback_exceptions=True, meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}])
server = app.server
REPORTS = loader.load_all()

app.index_string = """<!DOCTYPE html>
<html lang="en">
<head>
    {%metas%}
    <title>{%title%}</title>
<meta name="description" content="Know what a change will break. Prove it. Fix it.">
<meta property="og:title" content="Uplift: know what a change will break">
<meta property="og:description" content="Predict, prove and repair code changes with IBM Bob.">
<meta property="og:image" content="/assets/og.png">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    {%favicon%}
    {%css%}
  </head>
<body>
    {%app_entry%}
    <footer>{%config%}{%scripts%}{%renderer%}</footer>
</body>
</html>"""

# Accent colour for Loading spinner (matches --accent CSS token)
var_accent = "#4f6df5"

# ── risk-level colour token map ─────────────────────────────────────────────
# Bootstrap's semantic colour tokens (danger/warning/success) render as a
# different red/orange/green than the custom palette used everywhere else
# (the risk gauge, the graph, the filter chips), so the landing-page badge
# used to be visibly a different shade than the rest of the app. This map
# uses the exact same hexes as panels._RISK_GAUGE_COLOR / graph.VERDICT_COLORS
# so risk colour reads as one system across the whole surface.
RISK_COLOUR_HEX = {
    "high":    "#d64545",
    "medium":  "#e0a030",
    "low":     "#3fa66a",
    "unknown": "#8a8f98",
}

# ── how-it-works steps ──────────────────────────────────────────────────────
HOW_IT_WORKS = [
    ("1", "Predict",  "Build a code graph; Bob judges every affected place."),
    ("2", "Prove",    "Write a test that passes on base and fails on head."),
    ("3", "Repair",   "Sandboxed Bob workers fix each module in parallel."),
    ("4", "Verify",   "Re-run the suite; confirm zero regressions."),
]

# ── filter chip options ──────────────────────────────────────────────────────
FILTER_OPTIONS = [
    {"label": "will break", "value": "will_break"},
    {"label": "might break", "value": "might_break"},
    {"label": "safe", "value": "safe"},
    {"label": "unknown", "value": "unknown"},
    {"label": "untested only", "value": "untested"},
]
FILTER_DEFAULT = ["will_break", "might_break", "safe", "unknown"]

# ── legend definition ────────────────────────────────────────────────────────
# Colours here must match graph.py's actual node styles (build_stylesheet) —
# a legend teaching the wrong colour for a status is worse than no legend.
LEGEND_ITEMS = [
    ("★", "#3b5bdb", "Changed symbol"),
    ("▬", "#d64545", "Will break"),
    ("▬", "#e0a030", "Might break"),
    ("▬", "#3fa66a", "Safe"),
    ("▬", "#8a8f98", "Unknown"),
    ("⬡", "#ff9800", "Untested (dashed border)"),
    ("⬛", "#0d9488", "Docker layer impact"),
    ("✓", "#3fa66a", "Proof confirmed"),
    ("?", "#e0a030", "Proof unconfirmed"),
]


def metric_card(label: str, value) -> dbc.Col:
    return dbc.Col(dbc.Card(dbc.CardBody([html.Div(str(value), className="metric-value"),
                                          html.Div(label, className="metric-label")])), xs=6, md=3)


def stepper(pipeline: dict) -> html.Div:
    """Render pipeline steps with an accessible text label (never colour-only)."""
    steps = []
    for name in ("predict", "prove", "repair", "verify"):
        state = pipeline.get(name, "pending")
        # Accessible: icon + text label, aria-label carries full meaning
        icon = "✓" if state == "done" else "…"
        label = f"{name.title()} — {state}"
        steps.append(
            html.Span(
                [html.Span(icon, className="step-icon", **{"aria-hidden": "true"}),
                 html.Span(label, className="step-label")],
                className=f"step step-{state}",
                **{"aria-label": label, "role": "status"},
            )
        )
    return html.Div(steps, className="stepper", role="list")


def scenario_cards() -> dbc.Row:
    cards = []
    for sid, r in REPORTS.items():
        m = r.get("metrics", {})
        risk = r.get("risk", {})
        risk_level = risk.get("level", "unknown")
        risk_hex = RISK_COLOUR_HEX.get(risk_level, "#8a8f98")
        cards.append(
            dbc.Col(
                dbc.Card([
                    dbc.CardBody([
                        html.Div(
                            dbc.Badge(
                                risk_level.upper(),
                                className="risk-badge",
                                style={"backgroundColor": risk_hex, "color": "#ffffff"},
                            ),
                            className="d-flex justify-content-end mb-1",
                        ),
                        html.H5(r["scenario"]["title"], className="card-title"),
                        html.P(r["scenario"].get("description", ""), className="text-dim card-desc"),
                        # Four large headline figures
                        dbc.Row([
                            dbc.Col([html.Div(str(m.get("predicted", 0)),   className="fig-value"),
                                     html.Div("predicted",  className="fig-label")], xs=6, md=3),
                            dbc.Col([html.Div(str(m.get("confirmed", 0)),   className="fig-value"),
                                     html.Div("confirmed",  className="fig-label")], xs=6, md=3),
                            dbc.Col([html.Div(str(m.get("fixed", 0)),       className="fig-value"),
                                     html.Div("fixed",      className="fig-label")], xs=6, md=3),
                            dbc.Col([html.Div(str(m.get("regressions", 0)),
                                              className="fig-value fig-regressions" if m.get("regressions", 0) else "fig-value"),
                                     html.Div("regressions", className="fig-label")], xs=6, md=3),
                        ], className="g-2 my-2"),
                        dcc.Link("Open →", href=f"/?scenario={sid}", className="btn btn-primary btn-sm mt-1"),
                    ])
                ], className="scenario-card h-100"),
                xs=12, md=6,
            )
        )
    return dbc.Row(cards, className="g-4")


def how_it_works() -> html.Section:
    steps = []
    for num, title, desc in HOW_IT_WORKS:
        steps.append(
            dbc.Col(
                html.Div([
                    html.Div(num, className="hiw-num", **{"aria-hidden": "true"}),
                    html.Div([
                        html.Strong(title),
                        html.Span(f" — {desc}"),
                    ], className="hiw-text"),
                ], className="hiw-step"),
                xs=12, sm=6, md=3,
            )
        )
    return html.Section(
        [
            html.H2("How it works", className="hiw-heading"),
            dbc.Row(steps, className="g-3"),
        ],
        className="hiw-strip",
        **{"aria-label": "How Uplift works"},
    )


def graph_legend() -> html.Div:
    """A row of coloured chips explaining node shapes/colours."""
    chips = []
    for icon, color, label in LEGEND_ITEMS:
        chips.append(
            html.Span(
                [html.Span(icon, style={"color": color, "margin-right": "4px", "font-size": "1rem"}),
                 html.Span(label, style={"font-size": "0.78rem"})],
                className="legend-chip",
                title=label,
            )
        )
    return html.Div(chips, className="graph-legend", role="list", **{"aria-label": "Graph legend"})


def accessible_node_list(report: dict, hide: set[str] | None = None, untested_only: bool = False) -> html.Div:
    """Plain <ul> listing all visible nodes for screen readers and keyboard users."""
    hide = hide or set()
    items = []
    for c in report.get("changedSymbols", []):
        items.append(html.Li(f"[changed] {c['id']}", className="a11y-node"))
    for item in report.get("affected", []):
        if item["verdict"] in hide:
            continue
        if untested_only and item.get("tests"):
            continue
        proof_status = (item.get("proof") or {}).get("status", "")
        untested = " (untested)" if not item.get("tests") else ""
        proof_txt = f" — proof: {proof_status}" if proof_status else ""
        items.append(html.Li(
            f"[{item['verdict']}] {item['id']}{untested}{proof_txt}",
            className="a11y-node",
        ))
    if not untested_only:
        for contract in report.get("contracts") or []:
            if contract["verdict"] in hide:
                continue
            items.append(html.Li(f"[contract/{contract['verdict']}] {contract['id']}", className="a11y-node"))
        for infra in report.get("infraImpact") or []:
            items.append(html.Li(f"[docker] {infra['file']} — {infra.get('trigger', '')}", className="a11y-node"))
    return html.Div(
        [html.H4("Nodes (accessible list)", className="visually-hidden"),
         html.Ul(items, id="node-list", className="node-a11y-list")],
        **{"aria-label": "Accessible node list"},
    )


def _pr_comment_tab(r: dict) -> dbc.Tab:
    """Build the PR comment tab content."""
    comment_text = _comment_mod.pr_comment(r)
    return dbc.Tab(
        html.Div([
            html.Div([
                dcc.Clipboard(
                    target_id="pr-comment-md",
                    title="Copy comment",
                    className="copy-comment-btn",
                    style={"fontSize": "13px", "cursor": "pointer"},
                ),
                html.Span("📋 Copy comment", className="ms-1", style={"pointerEvents": "none", "fontSize": "13px", "color": "var(--text)"}),
            ], className="d-flex align-items-center gap-2 mb-1"),
            html.P(
                "This is the exact comment Uplift posts on the pull request.",
                className="pr-comment-caption",
            ),
            html.Div(
                dbc.Card(
                    dbc.CardBody(
                        dcc.Markdown(
                            comment_text,
                            id="pr-comment-md",
                            className="release-notes-md pr-md-content",
                        ),
                        style={"backgroundColor": "#ffffff", "padding": "16px"},
                    ),
                    className="pr-comment-card",
                    style={"border": "1px solid #e5e7eb"},
                ),
                className="pr-comment-scroll",
            ),
        ], className="mt-3"),
        label="PR comment",
        tab_id="tab-pr-comment",
    )


def _bob_tab(r: dict) -> dbc.Tab:
    """Build the 'Powered by IBM Bob' tab content."""
    return dbc.Tab(
        html.Div(panels.bob_panel(r), className="mt-3"),
        label="Powered by IBM Bob",
        tab_id="tab-bob",
    )


def detail_view(sid: str, uploaded_report: dict | None = None) -> html.Div:
    # Resolve the report: prefer the uploaded store, then built-in REPORTS
    if sid == "uploaded" and uploaded_report is not None:
        r = uploaded_report
    elif sid in REPORTS:
        r = REPORTS[sid]
    else:
        return home()

    if r.get("_errors"):
        return html.Div([dbc.Alert("This report does not match the schema:", color="danger"),
                         html.Ul([html.Li(e) for e in r["_errors"][:10]])])

    # ── Migrate mode: dedicated view ──────────────────────────────────────────
    if r.get("mode") == "migrate":
        migration = r.get("migration") or {}
        has_catalog = bool(migration.get("catalog"))
        main_content = html.Div([
            html.H3(r["scenario"]["title"]),
            stepper(r["pipeline"]),
            panels.summary_strip(r),
            panels.migrate_view(r),
            dcc.Store(id="sid", data=sid),
            dcc.Store(id="large-flag", data=False),
            # Stub components for callbacks that expect these ids regardless of mode
            html.Div(id="detail", style={"display": "none"}),
            html.Div(id="a11y-list", style={"display": "none"}),
            dcc.Checklist(id="filter-chips", options=[], value=[], style={"display": "none"}),
            # Stub for catalog filter when catalog is absent
            *([dcc.Dropdown(id="catalog-kind-filter", style={"display": "none"})]
              if not has_catalog else []),
        ])
        # Tabs: main view + PR comment + Bob panel
        return html.Div([
            dbc.Tabs([
                dbc.Tab(main_content, label="Overview", tab_id="tab-overview"),
                _pr_comment_tab(r),
                _bob_tab(r),
            ], id="detail-tabs", active_tab="tab-overview"),
        ])

    node_count = len(r.get("affected", [])) + len(r.get("changedSymbols", []))
    large = node_count > 60
    initial_elements = graph.build_elements(r, large=large)

    conv_card = panels.conventions_card(r.get("conventions"))

    main_content = html.Div([
        html.H3(r["scenario"]["title"]),
        stepper(r["pipeline"]),
        panels.summary_strip(r),
        *([conv_card] if conv_card is not None else []),

        # ── Filter chips ──────────────────────────────────────────────────────
        html.Div([
            html.Span("Filter: ", className="filter-label", **{"aria-hidden": "true"}),
            html.Div([
                dcc.Checklist(
                    id="filter-chips",
                    options=FILTER_OPTIONS,
                    value=FILTER_DEFAULT,
                    inline=True,
                    className="filter-checklist",
                    inputClassName="filter-chip-input",
                    labelClassName="filter-chip-label",
                ),
                html.P(
                    "Toggle a verdict to show or hide those nodes. "
                    "'Untested only' keeps just code that no test covers.",
                    className="filter-hint",
                ),
            ], className="filter-chips-wrap"),
        ], className="filter-row", role="group", **{"aria-label": "Filter nodes by verdict"}),

        dbc.Row([
            dbc.Col([
                # ── Fit button + Cytoscape graph ─────────────────────────────
                html.Div([
                    html.Button("Fit", id="fit-btn", className="btn btn-sm btn-outline-secondary fit-btn",
                                title="Reset zoom and pan to fit all nodes",
                                **{"aria-label": "Fit graph — reset zoom and pan to show all nodes"}),
                ], className="graph-toolbar"),
                html.Div(
                    dcc.Loading(
                        cyto.Cytoscape(
                            id="graph",
                            elements=initial_elements,
                            stylesheet=graph.build_stylesheet(large=large),
                            layout={"name": "preset", "fit": True, "padding": 30},
                            style={"width": "100%", "height": "520px"},
                            minZoom=0.15,
                            maxZoom=3.0,
                        ),
                        type="circle",
                        color=var_accent,
                    ),
                    **{"aria-label": "Change impact graph — click a node to see details",
                       "role": "img"},
                ),
                graph_legend(),
            ], md=8),
            dbc.Col(html.Div(id="detail", children="Click a node."), md=4),
        ]),

        # ── Affected items table ───────────────────────────────────────────────
        html.H4("Affected items", className="mt-4 mb-2"),
        panels.affected_table(r),

        # ── Accessible node list (below the graph) ────────────────────────────
        html.Details([
            html.Summary("Show accessible node list (screen reader / keyboard)"),
            html.Div(id="a11y-list"),
        ], className="a11y-details"),

        dcc.Store(id="sid", data=sid),
        dcc.Store(id="large-flag", data=large),
        # Stub — catalog filter only exists on migrate pages
        dcc.Dropdown(id="catalog-kind-filter", style={"display": "none"}),
    ])

    # Tabs: main view + PR comment + Bob panel
    return html.Div([
        dbc.Tabs([
            dbc.Tab(main_content, label="Overview", tab_id="tab-overview"),
            _pr_comment_tab(r),
            _bob_tab(r),
        ], id="detail-tabs", active_tab="tab-overview"),
    ])


def home() -> html.Div:
    return html.Div([
        # ── Hero ──────────────────────────────────────────────────────────────
        html.Section(
            [
                html.H1(
                    ["Know what a change will ",
                     html.Span("break", className="hero-emphasis"),
                     ". Prove it. Fix it."],
                    className="hero-h1",
                ),
                html.P(
                    "Uplift predicts what a change breaks, proves it with a failing test, "
                    "and repairs it with sandboxed IBM Bob workers.",
                    className="hero-sub",
                ),
                html.Div([
                    dcc.Link(
                        "Open the S1 demo",
                        href="/?scenario=s1-null-user",
                        className="btn-primary-cta",
                    ),
                    html.A(
                        "Read how it works",
                        href="#how-it-works",
                        className="btn-secondary-cta",
                    ),
                ], className="hero-cta"),
                # Proof teaser: the *actual* pipeline stepper component this
                # product renders on every scenario — not a decorative promise,
                # a real piece of the UI you're about to open.
                html.Div([
                    html.Div("This is the real pipeline every change goes through",
                             className="hero-proof-caption"),
                    stepper({"predict": "done", "prove": "done", "repair": "done", "verify": "done"}),
                ], className="hero-proof-teaser"),
            ],
            className="hero-section",
        ),
        # ── How it works strip ────────────────────────────────────────────────
        html.Section(
            how_it_works(),
            id="how-it-works",
        ),
        # ── Scenario cards ────────────────────────────────────────────────────
        html.H2("Scenarios", className="section-heading"),
        scenario_cards(),
        # ── Integrate strip ───────────────────────────────────────────────────
        html.Section([
            html.H2("Built for IBM Bob", className="integrate-heading"),
            html.P(
                "Uplift ships a native MCP server and CLI — Bob workers call it directly. "
                "No wrappers, no glue code.",
                className="integrate-sub",
            ),
            html.Div([
                html.Div([
                    html.Span("MCP Server", className="integrate-pill-label"),
                    html.Code("uplift mcp", className="integrate-code"),
                    html.P(
                        "Exposes uplift_graph, uplift_proof_run, uplift_migrate_scan, uplift_report "
                        "as MCP tools. Bob modes call them directly via .bob/mcp.json.",
                        className="integrate-pill-desc",
                    ),
                ], className="integrate-pill"),
                html.Div([
                    html.Span("CLI", className="integrate-pill-label"),
                    html.Code("uplift graph | proof-run | report | comment", className="integrate-code"),
                    html.P(
                        "Run the full pipeline from any terminal or CI step. "
                        "GitHub Action included — posts impact comment on every PR.",
                        className="integrate-pill-desc",
                    ),
                ], className="integrate-pill"),
                html.Div([
                    html.Span("Parallel Workers", className="integrate-pill-label"),
                    html.Code(".bob/custom_modes.yaml", className="integrate-code"),
                    html.P(
                        "Four sandboxed Bob repair workers (users, orders, payments, core) "
                        "run concurrently via uplift-worker-* modes with file-level edit restrictions.",
                        className="integrate-pill-desc",
                    ),
                ], className="integrate-pill"),
            ], className="integrate-grid"),
        ], className="integrate-section"),
    ])


# ── Layout ────────────────────────────────────────────────────────────────────
app.layout = dbc.Container([
    dcc.Location(id="url"),
    html.Div(id="page"),
    # ── Upload area ───────────────────────────────────────────────────────────
    html.Div(
        dcc.Upload(
            id="upload",
            children=html.Div([
                html.Span("Drop a report.json here or click to browse"),
            ]),
            className="upload",
        ),
        **{"aria-label": "Upload a report JSON file — drop here or click to browse",
           "role": "region"},
    ),
    # ── Paste JSON area ───────────────────────────────────────────────────────
    html.Div([
        dbc.Textarea(
            id="paste-json",
            placeholder="or paste report JSON here",
            rows=5,
            className="paste-json-textarea",
            style={
                "backgroundColor": "#1c2540",
                "color": "#e6ebf5",
                "border": "1px solid #3a4763",
                "borderRadius": "10px",
                "fontFamily": "ui-monospace, 'Cascadia Code', monospace",
                "fontSize": "14px",
                "minHeight": "140px",
                "resize": "vertical",
                "width": "100%",
            },
        ),
        html.Div([
            dbc.Button(
                "Validate",
                id="paste-validate-btn",
                className="btn-uplift-primary",
                style={
                    "backgroundColor": "#4f6df5",
                    "color": "#ffffff",
                    "border": "none",
                    "borderRadius": "8px",
                    "padding": "10px 20px",
                    "fontSize": "15px",
                    "fontWeight": "600",
                    "minHeight": "44px",
                    "cursor": "pointer",
                },
            ),
            html.Span(
                "Reports are validated in your browser session and never uploaded.",
                className="paste-helper-text",
                style={"fontSize": "12px", "color": "#9fb0cc", "fontStyle": "italic"},
            ),
        ], className="paste-action-row"),
    ], className="mt-2"),
    html.Div(id="upload-msg"),
    # ── In-memory store for uploaded/pasted reports ───────────────────────────
    dcc.Store(id="uploaded-report", storage_type="memory"),
], fluid=True, className="px-3 px-md-4")


# ── Routing ───────────────────────────────────────────────────────────────────

def _resolve_report(sid: str | None, uploaded: dict | None) -> dict | None:
    """Resolve a report by sid, including the "uploaded" pseudo-id.

    Every callback that needs "the current report" must go through this
    instead of indexing REPORTS directly — REPORTS never contains a key for
    the dropped/pasted report (it lives in the uploaded-report dcc.Store), so
    a bare ``REPORTS[sid]``/``sid in REPORTS`` silently breaks every
    interaction (filter, tap, row-click) on an uploaded report.
    """
    if sid == "uploaded":
        return uploaded
    return REPORTS.get(sid)


@app.callback(
    Output("page", "children"),
    Input("url", "search"),
    Input("uploaded-report", "data"),
)
def route(search, uploaded_data=None):
    sid = (search or "").split("scenario=")[-1] if "scenario=" in (search or "") else None
    if sid == "uploaded" and uploaded_data is not None:
        return detail_view("uploaded", uploaded_report=uploaded_data)
    if sid in REPORTS:
        return detail_view(sid)
    return home()


# ── Upload / paste callbacks ──────────────────────────────────────────────────

def _process_report_dict(report: dict):
    """Validate a report dict. Returns (store_data, msg_component, redirect_href)."""
    errors = loader.validate(report)
    if not errors:
        return report, dbc.Alert("Report loaded — rendering now…", color="success"), "/?scenario=uploaded"
    error_items = [html.Li(e) for e in errors[:5]]
    msg = html.Div([
        dbc.Alert("Report has schema errors:", color="danger",
                  style={"marginBottom": "4px"}),
        html.Ul(error_items, className="upload-error-list"),
    ])
    return None, msg, dash.no_update


@app.callback(
    Output("uploaded-report", "data"),
    Output("upload-msg", "children"),
    Output("url", "href"),
    Input("upload", "contents"),
    Input("paste-validate-btn", "n_clicks"),
    State("paste-json", "value"),
    prevent_initial_call=True,
)
def on_upload(contents, _n_clicks, paste_value):
    """Handle dropped file upload or pasted JSON validation."""
    from dash import ctx  # noqa: PLC0415
    triggered = ctx.triggered_id

    if triggered == "upload" and contents:
        try:
            raw = base64.b64decode(contents.split(",", 1)[1]).decode("utf-8")
            report = json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            return None, dbc.Alert(f"Not valid JSON: {exc}", color="danger"), dash.no_update
        store, msg, href = _process_report_dict(report)
        return store, msg, href

    if triggered == "paste-validate-btn":
        if not paste_value or not paste_value.strip():
            return None, dbc.Alert("Paste some JSON first.", color="warning"), dash.no_update
        try:
            report = json.loads(paste_value)
        except Exception as exc:  # noqa: BLE001
            return None, dbc.Alert(f"Not valid JSON: {exc}", color="danger"), dash.no_update
        store, msg, href = _process_report_dict(report)
        return store, msg, href

    return dash.no_update, dash.no_update, dash.no_update


@app.callback(
    Output("detail", "children"),
    Input("graph", "tapNodeData"),
    Input("affected-table", "selected_rows"),
    State("sid", "data"),
    State("uploaded-report", "data"),
)
def show_detail(node, selected_rows, sid, uploaded):
    """Show the detail panel when a graph node or a table row is clicked."""
    from dash import ctx  # noqa: PLC0415
    triggered = ctx.triggered_id if ctx.triggered_id else None

    r = _resolve_report(sid, uploaded) or {}

    # Table row click takes priority when that is the trigger
    if triggered == "affected-table" and selected_rows:
        row_index = selected_rows[0]
        affected = r.get("affected", [])
        if row_index >= len(affected):
            return "Click a node or table row."
        return panels.detail_panel(affected[row_index])

    # Graph node tap
    if node:
        infra = graph.find_infra_impact(r, node["id"])
        if infra:
            return panels.infra_panel(infra)
        item = graph.find_item(r, node["id"])
        if item:
            return panels.detail_panel(item)
        changed = graph.find_changed_symbol(r, node["id"])
        if changed:
            return panels.changed_symbol_panel(changed, r.get("change"))
        return "Changed symbol"

    return "Click a node or table row."


@app.callback(
    Output("graph", "elements"),
    Output("a11y-list", "children"),
    Input("filter-chips", "value"),
    Input("graph", "tapNodeData"),
    State("sid", "data"),
    State("large-flag", "data"),
    State("uploaded-report", "data"),
)
def update_graph(selected_filters, tapped_node, sid, large, uploaded):
    """Rebuild elements on filter change or node tap."""
    r = _resolve_report(sid, uploaded)
    if not r:
        return [], html.Ul()
    large = large or False

    # Determine which verdicts to hide from the filter chips, and whether the
    # "untested only" chip is on (it is not a verdict, so it is not part of
    # `hide` — it is a separate keep-only filter applied on top).
    selected = selected_filters or []
    hide = graph.filter_hide(selected)
    untested_only = "untested" in selected

    # Determine highlight path from tapped node
    highlight: set[str] = set()
    if tapped_node:
        highlight = set(graph.path_to_root(r, tapped_node["id"]))

    elements = graph.build_elements(r, hide=hide, highlight=highlight, large=large, untested_only=untested_only)
    a11y = accessible_node_list(r, hide=hide, untested_only=untested_only)
    return elements, a11y


@app.callback(
    Output("graph", "selectedNodeData"),
    Input("affected-table", "selected_rows"),
    State("sid", "data"),
    State("uploaded-report", "data"),
    prevent_initial_call=True,
)
def table_row_selects_node(selected_rows, sid, uploaded):
    """When a table row is clicked, select the matching node so the graph highlights it."""
    r = _resolve_report(sid, uploaded)
    if not r or not selected_rows:
        return []
    affected = r.get("affected", [])
    row_index = selected_rows[0]
    if row_index >= len(affected):
        return []
    return [{"id": affected[row_index]["id"]}]


@app.callback(
    Output("graph", "layout"),
    Input("fit-btn", "n_clicks"),
    prevent_initial_call=True,
)
def fit_graph(_n):
    """Reset zoom/pan by re-applying the preset layout with fit=True."""
    return {"name": "preset", "fit": True, "padding": 30}


@app.callback(
    Output("catalog-table", "data"),
    Input("catalog-kind-filter", "value"),
    State("sid", "data"),
    State("uploaded-report", "data"),
    prevent_initial_call=True,
)
def filter_catalog(kind_value, sid, uploaded):
    """Filter the catalog DataTable rows by kind when the dropdown changes."""
    r = _resolve_report(sid, uploaded)
    if not r:
        return []
    migration = r.get("migration") or {}
    catalog = migration.get("catalog") or []
    if not catalog or kind_value in (None, "all"):
        rows = catalog
    else:
        rows = [e for e in catalog if e.get("kind") == kind_value]
    return [
        {
            "title":        entry.get("title", ""),
            "kind":         panels._KIND_LABELS.get(entry.get("kind", ""), entry.get("kind", "")),
            "guideSection": entry.get("guideSection", ""),
            "occurrences":  entry.get("occurrences", 0),
            "replacement":  entry.get("replacement", ""),
        }
        for entry in rows
    ]


if __name__ == "__main__":
    app.run(debug=False)
