"""Email dispatch service with SMTP support and safe local outbox fallback."""

import logging
import smtplib
from email.message import EmailMessage

from flask import current_app

logger = logging.getLogger("busreserve.mail")


def dispatch_transactional_email(
    recipient: str,
    subject: str,
    body_text: str,
    action_path: str,
    raw_token: str,
) -> dict[str, str] | None:
    """Deliver email via SMTP if configured; otherwise use safe local outbox mode."""
    smtp_host = current_app.config.get("SMTP_HOST", "").strip()
    base_url = current_app.config.get("FRONTEND_BASE_URL", "http://localhost:8080").rstrip("/")
    action_url = f"{base_url}{action_path}?token={raw_token}"

    if smtp_host:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = current_app.config.get("SMTP_FROM", "no-reply@busreserve.local")
        msg["To"] = recipient
        msg.set_content(f"{body_text}\n\nLink: {action_url}\n")

        port = int(current_app.config.get("SMTP_PORT", 587))
        use_tls = bool(current_app.config.get("SMTP_USE_TLS", True))
        smtp_user = current_app.config.get("SMTP_USER", "")
        smtp_password = current_app.config.get("SMTP_PASSWORD", "")

        with smtplib.SMTP(smtp_host, port, timeout=10) as client:
            if use_tls:
                client.starttls()
            if smtp_user and smtp_password:
                client.login(smtp_user, smtp_password)
            client.send_message(msg)

        logger.info("smtp_email_sent", extra={"recipient": recipient, "subject": subject})
        return None

    logger.info(
        "local_outbox_email_recorded",
        extra={"recipient": recipient, "subject": subject, "action_path": action_path},
    )

    if current_app.config.get("ALLOW_LOCAL_MAIL_PREVIEW", False):
        return {
            "delivery": "local_outbox",
            "token": raw_token,
            "action_url": f"{action_path}?token={raw_token}",
        }
    return None
