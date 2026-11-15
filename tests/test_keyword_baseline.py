import unittest
from pathlib import Path

from src.keyword_baseline import load_policy, predict
from src.score import rates

ROOT = Path(__file__).resolve().parents[1]


class KeywordBaselineTest(unittest.TestCase):
    def setUp(self):
        self.policy = load_policy(ROOT / "policy" / "prohibited_items.json")

    def test_pillow_matches_pill(self):
        result = predict("Memory foam pillow", "Queen size", self.policy)
        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["keyword"], "pill")
        self.assertEqual(result["category"], "drugs")

    def test_first_category_in_file_order_wins(self):
        result = predict("crystal knife", "for the kitchen", self.policy)
        self.assertEqual(result["category"], "weapons")
        self.assertEqual(result["keyword"], "knife")

    def test_bourbon_is_not_on_the_list(self):
        result = predict("Unopened bourbon", "Bottle of Woodford Reserve", self.policy)
        self.assertEqual(result["decision"], "allow")

    def test_digit_in_glock_is_a_miss(self):
        result = predict("Gl0ck nineteen", "Nine mil", self.policy)
        self.assertEqual(result["decision"], "allow")

    def test_match_is_case_insensitive(self):
        result = predict("GLOCK", "swap", self.policy)
        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["keyword"], "glock")


class ScoreTest(unittest.TestCase):
    def test_rates_for_an_even_split(self):
        result = rates({"tp": 1, "fp": 1, "tn": 1, "fn": 1})
        self.assertEqual(result["precision"], 0.5)
        self.assertEqual(result["recall"], 0.5)
        self.assertEqual(result["fpr"], 0.5)
        self.assertEqual(result["f1"], 0.5)
        self.assertEqual(result["n"], 4)


if __name__ == "__main__":
    unittest.main()
