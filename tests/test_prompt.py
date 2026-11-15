import unittest
from pathlib import Path

from src.prompt import ROOT, listing_message, load_system_prompt


class PromptTest(unittest.TestCase):
    def test_system_prompt_starts_at_the_marker(self):
        prompt = load_system_prompt()
        self.assertTrue(prompt.startswith("You moderate listings for Swapstr"))
        self.assertNotIn("## SYSTEM", prompt)
        self.assertIn("tobacco", prompt)
        self.assertIn('"decision"', prompt)

    def test_v2_states_categories_without_the_v1_exceptions(self):
        prompt = load_system_prompt(ROOT / "prompts" / "classifier_v2.md")
        self.assertIn("tobacco", prompt)
        self.assertNotIn("kitchen knives", prompt)
        self.assertNotIn("blind box", prompt)
        self.assertNotIn("culinary", prompt)

    def test_listing_message_is_title_and_description(self):
        message = listing_message("Oak chair", "One leg is loose.")
        self.assertEqual(message, "Title: Oak chair\nDescription: One leg is loose.")


if __name__ == "__main__":
    unittest.main()
