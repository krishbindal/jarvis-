"""Readiness diagnostics must report observable facts, not fabricated readiness."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from diagnostics import evidence
from diagnostics.final_report import generate_report
from diagnostics.jarvis_master_check import JarvisMasterCheck


class EvidenceOnlyTests(unittest.TestCase):
    def test_all_modules_and_keys_still_cannot_mark_release_ready(self):
        with tempfile.TemporaryDirectory() as folder:
            with (
                patch.object(evidence, "_module_present", return_value=True),
                patch.object(evidence, "urlopen") as network,
            ):
                report = evidence.collect_evidence(
                    root=Path(folder),
                    environment={"GROQ_API_KEY": "secret-value", "GEMINI_API_KEY": "secret-other"},
                )
        self.assertIs(report["release_ready"], False)
        self.assertEqual(report["release_status"], "NOT_VERIFIED")
        cloud_checks = [c for c in report["checks"] if c["name"].endswith("credential")]
        self.assertEqual(len(cloud_checks), 2)
        self.assertTrue(all(c["status"] == "not_tested" for c in cloud_checks))
        encoded = json.dumps(report)
        self.assertNotIn("secret-value", encoded)
        self.assertNotIn("secret-other", encoded)
        network.assert_not_called()

    def test_missing_voice_model_not_marked_operational(self):
        with tempfile.TemporaryDirectory() as folder:
            report = evidence.collect_evidence(
                root=Path(folder),
                environment={"VOICE_MODEL_PATH": "missing-vosk"},
            )
        model = next(c for c in report["checks"] if c["name"] == "Vosk model folder")
        self.assertEqual(model["status"], "unavailable")
        self.assertNotIn("FULLY OPERATIONAL", evidence.render_markdown(report))

    def test_directory_presence_is_not_audio_recognition(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "voice" / "model").mkdir(parents=True)
            report = evidence.collect_evidence(root=root, environment={})
        model = next(c for c in report["checks"] if c["name"] == "Vosk model folder")
        mic = next(c for c in report["checks"] if c["name"] == "Physical microphone and wake recognition")
        self.assertEqual(model["status"], "observed")
        self.assertEqual(mic["status"], "not_tested")
        self.assertIn("NOT been tested", model["detail"])

    def test_no_database_is_created_by_readonly_check(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "memory" / "jarvis.db"
            report = evidence.collect_evidence(root=Path(folder), environment={})
            self.assertFalse(path.exists())
        db = next(c for c in report["checks"] if c["name"] == "Local memory database")
        self.assertEqual(db["status"], "not_tested")

    def test_existing_database_schema_is_observed_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "memory").mkdir()
            path = root / "memory" / "jarvis.db"
            with sqlite3.connect(path) as connection:
                connection.execute("CREATE TABLE interactions (id INTEGER PRIMARY KEY)")
            report = evidence.collect_evidence(root=root, environment={})
        db = next(c for c in report["checks"] if c["name"] == "Local memory database")
        self.assertEqual(db["status"], "observed")
        self.assertIn("NOT tested", db["detail"])

    def test_opt_in_local_ollama_probe_never_claims_generation(self):
        response = MagicMock(status=200)
        response.__enter__.return_value = response
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(evidence, "urlopen", return_value=response) as request:
                report = evidence.collect_evidence(root=Path(folder), environment={}, probe_ollama=True)
        request.assert_called_once()
        local = next(c for c in report["checks"] if c["name"] == "Ollama local HTTP endpoint")
        self.assertEqual(local["status"], "observed")
        self.assertIn("NOT tested", local["detail"])
        self.assertFalse(report["release_ready"])

    def test_markdown_and_json_have_real_newlines_and_consistent_status(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            report = evidence.collect_evidence(root=root, environment={})
            json_path, md_path = evidence.write_report(report, root / "artifacts")
            parsed = json.loads(json_path.read_text(encoding="utf-8"))
            content = md_path.read_text(encoding="utf-8")
        self.assertEqual(parsed["release_status"], "NOT_VERIFIED")
        self.assertIn("\n| Observation | Status |", content)
        self.assertIn("**Release status: NOT VERIFIED**", content)
        self.assertNotIn("SYSTEM READY", content)

    def test_both_legacy_entrypoints_use_shared_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("diagnostics.final_report.collect_evidence") as collected:
                collected.return_value = evidence.collect_evidence(root=Path(folder), environment={})
                with patch("builtins.print"):
                    report = generate_report(Path(folder) / "final")
                collected.assert_called_once()
                self.assertEqual(report["release_status"], "NOT_VERIFIED")
            with patch("diagnostics.jarvis_master_check.collect_evidence") as master:
                master.return_value = report
                with patch("builtins.print"):
                    other = JarvisMasterCheck().run_all(output_dir=Path(folder) / "master")
                self.assertIs(other, report)
                master.assert_called_once()

    def test_legacy_benchmark_exits_as_unverified(self):
        from diagnostics import jarvis_performance_suite as legacy
        with patch("builtins.print") as printer:
            self.assertNotEqual(legacy.main(), 0)
        self.assertIn("not a valid end-to-end", printer.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
