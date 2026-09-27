"""
Compute prediction accuracy for an Uplift impact report against ground truth.

Usage:
    python scripts/accuracy.py --report <report.json> --truth <expected.json>

The report's affected items whose verdict is will_break or might_break form the
predicted_broken set (changed symbols are excluded).  The truth_broken set is every
item in the expected.json whose "expected" field is "will_break".  Items that appear
in truth but are absent from the report count as false negatives.
"""

import argparse
import json


def accuracy(
    predicted_broken: set[str],
    truth_broken: set[str],
    truth_all: set[str],
) -> dict:
    tp = len(predicted_broken & truth_broken)
    fp = len(predicted_broken - truth_broken)
    fn = len(truth_broken - predicted_broken)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "precision": round(precision, 2),
        "recall": round(recall, 2),
        "truePositives": tp,
        "falsePositives": fp,
        "falseNegatives": fn,
    }


def evaluate(report: dict, truth: dict) -> dict:
    """Reject mismatched inputs before calculating candidate-only metrics."""
    if not isinstance(report, dict) or not isinstance(truth, dict):
        raise ValueError("Report and truth must be objects")
    scenario = report.get("scenario", {})
    if not isinstance(scenario, dict) or not scenario.get("id"):
        raise ValueError("Report must contain scenario.id")
    if scenario["id"] != truth.get("scenario"):
        raise ValueError("Report and truth scenarios do not match")
    if report.get("mode") != "impact":
        raise ValueError("Accuracy requires an impact report")
    changed = report.get("changedSymbols")
    if not isinstance(changed, list) or not all(isinstance(x, dict) and isinstance(x.get("id"), str) for x in changed):
        raise ValueError("changedSymbols must contain symbol ids")
    changed_ids = {x["id"] for x in changed}
    if not truth.get("changedSymbol") or truth["changedSymbol"] not in changed_ids:
        raise ValueError("Ground-truth changedSymbol is absent from the report")
    affected, items = report.get("affected"), truth.get("items")
    if not isinstance(affected, list) or not isinstance(items, list) or not items:
        raise ValueError("affected and nonempty truth items must be lists")
    for rows, field, allowed in [
        (affected, "verdict", {"will_break", "might_break", "safe", "unknown"}),
        (items, "expected", {"will_break", "safe"}),
    ]:
        seen = set()
        for item in rows:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
                raise ValueError("Every candidate must have a nonempty string id")
            if item["id"] in seen:
                raise ValueError("Duplicate candidate id: " + item["id"])
            seen.add(item["id"])
            if item.get(field) not in allowed:
                raise ValueError("Invalid " + field + " for " + item["id"])
    predicted = {x["id"] for x in affected if x["id"] not in changed_ids and x["verdict"] in ("will_break", "might_break")}
    broken = {x["id"] for x in items if x["expected"] == "will_break"}
    return {"accuracy": accuracy(predicted, broken, {x["id"] for x in items}),
            "predicted": sorted(predicted), "truthBroken": sorted(broken),
            "falsePositives": sorted(predicted - broken),
            "falseNegatives": sorted(broken - predicted)}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Compute Uplift prediction accuracy.")
    parser.add_argument("--report", required=True, help="Path to the Uplift report JSON.")
    parser.add_argument("--truth", required=True, help="Path to the expected.json ground truth.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable results.")
    args = parser.parse_args(argv)

    try:
        with open(args.report, encoding="utf-8-sig") as f:
            report = json.load(f)
        with open(args.truth, encoding="utf-8-sig") as f:
            truth = json.load(f)
        evaluation = evaluate(report, truth)
    except (OSError, ValueError) as exc:
        parser.exit(2, "Accuracy input error: " + str(exc) + "\n")
    if args.json:
        print(json.dumps(evaluation, indent=2))
        return
    predicted_broken = set(evaluation["predicted"])
    truth_broken = set(evaluation["truthBroken"])
    result = evaluation["accuracy"]

    print(f"predicted_broken : {sorted(predicted_broken) or '(none)'}")
    print(f"truth_broken     : {sorted(truth_broken)}")
    print()
    print(f"truePositives  : {result['truePositives']}")
    print(f"falsePositives : {result['falsePositives']}")
    print(f"falseNegatives : {result['falseNegatives']}")
    print(f"precision      : {result['precision']:.2f}")
    print(f"recall         : {result['recall']:.2f}")

    missed = truth_broken - predicted_broken
    if missed:
        print(f"\nMissed (false negatives): {sorted(missed)}")

    spurious = predicted_broken - truth_broken
    if spurious:
        print(f"Spurious (false positives): {sorted(spurious)}")


if __name__ == "__main__":
    main()
