import json
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from app.database import SessionLocal
from app.models.meeting import Meeting
from app.models.transcript import Transcript
from app.models.mom import MOM
from app.models.user import User
from app.services.gemini_service import generate_mom
from app.services.notification_service import send_mom_ready_email
from app.tasks import generate_mom_task
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
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()
    try:
        meeting = db.query(Meeting).filter(
            Meeting.id == meeting_id
        ).first()
        if not meeting:
            raise HTTPException(404, "Meeting not found")

        # Queue the Celery task in the background
        generate_mom_task.delay(meeting_id, current_user.email)

        return {
            "message": "MOM generation started! Please refresh in a few seconds.",
            "status": "processing"
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