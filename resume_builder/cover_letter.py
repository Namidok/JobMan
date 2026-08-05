"""
Generates an honest cover letter docx per posting.
Pulls only from config.py content -- no invented achievements.

FIXES IN THIS VERSION:
  * Page size is now A4. It was silently defaulting to US Letter while the
    resume was A4 -- a visible mismatch on a German application.
  * Uses VARIANTS[...]["letter_intro"] instead of pasting the resume
    `summary` verbatim, which produced a headless fragment:
      "I'm writing to apply for X. AI/ML & Data Engineer with 3 years..."
  * The "your posting highlights" line now uses relevance-ranked DISPLAY
    names from scorer.highlights, not alphabetical raw tokens. It also
    suppresses itself entirely when there aren't at least 2 real hits,
    rather than emitting something embarrassing.
  * Adds a Betreff (subject) line, which German convention expects.
  * Normalises the role title: LinkedIn titles arrive as
    "AI Scientist, Internship, Germany - BCG X", which produced
    "the ... - BCG X position at BCG X".
"""

from docx import Document
from docx.shared import Pt, RGBColor, Cm
from datetime import date
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import CONTACT, VARIANTS, validate

GREY = RGBColor(0x55, 0x55, 0x55)

GERMAN_MONTHS = ["Januar", "Februar", "M\u00e4rz", "April", "Mai", "Juni",
                 "Juli", "August", "September", "Oktober", "November", "Dezember"]

TIE_INS = {
    "data_engineer": "the same tools behind my Python ETL and data-validation work on CreditLens",
    "ai_ml": "tools I've applied in production NLP and RAG systems",
    "nlp": "tools I've applied across my NLP systems and RAG document Q&A work",
    "software_eng": "the stack I have shipped production features in",
}

HIGHLIGHTS = {
    "data_engineer": (
        "My most recent project, CreditLens, is a private-credit portfolio monitoring tool "
        "with a Python ETL pipeline that validates and repairs inconsistently formatted "
        "financial data, backed by a star-schema SQLite design and deployed on AWS EC2."
    ),
    "ai_ml": (
        "My most recent project, CreditLens, combines a Python ETL/data-validation pipeline "
        "with a RAG layer (sentence-transformers, ChromaDB, Groq/Llama 3.3) that answers "
        "questions over financial documents with cited sources and declines to answer when "
        "the context doesn't support it."
    ),
    "software_eng": (
        "My most recent project, CreditLens, is an application I scoped, built and shipped "
        "end to end: a Python backend with a validation pipeline, a SQL schema designed for "
        "time-series comparison, and a Next.js + FastAPI frontend deployed on AWS EC2 behind "
        "Nginx with systemd process management."
    ),
    "nlp": (
        "My work spans several NLP systems in production, from a support chatbot that "
        "autonomously resolved around 72% of customer queries to CreditLens's RAG-based "
        "document Q&A engine with cited, grounded answers."
    ),
}

# Suffixes LinkedIn/Indeed bolt onto job titles.
_TITLE_NOISE = re.compile(
    r"\s*(?:\((?:m|w|f|d|x|all genders)[/\s|,;·-]*(?:m|w|f|d|x)?[/\s|,;·-]*"
    r"(?:m|w|f|d|x)?\)|\(all genders\))\s*",
    re.IGNORECASE,
)

# German gender forms: "Praktikant*in", "Praktikant:innen", "Praktikant/-in".
_GENDER_STAR = re.compile(r"[*:]\s*in(?:nen)?\b|/-?in(?:nen)?\b|\*(?=\s|$)", re.IGNORECASE)


def _german_date():
    today = date.today()
    return f"{today.day}. {GERMAN_MONTHS[today.month - 1]} {today.year}"


def clean_role_title(role: str, company: str = "") -> str:
    """'AI Scientist, Internship, Germany - BCG X' + 'BCG X' -> 'AI Scientist, Internship'."""
    title = (role or "").strip()
    title = _GENDER_STAR.sub("", title)
    title = _TITLE_NOISE.sub(" ", title)

    if company:
        # Drop a trailing "- Company" / "at Company" / "| Company".
        title = re.sub(
            r"\s*[-\u2013\u2014|@]\s*" + re.escape(company.strip()) + r"\s*$",
            "", title, flags=re.IGNORECASE,
        )
        title = re.sub(r"\s+at\s+" + re.escape(company.strip()) + r"\s*$",
                       "", title, flags=re.IGNORECASE)

    # Drop a trailing country/location fragment.
    title = re.sub(r",\s*(?:Germany|Deutschland|Berlin|M\u00fcnchen|Munich|Frankfurt|Hamburg)\s*$",
                   "", title, flags=re.IGNORECASE)

    return re.sub(r"[\s,;\-\u2013\u2014|]+$", "", title).strip() or (role or "").strip()


def _highlight_line(variant_key, highlights):
    """Only emit this sentence when there are >= 2 genuine, display-ready hits.

    The old version fired unconditionally on alphabetically-sorted raw tokens,
    producing: 'Your posting highlights aws, english, german, git, language, rag'.
    """
    if not highlights or len(highlights) < 2:
        return ""
    picked = highlights[:4]
    skills = ", ".join(picked[:-1]) + f" and {picked[-1]}"
    return f"Your posting calls for {skills} \u2014 {TIE_INS[variant_key]}."


def build_cover_letter(variant_key: str, company: str, role: str, output_path: str,
                       matched=None, highlights=None):
    validate()

    variant = VARIANTS[variant_key]
    # Back-compat: older callers passed `matched` (raw tokens) only.
    highlights = highlights if highlights is not None else (matched or [])
    role_clean = clean_role_title(role, company)

    parts = [
        f"Berlin, {_german_date()}",
        f"Application for the {role_clean} position",          # Betreff
        f"Dear Hiring Team at {company},",
        (f"I am writing to apply for the {role_clean} position at {company}. "
         f"{variant['letter_intro']}"),
        HIGHLIGHTS[variant_key],
    ]

    line = _highlight_line(variant_key, highlights)
    if line:
        parts.append(line)

    parts += [
        "I have attached my CV with further detail on my experience and projects, including "
        "CreditLens, SkillSync and CoverCraft \u2014 all live, self-deployed applications. "
        "I would welcome the chance to talk about how I could contribute to your team.",
        "Thank you for your consideration.",
        f"Best regards,\nSrikar Kodi\n{CONTACT['email']} | {CONTACT['phone']}",
    ]

    doc = Document()
    section = doc.sections[0]          # A4, was defaulting to US Letter
    section.page_height = Cm(29.7)
    section.page_width = Cm(21.0)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    for i, para in enumerate(parts):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(10)
        r = p.add_run(para.strip())
        r.font.size = Pt(11)
        if i == 1:                     # Betreff is bold
            r.bold = True

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    doc.save(output_path)
    return output_path