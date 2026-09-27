"""Regression checks for accuracy accounting and scenario isolation."""
import copy
import unittest
from accuracy import accuracy, evaluate


class AccuracyTests(unittest.TestCase):
    def setUp(self):
        self.report = {"mode": "impact", "scenario": {"id": "s1"},
                       "changedSymbols": [{"id": "changed"}],
                       "affected": [{"id": "changed", "verdict": "will_break"},
                                    {"id": "hit", "verdict": "might_break"},
                                    {"id": "extra", "verdict": "will_break"}]}
        self.truth = {"scenario": "s1", "changedSymbol": "changed", "items": [
            {"id": "hit", "expected": "will_break"},
            {"id": "missed", "expected": "will_break"}]}

    def test_missing_candidates_and_false_positives(self):
        before = copy.deepcopy(self.report)
        result = evaluate(self.report, self.truth)
        self.assertEqual(result["accuracy"], {"precision": .5, "recall": .5,
            "truePositives": 1, "falsePositives": 1, "falseNegatives": 1})
        self.assertEqual(result["falseNegatives"], ["missed"])
        self.assertEqual(result["falsePositives"], ["extra"])
        self.assertEqual(before, self.report)

    def test_empty_predictions(self):
        self.report["affected"] = []
        self.assertEqual(evaluate(self.report, self.truth)["accuracy"]["falseNegatives"], 2)
        self.assertEqual(accuracy(set(), set(), set())["precision"], 0.0)

    def test_wrong_scenario(self):
        self.truth["scenario"] = "s2"
        with self.assertRaisesRegex(ValueError, "scenarios"):
            evaluate(self.report, self.truth)

    def test_wrong_changed_symbol(self):
        self.truth["changedSymbol"] = "another"
        with self.assertRaisesRegex(ValueError, "changedSymbol"):
            evaluate(self.report, self.truth)

    def test_duplicate_or_invalid_verdict(self):
        self.report["affected"].append(self.report["affected"][1])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            evaluate(self.report, self.truth)
        self.report["affected"].pop()
        self.report["affected"][1]["verdict"] = "broken"
        with self.assertRaisesRegex(ValueError, "Invalid"):
            evaluate(self.report, self.truth)

    def test_migration_rejected(self):
        self.report["mode"] = "migrate"
        with self.assertRaisesRegex(ValueError, "impact"):
            evaluate(self.report, self.truth)


if __name__ == "__main__":
    unittest.main()
