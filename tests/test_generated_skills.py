"""Generated Python is staged inertly and never imported automatically."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from skills.skill_staging import extract_skill_name, stage_skill_candidate

GOOD = "SKILL_NAME = 'safe_example'\nSKILL_DESCRIPTION = 'test'\n"


class SkillGenerationSafetyTests(unittest.TestCase):
    def test_literal_name_extraction_is_nonexecuting(self):
        self.assertEqual(extract_skill_name(GOOD), "safe_example")
        self.assertIsNone(extract_skill_name("SKILL_NAME = get_secret()"))

    def test_rejects_directory_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            res = stage_skill_candidate("SKILL_NAME = '../escape'", "../escape", Path(directory))
            self.assertFalse(res["success"])
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_rejects_syntax_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            res = stage_skill_candidate("SKILL_NAME = 'safe_example'\ndef :", "safe_example", Path(directory))
            self.assertFalse(res["success"])

    def test_stages_inert_candidate_not_in_live_skills(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            res = stage_skill_candidate(GOOD, "safe_example", path)
            self.assertTrue(res["success"], res)
            self.assertEqual(res["status"], "pending_review")
            self.assertEqual((path / "safe_example.py").read_text(), GOOD)
            self.assertNotIn("safe_example", __import__("sys").modules)
            res2 = stage_skill_candidate(GOOD, "safe_example", path)
            self.assertFalse(res2["success"], "Must not silently overwrite a proposal")

    def test_requires_explicit_generation_opt_in(self):
        from skills import genesis_agent, forge_skill
        with patch.object(genesis_agent, "ENABLE_SKILL_GENERATION", False):
            self.assertEqual(genesis_agent.execute("do x")["status"], "disabled")
        with patch.object(forge_skill, "ENABLE_SKILL_GENERATION", False):
            self.assertEqual(forge_skill.execute("do x")["status"], "disabled")


if __name__ == "__main__":
    unittest.main()
