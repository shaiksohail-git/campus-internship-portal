"""Email abstraction.

The rest of the application only talks to `email_service`; the underlying
delivery (dev mailbox vs real SMTP) is a configuration detail.
"""

import logging
import smtplib
from email.message import EmailMessage

from flask import current_app

logger = logging.getLogger(__name__)


class EmailService:
    def send(self, recipient, subject, body):
        if current_app.config["MAIL_MODE"] == "smtp":
            return self._send_smtp(recipient, subject, body)
        return self._send_console(recipient, subject, body)

    def _send_console(self, recipient, subject, body):
        """Store into the dev mailbox table and print to the console."""
        from app.models.mailbox import DevMailbox

        from app.extensions import db

        db.session.add(
            DevMailbox(recipient=recipient, subject=subject, body=body)
        )
        db.session.commit()
        logger.info("[DEV MAIL] To: %s | Subject: %s", recipient, subject)
        print(f"\n========== [DEV MAILBOX] ==========\nTo: {recipient}\nSubject: {subject}\n{body}\n===================================\n")
        return True

    def _send_smtp(self, recipient, subject, body):
        cfg = current_app.config
        msg = EmailMessage()
        msg["From"] = cfg["MAIL_FROM"]
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.set_content(body)

        try:
            with smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=15) as server:
                if cfg["SMTP_USE_TLS"]:
                    server.starttls()
                if cfg["SMTP_USERNAME"]:
                    server.login(cfg["SMTP_USERNAME"], cfg["SMTP_PASSWORD"])
                server.send_message(msg)
            logger.info("SMTP mail sent to %s", recipient)
            return True
        except Exception:  # noqa: BLE001 — delivery failure must not break flows
            logger.exception("Failed to send email to %s", recipient)
            return False


email_service = EmailService()
