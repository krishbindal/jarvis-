"""Provider model selection and system-agent execution control."""
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class ModelConfigurationTests(unittest.TestCase):
    def _load_isolated(self):
        spec = importlib.util.spec_from_file_location("provider_config_test", ROOT / "brain/provider_config.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_current_stable_model_is_default(self):
        with patch.dict(os.environ, {}, clear=True):
            module = self._load_isolated()
        self.assertEqual(module.GEMINI_MODEL, "gemini-3.5-flash")
        self.assertEqual(module.VISION_MODEL, module.GEMINI_MODEL)

    def test_user_can_change_both_models(self):
        with patch.dict(os.environ, {"GEMINI_MODEL": "custom-model", "JARVIS_VISION_MODEL": "vision-custom"}):
            module = self._load_isolated()
        self.assertEqual(module.GEMINI_MODEL, "custom-model")
        self.assertEqual(module.VISION_MODEL, "vision-custom")

    def test_no_retired_gemini_literals_in_runtime(self):
        for path in ("brain/provider_config.py", "brain/ai_engine.py", "brain/vision_provider.py", "skills/system_agent.py"):
            source = (ROOT / path).read_text(encoding="utf-8")
            self.assertNotIn("gemini-2.0-flash", source, path)


class GeneratedCodeExecutionTests(unittest.TestCase):
    def test_both_flags_required(self):
        import skills.system_agent as agent
        for allow_code, allow_model in ((False, False), (True, False), (False, True)):
            with (
                self.subTest(flags=(allow_code, allow_model)),
                patch.object(agent, "ALLOW_CODE_EXECUTION", allow_code),
                patch.object(agent, "ALLOW_MODEL_CODE_EXECUTION", allow_model),
                patch.object(agent, "_generate_code") as generator,
            ):
                result = agent.execute("do something")
                self.assertEqual(result["status"], "disabled")
                generator.assert_not_called()

    def test_model_code_uses_shared_runner_not_unrestricted_python(self):
        import skills.system_agent as agent
        with (
            patch.object(agent, "ALLOW_CODE_EXECUTION", True),
            patch.object(agent, "ALLOW_MODEL_CODE_EXECUTION", True),
            patch.object(agent, "_generate_code", return_value="print(42)"),
            patch.object(agent, "run_python_code", return_value={"success": True, "status": "success"}) as runner,
        ):
            result = agent.execute("calculate")
        self.assertTrue(result["success"])
        runner.assert_called_once_with("print(42)")


if __name__ == "__main__":
    unittest.main()
