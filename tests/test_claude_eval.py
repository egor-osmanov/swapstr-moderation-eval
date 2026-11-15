import unittest

from src.claude_eval import build_request, comparable_decision, parse_response


class ParseResponseTest(unittest.TestCase):
    def test_reads_the_text_block_and_ignores_thinking(self):
        payload = {
            "stop_reason": "end_turn",
            "content": [
                {"type": "thinking", "thinking": ""},
                {
                    "type": "text",
                    "text": '{"decision":"Block","category":"Weapons","reason":"A firearm."}',
                },
            ],
        }
        parsed = parse_response(payload)
        self.assertEqual(parsed["status"], "ok")
        self.assertEqual(parsed["decision"], "block")
        self.assertEqual(parsed["category"], "weapons")

    def test_strips_a_json_fence(self):
        payload = {
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": '```json\n{"decision":"allow","category":"none","reason":"A lamp."}\n```'}],
        }
        self.assertEqual(parse_response(payload)["decision"], "allow")

    def test_refusal_has_no_decision(self):
        parsed = parse_response({"stop_reason": "refusal", "content": []})
        self.assertEqual(parsed["status"], "refusal")
        self.assertIsNone(parsed["decision"])

    def test_invalid_json_is_a_parse_failure(self):
        payload = {"stop_reason": "end_turn", "content": [{"type": "text", "text": "sure, allow it"}]}
        self.assertEqual(parse_response(payload)["status"], "parse_failure")

    def test_missing_decision_counts_as_the_wrong_label(self):
        missing = {"status": "refusal", "decision": None}
        self.assertEqual(comparable_decision("block", missing), "allow")
        self.assertEqual(comparable_decision("allow", missing), "block")

    def test_request_omits_sampling_parameters(self):
        body = build_request("policy", "Title: Chair\nDescription: Wood.")
        self.assertEqual(body["model"], "claude-haiku-5-5")
        self.assertNotIn("temperature", body)
        self.assertEqual(body["output_config"]["effort"], "low")
        self.assertEqual(body["messages"][-1]["role"], "user")


if __name__ == "__main__":
    unittest.main()
