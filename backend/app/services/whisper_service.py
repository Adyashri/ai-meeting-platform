import tempfile
import os
import subprocess
import whisper
from app.config import get_settings

settings = get_settings()
_model = None

def get_model():
    global _model
    if _model is None:
        print("Loading Whisper model...")
        _model = whisper.load_model("base")
        print("Whisper model ready!")
    return _model

def convert_to_wav(input_path: str, output_path: str) -> bool:
    """WebM/any format ko WAV mein convert karo FFmpeg se"""
    try:
        result = subprocess.run([
            "ffmpeg", "-y",
            "-i", input_path,
            "-ar", "16000",
            "-ac", "1",
            "-f", "wav",
            output_path
        ], capture_output=True, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"FFmpeg error: {e}")
        return False

def transcribe_audio(audio_bytes: bytes) -> dict:
    """
    Audio bytes lo — text return karo
    WebM/WAV dono support karta hai
    """
    # Input file banao
    with tempfile.NamedTemporaryFile(
        suffix=".webm",
        delete=False
    ) as tmp_input:
        tmp_input.write(audio_bytes)
        input_path = tmp_input.name

    # Output WAV file path
    output_path = input_path.replace(".webm", ".wav")

    try:
        # FFmpeg se convert karo
        converted = convert_to_wav(input_path, output_path)

        if not converted:
            print("FFmpeg conversion failed!")
            return {"text": "", "language": "en", "segments": []}

        # Whisper se transcribe karo
        model = get_model()
        result = model.transcribe(
            output_path,
            fp16=False
        )

        text = result.get("text", "").strip()
        print(f"TRANSCRIBED: {text}")

        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "text": seg["text"].strip(),
                "start": seg["start"],
                "end": seg["end"],
            })

        return {
            "text": text,
            "language": result.get("language", "en"),
            "segments": segments
        }

    except Exception as e:
        print(f"Transcription error: {e}")
        return {"text": "", "language": "en", "segments": []}

    finally:
        # Temp files delete karo
        if os.path.exists(input_path):
            os.unlink(input_path)
        if os.path.exists(output_path):
            os.unlink(output_path)