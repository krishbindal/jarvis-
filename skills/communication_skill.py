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

import json
from pathlib import Path

logger = get_logger(__name__)

SKILL_NAME = "communication"
SKILL_DESCRIPTION = "Send emails and WhatsApp messages to contacts."
SKILL_PATTERNS = [
    r"(?:send\s+)?(?:an\s+)?email\s+to\s+([\w\.-]+@[\w\.-]+\.\w+)\s+(?:saying|content|message)\s+(.*)$",
    r"(?:send\s+)?(?:a\s+)?whatsapp\s+(?:message\s+)?to\s+([\w\d\+\s]+)\s+(?:saying|content|message)\s+(.*)$",
    r"(?:message|text|tell)\s+([\w\s]+?)\s+(?:saying|that|message)?\s*(.*)$",
    r"whatsapp\s+([\w\d\+\s]+)\s+(.*)$"
]

def _resolve_contact(identifier: str) -> str:
    """Resolve a name or phone number to a WhatsApp-compatible string."""
    identifier = identifier.strip().lower()
    
    # If it looks like a phone number already, return as-is
    if identifier.startswith("+") or (identifier.isdigit() and len(identifier) > 5):
        return identifier
        
    # Otherwise, check contacts.json and contacts_cache.json
    try:
        paths = [Path("data/contacts.json"), Path("memory/contacts_cache.json")]
        for p in paths:
            if p.exists():
                with open(p, "r") as f:
                    contacts = json.load(f)
                    match = contacts.get(identifier)
                    if match:
                        return match
    except Exception as e:
        logger.error(f"[COMMUNICATION] Contact lookup failed: {e}")
        
    return identifier # Fallback to identifier if no match found

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

def _smart_desktop_send(platform: str, recipient: str, message: str) -> bool:
    """Automate desktop app interactions using Vision to find search bars."""
    import time
    try:
        import pyautogui
        from brain.vision_provider import get_vision_provider
        from executor.system_executor import open_app
        
        # 1. Open the app
        open_app(platform)
        time.sleep(3) # Wait for app to load/focus
        
        # 2. Find Search Bar
        vision = get_vision_provider()
        search_prompt = f"The search bar or 'New Chat' button in {platform} Windows App"
        coords = vision.find_element(search_prompt)
        
        if not coords:
            logger.warning(f"[COMMUNICATION] Could not find search bar for {platform} via Vision. Trying Ctrl+F.")
            pyautogui.hotkey('ctrl', 'f')
        else:
            pyautogui.click(coords[0], coords[1])
            
        time.sleep(0.5)
        
        # 3. Type Name and Select
        pyautogui.write(recipient, interval=0.05)
        time.sleep(1)
        pyautogui.press('enter')
        time.sleep(1)
        
        # 4. Type Message and Send
        pyautogui.write(message, interval=0.01)
        pyautogui.press('enter')
        
        # 5. Cache success
        cache_path = Path("memory/contacts_cache.json")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache = {}
        if cache_path.exists():
            with open(cache_path, "r") as f:
                cache = json.load(f)
        
        cache[recipient.lower()] = recipient # Store the search term
        with open(cache_path, "w") as f:
            json.dump(cache, f, indent=4)
            
        logger.info(f"[COMMUNICATION] Smart Send complete for {recipient} on {platform}")
        return True
    except Exception as e:
        logger.error(f"[COMMUNICATION] Smart Send failed: {e}")
        return False

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

    # Try WhatsApp/Instagram/Text Matching
    wa_match = (
        re.search(SKILL_PATTERNS[1], target, re.IGNORECASE) or 
        re.search(SKILL_PATTERNS[2], target, re.IGNORECASE) or 
        re.search(SKILL_PATTERNS[3], target, re.IGNORECASE)
    )
    
    # Check for direct platform mention
    is_insta = "instagram" in target.lower()
    platform = "instagram" if is_insta else "whatsapp"
    
    if wa_match:
        recipient = wa_match.group(1).strip(" .!,?")
        message = wa_match.group(2).strip(" .!,?")
        
        phone = _resolve_contact(recipient)
        
        # If it's a phone number or a resolved contact, use URI
        if phone.startswith("+") or phone.isdigit():
             try:
                import urllib.parse
                import os
                
                encoded_msg = urllib.parse.quote(message)
                whatsapp_uri = f"whatsapp://send?phone={phone}&text={encoded_msg}"
                
                def _launch_wa():
                    try:
                        os.startfile(whatsapp_uri)
                        time.sleep(2)
                        import pyautogui
                        pyautogui.press('enter') # Send it
                    except Exception as e:
                        logger.warning(f"[COMMUNICATION] URI failed: {e}")

                threading.Thread(target=_launch_wa, daemon=True).start()
                return {"success": True, "message": f"Sending WhatsApp to {phone}..."}
             except Exception:
                 pass

        # SMART SEARCH FALLBACK (Normal Names / 100+ Contacts case)
        threading.Thread(target=_smart_desktop_send, args=(platform, recipient, message), daemon=True).start()
        
        return {
            "success": True,
            "status": "success",
            "message": f"I'm searching for {recipient} on {platform} and sending your message, Sir."
        }

    return {
        "success": False,
        "status": "unrecognized",
        "message": "I understood you want to communicate, but I couldn't parse the recipient or message correctly."
    }
