import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from app.config import settings


def smtp_configured() -> bool:
    return bool(
        settings.SMTP_EMAIL
        and settings.SMTP_PASSWORD
        and settings.SMTP_HOST
        and settings.SMTP_PORT
    )


def send_email(
    to_email: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None,
):
    # SMTP configure nahi hai toh silently skip karo — error mat do
    if not smtp_configured():
        print(f"[Email skipped — SMTP not configured] To: {to_email} | Subject: {subject}")
        return

    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"]    = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_EMAIL}>"
        message["To"]      = to_email

        message.attach(MIMEText(body, "plain", "utf-8"))
        if html_body:
            message.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_EMAIL, [to_email], message.as_string())

        print(f"[Email sent] To: {to_email} | Subject: {subject}")

    except Exception as e:
        # Email fail ho toh bhi app crash mat karo
        print(f"[Email error — skipped] {e}")


def send_meeting_started_email(to_email: str, meeting_title: str, room_code: str):
    subject = f"Meeting Started: {meeting_title}"
    body = (
        f"Hello,\n\n"
        f"Your meeting '{meeting_title}' has started.\n"
        f"Room Code: {room_code}\n\n"
        f"Regards,\nAI Meeting Platform"
    )
    send_email(to_email, subject, body)


def send_meeting_ended_email(to_email: str, meeting_title: str):
    subject = f"Meeting Ended: {meeting_title}"
    body = (
        f"Hello,\n\n"
        f"Your meeting '{meeting_title}' has ended.\n"
        f"You can now generate MOM / export transcript from the platform.\n\n"
        f"Regards,\nAI Meeting Platform"
    )
    send_email(to_email, subject, body)


def send_mom_ready_email(to_email: str, meeting_title: str):
    subject = f"MOM Ready: {meeting_title}"
    body = (
        f"Hello,\n\n"
        f"Minutes of Meeting for '{meeting_title}' are ready.\n"
        f"Please open the platform to view/download them.\n\n"
        f"Regards,\nAI Meeting Platform"
    )
    send_email(to_email, subject, body)