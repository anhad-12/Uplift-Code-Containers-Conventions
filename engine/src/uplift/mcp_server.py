"""mcp_server.py — Uplift MCP server (stdio transport).

Exposes four tools that call the existing engine functions directly:
  uplift_graph        -> writes .uplift/graph.json
  uplift_proof_run    -> writes .uplift/proofs.json
  uplift_migrate_scan -> writes .uplift/occurrences.json
  uplift_report       -> assembles reports/<scenario>.json

Run via: python -m uplift mcp   (stdio transport)

Only the four Bob modes that carry the `mcp` permission group
(uplift-impact-analyst, uplift-prover, uplift-migration-planner,
uplift-verifier) can call these tools.
"""
from __future__ import annotations

import glob as _glob
import json
import sys
import time
from pathlib import Path
from typing import Optional


def build_mcp():
    """Build and return the FastMCP application with all four tools."""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("uplift")

    # ------------------------------------------------------------------ #
    # Tool 1: uplift_graph                                                 #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    def uplift_graph(repo: str, patch: str, applied: bool = False) -> str:
        """Build the change-impact graph for a patch and write .uplift/graph.json.

        Args:
            repo:    Path to the repository root (e.g. "sample-app").
            patch:   Path to the unified diff patch file.
            applied: True if the patch is already applied to the repo.

        Returns JSON string: {"ok": bool, "filesScanned": int, "candidates": int,
                              "graphFile": str, "secondsTaken": float}
        """
        from uplift.diff import changed_symbols, head_and_base
        from uplift.graph import find_candidates
        from uplift.routes import contracts_for, route_map
        from uplift.testmap import annotate_candidates

        t0 = time.monotonic()
        repo_path = Path(repo)
        patch_path = Path(patch)

        head, base = head_and_base(repo_path, patch_path, applied)
        changed = changed_symbols(head, base, patch_path)
        candidates = find_candidates(head, changed)

        routes = route_map(head)
        contracts = contracts_for(candidates, routes)
        annotate_candidates(candidates, head)

        tests_to_run = sorted({t for c in candidates for t in c.get("tests", [])})
        untested = sorted(c["id"] for c in candidates if not c.get("tests"))

        files_scanned = sum(
            1 for p in head.rglob("*.py")
            if not any(
                part in ("tests", "test", "node_modules", "__pycache__") or part.startswith(("test_", "."))
                for part in p.relative_to(head).parts
            )
        )

        from uplift.docker import impact
        from unidiff import PatchSet
        payload = {
            "changedSymbols": changed,
            "infraImpact": impact(head, [f.path for f in PatchSet(patch_path.read_text(encoding="utf-8"))]),
            "candidates": candidates,
            "contracts": contracts,
            "testsToRun": tests_to_run,
            "untested": untested,
            "filesScanned": files_scanned,
            "secondsTaken": round(time.monotonic() - t0, 3),
        }

        out = Path(".uplift/graph.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        return json.dumps({
            "ok": True,
            "filesScanned": files_scanned,
            "candidates": len(candidates),
            "graphFile": str(out),
            "secondsTaken": payload["secondsTaken"],
        })

    # ------------------------------------------------------------------ #
    # Tool 2: uplift_proof_run                                             #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    def uplift_proof_run(repo: str, patch: str, proofs: str, applied: bool = False, app_python: Optional[str] = None) -> str:
        """Run proof tests and write .uplift/proofs.json.

        Args:
            repo:    Path to the repository root.
            patch:   Path to the unified diff patch file.
            proofs:  Path to the directory containing proof test files.
            applied: True if the patch is already applied to the repo.

        Returns JSON string: {"ok": bool, "confirmed": int, "unconfirmed": int,
                              "proofsFile": str}
        """
        from uplift.proof import _default_app_python, proof_run

        repo_path = Path(repo)
        python = app_python or _default_app_python(repo_path)

        result = proof_run(
            repo=repo_path,
            patch=Path(patch),
            proofs_dir=Path(proofs),
            app_python=python,
            applied=applied,
        )

        out = Path(".uplift/proofs.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")

        confirmed = sum(1 for p in result["proofs"] if p["status"] == "confirmed")
        unconfirmed = sum(1 for p in result["proofs"] if p["status"] == "unconfirmed")

        return json.dumps({
            "ok": True,
            "confirmed": confirmed,
            "unconfirmed": unconfirmed,
            "proofsFile": str(out),
        })

    # ------------------------------------------------------------------ #
    # Tool 3: uplift_migrate_scan                                          #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    def uplift_migrate_scan(repo: str, catalog: str) -> str:
        """Scan repo/shop for every migration catalog entry and write .uplift/occurrences.json.

        Args:
            repo:    Path to the repository root.
            catalog: Path to the migration catalog JSON file (list of entries).

        Returns JSON string: {"ok": bool, "occurrences": int, "entries": int,
                              "occurrencesFile": str}
        """
        from uplift.migrate import scan

        catalog_data = json.loads(Path(catalog).read_text(encoding="utf-8"))
        entries = catalog_data if isinstance(catalog_data, list) else catalog_data.get("catalog", catalog_data)

        occurrences = scan(Path(repo), entries)
        counts: dict[str, int] = {}
        for occ in occurrences:
            counts[occ["entry"]] = counts.get(occ["entry"], 0) + 1

        result = {"occurrences": occurrences, "counts": counts}
        out = Path(".uplift/occurrences.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")

        return json.dumps({
            "ok": True,
            "occurrences": len(occurrences),
            "entries": len(counts),
            "occurrencesFile": str(out),
        })

    # ------------------------------------------------------------------ #
    # Tool 4: uplift_report                                                #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    def uplift_report(scenario: str, title: str, work_dir: str = ".uplift",
                      generated_by: str = "bob", verification_file: Optional[str] = None,
                      library: Optional[str] = None, lib_from: Optional[str] = None,
                      lib_to: Optional[str] = None) -> str:
        """Assemble a full Uplift report from whatever .uplift/*.json files exist.

        Reads work_dir/graph.json (required; prefers .uplift/<scenario>), plus verdicts.json, proofs.json,
        catalog.json, occurrences.json, and repair-*-<scenario>.json if present.
        Writes reports/<scenario>.json and validates it.

        Args:
            scenario: Scenario ID (e.g. "s1-null-user").
            title:    Human-readable scenario title.

        Returns JSON string: {"ok": bool, "reportFile": str, "valid": bool,
                              "risk": int, "mode": str}
        """
        from uplift.report import build_report

        import re
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", scenario):
            return json.dumps({"ok": False, "error": "Invalid scenario id"})
        work = Path(work_dir)
        if work_dir == ".uplift" and (work / scenario).is_dir():
            work = work / scenario
        graph_path = work / "graph.json"
        if not graph_path.exists():
            return json.dumps({"ok": False, "error": ".uplift/graph.json not found — run uplift_graph first"})

        graph = json.loads(graph_path.read_text(encoding="utf-8"))

        verdicts = None
        vp = work / "verdicts.json"
        if vp.exists():
            verdicts = json.loads(vp.read_text(encoding="utf-8"))

        proofs = None
        pp = work / "proofs.json"
        if pp.exists():
            raw = json.loads(pp.read_text(encoding="utf-8"))
            proofs = raw.get("proofs", raw) if isinstance(raw, dict) else raw

        repair_dicts: list[dict] = []
        for rpath in sorted(_glob.glob(str(work / "repair-*.json"))):
            try:
                repair_dicts.append(json.loads(Path(rpath).read_text(encoding="utf-8")))
            except Exception as exc:
                return json.dumps({"ok": False, "error": f"Invalid repair artifact: {rpath}: {exc}"})

        catalog = None
        cp = work / "catalog.json"
        if library and cp.exists():
            catalog = json.loads(cp.read_text(encoding="utf-8"))

        occurrences_data = None
        op = work / "occurrences.json"
        if library and op.exists():
            raw_occ = json.loads(op.read_text(encoding="utf-8"))
            occurrences_data = raw_occ.get("occurrences", raw_occ) if isinstance(raw_occ, dict) else raw_occ

        rpt = build_report(
            graph=graph,
            verdicts=verdicts,
            proofs=proofs,
            repair_files=repair_dicts,
            catalog=catalog,
            scenario_id=scenario,
            title=title,
            bob_modes=[],
            occurrences=occurrences_data,
            library=library, lib_from=lib_from, lib_to=lib_to,
            generated_by=generated_by,
            verified=verification_file is not None,
            verification=json.loads(Path(verification_file).read_text(encoding="utf-8-sig")) if verification_file else None,
            conventions=json.loads((work / "conventions.json").read_text(encoding="utf-8-sig")) if (work / "conventions.json").exists() else None,
        )

        out = Path(f"reports/{scenario}.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rpt, indent=2), encoding="utf-8")

        # Validate
        valid = True
        try:
            import jsonschema
            schema_path = next(
                p for p in [
                    Path("schema/report.schema.json"),
                    Path("../schema/report.schema.json"),
                ]
                if p.exists()
            )
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            jsonschema.validate(rpt, schema)
        except Exception:
            valid = False

        return json.dumps({
            "ok": valid,
            "reportFile": str(out),
            "valid": valid,
            "risk": rpt["risk"]["score"],
            "mode": rpt["mode"],
        })

    return mcp


def run() -> None:
    """Entry point for `uplift mcp` — starts the server on stdio."""
    mcp = build_mcp()
    mcp.run()
