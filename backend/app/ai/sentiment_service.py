"""
╔══════════════════════════════════════════════════════════════════════════════╗
║       sentiment_service.py  —  Meeting Sentiment Analysis                   ║
║       Owner: Jui Ramteke  |  AI/ML Pipeline Lead                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

WHAT THIS FILE DOES:
  Analyses the emotional tone (sentiment) of a meeting transcript.
  Answers questions like:
    - Was the overall meeting positive, neutral, or negative?
    - Who spoke most positively? Who was most negative?
    - Was the meeting getting more positive or more tense over time?

  This powers the Analytics Dashboard sentiment gauge and timeline chart.

HOW VADER WORKS:
  VADER (Valence Aware Dictionary and sEntiment Reasoner) is a rule-based
  sentiment analyser specifically tuned for short, conversational text.

  It gives 4 scores for any piece of text:
    - pos:      proportion of text that is positive (0.0–1.0)
    - neg:      proportion of text that is negative (0.0–1.0)
    - neu:      proportion of text that is neutral  (0.0–1.0)
    - compound: overall score from -1.0 (most negative) to +1.0 (most positive)

  Classification rules we use:
    compound >= 0.05  → Positive
    compound <= -0.05 → Negative
    else              → Neutral

  Examples:
    "This is a great decision!"              → compound: +0.72  → Positive
    "I strongly disagree with this plan."    → compound: -0.54  → Negative
    "Let's schedule a meeting for Thursday." → compound: +0.0   → Neutral

WHY VADER OVER TRANSFORMERS?
  We could use a BERT-based sentiment model (much more accurate) but VADER:
  - Runs instantly (no neural network, just dictionary lookup)
  - No download needed
  - Works well on conversational meeting language
  - Good enough for a meeting analytics dashboard

INSTALL:
  pip install vaderSentiment
"""

import logging
from typing import Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
#  SENTIMENT ANALYSER — loads VADER on first use
# ═════════════════════════════════════════════════════════════════════════════

class SentimentAnalyser:
    """
    Wraps the VADER sentiment intensity analyser.
    Loads the lexicon once and reuses it for all analysis calls.
    """

    def __init__(self):
        self._analyser = None

    def get_analyser(self):
        """Returns the VADER analyser, creating it on first call."""
        if self._analyser is None:
            try:
                from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
                self._analyser = SentimentIntensityAnalyzer()
                logger.info("✅ VADER sentiment analyser loaded")
            except ImportError:
                logger.error("vaderSentiment not installed. Run: pip install vaderSentiment")
                raise
        return self._analyser

    def score(self, text: str) -> dict:
        """
        Scores a piece of text.

        Args:
            text: any string (sentence, paragraph, full transcript)

        Returns:
            dict: {"compound": 0.72, "pos": 0.4, "neg": 0.1, "neu": 0.5}
        """
        if not text or not text.strip():
            return {"compound": 0.0, "pos": 0.0, "neg": 0.0, "neu": 1.0}
        return self.get_analyser().polarity_scores(text)


# Global instance
_analyser = SentimentAnalyser()


# ═════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ═════════════════════════════════════════════════════════════════════════════

def analyse_full_transcript(
    transcript_segments: list,
    speaker_map: dict = None,
) -> dict:
    """
    Performs comprehensive sentiment analysis on the entire meeting transcript.
    Called by the Celery background task after a meeting ends.

    Args:
        transcript_segments: list of {start, end, text, speaker} dicts
        speaker_map: optional {(start, end): "speaker_name"} from diarization

    Returns:
        Comprehensive sentiment report:
        {
            "overall": {
                "compound": 0.42,
                "label": "Positive",
                "pos": 0.31, "neg": 0.08, "neu": 0.61
            },
            "per_speaker": {
                "Pallavi": {"compound": 0.55, "label": "Positive", "utterance_count": 12},
                "Jui":     {"compound": 0.38, "label": "Positive", "utterance_count": 9},
            },
            "timeline": [
                {"time_window": "0–5min",  "compound": 0.3, "label": "Positive"},
                {"time_window": "5–10min", "compound": 0.1, "label": "Neutral"},
                {"time_window": "10–15min","compound": 0.6, "label": "Positive"},
            ],
            "productivity_score": 78,
            "key_positive_moments": ["Great decision on the API!", ...],
            "key_negative_moments": ["I strongly disagree with this.", ...],
        }
    """
    if not transcript_segments:
        return _empty_sentiment_result()

    logger.info(f"Analysing sentiment for {len(transcript_segments)} transcript segments")

    # ── 1. Overall transcript sentiment ──────────────────────────────────────
    full_text = " ".join(
        seg.get("text", "") for seg in transcript_segments if seg.get("text")
    )
    overall_scores = _analyser.score(full_text)
    overall_label = _compound_to_label(overall_scores["compound"])

    # ── 2. Per-speaker sentiment ──────────────────────────────────────────────
    # Group segments by speaker
    speaker_texts = defaultdict(list)
    for seg in transcript_segments:
        speaker = seg.get("speaker", "Unknown")
        text = seg.get("text", "").strip()
        if text:
            speaker_texts[speaker].append(text)

    per_speaker = {}
    for speaker, texts in speaker_texts.items():
        combined = " ".join(texts)
        scores = _analyser.score(combined)
        per_speaker[speaker] = {
            "compound": round(scores["compound"], 3),
            "label": _compound_to_label(scores["compound"]),
            "pos": round(scores["pos"], 3),
            "neg": round(scores["neg"], 3),
            "neu": round(scores["neu"], 3),
            "utterance_count": len(texts),
        }

    # ── 3. Sentiment timeline (5-minute windows) ──────────────────────────────
    # Group segments into 5-minute buckets for the trend line chart
    timeline = _build_sentiment_timeline(transcript_segments, window_minutes=5)

    # ── 4. Key moments (most positive and most negative utterances) ────────────
    scored_segments = []
    for seg in transcript_segments:
        text = seg.get("text", "").strip()
        if len(text) > 20:      # skip very short utterances
            score = _analyser.score(text)
            scored_segments.append({
                "text": text,
                "compound": score["compound"],
                "speaker": seg.get("speaker", "Unknown"),
                "timestamp": seg.get("start", 0),
            })

    # Sort by compound score to find extremes
    scored_segments.sort(key=lambda x: x["compound"])

    # Bottom 3 = most negative moments
    key_negative = [
        s["text"] for s in scored_segments[:3]
        if s["compound"] < -0.2
    ]

    # Top 3 = most positive moments
    key_positive = [
        s["text"] for s in scored_segments[-3:]
        if s["compound"] > 0.2
    ]

    # ── 5. Productivity score ─────────────────────────────────────────────────
    productivity = _calculate_productivity_score(
        overall_compound=overall_scores["compound"],
        segment_count=len(transcript_segments),
        speaker_count=len(speaker_texts),
        timeline=timeline,
    )

    result = {
        "overall": {
            "compound": round(overall_scores["compound"], 3),
            "label": overall_label,
            "pos": round(overall_scores["pos"], 3),
            "neg": round(overall_scores["neg"], 3),
            "neu": round(overall_scores["neu"], 3),
            "description": _get_sentiment_description(overall_scores["compound"]),
        },
        "per_speaker": per_speaker,
        "timeline": timeline,
        "productivity_score": productivity,
        "key_positive_moments": key_positive[-3:],  # top 3
        "key_negative_moments": key_negative[:3],   # bottom 3
        "segment_count": len(transcript_segments),
        "speaker_count": len(speaker_texts),
    }

    logger.info(
        f"Sentiment analysis complete — overall: {overall_label} "
        f"({overall_scores['compound']:.2f}), productivity: {productivity}"
    )
    return result


def analyse_single_utterance(text: str) -> dict:
    """
    Analyses sentiment of a single utterance in real-time.
    Called during live meetings for the AI meeting assistant sidebar.
    Very fast (< 1ms) since VADER is dictionary-based.

    Args:
        text: a single spoken sentence or utterance

    Returns:
        {"compound": 0.42, "label": "Positive", "emoji": "😊"}
    """
    if not text:
        return {"compound": 0.0, "label": "Neutral", "emoji": "😐"}

    scores = _analyser.score(text)
    compound = scores["compound"]
    label = _compound_to_label(compound)

    emoji_map = {
        "Very Positive": "😄",
        "Positive": "😊",
        "Neutral": "😐",
        "Negative": "😕",
        "Very Negative": "😠",
    }

    return {
        "compound": round(compound, 3),
        "label": label,
        "emoji": emoji_map.get(label, "😐"),
        "pos": round(scores["pos"], 3),
        "neg": round(scores["neg"], 3),
    }


# ═════════════════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════

def _compound_to_label(compound: float) -> str:
    """
    Converts a VADER compound score to a human-readable label.

    Score thresholds from the original VADER paper:
      compound >= 0.05  → Positive
      compound <= -0.05 → Negative
      else              → Neutral

    We add Very Positive / Very Negative for more nuanced display.
    """
    if compound >= 0.5:
        return "Very Positive"
    elif compound >= 0.05:
        return "Positive"
    elif compound <= -0.5:
        return "Very Negative"
    elif compound <= -0.05:
        return "Negative"
    else:
        return "Neutral"


def _get_sentiment_description(compound: float) -> str:
    """
    Returns a natural language description of the meeting's tone.
    Shown in the analytics dashboard as a summary sentence.
    """
    if compound >= 0.5:
        return "Excellent meeting! Very positive and productive atmosphere."
    elif compound >= 0.2:
        return "Good meeting with a generally positive tone."
    elif compound >= 0.05:
        return "Meeting had a slightly positive tone overall."
    elif compound >= -0.05:
        return "Meeting maintained a professional, neutral tone."
    elif compound >= -0.2:
        return "Meeting had some tension. Consider addressing concerns."
    elif compound >= -0.5:
        return "Meeting had a notably negative tone. Follow-up recommended."
    else:
        return "Very tense meeting. Immediate follow-up strongly recommended."


def _build_sentiment_timeline(segments: list, window_minutes: int = 5) -> list:
    """
    Groups transcript segments into time windows and computes
    sentiment for each window. This creates the sentiment trend line
    visible in the Analytics Dashboard.

    Args:
        segments: list of {start, end, text, speaker} dicts
        window_minutes: size of each time bucket in minutes

    Returns:
        list of:
        [
            {"time_window": "0–5 min",  "compound": 0.3, "label": "Positive"},
            {"time_window": "5–10 min", "compound": 0.1, "label": "Neutral"},
        ]
    """
    if not segments:
        return []

    window_seconds = window_minutes * 60
    max_time = max(seg.get("end", seg.get("start", 0)) for seg in segments)

    timeline = []
    t = 0
    while t < max_time:
        t_end = t + window_seconds

        # Collect all text in this time window
        window_texts = [
            seg["text"] for seg in segments
            if t <= seg.get("start", 0) < t_end and seg.get("text", "").strip()
        ]

        if window_texts:
            combined = " ".join(window_texts)
            scores = _analyser.score(combined)
            compound = round(scores["compound"], 3)
        else:
            compound = 0.0

        # Format: "0–5 min", "5–10 min", etc.
        start_label = f"{int(t // 60)}"
        end_label = f"{int(t_end // 60)}"
        timeline.append({
            "time_window": f"{start_label}–{end_label} min",
            "compound": compound,
            "label": _compound_to_label(compound),
            "utterance_count": len(window_texts),
        })

        t = t_end

    return timeline


def _calculate_productivity_score(
    overall_compound: float,
    segment_count: int,
    speaker_count: int,
    timeline: list,
) -> int:
    """
    Calculates a 0–100 productivity score for the meeting.
    This is a custom heuristic — not ML-based.

    FACTORS:
      1. Sentiment (40%): Positive meetings are more productive
      2. Participation (30%): More speakers = more collaboration
      3. Consistency (30%): Sentiment that improves over time is good

    Returns:
        int: score from 0 to 100
    """
    # Factor 1: Sentiment contribution (0–40 points)
    # Map compound (-1 to +1) to (0 to 40)
    sentiment_score = ((overall_compound + 1) / 2) * 40

    # Factor 2: Participation contribution (0–30 points)
    # 1 speaker = 5 pts, 2 = 15 pts, 3 = 22 pts, 4+ = 30 pts
    participation_map = {1: 5, 2: 15, 3: 22}
    participation_score = participation_map.get(speaker_count, 30)

    # Factor 3: Sentiment improvement over time (0–30 points)
    # Check if the last third of the meeting is more positive than the first third
    consistency_score = 15   # neutral baseline
    if len(timeline) >= 3:
        first_third = [w["compound"] for w in timeline[:len(timeline)//3]]
        last_third  = [w["compound"] for w in timeline[-len(timeline)//3:]]
        avg_first = sum(first_third) / len(first_third)
        avg_last  = sum(last_third)  / len(last_third)
        if avg_last > avg_first:
            consistency_score = 30  # improving trend
        elif avg_last < avg_first - 0.2:
            consistency_score = 5   # worsening trend

    total = sentiment_score + participation_score + consistency_score
    return max(0, min(100, round(total)))


def _empty_sentiment_result() -> dict:
    """Returns a zero/neutral sentiment result when no transcript is available."""
    return {
        "overall": {"compound": 0.0, "label": "Neutral", "pos": 0.0, "neg": 0.0, "neu": 1.0,
                    "description": "No transcript data available."},
        "per_speaker": {},
        "timeline": [],
        "productivity_score": 0,
        "key_positive_moments": [],
        "key_negative_moments": [],
        "segment_count": 0,
        "speaker_count": 0,
    }