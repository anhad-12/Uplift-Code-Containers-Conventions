from __future__ import annotations

import json
from pathlib import Path

import typer

from uplift.diff import changed_symbols, head_and_base

app = typer.Typer(
    help="Uplift: predict, prove, repair.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

# Keep all console output ASCII (no box characters, no emoji):
# Windows consoles can raise UnicodeEncodeError otherwise.


@app.command()
def diff(
    repo: Path = typer.Option(..., help="Path to the repository root."),
    patch: Path = typer.Option(..., help="Path to the unified diff patch file."),
    out: Path = typer.Option(..., help="Output JSON file path."),
    applied: bool = typer.Option(
        False, "--applied", help="Patch is already applied to repo (head=repo, base=reverse)."
    ),
) -> None:
    """Parse a patch and emit changed symbols with change classification."""
    head, base = head_and_base(repo, patch, applied)
    symbols = changed_symbols(head, base, patch)
    payload = {"changedSymbols": symbols}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Print ASCII table to stdout
    col_id = max((len(s["id"]) for s in symbols), default=2)
    col_ct = max((len(s["changeType"]) for s in symbols), default=10)
    col_id = max(col_id, 2)
    col_ct = max(col_ct, 10)
    fmt = f"{{:<{col_id}}}  {{:<{col_ct}}}  {{}}"
    print(fmt.format("id", "changeType", "hints"))
    print("-" * (col_id + col_ct + 4 + 30))
    for s in symbols:
        hints_str = ", ".join(s.get("hints", [])) or "-"
        print(fmt.format(s["id"], s["changeType"], hints_str))
    print(f"\n{len(symbols)} changed symbol(s) written to {out}")


@app.command()
def graph(
    repo: Path = typer.Option(..., help="Path to the repository root."),
    diff_file: Path = typer.Option(..., "--diff", help="Changed symbols JSON from `uplift diff`."),
    out: Path = typer.Option(..., help="Output JSON file path."),
    applied: bool = typer.Option(False, "--applied", help="Patch already applied to repo."),
) -> None:
    """Build the 3-hop reference graph (not yet implemented)."""
    raise NotImplementedError("graph: coming in B4")


@app.command()
def report(
    scenario: str = typer.Option(..., help="Scenario ID (e.g. s1-null-user)."),
    out: Path = typer.Option(..., help="Output report JSON file path."),
) -> None:
    """Assemble a full report.json (not yet implemented)."""
    raise NotImplementedError("report: coming in B8")


@app.command()
def validate(
    report_file: Path = typer.Argument(..., help="Path to a report JSON to validate."),
) -> None:
    """Validate a report JSON against the schema (not yet implemented)."""
    raise NotImplementedError("validate: coming in B9")


@app.command(name="proof-run")
def proof_run(
    repo: Path = typer.Option(..., help="Path to the repository root."),
    scenario: str = typer.Option(..., help="Scenario ID."),
) -> None:
    """Run proof tests and record results (not yet implemented)."""
    raise NotImplementedError("proof-run: coming in B7")


@app.command(name="migrate-scan")
def migrate_scan(
    repo: Path = typer.Option(..., help="Path to the repository root."),
    catalog: Path = typer.Option(..., help="Migration catalog JSON from Bob."),
) -> None:
    """Scan repo for migration catalog occurrences (not yet implemented)."""
    raise NotImplementedError("migrate-scan: coming in B8")


@app.command(name="upgrade-test")
def upgrade_test(
    repo: Path = typer.Option(..., help="Path to the repository root."),
) -> None:
    """Run tests against the upgraded dependency (not yet implemented)."""
    raise NotImplementedError("upgrade-test: coming in B8")


@app.command()
def comment(
    report_file: Path = typer.Option(..., help="Report JSON to render as PR comment."),
) -> None:
    """Generate a PR comment from a report (not yet implemented)."""
    raise NotImplementedError("comment: coming in B11")


@app.command(name="run-all")
def run_all(
    repo: Path = typer.Option(..., help="Path to the repository root."),
    scenario: str = typer.Option(..., help="Scenario ID."),
    applied: bool = typer.Option(False, "--applied", help="Patch already applied to repo."),
) -> None:
    """Run the full predict pipeline for a scenario (not yet implemented)."""
    raise NotImplementedError("run-all: coming in B9")


@app.command()
def mcp() -> None:
    """Start the MCP server (not yet implemented)."""
    raise NotImplementedError("mcp: coming in B14")
