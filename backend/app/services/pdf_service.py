from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import io
import json

NAVY  = colors.HexColor("#0D2B6E")
BLUE  = colors.HexColor("#1565C0")
WHITE = colors.white
GRAY  = colors.HexColor("#F1F3F4")
DARK  = colors.HexColor("#212529")

def generate_mom_pdf(mom_data: dict, meeting_title: str) -> bytes:
    """
    MOM data se PDF banao
    Return: PDF bytes
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20*mm,
        rightMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )

    story = []

    title_style = ParagraphStyle(
        "title",
        fontName="Helvetica-Bold",
        fontSize=20,
        textColor=WHITE,
        alignment=TA_CENTER,
        leading=28
    )
    heading_style = ParagraphStyle(
        "heading",
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=NAVY,
        leading=18,
        spaceBefore=12,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        "body",
        fontName="Helvetica",
        fontSize=10,
        textColor=DARK,
        leading=15,
        spaceAfter=4
    )
    small_style = ParagraphStyle(
        "small",
        fontName="Helvetica",
        fontSize=9,
        textColor=colors.HexColor("#6C757D"),
        leading=13
    )

    W = A4[0] - 40*mm

    title_table = Table(
        [[Paragraph("MINUTES OF MEETING", title_style)],
         [Paragraph(meeting_title, ParagraphStyle(
             "sub", fontName="Helvetica",
             fontSize=12, textColor=colors.HexColor("#BBDEFB"),
             alignment=TA_CENTER, leading=16
         ))]],
        colWidths=[W]
    )
    title_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), NAVY),
        ("PADDING",    (0,0), (-1,-1), 12),
        ("GRID",       (0,0), (-1,-1), 0, NAVY),
    ]))
    story.append(title_table)
    story.append(Spacer(1, 12))

    summary = mom_data.get("summary", "")
    if summary:
        story.append(Paragraph("Summary", heading_style))
        story.append(HRFlowable(
            width="100%", thickness=1.5,
            color=BLUE, spaceAfter=6
        ))
        story.append(Paragraph(summary, body_style))
        story.append(Spacer(1, 8))

    discussions = mom_data.get("key_discussions", [])
    if discussions:
        story.append(Paragraph("Key Discussions", heading_style))
        story.append(HRFlowable(
            width="100%", thickness=1.5,
            color=BLUE, spaceAfter=6
        ))
        for d in discussions:
            topic   = d.get("topic", "")
            details = d.get("details", "")
            story.append(Paragraph(
                f"<b>• {topic}</b>: {details}",
                body_style
            ))
        story.append(Spacer(1, 8))

    decisions = mom_data.get("decisions", [])
    if decisions:
        story.append(Paragraph("Decisions Made", heading_style))
        story.append(HRFlowable(
            width="100%", thickness=1.5,
            color=BLUE, spaceAfter=6
        ))
        for i, d in enumerate(decisions, 1):
            decision = d.get("decision", "")
            reason   = d.get("reason", "")
            story.append(Paragraph(
                f"{i}. <b>{decision}</b> — {reason}",
                body_style
            ))
        story.append(Spacer(1, 8))

    action_items = mom_data.get("action_items", [])
    if action_items:
        story.append(
            Paragraph("Action Items", heading_style)
        )
        story.append(HRFlowable(
            width="100%", thickness=1.5,
            color=BLUE, spaceAfter=6
        ))

        # Table headers
        table_data = [["Task", "Assigned To", "Deadline", "Priority"]]

        for item in action_items:
            table_data.append([
                item.get("task", ""),
                item.get("assigned_to", "TBD"),
                item.get("deadline", "TBD"),
                item.get("priority", "medium").upper()
            ])

        action_table = Table(
            table_data,
            colWidths=[80*mm, 35*mm, 35*mm, 25*mm]
        )
        action_table.setStyle(TableStyle([
            ("BACKGROUND",     (0,0), (-1,0),  NAVY),
            ("TEXTCOLOR",      (0,0), (-1,0),  WHITE),
            ("FONTNAME",       (0,0), (-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",       (0,0), (-1,-1), 9),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, GRAY]),
            ("GRID",           (0,0), (-1,-1), 0.4,
             colors.HexColor("#DEE2E6")),
            ("PADDING",        (0,0), (-1,-1), 6),
            ("VALIGN",         (0,0), (-1,-1), "MIDDLE"),
        ]))
        story.append(action_table)
        story.append(Spacer(1, 8))

    next_meeting = mom_data.get("next_meeting", "N/A")
    if next_meeting and next_meeting != "N/A":
        story.append(
            Paragraph("Next Meeting", heading_style)
        )
        story.append(HRFlowable(
            width="100%", thickness=1.5,
            color=BLUE, spaceAfter=6
        ))
        story.append(Paragraph(next_meeting, body_style))

    story.append(Spacer(1, 20))
    footer_table = Table(
        [[Paragraph(
            "Generated by AI Meeting Platform",
            ParagraphStyle(
                "footer",
                fontName="Helvetica",
                fontSize=8,
                textColor=WHITE,
                alignment=TA_CENTER
            )
        )]],
        colWidths=[W]
    )
    footer_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), NAVY),
        ("PADDING",    (0,0), (-1,-1), 8),
        ("GRID",       (0,0), (-1,-1), 0, NAVY),
    ]))
    story.append(footer_table)

    doc.build(story)
    return buffer.getvalue()