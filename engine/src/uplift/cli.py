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
    occurrences_file: Optional[Path] = typer.Option(None, "--occurrences", help="Path to .uplift/occurrences.json (migrate mode)."),
    library: Optional[str] = typer.Option(None, "--library", help="Library name for dependency upgrade, e.g. pydantic."),
    lib_from: Optional[str] = typer.Option(None, "--from", help="Library version being upgraded from."),
    lib_to: Optional[str] = typer.Option(None, "--to", help="Library version being upgraded to."),
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
        if isinstance(proofs, dict):
            proofs = proofs.get("proofs", [])

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

    occurrences_data = None
    if occurrences_file is not None:
        if not occurrences_file.exists():
            typer.echo(f"ERROR: occurrences file not found: {occurrences_file}", err=True)
            raise typer.Exit(1)
        occurrences_data = json.loads(occurrences_file.read_text(encoding="utf-8"))
        # May be {"occurrences": [...], "counts": {...}} or a raw list
        if isinstance(occurrences_data, dict):
            occurrences_data = occurrences_data.get("occurrences", [])

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
        occurrences=occurrences_data,
        library=library,
        lib_from=lib_from,
        lib_to=lib_to,
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
    patch: Path = typer.Option(..., help="Path to the unified diff patch file."),
    proofs: Path = typer.Option(..., help="Directory containing proof test files."),
    out: Path = typer.Option(..., help="Output proofs JSON file (e.g. .uplift/proofs.json)."),
    applied: bool = typer.Option(False, "--applied", help="Patch already applied to repo."),
    app_python: Optional[str] = typer.Option(
        None,
        "--app-python",
        help="Python interpreter for running tests (default: sample-app/.venv python or sys.executable).",
    ),
) -> None:
    """Run proof tests and emit proofs.json with confirmed/unconfirmed status."""
    from uplift.proof import proof_run as _proof_run, _default_app_python

    python = app_python or _default_app_python(repo)

    result = _proof_run(
        repo=repo,
        patch=patch,
        proofs_dir=proofs,
        app_python=python,
        applied=applied,
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    # ASCII summary table
    plist = result["proofs"]
    suite = result["suite"]
    if plist:
        col_item = max(len(p["item"]) for p in plist)
        col_item = max(col_item, 4)
        col_file = max(len(p["testFile"]) for p in plist)
        col_file = max(col_file, 8)
        fmt = f"  {{:<{col_item}}}  {{:<{col_file}}}  {{:<11}}  {{:<11}}  {{}}"
        typer.echo(fmt.format("item", "testFile", "passesOnBase", "failsOnHead", "status"))
        typer.echo("  " + "-" * (col_item + col_file + 40))
        for p in plist:
            typer.echo(fmt.format(
                p["item"], p["testFile"],
                str(p["passesOnBase"]), str(p["failsOnHead"]), p["status"],
            ))
    typer.echo(
        f"\nSuite  base: {suite['base']['passed']} passed / {suite['base']['failed']} failed"
        f"   head: {suite['head']['passed']} passed / {suite['head']['failed']} failed"
    )
    confirmed = sum(1 for p in plist if p["status"] == "confirmed")
    typer.echo(f"\n{confirmed}/{len(plist)} proofs confirmed. Written to {out}")


@app.command(name="migrate-scan")
def migrate_scan(
    repo: Path = typer.Option(..., help="Path to the repository root."),
    catalog: Path = typer.Option(..., help="Migration catalog JSON (list of entries)."),
    out: Path = typer.Option(..., help="Output JSON file path (e.g. .uplift/occurrences.json)."),
) -> None:
    """Scan repo/shop for every migration catalog entry occurrence."""
    import json as _json
    from uplift.migrate import scan as _scan

    if not catalog.exists():
        typer.echo(f"ERROR: catalog not found: {catalog}", err=True)
        raise typer.Exit(1)

    catalog_data = _json.loads(catalog.read_text(encoding="utf-8"))
    # catalog may be a list directly, or {"catalog": [...]}
    entries: list[dict] = catalog_data if isinstance(catalog_data, list) else catalog_data.get("catalog", catalog_data)

    occurrences = _scan(repo, entries)

    # Counts per entry id
    counts: dict[str, int] = {}
    for occ in occurrences:
        counts[occ["entry"]] = counts.get(occ["entry"], 0) + 1

    result = {"occurrences": occurrences, "counts": counts}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_json.dumps(result, indent=2), encoding="utf-8")

    # ASCII summary
    typer.echo(f"Scan complete: {len(occurrences)} occurrences across {len(counts)} catalog entries")
    col_e = max((len(e) for e in counts), default=5)
    col_e = max(col_e, 5)
    fmt = f"  {{:<{col_e}}}  {{:>5}}  {{}}"
    typer.echo(fmt.format("entry", "count", "modules"))
    typer.echo("  " + "-" * (col_e + 20))
    for entry_id, cnt in sorted(counts.items()):
        modules = sorted({o["module"] for o in occurrences if o["entry"] == entry_id})
        typer.echo(fmt.format(entry_id, cnt, ", ".join(modules)))
    typer.echo(f"\nOccurrences written to {out}")


@app.command(name="upgrade-test")
def upgrade_test_cmd(
    repo: Path = typer.Option(..., help="Path to the repository root (e.g. sample-app/)."),
    requirements: Path = typer.Option(..., "--requirements", help="Upgraded requirements.txt to test against."),
    out: Path = typer.Option(..., help="Output JSON file path (e.g. .uplift/upgrade-before.json)."),
    current: bool = typer.Option(False, "--current", help="Use existing interpreter instead of a temp venv."),
    app_python: Optional[str] = typer.Option(None, "--app-python", help="Python interpreter path."),
) -> None:
    """Run the test suite against upgraded requirements (creates a temp venv)."""
    from uplift.migrate import upgrade_test as _upgrade_test

    if not requirements.exists():
        typer.echo(f"ERROR: requirements file not found: {requirements}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Running upgrade test (current={current}, requirements={requirements}) ...")
    result = _upgrade_test(
        repo=repo,
        requirements=requirements,
        app_python=app_python,
        current=current,
        out=out,
    )

    typer.echo(f"\nResults: {result['passed']} passed, {result['failed']} failed")
    if result.get("byModule"):
        col_m = max((len(m) for m in result["byModule"]), default=6)
        col_m = max(col_m, 6)
        fmt = f"  {{:<{col_m}}}  {{:>6}}  {{:>6}}"
        typer.echo(fmt.format("module", "passed", "failed"))
        typer.echo("  " + "-" * (col_m + 16))
        for mod, counts in sorted(result["byModule"].items()):
            typer.echo(fmt.format(mod, counts.get("passed", 0), counts.get("failed", 0)))
    typer.echo(f"\nResults written to {out}")


@app.command()
def comment(
    report_file: Path = typer.Option(..., "--report", help="Report JSON to render as a Markdown PR comment."),
) -> None:
    """Print a Markdown PR comment (risk line, verdict table, contracts, metrics)."""
    from uplift.comment import pr_comment

    if not report_file.exists():
        typer.echo(f"ERROR: report file not found: {report_file}", err=True)
        raise typer.Exit(1)
    try:
        report = json.loads(report_file.read_text(encoding="utf-8"))
    except Exception as exc:
        typer.echo(f"ERROR: could not read report: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo(pr_comment(report))


@app.command(name="run-all")
def run_all(
    repo: Path = typer.Option(..., help="Path to the repository root."),
    patch: Path = typer.Option(..., help="Path to the unified diff patch file."),
    scenario: str = typer.Option(..., help="Scenario ID (e.g. s1-null-user)."),
    applied: bool = typer.Option(False, "--applied", help="Patch already applied to repo."),
) -> None:
    """Run diff + graph + routes + test-map and write .uplift/graph.json; print next steps for Bob."""
    t0 = time.monotonic()

    uplift_dir = Path(".uplift")
    uplift_dir.mkdir(parents=True, exist_ok=True)
    graph_out = uplift_dir / "graph.json"

    # --- diff ---
    typer.echo(f"[run-all] diff  repo={repo}  patch={patch}  applied={applied}")
    try:
        head, base = head_and_base(repo, patch, applied)
    except Exception as exc:
        typer.echo(f"ERROR: diff failed: {exc}", err=True)
        raise typer.Exit(1)

    try:
        changed = changed_symbols(head, base, patch)
    except Exception as exc:
        typer.echo(f"ERROR: changed_symbols failed: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo(f"[run-all] {len(changed)} changed symbol(s)")

    # --- graph (3-hop) ---
    typer.echo("[run-all] graph ...")
    try:
        candidates = find_candidates(head, changed)
    except Exception as exc:
        typer.echo(f"ERROR: graph failed: {exc}", err=True)
        raise typer.Exit(1)

    # --- routes + contracts ---
    try:
        routes = route_map(head)
        contracts = contracts_for(candidates, routes)
    except Exception as exc:
        typer.echo(f"ERROR: routes failed: {exc}", err=True)
        raise typer.Exit(1)

    # --- test map ---
    try:
        annotate_candidates(candidates, head)
    except Exception as exc:
        typer.echo(f"ERROR: test-map failed: {exc}", err=True)
        raise typer.Exit(1)

    tests_to_run: list[str] = sorted(
        {t for c in candidates for t in c.get("tests", [])}
    )
    untested: list[str] = sorted(
        c["id"] for c in candidates if not c.get("tests")
    )
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
    graph_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    typer.echo(f"[run-all] graph written to {graph_out}")
    typer.echo(
        f"[run-all] {len(candidates)} candidate(s), "
        f"{len(contracts)} contract(s), "
        f"{len(untested)} untested, "
        f"{files_scanned} files scanned, "
        f"{seconds_taken}s"
    )
    typer.echo("")
    typer.echo("=" * 60)
    typer.echo("NEXT STEPS FOR BOB")
    typer.echo("=" * 60)
    typer.echo(f"  Switch to mode : uplift-impact-analyst")
    typer.echo(f"  Open prompt    : prompts/A-brain.md  (task A2 - predict)")
    typer.echo(f"  Graph file     : {graph_out}")
    typer.echo(f"  Scenario       : {scenario}")
    typer.echo("")
    typer.echo("  After verdicts are written to .uplift/verdicts.json:")
    typer.echo("  Switch to mode : uplift-prover")
    typer.echo("  Open prompt    : prompts/A-brain.md  (task A3 - prove)")
    typer.echo("=" * 60)


@app.command()
def mcp() -> None:
    """Start the Uplift MCP server on stdio transport."""
    from uplift.mcp_server import run
    run()
