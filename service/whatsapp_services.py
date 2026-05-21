import logging
from typing import Any, Optional
import os

import requests

logger = logging.getLogger(__name__)

# Internal relay (default) — keeps existing behaviour
INTERNAL_API_URL = os.getenv("WHATSAPP_INTERNAL_API_URL", "https://rms.trishakti.com.np/api/v1/whatsapp/send-message")
INTERNAL_HEADERS = {"Content-Type": "application/json"}

# WhatsApp Cloud API settings (optional)
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")


def _normalize_phone(phone: str) -> str:
    """Normalize phone to E.164 without plus, default Nepal country code 977.
    Examples:
      '9841234567' -> '9779841234567'
      '+9779841234567' -> '9779841234567'
      '009779841234567' -> '9779841234567'
    """
    if not phone:
        return ""
    p = phone.strip()
    # remove common prefixes
    if p.startswith("+"):
        p = p[1:]
    if p.startswith("00"):
        p = p[2:]
    # remove non-digits
    p = ''.join(ch for ch in p if ch.isdigit())
    # if starts with country code 977 already
    if p.startswith("977"):
        return p
    # if starts with leading 0, drop it
    if p.startswith("0"):
        p = p[1:]
    # default to 977
    return "977" + p


def _send_via_internal(phone: str, message: str) -> Optional[dict[str, Any]]:
    payload = {"to": phone, "message": message}
    try:
        resp = requests.post(INTERNAL_API_URL, json=payload, headers=INTERNAL_HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        logger.info("Internal WhatsApp relay succeeded for %s", phone)
        return data
    except requests.exceptions.RequestException as e:
        logger.error("Internal WhatsApp relay failed for %s: %s", phone, e)
        return None


def _send_via_cloud(phone: str, message: str) -> Optional[dict[str, Any]]:
    """Send message using Meta WhatsApp Cloud API.

    Requires env vars: `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`.
    """
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logger.debug("WhatsApp Cloud credentials not configured")
        return None

    url = f"https://graph.facebook.com/v17.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": message},
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        logger.info("WhatsApp Cloud API sent message to %s", phone)
        return data
    except requests.exceptions.RequestException as e:
        logger.error("WhatsApp Cloud API failed for %s: %s", phone, e)
        return None


def send_message(phone: str, message: str) -> Optional[dict[str, Any]]:
    """Send a WhatsApp message.

    Behaviour:
    - Normalize phone
    - If WHATSAPP_TOKEN+PHONE_NUMBER_ID present, try Cloud API first
    - Otherwise fallback to internal relay API
    """
    normalized = _normalize_phone(phone)
    # try cloud first if configured
    cloud_resp = _send_via_cloud(normalized, message)
    if cloud_resp:
        return cloud_resp
    # fallback to internal relay
    return _send_via_internal(normalized, message)


def send_otp(phone: str, otp_code: str, username: str, minutes: int = 4) -> Optional[dict[str, Any]]:
    message = (
        f"Dear {username.upper()},\n\n"
        f"Your One-Time Password (OTP) is: {otp_code}\n\n"
        f"This OTP is valid for {minutes} minutes.\n\n"
        f"For security reasons, please do not share this OTP with anyone. Trishakti staff will never ask for your OTP.\n\n"
        f"Regards,\n"
        f"RMS Team - Trishakti Securities Limited\n\n"
        f"This is an automated message. Please do not reply."
    )
    return send_message(phone, message)
