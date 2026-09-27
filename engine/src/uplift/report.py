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
from copy import deepcopy
from pathlib import Path
from typing import Optional


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
    generated_by: Optional[str] = None,
    verification: Optional[dict] = None,
    conventions: Optional[dict] = None,
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
    graph = deepcopy(graph)
    if isinstance(proofs, dict):
        proofs = proofs.get("proofs", [])
    if isinstance(catalog, list):
        catalog = {"catalog": catalog}
    for repair in repair_files:
        if repair.get("scenario", scenario_id) != scenario_id:
            raise ValueError("Repair belongs to another scenario")
    if verified and (not verification or verification.get("failed", 0) or
                     verification.get("errors", 0) or verification.get("passed", 0) <= 0 or
                     verification.get("exitCode", 0) != 0):
        raise ValueError("Verification requires a successful, nonempty full-suite result")


    if occurrences is not None and library and graph.get("change", {}).get("kind") != "dependency-upgrade":
        dependency = f"requirements.txt#{library}"
        graph["changedSymbols"] = [{"id": dependency, "kind": "dependency", "changeType": "dependency"}]
        unique = {}
        for occ in occurrences:
            item_id = f"{occ['file']}#{occ.get('enclosing') or occ['module']}"
            unique.setdefault(item_id, {"id": item_id, "file": occ["file"], "line": occ["line"],
                                        "hop": 1, "layer": "direct", "via": dependency, "module": occ["module"]})
        graph["candidates"] = list(unique.values())
        graph["change"] = {"summary": f"Dependency upgrade: {library} {lib_from or ''} -> {lib_to or ''}",
                           "kind": "dependency-upgrade", "library": library}
        if lib_from:
            graph["change"]["from"] = lib_from
        if lib_to:
            graph["change"]["to"] = lib_to

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
                proof_map[pid] = dict(p)
                if p.get("status") == "confirmed" and not (p.get("passesOnBase") is True and p.get("failsOnHead") is True):
                    proof_map[pid]["status"] = "unconfirmed"

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
        else:
            for repair in repair_files:
                # Module repair files must explicitly name repaired ids; a changed file
                # alone cannot establish that every function in it was repaired.
                if cid in repair.get("fixedIds", []) and not repair.get("blocked"):
                    after = repair.get("testsAfter", {})
                    if after.get("passed", 0) > 0 and not after.get("failed", 0) and not after.get("errors", 0):
                        item["repair"] = {"status": "fixed", "worker": repair.get("worker", ""),
                                          "filesChanged": repair.get("filesChanged", [])}

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
    confirmed = sum(1 for a in affected if a["verdict"] == "will_break" and a.get("proof", {}).get("status") == "confirmed")
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
        "repair": "done" if repair_files and all(not r.get("blocked") and r.get("testsAfter", {}).get("failed", 0) == 0 and r.get("testsAfter", {}).get("errors", 0) == 0 for r in repair_files) else "pending",
        "verify": "done" if verified else "pending",
    }

    # ---- provenance ----------------------------------------------------------
    generated_by = generated_by or ("bob" if verdicts is not None else "engine")
    if generated_by not in {"bob", "engine", "codex", "mock"}:
        raise ValueError("Invalid report generator")
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
        catalog_entries = catalog.get("catalog", []) if catalog else []
        catalog_modules = repair_files or (catalog.get("modules", []) if catalog else [])
        migration = {
            "catalog": catalog_entries,
            "modules": catalog_modules,
        }
        if catalog and "releaseNotes" in catalog:
            migration["releaseNotes"] = catalog["releaseNotes"]

    if verification is not None:
        metrics.setdefault("tests", {})["after"] = verification
    result = {
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

    if graph.get("infraImpact"):
        result["infraImpact"] = graph["infraImpact"]
    if conventions:
        result["conventions"] = conventions
    return result
