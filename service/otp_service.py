import random
from datetime import datetime, timedelta
from db.db import get_connection
from service.email_service import send_email

# ---------- Config ----------
OTP_EXPIRY_MINUTES = 2
MAX_ATTEMPTS = 3

def get_otp_expiry(username: str) -> datetime:
    """Fetch the expiry time of the latest active OTP for the user"""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT expires_at FROM user_otp 
            WHERE username = %s AND is_used = FALSE 
            ORDER BY created_at DESC LIMIT 1;
        """, (username,))
        row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def generate_otp() -> str:
    """Generate a 6-digit numeric OTP"""
    return str(random.randint(100000, 999999))


async def create_user_otp(username: str, user_email: str) -> str:
    """
    Generate OTP, store in DB, and send to user's email
    :param username: user logging in
    :param user_email: user's email
    :return: generated OTP (for debug/testing only)
    """
    otp = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)

    conn = get_connection()
    with conn.cursor() as cur:
        # Remove previous unused OTPs
        cur.execute("""
            DELETE FROM user_otp
            WHERE username = %s AND is_used = FALSE;
        """, (username,))

        # Insert new OTP
        cur.execute("""
            INSERT INTO user_otp (username, otp, expires_at)
            VALUES (%s, %s, %s);
        """, (username, otp, expires_at))

    conn.commit()
    conn.close()

    # Send OTP via email
    subject = "RMS OTP Code"
    # body = f"Hello {username},\n\nYour OTP for login is: {otp}\nIt will expire in {OTP_EXPIRY_MINUTES} minutes.\n\nRMS - Trishakti"
    # send_email(user_email, subject, body)
    # send_email(to_email=user_email, subject=subject, username=username, otp_code=otp)

    return otp


def verify_user_otp(username: str, entered_otp: str) -> bool:
    """
    Verify the OTP entered by the user
    :param username: user logging in
    :param entered_otp: OTP entered by user
    :return: True if valid, False otherwise
    """
    conn = get_connection()
    with conn.cursor() as cur:
        # Fetch latest unused OTP
        cur.execute("""
            SELECT id, otp, expires_at, attempt_count
            FROM user_otp
            WHERE username = %s AND is_used = FALSE
            ORDER BY created_at DESC
            LIMIT 1;
        """, (username,))
        row = cur.fetchone()

        if not row:
            conn.close()
            return False  # no OTP available

        otp_id, db_otp, expires_at, attempt_count = row

        # Expired
        if datetime.utcnow() > expires_at:
            conn.close()
            return False

        # Max attempts reached
        if attempt_count >= MAX_ATTEMPTS:
            conn.close()
            return False

        # OTP mismatch
        if entered_otp != db_otp:
            cur.execute("""
                UPDATE user_otp
                SET attempt_count = attempt_count + 1
                WHERE id = %s;
            """, (otp_id,))
            conn.commit()
            conn.close()
            return False

        # Success → mark OTP used
        cur.execute("""
            UPDATE user_otp
            SET is_used = TRUE
            WHERE id = %s;
        """, (otp_id,))
        conn.commit()
    conn.close()
    return True
