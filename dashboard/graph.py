"""Turn a report into dash-cytoscape elements + stylesheet. Pure functions, no Dash imports."""
from __future__ import annotations

import math

VERDICT_COLORS = {"will_break": "#d64545", "might_break": "#e0a030", "safe": "#3fa66a", "unknown": "#8a8f98"}
PROOF_MARK = {"confirmed": "✓", "unconfirmed": "?", "not_attempted": "", "not_applicable": ""}

ALL_VERDICTS = {"will_break", "might_break", "safe", "unknown"}


def _label(item: dict) -> str:
    name = item["id"].split("#")[-1]
    mark = PROOF_MARK.get((item.get("proof") or {}).get("status", ""), "")
    return f"{name} {mark}".strip()


def filter_hide(selected: list[str]) -> set[str]:
    """Return the set of verdict values to hide given the list of checked filter chips.

    ``selected`` is the list of chip values the user has turned ON (checked).
    Any verdict not in the selected list should be hidden.
    The special value "untested" is not a verdict; it is handled separately in
    the UI layer, so it is excluded from the returned set.

    >>> filter_hide(["will_break", "might_break", "safe", "unknown"])
    set()
    >>> filter_hide(["will_break", "might_break"]) == {"safe", "unknown"}
    True
    >>> filter_hide([]) == {"will_break", "might_break", "safe", "unknown"}
    True
    """
    checked_verdicts = ALL_VERDICTS & set(selected)
    return ALL_VERDICTS - checked_verdicts


def path_to_root(report: dict, node_id: str) -> list[str]:
    """Return the list of node IDs on the path from *node_id* back to its
    changed-symbol ancestor, following the ``via`` links.

    The returned list includes *node_id* itself and the changed symbol at the
    end (the root).  If *node_id* is already a changed symbol or is not found
    in the report, return ``[node_id]``.

    >>> import json, pathlib
    >>> # lightweight structural test — see test_graph_and_loader.py for the
    >>> # full integration test using the mock report.
    """
    changed_ids = {c["id"] for c in report.get("changedSymbols", [])}
    if node_id in changed_ids:
        return [node_id]

    # Build a via-map for quick lookup
    via_map: dict[str, str | None] = {}
    for item in report.get("affected", []):
        via_map[item["id"]] = item.get("via")

    # Check contracts too
    for contract in report.get("contracts") or []:
        cid = f"contract:{contract['id']}"
        via_map[cid] = contract.get("handler")

    path: list[str] = []
    current: str | None = node_id
    visited: set[str] = set()
    while current is not None and current not in visited:
        path.append(current)
        if current in changed_ids:
            break
        visited.add(current)
        current = via_map.get(current)

    if not path:
        return [node_id]
    return path


def build_elements(report: dict, hide: set[str] | None = None,
                   highlight: set[str] | None = None,
                   large: bool = False,
                   untested_only: bool = False) -> list[dict]:
    """Nodes on rings by hop (preset positions), edges from `via` to the item.

    Args:
        report:        The parsed report dict.
        hide:          Set of verdict strings whose nodes should be omitted.
        highlight:     Set of node IDs (and edge source/target pairs) to mark with
                       the ``highlight`` class.
        large:         When True (>60 nodes), suppress labels on non-will_break nodes.
        untested_only: When True, keep only affected items that have no tests
                       (the "untested only" filter chip), on top of ``hide``.
    """
    hide = hide or set()
    highlight = highlight or set()
    elements: list[dict] = []
    changed = report["changedSymbols"]
    for i, c in enumerate(changed):
        cls = "changed"
        if c["id"] in highlight:
            cls += " highlight"
        elements.append({"data": {"id": c["id"], "label": c["id"].split("#")[-1], "kind": "changed"},
                         "position": {"x": 0, "y": i * 80}, "classes": cls})
    by_hop: dict[int, list[dict]] = {}
    for item in report["affected"]:
        if item["verdict"] in hide:
            continue
        if untested_only and item.get("tests"):
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
            if item["id"] in highlight:
                classes.append("highlight")
            if large and item["verdict"] != "will_break":
                classes.append("no-label")
            elements.append({
                "data": {"id": item["id"], "label": _label(item), "verdict": item["verdict"], "kind": "affected"},
                "position": {"x": radius * math.cos(angle), "y": radius * math.sin(angle)},
                "classes": " ".join(classes),
            })
            known.add(item["id"])
    for item in report["affected"]:
        if item["verdict"] in hide or not item.get("via") or item["via"] not in known:
            continue
        if untested_only and item.get("tests"):
            continue
        edge_classes = ""
        if item["id"] in highlight and item["via"] in highlight:
            edge_classes = "highlight"
        elements.append({"data": {"source": item["via"], "target": item["id"]},
                         "classes": edge_classes})
    # Contracts: skip when their own verdict is filtered out, and only draw an
    # edge to a handler that is actually rendered (avoids a dangling edge to a
    # node the filter just removed).
    if not untested_only:
        for j, contract in enumerate(report.get("contracts") or []):
            if contract["verdict"] in hide:
                continue
            cid = f"contract:{contract['id']}"
            cls = f"contract {contract['verdict']}"
            if cid in highlight:
                cls += " highlight"
            elements.append({"data": {"id": cid, "label": contract["id"], "verdict": contract["verdict"], "kind": "contract"},
                             "position": {"x": 170 * 3.4, "y": (j - 0.5) * 90}, "classes": cls})
            handler = contract.get("handler", "")
            source = next((a["id"] for a in report["affected"] if a["id"].split("#")[0] == handler.split("#")[0]), None)
            if source and source in known:
                edge_classes = ""
                if cid in highlight and source in highlight:
                    edge_classes = "highlight"
                elements.append({"data": {"source": source, "target": cid}, "classes": edge_classes})
    # Docker/infra-impact nodes (F17): one container-shaped node per entry,
    # connected to the first changed symbol (the root of the change).
    root_id = changed[0]["id"] if changed else None
    for k, infra in enumerate(report.get("infraImpact") or []):
        iid = f"infra:{infra['file']}"
        cls = "infra"
        if iid in highlight:
            cls += " highlight"
        label = "🐳 " + infra["file"].split("/")[-1]
        elements.append({
            "data": {"id": iid, "label": label, "kind": "infra"},
            "position": {"x": -170 * 2.2, "y": (k - 0.5) * 90},
            "classes": cls,
        })
        if root_id:
            edge_classes = "highlight" if (iid in highlight and root_id in highlight) else ""
            elements.append({"data": {"source": root_id, "target": iid}, "classes": edge_classes})
    return elements


def build_stylesheet(large: bool = False) -> list[dict]:
    sheet = [
        {"selector": "node", "style": {
            "label": "data(label)",
            "font-size": 11,
            "text-valign": "bottom",
            "text-margin-y": 4,
            "width": 26,
            "height": 26,
            # light label color so text is readable on dark node backgrounds
            "color": "#ffffff",
            "text-outline-color": "#000000",
            "text-outline-width": 1,
        }},
        {"selector": ".changed", "style": {"background-color": "#3b5bdb", "shape": "star", "width": 44, "height": 44}},
        {"selector": ".contract", "style": {"shape": "round-rectangle", "width": 40, "height": 26}},
        # Docker/infra-impact node: round-rectangle, a distinct colour from contracts
        # and from any verdict colour so it reads as its own category (F17).
        {"selector": ".infra", "style": {
            "shape": "round-rectangle",
            "background-color": "#0d9488",
            "width": 46,
            "height": 30,
        }},
        {"selector": ".untested", "style": {"border-width": 3, "border-style": "dashed", "border-color": "#ff9800"}},
        {"selector": "edge", "style": {"width": 1.5, "line-color": "#b8bcc4", "target-arrow-shape": "triangle",
                                       "target-arrow-color": "#b8bcc4", "curve-style": "bezier"}},
        {"selector": ":selected", "style": {"border-width": 4, "border-color": "#111"}},
        # Highlight class: tapped node + ancestors + connecting edges
        {"selector": "node.highlight", "style": {
            "border-width": 4,
            "border-color": "#ffffff",
            "border-style": "solid",
            "overlay-color": "#ffffff",
            "overlay-opacity": 0.15,
        }},
        {"selector": "edge.highlight", "style": {
            "width": 3.5,
            "line-color": "#ffffff",
            "target-arrow-color": "#ffffff",
        }},
    ]
    for verdict, color in VERDICT_COLORS.items():
        sheet.append({"selector": f".{verdict}", "style": {"background-color": color}})

    # Large graph: hide labels on non-will_break nodes normally, show on hover
    if large:
        sheet.append({"selector": ".no-label", "style": {"label": ""}})
        sheet.append({"selector": ".no-label:active", "style": {"label": "data(label)"}})

    return sheet


def find_item(report: dict, node_id: str) -> dict | None:
    if node_id.startswith("contract:"):
        return next((c for c in report.get("contracts") or [] if f"contract:{c['id']}" == node_id), None)
    return next((a for a in report["affected"] if a["id"] == node_id), None)


def find_infra_impact(report: dict, node_id: str) -> dict | None:
    """Return the ``infraImpact`` entry matching a ``infra:<file>`` node id, or None."""
    if not node_id.startswith("infra:"):
        return None
    return next((i for i in report.get("infraImpact") or [] if f"infra:{i['file']}" == node_id), None)


def find_changed_symbol(report: dict, node_id: str) -> dict | None:
    """Return the ``changedSymbols`` entry matching *node_id*, or None.

    ``find_item`` deliberately does not search ``changedSymbols`` (they are a
    different shape: id/kind/changeType/hints, not file/verdict/reason), so
    callers that tap the star "changed symbol" node use this instead.
    """
    return next((c for c in report.get("changedSymbols", []) if c["id"] == node_id), None)
