"""Right-hand detail panel and affected-items DataTable. Pure Dash components."""
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dash_table, dcc, html

# Maps verdict -> Bootstrap colour token
VERDICT_COLOR = {
    "will_break":  "danger",
    "might_break": "warning",
    "safe":        "success",
    "unknown":     "secondary",
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
    badge_color = VERDICT_COLOR.get(verdict, "secondary")
    badge_icon  = VERDICT_ICON.get(verdict, "?")

    # ── header row: id + verdict badge ──────────────────────────────────────
    header = dbc.CardHeader([
        html.Span(item_id, className="fw-bold small font-monospace d-block"),
        dbc.Badge(
            [html.Span(badge_icon, className="me-1", **{"aria-hidden": "true"}), verdict],
            color=badge_color,
            className="mt-1",
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
    body_children.append(html.P(item.get("reason", ""), className="small text-muted mb-1"))
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
    {"if": {"state": "selected"},                         "backgroundColor": "#dbeafe", "border": "1px solid #3b82d4"},
]


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
        style_cell={"textAlign": "left", "fontSize": "13px", "padding": "6px 10px"},
        style_header={"fontWeight": "bold", "backgroundColor": "#f7f8fa"},
        style_data_conditional=TABLE_STYLE_DATA_CONDITIONAL,
    )
