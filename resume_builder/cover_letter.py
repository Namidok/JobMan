"""
Generates a simple, honest cover letter docx per posting.
Pulls only from config.py content -- no invented achievements.

JD AWARENESS: when the caller passes the `matched` keyword list (the resume
keywords that appeared in the actual JD), a truthful sentence naming those
skills is injected into the letter. Facts like role/experience/availability
come from config.py (VARIANTS + CONTACT), never hardcoded.
"""

from docx import Document
from docx.shared import Pt, RGBColor
from datetime import date
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import CONTACT, VARIANTS

GREY = RGBColor(0x55, 0x55, 0x55)

GERMAN_MONTHS = ["Januar", "Februar", "M\u00e4rz", "April", "Mai", "Juni",
                 "Juli", "August", "September", "Oktober", "November", "Dezember"]

TIE_INS = {
    "data_engineer": "the same tools behind my Python ETL and data-validation work on CreditLens",
    "ai_ml": "tools I've applied in production NLP and RAG systems",
    "nlp": "tools I've applied across my NLP systems and RAG document Q&A work",
}

HIGHLIGHTS = {
    "data_engineer": (
        "My recent project, CreditLens, is a private-credit portfolio monitoring tool with a "
        "Python ETL pipeline that validates and repairs inconsistently formatted financial "
        "data, backed by a star-schema SQLite design -- work directly relevant to the data "
        "engineering challenges your team is solving."
    ),
    "ai_ml": (
        "My recent project, CreditLens, combines a Python ETL/data-validation pipeline with a "
        "RAG layer (sentence-transformers, ChromaDB, Groq/Llama 3.3) that answers questions "
        "over financial documents with cited sources -- the kind of applied AI/ML work I'd "
        "bring to this role."
    ),
    "nlp": (
        "My work spans several NLP systems in production, from an NLP-powered support chatbot "
        "to CreditLens's RAG-based document Q&A engine with cited, hallucination-checked "
        "answers -- directly relevant to the NLP work this role involves."
    ),
}


def _german_date():
    today = date.today()
    return f"{today.day}. {GERMAN_MONTHS[today.month - 1]} {today.year}"


def _jd_line(variant_key, matched):
    if not matched:
        return ""
    skills = ", ".join(matched[:6])
    return (f"Your posting highlights {skills} \u2014 {TIE_INS[variant_key]}.")


def build_cover_letter(variant_key: str, company: str, role: str, output_path: str,
                       matched=None):
    variant = VARIANTS[variant_key]
    matched = matched or []

    parts = [
        f"Berlin, {_german_date()}",
        f"Dear Hiring Team at {company},",
        (f"I'm writing to apply for the {role} position at {company}. "
         f"{variant['summary']}"),
        HIGHLIGHTS[variant_key],
    ]
    jd_line = _jd_line(variant_key, matched)
    if jd_line:
        parts.append(jd_line)
    parts += [
        "I've attached my resume with further detail on my experience and projects, "
        "including CreditLens, SkillSync, and CoverCraft -- all live, self-deployed "
        "applications. I'd welcome the chance to talk about how I could contribute to "
        "your team.",
        "Thank you for your consideration.",
        f"Best regards,\nSrikar Kodi\n{CONTACT['email']} | {CONTACT['phone']}",
    ]
    text = "\n\n".join(parts)

    doc = Document()
    for para in text.split("\n\n"):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(10)
        r = p.add_run(para.strip())
        r.font.size = Pt(11)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)
    return output_path
