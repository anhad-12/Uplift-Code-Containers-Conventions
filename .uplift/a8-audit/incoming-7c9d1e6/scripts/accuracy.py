"""accuracy.py — compare an Uplift report against ground truth expected.json.

Usage:
    python scripts/accuracy.py --report reports/s2-cents.json \
                               --truth sample-app/scenarios/s2-cents.expected.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


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


def evaluate(report_path: Path, truth_path: Path) -> dict:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    truth = json.loads(truth_path.read_text(encoding="utf-8"))

    truth_items = {item["id"]: item["expected"] for item in truth.get("items", [])}
    truth_broken: set[str] = {id_ for id_, exp in truth_items.items() if exp == "will_break"}
    truth_all: set[str] = set(truth_items.keys())

    predicted_broken: set[str] = set()
    for candidate in report.get("affected", []):
        if candidate.get("verdict") in ("will_break", "might_break"):
            predicted_broken.add(candidate["id"])

    metrics = accuracy(predicted_broken, truth_broken, truth_all)

    rows = []
    all_ids = truth_all | predicted_broken
    for id_ in sorted(all_ids):
        pred = "will_break" if id_ in predicted_broken else "safe/unknown"
        truth_exp = truth_items.get(id_, "(not in truth)")
        correct = pred == truth_exp or (pred == "safe/unknown" and truth_exp not in ("will_break",))
        rows.append({"id": id_, "predicted": pred, "truth": truth_exp, "correct": correct})

    return {
        "scenario": report.get("scenario", {}).get("id", ""),
        "metrics": metrics,
        "rows": rows,
        "misses": {
            "falsePositives": sorted(predicted_broken - truth_broken),
            "falseNegatives": sorted(truth_broken - predicted_broken),
        },
    }


def _print_results(result: dict) -> None:
    scenario = result["scenario"]
    m = result["metrics"]
    print(f"\n=== {scenario} ===")
    print(f"Precision: {m['precision']:.2f}  Recall: {m['recall']:.2f}")
    print(f"TP={m['truePositives']}  FP={m['falsePositives']}  FN={m['falseNegatives']}")
    print()
    print(f"{'id':<55} {'predicted':<14} {'truth':<14} correct")
    print("-" * 100)
    for row in result["rows"]:
        mark = "✓" if row["correct"] else "✗"
        print(f"{row['id']:<55} {row['predicted']:<14} {row['truth']:<14} {mark}")
    if result["misses"]["falsePositives"]:
        print("\nFalse positives (predicted broken, actually safe):")
        for fp in result["misses"]["falsePositives"]:
            print(f"  {fp}")
    if result["misses"]["falseNegatives"]:
        print("\nFalse negatives (missed — truth says broken, we said safe/absent):")
        for fn in result["misses"]["falseNegatives"]:
            print(f"  {fn}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Uplift report accuracy")
    parser.add_argument("--report", required=True, help="Path to report JSON")
    parser.add_argument("--truth", required=True, help="Path to expected.json ground truth")
    args = parser.parse_args()
    result = evaluate(Path(args.report), Path(args.truth))
    _print_results(result)


if __name__ == "__main__":
    main()
