from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from app.database import SessionLocal
from app.models.mom import MOM
from app.models.meeting import Meeting
from app.models.user import User
from app.routers.auth import get_current_user
from app.services.pdf_service import generate_mom_pdf
from app.services.docx_service import generate_mom_docx
import json

router = APIRouter()

def safe_json(val):
    if not val:
        return []
    try:
        return json.loads(val)
    except:
        return []

def get_mom_data(mom):
    return {
        "summary":         getattr(mom, "summary", "") or "",
        "key_discussions": safe_json(
            getattr(mom, "key_discussions", None)
        ),
        "decisions":       safe_json(
            getattr(mom, "decisions", None)
        ),
        "action_items":    safe_json(
            getattr(mom, "action_items", None)
        ),
        "next_meeting":    getattr(
            mom, "next_meeting", "N/A"
        ) or "N/A"
    }

@router.get("/pdf/{meeting_id}")
def download_pdf(
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
                404, "MOM not found — generate it first!"
            )
        meeting = db.query(Meeting).filter(
            Meeting.id == meeting_id
        ).first()
        title    = meeting.title if meeting else "Meeting"
        mom_data = get_mom_data(mom)
        pdf_bytes = generate_mom_pdf(mom_data, title)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition":
                f'attachment; filename="MOM_{meeting_id}.pdf"'
            }
        )
    finally:
        db.close()

@router.get("/docx/{meeting_id}")
def download_docx(
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
                404, "MOM not found — generate it first!"
            )
        meeting = db.query(Meeting).filter(
            Meeting.id == meeting_id
        ).first()
        title     = meeting.title if meeting else "Meeting"
        mom_data  = get_mom_data(mom)
        docx_bytes = generate_mom_docx(mom_data, title)
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition":
                f'attachment; filename="MOM_{meeting_id}.docx"'
            }
        )
    finally:
        db.close()