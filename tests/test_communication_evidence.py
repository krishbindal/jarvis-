"""Communication must never claim delivery before observable SMTP response."""
import smtplib
import unittest
from unittest.mock import MagicMock, patch

from skills import communication_skill as skill


class CommunicationEvidenceTests(unittest.TestCase):
    def _credentials(self):
        return (
            patch.object(skill.config, "EMAIL_USER", "sender@example.com"),
            patch.object(skill.config, "EMAIL_PASS", "fake-test-password"),
        )

    def test_smtp_accepted_is_not_inbox_delivered(self):
        server = MagicMock()
        server.send_message.return_value = {}
        context = MagicMock()
        context.__enter__.return_value = server
        with self._credentials()[0], self._credentials()[1], patch.object(skill.smtplib, "SMTP", return_value=context) as smtp:
            result = skill.execute("email to recipient@example.com saying Hello")
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "smtp_accepted")
        self.assertIn("not been verified", result["message"])
        server.send_message.assert_called_once()
        smtp.assert_called_once()

    def test_smtp_exception_is_not_success(self):
        context = MagicMock()
        context.__enter__.side_effect = smtplib.SMTPException("SMTP refused message")
        with self._credentials()[0], self._credentials()[1], patch.object(skill.smtplib, "SMTP", return_value=context):
            result = skill.execute("email to recipient@example.com saying Test")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "smtp_failed")

    def test_rejected_recipient_is_not_success(self):
        server = MagicMock()
        server.send_message.return_value = {"recipient@example.com": (550, "rejected")}
        context = MagicMock()
        context.__enter__.return_value = server
        with self._credentials()[0], self._credentials()[1], patch.object(skill.smtplib, "SMTP", return_value=context):
            result = skill.execute("email to recipient@example.com saying Test")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "smtp_rejected")

    def test_unconfigured_email_does_not_contact_smtp(self):
        with patch.object(skill.config, "EMAIL_PASS", ""), patch.object(skill.smtplib, "SMTP") as smtp:
            result = skill.execute("email to recipient@example.com saying Test")
        self.assertFalse(result["success"])
        smtp.assert_not_called()

    def test_whatsapp_only_opens_draft_and_never_claims_send(self):
        with patch.object(skill.webbrowser, "open", return_value=True) as browser:
            result = skill.execute("whatsapp to +919876543210 saying review this")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "awaiting_manual_send")
        url = browser.call_args.args[0]
        self.assertIn("https://wa.me/919876543210?text=review%20this", url)

    def test_unresolved_contact_cannot_be_guessed(self):
        with patch.object(skill, "_resolve_contact", return_value=None), patch.object(skill.webbrowser, "open") as browser:
            result = skill.execute("whatsapp to unknown person saying hi")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "recipient_unresolved")
        browser.assert_not_called()

    def test_whatsapp_browser_error_does_not_claim_success(self):
        with patch.object(skill.webbrowser, "open", return_value=False):
            result = skill.execute("whatsapp to +919876543210 saying hi")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "draft_not_opened")


if __name__ == "__main__":
    unittest.main()
