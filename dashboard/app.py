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
    {%favicon%}
    {%css%}
  </head>
<body>
    {%app_entry%}
    <footer>{%config%}{%scripts%}{%renderer%}</footer>
</body>
</html>"""

# ── risk-level colour token map (matches CSS variables) ────────────────────
RISK_COLOURS = {
    "high":    "danger",
    "medium":  "warning",
    "low":     "success",
    "unknown": "secondary",
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
LEGEND_ITEMS = [
    ("★", "#3b5bdb", "Changed symbol"),
    ("▬", "#d64545", "Will break"),
    ("▬", "#e0a030", "Might break"),
    ("▬", "#3fa66a", "Safe"),
    ("▬", "#8a8f98", "Unknown"),
    ("⬡", "#888", "Untested (dashed border)"),
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
        risk_colour = RISK_COLOURS.get(risk_level, "secondary")
        cards.append(
            dbc.Col(
                dbc.Card([
                    dbc.CardBody([
                        html.Div(
                            dbc.Badge(risk_level.upper(), color=risk_colour, className="risk-badge"),
                            className="d-flex justify-content-end mb-1",
                        ),
                        html.H5(r["scenario"]["title"], className="card-title"),
                        html.P(r["scenario"].get("description", ""), className="text-muted card-desc"),
                        # Four large headline figures
                        dbc.Row([
                            dbc.Col([html.Div(str(m.get("predicted", 0)),   className="fig-value"),
                                     html.Div("predicted",  className="fig-label")], xs=6, md=3),
                            dbc.Col([html.Div(str(m.get("confirmed", 0)),   className="fig-value"),
                                     html.Div("confirmed",  className="fig-label")], xs=6, md=3),
                            dbc.Col([html.Div(str(m.get("fixed", 0)),       className="fig-value"),
                                     html.Div("fixed",      className="fig-label")], xs=6, md=3),
                            dbc.Col([html.Div(str(m.get("regressions", 0)), className="fig-value fig-regressions"),
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


def accessible_node_list(report: dict, hide: set[str] | None = None) -> html.Div:
    """Plain <ul> listing all visible nodes for screen readers and keyboard users."""
    hide = hide or set()
    items = []
    for c in report.get("changedSymbols", []):
        items.append(html.Li(f"[changed] {c['id']}", className="a11y-node"))
    for item in report.get("affected", []):
        if item["verdict"] in hide:
            continue
        proof_status = (item.get("proof") or {}).get("status", "")
        untested = " (untested)" if not item.get("tests") else ""
        proof_txt = f" — proof: {proof_status}" if proof_status else ""
        items.append(html.Li(
            f"[{item['verdict']}] {item['id']}{untested}{proof_txt}",
            className="a11y-node",
        ))
    for contract in report.get("contracts") or []:
        if contract["verdict"] in hide:
            continue
        items.append(html.Li(f"[contract/{contract['verdict']}] {contract['id']}", className="a11y-node"))
    return html.Div(
        [html.H4("Nodes (accessible list)", className="visually-hidden"),
         html.Ul(items, id="node-list", className="node-a11y-list")],
        **{"aria-label": "Accessible node list"},
    )


def detail_view(sid: str) -> html.Div:
    r = REPORTS[sid]
    if r.get("_errors"):
        return html.Div([dbc.Alert("This report does not match the schema:", color="danger"),
                         html.Ul([html.Li(e) for e in r["_errors"][:10]])])
    m, risk = r["metrics"], r["risk"]
    node_count = len(r.get("affected", [])) + len(r.get("changedSymbols", []))
    large = node_count > 60
    initial_elements = graph.build_elements(r, large=large)

    return html.Div([
        html.H3(r["scenario"]["title"]),
        stepper(r["pipeline"]),
        dbc.Row([metric_card("Risk score", f"{risk['score']} ({risk['level']})"),
                 metric_card("Predicted", m["predicted"]), metric_card("Confirmed", m["confirmed"]),
                 metric_card("Fixed", m.get("fixed", 0))], className="g-3 my-2"),

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
                                title="Reset zoom and pan to fit all nodes"),
                ], className="graph-toolbar"),
                cyto.Cytoscape(
                    id="graph",
                    elements=initial_elements,
                    stylesheet=graph.build_stylesheet(large=large),
                    layout={"name": "preset", "fit": True, "padding": 30},
                    style={"width": "100%", "height": "520px"},
                    minZoom=0.15,
                    maxZoom=3.0,
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
    ])


def home() -> html.Div:
    return html.Div([
        # ── Hero ──────────────────────────────────────────────────────────────
        html.Section(
            [
                html.H1("Know what a change will break. Prove it. Fix it.", className="hero-h1"),
                html.P(
                    "Uplift predicts what a change breaks, proves it with a failing test, "
                    "and repairs it with sandboxed IBM Bob workers.",
                    className="hero-sub",
                ),
            ],
            className="hero-section",
        ),
        # ── How it works strip ────────────────────────────────────────────────
        how_it_works(),
        # ── Scenario cards ────────────────────────────────────────────────────
        html.H2("Scenarios", className="section-heading"),
        scenario_cards(),
    ])


app.layout = dbc.Container([dcc.Location(id="url"), html.Div(id="page"),
                            dcc.Upload(id="upload", children=html.Div("Drop a report.json here"),
                                       className="upload"), html.Div(id="upload-msg")], fluid=True,
                           className="px-3 px-md-4")


@app.callback(Output("page", "children"), Input("url", "search"))
def route(search):
    sid = (search or "").split("scenario=")[-1] if "scenario=" in (search or "") else None
    return detail_view(sid) if sid in REPORTS else home()


@app.callback(
    Output("detail", "children"),
    Input("graph", "tapNodeData"),
    Input("affected-table", "selected_rows"),
    State("sid", "data"),
)
def show_detail(node, selected_rows, sid):
    """Show the detail panel when a graph node or a table row is clicked."""
    from dash import ctx  # noqa: PLC0415
    triggered = ctx.triggered_id if ctx.triggered_id else None

    r = REPORTS[sid]

    # Table row click takes priority when that is the trigger
    if triggered == "affected-table" and selected_rows:
        row_index = selected_rows[0]
        item = r["affected"][row_index]
        return panels.detail_panel(item)

    # Graph node tap
    if node:
        item = graph.find_item(r, node["id"])
        if not item:
            return "Changed symbol"
        return panels.detail_panel(item)

    return "Click a node or table row."


@app.callback(
    Output("graph", "elements"),
    Output("a11y-list", "children"),
    Input("filter-chips", "value"),
    Input("graph", "tapNodeData"),
    State("sid", "data"),
    State("large-flag", "data"),
)
def update_graph(selected_filters, tapped_node, sid, large):
    """Rebuild elements on filter change or node tap."""
    if sid not in REPORTS:
        return [], html.Ul()
    r = REPORTS[sid]
    large = large or False

    # Determine which verdicts to hide from the filter chips
    selected = selected_filters or []
    hide = graph.filter_hide(selected)

    # Determine highlight path from tapped node
    highlight: set[str] = set()
    if tapped_node:
        highlight = set(graph.path_to_root(r, tapped_node["id"]))

    elements = graph.build_elements(r, hide=hide, highlight=highlight, large=large)
    a11y = accessible_node_list(r, hide=hide)
    return elements, a11y


@app.callback(
    Output("graph", "selectedNodeData"),
    Input("affected-table", "selected_rows"),
    State("sid", "data"),
    prevent_initial_call=True,
)
def table_row_selects_node(selected_rows, sid):
    """When a table row is clicked, return the node id so the graph highlights it."""
    # Cytoscape does not accept a direct "select by id" callback output, but
    # returning tapNodeData-compatible data keeps the highlight in sync via
    # the update_graph callback which listens to tapNodeData.
    # We update the graph elements via a separate approach: returning an empty
    # list clears selection; we rely on the existing tapNodeData flow for graph
    # highlighting (the table row still shows the panel via show_detail above).
    return []


@app.callback(
    Output("graph", "layout"),
    Input("fit-btn", "n_clicks"),
    prevent_initial_call=True,
)
def fit_graph(_n):
    """Reset zoom/pan by re-applying the preset layout with fit=True."""
    return {"name": "preset", "fit": True, "padding": 30}


@app.callback(Output("upload-msg", "children"), Input("upload", "contents"))
def on_upload(contents):
    if not contents:
        return ""
    try:
        report = json.loads(base64.b64decode(contents.split(",", 1)[1]).decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return dbc.Alert(f"Not valid JSON: {exc}", color="danger")
    errors = loader.validate(report)
    return dbc.Alert("Report is valid" if not errors else "; ".join(errors[:3]), color="success" if not errors else "danger")


if __name__ == "__main__":
    app.run(debug=False)
