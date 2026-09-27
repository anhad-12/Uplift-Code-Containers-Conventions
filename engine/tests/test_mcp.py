"""test_mcp.py — verify the MCP server exposes exactly four tools.

These tests require the mcp extra (pip install -e "engine[mcp]").
They are skipped automatically in CI where only engine[dev] is installed.
"""
from __future__ import annotations

import pytest

mcp = pytest.importorskip("mcp", reason="mcp extra not installed (engine[mcp] required)")


def test_mcp_tool_names() -> None:
    """build_mcp() must expose exactly the four expected tool names."""
    from uplift.mcp_server import build_mcp

    mcp = build_mcp()
    # FastMCP stores tools in ._tool_manager._tools (dict name -> Tool)
    tools = mcp._tool_manager._tools
    names = set(tools.keys())
    expected = {"uplift_graph", "uplift_proof_run", "uplift_migrate_scan", "uplift_report"}
    assert names == expected, f"Unexpected tools: {names}"


def test_mcp_tool_count() -> None:
    """Exactly four tools registered — no accidental extras."""
    from uplift.mcp_server import build_mcp

    mcp = build_mcp()
    assert len(mcp._tool_manager._tools) == 4
