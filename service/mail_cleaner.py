import imaplib
import email
from email.header import decode_header


class MailCleaner:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.connection = None

    def connect(self):
        self.connection = imaplib.IMAP4_SSL("mail.trishakti.com.np", 993)
        self.connection.login(self.username, self.password)

    def _decode_subject(self, raw_subject):
        if not raw_subject:
            return ""

        decoded_parts = decode_header(raw_subject)
        subject = ""

        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                subject += part.decode(encoding or "utf-8", errors="ignore")
            else:
                subject += part

        return subject.strip()

    def get_matching_email_ids(self, target_subject: str):
        self.connection.select("INBOX")

        # Normalize input
        target_subject = target_subject.strip().upper()

        # Fetch all emails (safe but can be heavy for huge inbox)
        status, messages = self.connection.search(None, "ALL")

        if status != "OK":
            return []

        email_ids = messages[0].split()
        matched_ids = []

        for email_id in email_ids:
            status, msg_data = self.connection.fetch(email_id, "(BODY.PEEK[HEADER])")

            if status != "OK":
                continue

            msg = email.message_from_bytes(msg_data[0][1])
            subject = self._decode_subject(msg.get("Subject"))

            # Normalize subject for comparison
            if target_subject in subject.upper():
                matched_ids.append(email_id)

        return matched_ids

    def delete_emails_stream(self, email_ids):
        total = len(email_ids)

        for index, email_id in enumerate(email_ids, start=1):
            self.connection.store(email_id, "+FLAGS", "\\Deleted")
            yield index, total

        self.connection.expunge()

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection.logout()