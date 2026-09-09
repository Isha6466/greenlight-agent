"""Deterministic Greenlight PDF report (no LLM)."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate, Spacer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"

_CONFIRMED_MARKERS = (
    "FINAL PRODUCTION BRIEF",
    "filmmaker confirmed",
)

_BRIEF_HEADINGS = (
    "Location",
    "Props & Authenticity",
    "Camera & Lighting",
    "Safety",
)

_DOSSIER_FIELDS = (
    ("best_shooting_season", "Best Shooting Season"),
    ("weather_risks", "Weather Risks"),
    ("security_notes", "Security & Permit Notes"),
    ("nearest_hospital", "Nearest Medical Facility"),
)

# ---- markdown cleanup ------------------------------------------------

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_HEADER_RE = re.compile(r"^#{1,6}\s*\d*\.?\s*", re.MULTILINE)
_HR_RE = re.compile(r"^\s*-{3,}\s*$", re.MULTILINE)
_STRAY_NUMBER_RE = re.compile(r"^\s*\d+\.\s*$", re.MULTILINE)

_FIELD_RE = re.compile(
    r"^\s*[-•]\s*\*{0,2}([^\*:\n]+?)\*{0,2}\s*:\s*(.+?)"
    r"(?=\n\s*[-•]\s*\*{0,2}[^\*:\n]+?\*{0,2}\s*:|\Z)",
    re.IGNORECASE | re.DOTALL | re.MULTILINE,
)


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple)):
        parts = [_as_text(item) for item in value]
        return "\n".join(p for p in parts if p)
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            body = _as_text(item)
            if body:
                lines.append(f"{key}: {body}")
        return "\n".join(lines)
    return str(value).strip()


def _xml(text: str) -> str:
    """Escape for reportlab, then convert markdown into real formatting
    instead of printing raw **, ###, --- characters."""
    escaped = escape(text)
    escaped = _HR_RE.sub("", escaped)
    escaped = _HEADER_RE.sub("", escaped)
    escaped = _BOLD_RE.sub(r"<b>\1</b>", escaped)
    return escaped.replace("\n", "<br/>")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "GreenlightTitle", parent=base["Heading1"], fontName="Helvetica-Bold",
            fontSize=18, leading=22, spaceAfter=14, alignment=TA_LEFT,
        ),
        "heading": ParagraphStyle(
            "GreenlightHeading", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=16, leading=20, spaceBefore=10, spaceAfter=10, alignment=TA_LEFT,
        ),
        "body": ParagraphStyle(
            "GreenlightBody", parent=base["BodyText"], fontName="Helvetica",
            fontSize=11, leading=16, spaceAfter=8, alignment=TA_LEFT,
        ),
        "label": ParagraphStyle(
            "GreenlightLabel", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=12, leading=16, spaceBefore=6, spaceAfter=4, alignment=TA_LEFT,
        ),
    }


def _paragraphs(text: str, style: ParagraphStyle, *, skip_if_empty: bool = False) -> list:
    cleaned = (text or "").strip()
    if not cleaned:
        return [] if skip_if_empty else [Paragraph(escape("Not available."), style)]
    blocks = [block.strip() for block in cleaned.split("\n\n") if block.strip()]
    if not blocks:
        blocks = [cleaned]
    return [Paragraph(_xml(block), style) for block in blocks]


def _bullet_items(text: str, style: ParagraphStyle) -> list:
    lines = [line.strip(" •-\t") for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return [Paragraph(escape("No options were recorded for this scene."), style)]
    items = [ListItem(Paragraph(_xml(line), style), leftIndent=12) for line in lines]
    return [
        ListFlowable(
            items, bulletType="bullet", start="•", leftIndent=18,
            bulletFontName="Helvetica", bulletFontSize=11,
        )
    ]


def _grounding_label(gate_decision: Any) -> str:
    text = _as_text(gate_decision).lower()
    if not text:
        return "Unknown"
    if any(t in text for t in (
        "grounding_needed: false", "grounding_needed=false",
        "grounding needed: no", "grounding needed? no", "no grounding",
    )):
        return "No"
    if any(t in text for t in (
        "grounding_needed: true", "grounding_needed=true",
        "grounding needed: yes", "grounding needed? yes",
    )):
        return "Yes"
    if "grounding" in text and " not " in text:
        return "No"
    if "grounding" in text:
        return "Yes"
    return "See reasoning below"


def _parse_field_bullets(text: str) -> dict[str, str]:
    """Parse '- **key**: value' style bullets into a plain dict."""
    fields: dict[str, str] = {}
    for m in _FIELD_RE.finditer(text):
        key = m.group(1).strip().lower()
        value = m.group(2).strip()
        if key and value:
            fields[key] = value
    return fields


def _mood_and_reason(gate_decision: Any) -> tuple[str, str]:
    """Pull mood/tone and reasoning out ONCE each — no duplication,
    even when the source text is a markdown bullet blob."""
    text = _as_text(gate_decision)
    if not text:
        return ("", "")

    fields = _parse_field_bullets(text)
    if fields:
        mood = None
        for key in ("mood / tone / stakes", "mood/tone/stakes", "mood", "tone"):
            if key in fields:
                mood = fields[key]
                break
        if mood is None:
            for key, value in fields.items():
                if "mood" in key or "tone" in key:
                    mood = value
                    break
        reason = fields.get("reason") or fields.get("reasoning")
        if mood or reason:
            return (mood or "", reason or "")

    return (text, "")


def _split_brief_sections(final_brief: str) -> dict[str, str]:
    text = _as_text(final_brief)
    text = _STRAY_NUMBER_RE.sub("", text)  # remove lone "2." "3." "4." lines
    sections = {heading: "" for heading in _BRIEF_HEADINGS}
    if not text:
        return sections

    positions: list[tuple[int, str]] = []
    lowered = text.lower()
    for heading in _BRIEF_HEADINGS:
        idx = lowered.find(heading.lower())
        if idx != -1:
            positions.append((idx, heading))
    if not positions:
        sections["Location"] = text
        return sections

    positions.sort()
    for i, (start, heading) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        chunk = text[start:end].strip()
        if chunk.lower().startswith(heading.lower()):
            chunk = chunk[len(heading):].lstrip(" :\n-")
        sections[heading] = chunk.strip()
    return sections


def _dossier_dict(location_dossier: Any) -> dict[str, str]:
    if isinstance(location_dossier, dict):
        return {k: _as_text(v) for k, v in location_dossier.items()}
    return {}


def generate_pdf_report(
    scene_text: Any,
    gate_decision: Any,
    location_options: Any,
    selected_option: Any,
    final_brief: Any,
    output_path: str | Path,
    location_dossier: Any = None,
) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    styles = _styles()
    story: list = []

    story.append(Paragraph("Greenlight — Scene", styles["title"]))
    story.append(Paragraph("The scene text the filmmaker entered.", styles["label"]))
    story.extend(_paragraphs(_as_text(scene_text), styles["body"]))
    story.append(PageBreak())

    mood, reason = _mood_and_reason(gate_decision)
    story.append(Paragraph("Greenlight — Gate Decision", styles["title"]))
    story.append(Paragraph("Grounding needed", styles["label"]))
    story.append(Paragraph(_xml(_grounding_label(gate_decision)), styles["body"]))
    if mood.strip():
        story.append(Paragraph("Mood / Tone", styles["label"]))
        story.extend(_paragraphs(mood, styles["body"], skip_if_empty=True))
    if reason.strip():
        story.append(Paragraph("Reasoning", styles["label"]))
        story.extend(_paragraphs(reason, styles["body"], skip_if_empty=True))
    story.append(PageBreak())

    options_text = _as_text(location_options)
    story.append(Paragraph("Greenlight — Location / Path Options", styles["title"]))
    if not options_text:
        story.append(Paragraph(
            escape("No location research was run. This scene uses an existing or generic set."),
            styles["body"],
        ))
    else:
        story.append(Paragraph("Options that were considered, each with a short reason.", styles["body"]))
        story.extend(_bullet_items(options_text, styles["body"]))
    story.append(PageBreak())

    story.append(Paragraph("Greenlight — Selected Option", styles["title"]))
    story.append(Paragraph("What the filmmaker selected, and why.", styles["label"]))
    story.extend(_paragraphs(_as_text(selected_option), styles["body"]))
    story.append(PageBreak())

    story.append(Paragraph("Greenlight — Final Production Brief", styles["title"]))
    sections = _split_brief_sections(_as_text(final_brief))
    section_list = [h for h in _BRIEF_HEADINGS if sections.get(h, "").strip()]
    for i, heading in enumerate(section_list):
        story.append(Paragraph(heading, styles["heading"]))
        story.extend(_paragraphs(sections[heading], styles["body"], skip_if_empty=True))
        if i < len(section_list) - 1:
            story.append(PageBreak())

    dossier = _dossier_dict(location_dossier)
    dossier_has_content = any(dossier.get(key, "").strip() for key, _ in _DOSSIER_FIELDS)
    if dossier_has_content:
        story.append(PageBreak())
        story.append(Paragraph("Greenlight — Location Dossier", styles["title"]))
        story.append(Paragraph(
            "Extra research for the confirmed location, via Parallel.",
            styles["body"],
        ))
        for key, label in _DOSSIER_FIELDS:
            content = dossier.get(key, "").strip()
            if not content:
                continue
            story.append(Paragraph(label, styles["heading"]))
            story.extend(_paragraphs(content, styles["body"], skip_if_empty=True))

    doc = SimpleDocTemplate(
        str(path), pagesize=letter,
        leftMargin=0.85 * inch, rightMargin=0.85 * inch,
        topMargin=0.8 * inch, bottomMargin=0.8 * inch,
        title="Greenlight Production Brief", author="Greenlight",
    )
    doc.build(story)
    return str(path.resolve())


def is_confirmed_brief(text: Any) -> bool:
    haystack = _as_text(text)
    return any(marker.lower() in haystack.lower() for marker in _CONFIRMED_MARKERS)


def write_report_from_state(
    state: Mapping[str, Any],
    *,
    final_brief: Any = None,
    selected_option: Any = None,
    output_dir: Path | None = None,
) -> str:
    dest_dir = Path(output_dir) if output_dir else OUTPUT_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = dest_dir / f"greenlight_report_{stamp}.pdf"

    brief = final_brief if final_brief is not None else state.get("production_brief")
    chosen = (
        selected_option
        if selected_option is not None
        else state.get("selected_option")
        or state.get("latest_user_message")
        or brief
    )
    locations = state.get("location_research")
    if not _as_text(locations):
        locations = (
            "No location research was run (Scene Interpreter decided "
            "real-world grounding was not needed)."
        )

    return generate_pdf_report(
        scene_text=state.get("scene_text") or state.get("latest_user_message"),
        gate_decision=state.get("scene_interpretation"),
        location_options=locations,
        selected_option=chosen,
        final_brief=brief,
        output_path=output_path,
        location_dossier=state.get("location_dossier"),
    )