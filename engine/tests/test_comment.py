"""test_comment.py — unit tests for uplift.comment.pr_comment.

Covers:
  - Full report (impact-s1.mock.json): risk line "Risk 71/100 (high)",
    table header, contracts line, untested line, metrics line.
  - Graph-only report (all verdicts "unknown"): "Graph only" notice present,
    no real verdict rows expected to list anything other than "unknown".
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from uplift.comment import pr_comment


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_mock(name: str) -> Path:
    """Walk up from this file to find schema/examples/<name>."""
    here = Path(__file__).resolve()
    for parent in list(here.parents):
        candidate = parent / "schema" / "examples" / name
        if candidate.exists():
            return candidate
    pytest.skip(f"schema/examples/{name} not found")


def _load_mock(name: str) -> dict:
    path = _find_mock(name)
    return json.loads(path.read_text(encoding="utf-8"))


def _graph_only_report() -> dict:
    """Minimal graph-only report where all verdicts are 'unknown'."""
    return {
        "scenario": {"id": "test", "title": "test scenario"},
        "risk": {"score": 0, "level": "low", "factors": []},
        "metrics": {"predicted": 0, "confirmed": 0, "fixed": 0, "regressions": 0},
        "affected": [
            {"id": "shop/foo.py#bar", "verdict": "unknown"},
            {"id": "shop/baz.py#qux", "verdict": "unknown"},
        ],
        "contracts": [],
        "untested": [],
        "testsToRun": [],
    }


# ---------------------------------------------------------------------------
# Tests against impact-s1.mock.json
# ---------------------------------------------------------------------------

class TestPrCommentS1Mock:
    """Tests using the canonical mock report (schema/examples/impact-s1.mock.json)."""

    @pytest.fixture(scope="class")
    def report(self) -> dict:
        return _load_mock("impact-s1.mock.json")

    @pytest.fixture(scope="class")
    def comment(self, report: dict) -> str:
        return pr_comment(report)

    def test_risk_line_present(self, comment: str) -> None:
        """Comment must contain the risk score, total and level."""
        assert "Risk 71/100 (high)" in comment

    def test_table_header_present(self, comment: str) -> None:
        """Markdown table header row must be present."""
        assert "| Item | Verdict | Proof | Reason |" in comment

    def test_contracts_line_present(self, comment: str) -> None:
        """API contracts line must be present (report has one contract)."""
        assert "**API contracts:**" in comment
        assert "GET /users/{user_id}" in comment

    def test_will_break_sorted_before_safe(self, comment: str) -> None:
        """'will_break' rows must appear before 'safe' rows in the table."""
        wb_pos = comment.index("will_break")
        safe_pos = comment.index("| safe |") if "| safe |" in comment else comment.index("safe")
        assert wb_pos < safe_pos

    def test_untested_line_present(self, comment: str) -> None:
        """Untested affected code line must list the untested item."""
        assert "**Untested affected code:**" in comment
        assert "user_spend_report" in comment

    def test_metrics_line_present(self, comment: str) -> None:
        """Metrics summary line must be present with correct counts."""
        assert "predicted 5" in comment
        assert "confirmed 4" in comment
        assert "fixed 4" in comment
        assert "regressions 0" in comment

    def test_no_graph_only_notice(self, comment: str) -> None:
        """Full report must NOT include the graph-only notice."""
        assert "Graph only" not in comment

    def test_heading_contains_scenario_title(self, comment: str) -> None:
        """Heading must contain the scenario title."""
        assert "get_user returns None instead of raising" in comment


# ---------------------------------------------------------------------------
# Tests for graph-only report
# ---------------------------------------------------------------------------

class TestPrCommentGraphOnly:
    """Tests for a report where all verdicts are 'unknown' (graph-only run)."""

    @pytest.fixture(scope="class")
    def comment(self) -> str:
        return pr_comment(_graph_only_report())

    def test_graph_only_notice_present(self, comment: str) -> None:
        """Graph-only notice must be present when no real verdicts exist."""
        assert "Graph only. Verdicts, proofs and repairs come from a Bob run." in comment

    def test_table_header_still_present(self, comment: str) -> None:
        """Table header must still be present even for graph-only output."""
        assert "| Item | Verdict | Proof | Reason |" in comment

    def test_no_contracts_line(self, comment: str) -> None:
        """No contracts line when contracts list is empty."""
        assert "**API contracts:**" not in comment

    def test_metrics_line_present(self, comment: str) -> None:
        """Metrics line must be present (all zeros for graph-only)."""
        assert "predicted 0" in comment
        assert "confirmed 0" in comment
