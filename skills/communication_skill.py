"""Consent-gated communication skill with truthful delivery states.

The skill dispatcher requires user confirmation before calling execute().
SMTP acceptance is reported as acceptance, not proof of inbox delivery.
WhatsApp links only prefill a draft; Jarvis never silently presses Send.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any, Dict
from urllib.parse import quote
import webbrowser

import config
from utils.logger import get_logger

logger = get_logger(__name__)

SKILL_NAME = "communication"
SKILL_DESCRIPTION = "Submit email via SMTP or open a WhatsApp draft for user review."
SKILL_PATTERNS = [
    r"(?:send\s+)?(?:an\s+)?email\s+to\s+([\w.+-]+@[\w.-]+\.\w+)\s+(?:saying|content|message)\s+(.*)$",
    r"(?:send\s+)?(?:a\s+)?whatsapp\s+(?:message\s+)?to\s+([\w\d+\s]+)\s+(?:saying|content|message)\s+(.*)$",
    r"(?:message|text|tell)\s+([\w\s]+?)\s+(?:saying|that|message)\s+(.*)$",
    r"whatsapp\s+([\w\d+\s]+)\s+(.*)$",
]

_ROOT = Path(__file__).resolve().parents[1]
_MAX_MESSAGE_CHARS = 10000


def _resolve_contact(identifier: str) -> str | None:
    """Resolve an explicit international number or locally saved contact."""
    name = identifier.strip()
    if name.startswith("+") and name[1:].isdigit():
        return name
    if name.isdigit():
        return name
    for path in (_ROOT / "data" / "contacts.json", _ROOT / "memory" / "contacts_cache.json"):
        try:
            if not path.is_file():
                continue
            with path.open("r", encoding="utf-8") as source:
                contacts = json.load(source)
            if isinstance(contacts, dict):
                for key, value in contacts.items():
                    if isinstance(key, str) and key.casefold() == name.casefold() and isinstance(value, str):
                        return value.strip()
        except (OSError, ValueError, TypeError):
            logger.warning("[COMMUNICATION] Could not read local contacts file %s", path.name)
    return None


def _smtp_submit(to_email: str, body: str) -> Dict[str, Any]:
    """Attempt SMTP submission synchronously in the existing command worker."""
    user = config.EMAIL_USER
    password = config.EMAIL_PASS
    if not user or not password or "your-email" in user or "your-app-password" in password:
        return {
            "success": False,
            "status": "config_required",
            "message": "Email credentials are not configured; nothing was sent.",
        }

    message = EmailMessage()
    message["From"] = user
    message["To"] = to_email
    message["Subject"] = "Message from JARVIS-X"
    message.set_content(body)

    try:
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT, timeout=15) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(user, password)
            rejected = server.send_message(message)
        if rejected:
            return {
                "success": False,
                "status": "smtp_rejected",
                "message": "The SMTP server refused at least one recipient. Delivery was not confirmed.",
            }
        return {
            "success": True,
            "status": "smtp_accepted",
            "message": (
                f"SMTP server accepted the message for {to_email}. "
                "Inbox delivery and reading have not been verified."
            ),
        }
    except (smtplib.SMTPException, OSError, TimeoutError) as exc:
        logger.warning("[COMMUNICATION] SMTP submission failed (%s)", type(exc).__name__)
        return {
            "success": False,
            "status": "smtp_failed",
            "message": "SMTP submission failed. No successful delivery was confirmed.",
        }


def _whatsapp_draft(recipient: str, body: str) -> Dict[str, Any]:
    phone = _resolve_contact(recipient)
    digits = phone[1:] if isinstance(phone, str) and phone.startswith("+") else ""
    if not digits.isdigit() or not 8 <= len(digits) <= 15:
        return {
            "success": False,
            "status": "recipient_unresolved",
            "message": (
                "I cannot verify the recipient's international phone number. "
                "Use + followed by the country code and phone number, or a saved contact."
            ),
        }
    url = f"https://wa.me/{digits}?text={quote(body)}"
    try:
        opened = webbrowser.open(url)
    except (OSError, ValueError) as exc:
        logger.warning("[COMMUNICATION] Failed to open draft (%s)", type(exc).__name__)
        opened = False
    if not opened:
        return {
            "success": False,
            "status": "draft_not_opened",
            "message": "Could not open a WhatsApp draft. No message was sent.",
        }
    return {
        "success": False,
        "status": "awaiting_manual_send",
        "message": "Requested a WhatsApp draft. Review the recipient and press Send yourself; delivery is not confirmed.",
    }


def execute(target: str, extra: Dict[str, Any] = None) -> Dict[str, Any]:
    """Parse an explicit recipient and refuse ambiguous or unverified delivery."""
    if not isinstance(target, str):
        return {"success": False, "status": "invalid_request", "message": "A text instruction is required."}

    email_match = re.search(SKILL_PATTERNS[0], target, re.IGNORECASE | re.DOTALL)
    if email_match:
        body = email_match.group(2).strip()
        if not body or len(body) > _MAX_MESSAGE_CHARS:
            return {"success": False, "status": "invalid_message", "message": "Email message must be 1–10000 characters."}
        return _smtp_submit(email_match.group(1), body)

    match = None
    if "instagram" not in target.lower():
        for expression in SKILL_PATTERNS[1:]:
            match = re.search(expression, target, re.IGNORECASE | re.DOTALL)
            if match:
                break

    if match:
        body = match.group(2).strip()
        if not body or len(body) > _MAX_MESSAGE_CHARS:
            return {"success": False, "status": "invalid_message", "message": "Message must be 1–10000 characters."}
        return _whatsapp_draft(match.group(1), body)

    return {
        "success": False,
        "status": "unrecognized",
        "message": "I couldn't verify a recipient and message. Nothing was sent.",
    }
