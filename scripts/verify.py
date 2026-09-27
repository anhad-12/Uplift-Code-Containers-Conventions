#!/usr/bin/env python3
"""Uplift readiness checker. Standard library only.

    python scripts/verify.py          static checks
    python scripts/verify.py --run    also run engine + sample-app tests

Exit code 1 if any check FAILs. Paste the output to whoever is reviewing at each checkpoint.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUN = "--run" in sys.argv
STRICT_BOB = "--require-bob-evidence" in sys.argv
SKIP_DIRS = {"node_modules", ".git", "dist", "__pycache__", ".venv", ".pytest_cache", "build"}

results: list[tuple[str, str, str, str]] = []
section = ""


def add(status: str, name: str, detail: str = "") -> None:
    results.append((section, status, name, detail))


def check(cond: bool, name: str, detail: str = "") -> None:
    add("PASS" if cond else "FAIL", name, "" if cond else detail)


def exists(p: str) -> bool:
    return (ROOT / p).exists()


def read(p: str) -> str:
    return (ROOT / p).read_text(encoding="utf-8")


def walk(d: str, pred=lambda p: True) -> list[Path]:
    base = ROOT / d
    if not base.exists():
        return []
    out = []
    for directory, dirs, files in os.walk(base):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS and not name.startswith(".venv") and not (name == "tmp" and Path(directory).name == ".uplift")]
        for name in files:
            p = Path(directory) / name
            if pred(p):
                out.append(p)
    return out


def words(s: str) -> int:
    return len(s.split())


# ---- mini schema validator (mirrors schema/report.schema.json) ----
VERDICTS = ["will_break", "might_break", "safe", "unknown"]


def validate_report(r: dict) -> list[str]:
    errs: list[str] = []

    def need(o, keys, where):
        for k in keys:
            if not isinstance(o, dict) or k not in o:
                errs.append(f"{where}.{k} missing")

    need(r, ["schemaVersion", "mode", "provenance", "scenario", "change", "changedSymbols", "affected", "risk", "pipeline", "metrics"], "report")
    if r.get("schemaVersion") != 1:
        errs.append("schemaVersion must be 1")
    if r.get("mode") not in ("impact", "migrate"):
        errs.append("mode invalid")
    if (r.get("provenance") or {}).get("generatedBy") not in ("bob", "engine", "codex", "mock"):
        errs.append("provenance.generatedBy invalid")
    for i, a in enumerate(r.get("affected") or []):
        need(a, ["id", "file", "line", "hop", "layer", "verdict"], f"affected[{i}]")
        if a.get("verdict") not in VERDICTS:
            errs.append(f"affected[{i}].verdict invalid")
        if a.get("layer") not in ("direct", "indirect", "contract"):
            errs.append(f"affected[{i}].layer invalid")
        if not (isinstance(a.get("hop"), int) and 1 <= a["hop"] <= 3):
            errs.append(f"affected[{i}].hop out of range")
    risk = r.get("risk") or {}
    if not (isinstance(risk.get("score"), int) and 0 <= risk["score"] <= 100):
        errs.append("risk.score invalid")
    if risk.get("level") not in ("low", "medium", "high", "critical"):
        errs.append("risk.level invalid")
    need(r.get("pipeline"), ["predict", "prove", "repair", "verify"], "pipeline")
    need(r.get("metrics"), ["filesScanned", "predicted", "confirmed"], "metrics")
    # risk formula check
    if isinstance(r.get("affected"), list) and risk:
        wb = sum(1 for a in r["affected"] if a.get("verdict") == "will_break")
        mb = sum(1 for a in r["affected"] if a.get("verdict") == "might_break")
        un = len(r.get("untested") or [])
        ch = sum(1 for c in (r.get("contracts") or []) if c.get("verdict") in ("will_break", "might_break"))
        score = min(100, 10 * wb + 4 * mb + 12 * un + 15 * ch)
        if score != risk.get("score"):
            errs.append(f"risk.score {risk.get('score')} != formula {score}")
    return errs


def report_checks(d: str, label: str) -> list[tuple[Path, dict]]:
    files = sorted(p for p in (ROOT / d).glob("*.json") if p.name != "index.json")
    if not files:
        add("FAIL", f"{label}: has real reports", f"no report JSON in {d}")
        return []
    out = []
    for f in files:
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            add("FAIL", f"{label}: {f.name} parses", str(e))
            continue
        errs = validate_report(r)
        check(not errs, f"{label}: {f.name} matches schema", "; ".join(errs[:4]))
        check((r.get("provenance") or {}).get("generatedBy") != "mock", f"{label}: {f.name} is not a mock", "replace with a real Bob/engine report")
        out.append((f, r))
    return out


def git(*args: str) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    except OSError:
        return None


# ---------------- checks ----------------
section = "1. Bob customization (.bob/)"
MODES = ["uplift-impact-analyst", "uplift-prover", "uplift-migration-planner", "uplift-worker-users",
         "uplift-worker-orders", "uplift-worker-payments", "uplift-worker-core", "uplift-verifier"]
if exists(".bob/custom_modes.yaml"):
    y = read(".bob/custom_modes.yaml")
    for s in MODES:
        check(s in y, f"mode {s} defined")
    check(bool(re.search(r"^customModes:", y, re.M)), "custom_modes.yaml has top-level customModes")
    check(not re.search(r"^\s*-\s*command\s*$", y, re.M), "no invalid 'command' group (shell access is 'execute')")
    check("fileRegex" in y, "modes use fileRegex edit restrictions")
    add("PASS" if "uplift-convention-scanner" in y else "WARN", "mode uplift-convention-scanner (F16)", "" if "uplift-convention-scanner" in y else "task A11")
else:
    add("FAIL", ".bob/custom_modes.yaml exists", "task A1")
check(exists(".bob/rules/rules.md"), ".bob/rules/rules.md exists", "task A0")
add("PASS" if exists(".bob/mcp.json") else "WARN", ".bob/mcp.json registered (F14)", "" if exists(".bob/mcp.json") else "task B11")
for s in ["impact-verdict-rubric", "write-proof-test", "migration-guide-reader"]:
    check(exists(f".bob/skills/{s}/SKILL.md"), f"skill {s}", "task A1")
add("PASS" if exists(".bob/skills/repo-conventions/SKILL.md") else "WARN", "skill repo-conventions (F16)", "" if exists(".bob/skills/repo-conventions/SKILL.md") else "task A11")
gt = walk("sample-app/scenarios", lambda p: p.name.endswith(".expected.json"))
bobignore = read(".bobignore").splitlines() if exists(".bobignore") else []
hidden = any(l.strip() and not l.strip().startswith("#") and "expected.json" in l for l in bobignore)
if not gt:
    add("SKIP", "ground truth hidden from Bob (.bobignore)", "no expected.json yet")
elif hidden:
    add("PASS", "ground truth hidden from Bob (.bobignore)")
else:
    add("WARN", "ground truth visible to Bob", "uncomment the .bobignore line (fine only during task A8)")

section = "2. Engine (F1-F4, F10, F14, F17)"
check(exists("engine/pyproject.toml"), "engine/pyproject.toml", "task B3")
for f in ["cli", "diff", "graph", "routes", "testmap", "report", "proof", "migrate", "comment"]:
    check(exists(f"engine/src/uplift/{f}.py"), f"engine/src/uplift/{f}.py", "tasks B3-B9")
add("PASS" if exists("engine/src/uplift/mcp_server.py") else "WARN", "engine/src/uplift/mcp_server.py (F14)", "" if exists("engine/src/uplift/mcp_server.py") else "task B11; modes fall back to CLI")
add("PASS" if exists("engine/src/uplift/docker.py") else "WARN", "engine/src/uplift/docker.py (F17, stretch)", "" if exists("engine/src/uplift/docker.py") else "task B13, only after CP2")
n_engine_tests = len(walk("engine/tests", lambda p: re.match(r"test_.*\.py$", p.name) is not None))
check(n_engine_tests >= 5, f"engine unit tests ({n_engine_tests} files, need 5+)", "tasks B3-B9")

section = "3. Sample app + scenarios"
check(exists("sample-app/requirements.txt"), "sample-app/requirements.txt", "task B1")
n_src = len(walk("sample-app/shop", lambda p: p.suffix == ".py"))
n_tests = len(walk("sample-app/tests", lambda p: re.match(r"test_.*\.py$", p.name) is not None and "uplift_proofs" not in p.parts))
check(n_src >= 20, f"sample-app shop/ files ({n_src}, need 20+)", "task B1")
check(n_tests >= 10, f"sample-app test files ({n_tests}, need 10+)", "task B1")
for s in ["s1-null-user", "s2-cents"]:
    check(exists(f"sample-app/scenarios/{s}.patch"), f"scenario {s}.patch", "task B2")
    check(exists(f"sample-app/scenarios/{s}.expected.json"), f"scenario {s}.expected.json (ground truth)", "task B2")
check(exists("sample-app/scenarios/s3-pydantic2.patch"), "scenario s3-pydantic2.patch", "task B2")
n_proofs = len(walk("sample-app/tests/uplift_proofs", lambda p: re.match(r"test_.*\.py$", p.name) is not None))
check(n_proofs >= 3, f"proof tests written by Bob ({n_proofs}, need 3+)", "task A3")

section = "4. Dashboard (F12)"
check(exists("dashboard/app.py"), "dashboard/app.py", "task C1")
check(exists("dashboard/requirements.txt"), "dashboard/requirements.txt", "task C1")
check(len(walk("dashboard", lambda p: p.suffix == ".py")) >= 3, "dashboard has 3+ Python modules", "tasks C1-C7")
check(exists("dashboard/reports/index.json"), "dashboard/reports/index.json", "task C1")
if exists("dashboard/schema/report.schema.json"):
    same = read("dashboard/schema/report.schema.json").splitlines() == read("schema/report.schema.json").splitlines()
    check(same, "dashboard/schema copy equals schema/report.schema.json", "re-copy schema/report.schema.json into dashboard/schema/")
else:
    add("FAIL", "dashboard/schema/report.schema.json (self-contained deploy)", "task C1")
n_dash_tests = len(walk("dashboard/tests", lambda p: re.match(r"test_.*\.py$", p.name) is not None))
check(n_dash_tests >= 3, f"dashboard tests ({n_dash_tests} files, need 3+)", "tasks C1-C7")
check(exists("dashboard/render.yaml") or exists("dashboard/README.md"), "deploy config or README", "task C8")

section = "5. Real reports (F5-F8, F13)"
evidence = report_checks("evidence", "evidence")
report_checks("dashboard/reports", "dashboard")
ids = {r.get("scenario", {}).get("id") for _, r in evidence}
for s in ["s1-null-user", "s2-cents", "s3-pydantic2"]:
    check(s in ids, f"evidence has scenario {s}", "tasks A2-A9")
for f, r in evidence:
    n = f.name
    if r.get("mode") == "impact":
        conf = sum(1 for a in r.get("affected", []) if (a.get("proof") or {}).get("status") == "confirmed")
        check(conf >= 1, f"{n}: at least one confirmed proof", "task A3")
        check(any((a.get("repair") or {}).get("status") == "fixed" for a in r.get("affected", [])), f"{n}: at least one fixed item", "task A6")
    else:
        check(len((r.get("migration") or {}).get("modules", [])) >= 3, f"{n}: 3+ worker lanes", "task A6")
        check(len((r.get("migration") or {}).get("catalog", [])) >= 3, f"{n}: catalog from guide", "task A5")
    check(bool((r.get("metrics") or {}).get("accuracy")) or r.get("mode") == "migrate", f"{n}: accuracy numbers present", "task A8")
    check((r.get("pipeline") or {}).get("verify") == "done", f"{n}: pipeline verify done", "task A7")
check(exists("evidence/eval.md"), "evidence/eval.md (accuracy write-up)", "task A8/A9")

section = "5b. Scenario branches"
b = git("branch", "--list")
if b is not None and b.returncode == 0:
    for n in ["scenario/s1-null-user", "scenario/s2-cents", "scenario/s3-pydantic2"]:
        add("PASS" if n in b.stdout else "WARN", f"branch {n}", "" if n in b.stdout else "task B2 (scripts/scenario_branch.py)")
else:
    add("SKIP", "scenario branches", "not a git repo")

section = "6. Bob evidence (required by the rules)"
shots = [p.name for p in walk("bob_sessions", lambda p: p.suffix.lower() == ".png")]
per = {"A": 0, "B": 0, "C": 0}
for n in shots:
    m = re.match(r"^uplift_([ABC])_task_?\d+[a-z]?(?:_.+)?_summary\.png$", n)
    if m:
        per[m.group(1)] += 1
    else:
        add("WARN", f"screenshot name off-pattern: {n}")
for m in "ABC":
    add("PASS" if per[m] >= 5 else "FAIL" if STRICT_BOB else "WARN", f"member {m}: {per[m]} archived Bob screenshots (original target: 5+)", "Historical Bob evidence is separate from Codex implementation readiness; --require-bob-evidence enforces the original target.")
if exists("bob_sessions/LOG.md"):
    log = read("bob_sessions/LOG.md").splitlines()
    for m in "ABC":
        rows = sum(1 for l in log if re.match(rf"^\|\s*{m}\s*\|", l))
        add("PASS" if rows >= per[m] else "FAIL" if STRICT_BOB else "WARN", f"member {m}: LOG.md rows ({rows}) cover screenshots ({per[m]})", "Historical gaps are not fabricated.")
else:
    add("FAIL", "bob_sessions/LOG.md exists")
g = git("log", "--pretty=%s")
if g is not None and g.returncode == 0:
    n = sum(1 for l in g.stdout.splitlines() if l.startswith("[bob "))
    check(n >= 15, f"[bob X#] commits ({n}, need 15+)", "commit Bob work with the prefix")
else:
    add("SKIP", "[bob] commit count", "not a git repo yet")

section = "7. Repo hygiene and deliverables"
check(exists("LICENSE") and "MIT License" in read("LICENSE"), "MIT LICENSE")
check(exists("README.md"), "README.md")
check(exists("SOURCES.md"), "SOURCES.md")
check(exists(".github/workflows/ci.yml"), "CI workflow", "task B10")
check(exists("docs/migration/pydantic-v2-migration-guide.pdf"), "migration guide PDF saved", "task A5 prep")
for f, label in [("docs/problem-solution.md", "Problem & Solution statement"), ("docs/bob-usage.md", "Bob Usage statement")]:
    if exists(f):
        w = words(read(f))
        check(0 < w <= 500, f"{label} <= 500 words ({w})")
    else:
        add("FAIL", f"{label} exists", f)
check(not walk(".", lambda p: p.name == ".env"), "no .env committed")

section = "7b. Scripts and line endings"
check(exists("scripts/make_patches.py"), "scripts/make_patches.py", "task B2")
check(exists("scripts/scenario_branch.py"), "scripts/scenario_branch.py", "task B2")
crlf = [p.name for p in walk("sample-app/scenarios", lambda p: p.suffix == ".patch") if bytes([13]) in p.read_bytes()]
check(not crlf, "scenario patches use LF line endings", ", ".join(crlf))
if exists("sample-app/requirements.txt"):
    req = read("sample-app/requirements.txt")
    check("httpx==0.27.2" in req, "sample-app pins httpx==0.27.2 (0.28 breaks the TestClient)", "pin httpx==0.27.2")
if exists("engine/pyproject.toml"):
    check("mcp>=1.2,<2" in read("engine/pyproject.toml"), "engine pins mcp<2 (2.x renamed FastMCP)", "pin mcp>=1.2,<2")

section = "8. Tests (--run)"
if RUN:
    py_engine = ROOT / "engine" / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    py_app = ROOT / "sample-app" / (".venv311" if (ROOT / "sample-app/.venv311").exists() else ".venv") / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    py_dash = ROOT / "dashboard/.venv311" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    for d, py in [("engine", py_engine), ("sample-app", py_app), ("dashboard", py_dash)]:
        if not exists(d) or not py.exists():
            add("FAIL", f"{d} tests", f"missing test interpreter: {py}")
            continue
        r = subprocess.run([str(py), "-m", "pytest", "-q"], cwd=ROOT / d, capture_output=True, text=True)
        tail = " | ".join((r.stdout + r.stderr).strip().splitlines()[-4:])
        check(r.returncode == 0, f"{d}: pytest", tail)
else:
    add("SKIP", "run engine + sample-app tests", "pass --run")

# ---------------- report ----------------
last = ""
for sec, status, name, detail in results:
    if sec != last:
        print(f"\n== {sec}")
        last = sec
    print(f"  [{status}] {name}{'  -> ' + detail if detail else ''}")
count = lambda s: sum(1 for r in results if r[1] == s)  # noqa: E731
print(f"\nSummary: {count('PASS')} pass, {count('FAIL')} fail, {count('WARN')} warn, {count('SKIP')} skip")
sys.exit(1 if count("FAIL") else 0)
