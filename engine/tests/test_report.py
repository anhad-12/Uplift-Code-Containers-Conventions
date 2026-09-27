"""test_report.py — unit tests for uplift.report.

Covers:
  - risk() formula: three hand-computed cases
  - build_report() merge: tiny graph.json + verdicts.json
  - build_report() validates against schema/report.schema.json
  - graph-only run: provenance "engine", all verdicts "unknown"
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from uplift.report import build_report, risk


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


def _find_schema() -> Path:
    """Walk up from this file to find schema/report.schema.json."""
    here = Path(__file__).resolve()
    for parent in list(here.parents):
        candidate = parent / "schema" / "report.schema.json"
        if candidate.exists():
            return candidate
    pytest.skip("schema/report.schema.json not found — skipping schema validation test")


# ---------------------------------------------------------------------------
# risk() — three hand-computed cases
# ---------------------------------------------------------------------------

class TestRisk:
    def test_zero_items_is_zero_low(self):
        """No items, no contracts, no untested -> score=0, level=low."""
        r = risk([], [], [])
        assert r["score"] == 0
        assert r["level"] == "low"
        assert isinstance(r["factors"], list)
        assert len(r["factors"]) == 4

    def test_formula_high(self):
        """4 will_break + 1 might_break + 1 untested + 1 contract hit = 71, high.

        Arithmetic:
          10*4 = 40  (will_break)
           4*1 =  4  (might_break)
          12*1 = 12  (untested)
          15*1 = 15  (contract hit)
          -----
               = 71  -> high (60 <= 71 < 80)
        """
        affected = (
            [{"verdict": "will_break"}] * 4
            + [{"verdict": "might_break"}]
        )
        contracts = [{"verdict": "will_break"}]  # 1 contract hit
        untested = ["id_a"]                        # 1 untested
        r = risk(affected, contracts, untested)
        assert r["score"] == 71
        assert r["level"] == "high"

    def test_cap_at_100_critical(self):
        """Score that would exceed 100 is capped at 100, level=critical.

        10 will_break -> 100 already; adding more pushes past 100 -> capped.
        """
        affected = [{"verdict": "will_break"}] * 10
        r = risk(affected, [], [])
        assert r["score"] == 100
        assert r["level"] == "critical"

    def test_medium_boundary(self):
        """Score 30..59 -> medium."""
        # 8 might_break = 4*8 = 32 -> medium
        affected = [{"verdict": "might_break"}] * 8
        r = risk(affected, [], [])
        assert r["score"] == 32
        assert r["level"] == "medium"


# ---------------------------------------------------------------------------
# Minimal graph fixture
# ---------------------------------------------------------------------------

def _minimal_graph() -> dict:
    """Return a hand-written graph dict mimicking .uplift/graph.json output."""
    return {
        "changedSymbols": [
            {
                "id": "shop/users/service.py#get_user",
                "kind": "function",
                "changeType": "returnShape",
                "hints": ["return None added"],
            }
        ],
        "candidates": [
            {
                "id": "shop/users/routes.py#get_user_route",
                "file": "shop/users/routes.py",
                "line": 15,
                "hop": 1,
                "via": "shop/users/service.py#get_user",
                "module": "users",
                "layer": "direct",
                "snippet": "def get_user_route(user_id: int):\n    user = get_user(user_id)\n    return user",
                "tests": ["tests/test_users.py::test_get_user"],
            },
            {
                "id": "shop/orders/service.py#create_order",
                "file": "shop/orders/service.py",
                "line": 22,
                "hop": 1,
                "via": "shop/users/service.py#get_user",
                "module": "orders",
                "layer": "direct",
                "snippet": "def create_order(user_id: int):\n    user = get_user(user_id)",
                "tests": [],
            },
        ],
        "contracts": [
            {
                "type": "route",
                "id": "GET /users/{user_id}",
                "handler": "shop/users/routes.py#get_user_route",
                "verdict": "unknown",
            }
        ],
        "testsToRun": ["tests/test_users.py::test_get_user"],
        "untested": ["shop/orders/service.py#create_order"],
        "filesScanned": 12,
        "secondsTaken": 0.5,
    }


def _minimal_verdicts() -> list[dict]:
    """Return a hand-written verdicts list as Bob would produce."""
    return [
        {
            "id": "shop/users/routes.py#get_user_route",
            "verdict": "will_break",
            "reason": "Route returns the user object directly; if get_user returns None the client gets a 500.",
            "fix": "Add a None check and return 404.",
        },
        {
            "id": "shop/orders/service.py#create_order",
            "verdict": "might_break",
            "reason": "Reads user.name without None guard.",
            "fix": "Check user is not None before accessing attributes.",
        },
    ]


# ---------------------------------------------------------------------------
# build_report() merge test
# ---------------------------------------------------------------------------

class TestBuildReport:
    def test_verdicts_merged(self):
        """Verdicts from verdicts list are merged into affected by candidate id."""
        graph = _minimal_graph()
        verdicts = _minimal_verdicts()

        rpt = build_report(
            graph=graph,
            verdicts=verdicts,
            proofs=None,
            repair_files=[],
            catalog=None,
            scenario_id="s1-null-user",
            title="S1 null user",
            bob_modes=[],
        )

        affected_by_id = {a["id"]: a for a in rpt["affected"]}
        assert affected_by_id["shop/users/routes.py#get_user_route"]["verdict"] == "will_break"
        assert affected_by_id["shop/orders/service.py#create_order"]["verdict"] == "might_break"

    def test_contract_verdict_propagated(self):
        """Contract verdict is updated from the verdict map via its handler id."""
        graph = _minimal_graph()
        verdicts = _minimal_verdicts()

        rpt = build_report(
            graph=graph,
            verdicts=verdicts,
            proofs=None,
            repair_files=[],
            catalog=None,
            scenario_id="s1-null-user",
            title="S1",
            bob_modes=[],
        )

        contracts = {c["id"]: c for c in rpt["contracts"]}
        assert contracts["GET /users/{user_id}"]["verdict"] == "will_break"

    def test_graph_only_provenance_engine(self):
        """When no verdicts file is given, provenance.generatedBy must be 'engine'."""
        graph = _minimal_graph()

        rpt = build_report(
            graph=graph,
            verdicts=None,   # <-- no verdicts
            proofs=None,
            repair_files=[],
            catalog=None,
            scenario_id="s1-null-user",
            title="S1",
            bob_modes=[],
        )

        assert rpt["provenance"]["generatedBy"] == "engine"

    def test_graph_only_all_verdicts_unknown(self):
        """Without verdicts, every affected item must have verdict='unknown'."""
        graph = _minimal_graph()

        rpt = build_report(
            graph=graph,
            verdicts=None,
            proofs=None,
            repair_files=[],
            catalog=None,
            scenario_id="s1-null-user",
            title="S1",
            bob_modes=[],
        )

        for item in rpt["affected"]:
            assert item["verdict"] == "unknown", (
                f"{item['id']} has verdict {item['verdict']!r}, expected 'unknown'"
            )

    def test_verdicts_given_provenance_bob(self):
        """When a verdicts list is given, provenance.generatedBy must be 'bob'."""
        graph = _minimal_graph()
        rpt = build_report(
            graph=graph,
            verdicts=_minimal_verdicts(),
            proofs=None,
            repair_files=[],
            catalog=None,
            scenario_id="s1-null-user",
            title="S1",
            bob_modes=["uplift-impact-analyst"],
        )
        assert rpt["provenance"]["generatedBy"] == "bob"
        assert "uplift-impact-analyst" in rpt["provenance"]["bobModes"]

    def test_pipeline_predict_done(self):
        """pipeline.predict is always 'done' when a graph is given."""
        rpt = build_report(
            graph=_minimal_graph(),
            verdicts=None,
            proofs=None,
            repair_files=[],
            catalog=None,
            scenario_id="test",
            title="Test",
            bob_modes=[],
        )
        assert rpt["pipeline"]["predict"] == "done"

    def test_pipeline_prove_done_when_proofs_given(self):
        """pipeline.prove becomes 'done' when a proofs list is provided."""
        proofs = [
            {
                "id": "shop/users/routes.py#get_user_route",
                "status": "confirmed",
                "testFile": "tests/uplift_proofs/test_s1_get_user_route.py",
                "passesOnBase": True,
                "failsOnHead": True,
            }
        ]
        rpt = build_report(
            graph=_minimal_graph(),
            verdicts=_minimal_verdicts(),
            proofs=proofs,
            repair_files=[],
            catalog=None,
            scenario_id="test",
            title="Test",
            bob_modes=[],
        )
        assert rpt["pipeline"]["prove"] == "done"
        # proof merged into affected
        affected_by_id = {a["id"]: a for a in rpt["affected"]}
        proof = affected_by_id["shop/users/routes.py#get_user_route"]["proof"]
        assert proof["status"] == "confirmed"
        assert proof["passesOnBase"] is True
        assert proof["failsOnHead"] is True

    def test_metrics_predicted_count(self):
        """metrics.predicted = will_break items + will_break contracts."""
        # 1 will_break item, 1 will_break contract -> predicted = 2
        graph = _minimal_graph()
        verdicts = _minimal_verdicts()  # route handler is will_break -> contract becomes will_break
        rpt = build_report(
            graph=graph,
            verdicts=verdicts,
            proofs=None,
            repair_files=[],
            catalog=None,
            scenario_id="s1-null-user",
            title="S1",
            bob_modes=[],
        )
        assert rpt["metrics"]["predicted"] == 2  # 1 affected + 1 contract


# ---------------------------------------------------------------------------
# Schema validation test
# ---------------------------------------------------------------------------

class TestSchemaValidation:
    def test_built_report_passes_schema(self):
        """A report built from the minimal fixture must validate against the schema."""
        import jsonschema

        schema_path = _find_schema()
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        rpt = build_report(
            graph=_minimal_graph(),
            verdicts=_minimal_verdicts(),
            proofs=None,
            repair_files=[],
            catalog=None,
            scenario_id="s1-null-user",
            title="S1 null user",
            bob_modes=["uplift-impact-analyst"],
        )

        validator = jsonschema.Draft7Validator(schema)
        errors = list(validator.iter_errors(rpt))
        assert not errors, (
            "Report failed schema validation:\n"
            + "\n".join(
                f"  {'->'.join(str(p) for p in e.absolute_path) or '(root)'}: {e.message}"
                for e in errors
            )
        )

    def test_graph_only_report_passes_schema(self):
        """Even a graph-only report (no verdicts) must validate."""
        import jsonschema

        schema_path = _find_schema()
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        rpt = build_report(
            graph=_minimal_graph(),
            verdicts=None,
            proofs=None,
            repair_files=[],
            catalog=None,
            scenario_id="s1-null-user",
            title="S1 null user",
            bob_modes=[],
        )

        validator = jsonschema.Draft7Validator(schema)
        errors = list(validator.iter_errors(rpt))
        assert not errors, (
            "Graph-only report failed schema validation:\n"
            + "\n".join(
                f"  {'->'.join(str(p) for p in e.absolute_path) or '(root)'}: {e.message}"
                for e in errors
            )
        )
