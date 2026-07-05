import tempfile
import os
import subprocess
import whisper

_model = None


def get_model():
    global _model
    if _model is None:
        print("Loading Whisper model...")

        # Faster and lighter model for Render/local testing
        _model = whisper.load_model("tiny")

        print("Whisper model ready!")
    return _model


def convert_to_wav(input_path: str, output_path: str) -> bool:
    """
    Convert incoming audio to 16kHz mono WAV
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
                output_path,
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print("FFmpeg conversion failed!")
            print(result.stderr)
            return False

        return True

    except Exception as e:
        print("FFmpeg Error:", e)
        return False


def transcribe_audio(audio_bytes: bytes) -> dict:
    """
    Receive audio bytes and return transcript
    """

    input_path = None
    output_path = None

    try:
        print("=" * 60)
        print("Received Audio Bytes:", len(audio_bytes) if audio_bytes else 0)

        if not audio_bytes:
            return {
                "text": "",
                "language": "en",
                "segments": [],
            }

        # Save incoming audio
        with tempfile.NamedTemporaryFile(
            suffix=".webm",
            delete=False,
        ) as tmp_input:
            tmp_input.write(audio_bytes)
            input_path = tmp_input.name

        output_path = input_path.replace(".webm", ".wav")

        print("Input File :", input_path)
        print("Output File:", output_path)

        converted = convert_to_wav(
            input_path,
            output_path,
        )

        if not converted:
            return {
                "text": "",
                "language": "en",
                "segments": [],
            }

        print("Starting Whisper...")

        model = get_model()

        result = model.transcribe(
            output_path,
            fp16=False,
            task="transcribe",
            temperature=0,
        )

        print("Whisper Result:", result)

        text = (result.get("text") or "").strip()

        print("TRANSCRIBED:", text)

        segments = []

        for seg in result.get("segments", []):

            seg_text = (seg.get("text") or "").strip()

            if seg_text:

                segments.append(
                    {
                        "text": seg_text,
                        "start": float(seg.get("start", 0)),
                        "end": float(seg.get("end", 0)),
                    }
                )

        return {
            "text": text,
            "language": result.get("language", "en"),
            "segments": segments,
        }

    except Exception as e:
        print("Transcription Error:", e)

        return {
            "text": "",
            "language": "en",
            "segments": [],
        }

    finally:

        if input_path and os.path.exists(input_path):
            os.unlink(input_path)

        if output_path and os.path.exists(output_path):
            os.unlink(output_path)