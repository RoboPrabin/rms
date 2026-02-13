import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

# <p style="margin:0; font-size:14px;">Risk Management System (RMS)</p>

# ---------- Config ----------
SENDER_EMAIL = "support@trishakti.com.np"
SENDER_PASSWORD = "Support.Trishakti@123"   
DISPLAY_NAME = "RMS - Trishakti"
SMTP_SERVER = "mail.trishakti.com.np"
SMTP_PORT = 587  # Using 587 as per your previous requirement for TLS

def send_email(to_email: str, subject: str, username: str, otp_code: str, minutes:any):
    """
    Sends a beautifully formatted HTML OTP email.
    """
    # HTML Template with inline CSS
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            .container {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 600px;
                margin: 0 auto;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                overflow: hidden;
            }}
            .header {{
                background-color: #1e3a8a; /* Deep Blue */
                color: #ffffff;
                padding: 20px;
                text-align: center;
            }}
            .content {{
                padding: 30px;
                line-height: 1.6;
                color: #333333;
                background-color: #ffffff;
            }}
            .otp-box {{
                background-color: #f3f4f6;
                border: 2px dashed #1e3a8a;
                border-radius: 6px;
                padding: 20px;
                text-align: center;
                margin: 20px 0;
            }}
            .otp-code {{
                font-size: 32px;
                font-weight: bold;
                letter-spacing: 5px;
                color: #1e3a8a;
            }}
            .footer {{
                background-color: #f9fafb;
                color: #6b7280;
                padding: 15px;
                text-align: center;
                font-size: 12px;
            }}
            .warning {{
                font-size: 12px;
                color: #991b1b;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2 style="margin:0;">Trishakti Securities Limited</h2>
                <p style="margin:0; font-size:14px;">R.M.S.</p>
            </div>
            <div class="content">
                <p>Hello <strong>{username}</strong>,</p>
                <p>You requested a secure login to the <b>RMS portal</b>. Please use the following One-Time Password (OTP) to complete your authentication:</p>
                
                <div class="otp-box">
                    <div class="otp-code">{otp_code}</div>
                    <p style="margin:5px 0 0 0; font-size:12px; color:#666;">Valid for {minutes} minutes only</p>
                </div>
                
                <p>If you did not attempt to log in, please contact the IT Department immediately or change your password.</p>
                
                <p class="warning">
                    <strong>Note:</strong> Never share your OTP or Login PIN with anyone. Trishakti staff will never ask for your password.
                </p>
            </div>
            <div class="footer">
                © 2026 Trishakti Securities Limited. All rights reserved.<br>
                This is an automated system message. Please do not reply.
            </div>
        </div>
    </body>
    </html>
    """

    msg = MIMEMultipart()
    msg['From'] = f"{DISPLAY_NAME} <{SENDER_EMAIL}>"
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        raise