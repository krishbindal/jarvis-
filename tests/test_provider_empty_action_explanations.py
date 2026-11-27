"""Valid AI explanations with zero tools are not execution failures or successes."""
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from brain.providers.base import _safe_json_extract, _valid_command_response
from brain.providers.gemini import GeminiProvider
from brain.providers.groq import GroqProvider
from brain.providers.ollama import OllamaProvider


EXPLANATION = {"steps": [], "message": "I cannot access that app without permission."}


class ResponseContractTests(unittest.TestCase):
    def test_valid_empty_plan_requires_real_explanation(self):
        self.assertTrue(_valid_command_response(EXPLANATION))
        self.assertFalse(_valid_command_response({"steps": []}))
        self.assertFalse(_valid_command_response({"steps": [], "message": ""}))
        self.assertFalse(_valid_command_response({"message": "Done"}))
        self.assertFalse(_valid_command_response({"steps": "not a list", "message": "done"}))

    def test_invalid_parse_is_not_invented_empty_plan(self):
        parsed = _safe_json_extract("not a JSON response")
        self.assertEqual(parsed, {})
        self.assertFalse(_valid_command_response(parsed))

    def test_rejects_broken_oversized_or_nonobject_steps(self):
        self.assertFalse(_valid_command_response({"steps": [{"action": "open_app"}] * 4}))
        self.assertFalse(_valid_command_response({"steps": ["not a step"]}))
        self.assertFalse(_valid_command_response({"steps": [{"action": "", "target": "x"}]}))

    def test_groq_accepts_empty_plan_as_an_explanation(self):
        api = Mock()
        api.chat.completions.create.return_value.choices = [
            SimpleNamespace(message=SimpleNamespace(content=json.dumps(EXPLANATION)))
        ]
        with (
            patch("brain.providers.groq.GROQ_API_KEY", "unit-test-key"),
            patch("brain.providers.groq.Groq", return_value=api),
        ):
            result = GroqProvider().generate_command("rules", "", "question")
        self.assertEqual(result["steps"], [])
        self.assertEqual(result["message"], EXPLANATION["message"])
        api.chat.completions.create.assert_called_once()

    def test_gemini_accepts_empty_plan_as_an_explanation(self):
        api = Mock()
        api.models.generate_content.return_value.text = json.dumps(EXPLANATION)
        with (
            patch("brain.providers.gemini.GEMINI_API_KEY", "unit-test-key"),
            patch("brain.providers.gemini.genai.Client", return_value=api),
        ):
            result = GeminiProvider().generate_command("rules", "", "question")
        self.assertEqual(result["steps"], [])
        self.assertEqual(result["message"], EXPLANATION["message"])

    def test_ollama_accepts_empty_plan_without_any_tool(self):
        response = Mock()
        response.json.return_value = {"message": {"content": json.dumps(EXPLANATION)}}
        with (
            patch.object(OllamaProvider, "is_available", return_value=True),
            patch("brain.providers.ollama.requests.post", return_value=response),
        ):
            result = OllamaProvider().generate_command("rules", "", "question")
        self.assertEqual(result["steps"], [])
        self.assertIn("cannot access", result["message"])

    def test_unknown_handler_displays_limitation_without_execution(self):
        from core import app
        with (
            patch.object(app, "interpret_command", return_value=EXPLANATION),
            patch.object(app, "get_recent_history", return_value=[]),
            patch.object(app, "get_relevant_context", return_value=[]),
            patch.object(app, "execute_action") as execute,
        ):
            result, attempted = app.JarvisApp._handle_unknown(object(), "please perform unavailable task", {})
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "not_executed")
        self.assertIn(EXPLANATION["message"], result["message"])
        self.assertIn("No action was executed", result["message"])
        self.assertEqual(attempted, [])
        execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
