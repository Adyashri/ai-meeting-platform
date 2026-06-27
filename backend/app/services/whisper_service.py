import tempfile
import os
import subprocess
import whisper

_model = None


def get_model():
    global _model
    if _model is None:
        print("Loading Whisper model...")
        # base se better result ke liye "small" use kar sakte ho agar machine handle kare
        # _model = whisper.load_model("small")
        _model = whisper.load_model("base")
        print("Whisper model ready!")
    return _model


def convert_to_wav(input_path: str, output_path: str) -> bool:
    """
    Input audio ko 16k mono WAV me convert karo
    """
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i", input_path,
                "-ar", "16000",
                "-ac", "1",
                "-f", "wav",
                output_path
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print("FFmpeg conversion failed!")
            print("STDERR:", result.stderr)
            return False

        return True

    except Exception as e:
        print(f"FFmpeg error: {e}")
        return False


def transcribe_audio(audio_bytes: bytes) -> dict:
    """
    Audio bytes lo aur transcript return karo
    """
    input_path = None
    output_path = None

    try:
        if not audio_bytes or len(audio_bytes) < 2000:
            return {"text": "", "language": "en", "segments": []}

        # incoming chunk ko temp webm file me save karo
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp_input:
            tmp_input.write(audio_bytes)
            input_path = tmp_input.name

        output_path = input_path.replace(".webm", ".wav")

        # convert to wav
        converted = convert_to_wav(input_path, output_path)
        if not converted:
            return {"text": "", "language": "en", "segments": []}

        # transcribe
        model = get_model()
        result = model.transcribe(
            output_path,
            fp16=False,
            task="transcribe",
            language="en",   # Hinglish ke liye English best रहता है in your current flow
            temperature=0
        )

        text = (result.get("text") or "").strip()
        print("TRANSCRIBED:", text)

        segments = []
        for seg in result.get("segments", []):
            seg_text = (seg.get("text") or "").strip()
            if seg_text:
                segments.append({
                    "text": seg_text,
                    "start": float(seg.get("start", 0)),
                    "end": float(seg.get("end", 0)),
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
        if input_path and os.path.exists(input_path):
            os.unlink(input_path)

        if output_path and os.path.exists(output_path):
            os.unlink(output_path)