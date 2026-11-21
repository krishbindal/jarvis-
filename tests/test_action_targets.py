"""Regression coverage for raw command arguments and packaged diagnostics."""
import unittest
from pathlib import Path
from unittest.mock import patch

from core import action_registry
from executor import system_executor


class ActionTargetTests(unittest.TestCase):
    def test_python_code_with_assignments_is_not_rewritten(self):
        source = "secret = 'contains=a=b'\nprint(secret)"
        seen = []
        with patch.dict(action_registry.ACTION_REGISTRY, {"execute_python": lambda code: seen.append(code) or {"success": True}}):
            result = action_registry.execute_action("execute_python", source)
        self.assertTrue(result["success"])
        self.assertEqual(seen, [source])

    def test_file_path_and_trailing_punctuation_are_preserved(self):
        path = "report=final.txt"
        seen = []
        with patch.dict(action_registry.ACTION_REGISTRY, {"file_info": lambda arg: seen.append(arg) or {"success": True}}):
            action_registry.execute_action("file_info", path)
        self.assertEqual(seen, [path])

    def test_simple_app_name_prefix_is_normalized(self):
        seen = []
        with patch.dict(action_registry.ACTION_REGISTRY, {"open_app": lambda arg: seen.append(arg) or {"success": True}}):
            action_registry.execute_action("open_app", "name=chrome")
        self.assertEqual(seen, ["chrome"])


class DiagnosticEntryTests(unittest.TestCase):
    def test_registry_uses_existing_module(self):
        with patch.object(action_registry.subprocess, "check_output", return_value=" STATUS: OK ") as execute:
            result = action_registry.execute_action("system_check", "")
        self.assertTrue(result["success"], result)
        args, kwargs = execute.call_args
        self.assertEqual(args[0][1:], ["-m", "diagnostics.jarvis_master_check"])
        self.assertTrue((Path(kwargs["cwd"]) / "diagnostics" / "jarvis_master_check.py").is_file())
        self.assertEqual(kwargs["timeout"], 45)

    def test_system_executor_uses_existing_module(self):
        with patch.object(system_executor.subprocess, "check_output", return_value="ok") as execute:
            result = system_executor.run_system_check()
        self.assertTrue(result["success"], result)
        args, kwargs = execute.call_args
        self.assertEqual(args[0][1:], ["-m", "diagnostics.jarvis_master_check"])
        self.assertTrue((Path(kwargs["cwd"]) / "diagnostics" / "jarvis_master_check.py").is_file())


if __name__ == "__main__":
    unittest.main()
