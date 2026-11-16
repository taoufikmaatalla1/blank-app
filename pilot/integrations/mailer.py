"""Send e-mails from your Gmail address (SMTP + app password).

Variables: GMAIL_ADDRESS, GMAIL_APP_PASSWORD (16 characters, created at
myaccount.google.com -> Security -> App passwords; needs 2-Step Verification).
"""

from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

SMTP_HOST, SMTP_PORT = "smtp.gmail.com", 465


class MailError(RuntimeError):
    pass


def configured() -> bool:
    return bool(os.environ.get("GMAIL_ADDRESS") and os.environ.get("GMAIL_APP_PASSWORD"))


def sender() -> str:
    return os.environ.get("GMAIL_ADDRESS", "")


def send(to: str, subject: str, body: str, *, from_name: str = "") -> str:
    """Send one plain-text e-mail. Returns the Message-ID."""
    if not configured():
        raise MailError("Gmail is not set up (GMAIL_ADDRESS and GMAIL_APP_PASSWORD).")
    to = (to or "").strip()
    if "@" not in to or any(c in to for c in "\r\n,;"):
        raise MailError(f"Invalid e-mail address: {to!r}")
    addr = sender()
    msg = EmailMessage()
    msg["From"] = formataddr((from_name, addr)) if from_name else addr
    msg["To"] = to
    msg["Subject"] = subject.replace("\r", " ").replace("\n", " ")
    msg["Message-ID"] = make_msgid(domain=addr.split("@")[-1])
    msg.set_content(body)
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ssl.create_default_context(),
                              timeout=30) as smtp:
            smtp.login(addr, os.environ["GMAIL_APP_PASSWORD"].replace(" ", ""))
            smtp.send_message(msg)
    except smtplib.SMTPAuthenticationError as e:
        raise MailError("Gmail refused the login: check the app password.") from e
    except (smtplib.SMTPException, OSError) as e:
        raise MailError(f"Could not send: {e}") from e
    return msg["Message-ID"]
