from __future__ import annotations

import glob as _glob
import json
import sys
import time
from pathlib import Path
from typing import List, Optional

import typer

from uplift.diff import changed_symbols, head_and_base
from uplift.graph import find_candidates
from uplift.report import build_report
from uplift.routes import contracts_for, route_map
from uplift.testmap import annotate_candidates

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
    patch: Path = typer.Option(..., help="Path to the unified diff patch file."),
    out: Path = typer.Option(..., help="Output JSON file path."),
    applied: bool = typer.Option(False, "--applied", help="Patch already applied to repo."),
) -> None:
    """Run diff + 3-hop reference graph and write graph.json."""
    t0 = time.monotonic()
    head, base = head_and_base(repo, patch, applied)
    changed = changed_symbols(head, base, patch)
    candidates = find_candidates(head, changed)

    # Route map + contracts
    routes = route_map(head)
    contracts = contracts_for(candidates, routes)

    # Test mapping — annotates candidates in-place, returns union + untested
    annotate_candidates(candidates, head)
    tests_to_run: list[str] = sorted(
        {t for c in candidates for t in c.get("tests", [])}
    )
    untested: list[str] = sorted(
        c["id"] for c in candidates if not c.get("tests")
    )

    # Count scanned files (non-test .py files under head)
    files_scanned = sum(
        1 for p in head.rglob("*.py")
        if not any(
            part in ("tests", "test") or part.startswith("test_")
            for part in p.relative_to(head).parts
        )
    )
    seconds_taken = round(time.monotonic() - t0, 3)

    payload = {
        "changedSymbols": changed,
        "candidates": candidates,
        "contracts": contracts,
        "testsToRun": tests_to_run,
        "untested": untested,
        "filesScanned": files_scanned,
        "secondsTaken": seconds_taken,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # ASCII summary table: hop | id | module | tests
    print(f"Changed symbols ({len(changed)}):")
    for s in changed:
        print(f"  {s['id']}  [{s['changeType']}]")

    print(f"\nCandidates ({len(candidates)}):")
    col_hop = 3
    col_mod = max((len(c.get("module", "")) for c in candidates), default=6)
    col_mod = max(col_mod, 6)
    col_id = max((len(c["id"]) for c in candidates), default=2)
    col_id = max(col_id, 2)
    fmt = f"  {{:<{col_hop}}}  {{:<{col_mod}}}  {{}}"
    print(fmt.format("hop", "module", "id"))
    print("  " + "-" * (col_hop + col_mod + col_id + 6))
    for c in candidates:
        print(fmt.format(c["hop"], c.get("module", ""), c["id"]))

    if contracts:
        print(f"\nContracts ({len(contracts)}):")
        for ct in contracts:
            print(f"  {ct['id']}  handler={ct['handler']}")

    if untested:
        print(f"\nUntested ({len(untested)}):")
        for u in untested:
            print(f"  {u}")

    print(f"\nFiles scanned: {files_scanned}  Time: {seconds_taken}s")
    print(f"Graph written to {out}")


@app.command()
def report(
    graph_file: Path = typer.Option(..., "--graph", help="Path to .uplift/graph.json."),
    scenario: str = typer.Option(..., help="Scenario ID (e.g. s1-null-user)."),
    title: str = typer.Option(..., help='Human-readable scenario title.'),
    out: Path = typer.Option(..., help="Output report JSON file path."),
    verdicts_file: Optional[Path] = typer.Option(None, "--verdicts", help="Path to .uplift/verdicts.json."),
    proofs_file: Optional[Path] = typer.Option(None, "--proofs", help="Path to .uplift/proofs.json."),
    repairs_glob: Optional[str] = typer.Option(None, "--repairs", help="Glob for repair files, e.g. .uplift/repair-*.json."),
    catalog_file: Optional[Path] = typer.Option(None, "--catalog", help="Path to .uplift/catalog.json."),
    bob_modes: Optional[str] = typer.Option(None, "--bob-modes", help="Comma-separated Bob mode names for provenance."),
    verified: bool = typer.Option(False, "--verified", help="Mark pipeline.verify as done."),
) -> None:
    """Assemble a full Uplift report from graph + optional verdict/proof/repair files."""
    if not graph_file.exists():
        typer.echo(f"ERROR: graph file not found: {graph_file}", err=True)
        raise typer.Exit(1)
    graph = json.loads(graph_file.read_text(encoding="utf-8"))

    verdicts = None
    if verdicts_file is not None:
        if not verdicts_file.exists():
            typer.echo(f"ERROR: verdicts file not found: {verdicts_file}", err=True)
            raise typer.Exit(1)
        verdicts = json.loads(verdicts_file.read_text(encoding="utf-8"))

    proofs = None
    if proofs_file is not None:
        if not proofs_file.exists():
            typer.echo(f"ERROR: proofs file not found: {proofs_file}", err=True)
            raise typer.Exit(1)
        proofs = json.loads(proofs_file.read_text(encoding="utf-8"))

    repair_dicts: list[dict] = []
    if repairs_glob:
        for rpath in sorted(_glob.glob(repairs_glob)):
            try:
                repair_dicts.append(json.loads(Path(rpath).read_text(encoding="utf-8")))
            except Exception as exc:
                typer.echo(f"WARNING: could not read repair file {rpath}: {exc}", err=True)

    catalog = None
    if catalog_file is not None:
        if not catalog_file.exists():
            typer.echo(f"ERROR: catalog file not found: {catalog_file}", err=True)
            raise typer.Exit(1)
        catalog = json.loads(catalog_file.read_text(encoding="utf-8"))

    modes_list: list[str] = [m.strip() for m in bob_modes.split(",")] if bob_modes else []

    rpt = build_report(
        graph=graph,
        verdicts=verdicts,
        proofs=proofs,
        repair_files=repair_dicts,
        catalog=catalog,
        scenario_id=scenario,
        title=title,
        bob_modes=modes_list,
        verified=verified,
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rpt, indent=2), encoding="utf-8")

    rk = rpt["risk"]
    typer.echo(
        f"Report written to {out}\n"
        f"  scenario: {scenario}  mode: {rpt['mode']}\n"
        f"  affected: {len(rpt['affected'])}  contracts: {len(rpt.get('contracts', []))}\n"
        f"  risk: {rk['score']} ({rk['level']})  predicted: {rpt['metrics']['predicted']}\n"
        f"  provenance.generatedBy: {rpt['provenance']['generatedBy']}"
    )


@app.command()
def validate(
    report_files: List[Path] = typer.Argument(..., help="Path(s) to report JSON file(s) to validate."),
) -> None:
    """Validate report JSON file(s) against schema/report.schema.json (Draft 7)."""
    import jsonschema

    # Walk up from the first file to find the repo root (contains schema/)
    def _find_schema(start: Path) -> Optional[Path]:
        for parent in [start] + list(start.parents):
            candidate = parent / "schema" / "report.schema.json"
            if candidate.exists():
                return candidate
        return None

    any_fail = False
    for rf in report_files:
        schema_path = _find_schema(rf.resolve())
        if schema_path is None:
            typer.echo(f"FAIL  {rf}  (schema/report.schema.json not found)", err=True)
            any_fail = True
            continue
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        try:
            instance = json.loads(rf.read_text(encoding="utf-8"))
        except Exception as exc:
            typer.echo(f"FAIL  {rf}  (could not read file: {exc})", err=True)
            any_fail = True
            continue
        validator = jsonschema.Draft7Validator(schema)
        errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))
        if errors:
            typer.echo(f"FAIL  {rf}")
            for err in errors:
                path = ".".join(str(p) for p in err.absolute_path) or "(root)"
                typer.echo(f"      {path}: {err.message}")
            any_fail = True
        else:
            typer.echo(f"PASS  {rf}")

    if any_fail:
        raise typer.Exit(1)


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
