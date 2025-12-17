import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr

def send_bulk_email(
    selected_df,
    body,
    subject="RMS - Credentials 🔐",
    sender_email="prabin.trishakti@gmail.com",
    sender_password="xfvf xpzp cvnt bnlv",
    display_name="RMS"
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