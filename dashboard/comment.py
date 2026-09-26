"""PR comment generator for Uplift reports."""
from __future__ import annotations

BADGE = {"low": "green", "medium": "yellow", "high": "orange", "critical": "red"}


def pr_comment(report: dict) -> str:
    r, m = report["risk"], report["metrics"]
    lines = [f"### Uplift: what `{report['scenario']['title']}` will break", "",
             f"**Risk {r['score']}/100 ({r['level']})** - {'; '.join(r.get('factors', []))}", ""]
    has_verdicts = any(a["verdict"] != "unknown" for a in report["affected"])
    if not has_verdicts:
        lines += ["_Graph only. Verdicts, proofs and repairs come from a Bob run._", ""]
    lines += ["| Item | Verdict | Proof | Reason |", "| --- | --- | --- | --- |"]
    for a in sorted(report["affected"], key=lambda a: ["will_break", "might_break", "unknown", "safe"].index(a["verdict"])):
        lines.append(f"| `{a['id']}` | {a['verdict']} | {(a.get('proof') or {}).get('status', '-')} | {a.get('reason', '')} |")
    if report.get("contracts"):
        lines += ["", "**API contracts:** " + ", ".join(f"`{c['id']}` ({c['verdict']})" for c in report["contracts"])]
    if report.get("untested"):
        lines += ["", "**Untested affected code:** " + ", ".join(f"`{u}`" for u in report["untested"])]
    lines += ["", f"**Tests to run:** {', '.join(report.get('testsToRun', [])) or 'none'}", "",
              f"predicted {m['predicted']}, confirmed {m['confirmed']}, fixed {m.get('fixed', 0)}, regressions {m.get('regressions', 0)}"]
    return "\n".join(lines)
