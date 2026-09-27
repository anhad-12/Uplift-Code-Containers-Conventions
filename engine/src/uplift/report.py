"""report.py — assemble a validated Uplift report from graph + verdict files.

Public API
----------
risk(affected, contracts, untested) -> dict
build_report(graph, verdicts, proofs, repairs, catalog, scenario_id, title, bob_modes, verified) -> dict
"""
from __future__ import annotations

import glob as _glob
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _module_of(file_path: str) -> str:
    """Derive module name from a repo-relative file path (e.g. shop/users/schemas.py → users)."""
    parts = file_path.replace("\\", "/").split("/")
    try:
        shop_idx = parts.index("shop")
        if shop_idx + 1 < len(parts):
            return parts[shop_idx + 1]
    except ValueError:
        pass
    return "core"


# ---------------------------------------------------------------------------
# Risk scoring
# ---------------------------------------------------------------------------

def risk(
    affected: list[dict],
    contracts: list[dict],
    untested: list[str],
) -> dict:
    """Compute the risk score from affected items, contracts, and untested ids.

    score = min(100, 10*willBreak + 4*mightBreak + 12*untestedAffected + 15*contractHits)
    low<30, medium<60, high<80, critical>=80
    """
    wb = sum(1 for a in affected if a["verdict"] == "will_break")
    mb = sum(1 for a in affected if a["verdict"] == "might_break")
    ch = sum(1 for c in contracts if c["verdict"] in ("will_break", "might_break"))
    ut = len(untested)
    score = min(100, 10 * wb + 4 * mb + 12 * ut + 15 * ch)
    level = (
        "low" if score < 30
        else "medium" if score < 60
        else "high" if score < 80
        else "critical"
    )
    factors = [
        f"{wb} will_break (+{10 * wb})",
        f"{mb} might_break (+{4 * mb})",
        f"{ut} untested affected item (+{12 * ut})",
        f"{ch} contract hit (+{15 * ch})",
    ]
    return {"score": score, "level": level, "factors": factors}


# ---------------------------------------------------------------------------
# Build report
# ---------------------------------------------------------------------------

def build_report(
    graph: dict,
    verdicts: Optional[list[dict]],
    proofs: Optional[list[dict]],
    repair_files: list[dict],
    catalog: Optional[dict],
    scenario_id: str,
    title: str,
    bob_modes: list[str],
    verified: bool = False,
    occurrences: Optional[list[dict]] = None,
    library: Optional[str] = None,
    lib_from: Optional[str] = None,
    lib_to: Optional[str] = None,
) -> dict:
    """Assemble a full report dict that validates against schema/report.schema.json.

    Parameters
    ----------
    graph:        Parsed contents of .uplift/graph.json (from `uplift graph`).
    verdicts:     Parsed array from .uplift/verdicts.json, or None.
    proofs:       Parsed array from .uplift/proofs.json, or None.
    repair_files: List of parsed dicts from .uplift/repair-*.json files.
    catalog:      Parsed .uplift/catalog.json dict, or None.
    scenario_id:  Scenario identifier, e.g. "s1-null-user".
    title:        Human-readable scenario title.
    bob_modes:    List of Bob mode names used (for provenance.bobModes).
    verified:     If True, pipeline.verify = "done".
    """
    t0 = time.monotonic()

    # ---- verdicts lookup: {candidate_id -> {verdict, reason, fix}} -----------
    verdict_map: dict[str, dict] = {}
    if verdicts:
        for v in verdicts:
            vid = v.get("id", "")
            if vid:
                verdict_map[vid] = v

    # ---- proofs lookup: {candidate_id -> proof dict} -------------------------
    proof_map: dict[str, dict] = {}
    if proofs:
        for p in proofs:
            pid = p.get("id", p.get("item", ""))
            if pid:
                proof_map[pid] = p

    # ---- repair lookup: {candidate_id -> repair dict} ------------------------
    # Each repair file may contain a list of repairs under "repairs" key,
    # or be a single repair object with an "id" field.
    repair_map: dict[str, dict] = {}
    repair_tests_before: Optional[dict] = None
    repair_tests_after: Optional[dict] = None
    for rfile in repair_files:
        repairs_list = rfile.get("repairs", [])
        for r in repairs_list:
            rid = r.get("id", "")
            if rid:
                repair_map[rid] = r
        # per-file tests.before/after (take last one seen)
        if "tests" in rfile:
            tb = rfile["tests"].get("before")
            ta = rfile["tests"].get("after")
            if tb is not None:
                repair_tests_before = tb
            if ta is not None:
                repair_tests_after = ta

    # ---- build affected list -------------------------------------------------
    candidates: list[dict] = graph.get("candidates", [])
    affected: list[dict] = []
    for c in candidates:
        cid = c["id"]
        v = verdict_map.get(cid, {})
        verdict = v.get("verdict", "unknown")

        proof_raw = proof_map.get(cid, {})
        proof: dict = {"status": proof_raw.get("status", "not_attempted")}
        if "testFile" in proof_raw:
            proof["testFile"] = proof_raw["testFile"]
        if "passesOnBase" in proof_raw:
            proof["passesOnBase"] = proof_raw["passesOnBase"]
        if "failsOnHead" in proof_raw:
            proof["failsOnHead"] = proof_raw["failsOnHead"]

        item: dict = {
            "id": cid,
            "file": c["file"],
            "line": c["line"],
            "hop": c["hop"],
            "layer": c.get("layer", "direct"),
            "verdict": verdict,
            "reason": v.get("reason", ""),
            "fix": v.get("fix", ""),
            "proof": proof,
        }
        # Optional fields from graph
        for opt_key in ("module", "via", "snippet", "tests"):
            if opt_key in c:
                item[opt_key] = c[opt_key]
        # Repair
        if cid in repair_map:
            item["repair"] = repair_map[cid]

        affected.append(item)

    # ---- contracts: update verdicts from verdict_map -------------------------
    raw_contracts: list[dict] = graph.get("contracts", [])
    contracts: list[dict] = []
    for ct in raw_contracts:
        handler = ct.get("handler", "")
        v = verdict_map.get(handler, {})
        verdict = v.get("verdict", ct.get("verdict", "unknown"))
        entry = {**ct, "verdict": verdict}
        contracts.append(entry)

    # ---- untested + risk -----------------------------------------------------
    untested: list[str] = graph.get("untested", [])
    rk = risk(affected, contracts, untested)

    # ---- metrics -------------------------------------------------------------
    predicted = sum(1 for a in affected if a["verdict"] == "will_break") + \
                sum(1 for c in contracts if c["verdict"] == "will_break")
    confirmed = sum(1 for a in affected if a.get("proof", {}).get("status") == "confirmed")
    unconfirmed = sum(1 for a in affected if a.get("proof", {}).get("status") == "unconfirmed")
    fixed = sum(1 for a in affected if a.get("repair", {}).get("status") == "fixed")

    metrics: dict = {
        "filesScanned": graph.get("filesScanned", 0),
        "secondsTaken": round(graph.get("secondsTaken", 0.0) + (time.monotonic() - t0), 1),
        "predicted": predicted,
        "confirmed": confirmed,
        "unconfirmed": unconfirmed,
        "fixed": fixed,
        "regressions": 0,
    }
    if repair_tests_before is not None or repair_tests_after is not None:
        metrics["tests"] = {}
        if repair_tests_before is not None:
            metrics["tests"]["before"] = repair_tests_before
        if repair_tests_after is not None:
            metrics["tests"]["after"] = repair_tests_after

    # ---- pipeline ------------------------------------------------------------
    pipeline = {
        "predict": "done",
        "prove": "done" if proofs else "pending",
        "repair": "done" if repair_files else "pending",
        "verify": "done" if verified else "pending",
    }

    # ---- provenance ----------------------------------------------------------
    generated_by = "bob" if verdicts is not None else "engine"
    provenance: dict = {
        "generatedBy": generated_by,
        "bobModes": bob_modes,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }

    # ---- change (from graph metadata if present, else defaults) --------------
    change: dict = graph.get("change", {
        "summary": f"Scenario {scenario_id}",
        "kind": "patch",
    })
    if "summary" not in change:
        change["summary"] = f"Scenario {scenario_id}"
    if "kind" not in change:
        change["kind"] = "patch"

    # ---- migration (from catalog + occurrences if present) ------------------
    migration = None
    mode = "impact"
    if catalog or occurrences is not None:
        mode = "migrate"
        if isinstance(catalog, list):
            catalog_entries = catalog
            catalog_modules = []
            catalog_release_notes = None
        else:
            catalog_entries = catalog.get("catalog", []) if catalog else []
            catalog_modules = catalog.get("modules", []) if catalog else []
            catalog_release_notes = catalog.get("releaseNotes") if catalog else None
        migration = {
            "catalog": catalog_entries,
            "modules": catalog_modules,
        }
        if catalog_release_notes:
            migration["releaseNotes"] = catalog_release_notes

    # If we have occurrences, build affected[] from them and override changedSymbols
    if occurrences is not None and library:
        via_id = f"requirements.txt#{library}"
        changed_sym = [{"id": via_id, "kind": "dependency", "changeType": "dependency"}]
        occ_affected: list[dict] = []
        verdict_map_local = verdict_map.copy()
        for occ in occurrences:
            file_path = occ.get("file", "")
            module = occ.get("module") or _module_of(file_path)
            enc = occ.get("enclosing") or module
            item_id = f"{file_path}#{enc}"
            v_entry = verdict_map_local.get(item_id, {})
            verdict = v_entry.get("verdict", "unknown")
            occ_affected.append({
                "id": item_id,
                "file": file_path,
                "line": occ.get("line", 0),
                "hop": 1,
                "layer": "direct",
                "via": via_id,
                "verdict": verdict,
                "reason": v_entry.get("reason", ""),
                "fix": v_entry.get("fix", ""),
                "proof": {"status": "not_attempted"},
                "module": module,
            })
        # Deduplicate by id
        seen_ids: set[str] = set()
        deduped: list[dict] = []
        for item in occ_affected:
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                deduped.append(item)
        affected = deduped
        # Recompute risk for migrate mode
        rk = risk(affected, contracts, untested)
        predicted = sum(1 for a in affected if a["verdict"] == "will_break")
        confirmed = sum(1 for a in affected if a.get("proof", {}).get("status") == "confirmed")
        metrics["predicted"] = predicted
        metrics["confirmed"] = confirmed
        # Override change for dependency upgrade
        change = {
            "summary": f"Dependency upgrade: {library} {lib_from} -> {lib_to}" if lib_from and lib_to else f"Dependency upgrade: {library}",
            "kind": "dependency-upgrade",
        }
        if library:
            change["library"] = library
        if lib_from:
            change["from"] = lib_from
        if lib_to:
            change["to"] = lib_to
        graph["changedSymbols"] = changed_sym

    return {
        "schemaVersion": 1,
        "mode": mode,
        "provenance": provenance,
        "scenario": {"id": scenario_id, "title": title},
        "change": change,
        "changedSymbols": graph.get("changedSymbols", []),
        "affected": affected,
        "contracts": contracts,
        "testsToRun": graph.get("testsToRun", []),
        "untested": untested,
        "risk": rk,
        "pipeline": pipeline,
        "migration": migration,
        "metrics": metrics,
    }
