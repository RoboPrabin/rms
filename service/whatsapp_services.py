import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

API_URL = "https://rms.trishakti.com.np/api/v1/whatsapp/send-message"
HEADERS = {"Content-Type": "application/json"}


def send_message(phone: str, message: str) -> dict[str, Any] | None:
    payload = {
        "to": f"977{phone}",
        "message": message,
    }

    try:
        response = requests.post(API_URL, json=payload, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        logger.info("Message sent to %s", f"977{phone}")
        return data
    except requests.exceptions.RequestException as e:
        logger.error("Failed to send message to %s: %s", f"977{phone}", e)
        return None


def send_otp(phone: str, otp_code: str, username: str, minutes: int = 4) -> dict[str, Any] | None:
    message = (
        f"Dear *{username.upper()}*,\n\n"
        f"Your One-Time Password (OTP) is: *{otp_code}*\n\n"
        f"This OTP is valid for {minutes} minutes.\n\n"
        f"For security reasons, please do not share this OTP with anyone. "
        f"Trishakti staff will never ask for your OTP.\n\n"
        f"Regards,\n"
        f"RMS Team\n"
        f"Trishakti Securities Limited\n\n"
        f"_This is an automated message. Please do not reply._"
    )
    return send_message(phone, message)
