# Member C: Face (dashboard, live URL, README, statements)

You own what voters and judges see first. The dashboard is a **Python Dash app** with `dash-cytoscape` for the graph. Build against `schema/examples/*.mock.json` from minute one and never wait for A or B. Mocks are labelled `generatedBy: "mock"`; before submission every mock must be replaced by real reports (`python scripts/verify.py` fails otherwise).
Screenshot the task summary after every task (PLAN.md section 11). Log it in `bob_sessions/LOG.md`. You work on `main`, in `dashboard/` only.

## How to use these prompts

- Paste the whole boxed prompt into a **new Bob task**, Agent mode. Every prompt has tested reference code and a **Done when** command. Do not accept "done" without the command output; if something fails, paste the failure into the same task and ask Bob to fix it.
- The reference code was **run and tested**: the app serves, both mock reports validate against the real schema with `jsonschema`, and 5 pytest tests pass. Bob should adapt it, not invent from scratch.
- **Coin figures are guesses.** After your first task check Settings > General and recalibrate.
- Do not fix core code by hand or with another tool; ask Bob.

## Environment (by hand, 5 minutes)

Python 3.11 or 3.12. `python -m venv dashboard/.venv`, then `dashboard/.venv/Scripts/python -m pip install -r dashboard/requirements.txt`. Set `PYTHONUTF8=1`.

## Two design rules learned from testing

1. **The dashboard must be self-contained.** Render deploys only the `dashboard/` folder (root directory), so the app cannot read `../schema`. Keep a committed **copy** of the schema at `dashboard/schema/report.schema.json` (`scripts/verify.py` checks that it equals `schema/report.schema.json`; re-copy when the schema changes).
2. **Graph positions are computed in Python** (preset layout, rings by hop). Cytoscape's concentric layout needs JavaScript callbacks, which Dash cannot pass. The tested `graph.py` does this.

---

## C1. Scaffold, loader, graph builder and tests  (about 3 coins, DO FIRST)

````text
Read PLAN.md and schema/report.schema.json first.

GOAL: create dashboard/, a Dash app that loads validated reports and draws the blast-radius graph. Use the tested reference code below EXACTLY as the starting point.

FILES:
- dashboard/requirements.txt (exact):
dash==4.4.1
dash-bootstrap-components==2.0.4
dash-cytoscape==1.0.2
jsonschema==4.26.0
gunicorn==26.2.0
pytest==8.3.3

- dashboard/schema/report.schema.json: a COPY of schema/report.schema.json (byte-identical).
- dashboard/loader.py, dashboard/graph.py, dashboard/app.py, dashboard/assets/style.css, dashboard/tests/test_graph_and_loader.py: from the reference code below.
- dashboard/reports/impact-s1.mock.json and dashboard/reports/migrate-pydantic2.mock.json: copies of schema/examples/*.mock.json.
- dashboard/reports/index.json (exact):
[
  {"id": "s1-null-user", "title": "get_user returns None instead of raising", "file": "impact-s1.mock.json"},
  {"id": "s3-pydantic2", "title": "Upgrade Pydantic v1 to v2", "file": "migrate-pydantic2.mock.json"}
]
- dashboard/README.md: how to create the venv, run (`python app.py`), test (`python -m pytest -q`), and deploy (filled in at C8).
- dashboard/assets/og.png: a 1200x630 placeholder image (generate it with Pillow if installed, or a plain colored PNG) so the Open Graph tag resolves; C8 replaces it.

STEPS: create the venv and install; create the files; run `cd dashboard && .venv/Scripts/python -m pytest -q` (expect 5 passed); run `.venv/Scripts/python app.py` and open http://127.0.0.1:8050: the home page lists two scenario cards; clicking one shows the risk/metric cards, the stepper, and a graph with a star in the middle and coloured nodes on rings; clicking a node fills the right-hand panel.

DONE WHEN: 5 tests pass; the app starts; both scenarios open; the graph renders (screenshot it).
Commit: [bob C1] dashboard scaffold, loader and graph

REFERENCE CODE:

**dashboard/loader.py**
```python
"""Load and validate reports. Keep this module free of Dash imports so it can be unit-tested."""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft7Validator

HERE = Path(__file__).parent
REPORTS = HERE / "reports"
SCHEMA_PATH = HERE / "schema" / "report.schema.json"  # a committed COPY: Render deploys only the dashboard/ folder


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate(report: dict) -> list[str]:
    """Return human-readable schema errors (empty list = valid)."""
    validator = Draft7Validator(load_schema())
    return [f"{'/'.join(map(str, e.absolute_path)) or 'report'}: {e.message}" for e in validator.iter_errors(report)]


def load_index() -> list[dict]:
    return json.loads((REPORTS / "index.json").read_text(encoding="utf-8"))


def load_report(file_name: str) -> dict:
    return json.loads((REPORTS / file_name).read_text(encoding="utf-8"))


def load_all() -> dict[str, dict]:
    """scenario id -> report; invalid reports are kept with an '_errors' key so the UI can show them."""
    out: dict[str, dict] = {}
    for entry in load_index():
        report = load_report(entry["file"])
        errors = validate(report)
        if errors:
            report = {**report, "_errors": errors}
        out[entry["id"]] = report
    return out
```

**dashboard/graph.py**
```python
"""Turn a report into dash-cytoscape elements + stylesheet. Pure functions, no Dash imports."""
from __future__ import annotations

import math

VERDICT_COLORS = {"will_break": "#d64545", "might_break": "#e0a030", "safe": "#3fa66a", "unknown": "#8a8f98"}
PROOF_MARK = {"confirmed": "✓", "unconfirmed": "?", "not_attempted": "", "not_applicable": ""}


def _label(item: dict) -> str:
    name = item["id"].split("#")[-1]
    mark = PROOF_MARK.get((item.get("proof") or {}).get("status", ""), "")
    return f"{name} {mark}".strip()


def build_elements(report: dict, hide: set[str] | None = None) -> list[dict]:
    """Nodes on rings by hop (preset positions), edges from `via` to the item."""
    hide = hide or set()
    elements: list[dict] = []
    changed = report["changedSymbols"]
    for i, c in enumerate(changed):
        elements.append({"data": {"id": c["id"], "label": c["id"].split("#")[-1], "kind": "changed"},
                         "position": {"x": 0, "y": i * 80}, "classes": "changed"})
    by_hop: dict[int, list[dict]] = {}
    for item in report["affected"]:
        if item["verdict"] in hide:
            continue
        by_hop.setdefault(item["hop"], []).append(item)
    known = {c["id"] for c in changed}
    for hop, items in sorted(by_hop.items()):
        radius = 170 * hop
        for i, item in enumerate(items):
            angle = 2 * math.pi * i / max(len(items), 1) + hop * 0.4
            classes = [item["verdict"]]
            if not item.get("tests"):
                classes.append("untested")
            elements.append({
                "data": {"id": item["id"], "label": _label(item), "verdict": item["verdict"], "kind": "affected"},
                "position": {"x": radius * math.cos(angle), "y": radius * math.sin(angle)},
                "classes": " ".join(classes),
            })
            known.add(item["id"])
    for item in report["affected"]:
        if item["verdict"] in hide or not item.get("via") or item["via"] not in known:
            continue
        elements.append({"data": {"source": item["via"], "target": item["id"]}})
    for j, contract in enumerate(report.get("contracts") or []):
        cid = f"contract:{contract['id']}"
        elements.append({"data": {"id": cid, "label": contract["id"], "verdict": contract["verdict"], "kind": "contract"},
                         "position": {"x": 170 * 3.4, "y": (j - 0.5) * 90}, "classes": f"contract {contract['verdict']}"})
        handler = contract.get("handler", "")
        source = next((a["id"] for a in report["affected"] if a["id"].split("#")[0] == handler.split("#")[0]), None)
        if source:
            elements.append({"data": {"source": source, "target": cid}})
    return elements


def build_stylesheet() -> list[dict]:
    sheet = [
        {"selector": "node", "style": {"label": "data(label)", "font-size": 11, "text-valign": "bottom",
                                       "text-margin-y": 4, "width": 26, "height": 26, "color": "#222"}},
        {"selector": ".changed", "style": {"background-color": "#3b5bdb", "shape": "star", "width": 44, "height": 44}},
        {"selector": ".contract", "style": {"shape": "round-rectangle", "width": 40, "height": 26}},
        {"selector": ".untested", "style": {"border-width": 3, "border-style": "dashed", "border-color": "#222"}},
        {"selector": "edge", "style": {"width": 1.5, "line-color": "#b8bcc4", "target-arrow-shape": "triangle",
                                       "target-arrow-color": "#b8bcc4", "curve-style": "bezier"}},
        {"selector": ":selected", "style": {"border-width": 4, "border-color": "#111"}},
    ]
    for verdict, color in VERDICT_COLORS.items():
        sheet.append({"selector": f".{verdict}", "style": {"background-color": color}})
    return sheet


def find_item(report: dict, node_id: str) -> dict | None:
    if node_id.startswith("contract:"):
        return next((c for c in report.get("contracts") or [] if f"contract:{c['id']}" == node_id), None)
    return next((a for a in report["affected"] if a["id"] == node_id), None)
```

**dashboard/app.py**
```python
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
```

**dashboard/assets/style.css**
```css
:root { --bg: #ffffff; --fg: #1d2330; --muted: #5d6675; --card: #f5f7fb; --accent: #3b5bdb;
        --will: #d64545; --might: #e0a030; --safe: #3fa66a; --unknown: #8a8f98; --radius: 12px; }
@media (prefers-color-scheme: dark) { :root { --bg: #11151c; --fg: #e8ecf3; --muted: #9aa4b5; --card: #1a202b; } }
body { background: var(--bg); color: var(--fg); }
.metric-value { font-size: 2rem; font-weight: 700; }
.metric-label { color: var(--muted); }
.stepper { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0; }
.step { padding: 6px 12px; border-radius: 999px; background: var(--card); }
.step-done { background: var(--safe); color: #fff; }
.step-pending { opacity: .6; }
.upload { border: 2px dashed var(--muted); border-radius: var(--radius); padding: 16px; text-align: center; margin: 24px 0; }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
```

**dashboard/tests/test_graph_and_loader.py**
```python
import json
from pathlib import Path

import graph
import loader

REPORTS = Path(__file__).resolve().parent.parent / "reports"


def report(name: str) -> dict:
    return json.loads((REPORTS / name).read_text(encoding="utf-8"))


def test_mock_reports_match_schema():
    for path in REPORTS.glob("*.mock.json"):
        assert loader.validate(json.loads(path.read_text(encoding="utf-8"))) == [], path.name


def test_invalid_report_reports_errors():
    assert len(loader.validate({"schemaVersion": 1})) > 0


def test_elements_have_changed_symbol_ring_positions_and_edges():
    els = graph.build_elements(report("impact-s1.mock.json"))
    nodes = [e for e in els if "source" not in e["data"]]
    edges = [e for e in els if "source" in e["data"]]
    assert any(n["classes"] == "changed" for n in nodes)
    assert len(edges) >= 5
    hop1 = [n for n in nodes if n["data"].get("verdict") and abs((n["position"]["x"] ** 2 + n["position"]["y"] ** 2) ** 0.5 - 170) < 1]
    assert hop1, "hop 1 nodes sit on the first ring"


def test_filter_hides_verdicts():
    r = report("impact-s1.mock.json")
    all_nodes = [e for e in graph.build_elements(r) if "source" not in e["data"]]
    no_safe = [e for e in graph.build_elements(r, hide={"safe"}) if "source" not in e["data"]]
    assert len(no_safe) == len(all_nodes) - 1


def test_untested_class_and_find_item():
    r = report("impact-s1.mock.json")
    els = {e["data"]["id"]: e for e in graph.build_elements(r) if "source" not in e["data"]}
    assert "untested" in els["shop/admin/reports.py#user_spend_report"]["classes"]
    assert graph.find_item(r, "shop/orders/invoice.py#build_invoice")["verdict"] == "will_break"
    assert graph.find_item(r, "contract:GET /users/{user_id}")["verdict"] == "will_break"
```
````


---

## C2. Landing page, scenario cards and pipeline stepper  (about 3 coins)

````text
Read PLAN.md. In dashboard/app.py improve the first screen (this is what voters see in 5 seconds, make it excellent) while keeping the tested structure (home(), scenario_cards(), stepper()):
- Hero: H1 "Know what a change will break. Prove it. Fix it." and a one-line subtitle: "Uplift predicts what a change breaks, proves it with a failing test, and repairs it with sandboxed IBM Bob workers."
- Scenario cards: title, one-line description, and the headline numbers "predicted N, confirmed N, fixed N, regressions N" as four large figures, plus the risk badge (level colour from the tokens in style.css) and an "Open" button.
- A "How it works" strip with the four steps Predict, Prove, Repair, Verify (icon or number, one line each) directly under the hero.
- The stepper on the detail page shows each step as done/pending with an accessible text label (never colour only).
Use dash-bootstrap-components (dbc) for the grid: cards in 1 column on a 375px phone, 2 columns on desktop; 16px gutters; no horizontal scroll at 375px.
Add tests in dashboard/tests/test_app.py: `app.server.test_client().get("/")` returns 200; `app.route("")` returns the home layout; `app.route("?scenario=s1-null-user")` returns the detail layout; an unknown scenario id falls back to home.
DONE WHEN: `python -m pytest -q` passes; on a 375px wide browser window the page has no horizontal scrollbar (screenshot).
Commit: [bob C2] landing and stepper
````


---

## C3. Blast radius graph: filters, hover path, legend  (about 4 coins, the centerpiece)

````text
Read PLAN.md. Extend the graph view (dashboard/graph.py, dashboard/app.py). Keep build_elements and build_stylesheet tested; add:
1. Filter chips above the graph (dcc.Checklist, inline): will_break, might_break, safe, unknown, and "untested only". A callback on the checklist rebuilds `elements` with `graph.build_elements(report, hide=<unchecked verdicts>)`. Add a pure function `filter_hide(selected: list[str]) -> set[str]` in graph.py with a unit test.
2. Hover/tap highlight: on tapNodeData, add class "highlight" to the tapped node, its ancestors along `via` (the path back to the changed symbol) and the connecting edges, by returning updated `elements` with classes; add matching stylesheet rules (thicker edge, dark border). Pure function `path_to_root(report, node_id) -> list[str]` in graph.py with a unit test.
3. A legend: a row of coloured chips with text and shape (star = changed symbol, rounded rectangle = API route contract, dashed border = untested code, check mark = proof confirmed, question mark = proof unconfirmed).
4. A "Fit" button (cyto.Cytoscape `zoom`/`pan` reset via the `layout` prop update with fit true), min/max zoom, and a plain accessible list of the same nodes below the graph (a `<ul>` with verdict text) for screen readers and keyboard users.
5. Handle up to 200 nodes: if there are more than 60 nodes, render labels only for will_break nodes and on hover (stylesheet rule).
DONE WHEN: `python -m pytest -q` passes (including the two new unit tests); toggling "safe" removes the green nodes; tapping a node highlights its path (screenshot).
Commit: [bob C3] graph filters and highlight
````


---

## C4. Detail panel and sortable table  (about 3 coins)

````text
Read PLAN.md. Build the right-hand detail panel as a function `detail_panel(item: dict) -> Component` in dashboard/panels.py (the callback in app.py calls it), showing for the selected item:
- id, file:line, module, hop, layer
- the code snippet in a `dcc.Markdown` fenced ```python block (the item's `snippet`)
- a verdict badge (dbc.Badge with text and icon), the reason, the suggested fix
- Proof: status, the test file name, and two rows "passes on base: yes/no" and "fails on head: yes/no" with a tick or cross AND the words yes/no
- Repair: status, the worker mode name, files changed (as a list)
- For contracts (ids starting with contract:): route, handler and the same verdict, reason, proof.
Below the graph add a `dash_table.DataTable` with all affected items: columns id, module, hop, layer, verdict, proof, repair; native sorting; row click selects the same node in the graph; conditional styling by verdict.
Tests in dashboard/tests/test_panels.py: detail_panel returns a component for an affected item, for a contract and for an item without a proof; the table rows count equals len(report["affected"]).
DONE WHEN: pytest passes; clicking a table row and a graph node shows the same panel (screenshot).
Commit: [bob C4] detail panel and table
````


---

## C5. Summary cards and honest accuracy  (about 3 coins)

````text
Read PLAN.md. Build `summary_strip(report) -> Component` in dashboard/panels.py, shown at the top of the detail page:
- Risk: a gauge 0 to 100 (plotly `go.Indicator` gauge, or a styled progress bar) with the level, plus a tooltip listing report.risk.factors and the formula from the schema ("score = min(100, 10*willBreak + 4*mightBreak + 12*untested + 15*contractHits)").
- Metric cards: predicted, confirmed, fixed, regressions (large figures).
- Tests before/after: a stacked bar (passed/failed) from metrics.tests, omitted if absent.
- Accuracy card from metrics.accuracy: precision and recall as percentages, true positives, false positives and false negatives as counts, and a "See what we missed" button that opens a dbc.Modal rendering dashboard/reports/eval.md (dcc.Markdown) if the file exists. Show misses plainly; honesty is a feature. If accuracy is absent (mock or migrate), show nothing.
- Two lists: "Tests to run" and "Untested affected code".
Add plotly to dashboard/requirements.txt only if you use it (pin the version you installed and tested).
Tests: summary_strip on the S1 mock contains the text "71"; on a report without accuracy it has no accuracy card.
DONE WHEN: pytest passes; the S1 page shows risk 71 (high), 5 predicted, 4 confirmed, 4 fixed, 0 regressions (screenshot).
Commit: [bob C5] summary and accuracy cards
````


---

## C6. Migrate view  (about 4 coins)

````text
Read PLAN.md. For reports with `mode == "migrate"` build `migrate_view(report)` in dashboard/panels.py and use it from detail_view:
- Catalog table (`dash_table.DataTable`): title, kind, guide section (verbatim quote, italic), occurrences, replacement; filter by kind.
- Worker lanes, side by side (dbc.Row with one dbc.Col per entry in migration.modules, 4 columns on desktop, stacked on phones): worker mode name, module, files changed, fixes applied, tests before -> after with a small before/after bar. The point is that the lanes are parallel and independent.
- Release notes rendered from migration.releaseNotes with dcc.Markdown.
- The same summary strip (C5) on top and the graph below (dependency changes have one changed-symbol node in the centre; occurrences are on ring 1).
Tests: migrate_view on schema/examples/migrate-pydantic2.mock.json returns a component with 4 lane columns and a table with 4 rows.
DONE WHEN: pytest passes; the Pydantic scenario shows the catalog, four lanes and the release notes (screenshot).
Commit: [bob C6] migrate view
````


---

## C7. Drop your own report, PR comment preview, Bob panel  (about 3 coins)

````text
Read PLAN.md. Add three features.
1. Upload or paste: the tested `on_upload` callback already reads a dropped JSON file. Extend it: on a valid report render it exactly like a built-in scenario (store it in a `dcc.Store(storage_type="memory")` and route to it as `?scenario=uploaded`); on an invalid report show the first 5 schema errors as a list. Also add a "paste JSON" textarea with a Validate button. Never upload anywhere; never write to disk on the server.
2. A "PR comment" tab (dbc.Tabs on the detail page): render `pr_comment(report)` from dashboard/comment.py (copy of the tested function below) with dcc.Markdown, plus a copy-to-clipboard button (dcc.Clipboard).
3. A "Powered by IBM Bob" panel: list report.provenance.bobModes (fall back to a static list of the 9 modes when empty) each with a one-line permission summary: uplift-impact-analyst "judges impact, cannot edit code", uplift-prover "writes proof tests only", uplift-migration-planner "reads the migration guide", uplift-worker-<module> "can edit only its own module", uplift-verifier "re-runs tests and writes reports", uplift-convention-scanner "learns the repo's style". Add a sentence naming the four Bob features used: Agent mode, parallel tasks, subagents, document understanding.
Tests: comment.py output on the S1 mock contains "Risk 71/100 (high)"; the Bob panel lists 9 modes when provenance.bobModes is empty.
DONE WHEN: pytest passes; dropping schema/examples/impact-s1.mock.json renders it; dropping a broken JSON shows errors (screenshot both).
Commit: [bob C7] drop report, PR preview, bob panel

REFERENCE (tested in the engine; copy into dashboard/comment.py):

```python
from __future__ import annotations

BADGE = {"low": "green", "medium": "yellow", "high": "orange", "critical": "red"}


def pr_comment(report: dict) -> str:
    r, m = report["risk"], report["metrics"]
    lines = [f"### Uplift: blast radius for `{report['scenario']['title']}`", "",
             f"**Risk {r['score']}/100 ({r['level']})** - {'; '.join(r.get('factors', []))}", ""]
    has_verdicts = any(a["verdict"] != "unknown" for a in report["affected"])
    if not has_verdicts:
        lines += ["_Graph only. Verdicts, proofs and repairs come from a Bob run._", ""]
    lines += ["| Item | Verdict | Proof | Reason |", "| --- | --- | --- | --- |"]
    for a in sorted(report["affected"], key=lambda a: ["will_break", "might_break", "unknown", "safe"].index(a["verdict"])):
        lines.append(f"| `{a['id']}` | {a['verdict']} | {(a.get('proof') or {}).get('status', '-')} | {a.get('reason', '')} |")
    if report.get("contracts"):
        lines += ["", "**API contracts:** " + ", ".join(f"`{c['id']}` ({c['verdict']})" for c in report["contracts"])]
    if report.get("untested"):
        lines += ["", "**Untested affected code:** " + ", ".join(f"`{u}`" for u in report["untested"])]
    lines += ["", f"**Tests to run:** {', '.join(report.get('testsToRun', [])) or 'none'}", "",
              f"predicted {m['predicted']}, confirmed {m['confirmed']}, fixed {m.get('fixed', 0)}, regressions {m.get('regressions', 0)}"]
    return "\n".join(lines)
```
````


---

## C8. Polish, share preview and deploy  (about 3 coins)

The share preview uses `app.index_string` (already in the tested app.py: it renders `og:title`, `og:description`, `og:image` and was verified in a test request).

````text
Read PLAN.md. Polish and ship.
1. Accessibility: colour contrast at least 4.5:1 for text (verify the verdict colours), visible focus outlines, aria-labels on the graph controls and upload area, `prefers-reduced-motion` respected (already in style.css), all interactive elements reachable by keyboard.
2. States: empty state (no reports), error state (invalid report with the schema errors), loading spinners (dcc.Loading around the graph).
3. Replace dashboard/assets/og.png with a real 1200x630 cover: the blast-radius graph screenshot of the S1 scenario on a dark background with the title "Uplift: know what a change will break". Keep the file under 300 kB.
4. Deploy to Render: create dashboard/render.yaml (exact text below), and give me the exact click-by-click steps for a Render "Web Service" from the GitHub repo (root directory dashboard, start command `gunicorn app:server`, Python 3.12). Also document a backup: Hugging Face Spaces with a Dockerfile (python:3.12-slim, pip install -r requirements.txt, CMD gunicorn -b 0.0.0.0:7860 app:server).
5. The app must run with only committed files: no backend, no secrets, no database. Confirm with `gunicorn app:server` locally (on Windows use `python app.py`, gunicorn needs Linux; also test `python -m pytest -q`).
6. Update dashboard/README.md with the live URL placeholder, run, test and deploy steps.

dashboard/render.yaml (exact):
services:
  - type: web
    name: uplift-dashboard
    runtime: python
    rootDir: dashboard
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:server
    envVars:
      - key: PYTHON_VERSION
        value: 3.12.6

DONE WHEN: pytest passes; the app works with a 375px window; the og.png is real; render.yaml exists; the deploy steps are written.
Commit: [bob C8] polish and deploy config
````


After the first Render deploy: open the live URL on your phone, paste it into the lablab "Application URL" field later, and fix any difference between local and deployed behaviour (usually a path or a missing committed file).

---

## C9. Swap mocks for real reports  (about 1 coin, after A9)

````text
Read PLAN.md. A9 published the real reports to evidence/ and dashboard/reports/. Now:
1. Update dashboard/reports/index.json to list the real scenarios (ids and titles from the reports: s1-null-user, s2-cents, s3-pydantic2) and delete every file whose provenance.generatedBy is "mock" (impact-s1.mock.json, migrate-pydantic2.mock.json).
2. Make sure dashboard/schema/report.schema.json is byte-identical to schema/report.schema.json.
3. Restart the app: all three scenarios render with no schema errors; the accuracy card and "See what we missed" (eval.md) work for S1 and S2.
4. Update the tests that referenced the mock file names so they use the real reports (or skip when absent), keep `python -m pytest -q` green.
DONE WHEN: `python scripts/verify.py` shows no "is not a mock" failure for dashboard/reports.
Commit: [bob C9] real reports in dashboard
````


---

## C10. Convention badge and Docker node  (F16 and F17, STRETCH, about 3 coins)

````text
Read PLAN.md. Update the dashboard for two OPTIONAL report fields (render nothing when absent):
1. report.conventions (F16): a "Repo conventions" card listing naming, imports, error handling and file layout with the evidence files, plus a compliance badge (checkedLines, violations, retried). If dashboard/reports/ contains generic.diff and convention-aware.diff (copy them from docs/convention-demo/), show them side by side (two dbc.Col with `html.Pre`, added lines green and removed lines red) under the caption "Generic fix vs convention-aware fix".
2. report.infraImpact (F17): render each entry as a container-shaped node (shape "round-rectangle", distinct colour) in the graph, connected to the changed symbol; clicking it shows file, "layer N of M", trigger, layers rebuilt, suggestion, and measuredRebuildSeconds ONLY if present (never show a made-up time).
Add both fields to the loader tests (validate a report that includes them).
DONE WHEN: pytest passes; a test report with conventions and infraImpact shows both.
Commit: [bob C10] convention badge and infra node
````


---

## Written deliverables (not Bob work, not counted as Bob tasks)

README, `docs/problem-solution.md` and `docs/bob-usage.md` (each 500 words or fewer), SOURCES.md, and the lablab submission text. Draft them from `bob_sessions/LOG.md`, then edit so they are accurate. **The Bob Usage statement lists exactly what Bob did (from LOG.md) and names any other tools used, and for what** (PLAN.md section 11a). Video and slides come from your skill.
