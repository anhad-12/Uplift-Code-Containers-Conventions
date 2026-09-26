"""comment.py — generate a Markdown PR comment from an Uplift report.

Public API
----------
pr_comment(report: dict) -> str
"""
from __future__ import annotations

# Verdict sort order: most severe first.
_VERDICT_ORDER = ["will_break", "might_break", "unknown", "safe"]


def pr_comment(report: dict) -> str:
    """Return a Markdown PR comment string for *report*.

    If no item has a real verdict (all are 'unknown'), the comment says
    "Graph only. Verdicts, proofs and repairs come from a Bob run."
    """
    r = report["risk"]
    m = report["metrics"]
    scenario_title = report["scenario"]["title"]

    factors_str = "; ".join(r.get("factors", []))
    lines: list[str] = [
        f"### Uplift: what `{scenario_title}` will break",
        "",
        f"**Risk {r['score']}/100 ({r['level']})** - {factors_str}",
        "",
    ]

    has_verdicts = any(
        a["verdict"] != "unknown" for a in report.get("affected", [])
    )
    if not has_verdicts:
        lines += [
            "_Graph only. Verdicts, proofs and repairs come from a Bob run._",
            "",
        ]

    lines += ["| Item | Verdict | Proof | Reason |", "| --- | --- | --- | --- |"]

    def _sort_key(item: dict) -> int:
        try:
            return _VERDICT_ORDER.index(item["verdict"])
        except ValueError:
            return len(_VERDICT_ORDER)

    for a in sorted(report.get("affected", []), key=_sort_key):
        proof_status = (a.get("proof") or {}).get("status", "-")
        reason = a.get("reason", "")
        lines.append(f"| `{a['id']}` | {a['verdict']} | {proof_status} | {reason} |")

    if report.get("contracts"):
        contract_parts = ", ".join(
            f"`{c['id']}` ({c['verdict']})" for c in report["contracts"]
        )
        lines += ["", f"**API contracts:** {contract_parts}"]

    if report.get("untested"):
        untested_parts = ", ".join(f"`{u}`" for u in report["untested"])
        lines += ["", f"**Untested affected code:** {untested_parts}"]

    tests_str = ", ".join(report.get("testsToRun", [])) or "none"
    lines += [
        "",
        f"**Tests to run:** {tests_str}",
        "",
        (
            f"predicted {m['predicted']}, confirmed {m['confirmed']}, "
            f"fixed {m.get('fixed', 0)}, regressions {m.get('regressions', 0)}"
        ),
    ]

    return "\n".join(lines)
