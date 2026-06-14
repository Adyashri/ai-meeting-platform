def generate_mom(
    transcript: str,
    meeting_title: str,
    attendees: list
) -> dict:

    return {
        "summary": f"Meeting '{meeting_title}' was conducted successfully with attendees: {', '.join(attendees)}. Important topics were discussed and action items were assigned.",

        "key_discussions": [
            {
                "topic": "Project Progress",
                "details": "Team reviewed current project status and pending tasks."
            },
            {
                "topic": "Frontend Development",
                "details": "UI improvements and testing were discussed."
            },
            {
                "topic": "Backend Integration",
                "details": "API integration and MOM generation workflow reviewed."
            }
        ],

        "decisions": [
            {
                "decision": "Continue current development plan",
                "reason": "Project timeline is on track"
            }
        ],

        "action_items": [
            {
                "task": "Complete remaining UI fixes",
                "assigned_to": attendees[0] if attendees else "Team",
                "deadline": "Next Meeting",
                "priority": "high"
            }
        ],

        "next_meeting": "To Be Decided"
    }