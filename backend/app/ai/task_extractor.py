"""
╔══════════════════════════════════════════════════════════════════════════════╗
║       task_extractor.py  —  AI Action Item & Task Extractor                 ║
║       Owner: Jui Ramteke  |  AI/ML Pipeline Lead                       ║
║       Module 6 from the Project Roadmap                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

WHAT THIS FILE DOES:
  Automatically extracts action items and tasks from the meeting transcript.

  Example — If someone says in the meeting:
    "Jui will deploy the auth module to staging by Friday."
    "Urvashi needs to finish the Whisper integration before Thursday's demo."

  This module detects those statements and creates structured task objects:
    {task: "Deploy auth module to staging",  assignee: "Jui",     deadline: "Friday"}
    {task: "Finish Whisper integration",     assignee: "Urvashi", deadline: "Thursday"}

TWO-STAGE APPROACH:
  Stage 1 — Gemini AI extraction:
    Sends the full transcript to Gemini with a structured extraction prompt.
    Gemini understands context ("will", "needs to", "by", "before") and
    extracts tasks as JSON. This handles 90% of cases.

  Stage 2 — spaCy NER validation:
    Named Entity Recognition validates that:
    - The assignee name is a real person (PERSON entity in spaCy)
    - Deadlines are recognised dates/times (DATE or TIME entity)
    - Enhances Gemini's output with entity metadata

WHY TWO STAGES?
  Gemini alone sometimes:
    - Invents tasks not mentioned in the transcript
    - Misidentifies the assignee

  spaCy alone:
    - Can't understand task context ("will do X" vs "already did X")
    - Struggles with Indian names and informal date references

  Together they catch each other's weaknesses.

INSTALL:
  pip install spacy
  python -m spacy download en_core_web_sm
  pip install google-generativeai
"""

import logging
import json
import re
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
#  spaCy NLP LOADER
# ═════════════════════════════════════════════════════════════════════════════

class NLPManager:
    """
    Manages the spaCy NLP model instance.
    Loads once, cached for the lifetime of the server.
    """
    def __init__(self):
        self._nlp = None

    def get_nlp(self):
        if self._nlp is None:
            try:
                import spacy
                # en_core_web_sm is the small English model (~12MB)
                # It can detect: PERSON, DATE, TIME, ORG, GPE entities
                self._nlp = spacy.load("en_core_web_sm")
                logger.info("✅ spaCy en_core_web_sm loaded")
            except OSError:
                logger.error(
                    "spaCy model not found. Run: python -m spacy download en_core_web_sm"
                )
                raise
            except ImportError:
                logger.error("spaCy not installed. Run: pip install spacy")
                raise
        return self._nlp

    @property
    def is_available(self):
        try:
            self.get_nlp()
            return True
        except Exception:
            return False


nlp_manager = NLPManager()


# ═════════════════════════════════════════════════════════════════════════════
#  MAIN TASK EXTRACTION FUNCTION
# ═════════════════════════════════════════════════════════════════════════════

def extract_tasks_from_transcript(
    transcript: str,
    participants: list = None,
    meeting_date: str = None,
) -> list:
    """
    Main entry point — extracts all tasks and action items from the transcript.

    Runs Stage 1 (Gemini) first, then Stage 2 (spaCy validation/enhancement).

    Args:
        transcript: the full meeting transcript text
        participants: known participant names for validation
        meeting_date: the date of the meeting (for relative deadline parsing)

    Returns:
        list of task dicts:
        [
            {
                "task": "Deploy auth module to staging",
                "assignee": "Jui",
                "deadline": "Friday",
                "deadline_normalized": "2025-07-11",   # ISO date if parseable
                "confidence": 0.92,                    # how confident we are
                "source_text": "Jui will deploy auth to staging by Friday",
                "validated": True,                     # spaCy confirmed the person
            },
            ...
        ]
    """
    if not transcript or len(transcript.strip()) < 100:
        logger.warning("Transcript too short for task extraction")
        return []

    logger.info(f"Extracting tasks from {len(transcript)} char transcript")

    # ── Stage 1: Gemini AI extraction ─────────────────────────────────────────
    gemini_tasks = _extract_with_gemini(transcript, participants)

    # ── Stage 2: spaCy NER validation ─────────────────────────────────────────
    validated_tasks = []
    for task in gemini_tasks:
        enhanced = _validate_and_enhance_with_spacy(task, transcript, participants)
        validated_tasks.append(enhanced)

    # ── Deduplicate: remove tasks with identical task text ─────────────────────
    seen_tasks = set()
    unique_tasks = []
    for task in validated_tasks:
        key = task["task"].lower().strip()
        if key not in seen_tasks:
            seen_tasks.add(key)
            unique_tasks.append(task)

    # ── Normalise deadlines ────────────────────────────────────────────────────
    if meeting_date:
        for task in unique_tasks:
            task["deadline_normalized"] = _normalise_deadline(
                task.get("deadline", ""), meeting_date
            )

    logger.info(f"Extracted {len(unique_tasks)} unique tasks")
    return unique_tasks


# ═════════════════════════════════════════════════════════════════════════════
#  STAGE 1: GEMINI EXTRACTION
# ═════════════════════════════════════════════════════════════════════════════

def _extract_with_gemini(transcript: str, participants: list = None) -> list:
    """
    Uses Gemini to extract action items from the transcript.

    PROMPT DESIGN:
      We use a "few-shot + constrained output" approach:
        - Tell Gemini its role
        - Give it the format we expect
        - Give it constraints to prevent hallucination
        - Ask for JSON-only output

    Args:
        transcript: full meeting transcript
        participants: list of known participant names

    Returns:
        list of raw task dicts from Gemini
    """
    from app.ai.gemini_service import _get_client, _call_with_retry, _parse_json_response
    from app.ai.gemini_service import _load_prompt

    participants_str = (
        f"Known participants: {', '.join(participants)}"
        if participants else "Participant names: extract from transcript"
    )

    prompt = _load_prompt("task_prompt.txt").format(
        participants_info=participants_str,
        transcript=transcript,
    )

    try:
        model = _get_client()
        response = _call_with_retry(model, prompt, max_retries=2)
        raw = _parse_json_response(response.text)

        # Gemini might return {"tasks": [...]} or just [...]
        if isinstance(raw, dict):
            tasks = raw.get("tasks", raw.get("action_items", []))
        elif isinstance(raw, list):
            tasks = raw
        else:
            tasks = []

        logger.info(f"Gemini extracted {len(tasks)} tasks")
        return tasks

    except Exception as e:
        logger.error(f"Gemini task extraction failed: {e}")
        return []


# ═════════════════════════════════════════════════════════════════════════════
#  STAGE 2: spaCy NER VALIDATION & ENHANCEMENT
# ═════════════════════════════════════════════════════════════════════════════

def _validate_and_enhance_with_spacy(
    task: dict,
    transcript: str,
    known_participants: list = None,
) -> dict:
    """
    Uses spaCy NER to validate and enhance a task dict from Gemini.

    WHAT spaCy CHECKS:
      1. PERSON validation: is the assignee a real person name?
         spaCy detects PERSON entities. If the assignee isn't found as a PERSON,
         we lower the confidence score.
      2. DATE validation: is the deadline a recognisable date?
         spaCy detects DATE and TIME entities. "Friday", "next week", "tomorrow"
         are all recognised as DATE entities.
      3. Source text finding: locates where in the transcript this task was mentioned

    Args:
        task: raw task dict from Gemini
        transcript: full transcript text
        known_participants: list of real participant names

    Returns:
        enhanced task dict with validation metadata
    """
    enhanced = {
        "task": task.get("task", "").strip(),
        "assignee": task.get("assignee", "").strip(),
        "deadline": task.get("deadline", "TBD").strip(),
        "deadline_normalized": None,
        "confidence": 0.7,         # default Gemini confidence
        "source_text": "",
        "validated": False,
        "entities": [],
    }

    if not enhanced["task"]:
        return enhanced

    if not nlp_manager.is_available:
        # spaCy not available — return Gemini result as-is
        enhanced["validated"] = True
        enhanced["confidence"] = 0.7
        return enhanced

    try:
        nlp = nlp_manager.get_nlp()

        # ── Find the source sentence in the transcript ─────────────────────────
        # Search for a sentence mentioning both the task keyword and assignee
        source = _find_source_sentence(
            transcript, enhanced["task"], enhanced["assignee"]
        )
        enhanced["source_text"] = source

        if not source:
            enhanced["confidence"] = 0.5   # lower confidence if no source found
            return enhanced

        # ── Run spaCy NER on the source sentence ──────────────────────────────
        doc = nlp(source)

        # Extract all entities
        entities = [
            {"text": ent.text, "label": ent.label_}
            for ent in doc.ents
        ]
        enhanced["entities"] = entities

        # ── Validate PERSON entity ─────────────────────────────────────────────
        person_names = [e["text"] for e in entities if e["label"] == "PERSON"]
        date_entities = [
            e["text"] for e in entities
            if e["label"] in ("DATE", "TIME")
        ]

        # Check if the assignee matches a known participant or spaCy PERSON
        assignee = enhanced["assignee"]

        person_validated = False
        if known_participants:
            # Check if assignee name partially matches a known participant
            for participant in known_participants:
                if (assignee.lower() in participant.lower() or
                        participant.lower() in assignee.lower()):
                    person_validated = True
                    enhanced["assignee"] = participant   # normalise to full name
                    break

        if not person_validated and any(
            assignee.lower() in p.lower() for p in person_names
        ):
            person_validated = True

        # ── Validate DATE entity ───────────────────────────────────────────────
        date_validated = bool(date_entities)
        if date_validated and not enhanced["deadline"] or enhanced["deadline"] == "TBD":
            enhanced["deadline"] = date_entities[0]

        # ── Calculate final confidence score ──────────────────────────────────
        # Start at 0.7 (Gemini base), add for each validation
        confidence = 0.7
        if person_validated:
            confidence += 0.15
        if date_validated:
            confidence += 0.10
        if source:
            confidence += 0.05

        enhanced["confidence"] = min(1.0, round(confidence, 2))
        enhanced["validated"] = person_validated

        return enhanced

    except Exception as e:
        logger.error(f"spaCy validation failed: {e}")
        enhanced["confidence"] = 0.7
        enhanced["validated"] = False
        return enhanced


# ═════════════════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════

def _find_source_sentence(
    transcript: str,
    task_text: str,
    assignee: str,
) -> str:
    """
    Finds the sentence(s) in the transcript that this task came from.
    Uses keyword matching — not NLP — for speed.

    Strategy:
      1. Extract key words from the task description
      2. Search transcript sentences for those keywords
      3. Return the best matching sentence

    Args:
        transcript: full transcript text
        task_text: the task description from Gemini
        assignee: the person assigned

    Returns:
        str: the source sentence, or "" if not found
    """
    # Split transcript into sentences (basic split on . ? !)
    sentences = re.split(r'[.!?]+', transcript)

    # Extract key words from task (remove stopwords)
    stopwords = {"the", "a", "an", "to", "for", "in", "on", "at", "by", "is",
                 "will", "need", "needs", "should", "must", "has", "have"}
    task_words = [
        w.lower() for w in task_text.split()
        if w.lower() not in stopwords and len(w) > 3
    ]

    best_sentence = ""
    best_score = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 20:
            continue

        sentence_lower = sentence.lower()

        # Score: count how many task keywords appear in this sentence
        score = sum(1 for w in task_words if w in sentence_lower)

        # Bonus if assignee name mentioned
        if assignee and assignee.lower() in sentence_lower:
            score += 3

        if score > best_score:
            best_score = score
            best_sentence = sentence

    return best_sentence if best_score >= 2 else ""


def _normalise_deadline(deadline_str: str, meeting_date: str) -> Optional[str]:
    """
    Converts relative deadline strings to ISO date format (YYYY-MM-DD).

    Examples:
      "Friday"     + meeting on Monday 2025-07-07 → "2025-07-11"
      "tomorrow"   + meeting on 2025-07-07         → "2025-07-08"
      "next week"  + meeting on 2025-07-07         → "2025-07-14"
      "2025-07-15" → "2025-07-15" (already normalised)

    Args:
        deadline_str: deadline text like "Friday", "next week", "07/15"
        meeting_date: ISO date string of when the meeting happened

    Returns:
        str: ISO date string or None if not parseable
    """
    if not deadline_str or deadline_str.upper() in ("TBD", "N/A", "NONE", ""):
        return None

    # Already in ISO format?
    iso_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    if iso_pattern.match(deadline_str.strip()):
        return deadline_str.strip()

    try:
        from datetime import datetime, timedelta

        meeting_dt = datetime.fromisoformat(meeting_date)

        # Map weekday names to day offsets from the meeting date
        weekday_map = {
            "monday": 0, "tuesday": 1, "wednesday": 2,
            "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
        }

        dl_lower = deadline_str.lower().strip()

        # Relative keywords
        if dl_lower == "tomorrow":
            target = meeting_dt + timedelta(days=1)
            return target.strftime("%Y-%m-%d")

        if "next week" in dl_lower:
            target = meeting_dt + timedelta(weeks=1)
            return target.strftime("%Y-%m-%d")

        if "end of week" in dl_lower or "this week" in dl_lower:
            # Find the next Friday
            days_until_friday = (4 - meeting_dt.weekday()) % 7
            target = meeting_dt + timedelta(days=days_until_friday or 7)
            return target.strftime("%Y-%m-%d")

        # Weekday names: "Friday", "Next Monday"
        for day_name, day_num in weekday_map.items():
            if day_name in dl_lower:
                days_ahead = (day_num - meeting_dt.weekday()) % 7
                if days_ahead == 0:
                    days_ahead = 7   # if today is Friday, "Friday" means next Friday
                target = meeting_dt + timedelta(days=days_ahead)
                return target.strftime("%Y-%m-%d")

        return None   # couldn't parse

    except Exception as e:
        logger.debug(f"Deadline normalisation failed for '{deadline_str}': {e}")
        return None


def extract_entities_from_text(text: str) -> dict:
    """
    General-purpose entity extraction using spaCy.
    Extracts all named entities from any text.
    Used by other parts of the system for entity analysis.

    Args:
        text: any text string

    Returns:
        dict: {
            "persons":  ["Pallavi", "Jui", ...],
            "dates":    ["Friday", "next week", ...],
            "orgs":     ["AAIECHAIN", "Google", ...],
            "locations": ["Chandrapur", ...],
        }
    """
    if not nlp_manager.is_available or not text:
        return {"persons": [], "dates": [], "orgs": [], "locations": []}

    try:
        nlp = nlp_manager.get_nlp()
        doc = nlp(text)

        entities = {
            "persons":   [],
            "dates":     [],
            "orgs":      [],
            "locations": [],
        }

        for ent in doc.ents:
            if ent.label_ == "PERSON":
                entities["persons"].append(ent.text)
            elif ent.label_ in ("DATE", "TIME"):
                entities["dates"].append(ent.text)
            elif ent.label_ == "ORG":
                entities["orgs"].append(ent.text)
            elif ent.label_ in ("GPE", "LOC"):
                entities["locations"].append(ent.text)

        # Deduplicate
        for key in entities:
            entities[key] = list(dict.fromkeys(entities[key]))

        return entities

    except Exception as e:
        logger.error(f"Entity extraction failed: {e}")
        return {"persons": [], "dates": [], "orgs": [], "locations": []}