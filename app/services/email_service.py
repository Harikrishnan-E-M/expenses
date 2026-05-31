from __future__ import annotations

import smtplib
from email.message import EmailMessage

from flask import current_app


def send_otp_email(recipient_name: str, recipient_email: str, otp: str) -> None:
    if current_app.config.get("EMAIL_DELIVERY_MODE", "smtp") == "console":
        current_app.logger.info(
            "FinTrack INR OTP for %s <%s>: %s",
            recipient_name,
            recipient_email,
            otp,
        )
        return

    message = EmailMessage()
    message["Subject"] = "FinTrack INR OTP Verification"
    message["From"] = current_app.config["SMTP_EMAIL"]
    message["To"] = recipient_email
    message.set_content(
        f"Hello {recipient_name},\n\nYour FinTrack INR verification OTP is {otp}. It expires in 10 minutes.\n\nIf you did not request this, ignore this email."
    )

    try:
        with smtplib.SMTP(current_app.config["SMTP_SERVER"], current_app.config["SMTP_PORT"], timeout=20) as server:
            server.starttls()
            server.login(current_app.config["SMTP_EMAIL"], current_app.config["SMTP_PASSWORD"])
            server.send_message(message)
    except smtplib.SMTPAuthenticationError as exc:
        current_app.logger.exception("SMTP authentication failed while sending OTP email")
        raise ValueError(
            "Unable to send the OTP email right now. Please verify the SMTP settings in .env and use a Gmail App Password if you are sending through Gmail."
        ) from exc
    except smtplib.SMTPException as exc:
        current_app.logger.exception("SMTP error while sending OTP email")
        raise ValueError("OTP email could not be sent. Check SMTP server settings and credentials.") from exc
