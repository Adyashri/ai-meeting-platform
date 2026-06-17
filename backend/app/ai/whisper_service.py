"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          whisper_service.py  —  Voice-to-Text Transcription                 ║
║          Owner: Jui Ramteke  |  AI/ML Pipeline Lead                    ║
║          Module 3 from the Project Roadmap                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

WHAT THIS FILE DOES:
  This is the first and most important AI module. It takes raw audio bytes
  (captured from the browser microphone during a meeting) and converts them
  into text using OpenAI Whisper — a transformer neural network trained on
  680,000 hours of speech in 99 languages.

  Supports English, Hindi (हिंदी), and Marathi (मराठी) automatically.
  Runs entirely on your laptop — no API cost, no internet needed after install.

HOW IT FITS INTO THE PROJECT:
  Browser mic → 5-sec WAV chunk → POST /api/transcribe → THIS FILE
  → returns text → Socket.io broadcasts to all participants → TranscriptPanel

WHISPER MODEL SIZES (tradeoff: speed vs accuracy):
  tiny   → fastest, least accurate (~1GB RAM)
  base   → good balance for real-time use ← WE USE THIS LIVE
  small  → better accuracy, slightly slower
  medium → great accuracy
  large  → best accuracy, slow (~10GB RAM)  ← WE USE THIS POST-MEETING

INSTALL:
  pip install openai-whisper
  pip install torch            (auto-installed with whisper)
  pip install ffmpeg-python    (for audio processing)
  # Also install ffmpeg binary: https://ffmpeg.org/download.html
"""

import whisper
import tempfile
import os
import time
import logging
import numpy as np
from typing import Optional

# ─── Logger ──────────────────────────────────────────────────────────────────
# logging.getLogger gives us a named logger — all output tagged with module name
logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
#  MODEL MANAGER
#  Loads Whisper models into memory once and keeps them there.
#  Loading takes ~5 seconds; we never want to do it per-request.
# ═════════════════════════════════════════════════════════════════════════════

class WhisperModelManager:
    """
    Singleton class that manages Whisper model instances.

    WHY A SINGLETON?
      Loading a Whisper model reads ~150MB of neural network weights from disk
      into RAM. If we did this for every audio chunk, each transcription would
      take 5+ extra seconds just to load the model. By keeping it in memory,
      subsequent calls are instant.

    TWO MODELS:
      - 'base'  : loaded for real-time live transcription (fast, ~5 sec/chunk)
      - 'small' : loaded for final post-meeting re-transcription (more accurate)
    """

    def __init__(self):
        # Dictionary holding loaded models: {"base": <model>, "small": <model>}
        self._models: dict = {}

    def get_model(self, size: str = "base") -> whisper.Whisper:
        """
        Returns a loaded Whisper model. Loads it on first call, caches after.

        Args:
            size: one of "tiny", "base", "small", "medium", "large"

        Returns:
            whisper.Whisper: the loaded model ready to transcribe
        """
        if size not in self._models:
            logger.info(f"Loading Whisper '{size}' model into memory...")
            start = time.time()

            # whisper.load_model downloads weights on first use to ~/.cache/whisper/
            # After that it loads from disk cache. CPU is used by default.
            # On a laptop with a GPU, add device="cuda" for 5-10x speedup.
            self._models[size] = whisper.load_model(size)

            elapsed = time.time() - start
            logger.info(f"✅ Whisper '{size}' loaded in {elapsed:.1f}s")

        return self._models[size]


# ─── Global model manager instance ───────────────────────────────────────────
# Import and use this in routes: from app.ai.whisper_service import whisper_manager
whisper_manager = WhisperModelManager()


# ═════════════════════════════════════════════════════════════════════════════
#  CORE TRANSCRIPTION FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════

def transcribe_audio_chunk(
    audio_bytes: bytes,
    language: Optional[str] = None,
    model_size: str = "base",
) -> dict:
    """
    Transcribes a 5-10 second audio chunk from the live meeting.
    Called by the /api/transcribe WebSocket endpoint during meetings.

    HOW IT WORKS STEP BY STEP:
      1. Receive raw audio bytes (WAV format from browser)
      2. Write to a temporary file (Whisper reads from files, not bytes)
      3. Run Whisper inference → get text + timestamps
      4. Delete the temp file (cleanup)
      5. Return structured result

    Args:
        audio_bytes: raw WAV audio data from the browser microphone
        language: language code — "en" (English), "hi" (Hindi), "mr" (Marathi)
                  If None, Whisper auto-detects the language
        model_size: "base" for live, "small"/"medium" for post-meeting

    Returns:
        dict with keys:
          - text: str — the transcribed text
          - segments: list — each segment has {start, end, text}
          - language: str — detected language code
          - duration: float — audio duration in seconds
          - processing_time: float — how long transcription took

    Example return:
        {
            "text": "Let's start the sprint backlog review.",
            "segments": [
                {"start": 0.0, "end": 2.34, "text": "Let's start the sprint"},
                {"start": 2.34, "end": 4.1,  "text": "backlog review."}
            ],
            "language": "en",
            "duration": 4.1,
            "processing_time": 1.23
        }
    """
    if not audio_bytes:
        logger.warning("transcribe_audio_chunk called with empty audio bytes")
        return {"text": "", "segments": [], "language": language or "en",
                "duration": 0, "processing_time": 0}

    start_time = time.time()

    # ── Step 1: Write audio bytes to a temporary WAV file ────────────────────
    # Whisper's transcribe() accepts a file path.
    # delete=False: we control when to delete (in the finally block)
    tmp_file = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False,
            dir="/tmp"          # use /tmp — guaranteed writable on all platforms
        ) as tmp:
            tmp.write(audio_bytes)
            tmp_file = tmp.name   # save path for transcription

        logger.debug(f"Audio chunk saved to temp file: {tmp_file} ({len(audio_bytes)} bytes)")

        # ── Step 2: Load the Whisper model ───────────────────────────────────
        model = whisper_manager.get_model(model_size)

        # ── Step 3: Build transcription options ──────────────────────────────
        # fp16=False: use 32-bit floats (fp16 needs a GPU; CPU uses fp32)
        # task="transcribe": convert speech to text in the SAME language
        #   (vs "translate" which would force output to English)
        options = {
            "fp16": False,
            "task": "transcribe",
            "verbose": False,   # suppress per-segment console output
        }

        # Add language if specified — skip auto-detection (saves ~0.5 seconds)
        if language and language in ["en", "hi", "mr", "hindi", "marathi"]:
            # Map common names to Whisper language codes
            lang_map = {"hindi": "hi", "marathi": "mr"}
            options["language"] = lang_map.get(language, language)

        # ── Step 4: Run Whisper inference ─────────────────────────────────────
        # This is the neural network forward pass — most of the processing time
        result = model.transcribe(tmp_file, **options)

        # ── Step 5: Extract and format the result ─────────────────────────────
        processing_time = time.time() - start_time

        # result["segments"] is a list of dicts, each with:
        #   id, seek, start, end, text, tokens, temperature, avg_logprob, etc.
        # We only need start, end, text for the transcript panel
        cleaned_segments = [
            {
                "start": round(seg["start"], 2),
                "end": round(seg["end"], 2),
                "text": seg["text"].strip(),
            }
            for seg in result.get("segments", [])
            if seg["text"].strip()          # skip empty segments
        ]

        output = {
            "text": result["text"].strip(),
            "segments": cleaned_segments,
            "language": result.get("language", language or "en"),
            "duration": cleaned_segments[-1]["end"] if cleaned_segments else 0,
            "processing_time": round(processing_time, 3),
        }

        logger.info(
            f"Transcription complete: '{output['text'][:60]}...' "
            f"[{output['language']}, {output['processing_time']}s]"
        )
        return output

    except Exception as e:
        logger.error(f"Transcription failed: {e}", exc_info=True)
        # Return empty result instead of crashing — meeting should continue
        return {
            "text": "",
            "segments": [],
            "language": language or "en",
            "duration": 0,
            "processing_time": round(time.time() - start_time, 3),
            "error": str(e),
        }

    finally:
        # ── Step 6: Clean up the temp file ───────────────────────────────────
        # ALWAYS runs, even if an exception occurred above
        if tmp_file and os.path.exists(tmp_file):
            os.unlink(tmp_file)
            logger.debug(f"Temp file deleted: {tmp_file}")


def transcribe_full_recording(
    audio_file_path: str,
    language: Optional[str] = None,
) -> dict:
    """
    Transcribes the complete meeting recording after the meeting ends.
    Uses a larger model ('small') for higher accuracy.
    Called by the Celery background task (workers/tasks.py).

    This produces the authoritative transcript that feeds:
      - MOM generation (Gemini)
      - RAG pipeline (FAISS embeddings)
      - Sentiment analysis (VADER)
      - Talk time calculation

    Args:
        audio_file_path: path to the full meeting WAV file on disk
        language: language code or None for auto-detect

    Returns:
        dict with full transcript text and all segments with timestamps
    """
    logger.info(f"Starting full recording transcription: {audio_file_path}")

    if not os.path.exists(audio_file_path):
        raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

    try:
        # Use 'small' model for better accuracy on the full recording
        model = whisper_manager.get_model("small")

        options = {
            "fp16": False,
            "task": "transcribe",
            "verbose": True,        # show progress for long recordings
            "word_timestamps": True,  # get word-level timestamps for speaker attribution
        }

        if language:
            options["language"] = language

        start_time = time.time()
        result = model.transcribe(audio_file_path, **options)
        elapsed = time.time() - start_time

        logger.info(f"Full transcription complete in {elapsed:.1f}s")

        # Build a clean, formatted transcript string
        # Format: [00:02:34] Text here.
        formatted_lines = []
        for seg in result.get("segments", []):
            timestamp = _seconds_to_timestamp(seg["start"])
            text = seg["text"].strip()
            if text:
                formatted_lines.append(f"[{timestamp}] {text}")

        full_text = "\n".join(formatted_lines)

        return {
            "text": result["text"].strip(),
            "formatted_transcript": full_text,
            "segments": [
                {
                    "start": round(seg["start"], 2),
                    "end": round(seg["end"], 2),
                    "text": seg["text"].strip(),
                    "words": seg.get("words", []),  # word-level timestamps
                }
                for seg in result.get("segments", [])
                if seg["text"].strip()
            ],
            "language": result.get("language", "en"),
            "duration": result["segments"][-1]["end"] if result.get("segments") else 0,
            "processing_time": round(elapsed, 2),
        }

    except Exception as e:
        logger.error(f"Full transcription failed: {e}", exc_info=True)
        raise


def detect_language(audio_bytes: bytes) -> str:
    """
    Detects the spoken language from a short audio sample.
    Used by the frontend language selector to auto-suggest the language.

    Whisper examines the first 30 seconds of audio and returns
    a probability distribution over 99 languages.

    Returns:
        str: language code like "en", "hi", "mr"
    """
    tmp_file = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir="/tmp") as tmp:
            tmp.write(audio_bytes)
            tmp_file = tmp.name

        model = whisper_manager.get_model("base")

        # Load audio and pad/trim to 30 seconds (Whisper's detection window)
        audio = whisper.load_audio(tmp_file)
        audio = whisper.pad_or_trim(audio)

        # Convert to log-Mel spectrogram (the "picture of sound" Whisper sees)
        n_mels = 80 if model.dims.n_mels == 80 else 128
        mel = whisper.log_mel_spectrogram(audio, n_mels=n_mels).to(model.device)

        # Get language probabilities from the encoder
        _, probs = model.detect_language(mel)

        # Return the most probable language
        detected = max(probs, key=probs.get)
        logger.info(f"Language detected: {detected} (confidence: {probs[detected]:.2%})")
        return detected

    except Exception as e:
        logger.error(f"Language detection failed: {e}")
        return "en"     # fallback to English

    finally:
        if tmp_file and os.path.exists(tmp_file):
            os.unlink(tmp_file)


# ═════════════════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════

def _seconds_to_timestamp(seconds: float) -> str:
    """
    Converts seconds (float) to HH:MM:SS timestamp string.

    Example: 154.3 → "00:02:34"
    """
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def format_transcript_for_display(segments: list, speaker_labels: dict = None) -> list:
    """
    Formats raw Whisper segments for the frontend TranscriptPanel component.
    Optionally adds speaker labels from pyannote diarization.

    Args:
        segments: list of {start, end, text} dicts from Whisper
        speaker_labels: dict mapping time ranges to speaker names
                        e.g., {(0.0, 4.5): "Pallavi", (4.5, 9.2): "Jui"}

    Returns:
        list of display-ready transcript lines:
        [
            {
                "timestamp": "00:02:34",
                "speaker": "Pallavi",    # from diarization or "Speaker 1"
                "text": "Let's start the meeting.",
                "start": 154.3,
                "end": 158.7,
            },
            ...
        ]
    """
    lines = []

    for seg in segments:
        speaker = "Unknown"

        # Find speaker for this segment's start time
        if speaker_labels:
            for (t_start, t_end), name in speaker_labels.items():
                if t_start <= seg["start"] < t_end:
                    speaker = name
                    break

        lines.append({
            "timestamp": _seconds_to_timestamp(seg["start"]),
            "speaker": speaker,
            "text": seg["text"],
            "start": seg["start"],
            "end": seg["end"],
        })

    return lines