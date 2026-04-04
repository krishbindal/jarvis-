"""
JARVIS-X Phase 27: Communication Protocol
Skill: Sends Emails via SMTP and WhatsApp messages via PyWhatKit.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pywhatkit
import threading
from typing import Any, Dict
import config
from utils.logger import get_logger

logger = get_logger(__name__)

SKILL_NAME = "communication"
SKILL_DESCRIPTION = "Send emails and WhatsApp messages to contacts."
SKILL_PATTERNS = [
    r"(?:send\s+)?(?:an\s+)?email\s+to\s+([\w\.-]+@[\w\.-]+\.\w+)\s+(?:saying|content|message)\s+(.*)$",
    r"(?:send\s+)?(?:a\s+)?whatsapp\s+(?:message\s+)?to\s+(\+?\d+)\s+(?:saying|content|message)\s+(.*)$",
    r"whatsapp\s+(\+?\d+)\s+(.*)$"
]

def _send_email_async(to_email: str, body: str) -> None:
    """Internal helper to send email without blocking the main event loop."""
    try:
        user = config.EMAIL_USER
        password = config.EMAIL_PASS
        
        if not password or "your-app-password" in password:
            logger.warning("[COMMUNICATION] EMAIL_PASS not set. Email sending skipped.")
            return

        msg = MIMEMultipart()
        msg['From'] = user
        msg['To'] = to_email
        msg['Subject'] = "Message from JARVIS-X"
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT)
        server.starttls()
        server.login(user, password)
        server.send_message(msg)
        server.quit()
        logger.info(f"[COMMUNICATION] Email successfully sent to {to_email}")
    except Exception as e:
        logger.error(f"[COMMUNICATION] Email failed: {e}")

def execute(target: str, extra: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute communication task based on patterns."""
    import re
    
    # Try Email Matching
    email_match = re.search(SKILL_PATTERNS[0], target, re.IGNORECASE)
    if email_match:
        to_email = email_match.group(1)
        body = email_match.group(2)
        
        if "your-email" in config.EMAIL_USER or not config.EMAIL_PASS:
            return {
                "success": False,
                "status": "config_required",
                "message": "Sir, I need your Gmail App Password to send emails. Please update the .env file."
            }

        threading.Thread(target=_send_email_async, args=(to_email, body), daemon=True).start()
        return {
            "success": True,
            "status": "success",
            "message": f"I've initiated the email to {to_email}, Sir. It will be sent in the background."
        }

    # Try WhatsApp Matching
    wa_match = re.search(SKILL_PATTERNS[1], target, re.IGNORECASE) or re.search(SKILL_PATTERNS[2], target, re.IGNORECASE)
    if wa_match:
        phone = wa_match.group(1).strip(" .!,?")
        message = wa_match.group(2).strip(" .!,?")
        
        try:
            import webbrowser
            import urllib.parse
            import os
            
            # 1. PC Native URI implementation 
            encoded_msg = urllib.parse.quote(message)
            whatsapp_uri = f"whatsapp://send?phone={phone}&text={encoded_msg}"
            
            def _launch_wa():
                logger.info(f"[COMMUNICATION] Attempting native WhatsApp PC: {phone}")
                # We try os.startfile first
                try:
                    os.startfile(whatsapp_uri)
                except Exception as e:
                    logger.warning(f"[COMMUNICATION] Native launch failed, using web fallback: {e}")
                    webbrowser.open(f"https://web.whatsapp.com/send?phone={phone}&text={encoded_msg}")

            threading.Thread(target=_launch_wa, daemon=True).start()
            
            return {
                "success": True,
                "status": "success",
                "message": f"I'm opening WhatsApp to message {phone}, Sir."
            }
        except Exception as e:
            logger.error(f"[COMMUNICATION] WhatsApp launch failed: {e}")
            return {
                "success": False,
                "status": "error",
                "message": f"Failed to trigger WhatsApp: {e}"
            }

    return {
        "success": False,
        "status": "unrecognized",
        "message": "I understood you want to communicate, but I couldn't parse the recipient or message correctly."
    }
