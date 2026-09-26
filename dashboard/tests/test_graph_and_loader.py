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
