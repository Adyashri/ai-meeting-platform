import requests
from typing import Optional
from app.config import settings


def smtp_configured() -> bool:
    return bool(settings.RESEND_API_KEY)


def send_email(
    to_email: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None,
):
    if not smtp_configured():
        print(f"[Email skipped — Resend not configured] To: {to_email} | Subject: {subject}")
        return
    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
            json={
                "from": "AI Meeting Platform <onboarding@resend.dev>",
                "to": [to_email],
                "subject": subject,
                "html": html_body if html_body else f"<p>{body}</p>",
            },
            timeout=10,
        )
        if response.status_code in (200, 201):
            print(f"[Email sent] To: {to_email} | Subject: {subject}")
        else:
            print(f"[Email error] Status: {response.status_code} | {response.text}")
    except Exception as e:
        print(f"[Email error — skipped] {e}")


def send_meeting_started_email(to_email: str, meeting_title: str, room_code: str):
    subject = f"Meeting Started: {meeting_title}"
    body = (
        f"Hello,<br><br>"
        f"Your meeting '{meeting_title}' has started.<br>"
        f"Room Code: {room_code}<br><br>"
        f"Regards,<br>AI Meeting Platform"
    )
    send_email(to_email, subject, body, html_body=body)


def send_meeting_ended_email(to_email: str, meeting_title: str):
    subject = f"Meeting Ended: {meeting_title}"
    body = (
        f"Hello,<br><br>"
        f"Your meeting '{meeting_title}' has ended.<br>"
        f"You can now generate MOM / export transcript from the platform.<br><br>"
        f"Regards,<br>AI Meeting Platform"
    )
    send_email(to_email, subject, body, html_body=body)


def send_mom_ready_email(to_email: str, meeting_title: str):
    subject = f"MOM Ready: {meeting_title}"
    body = (
        f"Hello,<br><br>"
        f"Minutes of Meeting for '{meeting_title}' are ready.<br>"
        f"Please open the platform to view/download them.<br><br>"
        f"Regards,<br>AI Meeting Platform"
    )
    send_email(to_email, subject, body, html_body=body)