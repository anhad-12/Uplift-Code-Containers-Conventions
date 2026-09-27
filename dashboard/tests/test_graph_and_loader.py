import json
from pathlib import Path

import graph
import loader

REPORTS = Path(__file__).resolve().parent / "fixtures"


def report(name: str) -> dict:
    return json.loads((REPORTS / name).read_text(encoding="utf-8"))


# ── filter_hide() unit tests ──────────────────────────────────────────────────

def test_filter_hide_all_selected_returns_empty_set():
    assert graph.filter_hide(["will_break", "might_break", "safe", "unknown"]) == set()


def test_filter_hide_partial_selection_hides_unselected():
    result = graph.filter_hide(["will_break", "might_break"])
    assert result == {"safe", "unknown"}


def test_filter_hide_none_selected_hides_all_verdicts():
    result = graph.filter_hide([])
    assert result == {"will_break", "might_break", "safe", "unknown"}


def test_filter_hide_untested_token_ignored():
    # "untested" is a UI-only token, not a verdict; it must not appear in the output
    result = graph.filter_hide(["will_break", "untested"])
    assert "untested" not in result
    # safe, might_break, unknown are unchecked -> hidden
    assert "safe" in result
    assert "might_break" in result
    assert "unknown" in result


# ── path_to_root() unit tests ─────────────────────────────────────────────────

def test_path_to_root_from_hop1_node():
    r = report("impact-s1.mock.json")
    # build_invoice is directly connected to the changed symbol via shop/users/service.py#get_user
    path = graph.path_to_root(r, "shop/orders/invoice.py#build_invoice")
    assert path[0] == "shop/orders/invoice.py#build_invoice"
    assert path[-1] == "shop/users/service.py#get_user"
    assert "shop/users/service.py#get_user" in path


def test_path_to_root_from_hop2_node():
    r = report("impact-s1.mock.json")
    # user_spend_report is hop-2: goes through create_order -> get_user
    path = graph.path_to_root(r, "shop/admin/reports.py#user_spend_report")
    assert path[0] == "shop/admin/reports.py#user_spend_report"
    assert "shop/orders/service.py#create_order" in path
    assert path[-1] == "shop/users/service.py#get_user"


def test_path_to_root_for_changed_symbol_is_itself():
    r = report("impact-s1.mock.json")
    path = graph.path_to_root(r, "shop/users/service.py#get_user")
    assert path == ["shop/users/service.py#get_user"]


def test_path_to_root_unknown_node_returns_singleton():
    r = report("impact-s1.mock.json")
    path = graph.path_to_root(r, "nonexistent/node.py#foo")
    assert path == ["nonexistent/node.py#foo"]


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
