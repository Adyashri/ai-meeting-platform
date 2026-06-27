import os
import json
import re
from typing import List, Dict, Any
import google.generativeai as genai
from app.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)


def clean_transcript_text(text: str) -> str:
    if not text:
        return ""

    # extra spaces cleanup
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()

    # broken trailing fragments remove (optional safe cleanup)
    text = text.replace("..", ".")
    return text


def extract_json_from_response(raw_text: str) -> dict:
    """
    Gemini response se valid JSON nikaalne ki koshish.
    """
    if not raw_text:
        raise ValueError("Empty Gemini response")

    raw_text = raw_text.strip()

    # markdown cleanup
    if raw_text.startswith("```json"):
        raw_text = raw_text.replace("```json", "", 1).strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.replace("```", "", 1).strip()
    if raw_text.endswith("```"):
        raw_text = raw_text[:-3].strip()

    # direct parse
    try:
        return json.loads(raw_text)
    except Exception:
        pass

    # first {...} block extract
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if match:
        possible_json = match.group(0)
        return json.loads(possible_json)

    raise ValueError("Could not parse JSON from Gemini response")


def build_fallback_mom(transcript_text: str, meeting_title: str, attendees: List[str]) -> Dict[str, Any]:
    """
    Gemini fail ho jaye to bhi transcript-based MOM do.
    Generic bakwaas summary nahi.
    """
    attendees_text = ", ".join(attendees) if attendees else "Unknown"

    lines = []
    for part in re.split(r"(?<=[.!?])\s+", transcript_text):
        part = part.strip()
        if part:
            lines.append(part)

    short_summary = transcript_text[:250].strip()
    if not short_summary:
        short_summary = f"Meeting '{meeting_title}' was conducted with attendees: {attendees_text}."

    key_discussions = []
    action_items = []
    decisions = []

    # Very lightweight heuristic extraction
    for line in lines[:6]:
        lower = line.lower()

        if any(word in lower for word in ["discussed", "reviewed", "talked about", "project", "integration", "page", "platform"]):
            key_discussions.append({
                "topic": "Discussion Point",
                "details": line
            })

        if any(word in lower for word in ["need to", "next", "will", "should", "improve", "complete", "fix"]):
            action_items.append({
                "task": line,
                "assigned_to": attendees[0] if attendees else "Team",
                "deadline": "N/A",
                "priority": "medium"
            })

        if any(word in lower for word in ["completed", "finalized", "approved", "decided"]):
            decisions.append({
                "decision": line,
                "reason": "Mentioned in transcript"
            })

    # fallback agar kuch bhi extract na hua
    if not key_discussions and transcript_text:
        key_discussions.append({
            "topic": "Meeting Discussion",
            "details": transcript_text[:400]
        })

    return {
        "summary": f"Meeting '{meeting_title}' was conducted with attendees: {attendees_text}. Discussion summary: {short_summary}",
        "key_discussions": key_discussions[:5],
        "decisions": decisions[:5],
        "action_items": action_items[:5],
        "next_meeting": "N/A"
    }


def normalize_mom_data(data: dict) -> dict:
    """
    Ensure final structure हमेशा सही रहे.
    """
    if not isinstance(data, dict):
        data = {}

    summary = data.get("summary", "")
    key_discussions = data.get("key_discussions", [])
    decisions = data.get("decisions", [])
    action_items = data.get("action_items", [])
    next_meeting = data.get("next_meeting", "N/A")

    if not isinstance(summary, str):
        summary = str(summary)

    if not isinstance(key_discussions, list):
        key_discussions = []

    if not isinstance(decisions, list):
        decisions = []

    if not isinstance(action_items, list):
        action_items = []

    if not isinstance(next_meeting, str):
        next_meeting = "N/A"

    # clean structures
    cleaned_discussions = []
    for item in key_discussions:
        if isinstance(item, dict):
            cleaned_discussions.append({
                "topic": str(item.get("topic", "Discussion")).strip(),
                "details": str(item.get("details", "")).strip()
            })

    cleaned_decisions = []
    for item in decisions:
        if isinstance(item, dict):
            cleaned_decisions.append({
                "decision": str(item.get("decision", "")).strip(),
                "reason": str(item.get("reason", "")).strip()
            })

    cleaned_actions = []
    for item in action_items:
        if isinstance(item, dict):
            priority = str(item.get("priority", "medium")).lower().strip()
            if priority not in ["high", "medium", "low"]:
                priority = "medium"

            cleaned_actions.append({
                "task": str(item.get("task", "")).strip(),
                "assigned_to": str(item.get("assigned_to", "Unassigned")).strip(),
                "deadline": str(item.get("deadline", "N/A")).strip(),
                "priority": priority
            })

    return {
        "summary": summary.strip(),
        "key_discussions": cleaned_discussions,
        "decisions": cleaned_decisions,
        "action_items": cleaned_actions,
        "next_meeting": next_meeting.strip() if next_meeting else "N/A"
    }


def generate_mom(transcript_text: str, meeting_title: str, attendees: list[str]):
    """
    Transcript se structured MOM generate karo.
    """
    attendees_text = ", ".join(attendees) if attendees else "Unknown"
    transcript_text = clean_transcript_text(transcript_text)

    if not transcript_text:
        return {
            "summary": f"Meeting '{meeting_title}' was conducted with attendees: {attendees_text}, but no transcript content was available.",
            "key_discussions": [],
            "decisions": [],
            "action_items": [],
            "next_meeting": "N/A"
        }

    prompt = f"""
You are an expert AI meeting assistant.

Generate Minutes of Meeting (MOM) strictly from the transcript below.

IMPORTANT RULES:
1. Use ONLY the transcript content.
2. Do NOT invent fake project details, fake attendees, fake decisions, or fake action items.
3. If a detail is unclear, keep it short and factual.
4. If there are no decisions, return an empty decisions array [].
5. If there are no action items, return an empty action_items array [].
6. If next meeting is not mentioned, return "N/A".
7. Return ONLY valid JSON. No markdown, no explanation.

Return JSON in exactly this format:

{{
  "summary": "short factual summary of the meeting",
  "key_discussions": [
    {{
      "topic": "short topic name",
      "details": "what was discussed"
    }}
  ],
  "decisions": [
    {{
      "decision": "decision taken",
      "reason": "why / context from transcript"
    }}
  ],
  "action_items": [
    {{
      "task": "task to be done",
      "assigned_to": "person name if clearly mentioned else Team",
      "deadline": "deadline if mentioned else N/A",
      "priority": "high or medium or low"
    }}
  ],
  "next_meeting": "next meeting date/time if mentioned else N/A"
}}

Meeting Title: {meeting_title}
Attendees: {attendees_text}

Transcript:
{transcript_text}
"""

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)

        raw_text = ""
        if hasattr(response, "text") and response.text:
            raw_text = response.text.strip()

        if not raw_text:
            raise ValueError("Gemini returned empty response")

        data = extract_json_from_response(raw_text)
        data = normalize_mom_data(data)

        # if Gemini gave almost empty output, use smart fallback
        if (
            not data["summary"]
            and not data["key_discussions"]
            and not data["decisions"]
            and not data["action_items"]
        ):
            return build_fallback_mom(transcript_text, meeting_title, attendees)

        # summary blank ho to fallback summary inject karo
        if not data["summary"]:
            data["summary"] = build_fallback_mom(
                transcript_text, meeting_title, attendees
            )["summary"]

        return data

    except Exception as e:
        print("Gemini MOM generation error:", e)
        return build_fallback_mom(transcript_text, meeting_title, attendees)