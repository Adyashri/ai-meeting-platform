"""
╔══════════════════════════════════════════════════════════════════════════════╗
║       gemini_service.py  —  Gemini AI / LLM Service                         ║
║       Owner: Jui Ramteke  |  AI/ML Pipeline Lead                       ║
║       Module 4 (MOM Generation) + Module 9 (AI Assistant)                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

WHAT THIS FILE DOES:
  All calls to Google Gemini (the LLM) go through this file.
  It handles:

  1. MOM GENERATION — reads the full transcript, produces structured JSON
     with key points, decisions, and action items
  2. LIVE AI ASSISTANT — during the meeting, analyses partial transcript
     and gives real-time suggestions to the host
  3. MULTILINGUAL SUMMARY — generates MOM in Hindi or Marathi
  4. RAG ANSWER GENERATION — given retrieved context + user question,
     generates a natural language answer (called by rag_pipeline.py)

WHY GEMINI?
  - Free tier: 15 requests/minute, 1 million tokens/day (as of 2025)
  - 1M token context window: can process multi-hour meeting transcripts
  - Supports Hindi and Marathi natively
  - Fast response time (~2-5 seconds)
  - Free API key from ai.google.dev

INSTALL:
  pip install google-generativeai
  pip install langchain-google-genai

USAGE:
  from app.ai.gemini_service import generate_mom, get_live_suggestion
"""

import logging
import json
import re
import time
from typing import Optional
import google.generativeai as genai
from app.config import settings

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
#  GEMINI CLIENT SETUP
# ═════════════════════════════════════════════════════════════════════════════

def _get_client() -> genai.GenerativeModel:
    """
    Creates and returns a configured Gemini model instance.

    We use gemini-1.5-flash:
      - Faster and cheaper than gemini-1.5-pro
      - Sufficient for meeting summarisation and chat
      - 1M token context window (handles even 3-hour meeting transcripts)

    GenerationConfig controls how Gemini generates text:
      temperature: 0.3 = focused/deterministic (good for structured output)
                   1.0 = creative/varied (not what we want for MOM)
      max_output_tokens: maximum response length
    """
    genai.configure(api_key=settings.GEMINI_API_KEY)

    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,   # "gemini-1.5-flash"
        generation_config=genai.types.GenerationConfig(
            temperature=0.3,            # low = consistent, factual output
            max_output_tokens=4096,     # enough for full MOM + action items
            top_p=0.8,                  # nucleus sampling parameter
        ),
        safety_settings=[
            # Relax safety filters for meeting content
            # (meeting discussions can mention "threats", "attacks", etc. in business context)
            {"category": "HARM_CATEGORY_HARASSMENT",        "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_HATE_SPEECH",       "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
        ],
    )
    return model


# ═════════════════════════════════════════════════════════════════════════════
#  MODULE 4: MOM GENERATION
# ═════════════════════════════════════════════════════════════════════════════

def generate_mom(
    transcript: str,
    meeting_title: str = "Team Meeting",
    participants: list = None,
    language: str = "en",
) -> dict:
    """
    Generates a structured Minutes of Meeting (MOM) from a meeting transcript.
    This is the most important AI function in the whole project.

    HOW PROMPT ENGINEERING WORKS HERE:
      We use a "structured output" prompt — we tell Gemini to return ONLY
      a JSON object in a specific format. This is called "zero-shot prompting
      with output format specification". No examples needed because the format
      is clear from the JSON structure we specify.

      Key prompt techniques used:
        1. Role assignment: "You are a professional corporate secretary"
        2. Output format: specify exact JSON keys
        3. Constraints: "Base ONLY on what was discussed. Do not invent."
        4. Language instruction: for multilingual support

    Args:
        transcript: full meeting transcript text (formatted with timestamps)
        meeting_title: name of the meeting
        participants: list of participant names
        language: "en" (English), "hi" (Hindi), "mr" (Marathi)

    Returns:
        dict with structure:
        {
            "meeting_title": "Sprint Planning Week 4",
            "summary": "One-paragraph executive summary",
            "key_points": ["Point 1", "Point 2", ...],
            "decisions": [
                {"decision": "Extend deadline by 2 days", "made_by": "Pallavi"},
                ...
            ],
            "action_items": [
                {"task": "Deploy auth to staging", "assignee": "Jui", "deadline": "Friday"},
                ...
            ],
            "next_steps": ["Schedule follow-up meeting", ...],
            "follow_up_date": "Next Monday",
        }
    """
    if not transcript or len(transcript.strip()) < 50:
        logger.warning("Transcript too short for MOM generation")
        return _empty_mom(meeting_title)

    logger.info(f"Generating MOM for '{meeting_title}' ({len(transcript)} chars)")

    # ── Load the MOM prompt template from file ────────────────────────────────
    prompt = _load_prompt("mom_prompt.txt")

    # ── Fill in the template variables ────────────────────────────────────────
    participants_str = ", ".join(participants) if participants else "Not specified"
    language_instruction = _get_language_instruction(language)

    filled_prompt = prompt.format(
        meeting_title=meeting_title,
        participants=participants_str,
        language_instruction=language_instruction,
        transcript=transcript,
    )

    # ── Call Gemini ───────────────────────────────────────────────────────────
    try:
        model = _get_client()
        response = _call_with_retry(model, filled_prompt, max_retries=3)
        raw_text = response.text

        # ── Parse the JSON response ───────────────────────────────────────────
        # Gemini sometimes wraps JSON in markdown code blocks: ```json ... ```
        # We strip those before parsing
        mom_data = _parse_json_response(raw_text)

        # Ensure required fields exist (Gemini might miss some)
        mom_data.setdefault("meeting_title", meeting_title)
        mom_data.setdefault("key_points", [])
        mom_data.setdefault("decisions", [])
        mom_data.setdefault("action_items", [])
        mom_data.setdefault("next_steps", [])
        mom_data.setdefault("summary", "")
        mom_data.setdefault("follow_up_date", "TBD")

        logger.info(
            f"MOM generated: {len(mom_data['key_points'])} key points, "
            f"{len(mom_data['action_items'])} action items"
        )
        return mom_data

    except Exception as e:
        logger.error(f"MOM generation failed: {e}", exc_info=True)
        return _empty_mom(meeting_title, error=str(e))


# ═════════════════════════════════════════════════════════════════════════════
#  MODULE 9: LIVE AI MEETING ASSISTANT
# ═════════════════════════════════════════════════════════════════════════════

def get_live_suggestion(
    partial_transcript: str,
    meeting_agenda: str = "",
    elapsed_minutes: int = 0,
    total_planned_minutes: int = 60,
) -> dict:
    """
    Analyses the live (partial) meeting transcript and provides real-time
    suggestions to the host. Called by the Socket.io service every 2 minutes.

    This is the Module 9 "AI Meeting Assistant" — shown only to the Host
    in the AssistantSidebar component.

    WHAT IT RETURNS:
      - Agenda suggestion: next topic to cover
      - Off-topic alert: if discussion drifted from the agenda
      - Time warning: if the meeting is running over
      - Wrap-up signal: when key topics are covered and meeting can end

    Args:
        partial_transcript: transcript so far (not the full meeting)
        meeting_agenda: the original agenda items (if host set them)
        elapsed_minutes: how many minutes have passed
        total_planned_minutes: how long the meeting was planned to be

    Returns:
        {
            "type": "suggestion" | "warning" | "info",
            "message": "The team has been discussing authentication for 8 minutes...",
            "action": "Consider moving to the next agenda item.",
            "urgency": "low" | "medium" | "high",
            "emoji": "💡"
        }
    """
    if not partial_transcript or len(partial_transcript.strip()) < 100:
        return {
            "type": "info",
            "message": "Meeting is just getting started.",
            "action": "Keep the discussion focused on your agenda.",
            "urgency": "low",
            "emoji": "👋",
        }

    # Limit transcript length to last 2000 chars — we only need recent context
    recent_transcript = partial_transcript[-2000:]

    prompt = _load_prompt("assistant_prompt.txt").format(
        agenda=meeting_agenda or "No agenda specified",
        elapsed_minutes=elapsed_minutes,
        total_planned_minutes=total_planned_minutes,
        time_remaining=max(0, total_planned_minutes - elapsed_minutes),
        recent_transcript=recent_transcript,
    )

    try:
        model = _get_client()
        response = _call_with_retry(model, prompt, max_retries=2)
        suggestion = _parse_json_response(response.text)

        # Validate and set defaults
        suggestion.setdefault("type", "suggestion")
        suggestion.setdefault("message", "Meeting is progressing well.")
        suggestion.setdefault("action", "Continue the discussion.")
        suggestion.setdefault("urgency", "low")
        suggestion.setdefault("emoji", "💡")

        return suggestion

    except Exception as e:
        logger.error(f"Live suggestion failed: {e}")
        return {
            "type": "info",
            "message": "AI assistant is processing...",
            "action": "Continue your discussion.",
            "urgency": "low",
            "emoji": "🤔",
        }


# ═════════════════════════════════════════════════════════════════════════════
#  RAG ANSWER GENERATION
#  (Called by rag_pipeline.py after retrieving relevant context from FAISS)
# ═════════════════════════════════════════════════════════════════════════════

def generate_rag_answer(
    question: str,
    context_chunks: list,
    meeting_title: str = "this meeting",
    language: str = "en",
) -> str:
    """
    Generates a natural language answer to a user's question about the meeting,
    grounded in the specific context chunks retrieved by FAISS.

    This is Step 6 in the RAG pipeline:
      Q: "What was decided about the sprint deadline?"
      → FAISS retrieves 5 relevant transcript chunks
      → This function sends those chunks + question to Gemini
      → Gemini answers ONLY from those chunks (no hallucination)

    WHY THIS IS BETTER THAN JUST ASKING GEMINI THE QUESTION DIRECTLY:
      Without RAG, Gemini might hallucinate an answer or say "I don't know."
      With RAG, we give Gemini the exact relevant parts of the transcript,
      so it answers accurately and can cite the source.

    Args:
        question: user's natural language question
        context_chunks: list of relevant transcript excerpts from FAISS
        meeting_title: for context in the answer
        language: response language ("en", "hi", "mr")

    Returns:
        str: natural language answer to the question
    """
    if not context_chunks:
        return (
            "I couldn't find relevant information in the meeting transcript "
            "to answer that question."
        )

    # Format context chunks with numbering
    formatted_context = "\n\n".join([
        f"[Excerpt {i+1}]\n{chunk}"
        for i, chunk in enumerate(context_chunks)
    ])

    language_instruction = _get_language_instruction(language)

    prompt = f"""You are an intelligent meeting assistant for {meeting_title}.
A user has asked a question about this meeting.

MEETING TRANSCRIPT EXCERPTS (retrieved from the meeting):
{formatted_context}

USER QUESTION: {question}

INSTRUCTIONS:
- Answer ONLY based on the transcript excerpts above
- If the answer is not in the excerpts, say "This was not discussed in the meeting"
- Be specific — mention timestamps or speaker names if available
- Keep the answer concise (2-4 sentences)
- {language_instruction}

ANSWER:"""

    try:
        model = _get_client()
        response = _call_with_retry(model, prompt, max_retries=2)
        return response.text.strip()

    except Exception as e:
        logger.error(f"RAG answer generation failed: {e}")
        return "I'm unable to process your question right now. Please try again."


# ═════════════════════════════════════════════════════════════════════════════
#  MULTILINGUAL SUPPORT — Module 8
# ═════════════════════════════════════════════════════════════════════════════

def translate_mom_to_language(mom_data: dict, target_language: str) -> dict:
    """
    Translates all text fields of a MOM dict into the target language.
    Used when the user selects Hindi or Marathi in the language selector.

    Args:
        mom_data: the English MOM dict from generate_mom()
        target_language: "hi" (Hindi) or "mr" (Marathi)

    Returns:
        MOM dict with all text fields translated
    """
    if target_language == "en":
        return mom_data   # no translation needed

    lang_name = {"hi": "Hindi", "mr": "Marathi"}.get(target_language, "Hindi")

    # Convert the MOM to a JSON string and ask Gemini to translate all values
    mom_json = json.dumps(mom_data, ensure_ascii=False, indent=2)

    prompt = f"""Translate all text values in the following JSON object to {lang_name}.
Keep the JSON structure and keys exactly the same.
Only translate the string values — do not translate JSON keys, dates, or names.
Return ONLY the JSON object, no other text.

JSON TO TRANSLATE:
{mom_json}

TRANSLATED JSON:"""

    try:
        model = _get_client()
        response = _call_with_retry(model, prompt, max_retries=2)
        translated = _parse_json_response(response.text)
        logger.info(f"MOM translated to {lang_name}")
        return translated

    except Exception as e:
        logger.error(f"Translation failed: {e}")
        return mom_data   # return original if translation fails


# ═════════════════════════════════════════════════════════════════════════════
#  INTERNAL HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _load_prompt(filename: str) -> str:
    """
    Loads a prompt template from the app/ai/prompts/ directory.
    Prompt templates are in .txt files with {variable} placeholders.

    Args:
        filename: e.g., "mom_prompt.txt"

    Returns:
        str: the prompt template text
    """
    import os
    prompt_dir = os.path.join(os.path.dirname(__file__), "prompts")
    prompt_path = os.path.join(prompt_dir, filename)

    if not os.path.exists(prompt_path):
        raise FileNotFoundError(
            f"Prompt file not found: {prompt_path}. "
            f"Make sure all prompt .txt files are in app/ai/prompts/"
        )

    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def _call_with_retry(model, prompt: str, max_retries: int = 3) -> object:
    """
    Calls Gemini with exponential backoff retry logic.

    WHY RETRY?
      The Gemini free tier has rate limits (15 req/min).
      Under load, requests may hit the limit and fail with a 429 error.
      Retry with increasing wait times handles this automatically.

    Args:
        model: Gemini model instance
        prompt: the full prompt string
        max_retries: number of attempts before giving up

    Returns:
        Gemini response object
    """
    wait_time = 1   # start with 1 second, doubles each retry

    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return response

        except Exception as e:
            error_str = str(e)

            # Rate limit error — wait and retry
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Gemini rate limit hit (attempt {attempt+1}). "
                        f"Waiting {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    wait_time *= 2  # exponential backoff: 1s, 2s, 4s
                else:
                    raise

            # Other errors — raise immediately
            else:
                logger.error(f"Gemini API error: {e}")
                raise

    raise RuntimeError(f"Gemini call failed after {max_retries} attempts")


def _parse_json_response(raw_text: str) -> dict:
    """
    Parses Gemini's response text into a Python dict.

    Gemini sometimes:
      - Wraps JSON in markdown: ```json { ... } ```
      - Adds explanation before/after the JSON
      - Returns slightly malformed JSON

    This function handles all those cases.

    Args:
        raw_text: raw string from Gemini's response

    Returns:
        dict parsed from the JSON content
    """
    if not raw_text:
        return {}

    text = raw_text.strip()

    # Remove markdown code blocks if present
    # Pattern: ```json ... ``` or ``` ... ```
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*$", "", text)
    text = text.strip()

    # Find the JSON object: look for the outermost { ... }
    # This handles cases where Gemini adds text before/after the JSON
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        text = json_match.group()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}\nRaw text: {text[:200]}")
        # Last resort: return a dict with the raw text as a field
        return {"raw_response": raw_text, "parse_error": str(e)}


def _get_language_instruction(language: str) -> str:
    """Returns a language instruction string to include in prompts."""
    instructions = {
        "en": "Respond in English.",
        "hi": "Respond in Hindi (हिंदी में उत्तर दें). Use Devanagari script.",
        "mr": "Respond in Marathi (मराठीत उत्तर द्या). Use Devanagari script.",
    }
    return instructions.get(language, instructions["en"])


def _empty_mom(meeting_title: str, error: str = None) -> dict:
    """Returns a default/empty MOM structure when generation fails."""
    result = {
        "meeting_title": meeting_title,
        "summary": "MOM could not be generated automatically.",
        "key_points": [],
        "decisions": [],
        "action_items": [],
        "next_steps": [],
        "follow_up_date": "TBD",
    }
    if error:
        result["error"] = error
    return result