from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional
from app.database import SessionLocal
from app.models.transcript import Transcript
from app.models.meeting import Meeting
from app.models.user import User
from app.routers.auth import get_current_user
import json
import time

router = APIRouter()


class TranscriptCreate(BaseModel):
    meeting_id: str
    speaker_name: Optional[str] = "Unknown"
    text: str
    start_time: Optional[float] = 0
    end_time: Optional[float] = 0
    language: Optional[str] = "en"


def serialize_transcript(row: Transcript):
    return {
        "id": str(row.id),
        "meeting_id": str(row.meeting_id),
        "speaker_name": row.speaker_name,
        "text": row.text,
        "start_time": row.start_time,
        "end_time": row.end_time,
        "language": row.language,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


# ================================
# 🔥 FIXED WEBSOCKET SECTION
# ================================
@router.websocket("/ws/{meeting_id}")
async def transcription_websocket(
    websocket: WebSocket,
    meeting_id: str,
    speaker_name: str = "Unknown"
):
    await websocket.accept()
    db = SessionLocal()
    start_time = time.time()

    print(f"=== Transcription started: {meeting_id} ===")

    try:
        from app.services.whisper_service import transcribe_audio

        while True:
            audio_data = await websocket.receive_bytes()

            print(f"Audio received: {len(audio_data)} bytes")
            print("Whisper function called")

            if not audio_data:
                continue

            result = transcribe_audio(audio_data)

            print("Whisper result:", result)

            text = result.get("text", "").strip()

            if not text:
                continue

            elapsed = time.time() - start_time

            segments = result.get("encsegments", []) or result.get("segments", [])

            for seg in segments:
                seg_text = seg.get("text", "").strip()

                if not seg_text:
                    continue

                db.add(
                    Transcript(
                        meeting_id=meeting_id,
                        speaker_name=speaker_name,
                        text=seg_text,
                        start_time=elapsed + seg.get("start", 0),
                        end_time=elapsed + seg.get("end", 0),
                        language=result.get("language", "en"),
                    )
                )

            db.commit()

            print(f"Transcript saved: {text}")

            await websocket.send_text(
                json.dumps(
                    {
                        "text": text,
                        "speaker": speaker_name,
                        "timestamp": round(elapsed, 2),
                        "language": result.get("language", "en"),
                    }
                )
            )

    except WebSocketDisconnect:
        print("WebSocket disconnected")

    except Exception as e:
        print("WebSocket error:", str(e))

    finally:
        db.close()
        print("WebSocket closed")


# ================================
# SAVE MANUAL TRANSCRIPT
# ================================
@router.post("/save")
def save_transcript(
    data: TranscriptCreate,
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()
    try:
        meeting = db.query(Meeting).filter(Meeting.id == data.meeting_id).first()

        if not meeting:
            raise HTTPException(404, "Meeting not found")

        t = Transcript(
            meeting_id=data.meeting_id,
            speaker_name=data.speaker_name,
            text=data.text,
            start_time=data.start_time,
            end_time=data.end_time,
            language=data.language,
        )

        db.add(t)
        db.commit()
        db.refresh(t)

        return {
            "message": "Transcript saved successfully",
            "transcript": serialize_transcript(t),
        }

    finally:
        db.close()


# ================================
# GET TRANSCRIPT
# ================================
@router.get("/{meeting_id}")
def get_transcript(
    meeting_id: str,
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()
    try:
        transcripts = (
            db.query(Transcript)
            .filter(Transcript.meeting_id == meeting_id)
            .order_by(Transcript.start_time.asc())
            .all()
        )

        return {
            "meeting_id": meeting_id,
            "count": len(transcripts),
            "transcripts": [serialize_transcript(t) for t in transcripts],
        }

    finally:
        db.close()


# ================================
# DELETE TRANSCRIPT
# ================================
@router.delete("/{meeting_id}")
def delete_transcript(
    meeting_id: str,
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()
    try:
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()

        if not meeting:
            raise HTTPException(404, "Meeting not found")

        if str(meeting.host_id) != str(current_user.id):
            raise HTTPException(403, "Only host can delete transcript")

        db.query(Transcript).filter(
            Transcript.meeting_id == meeting_id
        ).delete()

        db.commit()

        return {"message": "Transcript deleted successfully"}

    finally:
        db.close()