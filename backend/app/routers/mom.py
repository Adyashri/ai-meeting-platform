import json
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from app.database import SessionLocal
from app.models.meeting import Meeting
from app.models.transcript import Transcript
from app.models.mom import MOM
from app.models.user import User
from app.services.gemini_service import generate_mom
from app.services.notification_service import send_mom_ready_email
from app.routers.auth import get_current_user

router = APIRouter()


def safe_parse(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    try:
        result = json.loads(value)
        return result if isinstance(result, list) else []
    except Exception:
        return []


def serialize_mom(mom: MOM):
    return {
        "id":              str(mom.id),
        "meeting_id":      str(mom.meeting_id),
        "summary":         mom.summary or "",
        "key_discussions": safe_parse(mom.key_discussions),
        "decisions":       safe_parse(mom.decisions),
        "action_items":    safe_parse(mom.action_items),
        "next_meeting":    mom.next_meeting or "N/A",
    }


@router.post("/generate/{meeting_id}")
def generate_meeting_mom(
    meeting_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()
    try:
        meeting = db.query(Meeting).filter(
            Meeting.id == meeting_id
        ).first()
        if not meeting:
            raise HTTPException(404, "Meeting not found")

        # ✅ Host check hataya — koi bhi authenticated user MOM generate kar sakta hai
        # if str(meeting.host_id) != str(current_user.id):
        #     raise HTTPException(403, "Only host can generate MOM")

        transcripts = (
            db.query(Transcript)
            .filter(Transcript.meeting_id == meeting_id)
            .order_by(Transcript.start_time.asc())
            .all()
        )

        # ✅ Transcript nahi hai toh bhi basic MOM banana — 404 nahi dena
        lines     = []
        attendees = []
        for t in transcripts:
            speaker = (t.speaker_name or "Unknown").strip()
            text    = (t.text or "").strip()
            if not text:
                continue
            if speaker not in attendees:
                attendees.append(speaker)
            lines.append(f"[{speaker}]: {text}")

        transcript_text = "\n".join(lines).strip()

        # ✅ Transcript empty hai toh placeholder use karo
        if not transcript_text:
            transcript_text = "No audio was recorded in this meeting."
            attendees       = [current_user.name or "Host"]

        # Gemini se MOM generate karo
        mom_data = generate_mom(
            transcript_text=transcript_text,
            meeting_title=meeting.title or "Meeting",
            attendees=attendees
        )

        # Database mein save/update karo
        existing_mom = db.query(MOM).filter(
            MOM.meeting_id == meeting_id
        ).first()

        if existing_mom:
            mom = existing_mom
        else:
            mom = MOM(meeting_id=meeting_id)
            db.add(mom)

        mom.summary         = mom_data.get("summary", "")
        mom.key_discussions = json.dumps(mom_data.get("key_discussions", []))
        mom.decisions       = json.dumps(mom_data.get("decisions", []))
        mom.action_items    = json.dumps(mom_data.get("action_items", []))
        mom.next_meeting    = mom_data.get("next_meeting", "N/A")

        db.commit()
        db.refresh(mom)

        # Email notification (background mein)
        if current_user.email:
            background_tasks.add_task(
                send_mom_ready_email,
                current_user.email,
                meeting.title
            )

        return {
            "message": "MOM generated successfully!",
            "mom":     serialize_mom(mom)
        }

    finally:
        db.close()


@router.get("/{meeting_id}")
def get_mom(
    meeting_id: str,
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()
    try:
        mom = db.query(MOM).filter(
            MOM.meeting_id == meeting_id
        ).first()
        if not mom:
            raise HTTPException(404, "MOM not found — generate it first!")
        return serialize_mom(mom)
    finally:
        db.close()