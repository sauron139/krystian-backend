import logging
from email.message import EmailMessage

import aiosmtplib

from app.core.config import get_settings

log = logging.getLogger(__name__)


async def send_email(to: str, subject: str, body: str, reply_to: str | None = None) -> None:
    """Send a plain-text email. Failures are logged, not raised: callers run this in the
    background after the data is already saved, so a mail outage never loses a lead."""
    settings = get_settings()
    msg = EmailMessage()
    msg["From"] = settings.mail_from
    msg["To"] = to
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(body)
    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password.get_secret_value() if settings.smtp_password else None,
            start_tls=settings.smtp_starttls,
            timeout=10,
        )
    except (aiosmtplib.SMTPException, OSError):
        log.exception("failed to send email to %s", to)
