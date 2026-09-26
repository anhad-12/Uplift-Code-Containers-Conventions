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


def metric_card(label: str, value) -> dbc.Col:
    return dbc.Col(dbc.Card(dbc.CardBody([html.Div(str(value), className="metric-value"),
                                          html.Div(label, className="metric-label")])), xs=6, md=3)


def stepper(pipeline: dict) -> html.Div:
    steps = []
    for name in ("predict", "prove", "repair", "verify"):
        state = pipeline.get(name, "pending")
        steps.append(html.Span(f"{name.title()} ({state})", className=f"step step-{state}"))
    return html.Div(steps, className="stepper")


def scenario_cards() -> dbc.Row:
    cards = []
    for sid, r in REPORTS.items():
        m = r.get("metrics", {})
        cards.append(dbc.Col(dbc.Card(dbc.CardBody([
            html.H5(r["scenario"]["title"]),
            html.P(r["scenario"].get("description", ""), className="text-muted"),
            html.P(f"predicted {m.get('predicted', 0)} · confirmed {m.get('confirmed', 0)} · "
                   f"fixed {m.get('fixed', 0)} · regressions {m.get('regressions', 0)}"),
            dcc.Link("Open", href=f"/?scenario={sid}", className="btn btn-primary btn-sm"),
        ])), md=6))
    return dbc.Row(cards, className="g-3")


def detail_view(sid: str) -> html.Div:
    r = REPORTS[sid]
    if r.get("_errors"):
        return html.Div([dbc.Alert("This report does not match the schema:", color="danger"),
                         html.Ul([html.Li(e) for e in r["_errors"][:10]])])
    m, risk = r["metrics"], r["risk"]
    return html.Div([
        html.H3(r["scenario"]["title"]),
        stepper(r["pipeline"]),
        dbc.Row([metric_card("Risk score", f"{risk['score']} ({risk['level']})"),
                 metric_card("Predicted", m["predicted"]), metric_card("Confirmed", m["confirmed"]),
                 metric_card("Fixed", m.get("fixed", 0))], className="g-3 my-2"),
        dbc.Row([
            dbc.Col(cyto.Cytoscape(id="graph", elements=graph.build_elements(r), stylesheet=graph.build_stylesheet(),
                                   layout={"name": "preset", "fit": True, "padding": 30},
                                   style={"width": "100%", "height": "520px"}, minZoom=0.3, maxZoom=2.5), md=8),
            dbc.Col(html.Div(id="detail", children="Click a node."), md=4),
        ]),
        dcc.Store(id="sid", data=sid),
    ])


def home() -> html.Div:
    return html.Div([html.H1("Know what a change will break. Prove it. Fix it."), scenario_cards()])


app.layout = dbc.Container([dcc.Location(id="url"), html.Div(id="page"),
                            dcc.Upload(id="upload", children=html.Div("Drop a report.json here"),
                                       className="upload"), html.Div(id="upload-msg")], fluid=True)


@app.callback(Output("page", "children"), Input("url", "search"))
def route(search):
    sid = (search or "").split("scenario=")[-1] if "scenario=" in (search or "") else None
    return detail_view(sid) if sid in REPORTS else home()


@app.callback(Output("detail", "children"), Input("graph", "tapNodeData"), State("sid", "data"))
def show_detail(node, sid):
    if not node:
        return "Click a node."
    item = graph.find_item(REPORTS[sid], node["id"])
    if not item:
        return "Changed symbol"
    proof = item.get("proof") or {}
    return html.Div([
        html.H5(item["id"]),
        html.Pre(item.get("snippet", "")),
        html.P(f"Verdict: {item['verdict']}"), html.P(item.get("reason", "")),
        html.P(f"Fix: {item.get('fix', '')}"),
        html.P(f"Proof: {proof.get('status', 'n/a')}"),
    ])


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
