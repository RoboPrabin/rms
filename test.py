import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from email.message import EmailMessage
from typing import Optional


sender_email: str = "prabin.chand@trishakti.com.np"
sender_password: str = "papk nqvm bksx roqu"
display_name: str = "RMS - Trishakti"
subject: str = "RMS - Credentials 🔐"

def send_email(
    to_email: str,
    username:str,
    password:str,
    url:str = "https://holdings.trishakti.com.np:9999",
    sender_email: str = sender_email,
    sender_password: str = sender_password,
    display_name: str = display_name,
) -> None:
    """
    Send an email using Gmail SMTP.
    """

    msg = EmailMessage()
    msg["From"] = f"{display_name} <{sender_email}>"
    msg["To"] = to_email
    msg["Subject"] = "RMS Account Created."

    msg.set_content(f"""
    Hello,

    Your account has been created successfully.

    Username: {username.lower()}
    Password: {password}
    URL: {url}

    Please change your password after first login.

    Regards,
    RMS Team
    Trishakti Securities Limited
    Kathamndu, Nepal
    """)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)

    except Exception as e:
        raise RuntimeError(f"Failed to send email: {e}")



def send_bulk_email(
    selected_df,
    body,
    subject=subject,
    sender_email=sender_email,
    sender_password=sender_password,
    display_name=display_name
):
    results = []

    try:
        # ✅ Connect once
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)

        # ✅ Send all emails using the same connection
        for _, row in selected_df.iterrows():
            to_email = row["email"]
                # ✅ Skip if email is None, empty, or NaN
            if not to_email or pd.isna(to_email):
                print("Skipped empty email")
                continue


            msg = MIMEMultipart()
            msg["From"] = formataddr((display_name, sender_email))
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(
                    MIMEText(
                        body
                        + "\n\nUSERNAME: " + str(row["username"])
                        + "\nPASSWORD: " + str(row["password"])
                        + "\nURL: " + str("https://holdings.trishakti.com.np:9999/"),
                        "plain"
                    )
                )

            try:
                server.sendmail(sender_email, to_email, msg.as_string())
                results.append((to_email, True))
            except Exception:
                results.append((to_email, False))

        # ✅ Close once
        server.quit()

    except Exception:
        # If connection fails, mark all as failed
        for _, row in selected_df.iterrows():
            results.append((row["email"], False))

    return results



send_email(to_email="prabin.trishakti@gmail.com", username="prabin", password="prabin")