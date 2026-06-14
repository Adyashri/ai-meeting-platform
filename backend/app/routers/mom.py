from fastapi import APIRouter, Depends, HTTPException
from app.database import SessionLocal
from app.models.mom import MOM
from app.models.transcript import Transcript
from app.models.meeting import Meeting
from app.models.user import User
from app.routers.auth import get_current_user
from app.services.gemini_service import generate_mom
import json
from datetime import datetime

router = APIRouter()

@router.post("/generate/{meeting_id}")
def generate_meeting_mom(
    meeting_id: str,
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()
    try:
        # Meeting dhundho
        meeting = db.query(Meeting).filter(
            Meeting.id == meeting_id
        ).first()

        if not meeting:
            raise HTTPException(404, "Meeting not found")

        # Transcript lo
        transcripts = db.query(Transcript).filter(
            Transcript.meeting_id == meeting_id
        ).order_by(Transcript.start_time).all()

        if not transcripts:
            raise HTTPException(
                400,
                "No transcript found — record audio first!"
            )

        # Transcript text banao
        lines = []
        for t in transcripts:
            speaker = t.speaker_name or "Unknown"
            lines.append(f"[{speaker}]: {t.text}")
        transcript_text = "\n".join(lines)

        # Attendees list banao
        attendees = list(set([
            t.speaker_name for t in transcripts
            if t.speaker_name
        ]))

        # Gemini se MOM generate karo
        mom_data = generate_mom(
            transcript_text,
            meeting.title,
            attendees
        )

        # Database mein save karo
        existing = db.query(MOM).filter(
            MOM.meeting_id == meeting_id
        ).first()

        if existing:
            mom = existing
        else:
            mom = MOM(meeting_id=meeting_id)
            db.add(mom)

        mom.summary         = mom_data.get("summary", "")
        mom.decisions       = json.dumps(
            mom_data.get("decisions", [])
        )
        mom.action_items    = json.dumps(
            mom_data.get("action_items", [])
        )
        mom.key_discussions = json.dumps(
            mom_data.get("key_discussions", [])
        )
        mom.next_meeting    = mom_data.get("next_meeting", "N/A")
        mom.created_at      = datetime.utcnow()

        db.commit()
        db.refresh(mom)

        return {
            "message": "MOM generated successfully!",
            "mom": mom_data
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
            raise HTTPException(
                404,
                "MOM not found — generate it first!"
            )

        return {
            "summary": mom.summary,
            "decisions": json.loads(mom.decisions or "[]"),
            "action_items": json.loads(
                mom.action_items or "[]"
            ),
            "key_discussions": json.loads(
                mom.key_discussions or "[]"
            ),
            "next_meeting": mom.next_meeting
        }
    finally:
        db.close()