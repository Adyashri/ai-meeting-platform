from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.database import SessionLocal
from app.models.transcript import Transcript
from app.services.whisper_service import transcribe_audio
import json
import time

router = APIRouter()

@router.websocket("/ws/{meeting_id}")
async def live_transcription(
    websocket: WebSocket,
    meeting_id: str,
    speaker_name: str = "Unknown"
):
    await websocket.accept()

    db = SessionLocal()

    start_time = time.time()

    print(f"Transcription started: Meeting {meeting_id}")

    try:

        while True:

            audio_data = await websocket.receive_bytes()

            if not audio_data:
                continue

            elapsed = time.time() - start_time

            # Whisper transcription
            result = transcribe_audio(audio_data)

            text = result.get("text", "").strip()

            print("TRANSCRIBED TEXT:", text)

            if not text:
                continue

            segments = result.get("segments", [])

            # Agar segments available hain
            if segments:

                for seg in segments:

                    transcript = Transcript(
                        meeting_id=meeting_id,
                        speaker_name=speaker_name,
                        text=seg["text"].strip(),
                        start_time=elapsed + seg["start"],
                        end_time=elapsed + seg["end"],
                        language=result.get("language", "en"),
                    )

                    db.add(transcript)

            # Agar segments empty hain
            else:

                transcript = Transcript(
                    meeting_id=meeting_id,
                    speaker_name=speaker_name,
                    text=text,
                    start_time=elapsed,
                    end_time=elapsed + 5,
                    language=result.get("language", "en"),
                )

                db.add(transcript)

            # Database save
            db.commit()

            print("Transcript saved!")

            # Frontend ko transcript bhejo
            await websocket.send_text(
                json.dumps({
                    "text": text,
                    "speaker": speaker_name,
                    "timestamp": round(elapsed, 2),
                    "language": result.get("language", "en"),
                })
            )

    except WebSocketDisconnect:

        print(f"Disconnected: Meeting {meeting_id}")

    except Exception as e:

        print(f"Error: {e}")

    finally:

        db.close()


@router.get("/{meeting_id}")
def get_transcript(meeting_id: str):

    db = SessionLocal()

    try:

        transcripts = db.query(Transcript).filter(
            Transcript.meeting_id == meeting_id
        ).order_by(Transcript.start_time).all()

        return transcripts

    finally:

        db.close()

