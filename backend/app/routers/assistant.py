from fastapi import APIRouter, HTTPException, Depends
from app.database import SessionLocal
from app.models.meeting import Meeting
from app.models.transcript import Transcript
from app.models.user import User
from app.routers.auth import get_current_user
from app.services.gemini_service import get_live_suggestion

router = APIRouter()


@router.get("/suggest/{meeting_id}")
def suggest_for_meeting(
    meeting_id: str,
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()
    try:
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise HTTPException(404, "Meeting not found")

        # Only the host sees live suggestions
        if str(meeting.host_id) != str(current_user.id):
            raise HTTPException(403, "Only host can view live suggestions")

        # Last 15 transcript lines are enough for context
        transcripts = (
            db.query(Transcript)
            .filter(Transcript.meeting_id == meeting_id)
            .order_by(Transcript.created_at.desc())
            .limit(15)
            .all()
        )
        transcripts.reverse()

        transcript_text = " ".join([t.text for t in transcripts])

        result = get_live_suggestion(transcript_text, meeting.title or "Meeting")
        return result
    finally:
        db.close()