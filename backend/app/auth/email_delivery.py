import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import Settings
from app.core.exceptions import HealthLinkError


logger = logging.getLogger(__name__)


class EmailDeliveryError(HealthLinkError):
    def __init__(self) -> None:
        super().__init__("Email delivery is temporarily unavailable. Please try again shortly.", status_code=503)


def send_auth_email(settings: Settings, recipient: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = formataddr(("HealthLink", settings.auth_smtp_from_email))
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    context = ssl.create_default_context()
    try:
        if settings.auth_smtp_port == 465:
            connection = smtplib.SMTP_SSL(
                settings.auth_smtp_host, settings.auth_smtp_port, timeout=5, context=context,
            )
        else:
            connection = smtplib.SMTP(settings.auth_smtp_host, settings.auth_smtp_port, timeout=5)
        with connection:
            if settings.auth_smtp_port == 587:
                connection.starttls(context=context)
            connection.login(settings.auth_smtp_username, settings.auth_smtp_key)
            connection.send_message(message)
    except (OSError, smtplib.SMTPException):
        # SMTP errors can contain the recipient, headers or provider credentials.
        logger.warning("Authentication email delivery failed.")
        raise EmailDeliveryError() from None


def send_auth_email_in_background(settings: Settings, recipient: str, subject: str, body: str) -> None:
    try:
        send_auth_email(settings, recipient, subject, body)
    except EmailDeliveryError:
        pass
