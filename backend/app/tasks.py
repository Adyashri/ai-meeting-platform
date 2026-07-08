import json
from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.meeting import Meeting
from app.models.transcript import Transcript
from app.models.mom import MOM
from app.services.gemini_service import generate_mom
from app.services.notification_service import send_mom_ready_email


@celery_app.task(name="generate_mom_task")
def generate_mom_task(meeting_id: str, user_email: str = None):
    db = SessionLocal()
    try:
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            return {"error": "Meeting not found"}

        transcripts = (
            db.query(Transcript)
            .filter(Transcript.meeting_id == meeting_id)
            .order_by(Transcript.start_time.asc())
            .all()
        )

        lines = []
        attendees = []
        for t in transcripts:
            speaker = (t.speaker_name or "Unknown").strip()
            text = (t.text or "").strip()
            if not text:
                continue
            if speaker not in attendees:
                attendees.append(speaker)
            lines.append(f"[{speaker}]: {text}")

        transcript_text = "\n".join(lines).strip()

        if not transcript_text:
            transcript_text = "No audio was recorded in this meeting."
            attendees = ["Host"]

        mom_data = generate_mom(
            transcript_text=transcript_text,
            meeting_title=meeting.title or "Meeting",
            attendees=attendees
        )

        existing_mom = db.query(MOM).filter(MOM.meeting_id == meeting_id).first()

        if existing_mom:
            mom = existing_mom
        else:
            mom = MOM(meeting_id=meeting_id)
            db.add(mom)

        mom.summary = mom_data.get("summary", "")
        mom.key_discussions = json.dumps(mom_data.get("key_discussions", []))
        mom.decisions = json.dumps(mom_data.get("decisions", []))
        mom.action_items = json.dumps(mom_data.get("action_items", []))
        mom.next_meeting = mom_data.get("next_meeting", "N/A")

        db.commit()

        if user_email:
            send_mom_ready_email(user_email, meeting.title)

        print(f"[Celery] MOM generated for meeting {meeting_id}")
        return {"status": "done"}

    finally:
        db.close()