from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from app.database import SessionLocal
from app.models.meeting import Meeting
from app.models.user import User
from app.routers.auth import get_current_user
from app.services.notification_service import (
    send_meeting_started_email,
    send_meeting_ended_email,
)
import random
import string
from datetime import datetime

router = APIRouter()


class MeetingCreate(BaseModel):
    title:  str
    agenda: Optional[str] = None


def generate_room_code():
    return ''.join(
        random.choices(string.ascii_uppercase + string.digits, k=6)
    )


def serialize_meeting(m: Meeting):
    return {
        "id":         str(m.id),
        "title":      m.title,
        "room_code":  m.room_code,
        "host_id":    str(m.host_id),
        "status":     m.status,
        "agenda":     m.agenda,
        "started_at": m.started_at.isoformat() if m.started_at else None,
        "ended_at":   m.ended_at.isoformat()   if m.ended_at   else None,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


# ── Create Meeting ────────────────────────────────────────────
@router.post("/create")
def create_meeting(
    data: MeetingCreate,
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()
    try:
        room_code = generate_room_code()
        while db.query(Meeting).filter(
            Meeting.room_code == room_code
        ).first():
            room_code = generate_room_code()

        meeting = Meeting(
            title     = data.title,
            agenda    = data.agenda,
            room_code = room_code,
            host_id   = current_user.id,
            status    = "scheduled"
        )
        db.add(meeting)
        db.commit()
        db.refresh(meeting)

        return {
            "message":    "Meeting created successfully!",
            "meeting_id": str(meeting.id),
            "room_code":  meeting.room_code,
            "title":      meeting.title,
            "status":     meeting.status,
            "meeting":    serialize_meeting(meeting)
        }
    finally:
        db.close()


# ── List Meetings ─────────────────────────────────────────────
@router.get("/list")
def get_meetings(current_user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        meetings = (
            db.query(Meeting)
            .filter(Meeting.host_id == current_user.id)
            .order_by(Meeting.created_at.desc())
            .all()
        )
        return [serialize_meeting(m) for m in meetings]
    finally:
        db.close()


# ── Join by Room Code ─────────────────────────────────────────
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
            raise HTTPException(404, "Room code not found!")
        return {
            "message": "Meeting joined successfully!",
            "meeting": serialize_meeting(meeting)
        }
    finally:
        db.close()


# ── Meeting Status (Polling ke liye) ─────────────────────────
@router.get("/status/{meeting_id}")
def meeting_status(
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
        return {
            "meeting_id": str(meeting.id),
            "status":     meeting.status,
            "started_at": meeting.started_at.isoformat() if meeting.started_at else None,
            "ended_at":   meeting.ended_at.isoformat()   if meeting.ended_at   else None,
        }
    finally:
        db.close()


# ── Start Meeting ─────────────────────────────────────────────
@router.post("/start/{meeting_id}")
def start_meeting(
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
            raise HTTPException(404, "Meeting not found!")
        if str(meeting.host_id) != str(current_user.id):
            raise HTTPException(403, "Only host can start the meeting!")
        if meeting.status == "active":
            return {
                "message": "Meeting is already active!",
                "meeting": serialize_meeting(meeting)
            }

        meeting.status     = "active"
        meeting.started_at = datetime.utcnow()
        db.commit()
        db.refresh(meeting)

        # Email notification
        print(f"DEBUG: current_user.email = {current_user.email}")
        if current_user.email:
            background_tasks.add_task(
                send_meeting_started_email,
                current_user.email,
                meeting.title,
                meeting.room_code
            )

        return {
            "message": "Meeting started successfully!",
            "status":  "active",
            "meeting": serialize_meeting(meeting)
        }
    finally:
        db.close()


# ── End Meeting ───────────────────────────────────────────────
@router.post("/end/{meeting_id}")
def end_meeting(
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
            raise HTTPException(404, "Meeting not found!")
        if str(meeting.host_id) != str(current_user.id):
            raise HTTPException(403, "Only host can end the meeting!")
        if meeting.status == "ended":
            return {
                "message": "Meeting already ended!",
                "meeting": serialize_meeting(meeting)
            }

        meeting.status   = "ended"
        meeting.ended_at = datetime.utcnow()
        db.commit()
        db.refresh(meeting)

        # Email notification
        if current_user.email:
            background_tasks.add_task(
                send_meeting_ended_email,
                current_user.email,
                meeting.title
            )

        return {
            "message": "Meeting ended successfully!",
            "status":  "ended",
            "meeting": serialize_meeting(meeting)
        }
    finally:
        db.close()


# ── Delete Meeting ────────────────────────────────────────────
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
            raise HTTPException(404, "Meeting not found!")
        if str(meeting.host_id) != str(current_user.id):
            raise HTTPException(403, "Only host can delete meeting!")

        db.delete(meeting)
        db.commit()
        return {"message": "Meeting deleted successfully!"}
    finally:
        db.close()