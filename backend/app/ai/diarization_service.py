"""
╔══════════════════════════════════════════════════════════════════════════════╗
║       diarization_service.py  —  Speaker Identification (Who Said What)     ║
║       Owner: Jui Ramteke  |  AI/ML Pipeline Lead                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

WHAT THIS FILE DOES:
  Speaker Diarization = figuring out WHO is speaking at each moment in time.
  Whisper gives us "what was said". This module gives us "WHO said it".

  Example Whisper output (no diarization):
    [00:00:00] Let's start the sprint review.
    [00:00:05] I completed the auth module yesterday.

  With diarization:
    [00:00:00] PALLAVI: Let's start the sprint review.
    [00:00:05] JUI: I completed the auth module yesterday.

HOW IT WORKS:
  pyannote.audio is a deep learning model trained to detect speaker boundaries.
  It outputs "diarization segments" — time ranges with a generic speaker label
  (SPEAKER_00, SPEAKER_01, etc.). We then map these generic labels to real
  participant names using the meeting's participant list.

  Algorithm:
    1. Run pyannote on the audio → get {(start, end): "SPEAKER_00"} dict
    2. Match participant join/leave timestamps to speaker segments
    3. Assign real names based on who was most active in each segment
    4. Return final mapping: {(start, end): "Pallavi"}

INSTALL:
  pip install pyannote.audio
  pip install torch
  # Also need HuggingFace token (free): huggingface.co/settings/tokens
  # Accept pyannote license: huggingface.co/pyannote/speaker-diarization-3.1

NOTE FOR TEAM:
  pyannote requires ~2GB of model weights on first use.
  If your laptop has less than 8GB RAM, use the lightweight fallback
  function diarize_by_audio_energy() instead.
"""

import logging
import os
import time
import tempfile
from typing import Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
#  PYANNOTE PIPELINE MANAGER
#  Loads the heavy diarization model once and caches it.
# ═════════════════════════════════════════════════════════════════════════════

class DiarizationManager:
    """
    Manages the pyannote speaker diarization pipeline.
    Loads the model lazily (only when first used) and caches it.
    """

    def __init__(self):
        self._pipeline = None
        self._available = False     # tracks if pyannote loaded successfully

    def get_pipeline(self):
        """
        Returns the pyannote pipeline, loading it on first call.
        Falls back gracefully if pyannote is not installed or model fails to load.
        """
        if self._pipeline is not None:
            return self._pipeline

        try:
            from pyannote.audio import Pipeline
            import torch

            hf_token = os.getenv("HUGGINGFACE_TOKEN", "")

            if not hf_token:
                logger.warning(
                    "HUGGINGFACE_TOKEN not set in .env — "
                    "diarization will use energy-based fallback."
                )
                self._available = False
                return None

            logger.info("Loading pyannote diarization model (first load ~30s)...")
            start = time.time()

            # Load the state-of-the-art speaker diarization pipeline
            # "speaker-diarization-3.1" is the latest as of 2025
            self._pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=hf_token,
            )

            # Use GPU if available, else CPU
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self._pipeline = self._pipeline.to(device)

            logger.info(f"✅ Pyannote pipeline loaded in {time.time()-start:.1f}s on {device}")
            self._available = True
            return self._pipeline

        except ImportError:
            logger.warning("pyannote.audio not installed — using energy fallback")
            self._available = False
            return None

        except Exception as e:
            logger.error(f"Failed to load pyannote: {e}")
            self._available = False
            return None

    @property
    def is_available(self):
        """True if pyannote loaded successfully and can diarize."""
        return self._available


# Single global instance
diarization_manager = DiarizationManager()


# ═════════════════════════════════════════════════════════════════════════════
#  MAIN DIARIZATION FUNCTION
# ═════════════════════════════════════════════════════════════════════════════

def diarize_audio(
    audio_file_path: str,
    participant_names: list = None,
    num_speakers: Optional[int] = None,
) -> dict:
    """
    Main entry point for speaker diarization.

    Tries pyannote first. Falls back to energy-based method if unavailable.

    Args:
        audio_file_path: path to the complete meeting audio WAV file
        participant_names: list of participant names ["Pallavi", "Jui", "Urvashi", "Adyashri"]
                           Used to assign real names to SPEAKER_00, SPEAKER_01, etc.
        num_speakers: if known, pass this to improve accuracy (optional)

    Returns:
        dict mapping time ranges to speaker names:
        {
            (0.0, 12.4): "Pallavi",
            (12.4, 25.1): "Jui",
            (25.1, 38.9): "Pallavi",
            ...
        }
    """
    pipeline = diarization_manager.get_pipeline()

    if pipeline is not None:
        return _diarize_with_pyannote(
            pipeline, audio_file_path, participant_names, num_speakers
        )
    else:
        logger.info("Using energy-based fallback diarization")
        return _diarize_by_energy(audio_file_path, participant_names)


def _diarize_with_pyannote(
    pipeline,
    audio_file_path: str,
    participant_names: list,
    num_speakers: Optional[int],
) -> dict:
    """
    Uses pyannote neural model for high-accuracy speaker diarization.

    HOW PYANNOTE WORKS INTERNALLY:
      1. Voice Activity Detection (VAD) — finds speech vs silence
      2. Speaker embedding — converts each speech segment to a vector
         (like FAISS embeddings but for voice characteristics)
      3. Clustering — groups similar voice vectors together
         (SPEAKER_00, SPEAKER_01, etc.)
      4. Returns a timeline of who spoke when

    Args:
        pipeline: loaded pyannote pipeline object
        audio_file_path: path to the WAV file
        participant_names: real names to assign (optional)
        num_speakers: hint for the clustering algorithm

    Returns:
        dict: {(start_sec, end_sec): "speaker_name"}
    """
    logger.info(f"Running pyannote diarization on: {audio_file_path}")
    start_time = time.time()

    try:
        kwargs = {}
        if num_speakers:
            # Telling pyannote the exact number of speakers improves accuracy
            kwargs["num_speakers"] = num_speakers

        # Run the diarization pipeline — this is the main neural network call
        diarization = pipeline(audio_file_path, **kwargs)

        # Extract speaker segments from the pyannote result
        # diarization.itertracks(yield_label=True) gives us:
        #   (turn, _, speaker) where turn.start and turn.end are in seconds
        raw_segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            raw_segments.append({
                "start": round(turn.start, 2),
                "end": round(turn.end, 2),
                "speaker_id": speaker,      # "SPEAKER_00", "SPEAKER_01", etc.
            })

        logger.info(
            f"Pyannote found {len(set(s['speaker_id'] for s in raw_segments))} "
            f"unique speakers in {time.time()-start_time:.1f}s"
        )

        # Map generic speaker IDs to real participant names
        speaker_map = _assign_names_to_speakers(raw_segments, participant_names)

        # Build the final output dict: {(start, end): "name"}
        result = {}
        for seg in raw_segments:
            speaker_name = speaker_map.get(seg["speaker_id"], seg["speaker_id"])
            result[(seg["start"], seg["end"])] = speaker_name

        return result

    except Exception as e:
        logger.error(f"Pyannote diarization failed: {e}", exc_info=True)
        return _diarize_by_energy(audio_file_path, participant_names)


def _diarize_by_energy(
    audio_file_path: str,
    participant_names: list = None,
) -> dict:
    """
    Lightweight fallback diarization using audio energy (volume) analysis.

    WHY THIS EXISTS:
      pyannote needs HuggingFace token and ~2GB model download.
      If that's not available, this gives a "good enough" approximation
      by detecting speaker changes based on pauses in speech volume.

    HOW IT WORKS:
      1. Load audio as a numpy array of sample values
      2. Calculate RMS energy in small windows (500ms each)
      3. Detect "speaker change points" = places where volume drops to near-zero
         then comes back up (silence between speakers)
      4. Assign speakers by cycling through participant names at each change point

    LIMITATION: Can't distinguish voices — just detects turn-taking.
    Good enough for transcripts where turn order is informative.

    Args:
        audio_file_path: path to WAV file
        participant_names: names to cycle through at speaker changes

    Returns:
        dict: {(start_sec, end_sec): "speaker_name"}
    """
    try:
        import wave
        import struct

        if not participant_names:
            participant_names = ["Speaker 1", "Speaker 2", "Speaker 3", "Speaker 4"]

        # ── Read WAV file ─────────────────────────────────────────────────────
        with wave.open(audio_file_path, 'r') as wav:
            frames = wav.readframes(wav.getnframes())
            sample_rate = wav.getframerate()
            n_channels = wav.getnchannels()
            sampwidth = wav.getsampwidth()

        # Convert raw bytes to numpy array of audio samples
        try:
            import numpy as np
            fmt = {1: 'B', 2: 'h', 4: 'i'}.get(sampwidth, 'h')
            samples = np.array(struct.unpack(f"{len(frames)//sampwidth}{fmt}", frames))

            # Mix stereo to mono if needed
            if n_channels == 2:
                samples = samples.reshape(-1, 2).mean(axis=1)

            # Normalize to -1.0 to 1.0 range
            samples = samples.astype(float) / (2 ** (sampwidth * 8 - 1))

        except ImportError:
            # Pure Python fallback if numpy not available
            samples_per_frame = len(frames) // sampwidth
            samples = [
                struct.unpack('h', frames[i*2:(i+1)*2])[0] / 32768.0
                for i in range(min(samples_per_frame, 100000))
            ]
            import array
            samples = array.array('f', samples)

        # ── Calculate energy in 500ms windows ────────────────────────────────
        window_size = sample_rate // 2      # 500ms window
        total_duration = len(samples) / sample_rate

        segments = []
        speaker_idx = 0
        segment_start = 0.0
        silence_threshold = 0.01            # RMS below this = silence

        i = 0
        while i < len(samples):
            window = samples[i:i + window_size]

            try:
                import numpy as np
                # Root Mean Square energy of the window
                rms = float(np.sqrt(np.mean(np.array(window, dtype=float) ** 2)))
            except ImportError:
                rms = (sum(s**2 for s in window) / len(window)) ** 0.5

            current_time = i / sample_rate

            # Detect silence gap → potential speaker change
            if rms < silence_threshold and (current_time - segment_start) > 1.5:
                # Only change speaker after at least 1.5 seconds of speech
                if current_time > segment_start:
                    segments.append({
                        "start": segment_start,
                        "end": current_time,
                        "speaker_idx": speaker_idx,
                    })
                    # Move to next speaker (cycle through participants)
                    speaker_idx = (speaker_idx + 1) % len(participant_names)
                    segment_start = current_time

            i += window_size

        # Add final segment
        if segment_start < total_duration:
            segments.append({
                "start": segment_start,
                "end": total_duration,
                "speaker_idx": speaker_idx,
            })

        # ── Build result dict ──────────────────────────────────────────────────
        result = {}
        for seg in segments:
            name = participant_names[seg["speaker_idx"]]
            result[(seg["start"], seg["end"])] = name

        logger.info(f"Energy-based diarization found {len(segments)} segments")
        return result

    except Exception as e:
        logger.error(f"Energy-based diarization failed: {e}")
        # Last resort: return a single segment for the whole audio
        name = participant_names[0] if participant_names else "Speaker 1"
        return {(0.0, 9999.0): name}


# ═════════════════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════

def _assign_names_to_speakers(
    segments: list,
    participant_names: list = None,
) -> dict:
    """
    Maps pyannote's generic speaker IDs (SPEAKER_00, SPEAKER_01...) to
    real participant names by assigning them in order of first appearance.

    WHY ORDER OF FIRST APPEARANCE?
      We can't know WHO is SPEAKER_00 without extra information.
      The host usually speaks first, so SPEAKER_00 → first participant
      who joined is a reasonable heuristic.

    Args:
        segments: list of {start, end, speaker_id} from pyannote
        participant_names: ["Pallavi", "Jui", "Urvashi", "Adyashri"]

    Returns:
        dict: {"SPEAKER_00": "Pallavi", "SPEAKER_01": "Jui", ...}
    """
    if not participant_names:
        participant_names = [f"Speaker {i+1}" for i in range(10)]

    # Find unique speaker IDs in the order they first appear
    seen = []
    for seg in sorted(segments, key=lambda s: s["start"]):
        if seg["speaker_id"] not in seen:
            seen.append(seg["speaker_id"])

    # Map each unique ID to a participant name
    mapping = {}
    for i, speaker_id in enumerate(seen):
        if i < len(participant_names):
            mapping[speaker_id] = participant_names[i]
        else:
            mapping[speaker_id] = f"Speaker {i+1}"

    logger.debug(f"Speaker assignment: {mapping}")
    return mapping


def calculate_talk_time(speaker_map: dict) -> dict:
    """
    Calculates how many seconds each speaker talked.
    Used for the Analytics Dashboard talk-time bar chart.

    Args:
        speaker_map: {(start, end): "speaker_name"} from diarize_audio()

    Returns:
        dict: {"Pallavi": 845.3, "Jui": 612.1, "Urvashi": 450.7, ...}
              (values are in seconds)

    Example output after conversion for display:
        {"Pallavi": "14 min 5 sec", "Jui": "10 min 12 sec", ...}
    """
    talk_time = defaultdict(float)

    for (start, end), speaker in speaker_map.items():
        duration = end - start
        if duration > 0:
            talk_time[speaker] += duration

    # Sort by talk time descending
    sorted_talk_time = dict(
        sorted(talk_time.items(), key=lambda x: x[1], reverse=True)
    )

    logger.info(f"Talk time calculated: {sorted_talk_time}")
    return sorted_talk_time


def format_talk_time_for_display(talk_time_seconds: dict) -> list:
    """
    Converts talk time in seconds to display-ready format for Recharts.

    Args:
        talk_time_seconds: {"Pallavi": 845.3, "Jui": 612.1, ...}

    Returns:
        list of dicts ready for Recharts BarChart:
        [
            {"name": "Pallavi", "minutes": 14, "seconds_total": 845},
            {"name": "Jui",     "minutes": 10, "seconds_total": 612},
        ]
    """
    result = []
    for name, seconds in talk_time_seconds.items():
        minutes = round(seconds / 60, 1)
        result.append({
            "name": name,
            "minutes": minutes,
            "seconds_total": int(seconds),
            "display": f"{int(seconds // 60)}m {int(seconds % 60)}s",
        })
    return result