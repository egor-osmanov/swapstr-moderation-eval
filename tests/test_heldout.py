import json
import unittest
from pathlib import Path

from src.keyword_baseline import find_keywords, load_policy
from src.run_claude_eval import MODEL, ROOT, output_path

HELD_OUT = ROOT / "dataset" / "heldout.jsonl"
LISTINGS = ROOT / "dataset" / "listings.jsonl"
POLICY = load_policy(ROOT / "policy" / "prohibited_items.json")
FIELDS = {
    "id",
    "title",
    "description",
    "gold",
    "category",
    "slice",
    "adversarial_type",
    "note",
}


def load(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


class HeldOutTest(unittest.TestCase):
    def test_thirty_new_rows_stay_out_of_the_published_set(self):
        rows = load(HELD_OUT)
        published = {row["id"] for row in load(LISTINGS)}
        self.assertEqual(len(rows), 30)
        self.assertEqual([row["id"] for row in rows], [f"ho-{index:03d}" for index in range(1, 31)])
        self.assertTrue(published.isdisjoint(row["id"] for row in rows))
        for row in rows:
            self.assertEqual(set(row), FIELDS)
            if row["gold"] == "allow":
                self.assertEqual(row["category"], "none")
            else:
                self.assertIn(row["category"], POLICY["categories"])

    def test_plain_allows_do_not_contain_a_banned_substring(self):
        for row in load(HELD_OUT):
            if row["slice"] != "allow_clear":
                continue
            found = find_keywords(row["title"], row["description"], POLICY)
            self.assertEqual(found, [], row["id"])

    def test_heldout_scores_get_their_own_file(self):
        listings = HELD_OUT
        prompt = ROOT / "prompts" / "classifier_v2.md"
        out = output_path(prompt, MODEL, listings)
        self.assertEqual(out.name, "heldout_classifier_v2.json")
        sonnet = output_path(prompt, "claude-sonnet-5-5", listings)
        self.assertNotEqual(sonnet.name, "claude_classifier_v2.json")
