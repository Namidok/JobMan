"""
Generates a simple, honest cover letter docx per posting.
Pulls only from config.py content -- no invented achievements.
"""

from docx import Document
from docx.shared import Pt, RGBColor
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import CONTACT, VARIANTS

GREY = RGBColor(0x55, 0x55, 0x55)

TEMPLATE = """Dear Hiring Team at {company},

I'm writing to apply for the {role} position at {company}. I'm a Software Engineer with 3 years of production experience and currently completing an MSc in Computer Science (Big Data & AI) in Berlin, seeking a Pflichtpraktikum (mandatory internship) starting August 2026.

{highlight}

I've attached my resume with further detail on my experience and projects, including CreditLens, SkillSync, and CoverCraft -- all live, self-deployed applications. I'd welcome the chance to talk about how I could contribute to your team.

Thank you for your consideration.

Best regards,
Srikar Kodi
{email} | {phone}
"""

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


def build_cover_letter(variant_key: str, company: str, role: str, output_path: str):
    highlight = HIGHLIGHTS[variant_key]
    text = TEMPLATE.format(
        company=company,
        role=role,
        highlight=highlight,
        email=CONTACT["email"],
        phone=CONTACT["phone"],
    )

    doc = Document()
    for para in text.split("\n\n"):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(10)
        r = p.add_run(para.strip())
        r.font.size = Pt(11)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)
    return output_path
