"""
Estate OS — Estate Plan PDF Generator
=======================================
Generates a professional, printable PDF estate plan from a completed
(or partially completed) interview profile.
"""

from pathlib import Path
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
    KeepTogether, PageBreak, Table, TableStyle,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from questions import CHAPTERS

# ── Colors ─────────────────────────────────────────────────────────────────────

NAVY   = colors.HexColor("#1A2744")
GOLD   = colors.HexColor("#C9A846")
LIGHT  = colors.HexColor("#F7F3EE")
GRAY   = colors.HexColor("#6B7280")
BLACK  = colors.HexColor("#111827")
RED    = colors.HexColor("#7F1D1D")


# ── Styles ──────────────────────────────────────────────────────────────────────

def _make_styles():
    base = getSampleStyleSheet()

    styles = {
        "cover_title": ParagraphStyle("cover_title",
            fontName="Helvetica-Bold", fontSize=28, textColor=NAVY,
            alignment=TA_CENTER, spaceAfter=6),

        "cover_name": ParagraphStyle("cover_name",
            fontName="Helvetica-Bold", fontSize=22, textColor=GOLD,
            alignment=TA_CENTER, spaceAfter=4),

        "cover_sub": ParagraphStyle("cover_sub",
            fontName="Helvetica", fontSize=12, textColor=GRAY,
            alignment=TA_CENTER, spaceAfter=4),

        "cover_warning": ParagraphStyle("cover_warning",
            fontName="Helvetica-Oblique", fontSize=9, textColor=RED,
            alignment=TA_CENTER, spaceAfter=4),

        "section_title": ParagraphStyle("section_title",
            fontName="Helvetica-Bold", fontSize=13, textColor=NAVY,
            spaceBefore=18, spaceAfter=4),

        "field_label": ParagraphStyle("field_label",
            fontName="Helvetica-Bold", fontSize=9, textColor=GRAY,
            spaceBefore=8, spaceAfter=1),

        "field_value": ParagraphStyle("field_value",
            fontName="Helvetica", fontSize=10, textColor=BLACK,
            spaceAfter=2, leading=14),

        "field_empty": ParagraphStyle("field_empty",
            fontName="Helvetica-Oblique", fontSize=10,
            textColor=colors.HexColor("#9CA3AF"), spaceAfter=2),

        "message": ParagraphStyle("message",
            fontName="Helvetica-Oblique", fontSize=11, textColor=BLACK,
            leading=18, spaceAfter=6,
            leftIndent=18, rightIndent=18),

        "footer": ParagraphStyle("footer",
            fontName="Helvetica", fontSize=8, textColor=GRAY,
            alignment=TA_CENTER),

        "incomplete_banner": ParagraphStyle("incomplete_banner",
            fontName="Helvetica-Bold", fontSize=10,
            textColor=colors.HexColor("#92400E"),
            alignment=TA_CENTER),
    }
    return styles


# ── Header / footer ─────────────────────────────────────────────────────────────

def _header_footer(canvas, doc, person_name: str, export_date: str):
    canvas.saveState()
    w, h = letter

    # Header line (skip cover page)
    if doc.page > 1:
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(1.5)
        canvas.line(0.75 * inch, h - 0.55 * inch, w - 0.75 * inch, h - 0.55 * inch)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(NAVY)
        canvas.drawString(0.75 * inch, h - 0.45 * inch, "ESTATE PLAN — CONFIDENTIAL")
        canvas.setFillColor(GRAY)
        canvas.drawRightString(w - 0.75 * inch, h - 0.45 * inch, person_name.upper())

    # Footer
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(0.5)
    canvas.line(0.75 * inch, 0.65 * inch, w - 0.75 * inch, 0.65 * inch)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GRAY)
    canvas.drawString(0.75 * inch, 0.45 * inch, f"Prepared {export_date}")
    canvas.drawCentredString(w / 2, 0.45 * inch, f"Page {doc.page}")
    canvas.drawRightString(w - 0.75 * inch, 0.45 * inch, "Keep in a safe place")

    canvas.restoreState()


# ── Build document ──────────────────────────────────────────────────────────────

def generate_pdf(profile_data: dict, output_path: Path) -> Path:
    """
    Generate a PDF estate plan from profile data.
    profile_data is the dict loaded from the JSON profile file.
    Returns the path to the generated PDF.
    """
    name        = profile_data.get("name", "Unknown")
    answers     = profile_data.get("answers", {})
    created     = profile_data.get("created", "")
    last_updated = profile_data.get("last_updated", "")
    export_date = datetime.now().strftime("%B %d, %Y")

    # Count completion
    total_q   = sum(len(ch["questions"]) for ch in CHAPTERS)
    answered  = sum(1 for v in answers.values() if v.strip())
    pct       = int(answered / total_q * 100) if total_q else 0
    complete  = pct >= 95

    S = _make_styles()
    w, h = letter

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        topMargin=0.85 * inch,
        bottomMargin=0.85 * inch,
        onFirstPage=lambda c, d: _header_footer(c, d, name, export_date),
        onLaterPages=lambda c, d: _header_footer(c, d, name, export_date),
    )

    story = []

    # ── Cover page ──────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1.2 * inch))

    story.append(Paragraph("PERSONAL ESTATE PLAN", S["cover_title"]))
    story.append(Spacer(1, 0.1 * inch))

    # Gold rule
    story.append(HRFlowable(width="80%", thickness=2, color=GOLD, hAlign="CENTER"))
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph(name, S["cover_name"]))
    story.append(Spacer(1, 0.05 * inch))
    story.append(Paragraph("BREAK THE GLASS — EXECUTOR INSTRUCTIONS", S["cover_sub"]))
    story.append(Spacer(1, 0.25 * inch))
    story.append(HRFlowable(width="60%", thickness=0.5, color=GRAY, hAlign="CENTER"))
    story.append(Spacer(1, 0.2 * inch))

    if created:
        story.append(Paragraph(f"Started: {created}", S["cover_sub"]))
    story.append(Paragraph(f"Last updated: {last_updated or export_date}", S["cover_sub"]))
    story.append(Paragraph(f"Exported: {export_date}", S["cover_sub"]))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(f"{pct}% complete  —  {answered} of {total_q} questions answered", S["cover_sub"]))

    story.append(Spacer(1, 0.5 * inch))

    if not complete:
        story.append(Paragraph(
            f"NOTE: This plan is {pct}% complete. Sections below marked [Not yet answered] "
            "should be filled in to give your executor a complete picture.",
            S["incomplete_banner"],
        ))
        story.append(Spacer(1, 0.3 * inch))

    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY, hAlign="CENTER"))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(
        "CONFIDENTIAL — For the named executor and immediate family only.\n"
        "Store one printed copy in a fireproof safe and give one copy to your executor.",
        S["cover_warning"],
    ))

    story.append(PageBreak())

    # ── Emergency contacts page ─────────────────────────────────────────────────
    story.append(Paragraph("FIRST: WHO TO CALL", S["section_title"]))
    story.append(HRFlowable(width="100%", thickness=1, color=GOLD))
    story.append(Spacer(1, 0.1 * inch))

    story.append(Paragraph(
        "If something has happened, these are the most important contacts. Call them in this order.",
        ParagraphStyle("note", fontName="Helvetica-Oblique", fontSize=10, textColor=GRAY, spaceAfter=12)
    ))

    def _contact_row(label, value):
        return [
            Paragraph(label, ParagraphStyle("cl", fontName="Helvetica-Bold", fontSize=9, textColor=GRAY)),
            Paragraph(value or "—", ParagraphStyle("cv", fontName="Helvetica", fontSize=10, textColor=BLACK)),
        ]

    contact_data = [
        _contact_row("EXECUTOR (PRIMARY)",  f"{answers.get('executor_name', '')}  |  {answers.get('executor_phone', '')}"),
        _contact_row("EXECUTOR (BACKUP)",   answers.get("backup_executor", "")),
        _contact_row("SPOUSE / PARTNER",    f"{answers.get('spouse_name', '')}  |  {answers.get('spouse_phone', '')}"),
        _contact_row("ESTATE ATTORNEY",     f"{answers.get('attorney_name', '')}  |  {answers.get('attorney_phone', '')}"),
        _contact_row("FINANCIAL ADVISOR",   answers.get("financial_advisor", "")),
        _contact_row("ACCOUNTANT",          answers.get("accountant", "")),
        _contact_row("PRIMARY DOCTOR",      answers.get("primary_doctor", "")),
    ]

    contact_table = Table(contact_data, colWidths=[1.8 * inch, 4.5 * inch])
    contact_table.setStyle(TableStyle([
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0,0), (-1, -1), 6),
        ("LINEBELOW",   (0, 0), (-1, -2), 0.25, colors.HexColor("#E5E7EB")),
    ]))
    story.append(contact_table)
    story.append(PageBreak())

    # ── Chapter sections ────────────────────────────────────────────────────────
    for ch in CHAPTERS:
        section_items = []
        section_items.append(Paragraph(ch["title"].upper(), S["section_title"]))
        section_items.append(HRFlowable(width="100%", thickness=1, color=GOLD))
        section_items.append(Spacer(1, 0.1 * inch))

        for q in ch["questions"]:
            val = answers.get(q["id"], "").strip()
            section_items.append(Paragraph(q["label"].upper(), S["field_label"]))

            if ch["id"] == "messages" and val:
                section_items.append(Paragraph(val.replace("\n", "<br/>"), S["message"]))
            elif val:
                section_items.append(Paragraph(val.replace("\n", "<br/>"), S["field_value"]))
            else:
                section_items.append(Paragraph("[Not yet answered]", S["field_empty"]))

        story.append(KeepTogether(section_items[:4]))  # keep at least the header + first few fields together
        for item in section_items[4:]:
            story.append(item)
        story.append(Spacer(1, 0.15 * inch))
        story.append(PageBreak())

    doc.build(story)
    return output_path
