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
