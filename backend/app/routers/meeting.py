from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.meeting import Meeting
from app.models.user import User
from app.routers.auth import get_current_user
import random
import string
from datetime import datetime

router = APIRouter()

class MeetingCreate(BaseModel):
    title: str
    agenda: Optional[str] = None

def generate_room_code():
    return ''.join(
        random.choices(
            string.ascii_uppercase + string.digits,
            k=6
        )
    )

@router.post("/create")
def create_meeting(
    data: MeetingCreate,
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()
    try:
        room_code = generate_room_code()

        new_meeting = Meeting(
            title=data.title,
            room_code=room_code,
            host_id=current_user.id,
            status="scheduled"
        )

        db.add(new_meeting)
        db.commit()
        db.refresh(new_meeting)

        return {
            "message": "Meeting bani!",
            "meeting_id": new_meeting.id,
            "room_code": room_code,
            "title": new_meeting.title,
            "status": new_meeting.status
        }
    finally:
        db.close()

@router.get("/list")
def get_meetings(
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()
    try:
        meetings = db.query(Meeting).filter(
            Meeting.host_id == current_user.id
        ).all()
        return meetings
    finally:
        db.close()

@router.get("/join/{room_code}")
def join_meeting(
    room_code: str,
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()
    try:
        meeting = db.query(Meeting).filter(
            Meeting.room_code == room_code
        ).first()

        if not meeting:
            raise HTTPException(
                status_code=404,
                detail="Room code galat hai"
            )

        return {
            "meeting_id": meeting.id,
            "title": meeting.title,
            "room_code": meeting.room_code,
            "status": meeting.status
        }
    finally:
        db.close()

@router.post("/start/{meeting_id}")
def start_meeting(
    meeting_id: str,
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()
    try:
        meeting = db.query(Meeting).filter(
            Meeting.id == meeting_id
        ).first()

        if not meeting:
            raise HTTPException(404, "Meeting nahi mili")

        if meeting.host_id != current_user.id:
            raise HTTPException(
                403,
                "Sirf host meeting start kar sakta hai"
            )

        meeting.status = "active"
        meeting.started_at = datetime.utcnow()
        db.commit()
        db.refresh(meeting)

        return {
            "message": "Meeting shuru ho gayi!",
            "status": "active",
            "meeting_id": meeting.id,
            "room_code": meeting.room_code
        }
    finally:
        db.close()

@router.post("/end/{meeting_id}")
def end_meeting(
    meeting_id: str,
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()
    try:
        meeting = db.query(Meeting).filter(
            Meeting.id == meeting_id
        ).first()

        if not meeting:
            raise HTTPException(404, "Meeting nahi mili")

        if meeting.host_id != current_user.id:
            raise HTTPException(
                403,
                "Sirf host meeting khatam kar sakta hai"
            )

        meeting.status = "ended"
        meeting.ended_at = datetime.utcnow()
        db.commit()
        db.refresh(meeting)

        return {
            "message": "Meeting khatam ho gayi!",
            "status": "ended"
        }
    finally:
        db.close()

@router.delete("/delete/{meeting_id}")
def delete_meeting(
    meeting_id: str,
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()

    try:
        meeting = db.query(Meeting).filter(
            Meeting.id == meeting_id
        ).first()

        if not meeting:
            raise HTTPException(
                status_code=404,
                detail="Meeting not found"
            )

        if meeting.host_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Only host can delete meeting"
            )

        db.delete(meeting)
        db.commit()

        return {
            "message": "Meeting deleted successfully"
        }

    finally:
        db.close()